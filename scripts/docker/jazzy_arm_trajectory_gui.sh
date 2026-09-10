#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

if [[ -z "${DISPLAY:-}" ]]; then
  echo 'DISPLAY is not set; run this script from the host graphical session.' >&2
  exit 1
fi

export ATOM_UID="$(id -u)"
export ATOM_GID="$(id -g)"
mkdir -p .docker-runtime/jazzy_ws/{build,install,log}

# Mesa cannot always access the host DRI device from this container. In that
# case RViz starts as a ROS node but never creates a usable OpenGL window.
# Default to Mesa software rendering for a portable GUI baseline. Developers
# with a configured GPU passthrough can opt out with
# ATOM_GUI_SOFTWARE_RENDERING=0.
atom_gui_software_rendering="${ATOM_GUI_SOFTWARE_RENDERING:-1}"

./scripts/docker/jazzy_build.sh

docker_args=(
  run --rm
  --name atom-uf850-trajectory-gui
  -e "DISPLAY=${DISPLAY}"
  -e QT_X11_NO_MITSHM=1
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw
)

if [[ "${atom_gui_software_rendering}" == "1" ]]; then
  docker_args+=(
    -e LIBGL_ALWAYS_SOFTWARE=1
  )
fi

xauthority_path="${XAUTHORITY:-${HOME}/.Xauthority}"
if [[ -r "${xauthority_path}" ]]; then
  docker_args+=(
    -e XAUTHORITY=/tmp/atom-xauthority
    -v "${xauthority_path}:/tmp/atom-xauthority:ro"
  )
else
  echo "No readable Xauthority file found at ${xauthority_path}." >&2
  echo 'Set XAUTHORITY to the file used by the current graphical session.' >&2
  exit 1
fi

cleanup_container() {
  docker stop --time 5 atom-uf850-trajectory-gui >/dev/null 2>&1 || true
}
trap cleanup_container EXIT INT TERM

docker compose -f docker-compose.jazzy.yaml "${docker_args[@]}" atom-jazzy bash -lc '
  set -euo pipefail
  log_file=/jazzy_ws/log/atom_uf850_arm_trajectory_gui.log
  ros2 launch xarm_moveit_config uf850_moveit_gazebo.launch.py \
    add_gripper:=false \
    add_vacuum_gripper:=false \
    add_bio_gripper:=false >"${log_file}" 2>&1 &
  launch_pid=$!
  cleanup() {
    kill -INT "${launch_pid}" 2>/dev/null || true
    wait "${launch_pid}" 2>/dev/null || true
  }
  trap cleanup EXIT

  echo "Gazebo and RViz are starting. The trajectory demo will run when ROS is ready."
  for _ in $(seq 1 60); do
    if ros2 node list 2>/dev/null | grep -qx /rviz2; then
      break
    fi
    sleep 0.5
  done
  sleep 3
  ros2 run atom_xarm_sim trajectory_demo
  echo "Trajectory complete. GUI remains open; press Ctrl+C here to stop."
  echo "GUI log: ${log_file}"
  wait "${launch_pid}"
'

trap - EXIT INT TERM

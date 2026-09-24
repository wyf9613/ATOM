#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"
camera_mode="${1:-}"
if [[ "${camera_mode}" != "rgb" && "${camera_mode}" != "depth" ]]; then
  echo "Usage: $0 rgb|depth [rack_dx_m] [rack_dy_m] [rack_dyaw_rad]" >&2
  exit 2
fi
if [[ -z "${DISPLAY:-}" ]]; then
  echo 'DISPLAY is not set; run from a graphical desktop session.' >&2
  exit 1
fi
xauthority_path="${XAUTHORITY:-${HOME}/.Xauthority}"
if [[ ! -r "${xauthority_path}" ]]; then
  echo "No readable Xauthority file at ${xauthority_path}." >&2
  exit 1
fi

export ATOM_UID="$(id -u)"
export ATOM_GID="$(id -g)"
mkdir -p .docker-runtime/jazzy_ws/{build,install,log} tmp/camera_experiment
./scripts/docker/jazzy_build.sh

container_name="atom-camera-experiment-gui"
cleanup_container() {
  docker stop --time 5 "${container_name}" >/dev/null 2>&1 || true
}
trap cleanup_container EXIT INT TERM

docker compose -f docker-compose.jazzy.yaml run --rm \
  --name "${container_name}" \
  -e "DISPLAY=${DISPLAY}" \
  -e QT_X11_NO_MITSHM=1 \
  -e LIBGL_ALWAYS_SOFTWARE=1 \
  -e XAUTHORITY=/tmp/atom-xauthority \
  -e ATOM_CAMERA_MODE="${camera_mode}" \
  -e ATOM_RACK_DX="${2:-0.0}" \
  -e ATOM_RACK_DY="${3:-0.0}" \
  -e ATOM_RACK_DYAW="${4:-0.0}" \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v "${xauthority_path}:/tmp/atom-xauthority:ro" \
  atom-jazzy bash -lc '
    set -euo pipefail
    log_dir=/workspace/tmp/camera_experiment/gui_current
    mkdir -p "${log_dir}"
    rm -f "${log_dir}/report.json" "${log_dir}/rgb_annotated.png" \
      "${log_dir}/depth_m.npy" "${log_dir}/depth_preview.png"
    ros2 launch atom_xarm_sim uf850_arm_only.launch.py \
      camera_mode:="${ATOM_CAMERA_MODE}" demo_gripper:=true gui:=true \
      rack_dx_m:="${ATOM_RACK_DX}" \
      rack_dy_m:="${ATOM_RACK_DY}" \
      rack_dyaw_rad:="${ATOM_RACK_DYAW}" \
      >"${log_dir}/launch.log" 2>&1 &
    launch_pid=$!
    cleanup() {
      kill -INT "${launch_pid}" 2>/dev/null || true
      wait "${launch_pid}" 2>/dev/null || true
    }
    trap cleanup EXIT
    echo "Gazebo and RViz are starting; a held observation pose will follow."
    for _ in $(seq 1 100); do
      if ros2 node list 2>/dev/null | grep -Eq "^/rviz(2)?$"; then
        break
      fi
      sleep 0.5
    done
    ros2 run atom_xarm_sim camera_probe \
      --mode "${ATOM_CAMERA_MODE}" \
      --output-dir "${log_dir}" --min-tags 1 --timeout-sec 90 \
      >"${log_dir}/probe.log" 2>&1 &
    probe_pid=$!
    ros2 run atom_xarm_sim trajectory_demo \
      --ros-args -p hold_at_offset_sec:=30.0 -p allow_demo_gripper_joints:=true \
      -p "demo_offsets_rad:=[0.25,-0.16,-0.19,0.15,0.16,-0.18]" \
      >"${log_dir}/trajectory.log" 2>&1 &
    trajectory_pid=$!
    for _ in $(seq 1 120); do
      if grep -q "PASS: MoveIt planned and executed offset" \
          "${log_dir}/trajectory.log"; then
        break
      fi
      sleep 0.5
    done
    if ! wait "${probe_pid}"; then
      echo "Camera probe did not detect a tag; see ${log_dir}/probe.log" >&2
    fi
    if ! wait "${trajectory_pid}"; then
      echo "Trajectory demo failed; see ${log_dir}/trajectory.log" >&2
    fi
    echo "Camera demo finished. Gazebo/RViz remain open for recording; press Ctrl+C to close."
    echo "Images and logs: tmp/camera_experiment/gui_current"
    wait "${launch_pid}"
  '

trap - EXIT INT TERM

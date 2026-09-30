#!/usr/bin/env bash
# Internal implementation; use scripts/atom.sh.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
operation="${1:?Missing internal operation}"
shift
case "${operation}" in
arm)
if [[ -z "${DISPLAY:-}" ]]; then
  echo 'DISPLAY is not set; run this script from the host graphical session.' >&2
  exit 1
fi

mkdir -p .docker-runtime/jazzy_ws/{build,install,log}

# Mesa cannot always access the host DRI device from this container. In that
# case RViz starts as a ROS node but never creates a usable OpenGL window.
# Default to Mesa software rendering for a portable GUI baseline. Developers
# with a configured GPU passthrough can opt out with
# ATOM_GUI_SOFTWARE_RENDERING=0.
atom_gui_software_rendering="${ATOM_GUI_SOFTWARE_RENDERING:-1}"

"${repo_root}/scripts/atom.sh" build

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
;;
camera)
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

mkdir -p .docker-runtime/jazzy_ws/{build,install,log} tmp/camera_experiment
"${repo_root}/scripts/atom.sh" build

container_name="atom-camera-experiment-gui"
cleanup_container() {
  docker stop --time 5 "${container_name}" >/dev/null 2>&1 || true
}
trap cleanup_container EXIT INT TERM

# The GUI demo is a singleton. If a previous terminal or interrupted run left
# its named container behind, release the name before starting a new session.
if docker container inspect "${container_name}" >/dev/null 2>&1; then
  echo "Stopping stale ${container_name} container from a previous run."
  docker stop --time 5 "${container_name}" >/dev/null 2>&1 || true
  docker rm --force "${container_name}" >/dev/null 2>&1 || true
fi

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
;;
approach)
camera_mode="${1:-}"
if [[ "${camera_mode}" != "rgb" && "${camera_mode}" != "depth" ]]; then
  echo "Usage: $0 rgb|depth [rack_dx_m] [rack_dy_m] [rack_dyaw_rad] [target_distance_m]" >&2
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

mkdir -p .docker-runtime/jazzy_ws/{build,install,log} tmp/camera_experiment/pre_observation_current
"${repo_root}/scripts/atom.sh" build

container_name="atom-pre-observation-gui"
cleanup_container() {
  docker stop --time 5 "${container_name}" >/dev/null 2>&1 || true
}
trap cleanup_container EXIT INT TERM

if docker container inspect "${container_name}" >/dev/null 2>&1; then
  echo "Stopping stale ${container_name} container from a previous run."
  docker stop --time 5 "${container_name}" >/dev/null 2>&1 || true
  docker rm --force "${container_name}" >/dev/null 2>&1 || true
fi

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
  -e ATOM_TARGET_DISTANCE="${5:-0.35}" \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v "${xauthority_path}:/tmp/atom-xauthority:ro" \
  atom-jazzy bash -lc '
    set -euo pipefail
    log_dir=/workspace/tmp/camera_experiment/pre_observation_current
    mkdir -p "${log_dir}"
    rm -f "${log_dir}/pre_observation_report.json" "${log_dir}/approach_report.json" \
      "${log_dir}/tag_observations.jsonl" "${log_dir}/rgb_annotated.png"
    ros2 launch atom_xarm_sim uf850_arm_only.launch.py \
      camera_mode:="${ATOM_CAMERA_MODE}" demo_gripper:=true gui:=true \
      rack_dx_m:="${ATOM_RACK_DX}" \
      rack_dy_m:="${ATOM_RACK_DY}" \
      rack_dyaw_rad:="${ATOM_RACK_DYAW}" \
      >"${log_dir}/launch.log" 2>&1 &
    launch_pid=$!
    ros2 run atom_xarm_sim pre_observation_target_pose \
      --ros-args \
      -p input_topic:=/atom/pre_observation_target \
      -p output_topic:=/atom/pre_observation_pose \
      -p target_distance_m:="${ATOM_TARGET_DISTANCE}" \
      >"${log_dir}/target_pose.log" 2>&1 &
    target_pose_pid=$!
    cleanup() {
      kill -INT "${launch_pid}" 2>/dev/null || true
      wait "${launch_pid}" 2>/dev/null || true
      kill -INT "${target_pose_pid}" 2>/dev/null || true
      wait "${target_pose_pid}" 2>/dev/null || true
    }
    trap cleanup EXIT
    echo "Gazebo and RViz are starting; pre-observation and two-stage approach will run."
    for _ in $(seq 1 120); do
      if ros2 node list 2>/dev/null | grep -Eq "^/rviz(2)?$"; then
        break
      fi
      sleep 0.5
    done
    ros2 run atom_xarm_sim pre_observation_demo \
      --ros-args \
      -p camera_mode:="${ATOM_CAMERA_MODE}" \
      -p rack_dx_m:="${ATOM_RACK_DX}" \
      -p rack_dy_m:="${ATOM_RACK_DY}" \
      -p rack_dyaw_rad:="${ATOM_RACK_DYAW}" \
      -p output_dir:="${log_dir}"
    cp "${log_dir}/pre_observation_report.json" "${log_dir}/pre_observation_report_${ATOM_CAMERA_MODE}.json"
    cp "${log_dir}/approach_report.json" "${log_dir}/approach_report_${ATOM_CAMERA_MODE}.json"
    cp "${log_dir}/tag_observations.jsonl" "${log_dir}/tag_observations_${ATOM_CAMERA_MODE}.jsonl"
    echo "Approach completed. Gazebo/RViz remain open for inspection; press Ctrl+C to close."
    echo "Report and annotated image: ${log_dir}"
    wait "${launch_pid}"
  '

trap - EXIT INT TERM
;;
*) echo "Unknown internal operation: ${operation}" >&2; exit 2 ;;
esac

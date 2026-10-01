#!/usr/bin/env bash
# Internal implementation; use scripts/atom.sh.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
operation="${1:?Missing internal operation}"
shift
case "${operation}" in
workflow)
camera_mode="${1:-depth}"
restart="${2:-}"
workflow="${3:-approach}"
recipe="${4:-visual_approach}"
tag_id="${5:-1}"
[[ "${tag_id}" =~ ^[0-3]$ ]] || { echo "Invalid rack tag ID" >&2; exit 2; }
if [[ "${camera_mode}" != rgb && "${camera_mode}" != depth ]] || [[ -n "${restart}" && "${restart}" != --restart ]] || [[ "${workflow}" != transfer && "${workflow}" != approach ]]; then
  echo "Usage: $0 [rgb|depth] [--restart] [transfer|approach]" >&2
  exit 2
fi
if [[ "${workflow}" == transfer ]]; then
  echo "Legacy fixed-target arm motion test: targets do not correspond to the tube slots; physical pick/place is not executed."
else
  echo "Tag-guided visual approach experiment: physical pick/place is not implemented."
fi
container_name=atom-tube-workflow
if running="$(docker inspect --format '{{.State.Running}}' "${container_name}" 2>/dev/null)"; then
  if [[ "${running}" == true && "${restart}" != --restart ]]; then
    echo "The tube experiment is already running. GUI: http://127.0.0.1:8089"
    echo "To start a new trial: ${repo_root}/scripts/atom.sh sim --camera ${camera_mode} --restart --workflow ${workflow} --recipe ${recipe} --tag-id ${tag_id}"
    echo "To close this session: docker stop ${container_name}"
    exit 0
  fi
  if [[ "${running}" == true ]]; then
    echo "Stopping the existing tube experiment; reports remain in tmp/operator_gui/workflow/."
    docker stop --timeout 5 "${container_name}" >/dev/null
  fi
  # --rm may already have removed it. Remove only a stopped leftover container.
  for attempt in 1 2 3 4 5; do
    if ! docker inspect "${container_name}" >/dev/null 2>&1; then break; fi
    if docker rm "${container_name}" >/dev/null 2>&1; then break; fi
    sleep 0.2
  done
  if docker inspect "${container_name}" >/dev/null 2>&1; then
    echo "Could not release ${container_name}; inspect it before restarting." >&2
    exit 1
  fi
fi
# Detect other GUI instances before starting a scene or moving the arm.
python3 - <<'PORT_CHECK'
import socket
import sys
with socket.socket() as probe:
    probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    try:
        probe.bind(('127.0.0.1',8089))
    except OSError:
        print('Port 8089 is occupied by another GUI. Use http://127.0.0.1:8089 or close that session before launching a new scene.',file=sys.stderr)
        sys.exit(1)
PORT_CHECK
mkdir -p tmp/operator_gui/workflow
# One scene, one original motion runner, and an independent monitor.
docker compose -f docker-compose.jazzy.yaml run --rm -T --name atom-tube-workflow \
  -e ATOM_GUI_TAG_ID="${tag_id}" -e ATOM_GUI_TASK_RECIPE="${recipe}" -e ATOM_GUI_WORKFLOW="${workflow}" -e ATOM_GUI_CAMERA_MODE="${camera_mode}" -e LIBGL_ALWAYS_SOFTWARE=1 atom-jazzy bash -lc '
    set -eo pipefail
    cd /jazzy_ws
    colcon build --base-paths /workspace/ros2_ws/src/atom_xarm_sim --packages-select atom_xarm_sim --symlink-install \
      >/workspace/tmp/operator_gui/workflow/build.log 2>&1
    source /jazzy_ws/install/setup.bash
    cd /workspace
    log_dir="/workspace/tmp/operator_gui/workflow/run_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "${log_dir}"
    echo "Run reports: ${log_dir}"
    ros2 launch atom_xarm_sim uf850_arm_only.launch.py camera_mode:="${ATOM_GUI_CAMERA_MODE}" demo_gripper:=true gui:=false \
      >"${log_dir}/gazebo.log" 2>&1 &
    launch_pid=$!
    if [[ "${ATOM_GUI_WORKFLOW}" == transfer ]]; then
      config_file="$(ros2 pkg prefix atom_xarm_sim)/share/atom_xarm_sim/config/transfer_targets.yaml"
      ros2 run atom_xarm_sim target_publisher --ros-args --params-file "${config_file}" \
        >"${log_dir}/target_pose.log" 2>&1 &
      target_pid=$!
      ros2 run atom_xarm_sim transfer_demo --ros-args --params-file "${config_file}" \
        -p keep_status_alive:=true -p report_path:="${log_dir}/transfer_summary.json" \
        >"${log_dir}/workflow.log" 2>&1 &
    else
      ros2 run atom_xarm_sim pre_observation_target_pose --ros-args -p target_distance_m:=0.35 \
        >"${log_dir}/target_pose.log" 2>&1 &
      target_pid=$!
      ros2 run atom_xarm_sim task_executive --ros-args -p demo_tag_id:="${ATOM_GUI_TAG_ID}" -p task_recipe:="${ATOM_GUI_TASK_RECIPE}" -p depth_registered:=true -p camera_mode:="${ATOM_GUI_CAMERA_MODE}" \
        -p output_dir:="${log_dir}" -p keep_status_alive:=true \
        >"${log_dir}/workflow.log" 2>&1 &
    fi
    workflow_pid=$!
    cleanup() {
      kill -INT "${gateway_pid:-}" "${workflow_pid}" "${target_pid}" "${launch_pid}" 2>/dev/null || true
    }
    trap cleanup EXIT
    python3 tools/operator_gui/server.py --mode ros --port 8089 \
      --ros-config "tools/operator_gui/gazebo_${ATOM_GUI_CAMERA_MODE}.json" &
    gateway_pid=$!
    wait "${launch_pid}"
  '
;;
attach)
camera_mode="${1:-rgb}"
if [[ "${camera_mode}" != rgb && "${camera_mode}" != depth ]]; then echo "Usage: $0 rgb|depth" >&2; exit 2; fi
# Attach to the current ROS_DOMAIN_ID. No Gazebo, controllers or task are started.
docker compose -f docker-compose.jazzy.yaml run --rm -T --name atom-operator-monitor \
  -e ATOM_GUI_CAMERA_MODE="${camera_mode}" atom-jazzy bash -lc '
    python3 tools/operator_gui/server.py --mode ros --port 8089 \
      --ros-config "tools/operator_gui/gazebo_${ATOM_GUI_CAMERA_MODE}.json"
  '
;;
observe)
camera_mode="${1:-rgb}"
if [[ "${camera_mode}" != rgb && "${camera_mode}" != depth ]]; then
  echo "Usage: $0 [rgb|depth]" >&2
  exit 2
fi
control_mode="${2:-monitor}"
if [[ "${control_mode}" != monitor && "${control_mode}" != control ]]; then echo "Second argument must be monitor or control" >&2; exit 2; fi
mkdir -p tmp/operator_gui
# An existing session is never stopped implicitly.
docker compose -f docker-compose.jazzy.yaml run --rm -T --name atom-operator-gazebo \
  -e ATOM_GUI_CONTROL_MODE="${control_mode}" -e ATOM_GUI_CAMERA_MODE="${camera_mode}" -e LIBGL_ALWAYS_SOFTWARE=1 \
  atom-jazzy bash -lc '
    set -eo pipefail
    cd /jazzy_ws
    colcon build --base-paths /jazzy_ws/src /workspace/ros2_ws/src/atom_xarm_sim /workspace/ros2_ws/src/atom_operator_interfaces --packages-select atom_xarm_sim atom_operator_interfaces --symlink-install >/workspace/tmp/operator_gui/build.log 2>&1
    source /jazzy_ws/install/setup.bash
    cd /workspace
    python3 -m py_compile tools/operator_gui/sim_supervisor.py tools/operator_gui/task_client.py
    ros2 launch atom_xarm_sim uf850_arm_only.launch.py camera_mode:="${ATOM_GUI_CAMERA_MODE}" demo_gripper:=true gui:=false \
      >/workspace/tmp/operator_gui/gazebo.log 2>&1 &
    launch_pid=$!
    supervisor_pid=""
    cleanup() {
      if [[ -n "${supervisor_pid}" ]]; then kill -INT "${supervisor_pid}" 2>/dev/null || true; fi
      kill -INT "${launch_pid}" 2>/dev/null || true
    }
    trap cleanup EXIT
    control_args=()
    if [[ "${ATOM_GUI_CONTROL_MODE}" == control ]]; then
      python3 tools/operator_gui/sim_supervisor.py > /workspace/tmp/operator_gui/supervisor.log 2>&1 &
      supervisor_pid=$!
      control_args=(--enable-commands)
    fi
    python3 tools/operator_gui/server.py "${control_args[@]}" --mode ros --port 8089 \
      --ros-config "tools/operator_gui/gazebo_${ATOM_GUI_CAMERA_MODE}.json"
  '
;;
trial)
: "${ATOM_BENCH_RUN_DIR:?}"
: "${ATOM_BENCH_MODE:?}"
: "${ATOM_BENCH_SEED:?}"

mkdir -p "${ATOM_BENCH_RUN_DIR}"
ros2 launch atom_xarm_sim uf850_arm_only.launch.py \
  camera_mode:="${ATOM_BENCH_MODE}" demo_gripper:=true gui:=false \
  rack_dx_m:=0.0 rack_dy_m:=0.0 rack_dyaw_rad:=0.0 \
  >"${ATOM_BENCH_RUN_DIR}/launch.log" 2>&1 &
launch_pid=$!

ros2 run atom_xarm_sim pre_observation_target_pose \
  --ros-args -p target_distance_m:=0.35 \
  >"${ATOM_BENCH_RUN_DIR}/target_pose.log" 2>&1 &
target_pid=$!

cleanup() {
  kill -TERM "${launch_pid}" "${target_pid}" 2>/dev/null || true
  sleep 2
  kill -KILL "${launch_pid}" "${target_pid}" 2>/dev/null || true
  wait "${launch_pid}" "${target_pid}" 2>/dev/null || true
}
trap cleanup EXIT

set +e
ros2 run atom_xarm_sim task_executive --ros-args \
  -p depth_registered:=true -p camera_mode:="${ATOM_BENCH_MODE}" \
  -p random_seed:="${ATOM_BENCH_SEED}" \
  -p output_dir:="${ATOM_BENCH_RUN_DIR}" \
  >"${ATOM_BENCH_RUN_DIR}/execution.log" 2>&1
result=$?
set -e

exit "${result}"
;;
*) echo "Unknown internal operation: ${operation}" >&2; exit 2 ;;
esac

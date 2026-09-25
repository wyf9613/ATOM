#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"
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

export ATOM_UID="$(id -u)"
export ATOM_GID="$(id -g)"
mkdir -p .docker-runtime/jazzy_ws/{build,install,log} tmp/camera_experiment/pre_observation_current
./scripts/docker/jazzy_build.sh

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

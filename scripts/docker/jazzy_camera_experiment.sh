#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

camera_mode="${1:-}"
if [[ "${camera_mode}" != "rgb" && "${camera_mode}" != "depth" ]]; then
  echo "Usage: $0 rgb|depth [rack_dx_m] [rack_dy_m] [rack_dyaw_rad]" >&2
  exit 2
fi
rack_dx="${2:-0.0}"
rack_dy="${3:-0.0}"
rack_dyaw="${4:-0.0}"

export ATOM_UID="$(id -u)"
export ATOM_GID="$(id -g)"
run_name="${camera_mode}_$(date +%Y%m%d_%H%M%S)"
output_dir="/workspace/tmp/camera_experiment/${run_name}"
mkdir -p "tmp/camera_experiment/${run_name}" .docker-runtime/jazzy_ws/{build,install,log}
printf 'camera_mode=%s\nrack_dx_m=%s\nrack_dy_m=%s\nrack_dyaw_rad=%s\n' \
  "${camera_mode}" "${rack_dx}" "${rack_dy}" "${rack_dyaw}" \
  >"tmp/camera_experiment/${run_name}/conditions.txt"

./scripts/docker/jazzy_build.sh

docker compose -f docker-compose.jazzy.yaml run --rm \
  -e ATOM_CAMERA_MODE="${camera_mode}" \
  -e ATOM_RACK_DX="${rack_dx}" \
  -e ATOM_RACK_DY="${rack_dy}" \
  -e ATOM_RACK_DYAW="${rack_dyaw}" \
  -e ATOM_EXPERIMENT_OUTPUT="${output_dir}" \
  -e LIBGL_ALWAYS_SOFTWARE=1 \
  atom-jazzy bash -lc '
    set -euo pipefail
    ros2 launch atom_xarm_sim uf850_arm_only.launch.py \
      camera_mode:="${ATOM_CAMERA_MODE}" \
      demo_gripper:=true \
      rack_dx_m:="${ATOM_RACK_DX}" \
      rack_dy_m:="${ATOM_RACK_DY}" \
      rack_dyaw_rad:="${ATOM_RACK_DYAW}" \
      >"${ATOM_EXPERIMENT_OUTPUT}/launch.log" 2>&1 &
    launch_pid=$!
    cleanup() {
      kill -INT "${launch_pid}" 2>/dev/null || true
      for _ in $(seq 1 20); do
        if ! kill -0 "${launch_pid}" 2>/dev/null; then
          wait "${launch_pid}" 2>/dev/null || true
          return
        fi
        sleep 0.25
      done
      kill -TERM "${launch_pid}" 2>/dev/null || true
      sleep 1
      kill -KILL "${launch_pid}" 2>/dev/null || true
      wait "${launch_pid}" 2>/dev/null || true
    }
    trap cleanup EXIT

    ros2 run atom_xarm_sim trajectory_demo \
      --ros-args -p hold_at_offset_sec:=25.0 -p allow_demo_gripper_joints:=true \
      -p "demo_offsets_rad:=[0.25,-0.16,-0.19,0.15,0.16,-0.18]" \
      >"${ATOM_EXPERIMENT_OUTPUT}/trajectory.log" 2>&1 &
    trajectory_pid=$!
    for _ in $(seq 1 120); do
      if grep -q "PASS: MoveIt planned and executed offset" \
          "${ATOM_EXPERIMENT_OUTPUT}/trajectory.log"; then
        break
      fi
      if ! kill -0 "${trajectory_pid}" 2>/dev/null; then
        wait "${trajectory_pid}"
        exit 1
      fi
      sleep 0.5
    done
    if ! grep -q "PASS: MoveIt planned and executed offset" \
        "${ATOM_EXPERIMENT_OUTPUT}/trajectory.log"; then
      echo "Timed out waiting for the fixed observation pose" >&2
      exit 1
    fi
    ros2 run atom_xarm_sim camera_probe \
      --mode "${ATOM_CAMERA_MODE}" \
      --output-dir "${ATOM_EXPERIMENT_OUTPUT}" \
      --min-tags 1 --timeout-sec 70 \
      >"${ATOM_EXPERIMENT_OUTPUT}/probe.log" 2>&1
    wait "${trajectory_pid}"
    cat "${ATOM_EXPERIMENT_OUTPUT}/report.json"
  '

echo "Experiment artifacts: tmp/camera_experiment/${run_name}"

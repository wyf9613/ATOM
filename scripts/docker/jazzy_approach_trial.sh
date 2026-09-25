#!/usr/bin/env bash
set -euo pipefail

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
ros2 run atom_xarm_sim pre_observation_demo --ros-args \
  -p camera_mode:="${ATOM_BENCH_MODE}" \
  -p random_seed:="${ATOM_BENCH_SEED}" \
  -p output_dir:="${ATOM_BENCH_RUN_DIR}" \
  >"${ATOM_BENCH_RUN_DIR}/execution.log" 2>&1
result=$?
set -e

exit "${result}"

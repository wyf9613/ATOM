#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

export ATOM_UID="$(id -u)"
export ATOM_GID="$(id -g)"
mkdir -p .docker-runtime/jazzy_ws/{build,install,log}

./scripts/docker/jazzy_build.sh

docker compose -f docker-compose.jazzy.yaml run --rm atom-jazzy bash -lc '
  set -euo pipefail
  log_file=/jazzy_ws/log/atom_uf850_nominal_dynamics.log
  ros2 launch atom_xarm_sim uf850_arm_only.launch.py actuator_model:=nominal >"${log_file}" 2>&1 &
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
  ros2 run atom_xarm_sim trajectory_demo --ros-args \
    -p model_scope:="Gazebo rigid-body dynamics with nominal torque-PD actuator assumptions; not identified from the physical UF850" \
    -p report_stem:=atom_uf850_nominal_dynamics \
    -p demo_offsets_rad:="[0.70, -0.45, -0.55, 0.50, 0.45, -0.10]" \
    -p goal_tolerance_rad:=0.03
  echo "Dynamics log: ${log_file}"
'

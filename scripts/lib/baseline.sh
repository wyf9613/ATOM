#!/usr/bin/env bash
# Internal implementation; use scripts/atom.sh demo.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
operation="${1:?Missing baseline name}"
case "${operation}" in arm|dynamics|transfer|smoke) ;; *) exit 2 ;; esac
"${repo_root}/scripts/atom.sh" build
docker compose -f docker-compose.jazzy.yaml run --rm -e ATOM_BASELINE="${operation}" atom-jazzy bash -lc '
  set -euo pipefail
  log_file="/jazzy_ws/log/atom_${ATOM_BASELINE}.log"
  launch_args=(uf850_arm_only.launch.py)
  case "${ATOM_BASELINE}" in
    transfer) launch_args=(uf850_transfer.launch.py) ;;
    dynamics) launch_args+=(actuator_model:=nominal) ;;
  esac
  ros2 launch atom_xarm_sim "${launch_args[@]}" >"${log_file}" 2>&1 &
  launch_pid=$!
  cleanup() {
    kill -INT "${launch_pid}" 2>/dev/null || true
    for _ in $(seq 1 20); do
      if ! kill -0 "${launch_pid}" 2>/dev/null; then
        wait "${launch_pid}" 2>/dev/null || true
        return
      fi
      sleep .25
    done
    kill -TERM "${launch_pid}" 2>/dev/null || true
    sleep 1
    kill -KILL "${launch_pid}" 2>/dev/null || true
    wait "${launch_pid}" 2>/dev/null || true
  }
  trap cleanup EXIT
  case "${ATOM_BASELINE}" in
    arm) ros2 run atom_xarm_sim trajectory_demo ;;
    smoke) ros2 run atom_xarm_sim smoke_test ;;
    transfer)
      config_file="$(ros2 pkg prefix atom_xarm_sim)/share/atom_xarm_sim/config/transfer_targets.yaml"
      ros2 run atom_xarm_sim transfer_demo --ros-args --params-file "${config_file}"
      ;;
    dynamics)
      ros2 run atom_xarm_sim trajectory_demo --ros-args \
        -p model_scope:="Gazebo rigid-body dynamics with nominal torque-PD actuator assumptions; not identified from the physical UF850" \
        -p report_stem:=atom_uf850_nominal_dynamics \
        -p demo_offsets_rad:="[0.70, -0.45, -0.55, 0.50, 0.45, -0.10]" \
        -p goal_tolerance_rad:=0.03
      ;;
  esac
  echo "Baseline log: ${log_file}"
'

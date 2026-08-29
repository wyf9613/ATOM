#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

repetitions="${1:-10}"
if ! [[ "${repetitions}" =~ ^[1-9][0-9]*$ ]]; then
  echo "Usage: $0 [positive repetition count]" >&2
  exit 2
fi

export ATOM_UID="$(id -u)"
export ATOM_GID="$(id -g)"
results_dir="${repo_root}/.docker-runtime/acceptance"
mkdir -p "${results_dir}" .docker-runtime/humble_ws/{build,install,log}
rm -f "${results_dir}"/logical_*.log "${results_dir}"/physical_*.log

for mode in logical physical; do
  if [[ "${mode}" == "logical" ]]; then
    domain_base=80
  else
    domain_base=120
  fi
  for run in $(seq 1 "${repetitions}"); do
    export ROS_DOMAIN_ID="$((domain_base + (run - 1) % 30))"
    log="${results_dir}/${mode}_$(printf '%02d' "${run}").log"
    echo "[${mode}] run ${run}/${repetitions} (ROS_DOMAIN_ID=${ROS_DOMAIN_ID})"
    docker compose -f docker-compose.humble.yaml run --rm atom-humble bash -lc "
      set -eo pipefail
      cd /humble_ws
      source install/setup.bash
      timeout --signal=INT 70s ros2 launch atom_ur3e_moveit_config demo.launch.py \
        grasp_mode:=${mode} headless:=true rviz:=false run_task:=true
    " 2>&1 | tee "${log}"
    grep -F "RESULT PASS | mode=${mode}" "${log}" >/dev/null
  done
done

echo "RESULT PASS | logical=${repetitions}/${repetitions} physical=${repetitions}/${repetitions}"

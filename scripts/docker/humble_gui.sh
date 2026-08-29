#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

export ATOM_UID="$(id -u)"
export ATOM_GID="$(id -g)"
mkdir -p .docker-runtime/humble_ws/{build,install,log}

mode="${1:-logical}"
if [[ "${mode}" != "logical" && "${mode}" != "physical" && "${mode}" != "native" ]]; then
  echo "Usage: $0 [logical|physical|native]" >&2
  exit 2
fi

if [[ -z "${DISPLAY:-}" || ! -d /tmp/.X11-unix ]]; then
  echo "No X11 display is available; use humble_test.sh for headless testing." >&2
  exit 2
fi

if [[ "${mode}" == "native" ]]; then
  launch_command=(
    ros2 launch atom_gripper_description grasp.launch.py
    headless:=false run_test:=false
  )
else
  launch_command=(
    ros2 launch atom_ur3e_moveit_config demo.launch.py
    "grasp_mode:=${mode}" headless:=false rviz:=true run_task:=true
  )
fi

docker compose \
  -f docker-compose.humble.yaml \
  -f docker-compose.humble.gui.yaml \
  run --rm atom-humble "${launch_command[@]}"

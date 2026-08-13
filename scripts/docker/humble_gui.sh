#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

export ATOM_UID="$(id -u)"
export ATOM_GID="$(id -g)"
mkdir -p .docker-runtime/humble_ws/{build,install,log}

if [[ -z "${DISPLAY:-}" || ! -d /tmp/.X11-unix ]]; then
  echo "No X11 display is available; use humble_test.sh for headless testing." >&2
  exit 2
fi

docker compose \
  -f docker-compose.humble.yaml \
  -f docker-compose.humble.gui.yaml \
  run --rm atom-humble \
  ros2 launch atom_gripper_description grasp.launch.py

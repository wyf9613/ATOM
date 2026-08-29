#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

export ATOM_UID="$(id -u)"
export ATOM_GID="$(id -g)"
mkdir -p .docker-runtime/jazzy_ws/{build,install,log}

docker compose -f docker-compose.jazzy.yaml build atom-jazzy
docker compose -f docker-compose.jazzy.yaml run --rm atom-jazzy bash -lc '
  set -eo pipefail
  cd /jazzy_ws
  rosdep check --from-paths src --ignore-src
  colcon build --symlink-install --packages-up-to xarm_moveit_config
'

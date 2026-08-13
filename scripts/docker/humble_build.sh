#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

export ATOM_UID="$(id -u)"
export ATOM_GID="$(id -g)"
mkdir -p .docker-runtime/humble_ws/{build,install,log}

docker compose -f docker-compose.humble.yaml build atom-humble
docker compose -f docker-compose.humble.yaml run --rm atom-humble bash -lc '
  set -eo pipefail
  cd /humble_ws
  rosdep check --from-paths src --ignore-src
  colcon build --symlink-install \
    --packages-select ur_description atom_gripper_description
'

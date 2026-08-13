#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

export ATOM_UID="$(id -u)"
export ATOM_GID="$(id -g)"
mkdir -p .docker-runtime/humble_ws/{build,install,log}

docker compose -f docker-compose.humble.yaml run --rm atom-humble bash -lc '
  set -eo pipefail
  cd /humble_ws
  colcon build --symlink-install \
    --packages-select ur_description atom_gripper_description
  source install/setup.bash
  xacro \
    src/atom_gripper_description/urdf/ur3e_atom_humble.urdf.xacro \
    > /tmp/ur3e_atom_humble.urdf
  check_urdf /tmp/ur3e_atom_humble.urdf
  colcon test --packages-select atom_gripper_description \
    --event-handlers console_direct+
  colcon test-result --test-result-base build/atom_gripper_description --verbose

  set +e
  timeout --signal=INT 50s ros2 launch atom_gripper_description \
    grasp.launch.py headless:=true run_test:=true \
    2>&1 | tee /tmp/atom_humble_grasp.log
  launch_status=${PIPESTATUS[0]}
  set -e

  grep -F "RESULT PASS" /tmp/atom_humble_grasp.log
  if [[ ${launch_status} -ne 0 && ${launch_status} -ne 124 ]]; then
    echo "Gazebo launch exited unexpectedly: ${launch_status}" >&2
    exit "${launch_status}"
  fi
'

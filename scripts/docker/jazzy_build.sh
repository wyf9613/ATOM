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
  core_paths=(
    src/xarm_ros2/uf_ros_lib
    src/xarm_ros2/xarm_msgs
    src/xarm_ros2/xarm_sdk
    src/xarm_ros2/xarm_description
    src/xarm_ros2/xarm_api
    src/xarm_ros2/xarm_controller
    src/xarm_ros2/xarm_gazebo
    src/xarm_ros2/xarm_moveit_config
    /workspace/ros2_ws/src/atom_gripper_description
    /workspace/ros2_ws/src/atom_xarm_description
    /workspace/ros2_ws/src/atom_xarm_sim
  )
  rosdep check --from-paths "${core_paths[@]}" --ignore-src --skip-keys ament_python
  colcon build --symlink-install --packages-select \
    uf_ros_lib \
    xarm_msgs \
    xarm_sdk \
    xarm_description \
    xarm_api \
    xarm_controller \
    xarm_gazebo \
    xarm_moveit_config \
    atom_gripper_description \
    atom_xarm_description \
    atom_xarm_sim \
    --base-paths /jazzy_ws/src/xarm_ros2 /workspace/ros2_ws/src
'

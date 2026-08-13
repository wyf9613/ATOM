#!/usr/bin/env bash
set -e

source /opt/ros/humble/setup.bash

mkdir -p /humble_ws/src
ln -sfn \
  /workspace/ros2_ws/src/atom_gripper_description \
  /humble_ws/src/atom_gripper_description
ln -sfn \
  /workspace/ros2_ws/src/atom_ur3e_moveit_config \
  /humble_ws/src/atom_ur3e_moveit_config
ln -sfn \
  /workspace/ros2_ws/src/atom_manipulation \
  /humble_ws/src/atom_manipulation

if [[ -f /humble_ws/install/setup.bash ]]; then
  source /humble_ws/install/setup.bash
fi

exec "$@"

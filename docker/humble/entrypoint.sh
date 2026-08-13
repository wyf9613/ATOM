#!/usr/bin/env bash
set -e

source /opt/ros/humble/setup.bash

mkdir -p /humble_ws/src
ln -sfn \
  /workspace/ros2_ws/src/atom_gripper_description \
  /humble_ws/src/atom_gripper_description

if [[ -f /humble_ws/install/setup.bash ]]; then
  source /humble_ws/install/setup.bash
fi

exec "$@"

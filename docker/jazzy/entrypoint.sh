#!/usr/bin/env bash
set -e

source /opt/ros/jazzy/setup.bash

if [[ -f /jazzy_ws/install/setup.bash ]]; then
  source /jazzy_ws/install/setup.bash
fi

exec "$@"

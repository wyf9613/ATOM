#!/usr/bin/env bash
# In a Jazzy environment/container with the existing vendor sources available.
# Does not open CAN, serial, lidar, cameras or the physical arm.
set -eo pipefail
source /opt/ros/jazzy/setup.bash
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
result_root="${ATOM_MOBILE_RESULTS:-${repo_root}/tmp/mobile_integration_20261022/ros}"
vendor_root="${ATOM_VENDOR_ROOT:-${repo_root}/tmp/xarm_ros2}"
driver_root="${ATOM_BASE_VENDOR_ROOT:-${repo_root}/tmp}"
mkdir -p "${result_root}"
cd "${result_root}"
if [[ "${ATOM_MOBILE_SKIP_BUILD:-0}" != 1 ]]; then
python3 "${repo_root}/tools/base/prepare_drivers.py" "${driver_root}"
CMAKE_BUILD_PARALLEL_LEVEL=2 colcon build --parallel-workers 2 --symlink-install --base-paths \
  "${vendor_root}/xarm_description" "${vendor_root}/xarm_moveit_config" \
  "${repo_root}/ros2_ws/src/atom_gripper_description" \
  "${repo_root}/ros2_ws/src/atom_xarm_description" \
  "${repo_root}/ros2_ws/src/atom_mobile_description" \
  "${repo_root}/ros2_ws/src/atom_operator_interfaces" \
  "${repo_root}/ros2_ws/src/atom_gripper_hardware" \
  "${repo_root}/ros2_ws/src/atom_base" \
  "${driver_root}/tracer_ros2" "${driver_root}/ugv_sdk" \
  --cmake-args -DBUILD_TESTING=OFF
fi
source install/setup.bash
for package in atom_mobile_description atom_base atom_gripper_hardware atom_gripper_description atom_xarm_description; do
  python3 -m pytest -q "${repo_root}/ros2_ws/src/${package}/test" \
    --junitxml="${result_root}/${package}_tests.xml"
done
xacro "$(ros2 pkg prefix atom_mobile_description)/share/atom_mobile_description/urdf/atom_mobile.urdf.xacro" > atom_mobile.urdf
check_urdf atom_mobile.urdf
python3 "${repo_root}/tools/base/smoke_jazzy.py" --output "${result_root}/runtime.json"
python3 "${repo_root}/tools/base/check_nav2_jazzy.py" --output "${result_root}/nav2.json"
python3 "${repo_root}/tools/base/check_fine_adjust.py" --output "${result_root}/fine_adjust.json"

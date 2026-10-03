#!/usr/bin/env bash
# ROS integration against a fake serial device; never opens a hardware port.
set -eo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
artifact_dir="$PWD/tmp/gripper_integration"
mkdir -p "$artifact_dir"
# Jazzy binary extensions require Ubuntu's Python, not an active Conda Python.
export PATH="/usr/bin:/bin:$PATH"
source /opt/ros/jazzy/setup.bash
/usr/bin/python3 -c 'import rclpy, serial'
/usr/bin/colcon --log-base "$artifact_dir/colcon_log" build \
  --base-paths ros2_ws/src/atom_operator_interfaces ros2_ws/src/atom_gripper_hardware \
  --build-base "$artifact_dir/build" --install-base "$artifact_dir/install" \
  --packages-select atom_operator_interfaces atom_gripper_hardware \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3 -DPYTHON_EXECUTABLE=/usr/bin/python3 \
  2>&1 | tee "$artifact_dir/build.log"
source "$artifact_dir/install/setup.bash"
export PYTHONPATH="$PWD/ros2_ws/src/atom_gripper_hardware:${PYTHONPATH:-}"
/usr/bin/python3 -m unittest discover -s ros2_ws/src/atom_gripper_hardware/test -v \
  2>&1 | tee "$artifact_dir/controller_tests.log"
/usr/bin/python3 -m unittest discover -s tests/operator_gui -p test_gateway.py -v \
  2>&1 | tee "$artifact_dir/gateway_tests.log"
/usr/bin/python3 -m unittest discover -s tools/gripper -p test_motor_sweep.py -v \
  2>&1 | tee "$artifact_dir/sweep_tests.log"
g++ -std=c++11 -Ifirmware/atom_gripper_esp32/tests/mocks \
  firmware/atom_gripper_esp32/tests/test_motor_control.cpp -o "$artifact_dir/test_motor_control"
"$artifact_dir/test_motor_control" 2>&1 | tee "$artifact_dir/motor_control.log"
g++ -std=c++11 -Ifirmware/atom_gripper_esp32/tests/mocks \
  firmware/atom_gripper_esp32/tests/test_continuous_position.cpp -o "$artifact_dir/test_continuous_position"
"$artifact_dir/test_continuous_position" 2>&1 | tee "$artifact_dir/continuous_position.log"
g++ -std=c++11 firmware/atom_gripper_esp32/tests/test_motor_policy.cpp \
  -o "$artifact_dir/test_motor_policy"
"$artifact_dir/test_motor_policy" 2>&1 | tee "$artifact_dir/motor_policy.log"
# Isolate the smoke-test graph from the project's normal domain 42.
export ROS_DOMAIN_ID=91
/usr/bin/python3 ros2_ws/src/atom_gripper_hardware/test/ros_action_smoke.py \
  2>&1 | tee "$artifact_dir/ros_action_smoke.log"
echo "PASS: gripper software integration; logs: $artifact_dir"

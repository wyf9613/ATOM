# ESP32 sensor capture

This tool reads serial telemetry only. It never sends motor commands. Close Arduino Serial Monitor first; only one process can own the serial device.

From the repository root in PowerShell:

```powershell
python -m pip install -r tools/gripper/requirements.txt
python tools/gripper/capture.py --port COM4 --seconds 30 --label stationary --output tmp/gripper_bringup/stationary_01
```

Keep the fixture and magnets stationary during this run. The output directory must be new: use `stationary_02` for another run. Output includes `raw.bin` (unaltered bytes), `samples.csv` (including invalid records), and `summary.json` (valid-only magnetic statistics, actual sample counts, invalid records, gaps and device-timing rate). Units are µT. No force is calculated; gain/filter settings in the summary are expected firmware settings, not hardware readback. USB opening may reset the ESP32. Boot messages are retained in the raw file and excluded from samples. A malformed or wrong-address record is counted separately.

If there is no output or the firmware latched a sensor fault, add `--reset` to pulse EN through CP2102 RTS with BOOT deasserted. This restarts the sensor-only firmware; it does not transmit servo commands. An uncontrolled reset must not be used as a recovery policy for future active motor control.

The opener explicitly disables hardware/software flow control, deasserts DTR/RTS and clears the previous input queue. With `--reset`, it also waits for reset settling and purges the transient queue. Capture waits up to 5s for the first matching V1 record, then starts the requested acquisition duration. Pre-synchronization received lines are preserved in `startup.bin` and the complete received byte stream in `raw.bin`; discarded driver queue data is not captured. Later malformed/oversized/wrong-address records remain counted and cause a nonzero exit status, even if valid records also exist. Use `--sync-timeout` to change the startup timeout. Invalid sensor samples can establish framing sync but remain excluded from field statistics.

For a separate manual compression trial, use a different label and directory. Record timing, contact location, fixture position and loading conditions separately; statistics across an entire changing-force run are not stationary noise estimates. Independent force reference is needed for force calibration.

Replay without a serial device:

```powershell
python tools/gripper/capture.py --replay tmp/gripper_bringup/stationary_01/raw.bin --output tmp/gripper_bringup/replay_01
```

`host_elapsed_s` during replay is replay processing time; device timestamps preserve original timing. A nonzero exit status means no valid data, interruption or a device error; review summary and retained raw evidence.

ROS in the existing Jazzy environment:

```bash
cd ros2_ws
rosdep install --from-paths src/atom_gripper_hardware --ignore-src -r -y
colcon build --packages-select atom_gripper_hardware
source install/setup.bash
ros2 launch atom_gripper_hardware sensor.launch.py port:=/dev/serial/by-id/ACTUAL_DEVICE
ros2 topic hz /atom/gripper/magnetic_field
ros2 topic echo /diagnostics
```

ROS field units are tesla, not µT. Frame mount TF and covariance are unmeasured. Host receive timestamps are not synchronized with ESP32 clock. The package is a hardware sensor boundary, not a simulation gripper controller or a completed GripperCommand implementation. Serial reconnect is supported on the host; sensor initialization/read failure requires checking hardware and resetting ESP32 with EN.

Tests without ROS:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'ros2_ws/src/atom_gripper_hardware'
python -m unittest discover -s ros2_ws/src/atom_gripper_hardware/test -v
```

Motor commissioning commands and gated STS position-mode logic are implemented. See [first-power commissioning](../../docs/GRIPPER_MOTOR_COMMISSIONING.md). Default motor support is disabled; the enabled build requires FTServo and confirmed hardware, electrical compatibility, feedback and measured limits before ARM. No physical motor tests have been performed. USB/VIN is not an accepted servo-power supply. This ROS bridge remains read-only.

2026-10-03：为首次反馈测试启用 UART/FTServo（ATOM_MOTOR_ENABLED=1）；HARDWARE_CONFIRMED=0 且行程/负载/电压限制仍未填写，ARM 与运动保持拒绝。官方 SDK 2.0.0 已安装到用户 Arduino libraries/FTServo。首次仅执行 STATUS 和 PING；未验证实际供电及电平前不连接测试，不自动发送任何电机命令。

2026-10-03：电机调试版本默认关闭 V1 连续打印，但保留传感器采样与故障检查。串口命令 STREAM ON / STREAM OFF 可切换输出，不发送舵机指令。采集或使用只读 ROS 桥前，先在串口监视器发送 STREAM ON，然后关闭监视器；复位后需重新启用。纯传感器编译（ATOM_MOTOR_ENABLED=0）仍默认输出。

多位置自动往返测试：见 [测试说明](../../docs/GRIPPER_SWEEP_TEST.md)。默认先预览，--execute 执行3轮2000–2600目标测试，每段最多100计数，首故障中止，结束尝试STOP与DISARM。

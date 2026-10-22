# Source attribution

Navigation mission manager, HTTP bridge/web assets, map utilities and
IMU reader derive from LabBot's `amr_nav_2026-10-22.zip`, supplied by the base
team (maintainer zheming). Its amr_task_bridge and amr_imu package manifests
declare Apache-2.0. Fine-adjust control, geometry, tag detection and action
client/server derive from `labbot_visual_servo_2026-10-22.zip`'s
base_fine_adjust package, whose manifest declares MIT. Those archives did not
include complete license texts for these packages; obtain their authors' license
notices before external redistribution. ATOM integration changes and the velocity
gate are BSD-3-Clause. Per-file import paths and source hashes are retained in
HANDOVER_SOURCES.json; the received ZIPs remain unchanged in basement/.

The direct xArm SDK motion bridge, arm search/home/approach launchers and Gazebo
Classic plugins are intentionally retained only in the original archives. ATOM's
existing arm motion stack remains the arm owner. Existing ESP32 gripper hardware
and firmware remain their own modules; no second serial owner is introduced.

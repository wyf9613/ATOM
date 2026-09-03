# Simulation-to-Real Log

Record every material mismatch between the robot model/simulation and measured hardware.

| Date | Subsystem | Simulated assumption | Real measurement | Correction | Validation |
|---|---|---|---|---|---|
| 2026-08-29 | Gripper | Migrated limits of -15 to +5 mm per finger, 0.03 m/s maximum and simplified terminal-pad collisions | Pending physical measurement | Retain as explicitly provisional inputs in robot-independent Xacro | Standalone description tests pass; no physical validation |
| 2026-08-29 | Gripper | Total 0.58 kg distributed as 0.48/0.05/0.05 kg with box inertias | Previous report states 580 g; scale measurement and component mass properties pending | Retain traceable approximation | Xacro mass test passes; no physical validation |
| 2026-08-29 | Mount | Gripper mount coincident and axis-aligned with xArm `link_eef` | Pending adapter/quick-disconnect measurement | Neutral placeholder `xyz=0 0 0` m, `rpy=0 0 0` rad | Combined Xacro and override test pass; not validated on hardware |
| 2026-08-29 | TCP | `xyz=-0.0018 0 0.170536` m from `gripper_base` | Pending calibration | Retain inherited nominal value | Description test passes; no physical validation |
| TBD | Perception | Ideal camera extrinsics | Pending calibration | Pending | Pending |
| TBD | Collision | Simplified collision meshes | Pending clearance tests | Pending | Pending |
| 2026-08-29 | xArm 850 software baseline | Official generic six-axis `uf850` at pinned vendor commit | Arm delivered; controller/firmware, serial calibration, payload and TCP remain pending | Restrict the baseline to eight core vendor packages, add an ATOM-owned server-only wrapper and keep the custom gripper modular | Two consecutive runs after the controller-readiness fix: nine packages compiled; Xacro passed; six joint states and `world -> link_eef` TF present; both controllers active; MoveIt produced six points; 0.05 rad joint-1 offset and return over 2 s per leg completed with maximum reported simulated final-joint error 0.000050 rad across the two runs (test tolerance 0.02 rad) |
| 2026-09-03 | Bare-arm trajectory planning/control | Generic vendor `uf850`, exactly six arm joints, no gripper, 0.10 rad offsets on joints 1, 2, 3 and 5, MoveIt velocity/acceleration scaling 0.1 | Physical path accuracy, payload, TCP, collision clearance and controller behavior pending commissioning | Keep `uf850_arm_only.launch.py` and its MoveIt plan-and-execute acceptance test independent of custom-gripper integration | Two independent Docker/Gazebo Harmonic launches passed offset and return execution: 9/9 and 9/8 trajectory points per leg; maximum simulated final-joint error 0.009432 rad against a 0.02 rad tolerance |

For each entry, attach units, measurement method, configuration/revision and the test that closes the discrepancy.

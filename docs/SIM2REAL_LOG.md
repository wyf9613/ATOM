# Simulation-to-Real Log

Record every material mismatch between the robot model/simulation and measured hardware.

| Date | Subsystem | Simulated assumption | Real measurement | Correction | Validation |
|---|---|---|---|---|---|
| TBD | Gripper | Finger travel and joint limits from CAD | Pending | Pending | Pending |
| TBD | Gripper | Mass/inertia from CAD materials | Reported mass 580 g; measurement pending | Pending | Pending |
| TBD | Mount | CAD flange-to-gripper transform | Pending | Pending | Pending |
| TBD | TCP | TCP at nominal cuvette centreline | Pending calibration | Pending | Pending |
| TBD | Perception | Ideal camera extrinsics | Pending calibration | Pending | Pending |
| TBD | Collision | Simplified collision meshes | Pending clearance tests | Pending | Pending |
| 2026-08-29 | xArm 850 software baseline | Official generic six-axis `uf850` at pinned vendor commit | Arm delivered; controller/firmware, serial calibration, payload and TCP remain pending | Restrict the baseline to eight core vendor packages and keep the custom gripper modular | Image built once; eight packages compiled; Xacro passed; 35-second smoke reached MoveIt ready and activated both controllers; RViz offscreen exit remains open |

For each entry, attach units, measurement method, configuration/revision and the test that closes the discrepancy.

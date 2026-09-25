# Known Issues

## Project blockers

| ID | Issue | Impact | Next evidence/action |
|---|---|---|---|
| P-001 | The xArm 850 has arrived, but its controller variant, firmware, calibration files and supplied interfaces have not been inventoried. | Blocks hardware-safe configuration and physical commissioning. | Photograph labels, archive supplied files and record controller/firmware/network details. |
| P-002 | The ATOM headless xArm 850 smoke test passed twice consecutively after fixing a controller-readiness race; the camera experiment has since opened Gazebo GUI and RViz on the host. | A few simulation runs remain limited repeatability evidence. | Expand automated repetitions and record graphical startup/trajectory timing across runs. |
| P-003 | Firmware, ROS code, wiring and raw data are absent. | Cannot reproduce inherited control behaviour. | Request complete handover and archive it unchanged. |
| P-004 | Real workflow and instrument access are unconfirmed. | Test fixtures and precision requirements may be wrong. | Agree acceptance test with Chemical Engineering. |
| P-005 | Mobile-base interface is absent. | 2027 mechanical/electrical/software integration risk. | Freeze an interface-control document during 2026 S2. |
| P-006 | No 3D occupancy-map sensor plugin is configured in the arm-only MoveIt baseline. | The planner does not yet model sensed obstacles. | Add perception only after selecting a sensor model and defining its calibration and validation plan. |
| P-007 | The combined xArm 850 + ATOM gripper description uses a neutral placeholder mount and is not yet connected to gripper `ros2_control` or combined MoveIt collision semantics. | The model is suitable for description checks, not grasp simulation or hardware commands. | Measure the mounting transform, port the gripper controller independently, define SRDF collision rules and add integrated simulation acceptance tests. |
| P-008 | The temporary vendor G1 gripper and two-level four-slot rack scene can observe a front tag, but the requested tag-guided slot 1 to slot 2 transfer within that rack is not implemented. | A tag/trajectory video cannot be presented as a successful pick-and-place demonstration. | Measure or provisionally calibrate camera/tag/slot/TCP transforms for tag IDs 1 and 2, add the shelf and rack collision geometry to MoveIt, verify finger mimic/contact and grasp feedback, then execute and repeat a physical tube lift and in-rack placement in Gazebo. |
| P-009 | The new `pre_observation_target_pose` and `pre_observation_demo` implement the provisional `/atom/pre_observation_target` → `/atom/pre_observation_pose` pre-observation path and the two-segment obstacle-free approach. The base system does not yet publish the real bearing/height. The former default 0.2 m target at the current simulated height/orientation is not sampled by MoveIt; 0.35 m is now the default and completes. | The current demo cannot demonstrate real base-localisation input, grasp or placement; the requested 0.2 m pre-observation point needs a reachable UF850 pose or a clarified TCP/height definition. | Replace the provisional publisher with the base/rack localisation publisher, resolve the 0.2 m workspace issue with measured kinematics/target height, validate settling and Tag quality, then add environment collision geometry to the approach. |
| P-010 | The two-segment 0.40 m to 0.10 m approach is implemented and passed one RGB and one RGB-D nominal run, but a changed Tag center/plane can make the second-stage normal line miss the measured first-stage endpoint. Current checks stop if the mismatch exceeds 0.025 m; alternate rack perturbations remain unvalidated. | A new observation at the segment boundary may make the second segment's start violate its line constraint; simply issuing a new MoveIt goal cannot guarantee a perpendicular path. | Keep the boundary check; add an explicit realignment path when the updated normal line misses, and validate perturbed racks and degraded observations. |
| P-011 | The team reports 4 planning-failure terminations in 10 separate RGB runs (4/10, conditions and individual logs not yet archived here). In the retained automated batch, only four complete RGB trials are available and their failure categories differ. | The repeated-test result indicates a robustness problem, but the effect of viewing angle or RGB pose error cannot be isolated from planning and controller faults without run-level evidence. | Archive all ten runs with seeds, scene/camera settings, estimated-vs-true poses, planner result codes and controller readiness; classify each failure before changing the planner or camera choice. |
| P-012 | Single successful RGB and RGB-D runs have about 10–12 mm final horizontal error against independent simulated rack geometry; their selected-Tag observations show a positive `link_base` y bias. | The current standoff may be close to the visual estimate while missing the theoretical rack geometry. Single trajectories do not establish repeatability or depth benefit. | Check Tag plane geometry, camera extrinsics and AprilTag PnP calibration against independent truth, then repeat with matched seeds and measured calibration. |

## Gripper risks

| ID | Issue | Impact |
|---|---|---|
| G-001 | No timeout or maximum travel limit. | Empty grasp and unnecessary loading. |
| G-002 | No calibrated force measurement. | FR2 (< 5 N per the previous requirement) remains unverified. |
| G-003 | Silicone adhesion on release. | Placement failures; tape workaround is not production-ready. |
| G-004 | Quick-disconnect wear. | TCP and mounting repeatability can degrade. |
| G-005 | Low-mounted STM32 holder. | Collision/clearance risk. |
| G-006 | Bonded pads and magnets. | Durability and sensor alignment risk. |
| G-007 | Software-only reported emergency behaviour. | Does not satisfy a system-level hardware emergency stop. |
| G-008 | Conflicting final speed (180 in text, 200 in table). | Configuration cannot be trusted without firmware. |

## Evidence limitations

- The 49/50 result used fixed manually tuned waypoints and simulated holders.
- Placement accuracy on the real DynaPro and workspace integration with real instruments were only partially verified.
- The one failure was attributed to manual setup, but the system also lacked autonomous detection/recovery for that misplacement.
- Long-term pad wear, quick-release repeatability and varying object geometries were not evaluated.

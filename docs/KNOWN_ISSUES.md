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

## Operator GUI integration (2026-09-30)

- Browser UI is implemented but browser visual verification was blocked by the browser permission policy in this session. API and fake-source ROS checks passed; real hardware execution/stop remains unverified.
- Real pick/place/navigation buttons are unavailable until the proposed ExecuteTask ActionClient/server is connected. Stop/observe services require robot-local supervisor/task servers.
- Static map is shown; live OccupancyGrid, map/odom TF overlays, hardware stop feedback, authentication/control lease and persistent stop supervision are deployment work. See `OPERATOR_GUI_INTERFACES.md`.

Gazebo control follow-up supersedes the earlier missing-server note for observation/stop only. The new simulation supervisor supports fixed observation, arm-controller stop/reset and Action cancellation. It does not support hardware, environment avoidance, physical grasp, base navigation or system-wide stop of independent command publishers; authentication/control lease and real operator visual verification remain pending.

RGB-D workflow monitor verification: first monitored run completed alignment/perpendicular; a second run terminated after alignment because the refreshed Tag normal ray missed the alignment point by approximately 0.0920 m (configured limit 0.0250 m). GUI correctly reports FAILED with the reason and keeps live depth/Tag feedback; the algorithm needs a separately validated realignment step. Two runs are not a success-rate estimate. Monitoring acceptance and approach-task acceptance are separate; `tube_workflow_check.py --require-success` additionally requires the physical simulation approach to complete.

### Transfer GUI integration scope (2026-09-30)

The branch already has complete arm motion transfer phases, previously omitted from the GUI launch. These are now monitored through the same task schema. Original transfer still accepts `simulate_grasp_success=true`; its fixed pick/place poses are not calibrated to the current tube racks, no gripper closure/contact/attachment/release is performed, and visual approach has not been chained to transfer. A motion PASS is not physical pick/place PASS. GUI command buttons remain disabled for this external experiment runner. Browser visual/frame rendering validation remains pending.

### Correction: legacy transfer targets do not match the tube scene (2026-09-30)

The previous default-to-transfer GUI launcher decision was incorrect for the tube experiment and is superseded. Default is restored to `approach`; `transfer` must be explicitly selected and labelled as a legacy fixed-target motion test. Nominal scene coordinates from source: robot spawn [-0.2, -0.54, 1.021] m with yaw -1.571 rad; tube centre [0.530, -1.035, 1.2155] m in Gazebo. Converting into the nominal robot base frame gives approximately [0.495, 0.730, 0.195] m. Legacy pick uses [0.32085, 0.24571, 0.22907] m for link_eef, with no calibrated finger/TCP conversion. These poses are not the same target; the Gazebo spawn transform differs from the temporary identity ROS world-to-base TF. This is a source-based nominal calculation, not measured pose accuracy. Do not relabel the fixed-target motion PASS as a tube transfer or simply substitute the tube centre for the flange target. Full integration still requires Tag-to-slot/TCP conversion, collision-aware reachability, gripper/contact verification and physical transfer/release.

### Same-frame rack estimate and bounded realignment (2026-09-30)

A GUI-observed approach failure was reproduced: initial alignment passed against its frozen pose, then independent latest single-tag PnP positions changed the inferred normal and gave 0.0696 m lateral error against the unchanged 0.025 m bound. Rack estimation now deduplicates marker contours, fits tags 1/2 jointly in one image using provisional 0.040 m size / 0.070 m spacing, rejects reprojection RMS >2 px, and requires a fresh coherent pair for normal/selected pose. It uses observed image data and TF, not simulator truth. Motion still freezes observations per trajectory. After settling, the updated ray and distance are checked; up to three corrective alignment motions are allowed, otherwise the task fails. Limits on height, tilt, visibility and ray width are unchanged. GUI exposes a realignment phase and the updated geometric error rather than the prior frozen error.

First depth-mode run after the change passed alignment and perpendicular approach: updated-ray lateral 0.0151 m; final estimated plane distance 0.1016 m, frozen-ray lateral approximately 0.0002 m. Conditions: nominal static rack, software rendering, N=1, uncalibrated simulator geometry; no uncertainty/reliability or physical grasp claim. Report `tmp/operator_gui/workflow/run_20260930_045125/approach_report.json`. This run needed zero corrective motions; retry exhaustion and correction execution still require separate validation. Three synthetic-image regression tests verify known board pose, subpixel noise/rigid spacing and inconsistent-corner rejection; 16 gateway/sensor/geometry tests passed in the Jazzy container.

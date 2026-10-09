# Known Issues

## 2026-10-07 — v2 tool description is exported, deployment still pending

P-007 now has a CAD-based v2 flange/bracket composition and explicit tool SRDF,
with full inherited body/finger collision envelopes. The existing arm-only/G1
launcher does not consume it. No runtime or physical self-collision result has
been established; camera/PCB/cables/carried-object envelopes and measured flange
clocking/TCP/inertials/finger-state mapping remain missing. The print manifest's
source_cad/backplate/v2 and bracket STEP paths are absent locally, so original
source verification of those revisions remains open. Details:
[integration](GRIPPER_MOUNT_V2_INTEGRATION.md).

G-002 remains open: force estimate is uncalibrated and force requests remain
rejected. The fixed object's identity/mass/material, standard-force instrument,
actual serial connection and installed flange status have not been supplied.
No physical calibration data collected on 2026-10-07. Prepared procedure:
[force calibration](GRIPPER_FORCE_CALIBRATION.md).

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

Modular refactor boundary (2026-09-30): visual task composition is implemented within one ROS node using same-process capability modules/shared runtime state. Dedicated cross-node perception/motion APIs and the visual ExecuteTask/stop ownership integration are not implemented. Legacy demos remain isolated regression clients; their motion success does not establish physical tube transfer.

### RGB visual approach intermittently fails endpoint IK (2026-10-01)

On `refactor/modular-task-composition` at `7bbd038`, nominal static-rack RGB `visual_approach` completed joint Tag observation and 0.40 m alignment but failed the 0.10 m perpendicular endpoint IK gate: all seven yaw candidates returned MoveIt -31 / NO_IK_SOLUTION. A second run with the same seed (20260925) and scene parameters passed; Depth passed once. These three runs do not establish reliability or isolate the cause. The error alone does not distinguish collision, reachability, IK seed or observation variation. Limits were unchanged, the task stopped at the failed stage, and the GUI correctly exposed FAILED. Details and per-run evidence: [2026-10-01 Tag/rack test](TAG_RACK_TEST_20261001.md). Investigate sampled target/normal and IK seed/collision diagnostics before changing constraints.

## 2026-10-03 — First user-operated jog and unresolved feedback fault

User console reports ARM_OK; first JOG -5 returned MOVE_DONE; second JOG -5 caused servo_feedback_or_limit, followed by best-effort hold request and a latched fault. Physical displacement/direction was not reported; no force or motion accuracy result claimed. Existing message combined transport and limit failures, and stop handling could overwrite trigger values with newer feedback.

Added FEEDBACK_ERROR with SDK result/error/servo status; LIMIT_ERROR with values, configured bounds and per-limit flags; FAULT_TRIGGER and state snapshot before hold reads feedback again. MOVE_DONE now includes actual/target encoder values and telemetry. Existing raw load limit20 and all other motion gates remain unchanged. Cause (communication, load, voltage, temperature or position) remains unresolved; do not increase thresholds to bypass it. Native regressions cover feedback failure and injected load-only limit classification. Await physical diagnostic data after explicit DISARM, new firmware and guarded retry.

## 2026-10-03 — Directional jog debug instrumentation

User transcript: -50 from2310 reached2260; -100 from2260 reached2161(target2160); +100 from2161(target2261) faulted at2161 with raw load-52>absolute50, voltage76/temp21 within bounds. User quit. Root cause of this stop is confirmed absolute-load threshold; physical reason for directional asymmetry remains unknown. Completion load0 for negative moves is not their peak. Official pinned SDK SMS_STS::ReadLoad uses bit10 for direction, consistent with signed readings; no signed-load conversion bug found.

Added MOVE_START, approximately100ms MOTION samples, and MOTION_SUMMARY sampled absolute/signed peak, sample count, timing and encoder start/target/last position. Fault sample is included before stop feedback can overwrite it. Peaks are sampled, not guaranteed instantaneous maxima. Console saves commands and received lines to timestamped JSONL under tmp/gripper_bringup, with UTC arrival timestamps; no automatic movement. Threshold50, speed20, range1937–2668, +/-100 and heartbeat/fault gates unchanged. Native regression injects negative-load overlimit and verifies captured signed peak/fault summary; Python compilation passes. No real port opened or motion performed in this debug turn. QUIT sends best-effort STOP; it does not guarantee torque release—explicit DISARM or external power-off before uploading.

## 2026-10-03 — User transcript confirms four bounded jog completions

Source: user pasted attachment 4c83e827-d91a-4be2-a0b9-44c6978ce712/已粘贴的文本.txt; newest session references tmp/gripper_bringup/motor_20261003_143750_128786.jsonl. Older fault at-52 precedes new session, not a failure of these four motions. New session:

| Encoder start→target | Last position | Duration ms | Samples | Sampled absolute load peak | Signed peak |
|---|---:|---:|---:|---:|---:|
|2161→2111|2112|1020|12|28|28|
|2110→2010|2010|2111|22|48|48|
|2010→2110|2109|2105|22|44|-44|
|2109→2209|2208|2030|22|36|-36|

All four report done, endpoint error0–1 encoder counts; no new-session fault appears in provided excerpt. N=1 per command, not repeatability/reliability verification. Close/open over approximately2010–2110 have sampled peaks48 and44 respectively, so this trace does not support generally higher opening load. Previous opening-start52 remains evidence of variability; software threshold50 has only2 raw units margin over observed closure48. Approx100ms sampling can miss instantaneous peaks; physical displacement/force/current not independently measured. Raw voltage76–77, temperature19–21 during these records. No torque release appears at excerpt end: user should DISARM explicitly.

Important configuration discrepancy: speed register is set20, but measured100count movements take approximately2.0–2.1s, around47–49 encoder counts/s. Earlier comments interpreted speed20 as20counts/s; that interpretation is not established by this physical trace. SDK/model speed register units must be checked before claiming commanded physical velocity. Existing7s timeout remains conservative provisional bound, not measured stop latency.

### 2026-10-03 — Sweep residual-chasing fix

Physical run sweep_20261003_144358_789365 completed3segments then motion_timeout: after a100count move start2299/target2399, post-dwell encoder settled2398; host requested another2counts to waypoint2400. Feedback remained2398 for70samples over7096ms with sampled load peak24, raw voltage76–77/temp23, no load/electrical limit fault. End transcript confirms DISARM_OK; torque_release_confirmed=true. This is observed small-step non-response, consistent with servo deadband/friction; precise cause unmeasured.

Host waypoint tolerance changed1→3counts to avoid chasing residual2counts, matching existing post-dwell drift gate. Firmware commanded-target tolerance and all fault limits unchanged. Physical run remains FAIL; no completed3cycle claim. Regression checks2398→2400 generates no new command, and error4 still requires movement. Five tests pass. New script requires no firmware upload; existing latched fault must be manually DISARM/RESET with healthy feedback before rerun.

### 2026-10-03 — Firmware/host arrival tolerance alignment

Second physical sweep_20261003_144533_722742 failed after3segments: full command start2300 target2400 stayed2398 through7014ms,70samples, peak36 (voltage76–77,temp23). Unlike previous run, no2count follow-up command caused this failure; firmware1count arrival gate itself timed out. Cleanup confirmed DISARM_OK. Host-only prior fix was incomplete.

Firmware POSITION_TOLERANCE now3 encoder counts, host segment acceptance and waypoint/dwell tolerance all3; actual error remains in CSV. Timeout/load/position/voltage/temperature/watchdog gates unchanged. Native regression verifies error4 does not complete and error2 completes;6 host tests include accepting error2/rejecting4. Firmware upload required before physical rerun. Both physical sweeps remain failures, not repeatability passes; stable residual is observed, precise friction/deadband cause unproven.

### 2026-10-03 — Sweep cached/live feedback race

Physical sweep_20261003_144913_282840 stopped after10 recorded completions due host summary mismatch, not firmware fault. Host cached start2301 and sentJOG100; firmware MOVE_START and summary start2302/target2402, done2400 within3counts, peak44,2092ms. Cleanup DISARM_OK confirmed. Relative JOG is based on fresh firmware feedback, which may change between STATUS and command; strict equality to cached position was an incorrect host assumption.

Use MOVE_START live start/target as transaction reference, still requiring cached-to-live start and expected target discrepancy<=3counts, requested-vs-live delta discrepancy<=3 and target within1937–2668. Summary and completion must match that live target exactly, final encoder error<=3. CSV start now reflects live firmware start. Seven regressions pass, including1count feedback change accepted and4count change rejected. Host-only correction, no upload required. Run remains incomplete, not3cyclePASS.


## 2026-10-03 — UI / ROS gripper integration acceptance outstanding

New shared serial controller, ROS ControlGripper interface, operator controls and task capability pass host protocol/HTTP checks; this machine currently lacks rclpy/Jazzy; Docker Desktop startup was attempted but daemon queries remained unresponsive, so generated Action/colcon/ROS process interoperability is unverified. No physical UI/arm joint run in this coding task. Combined recipe remains opt-in and additionally blocked until real-arm integration verification; existing executive retains simulation-specific inputs and task cancellation/supervision is incomplete. Fingertip force calibration/control, physical grasp verification, mount TF/covariance, endpoints/aperture, exact electrical/load limits and stopping/holding behavior remain //TODO G01–G09. See GRIPPER_SYSTEM_INTEGRATION.md.

### 2026-10-03 — Gripper ROS environment blocker resolved on Linux

Follow-up to UI / ROS gripper integration acceptance above: the existing native Jazzy environment now builds ControlGripper and atom_gripper_hardware with system Python 3.12. ROS UI/bridge Action communication, cancellation/fault recovery and caller-loss STOP passed against a fake serial device. Conda Python 3.13 caused import/rosidl failures; the dedicated gripper validation script selects system Python explicitly. The earlier Windows/Docker blockage is historical, not the current ROS software status. Physical UI/arm integration, G01–G09 measurement requirements and task-supervisor synchronized cancellation remain outstanding; combined hardware recipe stays disabled.


### 2026-10-03 — USB boot race in gripper telemetry handshake

Live local UI connection failed with Timeout waiting for # STREAM ON. The serial log contained ESP32 POWERON_RESET/boot/sensor-ready output after the first STREAM ON, followed by command_unknown_or_motor_disabled. Add at most three 2 s telemetry handshake attempts; retry only STREAM ON, without ARM, RESET or motion. A fake boot regression drops the first request and verifies recovery without actuation; all 22 protocol/serial tests pass. After restarting the local gateway, CP2102 /dev/ttyUSB0 returned fresh motor and valid magnetic telemetry with no fault, armed=false. Position1937 is outside the UI ARM range2000–2600; manual disarmed repositioning is required, not a relaxed software envelope.


### 2026-10-03 — Motor replies continued after magnetic stream stopped

Live UI at position2193 showed valid last sensor data but sensor_fresh=false; motor PING remained fresh. Log contained another ESP32 POWERON_RESET at host monotonic1472.13s, after which V1 output ceased. Root cause of the reboot is unconfirmed. Idle controller now retries only STREAM ON when telemetry is stale (2 s retry interval,0.5 s acknowledgment timeout), preserving all motion/fault gates. An armed/moving reboot latches a host fault and cancellation; telemetry recovery cannot re-arm or clear it. POSIX serial opens request exclusive ownership to reject another cooperating pyserial owner.24 protocol/serial tests and ROS Action smoke pass. Live gateway restarted disarmed; both streams fresh, position2193 and no fault; ARM gate cleared. No motor motion performed.


### 2026-10-03 — Continuous firmware deployment pending user Arduino upload

Host/firmware sources now implement a single MOVE target and same-session normal Stop/resume. Firmware advertises continuous_position=1; older firmware blocks motion with an update-required reason, not a silent segmented fallback. User elected to compile/upload in Arduino IDE; no agent upload, full Arduino cross-compile or continuous hardware run claimed. Current UI gateway is stopped and CP2102 serial is free. After upload, restart tools/operator_gui/server.py and verify firmware/feedback before a user-operated empty-gripper test. Protocol/ROS fake-device and native C++ tests do not establish physical stopping latency or load protection.


### 2026-10-03 — Startup boot-text overflow recovery

User-uploaded continuous firmware was confirmed by live continuous_position=1 and sensor_ready output. Failed gateway log contained repeated/concatenated ROM boot text and Oversized device record, not an oversized normal MOTOR line (diagnostic capture longest138bytes). During bounded initial STREAM ON synchronization only, discard oversized startup records and replace non-ASCII boot characters; retain strict framing/ASCII checks after handshake.28 protocol tests pass, including startup garbage recovery and rejection of oversized post-handshake records. Restarted local gateway reports connected,fresh motor/sensor,position2001,armed=false,fault=null. No ARM/motion by agent. Upload is now user-confirmed through device capability; physical continuous-motion acceptance remains pending.


### 2026-10-03 — User confirms local gripper frontend integration

After Arduino IDE firmware upload and gateway startup recovery, user explicitly reports no issue and successful frontend integration. This closes local UI connection/deployment acceptance on user confirmation; exact exercised command sequence, repetition count and quantitative stop/force measurements were not supplied. Force calibration, independent grasp verification and combined physical arm supervision remain open.


## 2026-10-07 — V2 observation capture fails full-rack gate

Run tmp/operator_gui/workflow/run_20261007_030817 (depth, visual_observe,
Tag1, nominal scene, single trial): pre-observation motion passed, but capture
timed out after the 90 s configured wall-time gate (220 processed frames, last
IDs [0,1,2]). No coherent full [0,1,2,3] rack fit completed. GUI/API checks for
fresh arm, RGB/depth previews, Tag detections, read-only ownership and terminal
result passed; --require-success correctly failed. New camera pose is only an
unmeasured simulation placement; investigate coverage/occlusion/coherent fit
before approach or hardware deployment. Keep the full-rack quality gate.


2026-10-07 D435i hardware readiness: model identity confirmed, but serial,
firmware, USB transport, actual mounting and hand-eye remain unverified. Camera
SDK installation and no-motion bringup do not commission the real arm. Existing
visual observer accepts only 32FC1; real aligned 16UC1 requires tested conversion
before any hardware visual recipe. Native Harmonic RGB-D is not D435i stereo/IMU
emulation. Optical-offset changes can affect full-rack visibility.

D435i nominal observation follow-up: run_20261007_034304 passed visual_observe
once with the official model and current clocking/initial posture. This supersedes
neither earlier failed trials nor missing hardware calibration; visibility
repeatability and visual_approach under the D435i model remain untested.

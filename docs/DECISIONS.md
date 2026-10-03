# Decision Log

## 2026-10-03 — Separate ESP32 mount and reinforce printed flange adapter

User superseded the v1 side-on-flange electronics placement: mount ESP32 independently using the lower shell-seam pair opposite the camera bracket, retaining provisional 46.5 × 23.5 mm / Ø4.0 PCB holes. User requested rigidity over material saving and tentatively selected PLA, estimating gripper plus camera at about 700 g by heft, not a scale. [Backplate v2](../source_cad/backplate/v2/README.md) replaces the narrow bridge rails with a continuous thick annular body, 12 mm broad front plate, 14 mm flange end, enlarged root and 52 mm rear extension. Nominal UF850 flange pattern is unchanged. M6 screws are installed before attaching the gripper through dedicated axial access bores. [Independent ESP32 bracket](../source_cad/esp32_bracket/v1/README.md) uses inherited lower hole centres x=-33.7/-18.7, z=-65.725. Accepted scope is CAD revision direction only: PLA grade/printing, entire tool mass/CoM, original tab strength, stiffness, creep and dynamic capacity remain unvalidated.

## 2026-10-03 — Open gripper backplate and separate ESP32 carrier review CAD

User requested reuse of the four rear gripper holes, a partial/open backplate extending to the delivered UF850 flange, practical screw access and an ESP32 mounting location. Implement the requested review geometry in [backplate CAD v1](../source_cad/backplate/v1/README.md), retaining inherited assets and the independent camera bracket. The original STEP rear-hole pattern is Ø3.2 mm, 18 × 97 mm; these are CAD values. The official UF850 V2.3.0 manual p26 specifies ISO 9409-1-50-4-M6, Ø50 mm four-hole PCD, Ø63 mm flange, Ø31.50 H6 centre and Ø6 H7 locating hole. Adopt this nominal flange interface for CAD only; actual revision, pilot fit and fasteners remain unverified. User provisionally supplied ESP32 46.5 × 23.5 mm hole pitch and confirmed Ø4.0 mm after correcting an initial “40 mm” entry, while explicitly noting uncertainty. Put these holes on a removable side carrier; PCB outline and connector positions are placeholders. This records requested geometry and source selection, not manufacturing/material approval, validated load capacity or hardware calibration.

## 2026-10-02 — Camera bracket CAD revision direction

User requested two external mounting plates around the inherited two shell tabs (four-layer bolt stack), a narrower forward extension and a single front camera screw mounting hole, removing the v1 locating lips and ribs. Implement this review geometry in [CAD v2](../source_cad/camera_bracket/v2/README.md), preserving inherited assets and v1. The two original STEP hole axes are 15 mm apart with 3.2 mm diameters; these are CAD values, not physical measurements. The camera interface uses a clearance hole for a screw into the camera's existing 1/4-20 thread. D435 remains a tentative user recollection, with camera-hole coordinates, insertion depth, fit tolerances, fastener stack, stiffness and hardware calibration unverified. This records the requested geometry direction, not manufacturing approval or validated camera mounting capability.

## D-017 - ESP32 sensor-only gripper bring-up over a ROS serial boundary

- Date: 2026-10-02
- Status: Accepted for initial sensor bring-up; hardware verification pending
- Decision: Replace the inherited STM32 controller with the user's classic ESP32 DEVKIT V1 for staged redevelopment. Begin with one magnetic sensor over GPIO21/GPIO22 I2C and USB serial telemetry; add a read-only `atom_gripper_hardware` ROS bridge under the existing D-007 baseline. Motor control remains deferred.
- Evidence: User requested the replacement and supplied photographs showing ESP32 DEVKIT V1 and CP2102; previous report printed p14 Figure 9 shows 3.3V sensor supply and I2C wiring. Melexis MLX90393 datasheet confirms 2.2-3.6V chip supply; complete sensor ordering code/address remains unconfirmed.
- Node rationale: Existing description and simulation nodes do not own the physical sensor serial device; a separate lifecycle/fault boundary is required for device reconnect, parsing and magnetic-field units.
- Boundary: No board flash, sensor measurement, ROS runtime, force calibration or motor actuation has been verified. See ESP32_GRIPPER_BRINGUP.md.

## D-012 - Use the vendor G1 gripper only as a temporary Gazebo test tool

- Date: 2026-09-24
- Status: Accepted for the camera/transfer experiment fixture only
- Decision: Enable UFactory's BSD-3-Clause xArm G1 gripper from the pinned `xarm_ros2` description with `demo_gripper:=true`. Keep the default bare-arm launch and the separate ATOM gripper description available. This does not select the physical end effector or replace the inherited ATOM gripper design.
- Evidence: The official UFactory `xarm_ros2` README explicitly lists `uf850` with `add_gripper:=true`; the pinned repository includes the G1 Xacro, `XArmGripperSystem` and `uf850_gripper_traj_controller` configuration. In Gazebo, the controller became active and accepted a `drive_joint` position action; one 0.5 rad command reported success. Source: https://github.com/xArm-Developer/xarm_ros2
- Boundary: The G1 gripper mount, mimic fingers, tube contact grasp and physical ATOM interface are not validated. The original arm-only trajectory offsets collide or otherwise violate trajectory tolerance in the expanded fixture; a reduced observation trajectory passed after moving the shelf clear. No successful tube transfer is claimed.

## D-001 - Preserve raw handover assets

- Date: 2026-08-09
- Status: Accepted
- Decision: Keep the received context file, PDF and F3Z at their current paths and unchanged during repository initialization.
- Reason: Maintain provenance and avoid breaking the existing Obsidian workspace before the team agrees on migration.

## D-002 - Use modular robot descriptions

- Date: 2026-08-09
- Status: Accepted
- Decision: Compose vendor arm, custom gripper and future mobile base through top-level Xacro mounting transforms.
- Reason: Allows hardware substitution and mobile-base integration without rebuilding a monolithic model.

## D-003 - Establish the deterministic baseline first

- Date: 2026-08-09
- Status: Accepted
- Decision: Prioritise URDF/Xacro, TF, MoveIt 2, perception-guided pose updates and explicit state machines before learned control.
- Reason: These address the measured integration gaps and provide a reproducible comparison baseline.

## D-004 - Defer platform-specific ROS scaffolding

- Date: 2026-08-09
- Status: Accepted
- Decision: Create the ROS 2 workspace but no vendor/distro-specific packages until the arm and ROS 2 distribution are confirmed.
- Reason: Avoid committing to incompatible drivers, package formats or dependencies.

## D-005 - Track binary engineering assets with Git LFS

- Date: 2026-08-09
- Status: Accepted
- Decision: Use Git LFS for Fusion archives/models, neutral CAD meshes and PDFs.
- Reason: These binary files do not benefit from normal Git deltas and are expected to grow.

## D-006 - Use the delivered UFactory xArm 850 as the Project ATOM arm

- Date: 2026-08-29
- Status: Accepted
- Decision: Use the UFactory xArm 850 that has arrived for the Project ATOM manipulation platform. Keep the inherited UR3e simulation baseline on the dedicated `ur3e` branch; do not carry its arm-specific description, controllers or MoveIt configuration into the xArm baseline.
- Evidence: The project team reported physical arrival of the xArm 850 on 2026-08-29.
- Boundary: Arrival confirms the arm family/model for project work, but does not yet confirm the controller variant, serial-number-specific calibration, firmware, supplied end-effector interface, payload configuration, network settings, ROS 2 compatibility or safety integration. Record those from labels, supplied documents and repeatable commissioning tests before selecting a driver or MoveIt configuration.
- Effect on D-004: The arm-selection portion is resolved. D-007 selects the development and simulation software baseline; serial-number-specific hardware parameters and real-arm compatibility remain deferred until commissioning evidence is recorded.

## D-007 - Use an Ubuntu 24.04 / ROS 2 Jazzy Docker baseline for xArm 850

- Date: 2026-08-29
- Status: Accepted for development and simulation baseline
- Decision: Use one Docker baseline based on Ubuntu 24.04 Noble, ROS 2 Jazzy, Gazebo Harmonic, `gz_ros2_control` and MoveIt 2. Use UFactory's official `xarm_ros2` `jazzy` branch for the six-axis `uf850` model and pin repository commit `3dc2b5e8294758d96b54b15fa5920d581b7cbb3d` plus its SDK submodule commit `d84a2b7d533ff988bf1c2197ed50dd0d6723cf30`.
- Evidence: UFactory lists Ubuntu 24.04 + ROS 2 Jazzy as a developed/tested environment and provides `uf850` description, Gazebo, `ros2_control`, MoveIt fake/simulation and real-arm launch files. ROS 2 Jazzy supports Ubuntu 24.04, and Gazebo documents Harmonic as the recommended Jazzy pairing.
- Verification: On 2026-08-29, the ROS base image was pinned at digest `sha256:2589a8fba5257307857890173c069852c2abf913a0be7970f172478baecb09e4`. All eight vendor baseline packages and `atom_xarm_sim` compiled; the six-axis `uf850` Xacro passed `check_urdf`; and two consecutive server-only runs after fixing a controller-readiness race each verified six joint states, TF `world -> link_eef`, both active controllers, a six-point MoveIt plan, and a commanded 0.05 rad joint-1 offset and return over 2 s per leg. Maximum reported simulated final-joint error across those two runs was 0.000050 rad against a 0.02 rad test tolerance. Resolved key packages were `gz_ros2_control` 1.2.19, MoveIt 2.12.4, `ros_gz` 1.0.22 and `ros2_controllers` 4.40.1.
- Boundary: These are two deterministic simulation runs, not physical accuracy measurements; broader repeatability testing and host graphical operation remain pending. MoveIt reports that no 3D occupancy-map sensor plugin is configured, as expected for the current arm-only baseline. This decision does not validate the delivered controller firmware, network configuration, serial-number calibration, payload/TCP, custom gripper mount or any hardware motion.
- Supersedes: D-004 for Ubuntu/ROS selection. The prior Ubuntu 22.04 / ROS 2 Humble compatibility route remains only in the UR3e branch and is not part of the xArm 850 baseline.

## D-008 - Migrate the robot-independent gripper model and compose it above the vendor arm

- Date: 2026-08-29
- Status: Accepted for description and simulation development
- Decision: Migrate only the generic `atom_gripper_description` Xacro, derived visual meshes, CAD extraction tooling and traceability checks from the UR3e branch. Keep UR3e wrappers, controllers, MoveIt configuration and Fortress worlds on that branch. Compose the gripper with the official `uf850` model in a separate `atom_xarm_description` package attached at `link_eef`.
- Evidence: The migrated model retains derived meshes tied to source STEP SHA-256 `8ee4fd1c064210eab24cb10ba67623e497cab0866adbca86d5be9a0c63aaf351`. On 2026-08-29, both new packages built in the Jazzy container; the standalone and combined descriptions passed five pytest checks with no errors or failures; the combined tree passed `check_urdf`; and the existing arm-only MoveIt/Gazebo smoke test still passed.
- Boundary: The default mount (`xyz=0 0 0` m, `rpy=0 0 0` rad), 0.58 kg mass distribution, finger limits, collision primitives and TCP are provisional simulation inputs, not measurements. The dynamic smoke test remains arm-only. Gripper `ros2_control`, combined SRDF/collision validation, Gazebo actuation and physical commissioning are not demonstrated.
- Reinforces: D-002 modular-description boundary.

## D-009 - Keep a separately testable bare-arm trajectory baseline

- Date: 2026-09-03
- Status: Accepted for simulation development
- Decision: Maintain a headless `uf850` simulation path that loads exactly the six vendor arm joints, with all gripper options disabled. Its acceptance test must ask MoveIt to plan and execute a conservative joint-space offset and return through the simulated `uf850_traj_controller`. Gripper dynamics, SRDF and control are a separate integration step.
- Reason: A small deterministic arm-only baseline isolates vendor-arm planning/control faults from custom end-effector integration and provides a clean regression point for the two work streams.
- Verification: On branch `feature/uf850-arm-only-trajectory-sim`, two independent Docker launches on 2026-09-03 each observed exactly `joint1` through `joint6`, active joint-state and trajectory controllers, and successful MoveIt plan-and-execute results for a 0.10 rad four-joint offset followed by return. The two runs produced 9/9 and 9/8 planned/executed points per leg, with maximum simulated final-joint error 0.009432 rad. A subsequent visible-motion case exercised all six joints with offsets `[+0.70, -0.45, -0.55, +0.50, +0.45, -0.50]` rad at 0.05 velocity/acceleration scaling; offset and return each contained 69 points and passed with maximum error 0.010035 rad. The acceptance tolerance was 0.02 rad throughout.
- Boundary: This verifies deterministic command flow in the generic vendor simulation only. It does not establish physical trajectory accuracy, collision clearance, calibrated inertial/TCP data, controller/firmware compatibility, fault handling or any safety property.
- Reinforces: D-002 and D-003.

## D-010 - Add monitored nominal actuator dynamics without replacing the deterministic baseline

- Date: 2026-09-03
- Status: Accepted for simulation development
- Decision: Keep the official position-controlled Gazebo path as the fast regression baseline, and add a separate ATOM-owned `gz_ros2_control` hardware plugin that applies per-joint saturated PD torque to the Gazebo rigid-body model. Run this nominal dynamics path with the DART physics backend. Capture the trajectory-controller reference, feedback, error and output at 100 Hz and write machine-readable CSV and JSON reports after every successful trajectory demo.
- Reason: The official Gazebo position interface is useful for integration checks but is too idealised for examining actuator lag. A separate, parameterised execution layer exposes joint response without modifying the pinned vendor description or claiming that unmeasured gains represent the delivered hardware.
- Verification: On 2026-09-03, all 12 selected packages built in the Ubuntu 24.04 / ROS 2 Jazzy container. The DART nominal-dynamics run planned and executed 69/68 points for the offset leg and 68/67 for the return leg. Maximum final joint error was 0.015873 rad and 0.016712 rad respectively against a 0.03 rad dynamics-test tolerance. The 100 Hz report contained 573 samples per joint for the offset and 560 per joint for return; its largest transient position error was 0.019042 rad at return/joint6.
- Boundary: The PD gains are tuning inputs, not identified actuator parameters. Vendor rigid-body inertias and URDF effort limits are present, but motor electrical dynamics, gearbox compliance/backlash, internal servo behavior, communication delay, current/temperature and payload uncertainty are not modelled or validated. These simulation values cannot predict physical vibration or establish safe controller gains.
- MPC position: MPC is feasible later as an experimental outer loop that commands position/velocity through the supported arm interface. Torque-level MPC requires a verified real effort interface and an identified actuator model. It is not selected as the baseline until physical system identification and comparison against the deterministic controller are complete.
- Reinforces: D-002 and D-003.

## D-011 - Keep transfer targets separate from constrained motion execution

- Date: 2026-09-10
- Status: Accepted for arm-only simulation development
- Decision: Publish configurable pick and place `PoseStamped` targets on separate ROS 2 topics, then execute the post-grasp transfer as three checked Cartesian stages: vertical lift, orientation-constrained transfer between independently configured clearances, and vertical descent. Keep target publication independent of motion triggering and expose the active task phase on a status topic.
- Reason: This preserves the task sequence when fixed YAML targets are later replaced by timestamped perception output, and independently represents the source and destination clearances.
- Verification: On 2026-09-10, one `scripts/docker/jazzy_transfer_sim.sh` run built all 12 selected packages and completed all three Cartesian segments at fraction 1.0 with velocity/acceleration scaling 0.05. Against the configured 0.003 m endpoint, 0.004 m vertical-alignment and 0.09 rad total path-orientation limits, the largest final-position error during the constrained stages was 0.000010 m, the largest vertical lateral component was 0.002713 m, and the largest measured orientation error was 0.057725 rad. The JSON report records 1,416, 3,512 and 3,333 TF samples for lift, transfer and descent respectively. This is a single ideal-simulation regression run, not repeatability or physical-system evidence.
- Boundary: The present obstacle-free baseline uses a direct Cartesian transfer; introduce a collision-aware constrained free-space planner when workstation geometry is added. The MoveIt model constrains `link_eef`, not the provisional `gripper_tcp`; grasp success is simulated and no tube is attached in the planning scene. The configured target poses, clearances and tolerances are regression inputs, not measured workstation or safety parameters. Replace them with measured values and repeat validation after combined gripper SRDF/control and TCP calibration are available.
- Reinforces: D-002 and D-003.


## D-012 - Split shared-workspace validation into stop and reactive avoidance phases

- Date: 2026-09-11
- Status: Accepted for roadmap scope and development order; not implemented capability
- Decision: Split project Stage/Phase 4 into 4a (entry-triggered stop) and 4b (constrained reactive avoidance), with 4a retained as a higher-priority fallback. Begin perception, static collision modelling and stop-interface work during fixed-base development. Keep work package P4 as the separate perception work package.
- Evidence: The team relayed the supervisor's previous-week request in this session. Research and source links are recorded in `technical_roadmap/shared_workspace_perception.tex` and `RELATED_WORK.md`.
- Boundary: No shared-space safety property, numerical separation limit, sensor model, hardware stop interface or new planner configuration is accepted by this decision. RGB-D with RGB fiducials and measured rack geometry is a proposed evaluation configuration. Hybrid Planning, Servo and MPC remain candidates subject to compatibility and benchmark evidence against D-007/D-011.

## D-013 - Use a tag-guided transfer between two slots in one rack for the current Gazebo stage

- Date: 2026-09-24
- Status: Accepted for the current camera/transfer experiment stage
- Decision: Replace the two-rack source-to-destination demo with a transfer inside the four-slot rack on the upper shelf. The fixed task is slot 1 (AprilTag ID 1) to slot 2 (AprilTag ID 2). Remove the former tabletop destination rack from the generated Gazebo scene. Generate the pick and place targets from the respective observed tag poses and calibrated tag-to-slot/TCP offsets.
- Reason: This narrows the current stage to tag-guided localisation, contact grasp and controlled placement using one verified fixture, while retaining distinct perception-derived source and destination targets.
- Boundary: The changed stage target is an implementation and validation baseline, not evidence that tag IDs 1 and 2 are currently detected, that the tube can be grasped or placed, or that the simulated geometry and transforms match hardware. The broader Project ATOM objective still includes transfer between real workstations and instrument interaction.
- Reinforces: D-003 and D-011.

## D-014 - Split visual manipulation into pre-observation and approach phases

- Date: 2026-09-25
- Status: Accepted; provisional pre-observation and two-segment approach simulation implemented; real base input pending
- Decision: Before each pick or place, run a pre-observation phase that subscribes to a coarse target-bearing topic. A separate target-pose node places the TCP at the current default 0.35 m from the `link_base` origin along that bearing, uses the known target height, and aligns the gripper extension direction with the same bearing. Only after a valid RGB/RGB-D Tag observation may the approach phase change `x/y` and enter the grasp or placement region.
- Interface: The provisional topic is `/atom/pre_observation_target` with type `geometry_msgs/msg/PoseStamped`, referenced to the current simulation frame `link_base`. Its `pose.position.z` carries the pre-observation TCP height and its yaw carries the coarse bearing, positive counter-clockwise about `link_base` +Z; x/y are ignored as input. The target-pose node publishes the computed `PoseStamped` on `/atom/pre_observation_pose`. Until the base-localisation interface exists, the simulation bearing is `theta_true + U(-5°, +5°)` and the height is computed from the theoretical Tag height plus the provisional camera offset. The pick/place Tag ID remains task context rather than a field in this temporary message.
- Reason: Separate coarse, low-lateral-motion sensor alignment from fine visual target correction and the later approach. This prevents the noisy prior bearing from being mistaken for a precise manipulation target; environmental collision planning is a later increment under D-015.
- Boundary: The fixed six-joint camera trajectory remains a legacy observation baseline. The new script validates provisional pre-observation and two-segment obstacle-free approach in simulation; no environmental obstacle avoidance, grasp success or placement success is implied.
- Reinforces: D-011 and D-013.

## D-015 - Use two constrained, observation-updated approach segments

- Date: 2026-09-25
- Status: Accepted; provisional obstacle-free implementation validated once each in RGB and RGB-D nominal simulation
- Decision: The first approach segment uses the selected Tag pose observed at the end of pre-observation to move the front reference point to 0.40 m from the Tag plane. The second segment uses the latest valid observation published during the first segment and moves that point along a line perpendicular to the updated Tag plane to 0.10 m. The front reference point is 0.20 m along the gripper extension direction from `link_eef`, not the unmeasured physical grasp TCP. The action-type field distinguishes future pick/place tasks but is ignored by the current approach motion.
- Constraints: Hold the `link_eef` origin's height, roll and pitch at their measured post-pre-observation values; allow x, y and yaw. Require the camera optical axis, computed through the fixed camera mount, to keep the selected Tag center within a configurable angular tolerance. Constrain the second segment's front reference point to the updated Tag normal line. Each MoveIt request freezes its target estimate for that segment. RGB/RGB-D observations continue at a provisional maximum processing rate of 5 Hz during both segments and are published and logged without changing the active trajectory.
- Boundary: The first implementation is obstacle-free with respect to the environment but retains joint-limit and self-collision checks. It ends at the 0.10 m standoff and reports both segments' results and measured errors; it does not grasp, place, update an executing trajectory or claim environmental obstacle avoidance. If the new Tag estimate makes the second segment's normal-line constraint incompatible with its measured start, do not execute a path that violates the constraint.
- Reason: This gives a repeatable MoveIt planning baseline with a clear handoff between fresh perception and the final approach. OMPL path constraints are attempted first; if its orientation parameterization fails strict FK validation, the first segment uses Cartesian waypoints with the same FK acceptance limits. The Tag1/Tag2 center line supplies a stable common rack-plane normal because single-Tag PnP normals varied by several degrees at close range.
- Reinforces: D-014.

## D-016 - Add a browser operator GUI behind a robot-local gateway

- Date: 2026-09-30
- Status: Accepted for development; hardware deployment pending
- Decision: Use a separate Python HTTP gateway and browser UI with demo and ROS 2 modes. Reuse the D-007 Jazzy baseline and standard ROS telemetry/Trigger services; provide an ExecuteTask action contract for future task integration. Default to loopback and ROS read-only operation.
- Evidence: User requested arm/base/environment monitoring, command interfaces, checks and stopping, with deployment adapters to follow. ROS fake-source integration validates JointState reception and Trigger stop acknowledgment; GUI browser visual verification remains pending.
- Wireless direction: Keep robot-local control/stop supervision and wired arm Ethernet. Reach the gateway from the operator over Wi-Fi, initially via SSH forwarding. Vendor topology evidence: https://docs.xarm.ufactory.cc/2.hardware_installation.html . Actual hardware interfaces and wireless performance are unverified.
- Boundary: GUI software stop is not hardware emergency stop. Parameter-bearing real tasks and navigation, hardware safety supervisor, authentication/control ownership, live map/TF overlays and hardware trials remain pending. See `OPERATOR_GUI_INTERFACES.md` and `tools/operator_gui/README.md`.

### D-016 follow-up — Gazebo first, shared GUI with source profiles

- Date: 2026-09-30
- Decision: Use English GUI text, shared browser/API contracts and explicit Gazebo/hardware configuration profiles. Verify the monitoring path in Gazebo before connecting physical devices. Do not infer real motion or hardware safety equivalence from simulation telemetry.
- Evidence: Actual Gazebo RGB session received six arm joints, drive_joint, link_base → link_eef, advancing /clock, active controllers, DiagnosticArray and JPEG converted from raw Image. A two-sample check separated by 1 s passed; snapshots saved under tmp/operator_gui. Vendor source revision: 3dc2b5e8294758d96b54b15fa5920d581b7cbb3d.
- Boundary: Read-only simulation; the task/safety service servers and real ActionClient integration remain pending. The static lab map is a separate reference environment. Browser visual inspection remains pending.

### D-016 follow-up — Simulation observation action and software-stop adapter

- Date: 2026-09-30
- Decision: Add a standard ExecuteTask ActionClient and an explicitly Gazebo-only observation/safety supervisor. Reuse the validated reduced observation trajectory rather than claim unimplemented pick/place capability. Supervisor startup is locked and requires explicit reset after confirming standstill.
- Stop mechanism: Terminate the owned observation process, cancel MoveIt/trajectory goals, deactivate the arm trajectory controller and require fresh simulated joint-velocity observations below 0.01 rad/s for three consecutive samples. Reset activates the controller but never resumes a task. This is a provisional simulation test mechanism, not a physical stopping strategy.
- Evidence: End-to-end HTTP/action/MoveIt observation, software stop during movement, rejected repeat while latched, 1 s standstill sample, manual reset and standard action cancellation pass. Source snapshots and condition details are recorded in tmp/operator_gui/gazebo_control_check.json.
- Boundary: Only OBSERVE is implemented in the simulation task server; simulated hardware_estop is not_applicable. Physical stop, contact grasp, environment avoidance, mobile navigation and validated command ownership remain separate work.

### D-016 follow-up — Attach GUI to the real tube workflow

- Decision: Monitor the existing visual pre-observation/two-segment experiment directly through ROS status, image/depth and Tag messages. Keep this read-only workflow separate from the fixed Observe action supervisor; provide an independent attach launcher that starts no scene or motion.
- Evidence: A real RGB-D run reports observed Tags 1/2 and completed alignment/perpendicular segments, while GUI receives live joints, annotated RGB, depth and terminal status. Gateway/sensor checks include byte order, invalid depth masking, known Tag recognition and PnP; 13 checks pass.
- Boundary: Display detection is independent of the controller's detector and commands no motion. Visual approach success does not set grasp/place completion. Static lab map remains a reference map, not a Gazebo workstation localization result.

### D-016 follow-up: original transfer runner and image cadence (2026-09-30)

Connect the existing `transfer_demo` rather than treating visual approach as the whole branch workflow. The unified launcher defaults to transfer; `approach` explicitly selects the existing visual runner. Only one motion runner publishes task status per scene. Transfer uses existing fixed targets and simulated grasp confirmation; it does not validate physical tube transport or feed Tag poses into transfer. RGB/depth browser refresh is independent of telemetry; backend preview cap defaults to 15 Hz for the existing 10 Hz sensor, Tag monitor remains 2 Hz. Rates report wall-clock samples and window duration. No ROS/Ubuntu/vendor selection changed.

### Correction: legacy transfer targets do not match the tube scene (2026-09-30)

The previous default-to-transfer GUI launcher decision was incorrect for the tube experiment and is superseded. Default is restored to `approach`; `transfer` must be explicitly selected and labelled as a legacy fixed-target motion test. Nominal scene coordinates from source: robot spawn [-0.2, -0.54, 1.021] m with yaw -1.571 rad; tube centre [0.530, -1.035, 1.2155] m in Gazebo. Converting into the nominal robot base frame gives approximately [0.495, 0.730, 0.195] m. Legacy pick uses [0.32085, 0.24571, 0.22907] m for link_eef, with no calibrated finger/TCP conversion. These poses are not the same target; the Gazebo spawn transform differs from the temporary identity ROS world-to-base TF. This is a source-based nominal calculation, not measured pose accuracy. Do not relabel the fixed-target motion PASS as a tube transfer or simply substitute the tube centre for the flange target. Full integration still requires Tag-to-slot/TCP conversion, collision-aware reachability, gripper/contact verification and physical transfer/release.

### Same-frame rack estimate and bounded realignment (2026-09-30)

A GUI-observed approach failure was reproduced: initial alignment passed against its frozen pose, then independent latest single-tag PnP positions changed the inferred normal and gave 0.0696 m lateral error against the unchanged 0.025 m bound. Rack estimation now deduplicates marker contours, fits tags 1/2 jointly in one image using provisional 0.040 m size / 0.070 m spacing, rejects reprojection RMS >2 px, and requires a fresh coherent pair for normal/selected pose. It uses observed image data and TF, not simulator truth. Motion still freezes observations per trajectory. After settling, the updated ray and distance are checked; up to three corrective alignment motions are allowed, otherwise the task fails. Limits on height, tilt, visibility and ray width are unchanged. GUI exposes a realignment phase and the updated geometric error rather than the prior frozen error.

First depth-mode run after the change passed alignment and perpendicular approach: updated-ray lateral 0.0151 m; final estimated plane distance 0.1016 m, frozen-ray lateral approximately 0.0002 m. Conditions: nominal static rack, software rendering, N=1, uncalibrated simulator geometry; no uncertainty/reliability or physical grasp claim. Report `tmp/operator_gui/workflow/run_20260930_045125/approach_report.json`. This run needed zero corrective motions; retry exhaustion and correction execution still require separate validation. Three synthetic-image regression tests verify known board pose, subpixel noise/rigid spacing and inconsistent-corner rejection; 16 gateway/sensor/geometry tests passed in the Jazzy container.

### Script entry consolidation (2026-09-30)

Replace fourteen public Docker shell launchers with one `scripts/atom.sh` command interface and six internal library scripts. Merge the four headless baseline runners into a shared launch/cleanup implementation; group desktop and operator modes behind named subcommands. Existing simulation/controller/task behavior is preserved. Update active documentation and benchmark references; old file paths in historical decision evidence describe past runs only. No ROS distribution, image/version or vendor selection changes. Container stop is explicitly session lifecycle management, not an emergency stop.

### Module-based task composition (2026-09-30)

User-confirmed rule: organize nodes by module responsibilities; reuse existing nodes/capabilities to compose new tasks before adding a node. Record a necessity/independent-boundary justification for additions. Implemented first refactor on `refactor/modular-task-composition`: extract perception, planning/motion, gripper verification, simulation inputs, task telemetry and recipe execution modules within existing packages; replace the visual demo implementation with one task executive hosting both visual_observe and visual_approach. Existing command/status contracts, motion limits and hardware capability boundaries remain. No new ROS distribution, driver or planning configuration selected. See MODULES_AND_TASKS and regression report.

## 2026-10-01 — Coarse rack XY and target identity before observation

User-requested interface change on `refactor/modular-task-composition`: `/atom/pre_observation_target` now carries noisy rack-centre XY in metres and unchanged exact simulation TCP z, with identity orientation. `atom_pre_observation_target_pose` derives bearing from XY; its observation radius remains 0.35 m. Existing `/atom/approach_task` publishes selected tag/action before observation, with transient-local delivery. Both RGB and RGB-D use the same multi-tag rack observer, requiring all configured rack IDs including the target in one coherent pre-observation fit. No new ROS node/package, distribution, driver or hardware choice. This supersedes yaw-only coarse input and the hard-coded tag1/tag2 selection. Default XY noise ±0.025 m per axis is a provisional simulation setting, not measured localization uncertainty. See [interface and sequence](CAMERA_EXPERIMENT.md).

## 2026-10-01 — Registered depth assists the existing RGB rack estimator

Implement model-based point-to-plane plus RGB reprojection pose refinement inside the existing perception capability. Depth mode enables fusion, RGB retains its original estimate. Existing Gazebo scripts explicitly acknowledge registered optical-Z depth; direct node calls default that acknowledgment to false. Poor plane support falls back with a reported reason; depth/RGB inconsistency rejects the frame. Motion geometry limits are unchanged. Numeric fusion gates/weights are provisional simulation settings, not hardware accuracy or newly selected sensor/driver. [Method and validation](DEPTH_FUSION.md).

## 2026-10-02 — Gated ESP32 motor commissioning

Implement optional STS position-mode commissioning using the official FTServo Arduino SDK 2.0.0, pinned commit 64922cda46e56b21b8c1d9e830d936a1941645ae. Default motor support remains off until actual hardware and electrical compatibility are confirmed. No broadcast, EEPROM or wheel-mode writes; require configured limits/feedback/sensor before explicit ARM, bound JOG, latch faults, use best-effort position hold on watchdog events. No automatic torque release or boot motion commands. Magnetic delta is a provisional threshold, not calibrated force. Manual USB console precedes ROS actuator integration; ROS sensor bridge does not assert motor state. See GRIPPER_MOTOR_COMMISSIONING.md. Physical motor validation and stopping latency remain unresolved.

## 2026-10-03 — URT-1 logic supply evidence

Manufacturer URT-1 manual dated 2017-10-08, page 1, specifies logic 5V from USB or an external 5V supply; it does not establish a servo-power-to-5V output. Standalone supply design therefore uses a separate regulated 5V branch for ESP32 VIN and URT-1 logic, with servo-rated supply at the servo terminals and common ground. UART 3.3V selection is distinct from 5V supply. See source and revision limitations in GRIPPER_MOTOR_COMMISSIONING.md; actual board version remains unconfirmed.

## 2026-10-03 — First bounded motor motion preparation

User provided successful STS3215 PING: ID1, 1 Mbps, mode0, feedback valid; tight endpoint1917 and open endpoint2688 encoder counts, one observation each; earlier closed1944/1917 variation means endpoint repeatability remains unmeasured. User-reported adapter approximately7.5V; feedback raw voltage76–77, temperature19–21, load0. Actual rated voltage not independently confirmed. Positive encoder change opens.

Provisional inward bounds1937–2668 (20counts margin) selected for first manual test. At open2688 ARM rejects; manually reposition torque-off into range (~2660) before arming. Speed20counts/s, raw load abort20, voltage raw72–82, temperature40 are conservative provisional test gates, not measured safe force or hardware protection. Default JOG_ONLY limits commands to +/-5counts and rejects OPEN/CLOSE. Magnetic close remains uncalibrated. Completion tolerance reduced from5 to1count so a 5count step cannot immediately report done without approaching target. Host heartbeat console required. No physical motion or new upload performed by agent; software stop is best effort, not emergency stop.

### 2026-10-03 — Provisional jog load threshold adjustment

User-operated ARM succeeded after restoring sensor validity. JOG -5 from2317 to2312 triggered LIMIT_ERROR at position2317, load_raw24>20, voltage_raw76 within72–82, temp21<40; flags0,1,0,0 confirm only load threshold exceeded. Motion completion was not established. User disconnected power and requested adjustment. Raise provisional software raw-load abort threshold from20 to50 for next +/-5count test; speed20counts/s, bounds1937–2668, fault latch and all other gates unchanged. 50 is a test setting without force calibration or established safety meaning. Do not infer percentage torque or newtons. No automatic commands/upload or physical retest performed by agent.

### 2026-10-03 — User-authorized +/-100count manual jog

User reports two completed -5count jogs: 2317→2313 (target2312, raw load-20), then2313→2309 (target2308, raw load0), voltage76–77/temp21. User could not visually resolve gripper displacement; no physical motion accuracy claim. User explicitly requests +/-100count jog. Firmware and console now accept nonzero increments within[-100,100], rejecting outside increments and endpoints beyond1937–2668. OPEN/CLOSE remain disabled. Speed20counts/s and raw load abort50 unchanged. Motion timeout increased2→7s because100counts at20counts/s nominally requires5s plus2s margin; real motion duration/stop latency unvalidated. Heartbeat750ms/sensor350ms gates unchanged. C++ state/boundary and Python console boundary tests pass. No upload or physical motion by agent.

### 2026-10-03 — Lubricated-condition test preparation

User reports WD-40 Multi-Use applied to metal slide rail and requests less restrictive load threshold. Previous sweep_20261003_145120_389807 stopped atpos2157/load52>50 during closing, with voltage77/temp24 healthy. Change provisional software absolute-load abort50→80; all position, speed-register20, +/-100,7s timeout, sensor/watchdog and fault latch gates unchanged. 80 is not validated safe force or servo torque setting. User-reported lubrication changes test condition; amount/application/wait time and material compatibility not measured. New runs must be labelled lubricated plus changed threshold; these two changed factors prevent attributing improvement to lubrication alone. No physical rerun by agent. Existing faults require explicitDISARM/RESET or cold boot, never auto-recovery.


## 2026-10-03 — Shared gripper hardware boundary and operator control

Reuse the existing operator gateway/UI and task executive. Implement one atom_gripper_hardware hardware_bridge replacing the sensor-only bridge for actuator deployments; independent serial/device lifecycle, continuous watchdog and action fault handling justify this hardware node. Both ROS and standalone local UI use the same GripperController, never two concurrent serial owners. Keep vendor arm planning separate, retain default simulation recipes, add only reusable gripper capability and opt-in recipes. No ROS distribution/driver/procurement change.

Use successful physical sweep evidence (lubricated_load80, one run,3cycles/72segments) to restrict UI/Action position commands to nominal2000–2600counts, JOG<=100, encoder arrival tolerance3. This is position commissioning, not grasp validation. Force target/estimate extension points exist but force commands remain rejected until calibrated local control. ARM-to-STOP/DISARM ROS session lease prevents UI/task command competition; fault recovery is manual. Joint real-arm composition requires separate physical verification and is disabled by default. See GRIPPER_SYSTEM_INTEGRATION.md and //TODO G01–G09.

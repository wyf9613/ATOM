# Project Status

Last updated: 2026-09-25

## Phase

**Phase 0 - handover and architecture definition, with xArm 850 software-baseline verification underway**

The pinned official xArm 850 ROS 2 stack builds in Docker. A clean bare-arm path
now performs MoveIt planning and simulated trajectory execution without loading
the gripper. A separate arm-only transfer baseline publishes configurable pick
and place poses, then verifies vertical lift, orientation-constrained transfer
and vertical descent after simulated grasp success. Separately, the migrated
generic ATOM gripper description composes with the official arm model. Integrated
gripper control, attached-object handling, the complete task state machine and
physical-arm commissioning are not yet implemented or verified.

## Assets present

| Asset | Status | Location |
|---|---|---|
| Project context and proposed roadmap | Present | `ATOM_Project_Context.md` |
| Project scope and Stage 0–4 plan | Present, pending physical confirmation | `docs/PROJECT_SCOPE.md` |
| Related-work index and source papers | Present | `docs/RELATED_WORK.md`, `paper/paper/` |
| Previous-team final report | Present, 34 pages | `previous report/Capstone_Robotic_Hand_Lab_Experiment.pdf` |
| End-effector Fusion 360 archive | Present | `hardware/end effector/End Effector Assembly V3.f3z` |
| Derived ATOM gripper description | Migrated from the UR3e branch; standalone tests pass | `ros2_ws/src/atom_gripper_description`; parameters remain provisional pending measurement |
| Previous STM32 firmware | Missing | To request |
| Previous ROS/serial integration code | Missing | To request |
| Wiring diagram and pin map | Missing | To request |
| Raw experiment data | Missing | To request |
| Robot arm | UFactory xArm 850 delivered | Physical controller/accessory inventory and commissioning evidence required |
| Development environment | Docker image built: Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic | Base image digest pinned; headless acceptance tests pass; Gazebo and RViz X11 startup plus automated bare-arm motion verified on the current Ubuntu host |
| Vendor ROS stack | Official UFactory `xarm_ros2` Jazzy commit pinned and eight core packages built | `uf850` Xacro, TF, MoveIt planning and simulated trajectory control pass; physical hardware compatibility remains unverified |
| ATOM simulation packages | Ideal bare-arm, nominal actuator-dynamics and configurable transfer baselines pass | `ros2_ws/src/atom_xarm_sim` and `atom_xarm_dynamics`; server-only launch, MoveIt plan-and-execute acceptance, 100 Hz per-joint tracking reports, published pick/place poses and constrained three-segment transfer |
| Wrist camera and two-level tube-transfer fixture | One four-slot rack on the upper shelf with front-facing tag IDs 0–3, a transparent dynamic tube initially in slot 1, and a temporary vendor G1 gripper; mutually exclusive RGB / single RGB-D modes run in Gazebo. The current stage target is an in-rack slot 1 (tag 1) to slot 2 (tag 2) transfer. The workflow is topic-driven pre-observation followed by a separate approach phase | `docs/CAMERA_EXPERIMENT.md`; `pre_observation_target_pose` computes the default 0.35 m bearing target and `pre_observation_demo` executes it and reports Tag 1/2 poses in `link_base`, while the GUI wrapper launches Gazebo/RViz. The two-segment obstacle-free approach now executes to a 0.10 m selected-Tag standoff; one nominal RGB and one nominal RGB-D run passed with FK path checks and recorded visual updates. The real base/rack input, environment collision planning, actual contact grasp, in-rack transfer and hardware validation remain pending |
| Visual approach comparison and progress report | One complete successful RGB run and one complete successful RGB-D run have independent simulated-geometry error measurements. A separate 10-run RGB test reported by the team had 4 terminations classified as planning failures; its run-level logs and conditions are not archived here | `docs/RGB_VS_RGBD_SINGLE_RUN_COMPARISON_20260925.md`; `output/slides/ATOM_observation_progress_2026-09-25.html`; `output/video/Observation.webm`. The single-run comparison is not a success-rate or RGB-D-benefit estimate; depth is not yet fused into Tag pose |
| xArm + gripper composition | Description checks pass | `ros2_ws/src/atom_xarm_description`; neutral mount transform is a simulation placeholder, not a measured interface |
| Mobile-base specification/interface | Missing | Coordinate with base team |

## Demonstrated by the previous team

- UR3e-based, fixed-workstation pick-and-place using manually defined waypoints.
- Two simulated cuvette holders on one level surface, not the real instrument pair.
- 49 successful complete cycles out of 50 trials under that setup.
- Reported cycle time: 25.3 s for one cycle and 51.11 s for two continuous cycles.
- Quick-disconnect removal: approximately 5 s average over 20 trials.

## Not yet demonstrated

- Real Opentrons Flex to DynaPro NanoStar transfer or the specified +/-0.2 mm insertion accuracy.
- Measured gripping force below 5 N.
- Perception-guided grasp/place and online replanning. A simulated Tag-guided approach to 0.10 m standoff is demonstrated, but it does not execute a grasp or placement.
- Robust empty-grasp, timeout and maximum-travel handling.
- Hardware emergency-stop architecture.
- Commissioning on the delivered xArm 850.
- Dynamic Gazebo/MoveIt operation of the xArm 850 with the ATOM gripper attached.
- Physically identified arm actuator dynamics or validated vibration prediction.
- MPC implementation or comparison against the deterministic trajectory controller.
- Mobile-base navigation, docking or complete mobile manipulation.

## Development gates

| Gate | State | Exit evidence |
|---|---|---|
| 1. Inherited gripper understood | Not passed | Physical inspection, CAD hierarchy, firmware, wiring and parameter reconciliation |
| 2. Gripper robot description | In progress | Standalone Xacro, mesh provenance and parameter tests pass; RViz inspection and physical measurements remain |
| 3. Arm + gripper model | In progress | Modular combined Xacro and `check_urdf` pass with a neutral placeholder transform; measure the flange/adapter transform and validate collisions |
| 4. Simulation baseline | In progress | Ideal and nominal torque-driven bare-arm MoveIt runs pass without a gripper; 100 Hz per-joint reports and a target-publisher-driven lift/constrained-transfer/descent test are implemented. Physical model identification, combined gripper control/SRDF, attached-object handling and the complete task state machine remain follow-on work |
| 5. Real-arm deployment | Not started | Controller inventory, hardware-safe bring-up, mount/TCP measurement and commissioning |
| 6. Perception-guided manipulation | Tag-guided approach baseline passes; full gate open | RGB and RGB-D streams, pre-observation target topic, selected-Tag localisation and MoveIt approach to 0.10 m standoff pass in nominal simulation. Still require measured calibration, environment collision planning, robust repeated trials, grasp/place execution and fixed-waypoint comparison |
| 7. Mobile integration | Not started | Base interfaces, docking measurements and end-to-end trials |

## Immediate next work

1. Add arm-reach/reachability checks to pre-observation and an explicit realignment step when the latest Tag normal no longer passes through the alignment endpoint; archive the team's ten RGB trial logs and failure categories.
2. Obtain and verify the inherited gripper control code, then integrate measured TCP, contact feedback, grasp, lift and placement for the in-rack slot 1 → slot 2 task.
3. Design and 3D-print the rack and camera adapter, measure their transforms and repeatability, and begin small supervised physical trials after hardware-safe bring-up.

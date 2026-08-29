# Project Status

Last updated: 2026-08-29

## Phase

**Phase 0 - handover and architecture definition, with xArm 850 software-baseline verification underway**

The pinned official xArm 850 ROS 2 stack now builds in Docker and its description,
MoveIt and simulated-controller startup have been smoke-tested. The ATOM gripper,
whose generic description was migrated from the UR3e branch, now composes with
the official arm model. Integrated gripper control, task implementation and
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
| Development environment | Docker image built: Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic | Base image digest pinned; ATOM headless launch and automated smoke test passed twice consecutively after the controller-readiness fix; host GUI remains unverified |
| Vendor ROS stack | Official UFactory `xarm_ros2` Jazzy commit pinned and eight core packages built | `uf850` Xacro, TF, MoveIt planning and simulated trajectory control pass; physical hardware compatibility remains unverified |
| ATOM simulation package | Present and buildable | `ros2_ws/src/atom_xarm_sim`; server-only launch and automated smoke check |
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
- Perception-guided target localisation and replanning.
- Robust empty-grasp, timeout and maximum-travel handling.
- Hardware emergency-stop architecture.
- Commissioning on the delivered xArm 850.
- Dynamic Gazebo/MoveIt operation of the xArm 850 with the ATOM gripper attached.
- Mobile-base navigation, docking or complete mobile manipulation.

## Development gates

| Gate | State | Exit evidence |
|---|---|---|
| 1. Inherited gripper understood | Not passed | Physical inspection, CAD hierarchy, firmware, wiring and parameter reconciliation |
| 2. Gripper robot description | In progress | Standalone Xacro, mesh provenance and parameter tests pass; RViz inspection and physical measurements remain |
| 3. Arm + gripper model | In progress | Modular combined Xacro and `check_urdf` pass with a neutral placeholder transform; measure the flange/adapter transform and validate collisions |
| 4. Simulation baseline | In progress | Headless arm-only `uf850` TF, planning and trajectory checks pass; port gripper control/SRDF, then add the gripper action and task state machine |
| 5. Real-arm deployment | Not started | Controller inventory, hardware-safe bring-up, mount/TCP measurement and commissioning |
| 6. Perception-guided manipulation | Not started | Pose perturbation experiment against fixed-waypoint baseline |
| 7. Mobile integration | Not started | Base interfaces, docking measurements and end-to-end trials |

# Project Status

Last updated: 2026-08-29

## Phase

**Phase 0 - handover, inventory and architecture definition**

No ROS 2 package, robot model or buildable software stack has been received in this workspace yet.

## Assets present

| Asset | Status | Location |
|---|---|---|
| Project context and proposed roadmap | Present | `ATOM_Project_Context.md` |
| Previous-team final report | Present, 34 pages | `previous report/Capstone_Robotic_Hand_Lab_Experiment.pdf` |
| End-effector Fusion 360 archive | Present | `hardware/end effector/End Effector Assembly V3.f3z` |
| Previous STM32 firmware | Missing | To request |
| Previous ROS/serial integration code | Missing | To request |
| Wiring diagram and pin map | Missing | To request |
| Raw experiment data | Missing | To request |
| Robot arm | UFactory xArm 850 delivered | Physical controller/accessory inventory and commissioning evidence required |
| Development environment | Docker definition added: Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic | Not yet built or dynamically verified |
| Vendor ROS stack | Official UFactory `xarm_ros2` Jazzy commit pinned | `uf850` description/control/MoveIt/Gazebo baseline selected; hardware compatibility still unverified |
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
- Mobile-base navigation, docking or complete mobile manipulation.

## Development gates

| Gate | State | Exit evidence |
|---|---|---|
| 1. Inherited gripper understood | Not passed | Physical inspection, CAD hierarchy, firmware, wiring and parameter reconciliation |
| 2. Gripper robot description | Not started | Valid Xacro, TF, mesh scale, joint directions and limits in RViz |
| 3. Arm + gripper model | In progress | Official `uf850` stack pinned; add the inherited gripper as a separate model after measuring the flange transform |
| 4. Simulation baseline | Not started | Controllers, motion planning, gripper action and task state machine |
| 5. Real-arm deployment | Not started | Controller inventory, hardware-safe bring-up, mount/TCP measurement and commissioning |
| 6. Perception-guided manipulation | Not started | Pose perturbation experiment against fixed-waypoint baseline |
| 7. Mobile integration | Not started | Base interfaces, docking measurements and end-to-end trials |

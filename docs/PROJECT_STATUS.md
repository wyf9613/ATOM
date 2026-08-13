# Project Status

Last updated: 2026-08-13

## Phase

**Phase 0 - handover, inventory and architecture definition**

A buildable inherited-asset simulation baseline now exists. It is not the final
deployment stack and does not resolve the purchased-arm decision.

## Current documentation

- [`CURRENT_SIMULATION_BASELINE.md`](CURRENT_SIMULATION_BASELINE.md) records the
  implemented model, simulation, test evidence, reproduction steps and limits.
- [`ROS_GAZEBO_MOVEIT_TUTORIAL.md`](ROS_GAZEBO_MOVEIT_TUTORIAL.md) provides the
  prerequisite knowledge and project exercises for ROS 2, Gazebo,
  `ros2_control` and MoveIt 2.
- [`MOVEIT_GRASP_BASELINE.md`](MOVEIT_GRASP_BASELINE.md) records the implemented
  trajectory-control, task-state-machine and dual-mode acceptance workflow.

## Assets present

| Asset | Status | Location |
|---|---|---|
| Project context and proposed roadmap | Present | `ATOM_Project_Context.md` |
| Previous-team final report | Present, 34 pages | `previous report/Capstone_Robotic_Hand_Lab_Experiment.pdf` |
| End-effector Fusion 360 archive | Present | `hardware/end effector/End Effector Assembly V3.f3z` |
| End-effector neutral STEP assembly | Present, AP214, 20 products | `hardware/end effector/End Effector Assembly V3.step` |
| Modular gripper description | Provisional simulation model | `ros2_ws/src/atom_gripper_description` |
| Official UR3e description/simulation sources | Pinned verification dependency | `ros2_ws/atom_sim.repos` |
| Modular MoveIt verification configuration | Implemented, provisional | `ros2_ws/src/atom_ur3e_moveit_config` |
| Deterministic grasp task executor | Implemented for simulation | `ros2_ws/src/atom_manipulation` |
| Previous STM32 firmware | Missing | To request |
| Previous ROS/serial integration code | Missing | To request |
| Wiring diagram and pin map | Missing | To request |
| Raw experiment data | Missing | To request |
| Laboratory software baseline | Ubuntu 22.04 / ROS 2 Humble reported by supervisor | Reproduce with Docker, then verify exact packages on laboratory computer |
| Robot-arm model/driver selection | Unconfirmed | Procurement decision required |
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
- Commissioning on the actually purchased commercial arm.
- Mobile-base navigation, docking or complete mobile manipulation.

## Development gates

| Gate | State | Exit evidence |
|---|---|---|
| 1. Inherited gripper understood | Not passed | Physical inspection, CAD hierarchy, firmware, wiring and parameter reconciliation |
| 2. Gripper robot description | In progress | Xacro and mesh scale validate; physical joint directions, limits, inertials, mount and TCP remain open |
| 3. Arm + gripper model | Verification baseline only | Official UR3e description is composed with the gripper; purchased arm remains unconfirmed |
| 4. Simulation baseline | Verification baseline implemented | Native and `ros2_control` backends, MoveIt/RRT-Connect, Cartesian approach segments, explicit task states, and separate logical/physical grasp checks run in Humble/Fortress; real geometry, calibration, fault recovery and hardware equivalence remain open |
| 5. Real-arm deployment | Blocked | Hardware delivery, mount/TCP measurement and commissioning |
| 6. Perception-guided manipulation | Not started | Pose perturbation experiment against fixed-waypoint baseline |
| 7. Mobile integration | Not started | Base interfaces, docking measurements and end-to-end trials |

# Known Issues

## Project blockers

| ID | Issue | Impact | Next evidence/action |
|---|---|---|---|
| P-001 | Purchased arm is unconfirmed. | Blocks driver, URDF, MoveIt and mount selection. | Obtain purchase order/model/controller details. |
| P-002 | ROS 2 and Ubuntu versions are unconfirmed. | Blocks reproducible development environment. | Reconcile vendor and mobile-base support matrices. |
| P-003 | Firmware, ROS code, wiring and raw data are absent. | Cannot reproduce inherited control behaviour. | Request complete handover and archive it unchanged. |
| P-004 | Real workflow and instrument access are unconfirmed. | Test fixtures and precision requirements may be wrong. | Agree acceptance test with Chemical Engineering. |
| P-005 | Mobile-base interface is absent. | 2027 mechanical/electrical/software integration risk. | Freeze an interface-control document during 2026 S2. |

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
| G-009 | Simulation joint axes, -15 to +5 mm travel about the CAD assembly pose, inertial split, flange transform and TCP are provisional. | The model is suitable for software integration only; collision and kinematic results must not be treated as hardware evidence. |
| G-010 | Native Gazebo controllers and `ros2_control` are both retained and are numerically different backends. | The native path remains a regression test; only the `ros2_control` path is used for MoveIt trajectory execution, and neither is equivalent to a real vendor controller. |
| G-011 | Contact simulation uses rigid box collisions, a provisional 10 g cuvette and no silicone compliance. | A passing grasp test does not validate grip force, glass/COP stress, release adhesion or hardware reliability. |
| G-012 | The corrected contact baseline has only one clean run (`N=1`). | It is a regression check, not repeatability or statistical reliability evidence; run a defined batch after the provisional geometry is frozen. |
| G-013 | The MoveIt PlanningScene contains the robot and, during logical grasp, the cuvette, but not the Gazebo supports or real instrument geometry. | Current OMPL success is not obstacle-clearance or instrument-insertion evidence. |
| G-014 | MoveIt 2.5.9 on Humble can emit a class-loader shutdown fault after the task result while `move_group` is being torn down. | The task process and acceptance result complete first, but shutdown logs are noisy; reproduce against a newer supported MoveIt patch before treating clean process teardown as verified. |
| G-015 | The Ubuntu 24.04/Jazzy host currently lacks the `gz_ros2_control`, `moveit_ros_move_group` and `moveit_configs_utils` runtime packages. | Jazzy description/Xacro tests pass, but the new trajectory and MoveIt task path is dynamically validated only in the Humble/Fortress container until those host packages are installed. |

## Evidence limitations

- The 49/50 result used fixed manually tuned waypoints and simulated holders.
- Placement accuracy on the real DynaPro and workspace integration with real instruments were only partially verified.
- The one failure was attributed to manual setup, but the system also lacked autonomous detection/recovery for that misplacement.
- Long-term pad wear, quick-release repeatability and varying object geometries were not evaluated.
- The Gazebo fixture is a scenario support, not geometry for the Opentrons Flex or DynaPro NanoStar.

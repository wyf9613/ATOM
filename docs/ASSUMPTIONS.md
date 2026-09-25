# Assumptions and Open Questions

Items remain open until evidence is linked in `docs/DECISIONS.md`.

Resolved: A-001 (arm candidate) is superseded by D-006 after delivery of the
UFactory xArm 850.

Resolved: A-002 (Ubuntu/ROS direction) is superseded by D-007, selecting the
Ubuntu 24.04 / ROS 2 Jazzy Docker baseline. Exact package patches remain pinned
or captured by the container build.

| ID | Item | Current treatment |
|---|---|---|
| A-003 | Fiducials may be placed at workstations. | Preferred baseline, subject to lab approval. |
| A-004 | Real Opentrons Flex and DynaPro NanoStar access will be available. | Unconfirmed; maintain a representative test fixture plan. |
| A-005 | Precise insertion into the real DynaPro is required. | Unconfirmed; this changes sensing/control requirements. |
| A-006 | The inherited physical gripper matches the received F3Z and report. | Must be checked by inspection and measurement. |
| A-007 | Magnetic sensing can verify grasp force. | Only threshold-based contact was shown; force calibration is missing. |
| A-008 | The mobile base can carry and power the selected arm safely. | Requires payload, CoM, overturning moment and power data. |
| A-009 | The ATOM gripper mount is coincident and axis-aligned with the xArm `link_eef` frame. | Neutral simulation placeholder only (`xyz=0 0 0` m, `rpy=0 0 0` rad); measure the adapter/quick-disconnect transform before hardware use. |
| A-010 | The migrated gripper limits, mass distribution, TCP and terminal-pad collisions represent the inherited physical gripper. | Retained as traceable simulation inputs from the UR3e branch; verify against the delivered gripper and record measured replacements. |
| A-011 | Nominal joint PD gains reproduce the delivered xArm 850 servo response. | False until identified: current gains are simulation-only tuning inputs. Measure step/swept-sine response, delay, friction, backlash/compliance and payload dependence before using the model for prediction or MPC. |

## Perception and shared-workspace inputs (2026-09-11)

| ID | Unresolved input | Required evidence / closure |
|---|---|---|
| A-012 | Rigid fiducial boards can be attached to racks/instruments and slot geometry predicts the tube grasp pose. | Confirm mounting permission and measure rack-to-tag transform, tube seating, height and tilt variation; otherwise add direct object observations. |
| A-013 | A fixed RGB-D view covers the approach paths and provides useful depth under lab lighting. | Record camera assets, working distances, coverage/occlusion map, depth invalidity, latency and cross-view needs; no camera model selected. |
| A-014 | The delivered arm and gripper can execute and confirm a controlled stop while retaining the sample. | Verify controller/firmware interfaces, hardware protection path, watchdog, stop displacement by pose/speed/load, clamp hold and power-loss behavior. |
| A-015 | Calibration and waypoint error fit the true grasp/insertion tolerance. | Independently measure intrinsics/extrinsics, TCP, slot and aperture geometry; evaluate held-out poses and error budget in mm/rad. |
| A-016 | Online planning can meet the target computer and driver deadlines while preserving tube constraints. | Check D-007 pinned-version compatibility, measured planning/execution delay, command arbitration, predicted occupancy and timeout fallback before accepting a plugin/configuration. |
| A-017 | One ordinary RGB or one RGB-D camera can fit on the UF850 wrist at the provisional simulated mount without blocking the gripper or workspace. | Compare real candidate dimensions, mass, cable routing, field of view and motion clearance; measure a separate hand-eye transform for each candidate. No camera purchase is selected. |
| A-018 | One 0.040 m AprilTag can be installed on the front face of each of four source-rack slots and resolved from wrist observation poses. | Measure the actual rack pitch, front label area, occlusion and lighting; verify every tag ID across repeated poses and perturbations. The current four-slot Gazebo layout is only a fixture. |
| A-019 | The temporary vendor G1 gripper can hold and release the intended transparent tube without slip or fracture. | Demonstrate collision-aware approach, contact grasp, lift, release and placement in Gazebo; then test the actual selected end effector with measured tube and grip-force limits. Controller actuation alone is insufficient. |
| A-020 | The provisional two-level shelf, rack positions and empty tube mass/inertia approximate the intended bench. | Measure shelf clearances, rack/slot coordinates, tube outer/inner dimensions and mass; update SDF collision/inertia and compare repeated pickup/placement outcomes. |
| A-021 | The pick/place target has an accurately calibrated world-frame pose and the robot base has an approximate planar world-frame pose. | This pair of assumptions supplies target height and coarse bearing for pre-observation; the current simulation substitutes theoretical rack geometry and `theta_true + U(-5°, +5°)` for a base-localisation measurement. Define the real base-localisation method, measure bearing/height error over repeated dockings, and verify the common TF chain before hardware use. |
| A-022 | A custom multi-slot rack can be placed repeatably at a calibrated workstation pose, with one resolvable numbered Tag for each relevant slot and a measured camera-to-gripper adapter. | Design and 3D-print the rack and adapter, measure placement repeatability, tag-to-slot transforms, camera extrinsics and reachable viewpoints; the current printed hardware and metrology do not yet exist. |

## Questions for supervisors and partner teams

1. What controller, firmware, serial-number calibration and supplied accessories arrived with the xArm 850?
2. What Ubuntu/ROS 2 versions are required by the arm and mobile-base teams?
3. What is the exact sample-transfer workflow and success criterion?
4. Is real instrument insertion mandatory, and what is the true tolerance?
5. Can fiducials or structured fixtures be attached to each workstation?
6. Which cameras, force/torque sensors and compute hardware are available?
7. What laboratory safety review and emergency-stop architecture are required?
8. Can the previous team provide firmware, ROS code, wiring, raw data and a handover session?
9. What are the base payload, power, mounting, docking and navigation interfaces?

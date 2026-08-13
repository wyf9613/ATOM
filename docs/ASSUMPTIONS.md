# Assumptions and Open Questions

Items remain open until evidence is linked in `docs/DECISIONS.md`.

| ID | Item | Current treatment |
|---|---|---|
| A-001 | The commercial arm may be a UFactory xArm 850. | Candidate only; do not build against it yet. |
| A-002 | Ubuntu and ROS 2 will be used for integration. | Direction accepted; exact versions unconfirmed. |
| A-003 | Fiducials may be placed at workstations. | Preferred baseline, subject to lab approval. |
| A-004 | Real Opentrons Flex and DynaPro NanoStar access will be available. | Unconfirmed; maintain a representative test fixture plan. |
| A-005 | Precise insertion into the real DynaPro is required. | Unconfirmed; this changes sensing/control requirements. |
| A-006 | The inherited physical gripper matches the received F3Z and report. | Must be checked by inspection and measurement. |
| A-007 | Magnetic sensing can verify grasp force. | Only threshold-based contact was shown; force calibration is missing. |
| A-008 | The mobile base can carry and power the selected arm safely. | Requires payload, CoM, overturning moment and power data. |
| A-009 | The STEP assembly placements represent the as-built gripper geometry. | Use for simulation visuals only until checked against the physical gripper. |
| A-010 | The rack-and-pinion can be represented by two symmetric prismatic finger joints. | Provisional robot-level simplification; measure axes, zero position and travel before hardware use. |
| A-011 | The UR3e-to-gripper mounting transform can be inferred from CAD. | The simulation attaches `gripper_mount` to the official UR `flange` frame and uses the CAD case rear-face centre as a provisional datum. Replace this with measured quick-disconnect and TCP transforms before hardware use. |
| A-012 | A representative cuvette can be simulated with a rigid 14 x 14 x 45 mm, 10 g collision box. | The 14 x 14 mm cross-section is from the report; height and mass are provisional. The visual approximates the official WNDMC disposable COC microcuvette silhouette, but the exact inherited labware is unconfirmed. Replace both with identified labware CAD and filled-mass measurements. |
| A-013 | The reported mean static friction coefficient of 0.88 can parameterise rigid Gazebo contact. | Use only for baseline sensitivity tests. The report gives N=10 inclined-plane trials but no uncertainty, dynamic friction or compliant contact model. |

## Questions for supervisors and partner teams

1. What exact arm has been ordered, with what controller and delivery date?
2. What Ubuntu/ROS 2 versions are required by the arm and mobile-base teams?
3. What is the exact sample-transfer workflow and success criterion?
4. Is real instrument insertion mandatory, and what is the true tolerance?
5. Can fiducials or structured fixtures be attached to each workstation?
6. Which cameras, force/torque sensors and compute hardware are available?
7. What laboratory safety review and emergency-stop architecture are required?
8. Can the previous team provide firmware, ROS code, wiring, raw data and a handover session?
9. What are the base payload, power, mounting, docking and navigation interfaces?

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

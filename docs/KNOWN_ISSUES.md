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

## Evidence limitations

- The 49/50 result used fixed manually tuned waypoints and simulated holders.
- Placement accuracy on the real DynaPro and workspace integration with real instruments were only partially verified.
- The one failure was attributed to manual setup, but the system also lacked autonomous detection/recovery for that misplacement.
- Long-term pad wear, quick-release repeatability and varying object geometries were not evaluated.


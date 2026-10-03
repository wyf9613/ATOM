# Assumptions and Open Questions

## 2026-10-03 reinforced adapter update

- User tentatively selected PLA and estimates gripper plus camera at roughly 0.7 kg by heft; no scale, CoM, uncertainty, print parameters or motion/load history supplied. Include the new adapter, fasteners, ESP32 and cables in future weighed tool payload.
- Backplate v2 supersedes v1 geometry: 52 mm rear offset, 12/14 mm plate thicknesses and continuous Ø76 annular body. These are design dimensions, not validated printed stiffness/capacity. Original M3 shell tabs remain a potential load-path bottleneck.
- ESP32 now has a separate bracket on the lower seam holes opposite the camera. The provisional PCB/connector envelope reaches z=-97 mm in inherited coordinates; tabletop, finger and cable clearance require verification. See [v2 limits](../source_cad/backplate/v2/README.md).

## 2026-10-03 backplate / ESP32 mechanical inputs

- User-provisional ESP32 hole centres are 46.5 × 23.5 mm, Ø4.0 mm; no measurement method, sample count or uncertainty supplied. Actual PCB outline, thickness, corner-hole land, USB/headers/antenna and attached cables remain to be checked. The supplied electrical/module PDFs do not dimension the complete development board.
- Rear-hole Ø3.2 mm / 18 × 97 mm pattern and 10 mm tab depth are inherited CAD geometry, not hardware verification. Confirm fasteners, nut/washer access and physical agreement.
- UF850 nominal flange comes from official V2.3.0 p26. Delivered flange revision, Ø31.50 H6 mating fit, locating pin, actual usable thread depth and wrist/connector clearance remain open.
- Backplate v1 uses provisional 64.2 mm rear extension and 6/8 mm plate thicknesses. Material, stress/deflection, fatigue, preload, inertial data and calibrated mount/TCP are unverified. See [CAD v1](../source_cad/backplate/v1/README.md).

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

## Camera bracket unresolved inputs (2026-10-02)

- User tentatively recalls a RealSense D435; verify the physical model before finalizing mounting geometry or screw insertion depth.
- Reusing the two upper shell-fastening holes is a proposed concept. Hole geometry, existing fastener stack, shell clamping, bracket stiffness, finger/FOV/cable clearance and repeatable camera-to-gripper calibration remain unverified. See [camera bracket concept](GRIPPER_CAMERA_BRACKET_CONCEPT.md).

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

## 2026-10-01 — Coarse rack input limitations

Coarse rack XY noise is independently uniform ±0.025 m per axis by default, provisionally chosen for simulation regression, not measured base/localization error. Exact z is the desired pre-observation TCP height computed from nominal scene tag height plus the existing 0.080 m camera offset. Rack membership defaults to scene IDs 0..3; physical tag inventory, size, spacing and hand-eye/TCP calibration need measurement. Full configured rack visibility in a coherent frame is required before alignment; failure to see it must fail observation rather than substitute simulation truth. Separate pose/task topics currently have no atomic multi-task identity contract. RGB-D remains RGB PnP with depth-stream validation.

## 2026-10-01 — Depth fusion assumptions

Fusion needs registered optical-Z depth in metres, synchronized RGB and matching calibrated intrinsics/distortion. Simulation's single rgbd_camera is explicitly accepted by its scripts; no real sensor registration or noise model is confirmed. Planar opaque tag surfaces, known rigid tag layout and per-region depth support are assumed. Joint residual scales (0.7 px / 2 mm), plane quality and conflict gates are provisional; calibrate/validate against physical measurements before hardware use. Depth holes return RGB PnP with diagnostics; persistent conflict rejects observations. [Details](DEPTH_FUSION.md).

## ESP32 migration unresolved facts (2026-10-02)

- Sensor is provisionally MLX90393 based on user identification and board markings; full ordering code, carrier circuitry and sensor count are unconfirmed. User screenshots confirm address 0x14 and valid XYZ records.
- GPIO21/22 are selected from the photographed classic ESP32 DEVKIT V1; user confirmed wiring and sensor communication, but physical voltage is unmeasured. Initial address 0x0C was superseded by observed 0x14.
- STS3215 and URT-1 are reported inherited parts; actual labels, motor supply/current, interface levels, ID/baud/mode and travel limits still need verification. Report interface-board 5V must not be treated as confirmed motor supply.
- Original STM32 source and protocol are unavailable in the current handover. New protocol is not backwards-compatible evidence.
- New sensor frame has no measured mount TF, covariance or force calibration. Initial failed host captures were followed by reset/reopen fixes and two clean hardware runs (102 and 303 valid records). Long-duration reliability and motor/ROS runtime remain unverified. See GRIPPER_VALIDATION_LOG.md.

### 2026-10-02 motor implementation boundary

Optional motor commissioning code is implemented, but actual servo/driver model, UART compatibility, supply rating, ID/baud, position mode, limits/direction, load/voltage units and thresholds remain unmeasured. Candidate ID 1 / 1 Mbps are not confirmed. No real motor motion, fault-stop latency or force-control result is claimed. Default motor enable is zero; all measured limit/voltage/load configuration is unset. See GRIPPER_MOTOR_COMMISSIONING.md.

2026-10-03: User confirms STS3215, ID1/1Mbps/position mode via successful feedback. Observed tight1917/open2688, N=1 each; repeatability, rated voltage variant, force/load calibration and actual stopping response unresolved. First motion configuration uses provisional margins and +/-5count-only gates; no physical motion validation yet.


## 2026-10-03 — Provisional gripper integration envelope

UI/ROS Open2600 and Close2000counts use the nominal span covered by the one successful72segment empty-gripper sweep; they are not full mechanical limits or contact targets. Positive counts open. ±3counts completion tolerance is an encoder criterion, not measured mm accuracy. Servo load80 is a provisional raw abort setting without force meaning. Force estimate is unknown and force control disabled. Physical arm/real TF, calibrated jaw aperture and object grasp remain unverified; see GRIPPER_SYSTEM_INTEGRATION.md.

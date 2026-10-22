# Assumptions and Open Questions

## 2026-10-21 — Laser-cut cuvette-rack prototype unresolved inputs

The user confirms nominal 3 mm MDF and separate five-hole small/large racks. Measured thickness/variation, actual vessel shape/max diameter/cap envelope, same-machine kerf and friction retention remain open. The v1 nominal 0.15 mm full kerf, 0.05 mm interference and 0.60 mm diametral vessel clearance have zero physical test samples. Also verify 3 mm panel deflection/retention and tipping under real loads; gripper approach clearance; tag-ID inventory, MDF engraving contrast, view angles and measured tag-to-slot/TCP transforms; TCS internal format/template/layers/material acceptance. Existing four-slot runtime scenes have not been migrated. See [prototype and validation plan](mechanical/CUVETTE_RACK_LASER_V1.md).

## 2026-10-19 — Added finished-station candidates remain unvalidated

Rev06 compares six stations while retaining the Rev05 BLUETTI baseline. DJI Power 1000 V2 / Power 2000 / Mini advertised continuous battery outputs are 2600 / 3000 / 800 W; these are manufacturer ratings, not measured robot loads. V2's 2600 W figure is specified under 25 C laboratory conditions. Exact AU SKU, output/PE/protection, manuals, stock/PO quotes, restart behavior and arm/computer combination tests remain to be checked for any substitute. D1 availability wording conflicts, so no in-stock claim is made. EcoFlow Plus does not increase nominal energy above Classic. The same assumed 80% usable factor gives a 2 h mean-load threshold of 819.2 W for 2048 Wh versus 409.6 W for 1024 Wh; actual task input remains unmeasured. See [comparison and sources](research/POWER_STATION_COMPARISON_20261019.md).

## 2026-10-19 — Current proposal status after user preference

Rev05 restores BLUETTI Elite 100 V2 as the priority integrated candidate. Earlier ON HOLD wording describes the prior review stance, not the current candidate ranking. Manufacturer intended-use confirmation, electrical protection, startup/braking compatibility and physical tests remain outstanding. At an assumed80% usable factor,1024Wh supports the two-hour target only at approximately409.6W or less combined mean AC load; no task power has been measured. The preference is not an approval or safety/compatibility claim.

## 2026-10-19 — Shared source: candidate evidence and unresolved prices

Two-hour target confirmed; actual mean/peak AC input, delivered controller nameplate and motion profile still unmeasured. New modular candidates have explicit vehicle-use documentation, but none has UF850 paired validation. iTECH24V100 page has conflicting quick stats, its linked guide is largely generic, and the matching listed charger is sold out. Amptron50Ah old/new pages conflict on availability and IP revision. Require exact written datasheets, battery/inverter/charger pairing, stock, electrical installation and acceptance quotes before updating the purchase selection. See [comparison](research/SHARED_MOBILE_POWER_OPTIONS_20261019.md).

## 2026-10-19 — Mobile battery restriction found in the AU manual

The BLUETTI AU support manual explicitly restricts moving the product during operation (PDF p5). Tracer-mounted powered travel is therefore not cleared. Battery model selection is on hold pending explicit manufacturer permission, controller/inverter compatibility evidence and electrical review. Nominal voltage/frequency/power screening is not proof of system compatibility. See [battery evidence audit](research/BATTERY_COMPATIBILITY_AUDIT_20261019.md). Rev04 retains an energy funding placeholder only; the Pi remains included in the team budget.

## 2026-10-19 — AC battery supply and procurement prerequisites

User confirms wall-AC supply and approved GRA; earlier AC-vs-DC uncertainty is superseded at this level. Exact controller nameplate, AC inrush, regenerative compatibility and portable-source earthing/fault protection remain unverified. GRA coverage of new lithium/AC activities, approved charging location, project code, prior expenditure, prepurchase checklist, IO cable quote, servo variant/current and Chemical Engineering funding remain open. Public prices are budget evidence, not product approval or supplier formal quotes. See [procurement actions](research/PROCUREMENT_ACTIONS_20261019.md).

## 当前待确认输入入口（2026-10-06）

先看 [当前状态](PROJECT_STATUS.md) 与 [夹爪接入计划](gripper/GRIPPER_INTEGRATION_PLAN.md)。当前重点是传感器调整后的配置、试件允许力/变形、接触/力模型、停止/保持/释放标准，以及真实相机型号、安装/手眼/TCP、arm控制器/驱动、仪器工作流与底盘接口。

下方编号与日期条目保留历史假设；已有“Resolved”或后续实测的条目不作为当前缺失项。原固件未收到、电机未通信、早期引脚/阈值等描述须结合2026-10-03和2026-10-06增量记录解释。传感器重新装配或更换时，旧磁场基线/参数不能自动继承。

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
- Reusing the two upper shell-fastening holes is a proposed concept. Hole geometry, existing fastener stack, shell clamping, bracket stiffness, finger/FOV/cable clearance and repeatable camera-to-gripper calibration remain unverified. See [camera bracket concept](mechanical/GRIPPER_CAMERA_BRACKET_CONCEPT.md).

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

Fusion needs registered optical-Z depth in metres, synchronized RGB and matching calibrated intrinsics/distortion. Simulation's single rgbd_camera is explicitly accepted by its scripts; no real sensor registration or noise model is confirmed. Planar opaque tag surfaces, known rigid tag layout and per-region depth support are assumed. Joint residual scales (0.7 px / 2 mm), plane quality and conflict gates are provisional; calibrate/validate against physical measurements before hardware use. Depth holes return RGB PnP with diagnostics; persistent conflict rejects observations. [Details](perception/DEPTH_FUSION.md).

## ESP32 migration unresolved facts (2026-10-02)

- Sensor is provisionally MLX90393 based on user identification and board markings; full ordering code, carrier circuitry and sensor count are unconfirmed. User screenshots confirm address 0x14 and valid XYZ records.
- GPIO21/22 are selected from the photographed classic ESP32 DEVKIT V1; user confirmed wiring and sensor communication, but physical voltage is unmeasured. Initial address 0x0C was superseded by observed 0x14.
- STS3215 and URT-1 are reported inherited parts; actual labels, motor supply/current, interface levels, ID/baud/mode and travel limits still need verification. Report interface-board 5V must not be treated as confirmed motor supply.
- Original STM32 source and protocol were unavailable at the 2026-10-02 review. Superseded on 2026-10-06: user supplied EE.zip and balitom/Capstone_code, containing several Arduino sketches, G/R and GD/RD command/result strings and a separate MATLAB teaching protocol. The exact deployed legacy firmware/version remains unconfirmed; these files do not establish compatibility with the current ESP32 protocol. See LEGACY_GRIPPER_CODE_REVIEW.md.
- New sensor frame has no measured mount TF, covariance or force calibration. Initial failed host captures were followed by reset/reopen fixes and two clean hardware runs (102 and 303 valid records). Long-duration reliability and motor/ROS runtime remain unverified. See GRIPPER_VALIDATION_LOG.md.

### 2026-10-02 motor implementation boundary

Optional motor commissioning code is implemented, but actual servo/driver model, UART compatibility, supply rating, ID/baud, position mode, limits/direction, load/voltage units and thresholds remain unmeasured. Candidate ID 1 / 1 Mbps are not confirmed. No real motor motion, fault-stop latency or force-control result is claimed. Default motor enable is zero; all measured limit/voltage/load configuration is unset. See GRIPPER_MOTOR_COMMISSIONING.md.

2026-10-03: User confirms STS3215, ID1/1Mbps/position mode via successful feedback. Observed tight1917/open2688, N=1 each; repeatability, rated voltage variant, force/load calibration and actual stopping response unresolved. First motion configuration uses provisional margins and +/-5count-only gates; no physical motion validation yet.


## 2026-10-03 — Provisional gripper integration envelope

UI/ROS Open2600 and Close2000counts use the nominal span covered by the one successful72segment empty-gripper sweep; they are not full mechanical limits or contact targets. Positive counts open. ±3counts completion tolerance is an encoder criterion, not measured mm accuracy. Servo load80 is a provisional raw abort setting without force meaning. Force estimate is unknown and force control disabled. Physical arm/real TF, calibrated jaw aperture and object grasp remain unverified; see GRIPPER_SYSTEM_INTEGRATION.md.

## 2026-10-06 — Legacy gripper source handover

- Which sketch, dependency versions and parameters actually ran on the previous team's gripper remain unknown. Zip and GitHub EE_calibration differ, and the zip sketch has a missing semicolon. Request the deployed version plus repeatable raw measurements before treating either parameter set as established behavior.
- Legacy magnetic thresholds have no explicit units, calibration dataset, loading conditions or uncertainty in the supplied code; they are not inherited force limits. Current Adafruit telemetry is in µT and force remains unknown.
- Whether one stationary magnetic baseline separates contact from unloaded jaw motion, servo energization, temperature and mounting changes remains unmeasured. Collect position-dependent unloaded and independently measured force data before enabling contact/force control.
- At the 2026-10-06 review revision, UI/ROS close used position-mode JOG; current main uses continuous MOVE and does not run the firmware magnetic CLOSE branch. A future contact result must remain separate from position completion and stable grasp verification. Review and implementation mapping: [LEGACY_GRIPPER_CODE_REVIEW.md](gripper/LEGACY_GRIPPER_CODE_REVIEW.md).

## 2026-10-06 — Sensor adjustment before integration

User confirms the end-effector sensor still needs adjustment. Whether this changes sensor model, mounting, magnet, wiring or acquisition settings remains unspecified; the next sensor configuration is not frozen. Existing magnetic baseline/contact parameters must not qualify a changed configuration. Follow [GRIPPER_INTEGRATION_PLAN.md](gripper/GRIPPER_INTEGRATION_PLAN.md): software mocks can progress now, while hardware contact/force and combined arm tasks require configuration-specific evidence. Test article, allowable force/deformation, signal quality, stopping envelope, grasp/release criteria and test counts remain to be defined before the relevant physical gates can pass.

## 2026-10-07 — CAD v2 flange and calibration prerequisites

The print archive restores bracket placement by reversing its recorded translations.
Flange centre CAD [80.8,43.494,-22.225] mm and gripper +Z offset51.964mm
are geometry-based inferences, N=1 CAD assembly; hardware flange clocking,
fit, TCP, camera/PCB/cables, actual mass/CoM and finger encoder mapping remain
unmeasured. Source STEP files named by the print manifest are not present locally.
The fixed object's identity/mass/material, standard-force instrument, connected
computer/serial port and printed/installed flange state remain unspecified.
See GRIPPER_MOUNT_V2_INTEGRATION.md and GRIPPER_FORCE_CALIBRATION.md.


2026-10-07 本地同步补充：此前工作区的 source_cad/backplate、camera_bracket、esp32_bracket 和 print_pack 已恢复。上文“source STEP files absent locally”描述原提交环境；文件现已存在不代表已完成源模型复核、打印装配或物理验证。

## 2026-10-07 — Wrist power and camera link unresolved facts

User calls the arm “xArm 858” and tentatively recalls “D345i”; existing D-006 records UF850 arrival, but the actual camera label and delivered wrist connector revision need verification. UF850 V2.3.0 p27 describes M8 4-pole/100M Ethernet, whereas the current online §4.5 says 1000M and lists eight pins while retaining four-pole wording. Do not assume gigabit/four-pair wiring or USB-over-CAT compatibility. Tool IO documentation specifies 20–30V, nominal24V/max1.8A, not a direct5V or7.4V output. Board revision, VIN/USB power isolation, motor-rated voltage/peak current, DC/DC thermal/transient budget and hardware fault/hold behavior remain unmeasured. No DC/DC, extender or camera replacement is selected. See [research and candidate wiring](research/WRIST_POWER_AND_CAMERA_LINK_20261007.md).

## 2026-10-07 — Tracer2.0 onboard compute and energy boundary

User specifies future Tracer2.0 and onboard autonomous operation without carrying a laptop, with AUD500–1,000 compute budget. Procurement/arrival, chassis revision/CAN firmware, actual external power voltage/current/BMS/estop behavior, arm AC-vs-DC control box, computer workload/thermal profile, navigation sensors, CoM and dynamic stability remain unconfirmed. Current manufacturer page lists24V30Ah and24V15A external power; this does not establish that UF850 peak power can be supplied from that port. No onboard computer, JetPack, base-driver version or arm power converter is selected; retain D-007. See [candidate design and power calculations](research/TRACER2_ONBOARD_COMPUTE_20261007.md).

## 2026-10-21 — Backplate outline and independent teaching handle concept

User requests a contour-fitting backplate and a separate flange-side teaching handle, with concept review before CAD work. The sketch interprets separate as independently manufactured/removable parts sharing flange fasteners; whether shared fasteners/contact satisfy the user's intended independence remains unconfirmed. Handle material, grip clearance, orientation, ring thickness, pilot/locating-pin arrangement, fastener engagement/preload, hand force/moment envelope, wrist/cable clearance and structural qualification are unresolved. Original CAD nominal dimensions are not physical measurements. No manufacturing CAD, tool transform or hardware capability has been updated. See [concept and evidence](mechanical/backplate_handle_concept_20261021/README.md).

## 2026-10-21 — Contour/handle concept revision 02

User prioritizes strength while requesting no frontal outline protrusion from the custom adapter and a vertical SO101-inspired stick grip at the same flange-side location. The tighter outline requires reshaping the v2 shoulder/body, not just clipping corners. CAD envelope calculations show limited mounting-ear edge material; no equal-strength claim or manufacturing dimensions are established. Single-ended stick-grip support needs bending/torsion checks, replacing the previous D-loop assumptions. Shared flange fastening remains provisional. See [revision 02](mechanical/backplate_handle_concept_20261021/README.md#最新修订-02).

## 2026-10-21 — Mechanics screening and tentative PETG correction

The user wants all printed structural parts and subsequently corrected PLA to probably "pteg", interpreted provisionally as PETG; exact spool/grade remains unconfirmed. This supersedes using PLA as the current material assumption. Handle axis is now radial through the flange center, with no 90-degree offset support. Analytical screening compares existing v2, the previous elliptical sketch and a local-cap-trim alternative; no FEA, physical tests, load rating or safety factor exists. Narrow mounting ears, printed anisotropy, creep/preload, actual load envelope/CoM, fastener contact and wrist clearance remain unresolved. See [mechanics report](mechanical/backplate_handle_concept_20261021/analysis/REPORT.md).

## 2026-10-21 — Teaching handle v1 prototype inputs

Handle STL exported for printing; backplate revision deferred. The 16 mm ring uses provisional robot-side pilot OD31.45 x 2 mm, tool-side recess OD31.8 x 2.4 mm, four OD6.8 holes on PCD50 and a locating-pin clearance channel OD6.4. Delivered flange fit, printed tolerances, pin usage/length, M6 screw length/washer/head access and real wrist/cable/hand clearance remain unverified. PETG grade/process, printed strength, creep and actual load envelope are unknown; no load rating. The optional 7 mm fit coupon checks geometry only and cannot stand in for the 16 mm load-bearing ring. [Print guide](mechanical/TEACHING_HANDLE_V1_PRINT_GUIDE.md).

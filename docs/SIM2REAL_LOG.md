# Simulation-to-Real Log

Record every material mismatch between the robot model/simulation and measured hardware.

| Date | Subsystem | Simulated assumption | Real measurement | Correction | Validation |
|---|---|---|---|---|---|
| TBD | Gripper | Finger travel and joint limits from CAD | Pending | Pending | Pending |
| TBD | Gripper | Mass/inertia from CAD materials | Reported mass 580 g; measurement pending | Pending | Pending |
| TBD | Mount | CAD flange-to-gripper transform | Pending | Pending | Pending |
| TBD | TCP | TCP at nominal cuvette centreline | Pending calibration | Pending | Pending |
| TBD | Perception | Ideal camera extrinsics | Pending calibration | Pending | Pending |
| TBD | Collision | Simplified collision meshes | Pending clearance tests | Pending | Pending |
| TBD | Labware | Rigid 14 x 14 x 45 mm, 10 g cuvette | Pending identified labware measurement | Pending | Pending |
| TBD | Contact | Rigid Coulomb friction, mu=0.88 | Silicone 20A inclined-plane mean 0.88, N=10; uncertainty pending | Pending | Pending |

For each entry, attach units, measurement method, configuration/revision and the test that closes the discrepancy.

## 2026-08-12 - UR3e plus inherited gripper Gazebo baseline

### Simulation configuration

- Ubuntu 24.04.3, ROS 2 Jazzy, `ros_gz` 1.0.22 and Gazebo Sim 8.11.0.
- Official `ur_description` 3.5.0, with `ur_type:=ur3e` through the upstream UR3e parameter files.
- Inherited STEP assembly SHA-256
  `8EE4FD1C064210EAB24CB10BA67623E497CAB0866ADBCA86D5BE9A0C63AAF351`.
- STEP visuals exported as one fixed body and two moving finger subassemblies.
  Fixed-body mesh: 120,464 triangles; each finger mesh: 1,068 triangles.
- Collision geometry uses box primitives rather than detailed CAD.
- Gazebo-native position controllers provide the deterministic baseline. ROS 2
  `Float64` command topics and `JointState` feedback are bridged with `ros_gz_bridge`.
- Gravity is disabled because the available native Gazebo position controller
  is used only for a kinematic smoke test; gravity-compensating controller
  behaviour has not been validated.

### Smoke-test evidence

- `check_urdf` parsed the full chain from `world` through the UR3e `flange`,
  explicit gripper mount, gripper base, both fingers and provisional TCP.
- Gazebo spawned `ground_plane` and `ur3e_atom` and resolved both UR and gripper meshes.
- One deterministic four-pose demo run completed (`N=1`; functional smoke test,
  not a timing or accuracy experiment).
- Eight seconds after the final home command, one feedback sample showed a
  maximum arm-joint position error of `0.00210 rad`, a maximum arm-joint speed
  magnitude of `1.05e-5 rad/s`, and a maximum finger zero-position residual of
  `2.54e-5 m`.

### Differences and unresolved evidence

- UR3e nominal upstream kinematics are used; no serial-number-specific robot
  calibration has been applied.
- The UR3e is the previous team's university test platform, not the confirmed
  Project ATOM purchase.
- The reported gripper mass is 0.58 kg, but its simulated 0.48/0.05/0.05 kg
  link split and box inertias are estimates with unknown uncertainty.
- The original baseline incorrectly treated the URT-1 servo driver board as a
  mechanical mount datum and attached the gripper to `tool0`. The corrected
  baseline attaches `gripper_mount` to the upstream mechanical `flange` frame
  with the upstream `flange`-to-`tool0` axis alignment, and uses the centre of
  the CAD case rear faces as a reproducible provisional datum. The physical
  quick-disconnect transform and TCP have not been measured.
- Finger direction and the `-15 to +5 mm` single-side travel window are
  provisional and have not been checked against the physical gripper.
- No pad compliance, magnetic sensing, servo dynamics, calibrated grip force,
  fault handling, hardware stop, trajectory planning or real instrument
  geometry is represented.

## 2026-08-12 - Provisional cuvette gravity/contact baseline

### Scenario configuration

- Gravity: `9.81 m/s^2` downward; physics step: `0.001 s`.
- Cuvette collision: rigid box, `14 x 14 x 45 mm`; mass: `0.010 kg`
  provisional because no filled-cuvette mass was received.
- Cuvette visual approximates the blue-cap, transparent-body and four-foot
  silhouette shown for the official WNDMC disposable COC microcuvette. The
  report does not identify a part number or provide its full dimensions, so
  the visual details are illustrative and do not alter the collision model.
- Finger collision pads: rigid boxes, `6 x 20 x 20 mm`, aligned to terminal-pad
  CAD slices. The CAD assembly pose has an approximately `39.681 mm` visible
  pad gap; finger axes retain the symmetric prismatic simplification with a
  provisional `-15 to +5 mm` travel window about that pose.
- Coulomb friction input: `mu=mu2=0.88`, based on the report's mean from 10
  Silicone 20A/cuvette inclined-plane trials. No uncertainty or dynamic
  friction was reported.
- Gazebo-native PID gains were tuned for numerical holding under gravity. They
  are not UR3e, servo, `ros2_control` or hardware gains.

### Invalidated result and correction

- An earlier `N=3` result is invalid. The simplified finger collisions were
  centred near the overall finger bounding boxes rather than the terminal CAD
  pads. Their inner faces left only a `6.7 mm` gap while the rendered terminal
  pads left approximately `39.681 mm`, so Gazebo produced an invisible contact
  and an apparent air grasp. This was a model/test defect, not grasp evidence.
- CAD mesh slices place the zero-position terminal inner faces at `+18.000 mm`
  and `-21.681 mm` in the gripper frame. The corrected `6 x 20 x 20 mm`
  collisions use those faces, and the acceptance test now requires symmetric
  joint contact in a `-14.5 to -11.5 mm` window. For a centred `14 mm` object,
  the geometric estimate is `(39.681 - 14) / 2 = 12.8405 mm` per finger.

### Corrected acceptance test evidence

- One clean headless grasp/lift/hold/return/release run passed (`N=1`) after a
  fresh Gazebo start on 2026-08-12.
- Commanded lift was nominally `50 mm`; measured lift was `0.0500 m`.
- Maximum detected drop during the `5 s` hold was `0.0000 m` at the logged
  precision; lateral displacement during lift was `0.0040 m`.
- Release position error relative to the initial pose was `0.0005 m`.
- Both finger joints stopped at `-0.0128 m`, consistent with the `-0.0128405 m`
  geometric estimate at the displayed `0.1 mm` precision.
- Test thresholds: both contacts in `[-0.0145, -0.0115] m`, left/right contact
  difference at most `0.001 m`, lift at least `0.040 m`, lateral motion at most
  `0.010 m`, hold drop at most `0.005 m`, object retained at least `0.035 m`
  above start, and release error at most `0.015 m`.

This is a functional simulation check, not statistical reliability evidence or
validation of force, compliance, breakage risk, real insertion or the previous
team's reported 49/50 hardware trials.

# System Architecture

## 2026 S2 target

```text
Task executive
    |-- perception and workstation localisation
    |-- MoveIt 2 motion planning
    |-- safety and fault supervisor
    `-- gripper state machine
             |
Fixed base + UFactory xArm 850 + inherited gripper
```

The semester target is an integrated manipulation subsystem, not merely arm motion or raw gripper open/close commands.

## 2027 S1 extension

```text
Task executive
    |-- navigation and docking
    |-- perception and relocalisation
    |-- motion planning
    |-- safety and fault supervisor
    `-- manipulation
             |
Mobile base + arm + gripper + sensors
```

Navigation states should be inserted around the 2026 manipulation sequence without rewriting the manipulation subsystem.

## Description composition

```text
vendor arm description
        +
custom gripper description
        +
top-level mounting Xacro
        =
combined robot description
```

The future mobile-base description is another module joined through an `arm_mount` transform. Internal rack-and-pinion contact mechanics may be simplified to two coupled prismatic finger joints at robot level.

For the current project arm, `vendor arm description` means a pinned, verified
xArm 850 description supplied or published by UFactory. The inherited UR3e
baseline remains isolated on the `ur3e` branch and is reference evidence only.

## Provisional frame chain

```text
map -> odom -> base_link -> arm_mount -> arm_base -> ... -> tool0
    -> gripper_mount -> gripper_base -> gripper_tcp -> cuvette
```

Camera, source workstation, destination workstation, pre-grasp, grasp and insertion frames will be added when the sensor arrangement and laboratory workflow are confirmed.

## Interface boundaries to define

- Arm: vendor ROS 2 driver, controller interfaces, safety state and MoveIt compatibility.
- Gripper: action/state interface, calibration, object-present result, timeout and fault codes.
- Perception: timestamped target/workstation pose plus confidence and failure reason.
- Mobile base: odometry, command velocity/navigation action, docking result, battery and emergency state.
- Task executive: explicit transitions, retries, recovery and safe-state behaviour.

## Planned perception and shared-workspace extension (2026-09-11)

This is the D-012 roadmap architecture, not an implemented subsystem:

```text
RGB images -> fiducial pose -> calibrated workstation/slot targets -> task validity gate
Depth + joint states + calibrated TF -> observed/unknown occupancy -> scene updater
                                      |                          -> motion planner
                                      `-> stop supervisor -> command inhibit + verified stop interface
Controller feedback + sensor/TF freshness -> stop confirmation / fault latch
Independent hardware protection and emergency-stop chain -> validated hardware interfaces
```

The task executive consumes target validity, calibration version, timestamps and object/slot identity; a pose topic update does not start motion. The scene includes measured static instruments, articulated lid state and a tube attached only after grasp verification. Dynamic occupancy has timestamps and uncertainty; missing observations do not establish free space.

Phase 4a stops on entry into its monitored volume. Phase 4b may react in a separately validated outer zone while retaining mandatory inner stop boundaries. Planning and Servo must have one command owner at a time; stop inhibition has priority. Sensor failure, stale TF, expired scene data, planning deadline violation or missing stop confirmation must transition to a defined fault/stop state. Physical protection remains distinct from the software supervisor.

The proposed camera-to-waypoint transform, contact-task restrictions, sensor comparison and test gates are specified in the [roadmap chapter](technical_roadmap/shared_workspace_perception.tex). Compatibility with the pinned D-007 stack must be verified before selecting new planner plugins.

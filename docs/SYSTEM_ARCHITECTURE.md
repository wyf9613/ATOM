# System Architecture

## 2026 S2 target

```text
Task executive
    |-- perception and workstation localisation
    |-- MoveIt 2 motion planning
    |-- safety and fault supervisor
    `-- gripper state machine
             |
Fixed base + commercial arm + inherited gripper
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


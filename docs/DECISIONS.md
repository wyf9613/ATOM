# Decision Log

## D-001 - Preserve raw handover assets

- Date: 2026-08-09
- Status: Accepted
- Decision: Keep the received context file, PDF and F3Z at their current paths and unchanged during repository initialization.
- Reason: Maintain provenance and avoid breaking the existing Obsidian workspace before the team agrees on migration.

## D-002 - Use modular robot descriptions

- Date: 2026-08-09
- Status: Accepted
- Decision: Compose vendor arm, custom gripper and future mobile base through top-level Xacro mounting transforms.
- Reason: Allows hardware substitution and mobile-base integration without rebuilding a monolithic model.

## D-003 - Establish the deterministic baseline first

- Date: 2026-08-09
- Status: Accepted
- Decision: Prioritise URDF/Xacro, TF, MoveIt 2, perception-guided pose updates and explicit state machines before learned control.
- Reason: These address the measured integration gaps and provide a reproducible comparison baseline.

## D-004 - Defer platform-specific ROS scaffolding

- Date: 2026-08-09
- Status: Accepted
- Decision: Create the ROS 2 workspace but no vendor/distro-specific packages until the arm and ROS 2 distribution are confirmed.
- Reason: Avoid committing to incompatible drivers, package formats or dependencies.

## D-005 - Track binary engineering assets with Git LFS

- Date: 2026-08-09
- Status: Accepted
- Decision: Use Git LFS for Fusion archives/models, neutral CAD meshes and PDFs.
- Reason: These binary files do not benefit from normal Git deltas and are expected to grow.

## D-006 - Use the delivered UFactory xArm 850 as the Project ATOM arm

- Date: 2026-08-29
- Status: Accepted
- Decision: Use the UFactory xArm 850 that has arrived for the Project ATOM manipulation platform. Keep the inherited UR3e simulation baseline on the dedicated `ur3e` branch; do not carry its arm-specific description, controllers or MoveIt configuration into the xArm baseline.
- Evidence: The project team reported physical arrival of the xArm 850 on 2026-08-29.
- Boundary: Arrival confirms the arm family/model for project work, but does not yet confirm the controller variant, serial-number-specific calibration, firmware, supplied end-effector interface, payload configuration, network settings, ROS 2 compatibility or safety integration. Record those from labels, supplied documents and repeatable commissioning tests before selecting a driver or MoveIt configuration.
- Effect on D-004: The arm-selection portion is resolved. Ubuntu, ROS 2 distribution, vendor driver and MoveIt configuration remain deferred until compatibility and hardware evidence are recorded.

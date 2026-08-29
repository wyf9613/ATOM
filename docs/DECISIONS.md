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

## D-007 - Use an Ubuntu 24.04 / ROS 2 Jazzy Docker baseline for xArm 850

- Date: 2026-08-29
- Status: Accepted for development and simulation baseline
- Decision: Use one Docker baseline based on Ubuntu 24.04 Noble, ROS 2 Jazzy, Gazebo Harmonic, `gz_ros2_control` and MoveIt 2. Use UFactory's official `xarm_ros2` `jazzy` branch for the six-axis `uf850` model and pin repository commit `3dc2b5e8294758d96b54b15fa5920d581b7cbb3d` plus its SDK submodule commit `d84a2b7d533ff988bf1c2197ed50dd0d6723cf30`.
- Evidence: UFactory lists Ubuntu 24.04 + ROS 2 Jazzy as a developed/tested environment and provides `uf850` description, Gazebo, `ros2_control`, MoveIt fake/simulation and real-arm launch files. ROS 2 Jazzy supports Ubuntu 24.04, and Gazebo documents Harmonic as the recommended Jazzy pairing.
- Boundary: The Docker definition and dependency pin have not yet been built or dynamically tested in this repository. This decision does not validate the delivered controller firmware, network configuration, serial-number calibration, payload/TCP, custom gripper mount or any hardware motion.
- Supersedes: D-004 for Ubuntu/ROS selection. The prior Ubuntu 22.04 / ROS 2 Humble compatibility route remains only in the UR3e branch and is not part of the xArm 850 baseline.

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
- Effect on D-004: The arm-selection portion is resolved. D-007 selects the development and simulation software baseline; serial-number-specific hardware parameters and real-arm compatibility remain deferred until commissioning evidence is recorded.

## D-007 - Use an Ubuntu 24.04 / ROS 2 Jazzy Docker baseline for xArm 850

- Date: 2026-08-29
- Status: Accepted for development and simulation baseline
- Decision: Use one Docker baseline based on Ubuntu 24.04 Noble, ROS 2 Jazzy, Gazebo Harmonic, `gz_ros2_control` and MoveIt 2. Use UFactory's official `xarm_ros2` `jazzy` branch for the six-axis `uf850` model and pin repository commit `3dc2b5e8294758d96b54b15fa5920d581b7cbb3d` plus its SDK submodule commit `d84a2b7d533ff988bf1c2197ed50dd0d6723cf30`.
- Evidence: UFactory lists Ubuntu 24.04 + ROS 2 Jazzy as a developed/tested environment and provides `uf850` description, Gazebo, `ros2_control`, MoveIt fake/simulation and real-arm launch files. ROS 2 Jazzy supports Ubuntu 24.04, and Gazebo documents Harmonic as the recommended Jazzy pairing.
- Verification: On 2026-08-29, the ROS base image was pinned at digest `sha256:2589a8fba5257307857890173c069852c2abf913a0be7970f172478baecb09e4`. All eight vendor baseline packages and `atom_xarm_sim` compiled; the six-axis `uf850` Xacro passed `check_urdf`; and two consecutive server-only runs after fixing a controller-readiness race each verified six joint states, TF `world -> link_eef`, both active controllers, a six-point MoveIt plan, and a commanded 0.05 rad joint-1 offset and return over 2 s per leg. Maximum reported simulated final-joint error across those two runs was 0.000050 rad against a 0.02 rad test tolerance. Resolved key packages were `gz_ros2_control` 1.2.19, MoveIt 2.12.4, `ros_gz` 1.0.22 and `ros2_controllers` 4.40.1.
- Boundary: These are two deterministic simulation runs, not physical accuracy measurements; broader repeatability testing and host graphical operation remain pending. MoveIt reports that no 3D occupancy-map sensor plugin is configured, as expected for the current arm-only baseline. This decision does not validate the delivered controller firmware, network configuration, serial-number calibration, payload/TCP, custom gripper mount or any hardware motion.
- Supersedes: D-004 for Ubuntu/ROS selection. The prior Ubuntu 22.04 / ROS 2 Humble compatibility route remains only in the UR3e branch and is not part of the xArm 850 baseline.

## D-008 - Migrate the robot-independent gripper model and compose it above the vendor arm

- Date: 2026-08-29
- Status: Accepted for description and simulation development
- Decision: Migrate only the generic `atom_gripper_description` Xacro, derived visual meshes, CAD extraction tooling and traceability checks from the UR3e branch. Keep UR3e wrappers, controllers, MoveIt configuration and Fortress worlds on that branch. Compose the gripper with the official `uf850` model in a separate `atom_xarm_description` package attached at `link_eef`.
- Evidence: The migrated model retains derived meshes tied to source STEP SHA-256 `8ee4fd1c064210eab24cb10ba67623e497cab0866adbca86d5be9a0c63aaf351`. On 2026-08-29, both new packages built in the Jazzy container; the standalone and combined descriptions passed five pytest checks with no errors or failures; the combined tree passed `check_urdf`; and the existing arm-only MoveIt/Gazebo smoke test still passed.
- Boundary: The default mount (`xyz=0 0 0` m, `rpy=0 0 0` rad), 0.58 kg mass distribution, finger limits, collision primitives and TCP are provisional simulation inputs, not measurements. The dynamic smoke test remains arm-only. Gripper `ros2_control`, combined SRDF/collision validation, Gazebo actuation and physical commissioning are not demonstrated.
- Reinforces: D-002 modular-description boundary.

## D-009 - Keep a separately testable bare-arm trajectory baseline

- Date: 2026-09-03
- Status: Accepted for simulation development
- Decision: Maintain a headless `uf850` simulation path that loads exactly the six vendor arm joints, with all gripper options disabled. Its acceptance test must ask MoveIt to plan and execute a conservative joint-space offset and return through the simulated `uf850_traj_controller`. Gripper dynamics, SRDF and control are a separate integration step.
- Reason: A small deterministic arm-only baseline isolates vendor-arm planning/control faults from custom end-effector integration and provides a clean regression point for the two work streams.
- Verification: On branch `feature/uf850-arm-only-trajectory-sim`, two independent Docker launches on 2026-09-03 each observed exactly `joint1` through `joint6`, active joint-state and trajectory controllers, and successful MoveIt plan-and-execute results for a 0.10 rad four-joint offset followed by return. The two runs produced 9/9 and 9/8 planned/executed points per leg. Maximum simulated final-joint error was 0.009432 rad against a 0.02 rad acceptance tolerance.
- Boundary: This verifies deterministic command flow in the generic vendor simulation only. It does not establish physical trajectory accuracy, collision clearance, calibrated inertial/TCP data, controller/firmware compatibility, fault handling or any safety property.
- Reinforces: D-002 and D-003.

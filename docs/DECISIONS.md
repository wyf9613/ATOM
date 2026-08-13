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

## D-006 - Use ROS 2 Jazzy and Gazebo Harmonic for the inherited-asset simulation baseline

- Date: 2026-08-12
- Status: Accepted for simulation baseline only
- Decision: Use Ubuntu 24.04, ROS 2 Jazzy and Gazebo Harmonic (Gazebo Sim 8) for the reproducible inherited-asset verification environment.
- Evidence: The development machine runs Ubuntu 24.04.3 and has ROS 2 Jazzy desktop, `ros_gz` 1.0.22 and Gazebo Sim 8.11.0 installed. ROS 2 Jazzy is the ROS release targeting Ubuntu 24.04, and its `ros_gz` vendor packages provide Gazebo Harmonic.
- Boundary: This does not select the deployment computer, a real-arm driver, or the final project ROS distribution. Revisit after the purchased arm, controller and mobile-base support matrix are confirmed.

## D-007 - Use official Universal Robots packages for the UR3e verification model

- Date: 2026-08-12
- Status: Accepted for inherited-asset verification only
- Decision: Use the official Universal Robots ROS 2 description and Gazebo simulation repositories, pinned in `ros2_ws/atom_sim.repos`, with `ur_type:=ur3e`. Keep the custom gripper in a separate package and compose it through a top-level Xacro.
- Evidence: The previous-team report identifies the university test platform as a UR3e. Universal Robots publishes `Universal_Robots_ROS2_Description` and `Universal_Robots_ROS2_GZ_Simulation`, both with Jazzy-compatible releases and UR3e support.
- Boundary: UR3e is a reference platform for reproducing the inherited experiment, not a claim about the arm purchased for Project ATOM.

## D-008 - Separate the UR flange, gripper mount and provisional CAD datum

- Date: 2026-08-12
- Status: Accepted for simulation baseline only
- Decision: Attach an explicit `gripper_mount` frame to the official UR description's `flange` frame, applying the upstream `flange`-to-`tool0` axis alignment so the gripper points forward along the wrist. Place the inherited gripper visual model using the geometric centre of the two case rear faces as a reproducible provisional CAD datum.
- Evidence: The upstream UR Xacro identifies `flange` as the end-effector attachment point and `tool0` as the all-zeros tool frame, with a fixed 90-degree-axis rotation between them. The previous-team report identifies URT-1 as the servo driver, so its component centre is not a mechanical mounting reference.
- Boundary: The case datum is not evidence of the physical quick-disconnect pose. Replace the provisional transform and TCP with measured values, units, method and uncertainty before using the model for clearance, planning or hardware deployment.

## D-009 - Add a parameter-explicit rigid-contact grasp baseline

- Date: 2026-08-12
- Status: Accepted for simulation baseline only
- Decision: Add a separate gravity-enabled Gazebo scenario with a rigid cuvette, simplified terminal finger-pad collisions and an automated grasp/lift/hold/return/release acceptance test. Preserve the zero-gravity resource and motion smoke test as a separate scenario.
- Evidence: The inherited report specifies a 14 x 14 mm cuvette cross-section, Silicone 20A pads, a mean friction coefficient of 0.88 from 10 inclined-plane trials and a 20 mm contact height used in its pressure analysis. The CAD confirms symmetric parallel-jaw motion but does not establish physical limits.
- Boundary: The 45 mm height, 10 g mass, rigid contact, single-side 20 mm joint travel and controller gains are provisional. A pass is software evidence only and does not establish grip force, material stress, hardware reliability or real instrument compatibility.

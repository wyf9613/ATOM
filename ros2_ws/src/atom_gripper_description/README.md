# ATOM gripper description

This package contains the robot-independent portion of the inherited ATOM
gripper model. It was migrated from the verified UR3e branch without its
UR-specific wrapper, controller configuration, MoveIt package or Gazebo worlds.

The visual meshes were derived from the read-only handover STEP assembly and
retain its component placements. Collision geometry is deliberately simplified.
The following remain provisional simulation inputs pending physical inspection
and repeatable measurement:

- 0.58 kg total mass and its 0.48/0.05/0.05 kg distribution;
- -15 to +5 mm joint limits and 0.03 m/s velocity limit;
- finger axes and terminal-pad collision placement;
- TCP at `xyz=-0.0018 0 0.170536` m from `gripper_base`;
- friction coefficient 0.88 from the previous team's ten inclined-plane trials.

The reusable macro is `urdf/atom_gripper.urdf.xacro`. It accepts a parent link,
an optional name prefix, an optional mimic-joint mode and a caller-provided
mounting origin. `urdf/atom_gripper_standalone.urdf.xacro` exists only for
description validation.

`urdf/atom_gripper_v2.urdf.xacro` composes that gripper with the new flange,
camera bracket and ESP32 bracket. The full base/finger visual-mesh AABBs replace
the old short base and pad-only collision boxes, with 0.5 mm per-side padding
(an unvalidated modelling margin). New bracket/adapter inertials are omitted
until measured; this is a kinematic collision-review model, not a dynamics model.
Camera, PCB, screws, wiring and carried objects are not included in the archive
or this model. See `docs/GRIPPER_MOUNT_V2_INTEGRATION.md` in the repository.

Regenerate the visual meshes from the source STEP with:

```bash
python3 -m venv /tmp/atom-cad-env
/tmp/atom-cad-env/bin/pip install -r \
  ros2_ws/src/atom_gripper_description/tools/requirements-cad.txt
/tmp/atom-cad-env/bin/python \
  ros2_ws/src/atom_gripper_description/scripts/extract_step_meshes.py \
  "hardware/end effector/End Effector Assembly V3.step" \
  ros2_ws/src/atom_gripper_description/meshes/generated
```

Do not treat the derived meshes or provisional inertial/TCP values as physical
measurements.

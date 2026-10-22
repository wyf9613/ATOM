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
- finger axes and full visual-envelope collision placement;
- TCP at `xyz=-0.0018 0 0.170536` m from `gripper_base`;
- friction coefficient 0.88 from the previous team's ten inclined-plane trials.

The reusable macro is `urdf/atom_gripper.urdf.xacro`. It accepts a parent link,
an optional name prefix, an optional mimic-joint mode and a caller-provided
mounting origin. `urdf/atom_gripper_standalone.urdf.xacro` exists only for
description validation.

`urdf/atom_gripper_v2.urdf.xacro` composes the inherited gripper with flange V2,
ESP32 bracket V1 and camera bracket V3. The name v2 refers to the flange interface.
`meshes/generated/mount/` contains derived CAD-frame meshes; canonical STEP and
print STL are together in `hardware/end effector/` with parameters and provenance.
Run `scripts/import_mount_v2.py` from the source checkout to regenerate the mount
meshes/Xacro from that folder's manifest.

Full visual-mesh AABBs cover the body, fingers and brackets with 0.5 mm per-side
padding (an unvalidated modelling margin). A nominal D435i housing box is included;
no calibrated camera/optical TF is published. Bracket/camera inertials are omitted
until measured; this is a kinematic review model, not a dynamics model. PCB,
fasteners, cables and carried objects are absent. Tool-internal box exclusions
remain and do not validate internal mechanics. See
`docs/GRIPPER_MOUNT_V2_INTEGRATION.md` for the checks and deployment boundaries.

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

# ATOM xArm description

This package is the top-level composition layer for the official six-axis
UFactory 850 model and the robot-independent ATOM gripper model. It includes
both upstream macros and does not copy or modify the vendor arm description.

The current mounting transform is explicitly provisional:

```text
parent: link_eef
xyz:    0 0 0 m
rpy:    0 0 0 rad
```

It expresses only a neutral frame alignment for description testing. It is not
a measured adapter, quick-disconnect or TCP calibration. Override
`gripper_mount_xyz` and `gripper_mount_rpy` only for named simulation
experiments, and replace their defaults after physical measurement is recorded.

Expand and validate the model after building the workspace:

```bash
xacro $(ros2 pkg prefix atom_xarm_description)/share/atom_xarm_description/urdf/uf850_atom.urdf.xacro \
  > /tmp/uf850_atom.urdf
check_urdf /tmp/uf850_atom.urdf
```

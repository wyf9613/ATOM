# ATOM xArm description

This package is the top-level composition layer for the official six-axis
UFactory 850 model and the robot-independent ATOM gripper model. It includes
both upstream macros and does not copy or modify the vendor arm description.

The composition now includes the CAD v2 flange adapter, camera bracket and
ESP32 bracket recovered from the 2026-10-05 print archive. The flange correction
transform is explicitly provisional:

```text
parent: link_eef
xyz:    0 0 0 m
rpy:    0 0 0 rad
```

`link_eef -> tool_flange` uses this nominal alignment; `tool_flange ->
gripper_mount` adds CAD-derived +0.051964 m along Z. The inherited TCP therefore
lies nominally at [-0.0018, 0, 0.222500] m from the flange. Flange clocking,
hardware fit and TCP remain unmeasured. `gripper_mount_xyz/rpy` now correct the
whole tool flange, including the adapter and brackets, not only the gripper.

Expand and validate the model after building the workspace:

```bash
xacro $(ros2 pkg prefix atom_xarm_description)/share/atom_xarm_description/urdf/uf850_atom.urdf.xacro \
  > /tmp/uf850_atom.urdf
check_urdf /tmp/uf850_atom.urdf
xacro $(ros2 pkg prefix atom_xarm_description)/share/atom_xarm_description/srdf/uf850_atom.srdf.xacro \
  > /tmp/uf850_atom.srdf
```

URDF and SRDF must be supplied together to the same MoveIt instance and the
matching URDF to robot_state_publisher. The existing arm-only/G1 simulation
launcher does **not** load these files. Exporting them does not activate collision
checking on the physical arm. No controller configuration or real-arm launch is
added here; measured TF/payload/TCP, joint feedback, finger-state mapping and
MoveIt collision-state/path acceptance remain required.

The SRDF preserves vendor arm semantics, marks finger joints passive and adds a
tool group. It excludes overlapping tool-internal conservative envelopes and
adapter/link6 mounting contact only. All other tool/arm pairs remain checked.
There is no camera-to-all-arm exemption in this composition. Tool-internal
mechanical interference is outside this coarse envelope model.

See [integration evidence](../../../docs/GRIPPER_MOUNT_V2_INTEGRATION.md).

# ATOM Gripper Description

This package composes the inherited gripper with the official UR3e description
for simulation-baseline verification. It does not identify the arm purchased by
Project ATOM.

The generated STL files preserve the STEP assembly placements for visualisation.
Collision geometry is intentionally simplified. Finger axes, 20 mm total
travel window, mass distribution, flange transform and TCP are provisional until the
physical system is measured.

The combined model attaches the explicit `gripper_mount` frame to the upstream
UR `flange` frame and applies the upstream `flange`-to-`tool0` axis alignment so
the gripper tool axis points forward along the wrist. For visualisation,
`gripper_base` is placed at the geometric centre of the inherited CAD case rear
faces. This is a reproducible CAD datum, not a measured quick-disconnect
transform.

Gravity is disabled in `atom_empty.sdf`; that world checks model resources, TF,
joint commands and feedback. `atom_grasp.sdf` enables gravity and adds a
provisional cuvette/contact scenario. Both use Gazebo-native position
controllers and are not trajectory-controller or hardware-controller
validation.

Regenerate the visual meshes from the read-only source STEP with:

```bash
python3 -m venv /tmp/atom-cad-env
/tmp/atom-cad-env/bin/pip install -r \
  ros2_ws/src/atom_gripper_description/tools/requirements-cad.txt
/tmp/atom-cad-env/bin/python \
  ros2_ws/src/atom_gripper_description/scripts/extract_step_meshes.py \
  "hardware/end effector/End Effector Assembly V3.step" \
  ros2_ws/src/atom_gripper_description/meshes/generated
```

After importing the pinned upstream repositories and building the workspace:

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 launch atom_gripper_description sim.launch.py
```

The same launch entry points support the repository's Dockerized ROS 2 Humble /
Gazebo Fortress baseline. On Humble they automatically select the
`*_fortress.sdf` worlds, the Humble-compatible UR Xacro invocation and
`ignition.msgs` bridge type names. Do not launch the Fortress world variants
directly on Jazzy/Harmonic.

In another sourced terminal, run the deterministic motion smoke test:

```bash
ros2 run atom_gripper_description demo_motion.py
```

Run the gravity/contact scenario and its automatic acceptance test with:

```bash
ros2 launch atom_gripper_description grasp.launch.py run_test:=true
```

To inspect the scene before triggering the test manually, omit `run_test:=true`,
keep the launch terminal running, and then use a second sourced terminal:

```bash
ros2 run atom_gripper_description grasp_lift_test.py
```

Do not use `sim.launch.py` for this test; its default `atom_empty.sdf` world has
no cuvette. Run only one Gazebo launch at a time.

The test opens and closes both fingers, lifts the object nominally 50 mm, holds
for 5 s, returns and releases. It requires both fingers to stop symmetrically in
the CAD-derived -14.5 to -11.5 mm contact window. It also fails if the lift is
below 40 mm, lateral motion exceeds 10 mm, hold drop exceeds 5 mm, or release
error exceeds 15 mm.
During the 5 s loaded hold it also requires the largest six-axis position error
to remain below 0.020 rad and the largest within-hold drift below 0.005 rad.
The six arm-controller output caps are read from the official UR3e joint-limit
file (54/54/28/9/9/9 N.m).
The 14 x 14 x 45 mm geometry, 10 g mass, 20 mm pad collision height and native
PID gains are simulation inputs pending physical measurement. The reported
gripper mass is fixed at the previous report's 0.58 kg estimate. The reported
friction coefficient of 0.88 came from 10 previous-team inclined-plane trials;
it is not a calibrated Gazebo contact model or proof of grip force.

The finger joint zero is the inherited CAD assembly pose, where the visible pad
gap is approximately 39.681 mm. Closing therefore uses negative joint values;
the provisional limits are -15 to +5 mm. Simplified terminal-pad collisions are
aligned to CAD mesh slices rather than to the overall finger bounding boxes.

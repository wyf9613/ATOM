# Ubuntu 24.04 / ROS 2 Jazzy xArm 850 container

This is the single Project ATOM software baseline for the delivered UFactory
xArm 850. It follows UFactory's official `jazzy` branch and uses the ROS 2 Jazzy
pairing with Gazebo Harmonic.

Primary references:

- [UFactory `xarm_ros2` repository](https://github.com/xArm-Developer/xarm_ros2/tree/jazzy)
- [UFactory ROS 2 instructions](https://github.com/xArm-Developer/xarm_ros2/blob/jazzy/ReadMe.md)
- [ROS 2 Jazzy Ubuntu installation support](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
- [Gazebo/ROS compatibility matrix](https://gazebosim.org/docs/harmonic/ros_installation/)

## Pinned baseline

| Component | Selection |
|---|---|
| Ubuntu | 24.04 Noble |
| ROS 2 | Jazzy |
| Gazebo | Harmonic through Jazzy vendor packages |
| Simulation control | `gz_ros2_control` |
| Motion planning | MoveIt 2 |
| Arm model name | `uf850`, six joints |
| Vendor repository | `xArm-Developer/xarm_ros2` |
| Vendor commit | `3dc2b5e8294758d96b54b15fa5920d581b7cbb3d` |
| SDK submodule commit | `d84a2b7d533ff988bf1c2197ed50dd0d6723cf30` |
| ROS base image digest | `sha256:2589a8fba5257307857890173c069852c2abf913a0be7970f172478baecb09e4` |

The vendor repository provides the official `xarm_description`,
`xarm_controller`, `xarm_gazebo`, `xarm_moveit_config`, `xarm_api` and related
packages. The image deliberately resolves and builds only the eight core
packages needed for the `uf850` description, real/simulated control, Gazebo and
MoveIt. Optional monorepo packages such as joystick, MoveIt Servo and vision
demos are outside this baseline. Do not copy vendor packages into ATOM source
packages.

## Verification on 2026-08-29

- Built eight core vendor packages plus `atom_gripper_description`,
  `atom_xarm_description` and `atom_xarm_sim` (11 packages total).
- Validated the six-axis `uf850` Xacro with `check_urdf`.
- The migrated standalone gripper and modular `uf850` + gripper descriptions
  passed five pytest checks with no failures; the combined
  tree also passed `check_urdf`.
- Two consecutive server-only runs after the controller-readiness fix each
  received all six joint states, resolved TF `world -> link_eef`, confirmed both
  controllers active, planned a six-point MoveIt trajectory, and commanded a
  0.05 rad joint-1 offset and return over 2 s per leg. Maximum reported
  simulated final-joint error across the two runs was 0.000050 rad against a
  0.02 rad test tolerance. These are simulation results, not physical accuracy
  measurements.

The dynamic smoke test still uses the official arm-only MoveIt model. The
combined gripper description is currently description-tested only; gripper
`ros2_control`, SRDF collision semantics and a measured mount transform remain
future work.

Run the two description-package test suites inside `jazzy_shell.sh` with:

```bash
cd /jazzy_ws
colcon test \
  --base-paths /workspace/ros2_ws/src \
  --packages-select atom_gripper_description atom_xarm_description \
  --event-handlers console_direct+
```

## Build

From the repository root:

```bash
./scripts/docker/jazzy_build.sh
```

This builds the Docker image and then the vendor workspace. Generated colcon
files are stored below ignored `.docker-runtime/jazzy_ws/` directories.

## Bare-arm trajectory planning and control

Run the complete MoveIt plan-and-execute simulation, with no gripper loaded:

```bash
./scripts/docker/jazzy_arm_trajectory_sim.sh
```

The demo commands a clearly visible six-joint motion through MoveIt, with a
maximum joint offset of 0.70 rad and 0.05 velocity/acceleration scaling. It
verifies the executed trajectory and final simulated joint error, then plans and
executes a return to the initial state. This is the primary bare-arm trajectory
acceptance path.

To view the same bare-arm motion in Gazebo and RViz from an X11 host session:

```bash
./scripts/docker/jazzy_arm_trajectory_gui.sh
```

The graphical script forwards the current X11 display and authorization into
the container, launches the official UF850 Gazebo/RViz view with all gripper
options disabled, runs the trajectory demo once, and leaves the windows open.
Press `Ctrl+C` in the launching terminal to stop it. Its launch log is stored at
`.docker-runtime/jazzy_ws/log/atom_uf850_arm_trajectory_gui.log`.

In RViz, open the **MotionPlanning** panel and select planning group `uf850`.
Move the interactive end-effector marker (or choose a random valid goal), click
**Plan** to preview the planned motion, and click **Execute** to send that plan
through the ROS 2 trajectory controller to the Gazebo robot. **Plan & Execute**
performs both steps consecutively.

## Headless infrastructure smoke test

From the repository root:

```bash
./scripts/docker/jazzy_sim_smoke.sh
```

The script rebuilds incrementally, launches Gazebo server-only without RViz,
runs the checks described above and shuts the simulation down. Its latest log
is stored at `.docker-runtime/jazzy_ws/log/atom_uf850_headless_smoke.log`.

## Monitored actuator-dynamics simulation

Run the separate torque-driven nominal model with:

```bash
./scripts/docker/jazzy_arm_dynamics_sim.sh
```

This path uses the vendor UF850 rigid-body inertias and effort limits, Gazebo
DART physics, and an ATOM-owned saturated joint-space PD actuator layer. It
writes:

- `.docker-runtime/jazzy_ws/log/atom_uf850_nominal_dynamics_tracking.csv` —
  100 Hz reference, feedback, error and controller output for every joint;
- `.docker-runtime/jazzy_ws/log/atom_uf850_nominal_dynamics_summary.json` —
  per-phase/per-joint RMS and maximum position/velocity errors plus peak
  feedback velocity;
- `.docker-runtime/jazzy_ws/log/atom_uf850_nominal_dynamics.log` — complete
  launch and controller log.

The gains are nominal simulation inputs, not identified xArm 850 servo
parameters. This test can expose controller/model behavior and regression, but
cannot yet predict physical vibration. Real motor current, temperature,
gearbox compliance/backlash and controller delay are not available in this
report and must be collected during supervised hardware commissioning.

The same trajectory monitor also runs in the ideal bare-arm trajectory script,
using the `atom_uf850_trajectory_*` report names.

## Open a shell

```bash
./scripts/docker/jazzy_shell.sh
```

After the workspace has been built, the ATOM headless entry point is:

```bash
ros2 launch atom_xarm_sim uf850_arm_only.launch.py
```

The official graphical simulation entry point is:

```bash
ros2 launch xarm_moveit_config uf850_moveit_gazebo.launch.py
```

The official real-arm MoveIt entry point is shown here for traceability only:

```bash
ros2 launch xarm_moveit_config uf850_moveit_realmove.launch.py \
  robot_ip:=<verified-controller-ip>
```

Do not run the real-arm command until the controller IP, firmware, operating
mode, clearances, payload, TCP, emergency-stop chain and supervised low-speed
commissioning procedure have been verified.

## Custom ATOM gripper boundary

The vendor `add_gripper` option means the UFactory gripper, not the inherited
ATOM gripper. Keep it `false`. Add the ATOM gripper later as a separate package
and compose it at a measured xArm tool/flange transform; do not edit or fork the
vendor arm model for that integration.

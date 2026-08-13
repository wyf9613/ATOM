# ROS 2 Workspace

The deployment stack is still unconfirmed. For inherited-asset verification only,
`docs/DECISIONS.md` records an Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic and UR3e
simulation baseline. This must not be interpreted as the purchased-arm selection.

Official upstream sources are pinned in `atom_sim.repos`. Import them into `src/`
with `vcs import`; do not vendor or modify the Universal Robots model in this
repository.

## Build the verification baseline

```bash
cd ros2_ws
vcs import src < atom_sim.repos
source /opt/ros/jazzy/setup.bash
PATH=/usr/bin:/bin:$PATH colcon build --symlink-install \
  --packages-select ur_description atom_gripper_description \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash
ros2 launch atom_gripper_description sim.launch.py
```

The explicit system-Python selection prevents a user Conda environment from
overriding ROS 2's Python dependencies. Run the deterministic motion check in a
second sourced terminal with:

```bash
ros2 run atom_gripper_description demo_motion.py
```

After those decisions are recorded, create modular packages for:

- gripper description;
- combined robot description;
- MoveIt configuration;
- gripper driver/state machine;
- perception/localisation;
- task control;
- simulation;
- later mobile-base, navigation and docking integration.

Do not copy vendor robot models into this repository when an official, versioned upstream package can be pinned instead.

## Ubuntu 22.04 / ROS 2 Humble compatibility environment

The previous-project and laboratory baseline reported by the supervisor is
Ubuntu 22.04 with ROS 2 Humble. Do not reinstall the workstation solely for that
reason. The repository provides an isolated Humble/Fortress environment:

```bash
cd /home/wuyifan/ATOM
./scripts/docker/humble_build.sh
./scripts/docker/humble_test.sh
```

The Humble UR source is independently pinned in `atom_sim_humble.repos` because
the upstream Humble and Jazzy Xacro interfaces differ. See
`docker/humble/README.md` for Docker installation, GUI and laboratory validation
instructions.

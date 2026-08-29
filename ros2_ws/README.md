# ROS 2 Workspace

The selected development baseline is Docker on Ubuntu 24.04 with ROS 2 Jazzy,
Gazebo Harmonic and UFactory's official `xarm_ros2` stack for `uf850`. The
vendor source is pinned by `atom_xarm_jazzy.repos`; it is imported into the
container workspace rather than copied into this repository.

Create separate ATOM-owned packages for:

- gripper description;
- combined robot description;
- MoveIt configuration;
- gripper driver/state machine;
- perception/localisation;
- task control;
- simulation;
- later mobile-base, navigation and docking integration.

Do not copy vendor robot models into this repository when an official, versioned upstream package can be pinned instead.

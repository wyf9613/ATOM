# ROS 2 Workspace

This workspace is intentionally not buildable yet. The commercial arm is now confirmed as the delivered UFactory xArm 850. The controller/firmware inventory, target Ubuntu version, ROS 2 distribution, vendor driver and MoveIt configuration are still unconfirmed.

After those remaining decisions are recorded, create modular packages for:

- gripper description;
- combined robot description;
- MoveIt configuration;
- gripper driver/state machine;
- perception/localisation;
- task control;
- simulation;
- later mobile-base, navigation and docking integration.

Do not copy vendor robot models into this repository when an official, versioned upstream package can be pinned instead.

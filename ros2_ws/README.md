# ROS 2 Workspace

The selected development baseline is Docker on Ubuntu 24.04 with ROS 2 Jazzy,
Gazebo Harmonic and UFactory's official `xarm_ros2` stack for `uf850`. The
vendor source is pinned by `atom_xarm_jazzy.repos`; it is imported into the
container workspace rather than copied into this repository.

ATOM-owned packages currently present are:

- `atom_gripper_description`: robot-independent inherited gripper Xacro and
  derived visual meshes;
- `atom_xarm_description`: top-level `uf850` plus ATOM gripper composition;
- `atom_xarm_sim`: arm-only Gazebo/MoveIt launch, deterministic smoke check and
  plan-and-execute trajectory demo, plus configurable pick/place target
  publication and a checked lift/constrained-transfer/descent baseline;
- `atom_xarm_dynamics`: ATOM-owned nominal actuator layer and tracking reports.

None of these packages copies or modifies vendor robot-description files. The
combined gripper description is not yet used by the dynamic MoveIt/Gazebo smoke
test; that requires gripper control and collision semantics to be ported first.
The current package layout and run commands are documented in
[`docs/ARM_ONLY_SIMULATION.md`](../docs/ARM_ONLY_SIMULATION.md).

Run the configurable post-grasp transfer regression from the repository root:

```bash
./scripts/docker/jazzy_transfer_sim.sh
```

Its current targets and constraints are stored in
`ros2_ws/src/atom_xarm_sim/config/transfer_targets.yaml`. This remains an arm-only
simulation: it constrains `link_eef`, simulates grasp success and does not attach
a tube in the planning scene.

Create separate ATOM-owned packages for:

- MoveIt configuration;
- gripper driver/state machine;
- perception/localisation;
- task control;
- further simulation scenes and fixtures;
- later mobile-base, navigation and docking integration.

Do not copy vendor robot models into this repository when an official, versioned upstream package can be pinned instead.

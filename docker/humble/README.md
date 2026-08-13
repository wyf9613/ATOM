# Ubuntu 22.04 / ROS 2 Humble experiment container

This container mirrors the confirmed previous-project and laboratory software
baseline without replacing the Ubuntu 24.04 / ROS 2 Jazzy host installation.

## Pinned environment

| Component | Container baseline |
|---|---|
| Ubuntu | 22.04 Jammy |
| ROS 2 | Humble |
| Gazebo | Fortress (Gazebo Sim 6) |
| ROS/Gazebo integration | `ros-humble-ros-gz` |
| Motion-planning tools | MoveIt 2.5.9 with the ATOM verification configuration |
| UR description | official Humble branch commit `18e6f603b3ebc2ec479fecb62d6be544b15755e9` |
| Python | Ubuntu 22.04 system Python 3.10 |

The container is a software compatibility baseline. It does not prove that the
laboratory computer has the same package patch versions, GPU driver, device
permissions, UR controller version or gripper firmware.

## Install Docker on the host

The current workstation did not have Docker installed when this environment was
added. Run once on the Ubuntu host:

```bash
./scripts/docker/install_docker_ubuntu.sh
```

Logging out and back in is preferable to `newgrp` if the group change is not
visible in every terminal. Do not expose the Docker daemon over an unauthenticated
TCP socket. Membership in the `docker` group grants root-equivalent control of
the host; add only trusted users.

## Build the image and workspace

From the repository root:

```bash
./scripts/docker/humble_build.sh
```

The source repository is bind-mounted at `/workspace`. Colcon `build`, `install`
and `log` directories are stored under the ignored host directory
`.docker-runtime/humble_ws/`, so the host Jazzy workspace is not overwritten and
the files remain owned by the invoking user.

## Run the full compatibility check

```bash
./scripts/docker/humble_test.sh
```

This performs:

1. Humble workspace build;
2. Humble Xacro expansion and `check_urdf`;
3. description/world and MoveIt-configuration package tests;
4. a headless Fortress grasp/lift/hold/release regression;
5. one logical and one physical-contact MoveIt grasp/transfer/release task;
6. explicit searches for the structured `RESULT PASS` records.

The first complete workstation run passed on 2026-08-13. This is a regression
gate, not a substitute for repeating the test on the laboratory computer.

## Open a shell

```bash
./scripts/docker/humble_shell.sh
```

Inside the container:

```bash
source /opt/ros/humble/setup.bash
source /humble_ws/install/setup.bash
ros2 launch atom_gripper_description grasp.launch.py \
  headless:=true run_test:=true
```

## Optional GUI

The default Compose file is headless and does not require an X server. On an X11
host, permit the local container user as required by the local display policy,
then run the GUI wrapper:

```bash
./scripts/docker/humble_gui.sh logical
./scripts/docker/humble_gui.sh physical
```

Use `./scripts/docker/humble_gui.sh native` for the original Gazebo-native
controller regression. The MoveIt modes also open the repository RViz
configuration.

Wayland, NVIDIA and remote desktop setups may require host-specific rendering
configuration. Those differences do not block the headless compatibility gate.

## Reset generated files

This removes only ignored container build/install/log output, not source files:

```bash
rm -rf .docker-runtime/humble_ws
```

## Laboratory-computer gate

Before claiming laboratory compatibility, run `humble_test.sh` on the actual
laboratory computer and record:

- `uname -a` and `/etc/os-release`;
- `ros2 doctor --report`;
- `dpkg-query` versions for ROS, Gazebo, UR and MoveIt packages;
- GPU/renderer and USB/serial device access;
- test date, sample count and full log.

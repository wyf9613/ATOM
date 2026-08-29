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

The vendor repository provides the official `xarm_description`,
`xarm_controller`, `xarm_gazebo`, `xarm_moveit_config`, `xarm_api` and related
packages. Do not copy those packages into ATOM source packages.

## Build

From the repository root:

```bash
./scripts/docker/jazzy_build.sh
```

This builds the Docker image and then the vendor workspace. Generated colcon
files are stored below ignored `.docker-runtime/jazzy_ws/` directories.

## Open a shell

```bash
./scripts/docker/jazzy_shell.sh
```

After the workspace has been built, the official simulation entry point is:

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

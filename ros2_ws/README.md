# ROS 2 仿真验证工作区

此工作区已经包含 UR3e + 继承夹爪的仿真验证基线。它用于复现上一组平台和验证软件集成，**不代表采购机械臂或最终部署栈已经确定**。

## 当前环境

- 主机验证：Ubuntu 24.04、ROS 2 Jazzy、Gazebo Harmonic；
- 部署兼容门：Ubuntu 22.04、ROS 2 Humble、Gazebo Fortress Docker；
- 官方 UR 依赖通过 `atom_sim.repos` 和 `atom_sim_humble.repos` 固定；
- 不复制或直接修改厂商机器人模型。

## Jazzy/Harmonic 基线

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

第二个已 source 的终端运行：

```bash
ros2 run atom_gripper_description demo_motion.py
```

显式选择系统 Python 是为了防止 Conda 覆盖 ROS 2 Python 依赖。

## Humble/Fortress 兼容环境

```bash
./scripts/docker/humble_build.sh
./scripts/docker/humble_test.sh
```

MoveIt 双模式抓取的构建与验收命令见 `../docs/MOVEIT_GRASP_BASELINE.md`，Docker GUI 和实验室复现说明见 `../docker/humble/README.md`。

## 软件包职责

- `atom_gripper_description`：夹爪、组合模型、Gazebo 场景和描述测试；
- `atom_ur3e_moveit_config`：独立 MoveIt 验证配置；
- `atom_manipulation`：抓取任务状态机；
- 官方 `ur_description`：通过固定的上游依赖提供 UR3e 模型。

实机前仍需新增或确认夹爪驱动、真实机械臂驱动、感知、仪器技能、导航、底盘接口和安全监督。

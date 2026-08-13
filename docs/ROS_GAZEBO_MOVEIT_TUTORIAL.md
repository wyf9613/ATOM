# Project ATOM：ROS 2、Gazebo、ros2_control 与 MoveIt 2 必要知识教程

> 文档类型：项目学习与实践教程
>
> 目标平台：Ubuntu 24.04、ROS 2 Jazzy、Gazebo Harmonic
>
> 最后更新：2026-08-12
>
> 配套仓库：`/home/wuyifan/ATOM`

## 1. 教程目标

完成本教程后，项目成员应能够：

1. 正确建立、构建和 source ROS 2 workspace；
2. 使用 ROS 2 CLI 检查 node、topic、service、action、parameter 和 QoS；
3. 解释 TF frame、URDF link/joint、visual/collision/inertial 的区别；
4. 阅读并修改模块化 Xacro，而不是从 CAD 导出单体机器人；
5. 解释 Gazebo world、SDF、system plugin、物理步长和接触参数；
6. 使用 `ros_gz_bridge` 判断数据实际在哪个中间件中流动；
7. 理解 `ros2_control` 的硬件接口、Controller Manager 和轨迹控制器；
8. 理解 MoveIt 2 的 RobotModel、SRDF、PlanningScene、规划管线和执行链；
9. 将 MoveIt 生成的轨迹连接到 Gazebo 或真实控制器；
10. 用测试、日志和量化指标区分“画面能动”和“系统能力已验证”。

本教程服务于确定性、基于模型的 manipulation baseline。它不会将学习控制作为起点，
也不会将 Gazebo 成功等同于硬件成功。

## 2. 学习路线总览

推荐按以下依赖顺序学习：

```text
Linux / Git / Python / CMake
            |
            v
ROS 2 graph + workspace + launch
            |
            v
TF2 + 坐标变换 + URDF/Xacro
            |
            v
Gazebo SDF + physics + ros_gz_bridge
            |
            v
ros2_control + trajectory controller
            |
            v
MoveIt RobotModel + PlanningScene + planning
            |
            v
trajectory execution + gripper action
            |
            v
perception + calibration + task state machine
```

如果 TF、关节轴或 collision 还没有理解清楚，不应直接开始调 MoveIt planner。
MoveIt 会使用这些基础模型，错误只会被放大或以更难定位的方式出现。

## 3. 开始前应具备的基础

### 3.1 Linux 和命令行

必须掌握：

- 当前工作目录、绝对路径和相对路径；
- 环境变量、`PATH`、shell 初始化和进程；
- 文件权限和 shebang；
- `apt`、Debian 包和系统库；
- 标准输入、输出、错误流和退出码；
- `ps`、`pgrep`、`kill`、`top` 或 `htop`；
- `rg`、`find`、`sed`、`less`；
- SSH 和基本网络检查。

项目常用命令：

```bash
pwd
which python3
python3 --version
printenv ROS_DISTRO
printenv AMENT_PREFIX_PATH
pgrep -af "ros2|gz sim"
```

### 3.2 Git 和工程资产管理

必须掌握：

- working tree、staging、commit、branch、merge；
- `.gitignore` 与 Git LFS；
- 不修改继承原始输入；
- 固定上游版本，而不是复制 vendor 代码；
- 从 diff 中区分自己的更改和他人的更改。

本项目的 STEP、Fusion 归档和 PDF 应作为原始资产保留。派生网格和文档应有可追溯
的源路径、哈希和生成过程。

### 3.3 Python、C++、XML 和 YAML

ROS 2 原型和 launch 常使用 Python，实时控制器和 MoveIt 主要接口常使用 C++。
至少需要掌握：

- Python class、callback、异常、虚拟环境和模块导入；
- C++ class、RAII、智能指针、模板和 CMake 基础；
- XML 元素、属性和命名空间；
- YAML 字典、列表、缩进和参数文件；
- 浮点数、单位转换和容差比较。

### 3.4 数学和机器人学

必须掌握：

- 向量、矩阵、点积、叉积；
- 旋转矩阵、四元数、roll-pitch-yaw；
- 齐次变换和变换复合；
- 正运动学、逆运动学和 Jacobian 的用途；
- joint space 与 Cartesian space；
- 速度、加速度、力、力矩和惯量；
- PID 的基本行为；
- 摩擦、接触、刚体和柔顺性的区别。

坐标变换建议统一写成：

```text
T_world_object = T_world_robot * T_robot_tool * T_tool_object
```

每次记录 pose 都必须同时写明父 frame、子 frame、单位和时间戳。

## 4. 环境和 workspace

### 4.1 ROS 2 overlay 模型

ROS 2 环境由多个前缀按顺序叠加：

```text
/opt/ros/jazzy              # underlay
        +
/home/wuyifan/ATOM/ros2_ws/install  # project overlay
```

正确顺序：

```bash
source /opt/ros/jazzy/setup.bash
source /home/wuyifan/ATOM/ros2_ws/install/setup.bash
```

后 source 的 overlay 可以覆盖同名资源。调试包找不到或版本不对时检查：

```bash
echo "$AMENT_PREFIX_PATH" | tr ':' '\n'
ros2 pkg prefix atom_gripper_description
ros2 pkg prefix ur_description
```

### 4.2 Conda 与 ROS 2 Python ABI

ROS 2 Jazzy 的 Ubuntu 二进制包使用系统 Python 3.12。若 Conda 的 Python 3.13
覆盖系统解释器，纯 Python 模块可能被找到，但 `rclpy` 的二进制扩展无法加载。

错误示例：

```text
ModuleNotFoundError: No module named 'rclpy._rclpy_pybind11'
```

检查：

```bash
which python3
python3 --version
/usr/bin/python3 --version
python3 -c "import sys; print(sys.executable); print(sys.path)"
```

原则：

- ROS 节点使用与发行版匹配的系统 Python；
- CAD 转换等非 ROS 工具使用独立 venv；
- 不要重命名 `.so` 文件伪造 ABI 兼容；
- 不要在 `.bashrc` 中无条件 source 多个 ROS 发行版和 workspace。

### 4.3 colcon workspace 结构

```text
ros2_ws/
|-- src/       # 源包
|-- build/     # 每个包的构建中间文件
|-- install/   # 可 source 的安装空间
`-- log/       # 构建和测试日志
```

标准构建：

```bash
cd /home/wuyifan/ATOM/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
PATH=/usr/bin:/bin:$PATH colcon build --symlink-install \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash
```

`--symlink-install` 使 Python、launch 和配置文件的开发迭代更快，但 CMake 安装规则
仍然决定文件是否出现在 install space。

### 4.4 实验 0：确认环境

```bash
cd /home/wuyifan/ATOM
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
printenv ROS_DISTRO
ros2 pkg executables atom_gripper_description
gz sim --versions
```

完成标准：

- `ROS_DISTRO` 为 `jazzy`；
- 能看到 `demo_motion.py` 和 `grasp_lift_test.py`；
- Gazebo 主版本为 8；
- `ros2 pkg prefix atom_gripper_description` 指向本项目 install space。

## 5. ROS 2 核心概念

### 5.1 ROS graph

ROS graph 是运行时 node 和接口的网络。ROS 2 不是一个单独进程，也不是实时操作
系统。它提供通信、发现、参数、日志、launch 和工具生态。

最重要的实体：

| 实体 | 作用 | ATOM 示例 |
|---|---|---|
| Node | 单一职责的运行组件 | `robot_state_publisher` |
| Topic | 异步连续数据流 | `/joint_states` |
| Service | 短时请求/响应 | 生成或查询实体 |
| Action | 可取消的长任务，带反馈和结果 | 未来抓取或轨迹执行 |
| Parameter | node 的运行配置 | `use_sim_time` |
| TF | 带时间的 frame 关系 | `flange -> gripper_mount` |

官方接口建议是：连续数据用 topic，短时查询用 service，长时间且需要反馈/取消的任务
用 action。

### 5.2 Node

检查运行 node：

```bash
ros2 node list
ros2 node info /robot_state_publisher
ros2 node info /atom_grasp_lift_test
```

一个 node 应有明确职责。不要把感知、规划、驱动和任务逻辑全部放在同一个 node。

### 5.3 Topic

Topic 是异步 publish/subscribe 数据流。发布者通常不知道订阅者是谁。

```bash
ros2 topic list -t
ros2 topic info /joint_states --verbose
ros2 topic echo /joint_states --once
ros2 topic hz /joint_states
ros2 interface show sensor_msgs/msg/JointState
```

ATOM 当前的 `/joint_states` 是从 Gazebo bridge 得到的关节反馈。

### 5.4 Service

Service 用于快速、有限时长的请求/响应，不适合持续运动命令。

```bash
ros2 service list -t
ros2 service type /some_service
ros2 interface show example_interfaces/srv/AddTwoInts
```

不要用 service 表示需要数秒完成、需要反馈或需要取消的机械臂任务。

### 5.5 Action

Action 包含 goal、feedback、result 和 cancel 语义。适用于：

- 执行关节轨迹；
- 夹爪 open/close；
- 导航到目标；
- 完成一段可取消的 manipulation 子任务。

```bash
ros2 action list -t
ros2 action info /joint_trajectory_controller/follow_joint_trajectory
ros2 interface show control_msgs/action/FollowJointTrajectory
```

ATOM 当前尚未提供这些 action。直接发布 `Float64` 只能算临时仿真命令接口。

### 5.6 Parameter

Parameter 是 node 运行时配置，不是高频控制流。

```bash
ros2 param list /robot_state_publisher
ros2 param get /robot_state_publisher use_sim_time
ros2 param dump /robot_state_publisher
```

机器人描述通常通过 `robot_description` 参数提供。MoveIt 的语义描述通常使用
`robot_description_semantic`。

### 5.7 QoS

QoS 决定通信的可靠性、历史深度、持久性和时限行为。需要理解：

- reliability：reliable 或 best effort；
- durability：volatile 或 transient local；
- history/depth：保留多少条消息；
- deadline、lifespan 和 liveliness。

常见现象：topic 名和类型都相同，但 QoS 不兼容，订阅者仍收不到消息。检查：

```bash
ros2 topic info /joint_states --verbose
```

### 5.8 仿真时间

Gazebo 发布 `/clock`，仿真 node 设置 `use_sim_time:=true` 后使用仿真时间。暂停、
加速或减速仿真时，ROS 时间会跟随仿真，而 wall clock 不会。

当前测试脚本使用 `time.monotonic()` 控制脚本阶段，而 pose 来自 Gazebo。进行严格
仿真时间测试时，应明确选择 ROS time 或 wall time，不能混用后再作时间性能结论。

### 5.9 实验 1：检查当前 ROS graph

终端 A：

```bash
cd /home/wuyifan/ATOM
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 launch atom_gripper_description grasp.launch.py
```

终端 B：

```bash
source /opt/ros/jazzy/setup.bash
source /home/wuyifan/ATOM/ros2_ws/install/setup.bash
ros2 node list
ros2 topic list -t
ros2 topic echo /joint_states --once
ros2 topic echo /cuvette/pose --once
ros2 topic info /cuvette/pose --verbose
```

完成标准：能够指出每个 topic 的发布者、订阅者、消息类型、方向和物理含义。

## 6. ROS 2 package、ament 和 launch

### 6.1 `package.xml`

`package.xml` 描述包名、版本、许可证和依赖。依赖应按真实使用声明，不能依靠开发
机器碰巧已经安装。

ATOM description 包的主要运行依赖包括：

- `robot_state_publisher`；
- `rclpy`；
- `ros_gz_bridge`；
- `ros_gz_sim`；
- `sensor_msgs`、`std_msgs`、`tf2_msgs`；
- `ur_description`；
- `xacro`。

### 6.2 `CMakeLists.txt`

该文件负责安装 launch、mesh、URDF、world 和 Python 可执行脚本，并注册 pytest。
修改源码但 install space 没变化时，应检查安装规则和是否重新构建。

### 6.3 Launch

Launch 用于同时启动 Gazebo、bridge、robot state publisher 和模型生成器。需要掌握：

- `DeclareLaunchArgument`；
- `LaunchConfiguration`；
- `IncludeLaunchDescription`；
- `Node`；
- condition 和 timer；
- 参数、remapping 和环境变量。

查看参数：

```bash
ros2 launch atom_gripper_description sim.launch.py --show-args
ros2 launch atom_gripper_description grasp.launch.py --show-args
```

### 6.4 实验 2：理解 launch 展开

阅读：

```text
ros2_ws/src/atom_gripper_description/launch/sim.launch.py
ros2_ws/src/atom_gripper_description/launch/grasp.launch.py
```

回答：

1. 为什么 `grasp.launch.py` include `sim.launch.py`；
2. 为什么 `/cuvette/pose` 只在 `atom_grasp.sdf` 中桥接；
3. `headless` 如何改变 Gazebo 参数；
4. 自动测试为什么延时 `10 s`；
5. `GZ_SIM_RESOURCE_PATH` 为什么需要包含包 share 的父目录。

## 7. rclpy 节点编程

### 7.1 最小结构

```python
#!/usr/bin/python3

import rclpy
from rclpy.node import Node


class ExampleNode(Node):
    def __init__(self):
        super().__init__("example_node")


def main():
    rclpy.init()
    node = ExampleNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
```

理解构造器、publisher、subscription、timer、callback、executor 和 shutdown。

### 7.2 callback 和状态

当前抓取测试订阅 `/joint_states` 和 `/cuvette/pose`，callback 更新内部状态，主流程
通过 `spin_once()` 让 callback 得到执行机会。

需要避免：

- 在 callback 内长时间阻塞；
- 没有检查消息时间戳就混合不同时间的数据；
- 无边界增长的历史数组；
- 在多个 callback 中无保护地修改共享状态；
- 捕获不到异常时仍返回成功码。

### 7.3 退出码和日志

自动化脚本应使用：

- `0`：通过；
- 非零：失败或环境缺失；
- `INFO`：阶段和指标；
- `WARN`：可继续但证据不足；
- `ERROR`：不能完成任务。

### 7.4 实验 3：阅读测试节点

阅读 `scripts/grasp_lift_test.py`，画出状态变化：

```text
wait -> settle -> close -> lift -> hold -> return/release -> evaluate
```

回答：

1. 为什么仅检测试管抬高不足以证明真实接触；
2. 为什么要检查两个夹指的接触位置和对称性；
3. 为什么旧碰撞模型可以产生假通过；
4. 哪些阈值是场景验收条件，哪些是硬件要求；
5. 如何让超时、取消和失败恢复成为明确状态。

## 8. TF2 与坐标系

### 8.1 frame 是什么

Frame 是一个带名称的坐标系。TF2 保存 frame 之间随时间变化的变换树。

一个变换必须明确：

- parent frame；
- child frame；
- translation；
- rotation；
- timestamp；
- static 还是 dynamic。

### 8.2 右手坐标系和单位

ROS 通常使用右手坐标系，URDF 长度单位为米、角度单位为弧度、质量单位为千克。
CAD 常以毫米建模，因此 mesh scale 错误会造成 `1000` 倍尺寸问题。

### 8.3 RPY 与旋转顺序

URDF `rpy` 不能凭画面尝试。旋转不是普通向量，相乘顺序不可交换。遇到方向错误时：

1. 在 RViz 显示 TF axes；
2. 检查 parent 和 child；
3. 单独验证一个固定变换；
4. 用已知单位轴向量验证旋转结果；
5. 最后再检查网格自身 CAD 坐标。

### 8.4 静态和动态 TF

- 固定 joint 由 `robot_state_publisher` 发布静态关系；
- revolute/prismatic joint 结合 `/joint_states` 发布动态关系；
- 相机标定外参可以是静态 TF；
- 移动底盘 `map -> odom -> base_link` 通常是动态关系。

### 8.5 项目 frame 设计

当前链：

```text
world -> base_link -> ... -> flange -> gripper_mount
      -> gripper_base -> gripper_tcp
```

未来建议：

```text
map -> odom -> base_link -> arm_mount -> arm_base -> ... -> flange
    -> gripper_mount -> gripper_base -> gripper_tcp

camera_link -> camera_optical_frame
station_frame -> pregrasp_frame -> grasp_frame -> insertion_frame
```

### 8.6 TF 调试工具

```bash
ros2 run tf2_ros tf2_echo flange gripper_mount
ros2 run tf2_ros tf2_echo gripper_base gripper_tcp
ros2 run tf2_tools view_frames
```

### 8.7 实验 4：验证工具链

1. 启动 `sim.launch.py`；
2. 使用 `tf2_echo` 查询两个固定变换；
3. 运行 `demo_motion.py`；
4. 观察动态 arm frame 是否随 `/joint_states` 变化；
5. 写下 `gripper_tcp` 的 parent、平移单位和证据来源。

完成标准：不依赖 Gazebo 相机视角也能判断安装方向是否正确。

## 9. URDF 和 Xacro

### 9.1 URDF 的三种核心元素

```xml
<link name="link_name">...</link>
<joint name="joint_name" type="fixed">...</joint>
<robot name="robot_name">...</robot>
```

Link 描述刚体，joint 描述两个 link 的约束和相对关系。

### 9.2 Joint 类型

常见类型：

- `fixed`：无自由度；
- `revolute`：有角度上下限；
- `continuous`：连续旋转；
- `prismatic`：直线移动；
- `floating` 和 `planar`：特殊自由度。

每个运动 joint 都需要正确的 parent、child、origin、axis、limit 和 dynamics。

### 9.3 Visual、collision、inertial

```xml
<link name="finger">
  <visual>...</visual>
  <collision>...</collision>
  <inertial>...</inertial>
</link>
```

- Visual 可以详细；
- Collision 应简单、稳定且覆盖真实接触区域；
- Inertial 必须具有正质量和合理、正定的惯量矩阵。

碰撞体偏移会造成画面不接触但物理接触。惯量错误会造成数值不稳定、异常振动或
不真实响应。

### 9.4 Xacro

Xacro 为 URDF 增加 include、macro、参数和表达式，适合模块化组合。

ATOM 使用：

```text
ur3e_atom.urdf.xacro
|-- include ur_description/ur_macro.xacro
`-- include atom_gripper.urdf.xacro
```

夹爪 macro 接受 `parent`、`prefix`、`use_mimic` 和安装 origin，因此未来可以接到
其他机械臂，而不重写夹爪内部模型。

### 9.5 Mimic joint

URDF mimic 可以表达两个关节的运动关系，但具体模拟器或控制器是否执行 mimic 需要
单独确认。当前 Gazebo DART 路径不依赖 mimic，左右夹指分别接受命令。

### 9.6 验证命令

```bash
xacro ros2_ws/src/atom_gripper_description/urdf/ur3e_atom.urdf.xacro \
  > /tmp/ur3e_atom.urdf
check_urdf /tmp/ur3e_atom.urdf
```

不要只验证 XML 能解析，还要检查：

- 根 link 和树结构；
- link/joint 名称；
- mesh URI 和 scale；
- joint axis 和 limit；
- collision origin；
- 惯量和质量；
- TF 方向；
- RViz 和 Gazebo 中的表现。

### 9.7 实验 5：解释夹爪 Xacro

阅读 `urdf/atom_gripper.urdf.xacro`，回答：

1. 为什么 mesh scale 是 `0.001`；
2. 为什么两个 visual 使用相同的 CAD 变换；
3. 为什么两个 joint axis 方向相反，但相同负值都表示关闭；
4. 为什么碰撞盒只覆盖末端，而不是整个手指；
5. 当前 TCP 为什么不能用于真实插入。

## 10. CAD 网格与机器人模型

### 10.1 CAD 原点不是机器人 frame

CAD 原点取决于建模历史，机器人 frame 应取决于机械接口、运动轴和任务定义。
两者通过 visual origin 关联，但不能混为一谈。

### 10.2 网格处理检查项

- STEP 单位；
- 装配 placement 是否保留；
- 组件分组是否正确；
- mesh 法向和封闭性；
- 三角面数；
- 原点和包围盒；
- 左右件是否镜像或独立；
- visual 和 collision 是否在同一 link frame 中对齐。

### 10.3 碰撞简化原则

优先使用：

1. box、cylinder、sphere；
2. 少量 convex hull；
3. 必要时使用简化网格；
4. 避免将完整机械 CAD 直接用于动态碰撞。

对抓取接触，碰撞面位置比外观细节更重要。

### 10.4 实验 6：从几何预测接触位置

已知：

```text
零位夹持面间隙 = 39.681 mm
试管宽度 = 14 mm
左右对称关闭
```

计算：

```text
single_finger_travel = (39.681 - 14) / 2
                     = 12.8405 mm
```

运行抓取测试并比较 `finger_contact`。若结果远离 `-12.84 mm`，首先检查几何和碰撞，
不要先增加摩擦系数或控制增益。

## 11. Gazebo Harmonic

### 11.1 Gazebo 的职责

Gazebo 提供：

- world 和模型加载；
- 刚体动力学；
- collision/contact；
- sensor simulation；
- rendering；
- Gazebo Transport topic/service；
- system plugin。

Gazebo 不等于 ROS。两者可以各自运行，通过 `ros_gz` 连接。

### 11.2 SDF 与 URDF

- URDF 适合机器人运动树和 ROS 工具；
- SDF 更完整地描述 world、光源、物理、传感器、多个模型和 Gazebo plugin；
- ROS 中常用 URDF/Xacro 描述机器人，用 SDF 描述场景。

ATOM 的机器人由 Xacro 展开后动态生成，world 来自 `atom_empty.sdf` 或
`atom_grasp.sdf`。

### 11.3 Gazebo system plugin

当前 world 使用：

- Physics；
- UserCommands；
- SceneBroadcaster；
- Contact。

机器人使用：

- JointPositionController；
- JointStatePublisher。

试管使用 PosePublisher。没有对应 plugin 时，相关 topic 或行为不会自动存在。

### 11.4 物理步长和实时因子

```xml
<max_step_size>0.001</max_step_size>
<real_time_factor>1.0</real_time_factor>
```

`max_step_size` 是物理积分时间步。更小可能改善快速接触稳定性，但增加计算量。
`real_time_factor` 是目标仿真速度，不保证机器一定达到。

调参必须记录：

- physics engine；
- step size；
- real-time factor；
- CPU/GPU；
- 初始状态；
- controller update rate；
- 样本数和指标。

### 11.5 接触、摩擦和柔顺性

刚性库仑摩擦模型无法直接表示硅胶指垫的压缩、粘附、速度相关摩擦和材料破损。
即使使用报告的 `mu=0.88`，也只是在当前仿真模型中输入一个参数。

禁止的推理：

```text
Gazebo 中没有滑落 -> 真实夹持力满足要求
```

需要实物测量才能闭合的量包括：法向力、填充质量、动摩擦、接触面积、指垫刚度、
释放粘附和试管强度。

### 11.6 Gazebo CLI

```bash
gz topic -l
gz topic -i -t /model/ur3e_atom/joint_state
gz topic -e -t /model/ur3e_atom/joint_state -n 1
gz service -l
```

### 11.7 Headless 模式

```bash
ros2 launch atom_gripper_description grasp.launch.py \
  headless:=true run_test:=true
```

Headless 用于 CI 和区分渲染问题与物理/通信问题。最终涉及视觉传感器时仍需验证
rendering 路径。

### 11.8 实验 7：区分 visual 和 collision

1. 启动抓取场景但不运行测试；
2. 在 Gazebo GUI 打开 collision visualization；
3. 比较两指末端 visual 和 collision；
4. 运行测试并观察 Stage 2；
5. 确认接触时 visual 与试管侧面相符；
6. 记录关节反馈，而不是只截一张图。

完成标准：能够解释旧模型为什么会出现不可见接触。

## 12. `ros_gz_bridge`

### 12.1 为什么需要 bridge

Gazebo Transport 和 ROS 2 使用不同的消息和通信层。`ros_gz_bridge` 在支持的消息
类型之间转换。

桥接语法：

```text
/TOPIC@ROS_MSG@GZ_MSG   # 双向
/TOPIC@ROS_MSG[GZ_MSG   # Gazebo -> ROS
/TOPIC@ROS_MSG]GZ_MSG   # ROS -> Gazebo
```

ATOM 示例：

```text
/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock
/model/ur3e_atom/joint_state@sensor_msgs/msg/JointState[gz.msgs.Model
/model/ur3e_atom/joint/left_finger_joint/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double
```

### 12.2 Remapping

Gazebo 原始 joint state topic 较长，launch 将 ROS 侧 remap 为 `/joint_states`。检查
问题时必须知道 Gazebo 名称、bridge 名称和 ROS remap 后名称。

### 12.3 Bridge 不是控制器

Bridge 只做消息转换，不提供：

- 轨迹插值；
- 控制律；
- joint limit enforcement；
- goal/cancel/result；
- 硬件安全；
- 运动规划。

当前 `Float64 -> Gazebo position plugin` 只适合基线测试。

### 12.4 实验 8：追踪一条命令

1. 找到 `demo_motion.py` 发布的 ROS topic；
2. 在 `sim.launch.py` 找到 bridge 规则；
3. 在 `ur3e_atom.urdf.xacro` 找到 Gazebo plugin topic；
4. 用 `ros2 topic info --verbose` 确认 ROS 发布者和 bridge 订阅者；
5. 用 `gz topic -l` 确认 Gazebo 侧 topic；
6. 画出一条从 Python 到 Gazebo joint 的完整链路。

## 13. `ros2_control`

### 13.1 为什么下一步需要它

MoveIt 通常输出时间参数化关节轨迹，并通过 controller action 执行。当前逐关节
`Float64` 命令没有统一轨迹 action，因此不能作为完整 MoveIt 执行接口。

`ros2_control` 提供可复用的控制器架构，使上层能够在仿真和硬件之间保持相似接口。

### 13.2 核心架构

```text
MoveIt / application
        |
FollowJointTrajectory action
        |
joint_trajectory_controller
        |
Controller Manager
        |
command/state interfaces
        |
gz_ros2_control or vendor hardware interface
        |
Gazebo joints or real robot
```

### 13.3 Hardware component

Hardware component 暴露：

- state interface，例如 position、velocity、effort；
- command interface，例如 position、velocity、effort；
- lifecycle，例如 configure、activate、deactivate；
- read/write 更新过程。

仿真中由 `gz_ros2_control/GazeboSimSystem` 连接 Gazebo joint；实机中由 vendor driver
或自定义 hardware interface 连接控制器。

### 13.4 Controller Manager

Controller Manager 加载、配置、激活控制器，并在更新循环中交换 state 和 command。

常用命令：

```bash
ros2 control list_hardware_components
ros2 control list_hardware_interfaces
ros2 control list_controllers
ros2 control load_controller --set-state active joint_state_broadcaster
```

这些命令只有在完成 `ros2_control` 接入后才会对 ATOM 当前模型有效。

### 13.5 常用控制器

- `joint_state_broadcaster`：发布统一 `/joint_states`；
- `joint_trajectory_controller`：执行一组关节的时间轨迹；
- gripper action controller：提供标准夹爪 action；
- forward command controller：直接转发简单命令，适合有限场景。

`joint_trajectory_controller` 主要 action：

```text
/<controller>/follow_joint_trajectory
control_msgs/action/FollowJointTrajectory
```

### 13.6 `gz_ros2_control`

`gz_ros2_control` 在 Gazebo 内实例化 ros2_control Controller Manager，并将控制接口
连接到仿真 joint。需要：

1. URDF/SDF 中的 `<ros2_control>` 元素；
2. Gazebo `gz_ros2_control` plugin；
3. controller YAML；
4. joint 名称和 interface 一致；
5. spawner 或 launch 激活控制器。

### 13.7 安装状态与命令

截至 2026-08-12，本机软件源可提供以下 Jazzy 包，但尚未安装：

```text
ros-jazzy-ros2-control       candidate 4.44.0
ros-jazzy-ros2-controllers   candidate 4.39.0
ros-jazzy-gz-ros2-control    candidate 1.2.17
```

经项目决策记录确认后安装：

```bash
sudo apt update
sudo apt install \
  ros-jazzy-ros2-control \
  ros-jazzy-ros2-controllers \
  ros-jazzy-gz-ros2-control
```

安装软件不等于完成项目接入。接入完成需要控制器配置、启动、接口测试和执行指标。

### 13.8 ATOM 迁移练习设计

建议按以下顺序实施，不要一次同时修改 MoveIt：

1. 仅对两夹指增加 `<ros2_control>`；
2. 使用 `joint_state_broadcaster` 检查统一反馈；
3. 使用简单位置控制器验证 open/close；
4. 增加 arm 的 `joint_trajectory_controller`；
5. 用手写 `FollowJointTrajectory` goal 验证执行；
6. 加入取消、超时、错误码和 joint tolerance；
7. 通过后再连接 MoveIt。

### 13.9 `ros2_control` 完成标准

- Controller Manager 能启动且没有 interface claim 冲突；
- `/joint_states` 名称、顺序、单位和更新时间正确；
- trajectory action 可 goal、feedback、result、cancel；
- 超限目标被拒绝或限制；
- 仿真暂停/恢复行为可解释；
- 轨迹误差有量化阈值；
- 同一上层接口可映射到未来 vendor driver；
- 所有临时 controller gain 记录为仿真参数。

## 14. MoveIt 2

### 14.1 MoveIt 做什么

MoveIt 2 提供机器人运动规划所需的组件，包括：

- RobotModel；
- 正/逆运动学；
- PlanningScene 和碰撞检查；
- joint/pose/路径约束；
- 运动规划管线；
- 时间参数化；
- trajectory execution；
- RViz MotionPlanning 插件；
- Task Constructor 等高级任务组件。

MoveIt 不提供真实关节反馈，也不自动实现底层控制器或硬件急停。

### 14.2 `move_group` 数据流

```text
RViz / application / task executive
              |
              v
          move_group
        /      |       \
RobotModel  PlanningScene  planning pipeline
   |           |               |
URDF+SRDF   robot+world      OMPL/Pilz/CHOMP
              |
              v
       planned RobotTrajectory
              |
              v
FollowJointTrajectory action client
              |
              v
ros2_control or vendor controller
```

`move_group` 监听 `/joint_states` 和 TF，维护当前机器人状态和 PlanningScene。它只
作为 trajectory controller 的 action client，不替代 action server。

### 14.3 URDF 与 SRDF

URDF 描述物理运动树。SRDF 增加 MoveIt 需要的语义：

- planning group；
- chain、joint 或 subgroup；
- end effector；
- virtual joint；
- passive joint；
- named state；
- disabled collision pair。

SRDF 不能修复错误的 URDF。生成 self-collision matrix 后仍应审查，不能无条件接受
所有自动禁用项。

### 14.4 Planning group

ATOM 参考模型预计至少需要：

```text
ur_manipulator  # UR3e 六轴 arm group
atom_gripper    # 两个 prismatic finger joint
```

End effector 通常关联 `atom_gripper` group，并以 `gripper_tcp` 或明确的 parent link
连接 arm。最终命名需与 vendor description 和 controller joint 列表一致。

### 14.5 Kinematics

MoveIt 需要为 arm group 配置 IK solver。需要理解：

- IK 可能有多个解或无解；
- seed state 影响结果；
- singularity 附近解不稳定；
- position-only 和 full-pose IK 不同；
- IK timeout 和 search resolution；
- 工具 frame 错误会使所有目标 pose 系统性偏移。

对 Project ATOM，必须先测量 TCP，再讨论真实插入精度。

### 14.6 PlanningScene

PlanningScene 包含：

- 当前 RobotState；
- 自碰撞模型；
- world collision objects；
- attached collision objects；
- allowed collision matrix。

抓取时常见状态变化：

```text
cuvette in world
    -> close gripper
    -> attach cuvette to gripper
    -> transfer with attached collision object
    -> place
    -> detach cuvette back into world
```

Gazebo 中物体被摩擦夹住，不会自动让 MoveIt PlanningScene 知道物体已经 attached。
必须由任务逻辑显式同步两个世界模型。

### 14.7 Motion planning

MoveIt 默认可使用 OMPL，也可配置 Pilz、CHOMP 等规划管线。规划请求可以指定：

- joint goal；
- pose goal；
- position/orientation constraint；
- joint constraint；
- velocity/acceleration scaling；
- planner 和 planning time。

规划结果是带时间信息的 trajectory，不只是几何路径。

### 14.8 Plan 与 Execute 必须分开验证

**Plan-only gate**：

- RobotModel 正确；
- joint state 和 TF 正确；
- IK 可用；
- self-collision 和 world collision 正确；
- 能生成无碰撞 trajectory。

**Execution gate**：

- controller action 存在；
- joint 名称一致；
- controller 能接受 trajectory；
- feedback 更新；
- tolerance、cancel、timeout 正确；
- Gazebo 或真实机械臂实际跟踪。

RViz 显示规划轨迹成功不代表控制器已经执行。

### 14.9 MoveIt Setup Assistant

Setup Assistant 以 URDF 为输入，生成 SRDF 和 MoveIt 配置文件。典型步骤：

1. Load URDF/Xacro；
2. Generate Self-Collision Matrix；
3. Add Virtual Joints；
4. Add Planning Groups；
5. Add Robot Poses；
6. Define End Effectors；
7. Define Passive Joints；
8. 配置 controller；
9. 填写作者信息；
10. 生成独立 config package。

项目 MoveIt 包建议命名为独立的 `atom_moveit_config`，不能将生成文件放进
`atom_gripper_description`。

### 14.10 当前安装状态

截至 2026-08-12，本机软件源提供但尚未安装：

```text
ros-jazzy-moveit                  candidate 2.12.4
ros-jazzy-moveit-setup-assistant  candidate 2.12.4
```

在将 MoveIt 配置加入项目之前，需要在 `docs/DECISIONS.md` 记录版本、生成输入、
planning groups、IK plugin 和 controller mapping 的证据。经确认后可安装二进制包：

```bash
sudo apt update
sudo apt install ros-jazzy-moveit ros-jazzy-moveit-setup-assistant
```

启动 Setup Assistant：

```bash
source /opt/ros/jazzy/setup.bash
ros2 launch moveit_setup_assistant setup_assistant.launch.py
```

不要立即把首次生成结果当作最终配置。必须人工检查 SRDF、joint limit、kinematics、
controller 和碰撞矩阵。

### 14.11 推荐的 MoveIt 学习实验

先在官方教程机器人上学习：

1. MoveIt Quickstart in RViz；
2. Your First C++ MoveIt Project；
3. Planning Around Objects；
4. PlanningScene ROS API；
5. Pick and Place with MoveIt Task Constructor。

然后再迁移到 ATOM：

1. 只加载 `ur3e_atom` RobotModel；
2. 定义 arm 和 gripper group；
3. 在 RViz 中检查随机合法状态；
4. 检查 self-collision；
5. 完成 joint goal 的 plan-only；
6. 完成 `gripper_tcp` pose goal 的 plan-only；
7. 加入试管支架 collision object；
8. 连接 `joint_trajectory_controller`；
9. 执行低速 Gazebo trajectory；
10. 实现 attach/detach 试管；
11. 最后编排 pick/place 任务。

### 14.12 MoveIt 完成标准

- `move_group` 无缺失参数或 plugin 错误；
- RobotModel frame 和 joint limit 与 Xacro 一致；
- `/joint_states` 和 TF 无陈旧数据；
- arm 和 gripper group 正确；
- IK 成功率在定义的测试分布上有样本数和统计；
- collision object 与真实/仿真工装 frame 一致；
- plan-only 与 execution 分别有测试；
- controller mapping 与 action 名称一致；
- 速度和加速度缩放有明确上限；
- 失败、取消和超时返回可被 task executive 处理。

## 15. RViz 与 Gazebo 的区别

| 工具 | 主要职责 | 不应误解为 |
|---|---|---|
| RViz | 可视化 ROS 数据、TF、RobotModel、PlanningScene | 物理模拟器 |
| Gazebo | 物理、接触、传感器和动态 world | MoveIt 规划器 |
| MoveIt | 运动学、碰撞场景和轨迹规划 | 底层控制器 |
| ros2_control | 控制器与硬件接口框架 | 任务规划器 |

一个完整仿真通常同时运行四者，每一层都有自己的状态和接口。

## 16. Manipulation 任务架构

### 16.1 建议状态机

```text
IDLE
  -> ACQUIRE_TARGET
  -> PLAN_PREGRASP
  -> MOVE_PREGRASP
  -> PLAN_APPROACH
  -> APPROACH
  -> CLOSE_GRIPPER
  -> VERIFY_GRASP
  -> ATTACH_OBJECT
  -> LIFT
  -> TRANSFER
  -> PLACE
  -> OPEN_GRIPPER
  -> DETACH_OBJECT
  -> RETREAT
  -> COMPLETE
```

每个状态需要：

- 输入条件；
- timeout；
- 成功条件；
- 错误码；
- cancel 行为；
- recovery 或 safe state。

### 16.2 夹爪接口建议

未来夹爪不能只提供一个 open/close topic。至少需要：

- goal：目标宽度或 open/close 命令；
- feedback：位置、速度、对象接触或驱动状态；
- result：成功、空抓、超时、堵转、通信故障；
- cancel；
- 最大行程和力/电流限制；
- 标定状态。

磁传感器是否能估算抓取力尚无标定证据，不应提前定义为力传感器。

### 16.3 感知接口建议

目标 pose 应包含：

- `header.stamp`；
- `header.frame_id`；
- position 和 orientation；
- 置信度或质量指标；
- 目标 ID；
- 数据陈旧阈值；
- 失败原因。

固定 waypoint baseline 和感知更新 baseline 应使用相同任务、相同初始扰动和相同
成功条件比较。

## 17. 标定基础

### 17.1 必须标定的变换

- 机械臂 base 到世界/工作站；
- flange 到 gripper mount；
- gripper mount 到 TCP；
- base 或 flange 到 camera；
- workstation fiducial 到操作目标；
- 移动底盘 dock 后的 base pose。

### 17.2 标定记录

每个变换至少记录：

```text
parent frame
child frame
translation [m]
rotation [quaternion or RPY rad]
measurement method
instrument
sample count N
test conditions
repeatability / uncertainty
date and hardware revision
```

### 17.3 TCP 验证

TCP 不能只从 CAD 猜测。需要多姿态接触或经过验证的标定方法，并用独立验证点检查。
对插入任务，应分别评估位置、方向和重复性误差。

## 18. 测试和证据纪律

### 18.1 测试层次

1. XML/Xacro 静态检查；
2. 单元测试；
3. ROS graph 集成测试；
4. headless Gazebo 回归；
5. GUI/传感器可视检查；
6. 仿真参数敏感性测试；
7. 台架硬件测试；
8. 真实机械臂低速测试；
9. 真实工作站任务测试；
10. 系统级故障和安全测试。

### 18.2 定量报告模板

```markdown
- 指标：
- 单位：
- 样本数 N：
- 初始条件：
- 软件/硬件版本：
- 测量方法：
- 均值：
- 标准差或范围：
- 不确定度：
- 通过阈值：
- 原始数据位置：
```

### 18.3 假通过防护

自动测试不能只检查“物体最终变高”。还应检查：

- 接触发生在合理几何位置；
- 左右夹指行为一致；
- 物体在 lift 前没有被隐藏碰撞推走；
- 运动路径符合预期；
- 保持阶段没有下滑；
- 释放后物体回到合理区域；
- topic 数据不是陈旧样本；
- 测试进程退出码正确。

ATOM 的不可见碰撞问题是典型例子：画面、碰撞和判据必须互相交叉验证。

## 19. 调试方法

### 19.1 从下往上定位

```text
文件和环境
  -> package 是否发现
  -> node 是否运行
  -> topic/action 是否存在
  -> 消息是否流动
  -> TF 是否正确
  -> URDF/collision 是否正确
  -> controller 是否跟踪
  -> MoveIt 是否规划
  -> task 是否正确编排
```

不要一开始就修改 planner 或 PID。

### 19.2 ROS 常用检查

```bash
ros2 doctor --report
ros2 pkg list | rg 'atom|ur|moveit|control'
ros2 node list
ros2 topic list -t
ros2 service list -t
ros2 action list -t
ros2 param list
ros2 run rqt_graph rqt_graph
```

### 19.3 构建问题

```bash
colcon list
colcon graph
colcon --log-base ros2_ws/log test-result \
  --test-result-base ros2_ws/build \
  --verbose
rosdep check --from-paths ros2_ws/src --ignore-src
```

检查实际使用的是 source tree 还是 install space：

```bash
ros2 pkg prefix atom_gripper_description
```

### 19.4 TF 问题

症状：模型歪、目标 pose 偏、MoveIt IK 无解、碰撞物体漂移。

检查顺序：

1. parent/child；
2. 单位；
3. RPY 顺序；
4. 四元数是否归一化；
5. 时间戳；
6. 是否存在重复发布者；
7. optical frame 轴约定；
8. CAD mesh 自身坐标。

### 19.5 Controller 问题

症状：MoveIt plan 成功但 execute 失败。

检查：

```bash
ros2 control list_controllers
ros2 action list -t
ros2 action info /joint_trajectory_controller/follow_joint_trajectory
ros2 topic hz /joint_states
```

然后比较：

- MoveIt controller 名；
- action namespace；
- joint 列表和顺序；
- command/state interface；
- controller active 状态；
- joint limit 和 tolerance；
- `use_sim_time`。

### 19.6 Gazebo 问题

症状：模型抖动、穿透、爆炸、隔空接触、GUI 空白。

分开检查：

- URDF/SDF 解析；
- mesh resource path；
- collision shape；
- inertia；
- physics step；
- controller gain；
- 初始重叠；
- Gazebo Transport topic；
- ROS bridge；
- rendering driver。

## 20. 建议的四周学习安排

### 第 1 周：ROS 2 和工程环境

- 完成实验 0、1、2、3；
- 能构建包并解释 overlay；
- 能追踪 node/topic；
- 能解释 Conda ABI 问题；
- 能阅读 launch 和 rclpy 脚本。

交付物：一张当前 ROS graph 图和接口表。

### 第 2 周：TF、URDF、CAD 和 Gazebo

- 完成实验 4、5、6、7、8；
- 能独立展开 Xacro；
- 能显示 TF 和 collision；
- 能用几何预测接触位置；
- 能解释 ROS 与 Gazebo 的边界。

交付物：frame 树、碰撞截图和一次 headless 回归日志。

### 第 3 周：ros2_control

- 先运行官方 Jazzy demo；
- 理解 hardware interface 和 Controller Manager；
- 在独立分支为夹爪建立最小控制器；
- 用 action 测试轨迹、取消、超时和限位；
- 不接 MoveIt，先让控制层独立通过。

交付物：控制器配置、接口表和轨迹跟踪误差报告。

### 第 4 周：MoveIt 2

- 完成官方 RViz quickstart；
- 理解 URDF/SRDF 和 PlanningScene；
- 为组合模型创建独立配置包草案；
- 先 plan-only，再连接 Gazebo execute；
- 加入一个静态 collision object 和 attach/detach 流程。

交付物：经审查的 SRDF、规划场景、plan-only 测试和执行测试。

## 21. 项目准入检查表

成员开始修改 ATOM manipulation stack 前应能完成：

- [ ] 从干净终端正确 source Jazzy 和项目 workspace；
- [ ] 解释 underlay、overlay 和 install space；
- [ ] 用 CLI 找到 `/joint_states` 的发布者；
- [ ] 解释 topic、service 和 action 的选择；
- [ ] 解释 `use_sim_time`；
- [ ] 画出 `flange -> gripper_tcp` frame 链；
- [ ] 解释 `visual`、`collision` 和 `inertial`；
- [ ] 用 `xacro` 和 `check_urdf` 验证模型；
- [ ] 解释为什么 CAD 原点不是 TCP；
- [ ] 解释 `ros_gz_bridge` 的三个方向符号；
- [ ] 运行无重力运动冒烟测试；
- [ ] 运行有重力 headless 抓取回归；
- [ ] 解释旧不可见碰撞假通过；
- [ ] 解释 `ros2_control` 和 Gazebo position plugin 的区别；
- [ ] 解释 MoveIt plan-only 与 execute 的区别；
- [ ] 说明 PlanningScene attached object 为什么需要显式同步；
- [ ] 知道软件 stop 不等于硬件 emergency stop；
- [ ] 对任何量化结论写出单位、工况、样本数和不确定度。

## 22. 官方学习资料

### ROS 2 Jazzy

- [ROS 2 Jazzy 文档首页](https://docs.ros.org/en/jazzy/)
- [ROS 2 Jazzy 初学者 CLI 教程](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools.html)
- [Topic、Service、Action 接口选择](https://docs.ros.org/en/jazzy/How-To-Guides/Topics-Services-Actions.html)
- [ROS 2 Jazzy 安装故障排查](https://docs.ros.org/en/jazzy/How-To-Guides/Installation-Troubleshooting.html)

### Gazebo Harmonic 与 ROS

- [Gazebo Harmonic 文档](https://gazebosim.org/docs/harmonic/getstarted/)
- [ROS 2 integration overview](https://gazebosim.org/docs/harmonic/ros2_overview/)
- [Use ROS 2 to interact with Gazebo](https://gazebosim.org/docs/harmonic/ros2_integration/)
- [Gazebo Classic ROS 2 包迁移说明](https://gazebosim.org/docs/harmonic/migrating_gazebo_classic_ros2_packages/)

### ros2_control

- [ros2_control Jazzy 入门](https://control.ros.org/jazzy/doc/getting_started/getting_started.html)
- [`gz_ros2_control` Jazzy](https://control.ros.org/jazzy/doc/gz_ros2_control/doc/index.html)
- [`joint_trajectory_controller`](https://control.ros.org/jazzy/doc/ros2_controllers/joint_trajectory_controller/doc/userdoc.html)
- [ros2_control Jazzy demos](https://control.ros.org/jazzy/doc/ros2_control_demos/doc/index.html)

### MoveIt 2

- [MoveIt 2 教程目录](https://moveit.picknik.ai/main/doc/tutorials/tutorials.html)
- [MoveIt 2 Getting Started](https://moveit.picknik.ai/main/doc/tutorials/getting_started/getting_started.html)
- [MoveIt Setup Assistant](https://moveit.picknik.ai/main/doc/examples/setup_assistant/setup_assistant_tutorial.html)
- [`move_group` 架构](https://moveit.picknik.ai/main/doc/concepts/move_group.html)
- [MoveIt 运动规划概念](https://moveit.picknik.ai/main/doc/concepts/motion_planning.html)

MoveIt 官方 `main` 文档可能跟随上游开发分支变化。项目实际接入应固定 ROS 2 Jazzy
可用的 MoveIt 版本，并记录对应软件版本和生成配置的输入版本。

### 项目内资料

- [`CURRENT_SIMULATION_BASELINE.md`](CURRENT_SIMULATION_BASELINE.md)
- [`PHASE1_MINIMUM_LEARNING_ROADMAP.md`](PHASE1_MINIMUM_LEARNING_ROADMAP.md)
- [`SYSTEM_ARCHITECTURE.md`](SYSTEM_ARCHITECTURE.md)
- [`DECISIONS.md`](DECISIONS.md)
- [`ASSUMPTIONS.md`](ASSUMPTIONS.md)
- [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md)
- [`SIM2REAL_LOG.md`](SIM2REAL_LOG.md)

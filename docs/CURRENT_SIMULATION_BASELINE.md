# Project ATOM 当前工作与仿真基线说明

> 文档状态：当前基线说明
>
> 最后更新：2026-08-13
>
> 适用范围：继承资产检查、UR3e 参考平台组合、Gazebo 功能仿真
>
> 不适用范围：真实机械臂选型确认、真实夹爪标定、实验室安全认证、实物性能证明

## 1. 文档目的

本文档详细说明 Project ATOM 仓库目前已经完成的工作、实现结构、运行方法、
验证结果和证据边界。它回答以下问题：

1. 当前仓库里实际有什么；
2. STEP 装配体如何转成模块化机器人模型；
3. UR3e、夹爪、Gazebo 和 ROS 2 如何连接；
4. 目前能够重复运行哪些仿真；
5. 哪些参数来自原始资料，哪些仍是临时假设；
6. 当前 `ros2_control`、MoveIt 2 和双模式任务基线如何工作；
7. 进入实物和感知阶段前还缺什么。

本项目当前处于继承资产验证和架构定义阶段。本文中的“通过”仅指指定的软件回归
检查通过，不代表真实抓取力、可靠性、插入精度或安全性能已经得到验证。

## 2. 证据使用原则

项目按以下优先级使用证据：

1. 实物测量和可重复测试数据；
2. 原始 CAD、固件和源代码；
3. 上一届团队报告；
4. 项目背景和规划文档。

当前尚未看到或测量实物，因此本基线主要依赖原始 STEP、上一届报告和官方软件
包。所有缺少实测支持的尺寸、质量、惯量、安装变换和控制参数均明确标记为临时
值。

## 3. 当前结论摘要

### 3.1 已经完成

- 恢复并检查继承的 STEP 夹爪装配体；
- 将详细 CAD 生成三个可视 STL：固定主体、左指、右指；
- 创建模块化 ROS 2 描述包 `atom_gripper_description`；
- 通过顶层 Xacro 将官方 UR3e 描述与自定义夹爪组合；
- 建立 `flange -> gripper_mount -> gripper_base -> gripper_tcp` 工具链；
- 建立两个 Gazebo 场景：无重力运动冒烟测试和有重力刚性抓取测试；
- 建立 ROS 2 与 Gazebo Transport 的命令、关节状态和试管位姿桥接；
- 建立确定性的运动脚本和自动抓取验收脚本；
- 建立可切换的 Gazebo-native / `ros2_control` 控制后端；
- 建立独立 MoveIt 配置、RRT-Connect 自由空间规划和 CartesianPath 接近段；
- 建立逻辑附着与物理接触相互独立的抓取、转移和释放任务；
- 建立 Ubuntu 22.04 / ROS 2 Humble / Gazebo Fortress Docker 验收环境；
- 修复 Conda Python 版本污染导致的 `rclpy` C 扩展加载失败；
- 修复 UR 法兰安装方向和临时 CAD 基准误判；
- 修复夹指可视模型与碰撞模型不一致造成的“隔空抓取”；
- 通过 Xacro 展开、`check_urdf`、包测试和一次修正后的 Gazebo 抓取回归。

### 3.2 尚未完成

- 未确认 Project ATOM 最终采购的机械臂；
- 未测量真实快速连接件、工具安装变换和 TCP；
- 未测量真实夹指轴线、零位、行程、质量分布和惯量；
- 未确认实际试管型号，也未测量装液质量；
- 未建立 `ros2_control`、轨迹控制器和统一的仿真/实机控制接口；
- 未生成或验证 MoveIt 2 配置包；
- 未加入真实工作站、相机、标定、规划场景和碰撞物体；
- 未实现夹爪 action、任务状态机、超时、空抓、恢复和故障接口；
- 未验证真实接触、硅胶变形、抓取力、破损风险和释放粘附；
- 未建立系统级安全回路或硬件急停。

## 4. 软件环境

当前机器和仿真基线如下。

| 项目 | 当前值 | 状态 |
|---|---:|---|
| 操作系统 | Ubuntu 24.04.3 | 本机已确认 |
| ROS 2 | Jazzy Jalisco | 仿真基线决定 |
| Gazebo | Harmonic / Gazebo Sim 8.11.0 | 本机已确认 |
| `ros_gz` | 1.0.22 | 本机 Debian 包 |
| Python | 系统 Python 3.12 | ROS 2 Jazzy 使用 |
| UR description | 3.5.0 | `atom_sim.repos` 固定版本 |
| UR Gazebo source | 2.5.0 | `atom_sim.repos` 固定版本 |
| MoveIt 2 | 未安装或未接入本包 | 后续工作 |
| `ros2_control` | 当前模型未使用 | 后续工作 |

选择 Jazzy/Harmonic 的证据和适用边界记录在
[`DECISIONS.md`](DECISIONS.md) 的 D-006。该选择只服务于当前继承资产仿真，
不等于最终部署平台决定。

## 5. 输入资产与派生文件

### 5.1 只读原始输入

| 资产 | 路径 | 用途 |
|---|---|---|
| Fusion 360 归档 | `hardware/end effector/End Effector Assembly V3.f3z` | 机械源数据 |
| STEP 装配体 | `hardware/end effector/End Effector Assembly V3.step` | 网格生成和几何检查 |
| 上一届报告 | `previous report/Capstone_Robotic_Hand_Lab_Experiment.pdf` | 尺寸、材料和试验背景 |

这些文件属于继承原始资产，不应为仿真方便而直接修改。二进制 CAD 和 PDF 应通过
Git LFS 管理。

### 5.2 生成资产

生成网格位于：

```text
ros2_ws/src/atom_gripper_description/meshes/generated/
|-- base.stl
|-- left_finger.stl
|-- right_finger.stl
`-- manifest.json
```

`manifest.json` 保存源 STEP 路径、SHA-256、毫米单位、URDF 缩放比例、组件分组
和包围盒。当前 STEP SHA-256 为：

```text
8ee4fd1c064210eab24cb10ba67623e497cab0866adbca86d5be9a0c63aaf351
```

STL 保留 STEP 装配位置，仅作为详细可视几何。URDF 使用 `0.001` 缩放将毫米转换
为米。碰撞几何使用简化盒体，不使用高三角面数 STL。

## 6. ROS 2 包结构

当前自定义包为：

```text
atom_gripper_description/
|-- CMakeLists.txt
|-- package.xml
|-- launch/
|   |-- sim.launch.py
|   `-- grasp.launch.py
|-- meshes/generated/
|-- scripts/
|   |-- demo_motion.py
|   |-- extract_step_meshes.py
|   `-- grasp_lift_test.py
|-- test/
|   `-- test_description.py
|-- urdf/
|   |-- atom_gripper.urdf.xacro
|   `-- ur3e_atom.urdf.xacro
`-- worlds/
    |-- atom_empty.sdf
    `-- atom_grasp.sdf
```

包只负责描述、组合和当前仿真基线。未来的 MoveIt 配置、夹爪驱动、感知和任务
执行器应放在独立包中，不能继续堆入 description 包。

## 7. CAD 到机器人描述的处理

### 7.1 为什么不直接导出单体 URDF

原始 STEP 是机械装配源数据，但机器人模型需要明确的 link、joint、碰撞体和惯量。
直接将整个 CAD 导成单体 URDF 会产生以下问题：

- 左右夹指不能独立成为运动 link；
- 机械臂、夹爪和未来移动底盘无法模块化替换；
- 详细网格不适合作为实时碰撞几何；
- CAD 原点通常不等于法兰基准或工具中心点；
- CAD 装配约束不能直接替代机器人关节语义。

因此当前模型将装配体分为固定主体和两个移动指，并手工定义机器人层面的关节。

### 7.2 网格重新生成

在仓库根目录执行：

```bash
python3 -m venv /tmp/atom-cad-env
/tmp/atom-cad-env/bin/pip install -r \
  ros2_ws/src/atom_gripper_description/tools/requirements-cad.txt
/tmp/atom-cad-env/bin/python \
  ros2_ws/src/atom_gripper_description/scripts/extract_step_meshes.py \
  "hardware/end effector/End Effector Assembly V3.step" \
  ros2_ws/src/atom_gripper_description/meshes/generated
```

临时虚拟环境放在 `/tmp`，避免将 CAD 转换依赖混入 ROS 2 的系统 Python 环境。

### 7.3 当前机器人层简化

- 主体质量：`0.48 kg`；
- 每个夹指质量：`0.05 kg`；
- 总质量：`0.58 kg`，来自上一届报告；
- 惯量：使用盒体近似计算；
- 夹指：两个对称的 prismatic joint；
- 单指临时行程：`[-15, +5] mm`，总窗口 `20 mm`；
- CAD 零位可见夹持面间隙：约 `39.681 mm`；
- 关闭方向：负关节值；
- TCP：相对 `gripper_base` 的临时位置 `[-1.8, 0, 170.536] mm`。

这些值尚未经过实物检查，不能用于真实限位、可达性或安全判断。

## 8. 模块化机器人模型

### 8.1 组合关系

```text
官方 UR3e description
          +
自定义 ATOM gripper Xacro
          +
ur3e_atom 顶层组合 Xacro
          =
Gazebo 中的组合机器人
```

官方 UR 源固定在 `ros2_ws/atom_sim.repos`，自定义夹爪不复制或修改官方机械臂
网格。

顶层 Xacro 已直接使用官方 UR3e 的 `joint_limits.yaml`、
`default_kinematics.yaml`、`physical_parameters.yaml` 和
`visual_parameters.yaml`。六轴 Gazebo 控制器也从同一份关节限制文件读取
`54/54/28/9/9/9 N.m` 输出上限。官方文件仍只是标称刚体模型，不包含当前实机
的序列号标定、关节弹性、间隙、减速器/控制器动态或公开的加速度上限。

### 8.2 主要 frame 链

```text
world
`-- base_link
    `-- UR3e links ...
        `-- flange
            |-- tool0
            `-- gripper_mount
                `-- gripper_base
                    |-- left_finger
                    |-- right_finger
                    `-- gripper_tcp
```

`flange` 是上游 UR 描述提供的机械末端连接 frame。夹爪通过显式
`gripper_mount` 接入 `flange`，并施加临时旋转：

```xml
<origin xyz="0 0 0" rpy="1.5707963268 0 1.5707963268"/>
```

该旋转用于使当前 CAD 工具轴朝向 UR 腕部前方。真实快速连接件的平移和旋转尚未
测量。

### 8.3 `tool0`、`flange` 和 TCP 的区别

- `flange`：机械安装接口 frame；
- `tool0`：UR 描述中的全零工具 frame；
- `gripper_mount`：本项目显式增加的夹爪安装接口；
- `gripper_tcp`：当前临时的夹持工具中心点。

URT-1 在上一届资料中是舵机驱动器，不是机械安装基准，因此不能用其组件中心作为
法兰参考点。

## 9. 可视、碰撞和惯量模型

### 9.1 三者必须分开理解

| 模型 | 作用 | 当前实现 |
|---|---|---|
| Visual | Gazebo/RViz 中显示外观 | 详细 STEP 派生 STL |
| Collision | 接触和碰撞计算 | 盒体近似 |
| Inertial | 动力学质量与转动惯量 | 临时质量和盒体惯量 |

看到模型外观正确，不代表碰撞模型和惯量也正确。

### 9.2 夹指末端碰撞体

当前每个夹指使用 `6 x 20 x 20 mm` 末端盒体。它们根据变换后的 CAD 网格切片
对齐，而不是根据整个夹指包围盒放置。

CAD 零位下两端内表面分别为：

```text
左侧内表面：+18.000 mm
右侧内表面：-21.681 mm
可见间隙：   39.681 mm
```

对于居中的 `14 mm` 试管，理想单指关闭距离为：

```text
(39.681 - 14) / 2 = 12.8405 mm
```

因此仿真接触应发生在约 `-12.84 mm`，而不是零位附近。

### 9.3 已修复的不可见碰撞问题

早期模型的可视夹指仍有约 `39.681 mm` 间隙，但碰撞体内表面只剩 `6.7 mm`
间隙。Gazebo 因此在画面中尚未接触时已经产生接触力，导致试管看起来被“隔空
夹起”。

早期 `N=3` 的通过结果已作废。修复包括：

- 将碰撞盒移动到 CAD 末端夹持面；
- 将夹指命令改为负方向关闭；
- 把关节范围改为 `[-0.015, 0.005] m`；
- 验收脚本要求接触位置落在 `[-0.0145, -0.0115] m`；
- 要求左右接触差不超过 `0.001 m`；
- 将横向漂移加入通过条件；
- 在包测试中锁定碰撞盒尺寸、位置和关节限位。

完整问题记录见 [`SIM2REAL_LOG.md`](SIM2REAL_LOG.md)。

## 10. Gazebo 场景

### 10.1 `atom_empty.sdf`

用途：模型资源、TF、关节命令和关节反馈冒烟测试。

主要配置：

- 重力：`0 0 0 m/s^2`；
- 仿真步长：`0.001 s`；
- 地面：静态平面；
- 不包含试管；
- 机器人使用 Gazebo 原生关节位置控制插件。

该场景不是动力学或控制器性能测试。

### 10.2 `atom_grasp.sdf`

用途：临时刚性接触的抓取、抬升、保持、返回和释放测试。

主要配置：

| 参数 | 当前值 | 证据状态 |
|---|---:|---|
| 重力 | `9.81 m/s^2` 向下 | 标准仿真输入 |
| 步长 | `0.001 s` | 仿真配置 |
| 试管碰撞尺寸 | `14 x 14 x 45 mm` | 仅 `14 x 14 mm` 来自报告 |
| 试管质量 | `10 g` | 临时假设 |
| 夹持摩擦系数 | `0.88` | 报告中 `N=10` 倾斜面均值 |
| 指垫接触高度 | `20 mm` | 报告和简化模型输入 |
| 试管支架 | 简化盒体 | 仅为场景支撑，不是仪器模型 |

试管透明主体、蓝色顶部、内部样品和支脚只用于增强辨识度。它们不是继承试管的
精确 CAD，且不改变单一的 `14 x 14 x 45 mm` 盒体碰撞模型。

## 11. ROS 2 与 Gazebo 数据流

当前数据流为：

```text
ROS 2 Float64 command topics
          |
          v
ros_gz_bridge  --ROS_TO_GZ-->  Gazebo joint position plugins
                                      |
                                      v
                              Gazebo joint state plugin
                                      |
ROS /joint_states  <--GZ_TO_ROS-- ros_gz_bridge

Gazebo cuvette PosePublisher
          |
          v
ros_gz_bridge  --GZ_TO_ROS-->  ROS /cuvette/pose
```

主要 ROS 2 接口：

| 接口 | 类型 | 方向 | 用途 |
|---|---|---|---|
| `/joint_states` | `sensor_msgs/msg/JointState` | Gazebo 到 ROS | 机械臂和夹指反馈 |
| `/cuvette/pose` | `tf2_msgs/msg/TFMessage` | Gazebo 到 ROS | 抓取测试测量 |
| `/model/ur3e_atom/joint/<joint>/cmd_pos` | `std_msgs/msg/Float64` | ROS 到 Gazebo | 临时位置命令 |
| `/clock` | `rosgraph_msgs/msg/Clock` | Gazebo 到 ROS | 仿真时间 |

当前每个关节直接使用 `Float64` 位置话题，不是 `FollowJointTrajectory` action，
也不是最终硬件控制接口。

## 12. 控制与测试脚本

### 12.1 `demo_motion.py`

该脚本依次发布四组固定关节位置，用于检查：

- ROS 2 发布器可以创建；
- `ros_gz_bridge` 可以转发命令；
- UR3e 六个关节和两个夹指能在 Gazebo 中运动；
- 最终能返回初始姿态。

它不做路径规划、碰撞规避、速度规划或轨迹执行监控。

### 12.2 `grasp_lift_test.py`

测试流程：

1. 等待 `/cuvette/pose` 和机械臂/夹指全部关节反馈；
2. 在张开抓取姿态稳定 `2 s`；
3. 两指关闭 `2 s`；
4. 机械臂平滑插值到名义 `50 mm` 抬升姿态；
5. 保持 `5 s`；
6. 返回并释放；
7. 根据接触位置和试管轨迹判定通过或失败。

当前通过阈值：

| 指标 | 条件 |
|---|---:|
| 左右接触位置 | 每指在 `[-14.5, -11.5] mm` |
| 左右接触对称性 | 差值不超过 `1 mm` |
| 抬升高度 | 至少 `40 mm` |
| 抬升横向运动 | 不超过 `10 mm` |
| `5 s` 保持下滑 | 不超过 `5 mm` |
| 保持末端高度 | 至少高于初始 `35 mm` |
| 六轴最大保持误差 | 不超过 `0.020 rad` |
| 六轴最大保持漂移 | 不超过 `0.005 rad` |
| 释放位置误差 | 不超过 `15 mm` |

### 12.3 修正后的回归结果

在一次全新无界面 Gazebo 启动中得到：

```text
RESULT PASS
lift=0.0500 m
hold_drop=0.0000 m
lateral=0.0040 m
release_error=0.0005 m
arm_hold_error=0.0181 rad
arm_hold_drift=0.0001 rad
arm_samples=5002
finger_contact=(-0.0128, -0.0128) m
```

以上为 Jazzy/Harmonic 一次全新运行（`N=1`）；Humble/Fortress 独立运行得到
相同显示精度下的误差和漂移，并采集 `5001` 个保持阶段关节状态样本（`N=1`）。
这证明最终代码路径能够在官方标称关节力矩上限内完成指定的刚性仿真流程，但样本量
不足以表示可靠性，也不能外推到硬件挠曲或真实控制精度。

## 13. 构建和运行

### 13.1 终端环境规则

ROS 2 Jazzy 的 `rclpy` 针对系统 Python 3.12 构建。Conda `base` 环境可能把
Python 3.13 放到 `PATH` 前面，从而出现：

```text
ModuleNotFoundError: No module named 'rclpy._rclpy_pybind11'
```

本包的 ROS Python 可执行脚本使用 `/usr/bin/python3` shebang。构建时仍建议显式
选择系统 Python：

```bash
PATH=/usr/bin:/bin:$PATH colcon build \
  --symlink-install \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
```

不要在同一 shell 中混合多个 ROS 发行版或多个未明确排序的 overlay。

### 13.2 首次导入和构建

```bash
cd /home/wuyifan/ATOM/ros2_ws
source /opt/ros/jazzy/setup.bash
vcs import src < atom_sim.repos
rosdep install --from-paths src --ignore-src -r -y
PATH=/usr/bin:/bin:$PATH colcon build --symlink-install \
  --packages-select ur_description atom_gripper_description \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash
```

### 13.3 后续增量构建

```bash
cd /home/wuyifan/ATOM
source /opt/ros/jazzy/setup.bash
colcon --log-base ros2_ws/log build \
  --base-paths ros2_ws/src \
  --build-base ros2_ws/build \
  --install-base ros2_ws/install \
  --packages-select atom_gripper_description \
  --symlink-install
source ros2_ws/install/setup.bash
```

`--log-base` 是 `colcon` 全局参数，必须放在 `build` 或 `test` 子命令之前。

### 13.4 无重力运动冒烟测试

终端 A：

```bash
cd /home/wuyifan/ATOM
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 launch atom_gripper_description sim.launch.py
```

终端 B：

```bash
cd /home/wuyifan/ATOM
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 run atom_gripper_description demo_motion.py
```

### 13.5 自动抓取测试

```bash
cd /home/wuyifan/ATOM
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 launch atom_gripper_description grasp.launch.py run_test:=true
```

无图形界面回归：

```bash
ros2 launch atom_gripper_description grasp.launch.py \
  headless:=true run_test:=true
```

不要同时启动多个 Gazebo world。自动测试启动后前 `10 s` 用于 Gazebo 和机器人
生成，随后进入五阶段测试。

### 13.6 手动分步运行

终端 A：

```bash
ros2 launch atom_gripper_description grasp.launch.py
```

终端 B：

```bash
ros2 run atom_gripper_description grasp_lift_test.py
```

不要用默认的 `sim.launch.py` world 运行抓取脚本，因为 `atom_empty.sdf` 没有试管，
也不会桥接 `/cuvette/pose`。

## 14. 检查与调试命令

### 14.1 展开并检查 URDF

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
xacro ros2_ws/src/atom_gripper_description/urdf/ur3e_atom.urdf.xacro \
  > /tmp/ur3e_atom.urdf
check_urdf /tmp/ur3e_atom.urdf
```

预期根链从 `world` 经过 UR3e 到 `flange`、`gripper_mount`、`gripper_base`、两指和
`gripper_tcp`。

### 14.2 包测试

```bash
cd /home/wuyifan/ATOM
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
colcon --log-base ros2_ws/log test \
  --base-paths ros2_ws/src \
  --build-base ros2_ws/build \
  --install-base ros2_ws/install \
  --packages-select atom_gripper_description \
  --event-handlers console_direct+
colcon --log-base ros2_ws/log test-result \
  --test-result-base ros2_ws/build/atom_gripper_description \
  --verbose
```

当前结果为 `3 tests, 0 errors, 0 failures`。测试覆盖组合链、网格 URI、夹指碰撞
尺寸与位置、关节限位和抓取 world 的关键物理输入。

### 14.3 ROS 图检查

```bash
ros2 node list
ros2 topic list -t
ros2 topic echo /joint_states --once
ros2 topic hz /joint_states
ros2 topic echo /cuvette/pose --once
ros2 topic info /cuvette/pose --verbose
```

### 14.4 Gazebo 图检查

```bash
gz topic -l
gz topic -i -t /model/ur3e_atom/joint_state
gz topic -e -t /model/ur3e_atom/joint_state -n 1
```

### 14.5 TF 检查

```bash
ros2 run tf2_ros tf2_echo flange gripper_mount
ros2 run tf2_ros tf2_echo gripper_base gripper_tcp
ros2 run tf2_tools view_frames
```

## 15. 常见故障

### 15.1 `rclpy._rclpy_pybind11` 不存在

原因通常是 Conda Python 3.13 正在加载为 ROS 2 Jazzy 的解释器，而二进制扩展是为
Python 3.12 构建的。

检查：

```bash
which python3
python3 --version
head -n 1 ros2_ws/install/atom_gripper_description/lib/atom_gripper_description/grasp_lift_test.py
```

处理：使用系统 Python、重新构建并重新 source workspace。不要通过复制或重命名
`.so` 文件来绕过 ABI 不匹配。

### 15.2 抓取脚本报告没有试管位姿

```text
Missing cuvette pose on /cuvette/pose
```

检查是否启动的是 `grasp.launch.py`，而不是默认 `sim.launch.py`。确认只存在一个
Gazebo 实例，并检查：

```bash
ros2 topic info /cuvette/pose --verbose
```

### 15.3 模型方向错误

不要通过移动相机判断 frame。应依次检查：

1. `flange` 到 `gripper_mount` 的固定变换；
2. CAD 网格在 `gripper_base` 中的 visual origin；
3. `gripper_tcp` 相对 `gripper_base` 的位置；
4. TF 轴方向和 joint axis；
5. Gazebo 中的碰撞体显示。

### 15.4 看起来没接触却能抬起物体

这是典型的 visual/collision 不一致。必须检查碰撞体，而不能只调摩擦系数。当前
回归脚本同时检查接触位置窗口和左右对称性，以避免旧问题再次被误判为通过。

### 15.5 图形界面出现 EGL 警告

`libEGL` 或 DRI 警告通常属于渲染驱动路径。若服务端物理仿真可以运行，先使用
`headless:=true` 区分渲染问题和物理/ROS 问题，再单独检查 NVIDIA、Mesa、Wayland
或 X11 配置。

## 16. 能力与证据矩阵

| 能力 | 当前状态 | 可引用证据 | 不能声称 |
|---|---|---|---|
| STEP 可读取并生成网格 | 已完成 | manifest、STL、生成脚本 | 网格等同实物 |
| UR3e 与夹爪组合 | 已完成软件基线 | Xacro、`check_urdf` | UR3e 是已采购机械臂 |
| Gazebo 生成和关节运动 | 已通过冒烟测试 | launch、脚本、反馈 | 控制器等同真实硬件 |
| 刚性试管抓取流程 | 修正后 `N=1` 通过 | 自动测试日志 | 真实抓取可靠或安全 |
| 夹持碰撞对齐 | 与 CAD 切片一致 | URDF、单元测试 | 与实物指垫一致 |
| TCP | 有临时 frame | Xacro | 已标定 TCP |
| MoveIt 2 规划与执行 | 仿真验证基线已实现 | SRDF、OMPL、控制器映射、双模式自动测试 | 已具备真实仪器避障或插入能力 |
| 真实工作站转移 | 未实现 | 无 | 已验证仪器插入精度 |
| 硬件急停 | 未实现 | 无 | 具备安全认证 |

## 17. 进入下一阶段前的优先工作

### P0：冻结可测量事实

1. 确认采购机械臂型号、控制器、固件和厂商 ROS 2 支持矩阵；
2. 检查真实夹爪是否与 STEP 一致；
3. 测量法兰到快速连接件、夹爪基准和 TCP；
4. 测量夹指零位、方向、单指行程和机械限位；
5. 确认试管型号，测量空管/装液质量和关键尺寸；
6. 获取上一届固件、ROS/串口代码、接线和原始实验数据。

所有定量测量应记录单位、方法、样本数、工况和不确定度。

### P1：完善标准控制接口

1. 保留已实现的原生/`ros2_control` 可切换回归路径；
2. 为夹爪补充与未来实机驱动一致的标准 gripper action；
3. 在仿真和实机间保持相同的上层 action/topic 接口；
4. 加入取消、控制超时、控制器失活和错误传播测试；
5. 在实验室电脑复跑控制器和轨迹验收。

### P2：完善 MoveIt 2 基线

1. 审查已实现的 arm、gripper、end-effector 分组和 self-collision matrix；
2. 用确认后的硬件限制替换临时速度/加速度值；
3. 将试管架和仪器几何加入 PlanningScene；
4. 增加 planning-scene 与 Gazebo world 的位姿一致性检查；
5. 建立固定目标与扰动目标的重复试验；
6. 补充规划失败、执行超时和恢复路径。

### P3：感知、标定和任务执行

1. 定义相机、工作站和目标 frame；
2. 建立外参和 TCP 标定流程；
3. 输出带时间戳和置信度的目标 pose；
4. 用显式状态机执行 approach、grasp、verify、lift、transfer、place；
5. 加入空抓、目标丢失、规划失败、控制超时和恢复路径；
6. 最后才评估学习方法相对确定性基线是否有实际收益。

## 18. 相关项目文档

- [`PROJECT_STATUS.md`](PROJECT_STATUS.md)：项目阶段和开发 gate；
- [`DECISIONS.md`](DECISIONS.md)：已经接受的工程决定；
- [`ASSUMPTIONS.md`](ASSUMPTIONS.md)：未确认事实和开放问题；
- [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md)：阻塞项和技术风险；
- [`SIM2REAL_LOG.md`](SIM2REAL_LOG.md)：仿真与实物差异；
- [`CAD_INVENTORY.md`](CAD_INVENTORY.md)：CAD 资产盘点；
- [`SYSTEM_ARCHITECTURE.md`](SYSTEM_ARCHITECTURE.md)：目标系统边界；
- [`ROS_GAZEBO_MOVEIT_TUTORIAL.md`](ROS_GAZEBO_MOVEIT_TUTORIAL.md)：知识背景和实践教程。
- [`MOVEIT_GRASP_BASELINE.md`](MOVEIT_GRASP_BASELINE.md)：当前 MoveIt 抓放实现、命令、门控和验收边界。

## 19. 官方参考资料

- [ROS 2 Jazzy 文档](https://docs.ros.org/en/jazzy/)
- [ROS 2 topic、service 和 action 接口说明](https://docs.ros.org/en/jazzy/How-To-Guides/Topics-Services-Actions.html)
- [Gazebo Harmonic 与 ROS 2 集成](https://gazebosim.org/docs/harmonic/ros2_integration/)
- [Gazebo Harmonic ROS 2 集成概览](https://gazebosim.org/docs/harmonic/ros2_overview/)
- [ros2_control Jazzy 入门](https://control.ros.org/jazzy/doc/getting_started/getting_started.html)
- [`gz_ros2_control` Jazzy 文档](https://control.ros.org/jazzy/doc/gz_ros2_control/doc/index.html)
- [MoveIt 2 教程目录](https://moveit.picknik.ai/main/doc/tutorials/tutorials.html)
- [MoveIt Setup Assistant](https://moveit.picknik.ai/main/doc/examples/setup_assistant/setup_assistant_tutorial.html)

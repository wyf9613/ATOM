# UF850 纯机械臂仿真：当前阶段与代码结构

这份文档是当前开发工作的主入口。需要了解项目总体范围时再看
[`PROJECT_SCOPE.md`](PROJECT_SCOPE.md)，需要核对测试边界和历史决定时再看
[`PROJECT_STATUS.md`](PROJECT_STATUS.md) 与 [`DECISIONS.md`](DECISIONS.md)。

## 1. 当前处于什么阶段

项目总体仍处于 **Phase 0：接手、盘点与架构确认**。当前软件工作属于
**Stage 1：固定底座操作基线**中的第一小步：先建立一个不含夹爪的 UF850
确定性仿真基线，再单独集成 ATOM 夹爪。

当前已经完成：

- Ubuntu 24.04、ROS 2 Jazzy、Gazebo Harmonic 的 Docker 环境；
- 固定版本的 UFactory `xarm_ros2` Jazzy 源码；
- 纯 UF850 六关节模型、TF、MoveIt 和模拟轨迹控制器启动；
- MoveIt 规划并执行六关节大幅往返轨迹；
- 无界面自动验收，以及 Gazebo + RViz 图形启动入口。

当前没有完成：

- ATOM 夹爪的动态控制和组合 MoveIt 配置；
- 试管、试管架和仪器场景；
- 多 waypoint 的任务 combo、夹取和放置状态机；
- 实机控制器、标定、TCP、负载、碰撞和安全验证。

因此，目前结果证明的是软件命令链在仿真中可以工作，不代表实机精度或安全能力。

## 2. 当前软件链路

```text
trajectory_demo.py 或 RViz
          │  目标/MoveGroup 请求
          ▼
        MoveIt
          │  FollowJointTrajectory
          ▼
uf850_traj_controller
          │
          ▼
Gazebo 中的 UF850 ── joint_states / TF ──► MoveIt、RViz、自动检查
```

- **MoveIt** 负责碰撞检查和轨迹规划；
- **ROS 2 控制器**接收规划后的关节轨迹；
- **Gazebo**模拟机器人和物理环境；
- **RViz**用于设置目标、查看机器人状态和预览规划结果。

RViz 不直接计算轨迹。它把目标交给 MoveIt；点击 **Execute** 后，MoveIt
通过控制器驱动 Gazebo 中的机器人。

## 3. 代码结构

```text
ATOM/
├── docker-compose.jazzy.yaml
├── docker/jazzy/
│   ├── Dockerfile                 # Ubuntu 24.04 + ROS 2 Jazzy 镜像
│   ├── entrypoint.sh              # 自动加载 ROS 环境
│   └── README.md                  # 版本固定和底层环境细节
├── ros2_ws/
│   ├── atom_xarm_jazzy.repos      # 固定 UFactory 源码版本
│   └── src/
│       ├── atom_xarm_sim/         # 当前纯机械臂动态仿真
│       │   ├── launch/
│       │   │   └── uf850_arm_only.launch.py
│       │   └── atom_xarm_sim/
│       │       ├── smoke_test.py
│       │       └── trajectory_demo.py
│       ├── atom_gripper_description/ # 独立夹爪描述，当前仿真不加载
│       └── atom_xarm_description/    # UF850 + 夹爪组合描述，尚未动态控制
└── scripts/docker/
    ├── jazzy_build.sh
    ├── jazzy_sim_smoke.sh
    ├── jazzy_arm_trajectory_sim.sh
    ├── jazzy_arm_trajectory_gui.sh
    └── jazzy_shell.sh
```

关键文件职责：

| 文件 | 职责 |
| --- | --- |
| `uf850_arm_only.launch.py` | 无窗口启动 Gazebo server、UF850、MoveIt、TF 和两个控制器 |
| `trajectory_demo.py` | 提交目标、等待控制器、规划并执行、检查最终误差 |
| `smoke_test.py` | 分别检查 joint states、TF、MoveIt 规划和控制器执行 |
| `jazzy_arm_trajectory_sim.sh` | 构建并运行无窗口轨迹验收，结束后自动退出 |
| `jazzy_arm_trajectory_gui.sh` | 转发 X11，打开 Gazebo/RViz，自动演示后保留窗口 |

厂商源码不会复制进本仓库；Docker 构建时根据 `.repos` 文件导入
`/jazzy_ws/src/xarm_ros2`。

## 4. 最常用的三个命令

### 无界面验收

```bash
./scripts/docker/jazzy_arm_trajectory_sim.sh
```

这是判断当前基线是否正常的首选命令。

### 查看 Gazebo 和 RViz

```bash
./scripts/docker/jazzy_arm_trajectory_gui.sh
```

图形界面准备好后，脚本自动执行一次大幅往返动作，随后保持窗口打开；在终端按
`Ctrl+C` 关闭。当前演示的六关节偏移为：

```text
[+0.70, -0.45, -0.55, +0.50, +0.45, -0.50] rad
```

速度和加速度缩放均为 0.05。这个参数只用于仿真观察，不是实机参数。

### 进入开发容器

```bash
./scripts/docker/jazzy_shell.sh
```

## 5. 在 RViz 中手动规划

1. 打开右侧 **MotionPlanning** 面板；
2. 选择 planning group `uf850`；
3. 拖动末端交互标记，或选择一个随机有效目标；
4. 点击 **Plan**，只计算并预览轨迹；
5. 点击 **Execute**，把已规划轨迹发送到控制器，Gazebo 机器人随之运动；
6. 点击 **Plan & Execute**，则连续完成规划和执行。

在左侧 `Displays → MotionPlanning → Planned Path` 中可以调整轨迹动画显示，
包括循环播放和状态显示时间。

## 6. waypoint 和 combo

waypoint 是路径中的目标点。例如：

```text
当前位置 → A → B → C
```

其中 A、B、C 是三个 waypoint，可以用六个关节角表示，也可以用末端位姿
`x, y, z, roll, pitch, yaw` 表示。

下一步的纯机械臂 combo 建议实现为：

```text
Home → 工作位 A → 工作位 B → Home
```

每一段分别执行“规划 → 执行 → 状态检查”。后续加入夹爪后，再扩展为：

```text
Home → 抓取上方 → 抓取位 → 夹爪闭合 → 抬起
     → 放置上方 → 放置位 → 夹爪张开 → Home
```

自由空间转移使用 MoveIt 规划；下降、插入和退出等需要保持方向的动作应使用
笛卡尔直线约束，不能只依赖两个端点。

## 7. 当前验证结果

2026-09-03，在 Docker/Gazebo Harmonic 中完成一次六关节大幅往返测试：

| 条件 | 结果 |
| --- | --- |
| 加载关节 | 仅 `joint1` 至 `joint6`，无夹爪关节 |
| 控制器 | `joint_state_broadcaster` 与 `uf850_traj_controller` active |
| 去程 | 69 个轨迹点，成功执行 |
| 回程 | 69 个轨迹点，成功执行 |
| 最大模拟最终关节误差 | 0.010035 rad |
| 自动验收门限 | 0.02 rad |

这是单次大动作仿真结果；更小幅轨迹的重复测试和完整边界记录见
[`DECISIONS.md`](DECISIONS.md#d-009---keep-a-separately-testable-bare-arm-trajectory-baseline)
与 [`SIM2REAL_LOG.md`](SIM2REAL_LOG.md)。

## 8. 下一步拆分

接下来的工作分为两个相互独立的部分：

1. **纯机械臂**：实现多 waypoint combo、分段检查和轨迹显示；
2. **机械臂 + ATOM 夹爪**：补充夹爪控制、组合 SRDF、碰撞矩阵和动作接口。

只有这两部分分别通过后，再组合抓取、搬运和放置任务。

# MoveIt 双模式抓放仿真基线

更新日期：2026-08-13

## 1. 目标与边界

当前实现验证的是一条确定性的仿真软件链：

```text
MoveIt 2 -> FollowJointTrajectory -> ros2_control -> Gazebo
         -> 显式任务状态机 -> 逻辑附着或物理接触验收
```

UR3e 是继承实验的参考平台，不代表 Project ATOM 已采购该机械臂。夹爪安装位姿、
TCP、质量分配、夹指行程、试管质量和工作站几何仍是临时值。仿真通过不能证明实物
抓取力、材料安全、插入精度、硬件急停或实验室部署兼容性。

## 2. 软件包职责

| 包 | 职责 |
|---|---|
| `atom_gripper_description` | 模块化 UR3e + 夹爪 Xacro、控制接口、Gazebo worlds 和原生回归脚本 |
| `atom_ur3e_moveit_config` | SRDF、KDL、OMPL、规划限制、控制器映射、RViz 和组合 launch |
| `atom_manipulation` | 抓取、转移、释放状态机及结构化验收结果 |

`control_backend:=native` 保留原有位置命令回归；MoveIt 任务固定使用
`control_backend:=ros2_control`，其中机械臂和夹爪分别由两个
`JointTrajectoryController` 执行。

## 3. 任务状态机

任务依次执行：

```text
PREGRASP -> OPEN -> APPROACH -> CLOSE -> ACQUIRE -> LIFT
          -> TRANSFER -> LOWER -> RELEASE -> RETREAT
```

- `PREGRASP` 和 `TRANSFER` 使用 OMPL `RRTConnectkConfigDefault`；
- approach、lift、lower、retreat 是沿世界 Z 轴的 `0.050 m` CartesianPath；
- transfer 将 shoulder pan 从 `0` 转到 `0.2 rad`；
- 每次 CartesianPath 必须达到至少 `0.99` fraction；
- 抬升必须至少 `0.040 m`，转移过程允许的最大掉落为 `0.008 m`；
- 释放后的目标平面误差必须不超过 `0.020 m`。

这些阈值是当前固定仿真场景的验收条件，不是实物规格。

## 4. 两种抓取模式

### 4.1 logical

逻辑世界使用缩小到 `4 x 4 x 35 mm` 的试管碰撞体，避免摩擦接触替逻辑附着提供
支撑。只有以下条件同时成立时才向 Gazebo detachable-joint 插件发布 attach：

- TCP 到物体中心距离不超过 `0.035 m`；
- 六个机械臂关节速度最大值不超过 `0.020 rad/s`；
- 物体速度不超过 `0.020 m/s`；
- 夹爪闭合轨迹已成功完成。

MoveIt PlanningScene 同时添加试管 collision object，并附着到 `gripper_tcp`。
释放时先恢复为世界物体，再解除 Gazebo fixed joint。该模式验证任务编排和规划链，
不能作为摩擦夹持证据。

### 4.2 physical

物理世界不创建或调用 detachable joint。试管碰撞为 `14 x 14 x 45 mm`、临时质量
`0.010 kg`，接触摩擦输入为报告均值 `0.88`。只有刚体碰撞和摩擦能使物体随夹爪
抬升。该模式仍没有硅胶顺应性、传感器、夹持力或破坏模型。

## 5. Docker 使用

首次构建：

```bash
cd /home/wuyifan/ATOM
./scripts/docker/humble_build.sh
```

运行一个可视化逻辑抓取任务：

```bash
xhost +local:docker
./scripts/docker/humble_gui.sh logical
```

物理接触模式使用 `./scripts/docker/humble_gui.sh physical`；旧的 Gazebo-native
回归使用 `./scripts/docker/humble_gui.sh native`。

完整回归默认各跑一次 MoveIt 模式：

```bash
./scripts/docker/humble_test.sh
```

单独执行每种模式各 10 次：

```bash
./scripts/docker/humble_moveit_acceptance.sh 10
```

每次运行使用独立 `ROS_DOMAIN_ID`，避免上一轮 DDS discovery 缓存干扰控制器启动；
完整日志写入 `.docker-runtime/acceptance/`，该目录不是项目证据源，确认后的汇总必须
写入 `docs/SIM2REAL_LOG.md`。

## 6. 验证输出

成功任务输出一行机器可检索结果，例如：

```text
RESULT PASS | mode=physical lift=0.0500_m release_xy_error=0.0005_m plans=9 planning_time=0.087_s
```

静态测试还检查：

- 原生和 `ros2_control` Xacro 展开；
- 八个受控关节及 command interface；
- detachable-joint 参数和逻辑世界缩小碰撞体；
- SRDF 分组、home 状态和 end effector；
- MoveIt 控制器与 `ros2_controllers.yaml` 关节集合一致；
- 所有规划关节都有显式速度和加速度限制。

2026-08-13 的固定场景批量结果为 logical `10/10`、physical `10/10` 任务通过；
详细工况、范围和限制见 `SIM2REAL_LOG.md`。所有 20 次运行在任务结果输出之后都复现了
Humble MoveIt 2.5.9 的 `move_group` 退出段错误，因此“任务通过”不等于“进程干净退出”。

## 7. 下一步

1. 将 Gazebo 支架和确认后的仪器网格加入 PlanningScene；
2. 测量安装变换、TCP、夹指行程、质量、重心和惯量并记录不确定度；
3. 用真实硬件限制替换临时规划加速度；
4. 加入控制器失活、目标丢失、attach 拒绝、规划失败和执行超时测试；
5. 在实验室 Ubuntu 22.04 / Humble 电脑重复 Docker 验收；
6. 采购型号确认后，用厂商描述、驱动和标定替换 UR3e 参考模块。

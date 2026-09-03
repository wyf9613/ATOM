# Project ATOM

**ATOM — Autonomous Transport & Object Manipulation for the Autonomous Chemical Laboratory** 是墨尔本大学 2026 S2--2027 S1 的机电一体化 Capstone 项目，目标是逐步构建一个用于自主化学实验室样品运输与物体操作的移动操作平台。

当前处于 **Phase 0：接手、盘点与技术路线确认**。现有成果是上一组的夹爪原型、Fusion 360 装配文件和固定工位实验报告；完整自主实验室系统尚未实现。

## 当前事实

- 上一组使用 UR3e 和人工设定路点，在两个模拟比色皿托盘间完成了 49/50 次完整循环。
- 49/50 的结果不代表真实 Opentrons Flex 到 DynaPro NanoStar 工作流已经验证。
- 继承夹爪为 STS3215 驱动的双指平行夹爪，使用 STM32 Nucleo、硅胶接触垫和磁传感反馈。
- 报告中的夹爪外形约为 225 x 105 x 131 mm，总质量约 580 g。
- 项目机械臂已确认为到货的 UFactory xArm 850；仿真基线使用 ROS 2 Jazzy，控制器/固件清点、移动底盘接口和真实仪器访问条件仍待确认。

## 从这里开始

日常开发先看以下三份即可：

1. [当前阶段、仿真用法与代码结构](docs/ARM_ONLY_SIMULATION.md)
2. [当前项目状态](docs/PROJECT_STATUS.md)
3. [Stage 0–4 项目范围](docs/PROJECT_SCOPE.md)

决策、风险、CAD 和论文等专题资料统一从[文档导航](docs/README.md)查找。
项目的长期背景保留在 [ATOM_Project_Context.md](ATOM_Project_Context.md)。

已编译版本见 `output/pdf/ATOM_Technical_Roadmap.pdf`。

## 目录

```text
.
|-- ATOM_Project_Context.md        # 项目总体背景与路线
|-- docs/                          # 架构、决策、问题和实验记录
|-- hardware/                      # 当前收到的硬件资料
|-- previous report/               # 上一组原始报告
|-- reference/                     # 外部参考资料索引
|-- source_cad/                    # CAD 来源与导出约定
`-- ros2_ws/                       # ROS 2 Jazzy 工作区与 ATOM 自有软件包
```

原始 PDF 和 F3Z 保留在接手时的位置，不在初始化过程中改名或改写。

## 获取仓库后

```bash
git lfs install
git lfs pull
```

当前软件基线为 Docker 中的 Ubuntu 24.04、ROS 2 Jazzy、Gazebo Harmonic 和 UFactory 官方 `xarm_ros2` Jazzy 分支。xArm 850 已到货，但实机连接前仍需清点控制器、固件、标定与安全接口。当前开发说明见 [`docs/ARM_ONLY_SIMULATION.md`](docs/ARM_ONLY_SIMULATION.md)；底层环境和固定版本见 [`docker/jazzy/README.md`](docker/jazzy/README.md)。继承的 UR3e 仿真基线保留在 `ur3e` 分支。

准备好构建时，从仓库根目录运行：

```bash
./scripts/docker/jazzy_build.sh
./scripts/docker/jazzy_shell.sh
```

运行无窗口 xArm 850 仿真冒烟测试：

```bash
./scripts/docker/jazzy_sim_smoke.sh
```

运行不含夹爪的 MoveIt 轨迹规划与控制仿真：

```bash
./scripts/docker/jazzy_arm_trajectory_sim.sh
```

打开 Gazebo 与 RViz 并观看同一段轨迹：

```bash
./scripts/docker/jazzy_arm_trajectory_gui.sh
```

## 近期里程碑

完整任务按 [Stage 0–4](docs/PROJECT_SCOPE.md#5-分阶段交付) 推进。离开实验室期间先推进 Stage 1 的固定底座仿真基线；Stage 0 中依赖实物的控制器、夹爪和安全证据回到实验室后补齐。

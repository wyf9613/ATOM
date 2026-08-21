# Project ATOM

**ATOM - Autonomous Transport & Object Manipulation for the Autonomous Chemical Laboratory** 是墨尔本大学 2026 S2 至 2027 S1 的机电一体化 Capstone 项目。

项目目标是集成移动底盘、商用机械臂和上一组留下的自定义夹爪，在受控实验室中完成试管从 A 点到 B 点的运输，并操作指定仪器的盖子和启动按钮。

当前仍处于 **Phase 0：交接资产核验、需求确认与架构定义**，但新版分支已经建立了可构建的 UR3e + 夹爪 Gazebo/MoveIt 仿真验证基线。该基线用于复现和验证继承资产，不代表最终机械臂、部署软件栈或真实仪器流程已经确定。

## 建议先读

1. [项目中文总览](ATOM_Project_Context.md)
2. [文档导航](docs/README.md)
3. [当前状态](docs/PROJECT_STATUS.md)
4. [项目范围](docs/PROJECT_SCOPE.md)
5. [当前仿真基线](docs/CURRENT_SIMULATION_BASELINE.md)
6. [MoveIt 双模式抓取基线](docs/MOVEIT_GRASP_BASELINE.md)
7. [假设与待确认事项](docs/ASSUMPTIONS.md)

## 当前最重要的事实

- 上一组使用 UR3e 和人工设定路点，在模拟托架之间完成 49/50 次完整循环。
- 新版仓库已实现模块化 UR3e + 夹爪描述、Gazebo 场景、`ros2_control`、MoveIt 配置和仿真任务状态机。
- Humble/Fortress 中逻辑抓取和刚体接触抓取各完成 10/10 次任务，但 20 次均复现 MoveIt 关闭阶段故障；因此干净退出尚未通过。
- 上述仿真不代表真实夹持力、硅胶柔顺、仪器插入、移动导航或安全性能。
- 继承夹爪 CAD 和报告已收到，但固件、ROS 代码、接线图和原始数据仍缺失。
- 实际采购机械臂、移动底盘接口和目标仪器参数仍待确认。
- 2026-08-21 的暂定任务是：A 点取试管，移动至 B 点，开盖、插入、关盖并按启动按钮。

## 仓库结构

```text
.
|-- ATOM_Project_Context.md       # 中文项目总览
|-- docs/                         # 范围、状态、架构、决策和验证记录
|-- docker/                       # Humble/Fortress 兼容环境
|-- ros2_ws/                      # UR3e + 夹爪仿真验证工作区
|-- scripts/                      # Docker 构建和验收脚本
|-- paper/paper/                  # 相关论文 PDF（当前为本地未跟踪资产）
|-- previous report/              # 上一组原始报告，只读
|-- hardware/                     # 原始 CAD/硬件资料，只读
|-- source_cad/                   # 派生 CAD/网格来源说明
|-- reference/                    # 外部资料索引
|-- output/pdf/                   # 正式 PDF
`-- tmp/                          # 临时提取与渲染文件
```

## 获取仓库后

```bash
git lfs install
git lfs pull
```

本机 Jazzy/Harmonic 用于开发验证；Ubuntu 22.04、ROS 2 Humble 和 Gazebo Fortress Docker 用于实验室兼容性门。两者都不是最终真实机械臂部署选择。复现命令见 [MoveIt 抓取基线](docs/MOVEIT_GRASP_BASELINE.md) 和 [Docker 说明](docker/humble/README.md)。

## 文档和资产规则

- 原始 PDF、F3Z 和 STEP 不覆盖、不改写。
- 确认选择写入 `docs/DECISIONS.md`；假设写入 `docs/ASSUMPTIONS.md`。
- 风险和阻塞项写入 `docs/KNOWN_ISSUES.md`。
- 仿真与实物差异写入 `docs/SIM2REAL_LOG.md`。
- 定量结论必须注明单位、条件、样本数和不确定度。
- 仿真通过、计划内容和论文结果都不能写成 ATOM 已实现的实机能力。

## 近期行动

1. 修复或明确 MoveIt Humble 关闭故障的边界。
2. 与化学团队确认并测量试管、仪器、盖子、按钮和人工流程。
3. 获取机械臂采购证据和移动底盘接口。
4. 收齐上一组固件、ROS 代码、接线和原始数据。
5. 实测夹爪质量、行程、TCP、夹持力和快拆重复性。
6. 用真实测量替换仿真中的暂定几何、惯量、摩擦和安装变换。
7. 先验证独立仪器技能，再组合移动端到端流程。

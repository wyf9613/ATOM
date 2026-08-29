# Project ATOM 文档导航

本目录存放项目的可维护文档。阅读时先看事实与范围，再看方案和实施计划。

## 推荐阅读顺序

1. [当前状态](PROJECT_STATUS.md)：已经有什么、还缺什么、各开发门是否通过。
2. [项目范围](PROJECT_SCOPE.md)：要完成的任务、范围内外、阶段和验收框架。
3. [系统架构](SYSTEM_ARCHITECTURE.md)：子系统、接口、TF 和任务执行关系。
4. [已知问题](KNOWN_ISSUES.md)：当前阻塞项、夹爪风险和证据限制。
5. [假设与待确认事项](ASSUMPTIONS.md)：尚未获得证据的输入条件。
6. [决策记录](DECISIONS.md)：已经确认的工程选择及其依据。
7. [当前仿真基线](CURRENT_SIMULATION_BASELINE.md)：已经实现的模型、测试证据、复现步骤和边界。
8. [MoveIt 抓取基线](MOVEIT_GRASP_BASELINE.md)：轨迹控制、任务状态机和双模式验收。
9. [第一阶段学习与实施路线](PHASE1_MINIMUM_LEARNING_ROADMAP.md)：仿真阶段最小技术栈。

## 专题文档

| 文档 | 用途 |
| --- | --- |
| [夹爪设计与验证](GRIPPER_DESIGN.md) | 汇总上一组夹爪结构、实验结果、风险和首轮测试 |
| [CAD 资产清单](CAD_INVENTORY.md) | 记录收到的 CAD、校验信息和后续导出要求 |
| [仿真到实机差异记录](SIM2REAL_LOG.md) | 持续记录模型假设、实测结果和修正验证 |
| [ROS/Gazebo/MoveIt 教程](ROS_GAZEBO_MOVEIT_TUTORIAL.md) | 新组员学习和项目练习 |
| [相关工作与论文索引](RELATED_WORK.md) | 按项目问题整理本地论文、证据边界和可用于报告的 related-work 初稿 |
| `technical_roadmap/` | 文献支持的技术路线 LaTeX 源码 |

## 文档职责

- **确认事实**写入 `PROJECT_STATUS.md`，重要工程选择同时写入 `DECISIONS.md`。
- **尚未确认的事实**写入 `ASSUMPTIONS.md`。
- **已经发现的问题和风险**写入 `KNOWN_ISSUES.md`。
- **项目要做和不做什么**只在 `PROJECT_SCOPE.md` 定义。
- **系统如何拆分和连接**只在 `SYSTEM_ARCHITECTURE.md` 定义。
- **实测与仿真不一致**写入 `SIM2REAL_LOG.md`。
- 定量结论必须注明单位、测试条件、样本数和不确定度或离散程度。

计划文档描述的是拟开展工作，不代表功能已经实现。

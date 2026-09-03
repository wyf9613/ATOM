# Project ATOM 文档导航

本目录存放项目的可维护文档。日常开发不需要逐份阅读；先使用下面的三个入口，
遇到具体问题时再查专题记录。

## 推荐阅读顺序

1. [当前阶段、纯机械臂仿真与代码结构](ARM_ONLY_SIMULATION.md)：当前开发的主入口。
2. [当前状态](PROJECT_STATUS.md)：已经有什么、还缺什么、各开发门是否通过。
3. [项目范围](PROJECT_SCOPE.md)：Stage 0–4、范围内外和验收框架。

UR3e 的已实现仿真、MoveIt 抓取和 Humble/Fortress 验证文档保留在
`ur3e` 分支，作为继承资产验证记录，不是当前 xArm 850 的实现状态。

## 按需查阅

| 文档 | 用途 |
| --- | --- |
| [系统架构](SYSTEM_ARCHITECTURE.md) | 子系统、接口、TF 和任务执行关系 |
| [xArm 850 Jazzy Docker 基线](../docker/jazzy/README.md) | 软件版本、官方依赖和环境细节 |
| [决策记录](DECISIONS.md) | 已确认的工程选择、依据和验证边界 |
| [已知问题](KNOWN_ISSUES.md) | 当前阻塞项、风险和证据限制 |
| [假设与待确认事项](ASSUMPTIONS.md) | 尚未获得实测证据的输入条件 |
| [第一阶段学习路线](PHASE1_MINIMUM_LEARNING_ROADMAP.md) | 仿真阶段的技术栈与学习材料 |
| [夹爪设计与验证](GRIPPER_DESIGN.md) | 汇总上一组夹爪结构、实验结果、风险和首轮测试 |
| [CAD 资产清单](CAD_INVENTORY.md) | 记录收到的 CAD、校验信息和后续导出要求 |
| [仿真到实机差异记录](SIM2REAL_LOG.md) | 持续记录模型假设、实测结果和修正验证 |
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

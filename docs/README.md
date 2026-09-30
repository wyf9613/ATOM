# Project ATOM 文档导航

本目录存放项目的可维护文档。日常开发不需要逐份阅读；先使用下面的三个入口，
遇到具体问题时再查专题记录。

理解当前运行链路请先看 [当前实现架构：package、node、通信与 GUI](SYSTEM_ARCHITECTURE.md)，包含总览、时序和可选控制链路图。

## 推荐阅读顺序

1. [当前阶段、纯机械臂仿真与代码结构](ARM_ONLY_SIMULATION.md)：当前开发的主入口。
2. [当前状态](PROJECT_STATUS.md)：已经有什么、还缺什么、各开发门是否通过。
3. [项目范围](PROJECT_SCOPE.md)：Stage 0–4、范围内外和验收框架。

UR3e 的已实现仿真、MoveIt 抓取和 Humble/Fortress 验证文档保留在
`ur3e` 分支，作为继承资产验证记录，不是当前 xArm 850 的实现状态。

## 按需查阅

| 文档 | 用途 |
| --- | --- |
| [当前实现架构](SYSTEM_ARCHITECTURE.md) | 当前 package/node 数量、运行图、消息/Action/Service、GUI 与仿真协同 |
| [架构 roadmap](SYSTEM_ARCHITECTURE_ROADMAP.md) | 原有学期/未来移动底盘目标架构；规划而非已实现能力 |
| [xArm 850 Jazzy Docker 基线](../docker/jazzy/README.md) | 软件版本、官方依赖和环境细节 |
| [决策记录](DECISIONS.md) | 已确认的工程选择、依据和验证边界 |
| [已知问题](KNOWN_ISSUES.md) | 当前阻塞项、风险和证据限制 |
| [假设与待确认事项](ASSUMPTIONS.md) | 尚未获得实测证据的输入条件 |
| [第一阶段学习路线](PHASE1_MINIMUM_LEARNING_ROADMAP.md) | 仿真阶段的技术栈与学习材料 |
| [夹爪设计与验证](GRIPPER_DESIGN.md) | 汇总上一组夹爪结构、实验结果、风险和首轮测试 |
| [CAD 资产清单](CAD_INVENTORY.md) | 记录收到的 CAD、校验信息和后续导出要求 |
| [仿真到实机差异记录](SIM2REAL_LOG.md) | 持续记录模型假设、实测结果和修正验证 |
| [腕部相机与观察实验](CAMERA_EXPERIMENT.md) | 当前场景、预观察与两段接近的接口、运行命令及验证边界 |
| [RGB 与 RGB-D 单例精度对比](RGB_VS_RGBD_SINGLE_RUN_COMPARISON_20260925.md) | 两例成功运行的终点误差和逐帧定位误差；与独立重复试验区分 |
| [阶段性 HTML 报告](../output/slides/ATOM_observation_progress_2026-09-25.html) | 英文展示页：定位方案、三段轨迹、演示视频、精度对比和下一步 |
| [相关工作与论文索引](RELATED_WORK.md) | 按项目问题整理本地论文、证据边界和可用于报告的 related-work 初稿 |
| [技术 roadmap](technical_roadmap/README.md) | 文献支持的路线、Phase 4a/4b 动态避障、RGB/RGB-D 比较与感知 waypoint 方案 |

## 文档职责

- **确认事实**写入 `PROJECT_STATUS.md`，重要工程选择同时写入 `DECISIONS.md`。
- **尚未确认的事实**写入 `ASSUMPTIONS.md`。
- **已经发现的问题和风险**写入 `KNOWN_ISSUES.md`。
- **项目要做和不做什么**只在 `PROJECT_SCOPE.md` 定义。
- **系统如何拆分和连接**只在 `SYSTEM_ARCHITECTURE.md` 定义。
- **实测与仿真不一致**写入 `SIM2REAL_LOG.md`。
- 定量结论必须注明单位、测试条件、样本数和不确定度或离散程度。

计划文档描述的是拟开展工作，不代表功能已经实现。

- [操作 GUI 接口](OPERATOR_GUI_INTERFACES.md)：监控、任务/停止接口与部署接线；[运行说明](../tools/operator_gui/README.md)。

- [任务组合与重构建议](TASK_COMPOSITION.md)：诊断当前实验 node 的耦合，区分原子能力、node 和任务配方；建议尚未实现。

- [模块与任务组合：本次重构](MODULES_AND_TASKS.md)：已实施的能力模块、复用配方、node 边界及当前限制。
- [重构回归报告](REFACTOR_TEST_REPORT.md)：构建、组合故障测试及实际 Gazebo 回归证据。

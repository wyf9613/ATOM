# Project ATOM 文档入口

整理日期：2026-10-06。先从当前状态和对应专题进入；计划、软件实现、仿真结果、实物测量分别标明，不把接口存在或某次 PASS 当成完整系统验收。

## 日常只需这三个入口

1. **[当前状态与下一步](PROJECT_STATUS.md)**：已有能力、证据边界、阻塞项和近期工作。
2. **[当前系统架构](SYSTEM_ARCHITECTURE.md)**：模块、节点、数据路径、操作入口及实机接入边界。
3. **[当前夹爪接入计划](gripper/GRIPPER_INTEGRATION_PLAN.md)**：传感器调整期间可做什么、调整后如何标定与接入。

启动仿真看 [仿真运行说明](simulation/ARM_ONLY_SIMULATION.md) 和 [仓库运行入口](../README.md)；操作夹爪看 [现有夹爪接口/台架说明](gripper/GRIPPER_SYSTEM_INTEGRATION.md)；定位一次试验的结果看下方实验索引。

## 目录与职责

```text
docs/
  README.md                 文档导航
  PROJECT_STATUS.md         当前状态与工作优先级
  PROJECT_SCOPE.md          项目范围与阶段验收
  SYSTEM_ARCHITECTURE.md     当前实现结构
  DECISIONS.md              确认选择及依据
  ASSUMPTIONS.md            待确认输入
  KNOWN_ISSUES.md            未解决问题与历史诊断
  SIM2REAL_LOG.md            仿真/实物差异
  gripper/                  夹爪固件、调试、接入与验证
  perception/               腕部相机、Tag与深度融合
  mechanical/               CAD与安装结构说明
  architecture/             模块组合、GUI接口与未来架构
  simulation/               仿真启动与基线
  experiments/              测试报告与历史快照
  research/                 学习路线、论文索引和bibliography
  technical_roadmap/        原有LaTeX技术路线项目
```

根目录只保留八份通用文档。专题文件保留原文件名；原始 PDF/CAD 仍在项目原位置。`technical_roadmap/` 的项目内部组织保持完整。

## 通用工程台账

| 查什么 | 入口 | 如何理解 |
| --- | --- | --- |
| 做哪些任务、如何分阶段验收 | [项目范围](PROJECT_SCOPE.md) | 目标与约束，不等于当前已完成 |
| 已确认版本、接口与工程选择 | [决策记录](DECISIONS.md) | 按日期/决策依据看，后续明确修正取代旧设置 |
| 未测量/未确认的输入 | [假设](ASSUMPTIONS.md) | 当前待确认项优先；历史问题需结合最新证据 |
| 阻塞、故障与复现限制 | [已知问题](KNOWN_ISSUES.md) | 先读顶部当前摘要，再追查历史诊断 |
| 仿真参数与实物之间的差异 | [Sim2Real](SIM2REAL_LOG.md) | 每个差异都需测量或验证关闭 |

## 专题资料索引

- [五孔 MDF 比色皿架：激光切割初稿、尺寸、装配及试切](mechanical/CUVETTE_RACK_LASER_V1.md)

### 夹爪：优先阅读现有接口和接入计划

| 文档 | 信息角色 |
| --- | --- |
| [系统接入与校准边界](gripper/GRIPPER_SYSTEM_INTEGRATION.md) | 当前 UI/ROS/串口接口与 G01–G09；位置完成不代表夹持 |
| [Integration Plan](gripper/GRIPPER_INTEGRATION_PLAN.md) | 拟实施 P0–P5；传感器调整、接触验证和联合任务门槛 |
| [旧代码对照](gripper/LEGACY_GRIPPER_CODE_REVIEW.md) | EE.zip/GitHub 证据、缺陷及可借鉴项 |
| [实物与软件验证日志](gripper/GRIPPER_VALIDATION_LOG.md) | 各次试验条件、失败、修正和结果；追溯证据 |
| [往返扫测](gripper/GRIPPER_SWEEP_TEST.md) | 空载位置测试用法与结果语义 |
| [电机调试](gripper/GRIPPER_MOTOR_COMMISSIONING.md) | 接线、供电、门槛与人工调试；旧参数见日期修正 |
| [ESP32 传感器 bring-up](gripper/ESP32_GRIPPER_BRINGUP.md) | 原传感器装配下的采集/调试过程，调整后需复验 |
| [继承夹爪设计](gripper/GRIPPER_DESIGN.md) | 上一组报告中的结构、试验和风险，不是本组验收 |

| [夹爪标准力标定](gripper/GRIPPER_FORCE_CALIBRATION.md) | 固定物体持有验收、标准力采集与目标力开放条件 |

### 感知与仿真

| 文档 | 信息角色 |
| --- | --- |
| [相机与观察实验](perception/CAMERA_EXPERIMENT.md) | 粗输入、架身份、观察/接近流程与运行接口 |
| [RGB-D 架面融合](perception/DEPTH_FUSION.md) | 已实现的多 Tag/RGB与深度平面融合、质量与回退规则 |
| [Eye-in-hand 取管计划](perception/EYE_IN_HAND_TUBE_PICK_PLAN.md) | 视觉取管方案与后续集成目标；当前取放能力见状态页 |
| [机械臂仿真说明](simulation/ARM_ONLY_SIMULATION.md) | 纯臂、固定目标搬运与其他运行模式 |
| [Docker/版本基线](../docker/jazzy/README.md) | 已记录环境与 vendor 固定版本 |

### 机械与架构

| 文档 | 信息角色 |
| --- | --- |
| [CAD 资产清单](mechanical/CAD_INVENTORY.md) | 原始 CAD 来源与处理约定；派生结构另看 source_cad |
| [相机支架概念与版本](mechanical/GRIPPER_CAMERA_BRACKET_CONCEPT.md) | 概念历史、当前 CAD 版本链接及实物待验证项 |
| [紧固件长度候选](mechanical/FASTENER_SIZING_CAD.md) | 尺寸计算与安装核对，未完成承载验证 |
| [背板 v2](../source_cad/backplate/v2/README.md)、[相机支架 v2](../source_cad/camera_bracket/v2/README.md)、[ESP32 支架 v1](../source_cad/esp32_bracket/v1/README.md) | 对应 CAD 当前版本与几何来源 |
| [模块与任务组合](architecture/MODULES_AND_TASKS.md) | 已实施的能力提取、配方与节点职责 |
| [任务组合原诊断](architecture/TASK_COMPOSITION.md) | 重构前诊断与后续跨节点接口建议；已实施部分看上一项 |
| [GUI 接口](architecture/OPERATOR_GUI_INTERFACES.md) | 监控、Observe 控制与实机接口边界；夹爪增量看夹爪系统接入文档 |
| [未来系统架构](architecture/SYSTEM_ARCHITECTURE_ROADMAP.md) | 长期规划，不是当前运行图 |

### 实验与历史快照

| 文档 | 信息角色 |
| --- | --- |
| [2026-10-01 Tag/rack 复测](experiments/TAG_RACK_TEST_20261001.md) | RGB失败、粗输入/多Tag重构与融合回归证据 |
| [2026-09-30 重构回归](experiments/REFACTOR_TEST_REPORT.md) | 当时构建、软件和 Gazebo 检查；保留当时包数量与条件 |
| [2026-09-25 RGB/RGB-D 单例对比](experiments/RGB_VS_RGBD_SINGLE_RUN_COMPARISON_20260925.md) | 融合前的两例仿真对照，不能用于当前融合效果或成功率估计 |
| [旧状态页](experiments/PROJECT_STATUS_HISTORY_20260925_20260930.md) | 整理前全文及后续过程记录，部分状态已过期 |
| [旧架构快照](experiments/SYSTEM_ARCHITECTURE_SNAPSHOT_20260930.md) | 旧 node/topic/运行图解释；当前实现看根目录架构页 |
| [阶段性展示](../output/slides/ATOM_observation_progress_2026-09-25.html) | 当时对外展示材料，保留历史口径 |

### 学习与研究

| 文档 | 信息角色 |
| --- | --- |
| [第一阶段学习路线](research/PHASE1_MINIMUM_LEARNING_ROADMAP.md) | 学习材料与完成定义，实际完成情况看状态页 |
| [相关工作](research/RELATED_WORK.md)、[文献库](research/RELATED_WORK.bib) | 研究索引与引用；论文能力不是本组实现能力 |
| [LaTeX 技术路线](technical_roadmap/README.md) | 原有技术路线项目、正文与 bibliography |

## 后续文档维护

- 新事实先更新对应专题；当前摘要只在 PROJECT_STATUS 汇总并链接证据，避免在多个总览重复整段实验日志。
- 确认选择写 DECISIONS；未知输入写 ASSUMPTIONS；故障写 KNOWN_ISSUES；仿真/实物差异写 SIM2REAL_LOG。这些固定路径继续保留。
- 同一专题优先更新原文件；新试验按数据集/里程碑写报告，不为每次聊天新增一份总览或计划。
- 每份专题标明日期、实现/计划/历史角色和验收边界。旧建议有后续实现时，添加“被何文档/版本取代”，保留原始失败和数据。
- 定量结论记录单位、条件、样本数与不确定度；临时数据用 tmp，原始交接 CAD/PDF 不搬动或改写。
- 移动文件须同步 Markdown、仓库内文本路径和 LaTeX 引用。文件名保持稳定，便于全文检索与 Obsidian 名称链接。

新增 main 资料：[新法兰与夹爪模型集成](mechanical/GRIPPER_MOUNT_V2_INTEGRATION.md)，记录 CAD 坐标恢复、模块化 URDF/SRDF、碰撞覆盖及实机接入边界。

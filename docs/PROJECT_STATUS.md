# Project ATOM 当前状态

> 2026-10-07 main 同步：当前位置命令使用连续 MOVE，人工微调仍使用 JOG；普通 STOP/cancel 在确认保持后允许恢复，实际故障仍受门槛约束。Linux Jazzy 构建及假串口 ROS Action 联调已有通过记录，前端实物接入有用户反馈；接触/力标定、带物体停止与机械臂联合任务仍未验收。

更新：2026-10-07。本文根据当前代码、既有试验记录和用户确认汇总；本次文档整理没有进行新的实物或 ROS/Gazebo 验收。整理前的状态与过程全文见 [历史快照](experiments/PROJECT_STATUS_HISTORY_20260925_20260930.md)。

## 当前阶段与结论

项目仍处于继承资产验证和架构定义阶段，已有机械臂仿真/视觉接近基线，以及独立的 ESP32 夹爪空载位置测试。**真实视觉抓取、带物体转运、仪器插入、释放和移动操作系统尚未完成验收。**

当前重点：用户已说明末端传感器需要调整。先推进可复用接口与假设备联调；调整后冻结配置，测量基线/接触/力和停止行为，再开放接触闭合与机械臂联合任务。见 [夹爪接入计划](gripper/GRIPPER_INTEGRATION_PLAN.md)。

## 按子系统看已有内容与证据

| 子系统 | 已实现/已有证据 | 尚不能据此声称 | 主要来源 |
| --- | --- | --- | --- |
| 机械臂软件基线 | 已记录的 Docker Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic 与固定 vendor 栈；既有纯臂规划、执行及固定目标搬运仿真通过 | 实物 arm driver、硬件停止、模型辨识或真实搬管已验收；本机当前环境状态不能由历史构建推断 | [仿真说明](simulation/ARM_ONLY_SIMULATION.md)、[版本基线](../docker/jazzy/README.md)、[回归报告](experiments/REFACTOR_TEST_REPORT.md) |
| 视觉观察/接近 | 一个 task executive 按配方执行观察/接近；同帧多 Tag 架估计、粗 rack XY 输入、对齐/有界重对齐；RGB-D 深度平面已参与位姿融合 | 透明试管直接深度识别、独立重复可靠性、真实手眼/TCP精度或完整取放 | [相机实验](perception/CAMERA_EXPERIMENT.md)、[融合](perception/DEPTH_FUSION.md)、[复测](experiments/TAG_RACK_TEST_20261001.md) |
| 定制夹爪 | ESP32 磁场采集、位置模式 MOVE/JOG、反馈/心跳/故障门槛和日志；一次空载重复扫测完成，当前接触入口与 force 控制仍受阻断 | 已标定力、可靠接触/稳定夹持、调整后传感器参数或带物体停止已验收 | [验证日志](gripper/GRIPPER_VALIDATION_LOG.md)、[现有接口](gripper/GRIPPER_SYSTEM_INTEGRATION.md) |
| UI与ROS夹爪接口 | 本地/ROS适配、共享串口 controller、ControlGripper、控制权 lease 和薄任务能力已有代码；主机测试及 Linux 假串口 ROS Action 联调通过；前端实物接入有用户反馈 | 定量实物验收已完成，或 Close 成功代表夹稳 | [系统接入](gripper/GRIPPER_SYSTEM_INTEGRATION.md)、[旧代码对照](gripper/LEGACY_GRIPPER_CODE_REVIEW.md) |
| 仿真操作界面 | 默认视觉流程监控；独立 Observe 模式具有 Gazebo 任务/停止/取消验证 | 默认视觉任务已统一到网页命令/系统停止，或仿真停止能保证实机安全 | [GUI接口](architecture/OPERATOR_GUI_INTERFACES.md)、[架构](SYSTEM_ARCHITECTURE.md) |
| 描述与机械适配 | 模块化 arm/gripper description；背板v2、相机支架v2及ESP32支架v1的派生CAD/紧固件候选 | 结构承载、打印装配、碰撞、惯性/TCP与安装TF已实测合格 | [CAD清单](mechanical/CAD_INVENTORY.md)、[紧固件](mechanical/FASTENER_SIZING_CAD.md)、[Sim2Real](SIM2REAL_LOG.md) |
| 系统任务/安全/底盘 | 能力与配方组合规则、接口与后续计划已定义，部分仿真监督实现 | 完整实机任务、硬件急停合规、共享空间避障、底盘定位/导航/端到端操作完成 | [模块](architecture/MODULES_AND_TASKS.md)、[范围](PROJECT_SCOPE.md)、[问题](KNOWN_ISSUES.md) |

## 最有代表性的验证边界

- **夹爪空载位置**：2026-10-03，用户报告滑轨润滑且 raw load 阈值80，N=1次运行、3轮/72段、名义2000–2600编码器计数，最大编码器误差3计数、约100ms采样负载峰值52 raw。编码器与负载结果不等于mm精度或N；调整后需按变化范围复验。原始目录及条件见 [日志](gripper/GRIPPER_VALIDATION_LOG.md)。
- **主机软件**：2026-10-06旧代码审查期间21项既有夹爪主机测试通过，使用假设备，未打开实物串口；不代表ROS进程、停止时延或接触力通过。见 [审查边界](gripper/LEGACY_GRIPPER_CODE_REVIEW.md)。
- **融合仿真**：2026-10-01记录包含实际融合输出及完整接近回归。单运行内的相关图像帧是位姿对照，不是独立试验样本；误差相对名义仿真几何，不能解释为实物精度。见 [方法与记录](perception/DEPTH_FUSION.md)。
- **重构仿真**：2026-09-30构建与Gazebo回归报告中的包数量、次数和参数是当时快照；当前代码新增夹爪硬件包，其Linux ROS假串口联调已有通过记录，实机系统验收仍待完成。见 [原报告](experiments/REFACTOR_TEST_REPORT.md)。

## 继承资产与输入状态

| 资产/输入 | 当前状态 |
| --- | --- |
| 上一组报告与夹爪CAD | 已收到；原件在 previous report/ 和 hardware/，只读保留；[继承设计](gripper/GRIPPER_DESIGN.md)汇总原报告证据 |
| 上一组软件 | 2026-10-06收到Downloads中的EE.zip和GitHub参考；含Arduino实验代码和ROS末端位姿发布器；实际部署版本、完整系统接线及旧试验原始数据仍未齐全，未将ZIP原件迁入硬件资产目录 |
| 本组夹爪接线/调试 | 已有ESP32引脚、串口/传感器与STS位置反馈记录；电气规格、载荷/停止包络和调整后的传感器配置仍需核对 |
| 机械臂 | 历史交接/决策记有UFactory xArm 850到货；实物控制器、固件、附件/标定和实际驱动兼容性仍待清点与验收，不由仿真型号推定 |
| 相机/安装/TCP | 相机型号尚待核实，支架CAD不等于安装测量；tag-to-slot、hand-eye、mount/TCP、惯性和碰撞尚待实测 |
| 仪器/底盘/工作流 | 仪器访问、真实容差/成功定义及底盘接口尚未冻结 |

## 开发门与优先级

| 门 | 状态 | 下一步证据 |
| --- | --- | --- |
| 1. 继承资产理解 | 部分完成 | 核对部署固件/接线、实物结构与参数、旧数据来源 |
| 2. 夹爪描述 | 软件检查已有，实物验证未关闭 | 开口、质量/惯性、TCP与简化碰撞测量 |
| 3. arm+gripper模型 | 模块化描述已有，安装与联合控制未关闭 | mount/TF、SRDF/碰撞、真实驱动边界 |
| 4. 固定底座仿真基线 | 纯臂及视觉接近已有结果；完整取放未关闭 | 对象接触/持有、规划场景、联合配方与重复试验 |
| 5. 真实机械臂接入 | 未验收 | 控制器/固件清点、真实输入、监督与停止/TCP测量 |
| 6. 视觉抓取与放置 | 接近已实现；夹持/搬运/释放未验收 | 传感器调整及G01–G09、独立夹持证据和受监督转运 |
| 7. 移动集成 | 未验收 | 底盘接口、定位/停靠、载荷/电源与系统试验 |

近期工作按两条线推进：

1. **夹爪主线**：P0接口/假设备 → 传感器配置冻结 → 基线/力/停止测量 → 本地接触闭合 → ROS/UI台架 → 机械臂联合任务。所有新能力仍是 [计划](gripper/GRIPPER_INTEGRATION_PLAN.md)。
2. **仿真与系统线**：保留当前视觉/纯臂回归，继续定位RGB端点IK间歇失败；补真实TF/TCP、统一停止/取消和工位碰撞输入。不要通过放宽限值或接受仿真抓取成功来开放实机。

具体责任与台账：[DECISIONS](DECISIONS.md)记录确认选择，[ASSUMPTIONS](ASSUMPTIONS.md)记录未知输入，[KNOWN_ISSUES](KNOWN_ISSUES.md)记录故障/阻塞，[SIM2REAL_LOG](SIM2REAL_LOG.md)记录模型差异。原始背景与未来目标不作为实现证据。

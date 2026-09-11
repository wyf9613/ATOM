# Project ATOM 相关工作与论文索引

更新日期：2026-09-11

## 1. 使用范围

本文档围绕 ATOM 当前任务检索和整理文献：移动机器人到达工位、工位相对定位、试管抓取与运输、接触式插入/放置、仪器交互、任务编排、验证与故障处理。

文献中的结果只说明相应作者在其硬件、环境和测试条件下完成了验证，不能作为 ATOM 已实现功能的证据。特别是：

- LAPP、TARMAC 和 ADePT 主要提供架构、分类或评估框架；
- arXiv 论文必须标明预印本状态；
- 使用专用夹具、标志物、触觉探针或设备改造的结果，不能直接外推到 ATOM 的试管和目标仪器；
- 软件停止、避障或人感知研究不能证明硬件急停或安全合规。

## 2. 建议阅读顺序

### P0：直接影响 ATOM 近期设计

1. **Butterworth et al. (2023), Leveraging Multi-modal Sensing for Robotic Insertion Tasks in R&D Laboratories**
   直接研究玻璃小瓶插架，比较视觉、力和触觉反馈。对 ATOM 的试管插入、搜索策略、接触判据和失败检测最有参考价值。

2. **Scamarcio et al. (2025), Reliable and Robust Robotic Handling of Microplates via Computer Vision and Touch Feedback**
   展示“SLAM 粗到达 -> 标志物视觉定位 -> 接触式精定位 -> 放置”的完整分层定位链，和 ATOM 的工位 A/B 方案高度对应。

3. **Angelopoulos et al. (2023), High-Accuracy Injection Using a Mobile Manipulation Robot for Chemistry Lab Automation**
   说明移动底盘和抓取误差不能仅靠全局导航解决；设备端相机和视觉伺服适合高精度末端对准。

4. **Legowik, Bostelman and Hong (2016), Sensor Calibration and Registration for Mobile Manipulators**
   提供移动底盘、机械臂和工位之间的坐标注册与重复性测量方法，可用于设计 ATOM 的标定试验。

5. **Wan, Kotaka and Harada (2022), Arranging Test Tubes in Racks Using Combined Task and Motion Planning**
   对试管识别、抓取姿态、碰撞约束、任务级重排和执行反馈进行组合规划，适合支撑 ATOM 的试管架场景。

### P1：支撑感知、柔顺和系统架构

6. **Pai et al. (2023), Precise Well-plate Placing Utilizing Contact During Sliding with Tactile-based Pose Estimation**
   研究小间隙放置、抓取后物体位姿不确定性以及利用接触约束完成精对准。其对象不是试管，但方法与插入/落座任务相近。

7. **Makarova et al. (2024), LucidGrasp**（arXiv 预印本）
   讨论透明或半透明实验器皿的 6D 位姿估计、液位/瓶口感知和基于数字孪生的动作预检。应作为感知候选方案，而不是当前已选技术。

8. **Darvish et al. (2025), ORGANA**
   展示视觉反馈、长时序实验任务、资源调度和人在回路交互。对 ATOM 的任务执行器、日志和异常上报有参考价值；LLM 接口不是近期基线的必要条件。

9. **Wolf et al. (2024), LAPP Reference Architecture Model**
   给出实验室工作流、设备、机器人活动和控制层级的模块化分解，适合检查 ATOM 接口边界。它是参考架构，不是现成实现。

10. **Huang et al. (2025), TARMAC**（arXiv 预印本）
    提供化学机器人操作分类，可用于建立 ATOM 的技能清单、覆盖矩阵和未覆盖能力列表。

### P2：背景与扩展阅读

11. **Schober et al. (2025), Vision-based Robot Manipulation of Transparent Liquid Containers**
    针对透明容器液量估计和小开口倾倒，适合长期扩展到液体处理，但不是当前“运输试管并操作仪器”的最短路径。

12. **Wolf et al. (2023), LAPP Digital Twin**
    讨论设备坐标系、标志物、数字孪生和免示教集成。文中部分内容是概念性提案，引用时必须写成 proposed framework。

13. **Salazar-Villacis and Benyahia (2026), ADePT**
    从适应性、灵巧性、感知和任务复杂度四个维度评估实验室机器人。适合用来检查验收指标覆盖范围，不替代 ATOM 自己的测试协议。

14. **Burger et al. (2020) 与 Dai et al. (2024)**
    展示大型移动化学平台如何连接多个工作站。它们依赖结构化环境、专用站点和大量基础设施，只适合作为系统级长期参照。

## 3. 按研究问题整理

| 研究问题 | 关键论文 | 对 ATOM 的可迁移结论 | 主要限制 |
| --- | --- | --- | --- |
| 移动后如何达到操作精度 | Angelopoulos 2023；Scamarcio 2025；Legowik 2016；Burger 2020 | 使用分层定位：导航粗到达、工位相对观测、末端闭环精对准；分别测量每层误差 | 多数系统使用标志物、接触基准或设备端相机 |
| 试管/小瓶如何可靠插入 | Butterworth 2023；Pai 2023；Wan 2022 | 视觉给出初始位姿，力/触觉/受约束搜索处理最后几毫米的不确定性；失败应触发退出或重试 | 对象、间隙、材料、夹具和传感器与 ATOM 不同 |
| 透明器皿如何感知 | Makarova 2024；Schober 2025；ORGANA 2025 | 透明物体通常需要专门数据、几何先验或多模态感知；必须在 ATOM 的照明和背景下重新测试 | 预印本和特定数据集结果不能证明现场泛化 |
| 多步骤任务如何组织 | Yoshikawa 2023；Wan 2022；ORGANA 2025 | 显式动作前置条件、运动可行性检查、状态验证和重新规划比固定路点更适合长流程 | 完整 TAMP/LLM 系统可能超出 Capstone 的实现成本 |
| 多设备如何模块化集成 | Wolf 2023；Wolf 2024；Dai 2024 | 设备坐标系、设备能力、机器人技能和调度接口应分层；仪器动作应定义在设备坐标系中 | LAPP 的部分内容是参考模型或概念方案 |
| 如何评价系统能力 | ADePT 2026；TARMAC 2025；Falco et al. 2020 | 把感知、灵巧性、任务复杂度、夹爪性能和恢复能力拆开测试；保留测试条件和原始结果 | 分类框架不提供 ATOM 的具体合格阈值 |

## 4. 可用于报告的 related-work 初稿

现有自主化学实验室大致分为专用自动化平台和通用机器人平台。专用平台通常通过固定管路、液体处理器和定制工作站获得高通量与重复性；通用移动操作平台则试图在面向人的现有实验室中复用仪器。Burger 等和 Dai 等的系统证明了移动机器人可以连接空间分散的工作站，但这些系统仍依赖结构化环境、专用夹具、设备改造和明确的实验流程。因此，ATOM 不应把大型自主化学平台的系统规模作为近期交付目标，而应提取其分层定位、模块化工位和任务编排原则。

移动操作的核心难点不是单纯到达工位，而是将导航误差逐层收敛到操作允许范围。Angelopoulos 等使用设备端视觉与视觉伺服处理高精度注射；Scamarcio 等结合 SLAM、标志物视觉和接触式精定位完成实验室器皿放置；Legowik 等则从坐标注册和测量角度分析移动底盘、机械臂与工位之间的关系。这些工作共同支持 ATOM 采用“全局导航 -> 工位相对定位 -> 末端闭环对准”的架构，并分别记录各阶段的位姿误差，而不是把精密插入建立在移动底盘的名义位姿上。

试管放置属于接触丰富且容差较小的操作。Butterworth 等针对小瓶插架比较了视觉、力和触觉反馈，Pai 等利用接触滑动与触觉位姿估计处理小间隙放置，Wan 等则把试管识别、抓取和重排纳入任务与运动规划。这些结果表明，视觉适合提供接触前的初始估计，而最终落座更适合结合低速受约束运动、力或触觉事件以及显式的失败退出条件。对 ATOM 而言，是否需要力/力矩传感器、触觉传感器或机械导向，仍必须由真实试管、插入口公差和接触力测试决定。

长时序实验任务还要求机器人能够表达前置条件、验证动作结果并处理失败。Yoshikawa 等使用受约束任务与运动规划将化学步骤映射为可执行动作，ORGANA 进一步加入视觉反馈、资源调度和人在回路交互；LAPP 系列工作则从设备坐标系、数字孪生和控制层级角度讨论可复用集成。ATOM 可以采用较轻量的显式状态机或行为树实现这些原则：每个技能具有进入条件、超时、成功判据和安全退出路径，并在确定性基线稳定后再评估更复杂的学习或语言模型组件。

## 5. 当前文献仍未解决的 ATOM 问题

- 很少有工作在同一系统中同时验证移动导航、试管抓取、运输姿态、开盖、插入、关盖、按钮操作和故障恢复。
- 现有论文使用的小瓶、试管架、微孔板、注射器和仪器接口与 ATOM 目标对象不同，不能直接给出允许误差或接触力。
- 多数工作在结构化工位中运行；对人员进入、遮挡、工位移动和误操作的系统性压力测试有限。
- 很多论文展示成功率，但未统一报告失败类型、恢复次数、测试分布和跨日重复性。
- 感知论文往往依赖专门数据集和固定照明；透明试管在 ATOM 现场背景下的误差仍需独立测量。
- 现有研究不能替代硬件急停、保护停止、风险评估和正式安全验证。

## 6. 对 ATOM 下一阶段的具体建议

1. 把工位定位误差分成导航、工位相对定位、手眼/TCP、抓取后物体偏差和接触对准五项分别测量。
2. 先实现标志物或已知几何的确定性工位定位，再用试验判断是否需要视觉伺服、力反馈或触觉。
3. 为试管插入建立三种递进基线：开环慢速插入、视觉修正插入、接触反馈搜索；使用相同扰动集比较。
4. 为夹爪记录开口范围、夹持力、手指重复性、循环时间、滑移和破损结果；测试协议可参考 Falco 等的末端执行器基准。
5. 任务层使用显式状态和前置条件，至少覆盖空夹、目标缺失、路径失败、接触超限、插入失败和超时。
6. 每项实验记录对象尺寸与质量、夹具、传感器、软件版本、样本数、扰动分布、均值/离散程度和失败原因。

## 7. 本地论文文件

以下 12 篇为本次新增，均已完成 PDF 解析和首页渲染检查：

- [ORGANA_Robotic_Assistant_for_Automated_Chemistry_Experimentation.pdf](../paper/paper/ORGANA_Robotic_Assistant_for_Automated_Chemistry_Experimentation.pdf)
- [Leveraging_Multimodal_Sensing_for_Robotic_Vial_Insertion.pdf](../paper/paper/Leveraging_Multimodal_Sensing_for_Robotic_Vial_Insertion.pdf)
- [Arranging_Test_Tubes_in_Racks_Using_Task_and_Motion_Planning.pdf](../paper/paper/Arranging_Test_Tubes_in_Racks_Using_Task_and_Motion_Planning.pdf)
- [LucidGrasp_Transparent_Labware_6D_Pose_Estimation.pdf](../paper/paper/LucidGrasp_Transparent_Labware_6D_Pose_Estimation.pdf)
- [Vision_Based_Manipulation_of_Transparent_Liquid_Containers.pdf](../paper/paper/Vision_Based_Manipulation_of_Transparent_Liquid_Containers.pdf)
- [Precise_Well_Plate_Placing_with_Tactile_Pose_Estimation.pdf](../paper/paper/Precise_Well_Plate_Placing_with_Tactile_Pose_Estimation.pdf)
- [LAPP_Digital_Twin_for_Teaching_Free_Robot_Integration.pdf](../paper/paper/LAPP_Digital_Twin_for_Teaching_Free_Robot_Integration.pdf)
- [LAPP_Reference_Architecture_for_Robot_Integration.pdf](../paper/paper/LAPP_Reference_Architecture_for_Robot_Integration.pdf)
- [Reliable_Robotic_Handling_of_Microplates_Vision_and_Touch.pdf](../paper/paper/Reliable_Robotic_Handling_of_Microplates_Vision_and_Touch.pdf)
- [Sensor_Calibration_and_Registration_for_Mobile_Manipulators.pdf](../paper/paper/Sensor_Calibration_and_Registration_for_Mobile_Manipulators.pdf)
- [ADePT_Framework_for_Assessing_Autonomous_Laboratory_Robotics.pdf](../paper/paper/ADePT_Framework_for_Assessing_Autonomous_Laboratory_Robotics.pdf)
- [TARMAC_Taxonomy_for_Robot_Manipulation_in_Chemistry.pdf](../paper/paper/TARMAC_Taxonomy_for_Robot_Manipulation_in_Chemistry.pdf)

对应 BibTeX 见 [RELATED_WORK.bib](RELATED_WORK.bib)。

## 8. 在线补充阅读

- Falco et al., *Benchmarking Protocols for Evaluating Grasp Strength, Grasp Cycle Time, Finger Strength, and Finger Repeatability of Robot End-effectors*: https://doi.org/10.1109/LRA.2020.2964164
- Tom et al., *Self-Driving Laboratories for Chemistry and Materials Science*: https://doi.org/10.1021/acs.chemrev.4c00055
- ISO 10218-1:2025 与 ISO 10218-2:2025：工业机器人及应用安全要求；标准文本与论文的证据用途不同。
- ISO 18646-2:2024 与 ISO 18646-3:2021：服务机器人导航与操作性能测试框架。


## 9. 动态避障与感知路点研究补充（2026-09-11）

以下是本次核验的原始论文/作者机构记录与官方文档；没有新增本地论文 PDF，也未复现论文结果。详细实施方案进入 roadmap 正文 [新增章节](technical_roadmap/shared_workspace_perception.tex)，BibTeX 已同步到本目录及 roadmap 文献库。

| 来源与链接 | 用于哪个问题 | 可迁移内容与边界 |
| --- | --- | --- |
| Marvel & Norcross, *Implementing Speed and Separation Monitoring in Collaborative Robot Workcells*, RCIM 44, 144–155, 2017（在线 2016）[NIST](https://www.nist.gov/publications/implementing-speed-and-separation-monitoring-collaborative-robot-workcells) | 4a 何时停止 | 分解反应、制动、进入量和测量误差；需要本机停止实测，不能照抄距离阈值。 |
| Svarny et al., *Safe physical HRI*, IROS 2019, 7574–7581 [作者稿及出版信息](https://arxiv.org/abs/1908.03046) | 区域检测还是人体关键点 | 对比区域与 RGB-D 骨架间距监控；在 ATOM 中骨架只能细化，未知占用不能因没有识别人而放行。 |
| Zhu et al., *Real-Time Dynamic Obstacle Avoidance for Robot Manipulators Based on Cascaded Nonlinear MPC With Artificial Potential Field*, TIE 71(7), 7424–7434, 2024（在线 2023）[机构记录与作者稿](https://eprints.whiterose.ac.uk/id/eprint/205260/) | 4b 预测与平滑避障 | 高层规划、低层约束跟踪和障碍运动估计；作为模型辨识后的进阶对照，不替代当前确定性基线。 |
| [MoveIt Hybrid Planning 官方文档](https://moveit.picknik.ai/main/doc/examples/hybrid_planning/hybrid_planning_tutorial.html) | 全局换路与局部反应如何集成 | 提供组合架构，需要规划逻辑和失败策略；Rolling 文档不是当前 Jazzy 版本兼容性证据。 |
| [MoveIt Servo 官方文档](https://moveit.picknik.ai/main/doc/examples/realtime_servo/realtime_servo_tutorial.html) | 局部执行与视觉伺服 | 支持指令跟随、碰撞接近降速及奇异性检查；不自动选择绕行路线，不提供安全认证。 |
| Krogius et al., *Flexible Layouts for Fiducial Tags*, IROS 2019；[AprilTag 3 官方实现](https://github.com/AprilRobotics/apriltag)；[OpenCV PnP](https://docs.opencv.org/4.13.0/d5/d1f/calib3d_solvePnP.html) | 单目能否定位三维 waypoint | 已知标记尺寸和内参时估计公制位姿，再组合工位/槽位/TCP 标定；检测框中心不是抓取位姿。 |
| Sajjan et al., *ClearGrasp: 3D Shape Estimation of Transparent Objects for Manipulation*, ICRA 2020 [论文](https://arxiv.org/abs/1910.02550)、[作者实现及会议信息](https://github.com/Shreeyak/cleargrasp) | 为什么 depth camera 仍可能看不准试管 | 透明物体会使原始深度失真；学习补全可作为后续对照，不能作为未经本地测试的精密插入或安全边界。 |

本次结论是工程方案推导：用固定 RGB-D 的 RGB 通道估计架/仪器位姿，深度通道构建未知占用；试管先按结构化槽位与实际存在/姿态核验定位。先实现 4a，再在自由空间运输阶段推进 4b；接触动作停止优先。最终相机、误差阈值与规划插件均需试验确定。

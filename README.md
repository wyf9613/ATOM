# Project ATOM

**ATOM — Autonomous Transport & Object Manipulation for the Autonomous Chemical Laboratory** 是墨尔本大学 2026 S2--2027 S1 的机电一体化 Capstone 项目，目标是逐步构建一个用于自主化学实验室样品运输与物体操作的移动操作平台。

当前处于 **Phase 0：接手、盘点与技术路线确认**。现有成果是上一组的夹爪原型、Fusion 360 装配文件和固定工位实验报告；完整自主实验室系统尚未实现。

## 当前事实

- 上一组使用 UR3e 和人工设定路点，在两个模拟比色皿托盘间完成了 49/50 次完整循环。
- 49/50 的结果不代表真实 Opentrons Flex 到 DynaPro NanoStar 工作流已经验证。
- 继承夹爪为 STS3215 驱动的双指平行夹爪，使用 STM32 Nucleo、硅胶接触垫和磁传感反馈。
- 报告中的夹爪外形约为 225 x 105 x 131 mm，总质量约 580 g。
- 商用机械臂型号、ROS 2 发行版、移动底盘接口、真实仪器访问条件仍待确认。

## 先读这些

1. [项目背景与长期方案](ATOM_Project_Context.md)
2. [当前状态](docs/PROJECT_STATUS.md)
3. [已知问题](docs/KNOWN_ISSUES.md)
4. [系统架构](docs/SYSTEM_ARCHITECTURE.md)
5. [夹爪设计摘要](docs/GRIPPER_DESIGN.md)
6. [CAD 清单](docs/CAD_INVENTORY.md)
7. [技术路线、文献综述与实施计划（LaTeX 源码）](docs/technical_roadmap/main.tex)
8. [第一阶段最小技术栈与学习路线](docs/PHASE1_MINIMUM_LEARNING_ROADMAP.md)
9. [MoveIt 双模式抓放仿真基线](docs/MOVEIT_GRASP_BASELINE.md)

已编译版本见
[ATOM_Technical_Roadmap.pdf](output/pdf/ATOM_Technical_Roadmap.pdf)。该 PDF
由 Git LFS 管理；如果下载后文件只有约 131 字节，请先执行本页“获取仓库后”的
LFS 命令，不要将指针文本当作 PDF 打开。

## 目录

```text
.
|-- ATOM_Project_Context.md        # 项目总体背景与路线
|-- docs/                          # 架构、决策、问题和实验记录
|-- hardware/                      # 当前收到的硬件资料
|-- previous report/               # 上一组原始报告
|-- reference/                     # 外部参考资料索引
|-- source_cad/                    # CAD 来源与导出约定
`-- ros2_ws/                       # ROS 2 仿真验证工作区
```

原始 PDF 和 F3Z 保留在接手时的位置，不在初始化过程中改名或改写。

## 获取仓库后

```bash
git lfs install
git lfs pull
```

本机 Jazzy/Harmonic 用于开发验证；实验室兼容门使用 Ubuntu 22.04、ROS 2
Humble 和 Gazebo Fortress Docker。两者都不是最终真实机械臂驱动选择，相关边界见
[`docs/DECISIONS.md`](docs/DECISIONS.md)。Docker 构建与验收命令见
[`docs/MOVEIT_GRASP_BASELINE.md`](docs/MOVEIT_GRASP_BASELINE.md)。

## 近期里程碑

1. 收齐并校验上一组固件、ROS 代码、接线图和物理夹爪。
2. 确认机械臂型号、交付时间、相机/力传感器和真实仪器访问条件。
3. 完成夹爪运动、传感、标定、TCP 与安装接口的实测。
4. 建立模块化夹爪 URDF/Xacro，再集成厂商官方机械臂描述。
5. 先完成确定性的 MoveIt 2 仿真基线，再引入感知和闭环修正。

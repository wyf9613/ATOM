# 项目当前状态

最后更新：2026-08-21

## 当前阶段

**Phase 0：交接资产核验、需求确认与架构定义。**

目前已有可构建的继承资产仿真基线，但最终部署栈、采购机械臂和移动底盘仍未确认。仿真成果不能写成真实系统已经完成。

## 已实现的软件验证基线

- 模块化 UR3e + 继承夹爪 Xacro；
- 从 STEP 派生的夹爪视觉网格和简化碰撞；
- Gazebo native 与 `ros2_control` 两种后端；
- 独立 MoveIt 配置、RRT-Connect 和 Cartesian 末端段；
- 显式抓取任务状态机；
- 逻辑 attach 与刚体物理接触两种抓取模式；
- Jazzy/Harmonic 开发验证和 Humble/Fortress Docker 兼容环境；
- Humble/Fortress 中逻辑模式 10/10、物理模式 10/10 任务通过；
- 所有 20 次任务完成后都复现 `move_group` 关闭故障，因此干净退出未通过。

详细证据见：

- `docs/CURRENT_SIMULATION_BASELINE.md`；
- `docs/MOVEIT_GRASP_BASELINE.md`；
- `docs/SIM2REAL_LOG.md`；
- `docs/ROS_GAZEBO_MOVEIT_TUTORIAL.md`。

## 主要资产

| 资产 | 状态 | 位置 |
| --- | --- | --- |
| 暂定项目范围 | 已有，待实物确认 | `docs/PROJECT_SCOPE.md` |
| 相关论文 | 本地已有 5 篇，尚未跟踪 | `paper/paper/` |
| 上一组报告 | 已有，34 页 | `previous report/Capstone_Robotic_Hand_Lab_Experiment.pdf` |
| Fusion 360 和 STEP 装配 | 已有 | `hardware/end effector/` |
| 夹爪描述 | 已实现暂定仿真模型 | `ros2_ws/src/atom_gripper_description` |
| UR3e 官方来源 | 已固定验证依赖 | `ros2_ws/atom_sim.repos` |
| MoveIt 验证配置 | 已实现，暂定 | `ros2_ws/src/atom_ur3e_moveit_config` |
| 仿真任务执行器 | 已实现 | `ros2_ws/src/atom_manipulation` |
| STM32 固件、ROS/串口代码、接线和原始数据 | 缺失 | 需要索取 |
| 实际机械臂和移动底盘接口 | 未确认 | 需要采购和合作团队证据 |

## 上一组已经证明

- UR3e 固定工位、人工路点 pick-and-place；
- 模拟托架条件下 49/50 次完整循环；
- 单循环 25.3 s，连续两循环 51.11 s；
- 快拆拆卸约 5 s，N=20。

## 尚未证明

- 真实仪器端到端流程和 +/-0.2 mm 插入精度；
- 真实夹持力低于 5 N；
- 感知引导定位与重规划；
- 空夹、超时、最大行程和完整故障恢复；
- 实际采购机械臂 commissioning；
- 移动底盘导航、对接和误差补偿；
- 开盖、插入、关盖和按键；
- 系统级硬件急停和人机共享空间安全性能。

## 开发门

| 开发门 | 状态 | 通过所需证据 |
| --- | --- | --- |
| 1. 理解继承夹爪 | 未通过 | 实物、固件、接线、参数和传感标定 |
| 2. 夹爪描述 | 进行中 | 仿真 Xacro/网格已通过；实物轴线、限位、惯量、安装和 TCP 待确认 |
| 3. 机械臂 + 夹爪 | 仅验证基线 | UR3e 组合模型已有；采购机械臂未确认 |
| 4. 仿真基线 | 已实现验证基线 | 需修复 teardown，并加入真实几何、标定和故障恢复 |
| 5. 真实机械臂部署 | 阻塞 | 硬件、安装/TCP 和 commissioning |
| 6. 感知引导操作 | 未开始 | 位姿扰动实验优于固定路点 |
| 7. 仪器交互 | 未开始 | 分别验证开盖、插入、关盖和按键 |
| 8. 移动集成 | 未开始 | 底盘接口、对接测量和端到端试验 |
| 9. 人机共享空间 | 未开始 | 风险控制、停止行为和受控试验 |

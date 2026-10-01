# 模块化任务重构：回归报告

日期：2026-09-30；分支：`refactor/modular-task-composition`。重构前工作区先记录为提交 `779ba49`，再实施能力提取和任务组合，便于比较与回退。

## 测试条件与范围

使用项目既有 Docker Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic / MoveIt 环境及固定 vendor 代码；没有选择新的 ROS 版本、驱动、规划器或执行器参数。主机软件渲染，ROS Domain 默认 42；纯软件隔离检查使用 143。实际物理机械臂、无线链路、透明试管深度真实性与硬件急停未参与测试。

新结构保持 5 个自有 ROS package。默认视觉 node 由 `atom_pre_observation_demo` 替换为 `atom_task_executive`；能力提取不新增 ROS node。新增 `task_executive` 可执行入口，原 `pre_observation_demo` 是指向同一实现的兼容入口。

## 已完成的回归

| 检查 | 结果 | 证据 / 说明 |
| --- | --- | --- |
| 完整构建 | 通过 | 13 个选定 package 构建成功；`tmp/operator_gui/modular_full_build.log` |
| 自有 package colcon 检查 | 通过 | 7 tests，0 errors/failures/skipped；`modular_colcon_test.log`，检查五个自有 package 中配置的测试，不意味着每个 package 都有测试 |
| GUI / 传感器 / Tag 几何单元检查 | 16 项通过 | `modular_unit_tests.log` |
| 模块与任务组合检查 | 6 项通过 | 同能力观察前缀复用、缺失能力先于动作拒绝、感知失败阻止后续动作、未知配方拒绝、故障保留已完成步骤、能力模块不创建 node |
| CLI 检查 | 7 项通过 | 参数/配方合法性、作用域、模式分发、限定会话停止、批处理入口与容器 shell 语法 |
| Python / JS / Shell / diff 静态检查 | 通过 | compileall、`node --check`、所有脚本 `bash -n`、`git diff --check` |
| 兼容入口身份检查 | 通过 | `PreObservationDemo is TaskExecutive`；旧 supervisor 入口指向 `safety.sim_supervisor.Supervisor` |
| 深度模式视觉接近 | 通过 | `run_20260930_053800` 完成六个能力步骤；GUI 状态/图像/Tag/关节链路检查通过 |
| RGB 模式只观察配方 | 通过 | `run_20260930_054207` 只完成三个观察步骤，`completed_segments=[]`，没有执行接近 |
| RGB 模式视觉接近 | 通过 | `run_20260930_054456` 完成六个能力步骤及两段接近，GUI 检查通过 |
| GUI 控制型 Observe | 通过 | HTTP→Action→MoveIt/Gazebo；运动中停止、锁定拒绝、1 s 静止采样、复位、标准 Action 取消；`modular_control_check.json` |
| 纯臂关节轨迹 | 通过 | 原 offset/return 流程；最大报告终点关节误差 0.009578 / 0.009040 rad，限值沿用 0.02 rad；`modular_arm_baseline.log` |
| 旧固定目标搬运 | 通过 | 抬升/约束搬运/下降全部完成；仍是模拟抓取成功，未验证试管取放；`modular_transfer_baseline.log` |
| 仿真冒烟 | 通过 | 六关节、控制器、规划与往返执行；`modular_smoke.log` |
| 名义执行器动力学演示 | 通过 | 原 nominal 插件与参数、原轨迹/目标容差；`modular_dynamics.log`；不是实机辨识结果 |

共 29 项 Python 软件检查通过，另有 7 项 colcon 检查通过。各 Gazebo 模式上述记录各一次运行，不用这些样本估计成功率或不确定度。日志、JSON 和 trial reports 位于当前工作区 `tmp/` 或 `.docker-runtime/jazzy_ws/log/`，不提交大型生成文件；本报告提交到分支。

## 新结构的验收点

- 同一 `TaskExecutive` 执行观察/接近两个配方，前者是后者的能力前缀，不增加任务 node。
- 感知、约束运动、关节运动、搬运运动、夹爪反馈检查、仿真输入与状态记录在各模块；旧 demo 不再持有视觉流程实现副本。
- 运动客户端接线集中到 `planning/clients.py`；不同 motion 能力保留自身约束与后置条件。
- 状态携带配方、执行器和完成能力列表；仅观察时 GUI 不将接近阶段显示为完成。
- 故障/缺失能力不能继续下一步；没有降低原有几何限值来获得通过。

## 仍然存在的边界

默认视觉任务由脚本启动、GUI 只读；还没有统一到 GUI 的 `ExecuteTask` Action server。固定 Observe 的安全监督器不能被当作视觉任务的停止实现。物理抓取、附着/持有、释放/落槽及真实机械臂/移动底盘连接仍未完成。GUI 浏览器视觉验收仍需操作员检查；本次验证 HTTP/ROS 数据与接口结果。

## 复测命令

```bash
./scripts/atom.sh build
python3 -m unittest discover -s tests/architecture -v
python3 -m unittest discover -s tests/scripts -v
# GUI/sensor tests require OpenCV/numpy; use the existing Jazzy container.
docker exec atom-tube-workflow bash -lc 'source /jazzy_ws/install/setup.bash; cd /workspace; python3 -m unittest discover -s tests/operator_gui -v'
./scripts/atom.sh sim --camera depth --recipe visual_approach --restart
python3 tests/operator_gui/tube_workflow_check.py --require-success
```

切换独立控制/纯臂/搬运模式前先关闭已有同 Domain 场景，不让多个控制节点同时拥有机械臂命令。完整结构见 [模块与任务](MODULES_AND_TASKS.md)。

最终代码复测：`run_20260930_055714` 深度模式 visual_approach 与 `tube_workflow_check.py --require-success` 通过，实际经过 setup→预观察→alignment→perpendicular→complete。最终冻结观察目标的平面距离 0.099629 m，横向误差 0.001816 m；条件仍为单例名义静态仿真，无物理取放/成功率声明。最终运行保留在 GUI :8089 供查看。

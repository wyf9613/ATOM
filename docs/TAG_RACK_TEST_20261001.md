# 试管架与 Tag 预观察、对齐及接近复测

日期：2026-10-01（Australia/Melbourne）。测试代码：`refactor/modular-task-composition`，提交 `7bbd038`。本次未改动算法或放宽验收阈值。

## 条件

沿用仓库既有 Docker / ROS 2 Jazzy / Gazebo Harmonic / MoveIt 配置、软件渲染及 ROS Domain 42；没有运行实机。名义静态试管架，dx=dy=0 m、yaw=0 rad；相同任务配方 `visual_approach`，随机种子 20260925，粗方位噪声配置 ±5°；tag1/tag2 联合观测，演示目标 tag1。对齐距离 0.40 m，最终距离 0.10 m。Depth 一次、RGB 两次，RGB 第二次用于复核第一次失败；样本不足以估计成功率或不确定度。相同参数不保证图像采样、规划结果一致。

## 结果

完整构建 13 个 package 成功。任务组合 6 项、CLI 7 项、容器内 GUI/Tag 几何/传感器 16 项软件测试通过，共 29 项。此处没有重跑 colcon test，也没有将历史报告的检查计入本次结果。

两种相机模式均完成双 Tag 预观察和对齐。Depth 全流程通过；RGB 首次在最终接近端点 IK 检查失败，相同参数复测通过。因此不能认定 RGB 全流程稳定。

| 模式 | 运行证据目录（`tmp/operator_gui/workflow/`） | 任务结果 | 任务时长 s | 观测平面终点距离 / 横向误差 mm | 场景真值横向偏差 / 100 mm 距离误差 mm |
| --- | --- | --- | --- | --- | --- |
| depth | `run_20261001_115327` | 通过 | 79.68 | 97.51 / 0.73 | 2.02 / 5.56 |
| rgb | `run_20261001_115502` | 失败：perpendicular IK | 72.90 | — | — |
| rgb | `run_20261001_115645` | 通过 | 80.34 | 101.96 / 0.04 | 2.01 / 4.47 |

终点观测几何来自冻结的视觉架平面；独立真值核对使用源码场景名义 Tag 位置和执行终点前参考点，沿 Tag 连线分解横向/法向误差，沿用 benchmark 的两项 25 mm 判据。两次成功运行均通过独立核对。以上为单次数值，无实机标定或测量不确定度。

三次对齐均拒绝 8 条超出姿态约束的 OMPL 候选路径，使用已有 constant-height/tilt Cartesian waypoints 回退后通过；不是首条规划直接成功。RGB 失败运行在最终接近的 0、±0.025、±0.05、±0.10 rad 候选偏航角均返回 MoveIt -31（NO_IK_SOLUTION）；不能仅据该错误码确定是碰撞、种子、位姿估计还是可达性问题。复测成功说明首次失败未在这次同参数复测中重复，根因仍未定位。

`tube_workflow_check.py --require-success` 对 Depth 和 RGB 复测返回 0；RGB 首次返回 1。三次 GUI 状态、配置相机预览、Tag 检测和关节反馈接口检查均通过；失败终态与原因正确显示，后续动作没有被标记完成。只做 API 与保存图像检查，没有进行浏览器交互验收。首次在沙箱内启动的额外 HTTP 检查未作为验收证据，正式检查在允许本机 HTTP 访问的环境执行。

每个运行目录保留 `workflow.log`、`trial_summary.json`、预观察报告及 `gui_check.json`；成功运行还有 `approach_report.json` 和 `independent_truth_check.json`。构建/验收日志位于 `tmp/modular_*20261001.log`。这些临时证据不提交 Git。

## 复测

```bash
./scripts/atom.sh build
python3 -m unittest discover -s tests/architecture -v
python3 -m unittest discover -s tests/scripts -v
./scripts/atom.sh sim --camera depth --recipe visual_approach --restart
docker exec atom-tube-workflow bash -lc 'source /jazzy_ws/install/setup.bash; cd /workspace; python3 -m unittest discover -s tests/operator_gui -v'
python3 tests/operator_gui/tube_workflow_check.py --require-success
# 上一模式完成后再切换；同一 Domain 保持一个运动执行器。
./scripts/atom.sh sim --camera rgb --recipe visual_approach --restart
python3 tests/operator_gui/tube_workflow_check.py --require-success
```

最后保留 RGB 成功复测会话，监视界面为 http://127.0.0.1:8089；退出可用 `./scripts/atom.sh stop`。任务完成不代表物理试管抓取、放置或硬件安全已验证。

## 后续输入与全架 Tag 重构复测（2026-10-01）

基于同一分支的未提交改动，输入已从 yaw 改为 noisy rack XY；精确 z 保持不变。`xy_noise_m=0.025` m/轴，种子 20260925，名义静态架，软件渲染，ROS Domain 42。RGB 和 Depth 共用全部架成员 `[0,1,2,3]` 的联合 PnP，预观察必须同帧看到全部成员并包含指定目标。Depth 未加入深度融合。旧版前述结果仅作为重构前记录。

| 模式 | 配方 | 目标 tag | 运行目录（`tmp/operator_gui/workflow/`） | 结果 | 任务时长 s |
| --- | --- | --- | --- | --- | --- |
| depth | visual_approach | 1 | `run_20261001_123940` | 通过 | 77.10 |
| rgb | visual_approach | 1 | `run_20261001_124133` | 通过 | 81.01 |
| depth | visual_observe | 3 | `run_20261001_124347` | 通过 | 36.12 |

三次预观察报告均包含 tag0..3 的同一图像时间戳位姿。默认 tag1 的 RGB 和 Depth 全流程各一次通过；非默认 tag3 的 Depth 只观察配方通过，没有接近段。非默认目标的完整对齐/接近尚未做运行覆盖。单次结果不能估计成功率/不确定度。所有运行使用原来的运动限值，对齐仍通过既有 Cartesian 回退完成。

最终代码软件检查：6 项任务组合、8 项 CLI、21 项输入/多 Tag/GUI/传感器测试通过，共 35 项；compileall、shell 语法和 diff 检查通过。每次 sim 启动增量构建 atom_xarm_sim 成功；本次没有重做完整 13 包构建。新增用例涵盖 XY 决定方向而 quaternion 无效、z 不加噪声、XY 有界可重复噪声、无效 XY 拒绝、四 Tag 联合位姿与缺失目标/成员拒绝。

另启动后加入的真实 ROS 订阅者，验证 transient-local 交付三个 topic（粗输入、转换位姿、目标任务），检查输出位姿方向来自 XY、半径 0.35 m、z=0.247 m、任务 tag3 与架成员 0..3。证据 `tmp/xy_late_subscriber_check.json`；发布目标消息发生在预观察运动前。最后保留 tag3 的 Depth 只观察会话。

```bash
./scripts/atom.sh sim --camera depth --recipe visual_approach --tag-id 1 --restart
./scripts/atom.sh sim --camera rgb --recipe visual_approach --tag-id 1 --restart
./scripts/atom.sh sim --camera depth --recipe visual_observe --tag-id 3 --restart
# 每次等待当前运行完成，再启动下一项；使用验收脚本检查终态。
python3 tests/operator_gui/tube_workflow_check.py --require-success
```

## 深度融合最终复测（2026-10-01）

最终代码软件检查共 40 项通过：6 项组合（包括融合模块不新增 node）、8 项 CLI、26 项输入/感知/GUI检查（含 5 个新增融合几何测试）。compileall、shell 语法、diff 检查通过。沿用名义静态 Gazebo 架、软件渲染、Domain42、seed20260925、XY 每轴 ±0.025 m，目标 tag1；启动时增量构建 atom_xarm_sim 成功。

- 初次 Depth 融合：`run_20261001_133323`，全流程通过。
- 纯 RGB 回归：`run_20261001_133539`，全流程通过，无深度融合；接近规划首候选失败后下一候选通过。
- 最终 Depth 融合：`run_20261001_133836`，加入至少两个 tag 区域平面支撑门限后，全流程通过。`tube_workflow_check.py --require-success --require-depth-fusion` 返回 0，检查到实际融合位姿。

最终运行 85 个相关同帧对照观测，未出现融合回退。纯 RGB 平均目标位置误差 1.644 mm，融合平均 0.584 mm；相对静态仿真名义真值，不能当作独立重复样本/硬件精度。`depth_fusion_comparison.json` 保存均值/RMS和回退计数，分析工具为 `scripts/benchmarks/analyze_depth_fusion.py`。

终点观测架面距离 102.531 mm，横向误差 0.461 mm；独立场景真值核对横向偏差 0.088 mm，100 mm 距离误差 2.358 mm，均通过原有两项25 mm限值。该终点运动误差与感知位姿误差是不同指标。没有通过改运动阈值获得成功。

最后保留最终融合 Depth 会话。方法、门限、缺深度回退与冲突拒绝见 [深度融合说明](DEPTH_FUSION.md)。当前证据未验证真实深度设备的注册、同步、偏差、噪声、透明材料或实机运动。

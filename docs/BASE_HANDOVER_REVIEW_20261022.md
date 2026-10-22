# 底盘与视觉伺服代码交接审阅 — 2026-10-22

结论：收到的是导航栈和底盘/机械臂视觉对准实验两套代码，有可复用的导航与微调接口；尚未接入 ATOM，也没有在本次审阅中验证整机运行。优先补齐交接依赖、运动控制权与停止链，再讨论系统联调。本次保留原 ZIP，只解压至 `tmp/base_handover_20261022/`，未安装依赖、运行 ROS、连接设备或修改交接代码。

## 1. 原始资产与证据等级

| 原始文件 | SHA-256 | 文件数 / 解压字节数 |
| --- | --- | --- |
| `basement/amr_nav_2026-10-22.zip` | `d489e57155a15ed3639739785401945916ce8769e40cecf38652e1d0c12b009c` | 124 / 1,290,218 |
| `basement/labbot_visual_servo_2026-10-22.zip` | `0cb8affa682859d18890d0b135fd806576adcf993cd1525f41efb4e302cb9459` | 73 / 11,940,769 |

下文路径以压缩包内部为准：导航包根目录为 `amr_nav_2026-10-22/`；视觉包根目录包含 `README_PACKAGE.md` 与 `projects/`。参数和 README 中的硬件说明属于队友交接证据，不能自动等同于本机实测、当前安装状态或 ATOM 验收结果。

## 2. 实际包含的能力

| 部分 | 代码入口 | 审阅所得 |
| --- | --- | --- |
| 真车导航 | 导航包 `projects/amrjiaoben/real/start_real_nav.sh` | TRACER CAN 驱动、Livox 点云、双高度 LaserScan、IMU、EKF、Nav2 和网页任务台 |
| 定位 | 同上及 `real/map_odom_anchor.py`、`real/ekf.yaml` | 默认里程计定位，由 anchor 发布 `map→odom`；AMCL 不广播 TF，在启动/回 home 旋转后尝试修正 anchor。并非默认全程 AMCL |
| 当前规划配置 | `real/nav2_real.yaml` | Smac Lattice + Regulated Pure Pursuit；期望线速度 0.15 m/s，八边形底盘 footprint，inflation radius 0.42 m。这些是配置值，不是实测安全边界 |
| 网页导航任务 | `projects/ros2_ws/src/amr_task_bridge/` | HTTP → JSON mission → Nav2 action；路线、取消、状态、初始位姿与软件停止 |
| IMU | `projects/ros2_ws/src/amr_imu/` | Tinkerforge IMU 读取与 ROS 输出 |
| 旧固定路线演示 | `projects/ros2_ws/src/amr_mission_manager/` | A→B→home；取放仅等待计时，不能计为机械臂取放实现。默认网页任务台使用的是 `amr_task_bridge` 内的另一个 mission_manager |
| 导航仿真与分析 | `projects/amrjiaoben/sim_tracer/`、`projects/navigation_test/fair/` | 简化 Tracer SDF、地图生成世界、规划器组合配置和指标脚本；README 明确原始批量试验数据未随包交付 |
| 视觉微调 | 视觉包 `projects/combine/src/base_fine_adjust/` | ArUco 位姿→底盘相对目标→odom 闭环微调；另有持续跟随模式 |
| 机械臂控制 | 同包 `xarm_camera_bridge.py` 与 `projects/850/` | 直接 xArm Python SDK、手眼 TF、自写 FK/Jacobian/DLS、搜索/home/接近服务；属于独立机械臂控制实现 |

导航包 README 与脚本指定 Ubuntu 22.04 / ROS 2 Humble；ATOM D-007 是 Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic 的开发仿真基线。此处仅记录收到的环境，不变更现有版本/驱动决策，也不假定两个 ROS 环境的 action 与消息已互通。

## 3. 可以讨论复用的接口

| 接口 | 类型 / 语义 | 集成注意事项 |
| --- | --- | --- |
| `/navigate_to_pose` | `nav2_msgs/action/NavigateToPose`；导航目标在 `map` | 已有导航能力，优先组合复用 |
| `/mission_cmd` | `std_msgs/msg/String`，JSON `goto` / `route` / `cancel` | 例如 `{"cmd":"goto","x":1.0,"y":0.0,"yaw":0.0,"label":"station_a"}`，x/y 单位 m、yaw 单位 rad；当前无独立 request ID |
| `/mission_event` | `std_msgs/msg/String`，JSON 状态 | idle/navigating/waiting/arrived/cancelled/failed/relocalizing 等；`arrived` 不代表机械臂可达或取放完成 |
| HTTP 8080 | `/cmd`、`/status`、`/initialpose`、`/estop` 等 | 可作为已有任务台集成讨论的边界；当前 ATOM GUI 尚未连接 |
| `/fine_adjust` | `nav2_msgs/action/NavigateToPose`；输入支持 TF frame | 区别于全局导航；需要运动权交接和故障门控 |
| `/fine_adjust/goal_correction` | `geometry_msgs/msg/PoseStamped` | 标签生成的底盘目标，并非试管槽位或机械臂 TCP 目标 |
| `/mission/command`、`/mission/event` | String `ALIGN:<label>` → `ALIGN_<label>_DONE` / `FAIL` | 和无斜杠的 JSON mission 协议是两套接口，当前默认导航 manager 未将它们串联 |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | 导航、视觉微调、软件停止共用，尚无统一仲裁 |
| `/estop_state` | `std_msgs/msg/Bool` | 软件停止状态；微调和 SDK 臂控制未订阅此状态 |

TF 的导航侧链为 `map→odom→base_link`，`base_link` 是底盘；ATOM 现有 `link_base` 是机械臂基座，不能仅按近似名称替换。视觉桥计算 `T_base_camera = T_base_arm × T_arm_tool × T_tool_camera`，发布底盘到相机根部/光学坐标的动态 TF。整合 URDF 后需要明确 TF 的唯一发布者，避免和 robot_state_publisher 重复定义相机父链。现有仿真的临时 `world→link_base` 也不能直接作为移动整机的固定安装关系。

## 4. 先解决的问题

### 4.1 停止没有形成统一的运动输出门控（优先）

证据：导航包 `amr_task_bridge/estop_guard.py:29-32, 87-110` 创建 `/cmd_vel` 发布者，触发时取消 JSON mission，停止期间周期发零速度；`mission_manager.py:215-249` 接收新任务时没有检查停止状态。视觉包 `fine_adjust_server.py:92, 118-130` 与 `xarm_camera_bridge.py:142-148` 也没有订阅停止状态或同一取消源。

因此持续发零速度会与其他速度发布者交替到达驱动；取消导航不等于取消 `/fine_adjust`、持续跟随或 SDK 臂运动。不能将文件注释中的 “Nothing moves until reset” 视为保证。需要在驱动前形成唯一输出门控，明确 Nav2/微调的互斥所有权，并让系统停止覆盖独立臂控制。软件停止依赖运行进程与通信，硬件停止链仍需独立验证。

### 4.2 `run_real.sh` 默认存在机械臂动作，桥也不是只读节点（优先）

证据：视觉包 `run_real.sh` 在等待相机后默认调用 `arm_search`，只有 `--no-search` 会跳过；是否带 `--go` 仅影响之后的一次底盘微调。`xarm_camera_bridge.py:120-127` 初始化时会 `clean_error()`、`clean_warn()`、`motion_enable(True)` 并设置碰撞灵敏度；`set_servo()`、search/home/approach 会改变控制模式和下发命令。

因此无 `--go` 不构成整机干跑。与 ATOM 的 MoveIt/厂商臂驱动并用之前必须确定唯一臂运动所有者，不能把这个 bridge 当作纯 TF 读取器启动。

### 4.3 微调绕过 Nav2 的避障链，且缺少数据过期门控（优先）

证据：视觉包 `config/fine_adjust.yaml` 的 `scan_topic: ''` 默认关闭局部扫描停止。`fine_adjust_server.py:206-215` 更新 `last_scan_time`，控制循环没有使用它检查 scan 过期；`base_in_odom():136-143` 查询最新 TF，未检查变换年龄。单次 `run_goal():237-291` 在标签丢失后继续向 odom 固定目标运动，这是显式设计，不是视觉闭环持续有效的证据。follow 模式另有标签超时停止，不能推广到单次微调。

需要定义微调期间的障碍检测、TF/scan/标签时效策略与取消响应。仅缩小 `correction_max_jump` 不会实现丢标签停止。

### 4.4 微调任务入口之间没有完整互斥（优先）

证据：`fine_adjust_server.py:217-221` 在 action goal 回调检查 `active`，但该标记到 `run_goal():248-250` 才设置；`mission_align():427-458` 绕过 action 接收检查直接调用 `run_goal()`，没有取消回调。不同 `ALIGN` 命令会启动独立线程、共享 `goal_odom`；相同文本的连续 `ALIGN` 又被 `on_mission_command():417-421` 去重，无法表达新的同名任务。

需要原子任务占用、统一取消路径和请求标识；在这些入口并用时，当前代码存在目标覆盖和并发发布速度的风险。此项为源码审阅发现，尚未执行 ROS 并发复现。

### 4.5 两个安装/演示入口缺少必要的完整 package

导航包 `install.sh` 选择构建四个包，其中 `my_lab_world` 只有 `worlds/`，没有 `package.xml` 或构建定义，无法按交付内容作为 ROS package 构建。视觉包 `gazebo_demo.launch.py:31-38` 需要 `combine_nav` 的包索引和 `launch/tracer_piper_nav.launch.py`，交付中的 `combine_nav` 只有 `urdf/flange_camera.xacro`。因此两个 ZIP 不足以复现这些指定入口，需要补齐 package 或明确修订支持的启动方式。

第三方底盘/雷达驱动本体不在包内；交付提供远端仓库、commit 和补丁，仍需验证重新获取、应用补丁与构建。脚本有 `~/projects`、`/home/zheming` 等路径约定，不能直接当作当前 ATOM 工作空间的可移植安装入口。

### 4.6 README、有效配置和当前机械安装不能混用

视觉 README 描述 81.5 mm 标签，实机 YAML 使用 53 mm 手机屏标签；README 的微调角速度上限为 0.25 rad/s，实机 YAML 为 0.12 rad/s。标签尺寸错配会影响单目尺度。

YAML 注释报告机械臂安装为 `mount_xyz=[0,0,0.834] m`、yaw 90°，并说明 x/y 假定居中。这提供了待核对的安装线索，不能直接填入整机测量表作为已验收值。手眼数据日期为 2026-10-08，是否对应现有相机 V3 支架、当前夹爪和法兰安装尚未确认。

### 4.7 默认定位和启动动作需要显式告知上层

导航脚本默认 `ODOM_ONLY=true`，要求起始位置/朝向接近建图出发点；开启 `AMCL_AT_HOME` 时会在启动及回 home 后旋转校正。`mission_manager.py:993-1012` 的启动校正可在上层发任务前开始。这会影响机械臂姿态、线缆及周围空间，不能把启动完成等同于静止待命。里程计漂移、重定位前后 TF 跳变和停靠精度仍需带载重复测试。

## 5. 离线检查与已有数据的解释

- 71 个 Python 文件通过 AST 语法解析；31 个 shell 文件通过 `bash -n`；4 个现有 `package.xml` 可解析。没有进行 colcon 构建、依赖导入或 ROS 运行验证。
- 重放原 `scripts/sim_fine_adjust.py` 的 6 个确定性初始位姿，调用原 `control.py`，采用 `control.DEFAULTS`、理想单轮车模型、Euler 积分、步长 0.05 s、每例最多 120 s。6/6 到达代码终止条件；位置误差最大约 0.01968 m、航向误差最大约 1.991°，速度峰值 0.050 m/s / 0.250 rad/s。无噪声、滑移、障碍、通信延迟或 ROS action；也不含 server 的加速度限幅。此结果只核对控制律示例，不验证实机 YAML 或停靠精度；无硬件误差/不确定度估计。
- `projects/850/data/handeye_result.json` 记录 25 组样本、位置 RMS 2.3847 mm、角度 RMS 0.9935°，并包含 25 组原始手眼样本。它们是交付的拟合结果，本轮没有重解；独立标定验证和当前安装适用性未确认。
- `kinematics850_calib.json` 记录 600 组拟合/200 组测试、最大差值 0.1641 mm / 0.003789°。`tools/calibrate_kinematics.py` 明确通过控制器 `get_forward_kinematics()` 生成参考值：这是自写模型对控制器计算结果的一致性，不能宣称为独立实测的绝对定位精度。原始 800 组 FK 参考数据未随该结果文件提供。

本轮机器可读输出保存在临时目录的 `static_checks.json` 与 `control_replay.json`。ZIP 的测试数据缺失意味着不能复现 README 中导航性能、漂移或整机停止结论。

## 6. 后续集成顺序（建议，尚未实施）

1. 补齐 `my_lab_world` / `combine_nav`，确认底盘电脑的实际 OS、ROS、驱动 commit、传感器和安装版本，取得对应 rosbag/测试说明。Humble 与 Jazzy 的部署边界或迁移方案另记 `DECISIONS.md` 后实施。
2. 保留导航和微调能力边界；用现有任务执行模块组合“导航 staging→确认停稳/交出控制权→视觉观察/微调→臂操作”。任务变多不自动增加 node，尤其不要复制机械臂控制实现。
3. 明确底盘唯一速度输出门控、臂唯一运动所有者、全部任务的取消/停止/复位约定，先离线或假设备验证。
4. 核对 `base_link→机械臂基座`、当前手眼/TCP、标签尺寸和 workstation frame，按模块组合描述。已有导航 footprint 不包含机械臂、夹爪、负载的所有姿态包络。
5. 先接只读地图/定位/状态，再在受控条件下验收独立导航、微调与交接；记录样本数、载荷、误差分布、漂移及停止延迟后，才扩大到整机任务。

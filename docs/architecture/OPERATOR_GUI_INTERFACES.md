# 操作界面接口 v1（2026-09-30）

实现位置：`tools/operator_gui/`。当前为独立工具，不更换 D-007 Jazzy/驱动基线。

| 功能 | ROS 接口 | 类型 | 当前状态 |
|---|---|---|---|
| 关节反馈 | `/joint_states` | sensor_msgs/JointState | 已订阅，rad |
| 底盘反馈 | `/odom` | nav_msgs/Odometry | 已订阅，坐标由 header.frame_id 标识 |
| 电源 | `/battery_state` | sensor_msgs/BatteryState | 已订阅，percentage 0..1 → % |
| 诊断 | `/diagnostics` | diagnostic_msgs/DiagnosticArray | 已订阅，ERROR/STALE 阻止运动请求 |
| 相机 | `/atom/wrist_camera/image/compressed` | sensor_msgs/CompressedImage | 已订阅 JPEG/PNG；现有传感器需启用压缩输出 |
| 软件停止/复位 | `/atom/safety/stop`、`/atom/safety/reset_stop` | std_srvs/Trigger | client 已实现；Gazebo server 已实现；硬件 server 待实现 |
| 观察/取消 | `/atom/task/observe`、`/atom/task/cancel` | std_srvs/Trigger | client 已实现；Gazebo 观察通过 Action，取消服务已接入 |
| 取放/导航任务 | `/atom/task/execute` | atom_operator_interfaces/action/ExecuteTask | ActionClient 已实现；Gazebo server 仅支持 observe，其他任务待接入 |
| 实时地图 | `/map` | nav_msgs/OccupancyGrid | 预留；目前显示仓库静态 PGM |
| 底盘地图位姿 | map → odom TF | tf2 | 预留；不把 odom 位姿冒充地图位姿 |
| 导航执行 | `/navigate_to_pose` | nav2_msgs/action/NavigateToPose | 由未来 task executive 适配 Nav2，未实现 |

短期项目状态用 std_msgs/String JSON，须包含 `schema_version:1`；后续定义专用消息时保持字段含义和版本协商。

安全反馈 `/atom/safety/status`（建议 ≥ 2 Hz）：

```json
{"schema_version":1,"hardware_estop":"unknown","motion_allowed":false,"stop_confirmed":false}
```

硬件状态仅允许 `unknown/pressed/released`，布尔字段须真布尔值；未知或旧消息不能允许运动。`motion_allowed` 由 robot-local supervisor 的系统检查得出，不能由 GUI 自行推断。监督节点还应校验硬件、控制器、TF、目标、规划场景、控制权和校准版本。

任务反馈 `/atom/task/status`（建议 ≥ 2 Hz）：

```json
{"schema_version":1,"state":"IDLE","detail":"Waiting for task"}
```

建议状态：IDLE / OBSERVING / PLANNING / EXECUTING / STOPPED / FAULT；动作最终结果由 action result 给出。网关显示该状态但不自行把服务成功解释为抓取成功。

审计 `/atom/operator/request` 是 std_msgs/String JSON：`schema_version/request_id/command/parameters`。**只能记录，不得订阅后直接驱动运动**。参数命令当前在 ROS 模式拒绝，不能通过该 topic 绕过未实现的 ActionClient。

HTTP：`GET /api/v1/state`、`GET /api/v1/map`、`GET /api/v1/camera`、`GET /api/v1/session`、`POST /api/v1/commands`。命令返回 202 + request_id 是提交确认；执行确认来自事件和任务反馈。错误 400 表示参数问题，409 表示锁定/过期/服务不可用，403 表示会话/cross-origin 校验失败。客户端不得自动重试结果未知的运动请求。当前没有多操作员租约或跨进程幂等机制。

部署验收：加入 typed ActionClient/server 与取消/反馈/结果；验证 stop/复位/断链；加入地图和 TF、雷达覆盖/动态障碍、相机压缩；加入 TLS/认证/控制租约、持久化审计；测试 Wi-Fi 丢包/断连/延迟和重启，不从静态地图或演示数据推断避障能力。

## Gazebo → 实机兼容性核查（2026-09-30）

当前容器的 vendor 仓库版本为 `3dc2b5e8294758d96b54b15fa5920d581b7cbb3d`；以下以该源码、当前 launch 和实际 Gazebo 消息为依据，不把 upstream 最新文档当作当前实机事实。

| 子系统 | 仿真与实机匹配点 | 需要替换/验证的差异 |
|---|---|---|
| 关节状态 | sensor_msgs/JointState、六关节名、rad | topic namespace、串号标定；velocity/effort 的来源与可靠性 |
| 工具位姿 | tf2、link_base → link_eef、m/quaternion | link_eef 不等于实测抓取 TCP；安装和手眼标定 |
| 图像 | sensor_msgs/Image 或 CompressedImage | RGB 目前 /atom/wrist_camera，depth 模式 /atom/wrist_camera/image；实机驱动、内参、外参与曝光 |
| 控制器 | controller_manager/ListControllers；同一上层 MoveIt 边界 | GazeboSimSystem → vendor hardware system，controller 名称与就绪条件 |
| 时间 | 页面 API 接口保持一致 | 仿真 use_sim_time=true + /clock；实机 false + 系统时钟；网关接收过期用 monotonic 时间 |
| 错误状态 | 用统一 GUI 状态显示 | 实机 /ufactory/robot_states 的 RobotMsg；err/warn/state，不能用 Gazebo active 状态冒充硬件健康 |
| 停止 | 上层 Trigger 接口约定可复用 | 仿真取消/hold 与真实控制器停止/硬件反馈由不同 supervisor adapter 实现，均未接入本轮 Gazebo |
| 移动底盘 | Odometry/BatteryState 与未来导航 Action | 目前仿真没有底盘，不能测试 odom/map/导航匹配 |

已实现 Gazebo 原始图像转 JPEG、夹爪状态提取、仿真时钟检测、控制器状态查询和工具 TF；`hardware.example.json` 提供真实源配置模板和可选 RobotMsg 订阅，位置由 mm 归一化为 m。vendor topic 以现场 namespace 为准。硬件反馈并不自动开放 motion_allowed。

当前验收只完成 **Gazebo → ROS → HTTP 的监控链路**。`observe/pick/place/navigate/cancel/stop` 的真实任务与安全 server 未接入；8 项 gateway 测试、fake ROS Trigger 测试和真实 Gazebo 两样本检查不能替代控制链路/实体硬件验收。

后续顺序：

1. Gazebo task executive 暴露 ExecuteTask action，先运行 observation/approach，返回进度/最终结果；取放物理行为继续使用已有 TODO 验收标准。
2. 独立停止 supervisor：停止优先、取消在途动作、验证关节静止、锁定与人工复位；测试暂停/断连/超时/重启。
3. GUI 通过 ActionClient 连接任务，标准取消和 feedback/result，增加单操作员租约、幂等 request ID、持久化审计。
4. 实机先只读：核对 joint names、namespace、时间、TF、错误码、相机和硬件停止反馈；之后以限制速度的小范围任务验收控制，禁止自动启动运动。
5. 未来底盘接入 OccupancyGrid、map → odom → base_link、LaserScan、Nav2、battery 和 docking；当前静态实验室地图不对应桌面 Gazebo 工位，不能将二者直接拼成定位结果。

GUI 后续完善项包括速度/任务参数权限、相机/TF/目标数据质量、校准版本、规划轨迹预览、gripper object-present、软件报警确认和实验运行归档。只有收到来源明确的数据时展示通过/完成。

官方参考：[xarm_ros2](https://github.com/xArm-Developer/xarm_ros2)、[vendor API 文档](https://github.com/xArm-Developer/xarm_ros2/blob/humble/xarm_api/ReadMe.md)；页面数据必须以 pinned source 和现场测量优先。

## Gazebo 控制链路已接入（本轮更新）

- ExecuteTask ActionClient 可处理 goal acceptance、feedback/result、标准取消和 180 s 任务 deadline；deadline 时请求取消，结果未知期间保留在途任务，阻止重复任务。
- Gazebo supervisor 目前只接受 OBSERVE，执行已有固定关节观察往返；拒绝 PICK/PLACE/NAVIGATE。硬件配置不会自动启用这个 supervisor。
- `/atom/safety/stop`、`reset_stop` 和 `/atom/task/cancel` 的 Gazebo server 已实现。停止 latch、controller deactivation、实际关节静止确认、手动 reset 和启动锁定均在机器人侧；GUI 同时显示远端 latch。
- Gazebo safety 增加 `source:"gazebo"`、`hardware_estop:"not_applicable"` 和 `software_stop_latched`；硬件 profile 不接受 not_applicable 作为 motion 许可。硬件停止状态仍须真正的实机 adapter 提供。
- 原先“任务/停止 server 尚未接入”的记录仅适用于旧监控阶段及当前硬件模式；Gazebo observation/stop/cancel 路径已完成有限验收。视觉接近、取放、底盘导航、持久化操作审计和操作者租约继续待实现。

## 外部试管实验与 RGB-D 监控

pre_observation_demo 新增 `/atom/task/status`（String JSON, schema_version=1）和 0.5 s 状态心跳，字段 source=tube_approach_experiment、phase、request_id、camera_mode、tag_id、observed_tag_ids、completed_segments、planning_attempts、metrics、grasp_completed/place_completed。SUCCEEDED 表示现有视觉接近成功，grasp/place 均为 false。FAILED 包含实际异常原因。`keep_status_alive:=true` 只保持终态发布，不重跑运动；默认 false 兼容已有脚本。

GUI 独立 tag_preview 检测 AprilTag36h11，按已知唯一槽位 ID 合并重复轮廓，40 mm 标记的 PnP 位置以 camera frame/m 显示；这是显示用的仿真尺寸假定。真正控制路径沿用节点自己的 TF 与验收。检测成功、pose_valid、运动完成是不同状态。

新增 `/api/v1/depth` 返回 PNG；state.depth 包含 width/height、encoding、unit=m、valid_fraction/pixels、min/max/median、frame 和 source_stamp_s；valid 指有限且 0.08 < depth < 2.00 m。无效区为黑色。RGB-D 原始深度 topic 为 `/atom/wrist_camera/depth_image`，CameraInfo 为 `/atom/wrist_camera/camera_info`。这些指标不能证明透明材料的实机深度准确性。

`jazzy_operator_attach.sh depth` 在现有 graph 中启动独立只读网关，避免重复 Gazebo。`jazzy_tube_workflow_gui.sh depth` 将现有试管视觉接近节点、Gazebo 和监控一键启动；它不启用固定 Observe supervisor，不将两个任务状态发布者混在同一 graph。

### Transfer status and frame-rate fields (2026-09-30)

`transfer_demo` publishes schema v1 `/atom/task/status` with `source=transfer_baseline`, actual phase/state, unique request_id, phase metrics, `simulate_grasp_success`, and `grasp_completed=false`, `place_completed=false`. Terminal heartbeat is opt-in `keep_status_alive`; default CLI exit behavior remains unchanged. `report_path` allows a per-trial report. Launcher selects one runner, default `transfer`, optional `approach`; it never concurrently commands both. Transfer remains fixed-target and is not driven by monitor-only Tag detection.

Camera/depth stream values contain `received` and `preview` objects with `fps` (frames/s of wall time), `sample_count`, `window_s` (up to five seconds) and `sequence`. Browser fetches images independently at up to 10 Hz without queuing; telemetry stays 1 Hz. `preview_fps` is configurable in ROS gateway config, default 15 Hz; sensor remains configured at 10 Hz. Tag status is updated at up to 2 Hz and can therefore lag the current preview frame; use its source timestamp.

### Correction: legacy transfer targets do not match the tube scene (2026-09-30)

The previous default-to-transfer GUI launcher decision was incorrect for the tube experiment and is superseded. Default is restored to `approach`; `transfer` must be explicitly selected and labelled as a legacy fixed-target motion test. Nominal scene coordinates from source: robot spawn [-0.2, -0.54, 1.021] m with yaw -1.571 rad; tube centre [0.530, -1.035, 1.2155] m in Gazebo. Converting into the nominal robot base frame gives approximately [0.495, 0.730, 0.195] m. Legacy pick uses [0.32085, 0.24571, 0.22907] m for link_eef, with no calibrated finger/TCP conversion. These poses are not the same target; the Gazebo spawn transform differs from the temporary identity ROS world-to-base TF. This is a source-based nominal calculation, not measured pose accuracy. Do not relabel the fixed-target motion PASS as a tube transfer or simply substitute the tube centre for the flange target. Full integration still requires Tag-to-slot/TCP conversion, collision-aware reachability, gripper/contact verification and physical transfer/release.

Approach GUI phase `realignment` represents an optional corrective motion after settled same-frame two-tag re-observation. `metrics.ray_lateral_error_m` now includes the updated-frame acceptance check; `metrics.realignment_attempts` reports bounded corrections. The 0.025 m ray bound is unchanged. Task phase completion remains distinct from physical grasp/place.

# ATOM operator GUI

浏览器控制台 + 同机 HTTP/ROS 2 网关。默认启动演示数据；ROS 模式默认只读。

```bash
# 不依赖第三方 Python 库
python3 tools/operator_gui/server.py
# 浏览器打开 http://127.0.0.1:8088

# ROS Jazzy 使用系统 Python，避免 Conda Python ABI 不匹配
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=42
/usr/bin/python3 tools/operator_gui/server.py --mode ros
# 下游监督服务实现并验收后，显式追加 --enable-commands
```

在机器人计算机或已有 Jazzy 容器内运行网关；仓库挂载位置不同不影响脚本寻址。
可用 `--ros-config /path/to/config.json` 改 topics/services，样例见 `ros_config.json`。

## 当前实现

- 演示模式：合成六关节、底盘、电池、诊断、任务数据；观察/取放/导航按钮模拟响应并记录事件。
- ROS 模式：JointState、Odometry、BatteryState、DiagnosticArray、安全/任务状态订阅；图像为 CompressedImage（JPEG/PNG）。压缩图像 topic 需要相机驱动或 image_transport 提供。
- 每秒轮询状态；反馈 2 s 后标过期，网络请求 2 s 无响应标断开；相机过期隐藏。
- 自由/占据/未知地图预览、事件列表、状态快照导出、指令参数校验、会话 CSRF token。
- `observe/cancel/stop/reset_stop` 对接 Trigger 服务；需要真正的任务/安全监督节点提供响应。
- `pick/place/navigate` 当前保持不可用；ExecuteTask ActionClient 已实现，Gazebo task executive 当前仅支持 observe。不向旧演示的 JSON topic 下发动作，不直接写 cmd_vel 或关节轨迹。

## 停止语义

红色按钮为**软件停止请求**。启用指令的网关首先锁定本身的运动请求，再调用 `/atom/safety/stop`。服务未接入时保持锁定并报错；5 s 无服务响应记录“结果未知”。成功响应仅表示服务回应，实际停止由安全状态 `stop_confirmed` 判断。软件复位须服务成功、反馈新鲜、硬件急停已释放且停止已确认；复位响应到达前再次按停止不能解除新锁定。复位不继续任务。

只读模式禁用所有指令，包含软件停止。网关锁定是进程内状态，重启会丢失；机器人上的 supervisor 必须独立持有停止锁定、控制权和断链处理。网关不能取消其他节点绕过它发布的命令。硬件急停始终使用实体按钮/经验证的硬件回路；界面只显示反馈。

## 无线部署

推荐拓扑：操作电脑 → Wi-Fi → 实验室专用 AP → 机器人计算机 → 有线 Ethernet → xArm 控制箱。机械臂驱动、规划器、底盘和停止监督都运行在机器人侧，Wi-Fi 只传高层请求/遥测/压缩图像。底盘协议和实际控制箱接口仍待实测。

开发阶段保持默认 loopback，通过 SSH 隧道访问：

```bash
ssh -L 8088:127.0.0.1:8088 robot-user@robot-ip
# 操作电脑打开 http://127.0.0.1:8088
```

局域网正式部署需要反向代理 HTTPS、用户认证、单操作员控制权和网络访问限制，再使用 `--host` 绑定指定地址。当前 CSRF token 不是身份认证，不应直接把无认证的网关暴露到 Wi-Fi 或公网。停止和控制闭环不依赖浏览器心跳；禁止靠无线软件按钮实现硬件急停。

来源：UFactory [硬件安装文档](https://docs.xarm.ufactory.cc/2.hardware_installation.html)说明控制箱用 Ethernet 接路由器、PC 可无线接同一路由器。此为拓扑依据，尚未验证本项目控制箱的 IP、型号、实际无线性能。

## 检查

```bash
python3 -m unittest discover -s tests/operator_gui -v
source /opt/ros/jazzy/setup.bash
/usr/bin/python3 tests/operator_gui/ros_smoke.py
```

后者创建假 ROS 发布者和停止服务，不连接硬件。已检查反馈、停止锁定/响应、只读模式、过期反馈、非法参数、重复请求和跨域/token 拒绝；尚未完成浏览器视觉验收或实机停止测试。

## English GUI and Gazebo profile (2026-09-30)

界面文字已统一为英文；对话与中文项目文档保留中文。增加设备 readiness、夹爪/工具位姿/厂商故障、任务进度和请求 ID、网关响应延迟、运行配置查看、会话重连与断线状态。

```bash
# 启动既有 Gazebo 场景 + 只读 GUI 网关（无需图形桌面）
./scripts/atom.sh observe --camera rgb
# 或 depth；浏览器访问 http://127.0.0.1:8089
# 另一个地址 8088 仍是 synthetic demo，二者不可混用验收数据。
python3 tests/operator_gui/gazebo_gateway_check.py
```

脚本复用已构建的 Jazzy 镜像/工作区并重新构建 atom_xarm_sim，不拉取依赖或隐式停止现有容器。如果镜像或 vendor 工作区未准备好，先执行项目 `./scripts/atom.sh build`。`Ctrl+C` 退出或 `docker stop atom-operator-gazebo` 关闭本次仿真。

Gazebo 原始 Image 在网关中以可配置最高 15 Hz 转 JPEG（Gazebo 源配置为 10 Hz）（需要 cv2/numpy，当前容器已具备）。真实设备优先提供 CompressedImage。时间与帧配置分别见 `gazebo_rgb.json`、`gazebo_depth.json` 和 `hardware.example.json`；硬件样例 topic 名称必须用部署后的 ros2 topic list 核实，不能直接当作实机已接入。

目前 Gazebo 接入验收：2 个状态快照，间隔 1 s，检查 clock 与 joint source stamp 推进、六臂关节、drive_joint、末端 TF、active controller、diagnostics、JPEG 和只读禁令。原始快照和相机帧在 `tmp/operator_gui/`。8 项网关检查通过；GUI 仍未完成浏览器视觉验收。

## Gazebo control profile

```bash
./scripts/atom.sh observe --camera rgb --control
# http://127.0.0.1:8089
# Initial state is STOPPED; use Reset software stop before Observe.
python3 tests/operator_gui/gazebo_control_check.py
```

`monitor`（默认）只读；`control` 增加 **Gazebo 专用** task/safety supervisor 与指令权限。Observe 经 ExecuteTask ActionClient → MoveIt 运行已有的固定关节观察往返，含 2 s 停留；这不是视觉对准/抓取。Pick/Place/Navigation 保持不可用。

Action 显示 accepted、feedback 和最终 result；Cancel task 使用标准 Action 取消。软件停止终止本 supervisor 的观察进程、请求取消 MoveIt/trajectory goals、deactivate arm trajectory controller，再依据新鲜反馈确认连续三次 |velocity| < 0.01 rad/s。Reset 重新 activate controller、解除锁定，不继续旧任务。启动/重启 supervisor 默认锁定，确认仿真停止后需要人工 Reset。hardware_estop 在该 profile 明确为 not_applicable，不把不存在的实体回路标为 Released。

Supervisor 要求机器人描述是 `gz_ros2_control/GazeboSimSystem` 且 /clock/JointState/controller 反馈新鲜，才允许操作仿真控制器。它不是硬件停止实现：严禁在实机环境使用。仿真 gripper controller 保持 active，目前不支持夹爪运动指令，软件停止验收范围是机械臂。

10 项网关测试、fake ROS 服务测试和真实 Gazebo HTTP/Action/MoveIt 取样验收已通过：观察往返、运动中停止、锁定拒绝、1 s 静止取样、人工复位和标准 Action 取消。日志在 `tmp/operator_gui/tasks/`，验收快照在 `tmp/operator_gui/gazebo_control_check.json`。状态快照包含 request_id 和事件，动作追踪 CSV/JSON 位于当前容器 `/jazzy_ws/log/gui_*`（挂载到 .docker-runtime）。这些是少量理想仿真测试，不代表硬件安全或成功率。

## Monitor the actual tube experiment (RGB-D)

这与固定关节 Observe 演示不同：运行原有 pre_observation_demo，监控其预观察 → Tag1/2 识别 → alignment → perpendicular 接近两段，保持 GUI 只读，不启动竞争的任务。

```bash
# 一键启动同一个试管场景、真实视觉接近流程和 GUI（depth 模式）
./scripts/atom.sh sim --camera depth
# 打开 http://127.0.0.1:8089
```

每次启动生成独立 `tmp/operator_gui/workflow/run_<时间>/`，含 workflow.log、runtime_status.json、trial_summary.json、approach_report.json 和图像。任务结束后节点继续发布最终状态，不继续运动；Gazebo 和 GUI 保留以便检查。Ctrl+C 或 `docker stop atom-tube-workflow` 关闭本次场景。

如果另一终端已在运行原有试管实验，只启动独立监控：

```bash
./scripts/atom.sh attach --camera depth
```

Attach 不启动 Gazebo，不发送轨迹，不自动运行观察动作。双方 ROS_DOMAIN_ID 必须相同（当前 compose 默认 42），8089 不能已有另一网关占用。同一 domain 同时只运行一个 task/status 发布者。原有脚本使用更新后的 pre_observation_demo 才会提供阶段状态；已结束且节点退出的旧任务不会假装显示实时完成结果。更晚打开 GUI 时，keep_status_alive 模式会继续提供当前终态。

GUI 新增：RGB 上 AprilTag 框和 ID；当前帧 selected Tag 成功/未看到、相机坐标 PnP 位姿；深度伪彩图（0.08–2.00 m，非法像素黑色）、有效比例、min/max/median、源时间戳和 frame；实验阶段、真实阶段完成/失败原因、已识别 Tag 列表和接近几何误差。进度百分比表示阶段权重，不是连续轨迹完成百分比。

网关深度支持 32FC1（m）和 16UC1（mm→m）、行填充和字节序。全图有效深度比例不能当作透明试管表面质量。Tag 位姿仍由 RGB PnP 给出，没有把深度统计伪装成深度融合定位。独立 GUI detector 只作显示；运动仍使用实验节点自身的检测、TF 和规划验收。

```bash
# 真实 RGB-D workflow → GUI/API 验收
python3 tests/operator_gui/tube_workflow_check.py
# OpenCV/numpy 相关测试可在同一个运行中的容器执行
# docker exec atom-tube-workflow python3 -m unittest discover -s /workspace/tests/operator_gui -v
```

13 项网关/传感器测试已通过；实际 RGB-D 运行完成预观察和两段视觉接近，实时状态、RGB、深度、Tag 和最终结果进入 GUI。物理抓取、放置仍未实现。浏览器视觉验收仍待操作员检查。

复测记录：一次完整视觉接近成功；第二次在 alignment 后因更新法线射线偏离 0.0920 m、超过 0.0250 m 限值而失败，GUI 正确显示阶段/错误原因。`tube_workflow_check.py` 默认检验状态/深度/Tag/终态链路，明确打印实验成功或失败；加 `--require-success` 才同时要求接近算法成功。后续需实现并验收 realignment，不以两次运行估计稳定性。

已有 `atom-tube-workflow` 运行时，再次执行启动命令会显示现有 GUI 地址，不重复启动场景。重新跑一轮使用：

```bash
./scripts/atom.sh sim --camera depth --restart
```

这会结束当前同名试管仿真并启动新一轮；历史报告保留。启动前会检查 8089 是否被其他 GUI 占用，避免先运行任务后才发现监控无法启动。

## Original transfer baseline and camera refresh

默认入口为原有视觉接近实验；旧 `transfer_demo` 是与当前试管槽无关的固定目标运动测试，须显式选择：

```bash
./scripts/atom.sh sim --camera depth
# 如已有场景，显式运行旧固定目标运动测试：
./scripts/atom.sh sim --camera depth --restart --workflow transfer
# 如需原来的视觉接近实验：
./scripts/atom.sh sim --camera depth --restart
```

二者均在同一个试管场景接入实时 GUI，但每次仅运行一个任务节点。搬运沿用 `transfer_targets.yaml` 的固定末端位姿，不声称由 Tag 定位驱动。GUI 显示 MOVE_TO_PICK → VERIFY_GRASP → VERTICAL_LIFT → CONSTRAINED_TRANSFER → VERTICAL_DESCENT → COMPLETE。2026-09-30 单次 Gazebo 验收完成全部运动阶段，报告在 `tmp/operator_gui/workflow/run_20260930_043337/transfer_summary.json`。原代码 `simulate_grasp_success=true`；没有夹爪接触验证和物体附着/释放，GUI 显示 SIMULATED，物理抓取/放置保持未确认。这不是完整视觉取放验收。

网页图像独立按最高 10 Hz 请求，状态面板仍 1 Hz；后端图像限频可通过 `preview_fps` 配置（默认 15 Hz，允许 10 Hz 源的时间抖动），Tag 监控检测独立最高 2 Hz。深度 PNG 使用低压缩等级。RGB/深度显示收到及编码预览的 wall-clock fps，附 5 s 滑动窗的样本数、窗口时长和序号；仿真变慢时不把 simulation Hz 当作实际 fps。实际浏览器呈现率仍需操作员检查。网页隐藏时暂停图像请求。

2026-09-30 preview measurement: depth mode, 640×480, one Gazebo run using software rendering; final 4.94 s wall-clock window contained 49 RGB and 49 depth frames. Received and encoded preview rates were approximately 9.7 frames/s for both streams. This measures ROS gateway delivery/encoding, not browser display FPS or wireless/hardware performance. Samples: `tmp/operator_gui/transfer_camera_measurement.json`.

### Same-frame rack estimate and bounded realignment (2026-09-30)

A GUI-observed approach failure was reproduced: initial alignment passed against its frozen pose, then independent latest single-tag PnP positions changed the inferred normal and gave 0.0696 m lateral error against the unchanged 0.025 m bound. Rack estimation now deduplicates marker contours, fits tags 1/2 jointly in one image using provisional 0.040 m size / 0.070 m spacing, rejects reprojection RMS >2 px, and requires a fresh coherent pair for normal/selected pose. It uses observed image data and TF, not simulator truth. Motion still freezes observations per trajectory. After settling, the updated ray and distance are checked; up to three corrective alignment motions are allowed, otherwise the task fails. Limits on height, tilt, visibility and ray width are unchanged. GUI exposes a realignment phase and the updated geometric error rather than the prior frozen error.

First depth-mode run after the change passed alignment and perpendicular approach: updated-ray lateral 0.0151 m; final estimated plane distance 0.1016 m, frozen-ray lateral approximately 0.0002 m. Conditions: nominal static rack, software rendering, N=1, uncalibrated simulator geometry; no uncertainty/reliability or physical grasp claim. Report `tmp/operator_gui/workflow/run_20260930_045125/approach_report.json`. This run needed zero corrective motions; retry exhaustion and correction execution still require separate validation. Three synthetic-image regression tests verify known board pose, subpixel noise/rigid spacing and inconsistent-corner rejection; 16 gateway/sensor/geometry tests passed in the Jazzy container.

Final-code depth repeat also passed both approach segments and `tube_workflow_check.py --require-success`, with RGB/depth/Tag/joints and terminal heartbeat delivered to GUI. Report: `tmp/operator_gui/workflow/run_20260930_045345/approach_report.json`; final frozen-snapshot plane distance 0.101015 m and ray lateral 0.002645 m. Two nominal successful runs do not establish reliability.

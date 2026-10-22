# 移动底盘、UF850 与夹爪集成

日期：2026-10-22。分支：`integrate/mobile-base-gripper-jazzy`。

本次把底盘导航与精定位代码迁入现有 Jazzy 工作空间，复用当前 ESP32 夹爪边界，并新增模块化整机描述。原始 ZIP 保持不变。默认启动用于模型与接口审阅，不连接 CAN、机械臂、相机或夹爪，也不自动执行 home、搜索、导航或接近。

## 安装几何

用户确认机械臂底座与底盘中心在 XY 平面重合，从底盘 **top 面到机械臂底座安装面为 805 mm**。本轮未提供量具、测量重复次数或不确定度；该值是用户提供的安装输入。用户明确表示朝向暂未确认，所以 yaw 是独立参数，零值仅用于审阅。

```text
map → odom → base_link                 定位动态 TF；不写成固定 world 关节
               ├─ base_body / wheels   暂用交接仿真的简化外形
               ├─ base_top            底盘 top 安装基准
               │    └─ arm_pedestal    独立铝型材支架模块
               │         └─ arm_mount 底盘 top 上方 0.805 m，XY = 0
               │              └─ link_base → … → link_eef → 当前 ATOM 夹爪/法兰/支架
               ├─ livox_frame         交接参数，仍需核验安装
               └─ imu_link            交接参数，仍需核验安装
```

| 参数 | 默认值 | 来源与边界 |
| --- | --- | --- |
| `pedestal_height` | 0.805 m | 用户提供；top 面→机械臂安装面 |
| 安装中心 XY | [0, 0] m | 用户提供水平中心重合 |
| `arm_mount_yaw` | 0 rad | 可调审阅值，物理朝向未确认；不能把它当作已测结果 |
| `base_top_height` | 0.15 m | 交接简化 SDF 的离地 top 高度，尚未实测 |
| 支架 footprint | 0.36 × 0.32 m | 审阅占位，型材截面/横梁/紧固件仍需图纸或测量 |
| 底盘碰撞盒 | 0.72 × 0.59 × 0.10 m | 来自交接外包络的简化盒，非官方 TRACER 2.0 CAD |

在这些默认值下，机械臂安装面距地面为 **0.955 m**，这是参数相加的名义结果，不是新增实测。`base_link` 明确定义为底盘中心在地面的投影，`link_base` 保持厂商机械臂基座含义。实车 odometry frame 必须核对这个约定。支架使用完整实心碰撞外包络；它不能验证内部穿越空间或承载能力。

整机源：`ros2_ws/src/atom_mobile_description/urdf/atom_mobile.urdf.xacro`。引用独立的底盘审阅模型、支架 macro、D-007 厂商 arm macro 和当前 `atom_gripper_v2`，没有修改厂商机械模型。相应 SRDF 只排除明确安装接触，保留手臂与底盘/支架其他部分的碰撞检查。模型缺少实测底盘/支架惯量，默认只提供 fake ros2_control 描述，不用于宣称整机动力学、稳定性或载荷验收。

## 软件与模块边界

- 继续使用 Ubuntu 24.04 / ROS 2 Jazzy，与现有 arm 基线一致。现有独立 arm Gazebo Harmonic 回归入口保留。
- `atom_base` 从交接代码复用 JSON mission manager、网页任务台、地图工具、IMU reader、标签检测、微调控制律和 action。来源及 SHA-256 在 package 内 `HANDOVER_SOURCES.json`；许可声明在 `NOTICE.md`。
- 修正 Jazzy Nav2 plugin 标识、progress checker 列表、BT.CPP v4 XML；显式使用 `geometry_msgs/Twist`，安装路径从 package share 解析。显式组合本轮所需的 Nav2 服务，避免自动启动没有配置的 route/docking 服务；导航输出经过配置后的 collision monitor，再进入统一速度门。当前迁移参数保留 Smac Lattice + RPP；其调参不是当前带载整机的性能验证。
- 新入口使用连续 AMCL 拥有 `map→odom`。不启用交接版启动/回 home 自动旋转和里程计 anchor 修正，避免启动时出现隐式移动。初始位姿仍需操作员或经验证的定位来源提供。
- 现有 `atom_gripper_hardware` 继续拥有串口、ControlGripper action 和控制租约。整机入口增加软件停止状态门控与监督状态过期检查。力控制和抓取成功仍受现有标定门限制。
- 不导入交接的 SDK arm motion bridge、home/search/approach 脚本。相机 TF 应由统一机器人描述和核验后的标定提供，机械臂运动仍通过现有 arm 能力边界。
- 原 `/mission/command ALIGN:*` 字符串微调入口已禁用，统一使用 `/fine_adjust` action，避免任务线程绕过互斥与取消。上层任务可组合已有导航、微调、arm 与 gripper 能力，不能把新的任务名称当作新 node 的理由。

新增 node 的理由：`velocity_gate` 是底盘最终输出/故障边界，负责独占命令来源、过期和软件停止，需要独立于 Nav2、视觉微调进程运行。`kinematic_fixture` 仅为接口测试，消费同一个门控输出生成理想 odometry/TF/scan，不是生产导航或新的任务实现。

## 速度与停止接线

```text
Nav2 smoother ── /atom/base/nav_cmd_vel ──┐
                                        ├─ velocity_gate ─ /atom/base/cmd_vel ─ TRACER driver
fine_adjust ──── /atom/base/fine_cmd_vel ─┘

/atom/safety/stop (Bool true) ─→ latch stop, clear commands, disable base
                            └→ /atom/safety/stopped ─→ mission / fine-adjust / gripper
```

- 启动时停止锁存、底盘 disabled。reset 只解除软件锁存；切换来源会重新 disabled 并清空所有缓存，之后仍须明确 enable，且只接受新的速度命令。
- `select_fine_adjust` 的 false 选择 Nav2，true 选择微调。当前采用人工/上层明确交接，不自动抢占运行任务。
- 输入命令超时 0.3 s、扫描接收/采集时效 0.5 s，默认需要前方有效扫描；非法非平面/非有限命令锁存停止。门控限幅 0.15 m/s、0.2 rad/s，均为开发参数，不是验收后的安全速度。
- 微调默认需要新鲜标签、scan、TF 和自身控制权；丢失/过期时单次 action 终止并发零。follow 模式也受同一所有权和停止约束。标签默认是当前小架子的 AprilTag 36h11 ID 0、黑框边长 0.040 m；停靠距离尚需按实际可达空间调整。
- TRACER 下游额外增加 steady-clock 命令超时归零，避免门控进程消失后继续保留速度目标。该 300 ms 阈值及 50 ms 检查周期只说明软件配置；没有实测停止距离或延迟。
- 夹爪整机模式在停止状态未收到、为 true 或超过 0.5 s 未更新时拒绝新运动并请求 STOP 保持位置；保留传感器、固件故障、租约和力标定门。
- `/estop` true 兼容旧网页停止；false 不能直接清锁。网页 reset 改为调用显式 reset service，底盘仍 disabled。

当前门控范围是底盘和已选中的夹爪。新入口没有启动物理 arm driver，不能声称已经实现全系统物理停止。既有 arm-only supervisor 也不能自动等同于整机监督。硬件急停、遥控接管、机械臂故障接口和三者的停止/复位行为仍需整机验收。

## 使用

构建主环境仍使用 `./scripts/atom.sh build`，Docker 增加 Nav2、点云切片和 ROS 图像依赖，并从 `atom_mobile_jazzy.repos` 导入底盘来源、应用可重复的补丁。供应商源保存在容器/忽略目录，不复制到 ATOM package。

在已构建的 Jazzy shell 内：

```bash
# 只发布模型及审阅关节状态；无硬件与运动
ros2 launch atom_base mobile.launch.py

# 假底盘接口链路，可选网页 http://localhost:8080
ros2 launch atom_base mobile.launch.py backend:=fake web:=true arm_mount_yaw:=0.0

# 修改朝向示例，仅改变模型审阅参数，不能据此认定实物方向
ros2 launch atom_mobile_description display.launch.py arm_mount_yaw:=1.57079632679
```

仅在上述 **fake** 环境测试运动时，另一终端可依次：

```bash
ros2 service call /atom/safety/reset std_srvs/srv/Trigger '{}'
ros2 service call /atom/base/select_fine_adjust std_srvs/srv/SetBool '{data: false}'
ros2 service call /atom/base/enable std_srvs/srv/SetBool '{data: true}'
ros2 topic pub --once /mission_cmd std_msgs/msg/String '{data: "{\"cmd\":\"goto\",\"x\":0.1,\"y\":0.0,\"yaw\":0.0,\"label\":\"check\"}"}'
ros2 topic pub --once /atom/safety/stop std_msgs/msg/Bool '{data: true}'
```

`backend:=external navigation:=true` 是连接外部 `/scan`、`/scan_low`、`/odometry/filtered` 的 Nav2 入口；外部来源必须拥有唯一 `odom→base_link`。真实驱动单独从 `tracer.launch.py` 显式 opt-in，且不负责设置 CAN 权限或清除硬件故障。它启动 wheel/IMU EKF；未提供 IMU 时不能声称已经验证轮速/陀螺融合。`gripper:=true` 仅允许 external + 系统时钟，默认 `gripper_motion:=false`。硬件示例不作为当前已经获准或验收的运动流程。

不再执行旧 `install.sh`，不运行原先按名称批量 kill 的清理脚本。原始 Livox 驱动/SDK、Tinkerforge 服务与 Python 依赖、RealSense 驱动需要在硬件电脑上核实；本轮没有把它们的 Humble 支持声明转换为 Jazzy 实机兼容性。ROS 标准消息接口不能代替驱动验证。

## 导出与验证

已有导出位于 `output/mobile_robot_20261022/atom_mobile.urdf` / `.srdf`，附带 `mount_parameters.json` 和 `assembly_review.png`。预览现改为原始 visual 网格的正视/侧视正交投影，标出共同中心线和安装中心；不改变 URDF 几何。零关节角仅供布局审阅。

```bash
tmp/gripper_model_env/bin/python tools/base/export_description.py \
  --vendor-root tmp/xarm_ros2 --output /tmp/atom_mobile_review
```

导出器核对 D-007 厂商 commit；拒绝非有限参数和覆盖已有输出目录。导出的 `package://` mesh 引用需要对应的已安装 description package。

`tools/base/validate_jazzy.sh` 构建本次 package 与固定版本 TRACER/UGV 源，运行已有夹爪/描述回归、新的几何/门控/系统停止检查、urdfdom 和理想底盘端到端检查。`smoke_jazzy.py` 只使用假底盘；`check_nav2_jazzy.py` 用合成 scan/odom 实例化真正 Nav2 节点，并向当前估计位姿发目标来验证 BT 加载，速度门保持停止。它们都不打开硬件。

本轮实际结果：

| 检查 | 结果与条件 |
| --- | --- |
| Jazzy 构建 | 11 个 package 通过，包括固定版 TRACER/UGV、现有 gripper/interface/description 和新增两个 package |
| Python/ROS 回归 | 45 项通过：mobile description 4、速度策略 6、夹爪 29、原夹爪描述 2、原 arm+tool 描述 4；夹爪使用假串口设备 |
| urdfdom | 整机单根 `base_link`，解析通过 |
| 假底盘链路 | 9 项通过：默认/复位 disabled、JSON→action→门控→反馈、805 mm runtime TF、来源互斥、命令过期、停止、复位不恢复、网页状态及安装地图 |
| 真 Nav2 配置 | 10 个实际 Nav2/localization 节点 active，合成 scan/odom 条件下当前位姿目标返回 SUCCEEDED，验证自定义 BT 加载；速度门保持停止 |
| 生产微调 action | 5 项通过：停止时拒绝、并发互斥/闭环完成、停止中断、action 取消、过期目标中断；输入为合成 correction 和理想底盘 |

每条运行检查记录的是一次最终成功执行，不代表统计重复性。测试容器是 Ubuntu 24.04 / ROS 2 Jazzy，安装 Nav2 1.3.13；使用本地 `ros:jazzy-ros-base` digest `066420e07f60aa18262f2479981def87ebcfcec42eefb0c0c57c4a46098348ca` 构建目标验证镜像，**没有重新构建完整生产镜像或重跑原 arm Gazebo 轨迹回归**。D-007 的生产基础镜像 pin 保持不变。所有测试均未连接实物，不能外推精度、力、停靠、停止延迟或动力学。

可维护的机器可读结果保存在 [validation_summary.json](data/mobile/20261022/validation_summary.json)；完整日志/JUnit 在忽略目录 `tmp/mobile_integration_20261022/ros/`。`check_fine_adjust.py` 还验证了真实微调 action 的互斥、取消与数据时效；它没有替代生产控制实现。

## 尚需实物输入

底盘 top 离地高度及 frame 定义；安装 yaw；支架 footprint/截面/横梁/质量与 CoM；真实底盘几何、轮组参数；当前法兰/夹爪/相机安装对应的手眼与 TCP；实际指爪编码器映射；带载导航包络、停靠误差、制动/遥控/硬件急停测试。805 mm 只解决 top→arm 的高度输入，不能同时解决这些项目。

## 2026-10-22 — PNG 中心对齐核对

用户指出原斜视 PNG 看起来安装偏心。逐级计算 URDF 变换后，底盘 `base_link` 的 XY 为 [0,0] m，机械臂 `link_base` 的 XY 也为 [0,0] m；厂商底座 visual 的局部 X/Y 包络均约为 [-0.095,+0.095] m，原点与其几何包络中心重合。top→arm 的 Z 差为 0.805 m。本次只核对源码模型，没有新增实物测量。

原图的斜视投影、未标中心线及相近颜色不利于判断对中。已改为原始网格的正视/侧视图，橙色突出机械臂底座，红色竖线标出共同中心；未修改 URDF 安装位置。新图为 `output/mobile_robot_20261022/mount_centre_front_side.png`，计算记录为同目录 `mount_centre_check.json`。底盘/支架外形、150 mm top 名义高度及物理 yaw 的待确认状态保持不变。

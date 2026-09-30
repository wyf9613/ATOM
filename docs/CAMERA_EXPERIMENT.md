# 腕部相机与双层试管架实验环境

日期：2026-09-25。当前完成了 Gazebo 双层工位、临时 G1 夹爪、腕部相机、正面 Tag 检测和无环境避障的两段接近仿真；试管从同一架槽 1 到槽 2 的接触抓取与放置尚未完成。

## 场景与边界

两组试验互斥：`camera_mode=rgb` 安装一台普通彩色相机；`camera_mode=depth` 安装一台 RGB-D 相机，它自身输出 RGB 与深度。两组相机均以固定关节连接到临时 G1 的 `xarm_gripper_base_link`，随夹爪和机械臂末端同步运动；当前仿真安装变换为 `xyz=[-0.080, 0, 0.060] m`、`rpy=[0, -1.5708, 0] rad`，使相机光轴与夹爪 `+Z` 指向一致，并将镜头移到夹爪中心线下侧以减少自遮挡。相机为 640×480 px、1.0472 rad 水平视场角和 10 Hz 更新率。安装位姿、真实候选设备的尺寸、质量、噪声、重量限制和价格尚未实测或纳入模型，当前数据不能用于最终采购选型。

四槽试管架放在桌面上方的第二层搁板。槽间距为 0.070 m；每槽有上层敞开的导向孔和下层承托底板。每槽**正面**竖直贴一枚 0.040 m AprilTag 36h11，ID `0,1,2,3` 对应槽 `0,1,2,3`。一根独立 Gazebo 动态试管初始置于槽 1，槽 2 保持空置作为同架放置目标。试管暂定外半径 0.007 m、长度 0.095 m、质量 0.015 kg，使用十二片半透明管壁和封闭底部的视觉/碰撞几何，并设置独立惯量与暂定摩擦系数 0.6；实验 world 重力为 9.81 m/s²。此近似空心模型不代表真实玻璃/塑料的材料响应，仿真深度图也不能代表真实相机对透明表面的测量。所有尺寸、物性和架位均为演示输入，待实测替换。

预定取放任务是“同一试管架槽 1（AprilTag ID 1）→ 槽 2（AprilTag ID 2）”。抓取位和放置位均应从各自槽位 tag 的观测与已标定槽位偏移生成，而不是使用已删除的桌面目标架坐标。

## 两阶段观察流程

当前任务把运动拆成“预观察”和“接近”两个阶段。两者的边界必须保持清楚：预观察只把相机带到合适的高度和朝向，接近阶段才使用视觉结果修正末端的水平位置并进入抓取或放置区域。

### 预观察阶段

预观察阶段从一个 topic 同时接收粗略方向和预观察高度：

```text
topic: /atom/pre_observation_target
type:  geometry_msgs/msg/PoseStamped
frame: link_base
pose.position.z: 预观察 TCP 高度（m）
pose.orientation yaw: 粗略方向（rad，绕 link_base +Z，逆时针为正）
pose.position.x/y: 当前阶段不作为输入，由目标位姿节点按 yaw 重新计算
```

当前仿真方向值暂定为：

```text
theta_observation = theta_true + U(-5 deg, +5 deg)
```

这个值只代表带底座定位误差的预定方向。预观察高度由理论 Tag 高度和当前 provisional 相机安装偏移计算得到。后续方向和高度由底座/试管架定位模块提供，不能把该输入当作绝对精确的最终抓取位姿。
当前任务的目标 Tag ID 仍由任务上下文指定：夹取使用 ID 1，放置使用 ID 2；临时 `PoseStamped` topic 本身暂不携带目标 ID。

预观察动作顺序为：

1. 订阅目标方向和已知目标高度；
2. `pre_observation_target_pose` 默认将 TCP 放到 `link_base` 原点沿该方向 0.35 m 的位置，并把输入高度作为 TCP z；
3. 把夹爪延伸方向调整到订阅的粗略方向，使相机光轴朝向目标 Tag；
4. 等待机械臂和图像稳定，采集 RGB 或 RGB-D 数据；
5. 用 Tag ID、相机内参、深度有效性和时间戳检查观测；
6. 观测有效后输出目标位姿，转入接近阶段。

由于当前传感器视野和安装位置不能充分承担避障，预观察阶段不主动搜索大范围的 `x/y` 位置，也不宣称已经完成完整避障。当前启动脚本中已有的固定关节观察往返仍是旧的传感器基线；topic 驱动的预观察与两段接近已接入独立演示脚本。

### 接近阶段

接近阶段已实现为两段。任务 topic 至少给出目标 Tag ID 和动作类型（抓取/放置）；本轮只按 ID 从预观察看到的多个 Tag 中选择目标，动作类型先记录。前端参考点定义为 `link_eef` 原点沿夹爪延伸方向 0.20 m，距 Tag 平面的距离沿朝向相机一侧的法线测量。第一段使用预观察结束时选定 Tag 的观测位姿，让该前端点到达距 Tag 平面 0.40 m 的对准位；第二段使用第一段运行期间最新有效的同 ID 观测，沿 Tag 法线平行射线接近到 0.10 m。末端原点的高度、横滚、俯仰在两段中保持预观察结束值，只调整 `x/y/yaw`；相机视线角度约束以安装变换算出的相机光心和目标 Tag 中心为准，不用夹爪轴代替。

两段各自在规划开始时固定一份目标快照。MoveIt 先尝试路径约束规划；第一段不满足严格倾斜阈值时回退到恒高/恒倾斜笛卡尔锚点。执行前用 FK 逐点验收高度、倾斜与相机到 Tag 中心的视线角度；第二段还限制前端点沿法线射线移动。两段运动期间继续从 RGB 或 RGB-D 以暂定最高 5 Hz 处理选定 Tag，发布并记录位姿、时间戳和质量；这些更新不修改当前执行轨迹。第二段到位后在命令行打印两段结果、所用目标版本以及按实际 TF 计算的 0.10 m 平面距离和沿途约束误差。此次仅实现无环境障碍的接近；搁板、试管架、试管的 PlanningScene 碰撞体和运动中重规划属于后续工作。详细接口和异常边界见 [`EYE_IN_HAND_TUBE_PICK_PLAN.md`](EYE_IN_HAND_TUBE_PICK_PLAN.md)。

临时夹爪使用 [UFactory 官方 `xarm_ros2`](https://github.com/xArm-Developer/xarm_ros2) 中支持 `uf850` 的 BSD-3-Clause G1 开源描述及 `uf850_gripper_traj_controller`，通过 `demo_gripper:=true` 启用。它不代表 Project ATOM 最终夹爪。夹爪控制器已接受一条 `drive_joint=0.5 rad` 位置指令；指尖与试管的可靠接触、夹持力、滑移和放置均未验证。裸臂入口仍可用 `camera_mode=none demo_gripper:=false` 运行。运行时 world 和工装 SDF 在容器 `/tmp` 生成，不修改 vendor 文件或 `previous report/`。

## 运行与录像

在仓库根目录运行，保持两种相机的架位扰动一致：

```bash
./scripts/atom.sh demo camera --camera rgb
./scripts/atom.sh demo camera --camera depth
```

后三个参数依次是上层搁板及源架整体在机械臂基座坐标中的 `dx`（m）、`dy`（m）和偏航扰动（rad）；暂允许 `|dx|,|dy| ≤ 0.05 m`、`|dyaw| ≤ 0.2 rad`。旧的固定六关节观察往返仍可通过原入口回归；新的预观察入口见下文，它由独立目标位姿节点按方向生成默认 0.35 m 目标、规划高度和姿态，并在静止帧中累积 Tag 1/2 的观测。

输出在 `tmp/camera_experiment/<模式_时间戳>/`：条件、启动/轨迹/探测日志，`report.json`（tag ID、相机坐标位姿、图像信息），`rgb_annotated.png`；RGB-D 还保存 `depth_m.npy` 和 `depth_preview.png`。图形桌面录像入口为：

```bash
./scripts/atom.sh demo camera --gui --camera rgb
```

将 `rgb` 换成 `depth` 即为另一组。Gazebo GUI 与 RViz 会保持打开，按 `Ctrl+C` 结束；图片和日志放在 `tmp/camera_experiment/gui_current/`。单独开发可运行：

```bash
docker compose -f docker-compose.jazzy.yaml run --rm atom-jazzy \
  ros2 launch atom_xarm_sim uf850_arm_only.launch.py camera_mode:=rgb demo_gripper:=true
```

`scene_fixtures:=false` 或 `fixture_group:=shelf|rack|tube` 可做碰撞隔离诊断；其中 `rack` 会同时加载试管架及其支撑二层架，避免试管架悬空。`camera_probe` 只采集和解码，不发布抓取目标或驱动夹爪。

## 已验证与待完成

完整双层场景中，RGB 模式的 MoveIt 观察往返通过，正面 tag ID 0 被解出。RGB-D 一键流程也解出 ID 0、保存深度图，并完成观察往返；最终空心管/导向架版本的一帧有效深度像素比例为 0.7779（640×480 px），不代表透明试管的深度质量。图形入口已打开 Gazebo 与 RViz，并完成 RGB 观察轨迹和正面 tag 检测。这些都是少量仿真运行，尚无检测率、误差分布或采购结论。Gazebo/桥接接口以 [Gazebo Harmonic 传感器文档](https://gazebosim.org/docs/harmonic/sensors/)与 [ros_gz RGB-D 桥接示例](https://github.com/gazebosim/ros_gz/blob/ros2/ros_gz_sim_demos/config/rgbd_camera_bridge.yaml)为依据。

预观察脚本入口为：

```bash
./scripts/atom.sh demo approach --gui --camera rgb
./scripts/atom.sh demo approach --gui --camera depth
```

默认脚本使用 0.35 m 预观察目标距离；第五个参数可覆盖该值。脚本先完成预观察，再按任务 topic 指定的 Tag ID 执行两段接近；未收到外部任务时默认发布 `{"tag_id":1,"action":"pick"}`（`std_msgs/msg/String` JSON）。观测发布到 `/atom/approach/tag_observation`（同为 JSON），每条包含选定 Tag 的 `link_base` 位姿、图像时间戳和深度质量；结果保存在 `tmp/camera_experiment/pre_observation_current/` 下的 `pre_observation_report.json`、`approach_report.json`、`tag_observations.jsonl` 和标注图；成功运行后另保存带 `_rgb` 或 `_depth` 后缀的报告与逐帧观测文件，避免切换模式覆盖。名义场景 RGB 与 RGB-D 各完成一次预观察和两段接近仿真；原 0.2 m 目标在当前高度/姿态下不可采样。实际试管夹取、放置与环境避障未验证。

理论 Tag 位姿当前按 launch 中的 Gazebo 机器人生成位姿转换到 `link_base`；这是为了补偿临时 `world → link_base` 单位 TF，后续应由统一的实测/仿真 TF 链替换。RGB-D 模式目前用同步深度统计质量，不把透明试管深度直接融合进 Tag 位姿。

## 2026-09-25 阶段性精度与重复运行记录

在同一名义场景中，各选一例完整成功的 Tag1 / pick 运行，对比理论机架几何和末端前端参考点；RGB 种子为 `2026092504`，RGB-D 种子为 `2026092502`。终点水平位置误差分别为 12.573 mm 和 11.587 mm；其中横向误差为 1.431 mm 和 4.684 mm，前后距离误差为 12.491 mm 和 10.598 mm。对准段所选 Tag 的逐帧三维定位误差均值分别为 10.512 mm（RGB，N=100 帧）和 9.494 mm（RGB-D，N=98 帧）；垂直接近段为 6.200 mm 和 5.255 mm（各 N=40 帧）。这些帧在同一次轨迹内相关，不能当作独立重复试验，也不能据此判定 RGB-D 有真实定位增益。计算口径、逐帧样本方差、原始记录位置见 [单例对比报告](RGB_VS_RGBD_SINGLE_RUN_COMPARISON_20260925.md)。

团队另报告完成了 10 次 RGB 试验，其中 4 次因规划失败而终止，即该组条件下观测到 4/10（40%；若把这 10 次视作独立同条件样本，Wilson 95% 区间约 16.8%–68.7%）。这 10 次的场景参数、随机种子、逐次日志和失败细分类尚未归档到本仓库，独立同条件假设也未核对，故不与上面的单例精度统计合并，不据此推断跨场景成功率或断言全部失败由 RGB 解算误差直接造成。后续应归档逐次日志，区分目标位姿误差、法线射线不一致、MoveIt 规划和控制器就绪问题。阶段性英文展示见 [HTML 报告](../output/slides/ATOM_observation_progress_2026-09-25.html)及 [演示视频](../output/video/Observation.webm)。

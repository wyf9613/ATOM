# 腕部相机与双层试管架实验环境

日期：2026-09-24。当前完成了 Gazebo 双层工位、临时 G1 夹爪、腕部相机和正面 tag 的观察演示；尚未完成试管接触抓取及放入桌面目标架。

## 场景与边界

两组试验互斥：`camera_mode=rgb` 安装一台普通彩色相机；`camera_mode=depth` 安装一台 RGB-D 相机，它自身输出 RGB 与深度。两组采用同一临时腕部侧支架位姿、640×480 px、1.0472 rad 水平视场角和 10 Hz 更新率。真实候选设备的尺寸、质量、噪声、重量限制和价格尚未纳入模型，当前数据不能用于最终采购选型。

源试管架放在桌面上方的第二层搁板，桌面另放一只目标试管架。两架各四槽，槽间距 0.070 m；每槽有上层敞开的导向孔和下层承托底板。源架每槽**正面**竖直贴一枚 0.040 m AprilTag 36h11，ID `0,1,2,3` 对应槽 `0,1,2,3`。一根独立 Gazebo 动态试管初始置于源架槽 1。试管暂定外半径 0.007 m、长度 0.095 m、质量 0.015 kg，使用十二片半透明管壁和封闭底部的视觉/碰撞几何，并设置独立惯量与暂定摩擦系数 0.6；实验 world 重力为 9.81 m/s²。此近似空心模型不代表真实玻璃/塑料的材料响应，仿真深度图也不能代表真实相机对透明表面的测量。所有尺寸、物性和架位均为演示输入，待实测替换。

预定取放任务是“源架槽 1 → 桌面目标架槽 1”；目标架当前保持空置，供后续放置验证。

临时夹爪使用 [UFactory 官方 `xarm_ros2`](https://github.com/xArm-Developer/xarm_ros2) 中支持 `uf850` 的 BSD-3-Clause G1 开源描述及 `uf850_gripper_traj_controller`，通过 `demo_gripper:=true` 启用。它不代表 Project ATOM 最终夹爪。夹爪控制器已接受一条 `drive_joint=0.5 rad` 位置指令；指尖与试管的可靠接触、夹持力、滑移和放置均未验证。裸臂入口仍可用 `camera_mode=none demo_gripper:=false` 运行。运行时 world 和工装 SDF 在容器 `/tmp` 生成，不修改 vendor 文件或 `previous report/`。

## 运行与录像

在仓库根目录运行，保持两种相机的架位扰动一致：

```bash
./scripts/docker/jazzy_camera_experiment.sh rgb 0.0 0.0 0.0
./scripts/docker/jazzy_camera_experiment.sh depth 0.0 0.0 0.0
```

后三个参数依次是上层搁板及源架整体在机械臂基座坐标中的 `dx`（m）、`dy`（m）和偏航扰动（rad）；暂允许 `|dx|,|dy| ≤ 0.05 m`、`|dyaw| ≤ 0.2 rad`。每次运行启动 Gazebo、TF、控制器及 MoveIt，执行经搁板间隙验证的六关节观察往返，偏移量为 `[+0.25,-0.16,-0.19,+0.15,+0.16,-0.18]` rad，并在观察位停留 25 s。`camera_probe` 保存第一帧成功解出的正面 tag。

输出在 `tmp/camera_experiment/<模式_时间戳>/`：条件、启动/轨迹/探测日志，`report.json`（tag ID、相机坐标位姿、图像信息），`rgb_annotated.png`；RGB-D 还保存 `depth_m.npy` 和 `depth_preview.png`。图形桌面录像入口为：

```bash
./scripts/docker/jazzy_camera_experiment_gui.sh rgb 0.0 0.0 0.0
```

将 `rgb` 换成 `depth` 即为另一组。Gazebo GUI 与 RViz 会保持打开，按 `Ctrl+C` 结束；图片和日志放在 `tmp/camera_experiment/gui_current/`。单独开发可运行：

```bash
docker compose -f docker-compose.jazzy.yaml run --rm atom-jazzy \
  ros2 launch atom_xarm_sim uf850_arm_only.launch.py camera_mode:=rgb demo_gripper:=true
```

`scene_fixtures:=false` 或 `fixture_group:=shelf|racks|tube` 可做碰撞隔离诊断。`camera_probe` 只采集和解码，不发布抓取目标或驱动夹爪。

## 已验证与待完成

完整双层场景中，RGB 模式的 MoveIt 观察往返通过，正面 tag ID 0 被解出。RGB-D 一键流程也解出 ID 0、保存深度图，并完成观察往返；最终空心管/导向架版本的一帧有效深度像素比例为 0.7779（640×480 px），不代表透明试管的深度质量。图形入口已打开 Gazebo 与 RViz，并完成 RGB 观察轨迹和正面 tag 检测。这些都是少量仿真运行，尚无检测率、误差分布或采购结论。Gazebo/桥接接口以 [Gazebo Harmonic 传感器文档](https://gazebosim.org/docs/harmonic/sensors/)与 [ros_gz RGB-D 桥接示例](https://github.com/gazebosim/ros_gz/blob/ros2/ros_gz_sim_demos/config/rgbd_camera_bridge.yaml)为依据。

下一步先测量 tag 到槽位、夹爪 TCP 和相机手眼外参，建立 MoveIt 工装碰撞场景，再验证“识别源槽 → 接近透明试管 → 接触夹持 → 提升 → 搬运 → 放入桌面目标槽 → 松开”。录像中目前应标为“观察环境/相机对照演示”，不能标为已完成取放。

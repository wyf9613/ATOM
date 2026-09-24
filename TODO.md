# Gazebo 试管转移 Demo TODO

目标：UF850 从桌面上方第二层搁板的源试管架中取出一支透明试管，再放入桌面上的目标试管架。当前演示任务固定为源槽 1 → 目标槽 1。这里记录交给组员继续完成的工作，并区分已有环境与尚未完成的取放能力。

## 当前已有

- [x] UF850 的 Gazebo Harmonic / MoveIt 观察环境；裸臂入口仍可单独启动。
- [x] 桌面二层搁板、上层四槽源架、桌面四槽目标架。槽位上层有导向孔、下层有承托面。
- [x] 源架每槽正面一个 AprilTag 36h11（ID 0–3），腕部 RGB 和 RGB-D 两种模式互斥。
- [x] 源槽 1 中的透明动态试管模型，含近似空心管壁、封闭底部、质量、惯量、碰撞和重力。
- [x] 临时使用 UFactory 官方 xArm G1 夹爪模型；有独立 `drive_joint` 控制器。
- [x] RGB / RGB-D 观察轨迹和 tag 检测脚本；Gazebo GUI + RViz 录像入口。
- [x] 以上是仿真观察基线；尚未成功夹起或转移试管。试管尺寸/物性、支架尺寸、夹爪接触和相机外参均为临时值。

详情和启动方式见 [docs/CAMERA_EXPERIMENT.md](docs/CAMERA_EXPERIMENT.md)，总体感知设计见 [docs/EYE_IN_HAND_TUBE_PICK_PLAN.md](docs/EYE_IN_HAND_TUBE_PICK_PLAN.md)。

## 必须完成：试管抓取与放置

- [ ] 在 Gazebo GUI 检查当前场景外观和相对位置，按组内目标画面调整：机械臂、二层架、源架、桌面目标架及试管均须清晰可见；记录一张验收截图。
- [ ] 检查临时 G1 的关节 mimic、两指开合方向/行程、手指碰撞模型和 Gazebo 实际运动。控制器接受命令不等于手指和物体已正确接触。
- [ ] 将搁板、两只试管架、导向孔及桌面加入 MoveIt PlanningScene；确保规划会绕开搁板和试管架。观察轨迹不能代替取放轨迹验收。
- [ ] 确定相机、AprilTag、槽位、试管中心与临时 G1 TCP 的坐标变换。用 Gazebo 真值比对 tag 估计，并注明 provisional 数值；之后以实测尺寸和手眼/TCP 标定替换。
- [ ] 实现安全的状态序列：观察并选中源槽 → 预抓取 → 下降到抓取位 → 张爪/闭爪 → 验证夹持 → 垂直提升 → 搬运 → 目标槽上方 → 插入/放置 → 松爪 → 验证试管留在目标槽。
- [ ] 抓取必须通过夹爪与试管的 Gazebo 碰撞/接触实现；不要用 teleport、仅移动视觉模型或默认成功的模拟信号冒充抓取。若为了录像需要模拟辅助附着，需在界面和日志中明确标出，并与真实物理抓取区分。
- [ ] 将被夹持试管作为 MoveIt attached collision object 管理；检查提起时不会与架体/搁板碰撞，放下后正确解除附着。
- [ ] 至少重复 RGB 与 RGB-D 模式各 3 次，记录检测到的 tag ID、规划/执行结果、抓取成功、放置成功和失败原因。不要据此少量理想仿真直接下相机采购结论。

## 最终演示与交付

- [ ] 在 Ubuntu/ROS 2 Jazzy/Gazebo Harmonic 容器中运行构建和取放验收；保留命令、日志和参数。
- [ ] 图形模式分别录制普通 RGB 与 RGB-D 两组；视频要展示“源架槽 1 → 桌面目标架槽 1”的完整动作。若仍未完成接触抓取，视频标题标为“观察/规划演示”，不能称为取放成功。
- [ ] 更新 `docs/PROJECT_STATUS.md`、`docs/KNOWN_ISSUES.md`、`docs/SIM2REAL_LOG.md`；将试管架尺寸、试管质量/惯量、相机外参和夹爪 TCP 的实测值、单位、测量方法、样本数和不确定度记录下来。
- [ ] 检查最终 `git diff`、构建结果与录像文件，再提交组内可复现版本。

## 当前运行命令

```bash
# 单独跑相机观察/识别环境
./scripts/docker/jazzy_camera_experiment.sh rgb 0.0 0.0 0.0
./scripts/docker/jazzy_camera_experiment.sh depth 0.0 0.0 0.0

# 图形环境，供组员录制当前观察演示
./scripts/docker/jazzy_camera_experiment_gui.sh rgb 0.0 0.0 0.0
```

图形运行时按 `Ctrl+C` 退出；日志和图像在 `tmp/camera_experiment/`。当前 GUI 入口会自动运行观察往返与相机检测，不会执行试管抓取/放置。

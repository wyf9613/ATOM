# Gazebo 同架槽位转移 Demo TODO

目标：UF850 从桌面上方第二层搁板的四槽试管架中取出一支透明试管，再放回同一试管架的另一槽。当前阶段任务固定为槽 1（AprilTag ID 1）→ 槽 2（AprilTag ID 2）。这里记录交给组员继续完成的工作，并区分已有环境与尚未完成的取放能力。

## 当前已有

- [x] UF850 的 Gazebo Harmonic / MoveIt 观察环境；裸臂入口仍可单独启动。
- [x] 桌面二层搁板及上层四槽试管架。槽位上层有导向孔、下层有承托面。
- [x] 源架每槽正面一个 AprilTag 36h11（ID 0–3），腕部 RGB 和 RGB-D 两种模式互斥。
- [x] 源槽 1 中的透明动态试管模型，含近似空心管壁、封闭底部、质量、惯量、碰撞和重力。
- [x] 临时使用 UFactory 官方 xArm G1 夹爪模型；有独立 `drive_joint` 控制器。
- [x] RGB / RGB-D 观察轨迹和 tag 检测脚本；Gazebo GUI + RViz 录像入口。
- [x] 以上是仿真观察基线；尚未成功夹起或转移试管。试管尺寸/物性、支架尺寸、夹爪接触和相机外参均为临时值。

## 当前任务流程定义

任务拆成“预观察”和“接近”两个阶段。预观察只负责把末端移动到可观测姿态，不执行抓取或水平接近。

- [x] 预观察阶段订阅 `/atom/pre_observation_target`（暂定 `geometry_msgs/msg/PoseStamped`，参考系为当前仿真的 `link_base`）；消息的 `pose.position.z` 是相机与 Tag 对齐所需的预观察 TCP 高度，姿态 yaw 是粗略方向，x/y 字段不作为目标位置输入。当前仿真值暂用 `theta_true + random(-5°, +5°)`，后续由底座位置和试管架位置计算；该值表示带底座定位误差的粗略方向，不能当作绝对准确的目标角度。
- [x] 独立 `pre_observation_target_pose` 节点将输入方向转换为规划目标：当前默认目标位置为 `0.35·[cos(yaw), sin(yaw), 0]` 加输入高度，目标姿态使夹爪延伸方向与该方向一致，并发布 `/atom/pre_observation_pose`；预观察执行节点订阅该结果后调用 MoveIt。传感器限制下不在此阶段承担完整避障。
- [x] 末端到达后等待稳定，采集 RGB 或 RGB-D 图像，按 Tag ID、相机内参、深度质量和时间戳生成观测结果；观测结果有效后才允许进入接近阶段。当前脚本允许 Tag1/Tag2 在相邻静止帧中分别解出，再转换到 `link_base`。
- [ ] 将 provisional 输入发布替换为底座/试管架定位模块的真实 `/atom/pre_observation_target` 发布。
- [x] 接近阶段已实现无环境障碍的两段运动：任务 topic 指定 Tag ID/动作，以 `link_eef` 前方 0.20 m 为前端参考点，先到距 Tag 平面 0.40 m 的对准位，再使用第一段最新有效观测沿法线射线接近到 0.10 m。MoveIt 规划、FK 逐点验收与执行中抽样检查高度/姿态/视线；以最高 5 Hz 发布并记录选定 Tag 观测，段内不重规划。RGB 与 RGB-D 名义场景各完成一次端到端仿真；仍未抓取或放置。
- [ ] 后续再将搁板、试管架、试管等碰撞几何加入 MoveIt PlanningScene，验证环境避障；依据测试结果决定是否需要运动中重规划或连续视觉伺服。
- [x] 使用默认 0.35 m 目标运行 `scripts/docker/jazzy_pre_observation_gui.sh rgb|depth`，完成预观察及两段接近的名义场景仿真验收；原 0.2 m 目标在当前高度/姿态下不可采样，暂不作为默认值。
- [x] RGB、RGB-D 各保留一例完整成功运行，按独立仿真真值计算终点与逐帧 Tag 定位误差；已制作阶段性 [HTML 报告](output/slides/ATOM_observation_progress_2026-09-25.html)和 [观察视频](output/video/Observation.webm)。团队另完成 10 次 RGB 测试，报告其中 4 次因规划失败终止；逐次日志及条件待归档，不能与两例精度样本混算。详见 [单例对比](docs/RGB_VS_RGBD_SINGLE_RUN_COMPARISON_20260925.md)。

详情和启动方式见 [docs/CAMERA_EXPERIMENT.md](docs/CAMERA_EXPERIMENT.md)，总体感知设计见 [docs/EYE_IN_HAND_TUBE_PICK_PLAN.md](docs/EYE_IN_HAND_TUBE_PICK_PLAN.md)。

## 必须完成：试管抓取与放置

- [ ] 在 Gazebo GUI 检查当前场景外观和相对位置，按组内目标画面调整：机械臂、二层架、四槽试管架及试管均须清晰可见；记录一张验收截图。
- [ ] 检查临时 G1 的关节 mimic、两指开合方向/行程、手指碰撞模型和 Gazebo 实际运动。控制器接受命令不等于手指和物体已正确接触。
- [ ] 将搁板、四槽试管架、导向孔及桌面加入 MoveIt PlanningScene；确保规划会绕开搁板和架体，并允许受控进入槽 1 和槽 2 的接触区域。观察轨迹不能代替取放轨迹验收。
- [ ] 在预观察位姿选择中加入臂展/可达性检查；在更新的 Tag 法线射线偏离对准点时增加重新对准段，并归档 RGB 十次实验的逐次条件、日志和失败分类。
- [ ] 获取上一组夹爪控制代码，先验证通信、手指运动和接触反馈，再把视觉接近接到完整的抓取与放置序列。
- [ ] 设计并 3D 打印试管架及相机转接件，测量 Tag—槽位、相机—夹爪和 TCP 变换；开展小范围、受监督的实机实验。
- [ ] 确定相机、AprilTag ID 1/2、对应槽位、试管中心与临时 G1 TCP 的坐标变换。用 Gazebo 真值分别比对两个 tag 的估计，并注明 provisional 数值；之后以实测尺寸和手眼/TCP 标定替换。
- [ ] 实现安全的两阶段状态序列：预观察（订阅粗略方向、调整高度和夹爪朝向、采集并验证 Tag）→ 接近槽 1 并完成抓取 → 提升/搬运 → 预观察槽 2 → 接近槽 2 并完成放置 → 验证试管留在槽 2。
- [ ] 抓取必须通过夹爪与试管的 Gazebo 碰撞/接触实现；不要用 teleport、仅移动视觉模型或默认成功的模拟信号冒充抓取。若为了录像需要模拟辅助附着，需在界面和日志中明确标出，并与真实物理抓取区分。
- [ ] 将被夹持试管作为 MoveIt attached collision object 管理；检查提起时不会与架体/搁板碰撞，放下后正确解除附着。
- [ ] 至少重复 RGB 与 RGB-D 模式各 3 次，记录是否检测到源 Tag ID 1 和目标 Tag ID 2、规划/执行结果、抓取成功、放置成功和失败原因。不要据此少量理想仿真直接下相机采购结论。

## 最终演示与交付

- [ ] 在 Ubuntu/ROS 2 Jazzy/Gazebo Harmonic 容器中运行构建和取放验收；保留命令、日志和参数。
- [ ] 图形模式分别录制普通 RGB 与 RGB-D 两组；视频要展示“同一试管架槽 1（Tag ID 1）→ 槽 2（Tag ID 2）”的完整动作。若仍未完成接触抓取，视频标题标为“观察/规划演示”，不能称为取放成功。
- [ ] 更新 `docs/PROJECT_STATUS.md`、`docs/KNOWN_ISSUES.md`、`docs/SIM2REAL_LOG.md`；将试管架尺寸、试管质量/惯量、相机外参和夹爪 TCP 的实测值、单位、测量方法、样本数和不确定度记录下来。
- [ ] 检查最终 `git diff`、构建结果与录像文件，再提交组内可复现版本。

## 当前运行命令

```bash
# 单独跑相机观察/识别环境
./scripts/docker/jazzy_camera_experiment.sh rgb 0.0 0.0 0.0
./scripts/docker/jazzy_camera_experiment.sh depth 0.0 0.0 0.0

# 图形环境，供组员录制当前观察演示
./scripts/docker/jazzy_camera_experiment_gui.sh rgb 0.0 0.0 0.0

# 当前预观察 + 两段接近演示（RGB 或 RGB-D）
./scripts/docker/jazzy_pre_observation_gui.sh rgb 0.0 0.0 0.0
./scripts/docker/jazzy_pre_observation_gui.sh depth 0.0 0.0 0.0
```

图形运行时按 `Ctrl+C` 退出；日志和图像在 `tmp/camera_experiment/`。旧 `jazzy_camera_experiment_gui.sh` 仅运行固定关节观察往返与相机检测；新的 `jazzy_pre_observation_gui.sh` 运行 topic 驱动的预观察和两段接近。两者均不会执行试管抓取/放置。

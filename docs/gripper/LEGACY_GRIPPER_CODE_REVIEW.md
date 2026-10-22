# 旧夹爪代码对照审查

> 本文原审查基于同步前版本 7a3442a；其中代码行号及当时 JOG 行为属于该版本快照。2026-10-07 main 同步：当前位置命令使用连续 MOVE，人工微调仍使用 JOG；普通 STOP/cancel 在确认保持后允许恢复，实际故障仍受门槛约束。Linux Jazzy 构建及假串口 ROS Action 联调已有通过记录，前端实物接入有用户反馈；接触/力标定、带物体停止与机械臂联合任务仍未验收。

日期：2026-10-06。范围：用户提供的 `EE.zip`、`balitom/Capstone_code` 与当前 ESP32/ROS/UI 夹爪代码。接线已由本组更改；旧引脚、参数和操作说明仅作为被审查材料，不作为执行指令。本次没有烧录、打开硬件串口或改变控制代码。

## 结论

值得借鉴的是“磁场基线 → 接触信号 → 有界闭合 → 独立夹持验证”的思路，以及速度/电流诊断。现有代码已经实现基线、磁场差值、运动/反馈门槛和主机接口；真正缺口是磁场与力的标定、接触信号可靠性和稳定夹持验证。旧实现没有提供可以直接继承的力模型，也不足以替代当前控制器。

特别注意：当前 UI/ROS 的 `close` 是分段位置运动，不是磁场闭合或力控制。它在 `controller.py:194` 将目标设为 2000 编码器计数并发送 `JOG`；固件的 `JOG` 调用 `moveTo(..., false)`，不会启用磁场阈值停止。固件的独立 `CLOSE` 仍被 `ATOM_MOTOR_JOG_ONLY=1` 阻断，`ATOM_GRIP_DELTA_UT=-1` 未配置，`force` 请求被拒绝。位置成功始终返回 `grasp_verified=False`，应保留这个边界。

## 来源与版本

- 原始压缩包：`C:\Users\User\Downloads\EE.zip`，218418 bytes；SHA-256：`41DEBBA0E7D5A173526AF59C583FFD01FA395CC47C657443468E9D0614173FEF`。原件未修改。
- GitHub：审查快照提交 `e870e23d632f910f58638850cd3fd7d1b3b07a66`，提交时间 `2026-05-20T15:39:14+10:00`。完整提交号用于固定证据，不将 main 的未来内容当成本次审查内容。
- 临时副本：`tmp/legacy_gripper_review_20261006/`。压缩包解压时跳过 `.git/` 和 `.DS_Store`；没有运行其中的固件、脚本或 hooks。该目录被 Git 忽略，不是长期交付资产。
- 下文 `EE/` 表示解压后的 `End-effector code/`；行号以此次原始源文件为准。

| 材料 | 实际内容 | 借鉴范围 |
| --- | --- | --- |
| `EE/EE_calibration/EE_calibration.ino` | 磁场阈值夹持、速度模式、负载触边标定、G/R 与 GD/RD 文本协议 | 核心实验流程参考；不是已验证控制器 |
| `EE/MagSensorControlDraft/MagSensorControlDraft.ino` | 磁场差模长驱动的 PI 闭合草稿 | 有界输出和积分限幅思路 |
| `EE/basicVelControl/basicVelControl.ino` | 外层速度 PI，读取速度/位置 | 诊断和辨识参考 |
| `EE/basicVelocityCommands/basicVelocityCommands.ino` | f/b/s 手动速度控制 | 旧接线与模式参考 |
| `EE/UoM-RS-Arduino_Firmware.ino` 及配套库 | MATLAB/ChessBot 教学框架、状态分派、多个 STS 电机 | 通用框架；不能视为本夹爪最终部署版本 |
| `EE/SCServo/` | STS/SCS 驱动和示例，metadata 标为 1.0.2 | 只查实现；当前已使用独立固定版本的 FTServo |
| GitHub `ee_publisher.cpp` | ROS 2：JointState → URDF/KDL 正运动学 → `tool0_pos` | 位姿反馈思路；无夹爪命令、串口桥或机械臂运动控制 |
| GitHub `Calibration/` | 三个 Arduino 实验 sketch | 与 zip 重叠，但参数不完全一致 |

GitHub 的 [ee_publisher.cpp](https://github.com/balitom/Capstone_code/blob/e870e23d632f910f58638850cd3fd7d1b3b07a66/ee_publisher.cpp) 是末端位姿发布器，硬编码 `base_link` / `tool0`，不是完整 UR3e 控制工程。快照未提供 `package.xml`、`CMakeLists.txt` 或 launch；邮件所述“arm ROS code”不能扩大解释为完整部署资产。

zip 与 GitHub 的 `EE_calibration` 存在以下源代码差异。这些值是历史配置，没有随附测试条件、样本数或不确定度，不能解释为已验证阈值或物理速度：

| 常量 | zip | GitHub 快照 |
| --- | ---: | ---: |
| `MAX_LOAD`，舵机原始负载阈值 | 240 | 200 |
| `GRIP_SPEED`，速度指令值 | -180 | -100 |
| `GRIPPED`，磁场变化阈值，源文件未标明单位 | 500 | 550 |
| `DROP_SPEED`，速度指令值 | 100 | 50 |
| `RELEASE_DELAY_MS`，ms | 800 | 500 |
| 第二阶段释放速度指令值 | 200 | 150 |

## 可借鉴项与当前实现的对应关系

| 思路 | 旧代码证据 | 当前已有内容 | 建议补充，均未在本次实现 |
| --- | --- | --- | --- |
| 三轴基线与磁场差值 | `EE_calibration:278` 取无载基线；`:322` 计算差值模长 | `motor_control.h:17` 收样；`:112` 计算磁场差；ZERO 平均 20 个有效样本 | 验证无物体时不同位置、运动方向、通电状态的基线变化；检验一个固定基线是否充分。磁场量使用 µT，不能标成 N |
| 接触触发停止 | `EE_calibration:188` 超阈值停止并发 GD | `motor_control.h:59` 有条件阈值保持分支，但当前闭合入口禁用 | 增加经过验证的滤波、连续有效样本/持续时间门槛、迟滞、位置边界和超时。为接触结束提供独立结果与触发样本；当前 `stopMotion()` 只发通用 STOP，无法区分接触与人工停止 |
| 控制留在 MCU | PI 草稿在本地计算输出并限幅 | ESP32 已本地处理运动、心跳、传感器和负载门槛 | 先做确定性的有界接触闭合，再考虑经过标定的局部力控制；不用浏览器/ROS 消息间隔充当力闭环周期 |
| 积分限幅 | `MagSensorControlDraft:114`；`basicVelControl:57` | 当前没有外层 PI，使用 STS 位置模式 | 若以后需要 PI，重新辨识方向/增益/时间尺度，设置积分复位、dt 上下界及饱和处理；不复制历史 Kp/Ki，也不在未辨识舵机内环前叠加速度 PI |
| 速度/电流诊断 | `EE_calibration:309` 读取 speed、position、load、current | 当前 `feedback()` 缓存 position/load/voltage/temperature；本机 FTServo 有 `ReadSpeed(-1)` / `ReadCurrent(-1)` | 在一次成功且已检查 SDK 状态的 `FeedBack()` 后读取缓存速度/电流，按明确字段扩展日志/协议。先保留 raw 单位；实测单位后再换算。用于辨别摩擦、运动/停止与负载特征，不当作已标定指尖力 |
| 请求与完成分开 | G/R → GD/RD | 当前已有 MOVE_START、MOTION_SUMMARY、MOVE_DONE 和主机核对 | 保留更完整的现有协议；接触结果、位置结果、稳定夹持结果分开。单次阈值触发不能授权抬升 |
| 反馈末端位姿 | GitHub FK 发布器 | `planning/approach.py:32` 已通过 TF 获得可配置 robot_frame/tcp_link 位姿 | 复用已有 TF/telemetry 模块，核对真实 TCP 与时间戳；目前没有引入新 FK node 的必要 |

接线边界：旧例子有 `PB7/PB6`、`D0/D1`、`Serial1` 等接口；当前 `board_config.h` 为 GPIO21/22 的 I2C、GPIO16/17 的 UART，地址为实测 ACK 的 0x14。旧 MLX90393 调用使用 Theodore Yapo API，当前使用 Adafruit API；地址、设置枚举及返回状态必须按当前库解释。旧代码不能证明新接线的电平、供电或传感器身份。

## 不能照搬的具体缺陷

| 位置 | 源码发现与影响 | 当前应保持的约束 |
| --- | --- | --- |
| `EE_calibration:49`；PI 草稿 `:139` | zip 的 `const int detail = 0` 缺分号；草稿有未注释的 `↓`。原样源文件有语法缺陷；本次未执行 Arduino 编译 | 不把文件名或邮件描述当作“已运行最终版本”证据 |
| `MagSensorControlDraft:27,97`；`:78` | 初始 `cuvettGripped=false`，没有独立 gripping/armed 状态，上电后的 loop 就走闭合分支；release 后又设 false，下一步继续闭合 | 显式命令触发与上电不自动运动；release 后回到空闲 |
| `EE_calibration:90,174,220` | 标定、grip、release 都有阻塞循环；动作期间不回到串口命令处理；`ACTION_TIMEOUT` 定义后未使用 | 有界 poll、动作超时和可处理的 STOP/心跳。旧 20 ms delay 不能证明完整控制周期 |
| `EE_calibration:174`；旧 SDK `SMS_STS.cpp:169` | ReadLoad 通信失败返回 -1，`abs(-1)=1` 可继续通过负载门槛；传感器读返回状态也未检查 | 先验证整包反馈/SDK 状态与有效样本，失效锁定；不靠负载数值判断通信成功 |
| `basicVelControl:46` | 速度反馈被判为无效时只打印并 return，没有请求停止；之前速度命令可能继续。-1 也不能单独承担有符号反馈的有效性判断 | 独立反馈有效性和本地故障处理 |
| `EE_calibration:333` | XYZ 三次 movingAverage 共用同一数组，混合不同轴；实际返回的 norm 仍来自未滤波差值。定义滤波器不等于接触判断已滤波 | 每轴独立状态或对差值模长单独滤波，测延迟/噪声/误触发，并记录滤波结果的用途 |
| PI 草稿 `:100,109` | 只在未夹住分支更新 lastTime；长时间保持后重新 g 会使用过大的 dt，积分可能迅速到限幅。触阈值后只给零速度，没有持续调节或滑移验证 | 状态切换重置计时/积分；夹持稳定性独立验证 |
| `EE_calibration:90,220` | 通过持续向外运动直到负载触发来找端点；不能将摩擦/堵转与可靠机械端点区分。GRIPPER_OPEN 没有形成运动限位门槛 | 保留本组实测编码器范围与有界运动，不复制 3340 编码器计数或负载触边逻辑 |
| `EE_calibration:293` | `eStop()` 发送零速度、关闭扭矩并无限等待，没有硬件停止回路证据；关闭扭矩可能丢失夹持 | 软件保持与显式释放分开；不称作硬件急停 |
| `Robotics_Systems_library.cpp:27` | `i <= MAX_ID` 初始化长度 MAX_ID 的数组，最后一次越界写 | 不引入这套通用教学库 |
| 同库 `:232,275` | MATLAB 握手没有实际超时退出；文本编码把大于1000的值先按4位处理，1000落入错误分支，大于10000无法到达5位分支 | 保留当前有界、带版本/单位的文本协议 |

ROS 发布器另有三个问题：`ee_publisher.cpp:93` 只检查 position 总数，`:102–103` 按 name 下标读取 position/velocity，缺少数组对应检查，velocity 为空可越界；缺少关节名全集验证可混入旧值；`:123` 使用 now()，没有保留关节测量时间。此外 Tree FK 求解器使用全树关节数组，而代码只按选定 chain 大小/顺序填充，附加活动关节时需要重新验证映射。因此不直接移植。来源：[固定版本源码](https://github.com/balitom/Capstone_code/blob/e870e23d632f910f58638850cd3fd7d1b3b07a66/ee_publisher.cpp#L93)。

## 推荐后续顺序与验收证据

1. **先补齐空载与加载数据（G01/G02/G03/G06）。** 使用现有采集/日志工具，在记录装配、磁体/传感器方向、位置、通电状态和温度的条件下采空载开合，再用独立测力参考采加载/卸载数据。记录 µT、编码器 counts、N、采样数与重复次数，分离拟合/验证数据，报告漂移/迟滞/不确定度。先确定测的是单指力还是总夹持力，不将 raw load 换成 N。
2. **验证接触闭合及停止（G04/G05）。** 在已有 `AtomMotor` 内实现可中断状态机与经过验证的信号门槛；保留位置/负载/电压/温度/心跳/传感器故障 gates。测最坏情况下的采样间隔、停止延迟和额外闭合距离；当前配置约10 Hz采样和100 ms反馈调度不是实测最坏时序。滤波会增加延迟，参数需用试验确定。
3. **再验证稳定夹持（G09）。** 验证接触持续性、保持及滑移，故障时的保持/释放策略必须有物体试验证据。只有独立 grasp verification 通过才允许抬升/运输；GD、Close 完成和负载非零都不充分。
4. **最后扩展力控制与系统任务（G04/G07/G08）。** 已验证的模型和力范围才可接入 `calibration.py`；硬件联合任务还要满足真实 TF/TCP、监督与取消约束。复用已有 gripper capability/controller/task recipe，不增加任务专属节点。

以上是建议，不构成本次新的模式、阈值或驱动选择。待确认事实记入 [ASSUMPTIONS.md](../ASSUMPTIONS.md)，已有验收边界沿用 [GRIPPER_SYSTEM_INTEGRATION.md](GRIPPER_SYSTEM_INTEGRATION.md) 的 G01–G09。

## 本次验证边界

- 完成源代码静态对照、zip/GitHub 版本差异核对，以及本机当前 FTServo 缓存读取 API 检查。未编译/运行旧固件，也未做 ROS 进程或实物测试。
- 当前夹爪包既有 21 项主机测试全部通过，覆盖协议/单位、分段位置、无自动运动、无效传感器、故障锁定、STOP、控制权与串口打开策略；使用假串口，不证明实物停止或力控制。
- 本组此前实机证据见 [GRIPPER_VALIDATION_LOG.md](GRIPPER_VALIDATION_LOG.md)：2026-10-03 `lubricated_load80` 条件下 N=1 次运行，3轮/72段完成，名义2000–2600编码器计数、最大编码器误差3计数、采样 raw load 峰值52。原始 summary 仍在 `tmp/gripper_bringup/sweep_20261003_150022_860815/summary.json`。这是空载位置证据，不是接触夹持/力精度或可靠性结论。

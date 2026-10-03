# ESP32 夹爪电机首次测试

2026-10-02：已实现 STS 位置模式的命令与反馈逻辑；尚未连接独立舵机电源，未验证真实电机运动。当前默认 `ATOM_MOTOR_ENABLED=0`，保留已验证的传感器采样。启用版本可编译，但不能据此认定实际硬件兼容。

## 接线与供电

用户确认原 STM32 D0 的线接 ESP32 RX2/GPIO16，D1 的线接 TX2/GPIO17；驱动板 GND 与 ESP32 共地，驱动板逻辑 5V 接 VIN。传感器 SDA=21、CLK/SCL=22、V=3V3、G=GND，共八根迁移线。VIN 电压尚未测量。

驱动板额外电源端给舵机供电。先核对实际舵机及驱动板型号、额定电压、极性和 UART 电平，再接独立电源；ESP32 USB/VIN 不承担舵机功率。此前的 SMS 接线图不能证明实际舵机就是 SMS 或 STS，也不能证明板上 UART 对 ESP32 3.3V 安全。

2026-10-03 厂商资料补核：[飞特 URT-1 使用说明（2017-10-08，Seeed 托管厂商原文）](https://files.seeedstudio.com/products/Feetech/URT-1%E4%B8%AD%E6%96%87%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E.pdf) 第 1 页明确写“5V 电压取自 USB 供电，否则需外置供 5V 电压”。因此该版本不能按“舵机电源输入后自动降压输出 5V”设计。脱离电脑时，外部稳压 5V 应分别供 ESP32 VIN 和 URT-1 的逻辑 5V，舵机额定电源另供舵机端口，全部共地。UART 信号电平选择开关应按 ESP32 设为 3.3V，这与逻辑供电 5V 是不同设置。实物版本仍需对照。

## 固件配置

官方 [FTServo Arduino SDK](https://github.com/ftservo/FTServo_Arduino) 用于候选 STS3215/URT-1，验证版本 2.0.0，提交 `64922cda46e56b21b8c1d9e830d936a1941645ae`。Arduino IDE 安装该库后，在 `firmware/atom_gripper_esp32/motor_config.h` 改 `ATOM_MOTOR_ENABLED` 为 1，重新上传。默认版本不需要此库。

ID=1、波特率=1000000 只是查询候选值。先用 PING 获取应答、模式、编码器位置、负载、电压与温度；无响应时排查供电/型号/电平/ID/波特率，不自动扫描或广播写入。

在 ARM 前必须填写实测配置：`HARDWARE_CONFIRMED=1`、编码器 MIN/MAX、限速、原始负载上限、电压原始寄存器范围。MIN/MAX 必须在 0–4095 内且不跨回绕点；跨度跨零时此实现不适用。OPEN/CLOSED 用测得的端点；先保守缩小可用范围，避免机械撞限。当前 speed=100、acceleration=10、温度上限=50 是暂定值，需按实际型号确认。负载读数不是牛顿。

`CLOSE` 还需要 `ZERO` 的静止磁场基线及实测 `ATOM_GRIP_DELTA_UT` 阈值。该阈值仅限制磁场变化，不是已校准的夹持力控制。未填写时 CLOSE 被拒绝。

## 操作顺序

关闭 Arduino 串口监视器，IDE 可保持打开。上传启用版本后运行：

```powershell
python tools/gripper/motor_console.py --port COM4
```

控制台每 0.2 秒自动发 KEEPALIVE，连接时不发送运动命令，也不复位 ESP32。不要同时运行采集程序或 ROS 串口桥。

1. 输入 `STATUS`、`PING`，检查正常应答、`mode=0` 和反馈值。此阶段只读。
2. 独立电源断电，确认方向、机械可动范围和配置；重新上传后再上电。支撑夹爪及物体，确保能够直接切断舵机电源。
3. 若反馈显示已有扭矩使能，显式 `DISARM` 后检查机构；DISARM 会释放扭矩，可能掉落物体。`ZERO` 等待约 2 秒的 20 个有效样本；它不检测是否真的静止。
4. `ARM`：仅接受已配置的健康反馈、有效传感器及位置模式；先把目标写成当前位置，再使能扭矩。已有活动目标不会被静默覆盖。
5. 首次用 `JOG 5`，确认方向；再用 `JOG -5` 返回。每条 JOG 限制 ±20 编码器计数且限制在配置范围。确认后再测试 `OPEN`；校准磁阈值后测试 `CLOSE`。
6. `STOP` 请求保持当前位置；`QUIT` 或 Ctrl+C 退出前也请求 STOP。如需释放，显式 `DISARM`。

## 故障行为与边界

主机心跳超过 750 ms、传感器无效/超过 350 ms、反馈异常/超限、运动超过 2 秒都会锁存故障并尝试当前位置保持。保持失败报告外部停止要求。故障后不会自动继续；排查后 DISARM、RESET、重新 ZERO/ARM。

这些时限是代码检查阈值，SDK 和传感器调用会阻塞，尚未测量真实停止延迟。STOP 和故障处理不是硬件急停，不保证断电、扭矩释放或通讯中断时可靠停止；复位也不保证舵机旧目标消失。首次上电不能默认舵机静止。CLOSE 到达端点仅表示 MOVE_DONE，不证明已抓牢。

现有 ROS 桥仅发布磁场，不发送电机命令；本控制台是独立硬件调试入口。ROS 动作接口、实际反馈与故障测试、磁场到牛顿的标定仍待完成。

2026-10-03：为首次反馈测试启用 UART/FTServo（ATOM_MOTOR_ENABLED=1）；HARDWARE_CONFIRMED=0 且行程/负载/电压限制仍未填写，ARM 与运动保持拒绝。官方 SDK 2.0.0 已安装到用户 Arduino libraries/FTServo。首次仅执行 STATUS 和 PING；未验证实际供电及电平前不连接测试，不自动发送任何电机命令。

2026-10-03：电机调试版本默认关闭 V1 连续打印，但保留传感器采样与故障检查。串口命令 STREAM ON / STREAM OFF 可切换输出，不发送舵机指令。采集或使用只读 ROS 桥前，先在串口监视器发送 STREAM ON，然后关闭监视器；复位后需重新启用。纯传感器编译（ATOM_MOTOR_ENABLED=0）仍默认输出。

## 2026-10-03 — First bounded motor motion preparation

User provided successful STS3215 PING: ID1, 1 Mbps, mode0, feedback valid; tight endpoint1917 and open endpoint2688 encoder counts, one observation each; earlier closed1944/1917 variation means endpoint repeatability remains unmeasured. User-reported adapter approximately7.5V; feedback raw voltage76–77, temperature19–21, load0. Actual rated voltage not independently confirmed. Positive encoder change opens.

Provisional inward bounds1937–2668 (20counts margin) selected for first manual test. At open2688 ARM rejects; manually reposition torque-off into range (~2660) before arming. Speed20counts/s, raw load abort20, voltage raw72–82, temperature40 are conservative provisional test gates, not measured safe force or hardware protection. Default JOG_ONLY limits commands to +/-5counts and rejects OPEN/CLOSE. Magnetic close remains uncalibrated. Completion tolerance reduced from5 to1count so a 5count step cannot immediately report done without approaching target. Host heartbeat console required. No physical motion or new upload performed by agent; software stop is best effort, not emergency stop.

### 2026-10-03 — Provisional jog load threshold adjustment

User-operated ARM succeeded after restoring sensor validity. JOG -5 from2317 to2312 triggered LIMIT_ERROR at position2317, load_raw24>20, voltage_raw76 within72–82, temp21<40; flags0,1,0,0 confirm only load threshold exceeded. Motion completion was not established. User disconnected power and requested adjustment. Raise provisional software raw-load abort threshold from20 to50 for next +/-5count test; speed20counts/s, bounds1937–2668, fault latch and all other gates unchanged. 50 is a test setting without force calibration or established safety meaning. Do not infer percentage torque or newtons. No automatic commands/upload or physical retest performed by agent.

### 2026-10-03 — User-authorized +/-100count manual jog

User reports two completed -5count jogs: 2317→2313 (target2312, raw load-20), then2313→2309 (target2308, raw load0), voltage76–77/temp21. User could not visually resolve gripper displacement; no physical motion accuracy claim. User explicitly requests +/-100count jog. Firmware and console now accept nonzero increments within[-100,100], rejecting outside increments and endpoints beyond1937–2668. OPEN/CLOSE remain disabled. Speed20counts/s and raw load abort50 unchanged. Motion timeout increased2→7s because100counts at20counts/s nominally requires5s plus2s margin; real motion duration/stop latency unvalidated. Heartbeat750ms/sensor350ms gates unchanged. C++ state/boundary and Python console boundary tests pass. No upload or physical motion by agent.

## 2026-10-03 — Directional jog debug instrumentation

User transcript: -50 from2310 reached2260; -100 from2260 reached2161(target2160); +100 from2161(target2261) faulted at2161 with raw load-52>absolute50, voltage76/temp21 within bounds. User quit. Root cause of this stop is confirmed absolute-load threshold; physical reason for directional asymmetry remains unknown. Completion load0 for negative moves is not their peak. Official pinned SDK SMS_STS::ReadLoad uses bit10 for direction, consistent with signed readings; no signed-load conversion bug found.

Added MOVE_START, approximately100ms MOTION samples, and MOTION_SUMMARY sampled absolute/signed peak, sample count, timing and encoder start/target/last position. Fault sample is included before stop feedback can overwrite it. Peaks are sampled, not guaranteed instantaneous maxima. Console saves commands and received lines to timestamped JSONL under tmp/gripper_bringup, with UTC arrival timestamps; no automatic movement. Threshold50, speed20, range1937–2668, +/-100 and heartbeat/fault gates unchanged. Native regression injects negative-load overlimit and verifies captured signed peak/fault summary; Python compilation passes. No real port opened or motion performed in this debug turn. QUIT sends best-effort STOP; it does not guarantee torque release—explicit DISARM or external power-off before uploading.

多位置自动往返测试：见 [测试说明](GRIPPER_SWEEP_TEST.md)。默认先预览，--execute 执行3轮2000–2600目标测试，每段最多100计数，首故障中止，结束尝试STOP与DISARM。

### 2026-10-03 — Lubricated-condition test preparation

User reports WD-40 Multi-Use applied to metal slide rail and requests less restrictive load threshold. Previous sweep_20261003_145120_389807 stopped atpos2157/load52>50 during closing, with voltage77/temp24 healthy. Change provisional software absolute-load abort50→80; all position, speed-register20, +/-100,7s timeout, sensor/watchdog and fault latch gates unchanged. 80 is not validated safe force or servo torque setting. User-reported lubrication changes test condition; amount/application/wait time and material compatibility not measured. New runs must be labelled lubricated plus changed threshold; these two changed factors prevent attributing improvement to lubrication alone. No physical rerun by agent. Existing faults require explicitDISARM/RESET or cold boot, never auto-recovery.

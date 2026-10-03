# 多位置往返测试

2026-10-03：`tools/gripper/motor_sweep.py` 是现有夹爪 UART 命令的薄测试入口，不增加 ROS 节点或复制固件控制逻辑。复用已实现的 JOG、状态反馈、心跳和故障门槛。

## 运行

使用已输出 MOVE_START/MOTION/MOTION_SUMMARY 的固件即可，无需重新烧录。先关闭 Arduino 串口监视器和手动 motor_console，夹爪不夹物体，清空运动范围，保持能切断外部舵机电源。USB与舵机电源正常；当前位置需在固件1937–2668内，传感器需有效。QUIT不保证释放扭矩，脚本启动会明确DISARM。

```powershell
cd C:\Users\User\Desktop\学习\研究生\capstone
# 只展示计划，不打开串口或发送命令：
python tools/gripper/motor_sweep.py --cycles 3
# 执行物理运动：
python tools/gripper/motor_sweep.py --port COM4 --cycles 3 --execute
```

每轮依次到2200、2300、2400、2100、2500、2000、2600、2300；目标变化超过100计数时分段，每段<=100。目标端点保持2000–2600，额外避开固件暂定1937–2668限位。每段到位后默认停留0.5秒，检查armed=1、moving=0、fault=0，并拒绝超过3计数的停留漂移。允许--cycles 1..10、--dwell 0.2..5秒；Ctrl+C中止。

开始前检查PING/模式/配置/故障，随后ARM。故障、通讯异常、到位超时、结果不一致或状态漂移均中止，不自动重试或RESET。结束及异常退出都会尝试STOP、DISARM；若释放没有确认，显示外部断电提示。软件停止和释放请求不是硬件急停。原负载阈值50不提高，故障中止也是有效测量结果。

## 结果

自动生成`tmp/gripper_bringup/sweep_<timestamp>/`：

- transcript.jsonl：命令和全部串口数据，UTC主机时间。
- motions.csv：已成功完成的各段方向、起点、目标、到位位置、误差计数、耗时ms、样本数和负载原始峰值。
- summary.json：整体结果、完成段数和扭矩释放确认。故障段保留在原始日志，不当作成功段计数。

PASS只说明本次编码器反馈与流程门槛通过，不证明夹持力、物理位移精度、完整机构限位、重复可靠性或安全合规。约100ms采样的负载峰值可能漏掉瞬态，load_raw不是牛顿。对比开闭负载应使用相近区间的重复段，不能只比较不同位置或到位时的值。

软件验证：5个模拟回归通过，覆盖3轮计划、边界、首故障中止、同批完成/故障不能忽略故障，以及STOP超时仍尝试DISARM。计划预览通过；尚未执行此脚本的物理测试。

### 2026-10-03 — Sweep residual-chasing fix

Physical run sweep_20261003_144358_789365 completed3segments then motion_timeout: after a100count move start2299/target2399, post-dwell encoder settled2398; host requested another2counts to waypoint2400. Feedback remained2398 for70samples over7096ms with sampled load peak24, raw voltage76–77/temp23, no load/electrical limit fault. End transcript confirms DISARM_OK; torque_release_confirmed=true. This is observed small-step non-response, consistent with servo deadband/friction; precise cause unmeasured.

Host waypoint tolerance changed1→3counts to avoid chasing residual2counts, matching existing post-dwell drift gate. Firmware commanded-target tolerance and all fault limits unchanged. Physical run remains FAIL; no completed3cycle claim. Regression checks2398→2400 generates no new command, and error4 still requires movement. Five tests pass. New script requires no firmware upload; existing latched fault must be manually DISARM/RESET with healthy feedback before rerun.

### 2026-10-03 — Firmware/host arrival tolerance alignment

Second physical sweep_20261003_144533_722742 failed after3segments: full command start2300 target2400 stayed2398 through7014ms,70samples, peak36 (voltage76–77,temp23). Unlike previous run, no2count follow-up command caused this failure; firmware1count arrival gate itself timed out. Cleanup confirmed DISARM_OK. Host-only prior fix was incomplete.

Firmware POSITION_TOLERANCE now3 encoder counts, host segment acceptance and waypoint/dwell tolerance all3; actual error remains in CSV. Timeout/load/position/voltage/temperature/watchdog gates unchanged. Native regression verifies error4 does not complete and error2 completes;6 host tests include accepting error2/rejecting4. Firmware upload required before physical rerun. Both physical sweeps remain failures, not repeatability passes; stable residual is observed, precise friction/deadband cause unproven.

### 2026-10-03 — Sweep cached/live feedback race

Physical sweep_20261003_144913_282840 stopped after10 recorded completions due host summary mismatch, not firmware fault. Host cached start2301 and sentJOG100; firmware MOVE_START and summary start2302/target2402, done2400 within3counts, peak44,2092ms. Cleanup DISARM_OK confirmed. Relative JOG is based on fresh firmware feedback, which may change between STATUS and command; strict equality to cached position was an incorrect host assumption.

Use MOVE_START live start/target as transaction reference, still requiring cached-to-live start and expected target discrepancy<=3counts, requested-vs-live delta discrepancy<=3 and target within1937–2668. Summary and completion must match that live target exactly, final encoder error<=3. CSV start now reflects live firmware start. Seven regressions pass, including1count feedback change accepted and4count change rejected. Host-only correction, no upload required. Run remains incomplete, not3cyclePASS.

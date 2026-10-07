# Gripper bring-up validation log

Date: 2026-10-02. Sensor and host checks include physical capture; motor checks below are compilation and synthetic software regressions, not real actuation or safety compliance.

## Software checks

- Six standard-library unit tests passed: protocol version/metadata/nonfinite rejection, µT-to-T conversion, invalid records, fragmented lines, oversized-line recovery, missing samples and sequence/time wrap/restart.
- Synthetic end-to-end capture replay produced two valid samples, one invalid sample, one missing sequence, one wrong-address record and one malformed line, matching the fixture. No physical claim follows from synthetic data.
- Python source compilation passed. ROS runtime is unavailable in current Windows/WSL environment; real rclpy/launch/package build remains pending.
- Arduino toolchain: ESP32 core 3.3.0; MLX90393 2.0.5; BusIO 1.17.4; Unified Sensor 1.1.15. First CLI link failed due to non-ASCII build path; retry uses an ASCII temporary build path.
- Earlier sensor firmware compiled via Arduino CLI: 330559 bytes program storage, 22240 bytes global RAM. Later motor commissioning build results are recorded below. Not uploaded by the agent.

## Hardware evidence

- User screenshots previously confirmed I2C ACK at 0x14 and valid magnetic samples; stationary screenshot contains 15 complete visible samples. See ESP32_GRIPPER_BRINGUP.md for ranges and conditions. These are not a calibrated force measurement.
- User confirmed sensor wiring, serial wiring GPIO16/17 and VIN to interface-board 5V. Physical voltage, interface current, UART level compatibility and servo-power source remain unmeasured/unconfirmed.
- Host capture attempt 01, requested duration 30s, recorded 228 malformed textual lines and zero valid samples. Evidence: `tmp/gripper_bringup/stationary_20261002_01/`. Not a successful stationary test.
- After deasserting DTR/RTS before opening COM4, attempt 02 recorded 100 well-formed records over approximately 10.05s, all valid=0, no malformed or wrong-address records. Evidence: `tmp/gripper_bringup/stationary_20261002_02/`. Host parsing works; sensor data did not recover in that run. Current firmware latches read failure until EN reset. Reset-and-recapture requested; root cause is not established.

## Remaining commissioning

### Serial startup fix validation

Existing attempt 06 raw evidence was re-examined: all non-protocol text precedes the first complete V1 sample; there are no non-protocol lines thereafter. A no-reset baseline (attempt 07) received 80 valid samples over 8.05s with zero malformed records. This localizes the observed repeated fragments to startup/reset handling rather than steady sensor telemetry; the exact Windows/CP2102 mechanism producing repeated queue contents is not established.

Fix: shared serial opener explicitly disables flow control, deasserts DTR/RTS, purges the previous session queue, and for requested reset waits 0.3s after releasing EN before purging the reset-transient queue. Capture preserves received startup lines separately, waits for a matching V1 record before timing acquisition, and still flags corruption occurring after synchronization. ROS uses the same normal-opening policy without automatic reset.

Hardware regression on COM4, 2026-10-02:

| Run | Conditions | Effective acquisition | Valid / invalid | Malformed / gaps / duplicate sequences | Device rate |
|---|---|---|---|---|---|
| 08 | Explicit EN/RTS reset, user kept sensor wired | 10.02s | 102 / 0 | 0 / 0 / 0 | 9.99901Hz |
| 09 | Close/reopen without reset | 30.10s | 303 / 0 | 0 / 0 / 0 | 10.0Hz |

Both runs also had zero startup lines received after queue purge, zero wrong-address/oversized records and zero trailing partial bytes. Evidence is retained under `tmp/gripper_bringup/debug_20261002_08/` and `debug_20261002_09/`. Nine software unit tests passed, including reset/reopen policy, failed-open cleanup and no serial transmission. This validates the tested sensor transport paths only; ROS runtime, long-duration reliability, board voltages, force calibration and motor control remain unverified.

### Recovery and capture 06

User reported a disconnected wire and reseated it. Attempts 04/05 had no bytes; an RTS pulse with DTR deasserted then produced startup logs, ACK 0x14, sensor_ready and valid samples. Added an explicit `--reset` capture option for current sensor-only firmware (not a future motor recovery policy).

Attempt 06: approximately 30.02s host acquisition, 295 valid samples, zero invalid samples, no parsed sequence gaps, device-timestamp rate 9.99966Hz. XYZ means µT: -548.54, 245.64, 5311.46; sample standard deviations µT: 4.82, 1.61, 16.36. Fixture labelled stationary based on user preparation, but physical pose/temperature/voltage and force were not measured; standard deviations include possible drift and movement, not established sensor noise/uncertainty.

Important transport limitation: 2370 non-protocol records were rejected, including 2284 repeated partial text lines plus boot/reset fragments. Valid samples exist, but this is not a clean serial-stream acceptance result; USB reset/driver/buffering cause remains unresolved. Evidence: `tmp/gripper_bringup/stationary_20261002_06/raw.bin`, `samples.csv`, `summary.json`. No motor commands were sent.

User re-upload screenshot confirms hash verification of a 330912-byte image (not established as identical to CLI build). Host attempt 03 opened COM4 for 30.04s but received zero records/bytes; evidence retained under `tmp/gripper_bringup/stationary_20261002_03/`. Requested manual EN reset while capturing startup logs; no successful stationary capture claimed.

Real stationary/raw response capture and sensor fault recovery; ROS runtime and hardware topic/diagnostic tests; actual interface-board identification/electrical compatibility; independently powered servo read-only communication; bounded motor control and fault handling; independent force calibration; measured sensor TF and covariance.

## Optional motor commissioning software checks

Enabled STS build passed Arduino CLI, ESP32 core 3.3.0 and official FTServo 2.0.0 at pinned commit 64922cda46e56b21b8c1d9e830d936a1941645ae: 364283 bytes flash, 22504 bytes global RAM. Final default motor-disabled build passed: 331787 bytes flash, 22376 bytes global RAM. Both configurations include the sensor-baseline/feedback-gate correction.

Native C++ policy assertions passed for configured limits, bounded JOG and unsigned clock wrap. Native state-machine test using a mocked UART/servo passed: no servo writes on boot or disabled movement; no ARM without sensor; reject oversized JOG and uncalibrated CLOSE; heartbeat timeout and fault latch; explicit DISARM/RESET; invalid samples cancel ZERO; magnetic delta requests hold; failed feedback/hold reports fault. These mocks do not test the real SDK transport, power, mechanics or stopping latency. Python console whitelist passed 19 command cases; source compilation passed; nine existing host tests passed. No serial port opened, no real motor packets sent, no firmware uploaded during these checks.

Manual testing instructions and unmeasured configuration are in GRIPPER_MOTOR_COMMISSIONING.md. ROS actuator integration remains pending; sensor bridge now reports motor state unknown instead of assuming disabled.

## 2026-10-03 — First bounded motor motion preparation

User provided successful STS3215 PING: ID1, 1 Mbps, mode0, feedback valid; tight endpoint1917 and open endpoint2688 encoder counts, one observation each; earlier closed1944/1917 variation means endpoint repeatability remains unmeasured. User-reported adapter approximately7.5V; feedback raw voltage76–77, temperature19–21, load0. Actual rated voltage not independently confirmed. Positive encoder change opens.

Provisional inward bounds1937–2668 (20counts margin) selected for first manual test. At open2688 ARM rejects; manually reposition torque-off into range (~2660) before arming. Speed20counts/s, raw load abort20, voltage raw72–82, temperature40 are conservative provisional test gates, not measured safe force or hardware protection. Default JOG_ONLY limits commands to +/-5counts and rejects OPEN/CLOSE. Magnetic close remains uncalibrated. Completion tolerance reduced from5 to1count so a 5count step cannot immediately report done without approaching target. Host heartbeat console required. No physical motion or new upload performed by agent; software stop is best effort, not emergency stop.

## 2026-10-03 — First user-operated jog and unresolved feedback fault

User console reports ARM_OK; first JOG -5 returned MOVE_DONE; second JOG -5 caused servo_feedback_or_limit, followed by best-effort hold request and a latched fault. Physical displacement/direction was not reported; no force or motion accuracy result claimed. Existing message combined transport and limit failures, and stop handling could overwrite trigger values with newer feedback.

Added FEEDBACK_ERROR with SDK result/error/servo status; LIMIT_ERROR with values, configured bounds and per-limit flags; FAULT_TRIGGER and state snapshot before hold reads feedback again. MOVE_DONE now includes actual/target encoder values and telemetry. Existing raw load limit20 and all other motion gates remain unchanged. Cause (communication, load, voltage, temperature or position) remains unresolved; do not increase thresholds to bypass it. Native regressions cover feedback failure and injected load-only limit classification. Await physical diagnostic data after explicit DISARM, new firmware and guarded retry.

### 2026-10-03 — Provisional jog load threshold adjustment

User-operated ARM succeeded after restoring sensor validity. JOG -5 from2317 to2312 triggered LIMIT_ERROR at position2317, load_raw24>20, voltage_raw76 within72–82, temp21<40; flags0,1,0,0 confirm only load threshold exceeded. Motion completion was not established. User disconnected power and requested adjustment. Raise provisional software raw-load abort threshold from20 to50 for next +/-5count test; speed20counts/s, bounds1937–2668, fault latch and all other gates unchanged. 50 is a test setting without force calibration or established safety meaning. Do not infer percentage torque or newtons. No automatic commands/upload or physical retest performed by agent.

### 2026-10-03 — User-authorized +/-100count manual jog

User reports two completed -5count jogs: 2317→2313 (target2312, raw load-20), then2313→2309 (target2308, raw load0), voltage76–77/temp21. User could not visually resolve gripper displacement; no physical motion accuracy claim. User explicitly requests +/-100count jog. Firmware and console now accept nonzero increments within[-100,100], rejecting outside increments and endpoints beyond1937–2668. OPEN/CLOSE remain disabled. Speed20counts/s and raw load abort50 unchanged. Motion timeout increased2→7s because100counts at20counts/s nominally requires5s plus2s margin; real motion duration/stop latency unvalidated. Heartbeat750ms/sensor350ms gates unchanged. C++ state/boundary and Python console boundary tests pass. No upload or physical motion by agent.

## 2026-10-03 — Directional jog debug instrumentation

User transcript: -50 from2310 reached2260; -100 from2260 reached2161(target2160); +100 from2161(target2261) faulted at2161 with raw load-52>absolute50, voltage76/temp21 within bounds. User quit. Root cause of this stop is confirmed absolute-load threshold; physical reason for directional asymmetry remains unknown. Completion load0 for negative moves is not their peak. Official pinned SDK SMS_STS::ReadLoad uses bit10 for direction, consistent with signed readings; no signed-load conversion bug found.

Added MOVE_START, approximately100ms MOTION samples, and MOTION_SUMMARY sampled absolute/signed peak, sample count, timing and encoder start/target/last position. Fault sample is included before stop feedback can overwrite it. Peaks are sampled, not guaranteed instantaneous maxima. Console saves commands and received lines to timestamped JSONL under tmp/gripper_bringup, with UTC arrival timestamps; no automatic movement. Threshold50, speed20, range1937–2668, +/-100 and heartbeat/fault gates unchanged. Native regression injects negative-load overlimit and verifies captured signed peak/fault summary; Python compilation passes. No real port opened or motion performed in this debug turn. QUIT sends best-effort STOP; it does not guarantee torque release—explicit DISARM or external power-off before uploading.

## 2026-10-03 — User transcript confirms four bounded jog completions

Source: user pasted attachment 4c83e827-d91a-4be2-a0b9-44c6978ce712/已粘贴的文本.txt; newest session references tmp/gripper_bringup/motor_20261003_143750_128786.jsonl. Older fault at-52 precedes new session, not a failure of these four motions. New session:

| Encoder start→target | Last position | Duration ms | Samples | Sampled absolute load peak | Signed peak |
|---|---:|---:|---:|---:|---:|
|2161→2111|2112|1020|12|28|28|
|2110→2010|2010|2111|22|48|48|
|2010→2110|2109|2105|22|44|-44|
|2109→2209|2208|2030|22|36|-36|

All four report done, endpoint error0–1 encoder counts; no new-session fault appears in provided excerpt. N=1 per command, not repeatability/reliability verification. Close/open over approximately2010–2110 have sampled peaks48 and44 respectively, so this trace does not support generally higher opening load. Previous opening-start52 remains evidence of variability; software threshold50 has only2 raw units margin over observed closure48. Approx100ms sampling can miss instantaneous peaks; physical displacement/force/current not independently measured. Raw voltage76–77, temperature19–21 during these records. No torque release appears at excerpt end: user should DISARM explicitly.

Important configuration discrepancy: speed register is set20, but measured100count movements take approximately2.0–2.1s, around47–49 encoder counts/s. Earlier comments interpreted speed20 as20counts/s; that interpretation is not established by this physical trace. SDK/model speed register units must be checked before claiming commanded physical velocity. Existing7s timeout remains conservative provisional bound, not measured stop latency.

2026-10-03：新增motor_sweep薄测试脚本，复用固件状态机，不增加节点。5个模拟回归和无串口计划预览通过；真实重复运动尚未运行。执行说明及证据边界见GRIPPER_SWEEP_TEST.md。速度注释修正为SDK寄存器值，实测100计数约2.1秒，未确立单位。

### 2026-10-03 — Sweep residual-chasing fix

Physical run sweep_20261003_144358_789365 completed3segments then motion_timeout: after a100count move start2299/target2399, post-dwell encoder settled2398; host requested another2counts to waypoint2400. Feedback remained2398 for70samples over7096ms with sampled load peak24, raw voltage76–77/temp23, no load/electrical limit fault. End transcript confirms DISARM_OK; torque_release_confirmed=true. This is observed small-step non-response, consistent with servo deadband/friction; precise cause unmeasured.

Host waypoint tolerance changed1→3counts to avoid chasing residual2counts, matching existing post-dwell drift gate. Firmware commanded-target tolerance and all fault limits unchanged. Physical run remains FAIL; no completed3cycle claim. Regression checks2398→2400 generates no new command, and error4 still requires movement. Five tests pass. New script requires no firmware upload; existing latched fault must be manually DISARM/RESET with healthy feedback before rerun.

### 2026-10-03 — Firmware/host arrival tolerance alignment

Second physical sweep_20261003_144533_722742 failed after3segments: full command start2300 target2400 stayed2398 through7014ms,70samples, peak36 (voltage76–77,temp23). Unlike previous run, no2count follow-up command caused this failure; firmware1count arrival gate itself timed out. Cleanup confirmed DISARM_OK. Host-only prior fix was incomplete.

Firmware POSITION_TOLERANCE now3 encoder counts, host segment acceptance and waypoint/dwell tolerance all3; actual error remains in CSV. Timeout/load/position/voltage/temperature/watchdog gates unchanged. Native regression verifies error4 does not complete and error2 completes;6 host tests include accepting error2/rejecting4. Firmware upload required before physical rerun. Both physical sweeps remain failures, not repeatability passes; stable residual is observed, precise friction/deadband cause unproven.

### 2026-10-03 — Sweep cached/live feedback race

Physical sweep_20261003_144913_282840 stopped after10 recorded completions due host summary mismatch, not firmware fault. Host cached start2301 and sentJOG100; firmware MOVE_START and summary start2302/target2402, done2400 within3counts, peak44,2092ms. Cleanup DISARM_OK confirmed. Relative JOG is based on fresh firmware feedback, which may change between STATUS and command; strict equality to cached position was an incorrect host assumption.

Use MOVE_START live start/target as transaction reference, still requiring cached-to-live start and expected target discrepancy<=3counts, requested-vs-live delta discrepancy<=3 and target within1937–2668. Summary and completion must match that live target exactly, final encoder error<=3. CSV start now reflects live firmware start. Seven regressions pass, including1count feedback change accepted and4count change rejected. Host-only correction, no upload required. Run remains incomplete, not3cyclePASS.

### 2026-10-03 — Lubricated-condition test preparation

User reports WD-40 Multi-Use applied to metal slide rail and requests less restrictive load threshold. Previous sweep_20261003_145120_389807 stopped atpos2157/load52>50 during closing, with voltage77/temp24 healthy. Change provisional software absolute-load abort50→80; all position, speed-register20, +/-100,7s timeout, sensor/watchdog and fault latch gates unchanged. 80 is not validated safe force or servo torque setting. User-reported lubrication changes test condition; amount/application/wait time and material compatibility not measured. New runs must be labelled lubricated plus changed threshold; these two changed factors prevent attributing improvement to lubrication alone. No physical rerun by agent. Existing faults require explicitDISARM/RESET or cold boot, never auto-recovery.

## 2026-10-03 — Lubricated three-cycle sweep PASS

Evidence: tmp/gripper_bringup/sweep_20261003_150022_860815/. Condition label lubricated_load80; user reported WD-40 Multi-Use on metal slide rail, provisional firmware load threshold80. N=1 run with3cycles/72completed segments across nominal waypoints2000–2600; all segment verifications passed, no auto fault recovery, torque release confirmed at cleanup. Quantitative summary: {"summary": {"passed": true, "failure": null, "torque_release_confirmed": true, "condition": "lubricated_load80", "requested_cycles": 3, "completed_segments": 72, "waypoints": [2200, 2300, 2400, 2100, 2500, 2000, 2600, 2300], "sampled_peak_abs_load": 52, "notes": "Encoder-only verification. Sampled load is not calibrated force. No automatic fault reset."}, "max_abs_error_counts": 3, "durations_ms": [1501, 2132], "directions": {"open": {"segments": 36, "max_sampled_load": 44, "mean_segment_peak": 41.78}, "close": {"segments": 36, "max_sampled_load": 52, "mean_segment_peak": 41.78}}}. Peak values are approximately100ms-sampled raw servo loads, not force; encoder error is not measured physical displacement uncertainty. No matched unlubricated run at threshold80: lubricant effect cannot be isolated. Not full mechanical stroke/contact or calibrated force validation.

## 2026-10-07 — Calibration preparation and tool-description checks

Main at cf894b2 was already current; created test/gripper-force-calibration-20261007.
No hardware port opened, firmware uploaded, motor commanded, or physical force
data collected. Prepared fixed-object holding and independent force calibration
procedure in GRIPPER_FORCE_CALIBRATION.md. Existing force model stays uncalibrated.
Print archive member hashes match and three meshes are watertight. Combined UF850
URDF, standalone v2 tool URDF and combined SRDF expanded using D-007's pinned
vendor commit. Four offline geometry/semantics tests passed: six complete visual
vertex envelopes, prefixed/unprefixed tree and semantic references, narrow arm/tool
collision exclusions and CAD mounting values. No ROS/urdfdom/MoveIt/FCL runtime
or physical acceptance claimed. Details in GRIPPER_MOUNT_V2_INTEGRATION.md.

## 2026-10-07 — New Mac connection and user-operated position checks

Mac detected CP2102 USB UART, serial0001, at /dev/cu.usbserial-0001. User
launched motor_console with the Python environment containing pyserial3.5.
Reported transcript path: tmp/gripper_bringup/motor_20261007_144300_661483.jsonl.
User terminal output confirms sensor ACK0x14, sensor_ready, DISARM_OK and ZERO_OK
(magnetic baseline only). Initial ARM rejected position2682counts above2668;
load0raw, voltage76raw and temperature22raw did not exceed configured gates.
Subsequent PING confirmed mode0, valid feedback, position2312counts and no fault;
ARM then succeeded. Exact manual repositioning action was not reported.

One user-operated sequence, N=3 commanded moves, nominal targets2317/2312/2413counts:

| Command | Start / target / completion position (counts) | Completion elapsed (ms) | Sampled absolute peak load (raw) | Samples |
|---|---|---|---|---|
| JOG +5 | 2312 / 2317 / 2314 | 118 | 32 | 3 |
| JOG -5 | 2317 / 2312 / 2314 | 117 | 20 | 3 |
| JOG +100 | 2313 / 2413 / 2412 | 2094 | 44 | 22 |

All returned MOVE_DONE within the existing3count encoder tolerance; this is
threshold completion, not proof the servo had finished settling. Later start2317
after first completion2314 confirms feedback subsequently progressed. Motion
samples show voltage76–77raw, temperature23raw, no fault output. Final STOP
acknowledged position_hold_requested_not_estop; actual physical holding/stop
latency is not measured. Object/contact condition and visible motion direction
were not explicitly confirmed; physical displacement, force and grasp success
remain unverified. Sampled peaks are not guaranteed instantaneous maxima.
No agent serial commands, firmware upload, wiring or gate changes in this check.

### 2026-10-07 — Physical unloaded stationary magnetic baseline

User confirms no object and enables STREAM ON in the existing console. Agent
passively reads new JSONL records; no second serial owner, reset, ZERO or motor
commands. Three contiguous30s windows produced301/299/300valid samples, total900,
zero invalid/gaps/duplicates/resets/malformedV1; device rate10.0001Hz. Combined
XYZ meanµT[-280.216,-205.274,7842.070], sample SDµT[0.410,0.473,1.291]; maximum
group-mean spreadsµT[0.102,0.249,1.141]. These are observed baseline/waveform
statistics, not established sensor uncertainty, force calibration or repeatability
across remounts. Pose/temperature/current and force not independently measured.
Saved unloaded_baseline.json for offline subtraction only; firmware baseline
and force-control gates unchanged. Full conditions/evidence:
[stationary baseline](GRIPPER_STATIONARY_BASELINE_20261007.md).

### Second pose, 2026-10-07

User changes arm pose and estimates nearest metal distance30cm. Three30s windows
yield900valid samples, no invalid/gaps/duplicates/resets/malformedV1,10.0000Hz.
Mean XYZµT[-307.112,-200.889,7875.857], sample SDµT[0.484,0.442,3.061].
Difference from first captureµT[-26.896,+4.385,+33.787]; within second capture,
group3-minus-group1 Z=-6.471µT. Thus the new mean is retained as an observation,
not adopted as a fixed zero. Pose/environment/time effects are not isolated;
exact pose/jaw opening/temperature/current not measured. No ZERO or gripper
movement commands between captures; no agent hardware commands. Raw evidence:
tmp/gripper_force/stationary_pose2_20261007/. Force calibration remains pending.

### Third pose, 2026-10-07

Third user-selected pose, three30s windows,901/901valid, no invalid/gaps/duplicates/
resets/malformedV1,10.0000Hz. Mean XYZµT[-342.646,-209.126,7774.137], sample
SDµT[0.457,0.436,1.390]; group3-minus-group1 Z=-1.746µT. Third-minus-first mean
µT[-62.430,-3.852,-67.934]. Exact pose/metal distance/jaw state/temperature/current
not measured. Data retained in tmp/gripper_force/stationary_pose3_20261007/.
User requests per-closure unloaded baseline and explicitly clarifies the difference
method (current magnetic field minus baseline), not interpolation; document as
planned calibration method, pending reference-force points, unloaded closure,
monotonicity/hysteresis and cross-pose validation. No deployed force model or
hardware commands from agent. See GRIPPER_STATIONARY_BASELINE_20261007.md.

### Agent direct connection, 2026-10-07

After user exits console and authorizes direct acquisition, existing read-only
GripperController opens /dev/cu.usbserial-0001 (USB access approval required).
Startup text occurs despite no reset request. Firmware reports disarmed/not
moving/no fault; no ARM/MOVE/JOG/ZERO/RESET/DISARM commands. Three30s windows,
297/296/295valid samples,888total, no invalid/gaps/duplicates/window resets/V1
parse errors,9.8712Hz. Combined meanXYZµT[-307.641,-210.917,7766.758], sample
SDµT[1.746,0.918,1.962]. Early transient samples preserved; group3-minus-group1
Z=-3.538µT. No force calibration or empty-closure test. Serial closed afterwards.
Full conditions and evidence: [direct stationary measurement](GRIPPER_DIRECT_STATIONARY_20261007.md).

### User-authorized empty closure, 2026-10-07

Existing controller executes explicit empty-gripper DISARM/ARM, nominal targets
2410→2390→2370→2350→2410counts,2s settle and10s measurement each. One sequence,
five100sample platforms,500valid total, no invalid/per-platform gaps/duplicates/
resets; no fault. Actual platform encoder positions2410/2390/2371/2351/2409.
Closed60counts nominal: mean ΔXYZµT[-2.019,-0.435,-6.077]; return ΔXYZµT
[+0.078,-0.442,-3.802]. Empty-gripper position/time effects not isolated; no
force conversion or compensation coefficients inferred. STOP and DISARM confirmed,
serial closed. No ZERO/RESET/firmware/gate changes. Full conditions:
[empty closure](GRIPPER_EMPTY_CLOSURE_20261007.md).

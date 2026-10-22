# ESP32 夹爪迁移与今日传感器测试

日期：2026-10-02。状态：用户已烧录并得到有效磁场截图；电脑采集工具与 ROS 桥接代码已实现，ROS 运行未验证。电机控制未实现。

## 当前实物接线记录（用户确认，2026-10-02）

用户确认：除原接口板 5V 线外，其余线已按本次迁移对应关系连接。以下是用户报告的接线状态，不是通断/电压测量结果。

| 用途/线端 | 原 STM32 NUCLEO-H755ZI-Q | 当前 ESP32 DEVKIT V1 | 验证状态 |
|---|---|---|---|
| 传感器 CLK | D15 / PB8 / SCL | D22 / GPIO22 | 已有 I2C 响应和有效磁场记录 |
| 传感器 SDA | D14 / PB9 / SDA | D21 / GPIO21 | 同上 |
| 传感器 V | 3V3 | 3V3 | 用户确认连接；实际电压未测 |
| 传感器 G | GND | GND | 用户确认连接 |
| 原 D0 所接的接口板串口线 | D0 / PB7 / RX | RX2 / GPIO16 | 已接；接口板端标记、电平及通信未验证 |
| 原 D1 所接的接口板串口线 | D1 / PB6 / TX | TX2 / GPIO17 | 已接；接口板端标记、电平及通信未验证 |
| 接口板 GND | GND | ESP32 GND / 共地 | 用户称除 5V 外其余已连接；未测通断 |
| 接口板逻辑 5V | 5V | **VIN（用户后续确认已连接）** | USB 经二极管供电路径仅有原理图证据；接口板电压/电流兼容性未验证 |

- ESP32 USB 串口：COM4，Silicon Labs CP210x；用户提供上传日志显示写入、哈希校验完成。
- 实测总线地址：0x14（十进制 20），已写入 board_config.h。用户后续截图显示连续 valid=1 的 XYZ 数据。
- 用户确认先前大幅磁场变化期间在按压/移动。静止截图中完整可见 15 个有效样本，X 范围 -48.15 至 -46.80 µT，Y -37.20 至 -36.45 µT，Z 67.03 至 69.21 µT；仅为截图样本范围，无原始日志、力参考或测量不确定度，不构成力标定。
- 当前固件只采集磁传感器，**未启用 GPIO16/17 电机 UART，未发送舵机命令**。接线完成不能作为电机控制成功的证据；ROS 硬件桥接也尚未运行验证。
- 原报告将 D0/D1 的 TX/RX 标注颠倒；ST 官方表为 D0=RX、D1=TX。飞特 URT-1 官方示例为 TX-TX、RX-RX，不能按通用交叉规则猜测接口板丝印。当前迁移按原线去向保留功能。
- 用户提供的参考图是 SMS 系列，不是已确认的实物接口板照片；图上舵机 9-14V / 9-25V 不能用于确定 STS3215 供电。实际接口板版本、舵机额定电源、UART 逻辑电平仍待核对。

后续固件更新：已增加 GPIO16/17 的 UART2 配置与可选被动接收字节计数，默认 `ATOM_SERVO_UART_ENABLED=0`，115200 仅为候选诊断速率，不是已确认舵机波特率。只有确认板端电平兼容后才设为 1；无发送、无 ping、无运动控制。舵机可能仅在收到请求后回复，因此 rx_bytes=0 不能判定故障。VIN 不受软件控制，日志 power_unverified 不代表实际电源测量。此更新尚未编译/烧录验证；独立舵机供电、ID/波特率及实物型号待用户补充。


更新：用户已在 COM4（CP210x）编译烧录并校验成功。串口截图显示初始化失败、无 ACK 输出、valid=0，并出现重启回溯；尚无有效磁场样本。检查本机 Adafruit 驱动发现重复 begin_I2C 使用已释放指针，固件已改为先扫描、每次启动只初始化一次。此修正版尚未重新编译/烧录；驱动初始化或读取失败后须检查硬件并按 EN 重试，不能声称自动恢复已验证。

## 证据与原系统

原报告 `previous report/Capstone_Robotic_Hand_Lab_Experiment.pdf` 印刷页 10：STS3215 通过 URT-1 控制。页 14 图 9：传感器 V/G/CLK/SDA 分别连接 STM32 3.3V/GND/SCL/SDA；STM32 与接口板使用 TX/RX，与 Linux 主机通过 USB 串口通信。图中的接口板 5V 标签不能证明电机的额定供电。报告页 10、14 的扭矩供电条件还有 6V/7.4V 差异，需要实物标签和对应规格确认。

报告页 14-15 描述磁场阈值闭合停止、负载碰壳校准；没有交付可复现的固件、串口协议、完整引脚编号或磁场到力的标定。旧值 500 不可直接沿用。磁场是磁体与硅胶形变的观测量，不是已标定的牛顿数。碰壳校准不能直接复制到新固件。

用户照片：传感器载板可见 V/G/SDA/CLK；用户称 MLX90393 系列，照片不足以确定完整订货代码。两张控制板照片确认 ESP32 DEVKIT V1，经典 ESP32 与 CP2102。夹爪中实际传感器数量待确认。

官方资料：[Melexis MLX90393 数据表](https://media.melexis.com/-/media/files/documents/datasheets/mlx90393-datasheet-melexis.pdf)给出芯片供电 2.2-3.6V、I2C/SPI 和多个地址选项。[Adafruit 驱动](https://github.com/adafruit/Adafruit_MLX90393_Library)提供 I2C 初始化和以 µT 返回的 XYZ 数据。载板上是否有上拉、地址跳线和稳压需检查，不将其他品牌模块的 VIN 接法套用到本板。

## 今日接线：一次只接一个传感器

最新台架观察：用户后续截图中两次扫描均显示 `i2c_ack=0x14`、`devices=1`，检查时 SDA/SCL 为高电平。已将实际固件配置地址更新为 0x14（十进制 20）。ACK 不足以确认完整芯片型号或有效磁场；需重新烧录并检查初始化和读数。ROS 启动时使用 `-p sensor_address:=20`。

先拔 USB，断开原 STM32 与传感器连接，电机与 URT-1 暂不连接。用板上丝印确认引脚，不按照片左右计数。

| 传感器 | ESP32 DEVKIT V1 |
|---|---|
| V | 3V3 |
| G | GND |
| CLK | D22 / GPIO22 |
| SDA | D21 / GPIO21 |

USB 给开发板供电；从 3V3 输出给传感器供电。不得把传感器 V、SDA、CLK 接到 VIN/5V。检查载板现有上拉；若没有，可给 SDA/SCL 各接一个约 4.7kΩ 到 3.3V，之后测实际总上拉和总线波形。地址相同的两个传感器不能直接并接并期待独立读取；先分别测试，再确认地址跳线或选择多路复用方案。

## 烧录与读取

1. Arduino IDE 安装 Espressif 的 ESP32 板卡包，板型选择经典 ESP32 Dev Module；Library Manager 安装 Adafruit MLX90393 及其依赖 Adafruit BusIO、Adafruit Unified Sensor。记录实际版本。
2. 打开 `firmware/atom_gripper_esp32/atom_gripper_esp32.ino`。`board_config.h` 已设 GPIO21/22；当前实测地址为 0x14。
3. 确认端口对应 CP2102，烧录。串口监视器 115200 baud。若连接失败，核对数据线、驱动和端口；必要时按 BOOT 配合下载。
4. 启动输出 `# i2c_ack=0xNN`。ACK 只证明总线响应，不证明型号。若地址不是配置的 0x14，修改配置再烧录；没有 ACK 就先查电压、共地、线序、上拉。
5. 成功时输出 `# sensor_ready` 和 `V1,seq,device_ms,address,valid,Bx_uT,By_uT,Bz_uT`。valid=0 是失败记录，不可作为零磁场样本。固件目标周期 100ms，实际频率和串口抖动需测量。

## ROS 接入

沿用 D-007 的 Jazzy 开发环境。ESP32 保持独立采样，ROS 节点在主机上运行，通过 USB 串口桥接。新增独立节点的原因是物理串口生命周期、单位转换和掉线诊断边界；现有 gripper description 仅描述几何，仿真 G1 控制器也不能读取这块硬件。第一版是单传感器、只读接口。

在 Ubuntu ROS 环境安装依赖并构建：

```bash
cd ros2_ws
rosdep install --from-paths src/atom_gripper_hardware --ignore-src -r -y
colcon build --packages-select atom_gripper_hardware
source install/setup.bash
ros2 run atom_gripper_hardware sensor_bridge --ros-args \
  -p port:=/dev/serial/by-id/实际设备路径 -p sensor_address:=20
ros2 topic echo /atom/gripper/magnetic_field
ros2 topic echo /diagnostics
```

Docker 需将实际 USB 设备映射进去并具备串口权限；先关闭 Arduino 串口监视器。ROS MagneticField 单位为 T，桥接将 µT 乘 1e-6。时间戳是主机收到样本的 ROS 时间，未与设备时钟同步；frame_id 为暂定传感器坐标系，尚未提供测量得到的 TF。协方差全零表示未知。超过 1s 无有效样本、串口掉线或传感器失败会报错，连接重试周期 2s；不发布失败磁场。没有夹爪开闭服务、GripperCommand action 或真实 JointState。

## 台架测试记录

电脑数据采集入口和命令见 `tools/gripper/README.md`。使用 `capture.py` 保存原始字节、CSV 与统计；关闭 Arduino 串口监视器后独占 COM4。软件测试已覆盖协议单位/异常、串口分包/超长恢复、失败样本排除、序列丢样/重启/回绕。合成回放验证发现 1 条失败样本、1 个序列缺口、1 条错误地址和 1 条坏记录；这不是硬件测量。

记录传感器编号、板型、实际电压 V、地址、GPIO、固件/库版本、磁体位置与方向、环境温度、采样数 N、实际 Hz、丢帧和失败数。保存串口原始输出至 `tmp/gripper_bringup/`；结论放 docs。所有以下数量是计划，不是结果。

- 空载静止 30s，目标约 300 个有效样本：各轴均值与标准差 µT、实际 N、频率。
- 固定方向轻压硅胶、松开，10 次：各轴变化 µT、释放后的基线偏移和离散程度；不测试玻璃破坏极限。
- 断电后拔传感器，再通电：确认 valid=0、ROS 报错；断电恢复接线后检查自动恢复。避免带电插拔作为首轮测试。
- 拔 USB：确认诊断变为缺失/过期；重新连接后检查恢复。重新连接可能重启 ESP32。
- 检查靠近磁体时读数是否饱和；改变增益/分辨率后重新记录配置。无独立力参考时只报告磁场响应。

## 电机阶段的前置条件

### 用户提供的 ESP32 板卡资料核对（2026-10-02）

原始文件位于用户 Downloads，未修改。视觉核对两份原理图第 1 页：

- `ESP32 原理图.pdf` 是两侧各 15 针布局，与用户实物照片的引脚序列一致。供电图为 USB VCCUSB 经 D1 SS14 肖特基二极管到 VIN，VIN 再进入 NCP1117 生成 3.3V。因此若实物符合此图，USB 供电时 VIN 有 USB 电压减去二极管压降，不是精密稳压 5V 输出。能否给 URT-1 逻辑供电仍需确认其允许电压/电流和实际板版本；不用于供舵机功率。
- `ESP32 原理图 V2.pdf` 排针不同，不能按图中位置对照 30 针实物。其稳压器输入直接连 VUSB，VIN 位于 USB 经 SS14 后的另一支路；两图不完全等价。
- 两图 CP2102 连接 GPIO1/3 的 UART0，用于 USB 烧录与日志；GPIO16/17 对应 RX2/TX2。ESP32 为 3.3V 逻辑，不据此证明 URT-1 接口电平兼容。
- `ESP-WROOM-32 技术规格书.pdf` 与技术参考手册描述模块/芯片，不能代替具体开发板 USB/VIN 供电图。PDF 中文字体提取部分失败，原理图已视觉检查。


电机命令、限位、反馈、心跳超时和故障锁存已实现，默认关闭；实物兼容性和独立供电测试未完成。具体配置、上电检查及手动小步测试见 [电机首次测试](GRIPPER_MOTOR_COMMISSIONING.md)。当前 ROS 桥仍只读，软件停止不是硬件急停。

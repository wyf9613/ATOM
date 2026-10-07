# 夹爪连接与固定物体测试：当前操作流程

更新：2026-10-07。以当前 board_config.h、motor_config.h、固件和共享
controller 为准。旧 ESP32_GRIPPER_BRINGUP、GRIPPER_MOTOR_COMMISSIONING
包含历史配置，不应从头照抄。本流程没有记录新的实物测试结果。

本轮先在固定台架测试夹爪，不连接机械臂运动控制。电脑通过 ESP32 USB
运行现有工具，ESP32 通过 I2C 读传感器、UART2 控制舵机接口板。
夹爪不需要连接机械臂末端 I/O 才能完成本轮测试。

## 1. 准备与接线

准备 ESP32 DEVKIT V1、当前夹爪/STS3215、现有 URT-1 接口板、USB 数据线、
适配该实物舵机的独立电源、万用表、固定物体与接物托盘。
要标定 N，再准备沿接触法向加载的测力计或称重单元及固定夹具。
接线、改变电源或信号电平设置前，断开 USB 和舵机外部电源。

| 连接 | ESP32 端 | 说明 |
|---|---|---|
| 电脑 USB 数据线 | ESP32 USB | USB 串口与开发板逻辑供电；历史端口 COM4，重新核对实际端口 |
| 磁传感器 V | 3V3 | 保留已有 3.3 V 接法，不接 VIN/5V |
| 磁传感器 G | GND | 传感器地 |
| 磁传感器 SDA | GPIO21 / D21 | 当前代码 I2C SDA |
| 磁传感器 CLK/SCL | GPIO22 / D22 | 当前代码 I2C SCL；配置地址 0x14 |
| 原 STM32 D0 所接的接口板串口线 | GPIO16 / RX2 | 保留已经调通的线去向；接口板丝印须对照实物 |
| 原 STM32 D1 所接的接口板串口线 | GPIO17 / TX2 | 同上，不按通用 TX/RX 交叉规则重接 |
| 接口板 GND | ESP32 GND | 与舵机电源负极共地，按实际供电拓扑核对 |
| 接口板逻辑 5V | 历史接 ESP32 VIN | 用户曾确认该接法；必须实测 VIN/板端电压，USB 下 VIN 不是精密稳压 5V |
| 舵机线束 | 接口板对应的舵机端口 | 核对端口、型号、极性，沿用已有调通接法 |
| 舵机独立电源 | 接口板舵机电源输入 | 额定电压按实物标签确认；禁止接到 ESP32 VIN/3V3 |

供电有两个不同要求：接口板逻辑电源与 UART 信号电平。若实物符合
引用的 URT-1 版本，其逻辑需要 USB 或外置 5V，UART 电平可选 3.3V/5V；
ESP32 侧使用 3.3V 信号设置。不要认为舵机电源会自动提供逻辑 5V。
厂商原文：[URT-1 使用说明，第1页](https://files.seeedstudio.com/products/Feetech/URT-1%E4%B8%AD%E6%96%87%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E.pdf)。
该手册不能代替实物板版本与舵机电压确认。

若历史 USB→VIN→接口板逻辑供电的实测电压不符合板要求，先确认并
修正逻辑供电，不用提高软件阈值处理。换外部稳压逻辑电源时须核对
开发板回灌/多电源连接方式，不能简单并接两路 5V。
此前约 7.5 V 是用户报告的供电条件，不是对所有 STS3215 的额定推荐。

## 2. 固件与电脑准备

历史已上传并确认 continuous_position=true 的版本可先复用，不必每次烧录。
若需要重刷，支撑机构/取下物体、先断舵机功率电源，关闭全部占串口工具，
Arduino IDE 打开当前仓库 `firmware/atom_gripper_esp32/atom_gripper_esp32.ino`，
同目录头文件也必须是当前版本。使用经典 ESP32 Dev Module、实际 CP210x
端口及已验证的 MLX90393/FTServo 库。上传结束不自动 ARM。

当前代码：舵机 ID1、UART2 1 Mbps；电脑 USB 串口 115200 baud。
这两种波特率不是同一接口。界面绝对位置范围 2000–2600 counts，
正方向张开，负方向闭合；固件外层边界 1937–2668，JOG 最多±100。
速度寄存器20、加速度10、原始负载门槛80、电压原始值72–82、温度门槛40
均是现有临时设置，不是力标定或额定能力；不在本流程修改。

在仓库根目录（包含 tools、firmware、ros2_ws 的目录）运行：

```powershell
python -m pip install -r tools/gripper/requirements.txt
python -m serial.tools.list_ports
```

Windows 历史端口是 COM4；macOS/Linux 换成实际 /dev/cu.* 或串口设备路径。
确认的是 ESP32 CP210x 端口，不是接口板自身的 USB 端口。
本路径只由 ESP32 发送舵机指令，不同时使用厂商软件控制接口板。

## 3. 本次推荐：带日志的台架控制台

关闭 Arduino 串口监视器、GUI 网关、sensor_bridge、hardware_bridge、capture
和其他串口工具，只运行下面一个进程：

```powershell
python tools/gripper/motor_console.py --port COM4 --log tmp/gripper_force/session01/serial.jsonl
```

每次换新的 session 名；控制台会保存命令、UTC 时间及收到的全部串口行，
包括不在屏幕显示的 V1 磁场样本。连接后不自动 ARM/运动，持续发 KEEPALIVE。

先只接 USB 检查传感器，输入 `STATUS`、`STREAM ON`：磁场有效且持续更新。
在取下物体、机构支撑和可切断功率电源的条件下接通舵机独立电源，
输入 `PING`、`STATUS`，应看到 ok=1、mode=0、feedback_ok=1；
current STATUS 应报告 continuous_position=1、位置合理、传感器健康。
独立电源关闭时 PING 失败不代表必须改固件。

按下面顺序手动输入，每条命令等待回执；这不是自动执行脚本：

| 步骤 | 命令/动作 | 继续条件 |
|---|---|---|
| 释放 | `DISARM` | 无物体，机构有支撑；收到 DISARM_OK torque_off |
| 排故 | 必要时 `RESET` | 先解决实际故障，收到 RESET_OK；无故障无需强制 RESET |
| 空载基线 | `STREAM ON`，静置至少30s | 不接触/移动磁体和垫片，记录实际有效样本数 |
| 基线归零 | `ZERO` | 必须 disarmed、静止、无接触；等待 ZERO_OK，约20个有效样本 |
| 使能保持 | `ARM` | 收到 ARM_OK；反馈有效、无故障、位置在允许范围 |
| 确认方向 | `JOG 5`，到位后 `JOG -5` | 正向张开；两步都得到 MOVE_DONE 且无异常 |
| 空载检查 | 必要时 `OPEN` | 目标2600是空载位置测试；确认外部无机械干涉 |

若初始位置在1937–2668外，ARM会拒绝。先断舵机功率、检查卡滞并在
释放状态下人工回到已验证的2000–2600内侧区间，重新上电检查；
不要靠扩限或强行 ARM 解决。新夹爪装配的方向/行程不同则重新测量。

## 4. 固定物体夹持

物体放在托盘/支撑上，将接触处对准硅胶垫。先按物体宽度张开，在接触前
用单次 `JOG -5` 小步闭合，每步等待完成并检查机构、磁场与参考力。
不能把 `CLOSE`（直接到2000）当作通用带物体夹持动作。
接触后仍需参考力/物体允许载荷判断，5 counts 不代表固定或安全的力增量。

达到暂定持有状态后 `STOP` 并保留控制台和心跳，记录位置、物体质量、
姿态、接触材料、参考力（有仪器时），观察标记是否相对夹爪滑移。
确认物体有托盘保护后逐渐撤去支撑。拟定每次持有60s、重新夹持10次；
记录实际时长、滑移/mm和测量分辨率、掉落及损伤，不能只写“成功”。

`STOP` 是请求当前位置扭矩保持；`DISARM` 是释放扭矩。测试结束先支撑/
接住物体，再 DISARM、确认回执，最后 QUIT、关闭电源。
QUIT/退出控制台只尽力 STOP，不保证释放扭矩或断电仍不掉。
串口 STOP 不是硬件急停；预留直接切断舵机功率的操作，同时考虑掉物风险。

故障时保存原始报错和 STATUS，停止实验、支撑物体；检查机构、供电与
传感器后人工 DISARM→RESET→必要时空载 ZERO→ARM。没有自动复位续跑。

## 5. 想用现有网页操作时

先支撑/取下物体并在控制台 DISARM，退出控制台。不要同时打开两套工具。

```powershell
# 只读状态检查
python tools/operator_gui/server.py --mode gripper --gripper-port COM4
# Ctrl+C退出只读网关后，启动允许操作的网关
python tools/operator_gui/server.py --mode gripper --gripper-port COM4 --enable-gripper
```

打开 http://127.0.0.1:8088，在 Gripper controls 使用 Enable hold、
Target position、Stop、Disarm。`--enable-gripper` 仅开放操作权限，不自动使能。
带物体小步接近可用 Target position 每次减5 counts，保持2000–2600范围；
等待完成后再下一步。Open2600/Close2000只是位置目标。
ZERO 在释放、无载且静止时执行。页面失联会请求 STOP，仍须实测保持行为。
本次需要完整磁场标定日志时优先使用上节控制台；不能边开GUI边开capture。

## 6. 标准力标定与接机械臂

无标准参考时，本轮结果只能是针对该固定物体的持有位置配方。
要调目标力N，先沿接触法向安装参考测力装置，同步采磁场/位置/参考力，
进行多开口、多载荷、加载/卸载和独立验证；详见
[标准标定流程](GRIPPER_FORCE_CALIBRATION.md)。ZERO 与 load_raw 都不是N。
当前未实现力估计或本地力闭环，不启用 force 请求。

夹爪台架验收后再挂机械臂。先核对新法兰实物朝向、TCP、质量/重心和
相机/PCB/线缆包络，将配套 URDF/SRDF 接入真实规划链路并验收碰撞拒绝。
之前推送模型不表示现有启动器已加载，也不表示实机碰撞保护已启用；详见
[法兰集成边界](GRIPPER_MOUNT_V2_INTEGRATION.md)。

# Tracer 2.0 车载计算与整机供电候选方案

2026-10-07；研究结论与候选设计，非采购确认或部署验收。用户确认未来底盘型号为松灵 Tracer 2.0，目标为车载独立运行，不携带笔记本；计算机预算约 AUD500–1,000，不含机械臂、底盘和相机。是否包含全部电源、CAN、网络附件尚未明确，本研究保守将基本计算附件纳入预算。

## 推荐方向

当前 Project ATOM 以确定性视觉定位、MoveIt 规划、夹爪闭环和任务编排为基线，尚无已确认必须 CUDA 的生产推理负载。优先比较一台 x86-64 Mini PC（i5/Ryzen5级、建议32GB/至少16GB RAM、512GB NVMe）与 Jetson Orin Nano Super8GB。第一阶段不建议两台电脑分布式部署，避免额外同步、供电与故障边界。

- x86：更接近现有 Ubuntu24.04/Jazzy Docker 开发路径，内存余量和 CPU 工作负载更易安排；没有默认 NVIDIA CUDA 能力。消费级 Mini PC 需固定、散热、线缆应力释放和实际 Linux/USB 验证，不等于工业认证。NUC/i5 和 Ryzen5/7 小主机为候选等级，不承诺任意机型达到任务延时目标。
- Orin Nano Super8GB：适合需要 CUDA/TensorRT 的视觉推理，8GB RAM 为 CPU/GPU共享预算；需要 ARM64重建、相机驱动与 GPU容器兼容测试。不得按标称 TOPS推断 MoveIt/导航/点云都更快。NVMe、外壳/固定、车载 DC/DC、CAN适配器和无线附件需计费。
- 原版 Jetson Nano：NVIDIA已将其开发套件与 JetPack4标为 EOL，不建议为新平台采购。它与 Orin Nano是不同代际。
- Orin NX16GB或宽压工业整机可在并发感知负载/可靠性需求增加时复查；本预算先不预设采购。

澳洲价格锚点：2026-10-07查阅 Core Electronics，Orin Nano Super开发套件 DEV-22098 页面标价 AUD809.88含GST，未计运费及车载附件，不是总套装报价。预算上限1000时仅余190.12，完整装车可能超预算。x86采购可先把主机控制在500–700、预留150–300用于基本接口/电源/固定；这只是规划额度，不是市场报价或成本保证。

## 数据架构

```text
远程笔记本/平板 ── Wi-Fi/AP ── 车载主机（固定在底盘设备舱）
                                  ├─ Ethernet ── UF850原厂控制箱 ── 机械臂
                                  ├─ USB3 ── 腕部深度相机（型号待核）
                                  ├─ USB串口 ── ESP32 ── URT-1 ── 夹爪舵机
                                  ├─ USB/原生CAN ── Tracer2.0
                                  └─ USB/Ethernet ── 后续导航传感器（未选择）
```

相机 USB线和夹爪串口线留在机器人内部，不是连向外部笔记本的拖线。车载主机安装在底盘，避免把计算机重量加到腕部。控制箱 Ethernet与上次研究的腕部 User Ethernet直通通道是不同用途的接口。主机只有一个网口时可直连机械臂，以Wi-Fi管理；后续增加 Ethernet传感器再用车载交换机。

车上运行实机驱动、感知、规划/运动、任务执行、夹爪、导航与状态/故障处理；Gazebo、RViz和训练默认留在开发电脑。ROS任务在本地执行，Web界面只是操作入口；当前 GUI默认 loopback/read-only，远程开放需要受控网络、访问控制与明确的运动授权设计，不能直接绑定外网。

底盘厂商 ROS2包通过 ugv_sdk/CAN工作，官方组织页面列出 Tracer2.0兼容。但 tracer_ros2 README仅列Tracer/Tracer-mini，SDK公开常测环境仍列Ubuntu18.04/20.04/22.04及Foxy/Humble，不能宣称本项目Jazzy或交付固件已验证。使用Linux SocketCAN适配器（USB-CAN可选隔离），核对500kbps候选参数、终端电阻与实际固件协议；CAN电平不能直连普通GPIO。

功能按现有模块组合，任务优先使用配方。底盘硬件边界有独立驱动的合理性；不为每种“导航后抓取”任务另增节点或复制感知/规划代码。机械臂保留单一运动所有权，导航命令需仲裁和超时。首阶段候选流程为到站→确认停车/定位→操作机械臂→收臂到行驶姿态→再行驶；这是待批准/验证的设计建议，不是现有能力。腕部相机不能默认承担完整底盘导航/安全避障，导航传感器需另立预算与视野验证。

## 软件兼容性与证据

现有 D-007为Ubuntu24.04/ROS2 Jazzy，不因底盘或Jetson改变它。2026-10-07查阅NVIDIA当前文档：Orin Nano官方快速入门已使用JetPack7.2.1/L4T39.2.1，下载说明列Ubuntu24.04；所以不能用旧“Orin只能Ubuntu22.04”结论否定Jazzy路线。

该官方支持不证明本项目所有依赖能运行。Orin需验证载板BSP、UEFI更新前提、USB相机/librealsense、ARM64包/容器、xArm SDK、MoveIt、底盘驱动和GPU用户态/宿主驱动匹配。已有Dockerfile包含Gazebo/RViz等开发依赖，且固定镜像digest；它是部署输入，不是车载ARM64可直接运行的证据。运行镜像以后应按实机必要包收敛，未在本次修改实现。

## 电源是整机关键边界

当前Tracer2.0官方页面规格为24V30Ah电池、对外24V15A；这是产品标称，实际交付修订版、BMS允许电流、端口是否稳压、满充/欠压电压、急停是否切断扩展电源需确认。旧Tracer手册不能直接代替Tracer2.0资料。

```text
Tracer经确认的扩展电源
   ├─保险/滤波/适当DC/DC ── 车载主机
   ├─独立保护支路 ── 网络和导航传感器
   └─机械臂供电：独立核算并获厂商确认，不能默认共用该端口

机械臂工具24V ── 腕部5V与7.4V分配（见前一份研究）
```

Orin Nano官方开发套件配19V适配器，车载供电可研究适当24→19V稳压转换；实际载板输入范围与低压/瞬态需核对。不要把7–25W模块功耗模式当作整台主机、相机、NVMe、USB-CAN的输入峰值。原型可先将计算/传感器支路按60–100W作为待测设计占位量，不是实测负载或选定电源额定值。它约对应24V端2.5–4.2A（未计转换损耗），还需启动裕量和温升验证。消费级Mini PC同样按其铭牌输入配电，不能直接接24V。

UF850官方资料列：机械臂典型240W/最大1000W，建议500W电源；AC控制箱100–240VAC，DC8500控制箱输入48–72VDC。上述数字是厂家规格，具体工作循环未实测。Tracer标称外供功率24×15=360W；机械臂500W经90%效率转换后仅该支路即需约23.1A@24V，1000W约46.3A@24V，均超过15A。因此不能默认一块24→48V升压板就能用扩展口带动整套机械臂。典型240W也不是峰值设计保证。

若实物为AC控制箱，车载逆变器可作研究路线，但需峰值、浪涌、效率、PE/接地、故障与整机电池/BMS能力核算。若为DC控制箱，研究厂商认可的48–72V电源/独立电池系统及制动回馈。两者均未选型，不应绕过BMS私接电池。电源问题独立于“Jetson还是x86”，应先向机械臂/底盘厂商核对交付配置。

名义能量24×30=720Wh，不是可用能量。理想计算720/300=2.4h尚未计底盘驱动、损耗、剩余电量保护和任务负载，因此不能作为整机续航承诺。安装机械臂、控制箱与设备后须复核总质量、CoM、伸臂倾覆力矩和制动工况，150kg额定载重不证明伸臂稳定。

## 断网、重启与验收

自主任务在车载主机本地执行；远程会话断开后的停机/保持/继续策略应按任务明确。人工遥控命令过期必须停发有效运动命令并进入经验证的停止状态，不重放过期目标；通信恢复或主机重启不得自动恢复运动。故障锁存/授权复位与夹爪带物保持行为需验收。硬件急停链应独立于Wi-Fi、ROS和主机，验证对底盘、机械臂和工具的实际作用；软件stop不能当硬件急停。计算机是否在急停后保留供电以记录日志需由电气方案决定。

最低采购前验证：候选机实际相机流配置+感知+MoveIt+导航负载同时运行，记录CPU/GPU/RAM、任务延时、丢帧、CAN超时、磁盘写入、温升与耗电；CPU规划和USB链路亦需测量。之后分阶段验证底盘只读CAN、受控短距离运动、定点机械臂、停车后操作，以及断网/欠压/主机重启。无硬件在本次测试；ROS/SDK/OS确认选择在验证后记录到DECISIONS。

## 来源（2026-10-07查阅）

- [Tracer2.0官方产品参数](https://www.agilex.ai/page/6908c8545e78cfa260412c03?mi=0&rn=TRACER+2.0)：24V30Ah、24V15A、差速、150kg。
- [AgileX官方组织兼容列表](https://github.com/agilexrobotics)、[tracer_ros2](https://github.com/agilexrobotics/tracer_ros2)、[联合开发UGV SDK](https://github.com/westonrobot/ugv_sdk)：CAN路径与常测环境边界。
- [NVIDIA Orin Nano Super规格](https://www.nvidia.com/en-sg/autonomous-machines/embedded-systems/jetson-orin/nano-super-developer-kit/)：8GB、7–25W模块模式。
- [NVIDIA当前Orin Nano快速入门](https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/quick_start.html)、[JetPack当前下载/版本表](https://developer.nvidia.com/embedded/jetpack/downloads)：7.2.1/Ubuntu24.04、19V适配器。
- [NVIDIA Jetson FAQ](https://developer.nvidia.com/embedded/faq)：Nano/JetPack4 EOL与开发板使用定位。
- [Core Electronics澳洲报价](https://core-electronics.com.au/nvidia-jetson-orin-nano-developer-kit.html)：809.88AUD含GST，价格可能变化。
- [GEEKOM A6官方接口/内存示例](https://www.geekom.au/geekom-a6-mini-pc/)：消费级Ryzen小主机候选示例，未确定采购或项目兼容性。
- [UF850电源接口](https://docs.850.ufactory.cc/3.controller_electrical_interface.html)、[UF850技术规格](https://docs.850.ufactory.cc/8.technical_specifications.html)。
- [既有D-007](../DECISIONS.md)、[腕部供电研究](WRIST_POWER_AND_CAMERA_LINK_20261007.md)。

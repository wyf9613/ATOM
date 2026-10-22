# ATOM 汇报讲稿 · 2026-10-16

## 1. Semester scope. Hardware next.

今天主要汇报五件事：和化学组的会议、本学期范围、BOM、车载电脑以及下周实机测试。最后确认11号oral的具体时间。

## 2. Arrange a meeting next week.

我们已经加上Bo的联系方式，准备约下周和化学组见面。今天问Jon和Ying要不要参加，还是先由我们两个人去。建议带workflow图，确认具体操作、允许的标记或夹具、精度要求和实验室访问安排。会议尚未预约。

## 3. Where should this semester stop?

这页保留原workflow，不把它当作已实现能力。红框目前覆盖粗定位、观察、标记对齐和精确目标计算。请导师确认本学期终点：目标位姿输出，还是进一步包含局部校正或固定底座取放。底盘导航和完整端到端流程不默认纳入本学期交付。

## 4. A measurable target for 26 S2.

现有架构roadmap把本学期目标写为集成操作子系统，包含夹爪；新workflow红框更聚焦定位。今天需要对齐这两者。建议先保证实机目标位姿链路，再决定取放是必做还是扩展。精度门槛、测试次数和工况需一起约定，不在这里编造指标。

## 5. From current baseline to hardware evidence.

已有仿真视觉接近基线，以及独立夹爪空载位置测试，不代表真实视觉抓取已验收。先固定装配和几何，再标定、观察、测误差。如确认本学期要取放，还需要传感器配置冻结、夹持验证、停止验证和联合任务。每个任务按配方复用模块，不一框一节点。

## 6. Five procurement items to review.

这页按10月15日收敛后的五项BOM，不把旧扩展清单重新加进来。先盘点原厂引出线。5V和7.4V用真正DC/DC模块，核输出电流、瞬态、热和供电隔离。机械臂能源系统先确认控制箱AC/DC版本，再拆分器件；作为一个预算项避免重复计价。

## 7. Prefer an x86 NUC / Mini PC.

我倾向NUC或x86小主机。树莓派是ARM架构，需要检查依赖、驱动和容器重建，可能增加迁移工作；这不等于不能跑ROS。用户认为NUC价格不贵，但目前没有具体报价，因此用potentially affordable。比较要含存储、散热、供电和安装的整套成本，不能只看裸板价格。

## 8. Check compatibility before purchase.

16GB最低、32GB优先是已有BOM讨论稿的建议，不是实测得到的硬门槛。Pi5官方规格确认是ARM处理器，具备USB3；迁移风险要具体检查相机、SDK、容器和软件包。不要声称所有NUC都更快，也不默认有CUDA。最终选型及理由确认后记录DECISIONS。

## 9. Start with a stationary hardware setup.

下周实机测试先约时间和设备。建议静态固定底座起步，用无危险替代样品。先验证装配、供电、通信、相机，再做标定和重复定位。接触、抓取和联合动作依赖前置门槛通过。区分软件停止和硬件急停，确认实际作用，不能用软件stop代替硬件急停。测试计划不是已完成结果。

## 10. Confirm these before we leave.

下午还要找Jon和Ying确认oral。上次只说11号，具体时间没有说；月份也没有在这次请求里明确，所以不擅自写11月11日。现场确认具体时段，最好也确认日期、地点、时长和形式。这里是待办提示，不表示已发出消息或安排了会议。

来源：BOM_DRAFT_20261015.md；PROJECT_STATUS.md（2026-10-07状态）；SYSTEM_ARCHITECTURE_ROADMAP.md；用户提供workflow及今日事项。价格未新增报价，测试安排为建议。

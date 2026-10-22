# ATOM 成品电源站候选比较

查阅日期：2026-10-19。按用户要求补充 DJI 与同类品牌。BLUETTI（铂陆帝）和 EcoFlow（正浩）是不同品牌；此前优先候选是 BLUETTI Elite 100 V2。

## 价格与初筛

以下型号是**一台共用电源站的替代候选**。澳元公开零售价不等于学校正式报价、库存保证或机械臂组合适配证明。DJI 采用 D1 Store 澳洲单机含 GST 价，不计太阳能套装、扩展电池或无人机充电配件。

| 候选及购买页面 | 单机 AUD | 标称容量 Wh | 连续电池 AC 输出 W | 本项目判断 |
| --- | ---: | ---: | ---: | --- |
| [BLUETTI Elite 100 V2 AU](https://www.bluettipower.com.au/products/elite-100-v2-portable-power-station) | 999 | 1024 | 1800 | 保留为 BOM 基准候选 |
| [DJI Power 1000 V2](https://www.d1store.com.au/products/dji-power-1000-v2) | 999 | 1024 | 2600 | 同价、输出余量更大；同负载下不因额定 W 更高而增加续航 |
| [DJI Power 2000](https://www.d1store.com.au/products/dji-power-2000) | 1999 | 2048 | 3000 | 容量翻倍，约22 kg；若2小时目标的实测负载较高，更值得比较 |
| [DJI Power 1000 Mini](https://www.d1store.com.au/products/dji-power-1000-mini) | 699 | 1008 | 800 | 低功率参考；低于机械臂文档1000 W最大值，尚未计入电脑，不列为机械臂首选 |
| [EcoFlow DELTA 3 Classic](https://au.ecoflow.com/products/ecoflow-delta-3-classic-portable-power-station) | 1099 | 1024 | 1800 | 与基准同标称容量/输出，公开价较高，交期需确认 |
| [EcoFlow DELTA 3 Plus](https://au.ecoflow.com/products/ecoflow-delta-3-plus-portable-power-station) | 1399 | 1024 | 1800 | 容量与Classic相同；不能因Plus名称认定续航更长 |

以上均为厂家标称 LFP 成品站。技术依据：[DJI 澳洲官方比较页](https://store.dji.com/au/product/dji-power-1000-v2-200w-foldable-solar-panel-combo?from=site-nav&set_region=AU)、[Power 2000规格](https://www.dji.com/power-2000/specs)、[Mini规格](https://www.dji.com/power-1000-mini/specs)、[BLUETTI AU手册](https://s4.bluettipower.com/bluetti_lgf/support/2026/05/81a69e72-f8b6-41e9-a057-24a767ff28a5.pdf)。DJI官方比较链接为太阳能套装页面，**仅用于技术数据，不采用其套装价格**；V2的2600 W连续输出附25°C实验室条件。Mini的最大/旁路输出不能代替800 W电池连续输出。

## 2小时目标与经费

统一使用假设：可用 AC 能量 = 标称 Wh × 0.80；覆盖逆变损耗及预留，未测定。续航 = 可用能量 ÷ 机械臂加电脑的平均 AC 负载；不计 Tracer 行驶电池。

| 容量 | 达2小时所需平均 AC 负载上限 | 500 W平均负载估算续航 |
| --- | ---: | ---: |
| 1024 Wh | 409.6 W | 1.64 h |
| 2048 Wh | 819.2 W | 3.28 h |

这些是容量比较，非实测或续航保证。Power 2000在更高平均功耗下有更大容量余量；Power 1000 V2提高输出余量但没有增加相对基准的标称能量。

- 当前BOM仍计BLUETTI $999 + 安装/运费预留$100 = 向化学团队申请$1,099。
- 若改用同价DJI V2，按同一预留仍为$1,099，正式报价可能变化。
- 若选择DJI Power 2000，按同一预留为$2,099。安装/运费仍需按重量和供应商重报。
- 本队电气及Pi套件$602.96、既往支出前余量$197.04不变；不把六台候选累加采购。

## 正式询价与验证

D1页面库存正文与购买栏出现不一致，故没有确认现货。询价确认准确AU型号、GST、交期、学校PO及运费；EcoFlow同样需核实交期。保留原机械臂AC控制箱及Pi原厂PSU，先按各自原厂AC线供电，不在此轮改造主电路。所有候选仍需对应手册、接地/故障保护、电气审核、启动/制动及组合负载测试；相关安全工作见[既有证据审查](BATTERY_COMPATIBILITY_AUDIT_20261019.md)。品牌或更高瓦数不代表通过系统级安全验证。本轮没有采购、提交预算或发送询价。

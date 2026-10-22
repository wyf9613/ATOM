# 机械臂与机载电脑共用电源：候选方案研究

研究日期：2026-10-19。用户目标：约2小时持续工作；UF850现有AC控制箱；Tracer行驶时机载设备可保持供电。不是已完成集成或获批采购。未发送询价、未做实物测试。

**当前定位：备用方案研究。** 用户后续已选择优先恢复BLUETTI Elite 100 V2成品方案，以Rev06 BOM为当前提案，并新增[DJI与EcoFlow成品候选比较](POWER_STATION_COMPARISON_20261019.md)。下文分体型号及成本保留作技术比较，不表示替换主方案或确认采购。

## 推荐进入询价的路线

**独立24V级成品深循环电池 + 明确支持移动安装的纯正弦逆变器，同时供原厂机械臂AC控制箱及树莓派原厂USB-C电源。** 优先询价 Enerdrive EN1120S-X-24V；Victron Phoenix Inverter Smart 24/2000 作较便宜的比较项。两者都比原BLUETTI候选有更明确的车辆用途资料，但尚无UF850组合适配认可。

```text
独立24V级成品电池（自带BMS）
  → 经审核的DC保护、隔离开关及线束
  → 车载纯正弦逆变器 + 经审核的AC保护与分配
      ├─ 原厂AC电源线 → UF850原厂控制箱 → 机械臂及腕部电源
      └─ 树莓派原厂27W USB-C电源 → Pi 5及其USB外设

批准地点的墙上交流电 → 匹配电池的专用充电器 → 电池
Tracer原电池 → 底盘驱动（本方案不直接并联或改接两套电池）
```

这是一块电池供机械臂与电脑，并非两块电池。树莓派PSU已在原套件价格内，先核查交付型号。逆变器的AC转换损耗是保留原厂电源、简化初期接口验证所付出的代价。后期可研究独立DC/DC电脑支路，但必须核对5V/5A USB-PD识别、外设预算和供电保护，不直接用普通USB口或腕部5V降压替代。

共用逆变器故障会使两者同时失电。急停、低SOC任务停止、夹持保持、电脑关机/日志和恢复后不自动运动需要单独设计。原厂AC适配器隔离不等于整机急停或故障保护已完成。

## 具体型号与证据

| 候选 | 原厂/供应商事实 | 评价与未决项 |
| --- | --- | --- |
| **Enerdrive EN1120S-X-24V** | 24V输入21–31V；230V/50Hz、2000W正弦输出；内置RCD及AC转换开关，约5.9kg。2026 Rev1.4手册明确给出车辆/船舶安装及逆变侧保护安排 | **优先询价。** 移动用途和保护资料比原候选完整。AC转换开关不是电池充电器；仍需独立匹配充电器。启动峰值曲线、UF850启动和制动行为仍需书面确认 |
| **Victron Phoenix Inverter Smart 24/2000** | 2000VA；25°C持续1600W，40°C持续1450W；230V正弦输出；约13kg。原厂手册有车辆控制示例，发布汽车EMC资料 | 价格较低的比较项。**2000VA不等于2000W。** 要另行设计AC分配/保护；手册电池容量建议为24/2000配200–500Ah，较小LFP包必须让供应商确认，不擅自解释为已满足。汽车EMC资料不证明机器人振动、机械或系统安全合规 |
| **iTechworld iTECH24V100** | 官网$1,199含税；标称24V/100Ah，规格表列24.8V、连续100A、约26kg；明确面向房车、4WD、船舶和振动工况 | 经济型100Ah询价候选。网页Quick Stats列200A，而型号规格与正文列100A，按**100A**保守筛选；要求准确型号签章数据表、化学体系、可用Wh及峰值时间。所链接STD通用手册主要为12V示例，不套用其电压 |
| **Amptron AT-LFP-24-50AV01，升级外壳版本** | 官网$999；25.6V、50Ah/1280Wh，70A持续、140A峰值5s，约13.5kg；有移动/船舶用途及防振结构说明 | 轻量和较小容量候选。旧产品页标售罄，新升级页可加购；同SKU且标题IP65/正文IP67矛盾，需要书面确认交付修订版和库存，不把防水等级当化学品防护。70A电池不能释放逆变器全部2000W输出 |
| **Amptron BluEdge AT-LFP-24-100-BTC-BV10** | 官网起价$1,999；25.6V、100Ah/2560Wh，持续200A、峰值400A/3s，约22kg；内置BMS/通信，船舶及工业用途 | 更大容量和电流余量的替代候选，价格明显提高。起价含哪些附件、GST和具体合规证书需报价确认；不把营销页的通用标准表述当作此机器人系统认证 |

Enerdrive原厂页USB参数与2026手册数值不同，均不按Pi5完整供电使用。2026手册PDF第8页有车载供电示例、第10页移动接地要求、第12页说明逆变模式下RCD与厂家内部保护安排；由学校电气人员据交付版核验，学生不自行增加零地跨接。

## 两小时容量核算

先使用**80%综合可用系数**，合并转换损耗、余量及低压提前停止的规划假设；它不是实测效率或产品保证。P为逆变器AC输出侧的**机械臂+电脑+相机/附件的平均总功率**，不是机械臂额定最大值。

所需标称电量：`E(Wh) = P(W) × 2(h) / 0.80`。

| 假设平均总功率 | 两小时所需标称电量 | 1280Wh包的估算时长 | 2560Wh包的估算时长 |
| --- | ---: | ---: | ---: |
| 300W | 750Wh | 3.41h | 6.83h |
| 500W | 1250Wh | 2.05h | 4.10h |
| 800W | 2000Wh | 1.28h | 2.56h |
| 1000W | 2500Wh | 1.02h | 2.05h |

因此50Ah/1.28kWh只有在平均总负载约500W以下、且实测容量/温度/停止阈值允许时才可能达到2小时，不能先承诺。100Ah约2.5kWh为当前功耗未知时更有余量的询价方向。iTECH页面名义24.8V×100Ah≈2480Wh，其电压与LFP通用标称不同；上表2560Wh列是Amptron包计算，不将它套给iTECH。

电量够不代表峰值电流够。示例仅用于计算：1100W AC负载、21V低压、假设85%瞬时效率，DC电流约61.6A；2000W时约112A。故70A包不能按2kW持续系统宣传，100A包也不能无条件承诺低SOC时满2kW输出。浪涌、BMS时间曲线、线束压降及温升均需厂商审查及试验。

## 价格与预算影响（AUD，19 October 2026）

| 项目 | 公开参考价 | 价格性质/限制 |
| --- | ---: | --- |
| Enerdrive EN1120S-X-24V，Springers | 1547.26 | 网站含GST；准确型号库存与学校PO需询价。原厂页含税价1731作为第二价格锚点 |
| iTECH24V100 | 1199.00 | 官网含税；数据表缺口见上 |
| iTECHBC20-24原厂24V/20A充电器 | 399.00 | 官网含税但**售罄**；需查可采购库存或厂家认可替代品，不是已齐套可下单 |
| 配电、线束、安装固定、运输等 | 500.00 | **工程预留，不是报价**。不保证覆盖学校要求的安装、电气验收和检测服务 |
| **经济型100Ah询价方案合计** | **3645.26** | 不含树莓派购买价；已在本队$602.96单独计入，避免重复计算；安装/检测实际额外费用待报价 |

若采用原厂Enerdrive价1731，上述规划总额为3829。若改用Amptron BluEdge100Ah电池1999及配套充电器按未折扣价310、逆变器1547.26、预留500，规划总额为4356.26；GST/具体套装仍应在统一报价中明确。50Ah Amptron999+配套充电器310+逆变器1547.26+预留500为3356.26，省约289但容量约减半，且峰值余量更低。上述方案**互斥，不累加采购**。

Victron对比：1035的逆变器公开价较低，但外部AC保护与供应商对小容量电池的确认费用尚未落实；不能只用逆变器价差比较整套成本。EcoFlow Power Kits是真正面向RV的集成路线，但澳洲官网2kWh套装显示9999且售罄，本项目不优先考虑。原来的1099只适用于旧未通过候选的占位，已不能代表这些新的车载方案成本。

## 为什么不直接共用Tracer原电池

Tracer2.0官方页面公开扩展输出24V/15A，即约360W标称。它可能适合经匹配转换后的机载电脑支路；不足以默认覆盖UF850启动和最大负载。不可绕过底盘BMS私接原电池，也不可直接把两块电池并联。共用底盘电池带机械臂需要AgileX认可的专用高功率输出/电源集成方案及新报价，现无证据。

## 采购前收敛到一套整机报价

给学校认可的Enerdrive/Victron安装商或lab cluster同一份需求：UF850现有AC控制箱、Pi5原厂PSU、2小时目标、移动时保供电、停车后操作机械臂。请求其把电池、BMS、匹配充电器、逆变器、保护、安装和验收一起配套报价，并核查启动/制动/漏电及预充需要。要求输出保护图、低SOC与恢复策略和签字安装责任。保留原厂急停；RCD、BMS或软件停机都不替代整机硬件急停。

学校认可的充电地点、GRA新增活动覆盖、化学实验环境、液体/可燃蒸气隔离、质量/重心及防倾覆仍需评审。当前候选具备更充分的组件移动用途证据，但没有任何一套已完成UF850组合实测或系统安全认证。本次未选择新OS/ROS/驱动，也没有确定采购。

## 可追溯来源

- [Enerdrive当前原厂产品页](https://www.enerdrive.com.au/products/2000w-24v-true-sine-wave-inverter-with-ac-transfer-safety-switch)
- [Enerdrive Inverter-X手册2026 Rev1.4](https://cdn.shopify.com/s/files/1/0953/8237/2639/files/Inverter-X-User-Manual-2026_Rev-1.4-1.pdf?v=1789531199)
- [Springers逆变器目录（EN1120S-X-24V含GST1547.26）](https://www.springers.com.au/shop/category/inverter-chargers-inverters-rv-inverters-83)
- [Victron原厂安装](https://www.victronenergy.com/media/pg/Inverter_Smart/en/installation.html)、[规格](https://www.victronenergy.com/media/pg/Inverter_Smart/en/technical-specifications.html)、[Springers24/2000含税1035](https://www.springers.com.au/shop/pin242201000-victron-phoenix-inverter-smart-24-2000-10631)
- [iTECH24V100型号及价格](https://itechworld.com.au/collections/lithium-batteries/products/itech24v100-24v-100ah-lithium-battery)、[所链接通用手册](https://itechworld.com.au/cdn/shop/files/STD_Range_User_Guide.pdf?v=10171185027194175861)、[原厂充电器](https://itechworld.com.au/products/itech24v20a-24v-20a-ac-charger)
- [Amptron50Ah升级页](https://amptron.au/products/classic-24v-50ah-70a-ip67-lifepo4-battery/)、[旧页](https://amptron.au/products/24v-50ah-70a-continuous-discharge-lifepo4-battery/)、[BluEdge100Ah/200A](https://amptron.au/products/24v-100ah-200a-continuous-discharge-lifepo4-battery/)
- [EcoFlow Power Kits用途](https://www.ecoflow.com/au/ecoflow-power-kits/series)、[澳洲价格/库存](https://au.ecoflow.com/collections/ecoflow-power-kits)
- [Tracer2.0原厂](https://www.agilex.ai/page/6908c8545e78cfa260412c03?mi=0&rn=TRACER+2.0)
- [Pi5原厂供电建议](https://www.raspberrypi.com/documentation/computers/getting-started.html)、[27W电源](https://www.raspberrypi.com/products/27w-power-supply/)
- [UF850原厂AC接口](https://docs.850.ufactory.cc/3.controller_electrical_interface.html)、[功率规格](https://docs.850.ufactory.cc/8.technical_specifications.html)

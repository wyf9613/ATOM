# ATOM 学校采购流程与当前行动清单

整理日期：2026-10-19。已读 `uni documents/买东西/` 下全部五份文件，未修改原件。用户确认 GRA 已批、预算尚未提交，机械臂控制箱接墙上交流电。以下是流程整理及候选设计，未代发邮件、提交预算或下单。

**当前主方案（Rev06）：** 按用户选择，优先采用BLUETTI Elite 100 V2成品电源站作为机械臂及机载电脑共用电源候选。电源站$999，安装/运输预留$100，拟向化学团队申请$1,099；树莓派仍计入本队$602.96。材料突出集成便利、价格与续航，采购条件中简要保留厂家使用条件确认及电气/负载验证，不能表述为已验证适配。详见[证据审查](BATTERY_COMPATIBILITY_AUDIT_20261019.md)。

Rev06新增[六款成品站对比及购买页面](POWER_STATION_COMPARISON_20261019.md)：三款DJI及两款EcoFlow与现有BLUETTI基准并列，均为替代候选，不累计采购。DJI Power 1000 V2公开单机价$999；Power 2000为$1,999，若选用且保持$100安装预留，能源经费改为$2,099。Mini仅800W连续输出，作为低功率参考。新增比较未改变当前基准经费，也没有完成选型批准。

约2小时为目标，按1024Wh和80%综合可用假设，机械臂加电脑平均AC负载需约410W或以下，仍需实测。分体电池/逆变器方案保留为[备用研究](SHARED_MOBILE_POWER_OPTIONS_20261019.md)，其更高估算不计入当前成品电源站主方案。

## 按顺序推进

1. **团队与导师确认BOM和经费分工。** 五项供电物料加一套树莓派 Pi 5 8GB 套件。按用户修正，树莓派正式计入本队采购预算：电气零件及运费预留 $213.53 + 树莓派套件 $389.43 = $602.96；扣除既往支出前距 $800 还有 $197.04，用于后续装车供电、固定件或报价变化。机械臂电池系统 $1,099 另向化学团队申请，不占本队 $800 额度。经费归属尚未获批，不代表可个人垫付。
2. **带BOM、GRA与电池方案找项目指定lab cluster。** 主要技术方向为MED，化学实验室使用条件请CMM协同。查IO线和电脑库存、核对供应商，确认新增锂电/AC活动是否需要修订GRA或补充task/plant RA、SOP和培训。已批GRA不自动覆盖未评估的新活动。
3. **取得预采购检查表和正式询价。** 文件夹缺少单独的prepurchase checklist及App Guide引用的独立FEIT Capstone Budget Guide，应向当前LMS/cluster取得。询价要含AU型号、数量、GST、运费、库存/交期、学校PO可接受性及有效期。公开零售价可支持预算估算，但工程预留额不是供应商报价。
4. **Capstone App填Cash及In Kind。** View/Update Budget → +Spending。硬件通常为Equipment，其余按真实类别。同供应商合一行，附明细BOM/报价，comment说明用途。借用电脑、工具或服务也登记In Kind，通常附提供方估值邮件PDF；普通小件可用指南允许的网络估值。
5. **金额含GST并纳入运费。** App会向上取整到整澳元。每队$800是耗材采购额度，不是额外电脑额度；既往支出/实际余额尚未确认。
6. **上传对应附件和prepurchase checklist，再点Submit。** Update/保存不等于提交。导师endorsement不是最终批准，仍有协调人/Facility审核。
7. **获批后走eMarket。** 用Catalogue、PunchOut或Free Format；找不到商品/供应商则请cluster/Student Guides协助。篮子名含项目代码，分享给当前cluster处理人和Student Guides，勾选可修改权限并通知审批人。学生建篮子，工作人员完成采购及PO。
8. **按通知领取和验收。** 电池等危险/大件可送专门库房，一般件多到Loans Hub，课件要求收到通知后约48小时内领取。保存PO、发票、序列号、验收记录；借用或可复用设备按cluster安排归还。

## 文件里的关键细节与差异

- **个人垫付不报销：** 2026课件slide11明确规定。获批预算也不等于可以自行网购。
- **IT设备先查借用：** 2026课件slide9建议向cluster借硬盘/路由器/相机等IT设备，登记In Kind。借电脑须确认借期及可装车使用。
- **TCS不能提供免费电子/五金耗材：** 课件slides9/20、App Guide p8。PLA打印服务可免费（slide10），服务估值与登记向cluster确认。
- **TCS不允许锂电池或240V设备：** 课件slide20直接列出两者，不默认在那里充电或测试电源站/机械臂。由cluster安排其他地点。
- **人工成本与采购现金分开：** Week3 slide6的学生$100/h、导师$200/h和单件<$100归Sundries用于项目/Charter成本估算；采购App依2026年3月指南按供应商聚合，不计人工进$800购物清单。
- **当前负责人需核对：** 2026课件slide15列Diandra Elizabeth、Mr Andy Kang、Ms Katya Shemetova，FAQ p3列Miss Arati Nair、Mr Andy Kang及cluster成员。使用当前项目指定人员，先向Student Guides核对。eMarket指南文件名为2025但末页标February2021，通用UI步骤可用，不能据此确认联系人或实时权限。
- **FAQ自身对改篮子有矛盾：** p3说加物后邮件通知，p4说共享后不再加物、用项目代码#1/#2新篮子。建议新建追加篮子并通知，由处理人确认。
- **缺少当前截止日期：** 2026课件列GRA开放21.08、预算开放04.09，这些是开放日；部分分隔页仍标Semester1。需查LMS/cluster确认当前截止日期。

## 电池与火灾风险

既有AC控制箱下的候选路线：AU成品LFP交流电源站 → 原厂AC控制箱 → UF850；保留Tracer原电池/BMS。电源站自带电池/BMS/逆变器/交流充电功能，不重复采购裸电芯、独立BMS和DIY逆变器。电池用于最终移动无拖线目标；现有固定底座测试仍可接墙上电源。

初筛约1kWh、额定1800W、纯正弦输出、AU接口与原厂充电、安全资料完整。Wh是容量、W是功率；X-Boost/Power Lifting不能当额定功率使用。仍需核对实物铭牌、启动浪涌、制动/再生兼容性、接地与故障保护，不能只按瓦数承诺可用。

| 风险 | 下单/使用前措施 | 所需证据 |
| --- | --- | --- |
| 电芯失效、热失控 | 完整未改装成品、AU型号、BMS/温度保护及安全/保修/召回资料。LFP同样可能热失控，不能承诺不着火 | 供应商文件、cluster/HSW复核 |
| 充电过热 | 原厂规定充电设备；cluster批准地点，通风、非可燃表面、远离化学品及出口；有人看护，不默认过夜无人充电，不在TCS充电 | 充电SOP、指定地点 |
| AC触电/保护失效 | 学校电气人员核对PE、隔离形式、适用保护及检查测试要求。未核对前不认定普通插入式RCD有效，不自行做零地跨接 | 原厂说明、电气复核 |
| DC短路、降压过热 | 输入/支路保护、合适线径、绝缘、极性防错及应力释放；负载/温升测试。电源站BMS不替代外部线束保护 | 配电图、测试记录 |
| 松脱、碰撞或通风受阻 | 底盘低位刚性固定，防泼溅且保持厂家通风间距，核对整机质量/CoM与伸臂稳定性 | 安装图、检查记录 |
| 欠压、掉电或自动复电 | 定义低电量停止任务与带物保持响应，禁用未经验证的定时启动/自动复电恢复运动和省电自动断电 | 受控失电/恢复测试 |
| 烟、异味、异常发热或鼓包 | 停用；有烟/火则撤离，按现场应急流程报警/拨000。不要搬动正在冒烟或燃烧的约1kWh电源站，不自行拆包处置 | 现场应急流程 |

CFA的大型储能指南仅用于“LFP也可能热失控”的化学风险说明，不把其设施级规定套用到本原型。可向供应商索取UN38.3等适用运输文件，但运输测试不等于实验室使用获批。软件STOP不等于硬件急停，工具失电可能导致夹持变化，整机停机行为仍需验证。

## 现在还缺什么

项目代码、既往支出/余额、预采购检查表、IO线库存与准确型号/报价、舵机电压变体及峰值电流、电源站AU技术资料和学校可采购路径、化学团队经费承诺、批准的充电地点、计算机借用条件。

## 学校文件索引

| 文件 | 关键页 | 用途 |
| --- | --- | --- |
| MATZ - S2 2026 Capstone budget and procurement steps.pptx | slides8-11、13-16、20 | RA、库存/借用、供应商、个人不报销、篮子分享、TCS限制 |
| FEIT Capstone Project App Guide - budget plan (updated March2026).pdf | p3-6、7-8 | GST、供应商聚合、附件、预采购表、InKind |
| EMI CAPSTONE- FAQ AND FAS.pdf | p2-4 | RA、最终审批、分享权限、联系人及追加篮子 |
| eMarket - Student User Guide2025.pdf | p4、6-15、16 | 登录、Catalogue/PunchOut/FreeFormat、分享并通知审批人 |
| Lecture_week3_Scheduling_and_Cost.pptx | slides5-6 | 项目成本估算与$800耗材采购的区别 |

主技术联系 `feit-medlabcluster@unimelb.edu.au`；化学实验室使用条件 `feit-cmmlabcluster@unimelb.edu.au`；篮子与操作协助 `feit-studentguide@unimelb.edu.au`。主题带项目代码。本文未发送邮件。

外部技术来源，查阅2026-10-19：[UF850控制箱](https://docs.850.ufactory.cc/3.controller_electrical_interface.html)、[UF850功率规格](https://docs.850.ufactory.cc/8.technical_specifications.html)、[CFA充电安全](https://www.cfa.vic.gov.au/fire-safety/home-fire-safety/preventing-house-fires/battery-and-charging-safety)、[CFA LFP风险说明](https://www.cfa.vic.gov.au/ArticleDocuments/1933/250611%20-%20CFA%20DGMR%20Renewable%20Energy%20Facilities%20v4.4.pdf)。

# Ethics 展示与答辩准备（不提交）

作者：Yifan Wu，1618332。书面正文、slides、英文讲稿由同一套论证组织。此文件供理解与练习，不属于 850 词报告，也不需要上传 Canvas。

## 核心论点

ATOM 的潜在价值是帮助实验室人员完成重复操作，但是否伦理上可接受，取决于目标是否正当、手段是否可接受，以及是否认真处理可预见的后果。不要只用效率或成功演示来证明项目有价值。

具体证据是 2026-10-07 的空载夹爪实验：没有报告物体接触时，磁场也发生变化。它支持“不能把磁场直接等同于接触力”的审慎结论，不支持某种具体故障原因，也不证明夹持力大小或安全性。现有代码阻断未标定的 force 命令；校准、停止和样品保持验证、员工咨询都是下一步建议，不要说成已经完成。

## 与课程的对应

| 概念 | 课程位置 | 在作业中的应用 |
| --- | --- | --- |
| 伦理理由区别于自利或法律理由 | Final PPE slides 21–22 及 notes | deadline、效率、符合规格不能单独证明道德正当性 |
| Principlism | Final PPE slide 25；EE-4 p.14 | non-maleficence、beneficence、justice 是决策原则，分别讨论怎样限制或指导行动 |
| Duty of care | Final PPE slides 25、34 及 notes | 预见可能伤害并采取合理预防；不要把这里的道德概念写成法律保证 |
| Positive responsibility | Final PPE slide 35；EE-4 p.26 | 主动理解后果、预测影响、认识自身选择及其作用，不能只谈事故后追责 |
| Ethical design | Final PPE slides 8、38–39；EE-4 pp.28–29 | just goals、acceptable means、foreseeable intended and unintended ends |
| 职业守则 | Final PPE slides 40–41 | Consult Australia 7 + Engineers Australia 4.2，恰好两条 |
| 提前识别影响 | Brey 2012, section 4, journal pp.309–311 | 区分技术、具体产物和使用情境；把未来影响写成待审查情境，不假装已有数据 |

Howard 讲义中的 Beard & Longstaff 论点通过讲义作二手引用；没有声称读过该书原文。Brey 原文已读取。报告未使用预测警务文章作为实验室项目的证据。

## 展示方法

- 严格两页；不要另加封面、目录、参考文献页或 AI 声明页。
- 第一页解释项目边界、三类利益相关者与三个原则；第二页用真实数据展开一项伦理判断及两条认识。
- 完整逐字稿在 `oral.json`，也嵌入 HTML 的讲稿面板；导出的讲稿为 `ATOM_Ethics_Speaker_Notes.md`。
- HTML 可离线使用：←／→ 翻页，F 全屏，N 显示／隐藏讲稿，P 打印。打印只包含两页 slides，不包含讲稿与操作按钮。
- 讲稿已改为 323 词的简单英文版；[中英对照稿](ATOM_Ethics_Speaker_Notes_Bilingual.md) 附词义说明。
- 目标结束时间约 4:30，留 30 秒余量。按自己的实际语速计时；不要为了逐字读完而加速。
- 超时时先缩短第一页面向三类人的举例，再缩短第二页关于具体样本数的口头解释；不要删掉证据限制或结尾两项行动。
- 图中 ΔBz 单位是 µT（微特斯拉）。可以读作 “change in the magnetic field”。不要读作 N 或 force。
- “Proposed” 必须说清。没有完成员工访谈，没有完成硬件系统安全验证，没有证明自动化会增加或减少岗位。

## 可能的 Q&A 与英文回答

### 1. Why is this an ethical issue rather than only a technical calibration problem?

The calibration issue changes what others may reasonably rely on. If I call an uncalibrated reading a safe force measurement, operators could permit a task without understanding its limits. The ethical issue is exposing others to foreseeable harm through an unsupported claim. Calibration is one technical means of meeting that responsibility.

中文要点：从“传感器准不准”走到“别人会根据你的说法做什么、由谁承担风险”。

### 2. Why are you confident you can meet your duty of care?

I would not claim the review proves that we have already met it for deployment. It identifies foreseeable harms and the evidence needed before progressing. I can contribute by retaining test boundaries, communicating uncertainty and escalating unresolved hazards. Integrated operation should remain conditional on reviewed controls and physical validation.

中文要点：不要承诺零风险或已满足 duty of care；解释主动预防和有条件推进。

### 3. What would you do for stakeholders who do not directly benefit?

I would include cleaning, maintenance and nearby laboratory staff when defining operating zones and recovery procedures. Trials should preserve their access and avoid transferring extra work or exposure to them. Clear training and reporting routes would help, but consultation must also be able to change the design or deployment decision.

中文要点：咨询必须能改变决策，而不是通知别人接受风险。

### 4. Which means would be unethical even if they improved the demonstration?

Bypassing an unresolved force gate to make a demonstration work, hiding failed trials, or allowing people into an unvalidated motion area would be unacceptable. A useful end cannot automatically justify those means. I would reduce the demonstration to a supported subsystem and explain the limitation instead.

中文要点：给出项目具体例子；不能只说“危险行为不伦理”。

### 5. You did not choose autonomy or self-determination. Why?

I prioritised non-maleficence, beneficence and justice because this review centres on handling risks and the distribution of automation's effects. That is a focus choice, not a claim that autonomy is unimportant. Meaningful operator control, honest information and staff involvement still protect people's ability to influence work that affects them.

中文要点：三个原则不是完整排名；未单列 autonomy 不等于忽视它。

### 6. What is the difference between a value and a principle?

A value identifies something worth protecting, such as honesty, care or accountability. A principle directs a decision. For example, care makes nearby staff's welfare matter; non-maleficence requires us to avoid progressing when foreseeable harm is not adequately controlled. The principle turns the concern into a reason for action.

中文要点：关心什么 vs 怎样据此行动；用同一个项目场景说明。

### 7. How do goals, means and ends differ in ATOM?

A repeatable tube transfer is an immediate engineering goal. Calibration, staged testing and the chosen control method are means. Better working conditions are an intended end, while job disruption or overreliance could be unintended ends. The review examines all three because achieving the technical goal does not establish an ethical overall outcome.

中文要点：ends 包括非预期后果，不能只列正面的最终愿景。

### 8. What does the graph establish, and what does it not establish?

It describes one reported empty-gripper sequence with one hundred samples at each of five platforms. Mean magnetic readings changed during that sequence. Without an independent force reference or matched time control, it does not identify contact force, isolate the cause, prove repeatability or quantify total measurement uncertainty. It motivates further calibration work.

中文要点：500 个样本不等于 500 次独立实验；本轮不能区分位置、时间漂移和回差。

### 9. What if uncertainty is unavoidable? Would your position stop all development?

Uncertainty calls for proportionate limits, rather than stopping every activity. We can continue supervised subsystem tests using non-hazardous surrogates while collecting evidence. The key is to match autonomy and exposure to what is supported, then reassess. A deadline does not remove the obligation to explain remaining uncertainty.

中文要点：允许在限定条件下学习，不能把“零风险”当作唯一门槛。

### 10. How would you resolve a conflict between productivity and safety?

I would identify who gains, who faces harm and what alternatives are available. If the faster mode depends on unsupported sensing or unvalidated stopping, I would retain the conservative mode. If later evidence supports a change, affected staff should be involved. The researcher's productivity benefit alone is not a sufficient reason to impose risk on others.

中文要点：moral vs prudential；不要只做总收益减总成本，把少数人风险抹平。

### 11. Why choose Consult Australia 7 and Engineers Australia 4.2?

They address two connected responsibilities. The first concerns whether our claims have an adequate evidential basis. The second concerns the effects of our engineering on people and the environment. In this case, honest force-sensing limitations should affect permission to progress; simply adding a disclaimer while allowing the same unsupported operation would be insufficient.

中文要点：证据诚实必须改变运行边界，不能只靠免责声明。

### 12. Is a software stop enough? Should the gripper simply release torque?

Neither should be assumed safe. A software stop depends on its control and communication paths; it does not establish a hardware emergency-stop function. Releasing gripper torque might drop a tube. We need separate assessment of motion stopping, sample retention, communication loss and power loss under the intended test conditions. Those validations are not complete.

中文要点：不现场臆测具体停机策略；停止运动和保持样品是相关但不同的验证对象。

### 13. Could automation displace workers? Does retraining solve that?

Displacement is a foreseeable possibility, not an outcome we have measured. Retraining can help but does not guarantee secure employment or preserve influence over work. I would involve technicians in task allocation and assess how benefits and burdens are distributed. An efficiency gain for owners does not by itself justify losses imposed on workers.

中文要点：不编造岗位变化数据，也不把培训当作自动解决方案。

### 14. Why call reuse sustainable when robots consume energy?

Reuse may avoid some material and fabrication waste, but that does not prove a net environmental benefit. We would need to consider energy, replacement parts, damaged tubes, failed samples and disposal under comparable conditions. My claim is that these effects belong in the design assessment, not that ATOM is already environmentally superior.

中文要点：reuse 是有条件的潜在优势，不是完整生命周期结论。

### 15. What did you learn from the review?

I learned that progress needs both reliable evidence and a defensible account of who is affected. The gripper example makes uncertainty a reason to limit autonomy, not merely a technical caveat. Looking beyond the operator also changes the design process: nearby staff need influence before deployment decisions are fixed.

中文要点：两项认识对应分阶段验证与利益相关者参与，不重复项目介绍。

### 16. How does your review relate to ethical theories and positive responsibility?

Care and honesty concern professional character; duty of care constrains our actions; beneficence considers consequences; justice asks how those consequences are distributed. I use principlism to connect these considerations in practice. Positive responsibility means using our ability to influence the design before harm occurs, rather than only identifying blame after an incident.

中文要点：virtue、duty、consequences 可共同支持判断；不要把 principlism 简化为单一效益主义。

### 17. How does Brey's technology–artefact–application distinction help?

At the technology level I would consider control of autonomous action. At the artefact level I would examine this gripper and its failure modes. At the application level I would consider the workcell, staff roles and who receives the benefits. This avoids assuming a generally useful technology is appropriate in every deployment context.

中文要点：这是一种对机器人项目的方法迁移；Brey 的原文研究 emerging IT。

### 18. What if a supervisor asks you to proceed despite unresolved concerns?

I would explain the concern, the missing evidence and a bounded alternative, and document the decision. If foreseeable harm remained inadequately controlled, I would decline that operation and raise the issue through the appropriate project or laboratory channel. A supervisory instruction does not remove my ethical responsibility to affected people.

中文要点：课堂 Challenger 的启发是责任不能完全交给上级；回答为假设场景，不暗示导师实际施压。

## AI 使用

AI 实际参与了证据梳理、伦理论点形成、英文初稿、修订、slides、讲稿、Q&A 和文件生成，不能写成“仅语法润色”。报告已有完整声明，slides 第二页有相应声明。保留这次对话与生成源文件，便于按课程规定说明过程。

具体 Faculty/Capstone AI 规则尚未提供。这份文件不据此推断 AI 代写获得许可；应核对实际允许的用途并由本人理解、检查和修改。课程讲义已经对齐，不需要再为术语寻找材料。

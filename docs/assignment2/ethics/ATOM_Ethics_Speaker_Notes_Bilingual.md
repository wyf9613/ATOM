# ATOM Ethics：简单英文讲稿（中英对照）

Yifan Wu · 1618332

英文共 323 词。只读英文，中文帮助理解。练习目标约 4 分 30 秒，以自己实际计时为准；最多 5 分钟。

标题、时间提示和最后的词表不用念。先读一句英文，再确认自己知道它的中文意思。两个守则的英文说明是口头概括，并非原文引用。

## 第 1 页

练习时间：0:00–1:50

> Hello.  
> I am Yifan Wu.  
> Today I will talk about ethics in Project ATOM.  

大家好，我是 Yifan Wu。今天我介绍 ATOM 项目的伦理问题。

> Our robot aims to move test tubes in a lab.  
> So far, we have tested robot moves on a computer.  
> We have also tested the gripper.  
> The full system is not ready yet.  

我们的机器人目标是在实验室里搬运试管。目前，我们在电脑仿真中测试了机器人运动，也测试了夹爪。完整系统还没有准备好。

> My main question is: who gets help, and who takes the risk?  

我最关心的问题是：谁得到帮助，谁承担风险？

> Lab workers may spend less time moving tubes.  
> But their jobs may change.  
> Lab owners may get more work done.  
> But tubes or tools may break.  

实验室工作人员可能少花一些时间搬试管，但他们的工作也可能改变。实验室管理方可能完成更多工作，但试管或设备也可能损坏。

> People nearby may face risks too.  
> This includes cleaners.  
> They may get little help from the robot.  

附近的人也可能面临风险，包括清洁人员。他们可能没有直接从机器人那里得到多少帮助。

> I use three rules: help people, avoid harm, and be fair.  
> We should not add risk just to save time.  
> We should also ask workers what they need.  

我采用三个原则：帮助别人、避免伤害、公平对待。我们不应仅仅为了节省时间就增加风险，也应询问工作人员的需要。

## 第 2 页

练习时间：1:50–4:30

> This graph shows one test of our empty gripper.  
> The sensor reading changed, even with no tube in it.  

这张图展示了我们对空夹爪的一次测试。夹爪里没有试管时，传感器读数也发生了变化。

> The sensor measures a magnetic field.  
> It does not measure force directly.  
> We still need to test the link between the reading and force.  
> So this graph cannot show that the grip is safe.  

传感器测的是磁场，不是直接测力。我们仍需测试读数与力之间的关系。因此，这张图不能证明夹持是安全的。

> Right now, the code blocks force commands.  
> I think we should keep this limit.  
> We need more tests before using force control.  

目前，代码阻断了力控制指令。我认为应保留这个限制。在使用力控制前，我们还需要更多测试。

> We also need to check how the robot stops.  
> Will the tube stay in the gripper?  
> What if the power goes off?  
> The screen stop is not a hardware emergency stop.  

我们还要检查机器人怎样停止。停下后，试管能否留在夹爪里？如果断电会怎样？屏幕里的停止功能不等于硬件急停。

> Two codes guide my view.  
> Consult Australia, rule seven: say only what we really know.  
> Engineers Australia, rule four point two: care for people and the environment.  

两条职业守则指导我的判断。Consult Australia 第七条：我们的说法要有充分知识依据。Engineers Australia 第四点二条：关心人员与环境。这里用简短的话概括了两条守则与项目的关系。

> Our goal is to move tubes well.  
> But we must also think about how we do it.  
> We must think about how it may change people's work.  

我们的目标是把试管搬好，但还必须考虑实现方式，以及它可能怎样改变别人的工作。

> I learned two things.  
> First, test each step before the robot does more.  
> Second, ask the people who may face risks.  
> These are my next steps.  
> They are not finished yet.  
> Thank you.  

我学到了两点。第一，机器人做更多任务之前，应逐步测试。第二，应询问可能承担风险的人。这些是我提出的下一步工作，还没有完成。谢谢。

## 简单说法与课堂术语

演讲时可以用下面的简单说法解释原则；老师追问名称时，再对应到报告中的术语。

| 讲稿里的简单说法 | 报告里的原则 | 中文意思 |
| --- | --- | --- |
| Help people | Beneficence | 为别人带来益处 |
| Avoid harm | Non-maleficence | 避免伤害 |
| Be fair | Justice | 公平分配收益和负担 |

## 需要认得的词

| 英文 | 中文 |
| --- | --- |
| ethics | 伦理：应该怎样做，以及为什么 |
| lab | 实验室，laboratory 的简称 |
| gripper | 夹爪 |
| sensor reading | 传感器读数 |
| magnetic field | 磁场 |
| force | 力 |
| risk | 风险 |
| avoid harm | 避免伤害 |
| fair | 公平的 |
| code / rule | 这里指职业守则／条款 |
| environment | 环境 |
| hardware emergency stop | 硬件急停 |

## 只记住这条逻辑也能把第二页讲顺

空夹爪的读数也会变化 → 磁场不是直接测出的力 → 还需验证 → 保留力控制限制 → 再检查停止和样品保持。

讲到真实项目状态时，保留原稿中的 may、need 和 not yet：可能的影响不等于已经发生，需要完成的测试也不能说成已经完成。

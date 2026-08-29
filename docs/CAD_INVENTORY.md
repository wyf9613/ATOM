# CAD 资产清单

## 1. Fusion 360 原始归档

`hardware/end effector/End Effector Assembly V3.f3z`

- 格式：Fusion 360 分布式设计归档；
- 大小：3,242,872 bytes；
- SHA-256：`9E27B636EE18203D0501DDA5FDDBF83745068A4C52F6580EE69B1A690C6E5581`；
- 根装配：`c20df9ed-acc4-470e-bb55-90ebb96c8449.f3d`。

| 名称 | 归档成员 | 作用 |
| --- | --- | --- |
| End Effector Assembly V3 | `c20df9ed-acc4-470e-bb55-90ebb96c8449.f3d` | 根装配 |
| STS3215 Sub Assembly | `f0795558-8f67-4bee-9ddc-19ff2827dc19.f3d` | 舵机子装配 |
| PDL-RS-MTR-STS3215 FeeTech STS3215 ASM | `92ca7797-e0d8-4603-8317-6ad3d94966b9.f3d` | 舵机模型 |
| STS3215 Servo Mount | `a72196c6-7a60-4a88-b460-35e568c067eb.f3d` | 舵机安装件 |
| Case Opened | `c32a4a06-e177-4b62-b025-11ab20e7abce.f3d` | 外壳零件 |

归档包含声明的外部引用，只能证明结构可解析，不能证明几何、关节语义或可制造性正确。

## 2. 中性 STEP 装配

`hardware/end effector/End Effector Assembly V3.step`

- 格式：STEP AP214；
- 大小：4,213,475 bytes；
- SHA-256：`8EE4FD1C064210EAB24CB10BA67623E497CAB0866ADBCA86D5BE9A0C63AAF351`；
- 解析结构：20 个 product、25 个装配 occurrence、74 个 solid B-rep；
- 已派生固定本体和两个手指视觉网格，位于 `ros2_ws/src/atom_gripper_description/meshes/generated/`。

STEP 层级和位置可用于暂定仿真视觉，但不能定义 URDF 关节、实测惯量、可靠安装变换或 TCP。

## 3. 导出与实测检查

- 在 Fusion 360 中确认全部外部引用；
- 确认单位并复核报告中的 225 x 105 x 131 mm 外形；
- 识别固定组件、关节轴线、限位和手指对称关系；
- 识别法兰、快拆、夹爪基准和 TCP；
- 实测质量和重心，与报告 580 g 比较；
- 分别维护视觉网格和简化碰撞网格；
- 记录来源哈希、导出日期、软件版本、单位、坐标轴和简化方法；
- 原始 F3Z 和 STEP 保持只读。

## 4. 仍缺少

- 单零件制造文件和修订编号；
- 机械臂接口与快拆尺寸图；
- 装配关节限位说明；
- 经验证的材料、质量、重心和惯量报告。

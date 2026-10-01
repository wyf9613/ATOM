# RGB-D 架面融合

2026-10-01，`refactor/modular-task-composition`。能力实现位于 `atom_xarm_sim/perception/depth_fusion.py`，由现有 RackObserver 调用，无新增 node。融合输出取代原 PnP tag 位姿，经过同一 TF 后用于预观察目标确认、架面法向、对齐及接近；没有改变运动验收限值或使用场景真值控制运动。

## 数据与方法

输入必须是已配准到 RGB 的 optical-Z 深度（m），对应 RGB CameraInfo 的成像几何，不是径向量程。现有 Gazebo 同一个 rgbd_camera（640×480、单一光学坐标系/成像设置）通过仿真脚本显式设置 `depth_registered:=true`；任务节点默认该确认参数为 false，不能以相同 frame_id 自动推定实机配准。保留尺寸/frame 检查，RGB/Depth 时间差收紧到 0.035 s；支持 32FC1 大小端及行步长。RGB 与 RGB-D 使用相同架身份门限。

步骤：

1. 同帧多 tag RGB PnP 初始位姿。
2. 各 tag 多边形内缩 5×5 erosion，取不透明 tag 面上的深度，过滤非有限值及 0.08..2.0 m 外值。以 CameraInfo/畸变模型反投影，避开孔洞、背景和透明试管。
3. 80 次确定性 RANSAC（最多 600 个采样点）和 SVD 拟合架平面。要求有效支撑分布至少两个 tag 区域，避免单点测距或窄线估计法向。
4. 对一个 6 自由度刚体位姿联合最小二乘：角点重投影残差 / 0.7 px，深度点到板平面残差 / 0.002 m。深度残差按点数归一化，避免分辨率改变权重。保留已知 tag 尺寸/间距；RGB 约束板内位置与旋转，深度约束法向与距离。
5. 验收正向距离、重投影 RMS ≤2 px、融合平面 RMS ≤4 mm，再使用融合位姿控制。

深度质量门限与权重是暂定仿真配置，不是实机标定的噪声/协方差：每个采样区域至少 15 像素且有效比例 ≥0.5，总样本/内点至少 80，内点比例 ≥0.75，RANSAC 距离门限 4 mm，第二平面方向支撑标准差 ≥6 mm，拟合平面 RMS ≤3 mm。每次处理保存 coverage、内点比例、平面 RMS、融合残差与位移变化。

## 故障与回退

`depth_fusion_enabled` 默认 true；关闭时记录 disabled。缺少支撑、离群点过多、平面退化或噪声过大时保留 RGB PnP 并报告 `used=false` / reason。深度平面与 PnP 初始位姿差超过 30 mm 或法向夹角超过 20° 时拒绝观测，不把矛盾数据当作缺深度静默回退；融合后残差超限也拒绝。旧位姿仍受新鲜度门限约束。持续无有效观测会导致任务超时/失败，不继续动作。

GUI/task 状态、初始报告和 trial summary 的 `depth_quality.fusion.used` / `method` 明确表示是否实际融合。记录的 `rgb_pnp_pose` 是同一帧/同一 TF 的未融合对照；正常目标位姿 `pose` 是实际控制采用的结果。仅观察帧报告保留 `rgb_pnp_tag_poses_robot`。

## 复测与对照

```bash
./scripts/atom.sh sim --camera depth --recipe visual_approach --tag-id 1 --restart
python3 tests/operator_gui/tube_workflow_check.py --require-success --require-depth-fusion
# 按控制台打印的实际 run 目录替换下面路径。
python3 scripts/benchmarks/analyze_depth_fusion.py tmp/operator_gui/workflow/run_YYYYMMDD_HHMMSS
# 容器内软件检查
 docker exec atom-tube-workflow bash -lc 'source /jazzy_ws/install/setup.bash; cd /workspace; python3 -m unittest discover -s tests/operator_gui -v'
```

首次融合运行 `run_20261001_133323` 全流程成功；87 个带融合的同帧目标观测，纯 RGB 平均位置误差 1.549 mm / RMS 1.643 mm，融合平均 0.611 mm / RMS 0.620 mm，相对源码名义 Tag 真值。没有观测回退。采样来自同一次静态场景运行、不同阶段距离且帧间相关，不能当作 87 次独立试验或据此估计实机准确度/置信区间。测试未包含真实噪声、透明材料、外参误差、同步偏差或硬件执行。最终代码与纯 RGB 回归记录见 [测试记录](TAG_RACK_TEST_20261001.md)。

新增合成测试覆盖偏差 RGB 距离修正、法向修正、深度孔洞回退、离群点过滤和大偏差冲突拒绝。后续应使用实物平面/测量真值、不同距离/视角、注入噪声/空洞/配准偏差进行独立对照，不从理想 Gazebo 结果选择实机融合权重。

最终代码运行 `run_20261001_133836`：85 个相关同帧配对，纯 RGB 平均位置误差 1.644 mm，融合 0.584 mm；没有融合回退。完整运动与独立终点真值检查通过；纯 RGB 完整回归也通过。所有指标仅针对本次仿真条件。

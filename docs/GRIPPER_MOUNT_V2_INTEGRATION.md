# 新法兰与原夹爪的模块化集成

2026-10-07。本轮为源码、CAD 网格和描述结构检查；没有实机运动或
MoveIt/FCL 运行时碰撞检查，不是实机防碰撞验收。

## 来源与坐标

只读输入：`hardware/end effector/ATOM_three_parts_20261005.zip`。
三个 STL 的 SHA-256 均与包内 export_manifest.json 一致，网格闭合。
原 STEP 夹爪视觉网格继续使用已有文件，没有修改原始 CAD。
包内指向的 `source_cad/backplate/v2` 等源 STEP 在本工作区不存在；
本次能验证的是 STL、导出清单及原夹爪网格，不能复核缺失的源 CAD。

打印导出只做平移。减去清单 translation_xyz_mm 后恢复原装配坐标。
夹爪视觉变换 R=Ry(π/2)Rx(π/2)，即
`x_g=y_cad−43.494; y_g=−z_cad−22.225; z_g=28.836−x_cad`（mm）。
法兰 STL 的 x=80.8 mm 平面及 x=82.8 mm 的 Ø31.45 mm 定位凸台
支持安装面中心 CAD [80.8,43.494,−22.225] mm 的推导。
因此夹爪基准位于名义法兰 +Z 51.964 mm；名义 TCP 为
[-1.8,0,222.500] mm。采样数是单套 CAD/网格，不具有实测不确定度。
法兰绕轴安装角度、原基准微小偏移、打印件尺寸和 TCP 尚未实测。

衍生网格与来源清单：`atom_gripper_description/meshes/generated/mount_v2/`。
各部件保持独立固定 link，与供应商机械臂 Xacro 组合；没有从 CAD
导出整个机械臂加夹爪的单体网格或 URDF。

## 碰撞模型与范围

原 base 碰撞箱未覆盖完整视觉外形，两个 finger 仅有接触垫碰撞箱。
已替换为各自完整视觉网格在 link 坐标系的包围盒，并为新三个部件加箱体。
各盒每侧加 0.5 mm，是拟定建模余量，不是已证明足够的安全距离。
手指箱体随各自关节运动，但继承的轴、行程和编码器→关节映射仍未实测。
粗包络会误报碰撞；后续可用经覆盖检查的分块包络减小误报，不能简单
禁用工具与机械臂碰撞来消除报错。

新 SRDF 保留供应商原机械臂组及碰撞排除；工具内部重叠包络两两排除，
仅新增 flange_adapter/link6 安装接触排除。夹爪本体、手指、两个支架与
link_base/link1…link6 的检查保留；法兰与其余机械臂 link 也保留。
它不检查工具内部机械干涉。相机本体、ESP32 PCB、螺丝、电缆及被夹物
未在压缩包中，尚无它们的包络；有这些实物时必须补充后再验收。
新部件未虚构质量/惯量；继承夹爪惯量仍为历史临时值，不可用于真实负载配置。

## 生成与验证

在仓库根目录使用独立 Python 环境：

```bash
python3 -m venv tmp/gripper_model_env
tmp/gripper_model_env/bin/pip install -r tools/gripper/requirements-model.txt
# 仅首次准备供应商源码；沿用 D-007 的版本
git clone https://github.com/xArm-Developer/xarm_ros2.git tmp/xarm_ros2
git -C tmp/xarm_ros2 checkout 3dc2b5e8294758d96b54b15fa5920d581b7cbb3d
tmp/gripper_model_env/bin/python ros2_ws/src/atom_gripper_description/scripts/import_mount_v2.py
tmp/gripper_model_env/bin/python tools/gripper/export_description.py \
  --vendor-root tmp/xarm_ros2 --output tmp/gripper_integration/export
tmp/gripper_model_env/bin/python -m pytest -q tools/gripper/test_description_geometry.py
```

export 的输出目录须不存在，以免覆盖已有验收文件。输出：
`atom_gripper_v2.urdf`（独立工具）、`uf850_atom.urdf`（组合）、
`uf850_atom.srdf`。网格 URI 需相应 ROS 包可见，不能只拷贝 URDF。
离线 export 使用明确的本地包路径解析 Xacro，不需要 ROS，不启动控制器。

本轮验证：三个模型/语义文件成功展开；4 项几何回归通过，检查六个
部件的所有视觉顶点被碰撞盒覆盖、空/非空前缀结构、SRDF 引用以及
工具与机械臂碰撞排除范围。使用项目固定供应商源码；Python/Xacro
版本见 requirements-model.txt。没有 urdfdom、Jazzy/MoveIt/FCL 运行时，
没有宣称实际姿态可达或碰撞安全。既有 ROS 包测试需在 Jazzy 构建后运行。

## 接入原机械臂前的验收

原 `uf850_arm_only.launch.py` 构建供应商裸臂或 G1 模型，未加载本组合。
先在既有 Jazzy 环境将同一套 URDF/SRDF 接入 MoveIt 和 TF 发布者，
用静态关节状态检查 RViz 外形、法兰朝向、指间开口和末端 TCP。
记录实际 payload/CoM、相机/PCB/线缆包络与手指状态映射。
机械臂运动组仍以 link_eef 为末端；不能把未标定 gripper_tcp 当作已验证 IK 目标。

以真实起始关节状态和测量后的模型，检查目标与整条路径；分别验证
夹爪开/闭、法兰/支架对各机械臂 link、携物包络和工作台障碍。
需要一个已知碰撞姿态被拒绝的反例，确认碰撞检查确实启用，且没有
ACM、SRDF 或驱动参数把工具相关碰撞全部忽略。再进行低速人工监督验收。
规划碰撞检查不替代机械臂硬件保护或硬件急停，也不覆盖未经监督的直接驱动命令。

# 当前末端的模块化 URDF 检查

2026-10-08。当前组合为原夹爪 + 法兰 V2 + ESP32 支架 V1 + 相机支架 V3。
文件名中的 `v2` 沿用法兰组合接口，不表示相机仍是 V2。
[硬件文件、坐标与打印说明](<../hardware/end effector/README.md>)。

## 修复与保留边界

昨天的组合仍加载相机支架 V2，且没有相机本体碰撞包络；现已替换为
V3，并按同一装配坐标加入 90×25×25.05 mm 的名义 D435i 外壳盒。
夹爪、法兰、两个支架及相机分别为独立 link，机械臂仍由供应商宏提供。
没有合并机械臂 CAD，也没有增加控制节点或新的运动所有者。

组合文件原来默认真实厂商驱动而没有 robot_ip；离线检查现在默认
`fake_components/GenericSystem`。真实配置必须显式提供已验证的
`ros2_control_plugin` / `robot_ip`，并完成相应运行时接入；本轮未启动
任何控制器、连接机械臂或发出运动命令。现有 arm-only/G1/Gazebo 入口
仍未改为使用本组合，不能把本次静态检查当作运行时迁移完成。

视觉网格在 `atom_gripper_description/meshes/generated/mount/`，由硬件
打印 STL 及 manifest 变换生成。所有碰撞包络为覆盖完整视觉外形的
简化箱体，每侧 0.5 mm 建模余量；这个余量没有经过物理验证。
相机盒只是名义壳体，不创建 `camera_link` 或 optical TF，避免把 CAD
推断外参当作已标定驱动帧。PCB、螺钉、USB/线缆和被夹物仍缺包络。

## 名义坐标，单位 mm

由原 CAD 推断，样本 N=1；没有实测不确定度：

- CAD 法兰面中心 `[80.8,43.494,−22.225]`；夹爪转换
  `x_g=y_cad−43.494; y_g=−z_cad−22.225; z_g=28.836−x_cad`。
- `tool_flange → gripper_mount`：`[0,0,51.964]`。
- `tool_flange → gripper_tcp`：`[−1.8,0,222.500]`。
- `gripper_base → d435i_body`：`[0,−73.000,97.561]`；相机长轴沿 X_g，
  镜头暂定朝 +Z_g。`tool_flange → d435i_body` 的 Z 为 149.525。
- `gripper_mount_xyz/rpy` 校正整个工具，包括法兰和所有附属部件。
  法兰绕轴安装角度、相机朝向和 TCP 仍需实测。

原夹爪 0.58 kg 分配、关节 −15…+5 mm、轴向、摩擦系数和 TCP 是历史
临时值。新支架/相机没有虚构惯量；本模型不是完整动力学或实际负载模型。
机械臂仍是名义 UF850 描述，不能据此断言采购型号或实物配置已确认。

## 碰撞排除

继承的工具内部 15 对保守包络排除保留，因此本 SRDF **不验证工具内部
机械干涉**。新增相机仅排除其与相机支架的安装接触；相机对手指、
夹爪本体、法兰、ESP32 支架和各机械臂 link 的检查保留。
工具对机械臂只排除法兰适配件 / link6 安装接触，未批量关闭工具-机械臂
碰撞。粗包络可能误报，不应直接扩展排除列表掩盖错误。

## 生成与检查

使用 D-007 固定的供应商 checkout：
`3dc2b5e8294758d96b54b15fa5920d581b7cbb3d`。

```bash
# CAD 模型生成环境另见 hardware/end effector/README.md
python3 -m venv tmp/gripper_model_env
tmp/gripper_model_env/bin/pip install -r tools/gripper/requirements-model.txt
tmp/gripper_model_env/bin/python ros2_ws/src/atom_gripper_description/scripts/import_mount_v2.py
tmp/gripper_model_env/bin/python tools/gripper/export_description.py \
  --vendor-root tmp/xarm_ros2 --output tmp/current_tool_export
tmp/gripper_model_env/bin/python -m pytest -q tools/gripper/test_description_geometry.py
```

输出目录需不存在。源 Xacro 在两个描述包中；展开的 URDF/SRDF 是临时
产物，不作为第二份维护源码。网格 package URI 需相应 ROS 包可见。

本轮 11 项离线回归通过：完整视觉顶点覆盖、当前三版本与 SHA/坐标
来源、相机包络、空/非空前缀、唯一名称/完整树、网格 URI、mimic/控制
边界、SRDF 引用与排除范围，以及法兰/夹爪/TCP/相机的坐标一致性。
三份当前 CAD 再生成比对通过，最大采样偏差法兰约 0.01601 mm；这只是
数字模型之间的检查，不是打印精度。两份展开 URDF 在本机
`ros:jazzy-ros-base` 容器中由 urdfdom `check_urdf` 解析通过。
两个项目描述包及固定版本的两个供应商描述包已构建安装；两个项目包的
6 项 pytest 用例通过（colcon/CTest 汇总含测试包装器共 8 tests，0 errors /
0 failures）。基础容器缺少 xacro CLI，本轮使用项目固定 xacro 2.1.1 的
纯 Python 模块提供临时 CLI；测试源码和已安装包均未因此改写。
昨天的 `tmp/gripper_integration/export/` 已更新为通过检查的当前
URDF/SRDF，旧导出保留在本轮临时备份中。

未执行实际 MoveIt/FCL 路径碰撞、Gazebo 动力学或实机运动。部署前需要
实测装配、完整线缆/PCB 包络、惯量与 TF，在规划器中验证一个已知碰撞
反例被拒绝，确认整条轨迹及不同手指状态的碰撞检查，再做受监督的低速
验收。规划/软件停止不替代硬件急停或机械臂硬件保护。

# 当前末端 CAD

仅保留：原夹爪总装、法兰 V2、ESP32 支架 V1、D435i 相机支架 V3。

| 文件 | 用途 |
|---|---|
| `End Effector Assembly V3.f3z` / `.step` | 原始夹爪总装，保持原内容 |
| `flange_adapter_v2.step` / `_print_mm.stl` | 当前法兰；STEP 为规则实体反向重建，STL 为原导出 |
| `esp32_bracket_v1.step` / `_print_mm.stl` | 当前 ESP32 支架；STEP 为规则实体反向重建，STL 为原导出 |
| `camera_bracket_v3.step` / `_print_mm.stl` | 新 D435i 背面双 M3 支架 |
| `cad_parameters.json` | 三个零件的生成参数 |
| `cad_manifest.json` | 来源、SHA、打印坐标变换与验证记录 |

**全部 STEP 已统一为原夹爪 CAD 装配坐标；STL 为打印坐标，按 mm / 100% 导入。**
不要将打印 STL 原点直接当作装配原点。各变换记录在 manifest；ROS
使用独立描述包中的派生网格，没有把机械臂和夹爪合并成单体模型。

法兰和 ESP32 的实体具有真实平面、圆柱/圆锥面，可以在 Fusion 等软件
中修改；原草图和特征树没有恢复。几何源各 N=1，双向表面采样最大差
分别为 0.01601 mm 和 0.000393 mm；检查方法和样本数见 manifest。
这些数值不是打印精度或实物公差。原 F3Z 的五个声明 F3D 成员均在包内；
尚未交互验证 Fusion 引用解析。

## 相机支架 V3

[D400 官方图纸](https://www.realsenseai.com/wp-content/uploads/2020/05/Intel-RealSense-D400-Series-Datasheet-May-2020.pdf)
第 108 页：背面双 M3 中心距 45 mm，最大旋入深度 3 mm。
本设计：Ø3.4 通孔、5 厚背板、6 厚连接梁、两道 4 厚加强肋；夹口从
4 扩到 6（两侧各外移 1），外侧根部 R1.5，整个夹口保持 6 净宽。
ESP32 支架保持原 4 mm 夹口。

试制起点：PETG、0.4 喷嘴、0.2 层高、6 道壁、40–50% 填充、至少
6 层顶底；孔和根部可局部实心。相机打印 STL 已侧放，背板侧边落床，
梁、夹脚和上翼需支撑。实际材料应匹配实验室温度、溶剂和清洁方式。
M3×8 加约 0.5 平垫圈的名义旋入为 2.5；装配前量实际板厚、垫圈、
接触间隙和螺钉长度，确保旋入≤3。夹紧跨度增加 2，原螺钉长度需试装。

没有实物 fit、强度、质量/惯量或相机外参标定结果。先试装夹口、
两相机孔及 USB 插头，再检查完整指间行程和线缆。相机换装后需重新
标定；名义包络不能替代相机/PCB/螺丝/线缆的实际装配检查。

## 复现

```bash
python3 -m venv tmp/cad_env
tmp/cad_env/bin/pip install -r tools/gripper/requirements-cad.txt
tmp/cad_env/bin/python tools/gripper/build_mount_cad.py --output tmp/cad_review
```

生成器输出到新目录，并与本目录的当前 CAD/STL 做几何比对，避免覆盖
基准。改参数后是新设计，旧版的吻合阈值不再是其验收标准。
多余历史导出、预览、旧 V2 相机、ZIP 和切片 3MF 已移出活动目录；
本机临时备份在忽略跟踪的 `tmp/hardware_cleanup_20261008/`，Git 仍保留
此前提交的历史。原 ZIP 与成员 SHA 留在 manifest，不依赖备份生成模型。

URDF 与检查结果见 [集成说明](../../docs/GRIPPER_MOUNT_V2_INTEGRATION.md)。

# 五孔 MDF 比色皿架 v1

2026-10-21：可审阅、可试切的参数化初稿，尚未实物验收。

- [设计、尺寸、装配、试切及资料来源](../../../docs/mechanical/CUVETTE_RACK_LASER_V1.md)
- `small_assembly.png` / `large_assembly.png`：装配示意，蓝色为容器外包络。
- `small_dimensioned.svg` / `large_dimensioned.svg`：带尺寸的三视图，**不用于激光加工**。
- `small_cut_RASTER_REVIEW.dxf` / `large_cut_RASTER_REVIEW.dxf`：毫米单位，六块板，CUT_OUTER、CUT_INNER、RASTER 分层。
- 同名 SVG：红色切割路径、黑色实心刻蚀区域；不是 TCS 官方模板。
- `small_front_TAG_ONLY.dxf` / `.svg`：仅带 tag 的前板，ID 0–4；`large_front_TAG_ONLY.dxf` / `.svg`：仅带 tag 的前板，ID 5–9。包含红色切割轮廓和 RGB (0, 0, 0) 黑色刻蚀，毫米单位、1:1 比例；前板名义外包络均为 320 × 63 mm。
- `fit_and_tag_coupon_FIRST.dxf` / `.svg`：先切的公差及刻蚀小样。
- `*_tags_PRINT_100percent.svg`：备用黑白打印图，100% 比例，禁止 fit-to-page。
- [`print_a4/`](print_a4/README.md)：小试管架 ID 0–4 的单页 A4 打印 PDF；黑框外缘 40 × 40 mm，每边另留 5 mm 白边，打印选择实际大小 / 100%。
- `parameters.json`、`build_rack.py`：参数及生成源；`geometry_checks.json`：数字检查及标记到孔位的名义坐标。
- `verify_tag_reference.py` / `tag_reference_checks.json`：与 AprilRobotics 官方图稿逐像素核对，ID0–10 全部一致；校验脚本需要联网。

2026-10-22：加工文件的 RASTER 刻蚀颜色已明确为 **RGB (0, 0, 0)，完全不透明**。DXF 的图层及每个实心 HATCH 都设置 true color 黑色，避免仅使用 ACI 7 随背景显示为白色；SVG 的刻蚀填充及轮廓均为 `#000000`。两种尺寸和试切小样均已修正，切割路径、颜色、尺寸及 tag 图案未改动。Tag 的白色格子和外围留白仍为空白、不刻蚀。

当前刀路已经补偿假定的 **0.15 mm 全切缝**。加工软件不能再补偿一次。请先实测板厚、同机同料试切，修改参数再重建；不要直接将 REVIEW 文件视为最终制造版。

```powershell
python source_cad/cuvette_rack/v1/build_rack.py
```

依赖：Python、numpy、opencv-contrib-python（含 aruco）、ezdxf、shapely、matplotlib。SVG/DXF 无需这些库即可在 CAD 软件中查看。

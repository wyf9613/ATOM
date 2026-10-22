# 独立径向示教把手 v1

2026-10-21 生成，供 2026-10-22 PETG 打印和试装。背板不修改。材料牌号、物理配合与承载未验证。

- [完整把手 STL](../../print_pack/2026-10-21_handle/radial_teaching_handle_v1_mm.stl)：毫米、100%，已摆平放方向，约 172.5 × 63 × 26 mm，打印 1 件。
- [可选试配环 STL](../../print_pack/2026-10-21_handle/flange_fit_coupon_v1_mm.stl)：约 63 × 63 × 9 mm；仅检查接口，不能承载使用。
- `radial_teaching_handle_v1.step` / `flange_fit_coupon_v1.step`：可编辑来源，保留设计坐标；STEP 的 X 轴为法兰轴，STL 已旋转至打印 Z 轴。
- `build_handle.py`：生成实体、导出 STEP/STL、检查网格与静态配合，输出 `parameters_and_checks.json`。
- `package_handle.py`：生成独立打印说明和 ZIP，核对包内数据。
- 三张 PNG：独立零件、平放姿态、与现有背板的静态配合预览。

详细尺寸、切片起点、定位配合、**增加 16 mm 环厚后所需的螺钉长度核对**、试装顺序和使用边界见 [打印与试装说明](../../../docs/mechanical/TEACHING_HANDLE_V1_PRINT_GUIDE.md)。此导出不等于打印件承载或硬件使用已经验证。

"""Export the three latest standalone STEP parts as checked, millimetre STLs."""
from pathlib import Path
import hashlib
import json
import struct
import zipfile

import cadquery as cq
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "2026-10-05"
PARTS = [
    ("camera_bracket_v2", "source_cad/camera_bracket/v2/camera_bracket_v2.step"),
    ("esp32_bracket_v1", "source_cad/esp32_bracket/v1/esp32_bracket_v1.step"),
    ("flange_adapter_v2", "source_cad/backplate/v2/reinforced_backplate_v2.step"),
]


def check_mesh(path, expected_dimensions, expected_volume):
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    assert len(data) == 84 + 50 * count, "Invalid binary STL length"
    dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
    triangles = np.frombuffer(data, dtype=dtype, offset=84, count=count)["vertices"].astype(float)
    assert np.isfinite(triangles).all()
    vertices, inverse = np.unique(np.round(triangles.reshape(-1, 3), 5), axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    undirected, edge_inverse, counts = np.unique(np.sort(edges, axis=1), axis=0, return_inverse=True, return_counts=True)
    assert (counts == 2).all(), "Mesh is not a closed two-manifold"
    orientations = np.where(edges[:, 0] < edges[:, 1], 1, -1)
    assert (np.bincount(edge_inverse, weights=orientations) == 0).all(), "Inconsistent winding"
    area_vectors = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    assert (np.linalg.norm(area_vectors, axis=1) > 1e-9).all(), "Degenerate triangles"
    assert len(np.unique(np.sort(faces, axis=1), axis=0)) == len(faces), "Duplicate triangles"
    parents = list(range(len(vertices)))

    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    for a, b in undirected:
        parents[find(int(a))] = find(int(b))
    components = len({find(i) for i in range(len(vertices))})
    assert components == 1, "Disconnected mesh"
    mesh_volume = float(np.einsum("ij,ij->i", triangles[:, 0], np.cross(triangles[:, 1], triangles[:, 2])).sum() / 6)
    assert mesh_volume > 0, "Non-positive mesh volume"
    volume_error = abs(mesh_volume - expected_volume) / expected_volume
    assert volume_error < 0.002, "Tessellation volume error exceeds 0.2%"
    dimensions = vertices.max(axis=0) - vertices.min(axis=0)
    assert np.max(np.abs(dimensions - expected_dimensions)) < 0.1, "Incorrect mesh dimensions"
    return {
        "triangles": count,
        "vertices": len(vertices),
        "connected_components": components,
        "closed_two_manifold": True,
        "consistent_winding": True,
        "dimensions_xyz_mm": dimensions.tolist(),
        "mesh_volume_mm3": mesh_volume,
        "volume_relative_error": volume_error,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "date": "2026-10-05",
        "units": "mm (STL is unitless; import as millimetres at 100% scale)",
        "tessellation_linear_tolerance_mm": 0.02,
        "tessellation_angular_tolerance_rad": 0.08,
        "cadquery_version": cq.__version__,
        "parts": [],
    }
    for name, relative_source in PARTS:
        source = ROOT / relative_source
        solid = cq.importers.importStep(str(source)).val()
        assert solid.isValid() and len(solid.Solids()) == 1
        bounds = solid.BoundingBox()
        dimensions = np.array([bounds.xlen, bounds.ylen, bounds.zlen])
        translation = [-bounds.xmin, -bounds.ymin, -bounds.zmin]
        printable = solid.translate(tuple(translation))
        target = OUT / f"{name}_mm.stl"
        assert printable.exportStl(str(target), tolerance=0.02, angularTolerance=0.08, relative=False, ascii=False)
        result = check_mesh(target, dimensions, solid.Volume())
        result.update({
            "filename": target.name,
            "source_step": relative_source,
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "source_valid_single_solid": True,
            "source_dimensions_xyz_mm": dimensions.tolist(),
            "translation_xyz_mm": translation,
            "rotation": "none; source orientation retained",
            "source_volume_mm3": solid.Volume(),
        })
        manifest["parts"].append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    (OUT / "export_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    notes = """ATOM 三个零件 STL 打印包 — 2026-10-05

每件打印 1 个，按毫米（mm）、100% 比例导入切片软件。
STL 不自带单位。只平移至坐标原点附近，保留原 CAD 方向；切片时需选择打印方向及支撑。

1. camera_bracket_v2_mm.stl：相机支架 v2，外形 70 × 18 × 17.9 mm。
2. esp32_bracket_v1_mm.stl：独立 ESP32 支架 v1，外形 67 × 42 × 17.9 mm。
3. flange_adapter_v2_mm.stl：加厚法兰转接 v2，外形 54 × 84 × 112 mm。

以上尺寸依次为模型 X/Y/Z 方向，可用来检查是否导入正确。
每个文件仅包含对应支架实体，不包含夹爪、相机、PCB、隔离柱或螺丝。
导出检查已确认：闭合网格、单连通件、三角面方向一致、尺寸与源 STEP 相符。

装配注意：
- 相机前端为 Ø6.8 通孔，用螺丝穿过支架拧入相机底部 1/4-20 UNC 孔；支架没有建模螺纹。
  相机型号、底部孔位置及螺丝旋入深度还需按实物确认。
- ESP32 四孔中心距暂定 46.5 × 23.5 mm，孔径 Ø4.0 mm，需要按实物复核。
- 法兰先装到机械臂，再装夹爪，方便安装四个 M6 螺丝。
  定位凸台暂定 Ø31.45、高 2 mm，打印后需检查配合。

法兰转接是 PLA 加厚试制设计，尚无打印刚度或承载试验结果。
打印方向需考虑层间受力；先检查装配，再在固定工装上验证承载，之后再评估机械臂运行工况。
详细来源、导出精度和网格检查记录见 export_manifest.json。
"""
    (OUT / "打印说明.txt").write_text(notes, encoding="utf-8-sig")
    archive = OUT.parent / "ATOM_three_parts_20261005.zip"
    files = sorted(OUT.glob("*_mm.stl")) + [OUT / "打印说明.txt", OUT / "export_manifest.json"]
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as pack:
        for file in files:
            pack.write(file, arcname=file.name)
    with zipfile.ZipFile(archive) as pack:
        assert pack.testzip() is None
        assert len(pack.namelist()) == 5
        for file in files:
            assert pack.read(file.name) == file.read_bytes()
    print(f"ZIP verified: {archive.name}, {archive.stat().st_size} bytes", flush=True)


if __name__ == "__main__":
    main()

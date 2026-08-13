#!/usr/bin/env python3
"""Extract fixed and moving visual meshes from the inherited STEP assembly."""

import argparse
import hashlib
import json
from pathlib import Path

import cadquery as cq
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_LabelSequence
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFDoc import XCAFDoc_DocumentTool


FINGER_NAMES = (
    "Finger Sub-Assembly STS3215 v8:1",
    "Finger Sub-Assembly STS3215 v8 (1):1",
)


def label_name(label):
    attribute = TDataStd_Name()
    if label.FindAttribute(TDataStd_Name.GetID_s(), attribute):
        return attribute.Get().ToExtString()
    return "<unnamed>"


def bounds(shape):
    box = Bnd_Box()
    BRepBndLib.Add_s(shape, box)
    return [round(value, 6) for value in box.Get()]


def load_components(step_path):
    document = TDocStd_Document(TCollection_ExtendedString("atom_gripper"))
    reader = STEPCAFControl_Reader()
    status = reader.ReadFile(str(step_path))
    if "RetDone" not in str(status) or not reader.Transfer(document):
        raise RuntimeError(f"Failed to read STEP assembly: {step_path}")

    shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(document.Main())
    roots = TDF_LabelSequence()
    shape_tool.GetFreeShapes(roots)
    if roots.Length() != 1:
        raise RuntimeError(f"Expected one assembly root, found {roots.Length()}")

    labels = TDF_LabelSequence()
    shape_tool.GetComponents_s(roots.Value(1), labels, False)
    return [
        (label_name(labels.Value(index)), shape_tool.GetShape_s(labels.Value(index)))
        for index in range(1, labels.Length() + 1)
    ]


def make_compound(shapes):
    return cq.Compound.makeCompound([cq.Shape.cast(shape) for shape in shapes])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("step", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    components = load_components(args.step)
    by_name = {name: shape for name, shape in components}
    missing = set(FINGER_NAMES) - set(by_name)
    if missing:
        raise RuntimeError(f"Missing expected moving components: {sorted(missing)}")

    groups = {
        "base": [shape for name, shape in components if name not in FINGER_NAMES],
        "left_finger": [by_name[FINGER_NAMES[0]]],
        "right_finger": [by_name[FINGER_NAMES[1]]],
    }

    manifest = {
        "source": str(args.step),
        "source_sha256": hashlib.sha256(args.step.read_bytes()).hexdigest(),
        "step_length_unit": "millimetre",
        "urdf_mesh_scale": 0.001,
        "grouping": {},
        "notes": [
            "Assembly placement is inherited CAD data and has not been checked against hardware.",
            "Meshes are visual geometry; URDF collision geometry uses simplified primitives.",
        ],
    }

    for group_name, shapes in groups.items():
        compound = make_compound(shapes)
        output_path = args.output / f"{group_name}.stl"
        cq.exporters.export(
            compound,
            str(output_path),
            exportType="STL",
            # Millimetre-scale tessellation is sufficient for Gazebo visuals and
            # avoids exporting millions of triangles from threads and bearings.
            tolerance=1.0,
            angularTolerance=0.5,
        )
        manifest["grouping"][group_name] = {
            "component_count": len(shapes),
            "bounds_mm": bounds(compound.wrapped),
            "mesh": output_path.name,
        }

    manifest["components"] = [
        {"name": name, "bounds_mm": bounds(shape)} for name, shape in components
    ]
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="ascii"
    )


if __name__ == "__main__":
    main()

"""Offline description export using explicit package roots; no ROS or hardware access."""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET


def expand(source, packages, mappings=None):
    import xacro
    import xacro.substitution_args as substitutions
    original = substitutions._eval_find
    def find(name):
        if name not in packages:
            raise ValueError(f'Package root not supplied: {name}')
        return str(packages[name].resolve())
    substitutions._eval_find = find
    try:
        return xacro.process_file(str(source), mappings=mappings or {}).toxml()
    finally:
        substitutions._eval_find = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vendor-root', type=Path, required=True,
                        help='xarm_ros2 checkout at the project-pinned revision')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    packages = {name: root / 'ros2_ws/src' / name for name in
                ('atom_gripper_description', 'atom_xarm_description')}
    packages.update({name: args.vendor_root / name for name in
                    ('xarm_description', 'xarm_moveit_config')})
    args.output.mkdir(parents=True, exist_ok=False)
    sources = {
        'atom_gripper_v2.urdf': packages['atom_gripper_description'] /
            'urdf/atom_gripper_v2_standalone.urdf.xacro',
        'uf850_atom.urdf': packages['atom_xarm_description'] / 'urdf/uf850_atom.urdf.xacro',
        'uf850_atom.srdf': packages['atom_xarm_description'] / 'srdf/uf850_atom.srdf.xacro',
    }
    for name, source in sources.items():
        xml = expand(source, packages)
        ET.fromstring(xml)
        (args.output / name).write_text(xml + '\n')
        print(args.output / name)


if __name__ == '__main__':
    main()

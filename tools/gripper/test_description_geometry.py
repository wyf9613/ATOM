"""Geometry regressions run offline with the project-pinned vendor checkout."""
import os
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pytest
import trimesh
from export_description import expand

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = {n: ROOT / 'ros2_ws/src' / n for n in
            ('atom_gripper_description', 'atom_xarm_description')}
VENDOR = Path(os.environ.get('ATOM_VENDOR_ROOT', ROOT / 'tmp/xarm_ros2'))
PACKAGES.update({n: VENDOR / n for n in ('xarm_description', 'xarm_moveit_config')})


def model(prefix=''):
    return ET.fromstring(expand(PACKAGES['atom_xarm_description'] /
        'urdf/uf850_atom.urdf.xacro', PACKAGES, {'prefix': prefix}))


def test_collision_boxes_cover_all_visual_vertices():
    robot = model()
    count = 0
    for link in robot.findall('link'):
        mesh_tag = link.find('visual/geometry/mesh')
        if mesh_tag is None or 'atom_gripper_description' not in mesh_tag.attrib['filename']:
            continue
        uri = mesh_tag.attrib['filename'].removeprefix('package://')
        package, relative = uri.split('/', 1)
        mesh = trimesh.load(PACKAGES[package] / relative)
        scale = np.fromstring(mesh_tag.attrib['scale'], sep=' ')
        origin = link.find('visual/origin')
        xyz = np.fromstring(origin.attrib['xyz'], sep=' ')
        rpy = np.fromstring(origin.attrib['rpy'], sep=' ')
        rotation = trimesh.transformations.euler_matrix(*rpy)[:3, :3]
        vertices = (mesh.vertices * scale) @ rotation.T + xyz
        centre = np.fromstring(link.find('collision/origin').attrib['xyz'], sep=' ')
        size = np.fromstring(link.find('collision/geometry/box').attrib['size'], sep=' ')
        assert np.all(vertices >= centre - size / 2 - 1e-8), link.attrib['name']
        assert np.all(vertices <= centre + size / 2 + 1e-8), link.attrib['name']
        count += 1
    assert count == 6


@pytest.mark.parametrize('prefix', ['', 'bench_'])
def test_semantics_preserve_tool_arm_collision_checks_and_valid_tree(prefix):
    robot = model(prefix)
    semantic = ET.fromstring(expand(PACKAGES['atom_xarm_description'] /
        'srdf/uf850_atom.srdf.xacro', PACKAGES, {'prefix': prefix}))
    links = {x.attrib['name'] for x in robot.findall('link')}
    joints = robot.findall('joint')
    children = [j.find('child').attrib['link'] for j in joints]
    assert len(children) == len(set(children))
    assert links - set(children) == {'world'}
    for joint in joints:
        assert joint.find('parent').attrib['link'] in links
        assert joint.find('child').attrib['link'] in links
    tool = {x.attrib['name'] for x in semantic.find(f"group[@name='{prefix}atom_tool']")}
    arm = {prefix + x for x in ['link_base', 'link1', 'link2', 'link3', 'link4', 'link5', 'link6']}
    cross = set()
    for pair in semantic.findall('disable_collisions'):
        a, b = pair.attrib['link1'], pair.attrib['link2']
        assert a in links and b in links
        if (a in tool and b in arm) or (b in tool and a in arm):
            cross.add(frozenset((a, b)))
    assert cross == {frozenset((prefix + 'flange_adapter', prefix + 'link6'))}
    # Every visual box moves rigidly with its link, so coverage also holds at finger limits.
    for name in ('left_finger', 'right_finger'):
        joint = robot.find(f"joint[@name='{prefix}{name}_joint']")
        assert joint.find('parent').attrib['link'] == prefix + 'gripper_base'


def test_cad_mount_restores_export_translation_and_flange_surface():
    robot = model()
    assert robot.find("joint[@name='gripper_mount_joint']/origin").attrib['xyz'] == '0 0 0.051964'
    flange = robot.find("link[@name='flange_adapter']")
    # Back face z=0 and pilot z=-2 mm in the flange frame, within tessellation precision.
    origin = np.fromstring(flange.find('visual/origin').attrib['xyz'], sep=' ')
    assert origin.tolist() == [-0.043494, -0.022225, 0.0808]

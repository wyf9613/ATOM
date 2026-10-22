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


def test_current_revisions_and_mesh_provenance():
    import hashlib
    import json
    hardware = ROOT / 'hardware/end effector'
    source = json.loads((hardware / 'cad_manifest.json').read_text())
    generated = json.loads((PACKAGES['atom_gripper_description'] /
                            'meshes/generated/mount/manifest.json').read_text())
    assert {p['name'] for p in source['parts']} == {
        'flange_adapter_v2', 'esp32_bracket_v1', 'camera_bracket_v3'}
    assert generated['hardware_manifest_sha256'] == hashlib.sha256(
        (hardware / 'cad_manifest.json').read_bytes()).hexdigest()
    for part in source['parts']:
        for name, sha in part['files_sha256'].items():
            assert hashlib.sha256((hardware / name).read_bytes()).hexdigest() == sha
        mesh = trimesh.load(hardware / part['print_stl'])
        mesh.apply_transform(part['print_to_cad_transform_mm'])
        imported = trimesh.load(PACKAGES['atom_gripper_description'] /
            f"meshes/generated/mount/{part['role']}.stl")
        assert np.allclose(mesh.bounds, imported.bounds, atol=1e-5)
        assert imported.is_watertight and imported.is_winding_consistent


@pytest.mark.parametrize('prefix', ['', 'bench_'])
def test_nominal_camera_body_is_covered_and_keeps_collision_checks(prefix):
    robot = model(prefix)
    body = robot.find(f"link[@name='{prefix}d435i_body']")
    nominal = np.fromstring(body.find('visual/geometry/box').attrib['size'], sep=' ')
    collision = np.fromstring(body.find('collision/geometry/box').attrib['size'], sep=' ')
    assert np.allclose(nominal, [.09, .025, .02505])
    assert np.allclose(collision - nominal, .001)
    origin = robot.find(f"joint[@name='{prefix}d435i_body_joint']/origin")
    assert np.allclose(np.fromstring(origin.attrib['xyz'], sep=' '), [0, -.073, .097561])
    assert body.find('inertial') is None  # No invented camera mass/inertia.
    semantic = ET.fromstring(expand(PACKAGES['atom_xarm_description'] /
        'srdf/uf850_atom.srdf.xacro', PACKAGES, {'prefix': prefix}))
    pairs = [frozenset((d.attrib['link1'], d.attrib['link2']))
             for d in semantic.findall('disable_collisions')]
    related = [p for p in pairs if prefix + 'd435i_body' in p]
    assert related == [frozenset((prefix + 'd435i_body', prefix + 'camera_bracket'))]
    assert robot.find(f"link[@name='{prefix}camera_link']") is None


def test_review_defaults_to_fake_hardware_and_driver_requires_explicit_override():
    robot = model()
    assert robot.find('ros2_control/hardware/plugin').text == 'fake_components/GenericSystem'
    hardware = ET.fromstring(expand(PACKAGES['atom_xarm_description'] /
        'urdf/uf850_atom.urdf.xacro', PACKAGES,
        {'ros2_control_plugin': 'uf_robot_hardware/UFRobotSystemHardware',
         'robot_ip': '192.0.2.1', 'prefix': 'bench_'}))
    assert hardware.find('ros2_control/hardware/plugin').text == 'uf_robot_hardware/UFRobotSystemHardware'
    assert hardware.find("ros2_control/hardware/param[@name='robot_ip']").text == 'R192.0.2.1'
    controlled = {j.attrib['name'] for j in hardware.findall('ros2_control/joint')}
    assert controlled == {f'bench_joint{i}' for i in range(1, 7)}


@pytest.mark.parametrize('prefix', ['', 'bench_'])
def test_tree_reachability_mesh_paths_and_mimic(prefix):
    robot = model(prefix)
    links = [x.attrib['name'] for x in robot.findall('link')]
    assert len(links) == len(set(links))
    joint_names = [x.attrib['name'] for x in robot.findall('joint')]
    assert len(joint_names) == len(set(joint_names))
    children = {}
    for j in robot.findall('joint'):
        children.setdefault(j.find('parent').attrib['link'], []).append(j.find('child').attrib['link'])
    reached = set()
    pending = ['world']
    while pending:
        name = pending.pop()
        assert name not in reached, 'Cycle or multiple parent: ' + name
        reached.add(name)
        pending.extend(children.get(name, []))
    assert reached == set(links)
    for m in robot.findall('.//mesh'):
        uri = m.attrib['filename']
        assert uri.startswith('package://')
        package, relative = uri[len('package://'):].split('/', 1)
        assert (PACKAGES[package] / relative).is_file(), uri
    right = robot.find(f"joint[@name='{prefix}right_finger_joint']")
    assert right.find('mimic').attrib == {'joint': prefix + 'left_finger_joint', 'multiplier': '1.0', 'offset': '0'}
    assert right.find('axis').attrib['xyz'] == '-1 0 0'


def test_flange_and_tool_share_one_cad_frame_with_mount_corrections():
    robot = ET.fromstring(expand(PACKAGES['atom_xarm_description'] /
        'urdf/uf850_atom.urdf.xacro', PACKAGES,
        {'gripper_mount_xyz': '.001 .002 .003', 'gripper_mount_rpy': '.1 .2 .3'}))
    joint_by_child = {j.find('child').attrib['link']: j for j in robot.findall('joint')}
    def pose(child):
        if child == 'tool_flange':
            return np.eye(4)
        j = joint_by_child[child]
        origin = j.find('origin')
        result = np.eye(4)
        if origin is not None:
            result = trimesh.transformations.euler_matrix(*np.fromstring(origin.attrib.get('rpy', '0 0 0'), sep=' '))
            result[:3, 3] = np.fromstring(origin.attrib.get('xyz', '0 0 0'), sep=' ')
        return pose(j.find('parent').attrib['link']) @ result
    R = np.array([[0, 1, 0], [0, 0, -1], [-1, 0, 0]])
    for name in ['flange_adapter', 'esp32_bracket', 'camera_bracket']:
        link = robot.find(f"link[@name='{name}']")
        v = link.find('visual')
        uri = v.find('geometry/mesh').attrib['filename'].removeprefix('package://')
        package, relative = uri.split('/', 1)
        mesh = trimesh.load(PACKAGES[package] / relative)
        o = v.find('origin')
        transform = trimesh.transformations.euler_matrix(*np.fromstring(o.attrib['rpy'], sep=' '))
        transform[:3, 3] = np.fromstring(o.attrib['xyz'], sep=' ')
        scale = np.fromstring(v.find('geometry/mesh').attrib['scale'], sep=' ')
        q = trimesh.transformations.transform_points(mesh.vertices * scale, pose(name) @ transform)
        expected = (mesh.vertices @ R.T + [-43.494, -22.225, 80.8]) / 1000
        assert np.allclose(q, expected, atol=1e-8), name
    assert np.allclose(pose('gripper_tcp')[:3, 3], [-.0018, 0, .2225])
    assert np.allclose(pose('d435i_body')[:3, 3], [0, -.073, .149525])

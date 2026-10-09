"""Installed vendor model and ATOM sensor/TF contract regressions."""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import xacro

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ros2_ws/src/atom_xarm_sim'))
from atom_xarm_sim.camera_experiment import add_wrist_camera, allow_wrist_camera_self_collisions


def robot(nominal=True, enabled=True):
    return xacro.process_file(str(ROOT / 'ros2_ws/src/atom_xarm_description/urdf/uf850_atom.urdf.xacro'),
        mappings={'camera_enabled': str(enabled).lower(),
                  'camera_nominal_extrinsics': str(nominal).lower()}).toxml()


def test_vendor_d435i_and_single_connected_tree():
    root = ET.fromstring(robot())
    links = {l.get('name') for l in root.findall('link')}
    assert {'wrist_camera_bottom_screw_frame', 'wrist_camera_link',
            'wrist_camera_color_optical_frame', 'wrist_camera_depth_optical_frame',
            'wrist_camera_optical_frame'} <= links
    assert any('imu' in n or 'accel' in n for n in links)
    joints = root.findall('joint')
    children = [j.find('child').get('link') for j in joints]
    assert len(children) == len(set(children))
    assert links - set(children) == {'world'}
    for j in joints:
        assert j.find('parent').get('link') in links
    assert root.find("joint[@name='wrist_camera_joint']/parent").get('link') == 'tool_flange'
    assert 'realsense2_description/meshes/d435.dae' in robot()


def test_hardware_extrinsics_have_single_driver_owner():
    root = ET.fromstring(robot(nominal=False))
    assert root.find("link[@name='wrist_camera_link']") is not None
    for name in ('color_optical_frame', 'depth_optical_frame', 'optical_frame'):
        assert root.find(f"link[@name='wrist_camera_{name}']") is None
    assert 'wrist_camera' not in robot(enabled=False)


def test_registered_simulator_uses_color_optics_without_duplicate_body():
    root = ET.fromstring(add_wrist_camera(robot(), 'depth', parent='tool_flange'))
    assert len(root.findall("link[@name='wrist_camera_link']")) == 1
    sensor = root.find("gazebo[@reference='wrist_camera_color_frame']/sensor")
    assert sensor.get('type') == 'rgbd_camera'
    assert sensor.find('gz_frame_id').text == 'wrist_camera_optical_frame'
    assert root.find("joint[@name='wrist_camera_optical_alias']/parent").get('link') == 'wrist_camera_color_optical_frame'


def test_camera_arm_collisions_remain_enabled():
    xml = robot()
    semantic = xacro.process_file(str(ROOT / 'ros2_ws/src/atom_xarm_description/srdf/uf850_atom.srdf.xacro')).toxml()
    result = ET.fromstring(allow_wrist_camera_self_collisions(semantic, xml))
    arm = {'link_base', *[f'link{i}' for i in range(1, 7)]}
    for pair in result.findall('disable_collisions'):
        names = {pair.get('link1'), pair.get('link2')}
        if 'wrist_camera_link' in names:
            assert not names & arm

import subprocess
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory


def expanded_gripper():
    share = get_package_share_directory('atom_gripper_description')
    result = subprocess.run(
        ['xacro', f'{share}/urdf/atom_gripper_standalone.urdf.xacro'],
        check=True,
        capture_output=True,
        text=True,
    )
    return ET.fromstring(result.stdout)


def test_standalone_gripper_has_expected_modular_chain():
    robot = expanded_gripper()
    links = {link.attrib['name'] for link in robot.findall('link')}
    joints = {joint.attrib['name']: joint for joint in robot.findall('joint')}

    assert links == {
        'world',
        'gripper_mount',
        'gripper_base',
        'left_finger',
        'right_finger',
        'gripper_tcp',
    }
    assert joints['gripper_mount_joint'].find('parent').attrib['link'] == 'world'
    assert joints['gripper_base_joint'].find('parent').attrib['link'] == 'gripper_mount'
    assert joints['left_finger_joint'].attrib['type'] == 'prismatic'
    assert joints['right_finger_joint'].attrib['type'] == 'prismatic'
    mimic = joints['right_finger_joint'].find('mimic')
    assert mimic is not None
    assert mimic.attrib['joint'] == 'left_finger_joint'


def test_provisional_geometry_and_parameters_remain_traceable():
    robot = expanded_gripper()
    joints = {joint.attrib['name']: joint for joint in robot.findall('joint')}

    for name in ('left_finger_joint', 'right_finger_joint'):
        assert joints[name].find('limit').attrib == {
            'lower': '-0.015',
            'upper': '0.005',
            'effort': '20',
            'velocity': '0.03',
        }

    tcp = joints['gripper_tcp_joint'].find('origin').attrib['xyz']
    assert tcp == '-0.0018 0 0.170536'

    masses = {
        link.attrib['name']: float(link.find('inertial/mass').attrib['value'])
        for link in robot.findall('link')
        if link.find('inertial/mass') is not None
    }
    assert masses == {
        'gripper_base': 0.48,
        'left_finger': 0.05,
        'right_finger': 0.05,
    }

    meshes = sorted(mesh.attrib['filename'] for mesh in robot.findall('.//mesh'))
    assert meshes == [
        'package://atom_gripper_description/meshes/generated/base.stl',
        'package://atom_gripper_description/meshes/generated/left_finger.stl',
        'package://atom_gripper_description/meshes/generated/right_finger.stl',
    ]

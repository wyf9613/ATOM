import subprocess
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory


def expanded_robot(*xacro_arguments):
    share = get_package_share_directory('atom_xarm_description')
    result = subprocess.run(
        ['xacro', f'{share}/urdf/uf850_atom.urdf.xacro', *xacro_arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout, ET.fromstring(result.stdout)


def test_uf850_and_gripper_are_composed_at_explicit_mount_frame():
    xml, robot = expanded_robot()
    links = {link.attrib['name'] for link in robot.findall('link')}
    joints = {joint.attrib['name']: joint for joint in robot.findall('joint')}

    assert {'world', 'link_base', 'link6', 'link_eef'} <= links
    assert {'gripper_mount', 'gripper_base', 'gripper_tcp'} <= links
    assert all(f'joint{index}' in joints for index in range(1, 7))
    mount = joints['gripper_mount_joint']
    assert mount.find('parent').attrib['link'] == 'link_eef'
    assert mount.find('child').attrib['link'] == 'gripper_mount'
    assert mount.find('origin').attrib == {'xyz': '0 0 0', 'rpy': '0 0 0'}
    assert 'ur3e' not in xml.lower()
    assert 'shoulder_pan_joint' not in joints


def test_mount_transform_is_overridable_without_modifying_vendor_model():
    _, robot = expanded_robot(
        'gripper_mount_xyz:=0.001 0.002 0.003',
        'gripper_mount_rpy:=0.1 0.2 0.3',
    )
    origin = robot.find("joint[@name='gripper_mount_joint']/origin")
    assert origin.attrib == {
        'xyz': '0.001 0.002 0.003',
        'rpy': '0.1 0.2 0.3',
    }


def test_combined_model_is_accepted_by_urdfdom():
    share = get_package_share_directory('atom_xarm_description')
    expanded = subprocess.run(
        ['xacro', f'{share}/urdf/uf850_atom.urdf.xacro'],
        check=True,
        capture_output=True,
        text=True,
    )
    checked = subprocess.run(
        ['check_urdf', '/dev/stdin'],
        input=expanded.stdout,
        capture_output=True,
        text=True,
    )
    assert checked.returncode == 0, checked.stderr

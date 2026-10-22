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
    assert {'gripper_mount', 'gripper_base', 'gripper_tcp', 'camera_bracket', 'd435i_body'} <= links
    assert all(f'joint{index}' in joints for index in range(1, 7))
    mount = joints['tool_flange_joint']
    assert mount.find('parent').attrib['link'] == 'link_eef'
    assert mount.find('child').attrib['link'] == 'tool_flange'
    assert mount.find('origin').attrib == {'xyz': '0 0 0', 'rpy': '0 0 0'}
    assert joints['gripper_mount_joint'].find('origin').attrib['xyz'] == '0 0 0.051964'
    assert 'ur3e' not in xml.lower()
    assert 'shoulder_pan_joint' not in joints


def test_mount_transform_is_overridable_without_modifying_vendor_model():
    _, robot = expanded_robot(
        'gripper_mount_xyz:=0.001 0.002 0.003',
        'gripper_mount_rpy:=0.1 0.2 0.3',
    )
    origin = robot.find("joint[@name='tool_flange_joint']/origin")
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


def test_current_camera_and_fake_review_defaults_are_installed():
    _, robot = expanded_robot()
    assert robot.find('ros2_control/hardware/plugin').text == 'fake_components/GenericSystem'
    body = robot.find("link[@name='d435i_body']")
    assert body.find('visual/geometry/box').attrib['size'] == '0.090000000 0.025000000 0.025050000'
    for mesh in robot.findall('.//mesh'):
        package, relative = mesh.attrib['filename'][len('package://'):].split('/', 1)
        from pathlib import Path
        assert (Path(get_package_share_directory(package)) / relative).is_file()

import math
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import pytest


def expand(kind='urdf', **mappings):
    try:
        from ament_index_python.packages import get_package_share_directory
    except ImportError:
        import sys
        root = Path(__file__).resolve().parents[4]
        sys.path.insert(0, str(root/'tools/gripper'))
        from export_description import expand as offline
        packages={n:root/'ros2_ws/src'/n for n in (
            'atom_mobile_description','atom_xarm_description','atom_gripper_description')}
        packages.update({n:root/'tmp/xarm_ros2'/n for n in ('xarm_description','xarm_moveit_config')})
        source=packages['atom_mobile_description']/kind/f'atom_mobile.{kind}.xacro'
        return ET.fromstring(offline(source,packages,{k:str(v) for k,v in mappings.items()}))
    share=Path(get_package_share_directory('atom_mobile_description'))
    result=subprocess.run(['xacro', str(share/kind/f'atom_mobile.{kind}.xacro'),
                           *[f'{k}:={v}' for k,v in mappings.items()]],check=True,capture_output=True,text=True)
    return ET.fromstring(result.stdout)


def test_mobile_tree_and_user_mount_are_not_fixed_to_world():
    robot=expand()
    links={x.attrib['name'] for x in robot.findall('link')}
    joints=robot.findall('joint')
    children=[j.find('child').attrib['link'] for j in joints]
    assert len(children)==len(set(children))
    assert links-set(children)=={'base_link'}
    assert {'base_top','arm_mount','link_base','gripper_tcp','d435i_body'}<=links
    assert 'world' not in links
    transforms={j.find('child').attrib['link']:(j.find('parent').attrib['link'],
                [float(v) for v in (j.find('origin') if j.find('origin') is not None else ET.Element('origin')).get('xyz','0 0 0').split()]) for j in joints}
    point=[0.,0.,0.];link='link_base'
    while link!='base_top':
        link,offset=transforms[link]
        point=[a+b for a,b in zip(point,offset)]
    assert point==pytest.approx([0.,0.,.805])
    assert robot.find('ros2_control/hardware/plugin').text=='fake_components/GenericSystem'
    assert not robot.findall('gazebo/plugin')


def test_deck_height_and_yaw_are_independent_of_pedestal_measurement():
    robot=expand(base_top_height=.19,arm_mount_yaw=math.pi/2)
    assert float(robot.find("joint[@name='base_top_joint']/origin").get('xyz').split()[2])==.19
    assert float(robot.find("joint[@name='world_joint']/origin").get('rpy').split()[2])==pytest.approx(math.pi/2)
    assert float(robot.find("joint[@name='pedestal_joint']/origin").get('xyz').split()[2])*2==.805


@pytest.mark.parametrize('prefix',['','arm_'])
def test_semantics_reference_real_links_and_preserve_arm_base_clearance(prefix):
    robot=expand(prefix=prefix);srdf=expand('srdf',prefix=prefix)
    links={x.attrib['name'] for x in robot.findall('link')}
    joints={x.attrib['name'] for x in robot.findall('joint')}
    for item in srdf.findall('.//link'): assert item.get('name') in links
    for item in srdf.findall('.//joint')+srdf.findall('passive_joint'): assert item.get('name') in joints
    for pair in srdf.findall('disable_collisions'):
        assert pair.get('link1') in links and pair.get('link2') in links
        if pair.get('link1')=='arm_pedestal': assert pair.get('link2')==prefix+'link_base'
    assert srdf.find('virtual_joint').get('child_link')=='base_link'

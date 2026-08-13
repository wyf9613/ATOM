import os
import subprocess
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory


def test_combined_description_expands_with_expected_chain():
    share = get_package_share_directory("atom_gripper_description")
    description_name = (
        "ur3e_atom_humble.urdf.xacro"
        if os.environ.get("ROS_DISTRO") == "humble"
        else "ur3e_atom.urdf.xacro"
    )
    description = f"{share}/urdf/{description_name}"
    result = subprocess.run(
        ["xacro", description], check=True, capture_output=True, text=True
    )
    robot = ET.fromstring(result.stdout)

    links = {element.attrib["name"] for element in robot.findall("link")}
    joints = {element.attrib["name"]: element for element in robot.findall("joint")}
    expected_links = {
        "base_link",
        "flange",
        "tool0",
        "gripper_mount",
        "gripper_base",
        "left_finger",
        "right_finger",
        "gripper_tcp",
    }
    assert expected_links <= links
    assert joints["gripper_mount_joint"].find("parent").attrib["link"] == "flange"
    assert joints["gripper_mount_joint"].find("child").attrib["link"] == "gripper_mount"
    assert joints["gripper_mount_joint"].find("origin").attrib["rpy"] == (
        "1.5707963268 0 1.5707963268"
    )
    assert joints["gripper_base_joint"].find("parent").attrib["link"] == "gripper_mount"
    assert joints["left_finger_joint"].attrib["type"] == "prismatic"
    assert joints["right_finger_joint"].attrib["type"] == "prismatic"
    assert joints["right_finger_joint"].find("mimic") is None

    gripper_meshes = [
        mesh.attrib["filename"]
        for mesh in robot.findall(".//mesh")
        if "atom_gripper_description" in mesh.attrib["filename"]
    ]
    assert sorted(gripper_meshes) == [
        "package://atom_gripper_description/meshes/generated/base.stl",
        "package://atom_gripper_description/meshes/generated/left_finger.stl",
        "package://atom_gripper_description/meshes/generated/right_finger.stl",
    ]

    finger_links = {
        link.attrib["name"]: link for link in robot.findall("link") if "finger" in link.attrib["name"]
    }
    expected_collision_origins = {
        "left_finger": "0.021 0.0005 0.154",
        "right_finger": "-0.024681 0.00045 0.154",
    }
    for name in ("left_finger", "right_finger"):
        size = finger_links[name].find("collision/geometry/box").attrib["size"]
        assert size == "0.006 0.020 0.020"
        origin = finger_links[name].find("collision/origin").attrib["xyz"]
        assert origin == expected_collision_origins[name]

    assert joints["left_finger_joint"].find("limit").attrib == {
        "lower": "-0.015",
        "upper": "0.005",
        "effort": "20",
        "velocity": "0.03",
    }
    assert joints["right_finger_joint"].find("limit").attrib == {
        "lower": "-0.015",
        "upper": "0.005",
        "effort": "20",
        "velocity": "0.03",
    }

    gripper_mass = sum(
        float(robot.find(f"link[@name='{name}']/inertial/mass").attrib["value"])
        for name in ("gripper_base", "left_finger", "right_finger")
    )
    assert abs(gripper_mass - 0.58) < 1e-12

    expected_arm_efforts = {
        "shoulder_pan_joint": 54.0,
        "shoulder_lift_joint": 54.0,
        "elbow_joint": 28.0,
        "wrist_1_joint": 9.0,
        "wrist_2_joint": 9.0,
        "wrist_3_joint": 9.0,
    }
    controller_caps = {
        plugin.find("joint_name").text: float(plugin.find("cmd_max").text)
        for plugin in robot.findall("gazebo/plugin")
        if plugin.find("joint_name") is not None
    }
    for joint, expected_effort in expected_arm_efforts.items():
        assert float(joints[joint].find("limit").attrib["effort"]) == expected_effort
        assert controller_caps[joint] == expected_effort


def test_ros2_control_backend_exposes_arm_and_gripper_joints():
    share = get_package_share_directory("atom_gripper_description")
    description_name = (
        "ur3e_atom_humble.urdf.xacro"
        if os.environ.get("ROS_DISTRO") == "humble"
        else "ur3e_atom.urdf.xacro"
    )
    result = subprocess.run(
        ["xacro", f"{share}/urdf/{description_name}", "control_backend:=ros2_control"],
        check=True,
        capture_output=True,
        text=True,
    )
    robot = ET.fromstring(result.stdout)

    control = robot.find("ros2_control")
    assert control is not None
    assert control.find("hardware/plugin").text in {
        "gz_ros2_control/GazeboSimSystem",
        "ign_ros2_control/IgnitionSystem",
    }
    controlled_joints = {joint.attrib["name"] for joint in control.findall("joint")}
    assert controlled_joints == {
        "shoulder_pan_joint",
        "shoulder_lift_joint",
        "elbow_joint",
        "wrist_1_joint",
        "wrist_2_joint",
        "wrist_3_joint",
        "left_finger_joint",
        "right_finger_joint",
    }
    for joint in control.findall("joint"):
        assert [interface.attrib["name"] for interface in joint.findall("command_interface")] == [
            "position"
        ]

    plugin_names = {
        plugin.attrib["name"] for plugin in robot.findall("gazebo/plugin")
    }
    assert not any("JointPositionController" in name for name in plugin_names)
    assert any("ROS2ControlPlugin" in name for name in plugin_names)


def test_grasp_world_contains_provisional_contact_baseline():
    share = get_package_share_directory("atom_gripper_description")
    world_name = (
        "atom_grasp_fortress.sdf"
        if os.environ.get("ROS_DISTRO") == "humble"
        else "atom_grasp.sdf"
    )
    world = ET.parse(f"{share}/worlds/{world_name}").getroot().find("world")
    assert world.find("gravity").text == "0 0 -9.81"

    models = {model.attrib["name"]: model for model in world.findall("model")}
    cuvette = models["cuvette"]
    assert cuvette.find("link/inertial/mass").text == "0.010"
    assert (
        cuvette.find("link/collision/geometry/box/size").text
        == "0.014 0.014 0.045"
    )
    assert (
        cuvette.find("link/collision/surface/friction/ode/mu").text == "0.88"
    )
    assert models["cuvette_support"].find("static").text == "true"
    if os.environ.get("ROS_DISTRO") == "humble":
        world_plugins = {plugin.attrib["name"] for plugin in world.findall("plugin")}
        assert "ignition::gazebo::systems::SceneBroadcaster" in world_plugins
    else:
        assert cuvette.find("plugin").attrib["name"] == (
            "gz::sim::systems::PosePublisher"
        )


def test_both_gazebo_world_variants_are_well_formed():
    share = get_package_share_directory("atom_gripper_description")
    harmonic_world = ET.parse(f"{share}/worlds/atom_grasp.sdf").getroot().find(
        "world"
    )
    harmonic_cuvette = harmonic_world.find("model[@name='cuvette']")
    assert harmonic_cuvette.find("plugin").attrib["name"] == (
        "gz::sim::systems::PosePublisher"
    )

    fortress_world = ET.parse(
        f"{share}/worlds/atom_grasp_fortress.sdf"
    ).getroot().find("world")
    fortress_plugins = {
        plugin.attrib["name"] for plugin in fortress_world.findall("plugin")
    }
    assert "ignition::gazebo::systems::SceneBroadcaster" in fortress_plugins


def test_logical_grasp_is_explicit_and_uses_reduced_collision():
    share = get_package_share_directory("atom_gripper_description")
    description_name = (
        "ur3e_atom_humble.urdf.xacro"
        if os.environ.get("ROS_DISTRO") == "humble"
        else "ur3e_atom.urdf.xacro"
    )
    result = subprocess.run(
        [
            "xacro",
            f"{share}/urdf/{description_name}",
            "control_backend:=ros2_control",
            "enable_logical_grasp:=true",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    robot = ET.fromstring(result.stdout)
    detachable = next(
        plugin
        for plugin in robot.findall("gazebo/plugin")
        if "DetachableJoint" in plugin.attrib["name"]
    )
    assert detachable.find("parent_link").text == "wrist_3_link"
    assert detachable.find("child_model").text == "cuvette"
    assert detachable.find("child_link").text == "body"
    assert detachable.find("attach_topic").text == "/atom_grasp/attach"
    assert detachable.find("detach_topic").text == "/atom_grasp/detach"

    for world_name in ("atom_logical_grasp.sdf", "atom_logical_grasp_fortress.sdf"):
        world = ET.parse(f"{share}/worlds/{world_name}").getroot().find("world")
        cuvette = world.find("model[@name='cuvette']")
        assert cuvette.find("link/collision/geometry/box/size").text == (
            "0.004 0.004 0.035"
        )
        assert world.find("model[@name='cuvette_target_support']") is not None

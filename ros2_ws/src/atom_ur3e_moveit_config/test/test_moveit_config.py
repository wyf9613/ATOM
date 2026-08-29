import xml.etree.ElementTree as ET

import yaml
from ament_index_python.packages import get_package_share_directory


ARM_JOINTS = {
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint",
}
GRIPPER_JOINTS = {"left_finger_joint", "right_finger_joint"}


def config_path(filename):
    share = get_package_share_directory("atom_ur3e_moveit_config")
    return f"{share}/config/{filename}"


def test_srdf_keeps_arm_and_gripper_modular():
    robot = ET.parse(config_path("ur3e_atom.srdf")).getroot()
    groups = {group.attrib["name"]: group for group in robot.findall("group")}
    arm_chain = groups["ur_manipulator"].find("chain")
    assert arm_chain.attrib == {"base_link": "base_link", "tip_link": "gripper_tcp"}
    assert {joint.attrib["name"] for joint in groups["atom_gripper"].findall("joint")} == (
        GRIPPER_JOINTS
    )
    home = robot.find("group_state[@name='home']")
    assert {joint.attrib["name"] for joint in home.findall("joint")} == ARM_JOINTS


def test_moveit_controllers_match_ros2_control_configuration():
    with open(config_path("moveit_controllers.yaml"), encoding="utf-8") as stream:
        moveit = yaml.safe_load(stream)["moveit_simple_controller_manager"]
    description_share = get_package_share_directory("atom_gripper_description")
    with open(
        f"{description_share}/config/ros2_controllers.yaml", encoding="utf-8"
    ) as stream:
        controllers = yaml.safe_load(stream)

    assert set(moveit["arm_controller"]["joints"]) == ARM_JOINTS
    assert set(moveit["gripper_controller"]["joints"]) == GRIPPER_JOINTS
    assert set(controllers["arm_controller"]["ros__parameters"]["joints"]) == ARM_JOINTS
    assert set(controllers["gripper_controller"]["ros__parameters"]["joints"]) == (
        GRIPPER_JOINTS
    )


def test_provisional_planning_limits_cover_every_commanded_joint():
    with open(config_path("joint_limits.yaml"), encoding="utf-8") as stream:
        limits = yaml.safe_load(stream)["joint_limits"]
    assert set(limits) == ARM_JOINTS | GRIPPER_JOINTS
    assert all(value["has_velocity_limits"] for value in limits.values())
    assert all(value["has_acceleration_limits"] for value in limits.values())

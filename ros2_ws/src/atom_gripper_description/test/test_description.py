import subprocess
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory


def test_combined_description_expands_with_expected_chain():
    share = get_package_share_directory("atom_gripper_description")
    description = f"{share}/urdf/ur3e_atom.urdf.xacro"
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


def test_grasp_world_contains_provisional_contact_baseline():
    share = get_package_share_directory("atom_gripper_description")
    world = ET.parse(f"{share}/worlds/atom_grasp.sdf").getroot().find("world")
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
    assert cuvette.find("plugin").attrib["name"] == "gz::sim::systems::PosePublisher"

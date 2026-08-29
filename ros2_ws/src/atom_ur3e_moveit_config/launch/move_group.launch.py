import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def build_moveit_config():
    description_share = get_package_share_directory("atom_gripper_description")
    description_name = (
        "ur3e_atom_humble.urdf.xacro"
        if os.environ.get("ROS_DISTRO") == "humble"
        else "ur3e_atom.urdf.xacro"
    )
    description_file = os.path.join(description_share, "urdf", description_name)
    return (
        MoveItConfigsBuilder(
            "ur3e_atom", package_name="atom_ur3e_moveit_config"
        )
        .robot_description(
            file_path=description_file,
            mappings={"control_backend": "ros2_control"},
        )
        .robot_description_semantic(file_path="config/ur3e_atom.srdf")
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .joint_limits(file_path="config/joint_limits.yaml")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(default_planning_pipeline="ompl", pipelines=["ompl"])
        .to_moveit_configs()
    )


def generate_launch_description():
    moveit_config = build_moveit_config()
    move_group = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {
                "use_sim_time": True,
                "allow_trajectory_execution": True,
                "publish_robot_description": True,
                "publish_robot_description_semantic": True,
                "publish_planning_scene": True,
                "publish_geometry_updates": True,
                "publish_state_updates": True,
                "publish_transforms_updates": True,
            },
        ],
    )
    return LaunchDescription([move_group])

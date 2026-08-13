import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def launch_setup(context):
    headless = LaunchConfiguration("headless").perform(context).lower() == "true"
    world_name = LaunchConfiguration("world").perform(context)
    gz_args = "-r -s" if headless else "-r"
    world = PathJoinSubstitution(
        [
            FindPackageShare("atom_gripper_description"),
            "worlds",
            LaunchConfiguration("world"),
        ]
    )
    description_file = PathJoinSubstitution(
        [FindPackageShare("atom_gripper_description"), "urdf", "ur3e_atom.urdf.xacro"]
    )
    robot_description = ParameterValue(
        Command(
            [
                FindExecutable(name="xacro"),
                " ",
                description_file,
                " initial_finger_position:=",
                LaunchConfiguration("initial_finger_position"),
            ]
        ),
        value_type=str,
    )
    package_share_parent = os.path.dirname(
        get_package_share_directory("atom_gripper_description")
    )
    bridge_arguments = [
        "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
        "/model/ur3e_atom/joint_state@sensor_msgs/msg/JointState[gz.msgs.Model",
        "/model/ur3e_atom/joint/shoulder_pan_joint/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double",
        "/model/ur3e_atom/joint/shoulder_lift_joint/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double",
        "/model/ur3e_atom/joint/elbow_joint/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double",
        "/model/ur3e_atom/joint/wrist_1_joint/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double",
        "/model/ur3e_atom/joint/wrist_2_joint/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double",
        "/model/ur3e_atom/joint/wrist_3_joint/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double",
        "/model/ur3e_atom/joint/left_finger_joint/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double",
        "/model/ur3e_atom/joint/right_finger_joint/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double",
    ]
    bridge_remappings = [
        ("/model/ur3e_atom/joint_state", "/joint_states"),
    ]
    if world_name == "atom_grasp.sdf":
        bridge_arguments.append(
            "/model/cuvette/pose@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V"
        )
        bridge_remappings.append(("/model/cuvette/pose", "/cuvette/pose"))

    return [
        AppendEnvironmentVariable(
            name="GZ_SIM_RESOURCE_PATH", value=package_share_parent
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"])
            ),
            launch_arguments={"gz_args": [gz_args, " ", world]}.items(),
        ),
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            parameters=[{"robot_description": robot_description, "use_sim_time": True}],
            output="screen",
        ),
        Node(
            package="ros_gz_sim",
            executable="create",
            arguments=["-topic", "robot_description", "-name", "ur3e_atom", "-allow_renaming", "false"],
            output="screen",
        ),
        Node(
            package="ros_gz_bridge",
            executable="parameter_bridge",
            arguments=bridge_arguments,
            remappings=bridge_remappings,
            output="screen",
        ),
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("headless", default_value="false"),
            DeclareLaunchArgument("world", default_value="atom_empty.sdf"),
            DeclareLaunchArgument("initial_finger_position", default_value="0.0"),
            OpaqueFunction(function=launch_setup),
        ]
    )

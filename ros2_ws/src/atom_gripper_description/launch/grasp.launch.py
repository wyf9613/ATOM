from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("atom_gripper_description"), "launch", "sim.launch.py"]
            )
        ),
        launch_arguments={
            "headless": LaunchConfiguration("headless"),
            "world": "atom_grasp.sdf",
            "initial_finger_position": "0.0",
        }.items(),
    )
    automatic_test = TimerAction(
        period=10.0,
        actions=[
            Node(
                package="atom_gripper_description",
                executable="grasp_lift_test.py",
                output="screen",
                condition=IfCondition(LaunchConfiguration("run_test")),
            )
        ],
    )
    return LaunchDescription(
        [
            DeclareLaunchArgument("headless", default_value="false"),
            DeclareLaunchArgument("run_test", default_value="false"),
            simulation,
            automatic_test,
        ]
    )

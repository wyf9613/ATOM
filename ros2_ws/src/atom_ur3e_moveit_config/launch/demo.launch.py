from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    EmitEvent,
    IncludeLaunchDescription,
    OpaqueFunction,
    RegisterEventHandler,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def launch_setup(context):
    grasp_mode = LaunchConfiguration("grasp_mode").perform(context)
    if grasp_mode not in {"logical", "physical"}:
        raise RuntimeError("grasp_mode must be either 'logical' or 'physical'")

    description_launch = PathJoinSubstitution(
        [FindPackageShare("atom_gripper_description"), "launch", "sim.launch.py"]
    )
    move_group_launch = PathJoinSubstitution(
        [FindPackageShare("atom_ur3e_moveit_config"), "launch", "move_group.launch.py"]
    )
    task_node = Node(
        package="atom_manipulation",
        executable="grasp_task_node",
        output="screen",
        parameters=[{"use_sim_time": True, "grasp_mode": grasp_mode}],
        condition=IfCondition(LaunchConfiguration("run_task")),
    )
    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(description_launch),
            launch_arguments={
                "headless": LaunchConfiguration("headless"),
                "world": (
                    "atom_logical_grasp.sdf"
                    if grasp_mode == "logical"
                    else "atom_grasp.sdf"
                ),
                "initial_finger_position": "0.0",
                "control_backend": "ros2_control",
                "logical_grasp": "true" if grasp_mode == "logical" else "false",
            }.items(),
        ),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(move_group_launch)),
        TimerAction(
            period=12.0,
            actions=[task_node],
        ),
        RegisterEventHandler(
            OnProcessExit(
                target_action=task_node,
                on_exit=[EmitEvent(event=Shutdown(reason="grasp task finished"))],
            )
        ),
        Node(
            package="rviz2",
            executable="rviz2",
            arguments=[
                "-d",
                PathJoinSubstitution(
                    [FindPackageShare("atom_ur3e_moveit_config"), "rviz", "atom_moveit.rviz"]
                ),
            ],
            parameters=[{"use_sim_time": True}],
            output="screen",
            condition=IfCondition(LaunchConfiguration("rviz")),
        ),
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("grasp_mode", default_value="logical"),
            DeclareLaunchArgument("headless", default_value="false"),
            DeclareLaunchArgument("rviz", default_value="false"),
            DeclareLaunchArgument("run_task", default_value="true"),
            OpaqueFunction(function=launch_setup),
        ]
    )

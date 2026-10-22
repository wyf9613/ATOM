"""Opt-in CAN driver boundary, remapped exclusively to the velocity gate.

Does not start an arm, reset faults, set CAN permissions or launch a second TF tree.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from pathlib import Path


def setup(context):
    g = lambda n: LaunchConfiguration(n).perform(context)
    if g('enable_driver') != 'true':
        raise ValueError('Explicit enable_driver:=true required for CAN connection')
    return [Node(package='tracer_base', executable='tracer_base_node', output='screen',
                 parameters=[{'port_name': g('can_interface'), 'base_frame': 'base_link',
                              'odom_frame': 'odom', 'publish_odom_tf': False,
                              'odom_linear_scale': float(g('odom_linear_scale')),
                              'odom_angular_scale': float(g('odom_angular_scale'))}],
                 remappings=[('/cmd_vel', '/atom/base/cmd_vel')]),
            Node(package='robot_localization', executable='ekf_node', output='screen',
                 parameters=[str(Path(get_package_share_directory('atom_base'))/'config/ekf.yaml')])]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('enable_driver', default_value='false'),
        DeclareLaunchArgument('can_interface', default_value='can0'),
        # Neutral calibration until measurements for the current load are verified.
        DeclareLaunchArgument('odom_linear_scale', default_value='1.0'),
        DeclareLaunchArgument('odom_angular_scale', default_value='1.0'),
        OpaqueFunction(function=setup),
    ])

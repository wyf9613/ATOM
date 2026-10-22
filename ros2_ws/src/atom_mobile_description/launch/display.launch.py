"""Review model only: no drivers, controller enable, arm search or motion."""
from pathlib import Path

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def setup(context):
    names = ('base_top_height', 'pedestal_height', 'arm_mount_yaw')
    mappings = {n: LaunchConfiguration(n).perform(context) for n in names}
    import math
    values = {n: float(v) for n, v in mappings.items()}
    if not all(math.isfinite(v) for v in values.values()) or any(values[n] <= 0 for n in names[:2]):
        raise ValueError('Mount heights must be finite and positive; yaw must be finite')
    model = Path(get_package_share_directory('atom_mobile_description')) / 'urdf/atom_mobile.urdf.xacro'
    description = xacro.process_file(str(model), mappings=mappings).toxml()
    return [
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': ParameterValue(description, value_type=str), 'use_sim_time': LaunchConfiguration('use_sim_time')}]),
        Node(package='joint_state_publisher', executable='joint_state_publisher',
             condition=IfCondition(LaunchConfiguration('publish_review_joints')),
             parameters=[{'robot_description': ParameterValue(description, value_type=str), 'use_sim_time': LaunchConfiguration('use_sim_time')}]),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('base_top_height', default_value='0.15'),
        DeclareLaunchArgument('pedestal_height', default_value='0.805'),
        DeclareLaunchArgument('arm_mount_yaw', default_value='0.0'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('publish_review_joints', default_value='true'),
        OpaqueFunction(function=setup),
    ])

#!/usr/bin/env python3

"""Launch the arm-only simulator and configurable transfer target publisher."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    package_share = get_package_share_directory('atom_xarm_sim')
    arm_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(package_share, 'launch', 'uf850_arm_only.launch.py')
        )
    )
    target_config = os.path.join(
        package_share, 'config', 'transfer_targets.yaml'
    )
    target_publisher = Node(
        package='atom_xarm_sim',
        executable='target_publisher',
        name='target_publisher',
        output='screen',
        parameters=[target_config],
    )
    return LaunchDescription([arm_launch, target_publisher])

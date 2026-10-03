from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('port', default_value='/dev/ttyUSB0'),
        Node(package='atom_gripper_hardware', executable='sensor_bridge',
             parameters=[{'port': LaunchConfiguration('port'), 'sensor_address': 20}],
             output='screen')])

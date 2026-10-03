from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('port',default_value='/dev/ttyUSB0'),
        DeclareLaunchArgument('enable_motion',default_value='false'),
        Node(package='atom_gripper_hardware',executable='hardware_bridge',output='screen',parameters=[{
            'port':LaunchConfiguration('port'),
            'enable_motion':ParameterValue(LaunchConfiguration('enable_motion'),value_type=bool)}])])

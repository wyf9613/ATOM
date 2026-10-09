"""Camera-only D435i bringup; no arm/task/controller launch."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    vendor = Path(get_package_share_directory('realsense2_camera'))
    return LaunchDescription([
        DeclareLaunchArgument('serial_no', default_value="''"),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(vendor / 'launch/rs_launch.py')),
            launch_arguments={
                'camera_name': 'wrist_camera', 'camera_namespace': 'atom',
                'serial_no': LaunchConfiguration('serial_no'), 'device_type': 'D435i',
                'enable_color': 'true', 'enable_depth': 'true',
                'rgb_camera.color_profile': '640,480,30',
                'depth_module.depth_profile': '640,480,30',
                'align_depth.enable': 'true', 'enable_sync': 'true',
                'enable_gyro': 'true', 'enable_accel': 'true',
                'unite_imu_method': '2', 'publish_tf': 'true',
                'pointcloud.enable': 'false', 'initial_reset': 'false',
                'wait_for_device_timeout': '10.0',
            }.items()),
    ])

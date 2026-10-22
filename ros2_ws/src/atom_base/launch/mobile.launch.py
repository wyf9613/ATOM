"""Integrated review/fake or externally supplied base. No physical arm control."""
from pathlib import Path
import tempfile
import yaml

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def setup(context):
    g = lambda n: LaunchConfiguration(n).perform(context)
    share = Path(get_package_share_directory('atom_base'))
    backend = g('backend')
    if backend not in {'review', 'fake', 'external'}:
        raise ValueError('backend must be review, fake or external')
    simulated = g('use_sim_time') == 'true'
    if g('gripper') == 'true' and (simulated or backend != 'external'):
        raise ValueError('Physical gripper requires external backend and system clock')
    if backend == 'fake' and simulated:
        raise ValueError('Ideal fake fixture uses wall clock; use_sim_time must be false')
    description = Path(get_package_share_directory('atom_mobile_description'))
    actions = [IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(description/'launch/display.launch.py')),
        launch_arguments={
            'base_top_height': g('base_top_height'), 'pedestal_height': g('pedestal_height'),
            'arm_mount_yaw': g('arm_mount_yaw'), 'use_sim_time': g('use_sim_time'),
            'publish_review_joints': 'false' if backend == 'external' else 'true',
        }.items()),
        Node(package='atom_base', executable='velocity_gate', output='screen', parameters=[{'use_sim_time': simulated}]),
    ]
    if backend == 'fake':
        actions.append(Node(package='atom_base', executable='kinematic_fixture', output='screen'))
    if g('navigation') == 'true':
        if backend != 'external':
            raise ValueError('Nav2 requires external odometry/scan; fake is an interface fixture')
        config = yaml.safe_load((share/'config/nav2_real.yaml').read_text())
        config['planner_server']['ros__parameters']['GridBased']['lattice_filepath'] = str(share/'config/lattice_straight_rotate.json')
        config['bt_navigator']['ros__parameters']['default_nav_to_pose_bt_xml'] = str(share/'config/bt_nav_to_pose_clear_wait.xml')
        config['bt_navigator']['ros__parameters']['default_nav_through_poses_bt_xml'] = str(share/'config/bt_nav_through_poses_clear_wait.xml')
        with tempfile.NamedTemporaryFile(mode='w', prefix='atom_nav2_', suffix='.yaml', delete=False) as f:
            yaml.safe_dump(config, f, sort_keys=False)
            params = f.name
        # Compose only the required standard servers. Recent Jazzy bringup also
        # starts route/docking servers, which are outside this integration scope.
        def clock_parameters(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == 'use_sim_time': value[key] = simulated
                    else: clock_parameters(child)
        clock_parameters(config)
        config['map_server']['ros__parameters']['yaml_filename'] = g('map')
        with open(params, 'w') as stream:
            yaml.safe_dump(config, stream, sort_keys=False)
        servers = (
            ('nav2_map_server', 'map_server', 'map_server', []),
            ('nav2_amcl', 'amcl', 'amcl', []),
            ('nav2_controller', 'controller_server', 'controller_server', [('cmd_vel','/atom/base/nav_raw_cmd_vel')]),
            ('nav2_smoother', 'smoother_server', 'smoother_server', []),
            ('nav2_planner', 'planner_server', 'planner_server', []),
            ('nav2_behaviors', 'behavior_server', 'behavior_server', [('cmd_vel','/atom/base/nav_raw_cmd_vel')]),
            ('nav2_velocity_smoother', 'velocity_smoother', 'velocity_smoother',
             [('cmd_vel','/atom/base/nav_raw_cmd_vel'),('cmd_vel_smoothed','/atom/base/nav_smoothed_cmd_vel')]),
            ('nav2_collision_monitor', 'collision_monitor', 'collision_monitor', []),
            ('nav2_bt_navigator', 'bt_navigator', 'bt_navigator', []),
            ('nav2_waypoint_follower', 'waypoint_follower', 'waypoint_follower', []),
        )
        for package, executable, name, remappings in servers:
            actions.append(Node(package=package, executable=executable, name=name, output='screen',
                                parameters=[params], remappings=remappings))
        for label, names in (
            ('localization', ['map_server','amcl']),
            ('navigation', [s[2] for s in servers[2:]]),
        ):
            actions.append(Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
                                name=f'lifecycle_manager_{label}', output='screen',
                                parameters=[{'use_sim_time': simulated, 'autostart': True, 'node_names': names}]))
    if backend != 'review':
        actions.append(Node(package='atom_base', executable='mission_manager', output='screen', parameters=[{
            'use_sim_time': simulated, 'points_yaml': str(share/'config/points.yaml'),
            'relocalize_at_home': False, 'relocalize_on_start': False, 'split_corners': False,
        }]))
    if g('web') == 'true':
        actions.append(Node(package='atom_base', executable='task_bridge', output='screen', parameters=[{
            'use_sim_time': simulated, 'map_yaml': g('map'), 'base_frame': 'base_link',
            'port': int(g('port')),
        }]))
    if g('fine_adjust') == 'true':
        if backend == 'review':
            raise ValueError('Fine adjustment requires odometry/scan and calibrated external camera TF')
        for executable in ('tag_goal_publisher', 'fine_adjust_server'):
            actions.append(Node(package='atom_base', executable=executable, output='screen',
                                parameters=[str(share/'config/fine_adjust.yaml'), {'use_sim_time': simulated}]))
    if g('gripper') == 'true':
        actions.append(Node(package='atom_gripper_hardware', executable='hardware_bridge', output='screen', parameters=[{
            'port': g('gripper_port'), 'enable_motion': g('gripper_motion') == 'true',
            'require_system_stop_state': True, 'use_sim_time': False,
        }]))
    return actions


def generate_launch_description():
    share = Path(get_package_share_directory('atom_base'))
    defaults = {
        'backend': 'review', 'navigation': 'false', 'web': 'false', 'port': '8080',
        'fine_adjust': 'false', 'gripper': 'false', 'gripper_motion': 'false',
        'gripper_port': '/dev/ttyUSB0', 'use_sim_time': 'false',
        'base_top_height': '0.15', 'pedestal_height': '0.805', 'arm_mount_yaw': '0.0',
        'map': str(share/'maps/robotics_lab_2026-10-07.yaml'),
    }
    return LaunchDescription([*[DeclareLaunchArgument(n, default_value=v) for n,v in defaults.items()],
                              OpaqueFunction(function=setup)])

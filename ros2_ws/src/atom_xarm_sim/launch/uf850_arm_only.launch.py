#!/usr/bin/env python3

"""Launch the bare six-axis UFactory 850 in server-only Gazebo with MoveIt."""

import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnProcessExit, OnProcessStart
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from uf_ros_lib.moveit_configs_builder import MoveItConfigsBuilder
from uf_ros_lib.uf_robot_utils import generate_ros2_control_params_temp_file


def launch_setup(context):
    # Keep this baseline deliberately arm-only. The ATOM gripper is integrated
    # and tested on a separate branch/path so controller and collision failures
    # cannot be hidden inside the bare-arm acceptance test.
    robot_type = 'uf850'
    dof = '6'
    ros2_control_params = generate_ros2_control_params_temp_file(
        os.path.join(
            get_package_share_directory('xarm_controller'),
            'config',
            'uf850_controllers.yaml',
        ),
        prefix='',
        add_gripper=False,
        add_bio_gripper=False,
        ros_namespace='',
        update_rate=1000,
        use_sim_time=True,
        robot_type=robot_type,
    )

    moveit_config = MoveItConfigsBuilder(
        context=context,
        controllers_name='fake_controllers',
        dof=dof,
        robot_type=robot_type,
        prefix='',
        hw_ns='ufactory',
        limited=True,
        effort_control=False,
        velocity_control=False,
        model1300=False,
        robot_sn='',
        attach_to='world',
        attach_xyz='"0 0 0"',
        attach_rpy='"0 0 0"',
        mesh_suffix='stl',
        kinematics_suffix='',
        ros2_control_plugin='gz_ros2_control/GazeboSimSystem',
        ros2_control_params=ros2_control_params,
        gripper_version='G1',
        add_gripper=False,
        add_vacuum_gripper=False,
        add_bio_gripper=False,
        add_realsense_d435i=False,
        add_d435i_links=True,
        add_other_geometry=False,
        geometry_type='box',
        geometry_mass=0.1,
        geometry_height=0.1,
        geometry_radius=0.1,
        geometry_length=0.1,
        geometry_width=0.1,
        geometry_mesh_filename='',
        geometry_mesh_origin_xyz='"0 0 0"',
        geometry_mesh_origin_rpy='"0 0 0"',
        geometry_mesh_tcp_xyz='"0 0 0"',
        geometry_mesh_tcp_rpy='"0 0 0"',
    ).to_moveit_configs()
    moveit_dict = moveit_config.to_dict()

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[
            {'use_sim_time': True},
            {'robot_description': moveit_dict['robot_description']},
        ],
    )

    world = str(Path(get_package_share_directory('xarm_gazebo')) / 'worlds' / 'table_gz.world')
    gazebo_server = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={
            'gz_args': (
                f'-s -r -v 3 {world} '
                '--physics-engine gz-physics-bullet-featherstone-plugin'
            ),
        }.items(),
    )

    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'UF_ROBOT',
            '-x', '-0.2',
            '-y', '-0.54',
            '-z', '1.021',
            '-Y', '1.571',
        ],
        parameters=[{'use_sim_time': True}],
    )

    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen',
    )

    controller_spawners = [
        Node(
            package='controller_manager',
            executable='spawner',
            output='screen',
            arguments=[name, '--controller-manager', '/controller_manager'],
            parameters=[{'use_sim_time': True}],
        )
        for name in ('joint_state_broadcaster', 'uf850_traj_controller')
    ]

    move_group = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        output='screen',
        parameters=[moveit_dict, {'use_sim_time': True}],
    )

    static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_transform_publisher',
        output='screen',
        arguments=['0', '0', '0', '0', '0', '0', 'world', 'link_base'],
        parameters=[{'use_sim_time': True}],
    )

    return [
        RegisterEventHandler(
            OnProcessStart(
                target_action=robot_state_publisher,
                on_start=[gazebo_server, spawn_robot, clock_bridge],
            )
        ),
        RegisterEventHandler(
            OnProcessExit(
                target_action=spawn_robot,
                on_exit=controller_spawners,
            )
        ),
        robot_state_publisher,
        static_tf,
        move_group,
    ]


def generate_launch_description():
    return LaunchDescription([OpaqueFunction(function=launch_setup)])

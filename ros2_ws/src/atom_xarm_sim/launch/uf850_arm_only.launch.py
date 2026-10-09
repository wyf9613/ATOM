#!/usr/bin/env python3

"""Launch the bare six-axis UFactory 850 in server-only Gazebo with MoveIt."""

import os
from pathlib import Path
import tempfile
import math
import xacro
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    OpaqueFunction,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit, OnProcessStart
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from uf_ros_lib.moveit_configs_builder import MoveItConfigsBuilder
from uf_ros_lib.uf_robot_utils import generate_ros2_control_params_temp_file

from atom_xarm_sim.camera_experiment import (
    add_wrist_camera, allow_wrist_camera_self_collisions, experiment_world, write_tag_rack,
    write_two_level_shelf, write_transparent_tube, SLOT_Y_M, SOURCE_SLOT_INDEX,
)


def launch_setup(context):
    # Keep this baseline deliberately arm-only. The ATOM gripper is integrated
    # and tested on a separate branch/path so controller and collision failures
    # cannot be hidden inside the bare-arm acceptance test.
    robot_type = 'uf850'
    dof = '6'
    actuator_model = LaunchConfiguration('actuator_model').perform(context)
    camera_mode = LaunchConfiguration('camera_mode').perform(context)
    atom_tool = LaunchConfiguration('atom_tool').perform(context) == 'v2'
    demo_gripper = LaunchConfiguration('demo_gripper').perform(context).lower() == 'true'
    if atom_tool:
        demo_gripper = False
    scene_fixtures = LaunchConfiguration('scene_fixtures').perform(context).lower() == 'true'
    fixture_group = LaunchConfiguration('fixture_group').perform(context)
    show_gui = LaunchConfiguration('gui').perform(context).lower() == 'true'
    rack_dx_m = float(LaunchConfiguration('rack_dx_m').perform(context))
    rack_dy_m = float(LaunchConfiguration('rack_dy_m').perform(context))
    rack_dyaw_rad = float(LaunchConfiguration('rack_dyaw_rad').perform(context))
    if not all(math.isfinite(value) for value in (rack_dx_m, rack_dy_m, rack_dyaw_rad)):
        raise ValueError('rack perturbations must be finite')
    if abs(rack_dx_m) > 0.05 or abs(rack_dy_m) > 0.05 or abs(rack_dyaw_rad) > 0.2:
        raise ValueError('rack perturbations exceed the provisional experiment bounds')
    if actuator_model == 'nominal':
        controller_config = os.path.join(
            get_package_share_directory('atom_xarm_dynamics'),
            'config',
            'uf850_dynamic_controllers.yaml',
        )
        update_rate = 250
        physics_engine = 'gz-physics-dartsim-plugin'
    else:
        controller_config = os.path.join(
            get_package_share_directory('xarm_controller'),
            'config',
            'uf850_controllers.yaml',
        )
        update_rate = 1000
        physics_engine = 'gz-physics-bullet-featherstone-plugin'

    ros2_control_params = generate_ros2_control_params_temp_file(
        controller_config,
        prefix='',
        add_gripper=demo_gripper,
        add_bio_gripper=False,
        ros_namespace='',
        update_rate=update_rate,
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
        # The vendor Xacro only inserts the Gazebo system plugin when this
        # exact value is used. The nominal mode swaps only the ros2_control
        # hardware class after expansion, leaving the vendor source untouched.
        ros2_control_plugin='gz_ros2_control/GazeboSimSystem',
        ros2_control_params=ros2_control_params,
        gripper_version='G1',
        add_gripper=demo_gripper,
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
    if atom_tool:
        description_share = Path(get_package_share_directory('atom_xarm_description'))
        moveit_dict['robot_description'] = xacro.process_file(
            str(description_share / 'urdf/uf850_atom.urdf.xacro'), mappings={
                'ros2_control_plugin': 'gz_ros2_control/GazeboSimSystem',
                'ros2_control_params': ros2_control_params,
                'load_gazebo_plugin': 'true',
                'camera_enabled': 'true' if camera_mode != 'none' else 'false',
                'camera_nominal_extrinsics': 'true',
            }).toxml()
        moveit_dict['robot_description_semantic'] = xacro.process_file(
            str(description_share / 'srdf/uf850_atom.srdf.xacro')).toxml()
        robot = ET.fromstring(moveit_dict['robot_description'])
        # V2 starts with the wrist pitched forward; vendor encoder zeros stay unchanged.
        for joint in robot.findall('ros2_control/joint'):
            position = joint.find("state_interface[@name='position']")
            if position is not None:
                initial = ET.SubElement(position, 'param', name='initial_value')
                initial.text = str(math.pi / 2 if joint.get('name') == 'joint5' else 0.0)
        # Observation-only simulation: hold uncalibrated fingers at CAD zero.
        # This does not simulate servo control or physical grasping.
        for name in ('left_finger_joint', 'right_finger_joint'):
            joint = robot.find(f"joint[@name='{name}']")
            joint.set('type', 'fixed')
            for tag in ('axis', 'limit', 'dynamics', 'mimic'):
                element = joint.find(tag)
                if element is not None:
                    joint.remove(element)
        for mesh in robot.findall('.//mesh'):
            uri = mesh.get('filename', '')
            if uri.startswith('package://'):
                package, relative = uri.removeprefix('package://').split('/', 1)
                mesh.set('filename', 'file://' + str(Path(get_package_share_directory(package)) / relative))
        moveit_dict['robot_description'] = ET.tostring(robot, encoding='unicode')
    moveit_dict['robot_description'] = add_wrist_camera(
        moveit_dict['robot_description'], camera_mode,
        parent='tool_flange' if atom_tool else 'xarm_gripper_base_link'
    )
    if camera_mode != 'none':
        moveit_dict['robot_description_semantic'] = allow_wrist_camera_self_collisions(
            moveit_dict['robot_description_semantic'],
            moveit_dict['robot_description'],
        )
    if actuator_model == 'nominal':
        standard_hardware = '<plugin>gz_ros2_control/GazeboSimSystem</plugin>'
        nominal_hardware = '<plugin>atom_xarm_dynamics/NominalActuatorSystem</plugin>'
        if standard_hardware not in moveit_dict['robot_description']:
            raise RuntimeError('could not locate the Gazebo hardware plugin in robot_description')
        moveit_dict['robot_description'] = moveit_dict['robot_description'].replace(
            standard_hardware,
            nominal_hardware,
            1,
        )

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
    if camera_mode != 'none':
        runtime_dir = Path(tempfile.mkdtemp(prefix='atom_camera_experiment_'))
        world = str(experiment_world(world, runtime_dir / 'world.sdf'))
        rack_path = str(write_tag_rack(runtime_dir / 'source_rack.sdf'))
        shelf_path = str(write_two_level_shelf(runtime_dir / 'shelf.sdf'))
        tube_path = str(write_transparent_tube(runtime_dir / 'tube.sdf'))
    gazebo_server = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={
            'gz_args': (
                f'-s -r -v 3 {world} '
                f'--physics-engine {physics_engine}'
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
            '-Y', '-1.571',
        ],
        parameters=[{'use_sim_time': True}],
    )

    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen',
    )

    camera_actions = []
    if camera_mode != 'none':
        source_shelf_x = 0.50
        source_x = source_shelf_x - rack_dy_m
        source_y = -1.00 + rack_dx_m
        source_yaw = -0.00 + rack_dyaw_rad
        tube_x = (source_x + 0.030 * math.cos(source_yaw)
                  - SLOT_Y_M[SOURCE_SLOT_INDEX] * math.sin(source_yaw))
        tube_y = (source_y + 0.030 * math.sin(source_yaw)
                  + SLOT_Y_M[SOURCE_SLOT_INDEX] * math.cos(source_yaw))
        fixtures = (
            (shelf_path, 'atom_two_level_shelf', source_x,
             source_y, 1.021, source_yaw),
            (rack_path, 'atom_source_rack', source_x,
             source_y, 1.159, source_yaw),
            (tube_path, 'atom_transfer_tube', tube_x,
             tube_y, 1.2155, 0.0),
        )
        if scene_fixtures:
            for fixture_path, name, x, y, z, yaw in fixtures:
                if fixture_group == 'shelf' and name != 'atom_two_level_shelf':
                    continue
                if fixture_group == 'rack' and name not in (
                    'atom_two_level_shelf', 'atom_source_rack'):
                    continue
                if fixture_group == 'tube' and name != 'atom_transfer_tube':
                    continue
                camera_actions.append(Node(
                    package='ros_gz_sim', executable='create', output='screen',
                    arguments=['-file', fixture_path, '-name', name,
                               '-x', str(x), '-y', str(y), '-z', str(z),
                               '-Y', str(yaw)],
                    parameters=[{'use_sim_time': True}],
                ))
        bridge_args = []
        if camera_mode == 'rgb':
            bridge_args.append(
                '/atom/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo'
            )
            bridge_args.append('/atom/wrist_camera@sensor_msgs/msg/Image[gz.msgs.Image')
        else:
            bridge_args.extend([
                '/atom/wrist_camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
                '/atom/wrist_camera/image@sensor_msgs/msg/Image[gz.msgs.Image',
            ])
            bridge_args.append(
                '/atom/wrist_camera/depth_image@sensor_msgs/msg/Image[gz.msgs.Image'
            )
        camera_actions.append(Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=bridge_args,
            output='screen',
        ))

    controller_spawners = [
        Node(
            package='controller_manager',
            executable='spawner',
            output='screen',
            arguments=[name, '--controller-manager', '/controller_manager'],
            parameters=[{'use_sim_time': True}],
        )
        for name in (
            'joint_state_broadcaster', 'uf850_traj_controller',
            *(['uf850_gripper_traj_controller'] if demo_gripper else []),
        )
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

    gui_actions = []
    if show_gui:
        gui_actions.append(ExecuteProcess(cmd=['gz', 'sim', '-g'], output='screen'))
        gui_actions.append(Node(
            package='rviz2',
            executable='rviz2',
            arguments=[
                '-d',
                os.path.join(
                    get_package_share_directory('xarm_moveit_config'),
                    'rviz', 'moveit.rviz',
                ),
            ],
            parameters=[moveit_dict, {'use_sim_time': True}],
            output='screen',
        ))

    return [
        RegisterEventHandler(
            OnProcessStart(
                target_action=robot_state_publisher,
                on_start=[gazebo_server, spawn_robot, clock_bridge,
                          *camera_actions, *gui_actions],
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
    return LaunchDescription([
        DeclareLaunchArgument('atom_tool', default_value='none', choices=['none', 'v2']),
        DeclareLaunchArgument(
            'actuator_model',
            default_value='ideal',
            choices=['ideal', 'nominal'],
            description='Gazebo actuator layer: ideal position following or nominal torque-PD',
        ),
        DeclareLaunchArgument(
            'camera_mode',
            default_value='none',
            choices=['none', 'rgb', 'depth'],
            description='Simulation-only wrist sensor; RGB and depth are mutually exclusive',
        ),
        DeclareLaunchArgument('demo_gripper', default_value='false',
                              choices=['true', 'false'],
                              description='Attach the official UFactory G1 demo gripper'),
        DeclareLaunchArgument('scene_fixtures', default_value='true',
                              choices=['true', 'false'],
                              description='Spawn the two-level rack and tube fixtures'),
        DeclareLaunchArgument('fixture_group', default_value='all',
                              choices=['all', 'shelf', 'rack', 'tube'],
                              description=(
                                  'Diagnostic subset; rack includes its supporting shelf'
                              )),
        DeclareLaunchArgument('rack_dx_m', default_value='0.0'),
        DeclareLaunchArgument('rack_dy_m', default_value='0.0'),
        DeclareLaunchArgument('rack_dyaw_rad', default_value='0.0'),
        DeclareLaunchArgument('gui', default_value='false', choices=['true', 'false']),
        OpaqueFunction(function=launch_setup),
    ])

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def launch_setup(context):
    headless = LaunchConfiguration("headless").perform(context).lower() == "true"
    world_name = LaunchConfiguration("world").perform(context)
    ros_distro = os.environ.get("ROS_DISTRO", "")
    is_humble = ros_distro == "humble"
    control_backend = LaunchConfiguration("control_backend").perform(context)
    if control_backend not in {"native", "ros2_control"}:
        raise RuntimeError(
            "control_backend must be either 'native' or 'ros2_control'"
        )
    use_ros2_control = control_backend == "ros2_control"
    logical_grasp = LaunchConfiguration("logical_grasp").perform(context).lower() == "true"
    gz_args = "-r -s" if headless else "-r"
    if is_humble:
        world_name = {
            "atom_empty.sdf": "atom_empty_fortress.sdf",
            "atom_grasp.sdf": "atom_grasp_fortress.sdf",
            "atom_logical_grasp.sdf": "atom_logical_grasp_fortress.sdf",
        }.get(world_name, world_name)
    world = PathJoinSubstitution(
        [
            FindPackageShare("atom_gripper_description"),
            "worlds",
            world_name,
        ]
    )
    description_name = (
        "ur3e_atom_humble.urdf.xacro" if is_humble else "ur3e_atom.urdf.xacro"
    )
    description_file = PathJoinSubstitution(
        [FindPackageShare("atom_gripper_description"), "urdf", description_name]
    )
    robot_description = ParameterValue(
        Command(
            [
                FindExecutable(name="xacro"),
                " ",
                description_file,
                " initial_finger_position:=",
                LaunchConfiguration("initial_finger_position"),
                " control_backend:=",
                LaunchConfiguration("control_backend"),
                " enable_logical_grasp:=",
                LaunchConfiguration("logical_grasp"),
            ]
        ),
        value_type=str,
    )
    resource_paths = os.pathsep.join(
        os.path.dirname(get_package_share_directory(package_name))
        for package_name in ("atom_gripper_description", "ur_description")
    )
    gz_message_prefix = "ignition.msgs" if is_humble else "gz.msgs"
    bridge_arguments = [f"/clock@rosgraph_msgs/msg/Clock[{gz_message_prefix}.Clock"]
    bridge_remappings = []
    if not use_ros2_control:
        bridge_arguments.append(
            f"/model/ur3e_atom/joint_state@sensor_msgs/msg/JointState["
            f"{gz_message_prefix}.Model"
        )
        bridge_arguments.extend(
            f"/model/ur3e_atom/joint/{joint}/cmd_pos@std_msgs/msg/Float64]"
            f"{gz_message_prefix}.Double"
            for joint in (
                "shoulder_pan_joint",
                "shoulder_lift_joint",
                "elbow_joint",
                "wrist_1_joint",
                "wrist_2_joint",
                "wrist_3_joint",
                "left_finger_joint",
                "right_finger_joint",
            )
        )
        bridge_remappings.append(
            ("/model/ur3e_atom/joint_state", "/joint_states")
        )
    if world_name in {
        "atom_grasp.sdf",
        "atom_grasp_fortress.sdf",
        "atom_logical_grasp.sdf",
        "atom_logical_grasp_fortress.sdf",
    }:
        cuvette_pose_topic = (
            f"/world/{'atom_logical_grasp' if logical_grasp else 'atom_grasp'}/dynamic_pose/info"
            if is_humble
            else "/model/cuvette/pose"
        )
        bridge_arguments.append(
            f"{cuvette_pose_topic}@tf2_msgs/msg/TFMessage["
            f"{gz_message_prefix}.Pose_V"
        )
        bridge_remappings.append((cuvette_pose_topic, "/cuvette/pose"))
    if logical_grasp:
        bridge_arguments.extend(
            [
                f"/atom_grasp/attach@std_msgs/msg/Empty]{gz_message_prefix}.Empty",
                f"/atom_grasp/detach@std_msgs/msg/Empty]{gz_message_prefix}.Empty",
                f"/atom_grasp/state@std_msgs/msg/String[{gz_message_prefix}.StringMsg",
            ]
        )

    create_node = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-topic",
            "robot_description",
            "-name",
            "ur3e_atom",
            "-allow_renaming",
            "false",
        ],
        output="screen",
    )
    actions = [
        AppendEnvironmentVariable(
            name="GZ_SIM_RESOURCE_PATH", value=resource_paths
        ),
        AppendEnvironmentVariable(
            name="IGN_GAZEBO_RESOURCE_PATH", value=resource_paths
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"])
            ),
            launch_arguments={"gz_args": [gz_args, " ", world]}.items(),
        ),
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            parameters=[{"robot_description": robot_description, "use_sim_time": True}],
            output="screen",
        ),
        create_node,
        Node(
            package="ros_gz_bridge",
            executable="parameter_bridge",
            arguments=bridge_arguments,
            remappings=bridge_remappings,
            output="screen",
        ),
    ]
    if use_ros2_control:
        controller_spawners = [
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=[
                    controller,
                    "--controller-manager",
                    "/controller_manager",
                    "--controller-manager-timeout",
                    "30",
                ],
                output="screen",
            )
            for controller in (
                "joint_state_broadcaster",
                "arm_controller",
                "gripper_controller",
            )
        ]
        actions.append(
            RegisterEventHandler(
                OnProcessExit(
                    target_action=create_node,
                    on_exit=controller_spawners,
                )
            )
        )
    return actions


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("headless", default_value="false"),
            DeclareLaunchArgument("world", default_value="atom_empty.sdf"),
            DeclareLaunchArgument("initial_finger_position", default_value="0.0"),
            DeclareLaunchArgument("control_backend", default_value="native"),
            DeclareLaunchArgument("logical_grasp", default_value="false"),
            OpaqueFunction(function=launch_setup),
        ]
    )

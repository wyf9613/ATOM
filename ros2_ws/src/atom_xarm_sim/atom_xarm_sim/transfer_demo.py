#!/usr/bin/env python3

"""Execute lift, constrained transfer and vertical descent from published poses."""

from copy import deepcopy
import json
import math
from pathlib import Path
import sys
import time

from action_msgs.msg import GoalStatus
from controller_manager_msgs.srv import ListControllers
from geometry_msgs.msg import Pose, PoseStamped
from moveit_msgs.action import ExecuteTrajectory, MoveGroup
from moveit_msgs.msg import (
    Constraints,
    MoveItErrorCodes,
    OrientationConstraint,
    PositionConstraint,
)
from moveit_msgs.srv import GetCartesianPath
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from shape_msgs.msg import SolidPrimitive
from std_msgs.msg import Bool, String
from tf2_ros import Buffer, TransformException, TransformListener


REPORT_PATH = Path('/jazzy_ws/log/atom_uf850_transfer_summary.json')


def _finite_vector(node, name, length):
    values = [float(value) for value in node.get_parameter(name).value]
    if len(values) != length or not all(math.isfinite(value) for value in values):
        raise RuntimeError(f'{name} must contain {length} finite values')
    return values


def _normalise(values, name):
    norm = math.sqrt(sum(value * value for value in values))
    if norm < 1e-9:
        raise RuntimeError(f'{name} must not be a zero vector')
    return [value / norm for value in values]


def _quaternion_angle(first, second):
    a = _normalise([first.x, first.y, first.z, first.w], 'first quaternion')
    b = _normalise([second.x, second.y, second.z, second.w], 'second quaternion')
    dot = abs(sum(left * right for left, right in zip(a, b)))
    return 2.0 * math.acos(max(-1.0, min(1.0, dot)))


class TransferDemo(Node):
    def __init__(self):
        super().__init__('transfer_demo')
        self.declare_parameter('reference_frame', 'world')
        self.declare_parameter('planning_group', 'uf850')
        self.declare_parameter('tcp_link', 'link_eef')
        self.declare_parameter('pick_lift_height_m', 0.05)
        self.declare_parameter('place_approach_height_m', 0.08)
        self.declare_parameter('pick_up_axis_xyz', [0.0, 0.0, 1.0])
        self.declare_parameter('place_up_axis_xyz', [0.0, 0.0, 1.0])
        self.declare_parameter('position_tolerance_m', 0.003)
        self.declare_parameter('vertical_alignment_tolerance_m', 0.004)
        self.declare_parameter('orientation_tolerance_xyz_rad', [0.10, 0.10, 0.10])
        self.declare_parameter('final_orientation_error_tolerance_rad', 0.12)
        self.declare_parameter('max_path_orientation_error_rad', 0.12)
        self.declare_parameter('cartesian_max_step_m', 0.005)
        self.declare_parameter('cartesian_jump_threshold', 2.0)
        self.declare_parameter('minimum_cartesian_fraction', 0.999)
        self.declare_parameter('velocity_scaling', 0.05)
        self.declare_parameter('acceleration_scaling', 0.05)
        self.declare_parameter('planning_time_sec', 10.0)
        self.declare_parameter('simulate_grasp_success', True)

        self.reference_frame = str(self.get_parameter('reference_frame').value)
        self.group_name = str(self.get_parameter('planning_group').value)
        self.tcp_link = str(self.get_parameter('tcp_link').value)
        self.pick_lift_height = self._positive_parameter('pick_lift_height_m')
        self.place_approach_height = self._positive_parameter('place_approach_height_m')
        self.pick_up_axis = _normalise(
            _finite_vector(self, 'pick_up_axis_xyz', 3), 'pick_up_axis_xyz'
        )
        self.place_up_axis = _normalise(
            _finite_vector(self, 'place_up_axis_xyz', 3), 'place_up_axis_xyz'
        )
        self.position_tolerance = self._positive_parameter('position_tolerance_m')
        self.vertical_alignment_tolerance = self._positive_parameter(
            'vertical_alignment_tolerance_m'
        )
        self.orientation_tolerances = _finite_vector(
            self, 'orientation_tolerance_xyz_rad', 3
        )
        if any(value <= 0.0 for value in self.orientation_tolerances):
            raise RuntimeError('orientation_tolerance_xyz_rad values must be positive')
        self.final_orientation_tolerance = self._positive_parameter(
            'final_orientation_error_tolerance_rad'
        )
        self.max_path_orientation_error = self._positive_parameter(
            'max_path_orientation_error_rad'
        )
        self.cartesian_max_step = self._positive_parameter('cartesian_max_step_m')
        self.cartesian_jump_threshold = self._positive_parameter(
            'cartesian_jump_threshold'
        )
        self.minimum_cartesian_fraction = float(
            self.get_parameter('minimum_cartesian_fraction').value
        )
        if not 0.0 < self.minimum_cartesian_fraction <= 1.0:
            raise RuntimeError('minimum_cartesian_fraction must be in (0, 1]')
        self.velocity_scaling = self._unit_interval_parameter('velocity_scaling')
        self.acceleration_scaling = self._unit_interval_parameter('acceleration_scaling')
        self.planning_time = self._positive_parameter('planning_time_sec')
        self.simulate_grasp_success = bool(
            self.get_parameter('simulate_grasp_success').value
        )

        self.pick_pose = None
        self.place_pose = None
        self.grasp_success = False
        target_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.create_subscription(
            PoseStamped, '/atom/pick_pose', self._pick_callback, target_qos
        )
        self.create_subscription(
            PoseStamped, '/atom/place_pose', self._place_callback, target_qos
        )
        self.create_subscription(
            Bool, '/atom/gripper/grasp_success', self._grasp_callback, 10
        )
        self.phase_publisher = self.create_publisher(String, '/atom/transfer_phase', 10)

        self.cartesian_client = self.create_client(
            GetCartesianPath, '/compute_cartesian_path'
        )
        self.controller_client = self.create_client(
            ListControllers, '/controller_manager/list_controllers'
        )
        self.move_group_client = ActionClient(self, MoveGroup, '/move_action')
        self.execute_client = ActionClient(
            self, ExecuteTrajectory, '/execute_trajectory'
        )
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.phase_metrics = {}

    def _positive_parameter(self, name):
        value = float(self.get_parameter(name).value)
        if not math.isfinite(value) or value <= 0.0:
            raise RuntimeError(f'{name} must be positive and finite')
        return value

    def _unit_interval_parameter(self, name):
        value = float(self.get_parameter(name).value)
        if not math.isfinite(value) or not 0.0 < value <= 1.0:
            raise RuntimeError(f'{name} must be in (0, 1]')
        return value

    def _pick_callback(self, message):
        self.pick_pose = message

    def _place_callback(self, message):
        self.place_pose = message

    def _grasp_callback(self, message):
        self.grasp_success = bool(message.data)

    def _publish_phase(self, phase):
        self.phase_publisher.publish(String(data=phase))
        self.get_logger().info(f'PHASE: {phase}')

    def _wait_for_targets(self, timeout_sec=20.0):
        deadline = time.monotonic() + timeout_sec
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.2)
            if self.pick_pose is not None and self.place_pose is not None:
                break
        if self.pick_pose is None or self.place_pose is None:
            raise RuntimeError('timed out waiting for published pick and place poses')
        for label, target in (('pick', self.pick_pose), ('place', self.place_pose)):
            if target.header.frame_id != self.reference_frame:
                raise RuntimeError(
                    f'{label} pose frame {target.header.frame_id!r} does not match '
                    f'reference_frame {self.reference_frame!r}'
                )
            quaternion = target.pose.orientation
            _normalise(
                [quaternion.x, quaternion.y, quaternion.z, quaternion.w],
                f'{label} quaternion',
            )
        orientation_difference = _quaternion_angle(
            self.pick_pose.pose.orientation, self.place_pose.pose.orientation
        )
        if orientation_difference > min(self.orientation_tolerances):
            raise RuntimeError(
                'pick and place orientations differ by '
                f'{orientation_difference:.4f} rad, outside the fixed transport '
                'orientation tolerance'
            )
        self.get_logger().info('PASS: received compatible pick and place targets')

    def _wait_for_moveit(self):
        if not self.controller_client.wait_for_service(timeout_sec=30.0):
            raise RuntimeError('/controller_manager/list_controllers is unavailable')
        required = {'joint_state_broadcaster', 'uf850_traj_controller'}
        deadline = time.monotonic() + 30.0
        observed = {}
        while rclpy.ok() and time.monotonic() < deadline:
            future = self.controller_client.call_async(ListControllers.Request())
            rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)
            response = future.result() if future.done() else None
            if response is not None:
                observed = {
                    controller.name: controller.state
                    for controller in response.controller
                }
                if all(observed.get(name) == 'active' for name in required):
                    break
            time.sleep(0.2)
        else:
            raise RuntimeError(f'controllers are not active: observed={observed}')
        self.get_logger().info('PASS: arm trajectory controllers are active')

        if not self.cartesian_client.wait_for_service(timeout_sec=30.0):
            raise RuntimeError('/compute_cartesian_path is unavailable')
        if not self.move_group_client.wait_for_server(timeout_sec=30.0):
            raise RuntimeError('/move_action is unavailable')
        if not self.execute_client.wait_for_server(timeout_sec=30.0):
            raise RuntimeError('/execute_trajectory is unavailable')

    def _orientation_constraint(self, orientation, name):
        constraint = OrientationConstraint()
        constraint.header.frame_id = self.reference_frame
        constraint.link_name = self.tcp_link
        constraint.orientation = deepcopy(orientation)
        constraint.absolute_x_axis_tolerance = self.orientation_tolerances[0]
        constraint.absolute_y_axis_tolerance = self.orientation_tolerances[1]
        constraint.absolute_z_axis_tolerance = self.orientation_tolerances[2]
        constraint.parameterization = OrientationConstraint.ROTATION_VECTOR
        constraint.weight = 1.0
        constraints = Constraints(name=name)
        constraints.orientation_constraints.append(constraint)
        return constraints

    def _pose_goal_constraints(self, pose, name):
        constraints = self._orientation_constraint(pose.orientation, name)
        position = PositionConstraint()
        position.header.frame_id = self.reference_frame
        position.link_name = self.tcp_link
        sphere = SolidPrimitive()
        sphere.type = SolidPrimitive.SPHERE
        sphere.dimensions = [self.position_tolerance]
        sphere_pose = Pose()
        sphere_pose.position = deepcopy(pose.position)
        sphere_pose.orientation.w = 1.0
        position.constraint_region.primitives.append(sphere)
        position.constraint_region.primitive_poses.append(sphere_pose)
        position.weight = 1.0
        constraints.position_constraints.append(position)
        return constraints

    @staticmethod
    def _offset_pose(source, axis, distance):
        target = deepcopy(source)
        target.position.x += axis[0] * distance
        target.position.y += axis[1] * distance
        target.position.z += axis[2] * distance
        return target

    def _current_pose(self):
        try:
            transform = self.tf_buffer.lookup_transform(
                self.reference_frame, self.tcp_link, rclpy.time.Time()
            )
        except TransformException:
            return None
        pose = Pose()
        pose.position.x = transform.transform.translation.x
        pose.position.y = transform.transform.translation.y
        pose.position.z = transform.transform.translation.z
        pose.orientation = transform.transform.rotation
        return pose

    def _pose_errors(self, target):
        current = self._current_pose()
        if current is None:
            return None
        position_error = math.sqrt(
            (current.position.x - target.position.x) ** 2
            + (current.position.y - target.position.y) ** 2
            + (current.position.z - target.position.z) ** 2
        )
        return position_error, _quaternion_angle(current.orientation, target.orientation)

    def _record_orientation_sample(self, desired_orientation, metrics):
        current = self._current_pose()
        if current is None:
            return
        error = _quaternion_angle(current.orientation, desired_orientation)
        metrics['samples'] += 1
        metrics['max_orientation_error_rad'] = max(
            metrics['max_orientation_error_rad'], error
        )

    def _vertical_alignment(self, target, axis, expected_direction, label):
        current = self._current_pose()
        if current is None:
            raise RuntimeError(f'no TF available before {label}')
        displacement = [
            target.position.x - current.position.x,
            target.position.y - current.position.y,
            target.position.z - current.position.z,
        ]
        axial_distance = sum(
            component * axis_component
            for component, axis_component in zip(displacement, axis)
        )
        lateral_distance = math.sqrt(sum(
            (component - axial_distance * axis_component) ** 2
            for component, axis_component in zip(displacement, axis)
        ))
        if expected_direction * axial_distance <= 0.0:
            raise RuntimeError(
                f'{label} target is in the wrong direction along its vertical axis'
            )
        if lateral_distance > self.vertical_alignment_tolerance:
            raise RuntimeError(
                f'{label} would include {lateral_distance:.5f} m lateral motion, '
                f'exceeding {self.vertical_alignment_tolerance:.5f} m'
            )
        return {
            'commanded_axial_distance_m': axial_distance,
            'commanded_lateral_distance_m': lateral_distance,
        }

    def _wait_action_result(
        self,
        result_future,
        timeout_sec,
        label,
        desired_orientation,
        enforce_orientation=False,
    ):
        metrics = {'samples': 0, 'max_orientation_error_rad': 0.0}
        deadline = time.monotonic() + timeout_sec
        while rclpy.ok() and not result_future.done() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.02)
            self._record_orientation_sample(desired_orientation, metrics)
        if not result_future.done():
            raise RuntimeError(f'{label} execution timed out')
        self.phase_metrics[label] = metrics
        if enforce_orientation:
            if metrics['samples'] == 0:
                raise RuntimeError(f'no TCP orientation samples captured during {label}')
            if (
                metrics['max_orientation_error_rad']
                > self.max_path_orientation_error
            ):
                raise RuntimeError(
                    f'{label} maximum measured orientation error '
                    f'{metrics["max_orientation_error_rad"]:.5f} rad exceeds '
                    f' {self.max_path_orientation_error:.5f} rad'
                )
        return result_future.result()

    def _verify_pose(self, target, label, timeout_sec=4.0):
        deadline = time.monotonic() + timeout_sec
        latest = None
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
            latest = self._pose_errors(target)
            if latest is not None and (
                latest[0] <= self.position_tolerance
                and latest[1] <= self.final_orientation_tolerance
            ):
                break
        if latest is None:
            raise RuntimeError(f'no TF available while verifying {label}')
        if (
            latest[0] > self.position_tolerance
            or latest[1] > self.final_orientation_tolerance
        ):
            raise RuntimeError(
                f'{label} final error exceeds tolerance: '
                f'position={latest[0]:.5f} m, orientation={latest[1]:.5f} rad'
            )
        self.phase_metrics.setdefault(label, {})
        self.phase_metrics[label].update({
            'final_position_error_m': latest[0],
            'final_orientation_error_rad': latest[1],
        })
        self.get_logger().info(
            f'PASS: {label} final position error={latest[0]:.5f} m, '
            f'orientation error={latest[1]:.5f} rad'
        )

    def _move_to_pick_if_needed(self):
        current_errors = self._pose_errors(self.pick_pose.pose)
        if current_errors is not None and (
            current_errors[0] <= self.position_tolerance
            and current_errors[1] <= self.final_orientation_tolerance
        ):
            self.get_logger().info('Already at the published pick pose')
            return

        self._publish_phase('MOVE_TO_PICK')
        goal = MoveGroup.Goal()
        goal.request.group_name = self.group_name
        goal.request.num_planning_attempts = 10
        goal.request.allowed_planning_time = self.planning_time
        goal.request.max_velocity_scaling_factor = self.velocity_scaling
        goal.request.max_acceleration_scaling_factor = self.acceleration_scaling
        goal.request.start_state.is_diff = True
        goal.request.goal_constraints.append(
            self._pose_goal_constraints(self.pick_pose.pose, 'pick_goal')
        )
        goal.planning_options.plan_only = False
        goal.planning_options.replan = False
        goal.planning_options.planning_scene_diff.is_diff = True
        goal.planning_options.planning_scene_diff.robot_state.is_diff = True
        send_future = self.move_group_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=10.0)
        handle = send_future.result() if send_future.done() else None
        if handle is None or not handle.accepted:
            raise RuntimeError('MoveIt rejected the move-to-pick goal')
        wrapped = self._wait_action_result(
            handle.get_result_async(), 60.0, 'move_to_pick', self.pick_pose.pose.orientation
        )
        if (
            wrapped.status != GoalStatus.STATUS_SUCCEEDED
            or wrapped.result.error_code.val != MoveItErrorCodes.SUCCESS
        ):
            raise RuntimeError(
                'move-to-pick failed with MoveIt code '
                f'{wrapped.result.error_code.val}'
            )
        self._verify_pose(self.pick_pose.pose, 'move_to_pick')

    def _wait_for_grasp(self, timeout_sec=20.0):
        self._publish_phase('VERIFY_GRASP')
        if self.simulate_grasp_success:
            self.get_logger().warning(
                'SIMULATION ONLY: accepting a simulated grasp-success result; '
                'no gripper controller or object attachment is active'
            )
            return
        deadline = time.monotonic() + timeout_sec
        while rclpy.ok() and not self.grasp_success and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.2)
        if not self.grasp_success:
            raise RuntimeError('timed out waiting for /atom/gripper/grasp_success')

    def _cartesian_motion(
        self,
        target,
        label,
        constrained_orientation,
        vertical_axis=None,
        expected_direction=None,
    ):
        self._publish_phase(label.upper())
        alignment_metrics = {}
        if vertical_axis is not None:
            alignment_metrics = self._vertical_alignment(
                target, vertical_axis, expected_direction, label
            )
        request = GetCartesianPath.Request()
        request.header.frame_id = self.reference_frame
        request.start_state.is_diff = True
        request.group_name = self.group_name
        request.link_name = self.tcp_link
        request.waypoints.append(deepcopy(target))
        request.max_step = self.cartesian_max_step
        request.jump_threshold = self.cartesian_jump_threshold
        request.avoid_collisions = True
        request.path_constraints = self._orientation_constraint(
            constrained_orientation, f'{label}_orientation'
        )
        request.max_velocity_scaling_factor = self.velocity_scaling
        request.max_acceleration_scaling_factor = self.acceleration_scaling

        future = self.cartesian_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=20.0)
        response = future.result() if future.done() else None
        if response is None:
            raise RuntimeError(f'{label} Cartesian planning timed out')
        if response.error_code.val != MoveItErrorCodes.SUCCESS:
            raise RuntimeError(
                f'{label} Cartesian planning failed with code {response.error_code.val}'
            )
        if response.fraction < self.minimum_cartesian_fraction:
            raise RuntimeError(
                f'{label} Cartesian path fraction {response.fraction:.5f} is below '
                f'{self.minimum_cartesian_fraction:.5f}'
            )
        cartesian_points = len(response.solution.joint_trajectory.points)
        if cartesian_points == 0:
            raise RuntimeError(f'{label} Cartesian planning returned no points')

        goal = ExecuteTrajectory.Goal()
        goal.trajectory = response.solution
        send_future = self.execute_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=10.0)
        handle = send_future.result() if send_future.done() else None
        if handle is None or not handle.accepted:
            raise RuntimeError(f'MoveIt rejected the {label} trajectory')
        wrapped = self._wait_action_result(
            handle.get_result_async(),
            40.0,
            label,
            constrained_orientation,
            enforce_orientation=True,
        )
        if (
            wrapped.status != GoalStatus.STATUS_SUCCEEDED
            or wrapped.result.error_code.val != MoveItErrorCodes.SUCCESS
        ):
            raise RuntimeError(
                f'{label} execution failed with MoveIt code '
                f'{wrapped.result.error_code.val}'
            )
        self.phase_metrics[label]['cartesian_fraction'] = response.fraction
        self.phase_metrics[label]['cartesian_points'] = cartesian_points
        self.phase_metrics[label].update(alignment_metrics)
        self._verify_pose(target, label)

    def _write_report(self, pick_lift_pose, place_approach_pose):
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        report = {
            'scope': (
                'arm-only Gazebo baseline with simulated grasp success; '
                'not physical gripper validation'
            ),
            'reference_frame': self.reference_frame,
            'tcp_link': self.tcp_link,
            'pick_lift_height_m': self.pick_lift_height,
            'place_approach_height_m': self.place_approach_height,
            'pick_lift_position_xyz_m': [
                pick_lift_pose.position.x,
                pick_lift_pose.position.y,
                pick_lift_pose.position.z,
            ],
            'place_approach_position_xyz_m': [
                place_approach_pose.position.x,
                place_approach_pose.position.y,
                place_approach_pose.position.z,
            ],
            'phases': self.phase_metrics,
        }
        with REPORT_PATH.open('w', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
        self.get_logger().info(f'Transfer report: {REPORT_PATH}')

    def run(self):
        self._wait_for_targets()
        self._wait_for_moveit()
        self._move_to_pick_if_needed()
        self._wait_for_grasp()

        transport_orientation = deepcopy(self.pick_pose.pose.orientation)
        pick_lift_pose = self._offset_pose(
            self.pick_pose.pose, self.pick_up_axis, self.pick_lift_height
        )
        place_approach_pose = self._offset_pose(
            self.place_pose.pose, self.place_up_axis, self.place_approach_height
        )
        self._cartesian_motion(
            pick_lift_pose,
            'vertical_lift',
            transport_orientation,
            self.pick_up_axis,
            1.0,
        )
        self._cartesian_motion(
            place_approach_pose,
            'constrained_transfer',
            transport_orientation,
        )
        self._cartesian_motion(
            self.place_pose.pose,
            'vertical_descent',
            transport_orientation,
            self.place_up_axis,
            -1.0,
        )
        self._write_report(pick_lift_pose, place_approach_pose)
        self._publish_phase('COMPLETE')
        self.get_logger().info(
            'PASS: vertical lift, orientation-constrained transfer and '
            'vertical descent completed'
        )


def main():
    rclpy.init()
    node = None
    try:
        node = TransferDemo()
        node.run()
    except Exception as error:
        logger = node.get_logger() if node is not None else rclpy.logging.get_logger(
            'transfer_demo'
        )
        logger.error(f'FAIL: {error}')
        return_code = 1
    else:
        return_code = 0
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()
    sys.exit(return_code)


if __name__ == '__main__':
    main()

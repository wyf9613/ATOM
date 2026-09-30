"""Reusable TransportMotion capability; no task-specific node."""
from copy import deepcopy
import math
import time
from action_msgs.msg import GoalStatus
from controller_manager_msgs.srv import ListControllers
from geometry_msgs.msg import (
    Pose,
)
from moveit_msgs.action import ExecuteTrajectory, MoveGroup
from moveit_msgs.msg import (
    Constraints,
    MoveItErrorCodes,
    OrientationConstraint,
    PositionConstraint,
)
from moveit_msgs.srv import GetCartesianPath
import rclpy
from shape_msgs.msg import SolidPrimitive
from tf2_ros import (
    TransformException,
)
from atom_xarm_sim.planning.transfer_support import (
    _quaternion_angle,
)

class TransportMotion:
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

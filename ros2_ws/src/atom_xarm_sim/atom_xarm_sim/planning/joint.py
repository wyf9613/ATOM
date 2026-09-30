"""Reusable JointMotion capability; no task-specific node."""
import math
import time
import rclpy
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint, MoveItErrorCodes
from atom_xarm_sim.planning.trajectory_support import (
    JOINT_NAMES,
)

class JointMotion:
    @staticmethod
    def _goal_constraints(target, label):
        constraints = Constraints(name=label)
        for name, position in zip(JOINT_NAMES, target):
            constraint = JointConstraint()
            constraint.joint_name = name
            constraint.position = position
            constraint.tolerance_above = 0.01
            constraint.tolerance_below = 0.01
            constraint.weight = 1.0
            constraints.joint_constraints.append(constraint)
        return constraints

    def _plan_and_execute(self, target, label):
        if not self.move_group_client.wait_for_server(timeout_sec=30.0):
            raise RuntimeError('MoveIt /move_action server is unavailable')

        goal = MoveGroup.Goal()
        goal.request.group_name = 'uf850'
        goal.request.num_planning_attempts = 5
        goal.request.allowed_planning_time = 5.0
        goal.request.max_velocity_scaling_factor = 0.05
        goal.request.max_acceleration_scaling_factor = 0.05
        goal.request.start_state.is_diff = True
        goal.request.goal_constraints.append(self._goal_constraints(target, label))
        goal.planning_options.plan_only = False
        goal.planning_options.replan = False
        goal.planning_options.planning_scene_diff.is_diff = True
        goal.planning_options.planning_scene_diff.robot_state.is_diff = True

        self.monitor_phase = label
        send_future = self.move_group_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=10.0)
        handle = send_future.result() if send_future.done() else None
        if handle is None or not handle.accepted:
            self.monitor_phase = None
            raise RuntimeError(f'MoveIt rejected the {label} goal')

        result_future = handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=40.0)
        self.monitor_phase = None
        wrapped_result = result_future.result() if result_future.done() else None
        if wrapped_result is None:
            raise RuntimeError(f'MoveIt {label} result timed out')
        result = wrapped_result.result
        if result.error_code.val != MoveItErrorCodes.SUCCESS:
            diagnostics = {
                name: next(
                    (
                        sample for sample in reversed(self.monitor_samples)
                        if sample['phase'] == label and sample['joint'] == name
                    ),
                    None,
                )
                for name in JOINT_NAMES
            }
            self.get_logger().error(f'controller diagnostics: {diagnostics}')
            raise RuntimeError(
                f'MoveIt {label} plan-and-execute failed with code {result.error_code.val}'
            )
        planned_points = len(result.planned_trajectory.joint_trajectory.points)
        executed_points = len(result.executed_trajectory.joint_trajectory.points)
        if planned_points == 0 or executed_points == 0:
            raise RuntimeError(
                f'MoveIt {label} returned empty trajectory data '
                f'(planned={planned_points}, executed={executed_points})'
            )

        deadline = time.monotonic() + 3.0
        goal_tolerance = float(self.get_parameter('goal_tolerance_rad').value)
        if not math.isfinite(goal_tolerance) or goal_tolerance <= 0.0:
            raise RuntimeError('goal_tolerance_rad must be a positive finite value')
        max_error = math.inf
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.positions is not None:
                max_error = max(
                    abs(actual - desired)
                    for actual, desired in zip(self.positions, target)
                )
                if max_error <= goal_tolerance:
                    break
        if max_error > goal_tolerance:
            raise RuntimeError(
                f'MoveIt {label} final error {max_error:.6f} rad exceeds '
                f'{goal_tolerance:.3f} rad'
            )
        self.get_logger().info(
            f'PASS: MoveIt planned and executed {label} '
            f'(planned points={planned_points}, executed points={executed_points}, '
            f'max joint error={max_error:.6f} rad)'
        )

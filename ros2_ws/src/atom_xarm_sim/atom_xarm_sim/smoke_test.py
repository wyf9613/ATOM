#!/usr/bin/env python3

import math
import sys
import time

import rclpy
from control_msgs.action import FollowJointTrajectory
from controller_manager_msgs.srv import ListControllers
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint, MoveItErrorCodes
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import JointState
from tf2_ros import Buffer, TransformException, TransformListener
from trajectory_msgs.msg import JointTrajectoryPoint


JOINT_NAMES = [f'joint{index}' for index in range(1, 7)]


class Uf850SmokeTest(Node):
    def __init__(self):
        super().__init__('uf850_smoke_test')
        self.positions = None
        self.create_subscription(JointState, '/joint_states', self._joint_state_callback, 10)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.controller_client = self.create_client(ListControllers, '/controller_manager/list_controllers')
        self.move_group_client = ActionClient(self, MoveGroup, '/move_action')
        self.trajectory_client = ActionClient(
            self,
            FollowJointTrajectory,
            '/uf850_traj_controller/follow_joint_trajectory',
        )

    def _joint_state_callback(self, message):
        values = dict(zip(message.name, message.position))
        if all(name in values for name in JOINT_NAMES):
            self.positions = [values[name] for name in JOINT_NAMES]

    def _wait_for_joint_state(self, timeout_sec=30.0):
        deadline = time.monotonic() + timeout_sec
        while rclpy.ok() and self.positions is None and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.2)
        if self.positions is None:
            raise RuntimeError('timed out waiting for all six xArm joint states')
        self.get_logger().info('PASS: received all six xArm joint states')

    def _check_controllers(self, timeout_sec=30.0):
        if not self.controller_client.wait_for_service(timeout_sec=timeout_sec):
            raise RuntimeError('controller manager list service is unavailable')
        required = ('joint_state_broadcaster', 'uf850_traj_controller')
        deadline = time.monotonic() + timeout_sec
        states = {}
        while rclpy.ok() and time.monotonic() < deadline:
            future = self.controller_client.call_async(ListControllers.Request())
            rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)
            if future.done() and future.result() is not None:
                states = {
                    controller.name: controller.state
                    for controller in future.result().controller
                }
                if all(states.get(name) == 'active' for name in required):
                    self.get_logger().info(
                        'PASS: joint-state and trajectory controllers are active'
                    )
                    return
            rclpy.spin_once(self, timeout_sec=0.2)
        inactive = [name for name in required if states.get(name) != 'active']
        raise RuntimeError(
            f'controllers did not become active within {timeout_sec:.1f} s: '
            f'{inactive}; observed={states}'
        )

    def _check_tf(self):
        deadline = time.monotonic() + 20.0
        while rclpy.ok() and time.monotonic() < deadline:
            try:
                self.tf_buffer.lookup_transform('world', 'link_eef', rclpy.time.Time())
                self.get_logger().info('PASS: TF world -> link_eef is available')
                return
            except TransformException:
                rclpy.spin_once(self, timeout_sec=0.2)
        raise RuntimeError('timed out waiting for TF world -> link_eef')

    def _check_moveit_plan(self, target):
        if not self.move_group_client.wait_for_server(timeout_sec=30.0):
            raise RuntimeError('MoveIt /move_action server is unavailable')

        goal = MoveGroup.Goal()
        goal.request.group_name = 'uf850'
        goal.request.num_planning_attempts = 5
        goal.request.allowed_planning_time = 5.0
        goal.request.max_velocity_scaling_factor = 0.1
        goal.request.max_acceleration_scaling_factor = 0.1
        goal.request.start_state.is_diff = True
        constraints = Constraints(name='atom_smoke_joint_goal')
        for name, position in zip(JOINT_NAMES, target):
            constraint = JointConstraint()
            constraint.joint_name = name
            constraint.position = position
            constraint.tolerance_above = 0.01
            constraint.tolerance_below = 0.01
            constraint.weight = 1.0
            constraints.joint_constraints.append(constraint)
        goal.request.goal_constraints.append(constraints)
        goal.planning_options.plan_only = True

        send_future = self.move_group_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=10.0)
        handle = send_future.result() if send_future.done() else None
        if handle is None or not handle.accepted:
            raise RuntimeError('MoveIt rejected the planning goal')
        result_future = handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=20.0)
        wrapped_result = result_future.result() if result_future.done() else None
        if wrapped_result is None:
            raise RuntimeError('MoveIt planning result timed out')
        result = wrapped_result.result
        if result.error_code.val != MoveItErrorCodes.SUCCESS:
            raise RuntimeError(f'MoveIt planning failed with code {result.error_code.val}')
        points = result.planned_trajectory.joint_trajectory.points
        if not points:
            raise RuntimeError('MoveIt returned an empty planned trajectory')
        self.get_logger().info(f'PASS: MoveIt planned a trajectory with {len(points)} points')

    def _execute_trajectory(self, target, label):
        if not self.trajectory_client.wait_for_server(timeout_sec=20.0):
            raise RuntimeError('trajectory controller action server is unavailable')
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = JOINT_NAMES
        point = JointTrajectoryPoint()
        point.positions = target
        point.time_from_start.sec = 2
        goal.trajectory.points = [point]
        send_future = self.trajectory_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=10.0)
        handle = send_future.result() if send_future.done() else None
        if handle is None or not handle.accepted:
            raise RuntimeError(f'trajectory controller rejected {label} goal')
        result_future = handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=15.0)
        wrapped_result = result_future.result() if result_future.done() else None
        if wrapped_result is None or wrapped_result.result.error_code != 0:
            code = None if wrapped_result is None else wrapped_result.result.error_code
            raise RuntimeError(f'trajectory {label} failed with code {code}')
        deadline = time.monotonic() + 3.0
        max_error = math.inf
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.positions is not None:
                max_error = max(abs(actual - desired) for actual, desired in zip(self.positions, target))
                if max_error <= 0.02:
                    break
        if max_error > 0.02:
            raise RuntimeError(
                f'trajectory {label} final joint error {max_error:.6f} rad exceeds 0.02 rad'
            )
        self.get_logger().info(
            f'PASS: trajectory controller completed {label} goal '
            f'(max joint error {max_error:.6f} rad)'
        )

    def run(self):
        self._wait_for_joint_state()
        self._check_controllers()
        self._check_tf()
        initial = list(self.positions)
        target = list(initial)
        target[0] = initial[0] + 0.05
        if not math.isfinite(target[0]):
            raise RuntimeError('joint state contains a non-finite position')
        self._check_moveit_plan(target)
        self._execute_trajectory(target, 'offset')
        self._execute_trajectory(initial, 'return')
        self.get_logger().info('PASS: xArm 850 headless simulation smoke test completed')


def main():
    rclpy.init()
    node = Uf850SmokeTest()
    try:
        node.run()
    except Exception as error:
        node.get_logger().error(f'FAIL: {error}')
        return_code = 1
    else:
        return_code = 0
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(return_code)


if __name__ == '__main__':
    main()

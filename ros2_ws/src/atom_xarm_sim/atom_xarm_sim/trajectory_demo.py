#!/usr/bin/env python3

"""Plan and execute a deterministic, arm-only UFactory 850 joint trajectory."""

import csv
import json
import math
from pathlib import Path
import sys
import time

import rclpy
from control_msgs.msg import JointTrajectoryControllerState
from controller_manager_msgs.srv import ListControllers
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint, MoveItErrorCodes
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import JointState


JOINT_NAMES = [f'joint{index}' for index in range(1, 7)]
GOAL_TOLERANCE_RAD = 0.02
MONITOR_TOPIC = '/uf850_traj_controller/controller_state'
REPORT_DIRECTORY = Path('/jazzy_ws/log')
# A visible six-joint motion that stays well inside the vendor's limited-model
# joint bounds when starting from the simulation home pose.
DEMO_OFFSETS_RAD = [0.70, -0.45, -0.55, 0.50, 0.45, -0.50]


class Uf850TrajectoryDemo(Node):
    def __init__(self):
        super().__init__('uf850_arm_only_trajectory_demo')
        self.positions = None
        self.observed_joint_names = set()
        self.monitor_phase = None
        self.monitor_samples = []
        self.last_monitor_time = {}
        self.declare_parameter(
            'model_scope',
            'ideal Gazebo position-interface simulation; not validated against physical UF850',
        )
        self.declare_parameter('report_stem', 'atom_uf850_trajectory')
        self.declare_parameter('demo_offsets_rad', DEMO_OFFSETS_RAD)
        self.declare_parameter('goal_tolerance_rad', GOAL_TOLERANCE_RAD)
        self.create_subscription(JointState, '/joint_states', self._joint_state_callback, 10)
        self.create_subscription(
            JointTrajectoryControllerState,
            MONITOR_TOPIC,
            self._controller_state_callback,
            100,
        )
        self.move_group_client = ActionClient(self, MoveGroup, '/move_action')
        self.controller_client = self.create_client(
            ListControllers, '/controller_manager/list_controllers'
        )

    def _joint_state_callback(self, message):
        values = dict(zip(message.name, message.position))
        self.observed_joint_names.update(message.name)
        if all(name in values for name in JOINT_NAMES):
            self.positions = [values[name] for name in JOINT_NAMES]

    def _controller_state_callback(self, message):
        if self.monitor_phase is None:
            return
        indices = {name: index for index, name in enumerate(message.joint_names)}
        if not all(name in indices for name in JOINT_NAMES):
            return
        timestamp = message.header.stamp.sec + message.header.stamp.nanosec * 1e-9
        # Controller state can arrive at the physics rate. A deterministic 100 Hz
        # report is sufficient for this baseline and keeps the CSV practical.
        previous_timestamp = self.last_monitor_time.get(self.monitor_phase)
        if previous_timestamp is not None and timestamp - previous_timestamp < 0.0095:
            return
        self.last_monitor_time[self.monitor_phase] = timestamp
        for name in JOINT_NAMES:
            index = indices[name]
            self.monitor_samples.append({
                'phase': self.monitor_phase,
                'time_sec': timestamp,
                'joint': name,
                'reference_position_rad': message.reference.positions[index],
                'feedback_position_rad': message.feedback.positions[index],
                'position_error_rad': message.error.positions[index],
                'reference_velocity_rad_s': message.reference.velocities[index],
                'feedback_velocity_rad_s': message.feedback.velocities[index],
                'velocity_error_rad_s': message.error.velocities[index],
                'output_position_rad': message.output.positions[index],
                'output_velocity_rad_s': message.output.velocities[index],
            })

    def _wait_for_arm_only_state(self, timeout_sec=30.0):
        deadline = time.monotonic() + timeout_sec
        while rclpy.ok() and self.positions is None and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.2)
        if self.positions is None:
            raise RuntimeError('timed out waiting for all six UFactory 850 joints')
        unexpected = sorted(self.observed_joint_names - set(JOINT_NAMES))
        if unexpected:
            raise RuntimeError(f'arm-only baseline published unexpected joints: {unexpected}')
        if not all(math.isfinite(position) for position in self.positions):
            raise RuntimeError('joint state contains a non-finite position')
        self.get_logger().info('PASS: received exactly six arm joints and no gripper joints')

    def _wait_for_controllers(self, timeout_sec=30.0):
        if not self.controller_client.wait_for_service(timeout_sec=timeout_sec):
            raise RuntimeError('controller manager is unavailable')

        required = {'joint_state_broadcaster', 'uf850_traj_controller'}
        deadline = time.monotonic() + timeout_sec
        observed = {}
        while rclpy.ok() and time.monotonic() < deadline:
            future = self.controller_client.call_async(ListControllers.Request())
            rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)
            response = future.result() if future.done() else None
            if response is not None:
                observed = {controller.name: controller.state for controller in response.controller}
                if all(observed.get(name) == 'active' for name in required):
                    self.get_logger().info(
                        'PASS: joint-state and UF850 trajectory controllers are active'
                    )
                    return
            time.sleep(0.2)
        raise RuntimeError(f'controllers are not active: observed={observed}')

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

    def _write_monitoring_report(self):
        if not self.monitor_samples:
            raise RuntimeError(f'no controller-state samples received from {MONITOR_TOPIC}')

        REPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)
        report_stem = self.get_parameter('report_stem').value
        allowed_report_characters = (
            '-_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        )
        if not report_stem or any(
            character not in allowed_report_characters for character in report_stem
        ):
            raise RuntimeError('report_stem may contain only letters, numbers, hyphen and underscore')
        csv_path = REPORT_DIRECTORY / f'{report_stem}_tracking.csv'
        json_path = REPORT_DIRECTORY / f'{report_stem}_summary.json'
        fieldnames = list(self.monitor_samples[0])
        with csv_path.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.monitor_samples)

        summary = {
            'model_scope': self.get_parameter('model_scope').value,
            'source_topic': MONITOR_TOPIC,
            'position_unit': 'rad',
            'velocity_unit': 'rad/s',
            'phases': {},
        }
        for phase in ('offset', 'return'):
            phase_samples = [
                sample for sample in self.monitor_samples if sample['phase'] == phase
            ]
            if not phase_samples:
                raise RuntimeError(f'no controller-state samples captured for {phase}')
            joint_metrics = {}
            for name in JOINT_NAMES:
                samples = [sample for sample in phase_samples if sample['joint'] == name]
                position_errors = [sample['position_error_rad'] for sample in samples]
                velocity_errors = [sample['velocity_error_rad_s'] for sample in samples]
                feedback_velocities = [sample['feedback_velocity_rad_s'] for sample in samples]
                joint_metrics[name] = {
                    'samples': len(samples),
                    'rms_position_error_rad': math.sqrt(
                        sum(error * error for error in position_errors) / len(position_errors)
                    ),
                    'max_abs_position_error_rad': max(map(abs, position_errors)),
                    'rms_velocity_error_rad_s': math.sqrt(
                        sum(error * error for error in velocity_errors) / len(velocity_errors)
                    ),
                    'max_abs_velocity_error_rad_s': max(map(abs, velocity_errors)),
                    'peak_abs_feedback_velocity_rad_s': max(map(abs, feedback_velocities)),
                }
            summary['phases'][phase] = joint_metrics

        with json_path.open('w', encoding='utf-8') as stream:
            json.dump(summary, stream, indent=2)
            stream.write('\n')

        worst = max(
            (
                metrics['max_abs_position_error_rad'],
                phase,
                name,
            )
            for phase, joints in summary['phases'].items()
            for name, metrics in joints.items()
        )
        self.get_logger().info(
            'TRACKING: worst transient position error '
            f'{worst[0]:.6f} rad at {worst[1]}/{worst[2]}'
        )
        self.get_logger().info(f'Tracking CSV: {csv_path}')
        self.get_logger().info(f'Tracking summary: {json_path}')

    def run(self):
        self._wait_for_arm_only_state()
        self._wait_for_controllers()
        initial = list(self.positions)
        offsets = list(self.get_parameter('demo_offsets_rad').value)
        if len(offsets) != len(JOINT_NAMES) or not all(
            math.isfinite(value) for value in offsets
        ):
            raise RuntimeError('demo_offsets_rad must contain six finite values')
        target = [
            position + offset
            for position, offset in zip(initial, offsets)
        ]

        self._plan_and_execute(target, 'offset')
        self._plan_and_execute(initial, 'return')
        self._write_monitoring_report()
        self.get_logger().info(
            'PASS: bare UFactory 850 MoveIt planning/control simulation completed'
        )


def main():
    rclpy.init()
    node = Uf850TrajectoryDemo()
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

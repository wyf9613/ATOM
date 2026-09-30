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














from atom_xarm_sim.planning.clients import MotionClients


from atom_xarm_sim.planning.transfer_support import (REPORT_PATH, _finite_vector, _normalise, _quaternion_angle)

from atom_xarm_sim.planning.transport import TransportMotion
from atom_xarm_sim.gripper.verification import GraspVerification

class TransferDemo(TransportMotion, GraspVerification, Node):
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
        self.declare_parameter('keep_status_alive', False)
        self.declare_parameter('report_path', str(REPORT_PATH))

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
        self.status_publisher = self.create_publisher(String, '/atom/task/status', 10)
        self.current_phase='INITIALIZING'
        self.task_state='RUNNING'
        self.task_detail='Legacy fixed-target arm motion test; targets are unrelated to current tube slots'
        self.request_id=f'transfer_{time.time_ns()}'
        self.create_timer(.5,self._publish_status)
        self.phase_publisher = self.create_publisher(String, '/atom/transfer_phase', 10)

        self.motion_clients = MotionClients(self, cartesian=True)
        self.motion_clients.bind(self)
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


    def _publish_status(self):
        stages=['INITIALIZING','MOVE_TO_PICK','VERIFY_GRASP','VERTICAL_LIFT',
                'CONSTRAINED_TRANSFER','VERTICAL_DESCENT','COMPLETE']
        self.status_publisher.publish(String(data=json.dumps({
            'schema_version':1,'source':'transfer_baseline','request_id':self.request_id,
            'phase':self.current_phase,'state':self.task_state,'detail':self.task_detail,
            'progress':stages.index(self.current_phase)/(len(stages)-1),
            'simulate_grasp_success':self.simulate_grasp_success,
            'grasp_completed':False,'place_completed':False,'metrics':self.phase_metrics})))

    def _publish_phase(self, phase):
        self.current_phase=phase
        if phase=='COMPLETE':
            self.task_state='SUCCEEDED'
            self.task_detail='Fixed-target arm motion test passed; no tube pick/place was executed'
        self._publish_status()
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














    def _write_report(self, pick_lift_pose, place_approach_pose):
        report_path=Path(self.get_parameter('report_path').value)
        report_path.parent.mkdir(parents=True, exist_ok=True)
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
        with report_path.open('w', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
        self.get_logger().info(f'Transfer report: {report_path}')

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
        if node is not None:
            node.task_state='FAILED'
            node.task_detail=str(error)
            node._publish_status()
        return_code = 1
    else:
        return_code = 0
    finally:
        if node is not None and node.get_parameter('keep_status_alive').value:
            try:
                while rclpy.ok():
                    rclpy.spin_once(node,timeout_sec=.2)
            except KeyboardInterrupt:
                pass
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()
    sys.exit(return_code)


if __name__ == '__main__':
    main()

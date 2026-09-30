#!/usr/bin/env python3

"""Execute the two-stage experiment's pre-observation phase.

The coarse height/bearing input is converted to a fixed-distance target by the
separate ``pre_observation_target_pose`` node.  This node waits for that target,
executes it with MoveIt, and performs the post-move Tag observation.
"""

from copy import deepcopy
import json
import math
from pathlib import Path
import random
import sys
import time
from types import SimpleNamespace

import cv2
import numpy as np
from controller_manager_msgs.srv import ListControllers
from geometry_msgs.msg import Pose, PoseStamped
from moveit_msgs.action import ExecuteTrajectory, MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint, MoveItErrorCodes, OrientationConstraint, PositionConstraint, VisibilityConstraint
from moveit_msgs.srv import GetCartesianPath, GetPositionFK, GetPositionIK
from rclpy.action import ActionClient
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from shape_msgs.msg import SolidPrimitive
from std_msgs.msg import String
from tf2_ros import Buffer, TransformException, TransformListener

from atom_xarm_sim.rack_pose import estimate_rack_pair
from atom_xarm_sim.camera_experiment import SLOT_Y_M, TAG_FAMILY, TAG_SIZE_M


INPUT_TOPIC = '/atom/pre_observation_target'
TARGET_POSE_TOPIC = '/atom/pre_observation_pose'
ROBOT_FRAME = 'link_base'
WORLD_FRAME = 'world'
TCP_LINK = 'link_eef'
ROBOT_SPAWN_XYZ_M = (-0.2, -0.54, 1.021)
ROBOT_SPAWN_YAW_RAD = -1.571
TAG_LOCAL_X_M = -0.0695
TAG_LOCAL_Z_M = 0.029
RACK_Z_M = 1.159
CAMERA_EEF_VERTICAL_OFFSET_M = 0.080
POSITION_TOLERANCE_M = 0.005
ORIENTATION_TOLERANCE_RAD = 0.10
FINAL_ORIENTATION_TOLERANCE_RAD = 0.25
FRONT_OFFSET_M = 0.20
ALIGNMENT_DISTANCE_M = 0.40
FINAL_DISTANCE_M = 0.10
CAMERA_FRAME = 'wrist_camera_optical_frame'


def _normalise(values):
    norm = math.sqrt(sum(value * value for value in values))
    if norm < 1e-12:
        raise ValueError('zero quaternion/vector cannot be normalised')
    return [value / norm for value in values]


def _quat_mul(first, second):
    ax, ay, az, aw = first
    bx, by, bz, bw = second
    return [
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    ]


def _quat_from_yaw(yaw):
    return [0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)]


def _quat_from_pitch(pitch):
    return [0.0, math.sin(pitch / 2.0), 0.0, math.cos(pitch / 2.0)]


def _quat_conjugate(quaternion):
    return [-quaternion[0], -quaternion[1], -quaternion[2], quaternion[3]]


def _angle(a, b):
    a, b = _normalise(a), _normalise(b)
    return math.acos(max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b)))))


def _tilt_delta(first, second):
    # The third row of R is invariant under a world-Z (yaw) rotation.
    return _angle(_rotation_matrix(first)[2], _rotation_matrix(second)[2])


def _quat_from_matrix(matrix):
    trace = matrix[0][0] + matrix[1][1] + matrix[2][2]
    if trace > 0.0:
        scale = math.sqrt(trace + 1.0) * 2.0
        return _normalise([
            (matrix[2][1] - matrix[1][2]) / scale,
            (matrix[0][2] - matrix[2][0]) / scale,
            (matrix[1][0] - matrix[0][1]) / scale,
            0.25 * scale,
        ])
    diagonal = [matrix[0][0], matrix[1][1], matrix[2][2]]
    index = max(range(3), key=lambda item: diagonal[item])
    if index == 0:
        scale = math.sqrt(max(1e-16, 1.0 + matrix[0][0] - matrix[1][1] - matrix[2][2])) * 2.0
        return _normalise([
            0.25 * scale,
            (matrix[0][1] + matrix[1][0]) / scale,
            (matrix[0][2] + matrix[2][0]) / scale,
            (matrix[2][1] - matrix[1][2]) / scale,
        ])
    if index == 1:
        scale = math.sqrt(max(1e-16, 1.0 + matrix[1][1] - matrix[0][0] - matrix[2][2])) * 2.0
        return _normalise([
            (matrix[0][1] + matrix[1][0]) / scale,
            0.25 * scale,
            (matrix[1][2] + matrix[2][1]) / scale,
            (matrix[0][2] - matrix[2][0]) / scale,
        ])
    scale = math.sqrt(max(1e-16, 1.0 + matrix[2][2] - matrix[0][0] - matrix[1][1])) * 2.0
    return _normalise([
        (matrix[0][2] + matrix[2][0]) / scale,
        (matrix[1][2] + matrix[2][1]) / scale,
        0.25 * scale,
        (matrix[1][0] - matrix[0][1]) / scale,
    ])


def _rotation_matrix(quaternion):
    x, y, z, w = _normalise(quaternion)
    return [
        [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)],
        [2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)],
        [2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)],
    ]


def _rotate(quaternion, vector):
    matrix = _rotation_matrix(quaternion)
    return [
        sum(matrix[row][column] * vector[column] for column in range(3))
        for row in range(3)
    ]


def _stamp_to_float(stamp):
    return stamp.sec + stamp.nanosec * 1e-9


def _pose_dict(pose):
    return {
        'frame_id': pose.header.frame_id,
        'stamp_sec': _stamp_to_float(pose.header.stamp),
        'position_m': {
            'x': pose.pose.position.x,
            'y': pose.pose.position.y,
            'z': pose.pose.position.z,
        },
        'orientation_xyzw': [
            pose.pose.orientation.x,
            pose.pose.orientation.y,
            pose.pose.orientation.z,
            pose.pose.orientation.w,
        ],
    }


class PreObservationDemo(Node):
    def __init__(self):
        super().__init__('atom_pre_observation_demo')
        self.run_start_monotonic = time.monotonic()
        self.current_stage = 'initialization'
        self.planning_attempts = {}
        self.declare_parameter('camera_mode', 'rgb')
        self.declare_parameter('keep_status_alive', False)
        self.declare_parameter('robot_frame', ROBOT_FRAME)
        self.declare_parameter('tcp_link', TCP_LINK)
        self.declare_parameter('input_topic', INPUT_TOPIC)
        self.declare_parameter('target_pose_topic', TARGET_POSE_TOPIC)
        self.declare_parameter('rack_dx_m', 0.0)
        self.declare_parameter('rack_dy_m', 0.0)
        self.declare_parameter('rack_dyaw_rad', 0.0)
        self.declare_parameter('random_seed', 20260925)
        self.declare_parameter('bearing_noise_deg', 5.0)
        self.declare_parameter('settle_sec', 1.0)
        self.declare_parameter('timeout_sec', 90.0)
        self.declare_parameter('output_dir', '/tmp/atom_pre_observation')
        self.declare_parameter('task_topic', '/atom/approach_task')
        self.declare_parameter('observation_topic', '/atom/approach/tag_observation')
        self.declare_parameter('demo_tag_id', 1)
        self.declare_parameter('demo_action', 'pick')
        self.declare_parameter('observation_hz', 5.0)
        self.declare_parameter('observation_max_age_sec', 1.0)
        self.declare_parameter('post_move_observation_sec', 3.0)
        self.declare_parameter('visibility_tolerance_rad', 0.30)
        self.declare_parameter('height_tolerance_m', 0.015)
        self.declare_parameter('tilt_tolerance_rad', 0.10)
        self.declare_parameter('ray_width_m', 0.025)
        self.declare_parameter('max_realignment_attempts', 3)
        self.declare_parameter('moveit_visibility_constraint', False)

        self.camera_mode = str(self.get_parameter('camera_mode').value)
        if self.camera_mode not in ('rgb', 'depth'):
            raise RuntimeError('camera_mode must be rgb or depth')
        self.robot_frame = str(self.get_parameter('robot_frame').value)
        self.tcp_link = str(self.get_parameter('tcp_link').value)
        self.input_topic = str(self.get_parameter('input_topic').value)
        self.target_pose_topic = str(self.get_parameter('target_pose_topic').value)
        self.rack_dx = float(self.get_parameter('rack_dx_m').value)
        self.rack_dy = float(self.get_parameter('rack_dy_m').value)
        self.rack_dyaw = float(self.get_parameter('rack_dyaw_rad').value)
        if not all(math.isfinite(value) for value in (self.rack_dx, self.rack_dy, self.rack_dyaw)):
            raise RuntimeError('rack perturbations must be finite')
        self.settle_sec = float(self.get_parameter('settle_sec').value)
        self.timeout_sec = float(self.get_parameter('timeout_sec').value)
        if self.settle_sec < 0.0 or self.timeout_sec <= 0.0:
            raise RuntimeError('settle_sec must be nonnegative and timeout_sec positive')
        self.output_dir = Path(str(self.get_parameter('output_dir').value))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.move_group_client = ActionClient(self, MoveGroup, '/move_action')
        self.execute_client = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')
        self.fk_client = self.create_client(GetPositionFK, '/compute_fk')
        self.ik_client = self.create_client(GetPositionIK, '/compute_ik')
        self.cartesian_client = self.create_client(GetCartesianPath, '/compute_cartesian_path')
        self.controller_client = self.create_client(
            ListControllers, '/controller_manager/list_controllers'
        )

        input_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.input_publisher = self.create_publisher(PoseStamped, self.input_topic, input_qos)
        self.input_message = None
        self.create_subscription(PoseStamped, self.input_topic, self._input_callback, input_qos)
        self.target_pose_message = None
        self.create_subscription(
            PoseStamped, self.target_pose_topic, self._target_pose_callback, input_qos
        )
        self.task_topic = str(self.get_parameter('task_topic').value)
        self.observation_topic = str(self.get_parameter('observation_topic').value)
        self.task_publisher = self.create_publisher(String, self.task_topic, input_qos)
        self.observation_publisher = self.create_publisher(String, self.observation_topic, 10)
        self.create_subscription(String, self.task_topic, self._task_callback, input_qos)
        self.task = None
        self.approach_phase = None
        self.phase_observations = []
        self.all_observations = []
        self.last_observation_wall = 0.0
        self.last_processed_stamp = None
        self.last_depth_stamp = None
        self.phase_metrics = {}
        self.approach_start_pose = None
        self.camera_offset = None
        self.camera_rotation = None
        self.rack_plane_normal = None
        self.rack_observation = None
        self.rack_observation_wall = 0.0

        self.camera_info = None
        self.rgb_message = None
        self.depth_message = None
        info_topic = '/atom/camera_info' if self.camera_mode == 'rgb' else '/atom/wrist_camera/camera_info'
        self.create_subscription(CameraInfo, info_topic, self._camera_info_callback, qos_profile_sensor_data)
        if self.camera_mode == 'rgb':
            self.create_subscription(Image, '/atom/wrist_camera', self._rgb_callback, qos_profile_sensor_data)
        else:
            self.create_subscription(Image, '/atom/wrist_camera/image', self._rgb_callback, qos_profile_sensor_data)
            self.create_subscription(Image, '/atom/wrist_camera/depth_image', self._depth_callback, qos_profile_sensor_data)
        # Image callbacks can precede the matching joint-state TF by a few ms.
        # Retry the cached frame from a timer once TF catches up.
        self.create_timer(0.05, self._capture_timer)

        self.dictionary = cv2.aruco.Dictionary_get(getattr(cv2.aruco, TAG_FAMILY))
        self.detector_params = cv2.aruco.DetectorParameters_create()
        # The four adjacent 40 mm markers occupy a small, tightly spaced
        # strip in the 640 px image. Relax only the inter-marker spacing and
        # perimeter gates enough to keep all four candidates.
        self.detector_params.minMarkerDistanceRate = 0.01
        self.detector_params.minCornerDistanceRate = 0.02
        self.detector_params.minMarkerPerimeterRate = 0.01
        self.detector_params.maxMarkerPerimeterRate = 4.0
        self.capture_enabled = False
        self.observed = {}
        self.depth_quality = {}
        self.capture_error = None
        self.result = None
        self.capture_frame_count = 0
        self.last_detected_ids = []
        self.expected = {}
        self.theoretical_bearing = None
        self.observation_bearing = None
        self.pre_observation_command = None
        self.target_pose_command = None
        self.measured_ray_error_rad = None
        self.gui_request_id = 'approach_' + str(time.time_ns())
        self.gui_final = None
        self.gui_execution_metrics = {}
        self.gui_status_publisher = self.create_publisher(String, '/atom/task/status', input_qos)
        self.create_timer(0.5, self._publish_gui_status)
        self._publish_gui_status()

    def _publish_gui_status(self):
        phases = {
            'initialization': (0.0, 'Initializing experiment'),
            'pre_observation_setup': (0.05, 'Waiting for TF, coarse target and controllers'),
            'pre_observation_move': (0.20, 'Moving to the pre-observation pose'),
            'pre_observation_capture': (0.35, 'Detecting Tag 1 and Tag 2'),
            'realignment': (0.60, 'Re-observing and correcting alignment at 0.40 m'),
            'alignment': (0.55, 'Aligning the front reference point at 0.40 m'),
            'perpendicular': (0.80, 'Approaching the selected Tag plane to 0.10 m'),
            'complete': (1.0, 'Visual approach completed; physical grasp is not implemented'),
        }
        progress, detail = phases.get(self.current_stage, (0, self.current_stage))
        state = 'RUNNING'
        if self.gui_final:
            state, detail = self.gui_final
        status = {
            'schema_version': 1, 'source': 'tube_approach_experiment',
            'request_id': self.gui_request_id, 'state': state,
            'phase': self.current_stage, 'progress': progress,
            'detail': detail, 'camera_mode': self.camera_mode,
            'tag_id': self.task['tag_id'] if self.task else int(self.get_parameter('demo_tag_id').value),
            'requested_action': self.task['action'] if self.task else 'pick',
            'observed_tag_ids': sorted(self.observed),
            'observation_count': len(self.all_observations),
            'completed_segments': list(self.phase_metrics),
            'planning_attempts': dict(self.planning_attempts),
            'execution': 'executing' if self.approach_phase else 'planning_or_waiting',
            'metrics': dict(self.gui_execution_metrics),
            'grasp_completed': False, 'place_completed': False,
        }
        self.gui_status_publisher.publish(String(data=json.dumps(status)))
        # Persist actual status for run inspection; never synthesize task success.
        path = self.output_dir / 'runtime_status.json'
        temporary = self.output_dir / 'runtime_status.tmp'
        temporary.write_text(json.dumps(status, indent=2) + '\n', encoding='utf-8')
        temporary.replace(path)

    def _input_callback(self, message):
        self.input_message = message

    def _target_pose_callback(self, message):
        self.target_pose_message = message

    def _task_callback(self, message):
        try:
            task = json.loads(message.data)
            tag_id = int(task['tag_id'])
            action = str(task['action'])
            if tag_id not in (1, 2) or action not in ('pick', 'place'):
                raise ValueError('tag_id must be 1 or 2; action must be pick or place')
            self.task = {'tag_id': tag_id, 'action': action}
        except (ValueError, KeyError, TypeError) as error:
            self.get_logger().warning(f'Ignoring malformed approach task: {error}')

    def _camera_info_callback(self, message):
        self.camera_info = message

    def _rgb_callback(self, message):
        self.rgb_message = message

    def _depth_callback(self, message):
        self.depth_message = message

    def _capture_timer(self):
        self._try_capture(self.rgb_message,
                          self.depth_message if self.camera_mode == 'depth' else None)

    def _rack_pose(self):
        return 0.50 - self.rack_dy, -1.00 + self.rack_dx, self.rack_dyaw

    def _expected_tag_world(self, tag_id):
        rack_x, rack_y, rack_yaw = self._rack_pose()
        local = [TAG_LOCAL_X_M, SLOT_Y_M[tag_id], TAG_LOCAL_Z_M]
        c = math.cos(rack_yaw)
        s = math.sin(rack_yaw)
        position = [
            rack_x + c * local[0] - s * local[1],
            rack_y + s * local[0] + c * local[1],
            RACK_Z_M + local[2],
        ]
        # Tag axes follow the generated marker: image-right=-Y, image-down=-Z,
        # and the right-handed marker normal is +X in the rack frame.
        local_matrix = [[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]]
        rack_rotation = _rotation_matrix(_quat_from_yaw(rack_yaw))
        matrix = [
            [sum(rack_rotation[row][k] * local_matrix[k][column] for k in range(3))
             for column in range(3)]
            for row in range(3)
        ]
        return position, _quat_from_matrix(matrix)

    def _lookup_transform(self, target_frame, source_frame, stamp=None):
        query_time = rclpy.time.Time() if stamp is None else rclpy.time.Time.from_msg(stamp)
        # Gazebo publishes the robot TF only after the controller spawners
        # finish. The GUI wrapper starts this node as soon as RViz appears, so
        # allow the normal controller startup window here.
        deadline = time.monotonic() + 45.0
        while rclpy.ok() and time.monotonic() < deadline:
            try:
                return self.tf_buffer.lookup_transform(
                    target_frame, source_frame, query_time,
                    timeout=rclpy.duration.Duration(seconds=0.2),
                )
            except TransformException:
                rclpy.spin_once(self, timeout_sec=0.05)
        raise RuntimeError(f'no TF {target_frame} <- {source_frame}')

    @staticmethod
    def _transform_pose(transform, position, orientation):
        tf_q = [
            transform.transform.rotation.x,
            transform.transform.rotation.y,
            transform.transform.rotation.z,
            transform.transform.rotation.w,
        ]
        rotated = _rotate(tf_q, position)
        return [
            transform.transform.translation.x + rotated[0],
            transform.transform.translation.y + rotated[1],
            transform.transform.translation.z + rotated[2],
        ], _quat_mul(tf_q, orientation)

    def _expected_in_robot_frame(self):
        expected = {}
        # The launch file spawns the Gazebo model away from world origin, but
        # its temporary world -> link_base TF is identity for MoveIt. Convert
        # fixture truth through that known spawn pose instead of using the
        # identity TF as if it described the physical Gazebo model pose.
        spawn_q = _quat_from_yaw(ROBOT_SPAWN_YAW_RAD)
        inverse_spawn_q = [
            -spawn_q[0], -spawn_q[1], -spawn_q[2], spawn_q[3]
        ]
        for tag_id in (1, 2):
            position, orientation = self._expected_tag_world(tag_id)
            relative = [
                position[0] - ROBOT_SPAWN_XYZ_M[0],
                position[1] - ROBOT_SPAWN_XYZ_M[1],
                position[2] - ROBOT_SPAWN_XYZ_M[2],
            ]
            transformed_position = _rotate(inverse_spawn_q, relative)
            transformed_orientation = _quat_mul(inverse_spawn_q, orientation)
            pose = PoseStamped()
            pose.header.frame_id = self.robot_frame
            pose.header.stamp = self.get_clock().now().to_msg()
            pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = transformed_position
            pose.pose.orientation.x, pose.pose.orientation.y, pose.pose.orientation.z, pose.pose.orientation.w = transformed_orientation
            expected[tag_id] = pose
        return expected

    def _publish_provisional_input(self, expected):
        rack_position = [
            (expected[1].pose.position.x + expected[2].pose.position.x) / 2.0,
            (expected[1].pose.position.y + expected[2].pose.position.y) / 2.0,
        ]
        self.theoretical_bearing = math.atan2(rack_position[1], rack_position[0])
        noise_limit = math.radians(float(self.get_parameter('bearing_noise_deg').value))
        if not math.isfinite(noise_limit) or noise_limit < 0.0:
            raise RuntimeError('bearing_noise_deg must be nonnegative and finite')
        rng = random.Random(int(self.get_parameter('random_seed').value))
        noise = rng.uniform(-noise_limit, noise_limit)
        self.observation_bearing = self.theoretical_bearing + noise

        # The topic carries the desired TCP height. The provisional camera
        # mount places the optical origin 0.080 m below the horizontal TCP
        # pose used here; replace this offset after hand-eye measurement.
        target_height = (expected[1].pose.position.z + expected[2].pose.position.z) / 2.0
        tcp_height = target_height + CAMERA_EEF_VERTICAL_OFFSET_M
        message = PoseStamped()
        message.header.frame_id = self.robot_frame
        message.header.stamp = self.get_clock().now().to_msg()
        message.pose.position.z = tcp_height
        noisy_orientation = _quat_from_yaw(self.observation_bearing)
        message.pose.orientation.x, message.pose.orientation.y = noisy_orientation[0], noisy_orientation[1]
        message.pose.orientation.z, message.pose.orientation.w = noisy_orientation[2], noisy_orientation[3]
        self.input_publisher.publish(message)
        self.pre_observation_command = message
        self.get_logger().info(
            f'INPUT: {self.input_topic} bearing={self.observation_bearing:.6f} rad '
            f'(true={self.theoretical_bearing:.6f}, noise={noise:.6f}), '
            f'tcp_height={tcp_height:.6f} m'
        )

    def _wait_for_input(self):
        deadline = time.monotonic() + 5.0
        while rclpy.ok() and self.input_message is None and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
        if self.input_message is None:
            raise RuntimeError(f'timed out waiting for {self.input_topic}')
        if self.input_message.header.frame_id != self.robot_frame:
            raise RuntimeError(
                f'input frame {self.input_message.header.frame_id!r} does not match {self.robot_frame!r}'
            )
        quaternion = [
            self.input_message.pose.orientation.x,
            self.input_message.pose.orientation.y,
            self.input_message.pose.orientation.z,
            self.input_message.pose.orientation.w,
        ]
        norm = math.sqrt(sum(value * value for value in quaternion))
        if norm < 1e-12:
            raise RuntimeError('input orientation is zero')
        x, y, z, w = [value / norm for value in quaternion]
        self.observation_bearing = math.atan2(
            2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z)
        )

    def _wait_for_target_pose(self):
        deadline = time.monotonic() + 10.0
        while rclpy.ok() and self.target_pose_message is None and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
        if self.target_pose_message is None:
            raise RuntimeError(f'timed out waiting for {self.target_pose_topic}')
        if self.target_pose_message.header.frame_id != self.robot_frame:
            raise RuntimeError(
                f'target pose frame {self.target_pose_message.header.frame_id!r} '
                f'does not match {self.robot_frame!r}'
            )
        self.target_pose_command = self.target_pose_message

    def _current_tcp_pose(self):
        transform = self._lookup_transform(self.robot_frame, self.tcp_link)
        pose = PoseStamped()
        pose.header.frame_id = self.robot_frame
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = transform.transform.translation.x
        pose.pose.position.y = transform.transform.translation.y
        pose.pose.position.z = transform.transform.translation.z
        pose.pose.orientation = transform.transform.rotation
        return pose

    def _pre_observation_pose(self):
        if self.target_pose_command is None:
            raise RuntimeError('target pose has not been received')
        target = deepcopy(self.target_pose_command)
        target.header.stamp = self.get_clock().now().to_msg()
        return target

    def _wait_for_controllers(self):
        if not self.controller_client.wait_for_service(timeout_sec=45.0):
            raise RuntimeError('/controller_manager/list_controllers is unavailable')
        required = {'joint_state_broadcaster', 'uf850_traj_controller'}
        deadline = time.monotonic() + 45.0
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
                    # MoveIt's simple controller manager can discover the
                    # FollowJointTrajectory action a moment after the
                    # controller manager reports ACTIVE.
                    deadline_settle = time.monotonic() + 5.0
                    while rclpy.ok() and time.monotonic() < deadline_settle:
                        rclpy.spin_once(self, timeout_sec=0.1)
                    return
            time.sleep(0.2)
        raise RuntimeError(f'controllers are not active: observed={observed}')

    @staticmethod
    def _orientation_constraint(orientation, frame_id, link_name):
        constraint = OrientationConstraint()
        constraint.header.frame_id = frame_id
        constraint.link_name = link_name
        constraint.orientation = deepcopy(orientation)
        constraint.absolute_x_axis_tolerance = ORIENTATION_TOLERANCE_RAD
        constraint.absolute_y_axis_tolerance = ORIENTATION_TOLERANCE_RAD
        constraint.absolute_z_axis_tolerance = ORIENTATION_TOLERANCE_RAD
        constraint.parameterization = OrientationConstraint.ROTATION_VECTOR
        constraint.weight = 1.0
        constraints = Constraints(name='pre_observation_goal')
        constraints.orientation_constraints.append(constraint)
        return constraints

    def _pose_constraints(self, pose):
        constraints = self._orientation_constraint(pose.pose.orientation, pose.header.frame_id, self.tcp_link)
        position = PositionConstraint()
        position.header.frame_id = pose.header.frame_id
        position.link_name = self.tcp_link
        sphere = SolidPrimitive()
        sphere.type = SolidPrimitive.SPHERE
        sphere.dimensions = [POSITION_TOLERANCE_M]
        sphere_pose = Pose()
        sphere_pose.position = deepcopy(pose.pose.position)
        sphere_pose.orientation.w = 1.0
        position.constraint_region.primitives.append(sphere)
        position.constraint_region.primitive_poses.append(sphere_pose)
        position.weight = 1.0
        constraints.position_constraints.append(position)
        return constraints

    def _move_to_pre_observation(self, target):
        if not self.move_group_client.wait_for_server(timeout_sec=30.0):
            raise RuntimeError('/move_action is unavailable')
        goal = MoveGroup.Goal()
        goal.request.group_name = 'uf850'
        goal.request.num_planning_attempts = 10
        goal.request.allowed_planning_time = 10.0
        goal.request.max_velocity_scaling_factor = 0.05
        goal.request.max_acceleration_scaling_factor = 0.05
        goal.request.start_state.is_diff = True
        goal.request.goal_constraints.append(self._pose_constraints(target))
        goal.planning_options.plan_only = False
        goal.planning_options.replan = False
        goal.planning_options.planning_scene_diff.is_diff = True
        goal.planning_options.planning_scene_diff.robot_state.is_diff = True
        send_future = self.move_group_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=15.0)
        handle = send_future.result() if send_future.done() else None
        if handle is None or not handle.accepted:
            raise RuntimeError('MoveIt rejected the pre-observation goal')
        result_future = handle.get_result_async()
        deadline = time.monotonic() + 90.0
        while rclpy.ok() and not result_future.done() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
        if not result_future.done():
            raise RuntimeError('pre-observation execution timed out')
        result = result_future.result().result
        if result.error_code.val != MoveItErrorCodes.SUCCESS:
            raise RuntimeError(f'pre-observation MoveIt failed with code {result.error_code.val}')
        current = self._current_tcp_pose()
        position_error = math.sqrt(sum(
            (getattr(current.pose.position, axis) - getattr(target.pose.position, axis)) ** 2
            for axis in ('x', 'y', 'z')
        ))
        dot = abs(sum(
            left * right for left, right in zip(
                [current.pose.orientation.x, current.pose.orientation.y,
                 current.pose.orientation.z, current.pose.orientation.w],
                [target.pose.orientation.x, target.pose.orientation.y,
                 target.pose.orientation.z, target.pose.orientation.w],
            )
        ))
        orientation_error = 2.0 * math.acos(max(-1.0, min(1.0, dot)))
        target_bearing = math.atan2(target.pose.position.y, target.pose.position.x)
        measured_ray = _rotate(
            [current.pose.orientation.x, current.pose.orientation.y,
             current.pose.orientation.z, current.pose.orientation.w],
            [0.0, 0.0, 1.0],
        )
        target_ray = [math.cos(target_bearing), math.sin(target_bearing), 0.0]
        ray_dot = max(-1.0, min(1.0, sum(a * b for a, b in zip(measured_ray, target_ray))))
        self.measured_ray_error_rad = math.acos(ray_dot)
        if position_error > POSITION_TOLERANCE_M or orientation_error > FINAL_ORIENTATION_TOLERANCE_RAD:
            raise RuntimeError(
                f'pre-observation final error exceeds tolerance: '
                f'position={position_error:.5f} m, orientation={orientation_error:.5f} rad'
            )
        self.get_logger().info(
            f'PASS: pre-observation MoveIt execution '
            f'(position error={position_error:.5f} m, orientation error={orientation_error:.5f} rad, '
            f'pointing-ray error={self.measured_ray_error_rad:.5f} rad)'
        )

    @staticmethod
    def _image_to_bgr(message):
        if message is None or message.encoding not in ('rgb8', 'bgr8'):
            raise ValueError('RGB image must use rgb8 or bgr8 encoding')
        frame = np.frombuffer(message.data, dtype=np.uint8).reshape(message.height, message.step)
        frame = frame[:, :message.width * 3].reshape(message.height, message.width, 3).copy()
        if message.encoding == 'rgb8':
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return frame

    def _try_capture(self, rgb_message, depth_message):
        if not self.capture_enabled or self.camera_info is None or rgb_message is None:
            return
        stamp = _stamp_to_float(rgb_message.header.stamp)
        if self.last_processed_stamp == stamp:
            return
        if self.approach_phase is not None:
            period = 1.0 / float(self.get_parameter('observation_hz').value)
            if time.monotonic() - self.last_observation_wall < period:
                return
        if rgb_message.width != self.camera_info.width or rgb_message.height != self.camera_info.height:
            return
        if rgb_message.header.frame_id != self.camera_info.header.frame_id:
            return
        if self.camera_mode == 'depth':
            if depth_message is None or depth_message.header.frame_id != rgb_message.header.frame_id:
                return
            if abs(_stamp_to_float(depth_message.header.stamp) - _stamp_to_float(rgb_message.header.stamp)) > 0.15:
                return
        try:
            frame = self._image_to_bgr(rgb_message)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = cv2.aruco.detectMarkers(
                gray, self.dictionary, parameters=self.detector_params
            )
            ids_list = [] if ids is None else [int(value) for value in ids.flatten()]
            self.capture_frame_count += 1
            self.last_detected_ids = ids_list
            if self.capture_frame_count == 1 or self.capture_frame_count % 10 == 0:
                cv2.imwrite(str(self.output_dir / 'rgb_last.png'), frame)
            if not any(tag_id in ids_list for tag_id in (1, 2)):
                self.last_processed_stamp = stamp
                return
            k = np.array(self.camera_info.k, dtype=np.float64).reshape(3, 3)
            d = np.array(self.camera_info.d, dtype=np.float64)
            # Reject duplicate nested contours for the same marker ID.
            best = {}
            for index, tag_id in enumerate(ids_list):
                area = abs(cv2.contourArea(corners[index].reshape(-1, 2)))
                if tag_id not in best or area > best[tag_id][0]:
                    best[tag_id] = (area, index)
            indices = [value[1] for value in best.values()]
            corners = [corners[index] for index in indices]
            ids_list = [ids_list[index] for index in indices]
            ids = np.asarray(ids_list, dtype=np.int32).reshape(-1, 1)
            rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(corners, TAG_SIZE_M, k, d)
            pair_poses = {}
            if all(tag_id in ids_list for tag_id in (1, 2)):
                # Marker +X is image-right (-rack Y); +Y points upwards.
                # Fit the rigid two-tag board in one image, rather than
                # differencing independently estimated single-tag depths.
                pair_poses = estimate_rack_pair(
                    {tag_id: corners[ids_list.index(tag_id)] for tag_id in (1, 2)},
                    k, d, TAG_SIZE_M, SLOT_Y_M)
            # This code runs inside the image subscription callback. Do not
            # spin a nested executor while waiting for TF; skip this frame and
            # let the next synchronized frame try again.
            camera_to_robot = self.tf_buffer.lookup_transform(
                self.robot_frame,
                rgb_message.header.frame_id,
                rclpy.time.Time.from_msg(rgb_message.header.stamp),
            )
            self.last_processed_stamp = stamp
            self.last_observation_wall = time.monotonic()
            self.capture_error = None
            observed = {}
            for index, tag_id in enumerate(ids_list):
                if tag_id not in (1, 2):
                    continue
                tag_rotation, tag_translation = pair_poses.get(tag_id, (rvecs[index], tvecs[index]))
                rotation_matrix, _ = cv2.Rodrigues(tag_rotation.reshape(3))
                orientation = _quat_from_matrix(rotation_matrix.tolist())
                position, orientation = self._transform_pose(
                    camera_to_robot,
                    [float(value) for value in tag_translation.reshape(3)],
                    orientation,
                )
                pose = PoseStamped()
                pose.header.frame_id = self.robot_frame
                pose.header.stamp = rgb_message.header.stamp
                pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = position
                pose.pose.orientation.x, pose.pose.orientation.y, pose.pose.orientation.z, pose.pose.orientation.w = orientation
                observed[tag_id] = pose
            if depth_message is not None:
                if depth_message.encoding != '32FC1':
                    raise ValueError(f'unsupported depth encoding {depth_message.encoding}')
                depth = np.frombuffer(depth_message.data, dtype=np.float32).reshape(
                    depth_message.height, depth_message.step // 4
                )[:, :depth_message.width]
                valid = np.isfinite(depth) & (depth > 0.08) & (depth < 2.0)
                self.depth_quality = {
                    'valid_depth_fraction': float(valid.mean()),
                    'depth_min_m': float(depth[valid].min()) if valid.any() else None,
                    'depth_max_m': float(depth[valid].max()) if valid.any() else None,
                }
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)
            cv2.imwrite(str(self.output_dir / 'rgb_annotated.png'), frame)
            # The camera is held still after the move, so adjacent tags may
            # alternate as valid candidates from frame to frame. Keep the
            # latest pose for each required ID and complete once both have
            # been observed, even if they were not decoded in one image.
            self.observed.update(observed)
            if pair_poses:
                self.rack_observation = deepcopy(observed)
                self.rack_observation_wall = time.monotonic()
            if self.approach_phase is not None and self.task is not None:
                selected = self.task['tag_id']
                if selected in observed:
                    record = {
                        'tag_id': selected, 'action': self.task['action'],
                        'phase': self.approach_phase,
                        'camera_mode': self.camera_mode,
                        'arrival_monotonic_sec': time.monotonic(),
                        'pose': _pose_dict(observed[selected]),
                        'depth_quality': deepcopy(self.depth_quality),
                        'detected_ids': ids_list,
                    }
                    self.phase_observations.append(record)
                    self.all_observations.append(record)
                    with (self.output_dir / 'tag_observations.jsonl').open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps(record) + '\n')
                    message = String()
                    message.data = json.dumps(record)
                    self.observation_publisher.publish(message)
            if all(tag_id in self.observed for tag_id in (1, 2)):
                self.result = True
        except (TransformException, RuntimeError, ValueError) as error:
            self.capture_error = str(error)

    def _write_report(self):
        report = {
            'stage': 'pre_observation',
            'input_topic': self.input_topic,
            'robot_frame': self.robot_frame,
            'camera_mode': self.camera_mode,
            'input_command': _pose_dict(self.pre_observation_command),
            'target_pose_command': _pose_dict(self.target_pose_command),
            'target_pose_topic': self.target_pose_topic,
            'target_distance_m': math.hypot(
                self.target_pose_command.pose.position.x,
                self.target_pose_command.pose.position.y,
            ),
            'measured_pointing_ray_error_rad': self.measured_ray_error_rad,
            'theoretical_bearing_rad': self.theoretical_bearing,
            'observation_bearing_rad': self.observation_bearing,
            'expected_tag_poses_robot': {str(tag_id): _pose_dict(pose) for tag_id, pose in self.expected.items()},
            'observed_tag_poses_robot': {str(tag_id): _pose_dict(pose) for tag_id, pose in self.observed.items()},
            'depth_quality': self.depth_quality,
        }
        (self.output_dir / 'pre_observation_report.json').write_text(
            json.dumps(report, indent=2) + '\n', encoding='utf-8'
        )

    def _camera_mount(self):
        transform = self._lookup_transform(self.tcp_link, CAMERA_FRAME)
        self.camera_offset = [getattr(transform.transform.translation, axis)
                              for axis in ('x', 'y', 'z')]
        self.camera_rotation = [getattr(transform.transform.rotation, axis)
                                for axis in ('x', 'y', 'z', 'w')]

    def _update_rack_plane_normal(self):
        pair = self.rack_observation
        if pair is None or time.monotonic()-self.rack_observation_wall > float(self.get_parameter('observation_max_age_sec').value):
            raise RuntimeError('rack plane requires a fresh same-frame two-tag observation')
        first, second = pair[1].pose.position, pair[2].pose.position
        tangent = [second.x - first.x, second.y - first.y]
        separation = math.hypot(*tangent)
        if not 0.055 <= separation <= 0.09:
            raise RuntimeError(f'tag1/tag2 separation {separation:.4f} m is inconsistent with rack')
        candidate = [-tangent[1] / separation, tangent[0] / separation]
        if self.rack_plane_normal is not None and sum(
                candidate[i] * self.rack_plane_normal[i] for i in (0, 1)) < 0.0:
            candidate = [-value for value in candidate]
        elif self.rack_plane_normal is None:
            camera_tf = self._lookup_transform(self.robot_frame, CAMERA_FRAME)
            camera = camera_tf.transform.translation
            if candidate[0] * (camera.x - first.x) + candidate[1] * (camera.y - first.y) < 0.0:
                candidate = [-value for value in candidate]
        self.rack_plane_normal = candidate
        self.get_logger().info(
            f'RACK PLANE: normal_xy={candidate}, tag separation={separation:.4f} m'
        )

    @staticmethod
    def _quaternion(pose):
        return [getattr(pose.orientation, axis) for axis in ('x', 'y', 'z', 'w')]

    def _geometry(self, eef, tag):
        e = [getattr(eef.pose.position, axis) for axis in ('x', 'y', 'z')]
        q = self._quaternion(eef.pose)
        extension = _rotate(q, [0.0, 0.0, 1.0])
        front = [e[i] + FRONT_OFFSET_M * extension[i] for i in range(3)]
        camera = [e[i] + _rotate(q, self.camera_offset)[i] for i in range(3)]
        optical = _rotate(_quat_mul(q, self.camera_rotation), [0.0, 0.0, 1.0])
        t = [getattr(tag.pose.position, axis) for axis in ('x', 'y', 'z')]
        if self.rack_plane_normal is None:
            normal = _rotate(self._quaternion(tag.pose), [0.0, 0.0, 1.0])
            if sum(normal[i] * (camera[i] - t[i]) for i in range(3)) < 0.0:
                normal = [-x for x in normal]
        else:
            normal = [self.rack_plane_normal[0], self.rack_plane_normal[1], 0.0]
        horizontal = _normalise(normal[:2])
        signed_distance = sum(normal[i] * (front[i] - t[i]) for i in range(3))
        lateral = abs((front[0] - t[0]) * horizontal[1] -
                      (front[1] - t[1]) * horizontal[0])
        return {
            'front': front, 'camera': camera, 'optical': optical,
            'normal': normal, 'horizontal_normal': horizontal,
            'distance_m': signed_distance, 'lateral_m': lateral,
            'sight_angle_rad': _angle(optical, [t[i] - camera[i] for i in range(3)]),
        }

    def _approach_target(self, tag, distance):
        initial = self.approach_start_pose
        base_q = self._quaternion(initial.pose)
        t = [getattr(tag.pose.position, axis) for axis in ('x', 'y', 'z')]
        reference = self._geometry(initial, tag)
        n = reference['horizontal_normal']
        front_xy = [t[i] + distance * n[i] for i in (0, 1)]
        best = None
        # A world-Z rotation preserves the measured height, roll and pitch.
        # Search it with the real camera offset, not the gripper axis.
        for index in range(721):
            delta = -math.pi + index * 2.0 * math.pi / 720.0
            q = _quat_mul(_quat_from_yaw(delta), base_q)
            direction = _rotate(q, [0.0, 0.0, 1.0])
            e = [front_xy[0] - FRONT_OFFSET_M * direction[0],
                 front_xy[1] - FRONT_OFFSET_M * direction[1],
                 initial.pose.position.z]
            camera_offset = _rotate(q, self.camera_offset)
            camera = [e[i] + camera_offset[i] for i in range(3)]
            optical = _rotate(_quat_mul(q, self.camera_rotation), [0.0, 0.0, 1.0])
            error = _angle(optical, [t[i] - camera[i] for i in range(3)])
            if best is None or error < best[0]:
                best = (error, q, e)
        tolerance = float(self.get_parameter('visibility_tolerance_rad').value)
        if best[0] > tolerance:
            raise RuntimeError(f'camera cannot face tag at fixed height/tilt: best angle={best[0]:.3f} rad')
        target = PoseStamped()
        target.header.frame_id = self.robot_frame
        target.header.stamp = self.get_clock().now().to_msg()
        target.pose.position.x, target.pose.position.y, target.pose.position.z = best[2]
        target.pose.orientation.x, target.pose.orientation.y, target.pose.orientation.z, target.pose.orientation.w = best[1]
        return target

    def _approach_constraints(self, tag, normal_ray=None):
        constraints = Constraints(name='approach_path')
        orientation = OrientationConstraint()
        orientation.header.frame_id = self.robot_frame
        orientation.link_name = self.tcp_link
        orientation.orientation = deepcopy(self.approach_start_pose.pose.orientation)
        # MoveIt's constraint parameterization couples world-yaw and local
        # tilt at this posture. Use a planning envelope, then reject any
        # returned trajectory whose FK exceeds the actual tilt tolerance.
        orientation.absolute_x_axis_tolerance = 0.15
        orientation.absolute_y_axis_tolerance = 0.15
        orientation.absolute_z_axis_tolerance = math.pi
        orientation.parameterization = OrientationConstraint.ROTATION_VECTOR
        orientation.weight = 1.0
        constraints.orientation_constraints.append(orientation)

        height = PositionConstraint()
        height.header.frame_id = self.robot_frame
        height.link_name = self.tcp_link
        slab = SolidPrimitive()
        slab.type = SolidPrimitive.BOX
        slab.dimensions = [4.0, 4.0, 2.0 * float(self.get_parameter('height_tolerance_m').value)]
        slab_pose = Pose()
        slab_pose.position.z = self.approach_start_pose.pose.position.z
        slab_pose.orientation.w = 1.0
        height.constraint_region.primitives.append(slab)
        height.constraint_region.primitive_poses.append(slab_pose)
        height.weight = 1.0
        constraints.position_constraints.append(height)

        visibility = VisibilityConstraint()
        visibility.target_radius = TAG_SIZE_M / 2.0
        visibility.target_pose = deepcopy(tag)
        visibility.cone_sides = 12
        visibility.sensor_pose.header.frame_id = self.tcp_link
        visibility.sensor_pose.pose.position.x, visibility.sensor_pose.pose.position.y, visibility.sensor_pose.pose.position.z = self.camera_offset
        visibility.sensor_pose.pose.orientation.x, visibility.sensor_pose.pose.orientation.y, visibility.sensor_pose.pose.orientation.z, visibility.sensor_pose.pose.orientation.w = self.camera_rotation
        visibility.sensor_view_direction = VisibilityConstraint.SENSOR_Z
        visibility.max_view_angle = 0.7
        visibility.max_range_angle = float(self.get_parameter('visibility_tolerance_rad').value)
        visibility.weight = 1.0
        if bool(self.get_parameter('moveit_visibility_constraint').value):
            constraints.visibility_constraints.append(visibility)

        if normal_ray is not None:
            start_front, end_front, horizontal_normal = normal_ray
            corridor = PositionConstraint()
            corridor.header.frame_id = self.robot_frame
            corridor.link_name = self.tcp_link
            corridor.target_point_offset.z = FRONT_OFFSET_M
            box = SolidPrimitive()
            box.type = SolidPrimitive.BOX
            box.dimensions = [math.dist(start_front[:2], end_front[:2]) + 0.04,
                              2.0 * float(self.get_parameter('ray_width_m').value), 0.05]
            box_pose = Pose()
            box_pose.position.x = (start_front[0] + end_front[0]) / 2.0
            box_pose.position.y = (start_front[1] + end_front[1]) / 2.0
            box_pose.position.z = (start_front[2] + end_front[2]) / 2.0
            box_pose.orientation.z = math.sin(math.atan2(horizontal_normal[1], horizontal_normal[0]) / 2.0)
            box_pose.orientation.w = math.cos(math.atan2(horizontal_normal[1], horizontal_normal[0]) / 2.0)
            corridor.constraint_region.primitives.append(box)
            corridor.constraint_region.primitive_poses.append(box_pose)
            corridor.weight = 1.0
            constraints.position_constraints.append(corridor)
        return constraints

    @staticmethod
    def _record_pose(record):
        data = record['pose']
        pose = PoseStamped()
        pose.header.frame_id = data['frame_id']
        seconds = data['stamp_sec']
        pose.header.stamp.sec = int(seconds)
        pose.header.stamp.nanosec = int(round((seconds - int(seconds)) * 1e9))
        pose.pose.position.x = data['position_m']['x']
        pose.pose.position.y = data['position_m']['y']
        pose.pose.position.z = data['position_m']['z']
        (pose.pose.orientation.x, pose.pose.orientation.y,
         pose.pose.orientation.z, pose.pose.orientation.w) = data['orientation_xyzw']
        return pose

    def _fresh_observation(self, records, label):
        if not records:
            raise RuntimeError(f'{label}: no selected-tag observation')
        record = records[-1]
        age = time.monotonic() - record['arrival_monotonic_sec']
        if age > float(self.get_parameter('observation_max_age_sec').value):
            raise RuntimeError(
                f'{label}: selected-tag observation stale by {age:.3f} s; '
                f'last_detected_ids={self.last_detected_ids}, capture_error={self.capture_error}'
            )
        pair_age = time.monotonic()-self.rack_observation_wall
        if self.rack_observation is None or pair_age > float(self.get_parameter('observation_max_age_sec').value):
            raise RuntimeError(f'{label}: no fresh same-frame two-tag rack pose')
        return deepcopy(self.rack_observation[self.task['tag_id']])

    def _record_execution_sample(self, tag, samples):
        try:
            current = self._current_tcp_pose()
            geometry = self._geometry(current, tag)
            initial_q = self._quaternion(self.approach_start_pose.pose)
            current_q = self._quaternion(current.pose)
            samples.append({
                'height_error_m': abs(current.pose.position.z - self.approach_start_pose.pose.position.z),
                'tilt_error_rad': _tilt_delta(initial_q, current_q),
                'sight_angle_rad': geometry['sight_angle_rad'],
                'front_plane_distance_m': geometry['distance_m'],
                'ray_lateral_error_m': geometry['lateral_m'],
            })
            self.gui_execution_metrics = dict(samples[-1])
        except (RuntimeError, TransformException):
            pass

    def _validate_planned_path(self, trajectory, tag, ray):
        if not self.fk_client.wait_for_service(timeout_sec=10.0):
            raise RuntimeError('/compute_fk is unavailable for whole-path validation')
        max_height = float(self.get_parameter('height_tolerance_m').value)
        max_tilt = float(self.get_parameter('tilt_tolerance_rad').value)
        max_sight = float(self.get_parameter('visibility_tolerance_rad').value)
        max_ray = float(self.get_parameter('ray_width_m').value)
        baseline = self._quaternion(self.approach_start_pose.pose)
        worst = {'height_m': 0.0, 'tilt_rad': 0.0, 'sight_rad': 0.0, 'ray_m': 0.0}
        for index, point in enumerate(trajectory.joint_trajectory.points):
            request = GetPositionFK.Request()
            request.header.frame_id = self.robot_frame
            request.fk_link_names = [self.tcp_link]
            request.robot_state.joint_state.name = list(trajectory.joint_trajectory.joint_names)
            request.robot_state.joint_state.position = list(point.positions)
            future = self.fk_client.call_async(request)
            rclpy.spin_until_future_complete(self, future, timeout_sec=3.0)
            response = future.result() if future.done() else None
            if (response is None or response.error_code.val != MoveItErrorCodes.SUCCESS or
                    len(response.pose_stamped) != 1):
                raise RuntimeError(f'FK failed at trajectory point {index}')
            pose = response.pose_stamped[0]
            geometry = self._geometry(pose, tag)
            height = abs(pose.pose.position.z - self.approach_start_pose.pose.position.z)
            tilt = _tilt_delta(self._quaternion(pose.pose), baseline)
            sight = geometry['sight_angle_rad']
            lateral = geometry['lateral_m'] if ray is not None else 0.0
            worst['height_m'] = max(worst['height_m'], height)
            worst['tilt_rad'] = max(worst['tilt_rad'], tilt)
            worst['sight_rad'] = max(worst['sight_rad'], sight)
            worst['ray_m'] = max(worst['ray_m'], lateral)
            if (height > max_height + 0.002 or tilt > max_tilt + 0.02 or
                    sight > max_sight or lateral > max_ray + 0.005):
                raise RuntimeError(
                    f'planned path violates constraints at point {index}: '
                    f'height={height:.3f} m, tilt={tilt:.3f} rad, '
                    f'sight={sight:.3f} rad, ray={lateral:.3f} m'
                )
        return worst

    def _plan_candidate(self, goal, label):
        send = self.move_group_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send, timeout_sec=15.0)
        handle = send.result() if send.done() else None
        if handle is None or not handle.accepted:
            raise RuntimeError(f'{label}: MoveIt rejected planning request')
        future = handle.get_result_async()
        rclpy.spin_until_future_complete(self, future, timeout_sec=45.0)
        if not future.done():
            raise RuntimeError(f'{label}: planning timed out')
        response = future.result().result
        if response.error_code.val != MoveItErrorCodes.SUCCESS:
            raise RuntimeError(f'{label}: planning failed, MoveIt code {response.error_code.val}')
        return response

    def _cartesian_candidate(self, label, target, tag, ray):
        if not self.cartesian_client.wait_for_service(timeout_sec=10.0):
            raise RuntimeError('/compute_cartesian_path is unavailable')
        start = self._current_tcp_pose()
        start_q = self._quaternion(start.pose)
        target_q = self._quaternion(target.pose)
        relative = _quat_mul(target_q, _quat_conjugate(start_q))
        yaw_change = math.atan2(2.0 * (relative[3] * relative[2] + relative[0] * relative[1]),
                                1.0 - 2.0 * (relative[1] ** 2 + relative[2] ** 2))
        request = GetCartesianPath.Request()
        request.header.frame_id = self.robot_frame
        request.start_state.is_diff = True
        request.group_name = 'uf850'
        request.link_name = self.tcp_link
        request.max_step = 0.01
        request.jump_threshold = 0.0
        request.avoid_collisions = True
        # Explicit world-yaw interpolation keeps measured roll/pitch and
        # link_eef height fixed, including between the coarse anchors.
        for index in range(1, 21):
            alpha = index / 20.0
            waypoint = Pose()
            waypoint.position.x = start.pose.position.x + alpha * (target.pose.position.x - start.pose.position.x)
            waypoint.position.y = start.pose.position.y + alpha * (target.pose.position.y - start.pose.position.y)
            waypoint.position.z = self.approach_start_pose.pose.position.z
            q = _quat_mul(_quat_from_yaw(alpha * yaw_change), start_q)
            waypoint.orientation.x, waypoint.orientation.y, waypoint.orientation.z, waypoint.orientation.w = q
            request.waypoints.append(waypoint)
        constraints = self._approach_constraints(tag, ray)
        constraints.orientation_constraints.clear()
        request.path_constraints = constraints
        request.max_velocity_scaling_factor = 0.04
        request.max_acceleration_scaling_factor = 0.04
        planning_started = time.monotonic()
        future = self.cartesian_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=45.0)
        response = future.result() if future.done() else None
        if response is None:
            raise RuntimeError(f'{label}: Cartesian planning timed out')
        if response.error_code.val != MoveItErrorCodes.SUCCESS or response.fraction < 0.999:
            raise RuntimeError(
                f'{label}: Cartesian path incomplete (fraction={response.fraction:.4f}, '
                f'code={response.error_code.val})'
            )
        return SimpleNamespace(
            planned_trajectory=response.solution,
            planning_time=time.monotonic() - planning_started,
        )

    def _plan_and_execute_approach(self, label, target, tag, ray=None):
        self.current_stage = 'realignment' if label.startswith('realignment_') else label
        self.planning_attempts[label] = 0
        ik_solution = None
        if self.ik_client.wait_for_service(timeout_sec=5.0):
            reference_front = self._geometry(target, tag)['front']
            for yaw_offset in (0.0, -0.025, 0.025, -0.05, 0.05,
                               -0.10, 0.10, -0.15, 0.15, -0.20, 0.20):
                candidate = deepcopy(target)
                if yaw_offset:
                    q = _quat_mul(_quat_from_yaw(yaw_offset), self._quaternion(target.pose))
                    extension = _rotate(q, [0.0, 0.0, 1.0])
                    candidate.pose.position.x = reference_front[0] - FRONT_OFFSET_M * extension[0]
                    candidate.pose.position.y = reference_front[1] - FRONT_OFFSET_M * extension[1]
                    (candidate.pose.orientation.x, candidate.pose.orientation.y,
                     candidate.pose.orientation.z, candidate.pose.orientation.w) = q
                if (self._geometry(candidate, tag)['sight_angle_rad'] >
                        float(self.get_parameter('visibility_tolerance_rad').value)):
                    continue
                request = GetPositionIK.Request()
                request.ik_request.group_name = 'uf850'
                request.ik_request.ik_link_name = self.tcp_link
                request.ik_request.pose_stamped = candidate
                request.ik_request.robot_state.is_diff = True
                request.ik_request.avoid_collisions = True
                request.ik_request.timeout.sec = 1
                diagnostic = self.ik_client.call_async(request)
                rclpy.spin_until_future_complete(self, diagnostic, timeout_sec=2.0)
                if diagnostic.done() and diagnostic.result() is not None:
                    self.get_logger().info(
                        f'{label}: endpoint IK yaw_offset={yaw_offset:.3f} rad '
                        f'code={diagnostic.result().error_code.val}'
                    )
                    if diagnostic.result().error_code.val == MoveItErrorCodes.SUCCESS:
                        ik_solution = diagnostic.result().solution.joint_state
                        target = candidate
                        break
        if ik_solution is None:
            raise RuntimeError(f'{label}: no collision-free endpoint IK solution')
        goal = MoveGroup.Goal()
        goal.request.group_name = 'uf850'
        goal.request.num_planning_attempts = 20
        goal.request.allowed_planning_time = 20.0
        goal.request.max_velocity_scaling_factor = 0.04
        goal.request.max_acceleration_scaling_factor = 0.04
        goal.request.start_state.is_diff = True
        joint_goal = Constraints(name=f'{label}_ik_goal')
        for name, position in zip(ik_solution.name, ik_solution.position):
            if name.startswith('joint'):
                constraint = JointConstraint()
                constraint.joint_name = name
                constraint.position = position
                constraint.tolerance_above = 0.005
                constraint.tolerance_below = 0.005
                constraint.weight = 1.0
                joint_goal.joint_constraints.append(constraint)
        if not joint_goal.joint_constraints:
            raise RuntimeError(f'{label}: IK returned no arm joints')
        goal.request.goal_constraints.append(joint_goal)
        goal.request.path_constraints = self._approach_constraints(tag, ray)
        goal.planning_options.plan_only = True
        goal.planning_options.replan = False
        goal.planning_options.planning_scene_diff.is_diff = True
        goal.planning_options.planning_scene_diff.robot_state.is_diff = True
        last_error = None
        planning_method = 'ompl_path_constraints'
        for attempt in range(8):
            try:
                self.planning_attempts[label] += 1
                response = self._plan_candidate(goal, label)
                points = len(response.planned_trajectory.joint_trajectory.points)
                if points < 2:
                    raise RuntimeError(f'{label}: incomplete/empty trajectory ({points} points)')
                planned_worst = self._validate_planned_path(response.planned_trajectory, tag, ray)
                break
            except RuntimeError as error:
                last_error = error
                self.get_logger().warning(f'{label}: candidate {attempt + 1}/8 rejected: {error}')
        else:
            planning_method = 'cartesian_waypoints'
            self.get_logger().warning(
                f'{label}: constrained OMPL candidates failed ({last_error}); '
                'trying constant-height/tilt Cartesian waypoints'
            )
            self.planning_attempts[label] += 1
            response = self._cartesian_candidate(label, target, tag, ray)
            points = len(response.planned_trajectory.joint_trajectory.points)
            if points < 2:
                raise RuntimeError(f'{label}: Cartesian path returned too few points')
            planned_worst = self._validate_planned_path(response.planned_trajectory, tag, ray)
        self.get_logger().info(f'{label}: planned {points} points; executing frozen target')

        execute = ExecuteTrajectory.Goal()
        execute.trajectory = response.planned_trajectory
        send = self.execute_client.send_goal_async(execute)
        rclpy.spin_until_future_complete(self, send, timeout_sec=10.0)
        handle = send.result() if send.done() else None
        if handle is None or not handle.accepted:
            raise RuntimeError(f'{label}: MoveIt rejected trajectory execution')
        self.approach_phase = label
        self.phase_observations = []
        samples = []
        future = handle.get_result_async()
        deadline = time.monotonic() + 90.0
        while rclpy.ok() and not future.done() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
            self._record_execution_sample(tag, samples)
        if not future.done():
            self.approach_phase = None
            raise RuntimeError(f'{label}: execution timed out')
        result = future.result().result
        if result.error_code.val != MoveItErrorCodes.SUCCESS:
            self.approach_phase = None
            raise RuntimeError(f'{label}: execution failed, MoveIt code {result.error_code.val}')
        settle_deadline = time.monotonic() + float(self.get_parameter('post_move_observation_sec').value)
        while rclpy.ok() and time.monotonic() < settle_deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.approach_phase = None
        self._record_execution_sample(tag, samples)
        actual = self._current_tcp_pose()
        final = self._geometry(actual, tag)
        if (abs(actual.pose.position.z - self.approach_start_pose.pose.position.z) >
                float(self.get_parameter('height_tolerance_m').value) or
                _tilt_delta(self._quaternion(actual.pose),
                            self._quaternion(self.approach_start_pose.pose)) >
                float(self.get_parameter('tilt_tolerance_rad').value)):
            raise RuntimeError(f'{label}: final height/tilt constraint was violated')
        self.phase_metrics[label] = {
            'planning_method': planning_method,
            'planning_attempts': self.planning_attempts[label],
            'planning_retries_before_execution': max(0, self.planning_attempts[label] - 1),
            'online_replans': 0,
            'planning_time_sec': response.planning_time,
            'trajectory_points': points,
            'worst_planned_path_errors': planned_worst,
            'target_pose': _pose_dict(target),
            'tag_snapshot': _pose_dict(tag),
            'observations_during_execution': len(self.phase_observations),
            'final_tcp_pose': _pose_dict(actual),
            'final_geometry': final,
            'max_sampled_height_error_m': max((x['height_error_m'] for x in samples), default=None),
            'max_sampled_tilt_error_rad': max((x['tilt_error_rad'] for x in samples), default=None),
            'max_sampled_sight_angle_rad': max((x['sight_angle_rad'] for x in samples), default=None),
            'max_sampled_ray_lateral_error_m': max((x['ray_lateral_error_m'] for x in samples), default=None),
        }
        self.get_logger().info(
            f'{label}: execution PASS; front plane distance={final["distance_m"]:.4f} m, '
            f'ray lateral={final["lateral_m"]:.4f} m, '
            f'sight angle={final["sight_angle_rad"]:.3f} rad; '
            f'valid updates={len(self.phase_observations)}'
        )
        return actual, list(self.phase_observations)

    def _run_approach(self):
        if not self.execute_client.wait_for_server(timeout_sec=30.0):
            raise RuntimeError('/execute_trajectory is unavailable')
        if self.task is None:
            provisional = String()
            provisional.data = json.dumps({
                'tag_id': int(self.get_parameter('demo_tag_id').value),
                'action': str(self.get_parameter('demo_action').value),
            })
            self.task_publisher.publish(provisional)
            deadline = time.monotonic() + 2.0
            while self.task is None and time.monotonic() < deadline:
                rclpy.spin_once(self, timeout_sec=0.05)
        if self.task is None:
            raise RuntimeError('no valid approach task')
        selected = self.task['tag_id']
        if selected not in self.observed:
            raise RuntimeError(f'tag {selected} was not detected in pre-observation')
        self._camera_mount()
        self._update_rack_plane_normal()
        self.approach_start_pose = self._current_tcp_pose()
        tag_initial = deepcopy(self.rack_observation[selected])
        self.get_logger().info(
            f'APPROACH START: geometry={self._geometry(self.approach_start_pose, tag_initial)}, '
            f'camera_mount_xyz={self.camera_offset}, camera_mount_xyzw={self.camera_rotation}'
        )
        align_target = self._approach_target(tag_initial, ALIGNMENT_DISTANCE_M)
        self.get_logger().info(
            f'ALIGN TARGET: pose={_pose_dict(align_target)}, '
            f'geometry={self._geometry(align_target, tag_initial)}, '
            f'tilt_delta={_tilt_delta(self._quaternion(align_target.pose), self._quaternion(self.approach_start_pose.pose)):.4f}'
        )
        self.get_logger().info(f'APPROACH TASK: {self.task}; segment 1 alignment at 0.40 m')
        align_actual, updates = self._plan_and_execute_approach('alignment', align_target, tag_initial)
        max_corrections = int(self.get_parameter('max_realignment_attempts').value)
        if not 0 <= max_corrections <= 5:
            raise RuntimeError('max_realignment_attempts must be between 0 and 5')
        ray_width = float(self.get_parameter('ray_width_m').value)
        for correction in range(max_corrections+1):
            tag_second = self._fresh_observation(updates, 'alignment')
            self._update_rack_plane_normal()
            geometry = self._geometry(align_actual, tag_second)
            normal = geometry['horizontal_normal']
            start_front = geometry['front']
            ray_error = geometry['lateral_m']
            self.gui_execution_metrics.update({
                'ray_lateral_error_m': ray_error,
                'front_plane_distance_m': geometry['distance_m'],
                'realignment_attempts': correction,
            })
            self.get_logger().info(f'UPDATED RACK: ray error={ray_error:.4f} m, correction={correction}/{max_corrections}')
            if ray_error <= ray_width and abs(geometry['distance_m']-ALIGNMENT_DISTANCE_M) <= ray_width:
                break
            if correction == max_corrections:
                raise RuntimeError(f'updated normal ray misses alignment point by {ray_error:.4f} m '
                                   f'(limit {ray_width:.4f} m); realignment retry limit reached')
            self.current_stage = 'realignment'
            self._publish_gui_status()
            target = self._approach_target(tag_second, ALIGNMENT_DISTANCE_M)
            align_actual, updates = self._plan_and_execute_approach(
                f'realignment_{correction+1}', target, tag_second)
        final_target = self._approach_target(tag_second, FINAL_DISTANCE_M)
        end_front = self._geometry(final_target, tag_second)['front']
        self.get_logger().info('SEGMENT 2: perpendicular approach to 0.10 m with updated frozen tag pose')
        final_actual, _ = self._plan_and_execute_approach(
            'perpendicular', final_target, tag_second,
            (start_front, end_front, normal),
        )
        final = self._geometry(final_actual, tag_second)
        if (abs(final['distance_m'] - FINAL_DISTANCE_M) > 0.025 or
                final['lateral_m'] > ray_width or
                final['sight_angle_rad'] > float(self.get_parameter('visibility_tolerance_rad').value)):
            raise RuntimeError(f'final approach geometry outside tolerance: {final}')
        report = {
            'stage': 'approach', 'task': self.task,
            'camera_mode': self.camera_mode,
            'front_offset_m': FRONT_OFFSET_M,
            'alignment_distance_m': ALIGNMENT_DISTANCE_M,
            'final_distance_m': FINAL_DISTANCE_M,
            'segments': self.phase_metrics,
            'observations': self.all_observations,
            'acceptance_tag_snapshot': _pose_dict(tag_second),
        }
        report_path = self.output_dir / 'approach_report.json'
        report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        self.get_logger().info(f'PASS: APPROACH_COMPLETE; report={report_path}')

    def run(self):
        self.current_stage = 'pre_observation_setup'
        self.expected = self._expected_in_robot_frame()
        self.get_logger().info('THEORETICAL EXPECTED TAG POSES (robot frame):')
        for tag_id in (1, 2):
            self.get_logger().info(f'  tag{tag_id}: {_pose_dict(self.expected[tag_id])}')
        self._publish_provisional_input(self.expected)
        self._wait_for_input()
        self._wait_for_target_pose()
        self._wait_for_controllers()
        target = self._pre_observation_pose()
        self.get_logger().info(
            f'PRE_OBSERVATION: target TCP '
            f'({target.pose.position.x:.6f}, {target.pose.position.y:.6f}) m, '
            f'z={target.pose.position.z:.6f} m, aligning bearing '
            f'{self.observation_bearing:.6f} rad'
        )
        self.current_stage = 'pre_observation_move'
        self._move_to_pre_observation(target)
        deadline = time.monotonic() + self.settle_sec
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=min(0.1, deadline - time.monotonic()))
        self.capture_enabled = True
        self.current_stage = 'pre_observation_capture'
        detection_deadline = time.monotonic() + self.timeout_sec
        while rclpy.ok() and self.result is None and time.monotonic() < detection_deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
        if self.result is None:
            reason = self.capture_error or (
                'did not observe both tag IDs 1 and 2 '
                f'(frames={self.capture_frame_count}, last_detected_ids={self.last_detected_ids})'
            )
            raise RuntimeError(f'pre-observation visual capture failed: {reason}')
        self._write_report()
        self.get_logger().info('OBSERVED TAG POSES (robot frame):')
        for tag_id in (1, 2):
            self.get_logger().info(f'  tag{tag_id}: {_pose_dict(self.observed[tag_id])}')
        self.get_logger().info(
            'PASS: PRE_OBSERVATION_COMPLETE; both tag1 and tag2 were detected '
            f'and transformed into {self.robot_frame}'
        )
        self.get_logger().info(f'Report: {self.output_dir / "pre_observation_report.json"}')
        self._run_approach()
        self.current_stage = 'complete'

    def _write_trial_summary(self, success, reason=None):
        summary = {
            'success': bool(success),
            'failure_stage': None if success else self.current_stage,
            'failure_reason': reason,
            'camera_mode': self.camera_mode,
            'random_seed': int(self.get_parameter('random_seed').value),
            'duration_sec': time.monotonic() - self.run_start_monotonic,
            'planning_attempts': self.planning_attempts,
            'planning_retries_before_execution': sum(
                max(0, attempts - 1) for attempts in self.planning_attempts.values()
            ),
            'online_replans': 0,
            'segments_completed': self.phase_metrics,
            'task': self.task,
            'expected_tag_poses_robot': {
                str(tag_id): _pose_dict(pose) for tag_id, pose in self.expected.items()
            },
            'observation_count': len(self.all_observations),
            'latest_capture_error': self.capture_error,
        }
        (self.output_dir / 'trial_summary.json').write_text(
            json.dumps(summary, indent=2) + '\n', encoding='utf-8'
        )


def main():
    rclpy.init()
    node = PreObservationDemo()
    try:
        node.run()
    except Exception as error:
        node.get_logger().error(f'FAIL: OBSERVATION_OR_APPROACH_INCOMPLETE: {error}')
        node.gui_final = ('FAILED', str(error))
        node._publish_gui_status()
        node._write_trial_summary(False, str(error))
        return_code = 1
    else:
        node.gui_final = ('SUCCEEDED', 'Visual approach completed; no physical grasp or placement')
        node._publish_gui_status()
        node._write_trial_summary(True)
        return_code = 0
    finally:
        try:
            if bool(node.get_parameter('keep_status_alive').value):
                while rclpy.ok():
                    rclpy.spin_once(node, timeout_sec=0.2)
        except KeyboardInterrupt:
            pass
        node.destroy_node()
        rclpy.shutdown()
    raise SystemExit(return_code)


if __name__ == '__main__':
    main()

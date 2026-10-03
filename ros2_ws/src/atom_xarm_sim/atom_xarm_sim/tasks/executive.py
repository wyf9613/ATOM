"""One task node composes reusable capabilities using named recipes."""
from copy import deepcopy
import json
import math
from pathlib import Path
import time
import cv2
from geometry_msgs.msg import (
    PoseStamped,
)
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String
from tf2_ros import (
    Buffer,
    TransformListener,
)
from atom_xarm_sim.camera_experiment import (
    TAG_FAMILY,
)
from atom_xarm_sim.geometry import (
    INPUT_TOPIC,
    TARGET_POSE_TOPIC,
    ROBOT_FRAME,
    TCP_LINK,
    FRONT_OFFSET_M,
    ALIGNMENT_DISTANCE_M,
    FINAL_DISTANCE_M,
    _tilt_delta,
    _pose_dict,
)

from atom_xarm_sim.perception.observer import RackObserver
from atom_xarm_sim.planning.approach import ApproachMotion
from atom_xarm_sim.planning.clients import MotionClients
from atom_xarm_sim.simulation.inputs import SimulationInputs
from atom_xarm_sim.telemetry.task_status import TaskTelemetry
from atom_xarm_sim.tasks.recipes import CAPABILITY_STEPS, execute_recipe
from atom_xarm_sim.gripper.control import GripperControl

class TaskExecutive(GripperControl, RackObserver, ApproachMotion, SimulationInputs, TaskTelemetry, Node):
    def __init__(self):
        super().__init__('atom_task_executive')
        self.initialize_gripper_control()
        self.run_start_monotonic = time.monotonic()
        self.current_stage = 'initialization'
        self.planning_attempts = {}
        self.declare_parameter('camera_mode', 'rgb')
        self.declare_parameter('depth_fusion_enabled', True)
        self.declare_parameter('depth_registered', False)
        self.declare_parameter('task_recipe', 'visual_approach')
        self.declare_parameter('keep_status_alive', False)
        self.declare_parameter('robot_frame', ROBOT_FRAME)
        self.declare_parameter('tcp_link', TCP_LINK)
        self.declare_parameter('input_topic', INPUT_TOPIC)
        self.declare_parameter('target_pose_topic', TARGET_POSE_TOPIC)
        self.declare_parameter('rack_dx_m', 0.0)
        self.declare_parameter('rack_dy_m', 0.0)
        self.declare_parameter('rack_dyaw_rad', 0.0)
        self.declare_parameter('random_seed', 20260925)
        self.declare_parameter('xy_noise_m', 0.025)
        self.declare_parameter('rack_tag_ids', [0, 1, 2, 3])
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

        self.rack_tag_ids = tuple(int(value) for value in self.get_parameter('rack_tag_ids').value)
        if len(set(self.rack_tag_ids)) != len(self.rack_tag_ids) or len(self.rack_tag_ids) < 2 or any(tag not in range(4) for tag in self.rack_tag_ids):
            raise RuntimeError('rack_tag_ids must contain at least two distinct scene tag IDs (0..3)')
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
        self.motion_clients = MotionClients(self, cartesian=True, kinematics=True)
        self.motion_clients.bind(self)


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
        self.rgb_pnp_observed = {}
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

    def _input_callback(self, message):
        self.input_message = message

    def _target_pose_callback(self, message):
        self.target_pose_message = message

    def _task_callback(self, message):
        try:
            task = json.loads(message.data)
            if 'rack_tag_ids' in task and list(task['rack_tag_ids']) != list(self.rack_tag_ids):
                raise ValueError('task rack membership does not match this configured rack')
            tag_id = int(task['tag_id'])
            action = str(task['action'])
            if tag_id not in self.rack_tag_ids or action not in ('pick', 'place'):
                raise ValueError('tag_id must belong to rack_tag_ids; action must be pick or place')
            if self.current_stage not in ('initialization', 'pre_observation_setup') and self.task != {'tag_id': tag_id, 'action': action}:
                raise ValueError('cannot change the target during an active observation/approach')
            self.task = {'tag_id': tag_id, 'action': action}
        except (ValueError, KeyError, TypeError) as error:
            self.get_logger().warning(f'Ignoring malformed approach task: {error}')

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
        xy = [self.input_message.pose.position.x, self.input_message.pose.position.y]
        if not all(math.isfinite(value) for value in xy) or math.hypot(*xy) < 1e-6:
            raise RuntimeError('coarse rack XY must be finite and away from the base origin')
        self.observation_bearing = math.atan2(xy[1], xy[0])
        self.pre_observation_command = deepcopy(self.input_message)

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

    def _pre_observation_pose(self):
        if self.target_pose_command is None:
            raise RuntimeError('target pose has not been received')
        target = deepcopy(self.target_pose_command)
        target.header.stamp = self.get_clock().now().to_msg()
        return target

    def prepare_observation(self):
        self.current_stage = 'pre_observation_setup'
        self.expected = self._expected_in_robot_frame()
        self.get_logger().info('THEORETICAL EXPECTED TAG POSES (robot frame):')
        for tag_id in self.rack_tag_ids:
            self.get_logger().info(f'  tag{tag_id}: {_pose_dict(self.expected[tag_id])}')
        self._ensure_task()
        self._publish_provisional_input(self.expected)
        self._wait_for_input()
        self._wait_for_target_pose()
        self._wait_for_controllers()

    def move_observation(self):
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

    def capture_observation(self):
        self.capture_enabled = True
        self.current_stage = 'pre_observation_capture'
        detection_deadline = time.monotonic() + self.timeout_sec
        while rclpy.ok() and self.result is None and time.monotonic() < detection_deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
        if self.result is None:
            reason = self.capture_error or (
                f'did not observe rack tags {self.rack_tag_ids} including target {self.task["tag_id"]} '
                f'(frames={self.capture_frame_count}, last_detected_ids={self.last_detected_ids})'
            )
            raise RuntimeError(f'pre-observation visual capture failed: {reason}')
        self._write_report()
        self.get_logger().info('OBSERVED TAG POSES (robot frame):')
        for tag_id in sorted(self.observed):
            self.get_logger().info(f'  tag{tag_id}: {_pose_dict(self.observed[tag_id])}')
        self.get_logger().info(
            f'PASS: PRE_OBSERVATION_COMPLETE; rack tags {sorted(self.observed)} including target {self.task["tag_id"]} were detected '
            f'and transformed into {self.robot_frame}'
        )
        self.get_logger().info(f'Report: {self.output_dir / "pre_observation_report.json"}')

    def _ensure_task(self):
        if self.task is None:
            provisional = String()
            provisional.data = json.dumps({
                'tag_id': int(self.get_parameter('demo_tag_id').value),
                'action': str(self.get_parameter('demo_action').value),
                'rack_tag_ids': list(self.rack_tag_ids),
            })
            self.task_publisher.publish(provisional)
            deadline = time.monotonic() + 2.0
            while self.task is None and time.monotonic() < deadline:
                rclpy.spin_once(self, timeout_sec=0.05)
        if self.task is None:
            raise RuntimeError('no valid approach task')

    def prepare_approach(self):
        if not self.execute_client.wait_for_server(timeout_sec=30.0):
            raise RuntimeError('/execute_trajectory is unavailable')
        self._ensure_task()
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
        self.approach_context = {'tag_initial': tag_initial, 'align_target': align_target}

    def align_selected(self):
        tag_initial = self.approach_context['tag_initial']
        align_target = self.approach_context['align_target']
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
        self.approach_context.update(tag_second=tag_second, normal=normal, start_front=start_front)

    def approach_selected(self):
        ray_width = float(self.get_parameter('ray_width_m').value)
        tag_second = self.approach_context['tag_second']
        normal = self.approach_context['normal']
        start_front = self.approach_context['start_front']
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
        recipe = str(self.get_parameter('task_recipe').value)
        steps = {name: getattr(self, name) for name in CAPABILITY_STEPS}
        self.completed_capabilities = []
        self.recipe_execution = execute_recipe(recipe, steps, on_complete=self.completed_capabilities.append)
        self.current_stage = 'complete'


def main():
    rclpy.init()
    node = TaskExecutive()
    try:
        node.run()
    except Exception as error:
        node.get_logger().error(f'FAIL: OBSERVATION_OR_APPROACH_INCOMPLETE: {error}')
        node.gui_final = ('FAILED', str(error))
        node._publish_gui_status()
        node._write_trial_summary(False, str(error))
        return_code = 1
    else:
        node.gui_final = ('SUCCEEDED', 'Task recipe completed; no physical grasp or placement')
        node._publish_gui_status()
        node._write_trial_summary(True)
        return_code = 0
    finally:
        node.cleanup_gripper_control()
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

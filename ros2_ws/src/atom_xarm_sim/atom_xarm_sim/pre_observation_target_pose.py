#!/usr/bin/env python3

"""Convert a coarse pre-observation bearing into a MoveIt target pose.

The input is a PoseStamped in ``link_base``. Its x/y coordinates are a
noisy estimate of the rack centre; z is the exact pre-observation TCP height.
The bearing is computed from x/y, not the quaternion.  The generated target is placed on that bearing at a
fixed distance from the robot origin and uses the horizontal gripper/camera
orientation convention used by the simulation.
"""

import math

from geometry_msgs.msg import PoseStamped
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy


INPUT_TOPIC = '/atom/pre_observation_target'
OUTPUT_TOPIC = '/atom/pre_observation_pose'
ROBOT_FRAME = 'link_base'
TARGET_DISTANCE_M = 0.35


def _normalise(values):
    norm = math.sqrt(sum(value * value for value in values))
    if norm < 1e-12:
        raise ValueError('zero quaternion cannot be normalised')
    return [value / norm for value in values]


def _quat_from_yaw(yaw):
    return [0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)]


def _quat_from_pitch(pitch):
    return [0.0, math.sin(pitch / 2.0), 0.0, math.cos(pitch / 2.0)]


def _quat_mul(first, second):
    ax, ay, az, aw = first
    bx, by, bz, bw = second
    return [
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    ]


def target_pose_from_command(command, target_distance_m=TARGET_DISTANCE_M,
                             robot_frame=ROBOT_FRAME):
    """Convert coarse rack XY and exact TCP height into an observation pose."""
    if command.header.frame_id != robot_frame:
        raise ValueError(
            f'input frame {command.header.frame_id!r} does not match {robot_frame!r}'
        )
    height = float(command.pose.position.z)
    if not math.isfinite(height):
        raise ValueError('input target height must be finite')
    if not math.isfinite(target_distance_m) or target_distance_m <= 0.0:
        raise ValueError('target_distance_m must be finite and positive')
    x, y = float(command.pose.position.x), float(command.pose.position.y)
    if not all(math.isfinite(value) for value in (x, y)) or math.hypot(x, y) < 1e-6:
        raise ValueError('coarse rack XY must be finite and away from the base origin')
    bearing = math.atan2(y, x)

    # link_eef +Z is the gripper/camera extension axis in this simulation.
    # Rz(bearing + pi) * Ry(-pi/2) maps that axis to the requested horizontal
    # bearing, so the pose position and the pointing ray share the same line.
    q_heading = _quat_from_yaw(bearing + math.pi)
    q_horizontal = _quat_from_pitch(-math.pi / 2.0)
    orientation = _quat_mul(q_heading, q_horizontal)

    target = PoseStamped()
    target.header = command.header
    target.header.frame_id = robot_frame
    target.pose.position.x = target_distance_m * math.cos(bearing)
    target.pose.position.y = target_distance_m * math.sin(bearing)
    target.pose.position.z = height
    target.pose.orientation.x = orientation[0]
    target.pose.orientation.y = orientation[1]
    target.pose.orientation.z = orientation[2]
    target.pose.orientation.w = orientation[3]
    return target, bearing


class PreObservationTargetPose(Node):
    def __init__(self):
        super().__init__('atom_pre_observation_target_pose')
        self.declare_parameter('input_topic', INPUT_TOPIC)
        self.declare_parameter('output_topic', OUTPUT_TOPIC)
        self.declare_parameter('robot_frame', ROBOT_FRAME)
        self.declare_parameter('target_distance_m', TARGET_DISTANCE_M)

        self.input_topic = str(self.get_parameter('input_topic').value)
        self.output_topic = str(self.get_parameter('output_topic').value)
        self.robot_frame = str(self.get_parameter('robot_frame').value)
        self.target_distance_m = float(self.get_parameter('target_distance_m').value)
        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.publisher = self.create_publisher(PoseStamped, self.output_topic, qos)
        self.create_subscription(PoseStamped, self.input_topic, self._callback, qos)

    def _callback(self, command):
        try:
            target, bearing = target_pose_from_command(
                command, self.target_distance_m, self.robot_frame
            )
        except ValueError as error:
            self.get_logger().error(f'Ignoring invalid pre-observation target: {error}')
            return
        self.publisher.publish(target)
        self.get_logger().info(
            f'PUBLISHED: {self.output_topic} position=('
            f'{target.pose.position.x:.6f}, {target.pose.position.y:.6f}, '
            f'{target.pose.position.z:.6f}) m bearing={bearing:.6f} rad '
            f'distance={self.target_distance_m:.3f} m'
        )


def main():
    rclpy.init()
    node = PreObservationTargetPose()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

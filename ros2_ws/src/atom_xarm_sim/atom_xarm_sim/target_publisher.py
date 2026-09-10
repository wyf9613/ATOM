#!/usr/bin/env python3

"""Publish configurable pick and place poses for the transfer baseline."""

import math
import sys

from geometry_msgs.msg import PoseStamped
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy


def _finite_vector(node, name, length):
    values = [float(value) for value in node.get_parameter(name).value]
    if len(values) != length or not all(math.isfinite(value) for value in values):
        raise RuntimeError(f'{name} must contain {length} finite values')
    return values


def _normalised_quaternion(values, name):
    norm = math.sqrt(sum(value * value for value in values))
    if norm < 1e-9:
        raise RuntimeError(f'{name} must not be a zero quaternion')
    return [value / norm for value in values]


class TargetPublisher(Node):
    def __init__(self):
        super().__init__('target_publisher')
        self.declare_parameter('reference_frame', 'world')
        self.declare_parameter('publish_rate_hz', 2.0)
        self.declare_parameter('pick_position_xyz_m', [0.0, 0.0, 0.0])
        self.declare_parameter('pick_orientation_xyzw', [0.0, 0.0, 0.0, 1.0])
        self.declare_parameter('place_position_xyz_m', [0.0, 0.0, 0.0])
        self.declare_parameter('place_orientation_xyzw', [0.0, 0.0, 0.0, 1.0])

        self.reference_frame = str(self.get_parameter('reference_frame').value)
        if not self.reference_frame:
            raise RuntimeError('reference_frame must not be empty')
        rate_hz = float(self.get_parameter('publish_rate_hz').value)
        if not math.isfinite(rate_hz) or rate_hz <= 0.0:
            raise RuntimeError('publish_rate_hz must be positive and finite')

        self.pick_pose = self._pose_from_parameters('pick')
        self.place_pose = self._pose_from_parameters('place')
        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.pick_publisher = self.create_publisher(PoseStamped, '/atom/pick_pose', qos)
        self.place_publisher = self.create_publisher(PoseStamped, '/atom/place_pose', qos)
        self.timer = self.create_timer(1.0 / rate_hz, self._publish)
        self._publish()
        self.get_logger().info(
            f'Publishing pick and place poses in {self.reference_frame} on '
            '/atom/pick_pose and /atom/place_pose'
        )

    def _pose_from_parameters(self, prefix):
        position = _finite_vector(self, f'{prefix}_position_xyz_m', 3)
        orientation = _normalised_quaternion(
            _finite_vector(self, f'{prefix}_orientation_xyzw', 4),
            f'{prefix}_orientation_xyzw',
        )
        pose = PoseStamped()
        pose.header.frame_id = self.reference_frame
        pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = position
        (
            pose.pose.orientation.x,
            pose.pose.orientation.y,
            pose.pose.orientation.z,
            pose.pose.orientation.w,
        ) = orientation
        return pose

    def _publish(self):
        stamp = self.get_clock().now().to_msg()
        self.pick_pose.header.stamp = stamp
        self.place_pose.header.stamp = stamp
        self.pick_publisher.publish(self.pick_pose)
        self.place_publisher.publish(self.place_pose)


def main():
    rclpy.init()
    try:
        node = TargetPublisher()
    except Exception as error:
        rclpy.logging.get_logger('target_publisher').error(f'FAIL: {error}')
        rclpy.shutdown()
        sys.exit(1)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

#!/usr/bin/python3
"""Publish a deterministic Gazebo smoke-test motion sequence."""

import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64


COMMAND_ROOT = "/model/ur3e_atom/joint"
JOINTS = (
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint",
    "left_finger_joint",
    "right_finger_joint",
)
POSES = (
    (0.0, -1.5708, 1.5708, -1.5708, -1.5708, 0.0, 0.0, 0.0),
    (0.35, -1.20, 1.40, -1.75, -1.5708, 0.40, 0.012, 0.012),
    (-0.25, -1.35, 1.65, -1.85, -1.5708, -0.30, 0.004, 0.004),
    (0.0, -1.5708, 1.5708, -1.5708, -1.5708, 0.0, 0.0, 0.0),
)


class DemoMotion(Node):
    def __init__(self):
        super().__init__("atom_demo_motion")
        self.publishers_by_joint = {
            joint: self.create_publisher(
                Float64, f"{COMMAND_ROOT}/{joint}/cmd_pos", 10
            )
            for joint in JOINTS
        }

    def publish_pose(self, positions, duration=2.0):
        deadline = time.monotonic() + duration
        while rclpy.ok() and time.monotonic() < deadline:
            for joint, position in zip(JOINTS, positions):
                self.publishers_by_joint[joint].publish(Float64(data=position))
            rclpy.spin_once(self, timeout_sec=0.02)


def main():
    rclpy.init()
    node = DemoMotion()
    time.sleep(1.0)
    for index, pose in enumerate(POSES, start=1):
        node.get_logger().info(f"Commanding smoke-test pose {index}/{len(POSES)}")
        node.publish_pose(pose)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()

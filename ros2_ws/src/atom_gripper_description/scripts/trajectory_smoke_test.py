#!/usr/bin/python3
"""Exercise the standard arm and gripper trajectory controller actions."""

import sys
import time

import rclpy
from control_msgs.action import FollowJointTrajectory
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


ARM_JOINTS = (
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint",
)
FINGER_JOINTS = ("left_finger_joint", "right_finger_joint")
HOME = (0.0, -1.5708, 1.5708, -1.5708, -1.5708, 0.0)
TEST_POSE = (0.15, -1.45, 1.40, -1.48, -1.45, 0.10)
OPEN = (0.0, 0.0)
CLOSED = (-0.010, -0.010)


class TrajectorySmokeTest(Node):
    def __init__(self):
        super().__init__("atom_trajectory_smoke_test")
        self.arm_client = ActionClient(
            self, FollowJointTrajectory, "/arm_controller/follow_joint_trajectory"
        )
        self.gripper_client = ActionClient(
            self,
            FollowJointTrajectory,
            "/gripper_controller/follow_joint_trajectory",
        )
        self.positions = {}
        self.create_subscription(JointState, "/joint_states", self._on_joints, 20)

    def _on_joints(self, message):
        self.positions.update(zip(message.name, message.position))

    def wait_for_interfaces(self, timeout=20.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
            joints_ready = all(
                joint in self.positions for joint in ARM_JOINTS + FINGER_JOINTS
            )
            if (
                joints_ready
                and self.arm_client.server_is_ready()
                and self.gripper_client.server_is_ready()
            ):
                return True
        return False

    def execute(self, client, joints, positions, duration, timeout=10.0):
        trajectory = JointTrajectory(joint_names=list(joints))
        point = JointTrajectoryPoint(positions=list(positions))
        point.time_from_start.sec = int(duration)
        point.time_from_start.nanosec = int((duration - int(duration)) * 1e9)
        trajectory.points.append(point)

        goal = FollowJointTrajectory.Goal(trajectory=trajectory)
        send_future = client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=timeout)
        if not send_future.done() or not send_future.result().accepted:
            return False
        result_future = send_future.result().get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=timeout)
        if not result_future.done():
            return False
        return result_future.result().result.error_code == 0

    def maximum_error(self, joints, targets):
        return max(
            abs(self.positions[joint] - target)
            for joint, target in zip(joints, targets)
        )


def main():
    rclpy.init()
    node = TrajectorySmokeTest()
    passed = False
    try:
        if not node.wait_for_interfaces():
            node.get_logger().error(
                "Missing trajectory actions or eight-joint feedback; launch with "
                "control_backend:=ros2_control"
            )
            return 2

        sequence = (
            (node.arm_client, ARM_JOINTS, TEST_POSE, 2.0, "arm test pose"),
            (node.gripper_client, FINGER_JOINTS, CLOSED, 1.0, "gripper close"),
            (node.gripper_client, FINGER_JOINTS, OPEN, 1.0, "gripper open"),
            (node.arm_client, ARM_JOINTS, HOME, 2.0, "arm home"),
        )
        for client, joints, targets, duration, label in sequence:
            node.get_logger().info(f"Executing {label}")
            if not node.execute(client, joints, targets, duration):
                node.get_logger().error(f"Trajectory action failed during {label}")
                return 1

        rclpy.spin_once(node, timeout_sec=0.1)
        arm_error = node.maximum_error(ARM_JOINTS, HOME)
        gripper_error = node.maximum_error(FINGER_JOINTS, OPEN)
        passed = arm_error <= 0.02 and gripper_error <= 0.002
        node.get_logger().info(
            f"RESULT {'PASS' if passed else 'FAIL'} | "
            f"arm_error={arm_error:.5f} rad gripper_error={gripper_error:.5f} m"
        )
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

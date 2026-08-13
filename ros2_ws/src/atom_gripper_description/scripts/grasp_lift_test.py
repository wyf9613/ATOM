#!/usr/bin/python3
"""Run and evaluate the provisional cuvette grasp-and-lift scenario."""

import math
import sys
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64
from tf2_msgs.msg import TFMessage


COMMAND_ROOT = "/model/ur3e_atom/joint"
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
LIFT = (0.0, -1.5708, 1.3358, -1.3358, -1.5708, 0.0)
OPEN = 0.0
CLOSED = -0.015
CONTACT_MIN = -0.0145
CONTACT_MAX = -0.0115
CONTACT_SYMMETRY_TOLERANCE = 0.001
MAX_LATERAL_MOTION = 0.010


class GraspLiftTest(Node):
    def __init__(self):
        super().__init__("atom_grasp_lift_test")
        self.publishers_by_joint = {
            joint: self.create_publisher(Float64, f"{COMMAND_ROOT}/{joint}/cmd_pos", 10)
            for joint in ARM_JOINTS + FINGER_JOINTS
        }
        self.joint_positions = {}
        self.cuvette_pose = None
        self.pose_history = []
        self.create_subscription(JointState, "/joint_states", self._on_joints, 20)
        self.create_subscription(TFMessage, "/cuvette/pose", self._on_cuvette_pose, 20)

    def _on_joints(self, message):
        self.joint_positions.update(zip(message.name, message.position))

    def _on_cuvette_pose(self, message):
        transform = next(
            (
                candidate
                for candidate in message.transforms
                if candidate.child_frame_id == "cuvette"
            ),
            None,
        )
        if transform is None:
            return
        transform = transform.transform
        self.cuvette_pose = (
            transform.translation.x,
            transform.translation.y,
            transform.translation.z,
        )
        self.pose_history.append((time.monotonic(), self.cuvette_pose))

    def publish(self, arm, fingers):
        for joint, position in zip(ARM_JOINTS, arm):
            self.publishers_by_joint[joint].publish(Float64(data=position))
        for joint in FINGER_JOINTS:
            self.publishers_by_joint[joint].publish(Float64(data=fingers))

    def hold(self, arm, fingers, duration):
        deadline = time.monotonic() + duration
        while rclpy.ok() and time.monotonic() < deadline:
            self.publish(arm, fingers)
            rclpy.spin_once(self, timeout_sec=0.02)

    def interpolate(self, start, end, fingers, duration):
        begin = time.monotonic()
        while rclpy.ok():
            fraction = min((time.monotonic() - begin) / duration, 1.0)
            smooth = fraction * fraction * (3.0 - 2.0 * fraction)
            arm = tuple(a + (b - a) * smooth for a, b in zip(start, end))
            self.publish(arm, fingers)
            rclpy.spin_once(self, timeout_sec=0.02)
            if fraction >= 1.0:
                break

    def wait_for_state(self, timeout=8.0):
        deadline = time.monotonic() + timeout
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
            if self.cuvette_pose is not None and all(
                joint in self.joint_positions for joint in FINGER_JOINTS
            ):
                return True
        return False

    def missing_state(self):
        missing = []
        if self.cuvette_pose is None:
            missing.append("cuvette pose on /cuvette/pose")
        absent_joints = [
            joint for joint in FINGER_JOINTS if joint not in self.joint_positions
        ]
        if absent_joints:
            missing.append("gripper joints on /joint_states")
        return missing


def distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def main():
    rclpy.init()
    node = GraspLiftTest()
    passed = False
    try:
        if not node.wait_for_state():
            missing = ", ".join(node.missing_state())
            node.get_logger().error(
                f"Missing {missing}. Start the contact scene first with: "
                "ros2 launch atom_gripper_description grasp.launch.py"
            )
            return 2

        node.get_logger().info("Stage 1/5: settle at open grasp pose")
        node.hold(HOME, OPEN, 2.0)
        start = node.cuvette_pose

        node.get_logger().info("Stage 2/5: close both fingers")
        node.hold(HOME, CLOSED, 2.0)
        contact_positions = tuple(node.joint_positions[j] for j in FINGER_JOINTS)

        node.get_logger().info("Stage 3/5: lift nominally 50 mm")
        node.interpolate(HOME, LIFT, CLOSED, 3.0)
        lifted = node.cuvette_pose

        node.get_logger().info("Stage 4/5: hold for 5 s")
        hold_start = node.cuvette_pose
        node.pose_history.clear()
        node.hold(LIFT, CLOSED, 5.0)
        held = node.cuvette_pose
        hold_min_z = min(pose[2] for _, pose in node.pose_history)

        lift_height = lifted[2] - start[2]
        hold_drop = hold_start[2] - hold_min_z
        lateral_motion = math.hypot(lifted[0] - start[0], lifted[1] - start[1])
        contact_in_expected_window = all(
            CONTACT_MIN <= position <= CONTACT_MAX for position in contact_positions
        )
        contact_is_symmetric = (
            abs(contact_positions[0] - contact_positions[1])
            <= CONTACT_SYMMETRY_TOLERANCE
        )
        retained = held[2] > start[2] + 0.035

        node.get_logger().info("Stage 5/5: return and release")
        node.interpolate(LIFT, HOME, CLOSED, 3.0)
        node.hold(HOME, OPEN, 2.0)
        released = node.cuvette_pose
        release_error = distance(start, released)

        passed = (
            contact_in_expected_window
            and contact_is_symmetric
            and lift_height >= 0.040
            and hold_drop <= 0.005
            and lateral_motion <= MAX_LATERAL_MOTION
            and retained
            and release_error <= 0.015
        )
        node.get_logger().info(
            f"RESULT {'PASS' if passed else 'FAIL'} | "
            f"lift={lift_height:.4f} m hold_drop={hold_drop:.4f} m "
            f"lateral={lateral_motion:.4f} m release_error={release_error:.4f} m "
            f"finger_contact=({contact_positions[0]:.4f}, "
            f"{contact_positions[1]:.4f}) m"
        )
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

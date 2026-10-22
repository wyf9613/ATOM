#!/usr/bin/env python3
"""Command-line client for the fine-adjust action.

    ros2 run base_fine_adjust send_goal -- 0.30 0.10 0        # x y yaw_deg in base_link: 30 cm ahead, 10 cm left
    ros2 run base_fine_adjust send_goal -- 0 0 15             # turn 15 deg left in place
    ros2 run base_fine_adjust send_goal -- 1.2 -3.1 0 --frame map
    ros2 run base_fine_adjust send_goal --from-tag            # use the live goal from tag_goal_publisher
"""
import argparse
import math
import sys

import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node

from .geom import yaw_to_quat


class Client(Node):
    def __init__(self):
        super().__init__('fine_adjust_client')
        self.client = ActionClient(self, NavigateToPose, 'fine_adjust')
        self.tag_goal = None

    def wait_tag_goal(self, timeout=5.0):
        sub = self.create_subscription(PoseStamped, '/fine_adjust/goal_correction', lambda m: setattr(self, 'tag_goal', m), 10)
        t0 = self.get_clock().now()
        while rclpy.ok() and self.tag_goal is None and (self.get_clock().now() - t0).nanoseconds < timeout * 1e9:
            rclpy.spin_once(self, timeout_sec=0.1)
        self.destroy_subscription(sub)
        return self.tag_goal

    def send(self, pose):
        if not self.client.wait_for_server(timeout_sec=3.0):
            print('fine_adjust action server not running')
            return 2
        goal = NavigateToPose.Goal()
        goal.pose = pose
        fut = self.client.send_goal_async(goal, feedback_callback=self.on_feedback)
        rclpy.spin_until_future_complete(self, fut)
        handle = fut.result()
        if not handle.accepted:
            print('goal rejected (another fine adjust running?)')
            return 3
        res_fut = handle.get_result_async()
        try:
            rclpy.spin_until_future_complete(self, res_fut)
        except KeyboardInterrupt:
            print('cancelling ...')
            cf = handle.cancel_goal_async()
            rclpy.spin_until_future_complete(self, cf)
            return 130
        status = res_fut.result().status
        print({4: 'SUCCEEDED', 5: 'CANCELED', 6: 'ABORTED'}.get(status, f'status {status}'))
        return 0 if status == 4 else 1

    def on_feedback(self, msg):
        fb = msg.feedback
        print(f'  remaining {fb.distance_remaining*100:5.1f} cm', end='\r', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('x', nargs='?', type=float, default=0.0)
    ap.add_argument('y', nargs='?', type=float, default=0.0)
    ap.add_argument('yaw_deg', nargs='?', type=float, default=0.0)
    ap.add_argument('--frame', default='base_link')
    ap.add_argument('--from-tag', action='store_true', help='use the latest /fine_adjust/goal_correction')
    args = ap.parse_args()
    rclpy.init()
    node = Client()
    try:
        if args.from_tag:
            pose = node.wait_tag_goal()
            if pose is None:
                print('no goal from tag_goal_publisher within 5 s (tag visible? TF ok?)')
                return 4
            print(f'tag goal: x={pose.pose.position.x:.3f} y={pose.pose.position.y:.3f} in {pose.header.frame_id}')
        else:
            pose = PoseStamped()
            pose.header.frame_id = args.frame
            pose.header.stamp = node.get_clock().now().to_msg()
            pose.pose.position.x, pose.pose.position.y = args.x, args.y
            pose.pose.orientation = yaw_to_quat(math.radians(args.yaw_deg))
        return node.send(pose)
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    sys.exit(main())

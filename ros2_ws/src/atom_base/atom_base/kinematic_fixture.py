"""Ideal integration fixture through the velocity gate, not Nav2 or physical dynamics."""
import math
import threading
import time

import rclpy
from geometry_msgs.msg import TransformStamped, Twist
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from tf2_ros import TransformBroadcaster

from .control import wrap


class KinematicFixture(Node):
    def __init__(self):
        super().__init__('base_kinematic_fixture')
        self.declare_parameter('navigation_action', True)
        self.declare_parameter('map_tf', True)
        self.x = self.y = self.yaw = 0.
        self.v = self.w = 0.
        self.seen = -math.inf
        self.reserved = False
        self.lock = threading.Lock()
        self.tf = TransformBroadcaster(self)
        self.nav_pub = self.create_publisher(Twist, '/atom/base/nav_cmd_vel', 10)
        self.odom_pub = self.create_publisher(Odometry, '/odometry/filtered', 10)
        self.scan_pub = self.create_publisher(LaserScan, '/scan', 10)
        cb = ReentrantCallbackGroup()
        self.create_subscription(Twist, '/atom/base/cmd_vel', self.on_cmd, 10, callback_group=cb)
        self.create_timer(.05, self.tick, callback_group=cb)
        if self.get_parameter('navigation_action').value:
            self.server = ActionServer(self, NavigateToPose, 'navigate_to_pose', self.execute,
                                       goal_callback=self.goal, cancel_callback=lambda _: CancelResponse.ACCEPT,
                                       callback_group=cb)

    def goal(self, request):
        with self.lock:
            if self.reserved or request.pose.header.frame_id != 'map':
                return GoalResponse.REJECT
            self.reserved = True
        return GoalResponse.ACCEPT

    def on_cmd(self, msg):
        self.v, self.w, self.seen = msg.linear.x, msg.angular.z, time.monotonic()

    def tick(self):
        if not rclpy.ok():
            return
        if time.monotonic()-self.seen < .3:
            self.x += self.v*math.cos(self.yaw)*.05
            self.y += self.v*math.sin(self.yaw)*.05
            self.yaw = wrap(self.yaw+self.w*.05)
        now = self.get_clock().now().to_msg()
        a = TransformStamped()
        a.header.stamp, a.header.frame_id, a.child_frame_id = now, 'map', 'odom'
        a.transform.rotation.w = 1.
        b = TransformStamped()
        b.header.stamp, b.header.frame_id, b.child_frame_id = now, 'odom', 'base_link'
        b.transform.translation.x, b.transform.translation.y = self.x, self.y
        b.transform.rotation.z, b.transform.rotation.w = math.sin(self.yaw/2), math.cos(self.yaw/2)
        self.tf.sendTransform([a,b] if self.get_parameter('map_tf').value else [b])
        odom = Odometry()
        odom.header, odom.child_frame_id = b.header, 'base_link'
        odom.pose.pose.position.x, odom.pose.pose.position.y = self.x, self.y
        odom.pose.pose.orientation = b.transform.rotation
        odom.twist.twist.linear.x, odom.twist.twist.angular.z = self.v, self.w
        self.odom_pub.publish(odom)
        scan = LaserScan()
        scan.header.stamp, scan.header.frame_id = now, 'base_link'
        scan.angle_min, scan.angle_max, scan.angle_increment = -.65, .65, .0325
        scan.range_min, scan.range_max, scan.ranges = .05, 10., [8.]*41
        self.scan_pub.publish(scan)

    def execute(self, handle):
        target = handle.request.pose.pose
        q = target.orientation
        yaw = math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
        t0 = time.monotonic()
        try:
            while rclpy.ok() and time.monotonic()-t0 < 90:
                if handle.is_cancel_requested:
                    handle.canceled()
                    return NavigateToPose.Result()
                dx,dy = target.position.x-self.x,target.position.y-self.y
                distance = math.hypot(dx,dy)
                bearing = wrap(math.atan2(dy,dx)-self.yaw)
                error = bearing if distance > .01 else wrap(yaw-self.yaw)
                if distance <= .01 and abs(error) < .025:
                    handle.succeed()
                    return NavigateToPose.Result()
                cmd = Twist()
                cmd.angular.z = max(-.2,min(.2,error))
                cmd.linear.x = min(.15,distance) if distance > .01 and abs(bearing)<.3 else 0.
                self.nav_pub.publish(cmd)
                feedback = NavigateToPose.Feedback()
                feedback.distance_remaining = distance
                handle.publish_feedback(feedback)
                time.sleep(.05)
            handle.abort()
            return NavigateToPose.Result()
        finally:
            if rclpy.ok():
                self.nav_pub.publish(Twist())
            with self.lock:
                self.reserved = False


def main(args=None):
    rclpy.init(args=args)
    node = KinematicFixture()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.try_shutdown()

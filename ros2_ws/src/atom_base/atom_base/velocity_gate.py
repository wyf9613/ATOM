"""Only base command publisher. Source changes disarm; reset never resumes motion."""
import json
import math
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool, String
from std_srvs.srv import SetBool, Trigger

from .velocity_policy import VelocityPolicy


class VelocityGate(Node):
    def __init__(self):
        super().__init__('base_velocity_gate')
        self.declare_parameter('require_scan', True)
        self.declare_parameter('stop_dist', 0.40)
        self.policy = VelocityPolicy(require_scan=self.get_parameter('require_scan').value)
        self.pub = self.create_publisher(Twist, '/atom/base/cmd_vel', 10)
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.stopped_pub = self.create_publisher(Bool, '/atom/safety/stopped', latched)
        self.legacy_pub = self.create_publisher(Bool, '/estop_state', latched)
        self.status_pub = self.create_publisher(String, '/atom/base/control_state', latched)
        self.create_subscription(Twist, '/atom/base/nav_cmd_vel', lambda m: self.command('nav', m), 10)
        self.create_subscription(Twist, '/atom/base/fine_cmd_vel', lambda m: self.command('fine', m), 10)
        self.create_subscription(Bool, '/atom/safety/stop', self.stop, 10)
        self.create_subscription(Bool, '/estop', self.stop, 10)
        self.create_subscription(LaserScan, '/scan', self.scan, qos_profile_sensor_data)
        self.create_service(Trigger, '/atom/safety/reset', self.reset)
        self.create_service(SetBool, '/atom/base/select_fine_adjust', self.select)
        self.create_service(SetBool, '/atom/base/enable', self.enable)
        self.create_timer(0.05, self.tick)

    def command(self, source, msg):
        # Reject unsupported lateral / non-planar commands rather than silently dropping them.
        if any(v != 0.0 for v in (msg.linear.y, msg.linear.z, msg.angular.x, msg.angular.y)):
            self.policy.stop()
        else:
            self.policy.receive(source, msg.linear.x, msg.angular.z, time.monotonic())

    def stop(self, msg):
        if msg.data:
            self.policy.stop()
            self.tick()

    def reset(self, req, resp):
        self.policy.reset()
        resp.success, resp.message = True, 'Stop reset; base remains disabled, select owner then enable explicitly'
        self.tick()
        return resp

    def select(self, req, resp):
        self.policy.select('fine' if req.data else 'nav')
        resp.success, resp.message = True, 'Source selected; base disabled and buffered commands cleared'
        return resp

    def enable(self, req, resp):
        resp.success = self.policy.enable(req.data)
        resp.message = 'Updated; a fresh command is required' if resp.success else 'Reset software stop first'
        return resp

    def scan(self, msg):
        # Front lidar alone does not cover reverse/side-swept clearance.
        age = (self.get_clock().now()-rclpy.time.Time.from_msg(msg.header.stamp)).nanoseconds/1e9
        if not -0.05 <= age <= self.policy.scan_timeout:
            self.policy.obstacle = True
            return
        rays = [r for i, r in enumerate(msg.ranges)
                if abs(msg.angle_min+i*msg.angle_increment) < math.radians(30)
                and math.isfinite(r) and msg.range_min <= r <= msg.range_max]
        if not rays:
            self.policy.obstacle = True
            return
        self.policy.scan_seen = time.monotonic()
        self.policy.obstacle = min(rays) < self.get_parameter('stop_dist').value

    def tick(self):
        msg = Twist()
        msg.linear.x, msg.angular.z = self.policy.output(time.monotonic())
        self.pub.publish(msg)
        stopped = Bool(data=self.policy.stopped)
        self.stopped_pub.publish(stopped)
        self.legacy_pub.publish(stopped)
        self.status_pub.publish(String(data=json.dumps({
            'stopped': self.policy.stopped, 'enabled': self.policy.enabled,
            'owner': self.policy.source, 'v': msg.linear.x, 'w': msg.angular.z,
            'scope': 'base output and integrated gripper; no physical arm driver started',
        })))


def main(args=None):
    rclpy.init(args=args)
    node = VelocityGate()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.policy.stop()
        if rclpy.ok():
            node.tick()
        node.destroy_node()
        rclpy.try_shutdown()

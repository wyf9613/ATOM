#!/usr/bin/env python3
"""Tinkerforge IMU Brick (v1.x) -> sensor_msgs/Imu on /imu/data.

Units from the brick: angular velocity in 1/14.375 deg/s, acceleration in mG,
orientation as a unit quaternion from the on-board fusion.
"""
import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry
from tinkerforge.ip_connection import IPConnection
from tinkerforge.brick_imu import BrickIMU

GYRO_SCALE = math.radians(1.0 / 14.375)   # raw -> rad/s
ACC_SCALE = 9.80665 / 1000.0              # mG -> m/s^2


class ImuBrickNode(Node):
    def __init__(self):
        super().__init__('imu_brick')
        self.declare_parameter('uid', '6R5Z2C')
        self.declare_parameter('host', 'localhost')
        self.declare_parameter('port', 4223)
        self.declare_parameter('frame_id', 'imu_link')
        self.declare_parameter('rate', 100.0)
        self.declare_parameter('use_orientation', True)
        self.declare_parameter('auto_bias_seconds', 3.0)   # average gyro while still at startup, subtract afterwards
        self.declare_parameter('gyro_scale', 1.0)          # multiply z rate (calibrate against odom / a known turn)
        self.declare_parameter('zupt_odom_topic', '/odom')  # re-estimate gyro bias whenever wheels report standstill
        self.declare_parameter('zupt_still_seconds', 2.0)
        self.declare_parameter('zupt_alpha', 0.02)          # EMA rate while still (per sample)
        self.frame_id = self.get_parameter('frame_id').value
        self.use_orientation = bool(self.get_parameter('use_orientation').value)
        self.auto_bias_n = int(float(self.get_parameter('auto_bias_seconds').value) * float(self.get_parameter('rate').value))
        self.gyro_scale = float(self.get_parameter('gyro_scale').value)
        self.bias_sum = [0.0, 0.0, 0.0]; self.bias_cnt = 0; self.bias = [0.0, 0.0, 0.0]
        self.zupt_still_n = int(float(self.get_parameter('zupt_still_seconds').value) * float(self.get_parameter('rate').value))
        self.zupt_alpha = float(self.get_parameter('zupt_alpha').value)
        self.wheels_still = False; self.still_count = 0; self.last_odom_time = 0.0
        self.create_subscription(Odometry, self.get_parameter('zupt_odom_topic').value, self.on_odom, 20)
        self.create_timer(10.0, lambda: self.get_logger().info('gyro bias z now %.3f deg/s (still=%s)' % (self.bias[2] / 14.375, self.wheels_still)))
        self.pub = self.create_publisher(Imu, 'imu/data', 50)

        self.ipc = IPConnection()
        self.ipc.connect(self.get_parameter('host').value, int(self.get_parameter('port').value))
        self.imu = BrickIMU(self.get_parameter('uid').value, self.ipc)
        self.imu.leds_off()
        ident = self.imu.get_identity()
        fw = ".".join(map(str, ident.firmware_version))
        self.get_logger().info(f'connected to IMU Brick uid={self.get_parameter("uid").value} fw={fw}')
        period = 1.0 / float(self.get_parameter('rate').value)
        self.timer = self.create_timer(period, self.tick)

    def on_odom(self, m):
        t = m.twist.twist
        self.wheels_still = abs(t.linear.x) < 1e-3 and abs(t.angular.z) < 1e-3
        self.last_odom_time = self.get_clock().now().nanoseconds / 1e9

    def tick(self):
        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        gx, gy, gz = self.imu.get_angular_velocity()
        ax, ay, az = self.imu.get_acceleration()
        if self.bias_cnt < self.auto_bias_n:
            for i, v in enumerate((gx, gy, gz)):
                self.bias_sum[i] += v
            self.bias_cnt += 1
            if self.bias_cnt == self.auto_bias_n:
                self.bias = [v / self.bias_cnt for v in self.bias_sum]
                self.get_logger().info('gyro bias (raw) = %.2f %.2f %.2f  -> %.2f deg/s on z'
                                       % (*self.bias, self.bias[2] / 14.375))
            return  # do not publish during bias estimation
        # zero-velocity update: wheels stopped for a while -> slowly track the current bias
        if self.wheels_still and (self.get_clock().now().nanoseconds / 1e9 - self.last_odom_time) < 0.5:
            self.still_count += 1
            if self.still_count > self.zupt_still_n:
                a = self.zupt_alpha
                self.bias = [(1 - a) * b + a * v for b, v in zip(self.bias, (gx, gy, gz))]
        else:
            self.still_count = 0
        msg.angular_velocity.x = (gx - self.bias[0]) * GYRO_SCALE
        msg.angular_velocity.y = (gy - self.bias[1]) * GYRO_SCALE
        msg.angular_velocity.z = (gz - self.bias[2]) * GYRO_SCALE * self.gyro_scale
        msg.linear_acceleration.x = ax * ACC_SCALE
        msg.linear_acceleration.y = ay * ACC_SCALE
        msg.linear_acceleration.z = az * ACC_SCALE
        if self.use_orientation:
            qx, qy, qz, qw = self.imu.get_quaternion()
            msg.orientation.x, msg.orientation.y, msg.orientation.z, msg.orientation.w = qx, qy, qz, qw
            msg.orientation_covariance = [0.01, 0.0, 0.0, 0.0, 0.01, 0.0, 0.0, 0.0, 0.05]
        else:
            msg.orientation_covariance[0] = -1.0
        msg.angular_velocity_covariance = [1e-4, 0.0, 0.0, 0.0, 1e-4, 0.0, 0.0, 0.0, 1e-4]
        msg.linear_acceleration_covariance = [0.05, 0.0, 0.0, 0.0, 0.05, 0.0, 0.0, 0.0, 0.05]
        self.pub.publish(msg)

    def destroy_node(self):
        try:
            self.ipc.disconnect()
        finally:
            super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ImuBrickNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()

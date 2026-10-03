"""Read-only serial device boundary. Arrival timestamps are host ROS time."""
import time
import serial
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import MagneticField
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from .protocol import parse_sample
from .framing import LineFramer
from .serial_connection import open_sensor_port


class SensorBridge(Node):
    def __init__(self):
        super().__init__('atom_gripper_sensor_bridge')
        self.declare_parameter('port', '/dev/ttyUSB0')
        self.declare_parameter('frame_id', 'gripper_magnetic_sensor')
        self.declare_parameter('sensor_address', 20)
        self.declare_parameter('stale_timeout_s', 1.0)
        self.expected_address = self.get_parameter('sensor_address').value
        self.timeout = self.get_parameter('stale_timeout_s').value
        if not 1 <= self.expected_address <= 126 or self.timeout <= 0:
            raise ValueError('invalid sensor address or stale timeout')
        self.link = None
        self.framer = LineFramer()
        self.last_good = None
        self.last_attempt = -float('inf')
        self.state = 'waiting for serial device'
        self.sequence = None
        self.field = self.create_publisher(MagneticField, '/atom/gripper/magnetic_field', 10)
        self.diagnostics = self.create_publisher(DiagnosticArray, '/diagnostics', 10)
        self.create_timer(0.02, self.poll)
        self.create_timer(0.5, self.report)

    def poll(self):
        if self.link is None:
            if time.monotonic() - self.last_attempt < 2.0:
                return
            self.last_attempt = time.monotonic()
            try:
                self.link = open_sensor_port(self.get_parameter('port').value)
                self.framer = LineFramer()
                self.last_good = None
                self.state = 'connected; waiting for valid sample'
            except (serial.SerialException, OSError) as exc:
                self.state = str(exc)
                return
        try:
            previous_overflows = self.framer.oversized
            for line in self.framer.feed(self.link.read(1024)):
                self.receive(line)
            if self.framer.oversized > previous_overflows:
                self.state = 'oversized serial record'
        except (serial.SerialException, OSError) as exc:
            self.state = str(exc)
            self.link.close()
            self.link = None
            self.last_good = None

    def receive(self, raw):
        if raw.startswith(b'#'):
            return
        try:
            sample = parse_sample(raw.decode('ascii'))
            if sample.address != self.expected_address:
                raise ValueError('unexpected sensor address')
        except (ValueError, UnicodeError) as exc:
            self.state = str(exc)
            return
        self.sequence = sample.sequence
        if not sample.valid:
            self.last_good = None
            self.state = 'sensor read failed'
            return
        msg = MagneticField()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.get_parameter('frame_id').value
        msg.magnetic_field.x, msg.magnetic_field.y, msg.magnetic_field.z = sample.field_tesla
        # All-zero covariance means unknown; no force calibration is implied.
        self.field.publish(msg)
        self.last_good = time.monotonic()
        self.state = 'sensor telemetry valid'

    def report(self):
        fresh = self.last_good is not None and time.monotonic() - self.last_good <= self.timeout
        status = DiagnosticStatus()
        status.name = 'atom_gripper/sensor'
        status.hardware_id = self.get_parameter('port').value
        status.level = DiagnosticStatus.OK if fresh and self.state.startswith('sensor telemetry valid') else DiagnosticStatus.ERROR
        status.message = self.state if fresh else 'missing/stale telemetry: ' + self.state
        status.values = [KeyValue(key='sequence', value=str(self.sequence)),
                         KeyValue(key='motor_state', value='unknown; sensor bridge is read-only')]
        msg = DiagnosticArray()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.status = [status]
        self.diagnostics.publish(msg)

    def destroy_node(self):
        if self.link is not None:
            self.link.close()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = SensorBridge()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

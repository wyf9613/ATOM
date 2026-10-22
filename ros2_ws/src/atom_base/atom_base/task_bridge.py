#!/usr/bin/env python3
"""HTTP <-> ROS 2 bridge for the web task station.

Runs on the robot computer. Standard library only (no Flask).

  GET  /              web page
  GET  /map.png       map image (converted from map_saver PGM)
  GET  /map.json      {width, height, resolution, origin}
  GET  /points.json   named destinations from points.yaml
  GET  /status        {robot: {x, y, yaw, ok}, mission: <last event>,
                       nav: {plan: [[x,y],..], rpp_path: [[x,y],..], lookahead: [x,y]|null}}
  POST /cmd           JSON mission command -> published on /mission_cmd
  POST /initialpose   {x, y, yaw} -> published on /initialpose (AMCL)
"""

import json
import math
import mimetypes
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PointStamped, PoseWithCovarianceStamped
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool, Empty, String
from std_srvs.srv import Trigger
from nav_msgs.msg import OccupancyGrid, Path
from tf2_ros import Buffer, TransformListener

from atom_base.map_utils import load_map, encode_png_gray


def quaternion_to_yaw(q):
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny, cosy)


class BridgeNode(Node):

    def __init__(self):
        super().__init__('task_bridge')
        share = get_package_share_directory('atom_base')

        self.declare_parameter('port', 8080)
        self.declare_parameter('map_yaml', '')
        self.declare_parameter('points_yaml', '')
        self.declare_parameter('web_dir', os.path.join(share, 'web'))
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('base_frame', 'base_footprint')

        self.port = int(self.get_parameter('port').value)
        self.web_dir = self.get_parameter('web_dir').value
        self.map_frame = self.get_parameter('map_frame').value
        self.base_frame = self.get_parameter('base_frame').value

        self.declare_parameter('live_map', False)   # true: follow /map from SLAM instead of a saved yaml
        self.live_map = bool(self.get_parameter('live_map').value)
        map_yaml = self.get_parameter('map_yaml').value
        if map_yaml and not self.live_map:
            self.map_meta, self.map_png = load_map(map_yaml)
            self.get_logger().info(
                f"map {map_yaml}: {self.map_meta['width']}x"
                f"{self.map_meta['height']} @ {self.map_meta['resolution']} m")
        elif self.live_map:
            self.map_meta, self.map_png = {'width': 1, 'height': 1, 'resolution': 0.05, 'origin': [0.0, 0.0, 0.0]}, encode_png_gray(1, 1, b'\xcd')
        else:
            raise RuntimeError('parameter map_yaml is required (or live_map:=true)')
        self.map_version = 0

        points_yaml = self.get_parameter('points_yaml').value \
            or os.path.join(share, 'config', 'points.yaml')
        with open(points_yaml, 'r', encoding='utf-8') as handle:
            self.points = yaml.safe_load(handle).get('points', [])

        latched = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.cmd_pub = self.create_publisher(String, 'mission_cmd', 10)
        self.init_pub = self.create_publisher(
            PoseWithCovarianceStamped, 'initialpose', 10)
        self.estop_pub = self.create_publisher(Bool, 'estop', 10)
        self.reset_client = self.create_client(Trigger, '/atom/safety/reset')
        self.hb_pub = self.create_publisher(Empty, 'estop_heartbeat', 10)
        self.estop_state = False
        self.create_subscription(Bool, 'estop_state', self.on_estop_state, latched)
        self.create_subscription(
            String, 'mission_event', self.on_event, latched)
        if self.live_map:
            self.create_subscription(OccupancyGrid, 'map', self.on_map, latched)
            self.get_logger().info('live map mode: following /map')

        self.lock = threading.Lock()
        self.last_event = {'state': 'unknown'}
        self.robot = {'ok': False, 'x': 0.0, 'y': 0.0, 'yaw': 0.0}

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.create_timer(0.2, self.update_robot_pose)

        # Navigation internals shown on the page: the planner's path (/plan), the path the controller is
        # following (/received_global_plan, published by RPP) and RPP's lookahead ("carrot") point.
        self.nav = {'plan': [], 'rpp_path': [], 'lookahead': None}
        self.nav_time = {'plan': 0.0, 'rpp_path': 0.0, 'lookahead': 0.0}
        self.create_subscription(Path, 'plan', lambda m: self.on_path('plan', m), 10)
        self.create_subscription(Path, 'received_global_plan', lambda m: self.on_path('rpp_path', m), 10)
        self.create_subscription(PointStamped, 'lookahead_point', self.on_lookahead, 10)

    def to_map(self, frame_id):
        """(tx, ty, cos, sin) taking points of frame_id into the map frame; None if the TF is missing."""
        if not frame_id or frame_id == self.map_frame:
            return (0.0, 0.0, 1.0, 0.0)
        try:
            tf = self.tf_buffer.lookup_transform(self.map_frame, frame_id, rclpy.time.Time())
        except Exception:  # noqa: BLE001
            return None
        yaw = quaternion_to_yaw(tf.transform.rotation)
        return (tf.transform.translation.x, tf.transform.translation.y, math.cos(yaw), math.sin(yaw))

    def on_path(self, key, msg):
        # /plan is in the map frame; RPP's received_global_plan is the window it tracks, in the local costmap
        # frame (odom), so both are brought into the map frame before they are drawn.
        tr = self.to_map(msg.header.frame_id)
        if tr is None:
            return
        tx, ty, c, s_ = tr
        raw = [(tx + c * ps.pose.position.x - s_ * ps.pose.position.y,
                ty + s_ * ps.pose.position.x + c * ps.pose.position.y) for ps in msg.poses]
        pts = []
        for x, y in raw:
            if not pts or (x - pts[-1][0]) ** 2 + (y - pts[-1][1]) ** 2 >= 0.01:   # keep ~every 10 cm
                pts.append([round(x, 3), round(y, 3)])
        if raw and (not pts or pts[-1] != [round(raw[-1][0], 3), round(raw[-1][1], 3)]):
            pts.append([round(raw[-1][0], 3), round(raw[-1][1], 3)])
        with self.lock:
            self.nav[key] = pts[:600]
            self.nav_time[key] = time.time()

    def on_lookahead(self, msg):
        # RPP publishes the carrot in the local costmap frame (odom); show it on the map.
        tr = self.to_map(msg.header.frame_id)
        if tr is None:
            return
        tx, ty, c, s_ = tr
        x, y = tx + c * msg.point.x - s_ * msg.point.y, ty + s_ * msg.point.x + c * msg.point.y
        with self.lock:
            self.nav['lookahead'] = [round(x, 3), round(y, 3)]
            self.nav_time['lookahead'] = time.time()

    def on_event(self, msg):
        try:
            event = json.loads(msg.data)
        except json.JSONDecodeError:
            event = {'state': 'unknown', 'raw': msg.data}
        with self.lock:
            self.last_event = event
            self.last_event_time = time.time()

    def on_map(self, m):
        w, h = m.info.width, m.info.height
        d = bytes(m.data)
        # occupancy -1 -> 205 (unknown), 0..100 -> 254..0 (map_saver convention); flip rows so image row 0 = top
        lut = bytes([205] + [max(0, 254 - int(v * 2.54)) for v in range(101)])
        row = bytearray(w * h)
        for r in range(h):
            src = d[r * w:(r + 1) * w]
            row[(h - 1 - r) * w:(h - r) * w] = bytes(lut[(b + 1) if b != 255 else 0] for b in src)
        png = encode_png_gray(w, h, bytes(row))
        with self.lock:
            self.map_meta = {'width': w, 'height': h, 'resolution': float(m.info.resolution),
                             'origin': [m.info.origin.position.x, m.info.origin.position.y, 0.0]}
            self.map_png = png
            self.map_version += 1

    def on_estop_state(self, msg):
        with self.lock:
            self.estop_state = bool(msg.data)

    def publish_estop(self, raw):
        if 'heartbeat' in raw and 'stop' not in raw:
            self.hb_pub.publish(Empty())
            return {'heartbeat': True}
        stop = bool(raw.get('stop', True))
        if stop:
            self.estop_pub.publish(Bool(data=True))
        else:
            if not self.reset_client.service_is_ready():
                raise ValueError('Software stop supervisor unavailable')
            self.reset_client.call_async(Trigger.Request())
        self.get_logger().warn('ESTOP %s' % ('TRIGGERED' if stop else 'reset'))
        return {'stop': stop, 'base_remains_disabled_after_reset': not stop}

    def update_robot_pose(self):
        try:
            tf = self.tf_buffer.lookup_transform(
                self.map_frame, self.base_frame, rclpy.time.Time())
        except Exception:  # noqa: BLE001  (tf2 raises several types)
            with self.lock:
                self.robot['ok'] = False
            return
        t = tf.transform.translation
        with self.lock:
            self.robot = {
                'ok': True,
                'x': round(t.x, 3),
                'y': round(t.y, 3),
                'yaw': round(quaternion_to_yaw(tf.transform.rotation), 3),
            }

    def status(self):
        with self.lock:
            return {
                'robot': dict(self.robot),
                'mission': dict(self.last_event),
                'nav': {k: (v if time.time() - self.nav_time[k] < (3.0 if k == 'lookahead' else 60.0) else ([] if k != 'lookahead' else None))
                        for k, v in self.nav.items()},
                'estop': self.estop_state,
                'map_version': self.map_version,
                'time': time.time(),
            }

    # ---------------------------------------------------------- commands

    @staticmethod
    def validate_point(raw):
        return {
            'x': float(raw['x']),
            'y': float(raw['y']),
            'yaw': float(raw.get('yaw', 0.0)),
            'wait': float(raw.get('wait', 0.0)),
            'label': str(raw.get('label', ''))[:64],
        }

    def publish_cmd(self, raw):
        kind = raw.get('cmd')
        if kind == 'cancel':
            cmd = {'cmd': 'cancel'}
        elif kind == 'goto':
            cmd = self.validate_point(raw)
            cmd['cmd'] = 'goto'
        elif kind == 'route':
            cmd = {
                'cmd': 'route',
                'label': str(raw.get('label', ''))[:64],
                'points': [self.validate_point(p) for p in raw['points']],
            }
        else:
            raise ValueError(f'unknown cmd {kind!r}')
        msg = String()
        msg.data = json.dumps(cmd, ensure_ascii=False)
        self.cmd_pub.publish(msg)
        self.get_logger().info(f'cmd: {msg.data}')
        return cmd

    def publish_initial_pose(self, raw):
        x, y, yaw = float(raw['x']), float(raw['y']), float(raw.get('yaw', 0))
        msg = PoseWithCovarianceStamped()
        msg.header.frame_id = self.map_frame
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.pose.pose.position.x = x
        msg.pose.pose.position.y = y
        msg.pose.pose.orientation.z = math.sin(yaw / 2.0)
        msg.pose.pose.orientation.w = math.cos(yaw / 2.0)
        cov = [0.0] * 36
        cov[0] = cov[7] = 0.25
        cov[35] = 0.0685
        msg.pose.covariance = cov
        self.init_pub.publish(msg)
        self.get_logger().info(f'initialpose: x={x:.2f} y={y:.2f} yaw={yaw:.2f}')
        return {'x': x, 'y': y, 'yaw': yaw}


class Handler(BaseHTTPRequestHandler):
    node: BridgeNode = None  # set by serve()

    def log_message(self, fmt, *args):  # quieter than default
        if self.path != '/status':
            self.node.get_logger().debug(fmt % args)

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(self, body, ctype, cache='no-store'):
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', cache)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        path = self.path.split('?', 1)[0]
        node = self.node
        if path == '/status':
            self.send_json(node.status())
        elif path == '/map.png':
            self.send_bytes(node.map_png, 'image/png')
        elif path == '/map.json':
            self.send_json(node.map_meta)
        elif path == '/points.json':
            self.send_json({'points': node.points})
        else:
            if path in ('', '/'):
                path = '/index.html'
            full = os.path.normpath(os.path.join(node.web_dir, path.lstrip('/')))
            if not full.startswith(os.path.abspath(node.web_dir)) \
                    or not os.path.isfile(full):
                self.send_json({'error': 'not found'}, 404)
                return
            ctype = mimetypes.guess_type(full)[0] or 'application/octet-stream'
            if ctype.startswith('text/'):
                ctype += '; charset=utf-8'
            with open(full, 'rb') as handle:
                self.send_bytes(handle.read(), ctype)

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get('Content-Length', 0))
        try:
            raw = json.loads(self.rfile.read(length) or b'{}')
            if not isinstance(raw, dict):
                raise ValueError('body must be a JSON object')
            if self.path == '/cmd':
                sent = self.node.publish_cmd(raw)
            elif self.path == '/initialpose':
                sent = self.node.publish_initial_pose(raw)
            elif self.path == '/estop':
                sent = self.node.publish_estop(raw)
            else:
                self.send_json({'error': 'not found'}, 404)
                return
        except (ValueError, KeyError, TypeError) as error:
            self.send_json({'ok': False, 'error': str(error)}, 400)
            return
        self.send_json({'ok': True, 'sent': sent})


def main(args=None):
    rclpy.init(args=args)
    node = BridgeNode()
    Handler.node = node

    server = ThreadingHTTPServer(('0.0.0.0', node.port), Handler)

    def spin():
        # rclpy owns SIGINT/SIGTERM: when it shuts down, stop HTTP too.
        try:
            rclpy.spin(node)
        except (ExternalShutdownException, KeyboardInterrupt):
            pass
        finally:
            server.shutdown()

    spin_thread = threading.Thread(target=spin, daemon=True)
    spin_thread.start()
    node.get_logger().info(
        f'Task station serving on http://0.0.0.0:{node.port}/')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if rclpy.ok():
            rclpy.shutdown()
        spin_thread.join(timeout=3)
        node.destroy_node()


if __name__ == '__main__':
    main()

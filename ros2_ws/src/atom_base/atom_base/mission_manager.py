#!/usr/bin/env python3
"""JSON-driven mission manager for Nav2.

Interface contract (all payloads are JSON inside std_msgs/String):

  /mission_cmd   (subscribe)
    {"cmd": "goto",  "x": -9.0, "y": 1.0, "yaw": 0.0, "label": "pickup_a"}
    {"cmd": "route", "label": "A then B",
     "points": [{"x": -9.0, "y": 1.0, "yaw": 0.0, "wait": 5.0}, ...]}
    {"cmd": "cancel"}

  /mission_event (publish, transient local so late joiners get last state)
    {"state": "idle"}
    {"state": "navigating", "label": "...", "index": 0, "total": 1,
     "target": {"x":..,"y":..,"yaw":..}, "distance_remaining": 3.2}
    {"state": "waiting", "label": "...", "seconds": 5.0}
    {"state": "arrived", "label": "..."}
    {"state": "cancelled", "label": "..."}
    {"state": "failed", "label": "...", "reason": "..."}
    {"state": "relocalizing", "label": "..."}          (spinning at home)
    {"state": "relocalized", "label": "...", "match": 0.87}

Relocalisation at home: whenever the robot reaches a point within
`home_radius` of the home position (the point labelled "home" in the
points file, else home_x/home_y), it turns once on the spot through the
Nav2 Spin behaviour so that AMCL can re-match the surrounding walls, then
checks how well the current scan fits the map (fraction of scan points
within `match_tolerance` of an occupied map cell). The route continues
only if the median fit is at least `min_match`; otherwise the mission
fails and the operator must set the initial pose.

With `relocalize_mode: amcl` (odometry-only stack: map->odom comes from
map_odom_anchor and AMCL runs alongside with tf_broadcast off) the same
spin is used to *correct* the pose once: before spinning, AMCL is
re-seeded around the odometry pose (so it only searches nearby), and
after the spin the anchor is moved to the AMCL estimate, but only when
that estimate fits the current scan better than the odometry pose and the
jump is within `max_correction_xy` / `max_correction_yaw_deg`. Otherwise
the odometry pose is kept and the route continues.

The node knows nothing about where commands come from: a web bridge,
`ros2 topic pub`, or another node all look the same.
"""

import json
import math
import time

import numpy as np
import rclpy
import yaml
from action_msgs.msg import GoalStatus
from builtin_interfaces.msg import Duration
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav2_msgs.action import ComputePathToPose, NavigateToPose, Spin
from nav_msgs.msg import OccupancyGrid
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, QoSProfile, ReliabilityPolicy,
                       qos_profile_sensor_data)
from rclpy.duration import Duration as RclDuration
from rclpy.time import Time
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool, String
from tf2_ros import Buffer, TransformListener


def yaw_to_quaternion(yaw):
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)


class MissionManager(Node):

    def __init__(self):
        super().__init__('mission_manager')

        self.declare_parameter('feedback_period', 1.0)
        self.feedback_period = float(
            self.get_parameter('feedback_period').value)

        latched = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )

        self.cmd_sub = self.create_subscription(
            String, 'mission_cmd', self.on_command, 10)
        self.event_pub = self.create_publisher(
            String, 'mission_event', latched)
        self.system_stopped = True
        self.cancel_requested = False
        self.request_pending = False
        self.create_subscription(Bool, '/atom/safety/stopped', self.on_stop, latched)

        self.nav_client = ActionClient(
            self, NavigateToPose, 'navigate_to_pose')

        # Relocalisation at home
        self.declare_parameter('relocalize_at_home', True)
        self.declare_parameter('points_yaml', '')
        self.declare_parameter('home_x', 0.0)
        self.declare_parameter('home_y', 0.0)
        self.declare_parameter('home_radius', 0.5)
        self.declare_parameter('spin_angle', 2.0 * math.pi)
        self.declare_parameter('spin_time_allowance', 70.0)
        self.declare_parameter('settle_seconds', 2.0)
        self.declare_parameter('min_match', 0.5)
        self.declare_parameter('match_tolerance', 0.10)
        self.declare_parameter('match_max_range', 6.0)
        # 'check': AMCL owns map->odom; spin, then fail the route if the scan fits the map poorly.
        # 'amcl' : odometry-only stack; AMCL runs without TF and is used once at home to move the anchor.
        self.declare_parameter('relocalize_mode', 'check')
        self.declare_parameter('seed_std_xy', 0.3)          # m, particle spread around the odometry pose
        self.declare_parameter('seed_std_yaw_deg', 20.0)
        self.declare_parameter('max_correction_xy', 1.0)    # m, larger AMCL jumps are rejected
        self.declare_parameter('max_correction_yaw_deg', 45.0)
        self.declare_parameter('min_match_gain', 0.05)      # AMCL must fit the scan this much better
        self.declare_parameter('relocalize_on_start', False)  # amcl mode: run the same correction once after start-up
        self.declare_parameter('start_delay', 5.0)           # s after Nav2 and TF are up before the start-up correction
        gp = lambda n: self.get_parameter(n).value  # noqa: E731
        self.relocalize_enabled = bool(gp('relocalize_at_home'))
        self.home = self.load_home(str(gp('points_yaml')),
                                   float(gp('home_x')), float(gp('home_y')))
        self.home_radius = float(gp('home_radius'))
        self.spin_angle = float(gp('spin_angle'))
        self.spin_time_allowance = float(gp('spin_time_allowance'))
        self.settle_seconds = float(gp('settle_seconds'))
        self.min_match = float(gp('min_match'))
        self.match_tolerance = float(gp('match_tolerance'))
        self.match_max_range = float(gp('match_max_range'))
        self.reloc_mode = str(gp('relocalize_mode')).lower()
        self.seed_std_xy = float(gp('seed_std_xy'))
        self.seed_std_yaw = math.radians(float(gp('seed_std_yaw_deg')))
        self.max_corr_xy = float(gp('max_correction_xy'))
        self.max_corr_yaw = math.radians(float(gp('max_correction_yaw_deg')))
        self.min_match_gain = float(gp('min_match_gain'))
        self.relocalize_on_start = bool(gp('relocalize_on_start')) and self.reloc_mode == 'amcl'
        self.start_delay = float(gp('start_delay'))
        self.start_ready_since = None
        self.start_timer = self.create_timer(1.0, self.on_start_tick) if self.relocalize_on_start else None
        self.initial_pose_pub = self.create_publisher(PoseWithCovarianceStamped, 'initialpose', 10)
        self.amcl_map_odom = None  # (x, y, yaw) map->odom implied by the latest AMCL pose
        self.amcl_cov = None
        self.amcl_time = 0.0
        self.last_scan = None
        if self.reloc_mode == 'amcl':
            self.create_subscription(PoseWithCovarianceStamped, 'amcl_pose', self.on_amcl_pose, 10)

        self.spin_client = ActionClient(self, Spin, 'spin')

        # Straight-line execution: every user goal is first planned, the plan is cut at its corners,
        # and each straight leg is sent as its own Nav2 goal whose heading is the next leg's direction.
        # The robot therefore drives straight, stops, turns on the spot, and drives straight again.
        self.declare_parameter('split_corners', True)
        self.declare_parameter('corner_angle_deg', 12.0)
        self.declare_parameter('min_leg_length', 0.20)
        self.split_corners = bool(self.get_parameter('split_corners').value)
        self.corner_angle = math.radians(float(self.get_parameter('corner_angle_deg').value))
        self.min_leg = float(self.get_parameter('min_leg_length').value)
        # Headings the straight-drive lattice can follow (lattice_straight_rotate.json); legs are kept on them.
        self.declare_parameter('lattice_json', '')
        self.declare_parameter('leg_clearance', 0.35)   # m from map obstacles required along a straightened leg
        self.lattice_headings = load_lattice_headings(str(self.get_parameter('lattice_json').value))
        self.leg_clearance = float(self.get_parameter('leg_clearance').value)
        self.path_client = ActionClient(self, ComputePathToPose, 'compute_path_to_pose')
        self.legs = []            # sub-goals for the current user point
        self.leg_index = 0
        self.path_handle = None
        self.after_success_timer = None  # delay between consecutive Nav2 goals
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.near_wall = None      # boolean grid: map cell near an obstacle
        self.clearance = None      # metres to the nearest obstacle, per map cell
        self.map_info = None
        self.create_subscription(OccupancyGrid, 'map', self.on_map, latched_map_qos())
        self.create_subscription(LaserScan, 'scan', self.on_scan,
                                 qos_profile_sensor_data)
        self.reloc = None          # active relocalisation state (dict)

        # Mission state
        self.route = []           # list of point dicts
        self.route_label = ''
        self.index = 0
        self.goal_handle = None
        self.wait_timer = None
        self.pending_route = None  # route waiting for a cancel to finish
        self.last_feedback_time = 0.0

        self.publish_event({'state': 'idle'})
        self.get_logger().info(
            'Mission manager ready. Listening on /mission_cmd. '
            f'Home ({self.home[0]:.2f}, {self.home[1]:.2f}), '
            f'relocalise at home: {self.relocalize_enabled} (mode {self.reloc_mode})')

    # ------------------------------------------------------------ events

    def publish_event(self, event):
        msg = String()
        msg.data = json.dumps(event, ensure_ascii=False)
        self.event_pub.publish(msg)
        self.get_logger().info(f'event: {msg.data}')

    def current_point(self):
        if 0 <= self.index < len(self.route):
            return self.route[self.index]
        return None

    def point_label(self):
        point = self.current_point()
        if point and point.get('label'):
            return point['label']
        if self.route_label:
            return self.route_label
        return f'point {self.index + 1}'

    # ---------------------------------------------------------- commands

    def on_stop(self, msg):
        previous = self.system_stopped
        self.system_stopped = msg.data
        if msg.data and not previous:
            self.pending_route = None
            self.cancel_current('system software stop')

    def on_command(self, msg):
        try:
            cmd = json.loads(msg.data)
        except json.JSONDecodeError as error:
            self.publish_event({'state': 'failed',
                                'reason': f'bad JSON: {error}'})
            return

        if not isinstance(cmd, dict):
            self.publish_event({'state': 'failed', 'reason': 'command must be an object'})
            return
        kind = cmd.get('cmd')
        if kind != 'cancel' and self.system_stopped:
            self.publish_event({'state': 'failed', 'reason': 'system software stop is active'})
            return
        if kind == 'cancel':
            self.cancel_current('cancelled by operator')
        elif kind == 'goto':
            try:
                point = self.parse_point(cmd)
            except (KeyError, TypeError, ValueError) as error:
                self.publish_event({'state': 'failed',
                                    'reason': f'bad goto: {error}'})
                return
            self.start_route([point], cmd.get('label', ''))
        elif kind == 'route':
            try:
                points = [self.parse_point(p) for p in cmd['points']]
            except (KeyError, TypeError, ValueError) as error:
                self.publish_event({'state': 'failed',
                                    'reason': f'bad route: {error}'})
                return
            if not points:
                self.publish_event({'state': 'failed',
                                    'reason': 'route has no points'})
                return
            self.start_route(points, cmd.get('label', ''))
        else:
            self.publish_event({'state': 'failed',
                                'reason': f'unknown cmd: {kind}'})

    @staticmethod
    def parse_point(raw):
        point = {
            'x': float(raw['x']),
            'y': float(raw['y']),
            'yaw': float(raw.get('yaw', 0.0)),
            'wait': float(raw.get('wait', 0.0)),
            'label': str(raw.get('label', '')),
        }
        if not all(math.isfinite(point[n]) for n in ('x', 'y', 'yaw', 'wait')) or point['wait'] < 0:
            raise ValueError('coordinates must be finite and wait nonnegative')
        return point

    def start_route(self, points, label):
        if self.is_busy():
            self.publish_event({'state': 'failed', 'reason': 'busy; cancel and await completion before replacing mission'})
            return
        self.cancel_requested = False
        self.route = points
        self.route_label = label
        self.index = 0
        self.send_current_goal()

    def is_busy(self):
        return (self.request_pending or self.goal_handle is not None or self.wait_timer is not None
                or self.reloc is not None or self.path_handle is not None
                or self.after_success_timer is not None)

    def cancel_current(self, reason):
        self.cancel_requested = True
        self.pending_route = None
        if self.request_pending:
            return  # Cancel the accepted handle as soon as its response arrives.
        if self.after_success_timer is not None and self.goal_handle is None:
            self.finish_route('cancelled', reason)
            return
        if self.reloc is not None:
            self.reloc['cancelled'] = reason
            if self.reloc.get('handle') is not None:
                self.reloc['handle'].cancel_goal_async()
            else:
                self.end_relocalize_timer()
                self.finish_route('cancelled', reason)
            return
        if self.wait_timer is not None:
            self.wait_timer.cancel()
            self.destroy_timer(self.wait_timer)
            self.wait_timer = None
            self.finish_route('cancelled', reason)
            return
        if self.goal_handle is None:
            if self.path_handle is not None:
                self.path_handle.cancel_goal_async()
                self.path_handle = None
                self.finish_route('cancelled', reason)
                return
            if self.pending_route is None:
                self.publish_event({'state': 'idle'})
            return
        self.goal_handle.cancel_goal_async()

    # -------------------------------------------------------- navigation

    def send_current_goal(self):
        point = self.current_point()
        if point is None:
            self.finish_route('arrived', '')
            return
        if not self.nav_client.wait_for_server(timeout_sec=10.0):
            self.finish_route('failed', 'Nav2 action server not available')
            return
        self.legs = []
        self.leg_index = 0
        if self.split_corners and self.path_client.wait_for_server(timeout_sec=1.0):
            self.publish_navigating(None)
            goal = ComputePathToPose.Goal()
            goal.goal = self.pose_msg(point['x'], point['y'], point['yaw'])
            goal.use_start = False
            self.request_pending = True
            self.path_client.send_goal_async(goal).add_done_callback(self.on_plan_response)
            return
        self.send_nav_goal(point['x'], point['y'], point['yaw'])

    def pose_msg(self, x, y, yaw):
        from geometry_msgs.msg import PoseStamped
        ps = PoseStamped()
        ps.header.frame_id = 'map'
        ps.header.stamp = self.get_clock().now().to_msg()
        ps.pose.position.x = float(x)
        ps.pose.position.y = float(y)
        qx, qy, qz, qw = yaw_to_quaternion(yaw)
        ps.pose.orientation.x = qx
        ps.pose.orientation.y = qy
        ps.pose.orientation.z = qz
        ps.pose.orientation.w = qw
        return ps

    # ---- corner splitting
    def on_plan_response(self, future):
        self.request_pending = False
        try:
            handle = future.result()
        except Exception as error:  # noqa: BLE001
            self.get_logger().warn(f'plan request failed ({error}); sending the goal directly')
            self.send_direct()
            return
        if not handle.accepted:
            self.send_direct()
            return
        if self.cancel_requested or self.system_stopped:
            handle.cancel_goal_async()
            self.finish_route('cancelled', 'cancelled while awaiting planner acceptance')
            return
        self.path_handle = handle
        handle.get_result_async().add_done_callback(self.on_plan_result)

    def send_direct(self):
        point = self.current_point()
        if point is not None:
            self.send_nav_goal(point['x'], point['y'], point['yaw'])

    def on_plan_result(self, future):
        self.path_handle = None
        if not self.route:
            return
        point = self.current_point()
        try:
            path = future.result().result.path
        except Exception:  # noqa: BLE001
            path = None
        if path is None or len(path.poses) < 2:
            # no plan now: let Nav2 try (its recoveries may clear the way)
            self.send_direct()
            return
        end = path.poses[-1].pose.position
        gap = math.hypot(end.x - point['x'], end.y - point['y'])
        if gap > 0.5:
            # Smac returns a stub path ending at the robot when the goal cannot be reached by this footprint;
            # Nav2 would then report "arrived" without moving. Fail clearly instead.
            self.finish_route('failed', f'goal ({point["x"]:.2f}, {point["y"]:.2f}) is not reachable for this '
                                        f'robot (plan ends {gap:.1f} m away); choose a point with more clearance')
            return
        self.legs = self.split_path(path, point)
        self.add_turn_spot(path)
        self.leg_index = 0
        self.get_logger().info(
            f'{self.point_label()}: {len(self.legs)} straight leg(s) via '
            + ', '.join(f'({l["x"]:.2f},{l["y"]:.2f})' for l in self.legs[:-1]))
        self.send_leg()

    def split_path(self, path, point):
        """Cut a planner path at its corners. Returns sub-goals [{x, y, yaw}, ...]; the last one is the user point."""
        pts = []
        for ps in path.poses:
            x, y = ps.pose.position.x, ps.pose.position.y
            if not pts or math.hypot(x - pts[-1][0], y - pts[-1][1]) > 1e-3:
                pts.append((x, y))
        if len(pts) < 2:
            return [dict(x=point['x'], y=point['y'], yaw=point['yaw'])]
        pts = self.simplify(pts, 0.08)   # drop centimetre-scale jogs of the grid path
        corners = []
        seg_dir = math.atan2(pts[1][1] - pts[0][1], pts[1][0] - pts[0][0])
        seg_start = 0
        for k in range(1, len(pts) - 1):
            d = math.atan2(pts[k + 1][1] - pts[k][1], pts[k + 1][0] - pts[k][0])
            if abs(math.atan2(math.sin(d - seg_dir), math.cos(d - seg_dir))) > self.corner_angle:
                corners.append(k)
                seg_dir = d
                seg_start = k
        # drop corners that are too close to the previous corner / start / goal
        kept = []
        last = pts[0]
        for k in corners:
            if math.hypot(pts[k][0] - last[0], pts[k][1] - last[1]) >= self.min_leg:
                kept.append(k)
                last = pts[k]
        while kept and math.hypot(pts[kept[-1]][0] - pts[-1][0], pts[kept[-1]][1] - pts[-1][1]) < self.min_leg:
            kept.pop()
        # Re-centre the corners for turning room, but only to spots that keep every leg on a lattice
        # heading: an off-lattice leg makes the per-leg Smac plan a dog-leg that RPP rounds off while driving.
        start = self.robot_pose()
        start = (start[0], start[1]) if start is not None else pts[0]
        corners = self.recentre_aligned(start, [pts[k] for k in kept], (point['x'], point['y']))
        legs = []
        for i, c in enumerate(corners):
            nxt = corners[i + 1] if i + 1 < len(corners) else (point['x'], point['y'])
            yaw = math.atan2(nxt[1] - c[1], nxt[0] - c[0])
            legs.append(dict(x=c[0], y=c[1], yaw=yaw))
        legs.append(dict(x=point['x'], y=point['y'], yaw=point['yaw']))
        return legs

    def robot_pose(self):
        try:
            tf = self.tf_buffer.lookup_transform(self.map_frame(), 'base_link', Time(),
                                                 timeout=RclDuration(seconds=0.2))
        except Exception:  # noqa: BLE001
            return None
        q = tf.transform.rotation
        return (tf.transform.translation.x, tf.transform.translation.y,
                math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z)))

    def clearance_at(self, x, y):
        if self.clearance is None or self.map_info is None:
            return -1.0
        info = self.map_info
        col = int((x - info.origin.position.x) / info.resolution)
        row = int((y - info.origin.position.y) / info.resolution)
        if 0 <= row < info.height and 0 <= col < info.width:
            return float(self.clearance[row, col])
        return -1.0

    def add_turn_spot(self, path, min_turn_deg=100.0, reach=0.6, step=0.05, needed=0.50):
        """If the first leg starts with a near-U-turn (dead end), first drive straight ahead to the widest
        spot within `reach` and turn there, instead of turning where the robot happens to stand."""
        if not self.legs or self.clearance is None:
            return
        pose = self.robot_pose()
        if pose is None and path.poses:   # the planner's path starts at the robot pose, with its heading
            p0 = path.poses[0].pose
            q = p0.orientation
            pose = (p0.position.x, p0.position.y,
                    math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z)))
        if pose is None:
            return
        px, py, yaw = pose
        first = self.legs[0]
        d = math.atan2(first['y'] - py, first['x'] - px)
        turn = abs(math.atan2(math.sin(d - yaw), math.cos(d - yaw)))
        if turn < math.radians(min_turn_deg):
            return
        here = self.clearance_at(px, py)
        best = (here, 0.0)
        s = step
        while s <= reach + 1e-9:
            x, y = px + s * math.cos(yaw), py + s * math.sin(yaw)
            c = self.clearance_at(x, y)
            if c < 0.30:      # the robot body cannot go further
                break
            if c > best[0] + 1e-6:
                best = (c, s)
            s += step
        if best[1] > 0.0 and best[0] >= here + 0.04 and best[0] >= needed:
            sx, sy = px + best[1] * math.cos(yaw), py + best[1] * math.sin(yaw)
            yaw_out = math.atan2(first['y'] - sy, first['x'] - sx)
            self.legs.insert(0, dict(x=sx, y=sy, yaw=yaw_out))
            self.get_logger().info(f'U-turn: driving {best[1]:.2f} m further to ({sx:.2f},{sy:.2f}) '
                                   f'(clearance {here:.2f} -> {best[0]:.2f} m) before turning')

    def recentre_aligned(self, start, corners, goal, radius=0.30):
        """Re-centre each corner (see recentre) while keeping all legs on lattice headings. 2026-10-15."""
        if self.clearance is None or self.map_info is None or not corners:
            return corners
        out = align_corners(start, corners, goal, self.lattice_headings, self.clearance_at,
                            min_leg=self.min_leg, radius=radius, leg_clearance=self.leg_clearance)
        for c, n in zip(corners, out):
            if math.hypot(n[0] - c[0], n[1] - c[1]) > 1e-6:
                self.get_logger().info(f'corner ({c[0]:.2f},{c[1]:.2f}) moved to ({n[0]:.2f},{n[1]:.2f}) on the lattice: '
                                       f'clearance {self.clearance_at(*c):.2f} -> {self.clearance_at(*n):.2f} m')
        return out

    def recentre(self, c, radius=0.30, step=0.05):
        """Move a corner to the point within `radius` that is farthest from any map obstacle, so the
        turn on the spot has the most room. The planner's corner is often at the minimum that just fits.
        (Unconstrained version, no longer used by split_path: it pushed the legs off the lattice headings.)"""
        if self.clearance is None or self.map_info is None:
            return c
        info = self.map_info
        def clear(x, y):
            col = int((x - info.origin.position.x) / info.resolution)
            row = int((y - info.origin.position.y) / info.resolution)
            if 0 <= row < info.height and 0 <= col < info.width:
                return float(self.clearance[row, col])
            return -1.0
        best = (clear(*c), 0.0, c)
        n = int(round(radius / step))
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                x, y = c[0] + i * step, c[1] + j * step
                d = math.hypot(i * step, j * step)
                if d > radius:
                    continue
                v = clear(x, y) - 0.02 * d      # prefer the original spot when clearances tie
                if v > best[0] + 1e-6:
                    best = (v, d, (x, y))
        if best[2] != c:
            self.get_logger().info(f'corner ({c[0]:.2f},{c[1]:.2f}) moved to ({best[2][0]:.2f},{best[2][1]:.2f}): '
                                   f'clearance {clear(*c):.2f} -> {clear(*best[2]):.2f} m')
        return best[2]

    @staticmethod
    def simplify(pts, eps):
        """Douglas-Peucker polyline simplification."""
        if len(pts) < 3:
            return pts
        (x0, y0), (x1, y1) = pts[0], pts[-1]
        length = math.hypot(x1 - x0, y1 - y0)
        if length < 1e-9:
            d = [math.hypot(x - x0, y - y0) for x, y in pts]
        else:
            d = [abs((y1 - y0) * x - (x1 - x0) * y + x1 * y0 - y1 * x0) / length for x, y in pts]
        i = max(range(len(pts)), key=lambda k: d[k])
        if d[i] > eps:
            return MissionManager.simplify(pts[:i + 1], eps)[:-1] + MissionManager.simplify(pts[i:], eps)
        return [pts[0], pts[-1]]

    def send_leg(self):
        leg = self.legs[self.leg_index]
        self.send_nav_goal(leg['x'], leg['y'], leg['yaw'])

    def send_nav_goal(self, x, y, yaw):
        if self.cancel_requested or self.system_stopped:
            self.finish_route('cancelled', 'stop before navigation goal')
            return
        goal = NavigateToPose.Goal()
        goal.pose = self.pose_msg(x, y, yaw)
        self.publish_navigating(None)
        self.request_pending = True
        future = self.nav_client.send_goal_async(
            goal, feedback_callback=self.on_feedback)
        future.add_done_callback(self.on_goal_response)

    def publish_navigating(self, distance):
        point = self.current_point()
        event = {
            'state': 'navigating',
            'label': self.point_label(),
            'index': self.index,
            'total': len(self.route),
            'target': {'x': point['x'], 'y': point['y'],
                       'yaw': point['yaw']},
        }
        if distance is not None:
            event['distance_remaining'] = round(distance, 2)
        if len(self.legs) > 1:
            event['leg'] = self.leg_index + 1
            event['legs'] = len(self.legs)
            # straight-leg waypoints for the web page (corners, then the user point)
            event['waypoints'] = [{'x': round(l['x'], 3), 'y': round(l['y'], 3), 'yaw': round(l['yaw'], 3)}
                                  for l in self.legs]
        self.publish_event(event)

    def on_goal_response(self, future):
        self.request_pending = False
        try:
            handle = future.result()
        except Exception as error:  # noqa: BLE001
            self.finish_route('failed', f'send goal failed: {error}')
            return
        if not handle.accepted:
            self.finish_route('failed', 'goal rejected by Nav2')
            return
        self.goal_handle = handle
        if self.cancel_requested or self.system_stopped:
            handle.cancel_goal_async()
        handle.get_result_async().add_done_callback(self.on_result)

    def on_feedback(self, feedback_msg):
        if not self.route:
            return
        now = self.get_clock().now().nanoseconds / 1e9
        if now - self.last_feedback_time < self.feedback_period:
            return
        self.last_feedback_time = now
        self.publish_navigating(feedback_msg.feedback.distance_remaining)

    def on_result(self, future):
        self.goal_handle = None
        if self.cancel_requested or self.system_stopped:
            self.finish_route('cancelled', 'software stop or operator cancellation')
            return
        try:
            status = future.result().status
        except Exception as error:  # noqa: BLE001
            self.finish_route('failed', f'result error: {error}')
            return

        if status == GoalStatus.STATUS_SUCCEEDED:
            # Nav2 (Humble) can report a goal sent immediately after a success as "reached" at once,
            # because the controller still holds the previous path end. Give it a moment first.
            self.after_success_timer = self.create_timer(0.8, self.on_success_settled)
        elif status == GoalStatus.STATUS_CANCELED:
            self.finish_route('cancelled', 'cancelled')
        elif status == GoalStatus.STATUS_ABORTED:
            self.finish_route(
                'failed',
                'Nav2 aborted (no path, blocked, or recovery failed)')
        else:
            self.finish_route('failed', f'Nav2 status {status}')

    def on_success_settled(self):
        if self.after_success_timer is not None:
            self.after_success_timer.cancel()
            self.destroy_timer(self.after_success_timer)
            self.after_success_timer = None
        if not self.route:
            return
        if self.legs and self.leg_index + 1 < len(self.legs):
            self.leg_index += 1
            self.send_leg()
            return
        self.legs = []
        self.leg_index = 0
        self.on_point_reached()

    def on_point_reached(self):
        point = self.current_point()
        if (self.relocalize_enabled and point is not None
                and math.hypot(point['x'] - self.home[0],
                               point['y'] - self.home[1]) <= self.home_radius):
            self.start_relocalize()
            return
        self.continue_after_point()

    def continue_after_point(self):
        point = self.current_point()
        wait = point['wait'] if point else 0.0
        if wait > 0.0:
            self.publish_event({'state': 'waiting',
                                'label': self.point_label(),
                                'seconds': wait})
            self.wait_timer = self.create_timer(wait, self.on_wait_done)
        else:
            self.advance()

    def on_wait_done(self):
        if self.wait_timer is not None:
            self.wait_timer.cancel()
            self.destroy_timer(self.wait_timer)
            self.wait_timer = None
        self.advance()

    def advance(self):
        self.index += 1
        if self.index >= len(self.route):
            self.finish_route('arrived', '')
        else:
            self.send_current_goal()

    def finish_route(self, state, reason):
        label = self.route_label or self.point_label()
        event = {'state': state, 'label': label}
        if reason:
            event['reason'] = reason
        self.publish_event(event)

        self.route = []
        self.route_label = ''
        self.index = 0
        self.goal_handle = None
        self.end_relocalize_timer()
        self.reloc = None
        if self.after_success_timer is not None:
            self.after_success_timer.cancel()
            self.destroy_timer(self.after_success_timer)
            self.after_success_timer = None
        self.legs = []
        self.leg_index = 0

        if self.pending_route is not None:
            points, label = self.pending_route
            self.pending_route = None
            self.route = points
            self.route_label = label
            self.send_current_goal()

    # ---------------------------------------------------- relocalisation

    def load_home(self, path, default_x, default_y):
        if not path:  # same default as the web bridge
            try:
                from ament_index_python.packages import get_package_share_directory
                path = get_package_share_directory('amr_task_bridge') + '/config/points.yaml'
            except Exception:  # noqa: BLE001
                path = ''
        if path:
            try:
                with open(path) as f:
                    for p in (yaml.safe_load(f) or {}).get('points', []):
                        if str(p.get('label', '')).lower() == 'home':
                            return float(p['x']), float(p['y'])
            except (OSError, yaml.YAMLError, KeyError, TypeError, ValueError) as error:
                self.get_logger().warn(f'could not read home from {path}: {error}')
        return default_x, default_y

    def on_map(self, msg):
        info = msg.info
        grid = np.asarray(msg.data, dtype=np.int16).reshape(info.height, info.width)
        occ = grid >= 65
        k = max(1, int(round(self.match_tolerance / info.resolution)))
        near = occ.copy()
        for dy in range(-k, k + 1):
            for dx in range(-k, k + 1):
                if dx * dx + dy * dy <= k * k and (dx or dy):
                    near |= np.roll(np.roll(occ, dy, axis=0), dx, axis=1)
        self.near_wall = near
        self.map_info = info
        try:
            from scipy import ndimage
            blocked = (grid >= 65) | (grid < 0)
            self.clearance = ndimage.distance_transform_edt(~blocked) * info.resolution
        except Exception as error:  # noqa: BLE001
            self.get_logger().warn(f'no clearance field ({error}); corners will not be re-centred')
            self.clearance = None

    def scan_match(self, msg, pose=None):
        """Fraction of scan points within match_tolerance of a map obstacle.

        The scan is placed on the map by TF (pose None) or by an explicit base_link pose
        (x, y, yaw) on the map, composed with the static base_link->laser mount."""
        if self.near_wall is None:
            return None
        try:
            if pose is None:
                tf = self.tf_buffer.lookup_transform(
                    self.map_frame(), msg.header.frame_id, Time.from_msg(msg.header.stamp),
                    timeout=RclDuration(seconds=0.05))
                tx, ty, yaw = tf.transform.translation.x, tf.transform.translation.y, yaw_of(tf.transform.rotation)
            else:
                tf = self.tf_buffer.lookup_transform('base_link', msg.header.frame_id, Time(),
                                                     timeout=RclDuration(seconds=0.05))
                tx, ty, yaw = compose(pose, (tf.transform.translation.x, tf.transform.translation.y,
                                             yaw_of(tf.transform.rotation)))
        except Exception:  # noqa: BLE001
            return None
        r = np.asarray(msg.ranges, dtype=float)
        a = msg.angle_min + np.arange(len(r)) * msg.angle_increment
        ok = np.isfinite(r) & (r >= msg.range_min) & (r <= min(msg.range_max, self.match_max_range))
        if ok.sum() < 10:
            return None
        lx = r[ok] * np.cos(a[ok]); ly = r[ok] * np.sin(a[ok])
        c, s_ = math.cos(yaw), math.sin(yaw)
        mx = tx + c * lx - s_ * ly
        my = ty + s_ * lx + c * ly
        info = self.map_info
        col = np.floor((mx - info.origin.position.x) / info.resolution).astype(int)
        row = np.floor((my - info.origin.position.y) / info.resolution).astype(int)
        inside = (col >= 0) & (col < info.width) & (row >= 0) & (row < info.height)
        if inside.sum() < 10:
            return None
        return float(np.mean(self.near_wall[row[inside], col[inside]]))

    @staticmethod
    def map_frame():
        return 'map'

    def on_scan(self, msg):
        self.last_scan = msg
        if self.reloc is None or self.reloc.get('phase') not in ('spin', 'settle'):
            return
        now = time.monotonic()
        if now - self.reloc['last_scan'] < 0.2:
            return
        self.reloc['last_scan'] = now
        m = self.scan_match(msg)
        if m is not None:
            self.reloc['scores'].append((now, m))

    def start_relocalize(self, standalone=False):
        """Spin at the current spot and (mode amcl) correct the pose. `standalone`: not part of a route
        (start-up correction); it ends in 'idle' instead of continuing a route and never fails a route."""
        label = 'startup' if standalone else self.point_label()
        if not self.spin_client.wait_for_server(timeout_sec=2.0):
            if standalone:
                self.get_logger().warn('start-up correction skipped: Nav2 spin behaviour not available')
                self.publish_event({'state': 'idle'})
                return
            self.finish_route('failed', 'relocalisation: Nav2 spin behaviour not available')
            return
        self.reloc = {'phase': 'spin', 'scores': [], 'last_scan': 0.0,
                      't0': time.monotonic(), 'handle': None, 'timer': None,
                      'cancelled': None, 'spin_ok': None, 'standalone': standalone, 'label': label}
        if self.reloc_mode == 'amcl':
            # Re-seed AMCL around the odometry pose: the filter then only has to find the local correction.
            # map_odom_anchor also receives this message and re-anchors to the same pose (no change).
            pose = self.robot_pose()
            if pose is None:
                self.get_logger().warn('relocalisation: no map->base_link pose; AMCL keeps its own belief')
            else:
                self.publish_initial_pose(pose, self.seed_std_xy ** 2, self.seed_std_yaw ** 2)
                self.get_logger().info(f'AMCL re-seeded at odometry pose ({pose[0]:.2f}, {pose[1]:.2f}, '
                                       f'{math.degrees(pose[2]):.1f} deg)')
        self.publish_event({'state': 'relocalizing', 'label': label})
        goal = Spin.Goal()
        goal.target_yaw = float(self.spin_angle)
        goal.time_allowance = Duration(sec=int(self.spin_time_allowance))
        self.spin_client.send_goal_async(goal).add_done_callback(self.on_spin_response)

    def on_spin_response(self, future):
        if self.reloc is None:
            return
        try:
            handle = future.result()
        except Exception as error:  # noqa: BLE001
            self.finish_route('failed', f'relocalisation spin failed: {error}')
            return
        if not handle.accepted:
            self.finish_route('failed', 'relocalisation spin rejected by Nav2')
            return
        self.reloc['handle'] = handle
        if self.reloc['cancelled']:
            handle.cancel_goal_async()
        handle.get_result_async().add_done_callback(self.on_spin_result)

    def on_spin_result(self, future):
        if self.reloc is None:
            return
        self.reloc['handle'] = None
        if self.reloc['cancelled']:
            if self.reloc.get('standalone'):
                self.reloc = None
                self.get_logger().info('start-up correction cancelled by a new mission')
            self.finish_route('cancelled', self.reloc['cancelled']) if self.reloc else self.start_pending()
            return
        try:
            status = future.result().status
        except Exception:  # noqa: BLE001
            status = None
        self.reloc['spin_ok'] = status == GoalStatus.STATUS_SUCCEEDED
        self.reloc['t_spin_end'] = time.monotonic()
        self.reloc['phase'] = 'settle'
        self.reloc['timer'] = self.create_timer(self.settle_seconds, self.on_settle_done)

    def start_pending(self):
        """Start the route that was waiting for the start-up correction to be cancelled."""
        if self.pending_route is not None:
            points, label = self.pending_route
            self.pending_route = None
            self.route = points
            self.route_label = label
            self.send_current_goal()
        else:
            self.publish_event({'state': 'idle'})

    def end_relocalize_timer(self):
        if self.reloc is not None and self.reloc.get('timer') is not None:
            self.reloc['timer'].cancel()
            self.destroy_timer(self.reloc['timer'])
            self.reloc['timer'] = None

    def on_settle_done(self):
        if self.reloc is None:
            return
        self.end_relocalize_timer()
        if self.reloc_mode == 'amcl':
            self.correct_from_amcl()
            return
        t0, t1 = self.reloc['t0'], self.reloc['t_spin_end']
        late = [m for t, m in self.reloc['scores'] if t >= t0 + 0.5 * (t1 - t0)]
        if not late:
            self.finish_route('failed', 'relocalisation: no usable scans (map or TF missing)')
            return
        match = float(np.median(late))
        spin_note = '' if self.reloc['spin_ok'] else ' (spin did not complete)'
        if match >= self.min_match:
            self.publish_event({'state': 'relocalized', 'label': self.point_label(),
                                'match': round(match, 2)})
            self.get_logger().info(f'relocalised at home: scan match {match:.0%}{spin_note}')
            self.reloc = None
            self.continue_after_point()
        else:
            self.finish_route('failed',
                              f'relocalisation at home failed: scan match {match:.0%}'
                              f'{spin_note}; set the initial pose by hand')

    # ------------------------------------------- one-shot AMCL correction

    def on_amcl_pose(self, msg):
        """Store the map->odom transform implied by an AMCL pose (map->base at the scan time)."""
        try:
            tf = self.tf_buffer.lookup_transform(
                'odom', 'base_link', Time.from_msg(msg.header.stamp), timeout=RclDuration(seconds=0.05))
        except Exception:  # noqa: BLE001
            try:
                tf = self.tf_buffer.lookup_transform('odom', 'base_link', Time())
            except Exception:  # noqa: BLE001
                return
        m = (msg.pose.pose.position.x, msg.pose.pose.position.y, yaw_of(msg.pose.pose.orientation))
        o = (tf.transform.translation.x, tf.transform.translation.y, yaw_of(tf.transform.rotation))
        self.amcl_map_odom = compose(m, invert(o))
        self.amcl_cov = list(msg.pose.covariance)
        self.amcl_time = time.monotonic()

    def amcl_pose_now(self):
        """AMCL's belief of the current base_link pose, carried forward with odometry."""
        if self.amcl_map_odom is None:
            return None
        try:
            tf = self.tf_buffer.lookup_transform('odom', 'base_link', Time(), timeout=RclDuration(seconds=0.2))
        except Exception:  # noqa: BLE001
            return None
        return compose(self.amcl_map_odom, (tf.transform.translation.x, tf.transform.translation.y,
                                            yaw_of(tf.transform.rotation)))

    def publish_initial_pose(self, pose, var_xy, var_yaw, cov=None):
        msg = PoseWithCovarianceStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.map_frame()
        msg.pose.pose.position.x, msg.pose.pose.position.y = pose[0], pose[1]
        qx, qy, qz, qw = yaw_to_quaternion(pose[2])
        msg.pose.pose.orientation.x, msg.pose.pose.orientation.y = qx, qy
        msg.pose.pose.orientation.z, msg.pose.pose.orientation.w = qz, qw
        if cov is not None and len(cov) == 36:
            msg.pose.covariance = [float(v) for v in cov]
        else:
            c = [0.0] * 36
            c[0] = c[7] = var_xy
            c[35] = var_yaw
            msg.pose.covariance = c
        self.initial_pose_pub.publish(msg)

    def correct_from_amcl(self):
        label = self.reloc.get('label') or self.point_label()
        standalone = bool(self.reloc.get('standalone'))
        spin_note = '' if self.reloc['spin_ok'] else ' (spin did not complete)'
        odom_pose = self.robot_pose()
        amcl_pose = self.amcl_pose_now() if self.amcl_time >= self.reloc['t0'] else None
        scan = self.last_scan
        m_now = self.scan_match(scan, odom_pose) if (scan is not None and odom_pose is not None) else None
        m_amcl = self.scan_match(scan, amcl_pose) if (scan is not None and amcl_pose is not None) else None
        self.reloc = None

        def pct(v):
            return None if v is None else round(float(v), 2)

        event = {'state': 'relocalized', 'label': label, 'corrected': False,
                 'match': pct(m_now), 'match_amcl': pct(m_amcl)}
        if amcl_pose is None:
            event['reason'] = 'no AMCL pose since the spin started'
        elif m_amcl is None or m_now is None:
            event['reason'] = 'scan or map not available for comparison'
        else:
            dx = amcl_pose[0] - odom_pose[0]
            dy = amcl_pose[1] - odom_pose[1]
            dyaw = math.atan2(math.sin(amcl_pose[2] - odom_pose[2]), math.cos(amcl_pose[2] - odom_pose[2]))
            event['shift'] = {'dx': round(dx, 3), 'dy': round(dy, 3), 'dyaw_deg': round(math.degrees(dyaw), 1)}
            if math.hypot(dx, dy) > self.max_corr_xy or abs(dyaw) > self.max_corr_yaw:
                event['reason'] = 'AMCL jump too large, kept odometry'
            elif m_amcl < self.min_match:
                event['reason'] = f'AMCL fit {m_amcl:.0%} below min_match, kept odometry'
            elif m_amcl < m_now + self.min_match_gain:
                event['reason'] = 'AMCL does not fit better, kept odometry'
            else:
                # Move the anchor (and re-seed AMCL at its own estimate) through /initialpose.
                self.publish_initial_pose(amcl_pose, 0.05 ** 2, math.radians(5.0) ** 2, cov=self.amcl_cov)
                event['corrected'] = True
                self.get_logger().info(
                    f'anchor corrected by ({dx:+.2f}, {dy:+.2f}) m, {math.degrees(dyaw):+.1f} deg; '
                    f'scan fit {m_now:.0%} -> {m_amcl:.0%}{spin_note}')
        if not event['corrected']:
            self.get_logger().warn(f"relocalisation ({label}): {event.get('reason')}{spin_note}")
            if (not standalone and m_now is not None and m_now < self.min_match
                    and (m_amcl is None or m_amcl < self.min_match)):
                self.finish_route('failed', f"relocalisation at home failed: scan fit {m_now:.0%}, "
                                            f"{event.get('reason')}; set the initial pose by hand")
                return
        self.publish_event(event)
        if standalone:
            self.publish_event({'state': 'idle'})
            return
        self.continue_after_point()

    # ---------------------------------------------- start-up correction

    def on_start_tick(self):
        """Once Nav2, TF and the map are up (and start_delay has passed), run the correction once."""
        if self.is_busy() or self.route:
            self.start_timer.cancel(); self.destroy_timer(self.start_timer); self.start_timer = None
            self.get_logger().info('start-up correction skipped: a mission started first')
            return
        ready = (self.near_wall is not None and self.robot_pose() is not None
                 and self.spin_client.server_is_ready())
        if not ready:
            self.start_ready_since = None
            return
        now = time.monotonic()
        if self.start_ready_since is None:
            self.start_ready_since = now
            return
        if now - self.start_ready_since < self.start_delay:
            return
        self.start_timer.cancel(); self.destroy_timer(self.start_timer); self.start_timer = None
        self.get_logger().info('start-up correction: spinning once at the start spot')
        self.start_relocalize(standalone=True)


def yaw_of(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


def load_lattice_headings(path):
    """Heading angles of the Smac lattice file, else the standard 16 grid headings (atan2 of (1,0), (2,1), (1,1), ...)."""
    if path:
        try:
            with open(path) as f:
                angles = json.load(f)['lattice_metadata']['heading_angles']
            return sorted(float(a) for a in angles)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            pass
    vec = [(1, 0), (2, 1), (1, 1), (1, 2), (0, 1), (-1, 2), (-1, 1), (-2, 1),
           (-1, 0), (-2, -1), (-1, -1), (-1, -2), (0, -1), (1, -2), (1, -1), (2, -1)]
    return sorted(math.atan2(j, i) for i, j in vec)


def align_corners(start, corners, goal, headings, clear_at, min_leg=0.2, radius=0.30, leg_clearance=0.35):
    """Move each corner within `radius` to the spot with the most clearance such that the leg into it
    (from the previous corner or `start`) and the leg out of it (towards the next corner or `goal`) both
    run along one of `headings`. Corners are processed in order. Where no such spot exists the corner is
    projected onto the nearest lattice ray from the previous point, so at least the incoming leg is
    straight. If the final leg into the fixed goal is still off-lattice, one extra corner is inserted so
    the goal is reached with two lattice-aligned legs. Returns the new corner list (may be one longer)."""
    dirs = [(math.cos(h), math.sin(h)) for h in headings]

    def leg_ok(a, b):
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.05))
        return all(clear_at(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) >= leg_clearance
                   for k in range(n + 1))

    def meet(prev, nxt):
        """All points p = prev + t*d1 = nxt - s*d2 (t, s >= min_leg) for lattice directions d1, d2."""
        rx, ry = nxt[0] - prev[0], nxt[1] - prev[1]
        for d1 in dirs:
            for d2 in dirs:
                den = d1[0] * d2[1] - d1[1] * d2[0]
                if abs(den) < 1e-9:
                    continue
                t = (rx * d2[1] - ry * d2[0]) / den
                s_ = -(rx * d1[1] - ry * d1[0]) / den
                if t >= min_leg and s_ >= min_leg:
                    yield (prev[0] + t * d1[0], prev[1] + t * d1[1])

    def off_lattice(a, b):
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        return min(abs(math.atan2(math.sin(h - ang), math.cos(h - ang))) for h in headings)

    out = []
    prev = start
    for i, c in enumerate(corners):
        nxt = corners[i + 1] if i + 1 < len(corners) else goal
        best = None
        for p in meet(prev, nxt):
            dist = math.hypot(p[0] - c[0], p[1] - c[1])
            if dist > radius:
                continue
            score = clear_at(*p) - 0.02 * dist           # prefer the original spot when clearances tie
            if best is not None and score <= best[0] + 1e-6:
                continue
            if not leg_ok(prev, p):
                continue
            best = (score, p)
        if best is not None:
            p = best[1]
        else:
            # no aligned spot nearby: keep at least the incoming leg on the nearest lattice ray
            ang = math.atan2(c[1] - prev[1], c[0] - prev[0])
            d1 = min(dirs, key=lambda d: abs(math.atan2(math.sin(math.atan2(d[1], d[0]) - ang),
                                                       math.cos(math.atan2(d[1], d[0]) - ang))))
            t = (c[0] - prev[0]) * d1[0] + (c[1] - prev[1]) * d1[1]
            p = (prev[0] + t * d1[0], prev[1] + t * d1[1])
            if t < min_leg or math.hypot(p[0] - c[0], p[1] - c[1]) > 1.5 * radius or not leg_ok(prev, p):
                p = c
        out.append(p)
        prev = p
    # final approach: the goal is fixed, so reach it with two lattice legs if one is not enough
    if off_lattice(prev, goal) > math.radians(3.0):
        best = None
        for q in meet(prev, goal):
            extra = (math.hypot(q[0] - prev[0], q[1] - prev[1]) + math.hypot(goal[0] - q[0], goal[1] - q[1])
                     - math.hypot(goal[0] - prev[0], goal[1] - prev[1]))
            score = clear_at(*q) - 0.1 * extra           # roomy turn spot, little detour
            if best is not None and score <= best[0] + 1e-6:
                continue
            if clear_at(*q) < 0.40 or not leg_ok(prev, q) or not leg_ok(q, goal):
                continue
            best = (score, q)
        if best is not None:
            out.append(best[1])
    return out


def compose(a, b):
    """Pose b expressed in frame a, both as (x, y, yaw) 2-D transforms: a * b."""
    c, s = math.cos(a[2]), math.sin(a[2])
    return (a[0] + c * b[0] - s * b[1], a[1] + s * b[0] + c * b[1],
            math.atan2(math.sin(a[2] + b[2]), math.cos(a[2] + b[2])))


def invert(a):
    c, s = math.cos(a[2]), math.sin(a[2])
    return (-(c * a[0] + s * a[1]), -(-s * a[0] + c * a[1]), -a[2])


def latched_map_qos():
    return QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                      durability=DurabilityPolicy.TRANSIENT_LOCAL)


def main(args=None):
    rclpy.init(args=args)
    node = MissionManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

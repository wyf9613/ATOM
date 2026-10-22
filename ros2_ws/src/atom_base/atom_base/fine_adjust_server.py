#!/usr/bin/env python3
"""Slow odom-anchored base positioning, adapted from the LabBot handover.

Uses the reusable Park/Kuipers control module and /fine_adjust NavigateToPose
Action. A single action or follow session owns this controller. Output goes only
to the dedicated fine command input of the final velocity gate. System software
stop, stale ownership/TF/scan/tag data and cancellation prevent continued motion.
The legacy ALIGN String/SDK arm-search path is deliberately disabled.
"""
import math
import json
import threading
import time

import rclpy
from geometry_msgs.msg import PoseStamped, Twist
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool, String
from std_srvs.srv import SetBool, Trigger
from tf2_ros import Buffer, TransformListener

from . import control
from .geom import planar, transform_pose, wrap, yaw_to_quat


class FineAdjustServer(Node):

    def __init__(self):
        super().__init__('fine_adjust_server')
        p = self.declare_parameters('', [
            ('cmd_vel_topic', '/atom/base/fine_cmd_vel'),
            ('odom_frame', 'odom'),
            ('base_frame', 'base_link'),
            ('rate_hz', 20.0),
            ('v_max', 0.05),            # m/s  hard cap for fine adjust
            ('v_min', 0.012),           # m/s  below this the Tracer does not move
            ('w_max', 0.25),            # rad/s
            ('w_min', 0.04),            # rad/s deadband compensation for in-place turns
            ('a_max', 0.10),            # m/s^2  command rate limit
            ('alpha_max', 0.6),         # rad/s^2
            ('k1', 1.0), ('k2', 3.0), ('beta', 0.4), ('lam', 2.0),   # Park & Kuipers gains
            ('slow_dist', 0.25),        # m  start scaling v down with distance inside this
            ('k_turn', 1.0),            # in-place turn gain (rad/s per rad)
            ('in_place_angle_deg', 60.0),   # |bearing| above this -> turn in place first
            ('final_dist', 0.15),       # m  inside this: face the goal point, drive straight, align yaw (no arcs)
            ('final_los_deg', 8.0),
            ('k_lin', 0.4),
            ('xy_tol', 0.02),           # m
            ('yaw_tol_deg', 2.0),
            ('max_goal_dist', 1.5),     # m  reject goals further than this (this is a fine adjust, not navigation)
            ('timeout_s', 90.0),
            ('allow_reverse', False),   # if the target is behind, allow driving backwards (short distances)
            ('correction_alpha', 0.3),  # blend factor for goal corrections (in odom frame)
            ('correction_max_jump', 0.35),  # m  corrections further than this from the current goal are ignored
            ('correction_max_yaw_jump_deg', 25.0),  # corrections turning the goal heading more than this are ignored
            ('freeze_dist', 0.20),      # m  inside this distance the goal is frozen (no more corrections)
            ('scan_topic', '/scan'),
            ('data_timeout_s', 0.5),
            ('require_tag', True),
            ('stop_dist', 0.25),
            ('mission_bridge', False),
            ('follow_xy_tol', 0.03),        # follow mode: hold still when inside this ...
            ('follow_yaw_tol_deg', 3.0),
            ('follow_resume_xy', 0.06),     # ... and start moving again when the error exceeds this
            ('follow_resume_yaw_deg', 8.0),
            ('follow_lost_stop_s', 1.0),    # no tag for this long -> stop (hold) until it is seen again
            ('follow_alpha', 0.5),          # goal blending in follow mode (more responsive than correction_alpha)
            ('search_before_align', False),
            ('mission_wait_correction_s', 5.0),
        ])
        g = lambda n: self.get_parameter(n).value  # noqa: E731
        self.cmd_pub = self.create_publisher(Twist, g('cmd_vel_topic'), 10)
        self.odom_frame, self.base_frame = g('odom_frame'), g('base_frame')
        self.period = 1.0 / g('rate_hz')
        self.cfg = {n: g(n) for n in ('v_max', 'v_min', 'w_max', 'w_min', 'a_max', 'alpha_max', 'k1', 'k2', 'beta',
                                      'lam', 'slow_dist', 'k_turn', 'xy_tol', 'max_goal_dist', 'timeout_s',
                                      'allow_reverse', 'correction_alpha', 'correction_max_jump', 'correction_max_yaw_jump_deg', 'freeze_dist', 'stop_dist',
                                      'mission_wait_correction_s')}
        self.cfg['in_place_angle'] = math.radians(g('in_place_angle_deg'))
        self.cfg['final_dist'] = float(g('final_dist'))
        self.cfg['final_los'] = math.radians(g('final_los_deg'))
        self.cfg['k_lin'] = float(g('k_lin'))
        self.cfg['yaw_tol'] = math.radians(g('yaw_tol_deg'))

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.lock = threading.Lock()
        self.goal_odom = None          # (x, y, yaw) in odom
        self.last_correction = None    # PoseStamped, raw, any frame
        self.last_correction_time = None
        self.active = False
        self.following = False
        self.follow_thread = None
        self.follow_rejects = 0
        self.scan_blocked = False
        self.last_scan_time = None
        self.system_stopped = True
        self.control_ready = False
        self.control_seen = -math.inf
        self.cancel_event = threading.Event()
        # The legacy String mission bridge bypasses action ownership/cancellation.
        # Compose ALIGN in the existing task executor using /fine_adjust instead.
        if g('mission_bridge'):
            raise ValueError('Use /fine_adjust action; legacy mission bridge is disabled in ATOM')

        cb = ReentrantCallbackGroup()
        self.create_subscription(PoseStamped, '/fine_adjust/goal_correction', self.on_correction, 10, callback_group=cb)
        if g('scan_topic'):
            self.create_subscription(LaserScan, g('scan_topic'), self.on_scan, qos_profile_sensor_data, callback_group=cb)
        latched_state = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(Bool, '/atom/safety/stopped', self.on_stop, latched_state, callback_group=cb)
        self.create_subscription(String, '/atom/base/control_state', self.on_control_state, latched_state, callback_group=cb)
        self.create_service(SetBool, '/fine_adjust/follow', self.on_follow, callback_group=cb)
        self.server = ActionServer(self, NavigateToPose, 'fine_adjust', execute_callback=self.execute,
                                   goal_callback=self.on_goal, cancel_callback=self.on_cancel, callback_group=cb)

        self.get_logger().info(f'fine_adjust ready: v<= {self.cfg["v_max"]} m/s, w<= {self.cfg["w_max"]} rad/s, '
                               f'tol {self.cfg["xy_tol"]*100:.0f} cm / {g("yaw_tol_deg")} deg')

    # ------------------------------------------------------------ helpers
    def on_stop(self, msg):
        self.system_stopped = msg.data
        if msg.data:
            self.cancel_event.set()
            self.following = False
            self.publish_cmd(0., 0.)

    def on_control_state(self, msg):
        try:
            s = json.loads(msg.data)
            self.control_ready = s['owner'] == 'fine' and s['enabled'] and not s['stopped']
            self.control_seen = time.monotonic()
        except (ValueError, KeyError, TypeError):
            self.control_ready = False
        if not self.control_ready:
            self.cancel_event.set()
            self.following = False

    def owns_motion(self):
        return (not self.system_stopped and self.control_ready
                and time.monotonic()-self.control_seen < self.get_parameter('data_timeout_s').value)

    def data_ready(self):
        timeout = self.get_parameter('data_timeout_s').value
        now = self.get_clock().now()
        if self.get_parameter('scan_topic').value:
            if self.last_scan_time is None or not 0 <= (now-self.last_scan_time).nanoseconds < timeout*1e9:
                return False
        if self.get_parameter('require_tag').value:
            with self.lock:
                corr = self.last_correction
            if corr is None:
                return False
            age = (now-rclpy.time.Time.from_msg(corr.header.stamp)).nanoseconds/1e9
            if not -0.05 <= age < timeout:
                return False
        return True

    def base_in_odom(self):
        try:
            ts = self.tf_buffer.lookup_transform(self.odom_frame, self.base_frame, rclpy.time.Time())
        except Exception as e:  # noqa: BLE001
            self.get_logger().warn(f'no TF {self.odom_frame}->{self.base_frame}: {e}', throttle_duration_sec=2.0)
            return None
        age = (self.get_clock().now()-rclpy.time.Time.from_msg(ts.header.stamp)).nanoseconds/1e9
        if not -0.05 <= age < self.get_parameter('data_timeout_s').value:
            return None
        t, q = ts.transform.translation, ts.transform.rotation
        return t.x, t.y, math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))

    def pose_to_odom(self, ps):
        """PoseStamped in any frame -> (x, y, yaw) in odom, or None."""
        if ps.header.frame_id in ('', self.odom_frame):
            return planar(ps.pose)
        try:
            ts = self.tf_buffer.lookup_transform(self.odom_frame, ps.header.frame_id, rclpy.time.Time.from_msg(ps.header.stamp))
        except Exception as e:  # noqa: BLE001
            self.get_logger().warn(f'cannot transform goal from {ps.header.frame_id}: {e}')
            return None
        return planar(transform_pose(ps, ts).pose)

    def publish_cmd(self, v, w):
        if not rclpy.ok():
            return
        m = Twist()
        m.linear.x, m.angular.z = float(v), float(w)
        self.cmd_pub.publish(m)

    def stop(self):
        for _ in range(3):
            self.publish_cmd(0.0, 0.0)
            time.sleep(0.02)

    # ---------------------------------------------------------- callbacks
    def on_correction(self, msg):
        with self.lock:
            self.last_correction = msg
            self.last_correction_time = self.get_clock().now()
            if not self.active or self.goal_odom is None:
                return
            new = self.pose_to_odom(msg)
            if new is None:
                return
            gx, gy, gyaw = self.goal_odom
            jump = math.hypot(new[0] - gx, new[1] - gy)
            if self.following:
                # live tracking: blend faster, no freeze; still reject a one-off normal flip (IPPE ambiguity),
                # but accept it if it persists ~1 s (the tag really was turned / moved far)
                a = float(self.get_parameter('follow_alpha').value)
                dyaw = abs(wrap(new[2] - gyaw))
                if jump > 2.0 * self.cfg['correction_max_jump'] or dyaw > math.radians(90.0):
                    self.follow_rejects += 1
                    if self.follow_rejects < 30:
                        return
                    self.get_logger().warn(f'follow: goal jumped {jump:.2f} m / {math.degrees(dyaw):.0f} deg, re-anchoring')
                    self.goal_odom = new
                else:
                    self.goal_odom = (gx + a * (new[0] - gx), gy + a * (new[1] - gy), gyaw + a * wrap(new[2] - gyaw))
                self.follow_rejects = 0
                return
            if jump > self.cfg['correction_max_jump']:
                self.get_logger().warn(f'goal correction ignored: {jump:.2f} m away from current goal', throttle_duration_sec=2.0)
                return
            dyaw = abs(wrap(new[2] - gyaw))
            if dyaw > math.radians(self.cfg['correction_max_yaw_jump_deg']):
                self.get_logger().warn(f'goal correction ignored: heading jump {math.degrees(dyaw):.0f} deg (tag normal flip?)', throttle_duration_sec=2.0)
                return
            cur = self.base_in_odom()
            if cur is not None and math.hypot(gx - cur[0], gy - cur[1]) < self.cfg['freeze_dist']:
                return   # close to the goal: stop chasing tag noise, finish on odometry
            a = self.cfg['correction_alpha']
            self.goal_odom = (gx + a * (new[0] - gx), gy + a * (new[1] - gy), gyaw + a * wrap(new[2] - gyaw))

    def on_scan(self, msg):
        n = len(msg.ranges)
        if n == 0:
            return
        half = int(math.radians(30.0) / max(msg.angle_increment, 1e-6))
        centre = int((0.0 - msg.angle_min) / max(msg.angle_increment, 1e-6))
        lo, hi = max(0, centre - half), min(n, centre + half)
        front = [r for r in msg.ranges[lo:hi] if msg.range_min < r < msg.range_max]
        self.scan_blocked = not front or min(front) < self.cfg['stop_dist']
        self.last_scan_time = self.get_clock().now()

    def on_goal(self, goal_request):
        p = goal_request.pose.pose
        valid = bool(goal_request.pose.header.frame_id) and all(math.isfinite(v) for v in (
            p.position.x, p.position.y, p.position.z,
            p.orientation.x, p.orientation.y, p.orientation.z, p.orientation.w))
        valid = valid and abs(sum(v*v for v in (p.orientation.x,p.orientation.y,p.orientation.z,p.orientation.w))-1.0) < 0.01
        with self.lock:
            if self.active or self.following or not valid or not self.owns_motion():
                return GoalResponse.REJECT
            self.active = True  # Reserve atomically before the executor starts.
            self.cancel_event.clear()
        return GoalResponse.ACCEPT

    def on_cancel(self, goal_handle):
        return CancelResponse.ACCEPT

    # ------------------------------------------------------------ control
    def control_step(self, state):
        """Returns (v, w, done, info). state carries the phase."""
        cur = self.base_in_odom()
        if cur is None:
            return 0.0, 0.0, False, 'no tf'
        with self.lock:
            goal = self.goal_odom
        x, y, yaw_t = control.target_in_robot_frame(cur, goal)
        return control.step(x, y, yaw_t, self.cfg, state)

    def run_goal(self, goal_pose, progress=None, should_cancel=None):
        """Blocking fine adjust to goal_pose (PoseStamped). Returns (ok, message)."""
        g = self.pose_to_odom(goal_pose)
        if g is None:
            return False, 'goal frame not transformable'
        cur = self.base_in_odom()
        if cur is None:
            return False, 'no odom->base_link TF'
        dist = math.hypot(g[0] - cur[0], g[1] - cur[1])
        if dist > self.cfg['max_goal_dist']:
            return False, f'goal {dist:.2f} m away exceeds max_goal_dist'
        with self.lock:
            self.goal_odom = g
            self.active = True
        self.get_logger().info(f'fine adjust start: {dist*100:.0f} cm, {math.degrees(wrap(g[2]-cur[2])):+.0f} deg')
        state = {'phase': 'drive'}
        v_prev = w_prev = 0.0
        t0 = time.time()
        last_log = 0.0
        blocked_since = None
        try:
            while rclpy.ok():
                t = time.time()
                if self.cancel_event.is_set() or not self.owns_motion():
                    return False, 'motion ownership lost or software stop'
                if not self.data_ready() or self.base_in_odom() is None:
                    return False, 'tag/scan/TF unavailable or stale'
                if should_cancel is not None and should_cancel():
                    return False, 'cancelled'
                if t - t0 > self.cfg['timeout_s']:
                    return False, 'timeout'
                if self.scan_blocked:
                    blocked_since = blocked_since or t
                    self.publish_cmd(0.0, 0.0)
                    if t - blocked_since > 15.0:
                        return False, 'obstacle ahead for 15 s'
                    time.sleep(self.period)
                    continue
                blocked_since = None
                v, w, done, info = self.control_step(state)
                if done:
                    self.stop()
                    return True, info
                dv, dw = self.cfg['a_max'] * self.period, self.cfg['alpha_max'] * self.period
                v = v_prev + max(-dv, min(dv, v - v_prev))
                w = w_prev + max(-dw, min(dw, w - w_prev))
                v_prev, w_prev = v, w
                self.publish_cmd(v, w)
                if progress is not None:
                    progress(state, v, w)
                if t - last_log > 1.0:
                    last_log = t
                    self.get_logger().info(f'{info}  cmd v={v:+.3f} w={w:+.3f}')
                time.sleep(max(0.0, self.period - (time.time() - t)))
            return False, 'shutdown'
        finally:
            self.stop()
            with self.lock:
                self.active = False

    # ------------------------------------------------------------- follow mode
    def on_follow(self, req, resp):
        if req.data:
            with self.lock:
                if self.following:
                    resp.success, resp.message = True, 'follow already on'
                    return resp
                if not self.owns_motion() or self.active:
                    resp.success, resp.message = False, 'motion gate unavailable or another goal owns fine adjustment'
                    return resp
                self.following = self.active = True
                self.cancel_event.clear()
            self.follow_thread = threading.Thread(target=self.follow_loop, daemon=True)
            self.follow_thread.start()
            resp.success, resp.message = True, 'follow ON: base keeps the tag-relative pose until disabled'
        elif self.following:
            self.following = False
            if self.follow_thread is not None:
                self.follow_thread.join(timeout=2.0)
            self.stop()
            resp.success, resp.message = True, 'follow OFF'
        else:
            resp.success, resp.message = True, 'follow already ' + ('on' if self.following else 'off')
        return resp

    def follow_loop(self):
        g = lambda n: self.get_parameter(n).value  # noqa: E731
        xy_tol, yaw_tol = float(g('follow_xy_tol')), math.radians(float(g('follow_yaw_tol_deg')))
        res_xy, res_yaw = float(g('follow_resume_xy')), math.radians(float(g('follow_resume_yaw_deg')))
        lost_s = float(g('follow_lost_stop_s'))
        self.get_logger().info('follow: waiting for the first tag goal')
        with self.lock:
            self.goal_odom = None
        state = {'phase': 'drive'}
        moving = False
        v_prev = w_prev = 0.0
        last_log = 0.0
        try:
            while rclpy.ok() and self.following:
                if not self.owns_motion() or self.cancel_event.is_set():
                    break
                if not self.data_ready():
                    self.publish_cmd(0., 0.)
                    time.sleep(self.period)
                    continue
                t = time.time()
                with self.lock:
                    corr, corr_t = self.last_correction, self.last_correction_time
                    goal = self.goal_odom
                fresh = corr is not None and corr_t is not None and (self.get_clock().now() - corr_t).nanoseconds < lost_s * 1e9
                if goal is None:
                    if fresh:
                        gnew = self.pose_to_odom(corr)
                        with self.lock:
                            self.goal_odom = gnew
                            self.active = True        # lets on_correction keep blending the goal
                        self.get_logger().info('follow: tag goal acquired')
                    self.publish_cmd(0.0, 0.0)
                    time.sleep(self.period)
                    continue
                if not fresh:
                    if moving:
                        self.get_logger().warn('follow: tag lost, holding', throttle_duration_sec=2.0)
                    moving = False
                    v_prev = w_prev = 0.0
                    self.publish_cmd(0.0, 0.0)
                    if corr_t is not None and (self.get_clock().now() - corr_t).nanoseconds > 3.0e9:
                        with self.lock:
                            self.goal_odom = None      # next sighting re-anchors instead of blending from a stale goal
                            self.follow_rejects = 0
                    time.sleep(self.period)
                    continue
                cur = self.base_in_odom()
                if cur is None:
                    self.publish_cmd(0.0, 0.0)
                    time.sleep(self.period)
                    continue
                x, y, yaw_t = control.target_in_robot_frame(cur, goal)
                r = math.hypot(x, y)
                if not moving and (r > res_xy or abs(yaw_t) > res_yaw):
                    moving, state = True, {'phase': 'drive'}
                if moving and r <= xy_tol and abs(yaw_t) <= yaw_tol:
                    moving = False
                    v_prev = w_prev = 0.0
                if not moving or self.scan_blocked:
                    self.publish_cmd(0.0, 0.0)
                else:
                    v, w, done, info = control.step(x, y, yaw_t, self.cfg, state)
                    if done:
                        moving, v, w = False, 0.0, 0.0
                    dv, dw = self.cfg['a_max'] * self.period, self.cfg['alpha_max'] * self.period
                    v = v_prev + max(-dv, min(dv, v - v_prev))
                    w = w_prev + max(-dw, min(dw, w - w_prev))
                    v_prev, w_prev = v, w
                    self.publish_cmd(v, w)
                    if t - last_log > 1.0:
                        last_log = t
                        self.get_logger().info(f'follow: {info}  cmd v={v:+.3f} w={w:+.3f}')
                time.sleep(max(0.0, self.period - (time.time() - t)))
        finally:
            self.stop()
            with self.lock:
                self.active = False
            self.get_logger().info('follow loop ended')

    # ------------------------------------------------------------- action
    def execute(self, goal_handle):
        fb = NavigateToPose.Feedback()
        t0 = self.get_clock().now()

        def progress(state, v, w):
            cur = self.base_in_odom()
            if cur is None:
                return
            with self.lock:
                gx, gy, _ = self.goal_odom
            fb.distance_remaining = float(math.hypot(gx - cur[0], gy - cur[1]))
            fb.current_pose.header.frame_id = self.odom_frame
            fb.current_pose.header.stamp = self.get_clock().now().to_msg()
            fb.current_pose.pose.position.x, fb.current_pose.pose.position.y = cur[0], cur[1]
            fb.current_pose.pose.orientation = yaw_to_quat(cur[2])
            fb.navigation_time = (self.get_clock().now() - t0).to_msg()
            goal_handle.publish_feedback(fb)

        try:
            ok, msg = self.run_goal(goal_handle.request.pose, progress, lambda: goal_handle.is_cancel_requested)
        finally:
            with self.lock:
                self.active = False
        self.get_logger().info(f'fine adjust {"OK" if ok else "FAILED"}: {msg}')
        if goal_handle.is_cancel_requested:
            goal_handle.canceled()
        elif ok:
            goal_handle.succeed()
        else:
            goal_handle.abort()
        return NavigateToPose.Result()

    # ---------------------------------------------------------- mission bridge



def main(args=None):
    rclpy.init(args=args)
    node = FineAdjustServer()
    ex = MultiThreadedExecutor(num_threads=4)
    ex.add_node(node)
    try:
        ex.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.following = False
        node.cancel_event.set()
        ex.shutdown()
        node.stop()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()

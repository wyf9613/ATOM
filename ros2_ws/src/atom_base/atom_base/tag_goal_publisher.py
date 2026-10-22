#!/usr/bin/env python3
"""Detect one ArUco tag in the RealSense colour image and publish where the BASE should go.

  in   /camera/color/image_raw + /camera/color/camera_info     (realsense2_camera node)
       TF  base_link <- camera optical frame                    (xarm_camera_bridge, follows the arm)
  out  /tag_pose/camera      PoseStamped  tag in the camera optical frame   (for the arm servo)
       /tag_pose/base_link   PoseStamped  tag in base_link                  (debug)
       /fine_adjust/goal_correction  PoseStamped (base_link)  desired base pose, continuously

The desired base pose is defined relative to the tag on the floor plane:
  heading h  = the tag axis `tag_heading_axis` projected on the floor (which way the "front" of
               the bench points, i.e. towards the aisle);  for a tag glued on a vertical surface
               facing the aisle use 'z' (the tag normal), for a tag lying flat use 'x' or 'y'
  goal xy    = tag_xy + desired_distance * h + lateral_offset * perp(h)
  goal yaw   = facing the tag (-h) + yaw_offset
Because the TF is looked up at the image timestamp, the arm may move while this runs.
"""
import math

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo, Image
from tf2_ros import Buffer, TransformListener

from .geom import mat_to_pose, pose_to_mat, yaw_to_quat


class TagDetector:
    def __init__(self, dict_name, marker_id, size_m):
        did = getattr(cv2.aruco, dict_name)
        self.id = marker_id
        s = size_m / 2.0
        self.obj = np.array([[-s, s, 0], [s, s, 0], [s, -s, 0], [-s, -s, 0]], np.float32)
        if hasattr(cv2.aruco, 'ArucoDetector'):          # OpenCV >= 4.7
            d = cv2.aruco.getPredefinedDictionary(did)
            p = cv2.aruco.DetectorParameters()
            p.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
            det = cv2.aruco.ArucoDetector(d, p)
            self._detect = det.detectMarkers
        else:                                             # OpenCV 4.5 (Ubuntu 22.04 apt)
            d = cv2.aruco.Dictionary_get(did)
            p = cv2.aruco.DetectorParameters_create()
            p.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
            self._detect = lambda img: cv2.aruco.detectMarkers(img, d, parameters=p)

    def __call__(self, gray, K, dist):
        corners, ids, _ = self._detect(gray)
        if ids is None:
            return None
        for c, i in zip(corners, ids.ravel()):
            if int(i) != self.id:
                continue
            img = c.reshape(4, 2).astype(np.float32)
            ok, rvec, tvec = cv2.solvePnP(self.obj, img, K, dist, flags=cv2.SOLVEPNP_IPPE_SQUARE)
            if not ok:
                return None
            T = np.eye(4)
            T[:3, :3] = cv2.Rodrigues(rvec)[0]
            T[:3, 3] = tvec.ravel()
            return T
        return None


class TagGoalPublisher(Node):

    def __init__(self):
        super().__init__('tag_goal_publisher')
        self.declare_parameters('', [
            ('image_topic', '/camera/color/image_raw'),
            ('camera_info_topic', '/camera/color/camera_info'),
            ('base_frame', 'base_link'),
            ('aruco_dict', 'DICT_APRILTAG_36h11'),
            ('marker_id', 0),
            ('tag_size_m', 0.040),
            ('tag_heading_axis', 'z'),       # 'x','y','z','-x','-y','-z' : tag axis pointing towards the aisle
            ('desired_distance', 0.50),      # m  base_link origin this far in front of the tag
            ('lateral_offset', 0.0),         # m  +left of the tag heading
            ('yaw_offset_deg', 0.0),         # deg added to "facing the tag"
            ('min_range', 0.15), ('max_range', 3.0),
            ('tf_timeout_s', 0.1),
        ])
        g = lambda n: self.get_parameter(n).value  # noqa: E731
        self.base_frame = g('base_frame')
        self.det = TagDetector(g('aruco_dict'), int(g('marker_id')), float(g('tag_size_m')))
        axis = g('tag_heading_axis')
        self.axis_sign = -1.0 if axis.startswith('-') else 1.0
        self.axis_idx = 'xyz'.index(axis.strip('-'))
        self.d, self.lat = float(g('desired_distance')), float(g('lateral_offset'))
        self.yaw_off = math.radians(float(g('yaw_offset_deg')))
        self.rng = (float(g('min_range')), float(g('max_range')))
        self.tf_timeout = rclpy.duration.Duration(seconds=float(g('tf_timeout_s')))

        self.bridge = CvBridge()
        self.K = self.dist = None
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.pub_cam = self.create_publisher(PoseStamped, '/tag_pose/camera', 10)
        self.pub_base = self.create_publisher(PoseStamped, '/tag_pose/base_link', 10)
        self.pub_goal = self.create_publisher(PoseStamped, '/fine_adjust/goal_correction', 10)
        self.create_subscription(CameraInfo, g('camera_info_topic'), self.on_info, 10)
        self.create_subscription(Image, g('image_topic'), self.on_image, 5)
        self.n_img = self.n_det = 0
        self.create_timer(5.0, self.report)
        self.get_logger().info(f'looking for {g("aruco_dict")} id {g("marker_id")} ({g("tag_size_m")*1000:.0f} mm)')

    def on_info(self, msg):
        self.K = np.array(msg.k, float).reshape(3, 3)
        self.dist = np.array(msg.d, float) if len(msg.d) else np.zeros(5)

    def report(self):
        self.get_logger().info(f'{self.n_img} images, tag seen in {self.n_det}', throttle_duration_sec=4.9)
        self.n_img = self.n_det = 0

    def on_image(self, msg):
        self.n_img += 1
        if self.K is None:
            return
        gray = self.bridge.imgmsg_to_cv2(msg, desired_encoding='mono8')
        T_ct = self.det(gray, self.K, self.dist)
        if T_ct is None:
            return
        rng = float(np.linalg.norm(T_ct[:3, 3]))
        if not (self.rng[0] <= rng <= self.rng[1]):
            return
        self.n_det += 1
        cam = PoseStamped()
        cam.header = msg.header
        cam.pose = mat_to_pose(T_ct)
        self.pub_cam.publish(cam)

        try:
            ts = self.tf_buffer.lookup_transform(self.base_frame, msg.header.frame_id, Time.from_msg(msg.header.stamp),
                                                 timeout=self.tf_timeout)
        except Exception:  # noqa: BLE001
            try:
                ts = self.tf_buffer.lookup_transform(self.base_frame, msg.header.frame_id, Time())
            except Exception as e:  # noqa: BLE001
                self.get_logger().warn(f'no TF {self.base_frame}<-{msg.header.frame_id}: {e}', throttle_duration_sec=2.0)
                return
        T_bt = pose_to_mat(ts.transform) @ T_ct
        base = PoseStamped()
        base.header.stamp, base.header.frame_id = msg.header.stamp, self.base_frame
        base.pose = mat_to_pose(T_bt)
        self.pub_base.publish(base)

        # desired base pose on the floor plane (offsets re-read every frame so `ros2 param set` works live)
        self.d = float(self.get_parameter('desired_distance').value)
        self.lat = float(self.get_parameter('lateral_offset').value)
        self.yaw_off = math.radians(float(self.get_parameter('yaw_offset_deg').value))
        h = self.axis_sign * T_bt[:2, self.axis_idx]
        n = np.linalg.norm(h)
        if n < 0.2:   # axis nearly vertical -> heading undefined
            self.get_logger().warn('tag heading axis is nearly vertical; check tag_heading_axis', throttle_duration_sec=5.0)
            return
        h /= n
        perp = np.array([-h[1], h[0]])
        gxy = T_bt[:2, 3] + self.d * h + self.lat * perp
        gyaw = math.atan2(-h[1], -h[0]) + self.yaw_off
        goal = PoseStamped()
        goal.header.stamp, goal.header.frame_id = msg.header.stamp, self.base_frame
        goal.pose.position.x, goal.pose.position.y = float(gxy[0]), float(gxy[1])
        goal.pose.orientation = yaw_to_quat(gyaw)
        self.pub_goal.publish(goal)


def main(args=None):
    rclpy.init(args=args)
    node = TagGoalPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()

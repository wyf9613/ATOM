#!/usr/bin/env python3
"""Capture one wrist sensor frame and report visible slot markers."""

import argparse
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image

from atom_xarm_sim.camera_experiment import TAG_FAMILY, TAG_SIZE_M


class CameraProbe(Node):
    def __init__(self, mode, output_dir, min_tags):
        super().__init__('atom_camera_probe')
        self.mode = mode
        self.output_dir = output_dir
        self.min_tags = min_tags
        self.info = None
        self.rgb_msg = None
        self.result = None
        self.valid_frames = 0
        self.dictionary = cv2.aruco.Dictionary_get(getattr(cv2.aruco, TAG_FAMILY))
        self.params = cv2.aruco.DetectorParameters_create()
        info_topic = ('/atom/camera_info' if mode == 'rgb'
                      else '/atom/wrist_camera/camera_info')
        self.create_subscription(CameraInfo, info_topic, self._info,
                                 qos_profile_sensor_data)
        image_topic = ('/atom/wrist_camera' if mode == 'rgb'
                       else '/atom/wrist_camera/depth_image')
        self.create_subscription(Image, image_topic, self._image, qos_profile_sensor_data)
        if mode == 'depth':
            self.create_subscription(
                Image, '/atom/wrist_camera/image', self._rgb_image,
                qos_profile_sensor_data,
            )

    def _info(self, msg):
        self.info = msg

    def _rgb_image(self, msg):
        self.rgb_msg = msg

    def _detect_rgb(self, msg, report):
        if msg.encoding not in ('rgb8', 'bgr8'):
            raise ValueError(f'unsupported RGB encoding {msg.encoding}')
        frame = np.frombuffer(msg.data, dtype=np.uint8).reshape(
            msg.height, msg.step
        )[:, :msg.width * 3].reshape(msg.height, msg.width, 3).copy()
        if msg.encoding == 'rgb8':
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = cv2.aruco.detectMarkers(
            gray, self.dictionary, parameters=self.params
        )
        ids_list = [] if ids is None else [int(value) for value in ids.flatten()]
        report['detected_tag_ids'] = ids_list
        report['tag_poses_camera_m'] = {}
        report['tag_rotation_vectors_camera_rad'] = {}
        if ids_list:
            k = np.array(self.info.k, dtype=np.float64).reshape(3, 3)
            d = np.array(self.info.d, dtype=np.float64)
            rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(
                corners, TAG_SIZE_M, k, d
            )
            for index, tag_id in enumerate(ids_list):
                report['tag_poses_camera_m'][str(tag_id)] = [
                    float(value) for value in tvecs[index].reshape(3)
                ]
                report['tag_rotation_vectors_camera_rad'][str(tag_id)] = [
                    float(value) for value in rvecs[index].reshape(3)
                ]
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)
        cv2.imwrite(str(self.output_dir / 'rgb_annotated.png'), frame)
        return ids_list

    def _image(self, msg):
        if self.result is not None or self.info is None:
            return
        if msg.width != self.info.width or msg.height != self.info.height:
            return
        if msg.header.frame_id != self.info.header.frame_id:
            return
        self.valid_frames += 1
        self.output_dir.mkdir(parents=True, exist_ok=True)
        report = {
            'mode': self.mode,
            'image_frame': msg.header.frame_id,
            'image_stamp_sec': msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
            'camera_info_stamp_sec': (
                self.info.header.stamp.sec + self.info.header.stamp.nanosec * 1e-9
            ),
            'width_px': msg.width,
            'height_px': msg.height,
            'encoding': msg.encoding,
        }
        if self.mode == 'rgb':
            ids_list = self._detect_rgb(msg, report)
        else:
            if self.rgb_msg is None:
                return
            rgb_stamp = (self.rgb_msg.header.stamp.sec
                         + self.rgb_msg.header.stamp.nanosec * 1e-9)
            if abs(rgb_stamp - report['image_stamp_sec']) > 0.15:
                return
            if self.rgb_msg.header.frame_id != msg.header.frame_id:
                return
            ids_list = self._detect_rgb(self.rgb_msg, report)
            report['rgb_stamp_sec'] = rgb_stamp
            if msg.encoding != '32FC1':
                self.get_logger().error(f'unsupported depth encoding {msg.encoding}')
                return
            depth = np.frombuffer(msg.data, dtype=np.float32).reshape(
                msg.height, msg.step // 4
            )[:, :msg.width].copy()
            valid = np.isfinite(depth) & (depth > 0.08) & (depth < 2.0)
            report['valid_depth_fraction'] = float(valid.mean())
            if valid.any():
                report['depth_min_m'] = float(depth[valid].min())
                report['depth_max_m'] = float(depth[valid].max())
            np.save(self.output_dir / 'depth_m.npy', depth)
            clipped = np.where(valid, depth, 2.0)
            preview = cv2.applyColorMap(
                np.uint8(255 * (2.0 - clipped) / 1.92), cv2.COLORMAP_TURBO
            )
            cv2.imwrite(str(self.output_dir / 'depth_preview.png'), preview)
        if len(ids_list) < self.min_tags:
            return
        (self.output_dir / 'report.json').write_text(
            json.dumps(report, indent=2) + '\n', encoding='utf-8'
        )
        self.result = report
        self.get_logger().info(f'Probe complete: {report}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('rgb', 'depth'), required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--min-tags', type=int, default=0)
    parser.add_argument('--timeout-sec', type=float, default=20.0)
    args = parser.parse_args()
    if args.min_tags < 0 or args.timeout_sec <= 0:
        parser.error('min-tags must be nonnegative and timeout-sec must be positive')
    rclpy.init()
    node = CameraProbe(args.mode, args.output_dir, args.min_tags)
    deadline = time.monotonic() + args.timeout_sec
    try:
        while rclpy.ok() and node.result is None and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.25)
        if node.result is None:
            if node.valid_frames:
                node.get_logger().error(
                    f'timed out without {args.min_tags} decoded tags '
                    f'after {node.valid_frames} matched frames'
                )
            else:
                node.get_logger().error('timed out waiting for a valid camera frame')
            sys.exit(1)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

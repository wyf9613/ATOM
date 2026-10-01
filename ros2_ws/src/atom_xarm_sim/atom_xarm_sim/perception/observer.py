"""Reusable RackObserver capability; hosted by the task node."""
from copy import deepcopy
import json
import math
import time
import cv2
import numpy as np
from geometry_msgs.msg import (
    PoseStamped,
)
import rclpy
from std_msgs.msg import String
from tf2_ros import (
    TransformException,
)
from atom_xarm_sim.perception.depth_fusion import fuse_rack_depth
from atom_xarm_sim.rack_pose import estimate_rack_pair, rack_observation_complete
from atom_xarm_sim.camera_experiment import (
    SLOT_Y_M,
    TAG_SIZE_M,
)
from atom_xarm_sim.geometry import (
    CAMERA_FRAME,
    _quat_mul,
    _quat_from_matrix,
    _rotate,
    _stamp_to_float,
    _pose_dict,
)

class RackObserver:
    def _camera_info_callback(self, message):
        self.camera_info = message

    def _rgb_callback(self, message):
        self.rgb_message = message

    def _depth_callback(self, message):
        self.depth_message = message

    def _capture_timer(self):
        self._try_capture(self.rgb_message,
                          self.depth_message if self.camera_mode == 'depth' else None)

    def _lookup_transform(self, target_frame, source_frame, stamp=None):
        query_time = rclpy.time.Time() if stamp is None else rclpy.time.Time.from_msg(stamp)
        # Gazebo publishes the robot TF only after the controller spawners
        # finish. The GUI wrapper starts this node as soon as RViz appears, so
        # allow the normal controller startup window here.
        deadline = time.monotonic() + 45.0
        while rclpy.ok() and time.monotonic() < deadline:
            try:
                return self.tf_buffer.lookup_transform(
                    target_frame, source_frame, query_time,
                    timeout=rclpy.duration.Duration(seconds=0.2),
                )
            except TransformException:
                rclpy.spin_once(self, timeout_sec=0.05)
        raise RuntimeError(f'no TF {target_frame} <- {source_frame}')

    @staticmethod
    def _transform_pose(transform, position, orientation):
        tf_q = [
            transform.transform.rotation.x,
            transform.transform.rotation.y,
            transform.transform.rotation.z,
            transform.transform.rotation.w,
        ]
        rotated = _rotate(tf_q, position)
        return [
            transform.transform.translation.x + rotated[0],
            transform.transform.translation.y + rotated[1],
            transform.transform.translation.z + rotated[2],
        ], _quat_mul(tf_q, orientation)

    @staticmethod
    def _image_to_bgr(message):
        if message is None or message.encoding not in ('rgb8', 'bgr8'):
            raise ValueError('RGB image must use rgb8 or bgr8 encoding')
        frame = np.frombuffer(message.data, dtype=np.uint8).reshape(message.height, message.step)
        frame = frame[:, :message.width * 3].reshape(message.height, message.width, 3).copy()
        if message.encoding == 'rgb8':
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return frame

    def _try_capture(self, rgb_message, depth_message):
        if not self.capture_enabled or self.camera_info is None or rgb_message is None:
            return
        stamp = _stamp_to_float(rgb_message.header.stamp)
        if self.last_processed_stamp == stamp:
            return
        if self.approach_phase is not None:
            period = 1.0 / float(self.get_parameter('observation_hz').value)
            if time.monotonic() - self.last_observation_wall < period:
                return
        if rgb_message.width != self.camera_info.width or rgb_message.height != self.camera_info.height:
            return
        if rgb_message.header.frame_id != self.camera_info.header.frame_id:
            return
        if self.camera_mode == 'depth':
            if depth_message is None or depth_message.header.frame_id != rgb_message.header.frame_id:
                return
            if abs(_stamp_to_float(depth_message.header.stamp) - _stamp_to_float(rgb_message.header.stamp)) > 0.035:
                return
        try:
            frame = self._image_to_bgr(rgb_message)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = cv2.aruco.detectMarkers(
                gray, self.dictionary, parameters=self.detector_params
            )
            ids_list = [] if ids is None else [int(value) for value in ids.flatten()]
            self.capture_frame_count += 1
            self.last_detected_ids = ids_list
            if self.capture_frame_count == 1 or self.capture_frame_count % 10 == 0:
                cv2.imwrite(str(self.output_dir / 'rgb_last.png'), frame)
            if not any(tag_id in ids_list for tag_id in self.rack_tag_ids):
                self.last_processed_stamp = stamp
                return
            k = np.array(self.camera_info.k, dtype=np.float64).reshape(3, 3)
            d = np.array(self.camera_info.d, dtype=np.float64)
            # Reject duplicate nested contours for the same marker ID.
            best = {}
            for index, tag_id in enumerate(ids_list):
                area = abs(cv2.contourArea(corners[index].reshape(-1, 2)))
                if tag_id not in best or area > best[tag_id][0]:
                    best[tag_id] = (area, index)
            indices = [value[1] for value in best.values()]
            corners = [corners[index] for index in indices]
            ids_list = [ids_list[index] for index in indices]
            ids = np.asarray(ids_list, dtype=np.int32).reshape(-1, 1)
            rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(corners, TAG_SIZE_M, k, d)
            pair_poses = {}
            visible_rack_ids = sorted(set(ids_list).intersection(self.rack_tag_ids))
            if len(visible_rack_ids) >= 2:
                # Marker +X is image-right (-rack Y); +Y points upwards.
                # Fit the rigid multi-tag board in one image, rather than
                # differencing independently estimated single-tag depths.
                pair_poses = estimate_rack_pair(
                    {tag_id: corners[ids_list.index(tag_id)] for tag_id in visible_rack_ids},
                    k, d, TAG_SIZE_M, SLOT_Y_M)
            rgb_pair_poses = deepcopy(pair_poses)
            if depth_message is not None:
                if depth_message.encoding != '32FC1':
                    raise ValueError(f'unsupported depth encoding {depth_message.encoding}')
                if depth_message.width != rgb_message.width or depth_message.height != rgb_message.height:
                    raise ValueError('depth/RGB image dimensions do not match')
                dtype = '>f4' if depth_message.is_bigendian else '<f4'
                depth = np.frombuffer(depth_message.data, dtype=dtype).reshape(
                    depth_message.height, depth_message.step // 4
                )[:, :depth_message.width]
                valid = np.isfinite(depth) & (depth > 0.08) & (depth < 2.0)
                self.depth_quality = {
                    'rgb_depth_time_difference_sec': abs(_stamp_to_float(depth_message.header.stamp)-stamp),
                    'valid_depth_fraction': float(valid.mean()),
                    'depth_min_m': float(depth[valid].min()) if valid.any() else None,
                    'depth_max_m': float(depth[valid].max()) if valid.any() else None,
                }
                if pair_poses and bool(self.get_parameter('depth_fusion_enabled').value):
                    if not bool(self.get_parameter('depth_registered').value):
                        raise ValueError('depth fusion requires explicitly registered optical-Z depth')
                    pair_poses, fusion = fuse_rack_depth(
                        pair_poses, {tag: corners[ids_list.index(tag)] for tag in visible_rack_ids},
                        depth, k, d, TAG_SIZE_M, SLOT_Y_M)
                    self.depth_quality['fusion'] = fusion
                else:
                    self.depth_quality['fusion'] = {'used': False, 'method': 'rgb_pnp', 'reason': 'disabled_or_no_board'}
            # This code runs inside the image subscription callback. Do not
            # spin a nested executor while waiting for TF; skip this frame and
            # let the next synchronized frame try again.
            camera_to_robot = self.tf_buffer.lookup_transform(
                self.robot_frame,
                rgb_message.header.frame_id,
                rclpy.time.Time.from_msg(rgb_message.header.stamp),
            )
            self.last_processed_stamp = stamp
            self.last_observation_wall = time.monotonic()
            self.capture_error = None
            observed = {}
            rgb_observed = {}
            for index, tag_id in enumerate(ids_list):
                if tag_id not in self.rack_tag_ids:
                    continue
                tag_rotation, tag_translation = pair_poses.get(tag_id, (rvecs[index], tvecs[index]))
                rotation_matrix, _ = cv2.Rodrigues(tag_rotation.reshape(3))
                orientation = _quat_from_matrix(rotation_matrix.tolist())
                position, orientation = self._transform_pose(
                    camera_to_robot,
                    [float(value) for value in tag_translation.reshape(3)],
                    orientation,
                )
                pose = PoseStamped()
                pose.header.frame_id = self.robot_frame
                pose.header.stamp = rgb_message.header.stamp
                pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = position
                pose.pose.orientation.x, pose.pose.orientation.y, pose.pose.orientation.z, pose.pose.orientation.w = orientation
                observed[tag_id] = pose
                baseline_rotation, baseline_translation = rgb_pair_poses.get(tag_id, (rvecs[index], tvecs[index]))
                baseline_matrix = cv2.Rodrigues(np.asarray(baseline_rotation).reshape(3))[0]
                bp, bq = self._transform_pose(camera_to_robot, np.asarray(baseline_translation).reshape(3).tolist(), _quat_from_matrix(baseline_matrix.tolist()))
                baseline = PoseStamped()
                baseline.header = pose.header
                baseline.pose.position.x, baseline.pose.position.y, baseline.pose.position.z = bp
                baseline.pose.orientation.x, baseline.pose.orientation.y, baseline.pose.orientation.z, baseline.pose.orientation.w = bq
                rgb_observed[tag_id] = baseline
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)
            cv2.imwrite(str(self.output_dir / 'rgb_annotated.png'), frame)
            # Keep all detected rack IDs for reporting. Completion requires
            # the full configured rack and selected target in one coherent fit.
            self.observed.update(observed)
            self.rgb_pnp_observed = rgb_observed
            if pair_poses:
                self.rack_observation = deepcopy(observed)
                self.rack_observation_wall = time.monotonic()
            if self.approach_phase is not None and self.task is not None:
                selected = self.task['tag_id']
                if selected in observed:
                    record = {
                        'tag_id': selected, 'action': self.task['action'],
                        'phase': self.approach_phase,
                        'camera_mode': self.camera_mode,
                        'arrival_monotonic_sec': time.monotonic(),
                        'pose': _pose_dict(observed[selected]),
                        'rgb_pnp_pose': _pose_dict(rgb_observed[selected]),
                        'depth_quality': deepcopy(self.depth_quality),
                        'detected_ids': ids_list,
                    }
                    self.phase_observations.append(record)
                    self.all_observations.append(record)
                    with (self.output_dir / 'tag_observations.jsonl').open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps(record) + '\n')
                    message = String()
                    message.data = json.dumps(record)
                    self.observation_publisher.publish(message)
            if self.task is not None and rack_observation_complete(pair_poses, self.rack_tag_ids, self.task['tag_id']):
                self.result = True
        except (TransformException, RuntimeError, ValueError) as error:
            self.capture_error = str(error)

    def _camera_mount(self):
        transform = self._lookup_transform(self.tcp_link, CAMERA_FRAME)
        self.camera_offset = [getattr(transform.transform.translation, axis)
                              for axis in ('x', 'y', 'z')]
        self.camera_rotation = [getattr(transform.transform.rotation, axis)
                                for axis in ('x', 'y', 'z', 'w')]

    def _update_rack_plane_normal(self):
        pair = self.rack_observation
        if pair is None or time.monotonic()-self.rack_observation_wall > float(self.get_parameter('observation_max_age_sec').value):
            raise RuntimeError('rack plane requires a fresh same-frame multi-tag observation')
        if self.task is None or self.task['tag_id'] not in pair or len(pair) < 2:
            raise RuntimeError('fresh rack observation must include selected target and another rack tag')
        tags = sorted(pair)
        first, second = pair[tags[0]].pose.position, pair[tags[-1]].pose.position
        tangent = [second.x - first.x, second.y - first.y]
        separation = math.hypot(*tangent)
        expected_spacing = abs(SLOT_Y_M[tags[-1]] - SLOT_Y_M[tags[0]])
        if abs(separation - expected_spacing) > 0.015:
            raise RuntimeError(f'rack tag separation {separation:.4f} m is inconsistent with rack')
        candidate = [-tangent[1] / separation, tangent[0] / separation]
        if self.rack_plane_normal is not None and sum(
                candidate[i] * self.rack_plane_normal[i] for i in (0, 1)) < 0.0:
            candidate = [-value for value in candidate]
        elif self.rack_plane_normal is None:
            camera_tf = self._lookup_transform(self.robot_frame, CAMERA_FRAME)
            camera = camera_tf.transform.translation
            if candidate[0] * (camera.x - first.x) + candidate[1] * (camera.y - first.y) < 0.0:
                candidate = [-value for value in candidate]
        self.rack_plane_normal = candidate
        self.get_logger().info(
            f'RACK PLANE: normal_xy={candidate}, tag separation={separation:.4f} m'
        )

    @staticmethod
    def _record_pose(record):
        data = record['pose']
        pose = PoseStamped()
        pose.header.frame_id = data['frame_id']
        seconds = data['stamp_sec']
        pose.header.stamp.sec = int(seconds)
        pose.header.stamp.nanosec = int(round((seconds - int(seconds)) * 1e9))
        pose.pose.position.x = data['position_m']['x']
        pose.pose.position.y = data['position_m']['y']
        pose.pose.position.z = data['position_m']['z']
        (pose.pose.orientation.x, pose.pose.orientation.y,
         pose.pose.orientation.z, pose.pose.orientation.w) = data['orientation_xyzw']
        return pose

    def _fresh_observation(self, records, label):
        if not records:
            raise RuntimeError(f'{label}: no selected-tag observation')
        record = records[-1]
        age = time.monotonic() - record['arrival_monotonic_sec']
        if age > float(self.get_parameter('observation_max_age_sec').value):
            raise RuntimeError(
                f'{label}: selected-tag observation stale by {age:.3f} s; '
                f'last_detected_ids={self.last_detected_ids}, capture_error={self.capture_error}'
            )
        pair_age = time.monotonic()-self.rack_observation_wall
        if self.rack_observation is None or pair_age > float(self.get_parameter('observation_max_age_sec').value):
            raise RuntimeError(f'{label}: no fresh same-frame multi-tag rack pose')
        if self.task['tag_id'] not in self.rack_observation:
            raise RuntimeError(f'{label}: selected tag absent from fresh rack observation')
        return deepcopy(self.rack_observation[self.task['tag_id']])

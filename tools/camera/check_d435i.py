"""Read-only camera acceptance snapshot. Does not start tasks or publish motion."""
import json
import time
from pathlib import Path
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, CameraInfo, Imu


def main():
    rclpy.init()
    node = Node('atom_d435i_check')
    samples = {name: [] for name in ('color', 'depth', 'info', 'imu')}
    subscriptions = []
    for name, kind, topic in (
        ('color', Image, '/atom/wrist_camera/color/image_raw'),
        ('depth', Image, '/atom/wrist_camera/aligned_depth_to_color/image_raw'),
        ('info', CameraInfo, '/atom/wrist_camera/color/camera_info'),
        ('imu', Imu, '/atom/wrist_camera/imu'),
    ):
        subscriptions.append(node.create_subscription(
            kind, topic, lambda msg, key=name: samples[key].append(msg) if len(samples[key]) < 60 else None,
            qos_profile_sensor_data))
    start = time.monotonic()
    while time.monotonic() - start < 15 and not all(len(v) >= 30 for v in samples.values()):
        rclpy.spin_once(node, timeout_sec=0.1)
    result = {'elapsed_wall_sec': time.monotonic() - start,
              'sample_counts': {k: len(v) for k, v in samples.items()},
              'hand_eye_calibrated': False}
    errors = []
    if not all(samples.values()):
        errors.append('Missing color/aligned depth/CameraInfo/IMU stream')
    else:
        color, depth, info = (samples[k][-1] for k in ('color', 'depth', 'info'))
        result.update(color_frame=color.header.frame_id, depth_frame=depth.header.frame_id,
                      resolution=[color.width, color.height], depth_encoding=depth.encoding,
                      intrinsics=list(info.k), distortion=list(info.d))
        if color.header.frame_id != depth.header.frame_id or color.header.frame_id != info.header.frame_id:
            errors.append('Aligned depth/color/CameraInfo frames differ')
        if (depth.width, depth.height) != (color.width, color.height) or (info.width, info.height) != (color.width, color.height):
            errors.append('Aligned depth/color/CameraInfo resolutions differ')
        if info.k[0] <= 0 or info.k[4] <= 0:
            errors.append('Invalid focal lengths')
        if depth.encoding not in ('16UC1', '32FC1'):
            errors.append('Unsupported depth encoding')
        else:
            endian = '>' if depth.is_bigendian else '<'
            dtype = np.dtype(endian + ('u2' if depth.encoding == '16UC1' else 'f4'))
            data = np.frombuffer(depth.data, dtype=dtype).reshape(depth.height, depth.step // dtype.itemsize)[:, :depth.width]
            metres = data.astype(float) * (0.001 if depth.encoding == '16UC1' else 1.0)
            valid = np.isfinite(metres) & (metres > 0)
            result['valid_depth_fraction'] = float(valid.mean())
            result['median_valid_depth_m'] = float(np.median(metres[valid])) if valid.any() else None
            if not valid.any():
                errors.append('No positive finite depth samples')
        stamp = lambda m: m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
        deltas = [min(abs(stamp(d) - stamp(c)) for c in samples['color']) for d in samples['depth']]
        result['nearest_color_depth_stamp_max_sec'] = max(deltas)
        if max(deltas) > 0.05:
            errors.append('Color/depth timestamps exceed provisional 50 ms gate')
    result['errors'] = errors
    result['passed'] = not errors
    output = Path('/workspace/tmp/camera_calibration')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'd435i_check.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    node.destroy_node()
    rclpy.shutdown()
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())

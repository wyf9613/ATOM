"""Shared geometry and provisional simulation constants; no ROS node."""
import math

INPUT_TOPIC = '/atom/pre_observation_target'

TARGET_POSE_TOPIC = '/atom/pre_observation_pose'

ROBOT_FRAME = 'link_base'

WORLD_FRAME = 'world'

TCP_LINK = 'link_eef'

ROBOT_SPAWN_XYZ_M = (-0.2, -0.54, 1.021)

ROBOT_SPAWN_YAW_RAD = -1.571

TAG_LOCAL_X_M = -0.0695

TAG_LOCAL_Z_M = 0.029

RACK_Z_M = 1.159

CAMERA_EEF_VERTICAL_OFFSET_M = 0.080

POSITION_TOLERANCE_M = 0.005

ORIENTATION_TOLERANCE_RAD = 0.10

FINAL_ORIENTATION_TOLERANCE_RAD = 0.25

FRONT_OFFSET_M = 0.20

ALIGNMENT_DISTANCE_M = 0.40

FINAL_DISTANCE_M = 0.10

CAMERA_FRAME = 'wrist_camera_optical_frame'

def _normalise(values):
    norm = math.sqrt(sum(value * value for value in values))
    if norm < 1e-12:
        raise ValueError('zero quaternion/vector cannot be normalised')
    return [value / norm for value in values]

def _quat_mul(first, second):
    ax, ay, az, aw = first
    bx, by, bz, bw = second
    return [
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    ]

def _quat_from_yaw(yaw):
    return [0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)]

def _quat_from_pitch(pitch):
    return [0.0, math.sin(pitch / 2.0), 0.0, math.cos(pitch / 2.0)]

def _quat_conjugate(quaternion):
    return [-quaternion[0], -quaternion[1], -quaternion[2], quaternion[3]]

def _angle(a, b):
    a, b = _normalise(a), _normalise(b)
    return math.acos(max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b)))))

def _tilt_delta(first, second):
    # The third row of R is invariant under a world-Z (yaw) rotation.
    return _angle(_rotation_matrix(first)[2], _rotation_matrix(second)[2])

def _quat_from_matrix(matrix):
    trace = matrix[0][0] + matrix[1][1] + matrix[2][2]
    if trace > 0.0:
        scale = math.sqrt(trace + 1.0) * 2.0
        return _normalise([
            (matrix[2][1] - matrix[1][2]) / scale,
            (matrix[0][2] - matrix[2][0]) / scale,
            (matrix[1][0] - matrix[0][1]) / scale,
            0.25 * scale,
        ])
    diagonal = [matrix[0][0], matrix[1][1], matrix[2][2]]
    index = max(range(3), key=lambda item: diagonal[item])
    if index == 0:
        scale = math.sqrt(max(1e-16, 1.0 + matrix[0][0] - matrix[1][1] - matrix[2][2])) * 2.0
        return _normalise([
            0.25 * scale,
            (matrix[0][1] + matrix[1][0]) / scale,
            (matrix[0][2] + matrix[2][0]) / scale,
            (matrix[2][1] - matrix[1][2]) / scale,
        ])
    if index == 1:
        scale = math.sqrt(max(1e-16, 1.0 + matrix[1][1] - matrix[0][0] - matrix[2][2])) * 2.0
        return _normalise([
            (matrix[0][1] + matrix[1][0]) / scale,
            0.25 * scale,
            (matrix[1][2] + matrix[2][1]) / scale,
            (matrix[0][2] - matrix[2][0]) / scale,
        ])
    scale = math.sqrt(max(1e-16, 1.0 + matrix[2][2] - matrix[0][0] - matrix[1][1])) * 2.0
    return _normalise([
        (matrix[0][2] + matrix[2][0]) / scale,
        (matrix[1][2] + matrix[2][1]) / scale,
        0.25 * scale,
        (matrix[1][0] - matrix[0][1]) / scale,
    ])

def _rotation_matrix(quaternion):
    x, y, z, w = _normalise(quaternion)
    return [
        [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)],
        [2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)],
        [2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)],
    ]

def _rotate(quaternion, vector):
    matrix = _rotation_matrix(quaternion)
    return [
        sum(matrix[row][column] * vector[column] for column in range(3))
        for row in range(3)
    ]

def _stamp_to_float(stamp):
    return stamp.sec + stamp.nanosec * 1e-9

def _pose_dict(pose):
    return {
        'frame_id': pose.header.frame_id,
        'stamp_sec': _stamp_to_float(pose.header.stamp),
        'position_m': {
            'x': pose.pose.position.x,
            'y': pose.pose.position.y,
            'z': pose.pose.position.z,
        },
        'orientation_xyzw': [
            pose.pose.orientation.x,
            pose.pose.orientation.y,
            pose.pose.orientation.z,
            pose.pose.orientation.w,
        ],
    }

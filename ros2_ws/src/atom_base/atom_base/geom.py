"""Small planar/3-D pose helpers shared by the fine-adjust nodes (no scipy / tf_transformations)."""
import math

import numpy as np
from geometry_msgs.msg import Pose, PoseStamped, Quaternion, Transform, TransformStamped


def wrap(a):
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def quat_to_mat(q):
    x, y, z, w = q.x, q.y, q.z, q.w
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def mat_to_quat(R):
    """Rotation matrix -> geometry_msgs Quaternion."""
    t = np.trace(R)
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        w, x, y, z = 0.25 * s, (R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        w, x, y, z = (R[2, 1] - R[1, 2]) / s, 0.25 * s, (R[0, 1] + R[1, 0]) / s, (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        w, x, y, z = (R[0, 2] - R[2, 0]) / s, (R[0, 1] + R[1, 0]) / s, 0.25 * s, (R[1, 2] + R[2, 1]) / s
    else:
        s = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        w, x, y, z = (R[1, 0] - R[0, 1]) / s, (R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s, 0.25 * s
    q = Quaternion()
    q.x, q.y, q.z, q.w = float(x), float(y), float(z), float(w)
    return q


def rpy_to_mat(roll, pitch, yaw):
    """R = Rz(yaw) Ry(pitch) Rx(roll)  (xArm / ROS fixed-axis XYZ convention)."""
    cr, sr, cp, sp, cy, sy = math.cos(roll), math.sin(roll), math.cos(pitch), math.sin(pitch), math.cos(yaw), math.sin(yaw)
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def yaw_of_quat(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def yaw_to_quat(yaw):
    q = Quaternion()
    q.z, q.w = math.sin(yaw / 2.0), math.cos(yaw / 2.0)
    return q


def pose_to_mat(p):
    """geometry_msgs Pose or Transform -> 4x4."""
    T = np.eye(4)
    if isinstance(p, Transform):
        T[:3, :3] = quat_to_mat(p.rotation)
        T[:3, 3] = [p.translation.x, p.translation.y, p.translation.z]
    else:
        T[:3, :3] = quat_to_mat(p.orientation)
        T[:3, 3] = [p.position.x, p.position.y, p.position.z]
    return T


def mat_to_pose(T):
    p = Pose()
    p.position.x, p.position.y, p.position.z = (float(v) for v in T[:3, 3])
    p.orientation = mat_to_quat(T[:3, :3])
    return p


def mat_to_transform_stamped(T, parent, child, stamp):
    ts = TransformStamped()
    ts.header.stamp = stamp
    ts.header.frame_id = parent
    ts.child_frame_id = child
    ts.transform.translation.x, ts.transform.translation.y, ts.transform.translation.z = (float(v) for v in T[:3, 3])
    ts.transform.rotation = mat_to_quat(T[:3, :3])
    return ts


def transform_pose(pose_stamped, ts):
    """PoseStamped in frame A -> PoseStamped in frame B given TransformStamped B<-A."""
    T = pose_to_mat(ts.transform) @ pose_to_mat(pose_stamped.pose)
    out = PoseStamped()
    out.header.stamp = pose_stamped.header.stamp
    out.header.frame_id = ts.header.frame_id
    out.pose = mat_to_pose(T)
    return out


def planar(pose):
    """Pose -> (x, y, yaw)."""
    return pose.position.x, pose.position.y, yaw_of_quat(pose.orientation)


def mat_to_rpy(R):
    """Rotation matrix -> (roll, pitch, yaw) with R = Rz(yaw) Ry(pitch) Rx(roll)  (xArm convention)."""
    pitch = math.asin(max(-1.0, min(1.0, -R[2, 0])))
    if abs(math.cos(pitch)) > 1e-6:
        roll, yaw = math.atan2(R[2, 1], R[2, 2]), math.atan2(R[1, 0], R[0, 0])
    else:
        roll, yaw = math.atan2(-R[1, 2], R[1, 1]), 0.0
    return roll, pitch, yaw

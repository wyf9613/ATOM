"""Reusable SimulationInputs capability; hosted by the task node."""
import math
import random
from geometry_msgs.msg import (
    PoseStamped,
)
from atom_xarm_sim.camera_experiment import (
    SLOT_Y_M,
)
from atom_xarm_sim.geometry import (
    ROBOT_SPAWN_XYZ_M,
    ROBOT_SPAWN_YAW_RAD,
    TAG_LOCAL_X_M,
    TAG_LOCAL_Z_M,
    RACK_Z_M,
    CAMERA_EEF_VERTICAL_OFFSET_M,
    _quat_mul,
    _quat_from_yaw,
    _quat_from_matrix,
    _rotation_matrix,
    _rotate,
)

class SimulationInputs:
    def _rack_pose(self):
        return 0.50 - self.rack_dy, -1.00 + self.rack_dx, self.rack_dyaw

    def _expected_tag_world(self, tag_id):
        rack_x, rack_y, rack_yaw = self._rack_pose()
        local = [TAG_LOCAL_X_M, SLOT_Y_M[tag_id], TAG_LOCAL_Z_M]
        c = math.cos(rack_yaw)
        s = math.sin(rack_yaw)
        position = [
            rack_x + c * local[0] - s * local[1],
            rack_y + s * local[0] + c * local[1],
            RACK_Z_M + local[2],
        ]
        # Tag axes follow the generated marker: image-right=-Y, image-down=-Z,
        # and the right-handed marker normal is +X in the rack frame.
        local_matrix = [[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]]
        rack_rotation = _rotation_matrix(_quat_from_yaw(rack_yaw))
        matrix = [
            [sum(rack_rotation[row][k] * local_matrix[k][column] for k in range(3))
             for column in range(3)]
            for row in range(3)
        ]
        return position, _quat_from_matrix(matrix)

    def _expected_in_robot_frame(self):
        expected = {}
        # The launch file spawns the Gazebo model away from world origin, but
        # its temporary world -> link_base TF is identity for MoveIt. Convert
        # fixture truth through that known spawn pose instead of using the
        # identity TF as if it described the physical Gazebo model pose.
        spawn_q = _quat_from_yaw(ROBOT_SPAWN_YAW_RAD)
        inverse_spawn_q = [
            -spawn_q[0], -spawn_q[1], -spawn_q[2], spawn_q[3]
        ]
        for tag_id in self.rack_tag_ids:
            position, orientation = self._expected_tag_world(tag_id)
            relative = [
                position[0] - ROBOT_SPAWN_XYZ_M[0],
                position[1] - ROBOT_SPAWN_XYZ_M[1],
                position[2] - ROBOT_SPAWN_XYZ_M[2],
            ]
            transformed_position = _rotate(inverse_spawn_q, relative)
            transformed_orientation = _quat_mul(inverse_spawn_q, orientation)
            pose = PoseStamped()
            pose.header.frame_id = self.robot_frame
            pose.header.stamp = self.get_clock().now().to_msg()
            pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = transformed_position
            pose.pose.orientation.x, pose.pose.orientation.y, pose.pose.orientation.z, pose.pose.orientation.w = transformed_orientation
            expected[tag_id] = pose
        return expected

    def _publish_provisional_input(self, expected):
        rack_position = [
            sum(pose.pose.position.x for pose in expected.values()) / len(expected),
            sum(pose.pose.position.y for pose in expected.values()) / len(expected),
        ]
        self.theoretical_bearing = math.atan2(rack_position[1], rack_position[0])
        noise_limit = float(self.get_parameter('xy_noise_m').value)
        if not math.isfinite(noise_limit) or noise_limit < 0.0:
            raise RuntimeError('xy_noise_m must be nonnegative and finite')
        rng = random.Random(int(self.get_parameter('random_seed').value))
        noisy_xy = [value + rng.uniform(-noise_limit, noise_limit) for value in rack_position]
        if math.hypot(*noisy_xy) < 1e-6:
            raise RuntimeError('coarse rack XY is at base origin')
        self.observation_bearing = math.atan2(noisy_xy[1], noisy_xy[0])
        # z remains the desired TCP height, not the rack surface height.
        target_height = sum(pose.pose.position.z for pose in expected.values()) / len(expected)
        tcp_height = target_height + CAMERA_EEF_VERTICAL_OFFSET_M
        message = PoseStamped()
        message.header.frame_id = self.robot_frame
        message.header.stamp = self.get_clock().now().to_msg()
        message.pose.position.x, message.pose.position.y = noisy_xy
        message.pose.position.z = tcp_height
        # Direction is derived by the consumer; quaternion carries no bearing.
        message.pose.orientation.w = 1.0
        self.input_publisher.publish(message)
        self.pre_observation_command = message
        self.get_logger().info(
            f'INPUT: {self.input_topic} noisy rack XY={noisy_xy} m, '
            f'bearing={self.observation_bearing:.6f} rad, tcp_height={tcp_height:.6f} m'
        )

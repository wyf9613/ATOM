"""Reusable ApproachMotion capability; hosted by the task node."""
from copy import deepcopy
import math
import time
from types import SimpleNamespace
from controller_manager_msgs.srv import ListControllers
from geometry_msgs.msg import Pose, PoseStamped
from moveit_msgs.action import ExecuteTrajectory, MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint, MoveItErrorCodes, OrientationConstraint, PositionConstraint, VisibilityConstraint
from moveit_msgs.srv import GetCartesianPath, GetPositionFK, GetPositionIK
import rclpy
from shape_msgs.msg import SolidPrimitive
from atom_xarm_sim.camera_experiment import (
    TAG_SIZE_M,
)
from atom_xarm_sim.geometry import (
    POSITION_TOLERANCE_M,
    ORIENTATION_TOLERANCE_RAD,
    FINAL_ORIENTATION_TOLERANCE_RAD,
    FRONT_OFFSET_M,
    _normalise,
    _quat_mul,
    _quat_from_yaw,
    _quat_conjugate,
    _angle,
    _tilt_delta,
    _rotate,
    _pose_dict,
)

class ApproachMotion:
    def _current_tcp_pose(self):
        transform = self._lookup_transform(self.robot_frame, self.tcp_link)
        pose = PoseStamped()
        pose.header.frame_id = self.robot_frame
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = transform.transform.translation.x
        pose.pose.position.y = transform.transform.translation.y
        pose.pose.position.z = transform.transform.translation.z
        pose.pose.orientation = transform.transform.rotation
        return pose

    def _wait_for_controllers(self):
        if not self.controller_client.wait_for_service(timeout_sec=45.0):
            raise RuntimeError('/controller_manager/list_controllers is unavailable')
        required = {'joint_state_broadcaster', 'uf850_traj_controller'}
        deadline = time.monotonic() + 45.0
        observed = {}
        while rclpy.ok() and time.monotonic() < deadline:
            future = self.controller_client.call_async(ListControllers.Request())
            rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)
            response = future.result() if future.done() else None
            if response is not None:
                observed = {controller.name: controller.state for controller in response.controller}
                if all(observed.get(name) == 'active' for name in required):
                    self.get_logger().info(
                        'PASS: joint-state and UF850 trajectory controllers are active'
                    )
                    # MoveIt's simple controller manager can discover the
                    # FollowJointTrajectory action a moment after the
                    # controller manager reports ACTIVE.
                    deadline_settle = time.monotonic() + 5.0
                    while rclpy.ok() and time.monotonic() < deadline_settle:
                        rclpy.spin_once(self, timeout_sec=0.1)
                    return
            time.sleep(0.2)
        raise RuntimeError(f'controllers are not active: observed={observed}')

    @staticmethod
    def _orientation_constraint(orientation, frame_id, link_name):
        constraint = OrientationConstraint()
        constraint.header.frame_id = frame_id
        constraint.link_name = link_name
        constraint.orientation = deepcopy(orientation)
        constraint.absolute_x_axis_tolerance = ORIENTATION_TOLERANCE_RAD
        constraint.absolute_y_axis_tolerance = ORIENTATION_TOLERANCE_RAD
        constraint.absolute_z_axis_tolerance = ORIENTATION_TOLERANCE_RAD
        constraint.parameterization = OrientationConstraint.ROTATION_VECTOR
        constraint.weight = 1.0
        constraints = Constraints(name='pre_observation_goal')
        constraints.orientation_constraints.append(constraint)
        return constraints

    def _pose_constraints(self, pose):
        constraints = self._orientation_constraint(pose.pose.orientation, pose.header.frame_id, self.tcp_link)
        position = PositionConstraint()
        position.header.frame_id = pose.header.frame_id
        position.link_name = self.tcp_link
        sphere = SolidPrimitive()
        sphere.type = SolidPrimitive.SPHERE
        sphere.dimensions = [POSITION_TOLERANCE_M]
        sphere_pose = Pose()
        sphere_pose.position = deepcopy(pose.pose.position)
        sphere_pose.orientation.w = 1.0
        position.constraint_region.primitives.append(sphere)
        position.constraint_region.primitive_poses.append(sphere_pose)
        position.weight = 1.0
        constraints.position_constraints.append(position)
        return constraints

    def _move_to_pre_observation(self, target):
        if not self.move_group_client.wait_for_server(timeout_sec=30.0):
            raise RuntimeError('/move_action is unavailable')
        goal = MoveGroup.Goal()
        goal.request.group_name = 'uf850'
        goal.request.num_planning_attempts = 10
        goal.request.allowed_planning_time = 10.0
        goal.request.max_velocity_scaling_factor = 0.05
        goal.request.max_acceleration_scaling_factor = 0.05
        goal.request.start_state.is_diff = True
        goal.request.goal_constraints.append(self._pose_constraints(target))
        goal.planning_options.plan_only = False
        goal.planning_options.replan = False
        goal.planning_options.planning_scene_diff.is_diff = True
        goal.planning_options.planning_scene_diff.robot_state.is_diff = True
        send_future = self.move_group_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=15.0)
        handle = send_future.result() if send_future.done() else None
        if handle is None or not handle.accepted:
            raise RuntimeError('MoveIt rejected the pre-observation goal')
        result_future = handle.get_result_async()
        deadline = time.monotonic() + 90.0
        while rclpy.ok() and not result_future.done() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
        if not result_future.done():
            raise RuntimeError('pre-observation execution timed out')
        result = result_future.result().result
        if result.error_code.val != MoveItErrorCodes.SUCCESS:
            raise RuntimeError(f'pre-observation MoveIt failed with code {result.error_code.val}')
        current = self._current_tcp_pose()
        position_error = math.sqrt(sum(
            (getattr(current.pose.position, axis) - getattr(target.pose.position, axis)) ** 2
            for axis in ('x', 'y', 'z')
        ))
        dot = abs(sum(
            left * right for left, right in zip(
                [current.pose.orientation.x, current.pose.orientation.y,
                 current.pose.orientation.z, current.pose.orientation.w],
                [target.pose.orientation.x, target.pose.orientation.y,
                 target.pose.orientation.z, target.pose.orientation.w],
            )
        ))
        orientation_error = 2.0 * math.acos(max(-1.0, min(1.0, dot)))
        target_bearing = math.atan2(target.pose.position.y, target.pose.position.x)
        measured_ray = _rotate(
            [current.pose.orientation.x, current.pose.orientation.y,
             current.pose.orientation.z, current.pose.orientation.w],
            [0.0, 0.0, 1.0],
        )
        target_ray = [math.cos(target_bearing), math.sin(target_bearing), 0.0]
        ray_dot = max(-1.0, min(1.0, sum(a * b for a, b in zip(measured_ray, target_ray))))
        self.measured_ray_error_rad = math.acos(ray_dot)
        if position_error > POSITION_TOLERANCE_M or orientation_error > FINAL_ORIENTATION_TOLERANCE_RAD:
            raise RuntimeError(
                f'pre-observation final error exceeds tolerance: '
                f'position={position_error:.5f} m, orientation={orientation_error:.5f} rad'
            )
        self.get_logger().info(
            f'PASS: pre-observation MoveIt execution '
            f'(position error={position_error:.5f} m, orientation error={orientation_error:.5f} rad, '
            f'pointing-ray error={self.measured_ray_error_rad:.5f} rad)'
        )

    @staticmethod
    def _quaternion(pose):
        return [getattr(pose.orientation, axis) for axis in ('x', 'y', 'z', 'w')]

    def _geometry(self, eef, tag):
        e = [getattr(eef.pose.position, axis) for axis in ('x', 'y', 'z')]
        q = self._quaternion(eef.pose)
        extension = _rotate(q, [0.0, 0.0, 1.0])
        front = [e[i] + FRONT_OFFSET_M * extension[i] for i in range(3)]
        camera = [e[i] + _rotate(q, self.camera_offset)[i] for i in range(3)]
        optical = _rotate(_quat_mul(q, self.camera_rotation), [0.0, 0.0, 1.0])
        t = [getattr(tag.pose.position, axis) for axis in ('x', 'y', 'z')]
        if self.rack_plane_normal is None:
            normal = _rotate(self._quaternion(tag.pose), [0.0, 0.0, 1.0])
            if sum(normal[i] * (camera[i] - t[i]) for i in range(3)) < 0.0:
                normal = [-x for x in normal]
        else:
            normal = [self.rack_plane_normal[0], self.rack_plane_normal[1], 0.0]
        horizontal = _normalise(normal[:2])
        signed_distance = sum(normal[i] * (front[i] - t[i]) for i in range(3))
        lateral = abs((front[0] - t[0]) * horizontal[1] -
                      (front[1] - t[1]) * horizontal[0])
        return {
            'front': front, 'camera': camera, 'optical': optical,
            'normal': normal, 'horizontal_normal': horizontal,
            'distance_m': signed_distance, 'lateral_m': lateral,
            'sight_angle_rad': _angle(optical, [t[i] - camera[i] for i in range(3)]),
        }

    def _approach_target(self, tag, distance):
        initial = self.approach_start_pose
        base_q = self._quaternion(initial.pose)
        t = [getattr(tag.pose.position, axis) for axis in ('x', 'y', 'z')]
        reference = self._geometry(initial, tag)
        n = reference['horizontal_normal']
        front_xy = [t[i] + distance * n[i] for i in (0, 1)]
        best = None
        # A world-Z rotation preserves the measured height, roll and pitch.
        # Search it with the real camera offset, not the gripper axis.
        for index in range(721):
            delta = -math.pi + index * 2.0 * math.pi / 720.0
            q = _quat_mul(_quat_from_yaw(delta), base_q)
            direction = _rotate(q, [0.0, 0.0, 1.0])
            e = [front_xy[0] - FRONT_OFFSET_M * direction[0],
                 front_xy[1] - FRONT_OFFSET_M * direction[1],
                 initial.pose.position.z]
            camera_offset = _rotate(q, self.camera_offset)
            camera = [e[i] + camera_offset[i] for i in range(3)]
            optical = _rotate(_quat_mul(q, self.camera_rotation), [0.0, 0.0, 1.0])
            error = _angle(optical, [t[i] - camera[i] for i in range(3)])
            if best is None or error < best[0]:
                best = (error, q, e)
        tolerance = float(self.get_parameter('visibility_tolerance_rad').value)
        if best[0] > tolerance:
            raise RuntimeError(f'camera cannot face tag at fixed height/tilt: best angle={best[0]:.3f} rad')
        target = PoseStamped()
        target.header.frame_id = self.robot_frame
        target.header.stamp = self.get_clock().now().to_msg()
        target.pose.position.x, target.pose.position.y, target.pose.position.z = best[2]
        target.pose.orientation.x, target.pose.orientation.y, target.pose.orientation.z, target.pose.orientation.w = best[1]
        return target

    def _approach_constraints(self, tag, normal_ray=None):
        constraints = Constraints(name='approach_path')
        orientation = OrientationConstraint()
        orientation.header.frame_id = self.robot_frame
        orientation.link_name = self.tcp_link
        orientation.orientation = deepcopy(self.approach_start_pose.pose.orientation)
        # MoveIt's constraint parameterization couples world-yaw and local
        # tilt at this posture. Use a planning envelope, then reject any
        # returned trajectory whose FK exceeds the actual tilt tolerance.
        orientation.absolute_x_axis_tolerance = 0.15
        orientation.absolute_y_axis_tolerance = 0.15
        orientation.absolute_z_axis_tolerance = math.pi
        orientation.parameterization = OrientationConstraint.ROTATION_VECTOR
        orientation.weight = 1.0
        constraints.orientation_constraints.append(orientation)

        height = PositionConstraint()
        height.header.frame_id = self.robot_frame
        height.link_name = self.tcp_link
        slab = SolidPrimitive()
        slab.type = SolidPrimitive.BOX
        slab.dimensions = [4.0, 4.0, 2.0 * float(self.get_parameter('height_tolerance_m').value)]
        slab_pose = Pose()
        slab_pose.position.z = self.approach_start_pose.pose.position.z
        slab_pose.orientation.w = 1.0
        height.constraint_region.primitives.append(slab)
        height.constraint_region.primitive_poses.append(slab_pose)
        height.weight = 1.0
        constraints.position_constraints.append(height)

        visibility = VisibilityConstraint()
        visibility.target_radius = TAG_SIZE_M / 2.0
        visibility.target_pose = deepcopy(tag)
        visibility.cone_sides = 12
        visibility.sensor_pose.header.frame_id = self.tcp_link
        visibility.sensor_pose.pose.position.x, visibility.sensor_pose.pose.position.y, visibility.sensor_pose.pose.position.z = self.camera_offset
        visibility.sensor_pose.pose.orientation.x, visibility.sensor_pose.pose.orientation.y, visibility.sensor_pose.pose.orientation.z, visibility.sensor_pose.pose.orientation.w = self.camera_rotation
        visibility.sensor_view_direction = VisibilityConstraint.SENSOR_Z
        visibility.max_view_angle = 0.7
        visibility.max_range_angle = float(self.get_parameter('visibility_tolerance_rad').value)
        visibility.weight = 1.0
        if bool(self.get_parameter('moveit_visibility_constraint').value):
            constraints.visibility_constraints.append(visibility)

        if normal_ray is not None:
            start_front, end_front, horizontal_normal = normal_ray
            corridor = PositionConstraint()
            corridor.header.frame_id = self.robot_frame
            corridor.link_name = self.tcp_link
            corridor.target_point_offset.z = FRONT_OFFSET_M
            box = SolidPrimitive()
            box.type = SolidPrimitive.BOX
            box.dimensions = [math.dist(start_front[:2], end_front[:2]) + 0.04,
                              2.0 * float(self.get_parameter('ray_width_m').value), 0.05]
            box_pose = Pose()
            box_pose.position.x = (start_front[0] + end_front[0]) / 2.0
            box_pose.position.y = (start_front[1] + end_front[1]) / 2.0
            box_pose.position.z = (start_front[2] + end_front[2]) / 2.0
            box_pose.orientation.z = math.sin(math.atan2(horizontal_normal[1], horizontal_normal[0]) / 2.0)
            box_pose.orientation.w = math.cos(math.atan2(horizontal_normal[1], horizontal_normal[0]) / 2.0)
            corridor.constraint_region.primitives.append(box)
            corridor.constraint_region.primitive_poses.append(box_pose)
            corridor.weight = 1.0
            constraints.position_constraints.append(corridor)
        return constraints

    def _validate_planned_path(self, trajectory, tag, ray):
        if not self.fk_client.wait_for_service(timeout_sec=10.0):
            raise RuntimeError('/compute_fk is unavailable for whole-path validation')
        max_height = float(self.get_parameter('height_tolerance_m').value)
        max_tilt = float(self.get_parameter('tilt_tolerance_rad').value)
        max_sight = float(self.get_parameter('visibility_tolerance_rad').value)
        max_ray = float(self.get_parameter('ray_width_m').value)
        baseline = self._quaternion(self.approach_start_pose.pose)
        worst = {'height_m': 0.0, 'tilt_rad': 0.0, 'sight_rad': 0.0, 'ray_m': 0.0}
        for index, point in enumerate(trajectory.joint_trajectory.points):
            request = GetPositionFK.Request()
            request.header.frame_id = self.robot_frame
            request.fk_link_names = [self.tcp_link]
            request.robot_state.joint_state.name = list(trajectory.joint_trajectory.joint_names)
            request.robot_state.joint_state.position = list(point.positions)
            future = self.fk_client.call_async(request)
            rclpy.spin_until_future_complete(self, future, timeout_sec=3.0)
            response = future.result() if future.done() else None
            if (response is None or response.error_code.val != MoveItErrorCodes.SUCCESS or
                    len(response.pose_stamped) != 1):
                raise RuntimeError(f'FK failed at trajectory point {index}')
            pose = response.pose_stamped[0]
            geometry = self._geometry(pose, tag)
            height = abs(pose.pose.position.z - self.approach_start_pose.pose.position.z)
            tilt = _tilt_delta(self._quaternion(pose.pose), baseline)
            sight = geometry['sight_angle_rad']
            lateral = geometry['lateral_m'] if ray is not None else 0.0
            worst['height_m'] = max(worst['height_m'], height)
            worst['tilt_rad'] = max(worst['tilt_rad'], tilt)
            worst['sight_rad'] = max(worst['sight_rad'], sight)
            worst['ray_m'] = max(worst['ray_m'], lateral)
            if (height > max_height + 0.002 or tilt > max_tilt + 0.02 or
                    sight > max_sight or lateral > max_ray + 0.005):
                raise RuntimeError(
                    f'planned path violates constraints at point {index}: '
                    f'height={height:.3f} m, tilt={tilt:.3f} rad, '
                    f'sight={sight:.3f} rad, ray={lateral:.3f} m'
                )
        return worst

    def _plan_candidate(self, goal, label):
        send = self.move_group_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send, timeout_sec=15.0)
        handle = send.result() if send.done() else None
        if handle is None or not handle.accepted:
            raise RuntimeError(f'{label}: MoveIt rejected planning request')
        future = handle.get_result_async()
        rclpy.spin_until_future_complete(self, future, timeout_sec=45.0)
        if not future.done():
            raise RuntimeError(f'{label}: planning timed out')
        response = future.result().result
        if response.error_code.val != MoveItErrorCodes.SUCCESS:
            raise RuntimeError(f'{label}: planning failed, MoveIt code {response.error_code.val}')
        return response

    def _cartesian_candidate(self, label, target, tag, ray):
        if not self.cartesian_client.wait_for_service(timeout_sec=10.0):
            raise RuntimeError('/compute_cartesian_path is unavailable')
        start = self._current_tcp_pose()
        start_q = self._quaternion(start.pose)
        target_q = self._quaternion(target.pose)
        relative = _quat_mul(target_q, _quat_conjugate(start_q))
        yaw_change = math.atan2(2.0 * (relative[3] * relative[2] + relative[0] * relative[1]),
                                1.0 - 2.0 * (relative[1] ** 2 + relative[2] ** 2))
        request = GetCartesianPath.Request()
        request.header.frame_id = self.robot_frame
        request.start_state.is_diff = True
        request.group_name = 'uf850'
        request.link_name = self.tcp_link
        request.max_step = 0.01
        request.jump_threshold = 0.0
        request.avoid_collisions = True
        # Explicit world-yaw interpolation keeps measured roll/pitch and
        # link_eef height fixed, including between the coarse anchors.
        for index in range(1, 21):
            alpha = index / 20.0
            waypoint = Pose()
            waypoint.position.x = start.pose.position.x + alpha * (target.pose.position.x - start.pose.position.x)
            waypoint.position.y = start.pose.position.y + alpha * (target.pose.position.y - start.pose.position.y)
            waypoint.position.z = self.approach_start_pose.pose.position.z
            q = _quat_mul(_quat_from_yaw(alpha * yaw_change), start_q)
            waypoint.orientation.x, waypoint.orientation.y, waypoint.orientation.z, waypoint.orientation.w = q
            request.waypoints.append(waypoint)
        constraints = self._approach_constraints(tag, ray)
        constraints.orientation_constraints.clear()
        request.path_constraints = constraints
        request.max_velocity_scaling_factor = 0.04
        request.max_acceleration_scaling_factor = 0.04
        planning_started = time.monotonic()
        future = self.cartesian_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=45.0)
        response = future.result() if future.done() else None
        if response is None:
            raise RuntimeError(f'{label}: Cartesian planning timed out')
        if response.error_code.val != MoveItErrorCodes.SUCCESS or response.fraction < 0.999:
            raise RuntimeError(
                f'{label}: Cartesian path incomplete (fraction={response.fraction:.4f}, '
                f'code={response.error_code.val})'
            )
        return SimpleNamespace(
            planned_trajectory=response.solution,
            planning_time=time.monotonic() - planning_started,
        )

    def _plan_and_execute_approach(self, label, target, tag, ray=None):
        self.current_stage = 'realignment' if label.startswith('realignment_') else label
        self.planning_attempts[label] = 0
        ik_solution = None
        if self.ik_client.wait_for_service(timeout_sec=5.0):
            reference_front = self._geometry(target, tag)['front']
            for yaw_offset in (0.0, -0.025, 0.025, -0.05, 0.05,
                               -0.10, 0.10, -0.15, 0.15, -0.20, 0.20):
                candidate = deepcopy(target)
                if yaw_offset:
                    q = _quat_mul(_quat_from_yaw(yaw_offset), self._quaternion(target.pose))
                    extension = _rotate(q, [0.0, 0.0, 1.0])
                    candidate.pose.position.x = reference_front[0] - FRONT_OFFSET_M * extension[0]
                    candidate.pose.position.y = reference_front[1] - FRONT_OFFSET_M * extension[1]
                    (candidate.pose.orientation.x, candidate.pose.orientation.y,
                     candidate.pose.orientation.z, candidate.pose.orientation.w) = q
                if (self._geometry(candidate, tag)['sight_angle_rad'] >
                        float(self.get_parameter('visibility_tolerance_rad').value)):
                    continue
                request = GetPositionIK.Request()
                request.ik_request.group_name = 'uf850'
                request.ik_request.ik_link_name = self.tcp_link
                request.ik_request.pose_stamped = candidate
                request.ik_request.robot_state.is_diff = True
                request.ik_request.avoid_collisions = True
                request.ik_request.timeout.sec = 1
                diagnostic = self.ik_client.call_async(request)
                rclpy.spin_until_future_complete(self, diagnostic, timeout_sec=2.0)
                if diagnostic.done() and diagnostic.result() is not None:
                    self.get_logger().info(
                        f'{label}: endpoint IK yaw_offset={yaw_offset:.3f} rad '
                        f'code={diagnostic.result().error_code.val}'
                    )
                    if diagnostic.result().error_code.val == MoveItErrorCodes.SUCCESS:
                        ik_solution = diagnostic.result().solution.joint_state
                        target = candidate
                        break
        if ik_solution is None:
            raise RuntimeError(f'{label}: no collision-free endpoint IK solution')
        goal = MoveGroup.Goal()
        goal.request.group_name = 'uf850'
        goal.request.num_planning_attempts = 20
        goal.request.allowed_planning_time = 20.0
        goal.request.max_velocity_scaling_factor = 0.04
        goal.request.max_acceleration_scaling_factor = 0.04
        goal.request.start_state.is_diff = True
        joint_goal = Constraints(name=f'{label}_ik_goal')
        for name, position in zip(ik_solution.name, ik_solution.position):
            if name.startswith('joint'):
                constraint = JointConstraint()
                constraint.joint_name = name
                constraint.position = position
                constraint.tolerance_above = 0.005
                constraint.tolerance_below = 0.005
                constraint.weight = 1.0
                joint_goal.joint_constraints.append(constraint)
        if not joint_goal.joint_constraints:
            raise RuntimeError(f'{label}: IK returned no arm joints')
        goal.request.goal_constraints.append(joint_goal)
        goal.request.path_constraints = self._approach_constraints(tag, ray)
        goal.planning_options.plan_only = True
        goal.planning_options.replan = False
        goal.planning_options.planning_scene_diff.is_diff = True
        goal.planning_options.planning_scene_diff.robot_state.is_diff = True
        last_error = None
        planning_method = 'ompl_path_constraints'
        for attempt in range(8):
            try:
                self.planning_attempts[label] += 1
                response = self._plan_candidate(goal, label)
                points = len(response.planned_trajectory.joint_trajectory.points)
                if points < 2:
                    raise RuntimeError(f'{label}: incomplete/empty trajectory ({points} points)')
                planned_worst = self._validate_planned_path(response.planned_trajectory, tag, ray)
                break
            except RuntimeError as error:
                last_error = error
                self.get_logger().warning(f'{label}: candidate {attempt + 1}/8 rejected: {error}')
        else:
            planning_method = 'cartesian_waypoints'
            self.get_logger().warning(
                f'{label}: constrained OMPL candidates failed ({last_error}); '
                'trying constant-height/tilt Cartesian waypoints'
            )
            self.planning_attempts[label] += 1
            response = self._cartesian_candidate(label, target, tag, ray)
            points = len(response.planned_trajectory.joint_trajectory.points)
            if points < 2:
                raise RuntimeError(f'{label}: Cartesian path returned too few points')
            planned_worst = self._validate_planned_path(response.planned_trajectory, tag, ray)
        self.get_logger().info(f'{label}: planned {points} points; executing frozen target')

        execute = ExecuteTrajectory.Goal()
        execute.trajectory = response.planned_trajectory
        send = self.execute_client.send_goal_async(execute)
        rclpy.spin_until_future_complete(self, send, timeout_sec=10.0)
        handle = send.result() if send.done() else None
        if handle is None or not handle.accepted:
            raise RuntimeError(f'{label}: MoveIt rejected trajectory execution')
        self.approach_phase = label
        self.phase_observations = []
        samples = []
        future = handle.get_result_async()
        deadline = time.monotonic() + 90.0
        while rclpy.ok() and not future.done() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
            self._record_execution_sample(tag, samples)
        if not future.done():
            self.approach_phase = None
            raise RuntimeError(f'{label}: execution timed out')
        result = future.result().result
        if result.error_code.val != MoveItErrorCodes.SUCCESS:
            self.approach_phase = None
            raise RuntimeError(f'{label}: execution failed, MoveIt code {result.error_code.val}')
        settle_deadline = time.monotonic() + float(self.get_parameter('post_move_observation_sec').value)
        while rclpy.ok() and time.monotonic() < settle_deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.approach_phase = None
        self._record_execution_sample(tag, samples)
        actual = self._current_tcp_pose()
        final = self._geometry(actual, tag)
        if (abs(actual.pose.position.z - self.approach_start_pose.pose.position.z) >
                float(self.get_parameter('height_tolerance_m').value) or
                _tilt_delta(self._quaternion(actual.pose),
                            self._quaternion(self.approach_start_pose.pose)) >
                float(self.get_parameter('tilt_tolerance_rad').value)):
            raise RuntimeError(f'{label}: final height/tilt constraint was violated')
        self.phase_metrics[label] = {
            'planning_method': planning_method,
            'planning_attempts': self.planning_attempts[label],
            'planning_retries_before_execution': max(0, self.planning_attempts[label] - 1),
            'online_replans': 0,
            'planning_time_sec': response.planning_time,
            'trajectory_points': points,
            'worst_planned_path_errors': planned_worst,
            'target_pose': _pose_dict(target),
            'tag_snapshot': _pose_dict(tag),
            'observations_during_execution': len(self.phase_observations),
            'final_tcp_pose': _pose_dict(actual),
            'final_geometry': final,
            'max_sampled_height_error_m': max((x['height_error_m'] for x in samples), default=None),
            'max_sampled_tilt_error_rad': max((x['tilt_error_rad'] for x in samples), default=None),
            'max_sampled_sight_angle_rad': max((x['sight_angle_rad'] for x in samples), default=None),
            'max_sampled_ray_lateral_error_m': max((x['ray_lateral_error_m'] for x in samples), default=None),
        }
        self.get_logger().info(
            f'{label}: execution PASS; front plane distance={final["distance_m"]:.4f} m, '
            f'ray lateral={final["lateral_m"]:.4f} m, '
            f'sight angle={final["sight_angle_rad"]:.3f} rad; '
            f'valid updates={len(self.phase_observations)}'
        )
        return actual, list(self.phase_observations)

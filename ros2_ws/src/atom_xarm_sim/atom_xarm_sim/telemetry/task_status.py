"""Reusable TaskTelemetry capability; hosted by the task node."""
import json
import math
import time
from std_msgs.msg import String
from tf2_ros import (
    TransformException,
)
from atom_xarm_sim.geometry import (_tilt_delta, _pose_dict)

class TaskTelemetry:
    def _publish_gui_status(self):
        phases = {
            'initialization': (0.0, 'Initializing experiment'),
            'pre_observation_setup': (0.05, 'Waiting for TF, coarse target and controllers'),
            'pre_observation_move': (0.20, 'Moving to the pre-observation pose'),
            'pre_observation_capture': (0.35, 'Detecting Tag 1 and Tag 2'),
            'realignment': (0.60, 'Re-observing and correcting alignment at 0.40 m'),
            'alignment': (0.55, 'Aligning the front reference point at 0.40 m'),
            'perpendicular': (0.80, 'Approaching the selected Tag plane to 0.10 m'),
            'complete': (1.0, 'Visual approach completed; physical grasp is not implemented'),
        }
        progress, detail = phases.get(self.current_stage, (0, self.current_stage))
        state = 'RUNNING'
        if self.gui_final:
            state, detail = self.gui_final
        status = {
            'schema_version': 1, 'source': 'tube_approach_experiment',
            'request_id': self.gui_request_id, 'state': state,
            'executor': 'atom_task_executive',
            'task_recipe': str(self.get_parameter('task_recipe').value),
            'phase': self.current_stage, 'progress': progress,
            'detail': detail, 'camera_mode': self.camera_mode,
            'tag_id': self.task['tag_id'] if self.task else int(self.get_parameter('demo_tag_id').value),
            'requested_action': self.task['action'] if self.task else 'pick',
            'observed_tag_ids': sorted(self.observed),
            'observation_count': len(self.all_observations),
            'completed_segments': list(self.phase_metrics),
            'completed_capabilities': list(getattr(self, 'completed_capabilities', [])),
            'planning_attempts': dict(self.planning_attempts),
            'execution': 'executing' if self.approach_phase else 'planning_or_waiting',
            'metrics': dict(self.gui_execution_metrics),
            'grasp_completed': False, 'place_completed': False,
        }
        self.gui_status_publisher.publish(String(data=json.dumps(status)))
        # Persist actual status for run inspection; never synthesize task success.
        path = self.output_dir / 'runtime_status.json'
        temporary = self.output_dir / 'runtime_status.tmp'
        temporary.write_text(json.dumps(status, indent=2) + '\n', encoding='utf-8')
        temporary.replace(path)

    def _write_report(self):
        report = {
            'stage': 'pre_observation',
            'input_topic': self.input_topic,
            'robot_frame': self.robot_frame,
            'camera_mode': self.camera_mode,
            'input_command': _pose_dict(self.pre_observation_command),
            'target_pose_command': _pose_dict(self.target_pose_command),
            'target_pose_topic': self.target_pose_topic,
            'target_distance_m': math.hypot(
                self.target_pose_command.pose.position.x,
                self.target_pose_command.pose.position.y,
            ),
            'measured_pointing_ray_error_rad': self.measured_ray_error_rad,
            'theoretical_bearing_rad': self.theoretical_bearing,
            'observation_bearing_rad': self.observation_bearing,
            'expected_tag_poses_robot': {str(tag_id): _pose_dict(pose) for tag_id, pose in self.expected.items()},
            'observed_tag_poses_robot': {str(tag_id): _pose_dict(pose) for tag_id, pose in self.observed.items()},
            'depth_quality': self.depth_quality,
        }
        (self.output_dir / 'pre_observation_report.json').write_text(
            json.dumps(report, indent=2) + '\n', encoding='utf-8'
        )

    def _write_trial_summary(self, success, reason=None):
        summary = {
            'success': bool(success),
            'task_recipe': str(self.get_parameter('task_recipe').value),
            'capability_steps_completed': list(getattr(self, 'completed_capabilities', [])),
            'failure_stage': None if success else self.current_stage,
            'failure_reason': reason,
            'camera_mode': self.camera_mode,
            'random_seed': int(self.get_parameter('random_seed').value),
            'duration_sec': time.monotonic() - self.run_start_monotonic,
            'planning_attempts': self.planning_attempts,
            'planning_retries_before_execution': sum(
                max(0, attempts - 1) for attempts in self.planning_attempts.values()
            ),
            'online_replans': 0,
            'segments_completed': self.phase_metrics,
            'task': self.task,
            'expected_tag_poses_robot': {
                str(tag_id): _pose_dict(pose) for tag_id, pose in self.expected.items()
            },
            'observation_count': len(self.all_observations),
            'latest_capture_error': self.capture_error,
        }
        (self.output_dir / 'trial_summary.json').write_text(
            json.dumps(summary, indent=2) + '\n', encoding='utf-8'
        )

    def _record_execution_sample(self, tag, samples):
        try:
            current = self._current_tcp_pose()
            geometry = self._geometry(current, tag)
            initial_q = self._quaternion(self.approach_start_pose.pose)
            current_q = self._quaternion(current.pose)
            samples.append({
                'height_error_m': abs(current.pose.position.z - self.approach_start_pose.pose.position.z),
                'tilt_error_rad': _tilt_delta(initial_q, current_q),
                'sight_angle_rad': geometry['sight_angle_rad'],
                'front_plane_distance_m': geometry['distance_m'],
                'ray_lateral_error_m': geometry['lateral_m'],
            })
            self.gui_execution_metrics = dict(samples[-1])
        except (RuntimeError, TransformException):
            pass

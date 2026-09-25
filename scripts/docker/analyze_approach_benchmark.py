#!/usr/bin/env python3
"""Summarize independent paired approach trials and retain per-trial data."""

import argparse
import csv
import json
import math
from pathlib import Path
import statistics


def stats(values):
    return {
        'n': len(values),
        'mean': statistics.mean(values) if values else None,
        'sample_variance': statistics.variance(values) if len(values) > 1 else None,
    }


def classify(reason, runner):
    if runner.get('timed_out') or not reason:
        return 'infrastructure_or_timeout'
    lower = reason.lower()
    if any(word in lower for word in (
            'controllers are not active', 'controller_manager',
            'launch failed', 'gazebo crashed')):
        return 'infrastructure_or_timeout'
    if any(word in lower for word in (
            'final approach geometry outside tolerance',
            'updated normal ray misses alignment point',
            'planned path violates constraints',
            'final height/tilt constraint was violated',
            'pre-observation final error exceeds tolerance',
            'camera cannot face tag at fixed height')):
        return 'precision_or_geometric_constraint'
    if any(word in lower for word in (
            'observation stale', 'visual capture failed', 'no selected-tag observation',
            'was not detected', 'tag1/tag2 separation', 'no tf', 'capture')):
        return 'perception_or_tf'
    if any(word in lower for word in (
            'ik solution', 'planning failed', 'cartesian path incomplete',
            'no validated plan', 'trajectory returned too few', 'moveit rejected')):
        return 'ik_or_planning'
    if any(word in lower for word in ('execution failed', 'execution timed out')):
        return 'execution'
    return 'other'


def trial_data(path):
    runner = json.loads((path / 'runner.json').read_text())
    summary_path = path / 'trial_summary.json'
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    approach_path = path / 'approach_report.json'
    approach = json.loads(approach_path.read_text()) if approach_path.exists() else {}
    expected = summary.get('expected_tag_poses_robot', {})
    if not expected and (path / 'pre_observation_report.json').exists():
        expected = json.loads((path / 'pre_observation_report.json').read_text()).get('expected_tag_poses_robot', {})
    observations = {'alignment': [], 'perpendicular': []}
    obs_path = path / 'tag_observations.jsonl'
    if obs_path.exists():
        for line in obs_path.read_text().splitlines():
            if not line.strip():
                continue
            observation = json.loads(line)
            phase = observation.get('phase')
            theory = expected.get(str(observation.get('tag_id')))
            if phase not in observations or theory is None:
                continue
            measured = observation['pose']['position_m']
            theoretical = theory['position_m']
            error = math.sqrt(sum((measured[axis] - theoretical[axis]) ** 2
                                  for axis in ('x', 'y', 'z')))
            observations[phase].append(error)
    final = approach.get('segments', {}).get('perpendicular', {}).get('final_geometry', {})
    reported_success = bool(summary.get('success')) and runner['exit_code'] == 0
    true_lateral = None
    true_standoff = None
    true_xy_error = None
    if final and '1' in expected and '2' in expected:
        first = expected['1']['position_m']
        second = expected['2']['position_m']
        tangent = [second['x'] - first['x'], second['y'] - first['y']]
        length = math.hypot(*tangent)
        tangent = [value / length for value in tangent]
        normal = [-tangent[1], tangent[0]]
        front = final['front']
        delta = [front[0] - first['x'], front[1] - first['y']]
        true_lateral = abs(delta[0] * tangent[0] + delta[1] * tangent[1])
        true_standoff = abs(abs(delta[0] * normal[0] + delta[1] * normal[1]) - 0.10)
        true_xy_error = math.hypot(true_lateral, true_standoff)
    precision_pass = (true_lateral is not None and true_lateral <= 0.025 and
                      true_standoff <= 0.025)
    success = reported_success and precision_pass
    reason = summary.get('failure_reason')
    if reported_success and not precision_pass:
        reason = ('independent truth tolerance exceeded: lateral_m='
                  f'{true_lateral}, standoff_error_m={true_standoff}')
    if not success and not reason:
        reason = f'runner_exit_{runner["exit_code"]}; see docker.log/execution.log'
    return {
        'mode': runner['mode'], 'index': runner['index'], 'seed': runner['seed'],
        'success': success, 'reported_success': reported_success,
        'failure_stage': 'independent_truth_check' if reported_success and not precision_pass else summary.get('failure_stage'),
        'failure_reason': reason,
        'failure_class': None if success else (
            'precision_or_geometric_constraint' if reported_success else classify(reason, runner)),
        'duration_sec': summary.get('duration_sec', runner['host_duration_sec']),
        'host_duration_sec': runner['host_duration_sec'],
        'planning_attempts': sum(summary.get('planning_attempts', {}).values()),
        'planning_retries_before_execution': summary.get('planning_retries_before_execution', 0),
        'online_replans': summary.get('online_replans', 0),
        'alignment_planning_method': summary.get('segments_completed', {}).get('alignment', {}).get('planning_method'),
        'perpendicular_planning_method': summary.get('segments_completed', {}).get('perpendicular', {}).get('planning_method'),
        'final_lateral_error_m': true_lateral,
        'final_standoff_error_m': true_standoff,
        'final_xy_error_m': true_xy_error,
        'reported_final_lateral_error_m': final.get('lateral_m') if reported_success else None,
        'observation_errors_m': observations,
        'run_dir': str(path),
    }


def summarize(rows, mode):
    chosen = [row for row in rows if row['mode'] == mode]
    successful = [row for row in chosen if row['success']]
    completed = [row for row in chosen if row['reported_success']]
    failed = [row for row in chosen if not row['success']]
    categories = {}
    for row in failed:
        categories[row['failure_class']] = categories.get(row['failure_class'], 0) + 1
    phase_stats = {}
    for phase in ('alignment', 'perpendicular'):
        per_run = [row['observation_errors_m'][phase] for row in chosen
                   if row['observation_errors_m'][phase]]
        pooled = [value for run in per_run for value in run]
        phase_stats[phase] = {
            'valid_runs': len(per_run),
            'all_valid_points': stats(pooled),
            'per_run_mean_error': stats([statistics.mean(run) for run in per_run]),
        }
    return {
        'trials': len(chosen), 'successes': len(successful),
        'software_completed': len(completed),
        'success_rate': len(successful) / len(chosen) if chosen else None,
        'failure_classes': categories,
        'precision_failure_probability': categories.get('precision_or_geometric_constraint', 0) / len(chosen) if chosen else None,
        'final_lateral_error_m': stats([row['final_lateral_error_m'] for row in completed]),
        'final_standoff_error_m': stats([row['final_standoff_error_m'] for row in completed]),
        'final_xy_error_m': stats([row['final_xy_error_m'] for row in completed]),
        'reported_final_lateral_error_m': stats([
            row['reported_final_lateral_error_m'] for row in completed]),
        'observation_error_m': phase_stats,
        'duration_sec_all_trials': stats([row['duration_sec'] for row in chosen]),
        'duration_sec_successes': stats([row['duration_sec'] for row in successful]),
        'planning_retries_before_execution_all_trials': stats([
            row['planning_retries_before_execution'] for row in chosen]),
        'online_replans_all_trials': stats([row['online_replans'] for row in chosen]),
        'alignment_cartesian_fallback_completed': sum(
            row['alignment_planning_method'] == 'cartesian_waypoints' for row in completed),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    root = args.directory.resolve()
    rows = [trial_data(path) for path in sorted(root.iterdir())
            if path.is_dir() and (path / 'runner.json').exists()]
    report = {
        'protocol': {
            'modes': ['rgb', 'depth'], 'nominal_rack': True,
            'paired_seed_base': 2026092500,
            'target_tag_id': 1, 'target_action': 'pick',
            'pre_observation_distance_m': 0.35,
            'theoretical_pose_source': 'simulation fixture geometry transformed to link_base',
            'observation_error': '3D Euclidean norm from each observed Tag center to theoretical Tag center, metres',
            'variance': 'sample variance (n-1), m^2 or s^2 as appropriate',
            'final_lateral_error': 'front point tangent-direction offset from independent theoretical tag1/rack geometry',
            'success': 'software completed and independent true lateral/standoff errors both <= 0.025 m',
            'reported_final_lateral_error': 'control residual relative to frozen observed Tag/rack plane',
            'online_replanning': 'disabled by design; pre-execution candidate retries reported separately',
            'depth_usage': 'RGB-D depth quality only; Tag pose is RGB AprilTag PnP in both modes',
        },
        'rgb': summarize(rows, 'rgb'),
        'depth': summarize(rows, 'depth'),
    }
    (root / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    flattened = []
    for row in rows:
        flat = {key: value for key, value in row.items()
                if key not in ('observation_errors_m',)}
        for phase in ('alignment', 'perpendicular'):
            values = row['observation_errors_m'][phase]
            flat[f'{phase}_observation_count'] = len(values)
            flat[f'{phase}_observation_mean_error_m'] = statistics.mean(values) if values else None
            flat[f'{phase}_observation_sample_variance_m2'] = statistics.variance(values) if len(values) > 1 else None
        flattened.append(flat)
    if flattened:
        with (root / 'trials.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(flattened[0]))
            writer.writeheader()
            writer.writerows(flattened)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

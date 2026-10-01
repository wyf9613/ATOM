#!/usr/bin/env python3
"""Compare RGB and fused poses in the same frames against nominal simulation truth."""
import argparse
import json
import math
from pathlib import Path
import statistics


def analyze(run_dir):
    summary = json.loads((run_dir/'trial_summary.json').read_text())
    baseline, fused = [], []
    reasons = {}
    for line in (run_dir/'tag_observations.jsonl').read_text().splitlines():
        record = json.loads(line)
        quality = record.get('depth_quality', {}).get('fusion', {})
        if not quality.get('used'):
            reason = quality.get('reason', 'not_fused')
            reasons[reason] = reasons.get(reason, 0)+1
            continue
        truth = summary['expected_tag_poses_robot'][str(record['tag_id'])]['position_m']
        for key, values in [('rgb_pnp_pose', baseline), ('pose', fused)]:
            position = record[key]['position_m']
            values.append(math.sqrt(sum((position[axis]-truth[axis])**2 for axis in 'xyz')))
    return {
        'run_dir': str(run_dir), 'task_success': summary['success'],
        'paired_observations': len(fused), 'fallback_counts': reasons,
        'rgb_mean_position_error_m': statistics.mean(baseline) if baseline else None,
        'fused_mean_position_error_m': statistics.mean(fused) if fused else None,
        'rgb_rms_position_error_m': math.sqrt(statistics.mean(v*v for v in baseline)) if baseline else None,
        'fused_rms_position_error_m': math.sqrt(statistics.mean(v*v for v in fused)) if fused else None,
        'conditions': 'One nominal static simulation run; correlated frames, not independent trials or hardware accuracy.',
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('run_dir',type=Path)
    args=parser.parse_args()
    result=analyze(args.run_dir)
    (args.run_dir/'depth_fusion_comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()

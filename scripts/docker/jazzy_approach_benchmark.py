#!/usr/bin/env python3
"""Run paired, isolated headless RGB/RGB-D approach trials."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import time


REPO = Path(__file__).resolve().parents[2]


def run_trial(output, mode, index, seed, timeout_sec):
    trial_name = f'{mode}_{index:02d}'
    run_dir = output / trial_name
    run_dir.mkdir(parents=True, exist_ok=True)
    runner_path = run_dir / 'runner.json'
    if runner_path.exists():
        print(f'SKIP {trial_name}: runner.json exists', flush=True)
        return
    container = f'atom-approach-benchmark-{mode}-{index:02d}'
    in_container = '/workspace/' + str(run_dir.relative_to(REPO))
    command = [
        'docker', 'compose', '-f', 'docker-compose.jazzy.yaml', 'run', '--rm',
        '--name', container,
        '-e', 'ROS_DOMAIN_ID=77',
        '-e', f'ATOM_BENCH_RUN_DIR={in_container}',
        '-e', f'ATOM_BENCH_MODE={mode}',
        '-e', f'ATOM_BENCH_SEED={seed}',
        'atom-jazzy', 'bash', '/workspace/scripts/docker/jazzy_approach_trial.sh',
    ]
    print(f'START {trial_name} seed={seed}', flush=True)
    started = time.monotonic()
    timed_out = False
    with (run_dir / 'docker.log').open('w', encoding='utf-8') as stream:
        try:
            result = subprocess.run(command, cwd=REPO, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=timeout_sec,
                                    check=False)
            exit_code = result.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            exit_code = 124
            subprocess.run(['docker', 'rm', '-f', container], cwd=REPO,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=False)
    runner = {
        'mode': mode, 'index': index, 'seed': seed,
        'exit_code': exit_code, 'timed_out': timed_out,
        'host_duration_sec': time.monotonic() - started,
    }
    runner_path.write_text(json.dumps(runner, indent=2) + '\n', encoding='utf-8')
    summary = run_dir / 'trial_summary.json'
    stage = 'no_trial_summary'
    if summary.exists():
        data = json.loads(summary.read_text(encoding='utf-8'))
        stage = 'complete' if data['success'] else data['failure_stage']
    print(f'END {trial_name} exit={exit_code} stage={stage} '
          f'duration={runner["host_duration_sec"]:.1f}s', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('tmp/camera_experiment/benchmark_20260925_10x'))
    parser.add_argument('--runs', type=int, default=10)
    parser.add_argument('--seed-base', type=int, default=2026092500)
    parser.add_argument('--timeout-sec', type=int, default=240)
    parser.add_argument('--modes', nargs='+', choices=['rgb', 'depth'], default=['rgb', 'depth'])
    args = parser.parse_args()
    output = (REPO / args.output).resolve()
    if not output.is_relative_to(REPO):
        parser.error('output must be inside the repository Docker mount')
    output.mkdir(parents=True, exist_ok=True)
    for index in range(1, args.runs + 1):
        for mode in args.modes:
            run_trial(output, mode, index, args.seed_base + index, args.timeout_sec)


if __name__ == '__main__':
    main()

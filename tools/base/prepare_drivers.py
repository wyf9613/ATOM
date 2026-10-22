#!/usr/bin/env python3
"""Verify pinned vendor checkouts and idempotently apply the inherited odometry patch.

Fetch sources with vcs import before this tool; it does not select revisions,
overwrite user changes, configure CAN or start hardware.
"""
import argparse
from pathlib import Path
import subprocess


def prepare(root):
    pins = {'tracer_ros2': '832ea9a48fe725d47d766a099d358062ea2f0f31',
            'ugv_sdk': 'f2704eacdc90357078cd93ec60aae08bb4baab35'}
    for name, pin in pins.items():
        repo = root/name
        head = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        if head != pin:
            raise RuntimeError(f'{name}: expected {pin}, got {head}; refusing to change revisions')
    for repo_name, name in (('tracer_ros2', 'tracer_ros2.patch'),
                           ('tracer_ros2', 'tracer_watchdog.patch'),
                           ('ugv_sdk', 'ugv_cmake.patch')):
        cmd = ['git', '-C', str(root/repo_name), 'apply']
        patch = Path(__file__).resolve().parent/'patches'/name
        if subprocess.run(cmd+['--reverse', '--check', str(patch)], capture_output=True).returncode == 0:
            print(f'{name} already applied')
        else:
            subprocess.run(cmd+['--check', str(patch)], check=True)
            subprocess.run(cmd+[str(patch)], check=True)
            print(f'Applied {name}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_root', type=Path)
    prepare(parser.parse_args().source_root.resolve())

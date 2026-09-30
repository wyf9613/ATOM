"""Shared baseline geometry/configuration; not a ROS node."""
from pathlib import Path

JOINT_NAMES = [f'joint{index}' for index in range(1, 7)]

GOAL_TOLERANCE_RAD = 0.02

MONITOR_TOPIC = '/uf850_traj_controller/controller_state'

REPORT_DIRECTORY = Path('/jazzy_ws/log')

DEMO_OFFSETS_RAD = [0.70, -0.45, -0.55, 0.50, 0.45, -0.50]

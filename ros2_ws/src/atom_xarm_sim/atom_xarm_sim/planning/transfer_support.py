"""Shared baseline geometry/configuration; not a ROS node."""
import math
from pathlib import Path

REPORT_PATH = Path('/jazzy_ws/log/atom_uf850_transfer_summary.json')

def _finite_vector(node, name, length):
    values = [float(value) for value in node.get_parameter(name).value]
    if len(values) != length or not all(math.isfinite(value) for value in values):
        raise RuntimeError(f'{name} must contain {length} finite values')
    return values

def _normalise(values, name):
    norm = math.sqrt(sum(value * value for value in values))
    if norm < 1e-9:
        raise RuntimeError(f'{name} must not be a zero vector')
    return [value / norm for value in values]

def _quaternion_angle(first, second):
    a = _normalise([first.x, first.y, first.z, first.w], 'first quaternion')
    b = _normalise([second.x, second.y, second.z, second.w], 'second quaternion')
    dot = abs(sum(left * right for left, right in zip(a, b)))
    return 2.0 * math.acos(max(-1.0, min(1.0, dot)))

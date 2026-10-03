"""Versioned bounded telemetry parser; no ROS dependency."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Sample:
    sequence: int
    device_ms: int
    address: int
    valid: bool
    field_tesla: tuple


def parse_sample(line):
    if len(line) > 256:
        raise ValueError('oversized record')
    fields = line.strip().split(',')
    if len(fields) != 8 or fields[0] != 'V1':
        raise ValueError('unsupported record')
    seq, ms, address, valid = map(int, fields[1:5])
    values = tuple(float(value) * 1e-6 for value in fields[5:])
    if not (0 <= seq <= 0xFFFFFFFF and 0 <= ms <= 0xFFFFFFFF and
            1 <= address <= 126 and valid in (0, 1)):
        raise ValueError('invalid metadata')
    if not all(math.isfinite(value) for value in values):
        raise ValueError('nonfinite magnetic field')
    return Sample(seq, ms, address, bool(valid), values)

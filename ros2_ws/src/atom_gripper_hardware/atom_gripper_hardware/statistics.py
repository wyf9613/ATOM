"""Offline magnetic statistics; does not estimate force."""
import statistics


def summarize(samples):
    valid = [sample for sample in samples if sample.valid]
    result = {'records': len(samples), 'valid': len(valid),
              'invalid': len(samples) - len(valid), 'units': 'uT',
              'force_calibrated': False}
    if not valid:
        return result
    for index, axis in enumerate('xyz'):
        values = [sample.field_tesla[index] * 1e6 for sample in valid]
        result[axis] = {'mean': statistics.mean(values),
                        'sample_std': statistics.stdev(values) if len(values) > 1 else None,
                        'min': min(values), 'max': max(values)}
    gaps = resets = duplicates = 0
    periods = []
    for previous, current in zip(samples, samples[1:]):
        step = (current.sequence - previous.sequence) & 0xFFFFFFFF
        elapsed = (current.device_ms - previous.device_ms) & 0xFFFFFFFF
        if step == 0:
            duplicates += 1
        elif step > 0x7FFFFFFF or elapsed > 0x7FFFFFFF:
            resets += 1
        else:
            gaps += step - 1
            if elapsed > 0:
                periods.append(elapsed / step)
    result.update(sequence_gaps=gaps, resets_or_reordering=resets, duplicates=duplicates,
                  device_rate_hz=1000 / statistics.mean(periods) if periods else None)
    return result

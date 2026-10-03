"""Capture ESP32 sensor telemetry without ROS; supports offline replay."""
import argparse
import csv
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ros2_ws/src/atom_gripper_hardware'))
from atom_gripper_hardware.protocol import parse_sample
from atom_gripper_hardware.framing import LineFramer
from atom_gripper_hardware.statistics import summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--port', help='COM4 or /dev/serial/by-id/...')
    source.add_argument('--replay', type=Path, help='previous raw serial text')
    parser.add_argument('--seconds', type=float, default=30)
    parser.add_argument('--address', type=lambda x: int(x, 0), default=0x14)
    parser.add_argument('--label', default='stationary', help='test conditions label')
    parser.add_argument('--reset', action='store_true', help='pulse ESP32 EN through RTS before capture')
    parser.add_argument('--sync-timeout', type=float, default=5,
                        help='maximum wait for first matching protocol record')
    parser.add_argument('--output', type=Path, required=True, help='new output directory')
    args = parser.parse_args()
    if args.seconds <= 0 or args.sync_timeout <= 0 or not 1 <= args.address <= 126:
        parser.error('seconds must be positive and address must be 1..126')
    # Refuse overwriting evidence from an earlier run.
    args.output.mkdir(parents=True, exist_ok=False)
    samples = []
    malformed = wrong_address = 0
    framer = LineFramer()
    link = None
    started = time.monotonic()
    acquisition_started = None
    startup_lines = 0
    termination = 'completed'
    try:
        if args.port:
            from atom_gripper_hardware.serial_connection import open_sensor_port
            link = open_sensor_port(args.port, timeout=0.1, reset=args.reset)
        else:
            link = args.replay.open('rb')
        with (args.output / 'raw.bin').open('wb') as raw, \
                (args.output / 'startup.bin').open('wb') as startup, \
                (args.output / 'samples.csv').open('w', newline='', encoding='utf-8') as output:
            writer = csv.writer(output)
            writer.writerow(['host_elapsed_s', 'sequence', 'device_ms', 'address',
                             'valid', 'bx_uT', 'by_uT', 'bz_uT'])
            sync_started = time.monotonic()
            while args.replay or acquisition_started is None or time.monotonic() - acquisition_started < args.seconds:
                if args.port and acquisition_started is None and time.monotonic() - sync_started > args.sync_timeout:
                    termination = 'error: protocol synchronization timed out'
                    break
                chunk = link.read(1024)
                if not chunk:
                    if args.replay:
                        break
                    continue
                raw.write(chunk)
                for line in framer.feed(chunk):
                    if args.port and acquisition_started is None:
                        try:
                            candidate = parse_sample(line.decode('ascii'))
                            synchronized = candidate.address == args.address
                        except (ValueError, UnicodeError):
                            synchronized = False
                        if not synchronized:
                            startup.write(line + b'\n')
                            startup_lines += 1
                            continue
                        acquisition_started = time.monotonic()
                    elif acquisition_started is None:
                        acquisition_started = time.monotonic()
                    if not line or line.startswith(b'#'):
                        continue
                    try:
                        sample = parse_sample(line.decode('ascii'))
                    except (ValueError, UnicodeError):
                        malformed += 1
                        continue
                    if sample.address != args.address:
                        wrong_address += 1
                        continue
                    samples.append(sample)
                    writer.writerow([time.monotonic() - acquisition_started, sample.sequence,
                                     sample.device_ms, sample.address, int(sample.valid),
                                     *(v * 1e6 for v in sample.field_tesla)])
    except KeyboardInterrupt:
        termination = 'interrupted'
    except (OSError, ImportError) as exc:
        termination = 'error: ' + str(exc)
    finally:
        if link is not None:
            link.close()
    result = summarize(samples)
    result.update(label=args.label, source=args.port or str(args.replay),
                  expected_address=args.address, malformed=malformed,
                  wrong_address=wrong_address, oversized=framer.oversized,
                  trailing_partial_bytes=len(framer.buffer), termination=termination,
                  host_elapsed_s=time.monotonic() - started,
                  acquisition_elapsed_s=(time.monotonic() - acquisition_started) if acquisition_started else 0,
                  startup_lines=startup_lines,
                  gain='1x', resolution='16-bit', osr=3, filter=5,
                  configuration_note='Expected firmware settings, not read back from device')
    (args.output / 'summary.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    clean = not (malformed or wrong_address or framer.oversized)
    return 0 if result['valid'] and termination == 'completed' and clean else 1


if __name__ == '__main__':
    raise SystemExit(main())

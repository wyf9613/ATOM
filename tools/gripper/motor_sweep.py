"""Bounded, supervised multi-position motor test; stops on first fault."""
import argparse
import csv
import datetime
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ros2_ws/src/atom_gripper_hardware'))
from atom_gripper_hardware.serial_connection import open_sensor_port
from atom_gripper_hardware.framing import LineFramer

POSITIONS = [2200, 2300, 2400, 2100, 2500, 2000, 2600, 2300]


def fields(line):
    return dict(part.split('=', 1) for part in line.split() if '=' in part)


def next_step(position, goal):
    if not 1937 <= position <= 2668 or not 2000 <= goal <= 2600:
        raise RuntimeError('position/goal outside configured test limits')
    difference = goal - position
    # Do not chase 2-count residuals: observed servo can hold a small deadband error.
    return max(-100, min(100, difference)) if abs(difference) > 3 else 0


class Session:
    def __init__(self, link, log):
        self.link, self.log = link, log
        self.framer = LineFramer()
        self.heartbeat = 0
        self.pending = []

    def record(self, kind, text):
        self.log.write(json.dumps({'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                  'kind': kind, 'text': text}) + '\n')
        self.log.flush()

    def send(self, command):
        self.record('command', command)
        self.link.write((command + '\n').encode('ascii'))

    def pump(self, strict=True):
        if time.monotonic() - self.heartbeat >= 0.2:
            self.link.write(b'KEEPALIVE\n')
            self.heartbeat = time.monotonic()
        lines = []
        for raw in self.framer.feed(self.link.read(4096)):
            line = raw.decode('ascii', errors='replace')
            self.record('device', line)
            if line.startswith('#'):
                lines.append(line)
        if strict and any(line.startswith(('# ERR', '# FAULT', '# LIMIT_ERROR', '# FEEDBACK_ERROR')) for line in lines):
            raise RuntimeError(' | '.join(line for line in lines if line.startswith(('# ERR', '# FAULT', '# LIMIT_ERROR', '# FEEDBACK_ERROR'))))
        if strict and self.framer.oversized:
            raise RuntimeError('oversized serial record')
        return lines

    def wait(self, prefix, timeout=3, strict=True):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.pending.extend(self.pump(strict))
            for index, line in enumerate(self.pending):
                if line.startswith(prefix):
                    del self.pending[index]
                    return line
            time.sleep(0.01)
        raise RuntimeError('timeout waiting for ' + prefix)

    def request(self, command, prefix, timeout=3):
        # Process old records before issuing a new request; never hide faults.
        self.pump()
        self.pending.clear()
        self.send(command)
        return self.wait(prefix, timeout)

    def dwell(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.pump()
            time.sleep(0.01)

    def cleanup(self):
        # QUIT/STOP alone does not release torque. Empty gripper required.
        confirmed = False
        for command, prefix in [('STOP', '# STOP'), ('DISARM', '# DISARM_OK')]:
            try:
                self.pending.clear()
                self.send(command)
                self.wait(prefix, timeout=2, strict=False)
                if command == 'DISARM':
                    confirmed = True
            except Exception as exc:
                self.record('cleanup_error', str(exc))
        return confirmed


def run(session, cycles, dwell, rows, writer):
    session.request('STREAM OFF', '# STREAM OFF')
    session.request('DISARM', '# DISARM_OK')
    ping = fields(session.request('PING', '# PING'))
    if any(ping.get(key) != '1' for key in ('ok', 'mode_read_ok', 'feedback_ok')) or ping.get('mode') != '0':
        raise RuntimeError('servo ping/mode/feedback verification failed')
    initial = fields(session.wait('# MOTOR'))
    if initial.get('configured') != '1' or initial.get('fault') != '0':
        raise RuntimeError('configuration missing or fault latched; inspect manually, no auto RESET')
    position = int(initial['pos'])
    next_step(position, POSITIONS[0])
    session.request('ARM', '# ARM_OK')
    for cycle in range(1, cycles + 1):
        for waypoint in POSITIONS:
            segments = 0
            while next_step(position, waypoint):
                segments += 1
                if segments > 16:
                    raise RuntimeError('waypoint progress failed')
                delta = next_step(position, waypoint)
                before = position
                start = fields(session.request('JOG ' + str(delta), '# MOVE_START'))
                live_start, live_target = int(start['start']), int(start['target'])
                if (abs(live_start-before)>3 or abs(live_target-(before+delta))>3 or
                    abs((live_target-live_start)-delta)>3 or not 1937<=live_target<=2668):
                    raise RuntimeError('motion start inconsistent with bounded command')
                summary = fields(session.wait('# MOTION_SUMMARY', timeout=9))
                done = fields(session.wait('# MOVE_DONE', timeout=2))
                if summary.get('result') != 'done' or int(summary['start']) != live_start or int(summary['target']) != live_target:
                    raise RuntimeError('motion summary inconsistent with command')
                target, actual = int(done['target']), int(done['pos'])
                if target != live_target or abs(actual - target) > 3:
                    raise RuntimeError('position verification failed')
                row = {'cycle': cycle, 'waypoint': waypoint, 'start': live_start, 'target': target,
                       'actual': actual, 'error_counts': actual-target,
                       'direction': 'open' if delta > 0 else 'close',
                       'elapsed_ms': int(summary['elapsed_ms']), 'samples': int(summary['samples']),
                       'peak_abs_load': int(summary['peak_abs_load']), 'peak_signed_load': int(summary['peak_signed_load'])}
                rows.append(row)
                writer.writerow(row)
                print(f"cycle {cycle}/{cycles}: {before}->{actual}, peak={row['peak_abs_load']}, {row['elapsed_ms']}ms")
                session.dwell(dwell)
                state = fields(session.request('STATUS', '# MOTOR'))
                if state.get('armed') != '1' or state.get('moving') != '0' or state.get('fault') != '0':
                    raise RuntimeError('post-motion state not healthy/settled')
                position = int(state['pos'])
                if abs(position-target)>3:
                    raise RuntimeError('post-motion position drift exceeds 3 counts')
    return position


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default='COM4')
    parser.add_argument('--cycles', type=int, default=3)
    parser.add_argument('--dwell', type=float, default=0.5)
    parser.add_argument('--condition', default='unspecified', help='Operator label for lubrication/setup changes')
    parser.add_argument('--execute', action='store_true', help='Run physical motion; otherwise show plan only')
    args = parser.parse_args()
    if not 1 <= args.cycles <= 10 or not 0.2 <= args.dwell <= 5:
        parser.error('cycles must be 1..10; dwell must be 0.2..5 seconds')
    print('Waypoints:', POSITIONS, 'cycles:', args.cycles, 'max step:100 counts; existing firmware gates unchanged')
    if not args.execute:
        print('Plan only. Add --execute with an empty gripper, clear travel and external power cutoff available.')
        return 0
    output = ROOT / 'tmp/gripper_bringup' / ('sweep_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    output.mkdir(parents=True)
    print('Evidence:', output)
    rows, failure, released, session = [], None, False, None
    columns = ['cycle','waypoint','start','target','actual','error_counts','direction','elapsed_ms','samples','peak_abs_load','peak_signed_load']
    with (output/'transcript.jsonl').open('w',encoding='utf-8') as log, (output/'motions.csv').open('w',newline='',encoding='utf-8') as csvfile:
        writer=csv.DictWriter(csvfile,fieldnames=columns); writer.writeheader()
        try:
            link=open_sensor_port(args.port, timeout=0) # Never reset a motor system on connection.
            session=Session(link, log)
            session.record('condition', args.condition)
            run(session, args.cycles, args.dwell, rows, writer)
        except (Exception, KeyboardInterrupt) as exc:
            failure=str(exc) or 'operator interrupted'
            print('TEST STOPPED:', failure)
        finally:
            if session is not None:
                released=session.cleanup()
                session.link.close()
            if not released:
                print('Torque release UNCONFIRMED: disconnect external servo power.')
    summary={'passed': failure is None and released, 'failure':failure,'torque_release_confirmed':released,
             'condition':args.condition,
             'requested_cycles':args.cycles,'completed_segments':len(rows),'waypoints':POSITIONS,
             'sampled_peak_abs_load':max((r['peak_abs_load'] for r in rows),default=None),
             'notes':'Encoder-only verification. Sampled load is not calibrated force. No automatic fault reset.'}
    (output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print('PASS' if summary['passed'] else 'FAIL', 'completed segments:',len(rows))
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())

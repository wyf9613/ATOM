"""Explicit manual motor commands with host KEEPALIVE; no motion on connect."""
import argparse
import datetime
import json
import queue
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ros2_ws/src/atom_gripper_hardware'))
from atom_gripper_hardware.serial_connection import open_sensor_port
from atom_gripper_hardware.framing import LineFramer

COMMANDS = {'STATUS','PING','ARM','DISARM','RESET','STOP','ZERO','OPEN','CLOSE'}


def allowed(text):
    if text in {'STREAM ON', 'STREAM OFF'}:
        return True
    parts = text.split()
    if len(parts) == 1 and parts[0] in COMMANDS:
        return True
    if len(parts) == 2 and parts[0] == 'JOG':
        try:
            return 0 < abs(int(parts[1])) <= 100
        except ValueError:
            pass
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default='COM4')
    parser.add_argument('--log', type=Path, help='JSONL transcript path; default tmp/gripper_bringup/motor_<timestamp>.jsonl')
    args = parser.parse_args()
    log_path = args.log or ROOT / 'tmp/gripper_bringup' / ('motor_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.jsonl')
    log_path.parent.mkdir(parents=True, exist_ok=True)
    def record(kind, text):
        with log_path.open('a', encoding='utf-8') as file:
            file.write(json.dumps({'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'kind':kind, 'text':text})+'\n')
    record('session', 'port='+args.port)
    print('Transcript:', log_path)
    commands = queue.Queue()
    def read_input():
        for line in sys.stdin:
            commands.put(line.strip().upper())
        commands.put('QUIT')
    threading.Thread(target=read_input, daemon=True).start()
    print('No automatic motion. Commands:', ', '.join(sorted(COMMANDS)), 'JOG -100..100 (excluding 0), STREAM ON/OFF, QUIT')
    link = open_sensor_port(args.port, timeout=0)
    framer = LineFramer()
    last_heartbeat = 0
    try:
        while True:
            now = time.monotonic()
            if now - last_heartbeat >= 0.2:
                link.write(b'KEEPALIVE\n')
                last_heartbeat = now
            while not commands.empty():
                command = commands.get_nowait()
                if command == 'QUIT':
                    record('command', command)
                    return
                if allowed(command):
                    record('command', command)
                    link.write((command+'\n').encode('ascii'))
                else:
                    record('rejected', command)
                    print('Rejected command')
            for line in framer.feed(link.read(1024)):
                record('device', line.decode('ascii', errors='replace'))
                if line.startswith(b'#'):
                    print(line.decode('ascii', errors='replace'))
            time.sleep(0.01)
    finally:
        try:
            record('command', 'STOP (console exit; torque release not guaranteed)')
            link.write(b'STOP\n')
            link.flush()
        finally:
            link.close()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass

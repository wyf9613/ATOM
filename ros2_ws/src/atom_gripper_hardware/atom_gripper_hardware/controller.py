"""Single serial owner shared by ROS and local UI. No automatic motion/reset."""
from concurrent.futures import Future
import copy
import json
import math
from pathlib import Path
import queue
import threading
import time
from .framing import LineFramer
from .protocol import parse_sample
from .serial_connection import open_sensor_port
from .calibration import UncalibratedForceModel

COMMANDS = {'arm', 'disarm', 'reset', 'stop', 'open', 'close', 'move', 'force', 'zero'}
MOTION = {'arm', 'open', 'close', 'move', 'zero'}


def fields(line):
    return dict(word.split('=', 1) for word in line.split() if '=' in word)


def validate(command, parameters):
    if command not in COMMANDS or not isinstance(parameters, dict):
        raise ValueError('Unknown gripper command/parameters')
    if command == 'move':
        value = parameters.get('position')
        if type(value) is not int or not 2000 <= value <= 2600:
            raise ValueError('Position must be an integer within verified test range 2000..2600')
    if command == 'force':
        value = parameters.get('force_n')
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError('force_n must be finite and nonnegative')
        # //TODO G01: calibrate B→force, validate bounds/uncertainty, then implement local force control.
        raise PermissionError('Force control unavailable: fingertip force calibration is incomplete')


class GripperController:
    def __init__(self, port, enable_motion=False, log_path=None, opener=open_sensor_port):
        self.port, self.enable_motion, self.opener = port, enable_motion, opener
        self.lock = threading.RLock()
        self.jobs = queue.Queue()
        self.stopping = threading.Event()
        self.cancel_motion = threading.Event()
        self.link = None
        self.framer = LineFramer()
        self.pending = []
        self.active = None
        self.heartbeat = 0
        self.last_poll = 0
        self.motor_time = self.sensor_time = 0
        self.force_model = UncalibratedForceModel()
        self.state = {'connected': False, 'fault': None, 'armed': False, 'moving': False,
                      'position': None, 'load_raw': None, 'voltage_raw': None, 'temperature_raw': None,
                      'sensor_valid': False, 'magnetic_uT': None, 'sensor_address': None,
                      'configured': False, 'command_state': 'idle', 'last_result': None,
                      'force_calibrated': False, 'force_n': None, 'grasp_verified': False,
                      'position_range': [2000, 2600], 'open_position': 2600, 'close_position': 2000,
                      'source': 'esp32_hardware', 'motion_enabled': enable_motion}
        # //TODO G02: remeasure endpoint repeatability, jaw width/TCP and position→aperture mapping.
        # //TODO G03: verify 80 raw-load gate, voltage variant/units, stopping latency and hardware stop.
        self.log_path = Path(log_path) if log_path else None
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _log(self, kind, value):
        if self.log_path:
            with self.log_path.open('a', encoding='utf-8') as file:
                file.write(json.dumps({'host_monotonic_s': time.monotonic(), 'kind': kind, 'value': value})+'\n')

    def snapshot(self):
        with self.lock:
            state = copy.deepcopy(self.state)
            now = time.monotonic()
            state.update(motor_fresh=bool(self.motor_time and now-self.motor_time<1),
                         sensor_fresh=bool(self.sensor_time and now-self.sensor_time<0.5),
                         busy=bool(self.active and not self.active.done()))
            return state

    def blocks(self):
        state = self.snapshot()
        blocks = {'force': 'Force calibration pending'}
        for command in COMMANDS - {'force'}:
            if command in {'stop', 'disarm'}:
                if not state['connected']: blocks[command] = 'Serial device disconnected'
                continue
            if not self.enable_motion: blocks[command] = 'Hardware commands disabled'
            elif not state['connected'] or not state['motor_fresh']: blocks[command] = 'Feedback missing/stale'
            elif command != 'reset' and state['fault']: blocks[command] = 'Fault latched; inspect then reset'
            elif command in {'arm', 'open', 'close', 'move', 'zero'} and (not state['sensor_valid'] or not state['sensor_fresh']): blocks[command] = 'Fingertip sensor missing/invalid'
            elif command in {'open', 'close', 'move'} and not state['armed']: blocks[command] = 'Arm gripper first'
            elif command in {'arm', 'reset', 'zero'} and state['armed']: blocks[command] = 'Disarm gripper first'
            elif command in {'arm', 'reset'} and not state['configured']: blocks[command] = 'Firmware not configured'
            elif command == 'arm' and not 2000 <= (state['position'] or -1) <= 2600: blocks[command] = 'Place gripper inside tested range 2000..2600 while disarmed'
            if command not in blocks and state['busy']: blocks[command] = 'Gripper request active'
        return blocks

    def submit(self, command, parameters=None):
        parameters = parameters or {}
        validate(command, parameters)
        with self.lock:
            if command in {'stop', 'disarm'}:
                self.cancel_motion.set()
            elif command in self.blocks():
                raise PermissionError(self.blocks()[command])
            if not self.state['connected']:
                raise PermissionError('Serial device disconnected')
            future = Future()
            if command not in {'stop', 'disarm'}:
                self.active = future
                self.state['command_state'] = 'queued: '+command
            self.jobs.put((command, parameters, future))
            return future

    def cancel(self):
        self.cancel_motion.set()

    def _send(self, command):
        self._log('command', command)
        self.link.write((command+'\n').encode('ascii'))

    def _consume(self, line):
        self._log('device', line)
        with self.lock:
            if line.startswith('V1,'):
                sample = parse_sample(line)
                if sample.address != 20:
                    raise RuntimeError('Unexpected sensor address')
                self.sensor_time = time.monotonic()
                self.state.update(sensor_valid=sample.valid, sensor_address=sample.address,
                                  magnetic_uT=[value*1e6 for value in sample.field_tesla] if sample.valid else None)
                estimate=self.force_model.estimate(self.state['magnetic_uT'],self.state['position'])
                self.state.update(force_n=estimate.force_n,force_calibrated=estimate.calibrated,
                                  force_uncertainty_n=estimate.uncertainty_n,force_status=estimate.reason)
            elif line.startswith('# MOTOR '):
                values = fields(line)
                self.motor_time = time.monotonic()
                self.state.update(configured=values['configured']=='1', armed=values['armed']=='1', moving=values['moving']=='1',
                                  position=int(values['pos']), load_raw=int(values['load_raw']), voltage_raw=int(values['voltage_raw']),
                                  temperature_raw=int(values['temp_raw']))
                if values['fault']=='1': self.state['fault'] = self.state['fault'] or 'firmware_fault'
                # A STATUS record alone must not clear a latched host/device fault.
            elif line.startswith('# ARM_OK'): self.state['armed'] = True
            elif line.startswith('# DISARM_OK'): self.state.update(armed=False, moving=False)
            elif line.startswith('# RESET_OK'): self.state['fault'] = None
            elif line.startswith('# MOVE_START'): self.state['moving'] = True
            elif line.startswith('# MOTION '):
                values=fields(line); self.motor_time=time.monotonic()
                self.state.update(position=int(values['pos']),load_raw=int(values['load_raw']),
                                  voltage_raw=int(values['voltage_raw']),temperature_raw=int(values['temp_raw']))
            elif line.startswith('# MOVE_DONE'):
                self.state.update(moving=False, position=int(fields(line)['pos']))
            elif line.startswith('# ZERO_OK'): self.state['magnetic_baseline_ready'] = True
            elif line.startswith(('# FAULT', '# LIMIT_ERROR', '# FEEDBACK_ERROR')):
                self.state['fault'] = line
                if line.startswith('# FEEDBACK_ERROR'): self.motor_time = 0

    def _pump(self, strict=True):
        if time.monotonic()-self.heartbeat >= 0.2:
            self.link.write(b'KEEPALIVE\n')
            self.heartbeat = time.monotonic()
        lines = []
        for raw in self.framer.feed(self.link.read(4096)):
            line = raw.decode('ascii').strip()
            self._consume(line)
            if line.startswith('#'): lines.append(line)
        if self.framer.oversized:
            raise RuntimeError('Oversized device record')
        if strict and any(x.startswith(('# ERR', '# FAULT', '# LIMIT_ERROR', '# FEEDBACK_ERROR')) for x in lines):
            raise RuntimeError(' | '.join(x for x in lines if x.startswith(('# ERR', '# FAULT', '# LIMIT_ERROR', '# FEEDBACK_ERROR'))))
        return lines

    def _wait(self, prefix, timeout=3, strict=True, cancellable=False):
        deadline = time.monotonic()+timeout
        while time.monotonic()<deadline:
            if cancellable and (self.cancel_motion.is_set() or self.stopping.is_set()):
                raise RuntimeError('Gripper motion canceled')
            self.pending.extend(self._pump(strict))
            for index, line in enumerate(self.pending):
                if line.startswith(prefix):
                    del self.pending[index]
                    return line
            time.sleep(0.01)
        raise RuntimeError('Timeout waiting for '+prefix)

    def _request(self, command, prefix, **kwargs):
        self._pump(strict=False)
        self.pending.clear()
        self._send(command)
        return self._wait(prefix, **kwargs)

    def _execute(self, command, parameters):
        if command in {'open', 'close', 'move'}:
            goal = 2600 if command=='open' else 2000 if command=='close' else parameters['position']
            # //TODO G04: contact/force control must remain local and calibrated; position is not grasp success.
            for _ in range(16):
                if self.snapshot()['fault']: raise RuntimeError('Latched gripper fault')
                state = fields(self._request('STATUS', '# MOTOR', cancellable=True))
                if state['armed']!='1' or state['fault']!='0': raise RuntimeError('Gripper not armed/healthy')
                position = int(state['pos'])
                if not 2000<=position<=2600: raise RuntimeError('Position outside tested integration envelope')
                if abs(goal-position)<=3: return {'position_verified': True, 'position': position, 'grasp_verified': False}
                delta = max(-100, min(100, goal-position))
                start = fields(self._request('JOG '+str(delta), '# MOVE_START', cancellable=True))
                live_start, target = int(start['start']), int(start['target'])
                if abs(live_start-position)>3 or abs(target-(position+delta))>3 or not 1937<=target<=2668:
                    raise RuntimeError('Motion start inconsistent with request')
                summary = fields(self._wait('# MOTION_SUMMARY', timeout=9, cancellable=True))
                done = fields(self._wait('# MOVE_DONE', cancellable=True))
                if (summary['result']!='done' or int(summary['start'])!=live_start or int(summary['target'])!=target or
                    int(done['target'])!=target or abs(int(done['pos'])-target)>3): raise RuntimeError('Gripper completion mismatch')
                settle = time.monotonic()+0.5
                while time.monotonic()<settle:
                    if self.cancel_motion.is_set(): raise RuntimeError('Gripper motion canceled')
                    self._pump(); time.sleep(0.01)
            raise RuntimeError('Gripper did not converge to requested position')
        wire = {'arm': ('ARM','# ARM_OK'), 'disarm': ('DISARM','# DISARM_OK'), 'reset': ('RESET','# RESET_OK'),
                'stop': ('STOP','# STOP'), 'zero': ('ZERO','# ZERO_OK')}[command]
        self._request(*wire, strict=command not in {'stop','disarm','reset'})
        return {'position_verified': False, 'grasp_verified': False, 'message': wire[1]}

    def _worker(self):
        try:
            self.link = self.opener(self.port, timeout=0) # Never reset on connection.
            with self.lock: self.state['connected'] = True
            self._request('STREAM ON', '# STREAM ON', strict=False)
            while not self.stopping.is_set():
                try: command, parameters, future = self.jobs.get_nowait()
                except queue.Empty:
                    self._pump(strict=False)
                    if time.monotonic()-self.last_poll>0.4:
                        self.last_poll = time.monotonic()
                        try:
                            if self.snapshot()['armed']: self._request('STATUS','# MOTOR',strict=False,cancellable=True)
                            else:
                                ping=fields(self._request('PING','# PING',strict=False,cancellable=True))
                                self._wait('# MOTOR',strict=False,cancellable=True)
                                if ping.get('feedback_ok')!='1': self.motor_time=0
                        except RuntimeError:
                            if not self.cancel_motion.is_set(): raise
                    time.sleep(0.01)
                    continue
                try:
                    if command not in {'stop','disarm'}:
                        reason = self.blocks().get(command)
                        if reason and reason!='Gripper request active': raise PermissionError(reason)
                        if self.cancel_motion.is_set(): raise RuntimeError('Request canceled by stop/release')
                    with self.lock: self.state['command_state'] = 'executing: '+command
                    result = self._execute(command, parameters)
                    result.update(success=True, command=command)
                    with self.lock: self.state['last_result'] = result
                    future.set_result(result)
                except Exception as exc:
                    with self.lock:
                        self.state['fault'] = self.state['fault'] or str(exc)
                        self.state['last_result'] = {'success': False, 'command':command, 'message':str(exc)}
                    if command in MOTION:
                        try: self._request('STOP','# STOP',strict=False)
                        except Exception: pass
                    future.set_exception(exc)
                finally:
                    if command in {'stop','disarm'}: self.cancel_motion.clear()
                    with self.lock: self.state['command_state'] = 'idle'
        except Exception as exc:
            with self.lock: self.state['fault'] = str(exc)
        finally:
            if self.link is not None:
                # //TODO G05: shutdown hold/torque policy when carrying an object; no automatic release.
                if self.snapshot()['armed']:
                    try: self._request('STOP','# STOP',timeout=1,strict=False)
                    except Exception: pass
                self.link.close()
            with self.lock: self.state.update(connected=False, command_state='disconnected')
            while not self.jobs.empty():
                _,_,future=self.jobs.get_nowait()
                if not future.done(): future.set_exception(RuntimeError('Controller disconnected'))

    def close(self):
        self.cancel_motion.set()
        self.stopping.set()
        self.thread.join(timeout=5)

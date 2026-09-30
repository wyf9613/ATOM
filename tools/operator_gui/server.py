#!/usr/bin/env python3
"""ATOM operator gateway. Dependency-free demo; optional ROS 2 adapter."""
import argparse
import collections
import json
import math
import os
import secrets
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).resolve().parent / 'static'
COMMANDS = {'observe', 'pick', 'place', 'navigate', 'cancel', 'stop', 'reset_stop'}

class Gateway:
    def __init__(self, demo=True, enable_commands=False):
        self.demo = demo
        self.enable_commands = enable_commands
        self.lock = threading.RLock()
        self.stop_latched = False
        self.stop_generation = 0
        self.events = collections.deque(maxlen=100)
        self.streams = {}
        self.pending = set()
        self.adapter = None
        self.camera_image = None
        self.depth_image = None
        self.metadata = {"profile": "demo" if demo else "ros", "use_sim_time": False,
                         "ros_domain_id": os.environ.get("ROS_DOMAIN_ID", "0"), "interfaces": {}}
        self.token = secrets.token_urlsafe(32)
        self.event('info', 'Gateway started: ' + ('DEMO synthetic telemetry' if demo else 'ROS 2 read-only' if not enable_commands else 'ROS 2 commands enabled'))

    def event(self, level, message):
        with self.lock:
            self.events.appendleft({'time': time.time(), 'level': level, 'message': message})

    def update(self, name, value):
        with self.lock:
            self.streams[name] = {'received': time.monotonic(), 'value': value}

    def snapshot(self):
        with self.lock:
            now = time.monotonic()
            if self.demo:
                q = [round(math.sin(now / 7 + i) * .5, 3) for i in range(6)]
                values = {'arm': {'names': ['joint'+str(i+1) for i in range(6)], 'position': q, 'velocity': [0]*6},
                          'base': {'x': 1.4, 'y': .8, 'yaw': .3, 'speed': 0},
                          'battery': {'percent': 83, 'voltage': 24.2},
                          'diagnostics': [{'name': 'Demo data source', 'level': 0, 'message': 'Synthetic data; hardware unconnected'}],
                          'safety': {'hardware_estop': 'unknown', 'stop_confirmed': False},
                          'task': {'state': 'STOP_LATCHED' if self.stop_latched else 'IDLE', 'detail': 'Demo only'}}
                streams = {k: {'age_s': 0, 'fresh': True, 'value': v} for k,v in values.items()}
            else:
                streams = {k: {'age_s': round(now-v['received'], 2), 'fresh': now-v['received'] < 2,
                               'value': v['value']} for k,v in self.streams.items()}
            available = self.adapter.available() if self.adapter else {c: self.demo for c in COMMANDS}
            return {'schema_version': 1, 'mode': 'demo' if self.demo else 'ros', 'time': time.time(),
                    'commands_enabled': self.demo or self.enable_commands,
                    'stop_latched': self.stop_latched or streams.get('safety',{}).get('value',{}).get('software_stop_latched',False),
                    'metadata': self.metadata, 'command_blocks': self.command_blocks(streams, available),
                    'streams': streams, 'available': available, 'pending': sorted(self.pending), 'events': list(self.events)}

    def safety_permits_reset(self, value):
        if self.metadata['profile']=='gazebo':
            return value.get('source')=='gazebo' and value.get('hardware_estop')=='not_applicable'
        return value.get('hardware_estop')=='released'

    def command_blocks(self, streams, available):
        blocks = {}
        for command in COMMANDS:
            reason = None
            if not (self.demo or self.enable_commands):
                reason = 'Read-only mode'
            elif not available.get(command):
                reason = 'Interface not connected'
            elif command in self.pending:
                reason = 'Request pending'
            elif command in ('observe','pick','place','navigate') and self.pending.intersection({'observe','pick','place','navigate'}):
                reason = 'Another task is active'
            elif command not in ('stop', 'cancel', 'reset_stop'):
                if self.stop_latched or streams.get('safety',{}).get('value',{}).get('software_stop_latched',False):
                    reason = 'Software stop latched'
                elif not self.demo:
                    required = ['base','safety','diagnostics'] if command == 'navigate' else ['arm','safety','diagnostics']
                    if self.metadata['profile'] == 'gazebo':
                        required += ['controller', 'sim_clock']
                    if any(not streams.get(k, {}).get('fresh') for k in required):
                        reason = 'Required feedback missing or stale'
                    elif not self.safety_permits_reset(streams['safety']['value']) or not streams['safety']['value'].get('motion_allowed',False):
                        reason = 'Safety supervisor has not permitted motion'
                    elif any(d.get('level',2) >= 2 for d in streams['diagnostics']['value']):
                        reason = 'Diagnostic error'
                    elif self.metadata['profile'] == 'gazebo' and streams['controller']['value'].get('state') != 'active':
                        reason = 'Arm controller not active'
            if reason:
                blocks[command] = reason
        return blocks

    def command(self, data):
        command = data.get('command')
        if command not in COMMANDS:
            raise ValueError('Unknown command')
        parameters = data.get('parameters', {})
        if not isinstance(parameters, dict):
            raise ValueError('parameters must be an object')
        if command in ('pick', 'place'):
            if type(parameters.get('slot')) is not int or not 0 <= parameters['slot'] <= 3:
                raise ValueError('slot must be an integer from 0 to 3')
        if command == 'navigate':
            for key in ('x', 'y', 'yaw'):
                value = parameters.get(key)
                if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value):
                    raise ValueError('Navigation requires finite x/y/yaw in map frame')
                if abs(value) > (math.pi if key == 'yaw' else 100):
                    raise ValueError('Navigation target outside provisional limits')
        with self.lock:
            if not (self.demo or self.enable_commands):
                raise PermissionError('Commands disabled: gateway is read-only')
            if command == 'stop':
                self.stop_latched = True  # Inhibit even when downstream service is absent.
                self.stop_generation += 1
            elif command not in ('cancel', 'reset_stop'):
                if self.stop_latched:
                    raise PermissionError('Software stop is latched')
                if not self.demo:
                    required = ('base','safety','diagnostics') if command == 'navigate' else ('arm','safety','diagnostics')
                    snapshot = self.snapshot()['streams']
                    if any(not snapshot.get(k, {}).get('fresh') for k in required):
                        raise PermissionError('Required telemetry missing or stale')
                    safety = snapshot['safety']['value']
                    if not self.safety_permits_reset(safety) or not safety.get('motion_allowed', False):
                        raise PermissionError('Supervisor has not permitted motion')
                    if any(d.get('level', 2) >= 2 for d in snapshot['diagnostics']['value']):
                        raise PermissionError('Diagnostic error blocks motion')
            available = self.adapter.available() if self.adapter else {c:self.demo for c in COMMANDS}
            blocks = self.command_blocks(self.snapshot()['streams'], available)
            if command in blocks and command != 'stop':
                raise PermissionError(blocks[command])
            if command in self.pending:
                raise PermissionError('Command already pending')
            request_id = secrets.token_hex(8)
            if self.demo:
                if command == 'reset_stop':
                    self.stop_latched = False
                self.event('info', f'DEMO {command} {parameters}: no hardware command sent')
            else:
                if not self.adapter or not self.adapter.available().get(command):
                    self.event('error', f'{command}: downstream interface unavailable')
                    raise PermissionError('Downstream interface unavailable; stop latch remains active if requested')
                self.pending.add(command)
                self.adapter.send(command, parameters, request_id)
            return {'request_id': request_id, 'status': 'demo_completed' if self.demo else 'submitted', 'command': command}


def map_svg():
    """ROS PGM rows already display +Y upward. 0 occupied, 205 unknown, 254 free."""
    p = ROOT / 'map/real_lab_clean.pgm'
    if not p.exists():
        return '<svg xmlns="http://www.w3.org/2000/svg"><text y="25">Map unavailable</text></svg>'
    from io import BytesIO
    f = BytesIO(p.read_bytes())
    tokens = []
    while len(tokens) < 4:
        line = f.readline().split(b'#')[0]
        tokens.extend(line.split())
    if tokens[0] != b'P5' or tokens[3] != b'255':
        raise ValueError('Unsupported map PGM')
    w,h = map(int,tokens[1:3]); pixels = f.read(w*h)
    if len(pixels) != w*h:
        raise ValueError('Invalid map data')
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="#94a3b8"/><g shape-rendering="crispEdges">']
    for row in range(h):
        for col in range(w):
            value = pixels[row*w+col]
            if value != 205:
                color = '#152238' if value == 0 else '#eff6ff'
                parts.append(f'<rect x="{col}" y="{row}" width="1" height="1" fill="{color}"/>')
    return ''.join(parts) + '</g></svg>'


def handler_for(gateway):
    class Handler(BaseHTTPRequestHandler):
        def respond(self, code, body, content_type='application/json'):
            if not isinstance(body, bytes):
                body = json.dumps(body).encode()
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers(); self.wfile.write(body)

        def do_GET(self):
            path = self.path.split('?')[0]
            if path == '/api/v1/state':
                return self.respond(200, gateway.snapshot())
            if path == '/api/v1/session':
                return self.respond(200, {'token': gateway.token})
            if path == '/api/v1/depth':
                with gateway.lock:content=gateway.depth_image
                if content is None:return self.respond(404, {'error':'Depth stream not connected'})
                return self.respond(200,content,'image/png')
            if path == '/api/v1/camera':
                with gateway.lock:
                    content = gateway.camera_image
                if not content:
                    return self.respond(404, {'error': 'Camera not connected'})
                return self.respond(200, content, 'image/jpeg' if content.startswith(b'\xff\xd8') else 'image/png')
            if path == '/api/v1/map':
                return self.respond(200, map_svg().encode(), 'image/svg+xml')
            files = {'/': ('index.html','text/html; charset=utf-8'), '/app.js': ('app.js','text/javascript'), '/style.css': ('style.css','text/css')}
            if path in files:
                filename,kind = files[path]
                return self.respond(200, (STATIC/filename).read_bytes(), kind)
            return self.respond(404, {'error': 'Not found'})

        def do_POST(self):
            if self.path != '/api/v1/commands':
                return self.respond(404, {'error': 'Not found'})
            # Reject cross-origin browser commands. This token is CSRF protection, not user authentication.
            origin = self.headers.get('Origin')
            if origin and origin not in ('http://' + self.headers.get('Host',''), 'https://' + self.headers.get('Host','')):
                return self.respond(403, {'error': 'Cross-origin commands rejected'})
            if self.headers.get('X-ATOM-Token') != gateway.token:
                return self.respond(403, {'error': 'Session token required'})
            try:
                length = int(self.headers.get('Content-Length','0'))
                if not 0 < length <= 4096:
                    raise ValueError('Request size must be 1..4096 bytes')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('Expected object')
                self.respond(202, gateway.command(data))
            except PermissionError as exc:
                self.respond(409, {'error': str(exc)})
            except (ValueError, TypeError) as exc:
                self.respond(400, {'error': str(exc)})

        def log_message(self, *args):
            pass
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['demo','ros'], default='demo')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8088)
    parser.add_argument('--enable-commands', action='store_true')
    parser.add_argument('--ros-config', type=Path, default=Path(__file__).resolve().parent / 'ros_config.json')
    args = parser.parse_args()
    gateway = Gateway(args.mode == 'demo', args.enable_commands)
    if args.mode == 'ros':
        from ros_adapter import RosAdapter
        gateway.adapter = RosAdapter(gateway, json.loads(args.ros_config.read_text()))
    server = ThreadingHTTPServer((args.host,args.port),handler_for(gateway))
    def stop_server(signum, frame):
        threading.Thread(target=server.shutdown,daemon=True).start()
    for signum in (signal.SIGINT,signal.SIGTERM):
        signal.signal(signum,stop_server)
    print(f'ATOM GUI: http://{args.host}:{args.port} ({args.mode})', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if gateway.adapter:
            gateway.adapter.close()

if __name__ == '__main__':
    main()

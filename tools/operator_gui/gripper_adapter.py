"""Operator transport adapters; shared hardware controller owns serial/motion."""
from concurrent.futures import Future
import json
from pathlib import Path
import sys
import threading
import time
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'ros2_ws/src/atom_gripper_hardware'))
from atom_gripper_hardware.controller import GripperController, validate


class LocalGripper:
    def __init__(self, port, enabled=False):
        self.controller=GripperController(port,enabled,ROOT/'tmp/gripper_bringup/operator_hardware.jsonl')
        self.last_client=time.monotonic(); self.lease=False; self.closed=False
        self.thread=threading.Thread(target=self.watch,daemon=True); self.thread.start()

    def touch(self): self.last_client=time.monotonic()
    def snapshot(self):
        state=self.controller.snapshot(); state['blocks']=self.controller.blocks()
        state['available']=True; state['transport']='local_serial'
        return state
    def submit(self,command,parameters):
        future=self.controller.submit(command,parameters)
        def completed(value):
            if value.exception() is None:
                if command=='arm': self.lease=True
                if command in {'stop','disarm'}: self.lease=False
        future.add_done_callback(completed)
        return future
    def watch(self):
        while not self.closed:
            if self.lease and time.monotonic()-self.last_client>2:
                self.lease=False
                try: self.controller.submit('stop')
                except Exception: self.controller.cancel()
            time.sleep(0.1)
    def close(self):
        self.closed=True; self.controller.close(); self.thread.join(timeout=1)


class RosGripper:
    def __init__(self,node,name,status_topic,enabled):
        from rclpy.action import ActionClient
        from atom_operator_interfaces.action import ControlGripper
        from std_msgs.msg import String
        self.client=ActionClient(node,ControlGripper,name); self.type=ControlGripper
        self.enabled=enabled; self.state={}; self.received=0
        self.lease=False; self.last_client=time.monotonic()
        self.active=None; self.handle=None
        self.control_owner='ui-'+uuid.uuid4().hex
        self.lock=threading.RLock(); self.requests={}; self.handles={}
        self.heartbeat=node.create_publisher(String,'/atom/gripper/control_heartbeat',10)
        self.heartbeat_type=String
        node.create_subscription(String,status_topic,self.receive,10)
        node.create_timer(0.2,self.watch)
    def receive(self,message):
        try:
            value=json.loads(message.data)
            if isinstance(value,dict): self.state=value; self.received=time.monotonic()
        except (ValueError,TypeError): pass
    def touch(self): self.last_client=time.monotonic()
    def snapshot(self):
        state=dict(self.state)
        fresh=time.monotonic()-self.received<1
        state.update(available=bool(self.client.server_is_ready()),transport='ros_action',motion_enabled=self.enabled)
        if not fresh: state.update(motor_fresh=False,sensor_fresh=False)
        blocks=dict(state.get('blocks',{}))
        for command in ('arm','open','close','move','reset','zero'):
            if not self.enabled: blocks[command]='Operator commands disabled'
            elif not fresh: blocks[command]='Gripper feedback stale'
            elif state.get('control_owner') not in (None,self.control_owner): blocks[command]='Task or another session owns gripper control'
        blocks['force']='Force calibration pending'
        state['blocks']=blocks
        return state
    def submit(self,command,parameters):
        with self.lock:
            return self._submit(command,parameters)

    def _submit(self,command,parameters):
        validate(command,parameters)
        if not self.client.server_is_ready(): raise PermissionError('Gripper action unavailable')
        if command in self.snapshot()['blocks']: raise PermissionError(self.snapshot()['blocks'][command])
        if self.active and not self.active.done() and command not in {'stop','disarm'}: raise PermissionError('Gripper action active')
        future=Future(); goal=self.type.Goal(command=command,control_owner=self.control_owner,position=parameters.get('position',0),force_n=float(parameters.get('force_n',0)))
        self.requests[future]=time.monotonic()+75
        if command not in {'stop','disarm'}: self.active=future
        def accepted(response):
            try:
                handle=response.result()
                if not handle.accepted: raise RuntimeError('Gripper action rejected')
                if future.done():
                    handle.cancel_goal_async()
                    return
                with self.lock: self.handles[future]=handle
                if command not in {'stop','disarm'}: self.handle=handle
                if command=='arm': self.lease=True
                def completed(value):
                    try:
                        result=value.result().result
                        if not result.success: raise RuntimeError(result.message)
                        if future.done(): return
                        if command=='arm': self.lease=True
                        if command in {'stop','disarm'}: self.lease=False
                        future.set_result({'success':result.success,'message':result.message,'position':result.final_position,
                                           'position_verified':result.position_verified,'grasp_verified':result.grasp_verified})
                    except Exception as exc:
                        if not future.done(): future.set_exception(exc)
                handle.get_result_async().add_done_callback(completed)
            except Exception as exc:
                if not future.done(): future.set_exception(exc)
        self.client.send_goal_async(goal).add_done_callback(accepted)
        return future
    def watch(self):
        if self.lease and time.monotonic()-self.last_client<=2:
            self.heartbeat.publish(self.heartbeat_type(data=self.control_owner))
        with self.lock:
            expired=[]
            for future,deadline in list(self.requests.items()):
                if not future.done() and time.monotonic()>deadline:
                    expired.append((future,self.handles.get(future)))
                if future.done() or time.monotonic()>deadline:
                    self.requests.pop(future,None); self.handles.pop(future,None)
        # Future callbacks enter the gateway; do not invoke them under our lock.
        for future,handle in expired:
            if handle: handle.cancel_goal_async()
            if not future.done(): future.set_exception(RuntimeError('Gripper result timeout; outcome unknown'))
        if self.lease and time.monotonic()-self.last_client>2:
            self.lease=False
            try: self.submit('stop',{})
            except Exception:
                if self.handle: self.handle.cancel_goal_async()
    def close(self):
        if self.lease:
            try: self.submit('stop',{}).result(timeout=2)
            except Exception: pass

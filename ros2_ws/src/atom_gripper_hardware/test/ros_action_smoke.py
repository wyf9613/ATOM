"""Run after colcon/source in Jazzy; actual ROS actions with a fake serial device.

Never opens a hardware port. Checks generated Action, bridge, session ownership,
shared controller and ROS operator adapter together.
"""
from pathlib import Path
import sys
import threading
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tools/operator_gui'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_controller import FakeDevice
from atom_gripper_hardware.controller import GripperController
from atom_gripper_hardware.hardware_bridge import HardwareBridge
from atom_operator_interfaces.action import ControlGripper
from gripper_adapter import RosGripper
import rclpy
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from action_msgs.msg import GoalStatus
from sensor_msgs.msg import MagneticField
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus


def await_result(future, timeout=8):
    deadline=time.monotonic()+timeout
    while not future.done() and time.monotonic()<deadline: time.sleep(.02)
    assert future.done(),'Timed out awaiting ROS result'
    return future.result()


def main():
    rclpy.init()
    fake=FakeDevice()
    factory=lambda *a,**kw:GripperController('fake',True,opener=lambda *a,**kw:fake)
    with patch('atom_gripper_hardware.hardware_bridge.GripperController',factory): bridge=HardwareBridge()
    ui=Node('gripper_ui_smoke'); adapter=RosGripper(ui,'/atom/gripper/control','/atom/gripper/status',True)
    fields=[]; diagnostics=[]
    ui.create_subscription(MagneticField,'/atom/gripper/magnetic_field',fields.append,10)
    ui.create_subscription(DiagnosticArray,'/diagnostics',diagnostics.append,10)
    ui.create_timer(.2,adapter.touch) # Fake browser polling while ROS callbacks run.
    other=ActionClient(ui,ControlGripper,'/atom/gripper/control')
    executor=MultiThreadedExecutor(num_threads=4); executor.add_node(bridge); executor.add_node(ui)
    thread=threading.Thread(target=executor.spin,daemon=True); thread.start()
    try:
        assert adapter.client.wait_for_server(timeout_sec=5)
        deadline=time.monotonic()+5
        while not adapter.snapshot().get('sensor_fresh') and time.monotonic()<deadline: time.sleep(.05)
        assert adapter.snapshot()['sensor_valid']
        deadline=time.monotonic()+2
        while (not fields or not diagnostics or diagnostics[-1].status[0].level!=DiagnosticStatus.OK) and time.monotonic()<deadline:
            time.sleep(.02)
        assert fields and abs(fields[-1].magnetic_field.x-52e-6)<1e-12
        assert fields[-1].header.frame_id=='gripper_magnetic_sensor'
        assert diagnostics and diagnostics[-1].status[0].level==DiagnosticStatus.OK
        assert 'ARM' not in fake.commands
        bridge.controller.enable_motion=False
        rejected=await_result(other.send_goal_async(ControlGripper.Goal(command='arm',control_owner='readonly')))
        assert not rejected.accepted and 'ARM' not in fake.commands
        bridge.controller.enable_motion=True
        adapter.touch(); assert await_result(adapter.submit('arm',{}))['success']
        deadline=time.monotonic()+2
        while 'open' in adapter.snapshot()['blocks'] and time.monotonic()<deadline: time.sleep(.02)
        # A second session cannot move the first session's armed gripper.
        rejected=await_result(other.send_goal_async(ControlGripper.Goal(command='open',control_owner='other')))
        assert not rejected.accepted
        adapter.touch(); result=await_result(adapter.submit('open',{}))
        assert result['position_verified'] and not result['grasp_verified']
        assert result['position']==2600
        try: adapter.submit('force',{'force_n':1})
        except PermissionError: pass
        else: raise AssertionError('Uncalibrated force was accepted')
        # Cancel a running Action through ROS; keep torque without a fault.
        fake.delay_motion=True
        before=len(fake.commands)
        moving=await_result(other.send_goal_async(ControlGripper.Goal(
            command='close',control_owner=adapter.control_owner)))
        assert moving.accepted
        deadline=time.monotonic()+2
        while not any(c.startswith('MOVE ') for c in fake.commands[before:]) and time.monotonic()<deadline:
            time.sleep(.02)
        assert any(c.startswith('MOVE ') for c in fake.commands[before:])
        canceled=await_result(moving.cancel_goal_async())
        assert canceled.goals_canceling
        outcome=await_result(moving.get_result_async())
        assert outcome.status==GoalStatus.STATUS_CANCELED and not outcome.result.success
        assert 'STOP' in fake.commands[before:] and fake.armed
        assert bridge.controller.snapshot()['fault'] is None
        # The same armed session can resume immediately after normal cancel.
        fake.delay_motion=False
        adapter.touch(); assert await_result(adapter.submit('close',{}))['position_verified']
        adapter.touch(); assert await_result(adapter.submit('stop',{}))['success']
        adapter.touch(); assert await_result(adapter.submit('open',{}))['position_verified']
        fake.delay_motion=False
        adapter.touch(); assert await_result(adapter.submit('disarm',{}))['success']
        assert not fake.armed
        deadline=time.monotonic()+2
        while 'reset' in adapter.snapshot()['blocks'] and time.monotonic()<deadline: time.sleep(.02)
        adapter.touch(); assert await_result(adapter.submit('reset',{}))['success']
        # A task/client disappearing after ARM must be held by the bridge.
        deadline=time.monotonic()+2
        while 'arm' in adapter.snapshot()['blocks'] and time.monotonic()<deadline: time.sleep(.02)
        adapter.touch(); await_result(adapter.submit('arm',{}))
        adapter.lease=False
        deadline=time.monotonic()+4
        before=len(fake.commands)
        while 'STOP' not in fake.commands[before:] and time.monotonic()<deadline: time.sleep(.02)
        assert 'STOP' in fake.commands[before:]
        assert fake.armed,'Caller loss must hold, not release torque'
        print('PASS: generated ROS Action, telemetry, position, ownership, force rejection, cancellation, manual recovery and caller-loss hold (fake serial only)')
    finally:
        adapter.close(); executor.shutdown(); thread.join(timeout=2)
        other.destroy(); ui.destroy_node(); bridge.destroy_node(); rclpy.try_shutdown()


if __name__=='__main__': main()

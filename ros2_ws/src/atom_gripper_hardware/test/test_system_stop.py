"""Real ROS node plus the existing simulated serial device; no physical port."""
import time
import pytest

pytest.importorskip('rclpy')
import rclpy
from std_msgs.msg import Bool
from rclpy.action import GoalResponse
from atom_operator_interfaces.action import ControlGripper
from atom_gripper_hardware import hardware_bridge as bridge
from atom_gripper_hardware.controller import GripperController
from test_controller import FakeDevice


def test_supervisor_blocks_startup_stops_armed_device_and_expires(monkeypatch):
    device=FakeDevice()
    monkeypatch.setattr(bridge, 'GripperController', lambda port, enabled, log:
                        GripperController('fake', True, opener=lambda *a, **kw:device))
    rclpy.init(args=['--ros-args','-p','require_system_stop_state:=true'])
    node=bridge.HardwareBridge()
    try:
        deadline=time.monotonic()+3
        while not node.controller.snapshot()['sensor_fresh'] or not node.controller.snapshot()['motor_fresh']:
            assert time.monotonic()<deadline
            time.sleep(.02)
        req=ControlGripper.Goal(command='arm',control_owner='test')
        assert node.goal(req)==GoalResponse.REJECT
        node.system_stop(Bool(data=True))
        node.system_stop(Bool(data=False))
        assert node.goal(req)==GoalResponse.ACCEPT
        # Exercise the already-owned controller using the same fake serial boundary.
        node.controller.submit('arm').result(timeout=3)
        node.system_stop(Bool(data=True))
        deadline=time.monotonic()+2
        while 'STOP' not in device.commands:
            assert time.monotonic()<deadline
            time.sleep(.02)
        assert node.goal(ControlGripper.Goal(command='move',position=2400,control_owner='test'))==GoalResponse.REJECT
        node.system_stop(Bool(data=False))
        node.system_state_seen=time.monotonic()-1.
        assert node.system_motion_blocked()
        assert node.goal(req)==GoalResponse.REJECT
        assert node.goal(ControlGripper.Goal(command='stop',control_owner='operator'))==GoalResponse.ACCEPT
    finally:
        node.controller.close()
        node.destroy_node()
        rclpy.shutdown()

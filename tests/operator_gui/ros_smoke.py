"""Run with Jazzy's system Python; fake ROS publishers/services, no hardware."""
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/operator_gui'))
from server import Gateway
from ros_adapter import RosAdapter
from rclpy.node import Node
from sensor_msgs.msg import JointState
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus
from std_msgs.msg import String
from std_srvs.srv import Trigger

gateway=Gateway(False,True);adapter=RosAdapter(gateway);gateway.adapter=adapter
# Adapter spin processes the fake source node through its executor too.
from rclpy import get_global_executor
node=Node('atom_gui_test_source');get_global_executor().add_node(node)
joints=node.create_publisher(JointState,'/joint_states',10)
safety=node.create_publisher(String,'/atom/safety/status',10)
diagnostics=node.create_publisher(DiagnosticArray,'/diagnostics',10)
def stop(request,response):
    response.success=True;response.message='fake supervisor stopped';return response
service=node.create_service(Trigger,'/atom/safety/stop',stop)
try:
    deadline=time.monotonic()+6
    while time.monotonic()<deadline:
        joints.publish(JointState(name=['joint1'],position=[.25]))
        safety.publish(String(data='{"schema_version":1,"hardware_estop":"released","motion_allowed":true,"stop_confirmed":true}'))
        diagnostics.publish(DiagnosticArray(status=[DiagnosticStatus(level=b'\x00',name='test',message='OK')]))
        if gateway.snapshot()['streams'].get('arm') and adapter.available()['stop']:break
        time.sleep(.1)
    assert gateway.snapshot()['streams']['arm']['value']['position']==[.25]
    gateway.command({'command':'stop'})
    deadline=time.monotonic()+3
    while gateway.pending and time.monotonic()<deadline:time.sleep(.05)
    assert gateway.snapshot()['streams']['diagnostics']['value'][0]['level']==0
    assert not gateway.pending
    assert gateway.stop_latched
    assert any('fake supervisor stopped' in e['message'] for e in gateway.events)
    assert not adapter.available()['pick'] and not adapter.available()['navigate']
    print('PASS: ROS joint telemetry, Trigger stop acknowledgment, latch and unavailable task adapters')
finally:
    get_global_executor().remove_node(node);node.destroy_node();adapter.close()

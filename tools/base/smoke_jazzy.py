#!/usr/bin/env python3
"""Bounded end-to-end gate/mission/TF test against the ideal base fixture only."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import rclpy
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool, String
from std_srvs.srv import SetBool, Trigger
from tf2_ros import Buffer, TransformListener


def main(output):
    output.parent.mkdir(parents=True,exist_ok=True)
    log=output.with_suffix('.log').open('w')
    proc=subprocess.Popen(['ros2','launch','atom_base','mobile.launch.py','backend:=fake','web:=true','port:=18080'],
                          stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    rclpy.init()
    node=rclpy.create_node('mobile_integration_check')
    state={'velocities':[],'events':[]}
    from rclpy.qos import QoSProfile,DurabilityPolicy
    latched=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL)
    node.create_subscription(Twist,'/atom/base/cmd_vel',lambda m:state['velocities'].append((time.monotonic(),m.linear.x,m.angular.z)),10)
    node.create_subscription(String,'/mission_event',lambda m:state['events'].append(json.loads(m.data)),latched)
    nav=node.create_publisher(Twist,'/atom/base/nav_cmd_vel',10)
    fine=node.create_publisher(Twist,'/atom/base/fine_cmd_vel',10)
    stop=node.create_publisher(Bool,'/atom/safety/stop',10)
    mission=node.create_publisher(String,'/mission_cmd',10)
    buffer=Buffer();listener=TransformListener(buffer,node)

    def spin(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            rclpy.spin_once(node,timeout_sec=.03)
            assert proc.poll() is None, 'launch process exited; see runtime.log'

    def call(service,typ,request):
        client=node.create_client(typ,service)
        assert client.wait_for_service(timeout_sec=20),service
        future=client.call_async(request)
        rclpy.spin_until_future_complete(node,future,timeout_sec=5)
        response=future.result()
        assert response is not None and response.success,(service,response)
        node.destroy_client(client)

    def current():
        return buffer.lookup_transform('map','base_link',rclpy.time.Time()).transform.translation.x

    results={}
    try:
        call('/atom/safety/reset',Trigger,Trigger.Request())
        spin(1.)
        assert all(v==0 and w==0 for _,v,w in state['velocities'])
        results['startup_and_reset_disabled']=True
        call('/atom/base/enable',SetBool,SetBool.Request(data=True))
        deadline=time.monotonic()+10
        while mission.get_subscription_count()==0 or not state['events']:
            assert time.monotonic()<deadline, 'mission manager discovery timed out'
            spin(.1)
        # The mission uses the normal JSON -> action -> cmd -> gate -> odometry chain.
        mission.publish(String(data=json.dumps({'cmd':'goto','x':.06,'y':0.,'yaw':0.,'label':'check'})))
        end=time.monotonic()+15
        while time.monotonic()<end and not any(e.get('state')=='arrived' for e in state['events']): spin(.1)
        assert any(e.get('state')=='arrived' for e in state['events']),state['events']
        assert .045<current()<.075,current()
        results['json_mission_action_and_gated_motion']=True
        tf=buffer.lookup_transform('base_top','link_base',rclpy.time.Time())
        assert abs(tf.transform.translation.z-.805)<1e-9
        assert abs(tf.transform.translation.x)<1e-9 and abs(tf.transform.translation.y)<1e-9
        results['runtime_mount_805mm']=True
        call('/atom/base/select_fine_adjust',SetBool,SetBool.Request(data=True))
        call('/atom/base/enable',SetBool,SetBool.Request(data=True))
        spin(.4)
        cmd=Twist();cmd.linear.x=.1
        before=current()
        for _ in range(8): nav.publish(cmd);spin(.05)
        assert abs(current()-before)<.005
        results['inactive_nav_publisher_excluded']=True
        for _ in range(8): fine.publish(cmd);spin(.05)
        assert current()>before+.02
        results['fine_owner_can_move_fixture']=True
        spin(.7)
        assert all(v==0 and w==0 for t,v,w in state['velocities'] if t>time.monotonic()-.2)
        results['command_expiry_zeroes_output']=True
        stop.publish(Bool(data=True));spin(.2)
        before=current()
        for _ in range(8): fine.publish(cmd);nav.publish(cmd);spin(.05)
        assert abs(current()-before)<.005
        results['stop_blocks_both_publishers']=True
        call('/atom/safety/reset',Trigger,Trigger.Request());spin(.3)
        assert abs(current()-before)<.005
        results['reset_does_not_resume']=True
        # Check optional inherited task UI is actually serving the installed map.
        from urllib.request import urlopen
        with urlopen('http://127.0.0.1:18080/status',timeout=3) as response:
            assert json.load(response)['robot']['ok']
        results['web_status_and_installed_map']=True
        output.write_text(json.dumps({'scope':'ideal kinematic interface fixture; no hardware or physics',
                                     'checks':results,'events':state['events']},indent=2)+'\n')
        print(json.dumps(results,indent=2))
    finally:
        node.destroy_node();rclpy.shutdown()
        proc.send_signal(signal.SIGINT)
        try: proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=5)
        log.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args().output)

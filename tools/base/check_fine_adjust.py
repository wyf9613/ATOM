#!/usr/bin/env python3
"""Exercise the production fine-adjust action with synthetic goal corrections.

Uses ideal base odometry and scan, never a physical camera/base/arm/gripper.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import rclpy
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped, Twist
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import Bool
from std_srvs.srv import SetBool, Trigger


def main(output):
    log=output.with_suffix('.log').open('w')
    proc=subprocess.Popen(['ros2','launch','atom_base','mobile.launch.py','backend:=fake','fine_adjust:=true'],
                          stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    rclpy.init();node=rclpy.create_node('fine_adjust_integration_check')
    correction=node.create_publisher(PoseStamped,'/fine_adjust/goal_correction',10)
    stop=node.create_publisher(Bool,'/atom/safety/stop',10)
    commands=[]
    node.create_subscription(Twist,'/atom/base/cmd_vel',lambda m:commands.append((time.monotonic(),m.linear.x,m.angular.z)),10)
    target=[.06]
    def pose():
        p=PoseStamped();p.header.frame_id='odom';p.header.stamp=node.get_clock().now().to_msg()
        p.pose.position.x=target[0];p.pose.orientation.w=1.
        return p
    timer=node.create_timer(.05,lambda:correction.publish(pose()))
    client=ActionClient(node,NavigateToPose,'/fine_adjust')
    def spin(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            rclpy.spin_once(node,timeout_sec=.02)
            assert proc.poll() is None
    def call(name,typ,request):
        c=node.create_client(typ,name);assert c.wait_for_service(timeout_sec=15)
        f=c.call_async(request);rclpy.spin_until_future_complete(node,f,timeout_sec=3)
        assert f.result() is not None and f.result().success
        node.destroy_client(c)
    def goal():
        req=NavigateToPose.Goal();req.pose=pose()
        f=client.send_goal_async(req);rclpy.spin_until_future_complete(node,f,timeout_sec=3)
        assert f.result() is not None
        return f.result()
    def result(handle,timeout=10):
        f=handle.get_result_async();rclpy.spin_until_future_complete(node,f,timeout_sec=timeout)
        assert f.result() is not None
        return f.result().status
    results={}
    try:
        assert client.wait_for_server(timeout_sec=20)
        assert not goal().accepted
        results['stopped_goal_rejected']=True
        call('/atom/safety/reset',Trigger,Trigger.Request())
        call('/atom/base/select_fine_adjust',SetBool,SetBool.Request(data=True))
        call('/atom/base/enable',SetBool,SetBool.Request(data=True))
        spin(1.)
        handle=goal();assert handle.accepted
        assert not goal().accepted
        assert result(handle)==4
        results['exclusive_action_and_closed_loop_success']=True
        target[0]=.5;spin(.2)
        handle=goal();assert handle.accepted
        spin(.3);stop.publish(Bool(data=True))
        assert result(handle)==6
        spin(.3)
        assert all(v==0 and w==0 for t,v,w in commands if t>time.monotonic()-.15)
        results['software_stop_aborts_action_and_zeroes_base']=True
        call('/atom/safety/reset',Trigger,Trigger.Request())
        call('/atom/base/select_fine_adjust',SetBool,SetBool.Request(data=True))
        call('/atom/base/enable',SetBool,SetBool.Request(data=True))
        spin(.3)
        handle=goal();assert handle.accepted
        f=handle.cancel_goal_async();rclpy.spin_until_future_complete(node,f,timeout_sec=3)
        assert result(handle)==5
        results['action_cancellation']=True
        timer.cancel();spin(.7)
        handle=goal();assert handle.accepted
        assert result(handle,3)==6
        results['stale_correction_aborts_without_motion']=True
        output.write_text(json.dumps({'scope':'production fine-adjust action; synthetic corrections and ideal base fixture only',
                                     'checks':results},indent=2)+'\n')
        print(output.read_text())
    finally:
        node.destroy_node();rclpy.shutdown()
        proc.send_signal(signal.SIGINT)
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=5)
        log.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args().output)

#!/usr/bin/env python3
"""Instantiate the actual Jazzy Nav2 plugins/BT against synthetic scan/odometry.

No CAN, serial, real camera, arm driver or commanded travel. The output gate
stays stopped, and the navigation target is the current estimated pose.
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
from lifecycle_msgs.srv import GetState
from nav2_msgs.action import NavigateToPose
from tf2_ros import Buffer, TransformListener


def main(output):
    log=output.with_suffix('.log').open('w')
    commands=[['ros2','run','atom_base','kinematic_fixture','--ros-args',
               '-p','navigation_action:=false','-p','map_tf:=false'],
              ['ros2','launch','atom_base','mobile.launch.py','backend:=external','navigation:=true']]
    procs=[subprocess.Popen(c,stdout=log,stderr=subprocess.STDOUT,start_new_session=True) for c in commands]
    rclpy.init();node=rclpy.create_node('nav2_jazzy_config_check')
    buffer=Buffer();listener=TransformListener(buffer,node)
    try:
        # Explicit synthetic seed; physical deployment still requires its measured initial pose.
        from geometry_msgs.msg import PoseWithCovarianceStamped
        initial=node.create_publisher(PoseWithCovarianceStamped,'/initialpose',10)
        states={}
        nodes=('map_server','amcl','planner_server','controller_server','smoother_server',
               'behavior_server','velocity_smoother','collision_monitor','bt_navigator','waypoint_follower')
        deadline=time.monotonic()+100
        while time.monotonic()<deadline:
            for name in nodes:
                if states.get(name)=='active': continue
                client=node.create_client(GetState,f'/{name}/get_state')
                if client.wait_for_service(timeout_sec=.3):
                    future=client.call_async(GetState.Request())
                    rclpy.spin_until_future_complete(node,future,timeout_sec=.5)
                    if future.done() and future.result(): states[name]=future.result().current_state.label
                node.destroy_client(client)
            pose=PoseWithCovarianceStamped()
            pose.header.frame_id='map';pose.header.stamp=node.get_clock().now().to_msg()
            pose.pose.pose.orientation.w=1.
            pose.pose.covariance[0]=pose.pose.covariance[7]=.001
            pose.pose.covariance[35]=.001
            initial.publish(pose)
            if all(states.get(n)=='active' for n in nodes): break
            rclpy.spin_once(node,timeout_sec=.1)
        assert all(states.get(n)=='active' for n in nodes),states
        client=ActionClient(node,NavigateToPose,'/navigate_to_pose')
        assert client.wait_for_server(timeout_sec=5)
        deadline=time.monotonic()+5
        while True:
            try:
                transform=buffer.lookup_transform('map','base_link',rclpy.time.Time());break
            except Exception:
                assert time.monotonic()<deadline
                rclpy.spin_once(node,timeout_sec=.1)
        goal=NavigateToPose.Goal()
        goal.pose.header.frame_id='map';goal.pose.header.stamp=node.get_clock().now().to_msg()
        goal.pose.pose.position.x=transform.transform.translation.x
        goal.pose.pose.position.y=transform.transform.translation.y
        goal.pose.pose.orientation=transform.transform.rotation
        future=client.send_goal_async(goal)
        rclpy.spin_until_future_complete(node,future,timeout_sec=10)
        assert future.result() is not None and future.result().accepted
        result=future.result().get_result_async()
        rclpy.spin_until_future_complete(node,result,timeout_sec=30)
        assert result.result() is not None and result.result().status==4,result.result()
        output.write_text(json.dumps({'scope':'Nav2 plugin/BT startup with synthetic sensors, current-pose target, base gate stopped',
                                     'nodes':states,'current_pose_goal_status':result.result().status},indent=2)+'\n')
        print(output.read_text())
    finally:
        node.destroy_node();rclpy.shutdown()
        for proc in procs:
            if proc.poll() is None: proc.send_signal(signal.SIGINT)
        for proc in procs:
            try: proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=5)
        log.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args().output)

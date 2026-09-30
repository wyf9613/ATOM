#!/usr/bin/env python3
"""Gazebo-only observation task and software-stop supervisor. Never a hardware E-stop."""
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from sensor_msgs.msg import JointState
from rosgraph_msgs.msg import Clock
from std_msgs.msg import String
from std_srvs.srv import Trigger
from rcl_interfaces.srv import GetParameters
from controller_manager_msgs.srv import ListControllers, SwitchController
from action_msgs.srv import CancelGoal
from atom_operator_interfaces.action import ExecuteTask

class Supervisor(Node):
    def __init__(self):
        super().__init__('atom_gazebo_task_supervisor')
        self.group=ReentrantCallbackGroup();self.lock=threading.RLock();self.transition_lock=threading.RLock()
        self.latched=True;self.startup_inhibit=True;self.generation=0;self.busy=False;self.process=None
        self.stop_confirmed=False;self.verified=False;self.last_clock=None;self.clock_seen=0
        self.positions={};self.velocities={};self.joint_seen=0;self.controller=None;self.controller_seen=0
        self.state={'schema_version':1,'state':'IDLE','detail':'Gazebo observation baseline only','progress':0}
        self.create_subscription(Clock,'/clock',self.clock,10,callback_group=self.group)
        self.create_subscription(JointState,'/joint_states',self.joints,10,callback_group=self.group)
        self.safety_pub=self.create_publisher(String,'/atom/safety/status',10)
        self.task_pub=self.create_publisher(String,'/atom/task/status',10)
        self.list_client=self.create_client(ListControllers,'/controller_manager/list_controllers',callback_group=self.group)
        self.switch_client=self.create_client(SwitchController,'/controller_manager/switch_controller',callback_group=self.group)
        self.param_client=self.create_client(GetParameters,'/robot_state_publisher/get_parameters',callback_group=self.group)
        self.cancel_clients=[self.create_client(CancelGoal,name,callback_group=self.group) for name in
                             ('/move_action/_action/cancel_goal','/uf850_traj_controller/follow_joint_trajectory/_action/cancel_goal')]
        self.create_service(Trigger,'/atom/safety/stop',self.stop,callback_group=self.group)
        self.create_service(Trigger,'/atom/safety/reset_stop',self.reset,callback_group=self.group)
        self.create_service(Trigger,'/atom/task/cancel',self.cancel,callback_group=self.group)
        self.action=ActionServer(self,ExecuteTask,'/atom/task/execute',execute_callback=self.execute,
                                goal_callback=self.goal,cancel_callback=self.cancel_goal,callback_group=self.group)
        self.create_timer(.2,self.publish,callback_group=self.group)
        self.create_timer(1.,self.poll,callback_group=self.group)
        self.polling=False
        self.log_dir=Path('/workspace/tmp/operator_gui/tasks');self.log_dir.mkdir(parents=True,exist_ok=True)

    def clock(self,message):
        value=message.clock.sec+message.clock.nanosec*1e-9
        if value!=self.last_clock:self.last_clock=value;self.clock_seen=time.monotonic()

    def joints(self,message):
        positions=dict(zip(message.name,message.position));velocities=dict(zip(message.name,message.velocity))
        names=[f'joint{i}' for i in range(1,7)]
        if all(n in positions and n in velocities and math.isfinite(positions[n]) and math.isfinite(velocities[n]) for n in names):
            with self.lock:
                self.positions={n:positions[n] for n in names};self.velocities={n:velocities[n] for n in names};self.joint_seen=time.monotonic()

    def wait(self,future,timeout=2):
        deadline=time.monotonic()+timeout
        while rclpy.ok() and not future.done() and time.monotonic()<deadline:time.sleep(.02)
        return future.result() if future.done() else None

    def poll(self):
        if self.polling:return
        self.polling=True
        try:
            if not self.verified and self.param_client.service_is_ready():
                response=self.wait(self.param_client.call_async(GetParameters.Request(names=['robot_description'])))
                if response and response.values:
                    description=response.values[0].string_value
                    self.verified='<plugin>gz_ros2_control/GazeboSimSystem</plugin>' in description
            if self.list_client.service_is_ready():
                response=self.wait(self.list_client.call_async(ListControllers.Request()))
                if response:
                    states={c.name:c.state for c in response.controller}
                    self.controller=states.get('uf850_traj_controller');self.controller_seen=time.monotonic()
            if self.startup_inhibit and self.fresh():
                if self.inhibit():
                    self.startup_inhibit=False
                    self.state={'schema_version':1,'state':'STOPPED','detail':'Startup stop confirmed; manual reset required','progress':0}
        finally:self.polling=False

    def fresh(self):
        now=time.monotonic()
        return self.verified and now-self.clock_seen<2 and now-self.joint_seen<1 and now-self.controller_seen<2

    def stationary(self):
        return self.fresh() and bool(self.velocities) and max(abs(v) for v in self.velocities.values())<.01

    def publish(self):
        with self.lock:
            if self.stop_confirmed and not self.stationary():
                self.stop_confirmed=False
            safety={'schema_version':1,'source':'gazebo','hardware_estop':'not_applicable',
                    'motion_allowed':self.fresh() and not self.latched and not self.busy and self.controller=='active',
                    'stop_confirmed':self.stop_confirmed,'software_stop_latched':self.latched}
            self.safety_pub.publish(String(data=json.dumps(safety)))
            self.task_pub.publish(String(data=json.dumps(self.state)))

    def goal(self,request):
        with self.lock:
            # Only the existing observation trajectory is implemented. Unsupported goals are rejected.
            if request.operation!=ExecuteTask.Goal.OBSERVE or not request.request_id or self.busy or self.latched or not self.fresh() or self.controller!='active':
                return GoalResponse.REJECT
            self.busy=True;self.stop_confirmed=False
            return GoalResponse.ACCEPT

    def switch(self,activate):
        if not self.verified or not self.switch_client.service_is_ready():return False
        request=SwitchController.Request(strictness=2)
        if activate:request.activate_controllers=['uf850_traj_controller']
        else:request.deactivate_controllers=['uf850_traj_controller']
        request.timeout.sec=2
        response=self.wait(self.switch_client.call_async(request),3)
        if not response or not response.ok:return False
        self.controller='active' if activate else 'inactive';self.controller_seen=time.monotonic()
        return True

    def terminate(self):
        with self.lock:process=self.process
        if process and process.poll() is None:
            try:os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:pass

    def inhibit(self):
        with self.transition_lock:
            return self._inhibit()

    def _inhibit(self):
        with self.lock:
            self.latched=True;self.generation+=1;self.stop_confirmed=False
        self.terminate()
        for client in self.cancel_clients:
            if client.service_is_ready():client.call_async(CancelGoal.Request())
        if not self.fresh():return False
        switched=self.controller=='inactive' or self.switch(False)
        deadline=time.monotonic()+.8;start_stamp=self.joint_seen;consecutive=0
        while switched and time.monotonic()<deadline:
            if self.joint_seen>start_stamp:
                consecutive=consecutive+1 if self.stationary() else 0;start_stamp=self.joint_seen
                if consecutive>=3:
                    with self.lock:self.stop_confirmed=True
                    return True
            time.sleep(.05)
        return False

    def stop(self,request,response):
        response.success=self.inhibit()
        response.message='Gazebo arm controller inactive; standstill verified' if response.success else 'Stop latched; standstill not confirmed'
        self.publish();return response

    def reset(self,request,response):
        with self.transition_lock:
            return self._reset(request,response)

    def _reset(self,request,response):
        with self.lock:
            generation=self.generation
            allowed=self.latched and self.stop_confirmed and not self.busy and self.stationary()
        response.success=False
        if allowed and self.switch(True):
            with self.lock:
                if generation==self.generation:
                    self.latched=False;response.success=True
                    self.state={'schema_version':1,'state':'IDLE','detail':'Reset completed; no task resumed','progress':0}
        response.message='Software latch reset; no task resumed' if response.success else 'Reset rejected: wait for confirmed stop, task termination and fresh feedback'
        self.publish();return response

    def cancel(self,request,response):
        response.success=self.inhibit();response.message='Cancellation requested; software stop latched'
        self.publish();return response

    def cancel_goal(self,handle):
        # Accept promptly; the execution worker inhibits motion and confirms stop
        # before returning the final CANCELED result.
        return CancelResponse.ACCEPT

    def execute(self,handle):
        request_id=handle.request.request_id
        # Never put arbitrary request_id into a shell or pathname.
        log_file=self.log_dir/(str(time.time_ns())+'.log')
        result=ExecuteTask.Result(success=False,error_code='FAILED',message='Observation failed')
        try:
            with self.lock:
                self.state={'schema_version':1,'state':'EXECUTING','request_id':request_id,'progress':0.1,
                            'detail':'Fixed observation round trip; no pick/place or obstacle avoidance'}
                if self.latched:raise RuntimeError('Stopped before execution')
                with log_file.open('w') as output:
                    self.process=subprocess.Popen(['ros2','run','atom_xarm_sim','trajectory_demo','--ros-args',
                        '-p','allow_demo_gripper_joints:=true','-p','demo_offsets_rad:=[0.25,-0.16,-0.19,0.15,0.16,-0.18]',
                        '-p','hold_at_offset_sec:=2.0','-p','report_stem:=gui_'+str(time.time_ns())],
                        stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
            deadline=time.monotonic()+150
            while self.process.poll() is None:
                if handle.is_cancel_requested or self.latched or not self.fresh() or time.monotonic()>deadline:
                    self.inhibit();self.terminate();break
                log=log_file.read_text(errors='replace')
                progress=.6 if 'PASS: MoveIt planned and executed offset' in log else .15
                with self.lock:self.state['progress']=progress
                handle.publish_feedback(ExecuteTask.Feedback(state='EXECUTING',progress=progress,message=self.state['detail']))
                time.sleep(.3)
            try:code=self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid,signal.SIGKILL);code=self.process.wait(timeout=2)
            log=log_file.read_text(errors='replace')
            if handle.is_cancel_requested:
                handle.canceled();result.error_code='CANCELED';result.message='Task canceled; reset software stop before another task'
            elif self.latched:
                handle.abort();result.error_code='STOPPED';result.message='Software stop interrupted observation'
            elif code==0 and 'planning/control simulation completed' in log:
                handle.succeed();result.success=True;result.error_code='';result.message='Gazebo fixed observation round trip completed'
            else:
                self.inhibit();handle.abort();result.message='Observation failed; inspect '+str(log_file)
        except Exception as exc:
            self.inhibit()
            if handle.is_active:handle.abort()
            result.message=str(exc)
        finally:
            with self.lock:
                self.busy=False;self.process=None
                self.state={'schema_version':1,'state':'SUCCEEDED' if result.success else result.error_code,
                            'detail':result.message,'request_id':request_id,'progress':1 if result.success else 0}
            self.publish()
        return result


def main():
    rclpy.init();node=Supervisor();executor=MultiThreadedExecutor(num_threads=6);executor.add_node(node)
    try:executor.spin()
    except KeyboardInterrupt:node.inhibit()
    finally:node.terminate();executor.shutdown();node.destroy_node();rclpy.try_shutdown()

if __name__=='__main__':main()

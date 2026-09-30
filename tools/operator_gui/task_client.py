"""Standard ROS action lifecycle; all movement belongs to the task executive."""
import math
import time
from rclpy.action import ActionClient
from atom_operator_interfaces.action import ExecuteTask

class TaskClient:
    def __init__(self, node, gateway, name, operations):
        self.gateway=gateway
        self.operations=set(operations)
        self.client=ActionClient(node,ExecuteTask,name)
        self.active=None
        self.handle=None
        self.started=0
        self.cancel_requested=False
        self.cancel_future=None
        node.create_timer(.2,self.watchdog)

    def ready(self,command):
        return command in self.operations and self.client.server_is_ready()

    def send(self,command,parameters,request_id):
        if self.active:
            self.gateway.pending.discard(command)
            raise PermissionError('Another action is active')
        goal=ExecuteTask.Goal(request_id=request_id)
        goal.operation={'observe':0,'pick':1,'place':2,'navigate':3}[command]
        goal.slot_id=parameters.get('slot',0)
        if command=='navigate':
            goal.target.header.frame_id='map'
            goal.target.pose.position.x=float(parameters['x']);goal.target.pose.position.y=float(parameters['y'])
            goal.target.pose.orientation.z=math.sin(parameters['yaw']/2)
            goal.target.pose.orientation.w=math.cos(parameters['yaw']/2)
        self.active=(command,request_id);self.handle=None;self.started=time.monotonic();self.cancel_requested=False;self.cancel_future=None
        self.gateway.update('task',{'schema_version':1,'state':'SUBMITTING','request_id':request_id,'progress':0,'detail':command})
        future=self.client.send_goal_async(goal,feedback_callback=self.feedback)
        future.add_done_callback(self.accepted)

    def feedback(self,message):
        with self.gateway.lock:
            if not self.active:return
            f=message.feedback
            self.gateway.update('task',{'schema_version':1,'state':f.state,'progress':f.progress,
                                       'detail':f.message,'request_id':self.active[1]})

    def accepted(self,future):
        with self.gateway.lock:
            try:
                self.handle=future.result()
                if not self.handle.accepted:
                    return self.finish(False,'Goal rejected by task executive','REJECTED')
                self.gateway.event('info',f'{self.active[1]}: goal accepted')
                self.handle.get_result_async().add_done_callback(self.result)
                if self.cancel_requested:self.request_cancel()
            except Exception as exc:self.finish(False,str(exc),'ERROR')

    def result(self,future):
        with self.gateway.lock:
            try:
                result=future.result().result
                self.finish(result.success,result.message,result.error_code or 'SUCCEEDED')
            except Exception as exc:self.finish(False,str(exc),'ERROR')

    def finish(self,success,message,code):
        if not self.active:return
        command,request_id=self.active
        self.gateway.pending.discard(command)
        self.gateway.update('task',{'schema_version':1,'state':'SUCCEEDED' if success else code,
                                   'progress':1 if success else None,'request_id':request_id,'detail':message})
        self.gateway.event('info' if success else 'error',f'{request_id}: {command} {code}: {message}')
        self.active=None;self.handle=None

    def request_cancel(self):
        self.cancel_requested=True
        if self.handle is not None and self.handle.accepted:
            if self.cancel_future is None or self.cancel_future.done():
                self.cancel_future=self.handle.cancel_goal_async()
                self.cancel_future.add_done_callback(self.cancel_response)

    def cancel_response(self,future):
        with self.gateway.lock:
            try:
                response=future.result()
                self.gateway.event('info' if response.goals_canceling else 'error',
                                   'Action cancellation acknowledged' if response.goals_canceling else 'Cancellation not accepted; inspect task result')
            except Exception as exc:self.gateway.event('error',f'Action cancellation response unknown: {exc}')

    def watchdog(self):
        with self.gateway.lock:
            if self.active and time.monotonic()-self.started>180 and not self.cancel_requested:
                self.gateway.event('error','Task deadline exceeded; requesting cancellation, awaiting final result')
                self.request_cancel()

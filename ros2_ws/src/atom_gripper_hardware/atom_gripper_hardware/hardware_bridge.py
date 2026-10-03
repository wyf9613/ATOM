"""One hardware boundary replaces sensor-only bridge when actuator integration is enabled."""
import json
import time
import threading
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from sensor_msgs.msg import MagneticField
from std_msgs.msg import String
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus
from atom_operator_interfaces.action import ControlGripper
from .controller import GripperController, validate
from .ownership import ControlLease


class HardwareBridge(Node):
    def __init__(self):
        super().__init__('atom_gripper_bridge')
        if self.get_parameter('use_sim_time').value:
            raise RuntimeError('Physical gripper bridge requires system clock')
        self.declare_parameter('port', '/dev/ttyUSB0')
        self.declare_parameter('enable_motion', False)
        self.declare_parameter('frame_id', 'gripper_magnetic_sensor')
        self.declare_parameter('log_path', '/tmp/atom_gripper_hardware.jsonl')
        self.controller = GripperController(self.get_parameter('port').value,
                                           self.get_parameter('enable_motion').value,
                                           self.get_parameter('log_path').value)
        self.status = self.create_publisher(String, '/atom/gripper/status', 10)
        self.field = self.create_publisher(MagneticField, '/atom/gripper/magnetic_field', 10)
        self.diagnostics = self.create_publisher(DiagnosticArray, '/diagnostics', 10)
        self.create_timer(0.1, self.publish_state)
        self.group = ReentrantCallbackGroup()
        self.action = ActionServer(self, ControlGripper, '/atom/gripper/control', self.execute,
                                   goal_callback=self.goal, cancel_callback=self.cancel,
                                   callback_group=self.group)
        self.owner_lock = threading.Lock()
        self.owner = None
        self.lease = ControlLease()
        self.lease_stop = None
        self.create_subscription(String,'/atom/gripper/control_heartbeat',self.caller_heartbeat,10)

    def caller_heartbeat(self, message):
        with self.owner_lock:
            self.lease.keepalive(message.data)

    def goal(self, goal):
        try:
            validate(goal.command, {'position':goal.position, 'force_n':goal.force_n})
            if goal.command in self.controller.blocks(): return GoalResponse.REJECT
            with self.owner_lock:
                if self.owner is not None and goal.command not in {'stop','disarm'}: return GoalResponse.REJECT
                self.lease.reserve(goal.command, goal.control_owner)
                if goal.command not in {'stop','disarm'}: self.owner = 'reserved'
            return GoalResponse.ACCEPT
        except (ValueError, PermissionError): return GoalResponse.REJECT

    def cancel(self, handle):
        with self.owner_lock:
            if self.owner is not handle: return CancelResponse.REJECT
        self.controller.cancel()
        return CancelResponse.ACCEPT

    def execute(self, handle):
        command = handle.request.command
        owns = command not in {'stop','disarm'}
        if owns:
            with self.owner_lock: self.owner = handle
        result = ControlGripper.Result()
        try:
            future = self.controller.submit(command, {'position':handle.request.position,'force_n':handle.request.force_n})
            deadline = time.monotonic()+70
            while not future.done():
                if handle.is_cancel_requested: self.controller.cancel()
                if time.monotonic()>deadline:
                    self.controller.cancel(); raise RuntimeError('Action timeout; stop requested')
                state=self.controller.snapshot()
                feedback=ControlGripper.Feedback()
                feedback.state=state['command_state']; feedback.position=state['position'] or -1
                feedback.load_raw=state['load_raw'] or 0; feedback.fault=bool(state['fault'])
                handle.publish_feedback(feedback)
                time.sleep(0.1)
            value=future.result()
            result.success=bool(value['success']); result.message=json.dumps(value)
            result.position_verified=value.get('position_verified',False)
            result.grasp_verified=False
            result.final_position=self.controller.snapshot()['position'] or -1
            if handle.is_cancel_requested: handle.canceled(); result.success=False
            else: handle.succeed()
        except Exception as exc:
            result.success=False; result.message=str(exc)
            if handle.is_cancel_requested: handle.canceled()
            else: handle.abort()
        finally:
            with self.owner_lock:
                self.lease.complete(command,handle.request.control_owner,result.success)
                if owns: self.owner=None
        return result

    def publish_state(self):
        # Caller loss requests hold; never silently release an object.
        new_stop=None
        with self.owner_lock:
            expired=self.lease.expired()
            generation=self.lease.generation
            if expired and (self.lease_stop is None or self.lease_stop.done()):
                try: new_stop=self.lease_stop=self.controller.submit('stop')
                except PermissionError: pass
        if new_stop:
            def stopped(future):
                if future.exception() is None:
                    with self.owner_lock:
                        if self.lease.generation==generation: self.lease.owner=None
            new_stop.add_done_callback(stopped)
        state=self.controller.snapshot()
        state['blocks']=self.controller.blocks()
        with self.owner_lock: state['control_owner']=self.lease.owner
        self.status.publish(String(data=json.dumps(state)))
        if state['sensor_valid'] and state['sensor_fresh']:
            msg=MagneticField(); msg.header.stamp=self.get_clock().now().to_msg()
            msg.header.frame_id=self.get_parameter('frame_id').value
            msg.magnetic_field.x,msg.magnetic_field.y,msg.magnetic_field.z=[v*1e-6 for v in state['magnetic_uT']]
            # //TODO G06: measure mount TF, covariance and clock synchronization; zeros mean unknown covariance.
            self.field.publish(msg)
        status=DiagnosticStatus()
        status.name='atom_gripper/hardware'; status.hardware_id=self.get_parameter('port').value
        ready=state['motor_fresh'] and state['sensor_fresh'] and state['sensor_valid'] and not state['fault']
        status.level=DiagnosticStatus.OK if ready else DiagnosticStatus.ERROR
        status.message='position commissioning; force uncalibrated' if ready else str(state['fault'] or 'feedback stale/invalid')
        msg=DiagnosticArray(); msg.header.stamp=self.get_clock().now().to_msg(); msg.status=[status]
        self.diagnostics.publish(msg)

    def destroy_node(self):
        self.controller.close()
        self.action.destroy()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args); node=HardwareBridge(); executor=MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try: executor.spin()
    finally: executor.shutdown(); node.destroy_node(); rclpy.try_shutdown()

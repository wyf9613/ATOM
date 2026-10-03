"""Reusable ROS gripper capability; explicit opt-in, no simulated grasp substitution."""
import time
import uuid
import rclpy


class GripperControl:
    def initialize_gripper_control(self):
        self.declare_parameter('enable_hardware_gripper',False)
        self.declare_parameter('hardware_arm_integration_verified',False)
        self.declare_parameter('gripper_action','/atom/gripper/control')
        self.gripper_client=None
        self.gripper_owned=False
        self.gripper_owner='task-'+uuid.uuid4().hex
        from std_msgs.msg import String
        self.gripper_heartbeat=self.create_publisher(String,'/atom/gripper/control_heartbeat',10)
        def heartbeat():
            if self.gripper_owned: self.gripper_heartbeat.publish(String(data=self.gripper_owner))
        self.create_timer(.2,heartbeat)

    def prepare_gripper(self):
        if not self.get_parameter('enable_hardware_gripper').value:
            raise RuntimeError('Hardware gripper recipe requires explicit enable_hardware_gripper')
        if self.get_parameter('use_sim_time').value:
            raise RuntimeError('Real gripper cannot run from a simulation-clock arm task')
        if (self.get_parameter('task_recipe').value!='gripper_position_check' and
                not self.get_parameter('hardware_arm_integration_verified').value):
            raise RuntimeError('Combined arm/gripper recipe awaits physical arm integration verification')
        # //TODO G07: verify physical arm TCP/TF, hardware safety supervision and arm/gripper synchronized abort.
        from rclpy.action import ActionClient
        from atom_operator_interfaces.action import ControlGripper
        self.gripper_type=ControlGripper
        self.gripper_client=ActionClient(self,ControlGripper,self.get_parameter('gripper_action').value)
        if not self.gripper_client.wait_for_server(timeout_sec=3): raise RuntimeError('Gripper hardware action unavailable')
        self.gripper_owned=True
        try: self._gripper_command('arm')
        except Exception:
            self.gripper_owned=False
            raise

    def _gripper_command(self,command,position=0):
        if self.gripper_client is None: raise RuntimeError('Prepare gripper capability first')
        future=self.gripper_client.send_goal_async(self.gripper_type.Goal(command=command,control_owner=self.gripper_owner,position=position,force_n=0.0))
        rclpy.spin_until_future_complete(self,future,timeout_sec=4)
        if not future.done(): raise RuntimeError('Gripper goal response timeout; outcome unknown')
        handle=future.result()
        if not handle.accepted: raise RuntimeError('Gripper command rejected: '+command)
        result=handle.get_result_async()
        deadline=time.monotonic()+65
        while not result.done() and time.monotonic()<deadline:
            # //TODO G08: consume the task supervisor stop/cancel state during hardware composition.
            rclpy.spin_once(self,timeout_sec=0.1)
        if not result.done():
            handle.cancel_goal_async()
            raise RuntimeError('Gripper action timeout; cancellation requested')
        value=result.result().result
        if not value.success: raise RuntimeError('Gripper failed: '+value.message)
        if command in {'open','close','move'} and not value.position_verified:
            raise RuntimeError('Gripper position completion not verified')
        return value

    def open_gripper(self): self._gripper_command('open')
    def close_gripper(self):
        # //TODO G09: do not lift/transport on position completion; independent contact/grasp validation required.
        self._gripper_command('close')
    def stop_gripper(self): self._gripper_command('stop')

    def cleanup_gripper_control(self):
        if self.gripper_client is not None:
            if self.gripper_owned:
                try: self._gripper_command('stop')
                except Exception as exc: self.get_logger().error('Gripper stop unconfirmed: '+str(exc))
            self.gripper_client.destroy(); self.gripper_client=None
            self.gripper_owned=False

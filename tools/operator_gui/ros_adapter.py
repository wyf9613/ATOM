"""ROS 2 telemetry adapter. Motion is delegated to the future task supervisor."""
import json
import math
import threading
import time
from collections import deque


class FrameRate:
    """Wall-clock rate over the last five seconds; rates are not simulation Hz."""
    def __init__(self):
        self.samples = deque()
        self.sequence = 0
    def tick(self):
        now = time.monotonic()
        self.sequence += 1
        self.samples.append(now)
        while self.samples and now-self.samples[0] > 5:
            self.samples.popleft()
        duration = now-self.samples[0]
        return {"fps": (len(self.samples)-1)/duration if duration > 0 else 0,
                "sample_count": len(self.samples), "window_s": duration, "sequence": self.sequence}


class RosAdapter:
    def __init__(self, gateway, config=None):
        import rclpy
        from rclpy.node import Node
        from rclpy.qos import qos_profile_sensor_data
        from sensor_msgs.msg import JointState, BatteryState, CompressedImage, Image, CameraInfo
        from rosgraph_msgs.msg import Clock
        try:
            from controller_manager_msgs.srv import ListControllers
        except ImportError:
            ListControllers = None
        from tf2_ros import Buffer, TransformListener
        from rclpy.parameter import Parameter
        from nav_msgs.msg import Odometry
        from diagnostic_msgs.msg import DiagnosticArray
        from std_msgs.msg import String
        from std_srvs.srv import Trigger
        self.rclpy = rclpy
        self.gateway = gateway
        rclpy.init(args=[])
        self.node = Node('atom_operator_gateway')
        config = config or {}
        self.node.set_parameters([Parameter('use_sim_time', value=bool(config.get('use_sim_time',False)))])
        gateway.metadata.update({'profile': config.get('profile','ros'),
                                 'use_sim_time':bool(config.get('use_sim_time',False)), 'interfaces':config})
        self.clients = {}
        self.futures = {}
        self.subscriptions = []
        def parameter(name, default):
            return self.node.declare_parameter(name, (config or {}).get(name, default)).value
        def subscribe(cls, name, default, callback):
            self.subscriptions.append(self.node.create_subscription(cls, parameter(name, default), callback, qos_profile_sensor_data))
        def joint_state(m):
            source_stamp = m.header.stamp.sec + m.header.stamp.nanosec*1e-9
            def filtered(indices):
                return {'names':[m.name[i] for i in indices],
                        'position':[m.position[i] if i<len(m.position) and math.isfinite(m.position[i]) else None for i in indices],
                        'velocity':[m.velocity[i] if i<len(m.velocity) and math.isfinite(m.velocity[i]) else None for i in indices],
                        'source_stamp_s':source_stamp}
            arm_indices = [i for i,n in enumerate(m.name) if n in config.get('arm_joint_names',[f'joint{k}' for k in range(1,7)])]
            gripper_indices = [i for i,n in enumerate(m.name) if 'gripper' in n or n == 'drive_joint']
            if arm_indices:
                gateway.update('arm',filtered(arm_indices))
            if gripper_indices:
                gateway.update('gripper',filtered(gripper_indices))
        subscribe(JointState,'joint_topic','/joint_states',joint_state)
        self.last_clock = None
        def clock(m):
            value = m.clock.sec + m.clock.nanosec*1e-9
            if value != self.last_clock:
                self.last_clock=value
                gateway.update('sim_clock', {'seconds':value})
        if config.get('use_sim_time',False):
            subscribe(Clock,'clock_topic','/clock',clock)
        self.tf_buffer=Buffer()
        self.tf_listener=TransformListener(self.tf_buffer,self.node)
        self.controller_client=(self.node.create_client(ListControllers, parameter('controller_service','/controller_manager/list_controllers'))
                                if ListControllers else None)
        if not ListControllers:
            gateway.event('info','Controller manager telemetry unavailable: controller_manager_msgs not installed')
        self.controller_future=None
        def controller_poll():
            if self.controller_client is None or not self.controller_client.service_is_ready() or self.controller_future and not self.controller_future.done():
                return
            self.controller_future=self.controller_client.call_async(ListControllers.Request())
            def received(future):
                try:
                    response=future.result()
                    states={c.name:c.state for c in response.controller}
                    gateway.update('controller', {'state':states.get(config.get('arm_controller','uf850_traj_controller'),'missing'),'controllers':states})
                except Exception as exc:
                    gateway.event('error',f'Controller query: {exc}')
            self.controller_future.add_done_callback(received)
        self.node.create_timer(1.0,controller_poll)
        def tool_poll():
            from rclpy.time import Time
            frame=config.get('tool_parent_frame','link_base');child=config.get('tool_frame','link_eef')
            if not self.tf_buffer.can_transform(frame,child,Time()):
                return
            t=self.tf_buffer.lookup_transform(frame,child,Time())
            stamp=t.header.stamp.sec+t.header.stamp.nanosec*1e-9
            age=self.node.get_clock().now().nanoseconds*1e-9-stamp
            if age > 2 or age < -.5:
                return
            p=t.transform.translation;q=t.transform.rotation
            gateway.update('tool', {'frame':frame,'child':child,'x':p.x,'y':p.y,'z':p.z,
                                    'quaternion':[q.x,q.y,q.z,q.w], 'source_stamp_s':stamp})
        self.node.create_timer(.5,tool_poll)
        subscribe(String,'perception_topic','/atom/approach/tag_observation',
                  lambda m: self.perception(m))
        def odom(m):
            p = m.pose.pose.position; q = m.pose.pose.orientation
            gateway.update('base', {'x': p.x,'y':p.y,'yaw':math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z)),
                                    'speed':m.twist.twist.linear.x, 'frame':m.header.frame_id})
        subscribe(Odometry,'odom_topic','/odom',odom)
        subscribe(BatteryState,'battery_topic','/battery_state',lambda m: gateway.update('battery',{
            'percent': None if not math.isfinite(m.percentage) else round(m.percentage*100,1),
            'voltage': None if not math.isfinite(m.voltage) else m.voltage}))
        subscribe(DiagnosticArray,'diagnostics_topic','/diagnostics',lambda m: gateway.update('diagnostics',[
            {'name':s.name,'level':int.from_bytes(s.level,'little') if isinstance(s.level,bytes) else int(s.level),'message':s.message} for s in m.status]))
        def structured(name, message):
            try:
                value = json.loads(message.data)
                if not isinstance(value, dict) or value.get('schema_version') != 1:
                    raise ValueError('Expected schema_version 1 JSON object')
                if name == 'safety':
                    if value.get('hardware_estop') not in ('unknown','pressed','released','not_applicable'):
                        raise ValueError('Invalid hardware_estop')
                    if type(value.get('motion_allowed')) is not bool or type(value.get('stop_confirmed')) is not bool:
                        raise ValueError('Safety flags must be booleans')
                if name=='task':
                    previous=gateway.streams.get('task',{}).get('value',{})
                    if (previous.get('request_id'),previous.get('phase'),previous.get('state')) != (value.get('request_id'),value.get('phase'),value.get('state')):
                        gateway.event('error' if value.get('state')=='FAILED' else 'info',f"Workflow {value.get('phase',value.get('state'))}: {value.get('detail','')}")
                gateway.update(name,value)
            except (ValueError,TypeError) as exc:
                gateway.event('error',f'Invalid {name} status: {exc}')
        subscribe(String,'safety_topic','/atom/safety/status',lambda m: structured('safety',m))
        subscribe(String,'task_topic','/atom/task/status',lambda m: structured('task',m))
        rgb_receive=FrameRate();rgb_preview=FrameRate();depth_receive=FrameRate();depth_output=FrameRate()
        self.rgb_rate={}
        preview_interval=1/max(1,min(30,float(config.get("preview_fps",15))))
        self.last_tag_image=0
        def camera(m):
            content = bytes(m.data)
            if len(content) > 4_000_000 or not content.startswith((b'\xff\xd8', b'\x89PNG')):
                return
            gateway.update('camera', {'encoding': 'jpeg' if content.startswith(b'\xff\xd8') else 'png',
                                      'preview':rgb_preview.tick(), 'received':self.rgb_rate})
            with gateway.lock:
                gateway.camera_image = content
        subscribe(CompressedImage, 'camera_topic', '/atom/wrist_camera/image/compressed', camera)
        if config.get('vendor_state_topic'):
            try:
                from xarm_msgs.msg import RobotMsg
                def vendor(m):
                    gateway.update('vendor', {'state':m.state,'mode':m.mode,'error_code':m.err,
                                             'warning_code':m.warn,'queued_commands':m.cmdnum,
                                             'tcp_position_m':[v/1000.0 for v in m.pose[:3]],
                                             'tcp_orientation_rad':list(m.pose[3:])})
                subscribe(RobotMsg,'vendor_state_topic',config['vendor_state_topic'],vendor)
            except ImportError:
                gateway.event('error','Vendor status unavailable: xarm_msgs not installed')
        self.camera_info=None
        def info(m):self.camera_info=m
        if config.get('camera_info_topic'):
            subscribe(CameraInfo,'camera_info_topic',config['camera_info_topic'],info)
        self.last_depth_image=0
        def depth(m):
            received=depth_receive.tick()
            if time.monotonic()-self.last_depth_image<preview_interval:return
            self.last_depth_image=time.monotonic()
            try:
                from sensor_preview import depth_preview
                content,metrics=depth_preview(m)
                with gateway.lock:gateway.depth_image=content
                metrics.update({"received":received,"preview":depth_output.tick()})
                gateway.update('depth',metrics)
            except (ImportError,ValueError) as exc:gateway.event('error',f'Depth preview: {exc}')
        if config.get('depth_topic'):
            subscribe(Image,'depth_topic',config['depth_topic'],depth)
        self.last_raw_image=0
        def raw_camera(m):
            self.rgb_rate=rgb_receive.tick()
            if time.monotonic()-self.last_raw_image < preview_interval:
                return
            self.last_raw_image=time.monotonic()
            try:
                import cv2
                import numpy as np
                channels={'rgb8':3,'bgr8':3,'rgba8':4,'bgra8':4,'mono8':1}.get(m.encoding)
                if not channels or m.height <= 0 or m.width <= 0 or m.width*m.height > 4_000_000 or m.step < m.width*channels:
                    return
                arr=np.frombuffer(bytes(m.data),dtype=np.uint8).reshape(m.height,m.step)
                image=arr[:,:m.width*channels].reshape(m.height,m.width,channels)
                if m.encoding=='rgb8':image=cv2.cvtColor(image,cv2.COLOR_RGB2BGR)
                elif m.encoding=='rgba8':image=cv2.cvtColor(image,cv2.COLOR_RGBA2BGR)
                elif m.encoding=='bgra8':image=cv2.cvtColor(image,cv2.COLOR_BGRA2BGR)
                if config.get('tag_monitor',False) and time.monotonic()-self.last_tag_image >= .5:
                    self.last_tag_image=time.monotonic()
                    from sensor_preview import tag_preview
                    if channels==1:image=cv2.cvtColor(image,cv2.COLOR_GRAY2BGR)
                    status=tag_preview(image,self.camera_info,m.header.frame_id)
                    status['source_stamp_s']=m.header.stamp.sec+m.header.stamp.nanosec*1e-9
                    previous=gateway.streams.get('tags',{}).get('value',{}).get('detected_ids')
                    if previous!=status['detected_ids']:
                        gateway.event('info','Detected Tags: '+str(status['detected_ids']))
                    gateway.update('tags',status)
                ok,encoded=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,75])
                if ok:
                    compressed=CompressedImage(format='jpeg',data=encoded.tobytes())
                    camera(compressed)
            except (ImportError,ValueError) as exc:
                gateway.event('error',f'Raw camera conversion unavailable: {exc}')
        if config.get('raw_camera_topic'):
            subscribe(Image,'raw_camera_topic',config['raw_camera_topic'],raw_camera)
        self.request_pub = self.node.create_publisher(String, parameter('request_topic','/atom/operator/request'),10)
        self.String = String
        self.Trigger = Trigger
        for command in ('observe','pick','place','navigate','cancel','stop','reset_stop'):
            service = parameter(command+'_service', '/atom/safety/'+command if command in ('stop','reset_stop') else '/atom/task/'+command)
            self.clients[command] = self.node.create_client(Trigger,service)
        self.tasks = None
        if config.get('task_action'):
            try:
                from task_client import TaskClient
                self.tasks=TaskClient(self.node,gateway,config['task_action'],config.get('task_operations',['observe']))
            except ImportError:
                gateway.event('error','Task action unavailable: atom_operator_interfaces is not built/sourced')
        self.node.create_timer(.2,self.check_timeouts)
        def spin():
            from rclpy.executors import ExternalShutdownException
            try:
                rclpy.spin(self.node)
            except ExternalShutdownException:
                pass
            except Exception as exc:
                gateway.metadata['ros_executor']='failed'
                gateway.event('error',f'ROS executor failed: {exc}; reconnect required')
        self.thread = threading.Thread(target=spin,daemon=True)
        self.thread.start()

    def perception(self, message):
        try:
            value=json.loads(message.data)
            if not isinstance(value,dict) or type(value.get('tag_id')) is not int:
                raise ValueError('Expected Tag observation')
            self.gateway.update('perception',value)
        except (ValueError,TypeError) as exc:
            self.gateway.event('error',f'Invalid perception data: {exc}')

    def available(self):
        if not self.rclpy.ok():
            return {c:False for c in self.clients}
        available={c: c not in ('pick','place','navigate') and client.service_is_ready()
                   for c,client in self.clients.items()}
        if self.tasks:
            for command in ('observe','pick','place','navigate'):
                available[command]=self.tasks.ready(command)
            available['cancel']=available['cancel'] or self.tasks.active is not None
        return available

    def send(self, command, parameters, request_id):
        if self.tasks and self.tasks.ready(command):
            self.tasks.send(command,parameters,request_id)
            return
        if self.tasks and command=='cancel' and self.tasks.active:
            self.tasks.request_cancel()
            self.gateway.pending.discard('cancel')
            return
        # Parameter-bearing requests belong to the task executive; never publish to cmd_vel or arm trajectory.
        # Trigger is used only for parameter-free operations. Pick/place/navigation await a typed action integration.
        if command in ('pick','place','navigate'):
            with self.gateway.lock:
                self.gateway.pending.discard(command)
            raise PermissionError('Parameterized tasks require the future typed action adapter; monitoring is connected')
        message = self.String()
        message.data = json.dumps({'schema_version':1,'request_id':request_id,'command':command,'parameters':parameters})
        self.request_pub.publish(message)  # Audit only; MUST NOT be a motion subscriber.
        try:
            future = self.clients[command].call_async(self.Trigger.Request())
            with self.gateway.lock:
                self.futures[request_id] = (command,future,time.monotonic(),self.gateway.stop_generation)
            future.add_done_callback(lambda f: self.completed(request_id,f))
        except Exception:
            with self.gateway.lock:
                self.gateway.pending.discard(command)
            raise

    def completed(self, request_id, future):
        with self.gateway.lock:
            item = self.futures.pop(request_id,None)
            if not item:
                return
            command = item[0]
            self.gateway.pending.discard(command)
            try:
                result = future.result()
                success = result is not None and result.success
                if command == 'reset_stop' and success:
                    safety = self.gateway.snapshot()['streams'].get('safety',{})
                    value = safety.get('value',{})
                    if (item[3] == self.gateway.stop_generation and safety.get('fresh')
                            and self.gateway.safety_permits_reset(value) and value.get('stop_confirmed')):
                        self.gateway.stop_latched = False
                    else:
                        success = False
                self.gateway.event('info' if success else 'error',f'{command}: '+(result.message if result else 'no response'))
            except Exception as exc:
                self.gateway.event('error',f'{command}: {exc}')

    def check_timeouts(self):
        with self.gateway.lock:
            for request_id,(command,future,started,generation) in list(self.futures.items()):
                if time.monotonic()-started > 5:
                    self.futures.pop(request_id)
                    self.gateway.pending.discard(command)
                    future.cancel()
                    self.gateway.event('error',f'{command}: acknowledgment timeout; outcome unknown')

    def close(self):
        self.rclpy.try_shutdown()
        self.thread.join(timeout=2)
        self.node.destroy_node()

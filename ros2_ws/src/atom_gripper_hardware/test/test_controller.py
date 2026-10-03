"""Protocol-level simulated device: never opens a physical serial port."""
import threading
import time
import unittest
from atom_gripper_hardware.controller import GripperController, validate
from atom_gripper_hardware.ownership import ControlLease


class FakeDevice:
    def __init__(self):
        self.commands=[]; self.buffer=bytearray(); self.lock=threading.RLock()
        self.position=2300; self.armed=False; self.fault=False; self.valid=True
        self.stream=False; self.last_sample=0; self.sequence=0
        self.delay_motion=False; self.fail_motion=False; self.closed=False

    def emit(self,*lines):
        self.buffer.extend(('\n'.join(lines)+'\n').encode())

    def status(self):
        return (f'# MOTOR enabled=1 configured=1 armed={int(self.armed)} moving=0 fault={int(self.fault)} '
                f'id=1 baud=1000000 pos={self.position} load_raw=44 voltage_raw=77 temp_raw=22')

    def write(self,data):
        with self.lock:
            command=data.decode().strip(); self.commands.append(command)
            if command=='STREAM ON': self.stream=True; self.emit('# STREAM ON')
            elif command=='PING': self.emit('# PING ok=1 mode=0 mode_read_ok=1 feedback_ok=1',self.status())
            elif command=='STATUS': self.emit(self.status())
            elif command=='ARM': self.armed=True; self.emit('# ARM_OK')
            elif command=='DISARM': self.armed=False; self.emit('# DISARM_OK torque_off')
            elif command=='RESET': self.fault=False; self.emit('# RESET_OK')
            elif command=='STOP': self.emit('# STOP position_hold_requested_not_estop')
            elif command.startswith('JOG '):
                start=self.position; target=start+int(command.split()[1])
                self.emit(f'# MOVE_START start={start} target={target}')
                if self.fail_motion:
                    self.fault=True; self.emit('# FAULT servo_limit_exceeded latched')
                elif not self.delay_motion:
                    self.position=target
                    self.emit(f'# MOTION_SUMMARY result=done start={start} target={target} last_pos={target} peak_abs_load=44',
                              f'# MOVE_DONE target={target} pos={target} load_raw=0 voltage_raw=77 temp_raw=22')
        return len(data)

    def read(self,count):
        with self.lock:
            if self.stream and time.monotonic()-self.last_sample>0.04:
                self.last_sample=time.monotonic(); self.sequence+=1
                self.emit(f'V1,{self.sequence},{self.sequence*100},20,{int(self.valid)},52,-66,60')
            result=bytes(self.buffer[:count]); del self.buffer[:count]; return result

    def close(self): self.closed=True


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.device=FakeDevice()
        self.controller=GripperController('fake',True,opener=lambda *a,**kw:self.device)
        self.wait_for(lambda:self.controller.snapshot()['motor_fresh'] and self.controller.snapshot()['sensor_fresh'])

    def tearDown(self): self.controller.close()

    def wait_for(self,predicate,timeout=2):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if predicate(): return
            time.sleep(0.01)
        self.fail('Condition not reached')

    def command(self,name,parameters=None): return self.controller.submit(name,parameters).result(timeout=4)

    def test_connect_never_arms_or_moves_and_units_are_preserved(self):
        self.assertFalse(any(c in {'ARM','DISARM','RESET'} or c.startswith('JOG') for c in self.device.commands))
        self.assertAlmostEqual(self.controller.snapshot()['magnetic_uT'][0],52)

    def test_position_is_segmented_without_grasp_claim(self):
        self.command('arm'); result=self.command('open')
        jogs=[int(c.split()[1]) for c in self.device.commands if c.startswith('JOG')]
        self.assertEqual(jogs,[100,100,100]); self.assertEqual(result['position'],2600)
        self.assertTrue(result['position_verified']); self.assertFalse(result['grasp_verified'])

    def test_invalid_and_force_commands_never_write(self):
        before=list(self.device.commands)
        for value in (1999,2601,True,2300.5):
            with self.assertRaises(ValueError): self.controller.submit('move',{'position':value})
        with self.assertRaises(PermissionError): self.controller.submit('force',{'force_n':1})
        self.assertFalse(any(c.startswith('JOG') for c in self.device.commands[len(before):]))

    def test_disarmed_or_invalid_sensor_blocks_motion(self):
        with self.assertRaises(PermissionError): self.controller.submit('close')
        self.device.valid=False
        self.wait_for(lambda:not self.controller.snapshot()['sensor_valid'])
        with self.assertRaises(PermissionError): self.controller.submit('arm')

    def test_stale_feedback_blocks_arm(self):
        with self.controller.lock:
            self.controller.motor_time=time.monotonic()-2
            self.assertIn('arm',self.controller.blocks())
            with self.assertRaises(PermissionError): self.controller.submit('arm')

    def test_fault_latched_until_manual_disarm_reset(self):
        self.command('arm'); self.device.fail_motion=True
        with self.assertRaises(RuntimeError): self.command('move',{'position':2400})
        self.assertTrue(self.controller.snapshot()['fault'])
        self.assertIn('STOP',self.device.commands)
        self.command('disarm')
        with self.assertRaises(PermissionError): self.controller.submit('arm')
        self.command('reset'); self.device.fail_motion=False
        self.command('arm')

    def test_stop_cancels_running_motion_without_automatic_release(self):
        self.command('arm'); self.device.delay_motion=True
        moving=self.controller.submit('open')
        self.wait_for(lambda:any(c.startswith('JOG') for c in self.device.commands))
        stopped=self.controller.submit('stop')
        with self.assertRaises(RuntimeError): moving.result(timeout=3)
        self.assertTrue(stopped.result(timeout=3)['success'])
        self.assertTrue(self.device.armed); self.assertNotIn('DISARM',self.device.commands)

    def test_readonly_and_busy_gate(self):
        self.controller.enable_motion=False
        with self.assertRaises(PermissionError): self.controller.submit('arm')
        self.command('disarm')
        self.controller.enable_motion=True; self.command('arm'); self.device.delay_motion=True
        self.controller.submit('open')
        with self.assertRaises(PermissionError): self.controller.submit('close')


class LeaseTests(unittest.TestCase):
    def test_only_current_owner_heartbeat_prevents_expiry(self):
        lease=ControlLease(); lease.reserve('arm','task',now=10)
        lease.keepalive('other',now=11.4)
        self.assertTrue(lease.expired(now=11.6))
        lease.keepalive('task',now=11.4)
        self.assertFalse(lease.expired(now=12))
        self.assertTrue(lease.expired(now=13))
    def test_session_spans_goals_and_emergency_commands_interrupt(self):
        lease=ControlLease(); lease.reserve('arm','task'); lease.complete('arm','task',True)
        lease.reserve('open','task')
        with self.assertRaises(PermissionError): lease.reserve('close','ui')
        lease.reserve('stop','ui'); lease.complete('stop','ui',True)
        self.assertIsNone(lease.owner)
        with self.assertRaises(PermissionError): lease.reserve('move','task')

    def test_failed_arm_releases_claim_and_failed_stop_does_not(self):
        lease=ControlLease(); lease.reserve('arm','ui'); lease.complete('arm','ui',False)
        self.assertIsNone(lease.owner)
        lease.reserve('arm','task'); lease.complete('stop','ui',False)
        self.assertEqual(lease.owner,'task')

    def test_force_never_enables_without_calibration(self):
        for force in (float('nan'),True,-1):
            with self.assertRaises(ValueError): validate('force',{'force_n':force})
        with self.assertRaises(PermissionError): validate('force',{'force_n':0})

import csv
import io
import unittest
from unittest.mock import patch
import motor_sweep as sweep


class FakeSession:
    def __init__(self, fail=False, error=0, drift=0):
        self.position=2300; self.target=2300; self.start=2300; self.fail=fail; self.commands=[]
        self.error=error
        self.drift=drift
    def request(self, command, prefix, timeout=3):
        self.commands.append(command)
        if command=='PING': return '# PING ok=1 mode=0 mode_read_ok=1 feedback_ok=1'
        if command=='STATUS': return f'# MOTOR armed=1 moving=0 fault=0 pos={self.position}'
        if command.startswith('JOG'):
            if self.fail: raise RuntimeError('LIMIT_ERROR')
            self.position+=self.drift
            delta=int(command.split()[1]); self.start=self.position; self.target=self.position+delta
            assert 0<abs(delta)<=100 and 1937<=self.target<=2668
            return f'# MOVE_START start={self.start} target={self.target} delta={delta}'
        return prefix
    def wait(self, prefix, timeout=3):
        if prefix=='# MOTOR': return '# MOTOR configured=1 fault=0 pos=2300'
        if prefix=='# MOTION_SUMMARY':
            self.position=self.target-self.error
            return f'# MOTION_SUMMARY result=done start={self.start} target={self.target} samples=10 peak_abs_load=40 peak_signed_load=-40 elapsed_ms=2000'
        return f'# MOVE_DONE target={self.target} pos={self.position}'
    def dwell(self, seconds): pass


class Tests(unittest.TestCase):
    def writer(self):
        class Writer:
            def writerow(self, row): pass
        return Writer()
    def test_complete_repeated_plan(self):
        session=FakeSession(); rows=[]
        with patch('builtins.print'):
            result=sweep.run(session,3,0.5,rows,self.writer())
        self.assertEqual(result,2300)
        self.assertEqual({r['cycle'] for r in rows},{1,2,3})
        self.assertEqual({r['waypoint'] for r in rows},set(sweep.POSITIONS))
        self.assertEqual({r['direction'] for r in rows},{'open','close'})
        self.assertNotIn('RESET',session.commands)
    def test_first_failure_aborts(self):
        session=FakeSession(fail=True)
        with self.assertRaisesRegex(RuntimeError,'LIMIT_ERROR'):
            sweep.run(session,3,0.5,[],self.writer())
        self.assertEqual(sum(c.startswith('JOG') for c in session.commands),1)
    def test_arrival_tolerance_matches_firmware(self):
        with patch('builtins.print'):
            rows=[]
            sweep.run(FakeSession(error=2),1,0.5,rows,self.writer())
            self.assertTrue(rows)
            self.assertTrue(all(row['error_counts']==-2 for row in rows))
        with self.assertRaisesRegex(RuntimeError,'position verification'):
            sweep.run(FakeSession(error=4),1,0.5,[],self.writer())
    def test_boundaries(self):
        self.assertEqual(sweep.next_step(2300,2600),100)
        self.assertEqual(sweep.next_step(2300,2000),-100)
        self.assertEqual(sweep.next_step(2301,2300),0)
        self.assertEqual(sweep.next_step(2398,2400),0)
        self.assertEqual(sweep.next_step(2303,2300),0)
        self.assertEqual(sweep.next_step(2304,2300),-4)
        for current,target in [(2688,2300),(2300,2700)]:
            with self.assertRaises(RuntimeError): sweep.next_step(current,target)
    def test_live_start_small_drift_allowed_large_rejected(self):
        with patch('builtins.print'):
            rows=[]
            sweep.run(FakeSession(drift=1),1,0.5,rows,self.writer())
            self.assertTrue(rows)
        with self.assertRaisesRegex(RuntimeError,'motion start inconsistent'):
            sweep.run(FakeSession(drift=4),1,0.5,[],self.writer())
    def test_cleanup_still_disarms_after_stop_timeout(self):
        session=sweep.Session(None,io.StringIO()); sent=[]
        session.send=sent.append
        def wait(prefix,timeout,strict):
            if prefix=='# STOP': raise RuntimeError('timeout')
            return '# DISARM_OK'
        session.wait=wait
        self.assertTrue(session.cleanup()); self.assertEqual(sent,['STOP','DISARM'])
    def test_batch_fault_cannot_hide_behind_done(self):
        class Link:
            def write(self,data): pass
            def read(self,size): return b'# MOVE_DONE target=2100 pos=2100\n# FAULT host_timeout\n'
        session=sweep.Session(Link(),io.StringIO())
        with self.assertRaisesRegex(RuntimeError,'FAULT'):
            session.wait('# MOVE_DONE')


if __name__=='__main__': unittest.main()

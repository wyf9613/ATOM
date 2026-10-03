import unittest
from atom_gripper_hardware.framing import LineFramer
from atom_gripper_hardware.protocol import parse_sample
from atom_gripper_hardware.statistics import summarize


class StreamTests(unittest.TestCase):
    def test_fragmented_records_and_overflow_recovery(self):
        framer = LineFramer(4)
        self.assertEqual(framer.feed(b'ab'), [])
        self.assertEqual(framer.feed(b'c\n123456'), [b'abc'])
        self.assertEqual(framer.feed(b'7\nok\n'), [b'ok'])
        self.assertEqual(framer.oversized, 1)

    def test_invalid_excluded_and_missing_sample_counted(self):
        samples = [parse_sample('V1,0,100,20,1,1,2,3'),
                   parse_sample('V1,1,200,20,0,0,0,0'),
                   parse_sample('V1,3,400,20,1,3,4,5')]
        result = summarize(samples)
        self.assertEqual(result['valid'], 2)
        self.assertEqual(result['sequence_gaps'], 1)
        self.assertAlmostEqual(result['x']['mean'], 2)
        self.assertEqual(result['device_rate_hz'], 10)

    def test_wrap_and_restart(self):
        wrap = [parse_sample('V1,4294967295,4294967246,20,1,0,0,0'),
                parse_sample('V1,0,50,20,1,0,0,0')]
        self.assertEqual(summarize(wrap)['resets_or_reordering'], 0)
        restart = [parse_sample('V1,20,2000,20,1,0,0,0'),
                   parse_sample('V1,0,100,20,1,0,0,0')]
        self.assertEqual(summarize(restart)['resets_or_reordering'], 1)

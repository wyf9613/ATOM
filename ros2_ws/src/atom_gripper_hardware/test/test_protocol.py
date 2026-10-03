import unittest
from atom_gripper_hardware.protocol import parse_sample


class ProtocolTests(unittest.TestCase):
    def test_units_and_wrap_boundary(self):
        sample = parse_sample('V1,4294967295,4294967295,12,1,100,-200,0')
        self.assertAlmostEqual(sample.field_tesla[0], 100e-6)
        self.assertAlmostEqual(sample.field_tesla[1], -200e-6)

    def test_invalid_sample_remains_invalid(self):
        self.assertFalse(parse_sample('V1,0,0,12,0,0,0,0').valid)

    def test_reject_bad_records(self):
        for line in ['V2,0,0,12,1,0,0,0', 'V1,0,0,12,1,nan,0,0',
                     'V1,-1,0,12,1,0,0,0', 'V1,0,0,12,2,0,0,0',
                     'V1,0,0,0,1,0,0,0', 'V1,0,0,12,1,0,0', 'x' * 257]:
            with self.subTest(line=line), self.assertRaises(ValueError):
                parse_sample(line)


if __name__ == '__main__':
    unittest.main()

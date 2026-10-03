import unittest
import os
from unittest.mock import patch, MagicMock
from atom_gripper_hardware.serial_connection import open_sensor_port


class ConnectionTests(unittest.TestCase):
    def test_reset_does_not_write_and_purges_transient_queue(self):
        link = MagicMock()
        with patch('atom_gripper_hardware.serial_connection.serial.Serial', return_value=link) as constructor, \
                patch('atom_gripper_hardware.serial_connection.time.sleep') as sleep:
            self.assertIs(open_sensor_port('COM4', reset=True), link)
        constructor.assert_called_once_with(port=None, baudrate=115200, timeout=0,
                                            xonxoff=False, rtscts=False, dsrdtr=False,
                                            **({'exclusive': True} if os.name == 'posix' else {}))
        self.assertEqual(link.reset_input_buffer.call_count, 2)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.15, 0.3])
        link.write.assert_not_called()
        self.assertFalse(link.dtr)
        self.assertFalse(link.rts)

    def test_normal_reopen_does_not_reset(self):
        link = MagicMock()
        with patch('atom_gripper_hardware.serial_connection.serial.Serial', return_value=link), \
                patch('atom_gripper_hardware.serial_connection.time.sleep') as sleep:
            open_sensor_port('COM4')
        self.assertEqual(link.reset_input_buffer.call_count, 1)
        sleep.assert_not_called()
        link.write.assert_not_called()

    def test_failed_open_closes_handle(self):
        link = MagicMock()
        link.open.side_effect = OSError('busy')
        with patch('atom_gripper_hardware.serial_connection.serial.Serial', return_value=link):
            with self.assertRaises(OSError):
                open_sensor_port('COM4')
        link.close.assert_called_once()

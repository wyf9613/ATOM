"""Explicit control-line policy for the current sensor-only ESP32 firmware."""
import time
import os
import serial


def open_sensor_port(port, timeout=0, reset=False):
    link = serial.Serial(port=None, baudrate=115200, timeout=timeout,
                         xonxoff=False, rtscts=False, dsrdtr=False,
                         **({'exclusive': True} if os.name == 'posix' else {}))
    link.dtr = False
    link.rts = False
    link.port = port
    try:
        link.open()
        # A reopened device can have unread data from the previous session.
        link.reset_input_buffer()
        if reset:
            link.rts = True
            time.sleep(0.15)
            link.rts = False
            # Wait for reset-line/USB settling, then discard that transient queue.
            # Sensor telemetry repeats; protocol synchronization follows in caller.
            time.sleep(0.3)
            link.reset_input_buffer()
        return link
    except BaseException:
        link.close()
        raise

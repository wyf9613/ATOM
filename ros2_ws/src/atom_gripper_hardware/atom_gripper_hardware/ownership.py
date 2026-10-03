"""Caller lease across action goals, separate from per-goal execution ownership."""
import time


class ControlLease:
    def __init__(self):
        self.owner = None
        self.generation = 0
        self.seen = 0

    def reserve(self, command, caller, now=None):
        if command in {'stop', 'disarm'}:
            return
        if not caller or len(caller) > 128:
            raise PermissionError('A bounded caller session is required')
        if self.owner is not None and self.owner != caller:
            raise PermissionError('Another session owns gripper control')
        if command in {'open', 'close', 'move'} and self.owner != caller:
            raise PermissionError('Acquire gripper control with ARM first')
        if command == 'arm':
            self.generation += 1
            self.owner = caller
            self.seen = time.monotonic() if now is None else now

    def keepalive(self, caller, now=None):
        if self.owner == caller:
            self.seen = time.monotonic() if now is None else now

    def expired(self, now=None):
        now=time.monotonic() if now is None else now
        return self.owner is not None and now-self.seen>1.5

    def complete(self, command, caller, success):
        if success and (command == 'disarm' or (command == 'stop' and caller != self.owner)):
            self.owner = None
        elif command == 'arm' and not success and self.owner == caller:
            self.owner = None

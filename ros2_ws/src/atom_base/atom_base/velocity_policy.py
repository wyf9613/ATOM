"""Exclusive, expiring command selection. Software interlock, not hardware E-stop."""
import math


class VelocityPolicy:
    def __init__(self, timeout=0.3, scan_timeout=0.5, require_scan=True,
                 max_v=0.15, max_w=0.2):
        self.timeout, self.scan_timeout = timeout, scan_timeout
        self.require_scan, self.max_v, self.max_w = require_scan, max_v, max_w
        self.stopped = True
        self.enabled = False
        self.source = 'nav'
        self.commands = {}
        self.scan_seen = None
        self.obstacle = True

    def stop(self):
        self.stopped, self.enabled = True, False
        self.commands.clear()

    def reset(self):
        self.stopped, self.enabled = False, False
        self.commands.clear()

    def select(self, source):
        if source not in {'nav', 'fine'}:
            raise ValueError('Unknown velocity source')
        self.source = source
        self.enabled = False
        self.commands.clear()

    def enable(self, enabled):
        if enabled and self.stopped:
            return False
        self.commands.clear()
        self.enabled = bool(enabled)
        return True

    def receive(self, source, v, w, now):
        if source not in {'nav', 'fine'} or not all(math.isfinite(x) for x in (v, w, now)):
            self.stop()
            return
        # Inactive publishers cannot leave a command for a later owner.
        if self.enabled and not self.stopped and source == self.source:
            self.commands[source] = (now, max(-self.max_v, min(self.max_v, v)),
                                     max(-self.max_w, min(self.max_w, w)))

    def output(self, now):
        if self.stopped or not self.enabled:
            return 0.0, 0.0
        if self.require_scan and (self.scan_seen is None or not 0 <= now-self.scan_seen <= self.scan_timeout or self.obstacle):
            return 0.0, 0.0
        seen, v, w = self.commands.get(self.source, (-math.inf, 0., 0.))
        return (v, w) if 0 <= now-seen <= self.timeout else (0., 0.)

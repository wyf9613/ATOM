"""Bounded newline framing, including fragmented USB reads."""
class LineFramer:
    def __init__(self, limit=256):
        self.limit = limit
        self.buffer = bytearray()
        self.discarding = False
        self.oversized = 0

    def feed(self, data):
        lines = []
        for byte in data:
            if byte == 10:
                if not self.discarding:
                    lines.append(bytes(self.buffer))
                self.buffer.clear()
                self.discarding = False
            elif not self.discarding:
                self.buffer.append(byte)
                if len(self.buffer) > self.limit:
                    self.buffer.clear()
                    self.discarding = True
                    self.oversized += 1
        return lines

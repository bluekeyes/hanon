import time

from hanon.note import Note


class RecordPort(object):
    def __init__(self, port, channel=0, idle_time=5):
        self.port = port
        self.channel = channel
        self.idle_time = idle_time

        self._last_event = 0

    def flush(self):
        while self.port.receive(block=False):
            pass

    def receive(self, block=True):
        while True:
            msg = self.port.receive(block=block)
            if msg and msg.channel == self.channel:
                msg.time = time.perf_counter()
                self._last_event = msg.time
                return msg
            elif not block:
                return None

    def receive_first(self, type=None):
        while True:
            msg = self.receive()
            if msg.type == type or type is None:
                return msg

    def is_idle(self):
        return time.perf_counter() - self._last_event > self.idle_time

    def __iter__(self):
        msg = self.receive_first(type='note_on')
        start_time = msg.time

        msg.time = 0
        yield msg

        while not self.is_idle():
            msg = self.receive(block=False)
            if not msg:
                continue

            if msg.type == 'note_on' or msg.type == 'note_off':
                msg.time -= start_time
                yield msg


def oneshot_record(port):
    notes = []
    active_notes = {}

    port.flush()
    for msg in port:
        if msg.type == 'note_on':
            active_notes[msg.note] = msg
        elif msg.type == 'note_off':
            on_msg = active_notes.pop(msg.note)
            notes.append(Note.from_midi(on_msg, msg))

    return sorted(notes, key=lambda n: n.time)

from itertools import accumulate


NOTE_NAMES = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')


class Scale(object):
    def __init__(self, root, steps):
        self.root = root
        self.steps = steps
        self.offsets = [0] + list(accumulate(steps))

    def transpose(self, amount):
        return Scale(self.root + amount, self.steps)

    def __getitem__(self, index):
        octave, note = divmod(index, len(self.steps))
        return self.root + 12 * octave + self.offsets[note]


class Note(object):
    @classmethod
    def from_midi(cls, note_on, note_off):
        return cls(
            time=note_on.time,
            duration=note_off.time - note_on.time,
            note=note_on.note,
            velocity=note_on.velocity)

    def __init__(self, time, duration, note, velocity=64, finger=None):
        self.time = time
        self.duration = duration
        self.note = note
        self.velocity = velocity
        self.finger = finger

        self.name = NOTE_NAMES[self.note % 12]
        self.octave = self.note // 12

    def is_double(self, other):
        return self.note == other.note and abs(self.time - other.time) < self.duration

    def __str__(self):
        return '{0.time:.4f} {0.name}{0.octave} {0.velocity} [{0.duration:.4f}]'.format(self)


class NoteMatch(object):
    def __init__(self, expected, actual=None):
        self.expected = expected
        self.actual = actual

    def finger(self):
        return self.expected.finger

    def is_match(self):
        return self.actual is not None

    def delay(self):
        return self.actual.time - self.expected.time

    def space(self):
        return self.expected.duration - self.actual.duration

    def __str__(self):
        return 'NoteMatch({} >< {})'.format(self.expected, self.actual)

#!/usr/bin/env python

import json
import mido
import time

from itertools import accumulate
from statistics import mean, pvariance

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def prompt_interfaces(interfaces):
    print_interfaces(interfaces)
    print()

    while True:
        selection = input('Selected interface [1]: ')
        if not selection:
            return interfaces[0]

        try:
            index = int(selection) - 1
            if 0 <= index < len(interfaces):
                return interfaces[index]
        except ValueError:
            pass

def print_interfaces(interfaces):
    print('Available interfaces:')
    for i, iface in enumerate(interfaces):
        print('  [{}]: {}'.format(i + 1, iface))


def load_exercises():
    def as_exercise(obj):
        if 'scale' in obj and 'patterns' in obj:
            return Exercise(SCALES[obj['scale']], obj['patterns'])
        return obj

    with open('exercises.json', 'r') as f:
        return json.load(f, object_hook=as_exercise)


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


SCALES = {
    'Cmaj': Scale(0, [2, 2, 1, 2, 2, 2, 1])
}


class Exercise(object):
    def __init__(self, scale, patterns, octave=4, bpm=108):
        self.scale = scale
        self.patterns = patterns
        self.bpm = bpm
        self.octave = octave

    def __iter__(self):
        time = 0
        duration = self.note_duration
        scale = self.scale.transpose(12 * self.octave)

        for pattern in self.patterns:
            base_step = pattern['start']
            notes_fingers = list(zip(
                    pattern['notes'],
                    pattern['fingers']['left'],
                    pattern['fingers']['right']))

            for bar in range(pattern['bars']):
                current_step = base_step + pattern['delta'] * bar
                for step_delta, lf, rf in notes_fingers:
                    current_step += step_delta
                    note_num = scale[current_step]

                    lnote = Note(time, duration, note_num - 12, finger=lf)
                    rnote = Note(time, duration, note_num, finger=rf)
                    time += duration

                    yield (lnote, rnote)

    @property
    def note_duration(self):
        return (60 / self.bpm) / 4

    def match(self, notes):
        matches = [(NoteMatch(ln), NoteMatch(rn)) for ln, rn in self]
        extras = []

        for note in sorted(notes, key=lambda n: n.time):
            bucket = note.time // self.note_duration
            start = int(max(0, bucket - 2))
            end = int(min(len(matches), bucket + 3))

            matched = False
            for match_pair in matches[start:end]:
                for match in match_pair:
                    if match.expected.is_double(note):
                        match.actual = note
                        matched = True

            if not matched:
                extras.append(note)

        return (matches, extras)


class NoteMatch(object):
    def __init__(self, expected, actual=None):
        self.expected = expected
        self.actual = actual

    def __str__(self):
        return 'NoteMatch({} >< {})'.format(self.expected, self.actual)


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
        return '{0.time:.4f} {0.name}{0.octave} {0.velocity} [{0.duration:.3f}]'.format(self)


class RecordPort(object):
    def __init__(self, port, idle_time=5):
        self.port = port
        self.idle_time = idle_time

        self._last_event = 0

    def receive(self, block=True):
        msg = self.port.receive(block=block)
        if msg:
            msg.time = time.perf_counter()
            self._last_event = msg.time
        return msg

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

    for msg in port:
        if msg.type == 'note_on':
            active_notes[msg.note] = msg
        elif msg.type == 'note_off':
            on_msg = active_notes.pop(msg.note)
            notes.append(Note.from_midi(on_msg, msg))

    return sorted(notes, key=lambda n: n.time)


def pair_stats(pairs):
    stats = []

    expected_time = 0
    for left, right in pairs:
        stats.append({
            'spread': right.time - left.time,
            'r_offset': right.time - expected_time,
            'l_offset': left.time - expected_time
        })
        expected_time += BEAT_TIME/4

    return stats


if __name__ == '__main__':
    # portmidi seems to have weird buffering problems
    mido.set_backend('mido.backends.rtmidi')

    exercises = load_exercises()
    interfaces = mido.get_input_names()

    print('---')
    iface = prompt_interfaces(interfaces)

    with mido.open_input(iface) as port:
        print('recording...', end=' ')
        notes = oneshot_record(RecordPort(port))
        print('done ({} notes)'.format(len(notes)))

    matches, extras = exercises[0].match(notes)

    print()
    print('{} unmatched notes'.format(len(extras)))
    for note in extras:
        print('  {}'.format(note))

    print()
    for match in matches:
        print('L: {0}, R: {1}'.format(*match))

    # median, avg, and min/max velocities
    #  - total
    #  - per exercise
    #  - per finger
    # avg, min/max spread between left+right
    #  - total
    #  - per exercise
    #  - per finger
    # median, avg, min/max offset from beat
    #  - total
    #  - per hand
    #  - per exercise
    #  - per finger
    # median, avg, min/max duration
    #  - total
    #  - per exercise
    #  - per finger

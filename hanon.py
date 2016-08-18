#!/usr/bin/env python

import json
import mido
import time

from itertools import accumulate, chain
from statistics import mean, pvariance, median

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

        notes = sorted(notes, key=lambda n: n.time)
        for i, note in enumerate(notes):
            bucket = note.time // self.note_duration
            start = int(max(0, bucket - 2))
            end = int(min(len(matches), bucket + 3))

            if bucket >= len(matches):
                break

            matched = False
            for match_pair in matches[start:end]:
                for match in match_pair:
                    if match.expected.is_double(note):
                        match.actual = note
                        matched = True

            if not matched:
                extras.append(note)

        return (matches, extras, notes[i:])


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


class RecordPort(object):
    def __init__(self, port, channel=0, idle_time=5):
        self.port = port
        self.channel = channel
        self.idle_time = idle_time

        self._last_event = 0

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

    for msg in port:
        if msg.type == 'note_on':
            active_notes[msg.note] = msg
        elif msg.type == 'note_off':
            on_msg = active_notes.pop(msg.note)
            notes.append(Note.from_midi(on_msg, msg))

    return sorted(notes, key=lambda n: n.time)


def group_by_finger(hand_matches):
    groups = {}
    for m in hand_matches:
        groups.setdefault(m.finger(), []).append(m)
    return groups


def split_filter_matches(matches):
    left, right = zip(*matches)
    return ([m for m in left if m.is_match()],
            [m for m in right if m.is_match()])


def compute_delay(matches):
    delays = [m.delay() for m in matches]
    return {
        'avg': mean(delays),
        'med': median(delays)
    }


def compute_velocity(matches):
    velocities = [m.actual.velocity for m in matches]
    return {
        'avg': mean(velocities),
        'med': median(velocities)
    }


class StatPrinter(object):
    def __init__(self, raw_matches):
        left, right = split_filter_matches(raw_matches)
        self.all = list(chain(left, right))

        self.left = left
        self.left_fingers = group_by_finger(left)

        self.right = right
        self.right_fingers = group_by_finger(right)

    def print(self, name, computer):
        print('== {} =='.format(name))
        self._print_stats(computer(self.all))

        for hand in ('left', 'right'):
            hand_matches = getattr(self, hand)
            self._print_stats(computer(hand_matches), header='-- {} --'.format(hand), indent=2)

            matches_by_finger = getattr(self, '{}_fingers'.format(hand))
            for f, matches in (matches_by_finger.items()):
                self._print_stats(computer(matches), header='> {}'.format(f), indent=4)

    def _print_stats(self, stats, header=None, indent=0):
        ispace = ' ' * indent
        if header is not None:
            print('{}{}'.format(ispace, header))
        for name, value in sorted(stats.items()):
            print('{}{}: {:.4f}'.format(ispace, name, value))


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

    matches, extras, notes = exercises[0].match(notes)

    print()
    print('{} unmatched notes'.format(len(extras)))
    for note in extras:
        print('  {}'.format(note))

    printer = StatPrinter(matches)

    print()
    printer.print('delay', compute_delay)

    print()
    printer.print('velocity', compute_velocity)

    # avg, min/max spread between left+right
    #  - total
    #  - per exercise
    #  - per finger
    # median, avg, min/max duration
    #  - total
    #  - per exercise
    #  - per finger

#!/usr/bin/env python

import time
import mido
import json

from itertools import accumulate
from statistics import mean, pvariance

TEMPO = 108
BEAT_TIME = 60 / TEMPO

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
    def __init__(self, scale, patterns):
        self.scale = scale
        self.patterns = patterns

    def notes(self, octave=4):
        scale = self.scale.transpose(12 * octave)
        for pattern in self.patterns:
            base = pattern['start']
            for bar in range(pattern['bars']):
                current = base + pattern['delta'] * bar
                for delta in pattern['notes']:
                    current += delta
                    yield scale[current]

    def fingers(self, hand='right'):
        for pattern in self.patterns:
            for bar in range(pattern['bars']):
                for finger in pattern['fingers'][hand]:
                    yield finger


class Note(object):
    def __init__(self, note_on, note_off):
        self.time = note_on.time
        self.duration = note_off.time - note_on.time
        self.note = note_on.note
        self.velocity = note_on.velocity

        self.name = NOTE_NAMES[self.note % 12]
        self.octave = self.note // 12

    def is_pair(self, other, window=BEAT_TIME/4):
        return self.name == other.name and abs(self.time - other.time) < window

    def __str__(self):
        return '{0.time:.5f} {0.name}{0.octave} {0.velocity} [{0.duration:.3f}]'.format(self)


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
            notes.append(Note(on_msg, msg))

    return sorted(notes, key=lambda n: n.time)


def pair_notes(notes):
    pairs = []
    outliers = []

    paired = set()
    for i, note in enumerate(notes):
        if note in paired:
            continue

        try:
            other = next(n for n in notes[i+1:] if n not in paired and note.is_pair(n))
            paired.add(other)
            if note.note < other.note:
                pairs.append((note, other))
            else:
                pairs.append((other, other))
        except StopIteration:
            outliers.append(note)

    return (pairs, outliers)


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
    interfaces = mido.get_input_names()

    print('---')
    iface = prompt_interfaces(interfaces)

    with mido.open_input(iface) as port:
        print('recording...', end=' ')
        notes = oneshot_record(RecordPort(port))
        print('done ({} notes)'.format(len(notes)))

    pairs, outliers = pair_notes(notes)
    stats = pair_stats(pairs)

    print()
    print('{} unpaired notes'.format(len(outliers)))
    for note in outliers:
        print('  {}'.format(note))

    print('---')
    print('avg spread: {:.4f}'.format(mean(s['spread'] for s in stats)))
    print('avg right offset: {:.4f}'.format(mean(s['r_offset'] for s in stats)))
    print('avg left offset: {:.4f}'.format(mean(s['l_offset'] for s in stats)))

    print('---')
    print('avg velocity: {:.2f}'.format(mean(n.velocity for n in notes)))
    print('velocity variance: {:.2f}'.format(pvariance(n.velocity for n in notes)))

    print('---')
    print('avg duration: {:.4f} (target = {:.4f})'.format(mean(n.duration for n in notes), BEAT_TIME/4))
    print('duration variance: {:.4f}'.format(pvariance(n.duration for n in notes)))

#!/usr/bin/env python

import time
import mido

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
            if 0 < index < len(interfaces):
                return interfaces[index]
        except ValueError:
            pass

def print_interfaces(interfaces):
    print('Available interfaces:')
    for i, iface in enumerate(interfaces):
        print('  [{}]: {}'.format(i + 1, iface))


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
    used = set()

    for i, note in enumerate(notes):
        if i in used:
            continue

        used.add(i)
        for j, other_note in enumerate(notes[i+1:], start=i+1):
            if j in used:
                continue

            if note.is_pair(other_note):
                used.add(j)
                break
            else:
                other_note = None

        if other_note is not None:
            if note.note < other_note.note:
                pairs.append((note, other_note))
            else:
                pairs.append((other_note, note))
        else:
            print('dropped {}, no pair'.format(note))


    return pairs


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

    pairs = pair_notes(notes)
    stats = pair_stats(pairs)

    print()
    print('avg spread: {}'.format(mean(s['spread'] for s in stats)))
    print('avg right offset: {}'.format(mean(s['r_offset'] for s in stats)))
    print('avg left offset: {}'.format(mean(s['l_offset'] for s in stats)))
    print('---')

    print('avg velocity: {}'.format(mean(n.velocity for n in notes)))
    print('velocity variance: {}'.format(pvariance(n.velocity for n in notes)))
    print('---')

    print('avg duration: {} (target = {})'.format(mean(n.duration for n in notes), BEAT_TIME/4))
    print('duration variance: {}'.format(pvariance(n.duration for n in notes)))

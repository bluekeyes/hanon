#!/usr/bin/env python

import time
import mido

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
    def __init__(self, note_on, note_off, start_time=0):
        self.time = note_on.time - start_time
        self.duration = note_off.time - note_on.time
        self.note = note_on.note
        self.velocity = note_on.velocity

        self.name = NOTE_NAMES[self.note % 12]
        self.octave = self.note // 12


    def is_pair(self, other, window=BEAT_TIME/8):
        return self.name == other.name and abs(self.time - other.time) < window

    def __lt__(self, other):
        return self.time < other.time

    def __str__(self):
        return '{0.time:.5f} {0.name}{0.octave} {0.velocity} [{0.duration:.3f}]'.format(self)


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

        pairs.append((note, other_note))

    return pairs



if __name__ == '__main__':
    interfaces = mido.get_input_names()

    print('---')
    iface = prompt_interfaces(interfaces)

    notes = []

    with mido.open_input(iface) as port:
        msg = port.receive()

        print('recording...', end=' ')
        msg.time = time.perf_counter()
        start_time = msg.time

        active_notes = {}

        # TODO: this assumes first event is note_on
        active_notes[msg.note] = msg

        while True:
            for msg in port.iter_pending():
                msg.time = time.perf_counter()
                if msg.type == 'note_on':
                    active_notes[msg.note] = msg
                elif msg.type == 'note_off':
                    note_on = active_notes.pop(msg.note)
                    notes.append(Note(note_on, msg, start_time))

            if time.perf_counter() - msg.time > 5:
                print('done')
                break

    notes = sorted(notes)
    pairs = pair_notes(notes)

    for pair in pairs:
        print('{} - {}'.format(*pair))

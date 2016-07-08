#!/usr/bin/env python

import time
import mido


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






if __name__ == '__main__':
    interfaces = mido.get_input_names()

    print('---')
    iface = prompt_interfaces(interfaces)

    # list of (time, duration, note, velocity)
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
                    notes.append((
                        note_on.time - start_time,
                        msg.time - note_on.time,
                        note_on.note,
                        note_on.velocity))

            if time.perf_counter() - msg.time > 5:
                print('done')
                break

    for note in sorted(notes):
        print(note)

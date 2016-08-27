import argparse
import glob
import os
import pickle

import mido

from datetime import date

from hanon.record import oneshot_record, RecordPort
from hanon.exercise import load_exercises
from hanon.stats import compute_delay, compute_velocity, StatPrinter


RECORDING_PATTERN = 'recording-{:%Y-%m-%d}.{}.pickle'


def prompt_interfaces(interfaces):
    print('Available interfaces:')
    print_interfaces(interfaces, number=True)
    print()

    while True:
        selection = input('Selected interface [1]: ')
        if not selection:
            return interfaces[0]

        try:
            index = int(selection) - 1
        except ValueError:
            index = -1

        if 0 <= index < len(interfaces):
            return interfaces[index]


def print_interfaces(interfaces, number=False):
    for i, iface in enumerate(interfaces):
        if number:
            print('  [{}]: {}'.format(i + 1, iface))
        else:
            print(iface)


def next_recording_path(directory):
    filename = RECORDING_PATTERN.format(date.toay(), '*')
    recordings = glob.glob(os.path.join(directory, filename))
    if len(recordings) == 0:
        next_id = 0
    else:
        last_recording = recordings[-1]
        next_id = int(last_recording.split('.')[1]) + 1

    return os.path.join(directory, RECORDING_PATTERN.format(date.today(), next_id))


def create_parser():
    parser = argparse.ArgumentParser(
            prog='hanon',
            description='Record and grade Hanon exercises',
            epilog="""
            With no arguments, the program promts for an interface, then waits
            for the first "Note On" event on that interface. It then records
            all events until a period of 5 seconds with no events. The
            recording is saved to the default output directory and statistics
            about the performance are printed to the console.
            """)

    parser.add_argument('-e', '--exercises', help='comma-separated list of expected excercises')

    parser.add_argument('-i', '--interface', help='MIDI interface to record')
    parser.add_argument('-c', '--channel', help='MIDI channel to record', default=0)
    parser.add_argument('-t', '--time', help='Seconds to wait for events before stopping', default=5)

    parser.add_argument('-d', '--recording-dir', help='path to recordings directory', metavar='DIR', default='./recordings')

    parser.add_argument('-a', '--analyze', help='analyze a saved recording', metavar='PATH')
    parser.add_argument('-l', '--list', action='store_true', help='list MIDI interfaces and exit')

    return parser


class CliConfigError(Exception):
    pass


def main():
    args = create_parser().parse_args()

    interfaces = mido.get_input_names()
    if args.list:
        return print_interfaces(interfaces)

    if args.analyze:
        # TODO: call analyze here
        return 0

    interface = args.interface or prompt_interfaces(interfaces)
    if interface not in interfaces:
        raise CliConfigError('interface "{}" does not exist'.format(interface))

    with mido.open_input(interface) as port:
        record_port = RecordPort(port, channel=args.channel, idle_time=args.time)
        notes = oneshot_record(record_port)
        print('recorded {} notes'.format(len(notes)))

    recording = next_recording_path(args.recording_dir)
    with open(recording, 'wb') as f:
        pickle.dump(notes, f)

    elapsed = 0
    exercises = load_exercises(os.path.join(os.path.dirname(__file__), 'exercises.json'))
    for i, exercise in enumerate(exercises):
        print()
        print('Execise #{}'.format(i + 1))
        print()

        exercise = exercise.shift(elapsed)
        elapsed += exercise.duration

        matches, extras, notes = exercise.match(notes)

        print('{} unmatched notes'.format(len(extras)))
        for note in extras:
            print('  {}'.format(note))

        printer = StatPrinter(matches)

        print()
        printer.print('delay', compute_delay)

        print()
        printer.print('velocity', compute_velocity)

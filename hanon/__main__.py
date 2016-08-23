import os
import mido

from hanon.record import oneshot_record, RecordPort
from hanon.exercise import load_exercises
from hanon.stats import compute_delay, compute_velocity, StatPrinter


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


# portmidi seems to have weird buffering problems
mido.set_backend('mido.backends.rtmidi')

exercises = load_exercises(os.path.join(os.path.dirname(__file__), 'exercises.json'))
interfaces = mido.get_input_names()

print('---')
iface = prompt_interfaces(interfaces)

with mido.open_input(iface) as port:
    print('recording...', end=' ')
    notes = oneshot_record(RecordPort(port))
    print('done ({} notes)'.format(len(notes)))

with open('recording.pickle', 'wb') as f:
    import pickle
    pickle.dump(notes, f)

# with open('recording.pickle', 'rb') as f:
#     import pickle
#     notes = pickle.load(f)

elapsed = 0
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

# avg, min/max spread between left+right
#  - total
#  - per exercise
#  - per finger
# median, avg, min/max duration
#  - total
#  - per exercise
#  - per finger

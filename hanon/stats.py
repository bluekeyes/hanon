from itertools import chain
from statistics import mean, median


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

import sys

from statistics import mean


class StatPrinter(object):
    def __init__(self, exercise, file=sys.stdout):
        self.exercise = exercise
        self.file = file

    def print_stats(self, graph=True):
        avg_delay = mean(m.delay() for m in self.exercise.all())
        avg_left_delay = mean(m.delay() for m in self.exercise.filter('left'))
        avg_right_delay = mean(m.delay() for m in self.exercise.filter('right'))

        self._print('extra notes: {}, missed notes: {}',
                    len(self.exercise.extras),
                    len(list(self.exercise.filter(match=False))))

        self._print('avg delay: {:.2f} (left: {:.2f}, right: {:.2f})',
                    1000 * avg_delay, 1000 * avg_left_delay, 1000 * avg_right_delay)

        self._print_line()
        if graph:
            self._graph_by_finger(
                    'avg delay by finger',
                    lambda matches: 1000 * mean(m.delay() for m in matches))

            self._graph_by_finger(
                    'avg velocity by finger',
                    lambda matches: mean(m.actual.velocity for m in matches))

    def _graph_by_finger(self, label, compute):
        for hand in ('left', 'right'):
            fingers = self.exercise.fingers(hand)
            data = [(str(f), compute(matches)) for f, matches in fingers.items()]

            self._print_graph('{} ({})'.format(label, hand), data)
            self._print_line()

    def _print_graph(self, title, data):
        limits = {}
        for label, value in data:
            limits['min_value'] = min(value, limits.get('min_value', 0))
            limits['max_value'] = max(value, limits.get('max_value', 0))
            limits['label_len'] = max(len(label), limits.get('label_len', 0))
            limits['value_len'] = max(len('{: .2f}'.format(value)), limits.get('value_len', 0))

        width = 70
        if limits['min_value'] < 0:
            spread = limits['max_value'] - limits['min_value']
            zero_point = int((abs(limits['min_value']) / spread) * width)
        else:
            zero_point = 0

        def get_bar_parts(value):
            if value < 0:
                part = int(zero_point * (value / limits['min_value']))
                return (' ' * (zero_point - part), '▬' * part, '│')
            else:
                part = int((width - zero_point - 1) * (value / limits['max_value']))
                return (' ' * zero_point, '│', '▬' * part)

        self._print(title)
        self._print('─' * (width + limits['label_len'] + limits['value_len'] + 2))

        line = '{{:{}}} {{: {}.2f}} {{}}'.format(limits['label_len'], limits['value_len'])
        for label, value in data:
            bar = ''.join(get_bar_parts(value))
            self._print(line, label, value, bar)

    def _print(self, pattern, *args, **kwargs):
        if len(args) == 0 and len(kwargs) == 0:
            print(pattern, file=self.file)
        else:
            print(pattern.format(*args, **kwargs), file=self.file)

    def _print_line(self):
        print(file=self.file)

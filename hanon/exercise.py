import json

from itertools import chain

from hanon.note import Note, NoteMatch, Scale


SCALES = {
    'Cmaj': Scale(0, [2, 2, 1, 2, 2, 2, 1])
}


def load_exercises(path, bpm):
    def as_exercise(obj):
        if 'scale' in obj and 'patterns' in obj:
            return Exercise(SCALES[obj['scale']], obj['patterns'], bpm=bpm)
        return obj

    with open(path, 'r') as f:
        return json.load(f, object_hook=as_exercise)


def match_exercises(notes, exercises):
    results = []

    elapsed = 0
    for exercise in exercises:
        exercise = exercise.shift(elapsed)
        elapsed += exercise.duration

        matched, notes = exercise.match(notes)
        results.append(matched)

    return results


class Exercise:
    def __init__(self, scale, patterns, start=0, octave=4, bpm=108):
        self.scale = scale
        self.patterns = patterns

        self.start = start
        self.octave = octave
        self.bpm = bpm

    @property
    def note_duration(self):
        return (60 / self.bpm) / 4

    @property
    def duration(self):
        return self.note_duration * len(self)

    def __len__(self):
        return sum(len(p['notes']) * p['bars'] for p in self.patterns)

    def __iter__(self):
        time = self.start
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

    def shift(self, delta):
        return Exercise(self.scale, self.patterns, self.start + delta, self.octave, self.bpm)

    def match(self, notes):
        matches = [(NoteMatch(ln), NoteMatch(rn)) for ln, rn in self]
        extras = []

        def find_match(note, start, end):
            for match_pair in matches[start:end]:
                for match in match_pair:
                    if match.expected.is_double(note):
                        match.actual = note
                        return True
            return False

        notes = sorted(notes, key=lambda n: n.time)
        for i, note in enumerate(notes):
            bucket = (note.time - self.start) // self.note_duration
            start = int(max(0, bucket - 2))
            end = int(min(len(matches), bucket + 3))

            if bucket >= len(matches):
                break

            if not find_match(note, start, end):
                extras.append(note)

        return (MatchedExercise(self, matches, extras), notes[i:])


class MatchedExercise:
    def __init__(self, exercise, matches, extras):
        self.exercise = exercise
        self.matches = matches
        self.extras = extras

    def all(self):
        """Returns an iterator over all matches."""
        return self.filter()

    def fingers(self, hand=None):
        fingers = {}
        for m in self.filter(hand=hand):
            fingers.setdefault(m.finger(), []).append(m)
        return fingers

    def filter(self, hand=None, fingers=(1, 2, 3, 4, 5)):
        if hand == 'left':
            matches = (m[0] for m in self.matches)
        elif hand == 'right':
            matches = (m[1] for m in self.matches)
        else:
            matches = chain.from_iterable(self.matches)

        fingers = set(fingers)
        return (m for m in matches if m.is_match() and m.finger() in fingers)

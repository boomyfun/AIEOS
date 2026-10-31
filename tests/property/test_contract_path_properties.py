"""Property tests of aieos_bootstrap.contract_path (task TASK-107, AC6): combinations and ids generated with fixed seeds, at most
50 cases each; standard library only. Each test names its criteria in its own docstring."""

import ast
import pathlib
import random
import re
import unittest

from aieos_bootstrap import contract_path as cp
from aieos_bootstrap import writer

SIDES = ('present', 'absent', 'refused')
CASES = 50


def expected(state, docs):
    """The table of the nine pairs, written out again here and not taken from the module."""
    if state == 'refused':
        return ('refused', 'state')
    if docs == 'refused':
        return ('refused', 'docs')
    if state == 'present' and docs == 'present':
        return ('both', None)
    if state == 'present':
        return ('read', 'state')
    if docs == 'present':
        return ('read', 'docs')
    return ('absent', None)


def other_task_ids(text):
    """The qualified AC ids of tasks other than TASK-107 in text, with every run of whitespace collapsed."""
    return re.findall(r'TASK-(?!107 )[0-9]+ AC[0-9]+', ' '.join(text.split()))


class AC6Properties(unittest.TestCase):

    def test_random_combinations_give_the_table(self):
        """TASK-107 AC1 and AC6: random pairs of sides, drawn with a fixed seed, give the table of the nine pairs; the answer
        is a pair of the four words and a side word or None."""
        rng = random.Random(107)
        for _ in range(CASES):
            state, docs = rng.choice(SIDES), rng.choice(SIDES)
            with self.subTest(state=state, docs=docs):
                got = cp.decide(state, docs)
                self.assertEqual(got, expected(state, docs))
                self.assertIn(got[0], ('read', 'both', 'absent', 'refused'))
                self.assertIn(got[1], ('state', 'docs', None))

    def test_a_refused_state_side_never_falls_back(self):
        """TASK-107 AC1 and AC6: whatever the docs side is, a refused state side never gives a read of docs, and a refusal on
        either side never gives a read at all."""
        rng = random.Random(1070)
        state_refused = any_refused = 0
        for _ in range(CASES):
            state, docs = rng.choice(SIDES), rng.choice(SIDES)
            what, side = cp.decide(state, docs)
            with self.subTest(state=state, docs=docs):
                if state == 'refused':
                    state_refused += 1
                    self.assertEqual((what, side), ('refused', 'state'))
                if 'refused' in (state, docs):
                    any_refused += 1
                    self.assertEqual(what, 'refused')
        self.assertGreater(state_refused, 0)
        self.assertGreater(any_refused, state_refused)

    def test_the_answer_depends_on_the_pair_only(self):
        """TASK-107 AC1 and AC6: the same pair gives the same answer each time, and the answer for a pair is not changed by
        deciding other pairs before it."""
        rng = random.Random(10700)
        first = {(s, d): cp.decide(s, d) for s in SIDES for d in SIDES}
        for _ in range(CASES):
            state, docs = rng.choice(SIDES), rng.choice(SIDES)
            with self.subTest(state=state, docs=docs):
                self.assertEqual(cp.decide(state, docs), first[(state, docs)])

    def test_candidates_of_random_ids(self):
        """TASK-107 AC1 and AC6: for a random id of the form TASK- and digits the two places are the state directory and docs,
        in that order, each with 'tasks' and the id's file name; any other id raises ValueError."""
        rng = random.Random(107000)
        for _ in range(CASES):
            task = 'TASK-%d' % rng.randint(0, 99999)
            with self.subTest(task=task):
                self.assertEqual(cp.candidates(task), ((writer.STATE_DIR, 'tasks', task + '.yaml'),
                                                       ('docs', 'tasks', task + '.yaml')))
        pieces = ['TASK', 'TASK-', '-', '1', '07', 'x', ' ', '\n', '١', '/']
        for _ in range(CASES):
            bad = ''.join(rng.choice(pieces) for _ in range(rng.randint(0, 6)))
            if re.fullmatch(r'TASK-[0-9]+', bad):
                continue
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    cp.candidates(bad)

    def test_these_tests_name_their_criteria(self):
        """TASK-107 AC6: every test function of this module names "TASK-107 ACn" in its own docstring and no other task's AC
        in qualified form; other_task_ids flags other tasks' qualified AC ids across a line break and not TASK-107's."""
        self.assertEqual(other_task_ids('TASK-107 AC1'), [])
        self.assertEqual(other_task_ids('TASK-106\n AC1'), ['TASK-106 AC1'])
        tree = ast.parse(pathlib.Path(__file__).read_bytes().decode('utf-8'))
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test')]:
            doc = ast.get_docstring(fn) or ''
            with self.subTest(test=fn.name):
                self.assertTrue(re.findall(r'TASK-107 AC[0-9]+', ' '.join(doc.split())))
                self.assertEqual(other_task_ids(doc), [])


if __name__ == '__main__':
    unittest.main()

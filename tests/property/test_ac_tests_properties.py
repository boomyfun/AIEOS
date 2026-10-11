"""Property tests of aieos_bootstrap.ac_tests (task TASK-022), standard library only, with fixed seeds.

For random well-formed inputs: every criterion of the G2 tests gate is either named by a counting test or reported
untested, never both; adding a test whose docstring names every criterion qualified by the task leaves no untested
finding; the result does not depend on the order of the tests mapping; and a record is returned exactly when there
are findings, in the form of specification 2 section 6.2. Each test names its criteria in its own docstring."""

import random
import unittest

from aieos_bootstrap import ac_tests, records

SEEDS = (1, 2, 3, 5, 8, 13, 21, 34)
ROUNDS = 30
TASKS = ('TASK-097', 'TASK-098', 'TASK-099')


def random_input(rng):
    task = rng.choice(TASKS)
    acs = ['AC%d' % n for n in rng.sample(range(1, 15), rng.randint(0, 6))]
    g2 = rng.sample(acs, rng.randint(0, len(acs)))
    c = {'acceptance_criteria': [{a: 'text ' + a} for a in acs],
         'verification_plan': [{'gate': 'G0', 'check': 'scope'}, {'gate': 'G2', 'check': 'tests', 'args': g2}],
         'constitution': ['INV-001']}
    paths = ['tests/unit/test_%d.py' % k for k in range(rng.randint(1, 4))]
    tests = {}
    for p in paths:
        funcs = []
        for k in range(rng.randint(0, 4)):
            words = []
            for _ in range(rng.randint(0, 3)):
                ac = 'AC%d' % rng.randint(1, 15)
                words.append(rng.choice([ac, rng.choice(TASKS) + ' ' + ac, 'TASK-096 ' + ac, 'note']))
            doc = ' '.join(words)
            name = 'test_%d' % k if rng.random() < 0.7 else 'test_ac%d_%d' % (rng.randint(1, 15), k)
            funcs.append('def %s():\n    """%s"""\n' % (name, doc) if doc else 'def %s():\n    pass\n' % name)
        tests[p] = '\n\n'.join(funcs) + '\n'
    ws = {t: rng.sample(paths, rng.randint(0, len(paths))) for t in TASKS}
    return task, c, tests, ws


def g2_of(c):
    out = []
    for gate in c['verification_plan']:
        if gate['gate'] == 'G2' and gate['check'] == 'tests':
            out += [a for a in gate.get('args', []) if a not in out]
    return out


class Properties(unittest.TestCase):

    def test_named_or_untested_never_both(self):
        """TASK-022 AC3 and TASK-022 AC12: each G2 tests criterion is named by a counting test or reported untested, never
        both, and nothing else is reported."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                task, c, tests, ws = random_input(rng)
                out = ac_tests.listing(task, c, tests, ws)
                untested = [f['ref'] for f in out['findings']]
                self.assertEqual({f['kind'] for f in out['findings']} - {'untested'}, set())
                for ac in g2_of(c):
                    self.assertNotEqual(bool(out['named'][ac]), ac in untested)
                self.assertEqual(sorted(untested), sorted(set(untested)))

    def test_a_qualified_test_for_every_criterion_leaves_none_untested(self):
        """TASK-022 AC2 and TASK-022 AC12: adding a test whose docstring names every criterion qualified by the task leaves no
        untested finding."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                task, c, tests, ws = random_input(rng)
                acs = [next(iter(a)) for a in c['acceptance_criteria']]
                doc = ' '.join('%s %s' % (task, a) for a in acs) or 'nothing'
                tests = dict(tests, **{'tests/unit/test_all.py': 'def test_all():\n    """%s"""\n' % doc})
                self.assertEqual(ac_tests.listing(task, c, tests, ws)['findings'], [])

    def test_order_of_the_tests_mapping_does_not_matter(self):
        """TASK-022 AC4 and TASK-022 AC12: the result does not depend on the order of the tests mapping or of the write sets."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                task, c, tests, ws = random_input(rng)
                items = list(tests.items())
                rng.shuffle(items)
                wsi = list(ws.items())
                rng.shuffle(wsi)
                self.assertEqual(ac_tests.listing(task, c, dict(items), dict(wsi)), ac_tests.listing(task, c, tests, ws))

    def test_a_record_exactly_when_there_are_findings(self):
        """TASK-022 AC5 and TASK-022 AC12: a record is returned exactly when there are findings, and check_record finds nothing
        in it."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                task, c, tests, ws = random_input(rng)
                findings = ac_tests.listing(task, c, tests, ws)['findings']
                rec = ac_tests.listing_record(task, 'v1', findings, 'p', 'deterministic_tool_external_ci')
                self.assertEqual(rec is None, not findings)
                if rec is not None:
                    self.assertEqual(records.check_record(rec), [])


if __name__ == '__main__':
    unittest.main()

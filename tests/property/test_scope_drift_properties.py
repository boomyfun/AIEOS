"""Property tests of aieos_bootstrap.scope_drift (task TASK-033 AC13), standard library only, fixed seeds. For random
well-formed inputs: an event is given exactly when the commit is detected and some changed path is not non-task;
exempt implies detected and no event; the payload's paths are exactly the changed paths that are not non-task; the
result never depends on the order of changed_paths, trailer_tasks, non_task or evaluator. The oracles are written from
the contract's text with literal folders and classes, not from the module's helpers. Each test names its criteria in
its own docstring."""

import random
import unittest

from aieos_bootstrap import scope_drift

LIST = ['docs/History/**', 'docs/Progress/**', 'docs/Deferred/**', 'docs/Lessons/**']
RULES = [{'match': ['docs/**', '*.md'], 'class': 'low'}, {'match': ['src/**', 'tests/**'], 'class': 'medium'},
         {'match': ['**/contracts/**'], 'class': 'critical'}, {'match': ['.github/**'], 'class': 'critical'}]
EVALUATOR = ['.github/**', 'src/aieos_bootstrap/**', 'docs/records/**', '**/pyproject.toml']
PATHS = ['docs/History/a.md', 'docs/Progress/2026-10.md', 'docs/Deferred/DEF-1.md', 'docs/Lessons/L-1.md',
         'docs/Deferred/contracts/x.md', 'docs/Lessons/pyproject.toml', 'docs/plan/p.md', 'docs/records/r.jsonl',
         'src/aieos_bootstrap/x.py', 'src/other.py', 'tests/unit/t.py', '.github/w.yml', 'README.md',
         'docs/specs/s.md']
# The non-task paths of PATHS by the contract's four conditions, written out: on the list, class exactly low (not
# under contracts/, not src/ or tests/, not .github/), no evaluator pattern (not pyproject.toml), not the constitution,
# the policy or .github/.
NON_TASK = {'docs/History/a.md', 'docs/Progress/2026-10.md', 'docs/Deferred/DEF-1.md', 'docs/Lessons/L-1.md'}
TASKS = ['TASK-1', 'TASK-2']


def world(rnd):
    paths = rnd.sample(PATHS, rnd.randint(1, 5))
    trailers = rnd.sample(TASKS, rnd.randint(0, 1))
    contracts = {}
    if trailers and rnd.random() < 0.9:
        contracts[trailers[0]] = rnd.sample(PATHS, rnd.randint(1, 6))
    return {'commit': '%040x' % rnd.getrandbits(160), 'parents': 1, 'trailer_tasks': trailers,
            'changed_paths': paths, 'contracts': contracts, 'non_task': list(LIST), 'risk_rules': list(RULES),
            'evaluator': list(EVALUATOR), 'constitution_path': 'docs/pre-genesis/constitution.md',
            'policy_path': 'docs/specs/risk-rules-gov-aieos.md'}


def oracle_detected(w):
    if not w['trailer_tasks']:
        return True
    t = w['trailer_tasks'][0]
    if t not in w['contracts']:
        return True
    return any(p not in w['contracts'][t] for p in w['changed_paths'])


class Properties(unittest.TestCase):

    def test_event_exactly_when_detected_and_not_all_non_task(self):
        """TASK-033 AC13 and TASK-033 AC3 and TASK-033 AC4 and TASK-033 AC5 and TASK-033 AC6: over 600 random worlds,
        detection matches the oracle, an event is given exactly when detected and some path is not non-task, and its
        paths are exactly those paths."""
        rnd = random.Random(33)
        events = exempt = 0
        for _ in range(600):
            w = world(rnd)
            res = scope_drift.claims(w)
            self.assertIsNone(res['error'])
            det = oracle_detected(w)
            self.assertEqual(res['detected'], det, w)
            rest = sorted(set(w['changed_paths']) - NON_TASK)
            if det and rest:
                events += 1
                self.assertEqual(len(res['events']), 1)
                self.assertEqual(res['events'][0]['payload']['paths'], rest)
                self.assertEqual(res['events'][0]['payload']['entities'], sorted(w['trailer_tasks']))
            else:
                self.assertEqual(res['events'], [])
            if res['exempt']:
                exempt += 1
                self.assertTrue(res['detected'])
                self.assertEqual(res['events'], [])
        self.assertGreater(events, 100)
        self.assertGreater(exempt, 5)

    def test_order_does_not_matter(self):
        """TASK-033 AC13 and TASK-033 AC8: shuffling changed_paths, trailer_tasks, non_task and evaluator never
        changes the result."""
        rnd = random.Random(330)
        for _ in range(300):
            w = world(rnd)
            first = scope_drift.claims(w)
            for key in ('changed_paths', 'trailer_tasks', 'non_task', 'evaluator'):
                rnd.shuffle(w[key])
            self.assertEqual(scope_drift.claims(w), first)

    def test_other_parent_counts_never_give_an_event(self):
        """TASK-033 AC13 and TASK-033 AC3: with a parent count other than one, no world gives an event."""
        rnd = random.Random(3300)
        for _ in range(200):
            w = world(rnd)
            w['parents'] = rnd.choice([0, 2, 3])
            res = scope_drift.claims(w)
            self.assertEqual((res['events'], res['detected']), ([], False))
            self.assertEqual(res['uncovered'], [{'ref': w['commit'], 'detail': 'not one parent'}])


if __name__ == '__main__':
    unittest.main()

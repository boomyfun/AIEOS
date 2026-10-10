"""Property tests of the Resume Check (TASK-008 AC14; INV-005's property_test): random well-formed inputs built in
memory with fixed seeds. Standard library only; nothing is read or written.
"""
import copy
import random
import unittest

from aieos_bootstrap import records, resume_check as rc

SEEDS = (3, 11, 29, 47, 83)
RUNS = 60
RISKS = ('low', 'medium', 'high', 'critical')
FILES = ['src/app/core/a.py', 'src/app/api/b.py', 'src/app/util/c.py', 'docs/d.md', 'tests/e.py']


def hexs(rng, n):
    return ''.join(rng.choice('0123456789abcdef') for _ in range(n))


def well_formed(rng):
    base, head = hexs(rng, 40), hexs(rng, 40)
    if rng.random() < 0.2:
        head = base
    deps = ['TASK-%d' % rng.randint(1, 9) for _ in range(rng.randint(0, 2))]
    budgets = {'retries': 2, 'tokens': '400k', 'wall_time': '2h', 'human_attention': '10m'}
    use = {'retries': {'used': rng.randint(0, 3), 'reported': rng.random() < 0.9},
           'tokens': {'used': rng.choice(['10k', '500k', 'many']), 'reported': rng.random() < 0.9},
           'wall_time': {'used': rng.choice(['10m', '3h']), 'reported': rng.random() < 0.9},
           'human_attention': {'used': '0m', 'reported': True}}
    return {
        'task_id': 'TASK-%d' % rng.randint(1, 999), 'log_seq': rng.randint(0, 50),
        'task_state': rng.choice(['READY', 'REWORK', 'IN_PROGRESS']),
        'contract': {'contract_version': 'v%d' % rng.randint(1, 3), 'task_type': 'implementation',
                     'risk': rng.choice(RISKS[:3]),
                     'input_state': {'base_commit': base, 'depends_on': deps, 'intent_versions': {'SPEC-003': 'v4'}},
                     'write_set': {'paths': [rng.choice(['src/app/core/**', 'src/app/core/a.py'])]},
                     'read_set': {'paths': [rng.choice(FILES)], 'interfaces': ['load_policy'], 'schemas': []},
                     'constitution': [], 'autonomy': {'budgets': budgets}},
        'contract_hash': 'a' * 64, 'approved_contract_hash': 'a' * 64, 'head_commit': head,
        'base_is_ancestor': rng.random() < 0.9,
        'commits': [{'id': hexs(rng, 40), 'paths': [{'path': p, 'change': rng.choice(['added', 'modified', 'deleted'])}
                                                    for p in rng.sample(FILES, rng.randint(0, 3))],
                     'submitted': rng.random() < 0.2} for _ in range(rng.randint(0, 2))],
        'components': [{'id': 'CMP-API', 'paths': ['src/app/api/**'], 'tags': []}],
        'interfaces': [{'id': 'load_policy', 'component': 'CMP-API'}],
        'symbols': [{'interface': 'load_policy', 'base': 'F', 'head': rng.choice(['F', 'G', None])}],
        'schemas': [], 'derived_read_set': [], 'observed_read_set': rng.choice([None, []]),
        'intent_current': {'SPEC-003': rng.choice(['v4', 'v4', 'v5', None])},
        'dependencies': {d: {'state': rng.choice(['DONE', 'DONE', 'STALE', 'READY', None]),
                             'stale_evidence': rng.random() < 0.3} for d in deps},
        'articles': [{'id': 'INV-001', 'scope': {'paths': ['src/**'], 'components': []}, 'applicability': None,
                      'violated': rng.choice([False, False, True, None])}],
        'runtime': {'adapter': 'an-adapter', 'max_risk': rng.choice(list(RISKS) + [None])},
        'risk_rules': [{'match': {'paths': ['src/**']}, 'risk': rng.choice(RISKS[:3])}],
        'policy_version': 'v2', 'budget_use': use,
    }


def cases():
    for seed in SEEDS:
        rng = random.Random(seed)
        for _ in range(RUNS):
            yield rng, well_formed(rng)


class Properties(unittest.TestCase):
    def test_a_record_with_no_finding_and_one_value(self):
        for _, inp in cases():
            rec = rc.check(inp)
            self.assertEqual(records.check_decision('decision.execution', rec), [])
            self.assertTrue(rec['decision'] in records.EXECUTION_DECISIONS or ('error' in rec and rec['decision'] is None))
            for e in rec.get('state_effect', []):
                self.assertEqual(records.check_payload(e['type'], e['payload']), [])

    def test_the_same_inputs_give_the_same_record(self):
        for _, inp in cases():
            self.assertEqual(rc.check(inp), rc.check(copy.deepcopy(inp)))

    def test_the_decision_is_the_first_fired_in_order(self):
        for _, inp in cases():
            rec = rc.check(inp)
            fired = rec['outcomes_fired']
            self.assertEqual(fired, [o for o in rc.ORDER if o in fired])
            self.assertEqual(rec['decision'], fired[0] if fired else 'CONTINUE')

    def test_adding_a_fired_condition_never_gives_a_milder_decision(self):
        rank = {d: i for i, d in enumerate(rc.ORDER + ('CONTINUE',))}
        for rng, inp in cases():
            before = rc.check(inp)['decision']
            worse = copy.deepcopy(inp)
            choice = rng.randrange(3)
            if choice == 0:
                worse['runtime']['max_risk'] = None
            elif choice == 1:
                worse['budget_use']['retries'] = {'used': 9, 'reported': True}
            else:
                worse['intent_current'] = {}
            after = rc.check(worse)['decision']
            self.assertLessEqual(rank[after], rank[before], (before, after))

    def test_the_inputs_are_never_changed(self):
        for _, inp in cases():
            before = copy.deepcopy(inp)
            rc.check(inp)
            self.assertEqual(inp, before)


if __name__ == '__main__':
    unittest.main()

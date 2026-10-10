"""Property tests of the decision.execution keys of aieos_bootstrap.records (TASK-011 AC8), standard library only,
with fixed seeds (INV-005's property_test). For random well-formed execution records with the keys of
specification 3 section 9, check_decision gives no finding; corrupting or adding any checked key gives a finding named
for that key; the decision vocabulary and the first-value rule hold; and the other payload types are checked as before
(reading: no copy of the old module is loaded; the comparison is with the rules as test_records_properties.py
generates them).
"""

import random
import string
import unittest

from aieos_bootstrap import records

SEEDS = (1, 2, 3, 5, 8, 13, 21, 34)
ROUNDS = 40
HEX = '0123456789abcdef'


def word(rng, n=8):
    return ''.join(rng.choice(string.ascii_lowercase) for _ in range(n))


def hex_of(rng, n):
    return ''.join(rng.choice(HEX) for _ in range(n))


def well_formed(rng):
    """A random decision.execution payload with every section 9 key, of correct forms."""
    order = list(records.EXECUTION_ORDER)
    fired = sorted(rng.sample(order, rng.randint(0, 3)), key=order.index)
    decision = fired[0] if fired else 'CONTINUE'
    nums = rng.sample(range(1, 9), len(fired))
    by_check = dict(zip(nums, fired))
    checks = []
    for n in rng.sample(range(1, 9), 8):
        status = 'fired' if n in by_check else rng.choice(['passed', 'skipped', 'not_run'])
        checks.append({'check': n, 'status': status, 'outcome': by_check.get(n), 'detail': word(rng, rng.randint(0, 6))})
    p = {'record_id': 'exe-' + word(rng), 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_local',
         'recorder': word(rng), 'subject': 'TASK-%d' % rng.randint(1, 999), 'decision': decision,
         'contract_hash': hex_of(rng, 64), 'contract_version': 'v%d' % rng.randint(1, 9),
         'base_commit': hex_of(rng, 40), 'head_commit': hex_of(rng, rng.choice([40, 64])),
         'log_seq': rng.randint(0, 10 ** 6), 'delta': [{'path': 'src/' + word(rng), 'change': 'modified'}],
         'checks': checks, 'outcomes_fired': fired, 'read_set': {'entries': [], 'estimate': rng.random() < 0.5},
         'signatures': [], 'intent_versions': {word(rng): {'contract': 'v1', 'current': rng.choice(['v1', 'v2', None])}},
         'dependencies': {'TASK-%d' % rng.randint(1, 99): 'DONE'}, 'constitution': {}, 'runtime': {},
         'budgets': {}, 'policy_version': rng.choice(['v1', None]),
         'engine_identity': {'code_sha256': rng.choice([None, hex_of(rng, 64)]),
                             'python': '%d.%d.%d' % (3, rng.randint(0, 20), rng.randint(0, 20))},
         'uncovered': [], 'state_effect': []}
    for key in rng.sample(sorted(records.EXECUTION_KEYS), rng.randint(0, 4)):
        del p[key]
    return p


CORRUPT = {
    'base_commit': lambda rng: hex_of(rng, 39), 'head_commit': lambda rng: 'Z' * 40,
    'log_seq': lambda rng: rng.choice([-1, 1.5, True, '3']), 'contract_hash': lambda rng: hex_of(rng, 63),
    'contract_version': lambda rng: str(rng.randint(1, 9)),
    'engine_identity': lambda rng: rng.choice([None, {}, {'code_sha256': None}, hex_of(rng, 64)]),
    'checks': lambda rng: rng.choice([[], 'x', None]), 'outcomes_fired': lambda rng: rng.choice([['ACCEPT'], 'x']),
    'policy_version': lambda rng: rng.choice(['', 3]), 'intent_versions': lambda rng: rng.choice([{word(rng): '1'}, {word(rng): {'contract': 'v1'}}, [word(rng)]]),
    'delta': lambda rng: {}, 'signatures': lambda rng: 'x', 'uncovered': lambda rng: None,
    'state_effect': lambda rng: {}, 'read_set': lambda rng: [], 'dependencies': lambda rng: 'x',
    'constitution': lambda rng: [], 'runtime': lambda rng: 1, 'budgets': lambda rng: [],
}


class Properties(unittest.TestCase):
    def test_well_formed_execution_records_give_no_finding(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                p = well_formed(rng)
                self.assertEqual(records.check_decision('decision.execution', p), [], (seed, p))

    def test_corrupting_a_checked_key_is_named(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                p = well_formed(rng)
                key = rng.choice(sorted(CORRUPT))
                p[key] = CORRUPT[key](rng)
                found = [f.rule for f in records.check_decision('decision.execution', p)]
                self.assertIn('6.4:' + key, found, (seed, key, p[key]))

    def test_an_unknown_key_is_named(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                p = well_formed(rng)
                p['x_' + word(rng, 5)] = 1
                found = [f.rule for f in records.check_decision('decision.execution', p)]
                self.assertIn('6.4:unknown_key', found)

    def test_the_decision_vocabulary_and_the_first_value_rule(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                p = well_formed(rng)
                p['outcomes_fired'] = sorted(rng.sample(list(records.EXECUTION_ORDER), rng.randint(0, 3)),
                                             key=records.EXECUTION_ORDER.index)
                value = rng.choice(sorted(records.EXECUTION_DECISIONS) + ['ACCEPT', 'STOP'])
                p['decision'] = value
                found = [f.rule for f in records.check_decision('decision.execution', p)]
                first = p['outcomes_fired'][0] if p['outcomes_fired'] else 'CONTINUE'
                self.assertEqual('6.4:decision' in found, value not in records.EXECUTION_DECISIONS, (seed, value))
                if value in records.EXECUTION_DECISIONS:
                    self.assertEqual('6.4:outcomes_fired' in found, value != first, (seed, value, first))

    def test_the_same_input_gives_the_same_findings(self):
        for seed in SEEDS:
            a = [records.check_decision('decision.execution', well_formed(random.Random(seed))) for _ in range(3)]
            self.assertEqual(a[0], a[1])
            self.assertEqual(a[1], a[2])

    def test_other_payload_types_keep_the_record_form(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                rec = {'record_id': 'r-' + word(rng), 'fact_kind': 'observation',
                       'source_class': 'deterministic_tool_external_ci', 'recorder': word(rng),
                       'subject': 'TASK-%d' % rng.randint(1, 99),
                       'intent_versions': {word(rng): 'v%d' % rng.randint(1, 9)}}
                etype = rng.choice(['record.added', 'violation.detected'])
                if etype == 'violation.detected':
                    rec.update(outcome='blocking', blocking_kind='violation')
                self.assertEqual(records.check_payload(etype, rec), [], (seed, etype))
                rec['intent_versions'] = {word(rng): {'contract': 'v1', 'current': 'v1'}}
                self.assertIn('6.2:intent_versions', [f.rule for f in records.check_payload(etype, rec)])
                key = rng.choice(sorted(records.EXECUTION_KEYS - records.RECORD_KEYS))
                rec2 = dict(rec, intent_versions={'A': 'v1'})
                rec2[key] = 1
                self.assertIn('6.2:unknown_key', [f.rule for f in records.check_payload(etype, rec2)], key)


if __name__ == '__main__':
    unittest.main()

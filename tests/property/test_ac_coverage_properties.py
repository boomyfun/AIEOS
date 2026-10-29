"""Property tests of aieos_bootstrap.ac_coverage (TASK-021 AC12), standard library only, with fixed seeds.

For random well-formed contracts: every AC id is either named by a gate or reported uncovered, never both; adding a
gate that names every AC leaves no uncovered finding; the result does not depend on the order of the input's other
keys; and a record is returned exactly when there are findings, in the form of specification 2 section 6.2."""

import random
import unittest

from aieos_bootstrap import ac_coverage, records

SEEDS = (1, 2, 3, 5, 8, 13, 21, 34)
ROUNDS = 40
ARTICLES = ('INV-001', 'INV-002', 'SEC-001', 'GOV-003', 'OPS-002')


def random_contract(rng):
    acs = ['AC%d' % n for n in rng.sample(range(1, 30), rng.randint(0, 8))]
    const = rng.sample(ARTICLES, rng.randint(0, len(ARTICLES)))
    pool = acs + const + ['AC%d' % rng.randint(30, 40), 'X-%d' % rng.randint(0, 3), rng.choice(ARTICLES)]
    plan = [{'gate': 'G0', 'check': 'scope'}]
    for g in range(1, rng.randint(1, 4)):
        gate = {'gate': 'G%d' % g, 'check': 'c%d' % g}
        if rng.random() < 0.8:
            gate['args'] = rng.sample(pool, rng.randint(0, len(pool)))
        plan.append(gate)
    c = {'acceptance_criteria': [{a: 'text ' + a} for a in acs], 'verification_plan': plan, 'constitution': const}
    for k in range(rng.randint(0, 3)):
        c['other_%d' % k] = rng.randint(0, 9)
    return c


class Properties(unittest.TestCase):

    def test_named_or_uncovered_never_both(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                c = random_contract(rng)
                out = ac_coverage.check(c)
                named = {a for g in c['verification_plan'] for a in g.get('args', [])}
                unc = {f['ref'] for f in out if f['kind'] == 'uncovered'}
                for item in c['acceptance_criteria']:
                    ac = next(iter(item))
                    self.assertTrue((ac in named) != (ac in unc), (seed, ac))
                self.assertNotIn('malformed', [f['kind'] for f in out])

    def test_a_gate_naming_every_ac_leaves_none_uncovered(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                c = random_contract(rng)
                acs = [next(iter(i)) for i in c['acceptance_criteria']]
                c['verification_plan'].append({'gate': 'G9', 'check': 'all', 'args': acs})
                self.assertNotIn('uncovered', [f['kind'] for f in ac_coverage.check(c)])

    def test_other_keys_and_their_order_do_not_matter(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                c = random_contract(rng)
                keys = list(c)
                rng.shuffle(keys)
                shuffled = {k: c[k] for k in keys}
                shuffled['extra'] = 'ignored'
                self.assertEqual(ac_coverage.check(shuffled), ac_coverage.check(c))

    def test_record_exactly_when_findings(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                out = ac_coverage.check(random_contract(rng))
                r = ac_coverage.coverage_record('TASK-%03d' % rng.randint(1, 99), 'v%d' % rng.randint(1, 3), out,
                                                'aieos-core', rng.choice(ac_coverage.SOURCE_CLASSES))
                self.assertEqual(r is None, out == [])
                if r is not None:
                    self.assertEqual(records.check_record(r), [])
                    self.assertEqual((r['outcome'], r['blocking_kind']), ('blocking', 'other'))

    def test_the_findings_equal_a_literal_oracle(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                c = random_contract(rng)
                acs = [next(iter(i)) for i in c['acceptance_criteria']]
                named = [a for g in c['verification_plan'] for a in g.get('args', [])]
                want = [('no_acceptance_criteria', 'acceptance_criteria')] if not acs else []
                want += [('uncovered', a) for a in acs if a not in named]
                strays = []
                for a in named:
                    if a not in acs and a not in c['constitution'] and a not in strays:
                        strays.append(a)
                want += [('stray_arg', a) for a in strays]
                self.assertEqual([(f['kind'], f['ref']) for f in ac_coverage.check(c)], want, (seed, c))


if __name__ == '__main__':
    unittest.main()

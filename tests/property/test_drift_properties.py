"""Property tests of aieos_bootstrap.drift (task TASK-030), standard library only, with fixed seeds.

For random well-formed inputs: every event's article applies, has a usable failing result and is not in already;
every applicable article is in exactly one of the events, already, the passing set or the uncovered refs; and the
result does not depend on the order of the articles, the rule results or the task records. Each test names its
criteria in its own docstring."""

import random
import unittest

from aieos_bootstrap import drift, governor

SEEDS = (1, 2, 3, 5, 8, 13, 21, 34)
ROUNDS = 30
PATHS = ['docs/a.md', 'src/x.py', 'src/y/z.py', 'tests/t.py', '.github/w.yml']
SCOPES = [['**'], ['src/**'], ['src/*'], ['tests/**'], ['docs/*.md'], ['*.yml'], None, []]
IDS = ['INV-001', 'INV-002', 'SEC-001', 'SEC-002', 'GOV-003', 'OPS-003']


def commit(rng):
    return ''.join(rng.choice('0123456789abcdef') for _ in range(40))


def rec(rng, c, ident, k, well=True):
    r = {'record_id': 'r%d' % k, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_external_ci',
         'recorder': 'ci', 'subject': c, 'commit': c, 'gate': 'G3', 'outcome': rng.choice(['pass', 'fail']),
         'refers_to': ident}
    if not well:
        r[rng.choice(['fact_kind', 'gate', 'commit'])] = rng.choice(['claim', 'G2', 'f' * 40])
    return r


def random_input(rng):
    c = commit(rng)
    ids = rng.sample(IDS, rng.randint(0, len(IDS)))
    arts = [{'id': i, 'scope': rng.choice(SCOPES)} for i in ids]
    results = [rec(rng, c, rng.choice(IDS), k, rng.random() < 0.85) for k in range(rng.randint(0, 8))]
    task = [rec(rng, c, rng.choice(IDS), 100 + k, rng.random() < 0.8) for k in range(rng.randint(0, 3))]
    return {'base_commit': c, 'changed_paths': rng.sample(PATHS, rng.randint(0, 3)), 'articles': arts,
            'rule_results': results, 'task_records': task, 'recorder': 'aieos-core (test)'}


def applies(a, paths):
    s = a['scope']
    if not (isinstance(s, list) and s):
        return True
    return any(governor.matches(p, path) for p in s for path in paths)


def usable(r, c):
    return (r['fact_kind'] == 'observation' and r['gate'] == 'G3' and r['commit'] == c)


class Properties(unittest.TestCase):

    def test_events_and_partition(self):
        """TASK-030 AC2 and TASK-030 AC3 and TASK-030 AC5 and TASK-030 AC6 and TASK-030 AC13: every event's article
        applies, has a usable failing result and is not in already; every applicable article falls in exactly one of
        events, already, passed or uncovered by "no rule result"; already is exactly the failing articles that a
        well-formed failing task record matches, the events exactly the others; and the samples give both."""
        seen = {'events': 0, 'already': 0}
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                i = random_input(rng)
                res = drift.violations(i)
                self.assertIsNone(res['error'])
                c = i['base_commit']
                app = {a['id'] for a in i['articles'] if applies(a, i['changed_paths'])}
                outcomes = {}
                for r in i['rule_results']:
                    if usable(r, c):
                        outcomes.setdefault(r['refers_to'], set()).add(r['outcome'])
                ev = {e['payload']['refers_to'] for e in res['events']}
                for a in ev:
                    self.assertIn(a, app)
                    self.assertIn('fail', outcomes.get(a, set()))
                    self.assertNotIn(a, res['already'])
                none = {u['ref'] for u in res['uncovered'] if u['detail'] == 'no rule result'}
                passed = {a for a in app if outcomes.get(a) and 'fail' not in outcomes[a]}
                for a in app:
                    groups = [a in ev, a in res['already'], a in passed, a in none]
                    self.assertEqual(sum(groups), 1, (seed, a, groups))
                failing = {a for a in app if 'fail' in outcomes.get(a, set())}
                matched = {r['refers_to'] for r in i['task_records'] if usable(r, c) and r['outcome'] == 'fail'}
                self.assertEqual(res['already'], sorted(failing & matched))
                self.assertEqual(ev, failing - matched)
                seen['events'] += len(ev)
                seen['already'] += len(res['already'])
        self.assertTrue(seen['events'] > 0 and seen['already'] > 0, seen)

    def test_order_does_not_matter(self):
        """TASK-030 AC8 and TASK-030 AC13: shuffling the articles, the rule results and the task records gives the same
        events, already and uncovered (record ids are distinct, so the named entries are the same)."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                i = random_input(rng)
                j = dict(i, articles=list(i['articles']), rule_results=list(i['rule_results']),
                         task_records=list(i['task_records']))
                for key in ('articles', 'rule_results', 'task_records'):
                    rng.shuffle(j[key])
                a, b = drift.violations(i), drift.violations(j)
                self.assertEqual((a['events'], a['already']), (b['events'], b['already']))
                self.assertEqual(sorted(map(str, a['uncovered'])), sorted(map(str, b['uncovered'])))


if __name__ == '__main__':
    unittest.main()

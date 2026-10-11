"""Property tests of aieos_bootstrap.stale (task TASK-023), standard library only, with fixed seeds.

For random well-formed inputs: a record is stale by a reason only when it can be checked for that rule, and an event's
ids are a subset of its reason's stale ids; a second run with the first run's events as earlier events gives no event;
and the result does not depend on the order of the records or of the read-set. Each test names its criteria in its own
docstring."""

import random
import unittest

from aieos_bootstrap import records, stale

SEEDS = (1, 2, 3, 5, 8, 13, 21, 34)
ROUNDS = 30
PATHS = ['docs/a.md', 'docs/b.md', 'src/x.py', 'src/y.py', 'tests/t.py']
IDS = ['spec-1', 'spec-2', 'spec-3']


def commit(rng):
    return ''.join(rng.choice('0123456789abcdef') for _ in range(40))


def random_input(rng):
    acc = commit(rng)
    base = []
    for _ in range(rng.randint(0, 4)):
        base.append({'commit': commit(rng), 'paths': rng.sample(PATHS, rng.randint(0, 3)),
                     'submitted_by_task': rng.random() < 0.2})
    known = [acc] + [c['commit'] for c in base]
    recs = []
    for k in range(rng.randint(0, 6)):
        r = {'record_id': 'r%d' % k}
        if rng.random() < 0.8:
            r['commit'] = rng.choice(known) if rng.random() < 0.8 else commit(rng)
        if rng.random() < 0.7:
            r['intent_versions'] = {i: 'v%d' % rng.randint(1, 2) for i in rng.sample(IDS, rng.randint(0, 2))}
        recs.append(r)
    rs = []
    for p in rng.sample(PATHS, rng.randint(0, 3)):
        rs.append({'entry': p, 'kind': 'path', 'patterns': [p]})
    if rng.random() < 0.5:
        rs.append({'entry': 'pkg.f', 'kind': rng.choice(('interface', 'schema')),
                   'patterns': None if rng.random() < 0.5 else [rng.choice(['docs/*.md', 'src/**'])]})
    return {'task_id': 'TASK-0%02d' % rng.randint(10, 99), 'accepted_commit': acc,
            'trigger_commit': base[-1]['commit'] if base else acc, 'records': recs,
            'intent_current': {i: 'v%d' % rng.randint(1, 2) for i in rng.sample(IDS, rng.randint(0, 3))},
            'read_set': rs, 'read_set_estimate': rng.random() < 0.3, 'base_commits': base, 'earlier_events': []}


class Properties(unittest.TestCase):

    def cases(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                yield random_input(rng)

    def test_stale_only_when_checkable(self):
        """TASK-023 AC2, TASK-023 AC4, TASK-023 AC5 and TASK-023 AC6: a record stale by commit has a commit, one stale
        by intent_version has intent_versions, and each event's ids are a subset of its reason's stale ids, in a payload
        check_payload accepts; over the seeds the generator reaches each case (a stale record by each reason, an unknown
        record commit, an unresolved entry and an event), so no property holds vacuously."""
        reached = {'commit': 0, 'intent_version': 0, 'commit order not known': 0, 'not resolved by the caller': 0,
                   'event': 0}
        for x in self.cases():
            r = stale.stale(x)
            self.assertIsNone(r['error'])
            by_id = {rec['record_id']: rec for rec in x['records']}
            self.assertTrue(all('commit' in by_id[i] for i in r['stale']['commit']))
            self.assertTrue(all('intent_versions' in by_id[i] for i in r['stale']['intent_version']))
            for e in r['events']:
                self.assertTrue(set(e['payload']['records']) <= set(r['stale'][e['payload']['reason']]))
                self.assertEqual(records.check_payload('evidence.stale', e['payload']), [])
            for reason in ('commit', 'intent_version'):
                reached[reason] += len(r['stale'][reason])
            for u in r['uncovered']:
                if u['detail'] in reached:
                    reached[u['detail']] += 1
            reached['event'] += len(r['events'])
        self.assertTrue(all(n > 0 for n in reached.values()), reached)

    def test_second_run_gives_no_event(self):
        """TASK-023 AC6 and TASK-023 AC8: with the first run's events as earlier events, a second run gives no event and
        the same stale lists; over the seeds some first run gives an event, so the property is not vacuous."""
        events = 0
        for x in self.cases():
            first = stale.stale(x)
            events += len(first['events'])
            y = dict(x, earlier_events=[e['payload'] for e in first['events']])
            second = stale.stale(y)
            self.assertEqual(second['events'], [])
            self.assertEqual(second['stale'], first['stale'])
        self.assertGreater(events, 0)

    def test_order_does_not_matter(self):
        """TASK-023 AC8: the result does not depend on the order of the records or of the read-set."""
        rng = random.Random(99)
        for x in self.cases():
            y = dict(x, records=rng.sample(x['records'], len(x['records'])),
                     read_set=rng.sample(x['read_set'], len(x['read_set'])))
            self.assertEqual(stale.stale(y), stale.stale(x))


if __name__ == '__main__':
    unittest.main()

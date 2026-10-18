"""Property tests of aieos_bootstrap.read_set_record and of the observed read-set rules of aieos_bootstrap.records (task
TASK-064, rules R2 and R5's properties), standard library only, with fixed seeds: build and observe are deterministic
over equal inputs; append is called at most once; the record's read_paths are the distinct given paths in first
order; the inputs are never changed; and a record with neither read_paths nor the name gets no "6.2:read_set" finding.
append is a stand-in, so no file is written. Each test names its criteria in its own docstring."""

import copy
import datetime
import random
import types
import unittest

from aieos_bootstrap import read_set_record as rs
from aieos_bootstrap import records

NOW = datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)
ALPHABET = 'ab/.-_ Z:\\'


def paths(rnd):
    pool = [''.join(rnd.choice(ALPHABET) for _ in range(rnd.randint(0, 4))) for _ in range(4)]
    return [rnd.choice(pool) for _ in range(rnd.randint(0, 8))]


def context(rnd):
    sid = rnd.choice(['s-1', 's/2', 'made-up-9', ''])
    c = {'root': 'C:\\proj\\repo', 'task_id': rnd.choice(['TASK-100', 'TASK-x']), 'session_id': sid,
         'fencing_token': {'epoch': 'e1', 'counter': rnd.randint(0, 3)}, 'write_set': ['docs/**'],
         'allowlist': ['git status'], 'recorder': rnd.choice(['rec ' + sid, 'rec other'])}
    if rnd.random() < 0.1:
        c.pop('root')
    return c


class Calls:
    def __init__(self, state):
        self.n = 0
        self.state = state

    def append(self, *args, **kw):
        self.n += 1
        return types.SimpleNamespace(result=self.state, reason=None, seq=1, findings=())


class Properties(unittest.TestCase):
    def test_build_distinct_in_first_order(self):
        """TASK-064 AC4: over generated lists, read_paths are the distinct given paths in first order, or the record is
        None when a path is empty; the given list is never changed; build is deterministic."""
        rnd = random.Random(6401)
        for _ in range(400):
            given = paths(rnd)
            kept = list(given)
            r = rs.build('TASK-100', 's-1', given, 'rec s-1')
            self.assertEqual(given, kept)
            self.assertEqual(r, rs.build('TASK-100', 's-1', list(given), 'rec s-1'))
            if '' in given:
                self.assertIsNone(r)
                continue
            want = []
            for p in given:
                if p not in want:
                    want.append(p)
            self.assertEqual(r['read_paths'], want)
            self.assertEqual(records.check_record(r), [])

    def test_observe_at_most_once_and_deterministic(self):
        """TASK-064 AC5: over generated contexts and lists, append is called at most once, and once only when the
        result is not a refusal before it; equal inputs give equal results; the inputs are never changed."""
        rnd = random.Random(6402)
        for _ in range(400):
            ctx, given = context(rnd), paths(rnd)
            state = rnd.choice(['appended', 'duplicate', 'refused'])
            ctx_copy, given_copy = copy.deepcopy(ctx), list(given)
            first, second = Calls(state), Calls(state)
            a = rs.observe(ctx, given, NOW, append=first.append)
            b = rs.observe(copy.deepcopy(ctx), list(given), NOW, append=second.append)
            self.assertEqual(a, b)
            self.assertLessEqual(first.n, 1)
            self.assertEqual(first.n == 1, a['reason'] in (None, 'core'))
            self.assertEqual((ctx, given), (ctx_copy, given_copy))

    def test_other_records_untouched(self):
        """TASK-064 AC2: over generated records with neither read_paths nor the name, check_read_set gives nothing and
        no finding of check_record has a "6.2:read_set" rule."""
        rnd = random.Random(6403)
        keys = ['record_id', 'fact_kind', 'source_class', 'recorder', 'subject', 'evidence_type', 'outcome',
                'dimension', 'commit', 'risk_class', 'refers_to', 'made_up_key']
        values = ['x', '', None, 3, 'observation', 'unit_test', 'risk_class', 'pass', 'TASK-1', ['a'], {'k': 'v'}]
        for _ in range(600):
            r = {k: rnd.choice(values) for k in keys if rnd.random() < 0.6}
            if r.get('evidence_type') == 'observed_read_set':
                continue
            self.assertEqual(records.check_read_set(r), [])
            self.assertEqual([f for f in records.check_record(r) if f.rule.startswith('6.2:read_set')], [])


if __name__ == '__main__':
    unittest.main()

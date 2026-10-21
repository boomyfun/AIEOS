"""Property tests of aieos_bootstrap.session_violation (TASK-070 AC8's property part), standard library only,
fixed seeds, at most 50 cases each: over generated lookup answers, arguments and answers of adapter.violation that carry
tokens, the result has exactly RESULT_KEYS, fencing_token is always None, no fencing token appears anywhere in it,
adapter.violation is called only after a tied lease of the checked shape and then with that lease's task and token,
and equal inputs give equal results. Stand-ins only: no file is written or opened."""

import datetime
import random
import string
import unittest
from unittest import mock

from aieos_bootstrap import adapter, session_violation, writer

UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 10, 16, 12, 0, 0, tzinfo=UTC)
ROOT = '/made-up-root'
CASES = 50
OBS = {'record_id': 'obs-1', 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
       'recorder': 'r', 'subject': 'TASK-001', 'evidence_type': 'write_outside_write_set', 'outcome': 'blocking',
       'blocking_kind': 'violation', 'refers_to': 'src/outside.py'}
FIXED = ('release: the lease is held with another token (not shown)', 'lease: the lookup gave no tied lease',
         'entry: adapter.violation gave no result mapping', 'release: nothing released (token)')


def epoch(rng, taken):
    """A generated epoch: at least 16 characters, distinct from the others and no substring of a fixed finding."""
    while True:
        e = 'E' + ''.join(rng.choice(string.ascii_uppercase + string.digits) for _ in range(rng.randint(15, 24)))
        if e not in taken and not any(e in f for f in FIXED):
            taken.add(e)
            return e


def holds_token(value, epochs):
    if isinstance(value, dict):
        if 'epoch' in value and 'counter' in value:
            return True
        return any(holds_token(k, epochs) or holds_token(v, epochs) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(holds_token(v, epochs) for v in value)
    if isinstance(value, str):
        return ('epoch' in value and 'counter' in value) or any(e in value for e in epochs)
    return False


def lease_with(rng, epochs):
    token = {'epoch': epoch(rng, epochs), 'counter': rng.randint(0, 9)}
    return {'task_id': 'TASK-%03d' % rng.randint(1, 999), 'fencing_token': token,
            'expires_at': NOW + datetime.timedelta(minutes=rng.randint(1, 90))}


def lookup_answer(rng, epochs):
    """A generated answer of the lookup and whether it is a tied lease of the checked shape."""
    lease = lease_with(rng, epochs)
    k = rng.randrange(9)
    if k < 4:
        return writer.StoreResult('done', 'tied', value=lease), lease
    return [writer.StoreResult('done', 'tied', value=dict(lease, more=1)),
            writer.StoreResult('done', 'tied', value=dict(lease, task_id='T-1')),
            writer.StoreResult('done', 'no_lease_row'),
            writer.StoreResult('refused', rng.choice(('session', 'ended', 'leases')),
                               ['leases: held with epoch %s counter 2' % lease['fencing_token']['epoch']]),
            None][k - 4], None


def violation_answer(rng, lease, epochs):
    """A generated answer of adapter.violation with tokens in released, core['released'] and the two filtered forms;
    epoch values appear nowhere else."""
    other = epoch(rng, epochs)
    released = dict(lease) if rng.random() < 0.7 else None
    refusal = 'the lease on %s is held with epoch %s counter 5, not epoch %s counter %d' % (
        lease['task_id'], other, lease['fencing_token']['epoch'], lease['fencing_token']['counter'])
    loose = 'held epoch %s counter 1' % epoch(rng, epochs)
    found = rng.sample(['release: nothing released (token)', refusal, loose, 'plain'], rng.randint(0, 4))
    core = {'result': 'done', 'reason': None, 'findings': found, 'appended': ['ev', 'ev/decision'], 'duplicate': [],
            'released': dict(released) if released else None}
    return {'result': 'done', 'reason': None, 'findings': rng.sample([refusal, loose, 'plain'], rng.randint(0, 3)),
            'core': core, 'decision': 'STOP: violation', 'fencing_token': None,
            'released': released}


def case(rng):
    epochs = set()
    answer, lease = lookup_answer(rng, epochs)
    given = violation_answer(rng, lease or lease_with(rng, epochs), epochs)
    calls = []

    def stand_in(*args, **kwargs):
        calls.append(args)
        return given

    sid = rng.choice(('s-1', 'made-up-session-7'))
    with mock.patch.object(adapter, 'violation', stand_in):
        out = session_violation.session_violation(ROOT, sid, OBS, 'ev', 'r', NOW, lookup=lambda r, s, n: answer)
    return answer, lease, given, calls, epochs, sid, out


class Properties(unittest.TestCase):

    def test_no_token_in_any_result(self):
        """TASK-070 AC8 (property) and TASK-070 AC1: exactly RESULT_KEYS, fencing_token None, findings a list of str,
        and the token predicate finds no token anywhere in the result, with the generated epochs."""
        rng = random.Random(69)
        for _ in range(CASES):
            answer, lease, given, calls, epochs, sid, out = case(rng)
            with self.subTest(answer=answer):
                self.assertEqual(tuple(out), adapter.RESULT_KEYS)
                self.assertIsNone(out['fencing_token'])
                self.assertTrue(all(isinstance(f, str) for f in out['findings']))
                self.assertFalse(holds_token(out, epochs), out)

    def test_the_record_only_after_a_tied_lease(self):
        """TASK-070 AC8 (property) and TASK-070 AC2 and TASK-070 AC3: adapter.violation is called only after a tied
        lease of the checked shape, once, with that lease's task and token; otherwise the result is "lease"."""
        rng = random.Random(6969)
        for _ in range(CASES):
            answer, lease, given, calls, epochs, sid, out = case(rng)
            with self.subTest(answer=answer):
                if lease is None:
                    self.assertEqual(calls, [])
                    self.assertEqual((out['result'], out['reason']), ('refused', 'lease'))
                else:
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(calls[0][1:3], (lease['task_id'], lease['fencing_token']))
                    self.assertEqual(out['result'], 'done')

    def test_equal_inputs_give_equal_results(self):
        """TASK-070 AC8 (property) and TASK-070 AC1: the same generated case twice gives equal results."""
        for seed in range(CASES):
            first = case(random.Random(seed))[-1]
            second = case(random.Random(seed))[-1]
            self.assertEqual(first, second)


if __name__ == '__main__':
    unittest.main()

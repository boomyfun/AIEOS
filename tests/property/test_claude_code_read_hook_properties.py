"""Property tests of aieos_bootstrap.claude_code_read_hook (TASK-068 AC9's property part), standard library only, fixed
seeds, at most 50 cases each: over generated judge, read_paths and add_reads answers (stand-ins) and generated
environ mappings, run's result has exactly its four keys, exit_code is always 0, add_reads is called only after a live
tie and a covered read, and equal inputs give equal results. Stand-ins only: no file is written or opened."""

import datetime
import os
import random
import unittest
from unittest import mock

from aieos_bootstrap import claude_code_read_hook as hook
from aieos_bootstrap import claude_code_reads, claude_code_store, writer

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
TOP = os.path.abspath(os.sep)
ROOT = os.path.join(TOP, 'made-up-root')
LEASE = {'task_id': 'TASK-001', 'fencing_token': {'epoch': 'e', 'counter': 1},
         'expires_at': T0 + datetime.timedelta(hours=1)}
CASES = 50
KEYS = {'exit_code', 'outcome', 'reason', 'findings'}
VALUES = (None, '', ' ', 's-1', ROOT, 0, b'x')
JUDGED = ({'outcome': 'tied', 'reason': 'tied', 'findings': [], 'root': ROOT, 'lease': LEASE},
          {'outcome': 'tied', 'reason': 'tied', 'findings': [], 'root': '', 'lease': LEASE},
          {'outcome': 'tied', 'reason': 'tied', 'findings': [], 'root': ROOT, 'lease': None},
          {'outcome': 'enforce_nothing', 'reason': 'no_lease_row', 'findings': [], 'root': ROOT, 'lease': None},
          {'outcome': 'refuse', 'reason': 'session', 'findings': ['session: x'], 'root': ROOT, 'lease': None},
          None, RuntimeError('x'))
READS = ({'result': 'read', 'reason': 'read', 'findings': [], 'read_paths': ['a']},
         {'result': 'read', 'reason': 'read', 'findings': [], 'read_paths': []},
         {'result': 'uncovered', 'reason': 'tool', 'findings': ['x'], 'read_paths': []}, 'read', KeyError('x'))
STORED = (writer.StoreResult('done', value=1), writer.StoreResult('refused', 'leases', ['leases: x']),
          writer.StoreResult('refused', 'path', [2]), None, OSError('x'))


def answer(value, calls, name):
    def call(*args):
        calls.append(name)
        if isinstance(value, BaseException):
            raise value
        return value
    return call


def run_with(rng):
    """One generated case: its choices, the calls made and run's result."""
    env = {}
    for name in (hook.SESSION_VAR, hook.ROOT_VAR):
        v = rng.choice(VALUES)
        if v is not None:
            env[name] = v
    j, r, s = rng.randrange(len(JUDGED)), rng.randrange(len(READS)), rng.randrange(len(STORED))
    calls = []
    with mock.patch.object(claude_code_store, 'judge', answer(JUDGED[j], calls, 'judge')), \
            mock.patch.object(claude_code_reads, 'read_paths', answer(READS[r], calls, 'read_paths')), \
            mock.patch.object(writer, 'add_reads', answer(STORED[s], calls, 'add_reads')):
        out = hook.run(b'{}', env, None, T0)
    return (sorted(env.items(), key=repr), j, r, s), calls, out


class Properties(unittest.TestCase):

    def test_the_shape_and_the_order(self):
        """TASK-068 AC9 (property), TASK-068 AC1 and TASK-068 AC2: exactly the four keys, exit_code 0, findings a list
        of str; add_reads called only after a live tie (with a non-empty session id and root) and a covered read."""
        rng = random.Random(68)
        outcomes = set()
        for _ in range(CASES):
            (env, j, r, _), calls, out = run_with(rng)
            outcomes.add(out['outcome'])
            self.assertEqual(set(out), KEYS)
            self.assertEqual(out['exit_code'], 0)
            self.assertTrue(isinstance(out['findings'], list) and all(isinstance(f, str) for f in out['findings']))
            if 'add_reads' in calls:
                sid = dict(env).get(hook.SESSION_VAR)
                self.assertEqual((j, r), (0, 0))
                self.assertTrue(isinstance(sid, str) and sid)
                self.assertEqual(calls, ['judge', 'read_paths', 'add_reads'])
            if out['outcome'] == 'recorded':
                self.assertIn('add_reads', calls)
        self.assertLessEqual(outcomes, {'skip', 'recorded', 'lost'})
        self.assertIn('skip', outcomes)

    def test_equal_inputs_give_equal_results(self):
        """TASK-068 AC9 (property) and TASK-068 AC1: the same generated case run twice gives the same result."""
        for seed in (1, 2):
            first = [run_with(random.Random(seed * 100 + i)) for i in range(CASES // 2)]
            second = [run_with(random.Random(seed * 100 + i)) for i in range(CASES // 2)]
            self.assertEqual(first, second)


if __name__ == '__main__':
    unittest.main()

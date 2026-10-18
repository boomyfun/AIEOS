"""Property tests of aieos_bootstrap.claude_code_store (TASK-066 AC9's property part), standard library only, fixed
seeds, at most 50 cases each: over generated session ids, roots, working folders and stand-in answers, judge's result
has exactly the five keys, lease is None unless the outcome is "tied", "enforce_nothing" occurs only when the session
id and the root were both absent, and equal inputs give equal results. Stand-ins only: no file is written or opened."""

import datetime
import os
import random
import types
import unittest
from unittest import mock

from aieos_bootstrap import claude_code_store, writer

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
TOP = os.path.abspath(os.sep)
PROJ = os.path.join(TOP, 'made-up-proj')
SUB = os.path.join(PROJ, 'sub')
LEASE = {'task_id': 'TASK-001', 'fencing_token': {'epoch': 'e', 'counter': 1},
         'expires_at': T0 + datetime.timedelta(hours=1)}
KEYS = {'outcome', 'reason', 'findings', 'root', 'lease'}
CASES = 50
VALUES = (None, '', ' ', 's-1', 'made-up-session-9', 0, False, [], b'', PROJ, SUB, 'relative', 1.5)
ANSWERS = (writer.StoreResult('done', 'tied', value=LEASE), writer.StoreResult('done', 'no_lease_row'),
           writer.StoreResult('refused', 'leases', ['leases: made-up']), writer.StoreResult('done', 'tied'),
           writer.StoreResult('refused', 'unreadable', ['unreadable: OSError']), None)


def judge_with(rng):
    """One generated case: its arguments, the stand-in disk and answer, and judge's result."""
    sid, root, wf = rng.choice(VALUES), rng.choice(VALUES), rng.choice(VALUES)
    if rng.random() < 0.4:
        sid, root, wf = rng.choice((None, '')), rng.choice((None, '')), rng.choice((PROJ, SUB))
    answer = rng.choice(ANSWERS)
    stores = {writer.store_path(PROJ)} if rng.random() < 0.6 else set()
    dirs = {PROJ, SUB}

    def lstat(p):
        if p in stores:
            return types.SimpleNamespace(st_mode=0o100644)
        raise FileNotFoundError(p)
    osns = types.SimpleNamespace(lstat=lstat, path=types.SimpleNamespace(
        abspath=os.path.abspath, isabs=os.path.isabs, isdir=lambda p: p in dirs, dirname=os.path.dirname))
    with mock.patch.object(claude_code_store, 'os', osns), \
            mock.patch.object(writer, 'session_lease', lambda r, s, n, *a: answer):
        out = claude_code_store.judge(sid, root, wf, T0)
    return (sid, root, wf, answer, tuple(sorted(stores))), out


def absent(v):
    return v is None or v == ''


class Properties(unittest.TestCase):

    def test_the_shape_and_the_enforce_nothing_rule(self):
        """TASK-066 AC9 (property) and TASK-066 AC4 and TASK-066 AC5: exactly the five keys; lease None unless "tied";
        "enforce_nothing" only with both values absent; findings a list of str."""
        rng = random.Random(66)
        outcomes = set()
        for _ in range(CASES):
            (sid, root, _, _, _), out = judge_with(rng)
            outcomes.add(out['outcome'])
            self.assertEqual(set(out), KEYS)
            if out['outcome'] != 'tied':
                self.assertIsNone(out['lease'])
            if out['outcome'] == 'enforce_nothing':
                self.assertTrue(absent(sid) and absent(root), (sid, root))
            self.assertIn(out['outcome'], ('tied', 'enforce_nothing', 'refuse'))
            self.assertTrue(isinstance(out['findings'], list) and all(isinstance(f, str) for f in out['findings']))
        self.assertEqual(outcomes, {'tied', 'enforce_nothing', 'refuse'})

    def test_equal_inputs_give_equal_results(self):
        """TASK-066 AC9 (property) and TASK-066 AC5: the same generated case run twice gives the same result."""
        for seed in (1, 2):
            first = [judge_with(random.Random(seed * 100 + i)) for i in range(CASES // 2)]
            second = [judge_with(random.Random(seed * 100 + i)) for i in range(CASES // 2)]
            self.assertEqual(first, second)


if __name__ == '__main__':
    unittest.main()

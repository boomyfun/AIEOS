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


FORCED_SESSIONS = ('s-1', ' ')
NOT_A_SESSION = (None, '', 0, b'x')


def run_forced(rng, forced):
    """One generated case of TASK-073 AC7: when forced, judge's answer is the live tie (JUDGED[0]), read_paths' the
    covered read (READS[0]) and the session id one of FORCED_SESSIONS; otherwise the same with exactly one of the three
    drawn away from it (another judge answer, another read_paths answer, or a session id from NOT_A_SESSION, None
    meaning absent). The root name is drawn from VALUES. Returns the environment, the choices, the calls made and
    run's result."""
    env = {}
    sid, j, r = rng.choice(FORCED_SESSIONS), 0, 0
    if not forced:
        away = rng.choice(('judge', 'read_paths', 'session'))
        if away == 'judge':
            j = rng.randrange(1, len(JUDGED))
        elif away == 'read_paths':
            r = rng.randrange(1, len(READS))
        else:
            sid = rng.choice(NOT_A_SESSION)
    if sid is not None:
        env[hook.SESSION_VAR] = sid
    v = rng.choice(VALUES)
    if v is not None:
        env[hook.ROOT_VAR] = v
    s = rng.randrange(len(STORED))
    calls = []
    with mock.patch.object(claude_code_store, 'judge', answer(JUDGED[j], calls, 'judge')), \
            mock.patch.object(claude_code_reads, 'read_paths', answer(READS[r], calls, 'read_paths')), \
            mock.patch.object(writer, 'add_reads', answer(STORED[s], calls, 'add_reads')):
        out = hook.run(b'{}', env, None, T0)
    return env, (j, r, s), calls, out


class LiveTieProperties(unittest.TestCase):

    def test_add_reads_is_called_if_and_only_if_a_live_tie(self):
        """TASK-073 AC7 (property): fixed seed 73, 50 cases, every second one forced to the live tie, the covered read
        and a session id from ('s-1', ' '), the others one step away from it (run_forced): add_reads is called if and
        only if judge's answer is JUDGED[0], read_paths' answer is READS[0] and the environment's session id is a
        non-empty str, in the order judge, read_paths, add_reads; the outcome is then "recorded" for STORED[0] and
        "lost" for every other STORED value."""
        rng = random.Random(73)
        forced_sessions, called = set(), 0
        for i in range(CASES):
            forced = i % 2 == 0
            env, (j, r, s), calls, out = run_forced(rng, forced)
            sid = env.get(hook.SESSION_VAR)
            if forced:
                forced_sessions.add(sid)
            expect = j == 0 and r == 0 and isinstance(sid, str) and sid != ''
            with self.subTest(case=i, env=env, choices=(j, r, s)):
                self.assertEqual('add_reads' in calls, expect)
                if expect:
                    called += 1
                    self.assertEqual(calls, ['judge', 'read_paths', 'add_reads'])
                    self.assertEqual(out['outcome'], 'recorded' if s == 0 else 'lost')
        self.assertEqual(forced_sessions, set(FORCED_SESSIONS))
        self.assertGreaterEqual(called, CASES // 2)


if __name__ == '__main__':
    unittest.main()

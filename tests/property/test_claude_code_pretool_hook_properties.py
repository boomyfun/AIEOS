"""Property tests of aieos_bootstrap.claude_code_pretool_hook (TASK-072 AC8), standard library only, fixed seeds, at
most 200 cases each: over arbitrary input bytes, generated environments and working folders, and generated answers of
the store lookup, the contract reader and the core path (stand-ins set on the module's own references), run never
raises for an Exception, its result has exactly its four keys, outcome and reason are always in OUTCOMES and REASONS,
the exit code is 0 exactly for an allow, the core is reached only after a live tie, and the findings hold no planted
text. main gives only 0 or 2. Stand-ins only: no file is written or opened."""

import datetime
import io
import json
import os
import random
import types
import unittest
from unittest import mock

from aieos_bootstrap import claude_code_pretool_hook as hook
from aieos_bootstrap import claude_code_channel, claude_code_hook, claude_code_store

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
ROOT = 'C:\\made-up-root'
PLANTED = 'PLANTEDTEXT'
CASES = 200
KEYS = {'exit_code', 'outcome', 'reason', 'findings'}
LEASE = {'task_id': 'TASK-001', 'fencing_token': {'epoch': PLANTED, 'counter': 1},
         'expires_at': T0 + datetime.timedelta(hours=1)}
VALUES = (None, '', ' ', 's-1', 'a b', PLANTED, ROOT, '0123456789abcdef0123456789abcdef01234567', 0, b'x')
JUDGED = ({'outcome': 'tied', 'reason': 'tied', 'findings': [], 'root': ROOT, 'lease': LEASE},
          {'outcome': 'tied', 'reason': 'tied', 'findings': [], 'root': '/made-up', 'lease': LEASE},
          {'outcome': 'tied', 'reason': 'tied', 'findings': [], 'root': ROOT, 'lease': None},
          {'outcome': 'enforce_nothing', 'reason': 'no_lease_row', 'findings': [], 'root': ROOT, 'lease': None},
          {'outcome': 'refuse', 'reason': 'session', 'findings': [PLANTED], 'root': ROOT, 'lease': None},
          {'outcome': 'refuse', 'reason': PLANTED, 'findings': [PLANTED], 'root': ROOT, 'lease': None},
          None, RuntimeError(PLANTED))
CONTRACTS = ({'result': 'read', 'reason': None, 'findings': [], 'task': 'TASK-001', 'base_commit': '0' * 40,
              'write_set': ['src/a.py'], 'forbidden': ['docs/**']},
             {'result': 'unreadable', 'reason': 'git', 'findings': [PLANTED], 'task': None, 'base_commit': None,
              'write_set': None, 'forbidden': None},
             None, KeyError(PLANTED))
CORES = ({'result': 'done', 'reason': None, 'findings': [PLANTED], 'core': None, 'decision': 'STOP: violation',
          'fencing_token': None, 'released': None},
         {'result': 'refused', 'reason': 'lease', 'findings': [PLANTED], 'core': None, 'decision': None,
          'fencing_token': None, 'released': None},
         {'result': 'refused', 'reason': PLANTED, 'findings': [], 'core': None, 'decision': None,
          'fencing_token': None, 'released': None},
         None, OSError(PLANTED))
TOOLS = ('Read', 'Grep', 'Glob', 'Write', 'Edit', 'Bash', 'PowerShell', PLANTED)


def answer(value, calls, name):
    def call(*args, **kwargs):
        calls.append(name)
        if isinstance(value, BaseException):
            raise value
        return value
    return call


def some_bytes(rng):
    kind = rng.randrange(4)
    if kind == 0:
        return bytes(rng.randrange(256) for _ in range(rng.randrange(40)))
    tool = rng.choice(TOOLS)
    value = {'tool_name': tool, 'tool_input': {'file_path': rng.choice((ROOT + '\\src\\a.py', ROOT + '\\' + PLANTED,
                                                                        PLANTED)),
                                               'command': rng.choice(('ls', 'git push', 'echo ' + PLANTED))}}
    if kind == 2:
        value['tool_use_id'] = rng.choice(('toolu_1', PLANTED + ' x', 7, 'y' * 201))
    text = json.dumps(value).encode('utf-8')
    return text if kind != 3 else text[:rng.randrange(len(text) + 1)]


def run_with(rng):
    env = {}
    for name in (hook.SESSION_VAR, hook.ROOT_VAR, hook.BASE_VAR, 'MADE_UP'):
        v = rng.choice(VALUES)
        if v is not None:
            env[name] = v
    j, k, m = rng.randrange(len(JUDGED)), rng.randrange(len(CONTRACTS)), rng.randrange(len(CORES))
    stdin = some_bytes(rng)
    folder = rng.choice((None, '', PLANTED, os.path.abspath(os.sep)))
    calls = []
    store = types.SimpleNamespace(judge=answer(JUDGED[j], calls, 'judge'), KEYS=claude_code_store.KEYS)
    reader = types.SimpleNamespace(read_contract=answer(CONTRACTS[k], calls, 'read_contract'))
    core = types.SimpleNamespace(session_violation=answer(CORES[m], calls, 'session_violation'))
    with mock.patch.object(hook, 'claude_code_store', store), mock.patch.object(hook, 'task_contract', reader), \
            mock.patch.object(hook, 'session_violation', core):
        out = hook.run(stdin, env, folder, T0, rng.choice((None, lambda: T0)))
    return (sorted(env.items(), key=repr), j, k, m, stdin, folder), calls, out


class AC8Properties(unittest.TestCase):

    def test_run_never_raises_and_keeps_its_form(self):
        """TASK-072 AC8: over generated cases run never raises for an Exception, gives exactly the four keys, outcome
        and reason in OUTCOMES and REASONS, exit 0 exactly for an allow, findings of fixed words with no planted text;
        the core is reached only after a live tie with a well-formed session id."""
        rng = random.Random(72)
        for _ in range(CASES):
            case, calls, out = run_with(rng)
            with self.subTest(case=repr(case)[:200]):
                self.assertEqual(set(out), KEYS)
                self.assertIn(out['outcome'], hook.OUTCOMES)
                self.assertIn(out['reason'], hook.REASONS)
                self.assertEqual(out['exit_code'] == 0, out['outcome'] == 'allow')
                self.assertIn(out['exit_code'], (0, 2))
                self.assertTrue(all(type(f) is str for f in out['findings']))
                self.assertNotIn(PLANTED, json.dumps(out['findings']))
                if 'session_violation' in calls:
                    self.assertEqual(calls[0], 'judge')
                    self.assertIn(case[1], (0, 1))
                    session = dict(case[0]).get(hook.SESSION_VAR)
                    self.assertIn(session, ('s-1', PLANTED, '0123456789abcdef0123456789abcdef01234567'))

    def test_equal_inputs_give_equal_results(self):
        """TASK-072 AC8: the same generated case twice gives the same result and the same calls."""
        for seed in range(20):
            first = run_with(random.Random(seed))
            second = run_with(random.Random(seed))
            self.assertEqual(first[1:], second[1:])

    def test_main_gives_only_zero_or_two(self):
        """TASK-072 AC8: main returns only 0 or 2 over generated run answers and exceptions, and its standard-error
        line holds a word of REASONS only."""
        rng = random.Random(720)
        answers = ({'exit_code': 0, 'outcome': 'allow', 'reason': 'tied_allow', 'findings': []},
                   {'exit_code': 2, 'outcome': 'refuse', 'reason': 'store', 'findings': [PLANTED]},
                   {'exit_code': 1, 'reason': PLANTED}, {}, None, ValueError(PLANTED))
        for _ in range(60):
            value = rng.choice(answers)
            err = io.StringIO()
            stdin = types.SimpleNamespace(buffer=io.BytesIO(some_bytes(rng)))
            with mock.patch.object(hook.sys, 'stdin', stdin), mock.patch.object(hook.sys, 'stderr', err), \
                    mock.patch.object(hook, 'run', answer(value, [], 'run')):
                code = hook.main()
            self.assertIn(code, (0, 2))
            self.assertNotIn(PLANTED, err.getvalue())
            if code == 2:
                word = err.getvalue()[len('AIEOS: this tool call was refused by the AIEOS hook ('):-2]
                self.assertIn(word, hook.REASONS)

    def test_stand_ins_keep_the_real_entry(self):
        """TASK-072 AC8: the entry and the channel stay real in these cases (only the tie, the reader and the core are
        stand-ins)."""
        self.assertIs(hook.claude_code_hook, claude_code_hook)
        self.assertIs(hook.claude_code_channel, claude_code_channel)


if __name__ == '__main__':
    unittest.main()

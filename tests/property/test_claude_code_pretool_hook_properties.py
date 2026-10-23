"""Property tests of aieos_bootstrap.claude_code_pretool_hook (TASK-072 AC8), standard library only, fixed seeds, at
most 200 cases each: over generated input bytes (random bytes and JSON calls built from small fixed sets), environments
and working folders drawn from small fixed sets, and generated answers of
the store lookup, the contract reader and the core path (stand-ins set on the module's own references), run never
raises for an Exception, its result has exactly its four keys, outcome and reason are always in OUTCOMES and REASONS,
the exit code is 0 exactly for an allow, the core is reached only after a live tie, and the findings hold no planted
text. main gives only 0 or 2. Stand-ins for the store lookup, the contract reader and the core path, except in
test_the_real_tie_over_folders, which runs the real store lookup read-only over the host's folders (host-dependent,
not hermetic); the entry and the channel are the real ones. No file is written."""

import datetime
import io
import json
import os
import random
import types
import unittest
from unittest import mock

from aieos_bootstrap import claude_code_pretool_hook as hook
from aieos_bootstrap import adapter, claude_code_channel, claude_code_hook, claude_code_store

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


def core_result(result, reason, findings, decision):
    out = dict.fromkeys(adapter.RESULT_KEYS)
    out.update(result=result, reason=reason, findings=list(findings), decision=decision)
    return out


CORES = (core_result('done', None, [PLANTED], 'STOP: violation'), core_result('refused', 'lease', [PLANTED], None),
         core_result('refused', PLANTED, [], None), None, OSError(PLANTED))
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

    def test_the_real_tie_over_folders(self):
        """TASK-072 AC8: with the real store lookup, no session id and no root, over generated working folders
        (absolute, missing, relative, empty, None) and generated bytes and environment values, run keeps its form, and
        nothing is read or recorded without a tie."""
        rng = random.Random(7272)
        top = os.path.abspath(os.sep)
        folders = (None, '', 'made-up-relative', top, os.path.join(top, 'made-up-missing-72'), PLANTED)
        for _ in range(60):
            calls = []
            env = {name: rng.choice(VALUES) for name in (hook.BASE_VAR, 'MADE_UP')}
            reader = types.SimpleNamespace(read_contract=answer(CONTRACTS[0], calls, 'read_contract'))
            core = types.SimpleNamespace(session_violation=answer(CORES[0], calls, 'session_violation'))
            folder = rng.choice(folders)
            with mock.patch.object(hook, 'task_contract', reader), mock.patch.object(hook, 'session_violation', core):
                out = hook.run(some_bytes(rng), env, folder, T0)
            with self.subTest(folder=folder):
                self.assertEqual(set(out), KEYS)
                self.assertIn(out['outcome'], hook.OUTCOMES)
                self.assertIn(out['reason'], ('enforce_nothing', 'store'))
                self.assertNotIn(PLANTED, json.dumps(out['findings']))
                self.assertEqual(calls, [])

    def test_main_runs_the_real_run(self):
        """TASK-072 AC8: main over generated input bytes and environments, with the real run and stand-ins for the
        tie, the reader and the core only, returns 0 or 2 and writes only the fixed line."""
        rng = random.Random(7200)
        for _ in range(40):
            env = {}
            for name in (hook.SESSION_VAR, hook.ROOT_VAR, hook.BASE_VAR):
                v = rng.choice(VALUES)
                if isinstance(v, str):
                    env[name] = v
            j, k, m = rng.randrange(len(JUDGED)), rng.randrange(len(CONTRACTS)), rng.randrange(len(CORES))
            calls, err = [], io.StringIO()
            stdin = types.SimpleNamespace(buffer=io.BytesIO(some_bytes(rng)))
            store = types.SimpleNamespace(judge=answer(JUDGED[j], calls, 'judge'), KEYS=claude_code_store.KEYS)
            reader = types.SimpleNamespace(read_contract=answer(CONTRACTS[k], calls, 'read_contract'))
            core = types.SimpleNamespace(session_violation=answer(CORES[m], calls, 'session_violation'))
            with mock.patch.object(hook.sys, 'stdin', stdin), mock.patch.object(hook.sys, 'stderr', err), \
                    mock.patch.dict(hook.os.environ, env, clear=True), \
                    mock.patch.object(hook, 'claude_code_store', store), \
                    mock.patch.object(hook, 'task_contract', reader), \
                    mock.patch.object(hook, 'session_violation', core):
                code = hook.main()
            self.assertIn(code, (0, 2))
            self.assertEqual(calls[0], 'judge')
            self.assertNotIn(PLANTED, err.getvalue())
            if code == 2:
                word = err.getvalue()[len('AIEOS: this tool call was refused by the AIEOS hook ('):-2]
                self.assertIn(word, hook.REASONS)
            else:
                self.assertEqual(err.getvalue(), '')


class AC6TheRealEntryAndChannel(unittest.TestCase):

    def test_the_entry_and_the_channel_stay_real(self):
        """TASK-074 AC6: with the store lookup, the contract reader and the core path replaced as run_with replaces
        them, the entry and the channel are the real modules during run, and a tied Write outside the write-set
        reaches the core with a record that record_findings accepts."""
        calls, seen, passed = [], [], []

        def read_contract(*args, **kwargs):
            calls.append('read_contract')
            seen.append((hook.claude_code_hook is claude_code_hook, hook.claude_code_channel is claude_code_channel))
            return CONTRACTS[0]

        def session_violation(*args, **kwargs):
            calls.append('session_violation')
            passed.append(args[2])
            return CORES[0]
        store = types.SimpleNamespace(judge=answer(JUDGED[0], calls, 'judge'), KEYS=claude_code_store.KEYS)
        reader = types.SimpleNamespace(read_contract=read_contract)
        core = types.SimpleNamespace(session_violation=session_violation)
        env = {hook.SESSION_VAR: 's-1', hook.ROOT_VAR: ROOT, hook.BASE_VAR: VALUES[7]}
        stdin = json.dumps({'tool_name': 'Write', 'tool_input': {'file_path': ROOT + '\\src\\b.py', 'content': 'x'},
                            'tool_use_id': 'toolu_1'}).encode('utf-8')
        with mock.patch.object(hook, 'claude_code_store', store), mock.patch.object(hook, 'task_contract', reader), \
                mock.patch.object(hook, 'session_violation', core):
            out = hook.run(stdin, env, None, T0)
        self.assertEqual(seen, [(True, True)])
        self.assertEqual(out['reason'], 'recorded')
        self.assertEqual(calls, ['judge', 'read_contract', 'session_violation'])
        self.assertEqual(claude_code_channel.record_findings(passed[0]), [])


if __name__ == '__main__':
    unittest.main()

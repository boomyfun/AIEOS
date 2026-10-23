"""Unit tests of aieos_bootstrap.claude_code_pretool_hook (TASK-072 AC1 to AC9): run's flow with stand-ins set on the
module's own references to claude_code_store, task_contract, claude_code_hook, claude_code_channel and
session_violation, and a stand-in gitread.run for the contract reader's own use; main with stand-ins for standard
input, standard error, the environment, the working folder and the clock; the AST check of the run seam with hostile
samples and broken copies; the imports and the docstring's words. No test writes a file, makes a folder or opens a
store; sources are read by pathlib's read_bytes relative to this file. The real-store cases of step 1 are in
tests/integration/test_writer_files.py."""

import ast
import datetime
import hashlib
import io
import json
import os
import pathlib
import re
import types
import unittest
from unittest import mock

from aieos_bootstrap import claude_code_pretool_hook as hook
from aieos_bootstrap import (adapter, claude_code, claude_code_channel, claude_code_hook, claude_code_read_hook,
                             claude_code_store, gitread, task_contract)

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
WIN_ROOT = 'C:\\made-up-root'
SID = 'made-up-session-1'
BASE = '0123456789abcdef0123456789abcdef01234567'
TASK = 'TASK-001'
LEASE = {'task_id': TASK, 'fencing_token': {'epoch': 'e', 'counter': 1}, 'expires_at': T0 + datetime.timedelta(hours=1)}
ENV = {hook.SESSION_VAR: SID, hook.ROOT_VAR: WIN_ROOT, hook.BASE_VAR: BASE}
KEYS = {'exit_code', 'outcome', 'reason', 'findings'}
SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap'
REPO = str(pathlib.Path(__file__).resolve().parents[2])
TEXT = (SRC / 'claude_code_pretool_hook.py').read_bytes().decode('utf-8')
RECORDER = 'claude_code_pretool_hook, session ' + SID
NOT_READABLE = 'the task contract is not readable at the base'
DEFAULT = object()


def call_bytes(tool, tool_input, tool_use_id='toolu_made-up-1'):
    value = {'session_id': 'made-up-input-session', 'tool_name': tool, 'tool_input': tool_input}
    if tool_use_id is not None:
        value['tool_use_id'] = tool_use_id
    return json.dumps(value).encode('utf-8')


READ = call_bytes('Read', {'file_path': WIN_ROOT + '\\src\\a.py'})
WRITE_IN = call_bytes('Write', {'file_path': WIN_ROOT + '\\src\\a.py', 'content': 'x'})
WRITE_OUT = call_bytes('Write', {'file_path': WIN_ROOT + '\\src\\b.py', 'content': 'x'})


def tied(root=WIN_ROOT, lease=LEASE):
    return {'outcome': 'tied', 'reason': 'tied', 'findings': [], 'root': root, 'lease': lease}


def refused(reason):
    return {'outcome': 'refuse', 'reason': reason, 'findings': ['%s: made-up' % reason], 'root': None, 'lease': None}


def readable(write_set=('src/a.py',)):
    return {'result': 'read', 'reason': None, 'findings': [], 'task': TASK, 'base_commit': BASE,
            'write_set': list(write_set), 'forbidden': ['docs/**']}


def shell_lists(allowlist=()):
    return {'result': 'read', 'policy': list(allowlist), 'contract': list(allowlist), 'allowlist': list(allowlist),
            'findings': []}


def unreadable(reason):
    return {'result': 'unreadable', 'reason': reason, 'findings': ['%s: made-up' % reason], 'task': None,
            'base_commit': None, 'write_set': None, 'forbidden': None}


def done():
    out = dict.fromkeys(adapter.RESULT_KEYS)
    out.update(result='done', findings=[], decision='STOP: violation')
    return out


class Calls:
    """The stand-ins and the order of their calls."""

    def __init__(self, judge=DEFAULT, contract=DEFAULT, core=DEFAULT, shell=DEFAULT):
        self.log, self.judge_args, self.contract_args, self.core_args = [], [], [], []
        self.shell_args = []
        self.judge_answer = tied() if judge is DEFAULT else judge
        self.contract_answer = readable() if contract is DEFAULT else contract
        self.core_answer = done() if core is DEFAULT else core
        self.shell_answer = shell_lists() if shell is DEFAULT else shell

    def judge(self, *args):
        self.log.append('judge')
        self.judge_args.append(args)
        answer = self.judge_answer(len(self.judge_args)) if callable(self.judge_answer) else self.judge_answer
        if isinstance(answer, BaseException):
            raise answer
        return answer

    def read_contract(self, *args, **kwargs):
        self.log.append('read_contract')
        self.contract_args.append((args, kwargs))
        return self.contract_answer

    def entry(self, *args, **kwargs):
        self.log.append('entry')
        return claude_code_hook.entry(*args, **kwargs)

    def record_findings(self, record):
        self.log.append('record_findings')
        return claude_code_channel.record_findings(record)

    def redact(self, record):
        self.log.append('redact')
        return claude_code_channel.redact(record)

    def session_violation(self, *args, **kwargs):
        self.log.append('session_violation')
        self.core_args.append((args, kwargs))
        return self.core_answer

    def clock(self):
        self.log.append('clock')
        return T0 + datetime.timedelta(seconds=5)

    def read_allowlist(self, *args, **kwargs):
        self.log.append('read_allowlist')
        self.shell_args.append((args, kwargs))
        if isinstance(self.shell_answer, BaseException):
            raise self.shell_answer
        return self.shell_answer

    def patches(self, channel=None, entry=None):
        return [mock.patch.object(hook, 'claude_code_store', types.SimpleNamespace(judge=self.judge,
                                                                                   KEYS=claude_code_store.KEYS)),
                mock.patch.object(hook, 'task_contract', types.SimpleNamespace(read_contract=self.read_contract)),
                mock.patch.object(hook, 'claude_code_hook', types.SimpleNamespace(
                    entry=entry or self.entry, RESULT_KEYS=claude_code_hook.RESULT_KEYS)),
                mock.patch.object(hook, 'claude_code_channel', channel or types.SimpleNamespace(
                    record_findings=self.record_findings, redact=self.redact,
                    RECORDER_JOIN=claude_code_channel.RECORDER_JOIN)),
                mock.patch.object(hook, 'session_violation',
                                  types.SimpleNamespace(session_violation=self.session_violation)),
                mock.patch.object(hook, 'claude_code_shell_allow',
                                  types.SimpleNamespace(read_allowlist=self.read_allowlist))]

    def run(self, stdin=READ, env=ENV, folder=None, now=T0, clock='own', channel=None, entry=None):
        ps = self.patches(channel, entry)
        for p in ps:
            p.start()
        try:
            return hook.run(stdin, env, folder, now, self.clock if clock == 'own' else clock)
        finally:
            for p in reversed(ps):
                p.stop()

    def passed(self):
        self.assert_one()
        return self.core_args[0][0][2]

    def assert_one(self):
        if len(self.core_args) != 1:
            raise AssertionError('session_violation called %d times' % len(self.core_args))


class AC1TheTie(unittest.TestCase):

    def test_enforce_nothing_allows(self):
        """TASK-072 AC1: "enforce_nothing" gives exit 0, outcome "allow", reason "enforce_nothing", and nothing more is
        called."""
        c = Calls(judge={'outcome': 'enforce_nothing', 'reason': 'no_store_found', 'findings': [], 'root': None,
                         'lease': None})
        self.assertEqual(c.run(env={}), {'exit_code': 0, 'outcome': 'allow', 'reason': 'enforce_nothing',
                                         'findings': []})
        self.assertEqual(c.log, ['judge'])

    def test_each_store_reason_is_kept_and_nothing_recorded(self):
        """TASK-072 AC1: each fixed refusal reason of the store lookup gives exit 2, "refuse", reason "store" and that
        word as the one finding; an unknown or non-string word gives "store: other"; nothing else is called."""
        words = ('argument', 'root_without_session', 'session_without_root', 'search', 'entry', 'root', 'no_store',
                 'link', 'unreadable', 'tables', 'lease_row_without_session', 'no_lease_row', 'session', 'ended',
                 'leases')
        self.assertEqual(hook.STORE_REASONS, words)
        sources = ((SRC / 'claude_code_store.py').read_bytes().decode('utf-8')
                   + (SRC / 'writer.py').read_bytes().decode('utf-8'))
        for word in words:
            self.assertTrue(re.search(r"_(?:refuse|refused|named)\('" + word + "'", sources), word)
        for word in words + ('made-up-word', 7, None):
            with self.subTest(word=word):
                c = Calls(judge=refused(word) if isinstance(word, str) else dict(refused('x'), reason=word))
                out = c.run()
                want = [word] if word in words else ['store: other']
                self.assertEqual(out, {'exit_code': 2, 'outcome': 'refuse', 'reason': 'store', 'findings': want})
                self.assertEqual(c.log, ['judge'])

    def test_the_names_are_read_and_passed(self):
        """TASK-072 AC1: judge gets the session id, the root, the working folder and now, unchanged."""
        c = Calls(judge=refused('session'))
        c.run(folder='made-up-folder')
        self.assertEqual(c.judge_args, [(SID, WIN_ROOT, 'made-up-folder', T0)])
        c = Calls(judge=refused('argument'))
        c.run(env={})
        self.assertEqual(c.judge_args, [(None, None, None, T0)])

    def test_a_session_id_out_of_form(self):
        """TASK-072 AC1: a tie whose session id is not of [A-Za-z0-9._-]{1,128} gives "store: session id form" and
        nothing is read or recorded."""
        for sid in ('a b', 'a/b', 'é', 'x' * 129, '', 7):
            with self.subTest(sid=sid):
                c = Calls()
                out = c.run(env=dict(ENV, **{hook.SESSION_VAR: sid}))
                self.assertEqual(out, {'exit_code': 2, 'outcome': 'refuse', 'reason': 'store',
                                       'findings': ['store: session id form']})
                self.assertEqual(c.log, ['judge'])
        c = Calls()
        self.assertEqual(c.run(stdin=WRITE_OUT, env=dict(ENV, **{hook.SESSION_VAR: 'x' * 128}))['reason'],
                         'recorded')

    def test_other_shapes_of_judge_give_entry(self):
        """TASK-072 AC1: any other shape of judge's answer gives reason "entry", nothing read or recorded."""
        bad = [None, [], {}, dict(tied(), extra=1), dict(tied(), outcome='made-up'), dict(tied(), reason='made-up'),
               tied(lease=None), tied(lease={'task_id': 7}), tied(lease={'task_id': 'TASK-x'}), tied(root=''),
               tied(root=None)]
        for answer in bad:
            with self.subTest(answer=answer):
                c = Calls(judge=answer)
                out = c.run()
                self.assertEqual((out['exit_code'], out['reason'], out['findings']), (2, 'entry', ['entry: judge']))
                self.assertEqual(c.log, ['judge'])


def recorded_contract_case(test, c, out, reason):
    test.assertEqual(out, {'exit_code': 2, 'outcome': 'refuse', 'reason': reason, 'findings': [hook._FINDING[reason]]})
    record = c.passed()
    test.assertEqual(claude_code_channel.record_findings(record), [])
    test.assertEqual(claude_code_channel.redact(record), record)
    test.assertEqual(record['refers_to'], NOT_READABLE)
    test.assertEqual(record['evidence_type'], 'write_outside_write_set')
    test.assertEqual(record['subject'], TASK)
    test.assertEqual(record['recorder'], claude_code.RECORDER + ', for ' + RECORDER)
    args = c.core_args[0][0]
    test.assertEqual((args[0], args[1], args[4]), (WIN_ROOT, SID, RECORDER))
    test.assertIn('/pretool-contract/', args[3])
    test.assertEqual(record['record_id'], args[3] + '/record')
    test.assertEqual(c.core_args[0][1], {})


class AC2TheBase(unittest.TestCase):

    def test_a_bad_base_is_recorded_without_a_read(self):
        """TASK-072 AC2: AIEOS_BASE absent, empty, of 64 characters, with an upper-case letter or a space gives exit 2,
        reason "base", one record passed with the fixed refers_to, and the contract is not read."""
        for base in (None, '', 'a' * 64, BASE.upper(), BASE[:-1] + 'G', BASE + ' ', BASE[:-1], 7):
            with self.subTest(base=base):
                env = dict(ENV)
                if base is None:
                    del env[hook.BASE_VAR]
                else:
                    env[hook.BASE_VAR] = base
                c = Calls()
                recorded_contract_case(self, c, c.run(env=env), 'base')
                self.assertEqual(c.log, ['judge', 'record_findings', 'redact', 'clock', 'session_violation'])

    def test_the_reader_asks_the_base_first_and_never_head(self):
        """TASK-072 AC2: with a stand-in gitread.run on the contract reader's call, the first id asked is AIEOS_BASE
        and "HEAD" is never asked; a well-formed base naming no commit gives the recorded STOP, reason "contract"."""
        asked = []

        def fake_run(root, args, timeout):
            asked.append(args)
            return {'exit': 128, 'out': b'', 'err': b'', 'error': None}
        c = Calls(judge=tied(root=REPO))
        ps = c.patches()
        ps[1] = mock.patch.object(hook, 'task_contract', task_contract)
        for p in ps:
            p.start()
        try:
            with mock.patch.object(gitread, 'run', fake_run):
                out = hook.run(READ, ENV, None, T0, c.clock)
        finally:
            for p in reversed(ps):
                p.stop()
        self.assertEqual(asked, [['cat-file', '-p', BASE]])
        self.assertFalse([a for a in asked if 'HEAD' in a])
        self.assertEqual(out['reason'], 'contract')
        self.assertEqual(c.passed()['refers_to'], NOT_READABLE)

    def test_the_contracts_own_base_commit_gives_contract_missing(self):
        """TASK-072 AC2: an AIEOS_BASE equal to the contract's own input_state.base_commit, at which the contract file
        does not exist, gives the recorded STOP, reason "contract" (a stand-in object store without the file)."""
        tree, docs, tasks = 'a' * 40, 'b' * 40, 'c' * 40
        objects = {BASE: ('tree %s\nauthor A <a> 1 +0000\ncommitter A <a> 1 +0000\n\nm\n' % tree).encode(),
                   tree: ('040000 tree %s\tdocs\n' % docs).encode(),
                   docs: ('040000 tree %s\ttasks\n' % tasks).encode(),
                   tasks: ('100644 blob %s\tTASK-000.yaml\n' % ('d' * 40)).encode()}
        asked = []

        def fake_run(root, args, timeout):
            asked.append(args[2])
            return {'exit': 0, 'out': objects[args[2]], 'err': b'', 'error': None}
        c = Calls(judge=tied(root=REPO))
        ps = c.patches()
        ps[1] = mock.patch.object(hook, 'task_contract', task_contract)
        for p in ps:
            p.start()
        try:
            with mock.patch.object(gitread, 'run', fake_run):
                out = hook.run(READ, ENV, None, T0, c.clock)
        finally:
            for p in reversed(ps):
                p.stop()
        self.assertEqual(asked, [BASE, tree, docs, tasks])
        self.assertEqual(out['reason'], 'contract')
        self.assertEqual(c.passed()['refers_to'], NOT_READABLE)


class AC3TheContract(unittest.TestCase):

    def test_every_unreadable_reason_is_recorded(self):
        """TASK-072 AC3: each "unreadable" reason of the contract reader, and any other answer, gives exit 2, reason
        "contract" and step 3's record in the judge's form, passing record_findings, unchanged by redact, its ids
        holding "/pretool-contract/"; the reader gets the root, the base and the task, and no runner."""
        answers = [unreadable(r) for r in ('argument', 'git', 'tree', 'bytes', 'parse', 'task', 'entry')]
        answers += [None, {}, readable(write_set=()), dict(readable(), write_set=None), dict(readable(), result='x'),
                    dict(readable(), write_set=[7])]
        for answer in answers:
            with self.subTest(answer=answer):
                c = Calls(contract=answer)
                recorded_contract_case(self, c, c.run(), 'contract')
                self.assertEqual(c.contract_args, [((WIN_ROOT, BASE, TASK), {})])

    def test_a_read_call_is_recorded_too(self):
        """TASK-072 AC3: an unreadable contract on a Read call gives the same recorded STOP (step 3 before step 4)."""
        c = Calls(contract=unreadable('git'))
        recorded_contract_case(self, c, c.run(stdin=READ), 'contract')
        self.assertNotIn('entry', c.log)

    def test_the_contracts_write_set_is_the_one_judged(self):
        """TASK-072 AC3: a readable contract's write-set is the one judged: a write inside it is allowed, reason
        "tied_allow"; one outside it is refused and recorded."""
        c = Calls(contract=readable(('src/a.py',)))
        self.assertEqual(c.run(stdin=WRITE_IN), {'exit_code': 0, 'outcome': 'allow', 'reason': 'tied_allow',
                                                 'findings': []})
        self.assertEqual(c.core_args, [])
        c = Calls(contract=readable(('src/b.py',)))
        self.assertEqual(c.run(stdin=WRITE_IN)['reason'], 'recorded')
        self.assertEqual(c.passed()['refers_to'], 'src/a.py')


class AC4TheJudgement(unittest.TestCase):

    def test_allow_gives_tied_allow(self):
        """TASK-072 AC4: a Read, Grep or Glob call and a write inside the write-set give exit 0, reason "tied_allow",
        and nothing passed to the core."""
        for stdin in (READ, call_bytes('Grep', {'pattern': 'x'}), call_bytes('Glob', {'pattern': '*'}), WRITE_IN):
            with self.subTest(stdin=stdin):
                c = Calls()
                self.assertEqual(c.run(stdin=stdin), {'exit_code': 0, 'outcome': 'allow', 'reason': 'tied_allow',
                                                      'findings': []})
                self.assertNotIn('session_violation', c.log)

    def test_uncovered_is_refused_without_a_record(self):
        """TASK-072 AC4: an uncovered call (an unjudged tool, a relative path, bytes that are not JSON) gives exit 2,
        reason "uncovered", nothing passed."""
        for stdin in (call_bytes('Task', {}), call_bytes('Write', {'file_path': 'src/a.py'}), b'not json',
                      b'\xef\xbb\xbf{}'):
            with self.subTest(stdin=stdin):
                c = Calls()
                self.assertEqual(c.run(stdin=stdin), {'exit_code': 2, 'outcome': 'refuse', 'reason': 'uncovered',
                                                      'findings': [hook._FINDING['uncovered']]})
                self.assertNotIn('session_violation', c.log)

    def test_the_three_concerns_are_recorded(self):
        """TASK-072 AC4: under the empty allowlist a shell call is refused and recorded (shell_not_allowed), a git push
        (git_push_refused) and a write outside the write-set (write_outside_write_set)."""
        cases = ((call_bytes('Bash', {'command': 'ls'}), 'shell_not_allowed'),
                 (call_bytes('PowerShell', {'command': 'dir'}), 'shell_not_allowed'),
                 (call_bytes('Bash', {'command': 'git push origin main'}), 'git_push_refused'),
                 (WRITE_OUT, 'write_outside_write_set'))
        for stdin, kind in cases:
            with self.subTest(kind=kind):
                c = Calls()
                self.assertEqual(c.run(stdin=stdin), {'exit_code': 2, 'outcome': 'refuse', 'reason': 'recorded',
                                                      'findings': [hook._FINDING['recorded']]})
                self.assertEqual(c.passed()['evidence_type'], kind)
                self.assertIn('/pretool/', c.core_args[0][0][3])

    def test_refusals_without_a_record(self):
        """TASK-072 AC4: the entry's argument refusal (stdin not bytes), the judge's argument refusal (a POSIX root),
        the entry's allowlist_form refusal and the judge's record refusal (stand-in entries) give exit 2, reason
        "no_record", nothing passed to the core. TASK-074 AC5: the first two cases assert that nothing reached the core
        too."""
        c = Calls()
        self.assertEqual(c.run(stdin='{}')['reason'], 'no_record')
        self.assertEqual(c.core_args, [])
        c = Calls(judge=tied(root='/made-up-root'))
        self.assertEqual(c.run(stdin=WRITE_OUT)['reason'], 'no_record')
        self.assertEqual(c.core_args, [])
        for reason in ('allowlist_form', 'record', 'argument'):
            with self.subTest(reason=reason):
                c = Calls()
                answer = claude_code_hook._result('refuse', None, reason, ['made-up'])
                out = c.run(stdin=WRITE_OUT, entry=lambda *a: answer)
                self.assertEqual(out, {'exit_code': 2, 'outcome': 'refuse', 'reason': 'no_record',
                                       'findings': [hook._FINDING['no_record']]})
                self.assertEqual(c.core_args, [])

    def test_the_entry_gets_the_contract_and_an_empty_allowlist(self):
        """TASK-072 AC4: the entry gets the input bytes, the root, the task, the contract's write-set, an empty
        allowlist, the record id and the recorder; another shape of its answer gives reason "entry"."""
        got = []

        def entry(*args):
            got.append(args)
            return None
        c = Calls()
        out = c.run(stdin=WRITE_OUT, entry=entry)
        self.assertEqual((out['reason'], out['findings']), ('entry', ['entry: judgement']))
        stdin, root, task, write_set, allowlist, record_id, recorder = got[0]
        self.assertEqual((stdin, root, task, write_set, allowlist, recorder),
                         (WRITE_OUT, WIN_ROOT, TASK, ['src/a.py'], [], RECORDER))
        self.assertEqual(record_id, SID + '/pretool/toolu_made-up-1/record')
        for answer in ({}, dict(claude_code_hook._result('allow', 'read', 'read'), verdict='made-up')):
            with self.subTest(answer=answer):
                self.assertEqual(Calls().run(entry=lambda *a: answer)['reason'], 'entry')


class AC5TheRecord(unittest.TestCase):

    def test_the_recorder_and_the_redacted_record(self):
        """TASK-072 AC5: the recorder text holds the session id; the record's recorder is claude_code.RECORDER +
        ", for " + it; the record passed is redact's, with no command text."""
        c = Calls()
        c.run(stdin=call_bytes('Bash', {'command': 'echo made-up-secret-text'}))
        record = c.passed()
        self.assertEqual(c.core_args[0][0][4], RECORDER)
        self.assertEqual(record['recorder'], claude_code.RECORDER + ', for ' + RECORDER)
        self.assertEqual(record['refers_to'], claude_code_channel.REDACTED['shell_not_allowed'])
        self.assertNotIn('made-up-secret-text', json.dumps(record))

    def test_a_record_out_of_form_is_not_passed(self):
        """TASK-072 AC5: a record failing record_findings, a subject or a recorder that does not match, and redact
        giving None each give exit 2, reason "record_form", nothing passed."""
        good = claude_code.judge({'tool_name': 'Write', 'tool_input': {'file_path': WIN_ROOT + '\\x'}}, WIN_ROOT,
                                 TASK, ['src/a.py'], [], 'r', RECORDER)['record']
        records = [dict(good, fact_kind='made-up'), dict(good, subject='TASK-002'),
                   dict(good, recorder=claude_code.RECORDER + ', for another')]
        for record in records:
            with self.subTest(record=record):
                c = Calls()
                answer = claude_code_hook._result('refuse', 'write', 'write_set', (), record)
                out = c.run(stdin=WRITE_OUT, entry=lambda *a: answer)
                self.assertEqual(out, {'exit_code': 2, 'outcome': 'refuse', 'reason': 'record_form',
                                       'findings': [hook._FINDING['record_form']]})
                self.assertEqual(c.core_args, [])
        c = Calls()
        channel = types.SimpleNamespace(record_findings=claude_code_channel.record_findings, redact=lambda r: None,
                                        RECORDER_JOIN=claude_code_channel.RECORDER_JOIN)
        self.assertEqual(c.run(stdin=WRITE_OUT, channel=channel)['reason'], 'record_form')
        self.assertEqual(c.core_args, [])

    def test_the_ids(self):
        """TASK-072 AC5: event_id is "<session id>/pretool/<tool_use_id>" for a tool_use_id of the form, else the
        SHA-256 fallback of the input bytes (a missing, bad or unparsable tool_use_id); record_id adds "/record"; each
        id within 128 + 21 + 200 + 7 characters. TASK-074 AC5: each fallback input also reaches the core through run,
        with a stand-in entry answering a refusal with a record."""
        c = Calls()
        c.run(stdin=WRITE_OUT)
        self.assertEqual(c.core_args[0][0][3], SID + '/pretool/toolu_made-up-1')
        self.assertEqual(c.passed()['record_id'], SID + '/pretool/toolu_made-up-1/record')
        bad = [call_bytes('Write', {'file_path': WIN_ROOT + '\\src\\b.py'}, tool_use_id=v)
               for v in (None, 'a b', 'x' * 201, 7, '', 'é')]
        bad.append(b'{"tool_name": "Write", "tool_input": {"file_path": "C:\\\\made-up-root\\\\b"}, '
                   b'"tool_use_id": "a", "tool_use_id": "b"}')
        for stdin in bad:
            with self.subTest(stdin=stdin):
                c = Calls()
                c.run(stdin=stdin)
                want = SID + '/pretool/sha256-' + hashlib.sha256(stdin).hexdigest()
                if c.core_args:
                    self.assertEqual(c.core_args[0][0][3], want)
                else:
                    self.assertEqual(hook._ids(SID, stdin, 'pretool')[0], want)
                c = Calls()
                c.run(stdin=stdin, entry=lambda *a: refusal_with_record())
                c.assert_one()
                self.assertEqual(c.core_args[0][0][3], want)
        longest = hook._ids('x' * 128, call_bytes('Read', {}, 'y' * 200), 'pretool-contract')
        self.assertEqual(len(longest[0]), 128 + 18 + 200)
        self.assertLessEqual(len(longest[1]), 128 + 21 + 200 + 7)
        for text in longest:
            self.assertIsNone(re.search(r'\s', text))
        self.assertEqual(hook._ids(SID, '{}', 'pretool')[0], SID + '/pretool/sha256-' + hashlib.sha256(b'').hexdigest())

    def test_a_bytes_subclass_hashes_its_bytes(self):
        """TASK-072 AC5: the SHA-256 fallback hashes the actual bytes of a bytes subclass, so two such inputs get two
        ids."""
        class Sub(bytes):
            pass
        ids = []
        for path in ('b.py', 'c.py'):
            data = call_bytes('Write', {'file_path': WIN_ROOT + '\\src\\' + path}, tool_use_id=None)
            c = Calls()
            c.run(stdin=Sub(data))
            self.assertEqual(c.core_args[0][0][3], SID + '/pretool/sha256-' + hashlib.sha256(data).hexdigest())
            ids.append(c.core_args[0][0][3])
        self.assertNotEqual(ids[0], ids[1])

    def test_a_repeat_after_a_stop_is_refused_at_the_tie(self):
        """TASK-072 AC5: a repeat of an identical call after a recorded STOP is refused at step 1 with nothing
        recorded (a stand-in tie that answers "ended" on the second call)."""
        c = Calls(judge=lambda n: tied() if n == 1 else refused('ended'))
        self.assertEqual(c.run(stdin=WRITE_OUT)['reason'], 'recorded')
        self.assertEqual(c.run(stdin=WRITE_OUT), {'exit_code': 2, 'outcome': 'refuse', 'reason': 'store',
                                                  'findings': ['ended']})
        self.assertEqual(len(c.core_args), 1)

    def test_the_core_results(self):
        """TASK-072 AC5: a "lease" result gives "lease_lost"; a "done" with the core's duplicate (a stand-in on this
        module's reference) gives "recorded"; any other result gives "core"; the findings hold nothing of the result."""
        lease = dict(done(), result='refused', reason='lease', findings=['lease: made-up'], decision=None)
        dup = dict(done(), core={'result': 'done', 'reason': None, 'findings': [], 'appended': [],
                                 'duplicate': ['made-up-event'], 'released': None})
        others = (dict(lease, reason='argument'), dict(lease, reason='entry'), None, [], {'result': 'made-up'})
        cases = [(lease, 'lease_lost'), (dup, 'recorded')] + [(o, 'core') for o in others]
        for answer, reason in cases:
            with self.subTest(answer=answer):
                c = Calls(core=answer)
                self.assertEqual(c.run(stdin=WRITE_OUT), {'exit_code': 2, 'outcome': 'refuse', 'reason': reason,
                                                          'findings': [hook._FINDING[reason]]})

    def test_the_clock_is_read_once_just_before_the_core(self):
        """TASK-072 AC5: clock is called once in every path that reaches session_violation, the bad-base path included,
        after every other step and immediately before session_violation, and its value is the now passed to it."""
        paths = ((WRITE_OUT, ENV, None, ['judge', 'read_contract', 'entry', 'record_findings', 'redact', 'clock',
                                         'session_violation']),
                 (READ, ENV, unreadable('git'), ['judge', 'read_contract', 'record_findings', 'redact', 'clock',
                                                 'session_violation']),
                 (READ, dict(ENV, **{hook.BASE_VAR: ''}), None, ['judge', 'record_findings', 'redact', 'clock',
                                                                  'session_violation']))
        for stdin, env, contract, log in paths:
            with self.subTest(log=log):
                c = Calls(contract=readable() if contract is None else contract)
                c.run(stdin=stdin, env=env)
                self.assertEqual(c.log, log)
                self.assertEqual(c.core_args[0][0][5], T0 + datetime.timedelta(seconds=5))
        c = Calls()
        c.run(stdin=WRITE_OUT, clock=None)
        self.assertEqual(c.core_args[0][0][5], T0)

    def test_a_raising_or_refused_clock(self):
        """TASK-072 AC5: a clock that raises gives reason "entry"; one whose value the core path refuses gives
        "core" (the real session_violation, which refuses a naive time before any lookup)."""
        def raising():
            raise OSError('made-up')
        c = Calls()
        self.assertEqual(c.run(stdin=WRITE_OUT, clock=raising), {'exit_code': 2, 'outcome': 'refuse',
                                                                  'reason': 'entry', 'findings': ['entry: OSError']})
        self.assertEqual(c.core_args, [])
        c = Calls()
        ps = c.patches()[:4]
        for p in ps:
            p.start()
        try:
            out = hook.run(WRITE_OUT, ENV, None, T0, lambda: datetime.datetime(2026, 10, 11, 12, 0, 0))
        finally:
            for p in reversed(ps):
                p.stop()
        self.assertEqual(out['reason'], 'core')


SEAM_MODULES = {'task_contract': ('read_contract', 3), 'session_violation': ('session_violation', 6),
                'claude_code_shell_allow': ('read_allowlist', 3)}
SEAM_STRINGS = ('task_contract', 'session_violation', 'read_contract', 'claude_code_shell_allow', 'read_allowlist')
SEAM_NAMES = {'setattr', 'delattr', 'globals', 'vars', 'locals', 'eval', 'exec', 'compile', 'attrgetter'}
SEAM_ATTRS = {'writer', 'adapter', 'eventlog', 'violation', 'read_set_record', 'observe'}


def seam_findings(text):
    """The run seam's AST check (TASK-072 AC5, D-1703 C1, t72b-R1b-2, R1b-9, t72c-R1c-3, R1c-5): the findings of a
    module text; an empty list means the seam is closed."""
    tree = ast.parse(text)
    findings, parent, docs = [], {}, set()
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n):
            parent[id(c)] = n
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body \
                and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant) \
                and isinstance(n.body[0].value.value, str):
            docs.add(id(n.body[0].value))
    binders = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            if (n.module or '') in ('aieos_bootstrap.task_contract', 'aieos_bootstrap.session_violation',
                                    'aieos_bootstrap.claude_code_shell_allow'):
                findings.append('from-import out of %s' % n.module)
            for a in n.names:
                if (a.asname or a.name) in SEAM_MODULES or a.name in SEAM_MODULES:
                    ok = n.module == 'aieos_bootstrap' and a.asname is None and n in tree.body and len(n.names) == 1
                    binders.append(a.name)
                    if not ok:
                        findings.append('a binder of %s other than the module-level import' % a.name)
        elif isinstance(n, ast.Import):
            for a in n.names:
                if any(m in a.name for m in SEAM_MODULES) or (a.asname or '') in SEAM_MODULES:
                    findings.append('an import of %s' % a.name)
        elif isinstance(n, ast.alias):
            continue
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name in SEAM_MODULES:
            findings.append('a def or class named %s' % n.name)
        elif isinstance(n, ast.arg) and n.arg in SEAM_MODULES:
            findings.append('an argument named %s' % n.arg)
        elif isinstance(n, ast.ExceptHandler) and n.name in SEAM_MODULES:
            findings.append('an except name %s' % n.name)
        elif isinstance(n, (ast.Global, ast.Nonlocal)) and set(n.names) & set(SEAM_MODULES):
            findings.append('a global or nonlocal name')
        elif isinstance(n, (ast.MatchAs, ast.MatchStar)) and n.name in SEAM_MODULES:
            findings.append('a match name')
        elif isinstance(n, ast.MatchMapping) and n.rest in SEAM_MODULES:
            findings.append('a match name')
        elif isinstance(n, ast.Name):
            if n.id in SEAM_NAMES:
                findings.append('the name %s' % n.id)
            if n.id in SEAM_MODULES:
                if not isinstance(n.ctx, ast.Load):
                    findings.append('%s bound or deleted' % n.id)
                    continue
                attr, count = SEAM_MODULES[n.id]
                p = parent.get(id(n))
                call = parent.get(id(p))
                if not (isinstance(p, ast.Attribute) and p.value is n and p.attr == attr and isinstance(call, ast.Call)
                        and call.func is p and len(call.args) == count and call.keywords == []
                        and not any(isinstance(a, ast.Starred) for a in call.args)):
                    findings.append('%s used other than as the call %s.%s with %d arguments'
                                    % (n.id, n.id, attr, count))
            elif n.id in ('read_contract', 'read_allowlist'):
                findings.append('the name %s' % n.id)
        elif isinstance(n, ast.Attribute):
            if n.attr in SEAM_ATTRS:
                findings.append('the attribute %s' % n.attr)
            if n.attr == '__dict__' or (n.attr == 'modules' and isinstance(n.value, ast.Name) and n.value.id == 'sys'):
                findings.append('the attribute %s' % n.attr)
            if n.attr in ('read_contract', 'session_violation', 'read_allowlist') and not (
                    isinstance(n.value, ast.Name) and SEAM_MODULES.get(n.value.id, ('',))[0] == n.attr):
                findings.append('the attribute %s on another object' % n.attr)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs:
            if any(s in n.value for s in SEAM_STRINGS):
                findings.append('a string naming the seam')
    if sorted(binders) != sorted(SEAM_MODULES):
        findings.append('the three module-level imports are not exactly once each')
    return findings


LEGIT = ('from aieos_bootstrap import task_contract\nfrom aieos_bootstrap import session_violation\n'
         'from aieos_bootstrap import claude_code_shell_allow\nimport re\n'
         'def f(a, b, c, d, e, g):\n    """Docstrings may name task_contract, session_violation and read_allowlist."""\n'
         '    task_contract.read_contract(a, b, c)\n    session_violation.session_violation(a, b, c, d, e, g)\n'
         '    claude_code_shell_allow.read_allowlist(a, b, c)\n'
         '    return re.fullmatch(a, b), re.compile(a)\n')
HEAD = ('from aieos_bootstrap import task_contract\nfrom aieos_bootstrap import session_violation\n'
        'from aieos_bootstrap import claude_code_shell_allow\n')


class AC5TheRunSeam(unittest.TestCase):

    def test_the_module_passes_the_seam_check(self):
        """TASK-072 AC5: the new module passes the run seam's AST check, and so do the legitimate calls."""
        self.assertEqual(seam_findings(TEXT), [])
        self.assertEqual(seam_findings(LEGIT), [])

    def test_hostile_samples_are_refused(self):
        """TASK-072 AC5: one hostile sample per form is refused: a Starred argument, a keyword, **kwargs, an alias, a
        rebound module name, getattr, partial, a wrapper function, an argument or def named for a module, setattr,
        globals, a string holding a name, an attribute chain, and the other forms the contract lists. TASK-076 AC7: the
        head holds the three module-level imports, and the forms are repeated for read_allowlist."""
        head = HEAD
        self.assertEqual(seam_findings(head), [])
        bodies = [
                  'claude_code_shell_allow.read_allowlist(*a)\n',
                  'claude_code_shell_allow.read_allowlist(a, b, c, run=d)\n',
                  'claude_code_shell_allow.read_allowlist(a, b, c, None)\n',
                  'claude_code_shell_allow.read_allowlist(a, b)\n',
                  'x = claude_code_shell_allow\n', 'claude_code_shell_allow = 1\n',
                  'getattr(claude_code_shell_allow, "read_allowlist")(a, b, c)\n',
                  's = "read_allowlist"\n', 'm.read_allowlist(a, b, c)\n', 'read_allowlist(a, b, c)\n',
                  'def claude_code_shell_allow():\n    pass\n',
                  'import aieos_bootstrap.claude_code_shell_allow\n',
                  'from aieos_bootstrap.claude_code_shell_allow import read_allowlist\n',
                  'task_contract.read_contract(*a)\n', 'task_contract.read_contract(a, b, c, run=d)\n',
                  'task_contract.read_contract(a, b, c, **k)\n',
                  'session_violation.session_violation(a, b, c, d, e, g, h)\n',
                  'task_contract.read_contract(a, b, c, d)\n', 'x = task_contract\n', 'task_contract = 1\n',
                  'getattr(task_contract, "read_contract")(a, b, c)\n',
                  'functools.partial(task_contract.read_contract, a)\n',
                  'def w(*a):\n    return task_contract.read_contract(*a)\n', 'def f(task_contract):\n    pass\n',
                  'def session_violation():\n    pass\n', 'setattr(m, "x", 1)\n', 'globals()\n', 'vars(m)\n',
                  's = "read_contract"\n', 'm.writer.append_event()\n', 'x.adapter.violation()\n', 'm.observe()\n',
                  'f(task_contract)\n', 'return_value = task_contract.read_contract\n', 'sys.modules\n',
                  'm.__dict__\n', 'try:\n    pass\nexcept E as task_contract:\n    pass\n',
                  'global session_violation\n', 'import aieos_bootstrap.task_contract\n',
                  'from aieos_bootstrap.task_contract import read_contract\n', 'eval("1")\n', 'exec("1")\n',
                  'compile("1", "f", "exec")\n', 'operator.attrgetter("read_contract")(task_contract)\n',
                  'attrgetter("x")\n',
                  'importlib.import_module("aieos_bootstrap.task_contract")\n', '__import__("x.session_violation")\n',
                  'm.read_contract(a, b, c)\n', 'locals()\n', 'delattr(m, "x")\n',
                  'match v:\n    case {**session_violation}:\n        pass\n',
                  'match v:\n    case task_contract:\n        pass\n', 'for task_contract in x:\n    pass\n',
                  'with m as session_violation:\n    pass\n', '(task_contract := 1)\n', 'del task_contract\n']
        for body in bodies:
            with self.subTest(body=body):
                self.assertTrue(seam_findings(head + body))
        third = 'from aieos_bootstrap import claude_code_shell_allow\n'
        self.assertTrue(seam_findings('from aieos_bootstrap import task_contract as t\n'
                                      'from aieos_bootstrap import session_violation\n' + third))
        self.assertTrue(seam_findings('from aieos_bootstrap import task_contract, session_violation\n' + third))
        self.assertTrue(seam_findings('def f():\n    from aieos_bootstrap import task_contract\n'
                                      'from aieos_bootstrap import session_violation\n' + third))
        self.assertTrue(seam_findings('from aieos_bootstrap import task_contract\n'
                                      'from aieos_bootstrap import session_violation\n'))
        self.assertTrue(seam_findings('from aieos_bootstrap import task_contract\n'
                                      'from aieos_bootstrap import session_violation\n'
                                      'from aieos_bootstrap import claude_code_shell_allow as s\n'))

    def test_broken_copies_of_the_module_are_caught(self):
        """TASK-072 AC5: broken copies of the new module, each with one form of a seam bypass, are caught. TASK-076 AC7:
        the shell allowlist reader's call is there exactly once, and copies that bypass it are caught too."""
        call_rc = 'task_contract.read_contract(root, base, task)'
        call_sv = 'session_violation.session_violation(root, session_id, redacted, event_id, recorder, at)'
        call_ra = 'claude_code_shell_allow.read_allowlist(root, base, task)'
        self.assertEqual(TEXT.count(call_rc), 1)
        self.assertEqual(TEXT.count(call_sv), 1)
        self.assertEqual(TEXT.count(call_ra), 1)
        broken = [TEXT.replace(call_ra, 'claude_code_shell_allow.read_allowlist(root, base, task, run=None)'),
                  TEXT.replace(call_ra, 'claude_code_shell_allow.read_allowlist(*(root, base, task))'),
                  TEXT.replace(call_ra, 'getattr(claude_code_shell_allow, "read_allowlist")(root, base, task)'),
                  TEXT + '\nREADER = claude_code_shell_allow.read_allowlist\n',
                  TEXT + '\n_NAME = "read_allowlist"\n',
                  TEXT.replace('from aieos_bootstrap import claude_code_shell_allow\n', ''),
                  TEXT + '\nfrom aieos_bootstrap.claude_code_shell_allow import read_allowlist\n',
TEXT.replace(call_rc, 'task_contract.read_contract(root, base, task, run=None)'),
                  TEXT.replace(call_rc, 'task_contract.read_contract(*(root, base, task))'),
                  TEXT.replace(call_sv, call_sv[:-1] + ', lookup=None)'),
                  TEXT.replace(call_sv, call_sv[:-1] + ', None)'),
                  TEXT.replace(call_rc, 'getattr(task_contract, "read_contract")(root, base, task)'),
                  TEXT.replace('from aieos_bootstrap import task_contract\n',
                               'from aieos_bootstrap import task_contract as task_contract\n'),
                  TEXT + '\nREADER = task_contract.read_contract\n',
                  TEXT + '\nsetattr(session_violation, "x", 1)\n',
                  TEXT + '\n_NAME = "session_violation"\n',
                  TEXT.replace(call_sv, 'session_violation.adapter.violation(root, session_id, redacted, event_id, '
                                        'recorder, at)'),
                  TEXT + '\nimport functools\nREADER = functools.partial(task_contract.read_contract, None)\n',
                  TEXT + '\nimport importlib\nimportlib.import_module("aieos_bootstrap.task_contract")\n',
                  TEXT + '\n__import__("aieos_bootstrap.session_violation")\n',
                  TEXT + '\n\ndef _wrap(*a):\n    return task_contract.read_contract(*a)\n',
                  TEXT + '\n\ndef _named(task_contract):\n    return None\n',
                  TEXT + '\n\ndef session_violation():\n    return None\n',
                  TEXT + '\ntask_contract = None\n',
                  TEXT + '\nfrom aieos_bootstrap.task_contract import read_contract\n']
        for text in broken:
            with self.subTest(i=broken.index(text)):
                self.assertNotEqual(text, TEXT)
                self.assertTrue(seam_findings(text))


class AC6Separation(unittest.TestCase):

    def test_imports_and_names(self):
        """TASK-072 AC6: the new module imports only datetime, hashlib, json, os, re and sys and, each as "from
        aieos_bootstrap import X", claude_code, claude_code_channel, claude_code_hook, claude_code_store,
        session_violation and task_contract; it opens no file, starts no process, names no project-state string and
        uses no attribute of writer, adapter, eventlog, violation or read_set_record. TASK-076 AC7: it imports
        claude_code_shell_allow too, and uses only its read_allowlist."""
        tree = ast.parse(TEXT)
        imports = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imports.update(('import', a.name) for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                imports.update((n.module, a.name) for a in n.names)
        self.assertEqual(imports, {('import', m) for m in ('datetime', 'hashlib', 'json', 'os', 're', 'sys')}
                         | {('aieos_bootstrap', m) for m in ('claude_code', 'claude_code_channel', 'claude_code_hook',
                                                             'claude_code_shell_allow', 'claude_code_store',
                                                             'session_violation', 'task_contract')})
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        self.assertFalse((names | attrs) & {'open', 'print', 'exec', 'eval', '__import__', 'importlib', 'subprocess',
                                            'socket', 'popen', 'system', 'spawn', 'urlopen', 'connect', 'sqlite3',
                                            'getenv', 'putenv', 'argv', 'writer', 'adapter', 'eventlog',
                                            'read_set_record', 'observe'})
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Assert)])
        self.assertNotIn('.' + 'aieos', TEXT)
        attrs_of = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
                attrs_of.setdefault(n.value.id, set()).add(n.attr)
        self.assertEqual(attrs_of['os'], {'getcwd', 'environ'})
        self.assertEqual(attrs_of['sys'], {'stdin', 'stderr', 'exit'})
        self.assertEqual(attrs_of['claude_code_store'], {'judge', 'KEYS'})
        self.assertEqual(attrs_of['claude_code_hook'], {'entry', 'RESULT_KEYS'})
        self.assertEqual(attrs_of['claude_code_channel'], {'record_findings', 'redact', 'RECORDER_JOIN'})
        self.assertEqual(attrs_of['claude_code'], {'RECORDER'})
        self.assertEqual(attrs_of['claude_code_shell_allow'], {'read_allowlist'})

    def test_the_names_equal_the_read_hooks(self):
        """TASK-072 AC6: SESSION_VAR and ROOT_VAR equal the read hook's; BASE_VAR is AIEOS_BASE; OUTCOMES and REASONS
        are the closed sets."""
        self.assertEqual((hook.SESSION_VAR, hook.ROOT_VAR),
                         (claude_code_read_hook.SESSION_VAR, claude_code_read_hook.ROOT_VAR))
        self.assertEqual(hook.BASE_VAR, 'AIEOS_BASE')
        self.assertEqual(hook.OUTCOMES, ('allow', 'refuse'))
        self.assertEqual(hook.REASONS, ('enforce_nothing', 'tied_allow', 'store', 'base', 'contract', 'uncovered',
                                        'no_record', 'record_form', 'recorded', 'lease_lost', 'core', 'entry'))


POLICY = b'version: 1\nshell_allow:\n  - ls\n  - git status\n  - cat\n'
CONTRACT = b'task: TASK-001\ncapabilities:\n  shell: {allow: ["ls -la", "git status"]}\n'


def object_store(policy=POLICY, contract=CONTRACT):
    """An in-memory object store at BASE with the policy file (when policy is not None) and the contract."""
    ids = {k: k * 40 for k in 'abcdef'}
    root_tree = '040000 tree %s\tdocs\n' % ids['d']
    objects = {BASE: ('tree %s\nauthor A <a> 1 +0000\ncommitter A <a> 1 +0000\n\nm\n' % ids['a']).encode(),
               ids['d']: ('040000 tree %s\ttasks\n' % ids['e']).encode(),
               ids['e']: ('100644 blob %s\t%s.yaml\n' % (ids['f'], TASK)).encode(), ids['f']: contract}
    if policy is not None:
        root_tree = '040000 tree %s\t.aieos\n' % ids['b'] + root_tree
        objects[ids['b']] = ('100644 blob %s\tproject.yaml\n' % ids['c']).encode()
        objects[ids['c']] = policy
    objects[ids['a']] = root_tree.encode()
    return objects


class AC6TheShellList(unittest.TestCase):

    def real(self, stdin, objects, entry=None):
        """run with the real claude_code_shell_allow over a stand-in gitread.run serving objects (and a stand-in
        gitread.form_error accepting the made-up root); the other stand-ins as Calls sets them."""
        c, asked = Calls(), []

        def fake_run(root, args, timeout):
            asked.append(args[2])
            if args[2] not in objects:
                return {'exit': 128, 'out': b'', 'err': b'', 'error': None}
            return {'exit': 0, 'out': objects[args[2]], 'err': b'', 'error': None}
        ps = c.patches(entry=entry)[:5]
        for p in ps:
            p.start()
        try:
            with mock.patch.object(gitread, 'run', fake_run), \
                    mock.patch.object(gitread, 'form_error', lambda *a: None):
                out = hook.run(stdin, ENV, None, T0, c.clock)
        finally:
            for p in reversed(ps):
                p.stop()
        return c, out, asked

    def test_a_shell_call_matching_both_lists_is_allowed(self):
        """TASK-076 AC6: with the real reader, a Bash or PowerShell call matching an entry of both lists gives run
        reason "tied_allow" and nothing passed to the core; the reader asks at most seven objects."""
        for stdin in (call_bytes('Bash', {'command': 'ls -la'}), call_bytes('PowerShell', {'command': 'git status'})):
            with self.subTest(stdin=stdin):
                c, out, asked = self.real(stdin, object_store())
                self.assertEqual(out, {'exit_code': 0, 'outcome': 'allow', 'reason': 'tied_allow', 'findings': []})
                self.assertEqual(c.core_args, [])
                self.assertLessEqual(len(asked), 7)
                self.assertEqual(asked[0], BASE)

    def test_a_call_matching_only_the_policy_is_recorded(self):
        """TASK-076 AC6: a call matching only the policy list gives run reason "recorded", the entry's reason
        "allowlist" and evidence type shell_not_allowed."""
        seen = []

        def entry(*args):
            r = claude_code_hook.entry(*args)
            seen.append(r)
            return r
        c, out, _ = self.real(call_bytes('Bash', {'command': 'cat a.txt'}), object_store(), entry)
        self.assertEqual(out['reason'], 'recorded')
        self.assertEqual(seen[0]['reason'], 'allowlist')
        self.assertEqual(c.passed()['evidence_type'], 'shell_not_allowed')

    def test_both_lists_empty_refuse_every_shell_call(self):
        """TASK-076 AC6: with no policy file at the base, or a contract without entries, every shell call is refused
        and recorded as before."""
        stores = (object_store(policy=None), object_store(contract=b'task: TASK-001\n'),
                  object_store(policy=None, contract=b'task: TASK-001\n'))
        for objects in stores:
            for command in ('ls -la', 'git status', 'ls'):
                with self.subTest(command=command):
                    c, out, _ = self.real(call_bytes('Bash', {'command': command}), objects)
                    self.assertEqual(out['reason'], 'recorded')
                    self.assertEqual(c.passed()['evidence_type'], 'shell_not_allowed')

    def test_other_tools_are_unaffected_and_not_read(self):
        """TASK-076 AC6: for a Read, a Write and an Edit call the verdict, the reason and the record are the same with
        an empty list and with a well-formed list, and the reader is not called."""
        edit = call_bytes('Edit', {'file_path': WIN_ROOT + '\\src\\b.py', 'old_string': 'a', 'new_string': 'b'})
        for stdin in (READ, WRITE_IN, WRITE_OUT, edit):
            with self.subTest(stdin=stdin):
                outs = []
                for shell in (shell_lists(), shell_lists(['ls', 'git status'])):
                    c = Calls(shell=shell)
                    outs.append((c.run(stdin=stdin), c.core_args[0][0][2] if c.core_args else None))
                    self.assertNotIn('read_allowlist', c.log)
                self.assertEqual(outs[0], outs[1])
        self.assertEqual(claude_code_hook.allowlist_findings(['ls', 'git status']), [])

    def test_parse_failures_give_no_read(self):
        """TASK-076 AC6: an input that is not bytes, starts with a byte-order mark, is not UTF-8, holds a duplicate key
        or a NaN, Infinity or -Infinity constant, is not an object, or has a tool_name that is not exactly Bash or
        PowerShell (a non-str among them) gives the empty list and no read."""
        bash = call_bytes('Bash', {'command': 'ls'})
        inputs = ['{}', b'\xef\xbb\xbf' + bash, b'\xff' + bash, b'[1]',
                  b'{"tool_name": "Bash", "tool_name": "Bash", "tool_input": {"command": "ls"}}',
                  b'{"tool_name": "Bash", "tool_input": {"command": "ls"}, "x": NaN}',
                  b'{"tool_name": "Bash", "tool_input": {"command": "ls"}, "x": Infinity}',
                  b'{"tool_name": "Bash", "tool_input": {"command": "ls"}, "x": -Infinity}',
                  call_bytes(7, {'command': 'ls'}), call_bytes('bash', {'command': 'ls'}),
                  call_bytes(['Bash'], {'command': 'ls'}), call_bytes(None, {'command': 'ls'})]
        for stdin in inputs:
            with self.subTest(stdin=stdin):
                c = Calls(shell=shell_lists(['ls']))
                c.run(stdin=stdin)
                self.assertNotIn('read_allowlist', c.log)
                self.assertEqual(hook._allowlist(stdin, WIN_ROOT, BASE, TASK), [])

    def test_the_reader_is_not_called_on_the_bad_base_and_contract_paths(self):
        """TASK-076 AC6: with AIEOS_BASE out of form, or the contract unreadable, a Bash call reads no list."""
        bash = call_bytes('Bash', {'command': 'ls'})
        c = Calls(shell=shell_lists(['ls']))
        self.assertEqual(c.run(stdin=bash, env=dict(ENV, **{hook.BASE_VAR: ''}))['reason'], 'base')
        self.assertNotIn('read_allowlist', c.log)
        c = Calls(shell=shell_lists(['ls']), contract=unreadable('git'))
        self.assertEqual(c.run(stdin=bash)['reason'], 'contract')
        self.assertNotIn('read_allowlist', c.log)

    def test_the_reader_gets_root_base_and_task_and_its_list_is_passed(self):
        """TASK-076 AC6: on the judged path the reader gets the tie's root, AIEOS_BASE and the lease's task, three
        arguments and no run; its list reaches the entry: a listed command is allowed."""
        got = []

        def entry(*args):
            got.append(args[4])
            return claude_code_hook.entry(*args)
        c = Calls(shell=shell_lists(['ls']))
        out = c.run(stdin=call_bytes('Bash', {'command': 'ls'}), entry=entry)
        self.assertEqual(c.shell_args, [((WIN_ROOT, BASE, TASK), {})])
        self.assertEqual(got, [['ls']])
        self.assertEqual(out['reason'], 'tied_allow')
        self.assertEqual(c.log, ['judge', 'read_contract', 'read_allowlist'])

    def test_a_raising_reader_or_an_answer_of_another_shape_gives_empty(self):
        """TASK-076 AC6: a reader that raises, or answers None, a list, a mapping without a list of str under
        "allowlist", gives the empty list: the shell call is refused and recorded."""
        answers = (RuntimeError('made-up'), None, [], {}, {'allowlist': 'ls'}, {'allowlist': [7]},
                   {'allowlist': ('ls',)}, KeyError('x'))
        for answer in answers:
            with self.subTest(answer=answer):
                got = []

                def entry(*args):
                    got.append(args[4])
                    return claude_code_hook.entry(*args)
                c = Calls(shell=answer)
                out = c.run(stdin=call_bytes('Bash', {'command': 'ls'}), entry=entry)
                self.assertEqual(got, [[]])
                self.assertEqual(out['reason'], 'recorded')

    def test_the_shell_tools_equal_the_judges(self):
        """TASK-076 AC6: the hook's own SHELL_TOOLS literals equal claude_code.SHELL_TOOLS."""
        self.assertEqual(hook.SHELL_TOOLS, claude_code.SHELL_TOOLS)
        self.assertEqual(hook.SHELL_TOOLS, ('Bash', 'PowerShell'))


class FakeStdin:
    def __init__(self, data):
        self.buffer = io.BytesIO(data)


class RaisingStderr:
    def write(self, text):
        raise OSError('made-up')


class AC7Main(unittest.TestCase):

    def main_with(self, run=None, stdin=b'{}', cwd='made-up-folder', stderr=None, environ=None, stdin_obj=None,
                  clock=None):
        err, out, got = stderr or io.StringIO(), io.StringIO(), []

        def fake_run(*args):
            got.append(args)
            if isinstance(run, BaseException):
                raise run
            return run

        def fake_cwd():
            if isinstance(cwd, BaseException):
                raise cwd
            return cwd
        patches = [mock.patch.object(hook.sys, 'stdin', stdin_obj or FakeStdin(stdin)),
                   mock.patch.object(hook.sys, 'stderr', err),
                   mock.patch.object(hook.sys, 'stdout', out), mock.patch.object(hook.os, 'getcwd', fake_cwd),
                   mock.patch.object(hook, '_raw_clock', clock or (lambda: T0 + datetime.timedelta(microseconds=5)))]
        if run is not None:
            patches.append(mock.patch.object(hook, 'run', fake_run))
        if environ is not None:
            patches.append(mock.patch.dict(hook.os.environ, environ, clear=True))
        for p in patches:
            p.start()
        try:
            code = hook.main()
        finally:
            for p in reversed(patches):
                p.stop()
        return code, err.getvalue() if isinstance(err, io.StringIO) else None, out.getvalue(), got

    def test_main_passes_its_inputs_and_the_clock_function(self):
        """TASK-072 AC7: main passes the input bytes, os.environ, the working folder, now rounded up to the next whole
        second, and the clock function itself, not its value; nothing on standard output; nothing on standard error
        on exit 0."""
        code, err, out, got = self.main_with(run={'exit_code': 0, 'outcome': 'allow', 'reason': 'tied_allow',
                                                  'findings': []}, stdin=b'made-up')
        self.assertEqual((code, err, out), (0, '', ''))
        stdin, environ, folder, now, clock = got[0]
        self.assertEqual((stdin, folder, now), (b'made-up', 'made-up-folder', T0 + datetime.timedelta(seconds=1)))
        self.assertIs(environ, os.environ)
        self.assertIs(clock, hook._whole_second_now)

    def test_a_refusal_writes_the_one_line(self):
        """TASK-072 AC7: on exit 2 exactly the line "AIEOS: this tool call was refused by the AIEOS hook (<reason>)" on
        standard error, the reason a word of REASONS; nothing on standard output."""
        for reason in hook.REASONS[2:]:
            with self.subTest(reason=reason):
                code, err, out, _ = self.main_with(run={'exit_code': 2, 'outcome': 'refuse', 'reason': reason,
                                                        'findings': []})
                self.assertEqual((code, err, out),
                                 (2, 'AIEOS: this tool call was refused by the AIEOS hook (%s)\n' % reason, ''))

    def test_a_failing_standard_error_keeps_the_code(self):
        """TASK-072 AC7: a standard error whose write raises keeps run's exit code."""
        code, _, out, _ = self.main_with(run={'exit_code': 2, 'outcome': 'refuse', 'reason': 'store', 'findings': []},
                                         stderr=RaisingStderr())
        self.assertEqual((code, out), (2, ''))

    def test_the_working_folder(self):
        """TASK-072 AC7: an OSError from os.getcwd with no session id set gives a refusal; with a session id and a
        root set the folder is not used (the real store lookup refuses the made-up root, not the folder)."""
        code, err, _, _ = self.main_with(cwd=OSError('made-up'), environ={})
        self.assertEqual((code, err), (2, 'AIEOS: this tool call was refused by the AIEOS hook (store)\n'))
        got = []
        real = claude_code_store.judge

        def judge(*args):
            got.append(args)
            return real(*args)
        with mock.patch.object(claude_code_store, 'judge', judge):
            code, err, _, _ = self.main_with(cwd=OSError('made-up'), environ={
                hook.SESSION_VAR: SID, hook.ROOT_VAR: os.path.join(os.path.abspath(os.sep), 'made-up-no-root')})
        self.assertEqual(code, 2)
        self.assertIsNone(got[0][2])
        out = real(*got[0])
        self.assertNotEqual(out['reason'], 'argument')

    def test_any_exception_in_main_gives_two(self):
        """TASK-072 AC7: any other Exception inside main gives 2, reason "entry", and the line, never 0 or 1; a run
        answer of another form gives 2 too."""
        for exc in (RuntimeError('made-up'), KeyError('x')):
            with self.subTest(exc=exc):
                code, err, _, _ = self.main_with(run=exc)
                self.assertEqual((code, err), (2, 'AIEOS: this tool call was refused by the AIEOS hook (entry)\n'))
        for answer in ({}, {'exit_code': 1, 'reason': 'made-up'}, {'exit_code': 2, 'reason': 'made-up'}):
            with self.subTest(answer=answer):
                code, err, _, _ = self.main_with(run=answer)
                self.assertEqual((code, err), (2, 'AIEOS: this tool call was refused by the AIEOS hook (entry)\n'))

    def test_a_raising_input_or_clock_inside_main(self):
        """TASK-072 AC7: a standard input whose read raises, and a clock that raises inside main, each give 2, reason
        "entry", and the line; a clock reading of a whole second is passed unchanged as now."""
        class RaisingBuffer:
            def read(self):
                raise OSError('made-up')

        def raising_clock():
            raise OSError('made-up')
        allow = {'exit_code': 0, 'outcome': 'allow', 'reason': 'tied_allow', 'findings': []}
        line = 'AIEOS: this tool call was refused by the AIEOS hook (entry)\n'
        stdin = types.SimpleNamespace(buffer=RaisingBuffer())
        self.assertEqual(self.main_with(run=allow, stdin_obj=stdin)[:2], (2, line))
        self.assertEqual(self.main_with(run=allow, clock=raising_clock)[:2], (2, line))
        code, err, _, got = self.main_with(run=allow, clock=lambda: T0)
        self.assertEqual((code, err, got[0][3]), (0, '', T0))


class AC8Findings(unittest.TestCase):

    def test_findings_hold_no_input_text(self):
        """TASK-072 AC8: text planted in the tool name, the command and the path, and the environment's values and a
        fencing token, never appear in run's findings; outcome and reason are in OUTCOMES and REASONS."""
        planted = 'PLANTEDTEXT'
        inputs = [call_bytes('Bash', {'command': 'echo ' + planted}), call_bytes(planted, {}),
                  call_bytes('Write', {'file_path': WIN_ROOT + '\\' + planted}),
                  call_bytes('Write', {'file_path': 'C:\\' + planted})]
        answers = [refused('session'), dict(refused('x'), reason=planted), tied()]
        for stdin in inputs:
            for judge in answers:
                for contract in (readable(), unreadable('git')):
                    with self.subTest(stdin=stdin, judge=judge, contract=contract):
                        c = Calls(judge=judge, contract=contract,
                                  core=dict(done(), findings=[planted], fencing_token={'epoch': planted, 'counter': 1}))
                        out = c.run(stdin=stdin, env=dict(ENV, made_up=planted))
                        self.assertEqual(set(out), KEYS)
                        self.assertNotIn(planted, json.dumps(out['findings']))
                        self.assertNotIn(SID, json.dumps(out['findings']))
                        self.assertIn(out['outcome'], hook.OUTCOMES)
                        self.assertIn(out['reason'], hook.REASONS)

    def test_an_exception_gives_entry_with_its_type_only(self):
        """TASK-072 AC8: an exception inside run gives exit 2, reason "entry" and only the type's name."""
        c = Calls(judge=ValueError('PLANTEDTEXT'))
        self.assertEqual(c.run(), {'exit_code': 2, 'outcome': 'refuse', 'reason': 'entry',
                                   'findings': ['entry: ValueError']})
        self.assertEqual(hook.run(b'{}', None, None, T0)['findings'], ['entry: AttributeError'])


class AC9WhatIsStated(unittest.TestCase):

    def test_the_docstring_states_the_limits(self):
        """TASK-072 AC9: the module docstring states each pinned phrase exactly as AC9 writes it, case kept and
        whitespace collapsed, and no effect label. TASK-076 AC7: the timing phrase is the twelve-call one, and the
        policy file, the refused first words and the copied walk are stated."""
        doc = ' '.join(ast.get_docstring(ast.parse(TEXT)).split())
        for words in ('every shell call is refused', 'refused without a record',
                      'twelve calls, about 120 seconds at worst for the git calls alone', 'the policy file',
                      'refuses a first word such as timeout or python', 'kept in step by hand',
                      'AIEOS_BASE is a proposal', 'a nested runtime chooses its own',
                      'cannot show that AIEOS_BASE is the tip of main', 'replace refs', 'forbidden is not enforced',
                      'unmeasured', 'a BaseException', 'a kill', 'only with stand-ins',
                      'the base is fixed at the grant',
                      'no STOP is recorded by this hook', 'no hook is placed'):
            with self.subTest(words=words):
                self.assertIn(words, doc)
        labels = '|'.join(('MEAS' + 'URED', 'ENFOR' + 'CED', 'GUARAN' + 'TEED'))
        self.assertIsNone(re.search(r'\b(' + labels + r')\b', TEXT))

    def test_every_test_names_its_criteria(self):
        """TASK-072 AC9, TASK-074 AC7 and TASK-076 AC7: every test function of this module names "TASK-072 ACn",
        "TASK-074 ACn" or "TASK-076 ACn" in its own docstring and no other task's AC in qualified form; every test
        function of the property module names one of those three, and every test function of PretoolHookFiles names
        "TASK-072 ACn"."""
        tree = ast.parse(pathlib.Path(__file__).read_bytes().decode('utf-8'))
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test')]:
            doc = ' '.join((ast.get_docstring(fn) or '').split())
            with self.subTest(test=fn.name):
                self.assertTrue(re.findall(r'TASK-07[246] AC[0-9]+', doc))
                self.assertEqual(re.findall(r'TASK-(?!07[246] )[0-9]+ AC[0-9]+', doc), [])
        self.assertEqual(re.findall(r'TASK-(?!07[246] )[0-9]+ AC[0-9]+', 'TASK-073 AC1 TASK-075 AC2'),
                         ['TASK-073 AC1', 'TASK-075 AC2'])
        here = pathlib.Path(__file__).resolve().parents[1]
        prop_path = here / 'property' / 'test_claude_code_pretool_hook_properties.py'
        prop = ast.parse(prop_path.read_bytes().decode('utf-8'))
        files = ast.parse((here / 'integration' / 'test_writer_files.py').read_bytes().decode('utf-8'))
        cls = [n for n in files.body if isinstance(n, ast.ClassDef) and n.name == 'PretoolHookFiles']
        self.assertEqual(len(cls), 1)
        for fn in [n for n in ast.walk(prop) if isinstance(n, ast.FunctionDef) and n.name.startswith('test')]:
            doc = ' '.join((ast.get_docstring(fn) or '').split())
            with self.subTest(test=fn.name):
                self.assertTrue(re.findall(r'TASK-07[246] AC[0-9]+', doc))
        for fn in [n for n in ast.walk(cls[0]) if isinstance(n, ast.FunctionDef) and n.name.startswith('test')]:
            doc = ' '.join((ast.get_docstring(fn) or '').split())
            with self.subTest(test=fn.name):
                self.assertTrue(re.findall(r'TASK-072 AC[0-9]+', doc))


def refusal_with_record():
    """A refusal of the entry with a record of the judge's form for this session (as test_a_record_out_of_form_is_not
    _passed builds it)."""
    record = claude_code.judge({'tool_name': 'Write', 'tool_input': {'file_path': WIN_ROOT + '\\x'}}, WIN_ROOT, TASK,
                               ['src/a.py'], [], 'r', RECORDER)['record']
    return claude_code_hook._result('refuse', 'write', 'write_set', (), record)


def contract_case_any_root(test, c, out, reason, root):
    test.assertEqual(out['reason'], reason)
    c.assert_one()
    record = c.passed()
    test.assertEqual(record['evidence_type'], 'write_outside_write_set')
    test.assertEqual(record['refers_to'], NOT_READABLE)
    args = c.core_args[0][0]
    test.assertEqual(args[0], root)
    test.assertIn('/pretool-contract/', args[3])


class WhatIsStatedTask074(unittest.TestCase):

    def test_the_n3_and_n4_sentences(self):
        """TASK-074 AC2: the module docstring states the judged path's refusal, the bad-base and contract paths'
        record with the empty-bytes hash, and the __bytes__ difference; the old sentence is gone."""
        doc = ' '.join(ast.get_docstring(ast.parse(TEXT)).split())
        for words in ('on the judged path (steps 4 and 5) the entry then refuses it without a record',
                      'its record goes to step 5 (the form check, redaction, then the core path) with the empty-bytes '
                      'hash', 'whose __bytes__ gives other bytes'):
            with self.subTest(words=words):
                self.assertIn(words, doc)
        self.assertNotIn('is hashed as no bytes, and the entry then refuses it without a record', doc)

    def test_the_s1_1_and_s1_2_sentences(self):
        """TASK-074 AC3: main's sentence cites the documentation as unmeasured, and the seconds count the git calls
        alone; the old sentences are gone. TASK-076 AC7: the 50 seconds became the twelve calls' 120 seconds."""
        doc = ' '.join(ast.get_docstring(ast.parse(TEXT)).split())
        for words in ("as Claude Code's documentation states (unmeasured, C6)",
                      'about 120 seconds at worst for the git calls alone'):
            with self.subTest(words=words):
                self.assertIn(words, doc)
        for words in ('exception, which would let the call go ahead', 'about 50 seconds at worst, against',
                      'about 50 seconds', 'an empty shell allowlist', 'authors no shell policy'):
            with self.subTest(words=words):
                self.assertNotIn(words, doc)


class AC2PinnedAsItIs(unittest.TestCase):

    def test_a_str_input_on_the_bad_base_and_contract_paths(self):
        """TASK-074 AC2: a str input with AIEOS_BASE absent gives reason "base", and with an unreadable contract
        reason "contract", each with the core called once and the event id of the empty-bytes hash."""
        want = SID + '/pretool-contract/sha256-' + hashlib.sha256(b'').hexdigest()
        env = dict(ENV)
        del env[hook.BASE_VAR]
        c = Calls()
        self.assertEqual(c.run(stdin='{}', env=env)['reason'], 'base')
        c.assert_one()
        self.assertEqual(c.core_args[0][0][3], want)
        c = Calls(contract=unreadable('git'))
        self.assertEqual(c.run(stdin='{}')['reason'], 'contract')
        c.assert_one()
        self.assertEqual(c.core_args[0][0][3], want)

    def test_a_bytes_subclass_whose_bytes_differ(self):
        """TASK-074 AC2: on the judged path, a bytes subclass whose __bytes__ gives other bytes gets the event id of
        those other bytes, while the entry gets the object itself."""
        own = call_bytes('Write', {'file_path': WIN_ROOT + '\\src\\b.py'}, tool_use_id=None)
        other = call_bytes('Write', {'file_path': WIN_ROOT + '\\src\\c.py'}, tool_use_id=None)

        class Other(bytes):
            def __bytes__(self):
                return other
        got = []

        def entry(*args):
            got.append(args[0])
            return refusal_with_record()
        c = Calls()
        self.assertEqual(c.run(stdin=Other(own), entry=entry)['reason'], 'recorded')
        c.assert_one()
        self.assertEqual(c.core_args[0][0][3], SID + '/pretool/sha256-' + hashlib.sha256(other).hexdigest())
        self.assertIs(type(got[0]), Other)
        self.assertEqual(bytes.__getitem__(got[0], slice(None)), own)


class AC4NonWindowsRoot(unittest.TestCase):

    def test_the_bad_base_and_contract_paths_pass_their_record(self):
        """TASK-074 AC4: with a tie whose root is not a Windows absolute path, AIEOS_BASE absent gives reason "base"
        and an unreadable contract reason "contract", each passing step 3's record once; the judged path gives
        "no_record" with nothing passed."""
        root = '/made-up-root'
        env = dict(ENV)
        del env[hook.BASE_VAR]
        c = Calls(judge=tied(root=root))
        contract_case_any_root(self, c, c.run(env=env), 'base', root)
        c = Calls(judge=tied(root=root), contract=unreadable('git'))
        contract_case_any_root(self, c, c.run(), 'contract', root)
        c = Calls(judge=tied(root=root))
        self.assertEqual(c.run(stdin=WRITE_OUT)['reason'], 'no_record')
        self.assertEqual(c.core_args, [])


if __name__ == '__main__':
    unittest.main()

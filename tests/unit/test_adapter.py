"""Unit tests of aieos_bootstrap.adapter (task TASK-051, rules R1 to R5 and R9): the three calls start, submit and end
with stand-ins for every function they call; no process starts and no file is written or created. Every call a stand-in records
is bound to the real function's signature. Each test names its criteria in its own docstring."""

import ast
import datetime
import inspect
import os
import pathlib
import re
import unittest

from aieos_bootstrap import adapter
from aieos_bootstrap import execution
from aieos_bootstrap import gitread
from aieos_bootstrap import submit as submission
from aieos_bootstrap import writer

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap'
ROOT = str(pathlib.Path(__file__).resolve().parents[2] / 'no-such-adapter-root')
REPO = str(pathlib.Path(__file__).resolve().parents[2])
TASK = 'TASK-100'
CODE = 'c' * 64
COMMIT = '3' * 40
NOW = datetime.datetime(2026, 10, 16, 12, 0, 0, tzinfo=datetime.timezone.utc)
LATER = NOW + datetime.timedelta(hours=1)
REC = 'aieos-adapter (unit)'
TOKEN = {'epoch': 'e1', 'counter': 1}
LEASE = {'task_id': TASK, 'fencing_token': TOKEN, 'expires_at': LATER}


class Calls:
    """Stand-ins that record each call, bound to the real function's signature, and give a set answer."""

    def __init__(self, answers=None):
        self.calls = []
        self.answers = dict(answers or {})

    def make(self, name, real):
        def stand_in(*args, **kwargs):
            inspect.signature(real).bind(*args, **kwargs)
            self.calls.append((name, args, kwargs))
            a = self.answers.get(name)
            if isinstance(a, Exception):
                raise a
            return a(*args, **kwargs) if callable(a) else a
        return stand_in

    def names(self):
        return [c[0] for c in self.calls]


def done(value=None):
    return writer.StoreResult('done', value=value)


def refused(reason):
    return writer.StoreResult('refused', reason, ['a finding'])


def bound(real, args):
    """Bind a stand-in's call to the real function's signature (raises TypeError when it does not fit); None."""
    inspect.signature(real).bind(*args)


def decided(lease=LEASE, decision='CONTINUE'):
    return {'result': 'decided', 'reason': None, 'findings': [], 'decision': decision, 'record_id': 'r1',
            'appended': ['r1'], 'duplicate': [], 'lease': lease, 'released': None, 'uncovered': []}


def run_start(c, **over):
    args = dict(root=ROOT, task_id=TASK, session_id='session-1', holder='agent-1', inputs={'task_id': TASK},
                code_sha256=CODE, expires_at=LATER, recorder=REC, now=NOW)
    args.update(over)
    return adapter.start(start_session=c.make('start_session', writer.start_session), **args)


def run_end(c, token=TOKEN, **over):
    args = dict(root=ROOT, task_id=TASK, session_id='session-1', fencing_token=token, now=NOW)
    args.update(over)
    return adapter.end(release_lease_token=c.make('release_lease_token', writer.release_lease_token),
                       end_session=c.make('end_session', writer.end_session), **args)


class StubExecute:
    """execution.execute replaced for one test, bound to its real signature."""

    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def __enter__(self):
        self.real = execution.execute

        def stand_in(*args, **kwargs):
            inspect.signature(self.real).bind(*args, **kwargs)
            self.calls.append((args, kwargs))
            if isinstance(self.answer, Exception):
                raise self.answer
            return self.answer
        execution.execute = stand_in
        return self

    def __exit__(self, *exc):
        execution.execute = self.real


class StubSubmit:
    """submit.submit replaced for one test, bound to its real signature."""

    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def __enter__(self):
        self.real = submission.submit

        def stand_in(*args, **kwargs):
            inspect.signature(self.real).bind(*args, **kwargs)
            self.calls.append((args, kwargs))
            return self.answer
        submission.submit = stand_in
        return self

    def __exit__(self, *exc):
        submission.submit = self.real


class R1Arguments(unittest.TestCase):
    def test_each_wrong_argument_of_start_is_refused_before_any_call(self):
        """TASK-051 AC1, TASK-051 AC5: each wrong argument of start gives "refused", reason "argument", and nothing
        is called (the passing case: a call in form reaches start_session)."""
        for over in ({'root': ''}, {'task_id': 'TASK-x'}, {'session_id': ''}, {'holder': None}, {'inputs': []},
                     {'code_sha256': 'C' * 64}, {'recorder': ''}, {'now': NOW.replace(tzinfo=None, microsecond=0)},
                     {'expires_at': NOW}, {'expires_at': LATER + datetime.timedelta(microseconds=5)}):
            c = Calls()
            with StubExecute(decided()) as ex:
                r = run_start(c, **over)
            self.assertEqual((r['result'], r['reason']), ('refused', 'argument'), over)
            self.assertEqual((c.calls, ex.calls), ([], []), over)
            self.assertEqual(tuple(r), adapter.RESULT_KEYS)
        c = Calls({'start_session': done()})
        with StubExecute(decided()) as ex:
            r = run_start(c)
        self.assertEqual(r['result'], 'done')
        self.assertEqual(len(ex.calls), 1)

    def test_each_wrong_argument_of_submit_and_end_is_refused(self):
        """TASK-051 AC1, TASK-051 AC5: submit and end refuse each wrong argument with reason "argument" and call
        nothing."""
        for over in ({'root': ''}, {'repo': ''}, {'commit_id': 'g' * 40}, {'task_id': 'T-1'}, {'event_id': ''},
                     {'recorder': None}, {'now': None}):
            args = dict(root=ROOT, repo=REPO, commit_id=COMMIT, task_id=TASK, event_id='sub-1', recorder=REC,
                        now=NOW)
            args.update(over)
            with StubSubmit({'result': 'submitted'}) as sb:
                r = adapter.submit(**args)
            self.assertEqual((r['result'], r['reason'], sb.calls), ('refused', 'argument', []), over)
        for over in ({'root': ''}, {'task_id': 'TASK-'}, {'session_id': ''}, {'token': {'epoch': 'e1'}},
                     {'token': {'epoch': 'e1', 'counter': True}}, {'now': 'now'}):
            c = Calls()
            token = over.pop('token', TOKEN)
            r = run_end(c, token, **over)
            self.assertEqual((r['result'], r['reason'], c.calls), ('refused', 'argument', []), over)

    def test_the_defaults_are_the_named_functions_at_call_time(self):
        """TASK-051 AC1: with no function given, start calls writer.start_session and gives execute the writer's
        functions, submit gives submit.submit gitread.run and the writer's, and end calls the writer's; each is read
        at call time."""
        seen = {}
        saved = {n: getattr(writer, n) for n in ('start_session', 'end_session', 'release_lease_token')}
        try:
            writer.start_session = lambda *a: bound(saved['start_session'], a) or seen.setdefault('start_session', done())
            writer.release_lease_token = lambda *a: bound(saved['release_lease_token'], a) or seen.setdefault('release', done())
            writer.end_session = lambda *a: bound(saved['end_session'], a) or seen.setdefault('end_session', done())
            with StubExecute(decided()) as ex:
                adapter.start(ROOT, TASK, 'session-1', 'agent-1', {}, CODE, LATER, REC, NOW)
            kw = ex.calls[0][1]
            self.assertIs(kw['read_log'], writer.read_log)
            self.assertIs(kw['append'], writer.append_event)
            self.assertIs(kw['grant'], writer.grant_lease)
            self.assertIs(kw['release'], writer.release_lease_token)
            self.assertIs(kw['held'], writer.held_lease)
            self.assertIsNone(kw['check'])  # execute's own default, resume_check.check
            with StubSubmit({'result': 'submitted'}) as sb:
                adapter.submit(ROOT, REPO, COMMIT, TASK, 'sub-1', REC, NOW)
            kw = sb.calls[0][1]
            self.assertIs(kw['read'], gitread.run)
            self.assertIs(kw['append'], writer.append_event)
            self.assertIs(kw['held'], writer.held_lease)
            adapter.end(ROOT, TASK, 'session-1', TOKEN, NOW)
        finally:
            for n, f in saved.items():
                setattr(writer, n, f)
        self.assertEqual(sorted(seen), ['end_session', 'release', 'start_session'])


class R2Start(unittest.TestCase):
    def test_the_session_row_first_then_execute_and_the_token(self):
        """TASK-051 AC2, TASK-051 AC5: start_session comes before execute; execute gets the grant request built from
        holder, session_id and expires_at; the result carries the decision and the lease's token."""
        c = Calls({'start_session': done()})
        with StubExecute(decided()) as ex:
            r = run_start(c)
        self.assertEqual(c.names(), ['start_session'])
        self.assertEqual(c.calls[0][1], (ROOT, 'session-1', 'agent-1', NOW))
        args, kw = ex.calls[0]
        self.assertEqual(args[:7], (ROOT, TASK, {'task_id': TASK}, CODE,
                                    {'holder': 'agent-1', 'session_id': 'session-1', 'expires_at': LATER}, REC, NOW))
        self.assertEqual((r['result'], r['decision'], r['fencing_token']), ('done', 'CONTINUE', TOKEN))
        self.assertEqual(r['core'], decided())

    def test_a_refused_session_start_stops_before_execute(self):
        """TASK-051 AC2, TASK-051 AC5: a refused or raising start_session gives reason "session" and execute is not
        called."""
        for answer in (refused('started'), ValueError('no store'), None):
            c = Calls({'start_session': answer})
            with StubExecute(decided()) as ex:
                r = run_start(c)
            self.assertEqual((r['result'], r['reason'], ex.calls), ('refused', 'session', []), answer)

    def test_no_token_without_a_lease_and_a_core_refusal(self):
        """TASK-051 AC2, TASK-051 AC5: a decision with no lease gives no token; execute's refusal gives reason "core"
        with its findings; a raising execute is caught."""
        c = Calls({'start_session': done()})
        with StubExecute(decided(lease=None, decision='REPLAN')):
            r = run_start(c)
        self.assertEqual((r['result'], r['decision'], r['fencing_token']), ('done', 'REPLAN', None))
        core = {'result': 'refused', 'reason': 'inputs', 'findings': ['inputs: log_seq differs']}
        with StubExecute(core):
            r = run_start(Calls({'start_session': done()}))
        self.assertEqual((r['result'], r['reason']), ('refused', 'core'))
        self.assertIn('inputs: log_seq differs', r['findings'])
        with StubExecute(RuntimeError('x')):
            r = run_start(Calls({'start_session': done()}))
        self.assertEqual((r['result'], r['reason']), ('refused', 'core'))


class R3Submit(unittest.TestCase):
    def test_submit_is_called_once_with_the_given_values(self):
        """TASK-051 AC3, TASK-051 AC5: submit.submit is called once with the call's values and functions; the adapter
        reads no commit and compares no token; a refusal gives reason "core"."""
        read = Calls().make('read', gitread.run)
        with StubSubmit({'result': 'submitted', 'reason': None, 'findings': []}) as sb:
            r = adapter.submit(ROOT, REPO, COMMIT, TASK, 'sub-1', REC, NOW, read=read)
        self.assertEqual(len(sb.calls), 1)
        self.assertEqual(sb.calls[0][0], (ROOT, REPO, COMMIT, TASK, 'sub-1', REC, NOW))
        self.assertIs(sb.calls[0][1]['read'], read)
        self.assertEqual((r['result'], r['fencing_token']), ('done', None))
        with StubSubmit({'result': 'duplicate', 'reason': None, 'findings': []}):
            self.assertEqual(adapter.submit(ROOT, REPO, COMMIT, TASK, 'sub-1', REC, NOW)['result'], 'done')
        with StubSubmit({'result': 'refused', 'reason': 'fence', 'findings': ['fence: no lease']}):
            r = adapter.submit(ROOT, REPO, COMMIT, TASK, 'sub-1', REC, NOW)
        self.assertEqual((r['result'], r['reason'], r['findings'][-1]), ('refused', 'core', 'fence: no lease'))

    def test_the_module_compares_no_token(self):
        """TASK-051 AC3: the text of submit() names no fencing token comparison: no "fencing_token" and no "fence"
        appears in its body."""
        tree = ast.parse((SRC / 'adapter.py').read_bytes().decode('utf-8'))
        body = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'submit')
        names = {n.id for n in ast.walk(body) if isinstance(n, ast.Name)}
        self.assertNotIn('fencing_token', names)
        self.assertFalse(any('fence' in n for n in names))


class R4End(unittest.TestCase):
    def test_release_then_end_session(self):
        """TASK-051 AC4, TASK-051 AC5: with a token, release_lease_token then end_session, in that order; the released
        lease is in the result."""
        c = Calls({'release_lease_token': done(LEASE), 'end_session': done([])})
        r = run_end(c)
        self.assertEqual(c.names(), ['release_lease_token', 'end_session'])
        self.assertEqual(c.calls[0][1], (ROOT, TASK, TOKEN))
        self.assertEqual((r['result'], r['released']), ('done', LEASE))

    def test_none_and_token_refusals_are_no_error(self):
        """TASK-051 AC4: a release refused "none" or "token" releases nothing and is no error; the session is still
        closed."""
        for reason in ('none', 'token'):
            c = Calls({'release_lease_token': refused(reason), 'end_session': done([])})
            r = run_end(c)
            self.assertEqual((r['result'], r['released'], c.names()), ('done', None,
                                                                      ['release_lease_token', 'end_session']))

    def test_no_release_without_a_token_and_a_refused_release_stops(self):
        """TASK-051 AC4, TASK-051 AC5: with no token no release is called; any other refusal or a raised exception
        gives reason "release" and end_session is not called; a refused end_session gives reason "session"."""
        c = Calls({'end_session': done([])})
        self.assertEqual(run_end(c, None)['result'], 'done')
        self.assertEqual(c.names(), ['end_session'])
        for answer in (refused('other'), ValueError('bad token'), None):
            c = Calls({'release_lease_token': answer, 'end_session': done([])})
            r = run_end(c)
            self.assertEqual((r['reason'], c.names()), ('release', ['release_lease_token']), answer)
        for answer in (refused('ended'), ValueError('no store')):
            r = run_end(Calls({'release_lease_token': done(LEASE), 'end_session': answer}))
            self.assertEqual((r['result'], r['reason'], r['released']), ('refused', 'session', LEASE))


class R5Result(unittest.TestCase):
    def test_the_keys_and_no_exception_escapes(self):
        """TASK-051 AC5: every result has exactly RESULT_KEYS, in every outcome, and an argument whose own methods
        raise is caught."""
        class Odd(datetime.tzinfo):
            def utcoffset(self, dt):
                raise RuntimeError('odd')
        odd = datetime.datetime(2026, 10, 16, 12, 0, 0, tzinfo=Odd())
        for r in (run_start(Calls(), now=odd), run_end(Calls(), now=odd),
                  adapter.submit(ROOT, REPO, COMMIT, TASK, 'sub-1', REC, odd)):
            self.assertEqual(tuple(r), adapter.RESULT_KEYS)
            self.assertEqual(r['result'], 'refused')

    def test_the_test_paths_are_absolute_on_this_platform(self):
        """TASK-051 AC12 (D-988 M1): the root and the repository path the tests give are absolute on the platform the
        suite runs on (submit.submit refuses a relative one), so the tests mean the same on Linux and Windows."""
        self.assertTrue(os.path.isabs(ROOT))
        self.assertTrue(os.path.isabs(REPO))


class R9Purity(unittest.TestCase):
    def test_imports_and_no_file_process_clock_or_environment(self):
        """TASK-051 AC10, TASK-051 AC9, TASK-052 AC9, TASK-052 AC8, TASK-053 AC6: adapter.py imports only datetime,
        re and aieos_bootstrap's execution, gitread, submit, violation (TASK-052) and writer; it calls no open, no
        subprocess, no clock and no environment; its docstring states the limits, task TASK-053's in place of the
        caller bar."""
        text = (SRC / 'adapter.py').read_bytes().decode('utf-8')
        tree = ast.parse(text)
        imports = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imports |= {a.name for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                imports |= {'%s.%s' % (n.module, a.name) for a in n.names}
        self.assertEqual(imports, {'datetime', 're', 'aieos_bootstrap.execution', 'aieos_bootstrap.gitread',
                                   'aieos_bootstrap.submit', 'aieos_bootstrap.violation', 'aieos_bootstrap.writer'})
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertFalse(attrs & {'now', 'utcnow', 'today', 'time', 'environ', 'getenv', 'system', 'popen', 'open'})
        self.assertFalse(names & {'open', 'exec', 'eval', 'compile', '__import__'})
        doc = ast.get_docstring(tree)
        for words in ('No observation call', 'section 11 point 10', 'write-set is neither passed',
                      'INV-004', 'One run at a time',
                      'makes every later evaluation of the task reject (task TASK-053)'):
            self.assertIn(words, doc)
        self.assertNotIn('called only by this function', doc)


class R9OwnTests(unittest.TestCase):
    def test_every_test_names_its_criteria_and_no_other_tasks(self):
        """TASK-051 AC11, TASK-051 AC12, TASK-052 AC10, TASK-053 AC9: every test function of the three test modules
        (TASK-052 adds test_violation.py) names at least one "TASK-051 ACn" or "TASK-052 ACn" in its own docstring and
        no other task's AC in qualified form but TASK-053's; together they name TASK-051's AC1 to AC12 and TASK-052's
        AC1 to AC11 (the failing case: a docstring naming another task's AC is found)."""
        here = pathlib.Path(__file__).resolve().parent
        named = {'051': set(), '052': set()}
        for name in ('test_adapter.py', 'test_replay.py', 'test_violation.py'):
            tree = ast.parse((here / name).read_bytes().decode('utf-8'))
            for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test')]:
                doc = ast.get_docstring(fn) or ''
                ids = re.findall(r'TASK-(051|052) (AC[0-9]+)', doc)
                self.assertTrue(ids, (name, fn.name))
                self.assertEqual(re.findall(r'TASK-(?!051 |052 |053 )[0-9]+ AC[0-9]+', doc), [], (name, fn.name))
                for task, ac in ids:
                    named[task].add(ac)
        self.assertEqual(named['051'], {'AC%d' % i for i in range(1, 13)})
        self.assertEqual(named['052'], {'AC%d' % i for i in range(1, 12)})
        self.assertEqual(re.findall(r'TASK-(?!051 |052 |053 )[0-9]+ AC[0-9]+', 'TASK-032 AC6'), ['TASK-032 AC6'])


if __name__ == '__main__':
    unittest.main()

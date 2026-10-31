"""Unit tests of aieos_bootstrap.launcher.start's gone sessions' step (task TASK-090): the new callees and their
defaults, the step's order and calls, failing per session, the "gone_records: " findings, DEF-0102's findings values,
the file's own rules and the docstring. Every store function and observe_gone are stand-ins that record their calls,
bound to the real function's signature (tests/unit/test_launcher_end.py's form, rebuilt here, not imported); start is
stopped at the expiry, or, for a full run, its four input readers are patched (each patch restored when its with block
ends); no test writes a file, runs Git or reads a clock; the root is a literal Windows path that names no folder."""

import ast
import datetime
import inspect
import pathlib
import types
import unittest
from unittest import mock

from aieos_bootstrap import adapter, base_files, execution, gitread, launcher, read_set_record, resume_inputs
from aieos_bootstrap import resume_log_inputs, writer

HERE = pathlib.Path(__file__).resolve()
REPO = str(HERE.parents[2])
ROOT = 'C:/launcher-gone-root-90'
TASK = 'TASK-100'
OTHER_TASK = 'TASK-200'
S1 = 'launch-' + 'a' * 32
S2 = 'launch-' + 'b' * 32
NOW = datetime.datetime(2026, 10, 25, 12, 0, 0, tzinfo=datetime.timezone.utc)
LATER = NOW + datetime.timedelta(hours=1)
EARLIER = NOW - datetime.timedelta(hours=1)
REC = 'aieos-launcher (unit)'
TOKEN = {'epoch': 'e1', 'counter': 1}
READS = ['src/a.py', 'src/b.py']
WHY = read_set_record.GONE_WHY[1]
HEAD = 'a' * 40
REAL = (('read_sessions', writer.read_sessions), ('session_leases', writer.session_leases),
        ('stored_reads', writer.stored_reads), ('remove_reads', writer.remove_reads),
        ('observe_gone', read_set_record.observe_gone), ('expire', writer.expire_leases))


def row(task=TASK, expires=LATER):
    return {'task_id': task, 'fencing_token': TOKEN, 'expires_at': expires}


def store(result='done', reason=None, value=None):
    return writer.StoreResult(result, reason, ['a finding'] if result != 'done' else [], value)


def leases(rows, ended=False):
    return store(value={'ended': ended, 'leases': rows})


def recorded(result='written', reason=None, core=None):
    return {'result': result, 'reason': reason, 'findings': [] if result != 'refused' else ['a record finding'],
            'record': None, 'core': core}


def core_refused(reason):
    return recorded('refused', 'core', {'result': 'refused', 'reason': reason, 'seq': None, 'findings': ['f']})


def recorder_of(session_id):
    return REC + ' at the next start, for session ' + session_id


class Hostile:
    """An answer whose every attribute raises."""

    def __getattr__(self, name):
        raise RuntimeError(name)


class Calls:
    """Stand-ins that record each call, bound to the real function's signature, and give a set answer (a callable
    answer is called with the arguments)."""

    def __init__(self, answers):
        self.calls = []
        self.answers = dict(answers)

    def make(self, name, real):
        def stand_in(*args, **kwargs):
            inspect.signature(real).bind(*args, **kwargs)
            self.calls.append((name, args, kwargs))
            a = self.answers.get(name)
            if isinstance(a, BaseException):
                raise a
            return a(*args, **kwargs) if callable(a) else a
        return stand_in

    def names(self):
        return [c[0] for c in self.calls]

    def of(self, name):
        return [c for c in self.calls if c[0] == name]


def run(listing=(S1,), **answers):
    """launcher.start with the five new callees and expire recording stand-ins; expire answers out of form, so start
    stops right after it with reason "expire"."""
    base = {'read_sessions': store(value=list(listing)), 'session_leases': leases([]),
            'stored_reads': store(value=list(READS)), 'observe_gone': recorded(), 'remove_reads': store(value=2),
            'expire': 'stop'}
    base.update(answers)
    c = Calls(base)
    kw = {name: c.make(name, real) for name, real in REAL}
    r = launcher.start(ROOT, REPO, TASK, 'unit', None, 'agent-1', REC, NOW, LATER,
                       read=c.make('read', gitread.run), **kw)
    return r, c


def ok_head(repo, args, timeout=30):
    """HEAD for every form but the status form (TASK-109), which answers clean."""
    out = b'' if args[0] == 'status' else (HEAD + '\n').encode('ascii')
    return {'exit': 0, 'out': out, 'err': b'', 'error': None}


def full(c, state='READY', started=None, ended=None, expired=()):
    """launcher.start run past the expiry with its four input readers patched (TASK-090 AC8's means), each patch
    restored when the with block ends; adapter.start and adapter.end are stand-ins giving the set answers."""
    view = {'task_state': state, 'log_seq': 1, 'approved_contract_hash': 'b' * 64}
    kw = {name: c.make(name, real) for name, real in REAL if name != 'expire'}
    with mock.patch.object(resume_inputs, 'git_inputs', lambda *a, **k: (dict.fromkeys(resume_inputs.KEYS), None)), \
            mock.patch.object(resume_log_inputs, 'log_inputs',
                              lambda *a, **k: (dict.fromkeys(resume_log_inputs.KEYS), None)), \
            mock.patch.object(base_files, 'read_file', lambda *a, **k: ({'text': 'x'}, None)), \
            mock.patch.object(execution, 'task_view', lambda *a, **k: (dict(view), None)):
        return launcher.start(ROOT, REPO, TASK, 'unit', 'critical', 'agent-1', REC, NOW, LATER, read=ok_head,
                              read_log=lambda root: b'', expire=lambda root, now: list(expired),
                              start=lambda *a, **k: started, end=lambda *a, **k: ended, **kw)


class Base(unittest.TestCase):
    def assert_form(self, r):
        self.assertEqual(tuple(r), launcher.START_KEYS)
        self.assertTrue(all(isinstance(f, str) for f in r['findings']))

    def stopped(self, r):
        """start reached the expiry and stopped there."""
        self.assert_form(r)
        self.assertEqual((r['result'], r['reason']), ('refused', 'expire'))

    def gone_lines(self, r):
        return [f for f in r['findings'] if f.startswith('gone_records: ')]


class TASK090AC3Callees(Base):
    def test_the_new_callees_default_at_call_time(self):
        """TASK-090 AC3: with none of the five new callees given and a non-empty listing, each defaults at call time
        to its named function: writer.read_sessions, writer.session_leases, writer.stored_reads, writer.remove_reads
        and read_set_record.observe_gone patched after import are the ones called, each patch restored after."""
        c = Calls({'read_sessions': store(value=[S1]), 'session_leases': leases([]), 'stored_reads': store(value=[]),
                   'observe_gone': recorded(), 'remove_reads': store(value=0)})
        with mock.patch.object(writer, 'read_sessions', c.make('read_sessions', writer.read_sessions)), \
                mock.patch.object(writer, 'session_leases', c.make('session_leases', writer.session_leases)), \
                mock.patch.object(writer, 'stored_reads', c.make('stored_reads', writer.stored_reads)), \
                mock.patch.object(writer, 'remove_reads', c.make('remove_reads', writer.remove_reads)), \
                mock.patch.object(read_set_record, 'observe_gone',
                                  c.make('observe_gone', read_set_record.observe_gone)):
            r = launcher.start(ROOT, REPO, TASK, 'unit', None, 'agent-1', REC, NOW, LATER,
                               read=lambda *a, **k: None, expire=lambda root, now: 'stop')
        self.stopped(r)
        self.assertEqual(c.names(), ['read_sessions', 'session_leases', 'stored_reads', 'observe_gone',
                                     'remove_reads'])

    def test_the_callee_names_and_the_keys(self):
        """TASK-090 AC3: _CALLEES ends with the five new names, in start's order; START_KEYS is unchanged."""
        self.assertEqual(launcher._CALLEES[-5:], ('read_sessions', 'session_leases', 'stored_reads', 'remove_reads',
                                                  'observe_gone'))
        self.assertEqual(launcher.START_KEYS, ('result', 'reason', 'findings', 'session_id', 'head_commit',
                                               'decision', 'fencing_token', 'environment', 'start', 'end'))

    def test_a_new_callee_out_of_form(self):
        """TASK-090 AC3: each of the five new callees given out of form gives "refused" with reason "argument" and
        zero callee calls."""
        for name in ('read_sessions', 'session_leases', 'stored_reads', 'remove_reads', 'observe_gone'):
            c = Calls({})
            kw = {n: c.make(n, real) for n, real in REAL}
            kw[name] = 'not callable'
            r = launcher.start(ROOT, REPO, TASK, 'unit', None, 'agent-1', REC, NOW, LATER, **kw)
            self.assert_form(r)
            self.assertEqual((r['result'], r['reason']), ('refused', 'argument'), name)
            self.assertEqual(c.calls, [], name)


class TASK090AC4TheStep(Base):
    def test_the_order_and_the_calls(self):
        """TASK-090 AC4: read_sessions(root, task_id) once and first; for each listed session with no row unexpired
        at now (no row, or only rows expired at now of any task, "ended" true and false): session_leases, stored_reads,
        observe_gone with 'lease gone (released or expired)' and the recorder holding the session id, remove_reads,
        in that order, then the next session, then expire."""
        answers = [leases([]), leases([row(expires=EARLIER), row(OTHER_TASK, NOW)]), leases([], ended=True),
                   leases([row(expires=NOW)], ended=False)]
        for answer in answers:
            r, c = run(listing=(S1, S2), session_leases=answer)
            self.stopped(r)
            per = ['session_leases', 'stored_reads', 'observe_gone', 'remove_reads']
            self.assertEqual(c.names(), ['read_sessions'] + per + per + ['expire'])
            self.assertEqual(c.of('read_sessions')[0][1], (ROOT, TASK))
            for n, sid in enumerate((S1, S2)):
                self.assertEqual(c.of('session_leases')[n][1], (ROOT, sid, NOW))
                self.assertEqual(c.of('stored_reads')[n][1], (ROOT, sid, TASK))
                self.assertEqual(c.of('observe_gone')[n][1], (ROOT, TASK, sid, READS, WHY, NOW, recorder_of(sid)))
                self.assertEqual(c.of('remove_reads')[n][1], (ROOT, sid, TASK))

    def test_a_session_with_an_unexpired_row_is_skipped(self):
        """TASK-090 AC4: a session with any row unexpired at now, of the task or of another task, "ended" true or
        not, gets only its session_leases call; the next session is still processed."""
        for rows, ended in (([row()], False), ([row(OTHER_TASK)], False), ([row(expires=EARLIER), row()], False),
                            ([row()], True)):
            r, c = run(listing=(S1, S2), session_leases=lambda root, sid, now, rows=rows, ended=ended: (
                leases(rows, ended) if sid == S1 else leases([])))
            self.stopped(r)
            self.assertEqual(c.names(), ['read_sessions', 'session_leases', 'session_leases', 'stored_reads',
                                         'observe_gone', 'remove_reads', 'expire'])
            self.assertEqual(c.of('observe_gone')[0][1][2], S2)

    def test_no_reads_still_gives_a_record(self):
        """TASK-090 AC4: stored_reads giving [] still gives the record call, with []."""
        r, c = run(stored_reads=store(value=[]))
        self.assertEqual(c.of('observe_gone')[0][1][3], [])
        self.assertEqual(len(c.of('remove_reads')), 1)

    def test_the_real_observe_gone_takes_the_recorder(self):
        """TASK-090 AC4: the real read_set_record.observe_gone, given the step's recorder text and a recording append
        stand-in, gives "written" with one append whose recorder holds the session id and ends with GONE_JOIN and
        'lease gone (released or expired)'."""
        seen = []

        def append(*args, **kwargs):
            seen.append((args, kwargs))
            return writer.WriteResult(types.SimpleNamespace(result='appended', reason=None, seq=1, line=b'',
                                                            findings=()))
        r = read_set_record.observe_gone(ROOT, TASK, S1, list(READS), WHY, NOW, recorder_of(S1), append=append)
        self.assertEqual(r['result'], 'written', r)
        self.assertEqual(len(seen), 1)
        text = seen[0][0][5]
        self.assertIn(S1, text)
        self.assertTrue(text.endswith(read_set_record.GONE_JOIN + WHY), text)
        self.assertNotIn('fencing_token', seen[0][1])


class TASK090AC5FailingPerSession(Base):
    def test_a_listing_that_fails(self):
        """TASK-090 AC5: a refused ("no_store", "root", "tables"), raising, hostile or malformed listing gives its
        "gone_records: " findings, no per-session call, and expire next."""
        bad = [store('refused', 'no_store'), store('refused', 'root'), store('refused', 'tables'), RuntimeError('x'),
               Hostile(), store(value='ab'), store(value=None), store(value=[S1, '']), store(value=[S1, 7])]
        for answer in bad:
            r, c = run(read_sessions=answer)
            self.stopped(r)
            self.assertEqual(c.names(), ['read_sessions', 'expire'], answer)
            lines = self.gone_lines(r)
            self.assertTrue(lines, answer)
            self.assertTrue(all(f.startswith('gone_records: %s: ' % TASK) for f in lines), lines)
            self.assertNotIn('a', r['findings'])

    def test_a_session_that_fails_before_the_record(self):
        """TASK-090 AC5: a refused ("session" among them), raising, hostile or malformed session_leases answer gives
        no stored_reads; a refused, raising, hostile or non-list stored_reads answer gives no record; the next session
        is processed after each, and expire follows."""
        per = ['session_leases', 'stored_reads', 'observe_gone', 'remove_reads']
        for answer in (store('refused', 'session'), store('refused', 'tables'), RuntimeError('x'), Hostile(),
                       store(value=None), store(value={'ended': 'no', 'leases': []}),
                       store(value={'ended': False, 'leases': {}}), leases([dict(row(), extra=1)]),
                       leases([{'task_id': TASK}]), leases([row(expires=LATER.replace(
                           tzinfo=None))])):
            r, c = run(listing=(S1, S2), session_leases=lambda root, sid, now, a=answer: (
                self._raise_or(a) if sid == S1 else leases([])))
            self.stopped(r)
            self.assertEqual(c.names(), ['read_sessions', 'session_leases'] + per + ['expire'], answer)
            self.assertEqual(c.of('stored_reads')[0][1][1], S2)
        for answer in (store('refused', 'tables'), RuntimeError('x'), Hostile(), store(value='x')):
            r, c = run(listing=(S1, S2), stored_reads=lambda root, sid, task, a=answer: (
                self._raise_or(a) if sid == S1 else store(value=[])))
            self.stopped(r)
            self.assertEqual(c.names(), ['read_sessions', 'session_leases', 'stored_reads'] + per + ['expire'],
                             answer)
            self.assertEqual(c.of('observe_gone')[0][1][2], S2)

    @staticmethod
    def _raise_or(answer):
        if isinstance(answer, BaseException):
            raise answer
        return answer

    def test_a_record_not_found_present(self):
        """TASK-090 AC5: a record not found present (a "core" refusal with core reason "fence" or "log", an
        "argument", a "read_paths" or an "observe" refusal) or a raising observe_gone gives no remove_reads; the next
        session is processed."""
        absent = [core_refused('fence'), core_refused('log'), recorded('refused', 'argument'),
                  recorded('refused', 'read_paths'), recorded('refused', 'observe'), RuntimeError('x'), 5]
        for answer in absent:
            r, c = run(listing=(S1, S2), observe_gone=lambda root, task, sid, reads, why, now, rec, a=answer: (
                self._raise_or(a) if sid == S1 else recorded()))
            self.stopped(r)
            self.assertEqual([x[1][1] for x in c.of('remove_reads')], [S2], answer)
            self.assertTrue(any(f.startswith('gone_records: %s: ' % S1) for f in r['findings']), answer)

    def test_a_raise_names_its_callee(self):
        """TASK-090 AC5: a raising session_leases, stored_reads, observe_gone or remove_reads gives the line
        "gone_records: <id>: <callee>: a step raised RuntimeError"; a raising remove_reads keeps the record's line
        before it; the next session and expire follow."""
        for name in ('session_leases', 'stored_reads', 'observe_gone', 'remove_reads'):
            r, c = run(listing=(S1, S2), **{name: lambda *a, n=name: self._raise_or(
                RuntimeError(n) if a[2 if n == 'observe_gone' else 1] == S1 else
                {'session_leases': leases([]), 'stored_reads': store(value=[]), 'observe_gone': recorded(),
                 'remove_reads': store(value=2)}[n])})
            self.stopped(r)
            lines = self.gone_lines(r)
            self.assertIn('gone_records: %s: %s: a step raised RuntimeError' % (S1, name), lines, name)
            self.assertIn('gone_records: %s: record written, 2 reads removed' % S2, lines, name)
        r, c = run(remove_reads=RuntimeError('x'))
        self.assertEqual(self.gone_lines(r), ['gone_records: %s: record written' % S1,
                                              'gone_records: %s: remove_reads: a step raised RuntimeError' % S1])

    def test_a_record_found_present(self):
        """TASK-090 AC5: "written", "duplicate" and a core "conflict" are each followed by remove_reads, the conflict
        named."""
        for record in (recorded(), recorded('duplicate'), core_refused('conflict')):
            r, c = run(observe_gone=record)
            self.assertEqual(len(c.of('remove_reads')), 1, record)
            conflict = record['reason'] == 'core'
            self.assertEqual(any('conflict' in f for f in r['findings']), conflict)

    def test_a_removal_that_fails(self):
        """TASK-090 AC5: a refused, raising or hostile remove_reads is named, and the next session and expire
        follow."""
        for answer in (store('refused', 'tables'), RuntimeError('x'), Hostile()):
            r, c = run(listing=(S1, S2), remove_reads=lambda root, sid, task, a=answer: (
                self._raise_or(a) if sid == S1 else store(value=2)))
            self.stopped(r)
            self.assertEqual(c.names()[-2:], ['remove_reads', 'expire'])
            self.assertEqual(len(c.of('observe_gone')), 2)
            self.assertTrue(any(f.startswith('gone_records: %s: ' % S1) for f in r['findings']), answer)


class TASK090AC6Findings(Base):
    def test_the_lines(self):
        """TASK-090 AC6: every line of the step begins "gone_records: <session_id>: "; a present record's line names
        its result and the removed count; a skipped session gives exactly the skip line; an empty listing gives no
        line."""
        r, c = run()
        self.assertEqual(self.gone_lines(r), ['gone_records: %s: record written, 2 reads removed' % S1])
        r, c = run(session_leases=leases([row()]))
        self.assertEqual(self.gone_lines(r), ['gone_records: %s: skipped, a lease row is unexpired' % S1])
        r, c = run(listing=())
        self.assertEqual(self.gone_lines(r), [])
        r, c = run(observe_gone=core_refused('conflict'))
        lines = self.gone_lines(r)
        self.assertTrue(lines and all(f.startswith('gone_records: %s: ' % S1) for f in lines), lines)

    def test_the_lines_come_first(self):
        """TASK-090 AC6: the step's lines come first, in order, in the findings of a refused, a not granted and a
        granted result; the result has exactly START_KEYS."""
        skip = 'gone_records: %s: skipped, a lease row is unexpired' % S1
        answers = {'read_sessions': store(value=[S1]), 'session_leases': leases([row()])}
        r = launcher.start(ROOT, REPO, TASK, 'unit', None, 'agent-1', REC, NOW, LATER, read=ok_head,
                           expire=lambda root, now: 'x', **{n: Calls(answers).make(n, real)
                                                             for n, real in REAL if n != 'expire'})
        self.assert_form(r)
        self.assertEqual((r['result'], r['findings'][0]), ('refused', skip))
        self.assertTrue(r['findings'][1].startswith('expire: '))
        r = full(Calls(answers), state='IN_PROGRESS')
        self.assert_form(r)
        self.assertEqual((r['result'], r['reason'], r['findings'][0]), ('not granted', 'held', skip))
        self.assertTrue(r['findings'][1].startswith('held: '))
        r = full(Calls(answers), started={'result': 'done', 'decision': 'CONTINUE', 'fencing_token': TOKEN})
        self.assert_form(r)
        self.assertEqual((r['result'], r['findings']), ('granted', [skip]))


class TASK090AC6TheRootStep(Base):
    def test_a_gone_session_is_processed_before_a_root_non_grant(self):
        """TASK-090 AC6 and TASK-090 AC4 (amended by TASK-109): with one gone session listed and a dirty root, the gone
        session's callees come first, then the expiry, then the three reads (HEAD, the base tip and the status, the
        status the third); the result is "not granted" with reason "root", the gone session's line comes first in the
        findings, and read_log, adapter.start and adapter.end are never called."""
        def dirty(repo, args, timeout=30):
            out = b'?? x\0' if args[0] == 'status' else (HEAD + '\n').encode('ascii')
            return {'exit': 0, 'out': out, 'err': b'', 'error': None}
        c = Calls({'read_sessions': store(value=[S1]), 'session_leases': leases([]),
                   'stored_reads': store(value=list(READS)), 'observe_gone': recorded(),
                   'remove_reads': store(value=2), 'expire': [], 'read': dirty, 'read_log': b'', 'start': None,
                   'end': None})
        kw = {name: c.make(name, real) for name, real in REAL}
        r = launcher.start(ROOT, REPO, TASK, 'unit', 'critical', 'agent-1', REC, NOW, LATER,
                           read=c.make('read', gitread.run), read_log=c.make('read_log', writer.read_log),
                           start=c.make('start', adapter.start), end=c.make('end', adapter.end), **kw)
        self.assert_form(r)
        self.assertEqual((r['result'], r['reason']), ('not granted', 'root'))
        self.assertEqual(c.names(), ['read_sessions', 'session_leases', 'stored_reads', 'observe_gone',
                                     'remove_reads', 'expire', 'read', 'read', 'read'])
        self.assertEqual(c.of('read')[2][1][1][0], 'status')
        self.assertTrue(r['findings'][0].startswith('gone_records: %s: ' % S1), r['findings'])
        self.assertTrue(any(f.startswith('root: 1 entries (') for f in r['findings'][1:]), r['findings'])
        self.assertIn("root: b'x'", r['findings'])
        self.assertIsNone(r['environment'])
        self.assertEqual(r['head_commit'], HEAD)
        for name in ('read_log', 'start', 'end'):
            self.assertEqual(c.of(name), [], name)


class TASK090AC8FindingsValues(Base):
    def test_the_adapter_start_findings(self):
        """TASK-090 AC8: adapter.start's findings given as a string, a number or a mapping give no item from them and
        no raise; a list keeps its str items."""
        done = {'result': 'done', 'findings': []}
        for given, kept in (('ab', []), (5, []), ({'x': 1}, []), (['kept', 7], ['kept'])):
            started = dict.fromkeys(('decision', 'fencing_token'))
            started.update({'result': 'refused', 'reason': 'core', 'findings': given})
            r = full(Calls({'read_sessions': store(value=[])}), started=started, ended=done)
            self.assert_form(r)
            self.assertEqual((r['result'], r['reason'], r['findings']), ('refused', 'core', kept), given)

    def test_the_adapter_end_findings(self):
        """TASK-090 AC8: adapter.end's findings given as a string, a number or a mapping give no item from them and
        no raise."""
        started = dict.fromkeys(('decision', 'fencing_token'))
        started.update({'result': 'refused', 'reason': 'core', 'findings': []})
        for given in ('ab', 5, {'x': 1}):
            r = full(Calls({'read_sessions': store(value=[])}), started=started,
                     ended={'result': 'refused', 'findings': given})
            self.assert_form(r)
            self.assertEqual((r['result'], r['reason'], r['findings']),
                             ('refused', 'end', ['end: adapter.end did not end the session']), given)

    def test_store_findings(self):
        """TASK-090 AC8: _store_findings keeps only the str items of a list or a tuple; a string, a number or a
        mapping gives no item from it and no raise."""
        for given, more in (('ab', []), (5, []), ({'x': 1}, []), (['f', 7], ['f']), (('g',), ['g'])):
            answer = types.SimpleNamespace(result='refused', reason='r', findings=given)
            self.assertEqual(launcher._store_findings('x', answer), ["x: x gave 'refused' ('r')"] + more, given)


class TASK090AC9TheFile(unittest.TestCase):
    def test_this_file_s_rules(self):
        """TASK-090 AC9: this file imports no tempfile, sqlite3 or shutil, names no open, makes no one-argument
        .replace() call, and roots only the literal 'C:/launcher-gone-root-90'."""
        tree = ast.parse(HERE.read_bytes().decode('utf-8'))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module)
        self.assertFalse(imported & {'tempfile', 'sqlite3', 'shutil'})
        self.assertNotIn('open', {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)})
        one = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr == 'replace' and len(n.args) == 1 and not n.keywords]
        self.assertEqual(one, [])
        self.assertEqual(ROOT, 'C:/launcher-gone-root-90')


class TASK090AC10Docstrings(unittest.TestCase):
    def test_the_launcher_s_docstring(self):
        """TASK-090 AC10: launcher.py's docstring holds the step's phrases and the new launch sentence, keeps
        "TASK-090", and no longer leaves the next start's record to TASK-090."""
        text = ' '.join(ast.get_docstring(ast.parse(inspect.getsource(launcher))).split())
        for words in ('gone_records', 'before the expiry', 'at the next start', 'TASK-090',
                      "not before DEF-0101's open points are closed"):
            self.assertIn(words, text)
        self.assertNotIn('not before TASK-090 lands', text)
        self.assertNotIn("the third, the next start's record of a session gone without an end, is TASK-090's", text)

    def test_read_sessions_docstring(self):
        """TASK-090 AC10: read_sessions' docstring says read only, core-only, that it writes and creates nothing, and
        that its read is a hand-kept copy of _read_reads' transaction steps."""
        text = ' '.join((writer.read_sessions.__doc__ or '').split())
        for words in ('read only', 'Core-only', 'writes and creates nothing', "hand-kept copy of _read_reads'"):
            self.assertIn(words, text)


class TASK090Naming(unittest.TestCase):
    def test_every_test_names_its_criteria(self):
        """TASK-090 AC10: every test function of this module names "TASK-090 AC" in its own docstring."""
        tree = ast.parse(HERE.read_bytes().decode('utf-8'))
        tests = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
        self.assertTrue(tests)
        for node in tests:
            self.assertIn('TASK-090 AC', ast.get_docstring(node) or '', node.name)


if __name__ == '__main__':
    unittest.main()

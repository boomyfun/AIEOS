"""Unit tests of aieos_bootstrap.launcher.end (task TASK-089): the arguments and the callees, the fenced path, the
held and gone paths by the session's own lease rows, the record found present, no reads, failing closed, and the
lease rows' key names. Every store function and both observe functions are stand-ins that record their calls, bound
to the real function's signature (tests/unit/test_launcher.py's form, rebuilt here, not imported); no test writes a
file, runs Git or reads a clock; the root is a literal Windows path that names no folder."""

import ast
import datetime
import inspect
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import adapter, eventlog, launcher, read_set_record, writer

HERE = pathlib.Path(__file__).resolve()
ROOT = 'C:/launcher-end-root-89'
TASK = 'TASK-100'
OTHER_TASK = 'TASK-200'
SESSION = 'session-1'
NOW = datetime.datetime(2026, 10, 25, 12, 0, 0, tzinfo=datetime.timezone.utc)
LATER = NOW + datetime.timedelta(hours=1)
EARLIER = NOW - datetime.timedelta(hours=1)
REC = 'aieos-launcher (unit) ' + SESSION
WRITE = ['src/aieos_bootstrap/mod.py']
MINE = {'epoch': 'e1', 'counter': 1}
THEIRS = {'epoch': 'e1', 'counter': 2}
BAD_FORM = {'epoch': 7}
READS = ['src/a.py', 'src/b.py']
GONE = read_set_record.GONE_WHY
REAL = (('session_leases', writer.session_leases), ('stored_reads', writer.stored_reads),
        ('remove_reads', writer.remove_reads), ('observe', read_set_record.observe),
        ('observe_gone', read_set_record.observe_gone), ('release_lease_token', writer.release_lease_token),
        ('end_session', writer.end_session))


def row(task=TASK, held_by=MINE, expires=LATER):
    return {'task_id': task, 'fencing_token': held_by, 'expires_at': expires}


def store(result='done', reason=None, value=None):
    return writer.StoreResult(result, reason, ['a finding'] if result != 'done' else [], value)


def leases(rows, ended=False):
    return store(value={'ended': ended, 'leases': rows})


def recorded(result='written', reason=None, core=None):
    return {'result': result, 'reason': reason, 'findings': [] if result != 'refused' else ['a record finding'],
            'record': None, 'core': core}


def core_refused(reason):
    return recorded('refused', 'core', {'result': 'refused', 'reason': reason, 'seq': None, 'findings': ['f']})


class Calls:
    """Stand-ins that record each call, bound to the real function's signature, and give a set answer."""

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
            return a
        return stand_in

    def names(self):
        return [c[0] for c in self.calls]

    def of(self, name):
        return [c for c in self.calls if c[0] == name]


def run(held_by=MINE, rows=None, violation=False, **answers):
    """launcher.end with every callee a recording stand-in; by default one unexpired row of the task holds MINE."""
    base = {'session_leases': leases([row()] if rows is None else rows), 'stored_reads': store(value=list(READS)),
            'remove_reads': store(value=2), 'observe': recorded(), 'observe_gone': recorded(),
            'release_lease_token': store(), 'end_session': store(value=[])}
    base.update(answers)
    c = Calls(base)
    kw = {name: c.make(name, real) for name, real in REAL}
    r = launcher.end(ROOT, TASK, SESSION, held_by, NOW, WRITE, [], REC, violation=violation, **kw)
    return r, c


class Base(unittest.TestCase):
    def assert_form(self, r):
        self.assertEqual(tuple(r), launcher.END_KEYS)
        self.assertTrue(all(isinstance(f, str) for f in r['findings']))
        if r['reason'] is not None:
            self.assertIn(r['reason'], launcher.END_REASONS)

    def closed(self, r, reason):
        """Refused with the reason, nothing removed, adapter.end not called."""
        self.assert_form(r)
        self.assertEqual((r['result'], r['reason'], r['removed'], r['end']), ('refused', reason, None, None))
        self.assertTrue(r['findings'])


class TASK089AC1Arguments(Base):
    def test_each_wrong_argument_is_refused_before_any_call(self):
        """TASK-089 AC1: each argument out of form, a root starting with "/" among them, gives "refused" with reason
        "argument", path None and no callee call."""
        cases = [dict(root='/x/y'), dict(root='x/y'), dict(root=None), dict(task_id='T-1'), dict(session_id=''),
                 dict(fencing_token=7), dict(fencing_token=[1]), dict(now=NOW.replace(tzinfo=None)),
                 dict(now=NOW.replace(microsecond=5)), dict(violation=1), dict(violation=None),
                 dict(observe=5), dict(session_leases='x'), dict(end_session=3)]
        for over in cases:
            c = Calls({})
            kw = {name: c.make(name, real) for name, real in REAL}
            args = dict(root=ROOT, task_id=TASK, session_id=SESSION, fencing_token=MINE, now=NOW, write_set=WRITE,
                        allowlist=[], recorder=REC, violation=False)
            args.update(kw)
            args.update(over)
            r = launcher.end(**args)
            self.assert_form(r)
            self.assertEqual((r['result'], r['reason'], r['path']), ('refused', 'argument', None), over)
            self.assertEqual(c.calls, [], over)

    def test_the_callees_default_at_call_time(self):
        """TASK-089 AC1: every callee defaults, at call time, to its named function: a patch after import is the
        one called."""
        c = Calls({'session_leases': leases([]), 'stored_reads': store(value=[]), 'remove_reads': store(value=0),
                   'observe_gone': recorded(), 'end_session': store(value=[])})
        gone = c.make('observe_gone', read_set_record.observe_gone)
        with mock.patch.object(writer, 'session_leases', c.make('session_leases', writer.session_leases)), \
                mock.patch.object(writer, 'stored_reads', c.make('stored_reads', writer.stored_reads)), \
                mock.patch.object(writer, 'remove_reads', c.make('remove_reads', writer.remove_reads)), \
                mock.patch.object(read_set_record, 'observe_gone', gone), \
                mock.patch.object(writer, 'end_session', c.make('end_session', writer.end_session)):
            r = launcher.end(ROOT, TASK, SESSION, None, NOW, WRITE, [], REC)
        self.assert_form(r)
        self.assertEqual(r['result'], 'done')
        self.assertEqual(c.names(), ['session_leases', 'stored_reads', 'observe_gone', 'remove_reads', 'end_session'])


class TASK089AC2Fenced(Base):
    def test_the_order_and_the_context(self):
        """TASK-089 AC2: with a row of the task unexpired at now holding the given token, with violation false and
        also true, the calls are session_leases (once, with root, session_id and now), stored_reads, observe,
        remove_reads, then adapter.end's release and end; observe's context is exactly as given; path "fenced"."""
        for violation in (False, True):
            r, c = run(violation=violation)
            self.assert_form(r)
            self.assertEqual((r['result'], r['path'], r['removed']), ('done', 'fenced', 2))
            self.assertEqual(c.names(), ['session_leases', 'stored_reads', 'observe', 'remove_reads',
                                         'release_lease_token', 'end_session'])
            self.assertEqual(c.of('session_leases')[0][1], (ROOT, SESSION, NOW))
            context, reads, now = c.of('observe')[0][1]
            self.assertEqual(context, {'root': ROOT, 'task_id': TASK, 'session_id': SESSION, 'fencing_token': MINE,
                                       'write_set': WRITE, 'allowlist': [], 'recorder': REC})
            self.assertEqual((reads, now), (READS, NOW))
            self.assertEqual(c.of('release_lease_token')[0][1], (ROOT, TASK, MINE))

    def test_an_expired_row_of_another_task_does_not_count(self):
        """TASK-089 AC2: an expired row of another task beside the task's matching row does not count; a row
        expiring exactly at now is expired."""
        for other in (row(OTHER_TASK, THEIRS, EARLIER), row(OTHER_TASK, THEIRS, NOW)):
            r, c = run(rows=[row(), other])
            self.assertEqual(r['path'], 'fenced')
            self.assertEqual(len(c.of('observe')), 1)


class TASK089AC3HeldAndGone(Base):
    def test_held(self):
        """TASK-089 AC3: a row of the task unexpired with no or another token, another task's unexpired row alone,
        or the task's matching row beside any other unexpired row of the session gives "refused" with reason "held",
        path None, and no stored_reads, record, removal or adapter.end, with violation false and true."""
        cases = [(MINE, [row(held_by=THEIRS)]), (None, [row()]), (MINE, [row(OTHER_TASK, THEIRS)]),
                 (MINE, [row(), row(OTHER_TASK, THEIRS)]), (MINE, [row(), row(held_by=THEIRS)])]
        for held_by, rows in cases:
            for violation in (False, True):
                r, c = run(held_by=held_by, rows=rows, violation=violation)
                self.closed(r, 'held')
                self.assertIsNone(r['path'])
                self.assertEqual(c.names(), ['session_leases'])

    def test_gone_and_its_reasons(self):
        """TASK-089 AC3: no row, only rows expired at now (of the task or of other tasks), or "ended" true with no
        rows give the gone path: observe_gone, not observe, with "violation" when violation is true, else "no fencing
        token given" when the token is None, else "lease gone (released or expired)"; then the removal and adapter.end
        with the given token."""
        answers = [leases([]), leases([row(expires=EARLIER)]), leases([row(OTHER_TASK, THEIRS, NOW)]),
                   leases([], ended=True)]
        for answer in answers:
            for held_by, violation, why in ((MINE, True, GONE[0]), (None, True, GONE[0]), (None, False, GONE[2]),
                                            (MINE, False, GONE[1])):
                r, c = run(held_by=held_by, violation=violation, session_leases=answer)
                self.assert_form(r)
                self.assertEqual((r['result'], r['path']), ('done', 'gone'))
                self.assertEqual(c.of('observe'), [])
                self.assertEqual(c.of('observe_gone')[0][1], (ROOT, TASK, SESSION, READS, why, NOW, REC))
                released = ['release_lease_token'] if held_by is not None else []
                self.assertEqual(c.names(), ['session_leases', 'stored_reads', 'observe_gone', 'remove_reads']
                                 + released + ['end_session'])
                if held_by is not None:
                    self.assertEqual(c.of('release_lease_token')[0][1], (ROOT, TASK, held_by))

    def test_an_ended_session_refused_by_end_session_is_passed_through(self):
        """TASK-089 AC3: on the gone path with "ended" true, end_session's refusal of the ended session is adapter.end's
        own result, passed through in "end", the record and the removal made first."""
        r, c = run(held_by=None, session_leases=leases([], ended=True), end_session=store('refused', 'session'))
        self.assert_form(r)
        self.assertEqual((r['result'], r['reason'], r['path'], r['removed']), ('refused', 'end', 'gone', 2))
        self.assertEqual(r['end']['result'], 'refused')
        self.assertEqual(c.names(), ['session_leases', 'stored_reads', 'observe_gone', 'remove_reads', 'end_session'])


class TASK089AC5FoundPresent(Base):
    def test_present_and_not_present(self):
        """TASK-089 AC5: on either path, "written", "duplicate", or "refused" with core reason "conflict" is followed
        by remove_reads, the conflict named; a "core" refusal with another core reason ("fence", "log") or a refusal
        for another reason is followed by no remove_reads."""
        present = [recorded(), recorded('duplicate'), core_refused('conflict')]
        absent = [core_refused('fence'), core_refused('log'), recorded('refused', 'context'),
                  recorded('refused', 'observe')]
        for held_by, rows, name in ((MINE, None, 'observe'), (None, [], 'observe_gone')):
            for record in present:
                r, c = run(held_by=held_by, rows=rows, **{name: record})
                self.assertEqual((r['result'], r['removed']), ('done', 2))
                self.assertEqual(len(c.of('remove_reads')), 1)
                conflict = record['reason'] == 'core'
                self.assertEqual(any('conflict' in f for f in r['findings']), conflict)
            for record in absent:
                r, c = run(held_by=held_by, rows=rows, **{name: record})
                self.assertEqual(c.of('remove_reads'), [])
                self.assertIn('record: the record was not found present', r['findings'])


class TASK089AC6NoReads(Base):
    def test_a_record_with_no_reads(self):
        """TASK-089 AC6: stored_reads giving an empty list still gives a record call with read_paths [] on either
        path."""
        r, c = run(stored_reads=store(value=[]))
        self.assertEqual(c.of('observe')[0][1][1], [])
        r, c = run(held_by=None, rows=[], stored_reads=store(value=[]))
        self.assertEqual(c.of('observe_gone')[0][1][3], [])


class TASK089AC7FailingClosed(Base):
    def test_the_lease_rows(self):
        """TASK-089 AC7: any refused session_leases result ("session", "no_store", "tables"), a malformed "done"
        value, or a raising session_leases gives reason "lease_rows" or the step's reason with nothing written, no
        removal and no adapter.end."""
        bad = [store('refused', 'session'), store('refused', 'no_store'), store('refused', 'tables'), store(value=None),
               store(value={'ended': 'no', 'leases': []}), store(value={'ended': False, 'leases': {}}),
               store(value={'ended': False}), leases([{'task_id': TASK}]), leases([row(expires=LATER.replace(
                   tzinfo=None))]), leases([dict(row(), extra=1)]), leases([5])]
        for answer in bad:
            r, c = run(session_leases=answer)
            self.closed(r, 'lease_rows')
            self.assertEqual(c.names(), ['session_leases'])
        r, c = run(session_leases=RuntimeError('x'))
        self.closed(r, 'lease_rows')
        self.assertEqual(c.names(), ['session_leases'])

    def test_before_the_record(self):
        """TASK-089 AC7: a stored_reads refusal "tables", a stored_reads value not a list, or a raising stored_reads
        gives "refused" with no record, no removal and no adapter.end."""
        for answer in (store('refused', 'tables'), store(value='x'), RuntimeError('x')):
            r, c = run(stored_reads=answer)
            self.closed(r, 'stored_reads')
            self.assertEqual(c.names(), ['session_leases', 'stored_reads'])

    def test_the_record_not_present(self):
        """TASK-089 AC7: on the fenced path a record not found present, or a raising observe, gives "refused" with
        no removal and no adapter.end; on the gone path such a record, or a raising observe_gone, gives no removal,
        and adapter.end is still called once."""
        for answer in (core_refused('fence'), RuntimeError('x')):
            r, c = run(observe=answer)
            self.closed(r, 'record')
            self.assertEqual(c.names(), ['session_leases', 'stored_reads', 'observe'])
            r, c = run(held_by=None, rows=[], observe_gone=answer)
            self.assert_form(r)
            self.assertEqual((r['result'], r['path'], r['removed']), ('done', 'gone', None))
            self.assertEqual(c.names(), ['session_leases', 'stored_reads', 'observe_gone', 'end_session'])

    def test_after_the_record(self):
        """TASK-089 AC7: a remove_reads refusal or raise is named in the findings and adapter.end is still called;
        adapter.end refused gives result "refused" with its result in "end"; no call raises."""
        for answer in (store('refused', 'tables'), RuntimeError('x')):
            r, c = run(remove_reads=answer)
            self.assertEqual((r['result'], r['removed']), ('done', None))
            self.assertTrue(any(f.startswith('remove_reads:') for f in r['findings']))
            self.assertEqual(c.names()[-2:], ['release_lease_token', 'end_session'])
        r, c = run(end_session=store('refused', 'session'))
        self.assertEqual((r['result'], r['reason'], r['end']['result']), ('refused', 'end', 'refused'))

    def test_a_token_out_of_form_on_the_gone_path(self):
        """TASK-089 AC7: on the gone path with a token mapping out of the store's form, the record is written, the
        reads are removed, then adapter.end's "argument" refusal is passed through in "end" with result "refused", in
        that order."""
        r, c = run(held_by=BAD_FORM, rows=[])
        self.assertEqual((r['result'], r['reason'], r['path'], r['removed']), ('refused', 'end', 'gone', 2))
        self.assertEqual(r['end']['reason'], 'argument')
        self.assertEqual(c.names(), ['session_leases', 'stored_reads', 'observe_gone', 'remove_reads'])


class TASK089AC10LeaseRows(unittest.TestCase):
    def test_the_row_keys_are_the_log_s(self):
        """TASK-089 AC10: launcher._ROW_KEYS, the implementer's literal of the lease rows' keys, equals
        eventlog.LEASE_KEYS, so a drift between the two fails here."""
        self.assertEqual(set(launcher._ROW_KEYS), set(eventlog.LEASE_KEYS))
        self.assertEqual(launcher.END_KEYS, ('result', 'reason', 'findings', 'path', 'record', 'removed', 'end'))
        self.assertTrue(set(adapter.RESULT_KEYS))


class TASK089Naming(unittest.TestCase):
    def test_every_test_names_its_criteria(self):
        """TASK-089 AC11: every test function of this module names "TASK-089 AC" in its own docstring."""
        tree = ast.parse(HERE.read_bytes().decode('utf-8'))
        tests = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
        self.assertTrue(tests)
        for node in tests:
            self.assertIn('TASK-089 AC', ast.get_docstring(node) or '', node.name)


if __name__ == '__main__':
    unittest.main()

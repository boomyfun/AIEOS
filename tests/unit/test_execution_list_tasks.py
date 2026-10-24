"""Unit tests of execution.list_tasks (task TASK-084): the tasks that may be taken. Every log is built in memory with
eventlog.append (a duplicate line by hand, since append makes none), and the store's held_leases is a stand-in that
records its calls. No process starts and no file is written; the only file read is the package's own execution.py,
with pathlib's read_bytes, for the ast checks. Each test names its criteria in its own docstring."""

import ast
import datetime
import inspect
import json
import pathlib
import random
import unittest
from unittest import mock

from aieos_bootstrap import eventlog
from aieos_bootstrap import execution
from aieos_bootstrap import writer

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap' / 'execution.py'
ROOT = 'C:/a-root'
NOW = datetime.datetime(2026, 10, 24, 12, 0, 0, tzinfo=datetime.timezone.utc)
LATER = NOW + datetime.timedelta(hours=1)
EARLIER = NOW - datetime.timedelta(hours=1)
H1 = 'a' * 64
H2 = 'b' * 64
TOKEN = {'epoch': 'e1', 'counter': 4}


def lease(task, expires=LATER, counter=4):
    return {'task_id': task, 'fencing_token': {'epoch': 'e1', 'counter': counter}, 'expires_at': expires}


class Log:
    """An event log kept as bytes; every line but a hand-made duplicate is decided by eventlog.append."""

    def __init__(self):
        self.data = b''
        self.lines = []

    def add(self, event_type, payload, event_id, task_id, fencing_token=None, held=None):
        r = eventlog.append(self.data, event_type, payload, event_id, NOW, task_id=task_id,
                            fencing_token=fencing_token, lease=held)
        if r.result != 'appended':
            raise AssertionError(r.findings)
        self.data += r.line
        self.lines.append(r.line)
        return self

    def approve(self, task, h=H1, eid=None):
        return self.add('task.approved', {'contract_version': 'v1', 'contract_hash': h, 'approval_record': 'appr'},
                        eid or 'approved-%s-%d' % (task, len(self.lines)), task)

    def duplicate(self, index):
        """A copy of line ``index`` with the next seq, as the log's own duplicate of it."""
        obj = json.loads(self.lines[index].decode('utf-8'))
        obj['seq'] = len(self.lines) + 1
        line = (json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode('utf-8')
        self.data += line
        self.lines.append(line)
        return self

    def block(self, task, eid):
        return self.add('task.blocked', {'reason': 'dependency', 'blocked_by': ['TASK-099']}, eid, task)

    def unblock(self, task, eid):
        return self.add('task.unblocked', {'reason': 'dependency done'}, eid, task)

    def accept(self, task, next_state, eid):
        payload = {'record_id': eid, 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_local',
                   'recorder': 'unit', 'subject': task, 'decision': 'NEEDS_REWORK', 'next_task_state': next_state}
        return self.add('decision.acceptance', payload, eid, task)


class Stand:
    """The two readers as stand-ins, each recording its call."""

    def __init__(self, log=Log, leases=None):
        self.log = Log() if log is Log else log
        self.leases = [] if leases is None else leases
        self.calls = []

    def read_log(self, root):
        self.calls.append(('read_log', (root,), {}))
        if isinstance(self.log, Exception):
            raise self.log
        return self.log if not isinstance(self.log, Log) else self.log.data

    def held_leases(self, root):
        self.calls.append(('held_leases', (root,), {}))
        if isinstance(self.leases, Exception):
            raise self.leases
        return self.leases

    def run(self, root=ROOT, now=NOW):
        return execution.list_tasks(root, now, read_log=self.read_log, held_leases=self.held_leases)

    def names(self):
        return [c[0] for c in self.calls]


def tasks_of(listed):
    return [t['task'] for t in listed]


class TASK084AC1Arguments(unittest.TestCase):
    def test_wrong_arguments_read_nothing(self):
        """TASK-084 AC1: root not a non-empty str, or now not a UTC datetime with whole seconds, gives findings with
        zero reader calls."""
        naive = datetime.datetime(2026, 10, 24, 12, 0, 0)
        for root, now in (('', NOW), (None, NOW), (3, NOW), (ROOT, naive), (ROOT, NOW.replace(microsecond=5)),
                          (ROOT, NOW.astimezone(datetime.timezone(datetime.timedelta(hours=7)))), (ROOT, '2026')):
            s = Stand()
            value, found = s.run(root=root, now=now)
            self.assertIsNone(value)
            self.assertTrue(found and all(isinstance(f, str) for f in found))
            self.assertEqual(s.calls, [])

    def test_defaults_at_call_time_and_the_order(self):
        """TASK-084 AC1: read_log and held_leases default at call time to the writer's functions; one call reads the
        log once, then the store once; every stand-in call binds to the real signature."""
        s = Stand(Log().approve('TASK-1'))
        with mock.patch.object(writer, 'read_log', s.read_log), mock.patch.object(writer, 'held_leases', s.held_leases):
            value, found = execution.list_tasks(ROOT, NOW)
        self.assertIsNone(found)
        self.assertEqual(tasks_of(value), ['TASK-1'])
        self.assertEqual(s.names(), ['read_log', 'held_leases'])
        real = {'read_log': writer.read_log, 'held_leases': writer.held_leases}
        for name, args, kwargs in s.calls:
            inspect.signature(real[name]).bind(*args, **kwargs)


class TASK084AC2WhichTasks(unittest.TestCase):
    def test_listed_states(self):
        """TASK-084 AC2: READY after the approval, READY after blocked then unblocked, REWORK after an acceptance;
        each element exactly {task, state, contract_hash, lease}."""
        log = Log().approve('TASK-1').approve('TASK-2').block('TASK-2', 'b2').unblock('TASK-2', 'u2')
        log.approve('TASK-3').accept('TASK-3', 'REWORK', 'acc3')
        value, found = Stand(log).run()
        self.assertIsNone(found)
        self.assertEqual(value, [{'task': 'TASK-1', 'state': 'READY', 'contract_hash': H1, 'lease': 'none'},
                                 {'task': 'TASK-2', 'state': 'READY', 'contract_hash': H1, 'lease': 'none'},
                                 {'task': 'TASK-3', 'state': 'REWORK', 'contract_hash': H1, 'lease': 'none'}])

    def test_unlisted_states_and_no_approval(self):
        """TASK-084 AC2: DRAFT, BLOCKED, VERIFYING, IN_REVIEW, ACCEPTED, DONE, STALE, REJECTED and ESCALATED are not
        listed, nor a task with no task.approved."""
        log = Log().approve('TASK-1')
        log.add('task.drafted', {'contract_version': 'v2', 'contract_hash': H2}, 'd2', 'TASK-2').approve('TASK-2')
        log.add('task.drafted', {'contract_version': 'v2', 'contract_hash': H2}, 'd2b', 'TASK-2')
        log.approve('TASK-3').block('TASK-3', 'b3')
        log.approve('TASK-4').add('task.submitted', {'commit': '1' * 40, 'compensating': False}, 's4', 'TASK-4',
                                  fencing_token=TOKEN, held=lease('TASK-4'))
        for n, state in enumerate(('IN_REVIEW', 'ACCEPTED', 'REJECTED', 'ESCALATED'), 5):
            log.approve('TASK-%d' % n).accept('TASK-%d' % n, state, 'acc%d' % n)
        log.approve('TASK-9').add('task.done', {'decision_record': 'dec-9'}, 'done9', 'TASK-9')
        log.approve('TASK-10').add('task.stale', {'cause': 'conflict', 'refers_to': 'x'}, 'st10', 'TASK-10')
        log.add('task.drafted', {'contract_version': 'v1', 'contract_hash': H1}, 'd11', 'TASK-11')
        value, found = Stand(log).run()
        self.assertIsNone(found)
        self.assertEqual(tasks_of(value), ['TASK-1'])

    def test_duplicates_last_approval_sort_and_empty(self):
        """TASK-084 AC2: a duplicated task.approved lists its task once; a duplicated task.blocked after its
        task.unblocked leaves the task READY; the last task.approved's hash counts; sorted by task number; an empty
        log gives ([], None)."""
        log = Log().approve('TASK-10').duplicate(0)
        log.approve('TASK-9').block('TASK-9', 'b9')
        log.unblock('TASK-9', 'u9').duplicate(3)
        log.approve('TASK-2', h=H1).approve('TASK-2', h=H2)
        log.approve('TASK-07').approve('TASK-7')
        value, found = Stand(log).run()
        self.assertIsNone(found)
        self.assertEqual(tasks_of(value), ['TASK-2', 'TASK-07', 'TASK-7', 'TASK-9', 'TASK-10'])
        self.assertEqual([t['state'] for t in value if t['task'] == 'TASK-9'], ['READY'])
        self.assertEqual([t['contract_hash'] for t in value if t['task'] == 'TASK-2'], [H2])
        self.assertEqual(Stand(b'').run(), ([], None))


class TASK084AC3Leases(unittest.TestCase):
    def test_unexpired_expired_and_none(self):
        """TASK-084 AC3: an unexpired lease removes its task; one at or before now lists it as "expired"; no lease,
        "none"."""
        log = Log().approve('TASK-1').approve('TASK-2').approve('TASK-3').approve('TASK-4')
        leases = [lease('TASK-1'), lease('TASK-2', expires=EARLIER, counter=5), lease('TASK-4', expires=NOW, counter=6)]
        value, found = Stand(log, leases).run()
        self.assertIsNone(found)
        self.assertEqual([(t['task'], t['lease']) for t in value],
                         [('TASK-2', 'expired'), ('TASK-3', 'none'), ('TASK-4', 'expired')])

    def test_a_lease_on_a_task_in_another_state_leaves_it_out(self):
        """TASK-084 AC3: an in-form lease, unexpired or expired, on a VERIFYING or BLOCKED task leaves that task out
        with no finding, the other tasks listed as without it."""
        log = Log().approve('TASK-1').approve('TASK-2').add('task.submitted', {'commit': '1' * 40, 'compensating': False},
                                                             's2', 'TASK-2', fencing_token=TOKEN, held=lease('TASK-2'))
        log.approve('TASK-3').block('TASK-3', 'b3')
        for leases in ([lease('TASK-2')], [lease('TASK-2', expires=EARLIER)], [lease('TASK-3', counter=7)]):
            value, found = Stand(log, leases).run()
            self.assertIsNone(found, leases)
            self.assertEqual(value, [{'task': 'TASK-1', 'state': 'READY', 'contract_hash': H1, 'lease': 'none'}])

    def test_bad_leases_fail_the_whole_list(self):
        """TASK-084 AC3: a lease out of form, a task_id not in the TASK- form, a lease on a task with no
        task.approved, two leases on one task, held_leases raising or answering a non-list, each gives findings."""
        log = Log().approve('TASK-1').approve('TASK-2')
        good = lease('TASK-1')
        bad_leases = [
            [{'task_id': 'TASK-1', 'fencing_token': TOKEN}],
            [dict(good, extra=1)],
            [dict(good, fencing_token={'epoch': 'e1', 'counter': '4'})],
            [dict(good, expires_at=datetime.datetime(2026, 10, 24, 13, 0, 0))],
            [dict(good, task_id='task-1')], [dict(good, task_id=1)], [dict(good, task_id=['TASK-1'])], ['a lease'],
            [lease('TASK-5')],
            [lease('TASK-1'), lease('TASK-1', counter=5)],
            RuntimeError('store'), MemoryError(), 'rows', 0, (good,),
        ]
        for leases in bad_leases:
            s = Stand(log, leases)
            value, found = s.run()
            self.assertIsNone(value, leases)
            self.assertTrue(found and all(isinstance(f, str) for f in found), leases)


class TASK084AC4FailClosed(unittest.TestCase):
    def test_a_refused_log(self):
        """TASK-084 AC4: read_log answering a non-bytes value, or a log check_log refuses, gives findings with no
        held_leases call."""
        for data in ('text', None, 3, b'not json\n', Log().approve('TASK-1').data + b'{"seq": 9}\n'):
            s = Stand(data)
            value, found = s.run()
            self.assertIsNone(value, data)
            self.assertTrue(found)
            self.assertEqual(s.names(), ['read_log'])

    def test_an_unnamed_event_and_in_progress(self):
        """TASK-084 AC4: a task.* event the projection does not name (made by patching STATE_OF) fails the whole
        list, a DONE task's too; a decision.acceptance giving IN_PROGRESS gives findings."""
        log = Log().approve('TASK-1').approve('TASK-2').add('task.done', {'decision_record': 'd'}, 'done2', 'TASK-2')
        names = {k: v for k, v in execution.STATE_OF.items() if k != 'task.done'}
        with mock.patch.object(execution, 'STATE_OF', names):
            value, found = Stand(log).run()
        self.assertIsNone(value)
        self.assertIn('task.done is a task event the projection does not name', found[0])
        log = Log().approve('TASK-1').approve('TASK-2').accept('TASK-2', 'IN_PROGRESS', 'acc2')
        value, found = Stand(log).run()
        self.assertIsNone(value)
        self.assertIn('IN_PROGRESS', found[0])

    def test_raising_readers_never_escape(self):
        """TASK-084 AC4: a reader that raises (RecursionError and MemoryError among them) gives findings; no call
        raises or returns a partial list."""
        for exc in (RuntimeError('x'), RecursionError('deep'), MemoryError(), ValueError('v')):
            for where in ('log', 'leases'):
                s = Stand(Log().approve('TASK-1'), [])
                setattr(s, where, exc)
                value, found = s.run()
                self.assertIsNone(value, (exc, where))
                self.assertTrue(found and all(isinstance(f, str) for f in found))


def _tree():
    return ast.parse(SRC.read_bytes().decode('utf-8'))


def writer_uses(source, names):
    """The writer attributes the named functions of ``source`` use, and the names they refuse to use (AC5)."""
    tree = ast.parse(source)
    fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    used = set()
    for name in names:
        for n in ast.walk(fns[name]):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == 'writer':
                used.add(n.attr)
    return used


NEW = ('list_tasks', '_lease_task', '_task_key')
REFUSED = {'expire_leases', 'grant_lease', 'release_lease_token', 'append_event', 'open_store', 'start_session',
           'end_session'}


class TASK084AC5ReadsOnly(unittest.TestCase):
    def test_writer_use(self):
        """TASK-084 AC5: by ast, list_tasks and the functions the task adds use of writer at most read_log and
        held_leases, and name none of the writing functions; a call records exactly one read_log and one
        held_leases."""
        used = writer_uses(SRC.read_bytes().decode('utf-8'), NEW)
        self.assertLessEqual(used, {'read_log', 'held_leases'})
        self.assertFalse(used & REFUSED)
        s = Stand(Log().approve('TASK-1'), [lease('TASK-1', expires=EARLIER)])
        s.run()
        self.assertEqual(s.names(), ['read_log', 'held_leases'])

    def test_names_refused_by_the_module_tests(self):
        """TASK-084 AC5: the added functions name no Name time, open, os, sys, compile or exec, no attribute now,
        write, expire_leases or release_lease, and the module holds no ".aieos" substring."""
        tree = _tree()
        fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        for name in NEW:
            names = {n.id for n in ast.walk(fns[name]) if isinstance(n, ast.Name)}
            attrs = {n.attr for n in ast.walk(fns[name]) if isinstance(n, ast.Attribute)}
            self.assertFalse(names & {'time', 'open', 'os', 'sys', 'compile', 'exec'}, name)
            self.assertFalse(attrs & {'now', 'write', 'expire_leases', 'release_lease'}, name)
        self.assertNotIn('.' + 'aieos', SRC.read_bytes().decode('utf-8'))


STATES = ('IN_REVIEW', 'ACCEPTED', 'REWORK', 'REJECTED', 'ESCALATED', 'VERIFYING')


class TASK084AC6SharedProjection(unittest.TestCase):
    def test_list_tasks_calls_project(self):
        """TASK-084 AC6: by ast, list_tasks calls _project."""
        fns = {n.name: n for n in ast.walk(_tree()) if isinstance(n, ast.FunctionDef)}
        calls = {n.func.id for n in ast.walk(fns['list_tasks']) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name)}
        self.assertIn('_project', calls)

    def test_random_logs(self):
        """TASK-084 AC6: 300 seeded random logs with drawn in-form leases: every listed task is READY or REWORK by
        _project with no unexpired lease, every other approved task is not listed, no findings, no raise; a bad lease
        added gives findings each time."""
        rng = random.Random(84)
        for round_ in range(300):
            log = Log()
            tasks = ['TASK-%d' % n for n in range(1, rng.randint(2, 6))]
            for task in tasks:
                log.approve(task)
                for k in range(rng.randint(0, 3)):
                    eid = '%s-%d' % (task, k)
                    pick = rng.random()
                    if pick < 0.25:
                        log.block(task, eid + 'b')
                    elif pick < 0.45:
                        log.unblock(task, eid + 'u')
                    elif pick < 0.7:
                        log.accept(task, rng.choice(STATES[:5]), eid + 'a')
                    elif pick < 0.8:
                        log.add('task.done', {'decision_record': 'd'}, eid + 'd', task)
                    elif pick < 0.9:
                        log.add('task.stale', {'cause': 'conflict', 'refers_to': 'x'}, eid + 's', task)
                    else:
                        log.approve(task, h=H2, eid=eid + 'r')
            leases = [lease(t, expires=rng.choice((LATER, EARLIER, NOW)), counter=i)
                      for i, t in enumerate(tasks) if rng.random() < 0.5]
            value, found = Stand(log, leases).run()
            self.assertIsNone(found, round_)
            lines = execution._log(lambda root: log.data, ROOT)
            by_task = {lz['task_id']: lz for lz in leases}
            for task in tasks:
                state = execution._project(lines, task)[0]
                live = task in by_task and by_task[task]['expires_at'] > NOW
                self.assertEqual(task in tasks_of(value), state in ('READY', 'REWORK') and not live, (round_, task))
            bad = rng.choice(([{'task_id': tasks[0]}], [lease('TASK-99')], [lease(tasks[0]), lease(tasks[0], counter=9)]))
            value, found = Stand(log, leases + bad).run()
            self.assertIsNone(value, round_)
            self.assertTrue(found)


PHRASES = ['What it does not do', 'DEF-0030', 'Point (i)', 'DEF-0055 P6', 'decision D-687 M4',
           'it gathers no Resume Check input', 'no task.unblocked', 'expires no lease', 'One run at a time',
           'list_tasks', 'the tasks that may be taken', 'DEF-0099', 'reads only']


class TASK084AC7Docstring(unittest.TestCase):
    def test_docstring_phrases(self):
        """TASK-084 AC7: the module docstring holds the nine phrases of the module's tests and the four of this task,
        whitespace read as single spaces."""
        doc = ' '.join(ast.get_docstring(_tree()).split())
        for phrase in PHRASES:
            self.assertIn(phrase, doc)

    def test_naming(self):
        """TASK-084 AC7: every test of this module names "TASK-084 ACn" at the start of its docstring."""
        classes = [v for v in globals().values() if isinstance(v, type) and issubclass(v, unittest.TestCase)
                   and v.__module__ == __name__]
        self.assertGreater(len(classes), 5)
        for cls in classes:
            for name in unittest.TestLoader().getTestCaseNames(cls):
                self.assertRegex(getattr(cls, name).__doc__ or '', r'^TASK-084 AC\d+', name)


if __name__ == '__main__':
    unittest.main()

"""Unit tests of execution.status_report and the command status of cli.py (task TASK-093; specification 7 section 3
:31). Every log is built in memory with eventlog.append (a duplicate line by hand, since append makes none) and given
through a read_log stand-in that records its calls; the command's tests replace execution.status_report through
mock.patch.object, restored after each test, and use a counting clock. No process starts and no file is written; the
only files read are the package's own execution.py and cli.py and this file, with pathlib's read_bytes, for the ast
checks; the root is a literal Windows path that names no folder. Each test names its criteria in its own
docstring."""

import ast
import datetime
import json
import pathlib
import unittest
from collections import OrderedDict
from unittest import mock

from aieos_bootstrap import cli, eventlog, execution, writer

HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / 'src' / 'aieos_bootstrap'
ROOT = 'C:/status-root-93'
NOW = datetime.datetime(2026, 10, 25, 12, 0, 0, tzinfo=datetime.timezone.utc)
LATER = NOW + datetime.timedelta(hours=1)
H1 = 'a' * 64
TOKEN = {'epoch': 'e1', 'counter': 4}
NA = 'not available'
OTHERS = {'drift': NA, 'waiting_for_approval': NA, 'requirements_lacking_assurance': NA}


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

    def approve(self, task):
        return self.add('task.approved', {'contract_version': 'v1', 'contract_hash': H1, 'approval_record': 'appr'},
                        'approved-%s-%d' % (task, len(self.lines)), task)

    def submit(self, task):
        held = {'task_id': task, 'fencing_token': TOKEN, 'expires_at': LATER}
        return self.add('task.submitted', {'commit': '1' * 40, 'compensating': False},
                        'submitted-%s-%d' % (task, len(self.lines)), task, fencing_token=TOKEN, held=held)

    def accept(self, task, next_state):
        eid = 'acc-%s-%d' % (task, len(self.lines))
        payload = {'record_id': eid, 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_local',
                   'recorder': 'unit', 'subject': task, 'decision': 'NEEDS_REWORK', 'next_task_state': next_state}
        return self.add('decision.acceptance', payload, eid, task)

    def done(self, task):
        return self.add('task.done', {'decision_record': 'd'}, 'done-%s-%d' % (task, len(self.lines)), task)

    def stale(self, task):
        return self.add('evidence.stale', {'records': ['rec-1'], 'reason': 'commit'},
                        'stale-%s-%d' % (task, len(self.lines)), task)

    def duplicate(self, index):
        """A copy of line ``index`` with the next seq, as the log's own duplicate of it."""
        obj = json.loads(self.lines[index].decode('utf-8'))
        obj['seq'] = len(self.lines) + 1
        line = (json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode('utf-8')
        self.data += line
        self.lines.append(line)
        return self


def three():
    """The AC2 log: TASK-10, TASK-2 and TASK-9 approved in that order; TASK-2 sent back to REWORK after its
    task.submitted; TASK-9 DONE with an evidence.stale after it."""
    log = Log().approve('TASK-10').approve('TASK-2').approve('TASK-9')
    log.submit('TASK-2').accept('TASK-2', 'REWORK')
    return log.done('TASK-9').stale('TASK-9')


THREE = [{'task': 'TASK-2', 'state': 'REWORK', 'stale_evidence': False},
         {'task': 'TASK-9', 'state': 'DONE', 'stale_evidence': True},
         {'task': 'TASK-10', 'state': 'READY', 'stale_evidence': False}]


class Reader:
    """read_log as a stand-in: gives its value, or raises it, and records each root it is called with."""

    def __init__(self, value):
        self.value = value
        self.calls = []

    def __call__(self, root):
        self.calls.append(root)
        if isinstance(self.value, BaseException):
            raise self.value
        return self.value


def report(value, root=ROOT, now=NOW):
    reader = Reader(value)
    return execution.status_report(root, now, read_log=reader), reader


class Odd(datetime.datetime):
    """A datetime whose own utcoffset raises."""

    def utcoffset(self):
        raise RuntimeError('offset')


def function(name, file_name):
    tree = ast.parse((SRC / file_name).read_bytes().decode('utf-8'))
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name][0]


def used_names(node):
    return ({n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            | {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)})


class TASK093AC1Arguments(unittest.TestCase):
    def test_wrong_root_or_now_reads_nothing(self):
        """TASK-093 AC1: a root that is empty or not a str, and a now that is naive, not UTC, with microseconds or
        not a datetime, each give (None, findings beginning "argument: ") with read_log not called."""
        naive = datetime.datetime(2026, 10, 25, 12, 0, 0)
        east = NOW.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        for root, now in (('', NOW), (None, NOW), (3, NOW), (b'r', NOW), (ROOT, naive), (ROOT, east),
                          (ROOT, NOW.replace(microsecond=5)), (ROOT, '2026'), (ROOT, None)):
            (value, found), reader = report(three().data, root, now)
            self.assertIsNone(value, (root, now))
            self.assertTrue(found and all(f.startswith('argument: ') for f in found), (root, now))
            self.assertEqual(reader.calls, [], (root, now))

    def test_read_log_neither_none_nor_callable(self):
        """TASK-093 AC1: a read_log that is neither None nor callable gives the one "argument: " finding."""
        for bad in (3, 'read_log', b'', [Reader(b'')]):
            answer = execution.status_report(ROOT, NOW, read_log=bad)
            self.assertEqual(answer, (None, ['argument: read_log is neither None nor callable']), bad)

    def test_a_now_whose_checks_raise(self):
        """TASK-093 AC1: a now whose own utcoffset raises gives "argument: checking the arguments raised
        RuntimeError", read_log not called; nothing raises."""
        (value, found), reader = report(b'', now=Odd(2026, 10, 25, 12, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual((value, found), (None, ['argument: checking the arguments raised RuntimeError']))
        self.assertEqual(reader.calls, [])

    def test_read_log_defaults_at_call_time(self):
        """TASK-093 AC1: with read_log left out, writer.read_log as patched after import is the one called, once,
        with the root."""
        reader = Reader(three().data)
        with mock.patch.object(writer, 'read_log', reader):
            value, found = execution.status_report(ROOT, NOW)
        self.assertIsNone(found)
        self.assertEqual(reader.calls, [ROOT])
        self.assertEqual(value['progress'], THREE)


class TASK093AC2Answer(unittest.TestCase):
    def test_the_three_tasks(self):
        """TASK-093 AC2: read_log is called exactly once with the root; the answer has exactly STATUS_KEYS; progress
        lists TASK-2, TASK-9 and TASK-10 in task-number order, each item equal to task_states' over the same bytes;
        the three other items are "not available"."""
        log = three()
        (value, found), reader = report(log.data)
        self.assertIsNone(found)
        self.assertEqual(reader.calls, [ROOT])
        self.assertEqual((type(value), len(value), set(value)), (dict, 4, set(execution.STATUS_KEYS)))
        self.assertEqual(value['progress'], THREE)
        states, none = execution.task_states(log.data, ['TASK-2', 'TASK-9', 'TASK-10'])
        self.assertIsNone(none)
        for item in value['progress']:
            self.assertEqual({'state': item['state'], 'stale_evidence': item['stale_evidence']}, states[item['task']])
        self.assertEqual({k: value[k] for k in OTHERS}, OTHERS)

    def test_the_constants(self):
        """TASK-093 AC2: STATUS_KEYS and NOT_AVAILABLE are the contract's."""
        self.assertEqual(execution.STATUS_KEYS, ('progress', 'drift', 'waiting_for_approval',
                                                 'requirements_lacking_assurance'))
        self.assertEqual(execution.NOT_AVAILABLE, 'not available')

    def test_task_states_once_over_the_same_bytes(self):
        """TASK-093 AC2: task_states is called once, with the bytes read_log gave and the approved ids in task-number
        order."""
        log = three()
        real = execution.task_states
        calls = []

        def counted(data, ids):
            calls.append((data, list(ids)))
            return real(data, ids)

        with mock.patch.object(execution, 'task_states', counted):
            (value, found), _ = report(log.data)
        self.assertIsNone(found)
        self.assertEqual(calls, [(log.data, ['TASK-2', 'TASK-9', 'TASK-10'])])

    def test_no_approved_task_and_the_empty_log(self):
        """TASK-093 AC2: a log with no task.approved, and an empty log (b''), give progress [] and the three other
        items "not available"."""
        drafted = Log().add('task.drafted', {'contract_version': 'v1', 'contract_hash': H1}, 'd1', 'TASK-1')
        for data in (drafted.data, b''):
            (value, found), reader = report(data)
            self.assertEqual((value, found), (dict(OTHERS, progress=[]), None), data)
            self.assertEqual(reader.calls, [ROOT])

    def test_a_duplicate_approval_lists_its_task_once(self):
        """TASK-093 AC2: a duplicated task.approved line lists its task once."""
        (value, found), _ = report(Log().approve('TASK-1').duplicate(0).data)
        self.assertIsNone(found)
        self.assertEqual(value['progress'], [{'task': 'TASK-1', 'state': 'READY', 'stale_evidence': False}])

    def test_reads_only_the_log(self):
        """TASK-093 AC2: by ast, status_report names no held_leases and uses no attribute of writer but read_log."""
        node = function('status_report', 'execution.py')
        self.assertNotIn('held_leases', used_names(node))
        uses = {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                and n.value.id == 'writer'}
        self.assertEqual(uses, {'read_log'})


class TASK093AC3Findings(unittest.TestCase):
    def assert_findings(self, answer):
        value, found = answer
        self.assertIsNone(value)
        self.assertTrue(type(found) is list and found and all(isinstance(f, str) for f in found), found)
        return found

    def test_read_log_not_bytes(self):
        """TASK-093 AC3: read_log giving a str, None or a bytearray gives "log: read_log gave <type>, not bytes"."""
        for data, kind in (('text', 'str'), (None, 'NoneType'), (bytearray(b''), 'bytearray')):
            answer, _ = report(data)
            self.assertEqual(answer, (None, ['log: read_log gave %s, not bytes' % kind]))

    def test_a_log_check_log_refuses(self):
        """TASK-093 AC3: bytes that check_log refuses give "log: line <n>: ..." findings and no partial answer."""
        for data in (b'not json\n', three().data + b'{"seq": 9}\n'):
            answer, _ = report(data)
            found = self.assert_findings(answer)
            self.assertTrue(all(f.startswith('log: line ') for f in found), found)

    def test_task_states_findings_as_given(self):
        """TASK-093 AC3: a log whose task events the projection refuses (a task.* type it does not name, made by
        patching STATE_OF) gives task_states' findings as they are."""
        log = Log().approve('TASK-1').approve('TASK-2').done('TASK-2')
        names = {k: v for k, v in execution.STATE_OF.items() if k != 'task.done'}
        with mock.patch.object(execution, 'STATE_OF', names):
            expected = execution.task_states(log.data, ['TASK-1', 'TASK-2'])
            answer, _ = report(log.data)
        self.assertIsNone(expected[0])
        self.assertEqual(answer, (None, expected[1]))
        self.assertIn('task.done is a task event the projection does not name', answer[1][0])

    def test_raises_never_escape(self):
        """TASK-093 AC3: a raise in read_log or in task_states gives "status_report: a step raised <type>" and no
        partial answer."""
        for exc in (RuntimeError('x'), RecursionError('deep'), MemoryError(), OSError('disk')):
            answer, _ = report(exc)
            self.assertEqual(answer, (None, ['status_report: a step raised %s' % type(exc).__name__]))
            with mock.patch.object(execution, 'task_states', mock.Mock(side_effect=exc)):
                answer, _ = report(three().data)
            self.assertEqual(answer, (None, ['status_report: a step raised %s' % type(exc).__name__]))


class Sink:
    def __init__(self):
        self.writes = []
        self.flushes = 0

    def write(self, text):
        self.writes.append(text)

    def flush(self):
        self.flushes += 1


class Clock:
    def __init__(self, raises=None):
        self.calls = 0
        self.raises = raises

    def __call__(self):
        self.calls += 1
        if self.raises is not None:
            raise self.raises
        return NOW


class Stand:
    """execution.status_report as a stand-in: gives its answer, or raises, and records each call."""

    def __init__(self, answer, raises=None):
        self.calls = []
        self.answer = answer
        self.raises = raises

    def __call__(self, root, now):
        self.calls.append((root, now))
        if self.raises is not None:
            raise self.raises
        return self.answer


PROGRESS = [{'task': 'TASK-2', 'state': 'REWORK', 'stale_evidence': False},
            {'task': 'TASK-9', 'state': 'DONE', 'stale_evidence': True}]
TEXT = ('progress: TASK-2 REWORK\n'
        'progress: TASK-9 DONE stale\n'
        'drift: not available\n'
        'waiting for approval: not available\n'
        'requirements lacking assurance: not available\n')
JSON = ('{"drift": "not available", "progress": [{"stale_evidence": false, "state": "REWORK", "task": "TASK-2"}, '
        '{"stale_evidence": true, "state": "DONE", "task": "TASK-9"}], "requirements_lacking_assurance": '
        '"not available", "waiting_for_approval": "not available"}\n')


def answer_of(progress=PROGRESS, **changes):
    value = {'progress': progress, 'drift': NA, 'waiting_for_approval': NA, 'requirements_lacking_assurance': NA}
    value.update(changes)
    return value


GOOD = object()


def run(argv, answer=GOOD, raises=None, clock=None, environ=None):
    sink = Sink()
    clock = Clock() if clock is None else clock
    stand = Stand((answer_of(), None) if answer is GOOD else answer, raises)
    with mock.patch.object(execution, 'status_report', stand):
        rc = cli.main(argv, sink, {} if environ is None else environ, clock)
    return rc, ''.join(sink.writes), stand, clock


def status(*flags):
    return ['status', '--root', ROOT] + list(flags)


class SubList(list):
    pass


class TASK093AC4Command(unittest.TestCase):
    def test_one_clock_and_one_status_report_call(self):
        """TASK-093 AC4: "status --root R" and "status --root R --json" (either flag order) call the clock once and
        status_report once with (R, the clock's value), giving exit 0."""
        for argv in (status(), status('--json'), ['status', '--json', '--root', ROOT]):
            rc, _, stand, clock = run(argv)
            self.assertEqual((rc, stand.calls, clock.calls), (0, [(ROOT, NOW)], 1), argv)

    def test_usage_errors(self):
        """TASK-093 AC4: "status", "status --root", "status --root R extra", "status R --root R" and "status --root
        R --json --json" give exit 2 and USAGE with nothing called."""
        for argv in (['status'], ['status', '--root'], status('extra'), ['status', ROOT, '--root', ROOT],
                     status('--json', '--json'), ['Status', '--root', ROOT]):
            rc, out, stand, clock = run(argv)
            self.assertEqual((rc, out, stand.calls, clock.calls), (2, cli.USAGE, [], 0), argv)

    def test_the_text_lines(self):
        """TASK-093 AC4: an answer gives exit 0, the progress lines in order (a stale task with " stale"), then the
        three "not available" lines."""
        self.assertEqual(run(status())[:2], (0, TEXT))

    def test_no_approved_task(self):
        """TASK-093 AC4: an answer with progress [] gives "progress: no approved task" and the three lines."""
        rc, out, _, _ = run(status(), answer=(answer_of([]), None))
        self.assertEqual((rc, out), (0, 'progress: no approved task\n' + TEXT.split('\n', 2)[2]))

    def test_the_json_line(self):
        """TASK-093 AC4: under --json the output is the exact expected line, sort_keys applied, the stand-in's items
        carrying their keys in the order task, state, stale_evidence."""
        rc, out, _, _ = run(status('--json'))
        self.assertEqual((rc, out), (0, JSON))
        self.assertEqual(json.loads(out), answer_of())

    def test_findings(self):
        """TASK-093 AC4: findings give exit 1 and their str items, as text lines or one JSON line."""
        rc, out, _, _ = run(status(), answer=(None, ['a', 3, 'b']))
        self.assertEqual((rc, out), (1, 'finding: a\nfinding: b\n'))
        rc, out, _, _ = run(status(), answer=(None, ('t',)))
        self.assertEqual((rc, out), (1, 'finding: t\n'))
        rc, out, _, _ = run(status('--json'), answer=(None, ['a', 3, 'b']))
        self.assertEqual((rc, out), (1, '{"findings": ["a", "b"]}\n'))

    def test_no_finding(self):
        """TASK-093 AC4: (None, None), (None, 'x'), (None, [3]) and (None, []) give exit 1 and the no-finding
        line."""
        for found in (None, 'x', [3], []):
            rc, out, _, _ = run(status(), answer=(None, found))
            self.assertEqual((rc, out), (1, 'finding: status: status_report gave no finding\n'), found)

    def test_answers_out_of_form(self):
        """TASK-093 AC4: an answer not a tuple of two, a list in place of the tuple, an OrderedDict answer, other
        keys, a list subclass for progress, an item with a non-str state or a stale_evidence of 1, an item with
        other keys, an item other than "not available", or a second other than None gives the out-of-form
        finding."""
        good = answer_of()
        item = dict(PROGRESS[0])
        bad = [
            'x', None, (good,), (good, None, None), [good, None], (OrderedDict(good), None),
            (dict(good, extra=NA), None), ({k: v for k, v in good.items() if k != 'drift'}, None),
            (answer_of(SubList(PROGRESS)), None), (answer_of((item,)), None),
            (answer_of([dict(item, state=3)]), None), (answer_of([dict(item, stale_evidence=1)]), None),
            (answer_of([dict(item, extra=1)]), None), (answer_of([OrderedDict(item)]), None),
            (answer_of(drift=0), None), (answer_of(waiting_for_approval='n/a'), None),
            (answer_of(requirements_lacking_assurance=None), None), (good, []), (good, 'x'),
        ]
        for answer in bad:
            rc, out, _, _ = run(status(), answer=answer)
            self.assertEqual((rc, out), (1, 'finding: status: status_report gave an answer out of form\n'), answer)

    def test_raising_steps(self):
        """TASK-093 AC4: a raising clock or status_report gives "status: a step raised <type>", the clock's raise
        with status_report not called."""
        rc, out, stand, _ = run(status(), clock=Clock(RuntimeError('clock')))
        self.assertEqual((rc, out, stand.calls), (1, 'finding: status: a step raised RuntimeError\n', []))
        rc, out, _, _ = run(status(), raises=MemoryError())
        self.assertEqual((rc, out), (1, 'finding: status: a step raised MemoryError\n'))

    def test_a_raising_render(self):
        """TASK-093 AC4: a raising _render_status (patched) gives exit 1 and "cli: a step raised <type>"."""
        with mock.patch.object(cli, '_render_status', mock.Mock(side_effect=ValueError('render'))):
            rc, out, _, _ = run(status())
        self.assertEqual((rc, out), (1, 'finding: cli: a step raised ValueError\n'))

    def test_not_refused_inside_a_runtime(self):
        """TASK-093 AC4: an environ holding the three RUNTIME_VARS gives the same output as {}, and in_runtime is not
        called."""
        inside = {name: 'x' for name in cli.RUNTIME_VARS}
        watch = mock.Mock(return_value=True)
        with mock.patch.object(cli, 'in_runtime', watch):
            self.assertEqual(run(status(), environ=inside)[:2], run(status(), environ={})[:2])
        self.assertEqual(watch.call_count, 0)

    def test_over_the_real_status_report(self):
        """TASK-093 AC4: with writer.read_log patched to give the AC2 log, the real status_report gives exit 0 and
        the three progress lines in task-number order."""
        reader = Reader(three().data)
        sink = Sink()
        with mock.patch.object(writer, 'read_log', reader):
            rc = cli.main(status(), sink, {}, Clock())
        self.assertEqual((rc, ''.join(sink.writes), reader.calls),
                         (0, 'progress: TASK-2 REWORK\nprogress: TASK-9 DONE stale\nprogress: TASK-10 READY\n'
                          + TEXT.split('\n', 2)[2], [ROOT]))


class TASK093AC5Modules(unittest.TestCase):
    def test_the_command_functions(self):
        """TASK-093 AC5: by ast, cli.py's _status and _render_status name no writer, held_leases or in_runtime."""
        for name in ('_status', '_render_status'):
            self.assertFalse(used_names(function(name, 'cli.py')) & {'writer', 'held_leases', 'in_runtime'}, name)

    def test_the_added_block(self):
        """TASK-093 AC5: by ast, status_report names no attribute now or write and no Name open, os, sys or time."""
        node = function('status_report', 'execution.py')
        attrs = {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}
        names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        self.assertFalse(attrs & {'now', 'write'})
        self.assertFalse(names & {'open', 'os', 'sys', 'time'})

    def test_this_test_file(self):
        """TASK-093 AC5: this file imports no tempfile, sqlite3 or shutil, names no open, roots only the literal
        'C:/status-root-93', and has no one-argument .replace() and no .replace(target=...)."""
        tree = ast.parse(HERE.read_bytes().decode('utf-8'))
        imported = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imported.update(a.name.split('.')[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                imported.add((n.module or '').split('.')[0])
        self.assertEqual(imported & {'tempfile', 'sqlite3', 'shutil'}, set())
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == 'open'])
        roots = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                 and len(n.value) > 3 and n.value.startswith('C:/')]
        self.assertEqual(set(roots), {ROOT})
        replaces = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == 'replace' and (len(n.args) == 1 or [k.arg for k in n.keywords] == ['target'])]
        self.assertEqual(replaces, [])


EXECUTION_KEPT = ('What it does not do', 'DEF-0030', 'Point (i)', 'DEF-0055 P6', 'decision D-687 M4',
                  'it gathers no Resume Check input', 'no task.unblocked', 'expires no lease', 'One run at a time',
                  'task_view', 'TASK-086', 'execute itself still gathers no Resume Check input', 'task_states',
                  'rework_count', 'TASK-088', 'list_tasks', 'the tasks that may be taken', 'DEF-0099', 'reads only')
CLI_KEPT = ('python -m aieos_bootstrap.cli', 'the installed name is open', 'writes nothing', 'never raises',
            'every Exception', 'outside any runtime', 'AIEOS_BASE is counted', "'' counts as present", 'spec 5 :120',
            '__init__.py is not changed', 'TASK-091', 'end <session>', 'refused inside a runtime', 'TASK-092')


def doc(file_name):
    return ' '.join(ast.get_docstring(ast.parse((SRC / file_name).read_bytes().decode('utf-8'))).split())


class TASK093AC6Docs(unittest.TestCase):
    def test_the_execution_paragraph(self):
        """TASK-093 AC6: execution.py's docstring holds the new paragraph's five phrases and keeps every phrase of
        the module's four pinning tests."""
        text = doc('execution.py')
        for phrase in ('status_report', 'TASK-093', 'not available', 'reads the log once', 'no held_leases'):
            self.assertIn(phrase, text)
        for phrase in EXECUTION_KEPT:
            self.assertIn(phrase, text)

    def test_the_cli_docstring_and_usage(self):
        """TASK-093 AC6, as TASK-095 AC6, TASK-094 AC6, TASK-096 AC6, TASK-097 AC6 and TASK-098 AC6 widen it: cli.py's
        docstring holds "aieos status" and "TASK-093", names status, init, launch, approve, edit, reject, import and
        run in its list of COMMANDS, keeps its pinned phrases and holds none of the eight replaced ones; USAGE names
        status."""
        text = doc('cli.py')
        for phrase in ('aieos status', 'TASK-093',
                       'COMMANDS, tasks, end, status, init, launch, approve, edit, reject, import or run') + CLI_KEPT:
            self.assertIn(phrase, text)
        for phrase in ('COMMANDS, tasks or end', 'COMMANDS, tasks, end or status', 'whose only entry is tasks',
                       'come with later tasks', 'COMMANDS, tasks, end, status or init',
                       'COMMANDS, tasks, end, status, init or launch',
                       'COMMANDS, tasks, end, status, init, launch, approve, edit or reject',
                       'COMMANDS, tasks, end, status, init, launch, approve, edit, reject or import'):
            self.assertNotIn(phrase, text)
        self.assertIn('status --root <path> [--json]', cli.USAGE)
        self.assertEqual(cli.COMMANDS, ('tasks', 'end', 'status', 'init', 'launch', 'approve', 'edit', 'reject',
                                        'import', 'run'))

    def test_every_test_names_its_criteria(self):
        """TASK-093 AC6: every test function of this module names "TASK-093 AC" in its own docstring, more than 20
        in all."""
        tree = ast.parse(HERE.read_bytes().decode('utf-8'))
        tests = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
        self.assertGreater(len(tests), 20)
        for node in tests:
            self.assertIn('TASK-093 AC', ast.get_docstring(node) or '', node.name)


if __name__ == '__main__':
    unittest.main()

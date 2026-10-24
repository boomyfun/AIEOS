"""Unit tests of aieos_bootstrap.read_set_record.observe_gone (task TASK-089): the record of a session whose lease is
gone, as the core's own observation with no fencing token. The append is a stand-in that records its calls, bound to
writer.append_event's signature; the event log's own form is exercised by eventlog.append over bytes held in memory;
no test writes a file, runs Git or reads a clock; the root is a literal Windows path that names no folder."""

import ast
import datetime
import inspect
import pathlib
import types
import unittest

from aieos_bootstrap import claude_code, claude_code_channel, eventlog, read_set_record, records, writer

HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / 'src' / 'aieos_bootstrap' / 'read_set_record.py'
ROOT = 'C:/read-set-gone-root-89'
TASK = 'TASK-100'
SESSION = 'session-1'
NOW = datetime.datetime(2026, 10, 25, 12, 0, 0, tzinfo=datetime.timezone.utc)
REC = 'aieos-launcher (unit) ' + SESSION
READS = ['src/b.py', 'src/a.py', 'src/b.py']
GONE = read_set_record.GONE_WHY


def answer(result, reason=None):
    return types.SimpleNamespace(result=result, reason=reason, seq=1 if result == 'appended' else None,
                                 findings=() if result in ('appended', 'duplicate') else ('a core finding',))


class Append:
    """A stand-in for writer.append_event that records its calls and gives a set answer, or raises."""

    def __init__(self, given):
        self.given = given
        self.calls = []

    def __call__(self, *args, **kwargs):
        inspect.signature(writer.append_event).bind(*args, **kwargs)
        self.calls.append((args, kwargs))
        if isinstance(self.given, BaseException):
            raise self.given
        return self.given


def gone(append, **over):
    args = dict(root=ROOT, task_id=TASK, session_id=SESSION, read_paths=list(READS), reason=GONE[1], now=NOW,
                recorder=REC, append=append)
    args.update(over)
    return read_set_record.observe_gone(**args)


class TASK089AC4ObserveGone(unittest.TestCase):
    def test_one_append_with_no_token(self):
        """TASK-089 AC4: one append of record.added, task_id the task, no fencing_token argument, the event id
        record_ids gives, the record build gives for "<recorder>; written by the core without a held lease:
        <reason>", that same text as the append's recorder; records.check_record finds nothing."""
        for why in GONE:
            append = Append(answer('appended'))
            r = gone(append, reason=why)
            self.assertEqual((tuple(r), r['result'], r['reason']), (read_set_record.RESULT_KEYS, 'written', None))
            self.assertEqual(len(append.calls), 1)
            args, kwargs = append.calls[0]
            text = REC + '; written by the core without a held lease: ' + why
            event_id, record_id = read_set_record.record_ids(TASK, SESSION)
            self.assertEqual(args[:2], (ROOT, 'record.added'))
            self.assertEqual((args[3], args[4], args[5]), (event_id, NOW, text))
            self.assertEqual(kwargs, {'task_id': TASK})
            record = args[2]
            self.assertEqual(record, read_set_record.build(TASK, SESSION, list(READS), text))
            self.assertEqual(record['recorder'], claude_code.RECORDER + claude_code_channel.RECORDER_JOIN + text)
            self.assertEqual((record['record_id'], record['read_paths'], record['evidence_type']),
                             (record_id, ['src/b.py', 'src/a.py'], records.READ_SET_TYPE))
            self.assertFalse(records.check_record(record))
            self.assertEqual(r['record'], record)

    def test_the_answers(self):
        """TASK-089 AC4: "appended" gives "written", "duplicate" gives "duplicate", any other answer gives
        "refused" with reason "core" and the core mapping in "core" (a "conflict" stand-in gives core reason
        "conflict"); a raising append gives "refused" with reason "observe"; it never raises."""
        r = gone(Append(answer('duplicate')))
        self.assertEqual((r['result'], r['reason']), ('duplicate', None))
        for reason in ('conflict', 'fence', 'log'):
            r = gone(Append(answer('refused', reason)))
            self.assertEqual((r['result'], r['reason']), ('refused', 'core'))
            self.assertEqual((r['core']['result'], r['core']['reason']), ('refused', reason))
            self.assertIn('a core finding', r['findings'])
        r = gone(Append(RuntimeError('x')))
        self.assertEqual((r['result'], r['reason']), ('refused', 'observe'))
        self.assertEqual(r['findings'], ['RuntimeError raised inside observe_gone'])
        self.assertIsNotNone(r['record'])

    def test_each_argument_out_of_form(self):
        """TASK-089 AC4: a bad root, task_id, session_id, a reason outside GONE_WHY, now out of form, or a recorder
        without the session id gives reason "argument"; read_paths not a list of non-empty strs gives reason
        "read_paths"; no append in either case."""
        argument = [dict(root=''), dict(root=None), dict(task_id='T-1'), dict(session_id='a/b'), dict(session_id=''),
                    dict(reason='expired'), dict(reason=None), dict(now=NOW.replace(tzinfo=None)),
                    dict(now=NOW.replace(microsecond=5)), dict(recorder='no session here'), dict(recorder='')]
        for over in argument:
            append = Append(answer('appended'))
            r = gone(append, **over)
            self.assertEqual((r['result'], r['reason']), ('refused', 'argument'), over)
            self.assertEqual(append.calls, [], over)
        for paths in ('src/a.py', ['src/a.py', ''], [1], None):
            append = Append(answer('appended'))
            r = gone(append, read_paths=paths)
            self.assertEqual((r['result'], r['reason']), ('refused', 'read_paths'), paths)
            self.assertEqual(append.calls, [], paths)

    def test_the_reason_sets(self):
        """TASK-089 AC4: GONE_WHY and GONE_RESULT_REASONS are exactly the contract's tuples, and every result reason
        is in GONE_RESULT_REASONS; REASONS is unchanged."""
        self.assertEqual(read_set_record.GONE_WHY,
                         ('violation', 'lease gone (released or expired)', 'no fencing token given'))
        self.assertEqual(read_set_record.GONE_RESULT_REASONS, ('argument', 'read_paths', 'core', 'observe'))
        self.assertEqual(read_set_record.REASONS, ('context', 'now', 'session_id', 'read_paths', 'core', 'observe'))
        for r in (gone(Append(answer('refused', 'log'))), gone(Append(RuntimeError('x'))), gone(None, task_id=1),
                  gone(None, read_paths=None)):
            self.assertIn(r['reason'], read_set_record.GONE_RESULT_REASONS)

    def test_no_reads(self):
        """TASK-089 AC4: an empty read_paths is a record of no reads."""
        append = Append(answer('appended'))
        r = gone(append, read_paths=[])
        self.assertEqual((r['result'], r['record']['read_paths']), ('written', []))


class TASK089AC8EventLog(unittest.TestCase):
    def test_a_real_append_needs_no_lease(self):
        """TASK-089 AC8: observe_gone's record line, appended with eventlog.append to an in-memory log with no
        fencing_token and no lease, is "appended", and a second append of the same event gives "duplicate"."""
        append = Append(answer('appended'))
        gone(append)
        args, kwargs = append.calls[0]
        _, event_type, record, event_id, now, recorder = args
        first = eventlog.append(b'', event_type, record, event_id, now, task_id=kwargs['task_id'])
        self.assertEqual(first.result, 'appended', first.findings)
        second = eventlog.append(first.line, event_type, record, event_id, now, task_id=kwargs['task_id'])
        self.assertEqual(second.result, 'duplicate', second.findings)


class TASK089AC10Module(unittest.TestCase):
    def test_the_imports_and_the_paragraph(self):
        """TASK-089 AC10, AC11: read_set_record.py's import set stays exactly the pinned one; its 22 pinned phrases
        stay; its new paragraph names observe_gone, TASK-089 and point 10, and says the two older statements no
        longer hold. The diff from the base being added lines only is checked at G3 by the task's own check, since
        no test runs Git."""
        text = SRC.read_bytes().decode('utf-8')
        tree = ast.parse(text)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.update(node.module + '.' + a.name for a in node.names)
        self.assertEqual(imports, {'datetime', 're', 'aieos_bootstrap.claude_code',
                                   'aieos_bootstrap.claude_code_channel', 'aieos_bootstrap.records',
                                   'aieos_bootstrap.writer'})
        doc = ' '.join(ast.get_docstring(tree).split())
        for words in ('TASK-063', 'context_findings', "lease holder's action", 'before the lease is released',
                      'observed-read-set/<task_id>/<session_id>', '"duplicate"', '"conflict"', 'eventlog.py:180-184',
                      'at most one such record per task and session_id', 'two session_ids for one session',
                      'exact string equality', 'section 10 point 13', 'lower bound at best', 'proves nothing',
                      'kept and not used', 'tier T3', 'CC-3', 'section 11 point 8', 'point 10', 'is then not known',
                      'not pure', 'claude_code_channel.RECORDER_JOIN', 'observe_gone', 'TASK-089',
                      'no longer hold', 'Three functions, called only by their tests', 'GONE_WHY',
                      'GONE_RESULT_REASONS'):
            self.assertIn(words, doc, words)


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

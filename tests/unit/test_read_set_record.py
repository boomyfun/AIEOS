"""Unit tests of aieos_bootstrap.read_set_record (task TASK-064, rules R3 to R7): the derived ids, the record, observe's
order and result, and the script checks of AC6 and AC7, over values made up for the test. append is a stand-in, so no
file is written and no process starts. Each test names its criteria in its own docstring."""

import ast
import copy
import datetime
import pathlib
import types
import unittest

from aieos_bootstrap import claude_code
from aieos_bootstrap import claude_code_channel
from aieos_bootstrap import read_set_record as rs
from aieos_bootstrap import records

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap' / 'read_set_record.py'
NOW = datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)
SID = 'made-up-session-7'
EVENT = 'observed-read-set/TASK-100/' + SID


def context(**kw):
    c = {'root': 'C:\\proj\\repo', 'task_id': 'TASK-100', 'session_id': SID,
         'fencing_token': {'epoch': 'e1', 'counter': 3}, 'write_set': ['docs/notes/**'],
         'allowlist': ['git status', 'git diff --stat'], 'recorder': 'a test session ' + SID}
    c.update(kw)
    return c


class Store:
    """A stand-in for writer.append_event that records its calls."""

    def __init__(self, state='appended', reason=None, raise_it=False, findings=()):
        self.calls = []
        self.state = state
        self.reason = reason
        self.raise_it = raise_it
        self.findings = findings

    def append(self, root, event_type, payload, event_id, now, recorder, task_id=None, fencing_token=None):
        self.calls.append((root, event_type, copy.deepcopy(payload), event_id, now, recorder, task_id, fencing_token))
        if self.raise_it:
            raise RuntimeError('made-up fault')
        return types.SimpleNamespace(result=self.state, reason=self.reason, seq=4, findings=self.findings)


def observe(ctx=None, paths=None, now=NOW, store=None):
    store = store or Store()
    return rs.observe(context() if ctx is None else ctx, ['a/b.py', 'c.md'] if paths is None else paths, now,
                      append=store.append), store


class Ids(unittest.TestCase):
    def test_derived_ids(self):
        """TASK-064 AC3: the event_id and record_id are derived from the task and the session."""
        self.assertEqual(rs.record_ids('TASK-100', SID), (EVENT, EVENT + '/record'))

    def test_ids_out_of_form(self):
        """TASK-064 AC3: a task_id or session_id out of form gives None, and nothing raises."""
        for task_id, session_id in (('TASK-x', SID), ('task-1', SID), (None, SID), ('TASK-1', ''), ('TASK-1', 'a b'),
                                    ('TASK-1', 'a/b'), ('TASK-1', None), ('TASK-1', 7), ('TASK-1', 'a\tb')):
            self.assertIsNone(rs.record_ids(task_id, session_id), (task_id, session_id))

    def test_ids_keep_other_characters(self):
        """TASK-064 AC3: a session_id holding a NUL, a backslash, a colon or two dots is kept verbatim in the ids (only
        whitespace and "/" are refused)."""
        for sid in ('a\x00b', 'a\\b', 'a:b', '..'):
            self.assertEqual(rs.record_ids('TASK-1', sid),
                             ('observed-read-set/TASK-1/' + sid, 'observed-read-set/TASK-1/' + sid + '/record'), sid)


class Build(unittest.TestCase):
    def test_the_record(self):
        """TASK-064 AC4: the record has exactly its keys, the exact recorder text, and passes check_record."""
        r = rs.build('TASK-100', SID, ['a/b.py'], 'a test session ' + SID)
        self.assertEqual(r, {'record_id': EVENT + '/record', 'fact_kind': 'observation',
                             'source_class': 'deterministic_tool_local',
                             'recorder': claude_code.RECORDER + ', for ' + 'a test session ' + SID,
                             'subject': 'TASK-100', 'evidence_type': 'observed_read_set', 'read_paths': ['a/b.py']})
        self.assertEqual(r['recorder'], claude_code.RECORDER + claude_code_channel.RECORDER_JOIN + 'a test session ' + SID)
        self.assertEqual(records.check_record(r), [])

    def test_repeats_removed_order_kept(self):
        """TASK-064 AC4: repeats are removed by exact string, the first order kept, and the given list is unchanged."""
        given = ['z.py', 'a.py', 'z.py', 'A.py', 'a.py', 'a.py ']
        kept = list(given)
        r = rs.build('TASK-100', SID, given, 'rec ' + SID)
        self.assertEqual(r['read_paths'], ['z.py', 'a.py', 'A.py', 'a.py '])
        self.assertEqual(given, kept)

    def test_no_normalising(self):
        """TASK-064 AC4: no path is normalised, case-folded or checked against a root or the disk."""
        paths = ['C:\\x\\y', '../up', './a', 'a//b', 'A/B', '/abs']
        self.assertEqual(rs.build('TASK-100', SID, paths, 'rec ' + SID)['read_paths'], paths)

    def test_empty_list(self):
        """TASK-064 AC4: an empty list gives a record with an empty read_paths."""
        self.assertEqual(rs.build('TASK-100', SID, [], 'rec ' + SID)['read_paths'], [])

    def test_arguments_out_of_form(self):
        """TASK-064 AC4: each argument out of form gives None, the recorder without the session id among them."""
        for args in (('TASK-x', SID, [], 'rec ' + SID), ('TASK-100', 'a/b', [], 'rec a/b'),
                     ('TASK-100', SID, 'a.py', 'rec ' + SID), ('TASK-100', SID, ['a.py', ''], 'rec ' + SID),
                     ('TASK-100', SID, ['a.py', 3], 'rec ' + SID), ('TASK-100', SID, None, 'rec ' + SID),
                     ('TASK-100', SID, [], ''), ('TASK-100', SID, [], 'rec without it'),
                     ('TASK-100', SID, [], None), ('TASK-100', SID, ('a.py',), 'rec ' + SID)):
            self.assertIsNone(rs.build(*args), args)

    def test_subclasses_as_given(self):
        """TASK-064 AC4: a list or str subclass is taken as given; read_paths is a plain list and its items keep their
        type (outside the trusted-caller model)."""
        class L(list):
            pass

        class S(str):
            pass
        r = rs.build('TASK-100', SID, L([S('a'), 'a']), 'rec ' + SID)
        self.assertEqual(r['read_paths'], ['a'])
        self.assertIs(type(r['read_paths']), list)
        self.assertIs(type(r['read_paths'][0]), S)


class Observe(unittest.TestCase):
    def test_written_once_with_the_exact_arguments(self):
        """TASK-064 AC5: append is called once with the context's root, task_id, fencing_token and recorder, the derived
        event_id and the record; "appended" gives "written"."""
        result, store = observe()
        self.assertEqual(set(result), set(rs.RESULT_KEYS))
        self.assertEqual((result['result'], result['reason'], result['findings']), ('written', None, []))
        rec = rs.build('TASK-100', SID, ['a/b.py', 'c.md'], 'a test session ' + SID)
        self.assertEqual(store.calls, [('C:\\proj\\repo', 'record.added', rec, EVENT, NOW, 'a test session ' + SID,
                                        'TASK-100', {'epoch': 'e1', 'counter': 3})])
        self.assertEqual(result['record'], rec)
        self.assertEqual(result['core'], {'result': 'appended', 'reason': None, 'seq': 4, 'findings': []})

    def test_duplicate_and_refusals_mapped(self):
        """TASK-064 AC5: "duplicate" gives "duplicate"; a refusal, the fence's and the conflict's among them, gives
        "refused" with reason "core", the append result's reason in core."""
        result, _ = observe(store=Store('duplicate'))
        self.assertEqual((result['result'], result['reason']), ('duplicate', None))
        for reason in ('fence', 'conflict', 'event'):
            result, store = observe(store=Store('refused', reason, findings=('made-up finding',)))
            self.assertEqual((result['result'], result['reason'], result['core']['reason']), ('refused', 'core', reason))
            self.assertIn('made-up finding', result['findings'])
            self.assertEqual(len(store.calls), 1)

    def test_order_of_checks(self):
        """TASK-064 AC5: context, then now, then session_id, then read_paths; append is not called for any of them."""
        cases = ((context(task_id='bad'), ['a'], NOW, 'context'),
                 (context(task_id='bad'), 'x', None, 'context'),
                 (context(), ['a'], None, 'now'),
                 (context(), 'x', NOW.replace(tzinfo=None), 'now'),
                 (context(), ['a'], NOW.replace(microsecond=5), 'now'),
                 (context(session_id='s/1', recorder='rec s/1'), 'x', NOW, 'session_id'),
                 (context(), 'x', NOW, 'read_paths'),
                 (context(), ['a', ''], NOW, 'read_paths'))
        for ctx, paths, now, reason in cases:
            result, store = observe(ctx, paths, now)
            self.assertEqual((result['result'], result['reason'], result['record']), ('refused', reason, None), reason)
            self.assertEqual(store.calls, [])

    def test_fault_in_append_keeps_the_record(self):
        """TASK-064 AC5: a fault raised by append gives "observe", the exception's type in findings, and the record."""
        result, store = observe(store=Store(raise_it=True))
        self.assertEqual((result['result'], result['reason']), ('refused', 'observe'))
        self.assertEqual(result['findings'], ['RuntimeError raised inside observe'])
        self.assertEqual(result['record']['record_id'], EVENT + '/record')
        self.assertEqual(len(store.calls), 1)

    def test_fault_before_the_call_keeps_no_record(self):
        """TASK-064 AC5: a fault before append is called gives "observe" with record None and no call."""

        class Odd(datetime.datetime):
            def utcoffset(self):
                raise ValueError('made-up fault')

        store = Store()
        odd = Odd(2026, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)
        result = rs.observe(context(), ['a'], odd, append=store.append)
        self.assertEqual((result['result'], result['reason'], result['record']), ('refused', 'observe', None))
        self.assertEqual(result['findings'], ['ValueError raised inside observe'])
        self.assertEqual(store.calls, [])

    def test_no_path_in_findings_and_inputs_unchanged(self):
        """TASK-064 AC5: no path of read_paths is copied into findings; the context and read_paths are not changed."""
        marker = 'MADE-UP-MARKER-PATH-91'
        ctx = context()
        paths = [marker + '/a.py', marker + '/a.py']
        ctx_copy, paths_copy = copy.deepcopy(ctx), list(paths)
        for store in (Store(), Store('refused', 'fence'), Store(raise_it=True)):
            result, _ = observe(ctx, paths, store=store)
            self.assertNotIn(marker, repr(result['findings']))
        result, _ = observe(ctx, paths + [''])
        self.assertNotIn(marker, repr(result))
        self.assertEqual((ctx, paths), (ctx_copy, paths_copy))

    def test_the_token_object_is_passed(self):
        """TASK-064 AC5: the context's fencing_token is passed to append as the same object (an append that changed it
        would change the context: a stated limit)."""
        ctx = context()
        _, store = observe(ctx)
        self.assertIs(store.calls[0][7], ctx['fencing_token'])

    def test_default_append_is_the_writer(self):
        """TASK-064 AC5, AC7: with no append given, observe calls writer.append_event, here refused by its own root
        check, which becomes a result."""
        result = rs.observe(context(root='C:\\made-up-missing-root-91'), ['a'], NOW)
        self.assertEqual((result['result'], result['reason']), ('refused', 'observe'))
        self.assertEqual(result['findings'], ['ValueError raised inside observe'])


class Statements(unittest.TestCase):
    def test_docstring_words(self):
        """TASK-064 AC6, AC3: the module's docstring states the interface, the ids and their limit, what a record shows,
        and what is not covered (the docstring's line breaks and indents read as single spaces)."""
        doc = ' '.join(ast.get_docstring(ast.parse(SRC.read_text(encoding='utf-8'))).split())
        for words in ('TASK-063', 'context_findings', "lease holder's action", 'before the lease is released',
                      'observed-read-set/<task_id>/<session_id>', '"duplicate"', '"conflict"', 'eventlog.py:180-184',
                      'at most one such record per task and session_id', 'two session_ids for one session',
                      'exact string equality', 'section 10 point 13', 'lower bound at best', 'proves nothing',
                      'kept and not used', 'tier T3', 'CC-3', 'section 11 point 8', 'point 10', 'is then not known',
                      'not pure', 'claude_code_channel.RECORDER_JOIN'):
            self.assertIn(words, doc, words)

    def test_imports_and_absent_calls(self):
        """TASK-064 AC7: only datetime, re and aieos_bootstrap's claude_code, claude_code_channel, records and writer are
        imported; no open, exec, eval, compile, __import__, importlib, print, sys, assert, os or subprocess; no name of
        the project-state directory."""
        text = SRC.read_text(encoding='utf-8')
        tree = ast.parse(text)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.update(node.module + '.' + a.name for a in node.names)
            self.assertNotIsInstance(node, ast.Assert)
        self.assertEqual(imports, {'datetime', 're', 'aieos_bootstrap.claude_code', 'aieos_bootstrap.claude_code_channel',
                                   'aieos_bootstrap.records', 'aieos_bootstrap.writer'})
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        for bad in ('open', 'exec', 'eval', 'compile', '__import__', 'importlib', 'print', 'sys', 'os', 'subprocess',
                    'input'):
            self.assertNotIn(bad, names)
        self.assertNotIn('.ai' + 'eos', text)


if __name__ == '__main__':
    unittest.main()

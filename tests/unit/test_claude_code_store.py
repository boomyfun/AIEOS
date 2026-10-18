"""Unit tests of aieos_bootstrap.claude_code_store (TASK-066 AC4 to AC7, AC9 rules R4 to R6): judge's values rule,
its upward search and its mapping, run with stand-ins only: claude_code_store's name os is replaced, for one call, by
a namespace giving only the functions judge uses, and writer.session_lease by a recording stand-in. No test writes a
file, makes a folder or opens a store; the paths are made-up absolute pieces derived from os.sep."""

import ast
import datetime
import os
import pathlib
import types
import unittest
from unittest import mock

from aieos_bootstrap import claude_code_store, writer

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
TOP = os.path.abspath(os.sep)
PROJ = os.path.join(TOP, 'made-up-proj')
SUB = os.path.join(PROJ, 'sub', 'deeper')
INNER = os.path.join(PROJ, 'sub')
LEASE = {'task_id': 'TASK-001', 'fencing_token': {'epoch': 'e', 'counter': 1},
         'expires_at': T0 + datetime.timedelta(hours=1)}
REGULAR = 0o100644
SOURCE = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap' / 'claude_code_store.py'
KEYS = {'outcome', 'reason', 'findings', 'root', 'lease'}


def fake_os(stores=(), dirs=(), errors=None, kinds=None):
    """A stand-in for claude_code_store's os: lstat over made-up entries, and the path functions judge uses."""
    stores, dirs, errors, kinds = set(stores), set(dirs), dict(errors or {}), dict(kinds or {})

    def lstat(p):
        if p in errors:
            raise errors[p]
        if p in kinds:
            return types.SimpleNamespace(st_mode=kinds[p])
        if p in stores:
            return types.SimpleNamespace(st_mode=REGULAR)
        raise FileNotFoundError(p)
    path = types.SimpleNamespace(abspath=os.path.abspath, isabs=os.path.isabs, isdir=lambda p: p in dirs,
                                 dirname=os.path.dirname)
    return types.SimpleNamespace(lstat=lstat, path=path)


class Recorder:
    """A stand-in for writer.session_lease that records its calls and gives a fixed answer."""

    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def __call__(self, root, session_id, now, *rest):
        self.calls.append((root, session_id, now) + rest)
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


TIED = object()


def run(session_id, root, working_folder, now=T0, answer=TIED, osns=None):
    rec = Recorder(writer.StoreResult('done', 'tied', value=LEASE) if answer is TIED else answer)
    with mock.patch.object(claude_code_store, 'os', osns or fake_os(dirs=[SUB, PROJ])), \
            mock.patch.object(writer, 'session_lease', rec):
        out = claude_code_store.judge(session_id, root, working_folder, now)
    return out, rec.calls


class R4ValuesRule(unittest.TestCase):

    def test_both_present_is_the_lookup_at_the_root(self):
        """TASK-066 AC4 and TASK-066 AC5: with a session id and a root, the lookup runs at that root only, no search
        is made, a bad working folder is ignored, and a tied answer gives "tied" with the lease and the root."""
        out, calls = run('s-1', PROJ, 'not absolute')
        self.assertEqual(out, {'outcome': 'tied', 'reason': 'tied', 'findings': [], 'root': PROJ, 'lease': LEASE})
        self.assertEqual(calls, [(PROJ, 's-1', T0)])
        out, calls = run(' ', PROJ, None)
        self.assertEqual((out['outcome'], calls), ('tied', [(PROJ, ' ', T0)]))

    def test_absent_values_are_none_and_the_empty_string(self):
        """TASK-066 AC4: None and "" are absent; a root without a session id and a session id without a root refuse,
        with no lookup."""
        for sid, root, reason in ((None, PROJ, 'root_without_session'), ('', PROJ, 'root_without_session'),
                                  ('s-1', None, 'session_without_root'), ('s-1', '', 'session_without_root'),
                                  (' ', None, 'session_without_root')):
            with self.subTest(sid=sid, root=root):
                out, calls = run(sid, root, PROJ)
                self.assertEqual((out['outcome'], out['reason'], out['lease'], out['root'], calls),
                                 ('refuse', reason, None, None, []))
                self.assertEqual(len(out['findings']), 1)

    def test_present_values_that_are_not_strings_refuse(self):
        """TASK-066 AC4: a present session id or root of another type, 0, False, [], b"" and a number among them,
        gives "argument" with no lookup."""
        for bad in (0, False, [], b'', 1.5, b's-1', ('s',)):
            for sid, root in ((bad, PROJ), ('s-1', bad), (bad, None), (None, bad)):
                with self.subTest(sid=sid, root=root):
                    out, calls = run(sid, root, PROJ)
                    self.assertEqual((out['outcome'], out['reason'], calls), ('refuse', 'argument', []))

    def test_a_present_root_must_be_absolute(self):
        """TASK-066 AC4: a relative root, or a whitespace-only root, refuses "argument" (fail closed)."""
        for root in ('made-up-proj', ' ', os.path.join('a', 'b')):
            with self.subTest(root=root):
                out, calls = run('s-1', root, PROJ)
                self.assertEqual((out['reason'], calls), ('argument', []))
                out, calls = run(None, root, PROJ)
                self.assertEqual((out['reason'], calls), ('argument', []))

    def test_a_bad_now_refuses_first(self):
        """TASK-066 AC4: now that is not a timezone-aware datetime in UTC with whole seconds refuses "argument",
        before any other rule; a raising tzinfo too."""

        class Raising(datetime.tzinfo):
            def utcoffset(self, dt):
                raise RuntimeError('made-up')
        bad_nows = (None, '2026-10-11T12:00:00Z', T0.replace(tzinfo=None), T0.replace(microsecond=5),
                    T0.astimezone(datetime.timezone(datetime.timedelta(hours=7))), T0.date(),
                    datetime.time(12, 0, tzinfo=UTC), 0, T0.replace(tzinfo=Raising()))
        for now in bad_nows:
            for args in (('s-1', PROJ, None), (None, None, PROJ), (0, None, 'x')):
                with self.subTest(now=now, args=args):
                    out, calls = run(*args, now=now)
                    self.assertEqual((out['outcome'], out['reason'], calls), ('refuse', 'argument', []))
                    self.assertTrue(out['findings'][0].startswith('argument: now'), out['findings'])
        self.assertEqual(run('s-1', PROJ, None, now=T0)[0]['outcome'], 'tied')

    def test_a_bad_working_folder_refuses_on_the_search_path(self):
        """TASK-066 AC4: with neither value, a working folder that is not a str, not absolute or not an existing
        folder refuses "argument" with no lookup."""
        for wf in (None, 7, b'/x', 'relative', os.path.join(PROJ, 'missing')):
            with self.subTest(wf=wf):
                out, calls = run(None, None, wf)
                self.assertEqual((out['reason'], calls), ('argument', []))


class R4UpwardSearch(unittest.TestCase):

    def test_the_nearest_store_is_found_and_looked_up_with_no_session(self):
        """TASK-066 AC4 and TASK-066 AC5: the search goes up from the working folder, passes folders with no store
        file, stops at the nearest store, and looks it up with no session id; "no_lease_row" there gives
        "enforce_nothing" with the folder found."""
        osns = fake_os(stores=[writer.store_path(PROJ)], dirs=[SUB])
        out, calls = run(None, None, SUB, answer=writer.StoreResult('done', 'no_lease_row'), osns=osns)
        self.assertEqual(out, {'outcome': 'enforce_nothing', 'reason': 'no_lease_row', 'findings': [], 'root': PROJ,
                               'lease': None})
        self.assertEqual(calls, [(PROJ, None, T0)])

    def test_an_inner_store_is_judged_alone(self):
        """TASK-066 AC4: a store found first in an inner folder is the one looked up, even with an outer store."""
        osns = fake_os(stores=[writer.store_path(PROJ), writer.store_path(INNER)], dirs=[SUB])
        out, calls = run(None, None, SUB, answer=writer.StoreResult('refused', 'lease_row_without_session',
                                                                    ['lease_row_without_session: x']), osns=osns)
        self.assertEqual((out['outcome'], out['reason'], out['root'], calls),
                         ('refuse', 'lease_row_without_session', INNER, [(INNER, None, T0)]))
        self.assertEqual(out['findings'], ['lease_row_without_session: x'])

    def test_no_store_up_to_the_top_enforces_nothing(self):
        """TASK-066 AC4: with no store in the working folder or any parent, up to the drive or share root, the result
        is "enforce_nothing", "no_store_found", with no lookup."""
        seen = []
        osns = fake_os(dirs=[SUB])
        real = osns.lstat

        def lstat(p):
            seen.append(p)
            return real(p)
        osns.lstat = lstat
        out, calls = run(None, None, SUB, osns=osns)
        self.assertEqual((out['outcome'], out['reason'], out['root'], out['lease'], calls),
                         ('enforce_nothing', 'no_store_found', None, None, []))
        self.assertEqual(seen, [writer.store_path(f) for f in (SUB, INNER, PROJ, TOP)])

    def test_a_folder_whose_state_folder_is_a_file_is_passed_over(self):
        """TASK-066 AC4: NotADirectoryError passes the folder over like FileNotFoundError."""
        osns = fake_os(stores=[writer.store_path(PROJ)], dirs=[SUB],
                       errors={writer.store_path(INNER): NotADirectoryError('x')})
        out, calls = run(None, None, SUB, osns=osns)
        self.assertEqual((out['outcome'], calls), ('tied', [(PROJ, None, T0)]))

    def test_an_entry_that_cannot_be_examined_refuses(self):
        """TASK-066 AC4: another OSError, a ValueError, or an entry that is not a regular file (a directory, a link, a
        dangling link, another kind) refuses "search" before the store above it is reached (fail closed)."""
        cases = [dict(errors={writer.store_path(INNER): PermissionError('x')}),
                 dict(errors={writer.store_path(INNER): OSError('x')}),
                 dict(errors={writer.store_path(INNER): ValueError('x')}),
                 dict(kinds={writer.store_path(INNER): 0o040755}),
                 dict(kinds={writer.store_path(INNER): 0o120777}),
                 dict(kinds={writer.store_path(INNER): 0o010644})]
        for kw in cases:
            with self.subTest(kw=kw):
                osns = fake_os(stores=[writer.store_path(PROJ)], dirs=[SUB], **kw)
                out, calls = run(None, None, SUB, osns=osns)
                self.assertEqual((out['outcome'], out['reason'], out['root'], calls), ('refuse', 'search', None, []))


class R4Mapping(unittest.TestCase):

    def test_every_refusal_is_passed_through(self):
        """TASK-066 AC5: every "refused" answer gives "refuse" with the same reason and findings, lease None."""
        for reason in ('argument', 'root', 'no_store', 'link', 'unreadable', 'tables', 'lease_row_without_session',
                       'no_lease_row', 'session', 'ended', 'leases'):
            with self.subTest(reason=reason):
                answer = writer.StoreResult('refused', reason, ['%s: made-up' % reason])
                out, _ = run('s-1', PROJ, None, answer=answer)
                self.assertEqual(out, {'outcome': 'refuse', 'reason': reason, 'findings': ['%s: made-up' % reason],
                                       'root': PROJ, 'lease': None})

    def test_odd_answers_give_entry(self):
        """TASK-066 AC5: "done" with another reason, "tied" with no lease, "no_lease_row" on the both-present path and
        a value that is not a StoreResult give "refuse", reason "entry"; enforce_nothing arises only with both
        absent."""
        odd = [writer.StoreResult('done', 'other', value=LEASE), writer.StoreResult('done', 'tied'),
               writer.StoreResult('done', 'no_lease_row'), writer.StoreResult('maybe', 'tied', value=LEASE),
               None, {'result': 'done', 'reason': 'tied', 'value': LEASE}, 'done']
        for answer in odd:
            with self.subTest(answer=answer):
                out, _ = run('s-1', PROJ, None, answer=answer)
                self.assertEqual((out['outcome'], out['reason'], out['lease']), ('refuse', 'entry', None))
        osns = fake_os(stores=[writer.store_path(PROJ)], dirs=[PROJ])
        out, _ = run(None, None, PROJ, answer=writer.StoreResult('done', 'other'), osns=osns)
        self.assertEqual((out['outcome'], out['reason']), ('refuse', 'entry'))

    def test_exceptions_give_entry(self):
        """TASK-066 AC5: an exception inside judge, from the lookup or from the file checks, gives "refuse", reason
        "entry", with the exception's type name in findings and never its message."""
        out, _ = run('s-1', PROJ, None, answer=RuntimeError('made-up message'))
        self.assertEqual((out['outcome'], out['reason'], out['findings']), ('refuse', 'entry', ['entry: RuntimeError']))
        osns = fake_os(dirs=[SUB])

        def boom(p):
            raise KeyError('made-up message')
        osns.lstat = boom
        out, _ = run(None, None, SUB, osns=osns)
        self.assertEqual((out['reason'], out['findings']), ('entry', ['entry: KeyError']))

    def test_equal_arguments_give_equal_results(self):
        """TASK-066 AC5: judge keeps no state; equal arguments over an unchanged disk give equal results."""
        osns = fake_os(stores=[writer.store_path(PROJ)], dirs=[SUB])
        first = [run(*a, osns=osns)[0] for a in (('s-1', PROJ, None), (None, None, SUB), ('s-1', None, None))]
        second = [run(*a, osns=osns)[0] for a in (('s-1', PROJ, None), (None, None, SUB), ('s-1', None, None))]
        self.assertEqual(first, second)
        for out in first:
            self.assertEqual(set(out), KEYS)


def tree():
    return ast.parse(SOURCE.read_bytes().decode('utf-8'))


class R5WhatTheModuleDoes(unittest.TestCase):

    def test_imports(self):
        """TASK-066 AC6: claude_code_store imports exactly os and, of aieos_bootstrap, writer."""
        imports = set()
        for n in ast.walk(tree()):
            if isinstance(n, ast.Import):
                imports.update(('import', a.name) for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                imports.update((n.module, a.name) for a in n.names)
        self.assertEqual(imports, {('import', 'os'), ('aieos_bootstrap', 'writer')})

    def test_only_two_writer_functions_are_called(self):
        """TASK-066 AC6: the only names of writer it calls are store_path and session_lease; it also names
        StoreResult, to check the answer's type."""
        called, named = set(), set()
        for n in ast.walk(tree()):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == 'writer':
                named.add(n.attr)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) \
                    and n.func.value.id == 'writer':
                called.add(n.func.attr)
        self.assertEqual(called, {'store_path', 'session_lease'})
        self.assertEqual(named, {'store_path', 'session_lease', 'StoreResult'})

    def test_absent_names_and_calls(self):
        """TASK-066 AC6: no open, process, standard input, environment, print, exit, clock, network or model call; no
        exec, eval, compile, __import__ or importlib; no assert; no string naming the project-state directory; the
        regular-file test reads st_mode's kind bits."""
        t = tree()
        names = {n.id for n in ast.walk(t) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(t) if isinstance(n, ast.Attribute)}
        self.assertFalse(names & {'open', 'print', 'exec', 'eval', 'compile', '__import__', 'importlib', 'input',
                                  'exit', 'sys', 'subprocess', 'socket', 'time', 'datetime', 'stat'})
        self.assertFalse(attrs & {'open', 'environ', 'getenv', 'stdin', 'system', 'popen', 'exit', 'now', 'utcnow',
                                  'time', 'monotonic', 'today', 'urlopen', 'connect', 'S_ISREG'})
        self.assertFalse([n for n in ast.walk(t) if isinstance(n, ast.Assert)])
        self.assertFalse([n for n in ast.walk(t) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                          and '.aieos' in n.value])
        text = SOURCE.read_bytes().decode('utf-8')
        self.assertIn('0o170000', text)
        self.assertIn('0o100000', text)
        self.assertIn('st_mode', text)


class R6WhatIsStated(unittest.TestCase):

    def test_the_docstring_states_the_rules_and_limits(self):
        """TASK-066 AC7: the module docstring states the outcomes and their sources, the values rule, the upward
        search and its limits, read-only and the lock, the arguments' source and the fail-open direction of now, and
        that no hook is placed and nothing is measured (whitespace collapsed)."""
        doc = ' '.join(ast.get_docstring(tree()).split())
        for words in ('specification 5 section 11 point 7', '"tied" (bullet 3)', '"enforce_nothing" (bullet 5)',
                      '"refuse" (bullet 6, no record)', 'whitespace-only included', 'empty-as-absent rule is this module',
                      'the drive or share root', 'a fail-closed reading', 'inner project is judged alone',
                      'outside every project\'s folder tree is not judged', 'is a race',
                      'takes only a shared lock', 'refused without a record', 'hot journal', 'UNC',
                      'four tables', 'untested in CI on Linux', 'hard links and bind mounts', 'check and use apart',
                      'a later contract\'s', 'fail-open direction', 'process clock', 'No hook is placed',
                      'nothing is measured', 'CC-3', 'C6'):
            with self.subTest(words=words):
                self.assertIn(words, doc)


if __name__ == '__main__':
    unittest.main()

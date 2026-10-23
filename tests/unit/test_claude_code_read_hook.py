"""Unit tests of aieos_bootstrap.claude_code_read_hook (TASK-068 AC1 to AC3, AC5, AC6 and AC7's word checks; AC9 rules
R1 to R3, R5 to R7): run's arguments, flow and mappings with recording stand-ins for claude_code_store.judge,
claude_code_reads.read_paths and writer.add_reads; main with stand-ins for standard input, the working folder, the
clock and run; the in-suite checks of the hook-side modules' imports and calls, and of the docstrings' words. No test
writes a file, makes a folder or opens a store; sources are read by pathlib's read_bytes relative to this file."""

import ast
import collections.abc
import datetime
import io
import json
import os
import pathlib
import sys
import types
import unittest
from unittest import mock

from aieos_bootstrap import claude_code_read_hook as hook
from aieos_bootstrap import claude_code_reads, claude_code_store, writer

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
TOP = os.path.abspath(os.sep)
ENV_ROOT = os.path.join(TOP, 'made-up-env-root')
JUDGED_ROOT = os.path.join(TOP, 'made-up-judged-root')
FOLDER = os.path.join(TOP, 'made-up-folder')
LEASE = {'task_id': 'TASK-001', 'fencing_token': {'epoch': 'e', 'counter': 1},
         'expires_at': T0 + datetime.timedelta(hours=1)}
INPUT = json.dumps({'session_id': 'made-up-input-session', 'cwd': os.path.join(TOP, 'made-up-input-cwd'),
                    'tool_name': 'Read', 'tool_input': {'file_path': 'made-up/a.txt'}}).encode('utf-8')
ENV = {hook.SESSION_VAR: 'made-up-env-session', hook.ROOT_VAR: ENV_ROOT}
KEYS = {'exit_code', 'outcome', 'reason', 'findings'}
SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap'
HOOK_SIDE = ('claude_code.py', 'claude_code_hook.py', 'claude_code_channel.py', 'claude_code_reads.py',
             'claude_code_store.py', 'claude_code_read_hook.py', 'claude_code_pretool_hook.py',
             'claude_code_shell_allow.py')
OWN_IMPORTS = {'claude_code.py': {'governor', 'records'}, 'claude_code_hook.py': {'claude_code'},
               'claude_code_channel.py': {'adapter', 'claude_code', 'claude_code_hook'}, 'claude_code_reads.py': set(),
               'claude_code_store.py': {'writer'},
               'claude_code_read_hook.py': {'claude_code_reads', 'claude_code_store', 'writer'},
               'claude_code_pretool_hook.py': {'claude_code', 'claude_code_store', 'claude_code_hook',
                                               'claude_code_channel', 'task_contract', 'session_violation',
                                               'claude_code_shell_allow'},
               'claude_code_shell_allow.py': {'claude_code_hook', 'gitread'}}
ALLOWED = {('claude_code_store.py', 'writer'): {'store_path', 'session_lease', 'StoreResult'},
           ('claude_code_read_hook.py', 'writer'): {'add_reads', 'StoreResult'}}
THE_PAIR = ('claude_code_channel.py', 'adapter', 'violation')
SECRETS = ('made-up', 'TASK-001', ENV_ROOT, JUDGED_ROOT, FOLDER)
DEFAULT = object()


def tied(root=JUDGED_ROOT, lease=LEASE, reason='tied'):
    return {'outcome': 'tied', 'reason': reason, 'findings': [], 'root': root, 'lease': lease}


def judged(outcome, reason, findings=(), root=None):
    return {'outcome': outcome, 'reason': reason, 'findings': list(findings), 'root': root, 'lease': None}


def read(paths=('made-up/a.txt',), result='read'):
    return {'result': result, 'reason': result, 'findings': [], 'read_paths': list(paths)}


class RecordingEnv(collections.abc.Mapping):
    """A Mapping whose only allowed read is get of the two names; every other access raises."""

    def __init__(self, values, raising=()):
        self.values, self.raising, self.gets = dict(values), set(raising), []

    def get(self, key, default=None):
        if key not in (hook.SESSION_VAR, hook.ROOT_VAR):
            raise AssertionError('another name read: %r' % (key,))
        self.gets.append(key)
        if key in self.raising:
            raise LookupError('made-up')
        return self.values.get(key, default)

    def __getitem__(self, key):
        raise AssertionError('__getitem__')

    def __iter__(self):
        raise AssertionError('__iter__')

    def __len__(self):
        raise AssertionError('__len__')

    def __contains__(self, key):
        raise AssertionError('__contains__')


class Flow:
    """Recording stand-ins for the three functions run calls, in one ordered list of calls."""

    def __init__(self, judge=DEFAULT, paths=DEFAULT, store=DEFAULT):
        self.answers = {'judge': tied() if judge is DEFAULT else judge,
                        'read_paths': read() if paths is DEFAULT else paths,
                        'add_reads': writer.StoreResult('done', value=1) if store is DEFAULT else store}
        self.calls = []

    def make(self, name):
        def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            answer = self.answers[name]
            if isinstance(answer, BaseException):
                raise answer
            return answer
        return call

    def run(self, stdin_bytes=INPUT, environ=DEFAULT, working_folder=FOLDER, now=T0):
        with mock.patch.object(claude_code_store, 'judge', self.make('judge')), \
                mock.patch.object(claude_code_reads, 'read_paths', self.make('read_paths')), \
                mock.patch.object(writer, 'add_reads', self.make('add_reads')):
            return hook.run(stdin_bytes, RecordingEnv(ENV) if environ is DEFAULT else environ, working_folder, now)

    def names(self):
        return [c[0] for c in self.calls]


class RaisingTz(datetime.tzinfo):
    def utcoffset(self, dt):
        raise ValueError('made-up')

    def dst(self, dt):
        return None


class R1Arguments(unittest.TestCase):

    def test_bad_arguments_skip_with_argument(self):
        """TASK-068 AC1 and TASK-068 AC9: each argument of a wrong kind gives "skip", reason "argument", a fixed finding
        naming the argument, exit code 0, and no function called."""
        cases = [('stdin_bytes', dict(stdin_bytes=bytearray(INPUT))), ('stdin_bytes', dict(stdin_bytes=memoryview(INPUT))),
                 ('stdin_bytes', dict(stdin_bytes=INPUT.decode('utf-8'))), ('stdin_bytes', dict(stdin_bytes=None)),
                 ('environ', dict(environ=list(ENV.items()))), ('environ', dict(environ=None)),
                 ('working_folder', dict(working_folder=b'x')), ('working_folder', dict(working_folder=1)),
                 ('now', dict(now=T0.replace(tzinfo=None))), ('now', dict(now=T0.replace(microsecond=5))),
                 ('now', dict(now=T0.astimezone(datetime.timezone(datetime.timedelta(hours=7))))),
                 ('now', dict(now=T0.date())), ('now', dict(now=T0.timetz())), ('now', dict(now='2026-10-11'))]
        for name, kw in cases:
            with self.subTest(name=name, kw=kw):
                flow = Flow()
                out = flow.run(**kw)
                self.assertEqual(out, {'exit_code': 0, 'outcome': 'skip', 'reason': 'argument',
                                       'findings': ['argument: %s' % name]})
                self.assertEqual(flow.calls, [])

    def test_a_raising_tzinfo_is_an_argument(self):
        """TASK-068 AC1 and TASK-068 AC9: a now whose tzinfo raises gives "skip", "argument", with only the type name,
        by step (1)'s own try."""
        flow = Flow()
        out = flow.run(now=datetime.datetime(2026, 10, 11, 12, 0, 0, tzinfo=RaisingTz()))
        self.assertEqual((out['outcome'], out['reason'], out['findings']), ('skip', 'argument', ['argument: ValueError']))
        self.assertEqual(flow.calls, [])

    def test_the_keys_and_equal_results(self):
        """TASK-068 AC1 and TASK-068 AC9: the result has exactly the four keys and exit code 0; equal arguments give
        equal results; a working folder of None is accepted."""
        first = Flow().run()
        self.assertEqual(set(first), KEYS)
        self.assertEqual(first, Flow().run())
        self.assertEqual(Flow().run(working_folder=None)['outcome'], 'recorded')
        self.assertEqual(first, {'exit_code': 0, 'outcome': 'recorded', 'reason': None, 'findings': []})


class R2Flow(unittest.TestCase):

    def test_the_order_and_the_exact_arguments(self):
        """TASK-068 AC2 and TASK-068 AC9: judge, then read_paths, then add_reads; judge gets the environment's two
        values unchanged, the working folder and now; read_paths gets the input bytes; add_reads gets judge's root
        (not the environment's), the environment's session id (not the input's), the paths and the same now; only
        the two names are read, each once, through get."""
        env = RecordingEnv(ENV)
        flow = Flow()
        out = flow.run(environ=env)
        self.assertEqual(out['outcome'], 'recorded')
        self.assertEqual(flow.calls, [
            ('judge', ('made-up-env-session', ENV_ROOT, FOLDER, T0), {}),
            ('read_paths', (INPUT,), {}),
            ('add_reads', (JUDGED_ROOT, 'made-up-env-session', ['made-up/a.txt'], T0), {})])
        self.assertEqual(sorted(env.gets), sorted([hook.SESSION_VAR, hook.ROOT_VAR]))

    def test_absent_and_empty_values_pass_unchanged(self):
        """TASK-068 AC2 and TASK-068 AC9: an absent name gives None and an empty one "", passed to judge as they are."""
        for values, expect in (({}, (None, None)), ({hook.SESSION_VAR: '', hook.ROOT_VAR: ''}, ('', '')),
                               ({hook.SESSION_VAR: 's', hook.ROOT_VAR: ''}, ('s', ''))):
            with self.subTest(values=values):
                flow = Flow(judge=judged('enforce_nothing', 'no_store_found'))
                flow.run(environ=RecordingEnv(values))
                self.assertEqual(flow.calls[0][1][:2], expect)

    def test_judges_answers(self):
        """TASK-068 AC2 and TASK-068 AC9: judge's answers in the header's order; no later function is called after
        an ending; "refuse" copies judge's findings, its reason as findings[0]'s prefix; every other shape gives the
        fixed ["entry: judge"]."""
        refuse = judged('refuse', 'session', ['session: no session with this id'])
        cases = [(judged('enforce_nothing', 'no_lease_row'), ('skip', 'enforce_nothing', [])),
                 (refuse, ('skip', 'refuse', ['session: no session with this id']))]
        entry = ('skip', 'entry', ['entry: judge'])
        odd = [None, [], 'tied', dict(tied(), extra=1), {k: v for k, v in tied().items() if k != 'lease'},
               dict(tied(), findings=('x',)), dict(tied(), findings=[1]), dict(refuse, reason=None),
               dict(refuse, reason=1), tied(root=''), tied(root=None), tied(root=1), tied(lease=None),
               tied(lease=[1]), tied(reason='done'), dict(tied(), outcome='other')]
        cases += [(answer, entry) for answer in odd]
        for answer, expect in cases:
            with self.subTest(answer=answer):
                flow = Flow(judge=answer)
                out = flow.run()
                self.assertEqual((out['outcome'], out['reason'], out['findings']), expect)
                self.assertEqual(flow.names(), ['judge'])
        for sid in ('', None, 1):
            with self.subTest(sid=sid):
                flow = Flow()
                out = flow.run(environ=RecordingEnv({hook.SESSION_VAR: sid, hook.ROOT_VAR: ENV_ROOT}))
                self.assertEqual((out['outcome'], out['reason'], out['findings']), entry)
                self.assertEqual(flow.names(), ['judge'])
        flow = Flow(judge=refuse)
        out = flow.run()
        self.assertTrue(out['findings'][0].startswith('session:'))
        self.assertIsNot(out['findings'], refuse['findings'])

    def test_read_paths_answers(self):
        """TASK-068 AC2 and TASK-068 AC9: "uncovered" gives "skip", findings [] (its finding not copied); any other
        shape, an empty list or a non-str item gives the fixed ["entry: read_paths"]; add_reads is not called."""
        uncovered = {'result': 'uncovered', 'reason': 'tool', 'findings': ['a search tool made-up'], 'read_paths': []}
        cases = [(uncovered, ('skip', 'uncovered', []))]
        entry = ('skip', 'entry', ['entry: read_paths'])
        for answer in (None, [], dict(read(), extra=1), {'result': 'read'}, read(paths=()), read(paths=[1]),
                       dict(read(), read_paths=('made-up/a.txt',)), read(result='other')):
            cases.append((answer, entry))
        for answer, expect in cases:
            with self.subTest(answer=answer):
                flow = Flow(paths=answer)
                out = flow.run()
                self.assertEqual((out['outcome'], out['reason'], out['findings']), expect)
                self.assertEqual(flow.names(), ['judge', 'read_paths'])

    def test_add_reads_answers(self):
        """TASK-068 AC2 and TASK-068 AC9: "done" gives "recorded"; each refusal reason of the writer is passed through
        as "lost" with its findings as a list; a non-str finding or reason, or an answer that is not a StoreResult,
        gives "lost" with the fixed ["entry: add_reads"]."""
        for reason in ('argument', 'bound', 'path', 'root', 'no_store', 'link', 'unreadable', 'tables', 'no_lease_row',
                       'session', 'ended', 'leases'):
            with self.subTest(reason=reason):
                out = Flow(store=writer.StoreResult('refused', reason, ['%s: fixed words' % reason])).run()
                self.assertEqual(out, {'exit_code': 0, 'outcome': 'lost', 'reason': reason,
                                       'findings': ['%s: fixed words' % reason]})
                self.assertIsInstance(out['findings'], list)
                self.assertTrue(out['findings'][0].startswith(reason + ':'))
        entry = ('lost', 'entry', ['entry: add_reads'])
        for answer in (writer.StoreResult('refused', 'path', [1]), writer.StoreResult('refused', None, ['x']),
                       writer.StoreResult('maybe'), None, {'result': 'done'}):
            with self.subTest(answer=answer):
                out = Flow(store=answer).run()
                self.assertEqual((out['outcome'], out['reason'], out['findings']), entry)
        self.assertEqual(Flow(store=writer.StoreResult('done', value=0)).run()['outcome'], 'recorded')

    def test_exceptions(self):
        """TASK-068 AC2 and TASK-068 AC9: an exception from environ.get (each name), judge or read_paths gives "skip",
        and one from add_reads "lost", reason "entry", findings only the type name; nothing escapes."""
        for name in (hook.SESSION_VAR, hook.ROOT_VAR):
            with self.subTest(name=name):
                flow = Flow()
                out = flow.run(environ=RecordingEnv(ENV, raising=[name]))
                self.assertEqual(out, {'exit_code': 0, 'outcome': 'skip', 'reason': 'entry',
                                       'findings': ['entry: LookupError']})
                self.assertEqual(flow.calls, [])
        for where, outcome in (('judge', 'skip'), ('read_paths', 'skip'), ('add_reads', 'lost')):
            with self.subTest(where=where):
                flow = Flow(**{{'judge': 'judge', 'read_paths': 'paths', 'add_reads': 'store'}[where]:
                               RuntimeError('made-up message')})
                out = flow.run()
                self.assertEqual(out, {'exit_code': 0, 'outcome': outcome, 'reason': 'entry',
                                       'findings': ['entry: RuntimeError']})

    def test_no_input_text_in_findings(self):
        """TASK-068 AC2 and TASK-068 AC9: over every ending above, no text of the input, the environment or a
        stand-in's answer appears in a finding, but judge's and the writer's own fixed findings."""
        endings = [Flow(judge=judged('refuse', 'session', ['session: no session with this id'])).run(),
                   Flow(judge=[]).run(), Flow(paths=[]).run(),
                   Flow(paths={'result': 'uncovered', 'reason': 'tool', 'findings': ['made-up tool'],
                               'read_paths': []}).run(),
                   Flow(store=writer.StoreResult('refused', None, ['made-up'])).run(),
                   Flow(judge=RuntimeError('made-up')).run(), Flow().run(now=T0.replace(tzinfo=None))]
        for out in endings:
            for f in out['findings']:
                for s in SECRETS:
                    self.assertNotIn(s, f)


class R3Main(unittest.TestCase):

    def call_main(self, stdin=b'{}', cwd=None, clock=None, run=None):
        out, err, calls = io.StringIO(), io.StringIO(), []

        def getcwd():
            calls.append('getcwd')
            if isinstance(cwd, BaseException):
                raise cwd
            return FOLDER if cwd is None else cwd

        def raw_clock():
            calls.append('clock')
            if isinstance(clock, BaseException):
                raise clock
            return T0 if clock is None else clock

        def fake_run(*args):
            calls.append(('run', args))
            if isinstance(run, BaseException):
                raise run
            return {'exit_code': 0, 'outcome': 'skip', 'reason': 'argument', 'findings': []} if run is None else run

        stdin_ns = types.SimpleNamespace(buffer=types.SimpleNamespace(read=lambda: calls.append('stdin') or stdin))
        with mock.patch.object(sys, 'stdin', stdin_ns), mock.patch.object(sys, 'stdout', out), \
                mock.patch.object(sys, 'stderr', err), mock.patch.object(os, 'getcwd', getcwd), \
                mock.patch.object(hook, '_raw_clock', raw_clock), mock.patch.object(hook, 'run', fake_run):
            code = hook.main()
        return code, calls, out.getvalue() + err.getvalue()

    def test_the_order_and_the_arguments(self):
        """TASK-068 AC3 and TASK-068 AC9: standard input once, then the working folder once, then the clock once, then
        run once with them and os.environ itself (unread by main); the return value is run's exit code; nothing is
        printed."""
        code, calls, printed = self.call_main(stdin=INPUT)
        self.assertEqual(code, 0)
        self.assertEqual(calls[:3], ['stdin', 'getcwd', 'clock'])
        self.assertEqual(len(calls), 4)
        name, args = calls[3]
        self.assertEqual(name, 'run')
        self.assertEqual(args[0], INPUT)
        self.assertIs(args[1], os.environ)
        self.assertEqual(args[2:], (FOLDER, T0))
        self.assertEqual(printed, '')

    def test_getcwd_oserror_and_exceptions(self):
        """TASK-068 AC3 and TASK-068 AC9: os.getcwd() raising OSError gives working folder None; an exception from
        standard input, the clock or run, or another from getcwd, gives 0 and nothing printed."""
        code, calls, printed = self.call_main(cwd=FileNotFoundError('made-up'))
        self.assertEqual(calls[-1][1][2], None)
        self.assertEqual((code, printed), (0, ''))
        for kw in (dict(clock=RuntimeError('x')), dict(run=RuntimeError('x')), dict(cwd=KeyError('x')),
                   dict(run={'exit_code': 0})):
            with self.subTest(kw=kw):
                code, _, printed = self.call_main(**kw)
                self.assertEqual((code, printed), (0, ''))
        with mock.patch.object(sys, 'stdin', None), mock.patch.object(hook, 'run', lambda *a: 1 / 0):
            self.assertEqual(hook.main(), 0)

    def test_the_clock_is_rounded_up(self):
        """TASK-068 AC3 and TASK-068 AC9: _whole_second_now keeps a whole second and rounds any fraction up."""
        cases = [(datetime.datetime(2026, 10, 11, 12, 0, 0, 0, UTC), datetime.datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)),
                 (datetime.datetime(2026, 10, 11, 12, 0, 0, 1, UTC), datetime.datetime(2026, 10, 11, 12, 0, 1, tzinfo=UTC)),
                 (datetime.datetime(2026, 10, 11, 12, 0, 0, 999999, UTC),
                  datetime.datetime(2026, 10, 11, 12, 0, 1, tzinfo=UTC)),
                 (datetime.datetime(2026, 10, 11, 23, 59, 59, 500000, UTC),
                  datetime.datetime(2026, 10, 12, 0, 0, 0, tzinfo=UTC))]
        for raw, expect in cases:
            with self.subTest(raw=raw):
                with mock.patch.object(hook, '_raw_clock', lambda: raw):
                    self.assertEqual(hook._whole_second_now(), expect)

    def test_the_source_of_the_clock_and_the_main_line(self):
        """TASK-068 AC3 and TASK-068 AC9: _raw_clock calls datetime.datetime.now with datetime.timezone.utc; the line
        `if __name__ == '__main__': sys.exit(main())` is present (no test runs it as a process)."""
        text = (SRC / 'claude_code_read_hook.py').read_bytes().decode('utf-8')
        fn = [n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == '_raw_clock'][0]
        self.assertEqual(ast.unparse(fn.body[-1]), 'return datetime.datetime.now(datetime.timezone.utc)')
        self.assertIn("\nif __name__ == '__main__':\n    sys.exit(main())\n", text)


def separation_findings(path, text):
    """The separation check of the hook-side modules (TASK-068 AC5): every name bound to the writer or the adapter
    module is resolved (aliases too); a star import, a from-import of a name out of writer or adapter, an import of
    read_set_record, an aieos_bootstrap import not in the module's own list, any use of a writer or adapter name other
    than as an attribute's object, any attribute of them not allowed for the file, and any use of a bound
    aieos_bootstrap package name (a dotted chain) are refused."""
    name = os.path.basename(path)
    own = OWN_IMPORTS.get(name, set())
    tree = ast.parse(text)
    findings, bound, packages = [], {}, set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            mod = n.module or ''
            for a in n.names:
                if a.name == '*':
                    findings.append('star import from %s' % mod)
                elif mod == 'aieos_bootstrap':
                    if a.name == 'read_set_record' or a.name not in own:
                        findings.append('import of %s' % a.name)
                    bound[a.asname or a.name] = a.name
                elif mod.startswith('aieos_bootstrap.'):
                    findings.append('from-import of %s out of %s' % (a.name, mod))
        elif isinstance(n, ast.Import):
            for a in n.names:
                if a.name == 'aieos_bootstrap':
                    packages.add(a.asname or a.name)
                elif a.name.startswith('aieos_bootstrap.'):
                    sub = a.name.split('.', 1)[1]
                    if sub == 'read_set_record' or sub not in own:
                        findings.append('import of %s' % sub)
                    if a.asname:
                        bound[a.asname] = sub
                    else:
                        packages.add('aieos_bootstrap')
    parent = {}
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n):
            parent[id(c)] = n
    for n in ast.walk(tree):
        if not isinstance(n, ast.Name):
            continue
        if n.id in packages:
            findings.append('a dotted chain through %s' % n.id)
            continue
        mod = bound.get(n.id)
        if mod not in ('writer', 'adapter'):
            continue
        p = parent.get(id(n))
        if not (isinstance(p, ast.Attribute) and p.value is n):
            findings.append('%s used other than as an attribute\'s object' % mod)
            continue
        if (name, mod, p.attr) == THE_PAIR:
            continue
        if p.attr not in ALLOWED.get((name, mod), set()):
            findings.append('%s.%s' % (mod, p.attr))
    return findings


class R5WhatTheModulesDo(unittest.TestCase):

    def tree(self):
        return ast.parse((SRC / 'claude_code_read_hook.py').read_bytes().decode('utf-8'))

    def test_imports_and_calls(self):
        """TASK-068 AC5 and TASK-068 AC9: the new module imports exactly collections.abc, datetime, os, sys and, of
        aieos_bootstrap, claude_code_reads, claude_code_store and writer; it calls of writer only add_reads, of
        claude_code_store only judge, of claude_code_reads only read_paths."""
        t = self.tree()
        imports = set()
        for n in ast.walk(t):
            if isinstance(n, ast.Import):
                imports.update(('import', a.name) for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                imports.update((n.module, a.name) for a in n.names)
        self.assertEqual(imports, {('import', 'collections.abc'), ('import', 'datetime'), ('import', 'os'),
                                   ('import', 'sys'), ('aieos_bootstrap', 'claude_code_reads'),
                                   ('aieos_bootstrap', 'claude_code_store'), ('aieos_bootstrap', 'writer')})
        called = {}
        for n in ast.walk(t):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name):
                called.setdefault(n.func.value.id, set()).add(n.func.attr)
        self.assertEqual(called['writer'], {'add_reads'})
        self.assertEqual(called['claude_code_store'], {'judge'})
        self.assertEqual(called['claude_code_reads'], {'read_paths'})

    def test_os_sys_and_absent_names(self):
        """TASK-068 AC5 and TASK-068 AC9: of os only getcwd and environ, of sys only stdin and exit; os.environ only as
        an argument of main's call of run; no getenv, putenv or argv, no .environ.get; no file opened, no process, no
        exec, eval, compile, __import__, importlib or assert; no string naming the project-state directory."""
        t = self.tree()
        attrs = {}
        for n in ast.walk(t):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
                attrs.setdefault(n.value.id, set()).add(n.attr)
        self.assertEqual(attrs['os'], {'getcwd', 'environ'})
        self.assertEqual(attrs['sys'], {'stdin', 'exit'})
        main = [n for n in t.body if isinstance(n, ast.FunctionDef) and n.name == 'main'][0]
        uses = [n for n in ast.walk(t) if isinstance(n, ast.Attribute) and n.attr == 'environ']
        runs = [n for n in ast.walk(main) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == 'run']
        self.assertEqual(len(uses), 1)
        self.assertEqual(len(runs), 1)
        self.assertIn(uses[0], runs[0].args)
        names = {n.id for n in ast.walk(t) if isinstance(n, ast.Name)}
        all_attrs = {n.attr for n in ast.walk(t) if isinstance(n, ast.Attribute)}
        self.assertFalse((names | all_attrs) & {'getenv', 'putenv', 'argv', 'open', 'print', 'exec', 'eval',
                                                'compile', '__import__', 'importlib', 'subprocess', 'socket',
                                                'popen', 'system', 'spawn', 'urlopen', 'connect', 'sqlite3'})
        self.assertFalse([n for n in ast.walk(t) if isinstance(n, ast.Attribute) and n.attr == 'get'
                          and isinstance(n.value, ast.Attribute) and n.value.attr == 'environ'])
        self.assertFalse([n for n in ast.walk(t) if isinstance(n, ast.Assert)])
        for name in ('claude_code_read_hook.py', 'claude_code_store.py'):
            with self.subTest(name=name):
                consts = [n.value for n in ast.walk(ast.parse((SRC / name).read_bytes().decode('utf-8')))
                          if isinstance(n, ast.Constant) and isinstance(n.value, str)]
                self.assertFalse([c for c in consts if '.aieos' in c])

    def test_the_separation_holds_on_the_six_modules(self):
        """TASK-068 AC5 and TASK-068 AC9: the separation check gives no finding on the hook-side modules. TASK-076 AC7:
        eight of them, claude_code_shell_allow among them with its own imports."""
        self.assertEqual(len(HOOK_SIDE), 8)
        for name in HOOK_SIDE:
            with self.subTest(name=name):
                self.assertEqual(separation_findings(name, (SRC / name).read_bytes().decode('utf-8')), [])

    def test_the_separation_finds_hostile_samples(self):
        """TASK-068 AC5 and TASK-068 AC9: hostile samples are each found: writer.remove_reads in the channel's name;
        adapter.violation in another hook-side name; an alias of writer; a star import; an import of read_set_record;
        a dotted chain; getattr on writer; a later writer function; the pair allowed only as that exact pair."""
        samples = [
            ('claude_code_channel.py', 'from aieos_bootstrap import adapter, claude_code, claude_code_hook\n'
                                       'from aieos_bootstrap import writer\nwriter.remove_reads()\n'),
            ('claude_code_hook.py', 'from aieos_bootstrap import claude_code\nfrom aieos_bootstrap import adapter\n'
                                    'adapter.violation()\n'),
            ('claude_code_store.py', 'import aieos_bootstrap.writer as w\nw.append_event()\n'),
            ('claude_code_store.py', 'from aieos_bootstrap.writer import *\n'),
            ('claude_code_read_hook.py', 'from aieos_bootstrap import read_set_record\nread_set_record.observe()\n'),
            ('claude_code_store.py', 'import aieos_bootstrap.writer\naieos_bootstrap.writer.remove_reads()\n'),
            ('claude_code_store.py', 'from aieos_bootstrap import writer\ngetattr(writer, "remove_reads")()\n'),
            ('claude_code_read_hook.py', 'from aieos_bootstrap import writer\nwriter.read_log()\n'),
            ('claude_code_channel.py', 'from aieos_bootstrap import adapter\nadapter.submit()\n'),
            ('claude_code_store.py', 'from aieos_bootstrap.writer import session_lease\n'),
        ]
        for name, text in samples:
            with self.subTest(name=name, text=text):
                self.assertTrue(separation_findings(name, text))

    def test_the_pair_is_exact_apart_from_the_import_rule(self):
        """TASK-068 AC5 and TASK-068 AC9: the allowed pair is exact apart from the import rule: adapter.violation under
        another hook-side name gives the attribute finding itself, not only the import finding; under the channel's
        name, with the channel's own imports, it gives none."""
        text = 'from aieos_bootstrap import claude_code\nfrom aieos_bootstrap import adapter\nadapter.violation()\n'
        self.assertIn('adapter.violation', separation_findings('claude_code_hook.py', text))
        channel = 'from aieos_bootstrap import adapter, claude_code, claude_code_hook\nadapter.violation()\n'
        self.assertEqual(separation_findings('claude_code_channel.py', channel), [])


class R6WhatIsStated(unittest.TestCase):

    def test_the_docstring_states_the_rules_and_limits(self):
        """TASK-068 AC6 and TASK-068 AC9: the new module's docstring states its use, flow, names, folder, input,
        clock, silence and limits (whitespace collapsed)."""
        doc = ' '.join(ast.get_docstring(ast.parse((SRC / 'claude_code_read_hook.py').read_bytes().decode('utf-8'))).split())
        for words in ('PostToolUse', 'nothing wires this program into Claude Code', 'AIEOS_SESSION_ID', 'AIEOS_ROOT',
                      'the empty-or-absent rule is judge\'s', 'the process\'s own working folder',
                      'no key of the hook input is read but through read_paths', 'writes no record',
                      'rounded up to the next whole second', 'now is fixed before the lookups', 'exit code 0',
                      'prints nothing', 'a read may be lost silently', '0 at the bound', 'hot journal',
                      'a failed COMMIT may have applied', 'read_set_record.observe is core-side',
                      'outside every project\'s folder tree is not judged', 'an inner project\'s store judges alone',
                      'a removed or emptied store', 'outside the launcher', 'project-state directory'):
            with self.subTest(words=words):
                self.assertIn(words, doc)


class R7StoreWords(unittest.TestCase):

    def test_the_store_docstring_states_deferred_points(self):
        """TASK-068 AC7 and TASK-068 AC9: claude_code_store's module docstring states the lexical search (a), the now
        finding (b), the mapping's guard (c) and the two checks of now (e) (whitespace collapsed)."""
        doc = ' '.join(ast.get_docstring(ast.parse((SRC / 'claude_code_store.py').read_bytes().decode('utf-8'))).split())
        for words in ('lexical parents', 'argument: now (', 'only when the lookup was made with a session id',
                      'the two checks of now differ and both fail closed'):
            with self.subTest(words=words):
                self.assertIn(words, doc)


class MadeUpBytes(bytes):
    """A made-up subclass of bytes (TASK-073 AC5)."""


class MadeUpStr(str):
    """A made-up subclass of str (TASK-073 AC5)."""


BAD_ARGUMENTS = [dict(stdin_bytes=bytearray(INPUT)), dict(stdin_bytes=memoryview(INPUT)),
                 dict(stdin_bytes=INPUT.decode('utf-8')), dict(stdin_bytes=None), dict(environ=list(ENV.items())),
                 dict(environ=None), dict(working_folder=b'x'), dict(working_folder=1),
                 dict(now=T0.replace(tzinfo=None)), dict(now=T0.replace(microsecond=5)),
                 dict(now=T0.astimezone(datetime.timezone(datetime.timedelta(hours=7)))), dict(now=T0.date()),
                 dict(now=T0.timetz()), dict(now='2026-10-11')]


def collapsed_docstrings():
    """The read hook's module docstring and run's and main's, each with its whitespace collapsed (TASK-073 AC2 and
    TASK-073 AC3)."""
    tree = ast.parse((SRC / 'claude_code_read_hook.py').read_bytes().decode('utf-8'))
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    return tuple(' '.join(ast.get_docstring(node).split()) for node in (tree, functions['run'], functions['main']))


class T73SaidNoMore(unittest.TestCase):

    def test_the_new_sentences_of_p1_p2_and_p3(self):
        """TASK-073 AC2: the module docstring holds the new phrases of P1, P2 and P3, run's and main's docstrings each
        hold "never raises an exception inheriting Exception", and none of the three holds a replaced phrase
        (whitespace collapsed)."""
        module, run_doc, main_doc = collapsed_docstrings()
        for words in ("a kill after add_reads' COMMIT may have stored the read",
                      'a BaseException that is not an Exception', '(as documented, unmeasured',
                      'An error inheriting Exception while reading'):
            with self.subTest(words=words):
                self.assertIn(words, module)
        for name, doc in (('run', run_doc), ('main', main_doc)):
            with self.subTest(name=name):
                self.assertIn('never raises an exception inheriting Exception', doc)
        for words in ('timeout stores nothing', 'never raises.', 'An error while reading'):
            for name, doc in (('module', module), ('run', run_doc), ('main', main_doc)):
                with self.subTest(words=words, name=name):
                    self.assertNotIn(words, doc)


class T73Wording(unittest.TestCase):

    def test_the_new_wording_of_p5_p6_and_result_keys(self):
        """TASK-073 AC3: the module docstring holds "kept (decision D-1484 C2)", "specification 5 section 7 and
        section 11 point 7" and "RESULT_KEYS, the four keys of run's result", and neither "kept because" nor "line
        108" (whitespace collapsed); RESULT_KEYS is exactly the four keys in their order."""
        module = collapsed_docstrings()[0]
        for words in ('kept (decision D-1484 C2)', 'specification 5 section 7 and section 11 point 7',
                      "RESULT_KEYS, the four keys of run's result"):
            with self.subTest(words=words):
                self.assertIn(words, module)
        for words in ('kept because', 'line 108'):
            with self.subTest(words=words):
                self.assertNotIn(words, module)
        self.assertEqual(hook.RESULT_KEYS, ('exit_code', 'outcome', 'reason', 'findings'))

    def test_every_result_has_the_result_keys(self):
        """TASK-073 AC3: over the 14 bad-argument cases, and over judge's answers "enforce_nothing", "refuse" and
        "tied" with read_paths' "uncovered" and "read" and add_reads' "done", "refused" and an exception, each result's
        key set is set(hook.RESULT_KEYS)."""
        self.assertEqual(len(BAD_ARGUMENTS), 14)
        results = [Flow().run(**kw) for kw in BAD_ARGUMENTS]
        judges = (judged('enforce_nothing', 'no_lease_row'),
                  judged('refuse', 'session', ['session: no session with this id']), tied())
        reads = ({'result': 'uncovered', 'reason': 'tool', 'findings': ['made-up tool'], 'read_paths': []}, read())
        stores = (writer.StoreResult('done', value=1), writer.StoreResult('refused', 'leases', ['leases: x']),
                  RuntimeError('made-up'))
        for j in judges:
            for r in reads:
                for s in stores:
                    results.append(Flow(judge=j, paths=r, store=s).run())
        self.assertEqual(len(results), 14 + 18)
        self.assertEqual({out['outcome'] for out in results}, {'skip', 'recorded', 'lost'})
        for out in results:
            with self.subTest(out=out):
                self.assertEqual(set(out), set(hook.RESULT_KEYS))


class T73Subclasses(unittest.TestCase):

    def test_a_bytes_subclass_is_an_argument(self):
        """TASK-073 AC5: stdin_bytes of a made-up subclass of bytes gives exit 0, "skip", reason "argument", findings
        ["argument: stdin_bytes"], and no stand-in is called."""
        flow = Flow()
        out = flow.run(stdin_bytes=MadeUpBytes(INPUT))
        self.assertEqual(out, {'exit_code': 0, 'outcome': 'skip', 'reason': 'argument',
                               'findings': ['argument: stdin_bytes']})
        self.assertEqual(flow.calls, [])

    def test_a_str_subclass_session_id_reaches_add_reads(self):
        """TASK-073 AC5: the read hook itself does not refuse a session id of a made-up subclass of str: with a
        recording stand-in judge answering "tied" it reaches add_reads, passed unchanged; with the real
        writer.add_reads and a made-up root, add_reads' exact-type check refuses it before any root is used: exit 0,
        "lost", reason "argument", findings[0] starting "argument:"."""
        sid = MadeUpStr('made-up-env-session')
        env = {hook.SESSION_VAR: sid, hook.ROOT_VAR: ENV_ROOT}
        flow = Flow()
        out = flow.run(environ=RecordingEnv(env))
        self.assertEqual(flow.names(), ['judge', 'read_paths', 'add_reads'])
        self.assertIs(flow.calls[2][1][1], sid)
        self.assertEqual(out['outcome'], 'recorded')
        real, seen = writer.add_reads, []

        def forward(*args):
            seen.append(args)
            return real(*args)
        flow = Flow()
        with mock.patch.object(claude_code_store, 'judge', flow.make('judge')), \
                mock.patch.object(claude_code_reads, 'read_paths', flow.make('read_paths')), \
                mock.patch.object(writer, 'add_reads', forward):
            out = hook.run(INPUT, RecordingEnv(env), FOLDER, T0)
        self.assertEqual(flow.names(), ['judge', 'read_paths'])
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][0], JUDGED_ROOT)
        self.assertIs(seen[0][1], sid)
        self.assertEqual((out['exit_code'], out['outcome'], out['reason']), (0, 'lost', 'argument'))
        self.assertTrue(out['findings'][0].startswith('argument:'))


class T73TheTypeErrorPath(unittest.TestCase):

    def test_findings_that_are_not_iterable_end_in_step_6(self):
        """TASK-073 AC7: add_reads' stand-in answering a writer.StoreResult('refused', 'path', ['path: x']) whose
        findings attribute is then set to None gives exit 0, "lost", reason "entry", findings ["entry: TypeError"]
        (step 6), not step 5's ["entry: add_reads"]; pinned as the code is."""
        answer = writer.StoreResult('refused', 'path', ['path: x'])
        answer.findings = None
        flow = Flow(store=answer)
        out = flow.run()
        self.assertEqual(flow.names(), ['judge', 'read_paths', 'add_reads'])
        self.assertEqual(out, {'exit_code': 0, 'outcome': 'lost', 'reason': 'entry', 'findings': ['entry: TypeError']})


if __name__ == '__main__':
    unittest.main()

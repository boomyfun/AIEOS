"""Unit tests of aieos_bootstrap.cli (task TASK-091): the parser, the command tasks over execution.list_tasks, never
raising, in_runtime and RUNTIME_VARS, the module's form and its docstrings. execution.list_tasks is replaced by a
stand-in through mock.patch.object, restored after each test; stdout is a list sink; the clock is a fixed or counting
stand-in; no test writes a file or runs Git, and only test_clock_form reads the system clock (through cli._clock);
the root is a literal Windows path that names no folder."""

import ast
import datetime
import pathlib
import unittest
from collections import OrderedDict
from unittest import mock

from aieos_bootstrap import claude_code_pretool_hook, cli, execution, mcp_server

HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / 'src' / 'aieos_bootstrap'
ROOT = 'C:/cli-root-91'
NOW = datetime.datetime(2026, 10, 25, 12, 0, 0, tzinfo=datetime.timezone.utc)
H1 = '1' * 64
H2 = '2' * 64


def item(task, state, contract_hash, lease):
    return {'task': task, 'state': state, 'contract_hash': contract_hash, 'lease': lease}


TWO = [item('TASK-1', 'READY', H1, 'none'), item('TASK-2', 'REWORK', H2, 'expired')]


class Sink:
    def __init__(self, raise_write=False, raise_flush=False, with_flush=True):
        self.writes = []
        self.flushes = 0
        self.raise_write = raise_write
        self.raise_flush = raise_flush
        if with_flush:
            self.flush = self._flush

    def write(self, text):
        if self.raise_write:
            raise OSError('write')
        self.writes.append(text)

    def _flush(self):
        self.flushes += 1
        if self.raise_flush:
            raise OSError('flush')


class AllRaise:
    def __getattr__(self, name):
        raise OSError(name)


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
    def __init__(self, answer=(TWO, None), raises=None):
        self.calls = []
        self.answer = answer
        self.raises = raises

    def __call__(self, root, now):
        self.calls.append((root, now))
        if self.raises is not None:
            raise self.raises
        return self.answer


def run(argv, answer=(TWO, None), raises=None, sink=None, clock=None, environ=None):
    sink = Sink() if sink is None else sink
    clock = Clock() if clock is None else clock
    stand = Stand(answer, raises)
    with mock.patch.object(execution, 'list_tasks', stand):
        rc = cli.main(argv, sink, {} if environ is None else environ, clock)
    out = ''.join(sink.writes) if isinstance(sink, Sink) else ''
    return rc, out, stand, clock, sink


def tasks(*flags):
    return ['tasks', '--root', ROOT] + list(flags)


class SubList(list):
    pass


BAD_ARGVS = [
    [], ('tasks', '--root', ROOT), SubList(['tasks', '--root', ROOT]), ['tasks', '--root', ROOT, 3],
    ['task', '--root', ROOT], ['Tasks', '--root', ROOT], ['end', '--root', ROOT], ['--'], ['-h'], ['--help'],
    ['--root', ROOT, 'tasks'], ['--json', 'tasks', '--root', ROOT], ['tasks'], ['tasks', '--root'],
    ['tasks', '--root', '--json'], ['tasks', '--root', '--x'], ['tasks', '--root', ''], tasks('--all'), tasks('-r'),
    ['tasks', '--root=' + ROOT], tasks('--root', ROOT), tasks('--json', '--json'), tasks('extra'),
]
GOOD_ARGVS = [
    (tasks(), ROOT), (['tasks', '--json', '--root', ROOT], ROOT), (tasks('--json'), ROOT),
    (['tasks', '--root', '-r'], '-r'), (['tasks', '--root', '   '], '   '),
]


class TASK091AC1Parser(unittest.TestCase):
    def test_usage_errors(self):
        """TASK-091 AC1: each argv out of form gives exit 2 and exactly USAGE, neither the clock nor list_tasks
        called."""
        for argv in BAD_ARGVS:
            rc, out, stand, clock, _ = run(argv)
            self.assertEqual((type(rc), rc, out), (int, 2, cli.USAGE), argv)
            self.assertEqual((stand.calls, clock.calls), ([], 0), argv)

    def test_accepted_forms(self):
        """TASK-091 AC1: the accepted forms reach the stand-in once with their root and give an exit code other
        than 2."""
        for argv, root in GOOD_ARGVS:
            rc, _, stand, _, _ = run(argv)
            self.assertNotEqual(rc, 2, argv)
            self.assertEqual(stand.calls, [(root, NOW)], argv)

    def test_usage_text(self):
        """TASK-091 AC1 and TASK-091 AC6: USAGE ends with LF and names tasks, --root and --json."""
        self.assertTrue(cli.USAGE.endswith('\n'))
        for word in ('tasks', '--root', '--json'):
            self.assertIn(word, cli.USAGE)


class TASK091AC2Tasks(unittest.TestCase):
    def test_two_items(self):
        """TASK-091 AC2: a list of two items gives exit 0 and exactly the two lines, in order, each ending with LF;
        list_tasks is called once with the root and the clock's value, the clock once."""
        rc, out, stand, clock, _ = run(tasks())
        self.assertEqual(rc, 0)
        self.assertEqual(out, 'TASK-1 READY %s lease=none\nTASK-2 REWORK %s lease=expired\n' % (H1, H2))
        self.assertEqual((stand.calls, clock.calls), ([(ROOT, NOW)], 1))

    def test_empty_list(self):
        """TASK-091 AC2: an empty list gives exit 0 and the one line "no task may be taken"."""
        rc, out, _, _, _ = run(tasks(), answer=([], None))
        self.assertEqual((rc, out), (0, 'no task may be taken\n'))

    def test_findings(self):
        """TASK-091 AC2: findings give exit 1 and one line each, non-str items left out, a tuple taken as a list."""
        for found, lines in ((['a', 'b'], 'finding: a\nfinding: b\n'), (['a', 3, 'b'], 'finding: a\nfinding: b\n'),
                             (('c',), 'finding: c\n')):
            rc, out, _, _, _ = run(tasks(), answer=(None, found))
            self.assertEqual((rc, out), (1, lines), found)

    def test_no_finding_left(self):
        """TASK-091 AC2: findings given as a str, [], (), [3], None, 5 or {} give exit 1 and the one line "finding:
        tasks: list_tasks gave no finding"."""
        for found in ('abc', [], (), [3], None, 5, {}):
            rc, out, _, _, _ = run(tasks(), answer=(None, found))
            self.assertEqual((rc, out), (1, 'finding: tasks: list_tasks gave no finding\n'), found)

    def test_json_list_exact(self):
        """TASK-091 AC2: with --json the list gives one line, json.dumps with sort_keys, compared as an exact
        string (the stand-in's items are in list_tasks' key order, so a missing sort_keys changes the line)."""
        rc, out, _, _, _ = run(tasks('--json'))
        want = ('{"tasks": [{"contract_hash": "%s", "lease": "none", "state": "READY", "task": "TASK-1"}, '
                '{"contract_hash": "%s", "lease": "expired", "state": "REWORK", "task": "TASK-2"}]}\n' % (H1, H2))
        self.assertEqual((rc, out), (0, want))

    def test_json_findings(self):
        """TASK-091 AC2: with --json, findings and the CLI's own findings give one line, json.dumps with
        sort_keys."""
        rc, out, _, _, _ = run(tasks('--json'), answer=(None, ['a', 'b']))
        self.assertEqual((rc, out), (1, '{"findings": ["a", "b"]}\n'))
        rc, out, _, _, _ = run(tasks('--json'), answer=(None, 'x'))
        self.assertEqual((rc, out), (1, '{"findings": ["tasks: list_tasks gave no finding"]}\n'))

    def test_answers_out_of_form(self):
        """TASK-091 AC2: an answer that is not a 2-tuple of (a list, None) or (None, any value), and an item out of
        form, give exit 1 and the out-of-form finding, in both forms."""
        bad_item = item('TASK-1', 'READY', H1, 'none')
        answers = [
            None, 5, 'x', [TWO, None], (TWO,), (TWO, None, None), (TWO, ['f']), (5, None), ('x', None),
            ([dict(bad_item, extra='x')], None), ([{'task': 'TASK-1', 'state': 'READY', 'lease': 'none'}], None),
            ([dict(bad_item, lease=3)], None), ([OrderedDict(bad_item)], None), (['TASK-1'], None),
        ]
        for answer in answers:
            rc, out, _, _, _ = run(tasks(), answer=answer)
            self.assertEqual((rc, out), (1, 'finding: tasks: list_tasks gave an answer out of form\n'), answer)
            rc, out, _, _, _ = run(tasks('--json'), answer=answer)
            self.assertEqual((rc, out), (1, '{"findings": ["tasks: list_tasks gave an answer out of form"]}\n'))

    def test_list_tasks_looked_up_at_call_time(self):
        """TASK-091 AC2: list_tasks is looked up as execution.list_tasks at each call: a mock.patch.object made after
        cli's import is the one called."""
        stand = Stand()
        with mock.patch.object(execution, 'list_tasks', stand):
            rc = cli.main(tasks(), Sink(), {}, Clock())
        self.assertEqual((rc, len(stand.calls)), (0, 1))

    def test_root_not_printed(self):
        """TASK-091 AC2: with stand-in findings that do not name it, no output line holds the --root value."""
        for answer in ((TWO, None), ([], None), (None, ['a']), (None, 5), (5, None)):
            for flags in ((), ('--json',)):
                _, out, _, _, _ = run(tasks(*flags), answer=answer)
                self.assertNotIn(ROOT, out)


class TASK091AC3NeverRaises(unittest.TestCase):
    def test_raising_list_tasks(self):
        """TASK-091 AC3: a raising list_tasks gives exit 1 and "finding: tasks: a step raised <type name>", and its
        --json form."""
        rc, out, _, _, _ = run(tasks(), raises=KeyError('k'))
        self.assertEqual((rc, out), (1, 'finding: tasks: a step raised KeyError\n'))
        rc, out, _, _, _ = run(tasks('--json'), raises=KeyError('k'))
        self.assertEqual((rc, out), (1, '{"findings": ["tasks: a step raised KeyError"]}\n'))

    def test_raising_clock(self):
        """TASK-091 AC3: a raising clock gives exit 1 and the same finding, and list_tasks is not called."""
        rc, out, stand, clock, _ = run(tasks(), clock=Clock(raises=ValueError('c')))
        self.assertEqual((rc, out, stand.calls, clock.calls), (1, 'finding: tasks: a step raised ValueError\n', [], 1))

    def test_raising_render(self):
        """TASK-091 AC3: a mock.patch.object of cli._render that raises gives exit 1 and "finding: cli: a step
        raised <type name>", in the text form and under --json in the --json form."""
        with mock.patch.object(cli, '_render', side_effect=TypeError('r')):
            rc, out, _, _, _ = run(tasks())
            self.assertEqual((rc, out), (1, 'finding: cli: a step raised TypeError\n'))
            rc, out, _, _, _ = run(tasks('--json'))
            self.assertEqual((rc, out), (1, '{"findings": ["cli: a step raised TypeError"]}\n'))

    def test_raising_findings_gives_1_and_no_output(self):
        """TASK-091 AC3: a raise in _findings itself gives exit 1 and writes nothing (D-3022's note)."""
        with mock.patch.object(cli, '_findings', side_effect=TypeError('f')):
            rc, out, _, _, sink = run(tasks(), answer=(None, ['a']))
        self.assertEqual((rc, out, sink.writes), (1, '', []))

    def test_one_write_then_flush(self):
        """TASK-091 AC3: the output of one call is one stdout.write call, then one flush through getattr; a sink
        with no flush is written once."""
        _, _, _, _, sink = run(tasks())
        self.assertEqual((len(sink.writes), sink.flushes), (1, 1))
        sink = Sink(with_flush=False)
        rc, out, _, _, _ = run(tasks(), sink=sink)
        self.assertEqual((rc, len(sink.writes)), (0, 1))
        self.assertFalse(hasattr(sink, 'flush'))

    def test_raising_write_or_flush(self):
        """TASK-091 AC3: a stdout whose write raises gives exit 1 on a usage error, a success and findings; so do a
        stdout whose every call raises and a sink whose flush raises."""
        for argv, answer in (([], (TWO, None)), (tasks(), (TWO, None)), (tasks(), (None, ['a']))):
            rc, _, _, _, _ = run(argv, answer=answer, sink=Sink(raise_write=True))
            self.assertEqual((type(rc), rc), (int, 1), argv)
            rc, _, _, _, _ = run(argv, answer=answer, sink=AllRaise())
            self.assertEqual((type(rc), rc), (int, 1), argv)
            rc, _, _, _, _ = run(argv, answer=answer, sink=Sink(raise_flush=True))
            self.assertEqual((type(rc), rc), (int, 1), argv)

    def test_return_codes_are_ints(self):
        """TASK-091 AC3: type(rc) is int and rc is 0, 1 or 2 in the cases of AC1 to AC3."""
        cases = [run(argv)[0] for argv in BAD_ARGVS] + [run(argv)[0] for argv, _ in GOOD_ARGVS]
        cases += [run(tasks(), answer=(None, ['a']))[0], run(tasks(), raises=KeyError('k'))[0]]
        for rc in cases:
            self.assertIs(type(rc), int)
            self.assertIn(rc, (0, 1, 2))

    def test_entry_line(self):
        """TASK-091 AC3: the module's entry line is exactly `if __name__ == '__main__':` followed by
        `sys.exit(main(sys.argv[1:], sys.stdout, os.environ, _clock))`, checked by ast."""
        tree = ast.parse((SRC / 'cli.py').read_bytes().decode('utf-8'))
        last = tree.body[-1]
        self.assertIsInstance(last, ast.If)
        self.assertEqual(ast.unparse(last.test), "__name__ == '__main__'")
        self.assertEqual([ast.unparse(s) for s in last.body],
                         ['sys.exit(main(sys.argv[1:], sys.stdout, os.environ, _clock))'])

    def test_clock_form(self):
        """TASK-091 AC3: _clock gives a timezone-aware UTC datetime with microsecond 0."""
        now = cli._clock()
        self.assertEqual((now.tzinfo, now.microsecond), (datetime.timezone.utc, 0))


class TASK091AC4Runtime(unittest.TestCase):
    def test_runtime_vars_equal_the_other_modules(self):
        """TASK-091 AC4: RUNTIME_VARS is exactly the three names, equal to mcp_server's SESSION_VAR and ROOT_VAR and
        the pretool hook's BASE_VAR."""
        self.assertEqual(cli.RUNTIME_VARS, ('AIEOS_SESSION_ID', 'AIEOS_ROOT', 'AIEOS_BASE'))
        self.assertEqual(cli.RUNTIME_VARS,
                         (mcp_server.SESSION_VAR, mcp_server.ROOT_VAR, claude_code_pretool_hook.BASE_VAR))

    def test_runtime_vars_equal_the_launcher_environment(self):
        """TASK-091 AC4: RUNTIME_VARS, as a set, equals the keys of the one dict literal assigned to environment in
        the FunctionDef start of launcher.py, read by ast, its keys all str constants."""
        tree = ast.parse((SRC / 'launcher.py').read_bytes().decode('utf-8'))
        start = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'start']
        self.assertEqual(len(start), 1)
        found = [n.value for n in ast.walk(start[0]) if isinstance(n, ast.Assign) and len(n.targets) == 1
                 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'environment'
                 and isinstance(n.value, ast.Dict)]
        self.assertEqual(len(found), 1)
        keys = found[0].keys
        self.assertTrue(all(isinstance(k, ast.Constant) and type(k.value) is str for k in keys))
        self.assertEqual({k.value for k in keys}, set(cli.RUNTIME_VARS))

    def test_in_runtime(self):
        """TASK-091 AC4: in_runtime is true for any one of the three names with any value, '' included; false for
        {} and for other names only."""
        for name in cli.RUNTIME_VARS:
            for value in ('x', ''):
                self.assertIs(cli.in_runtime({name: value}), True, name)
        self.assertIs(cli.in_runtime({}), False)
        self.assertIs(cli.in_runtime({'AIEOS_OTHER': 'x', 'PATH': 'p'}), False)

    def test_in_runtime_fails_closed(self):
        """TASK-091 AC4: an environ whose membership test raises counts as inside a runtime."""
        class Raising:
            def __contains__(self, name):
                raise RuntimeError('in')
        self.assertIs(cli.in_runtime(Raising()), True)

    def test_tasks_does_not_refuse_inside_a_runtime(self):
        """TASK-091 AC4: tasks gives the same output with an environ holding all three names as with {}."""
        inside = {name: 'x' for name in cli.RUNTIME_VARS}
        self.assertEqual(run(tasks(), environ=inside)[:2], run(tasks(), environ={})[:2])


class TASK091AC5Module(unittest.TestCase):
    def tree(self):
        return ast.parse((SRC / 'cli.py').read_bytes().decode('utf-8'))

    def test_imports(self):
        """TASK-091 AC5, as changed by TASK-092: cli.py imports exactly datetime, json, os, re, sys, and execution and
        launcher from aieos_bootstrap."""
        names = set()
        for n in ast.walk(self.tree()):
            if isinstance(n, ast.Import):
                names.update(a.name for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                names.update('%s.%s' % (n.module, a.name) for a in n.names)
        self.assertEqual(names, {'datetime', 'json', 'os', 're', 'sys', 'aieos_bootstrap.execution',
                                 'aieos_bootstrap.launcher'})

    def test_refused_names(self):
        """TASK-091 AC5: cli.py names no open, exec, eval, compile, __import__, input, argparse, subprocess, writer,
        time or getenv, as a name or an attribute."""
        refused = {'open', 'exec', 'eval', 'compile', '__import__', 'input', 'argparse', 'subprocess', 'writer',
                   'time', 'getenv'}
        used = set()
        for n in ast.walk(self.tree()):
            if isinstance(n, ast.Name):
                used.add(n.id)
            elif isinstance(n, ast.Attribute):
                used.add(n.attr)
        self.assertEqual(used & refused, set())

    def test_os_only_as_environ_in_the_entry_line(self):
        """TASK-091 AC5: os is used only as os.environ, and only in the entry line."""
        tree = self.tree()
        entry = tree.body[-1]
        uses = [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == 'os']
        in_entry = [n for n in ast.walk(entry) if isinstance(n, ast.Name) and n.id == 'os']
        self.assertEqual(len(uses), len(in_entry))
        attrs = [n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                 and n.value.id == 'os']
        self.assertEqual(attrs, ['environ'])

    def test_no_state_dir_string_assert_or_bare_pass(self):
        """TASK-091 AC5: cli.py holds no string naming the project-state directory, no assert and no except clause
        whose body is only pass."""
        tree = self.tree()
        state_dir = '.' + 'aieos'
        strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertFalse([s for s in strings if state_dir in s])
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Assert)])
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)
                          and all(isinstance(s, ast.Pass) for s in n.body)])

    def test_this_test_file(self):
        """TASK-091 AC5: this file imports no tempfile, sqlite3 or shutil, names no open, roots only the literal
        'C:/cli-root-91', takes of claude_code_pretool_hook only BASE_VAR, and has no one-argument .replace() and no
        .replace(target=...)."""
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
        hook = [n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                and n.value.id == 'claude_code_pretool_hook']
        self.assertEqual(set(hook), {'BASE_VAR'})
        replaces = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == 'replace' and (len(n.args) == 1 or [k.arg for k in n.keywords] == ['target'])]
        self.assertEqual(replaces, [])


class TASK091AC6Docs(unittest.TestCase):
    def test_module_docstring(self):
        """TASK-091 AC6: cli.py's docstring holds the contract's phrases."""
        doc = ast.get_docstring(ast.parse((SRC / 'cli.py').read_bytes().decode('utf-8')))
        for phrase in ('python -m aieos_bootstrap.cli', 'the installed name is open', 'writes nothing',
                       'never raises', 'every Exception', 'outside any runtime', 'AIEOS_BASE is counted',
                       "'' counts as present", 'spec 5 :120', '__init__.py is not changed', 'TASK-091'):
            self.assertIn(phrase, doc)

    def test_every_test_names_its_criteria(self):
        """TASK-091 AC6: every test function of this module names "TASK-091 AC" in its own docstring, more than 20
        in all."""
        tree = ast.parse(HERE.read_bytes().decode('utf-8'))
        tests = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
        self.assertGreater(len(tests), 20)
        for node in tests:
            self.assertIn('TASK-091 AC', ast.get_docstring(node) or '', node.name)


if __name__ == '__main__':
    unittest.main()

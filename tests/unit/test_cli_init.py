"""Unit tests of launcher.init_project and the command init of cli.py (task TASK-095; specification 7 section 3 :28).
writer.init_layout is replaced by a stand-in through mock.patch.object for init_project's tests, and
launcher.init_project for the command's, each restored after its test; the clock is a counting stand-in that init must
never call. No process starts and no file is written; the only files read are the package's own launcher.py and
cli.py and this file, with pathlib's read_bytes, for the ast checks; the root is a literal Windows path that names no
folder. Stand-in defaults are sentinels, never a value a case passes (L-0033). Each test names its criteria in its own
docstring."""

import ast
import datetime
import json
import pathlib
import unittest
from collections import OrderedDict
from unittest import mock

from aieos_bootstrap import cli, launcher, writer

HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / 'src' / 'aieos_bootstrap'
ROOT = 'C:/init-root-95'
NOW = datetime.datetime(2026, 10, 25, 12, 0, 0, tzinfo=datetime.timezone.utc)
CREATED = ('x/intent/requirements', 'x/changes')
OUT_OF_FORM = 'init_layout: init_layout gave an answer out of form'
GOOD = object()


def done(value=GOOD):
    return writer.StoreResult('done', value=CREATED if value is GOOD else value)


def refused(reason='exists', findings=('exists: the project-state directory is present',)):
    return writer.StoreResult('refused', reason, findings)


class Layout:
    """writer.init_layout as a stand-in: gives its answer, or raises, and records each root it is called with."""

    def __init__(self, answer=GOOD, raises=None):
        self.answer = done() if answer is GOOD else answer
        self.raises = raises
        self.calls = []

    def __call__(self, root):
        self.calls.append(root)
        if self.raises is not None:
            raise self.raises
        return self.answer


class SubResult(writer.StoreResult):
    pass


def project(answer=GOOD, raises=None):
    stand = Layout(answer, raises)
    with mock.patch.object(writer, 'init_layout', stand):
        out = launcher.init_project(ROOT)
    return out, stand


def mapping(result, reason=None, findings=(), created=()):
    return {'result': result, 'reason': reason, 'findings': list(findings), 'created': list(created)}


class TASK095AC3InitProject(unittest.TestCase):
    def test_the_keys(self):
        """TASK-095 AC3: INIT_KEYS is the contract's."""
        self.assertEqual(launcher.INIT_KEYS, ('result', 'reason', 'findings', 'created'))

    def test_done_and_the_default_at_call_time(self):
        """TASK-095 AC3: with init_layout left out, writer.init_layout as patched after import is called exactly once
        with the root, and its "done" gives the mapping with exactly INIT_KEYS and the created list."""
        out, stand = project()
        self.assertEqual(stand.calls, [ROOT])
        self.assertEqual(out, mapping('done', created=CREATED))
        self.assertEqual(tuple(out), launcher.INIT_KEYS)

    def test_refused(self):
        """TASK-095 AC3: a "refused" StoreResult with a str reason and str findings gives "refused" with that reason
        and those findings, and created []."""
        out, _ = project(refused())
        self.assertEqual(out, mapping('refused', 'exists', ['exists: the project-state directory is present']))

    def test_answers_out_of_form(self):
        """TASK-095 AC3: each answer out of form gives reason "init_layout" and the one out-of-form finding: not a
        StoreResult, a subclass, done with an empty tuple, a list, a non-str item, a reason or findings, refused with
        a non-str reason or findings not a tuple of str, and a result other than done or refused."""
        listed = done()
        listed.value = list(CREATED)
        nonstr_findings = refused()
        nonstr_findings.findings = ('a', 3)
        list_findings = refused()
        list_findings.findings = ['a']
        bad = [None, 'done', {'result': 'done'}, SubResult('done', value=CREATED), done(()), listed,
               done(('a', 3)), done('x'), writer.StoreResult('done', 'r', value=CREATED),
               writer.StoreResult('done', None, ('f',), CREATED), refused(3), nonstr_findings, list_findings,
               writer.StoreResult('other', value=CREATED)]
        for answer in bad:
            with self.subTest(answer=answer):
                out, stand = project(answer)
                self.assertEqual(out, mapping('refused', 'init_layout', [OUT_OF_FORM]))
                self.assertEqual(stand.calls, [ROOT])

    def test_raises_never_escape(self):
        """TASK-095 AC3: a raise in init_layout gives "init_layout: a step raised <type>"; no call raises."""
        for exc in (RuntimeError('x'), OSError('y'), MemoryError()):
            out, _ = project(raises=exc)
            self.assertEqual(out, mapping('refused', 'init_layout',
                                          ['init_layout: a step raised %s' % type(exc).__name__]))

    def test_the_given_init_layout_is_used(self):
        """TASK-095 AC3: an init_layout passed as an argument is the one called, once."""
        stand = Layout()
        with mock.patch.object(writer, 'init_layout', Layout(raises=RuntimeError('not this one'))):
            out = launcher.init_project(ROOT, init_layout=stand)
        self.assertEqual((out['result'], stand.calls), ('done', [ROOT]))

    def test_what_init_project_names(self):
        """TASK-095 AC3: by ast, init_project and its helpers name no open, os, sys, time or subprocess and no
        attribute now, environ, getenv or write."""
        tree = ast.parse((SRC / 'launcher.py').read_bytes().decode('utf-8'))
        mine = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                and (n.name == 'init_project' or n.name.startswith('_init_project'))]
        self.assertEqual(len(mine), 3)
        names = {x.id for n in mine for x in ast.walk(n) if isinstance(x, ast.Name)}
        attrs = {x.attr for n in mine for x in ast.walk(n) if isinstance(x, ast.Attribute)}
        self.assertEqual(names & {'open', 'os', 'sys', 'time', 'subprocess'}, set())
        self.assertEqual(attrs & {'now', 'environ', 'getenv', 'write'}, set())


class Sink:
    def __init__(self):
        self.writes = []

    def write(self, text):
        self.writes.append(text)

    def flush(self):
        pass


class Clock:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return NOW


class Stand:
    """launcher.init_project as a stand-in: gives its answer, or raises, and records each call."""

    def __init__(self, answer=GOOD, raises=None):
        self.answer = mapping('done', created=CREATED) if answer is GOOD else answer
        self.raises = raises
        self.calls = []

    def __call__(self, root):
        self.calls.append(root)
        if self.raises is not None:
            raise self.raises
        return self.answer


def run(argv, answer=GOOD, raises=None, environ=None):
    sink, clock = Sink(), Clock()
    stand = Stand(answer, raises)
    with mock.patch.object(launcher, 'init_project', stand):
        rc = cli.main(argv, sink, {} if environ is None else environ, clock)
    return rc, ''.join(sink.writes), stand, clock


def init(*flags):
    return ['init', '--root', ROOT] + list(flags)


TEXT = 'created: x/intent/requirements\ncreated: x/changes\n'
JSON = '{"created": ["x/intent/requirements", "x/changes"], "findings": []}\n'


class SubDict(dict):
    pass


class SubList(list):
    pass


class TASK095AC4Command(unittest.TestCase):
    def test_one_call_and_no_clock(self):
        """TASK-095 AC4: "init --root R" and "init --root R --json" (either flag order) call init_project once with R
        and the clock never."""
        for argv in (init(), init('--json'), ['init', '--json', '--root', ROOT]):
            rc, _, stand, clock = run(argv)
            self.assertEqual((rc, stand.calls, clock.calls), (0, [ROOT], 0), argv)

    def test_usage_errors(self):
        """TASK-095 AC4: "init", "init --root", "init --root R extra", "init R --root R" and "init --root R --json
        --json" give exit 2 and USAGE with nothing called, outside and inside a runtime."""
        bad = (['init'], ['init', '--root'], init('extra'), ['init', ROOT, '--root', ROOT], init('--json', '--json'),
               ['Init', '--root', ROOT])
        for environ in ({}, {'AIEOS_ROOT': 'x'}):
            for argv in bad:
                rc, out, stand, clock = run(argv, environ=environ)
                self.assertEqual((rc, out, stand.calls, clock.calls), (2, cli.USAGE, [], 0), (argv, environ))

    def test_refused_inside_a_runtime(self):
        """TASK-095 AC4: an environ holding any one of the three RUNTIME_VARS, an empty value included, gives exit 1
        and the one runtime-refusal finding with nothing called."""
        line = 'finding: %s\n' % cli.INIT_RUNTIME_REFUSAL
        for name in cli.RUNTIME_VARS:
            for value in ('x', ''):
                rc, out, stand, clock = run(init(), environ={name: value})
                self.assertEqual((rc, out, stand.calls, clock.calls), (1, line, [], 0), (name, value))

    def test_the_refusal_text(self):
        """TASK-095 AC4: the runtime refusal's text is the contract's, and under --json it is one JSON line."""
        self.assertEqual(cli.INIT_RUNTIME_REFUSAL, 'init: refused inside a runtime (it writes; specification 7 :34 '
                                                   'names end and launch, and init is refused for the same reason)')
        rc, out, _, _ = run(init('--json'), environ={'AIEOS_BASE': 'x'})
        self.assertEqual((rc, json.loads(out)), (1, {'findings': [cli.INIT_RUNTIME_REFUSAL]}))

    def test_done_lines(self):
        """TASK-095 AC4: "done" gives exit 0 and one "created: " line per folder, in order."""
        self.assertEqual(run(init())[:2], (0, TEXT))

    def test_the_json_line(self):
        """TASK-095 AC4: under --json "done" gives exactly '{"created": [...], "findings": []}' with sort_keys."""
        self.assertEqual(run(init('--json'))[:2], (0, JSON))

    def test_refused(self):
        """TASK-095 AC4: "refused" gives exit 1 and "finding: init: <reason>" then its findings, or one JSON line."""
        answer = mapping('refused', 'exists', ['exists: the project-state directory is present'])
        rc, out, _, _ = run(init(), answer=answer)
        self.assertEqual((rc, out), (1, 'finding: init: exists\nfinding: exists: the project-state directory is '
                                        'present\n'))
        rc, out, _, _ = run(init('--json'), answer=answer)
        self.assertEqual((rc, json.loads(out)), (1, {'findings': ['init: exists',
                                                                  'exists: the project-state directory is present']}))

    def test_answers_out_of_form(self):
        """TASK-095 AC4: an answer not a dict, a dict subclass, other keys, a created list subclass, a non-str item, an
        empty created list for done, a done with a reason or findings, and a refused with created items each give the
        out-of-form finding."""
        good = mapping('done', created=CREATED)
        bad = [None, 'done', [good], SubDict(good), OrderedDict(good), dict(good, extra=1),
               {k: v for k, v in good.items() if k != 'reason'}, dict(good, created=SubList(CREATED)),
               dict(good, created=['a', 3]), dict(good, created=[]), dict(good, created=tuple(CREATED)),
               dict(good, reason='r'), dict(good, findings=['f']), dict(good, result='other'), dict(good, result=None),
               mapping('refused', 'exists', ['f'], ['a']), mapping('refused', 3, ['f']),
               dict(mapping('refused', 'exists', ['f']), findings=('f',)), mapping('refused', 'exists', [3])]
        for answer in bad:
            with self.subTest(answer=answer):
                rc, out, _, _ = run(init(), answer=answer)
                self.assertEqual((rc, out), (1, 'finding: init: init_project gave an answer out of form\n'))

    def test_a_raising_init_project(self):
        """TASK-095 AC4: a raising init_project gives "init: a step raised <type>"."""
        rc, out, _, _ = run(init(), raises=MemoryError())
        self.assertEqual((rc, out), (1, 'finding: init: a step raised MemoryError\n'))

    def test_a_raising_render(self):
        """TASK-095 AC4: a raising _render_init (patched) gives exit 1 and "cli: a step raised <type>"."""
        with mock.patch.object(cli, '_render_init', mock.Mock(side_effect=ValueError('render'))):
            rc, out, _, _ = run(init())
        self.assertEqual((rc, out), (1, 'finding: cli: a step raised ValueError\n'))

    def test_the_other_commands_still_parse(self):
        """TASK-095 AC4, as TASK-094 AC6, TASK-096 AC6, TASK-097 AC6 and TASK-098 AC6 widen it: COMMANDS keeps tasks,
        end and status before init, then launch, approve, edit, reject, import and run, and init takes no session."""
        self.assertEqual(cli.COMMANDS, ('tasks', 'end', 'status', 'init', 'launch', 'approve', 'edit', 'reject',
                                        'import', 'run'))
        rc, out, stand, _ = run(['init', 'S', '--root', ROOT])
        self.assertEqual((rc, out, stand.calls), (2, cli.USAGE, []))


def used_names(node):
    return ({n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            | {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)})


def function(name, file_name):
    tree = ast.parse((SRC / file_name).read_bytes().decode('utf-8'))
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name][0]


class TASK095AC5Modules(unittest.TestCase):
    def test_the_command_functions(self):
        """TASK-095 AC5: by ast, cli.py's _init, _render_init and _init_in_form name no writer, held_leases or
        clock."""
        for name in ('_init', '_render_init', '_init_in_form'):
            self.assertFalse(used_names(function(name, 'cli.py')) & {'writer', 'held_leases', 'clock'}, name)

    def test_no_state_directory_text(self):
        """TASK-095 AC5: launcher.py and cli.py hold no string naming the project-state directory."""
        state_dir = '.' + 'aieos'
        for name in ('launcher.py', 'cli.py'):
            tree = ast.parse((SRC / name).read_bytes().decode('utf-8'))
            strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
            self.assertFalse([s for s in strings if state_dir in s], name)

    def test_this_test_file(self):
        """TASK-095 AC5: this file imports no tempfile, sqlite3 or shutil, names no open, roots only the literal
        'C:/init-root-95', and has no one-argument .replace() and no .replace(target=...)."""
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


def doc(file_name):
    return ' '.join(ast.get_docstring(ast.parse((SRC / file_name).read_bytes().decode('utf-8'))).split())


class TASK095AC6Docs(unittest.TestCase):
    def test_the_cli_docstring_and_usage(self):
        """TASK-095 AC6, as TASK-094 AC6, TASK-096 AC6, TASK-097 AC6 and TASK-098 AC6 widen it: cli.py's docstring
        holds "aieos init", "TASK-095", "COMMANDS, tasks, end, status, init, launch, approve, edit, reject, import or
        run" and "end and init call it after the parse", and not "COMMANDS, tasks, end or status", "COMMANDS, tasks,
        end, status or init", "COMMANDS, tasks, end, status, init or launch", "COMMANDS, tasks, end, status, init,
        launch, approve, edit or reject" nor "COMMANDS, tasks, end, status, init, launch, approve, edit, reject or
        import"; USAGE names init."""
        text = doc('cli.py')
        for phrase in ('aieos init', 'TASK-095',
                       'COMMANDS, tasks, end, status, init, launch, approve, edit, reject, import or run',
                       'end and init call it after the parse'):
            self.assertIn(phrase, text)
        for phrase in ('COMMANDS, tasks, end or status', 'COMMANDS, tasks, end, status or init',
                       'COMMANDS, tasks, end, status, init or launch',
                       'COMMANDS, tasks, end, status, init, launch, approve, edit or reject',
                       'COMMANDS, tasks, end, status, init, launch, approve, edit, reject or import'):
            self.assertNotIn(phrase, text)
        self.assertIn('init --root <path> [--json]', cli.USAGE)

    def test_the_launcher_docstring(self):
        """TASK-095 AC6: launcher.py's docstring holds "init_project" and "TASK-095"."""
        text = doc('launcher.py')
        for phrase in ('init_project', 'TASK-095'):
            self.assertIn(phrase, text)

    def test_every_test_names_its_criteria(self):
        """TASK-095 AC6: every test function of this module names "TASK-095 AC" in its own docstring, more than 20
        in all."""
        tree = ast.parse(HERE.read_bytes().decode('utf-8'))
        tests = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
        self.assertGreater(len(tests), 20)
        for node in tests:
            self.assertIn('TASK-095 AC', ast.get_docstring(node) or '', node.name)


if __name__ == '__main__':
    unittest.main()

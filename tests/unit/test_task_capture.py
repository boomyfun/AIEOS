"""Unit tests of aieos_runtime.task_capture (task TASK-147, the capture step of route (c) of DEF-0149), standard library
only. No test starts a process and none writes a file: the module's `subprocess` is replaced by a stand-in through
mock.patch.object and the environment through mock.patch.dict, each restored after its test; the only files read are
the module's own source, the CI workflow and this test file itself, with pathlib's read_bytes, for the ast and text
checks (the test file is read by the identity test). The behaviour against a real git
repository is not tested here: the CI's source rules refuse a test file that starts git or writes a file, so it is shown
at acceptance by a harness outside the repository (TASK-147 AC5). Each test names its criteria in its own docstring."""

import ast
import os
import pathlib
import re
import types
import unittest
from unittest import mock

from aieos_runtime import task_capture

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[2]
MODULE = ROOT / 'src' / 'aieos_runtime' / 'task_capture.py'
WORKFLOW = ROOT / '.github' / 'workflows' / 'aieos-checks.yml'

REPO = os.path.abspath('repo-146')
GITDIR = os.path.join(REPO, '.git')
INDEX = os.path.join(GITDIR, 'aieos-capture-index')
GOOD_PATH = os.path.abspath('bin-146')
OLD = 'a' * 40
TREE = 'b' * 40
COMMIT = 'c' * 40
MOVED = 'd' * 40
REF = 'refs/heads/task/TASK-147'
IDENTITY = {'name': 'Cap Tester', 'email': 'cap'}
MESSAGE = 'capture test\n\nAIEOS-Task: TASK-147\n'
STATE = '.aieos'
PATHS = ['a.txt', 'src/b.py', 'new/dir/c.txt']
CLASSES = {'a.txt': 'modified', 'src/b.py': 'deleted', 'new/dir/c.txt': 'added'}
PREFIX = 1 + len(task_capture.CAPTURE_OPTIONS) + 2
FIXED_NAMES = {key for key, value in task_capture.CAPTURE_ENV_FIXED}


class TimedOut(Exception):
    pass


class FakeSubprocess:
    """The module's `subprocess`: records each call of run and answers from a responder; starts nothing."""
    PIPE = object()
    TimeoutExpired = TimedOut

    def __init__(self, responder=None):
        self.calls = []
        self.responder = responder or default_answer

    def run(self, args, **kwargs):
        self.calls.append((list(args), dict(kwargs)))
        code, out, err = self.responder(list(args)[PREFIX:], kwargs)
        return types.SimpleNamespace(returncode=code, stdout=out, stderr=err)


def default_answer(form, kwargs):
    sub = form[0]
    if form[:2] == ['rev-parse', '--absolute-git-dir']:
        return 0, (GITDIR + '\n').encode('utf-8'), b''
    if form[:2] == ['rev-parse', '--verify']:
        return 0, (OLD + '\n').encode('ascii'), b''
    if sub == 'write-tree':
        return 0, (TREE + '\n').encode('ascii'), b''
    if sub == 'commit-tree':
        return 0, (COMMIT + '\n').encode('ascii'), b''
    if sub == 'diff':
        return 0, ('\n'.join(sorted(PATHS)) + '\n').encode('utf-8'), b''
    return 0, b'', b''


class World:
    """One test's stand-ins: the process function and an environment with an absolute PATH."""

    def __init__(self, responder=None, environ=None):
        self.sub = FakeSubprocess(responder)
        self.environ = {'PATH': GOOD_PATH, 'SYSTEMROOT': 'stand-in-root'} if environ is None else dict(environ)

    def __enter__(self):
        self.patches = [mock.patch.object(task_capture, 'subprocess', self.sub),
                        mock.patch.dict(os.environ, self.environ, clear=True)]
        for p in self.patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in reversed(self.patches):
            p.stop()
        return False


def good_capture(**changes):
    args = {'repo': REPO, 'ref': REF, 'old_head': OLD, 'paths': list(PATHS), 'message': MESSAGE,
            'identity': dict(IDENTITY), 'state_name': STATE}
    args.update(changes)
    return args


def good_restore(**changes):
    args = {'repo': REPO, 'paths': list(PATHS), 'classes': dict(CLASSES), 'state_name': STATE}
    args.update(changes)
    return args


def forms_of(world):
    return [call[0][PREFIX:] for call in world.sub.calls]


def source():
    return MODULE.read_bytes().decode('utf-8')


class Interface(unittest.TestCase):
    def test_a_good_capture_is_nine_calls_in_the_fixed_order(self):
        """TASK-147 AC1 and AC4: a capture gives {'result': 'done', 'commit': <id>} after exactly these calls in this order:
        rev-parse --absolute-git-dir, rev-parse --verify HEAD, read-tree, update-index, write-tree, commit-tree,
        update-ref, rev-parse --verify HEAD, diff; and nothing else is public in the module but capture and restore."""
        with World() as w:
            r = task_capture.capture(**good_capture())
        self.assertEqual(r, {'result': 'done', 'commit': COMMIT})
        self.assertEqual([f[0] if f[0] != 'rev-parse' else ' '.join(f[:2]) for f in forms_of(w)],
                         ['rev-parse --absolute-git-dir', 'rev-parse --verify', 'read-tree', 'update-index',
                          'write-tree', 'commit-tree', 'update-ref', 'rev-parse --verify', 'diff'])
        public = sorted(n for n in dir(task_capture) if not n.startswith('_') and callable(getattr(task_capture, n))
                        and getattr(getattr(task_capture, n), '__module__', None) == task_capture.__name__)
        self.assertEqual(public, ['capture', 'restore'])

    def test_a_good_restore_gives_done_and_reads_no_status(self):
        """TASK-147 AC1: a restore gives {'result': 'done'}; none of its calls is a status call or any form outside
        CAPTURE_FORMS."""
        with World() as w:
            r = task_capture.restore(**good_restore())
        self.assertEqual(r, {'result': 'done'})
        self.assertEqual([f[0] for f in forms_of(w)], ['restore', 'clean'])

    def test_the_refused_form_has_exactly_three_keys_and_a_known_reason(self):
        """TASK-147 AC1: a refusal is a mapping of exactly result, reason and findings, the reason one of REASONS and the
        findings a list of str that holds no path text."""
        with World() as w:
            r = task_capture.capture(**good_capture(paths=['bad:name']))
        self.assertEqual(sorted(r), ['findings', 'reason', 'result'])
        self.assertEqual(r['result'], 'refused')
        self.assertIn(r['reason'], task_capture.REASONS)
        self.assertTrue(all(type(f) is str and 'bad:name' not in f for f in r['findings']))
        self.assertEqual(w.sub.calls, [])

    def test_the_reason_words_are_the_closed_set(self):
        """TASK-147 AC1: REASONS is exactly the six words."""
        self.assertEqual(task_capture.REASONS, ('invalid-argument', 'head-moved', 'ref-exists', 'name-list-mismatch',
                                                'git-failed', 'timeout'))

    def test_the_docstring_states_the_limits_without_effect_labels(self):
        """TASK-147 AC1 and AC8: the docstring has the limits in plain words and none of the three effect labels."""
        doc = ast.get_docstring(ast.parse(source()))
        self.assertIn('Limits, in plain words', doc)
        for label in ('MEAS' + 'URED', 'ENFOR' + 'CED', 'GUARAN' + 'TEED'):
            self.assertNotIn(label, doc)

    def test_the_docstring_holds_the_four_statements_of_the_contract(self):
        """TASK-149 AC3: the docstring states, by these key words, the state-name rule as the code applies it, that the
        suite does not run the real git behaviour, that a git directory with a character outside ASCII is refused as
        git-failed, and the value 60 of the timeout constant; the check fails if one statement is removed."""
        doc = ' '.join(ast.get_docstring(ast.parse(source())).split())
        statements = {'the state-name rule as coded': ('is not only a dot', 'holds no slash and no backslash'),
                      'the real git behaviour is not run by the suite': ('does not run the real git behaviour',),
                      'a git directory outside ASCII is git-failed': ('outside ASCII is refused as git-failed',),
                      'the timeout constant': ('time limit of 60 seconds', 'the int constant 60')}
        for statement, keys in statements.items():
            for key in keys:
                self.assertIn(key, doc, statement)


class Refusals(unittest.TestCase):
    def check(self, call, args):
        with World() as w:
            r = call(**args)
        self.assertEqual(r['result'], 'refused', args)
        self.assertEqual(r['reason'], 'invalid-argument', args)
        self.assertEqual(w.sub.calls, [], args)

    def test_each_argument_of_capture_is_checked_before_any_process_starts(self):
        """TASK-147 AC2: an empty or non-list path list, a duplicate (also in another letter case), a backslash, a colon,
        an empty name, a dot name, a dot-dot name, a leading dash, an absolute path, a name ending in a dot or a space,
        a character below 0x20 or above 0x7e, a quote, a star, a question mark, a bracket, a state-directory first name
        in another letter case, a .git name anywhere in any letter case, a bad state name, a bad reference, a bad old
        head, an empty or NUL message, a bad identity and a non-absolute repository are each refused with no call."""
        bad_paths = ([], 'a.txt', ['a.txt', 'a.txt'], ['a.txt', 'A.TXT'], ['a\\b'], ['a:b'], ['a//b'], ['a/./b'],
                     ['a/../b'], ['-a'], ['/a'], ['a.'], ['a /b'], ['a/b '], ['a\x01b'], ['a\x7fb'], ['aéb'],
                     ['a"b'], ['a*b'], ['a?b'], ['a[b'], ['a]b'], ['.AIEOS/x'], ['.Aieos'], ['.git/config'],
                     ['dir/.GIT/x'], ['.Git/x'], [''], [1])
        for paths in bad_paths:
            self.check(task_capture.capture, good_capture(paths=paths))
        for state in ('', 'aieos', '.', '.a/b', '.a\\b', None):
            self.check(task_capture.capture, good_capture(state_name=state))
        for ref in ('refs/heads/main', 'refs/heads/task/TASK-', 'refs/heads/task/TASK-1x', 'task/TASK-1', '', None):
            self.check(task_capture.capture, good_capture(ref=ref))
        for head in ('a' * 39, 'A' * 40, 'g' * 40, '', None):
            self.check(task_capture.capture, good_capture(old_head=head))
        for message in ('', 'a\0b', None):
            self.check(task_capture.capture, good_capture(message=message))
        for identity in ({}, {'name': 'x'}, {'name': 'x', 'email': ''}, {'name': '', 'email': 'e'},
                         {'name': 'x<', 'email': 'e'}, {'name': 'x', 'email': 'e>'}, {'name': 'x\n', 'email': 'e'},
                         {'name': 'x', 'email': 'e\0'}, {'name': 'x', 'email': 'e', 'more': 'y'}, None):
            self.check(task_capture.capture, good_capture(identity=identity))
        self.check(task_capture.capture, good_capture(repo='relative'))
        self.check(task_capture.capture, good_capture(message='lone \ud800 surrogate'))

    def test_the_refusals_before_any_process_are_invalid_argument_and_start_no_process(self):
        """TASK-149 AC2: a bad path, a bad reference, an upper-case old head, a relative repository and a bad classes
        value are refused with the reason invalid-argument and with no process started, as before the id check that
        follows a printed id."""
        self.check(task_capture.capture, good_capture(paths=['bad:name']))
        self.check(task_capture.capture, good_capture(ref='refs/heads/main'))
        self.check(task_capture.capture, good_capture(old_head='A' * 40))
        self.check(task_capture.capture, good_capture(repo='relative'))
        self.check(task_capture.restore, good_restore(classes=None))

    def test_each_argument_of_restore_is_checked_before_any_process_starts(self):
        """TASK-147 AC2: for restore a class that is missing, extra or not one of the three, a classes value that is not
        a mapping, an empty path list, a path with a backslash, a bad state name and a non-absolute repository are
        refused with no call; of the path and state-name refusals of capture only these three are tried for restore,
        the others are tried for capture alone."""
        for classes in ({}, {'a.txt': 'modified'}, dict(CLASSES, extra='added'), dict(CLASSES, **{'a.txt': 'x'}), None):
            self.check(task_capture.restore, good_restore(classes=classes))
        self.check(task_capture.restore, good_restore(paths=[], classes={}))
        self.check(task_capture.restore, good_restore(paths=['a\\b'], classes={'a\\b': 'added'}))
        self.check(task_capture.restore, good_restore(state_name='aieos'))
        self.check(task_capture.restore, good_restore(repo='relative'))

    def test_a_form_outside_the_table_or_with_a_value_out_of_its_form_is_refused_before_a_call(self):
        """TASK-147 AC2 and AC4: _build refuses a form that is not one of CAPTURE_FORMS, an id that is not 40 lowercase
        hexadecimal characters, a reference that is not a task reference, paths that are not a part of the listed
        paths, an id the form does not take; so no argument vector outside the table is ever built."""
        form = task_capture.CAPTURE_FORMS
        self.assertEqual(task_capture._build(form[6], {}), (['rev-parse', '--verify', 'HEAD'], None))
        for template, values in ((('status',), {}), (form[3], {'ids': ['x' * 40, OLD]}), (form[3], {'ids': [TREE]}),
                                 (form[3], {'ids': [TREE, OLD, OLD]}), (form[4], {'ref': 'refs/heads/main', 'ids': [OLD]}),
                                 (form[1], {'allowed': ['a'], 'paths': ['b']}), (form[1], {'allowed': ['a'], 'paths': []}),
                                 (form[8], {'allowed': ['a'], 'paths': None})):
            out, found = task_capture._build(template, values)
            self.assertIsNone(out, template)
            self.assertTrue(found, template)


class Pins(unittest.TestCase):
    def test_the_three_literals_equal_the_workflows(self):
        """TASK-147 AC3: CAPTURE_FORMS, CAPTURE_OPTIONS and CAPTURE_ENV_FIXED equal the literals that the workflow's
        deterministic_rule step pins (revision 28), read from the workflow's text with ast and literal_eval."""
        lines = WORKFLOW.read_bytes().decode('utf-8').split('\n')
        first = [i for i, line in enumerate(lines) if line.startswith('          CAPTURE_FORMS = (')]
        last = [i for i, line in enumerate(lines) if line.startswith('          CAPTURE_PINS = ')]
        self.assertEqual((len(first), len(last)), (1, 1))
        block = '\n'.join(line[10:] for line in lines[first[0]:last[0]])
        found = {}
        for node in ast.parse(block).body:
            self.assertIsInstance(node, ast.Assign)
            found[node.targets[0].id] = ast.literal_eval(node.value)
        self.assertEqual(sorted(found), ['CAPTURE_ENV_FIXED', 'CAPTURE_FORMS', 'CAPTURE_OPTIONS'])
        self.assertEqual(task_capture.CAPTURE_FORMS, found['CAPTURE_FORMS'])
        self.assertEqual(task_capture.CAPTURE_OPTIONS, found['CAPTURE_OPTIONS'])
        self.assertEqual(task_capture.CAPTURE_ENV_FIXED, found['CAPTURE_ENV_FIXED'])


class SourceShape(unittest.TestCase):
    def setUp(self):
        self.tree = ast.parse(source())

    def test_one_process_call_one_os_import_and_no_other_import(self):
        """TASK-147 AC3: the module has exactly one subprocess.run call, one top-level import os, imports only os, re and
        subprocess, and no module of aieos_bootstrap."""
        runs = [n for n in ast.walk(self.tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == 'run' and isinstance(n.func.value, ast.Name) and n.func.value.id == 'subprocess']
        self.assertEqual(len(runs), 1)
        imports = [n for n in ast.walk(self.tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertEqual(sorted(a.name for n in imports if isinstance(n, ast.Import) for a in n.names),
                         ['os', 're', 'subprocess'])
        self.assertFalse([n for n in imports if isinstance(n, ast.ImportFrom)])
        top = [n for n in self.tree.body if isinstance(n, ast.Import) and [a.name for a in n.names] == ['os']
               and n.names[0].asname is None]
        self.assertEqual(len(top), 1)

    def test_the_pinned_names_are_bound_once_and_os_and_list_are_never_rebound(self):
        """TASK-147 AC3: each of the three pinned names is bound once, at module level; the names os and list are never
        stored, passed as a parameter or defined; no attribute devnull is stored; and none of setattr, globals, vars or
        a modules attribute is used."""
        stores = {}
        for n in ast.walk(self.tree):
            if isinstance(n, ast.Name) and not isinstance(n.ctx, ast.Load):
                stores[n.id] = stores.get(n.id, 0) + 1
            if isinstance(n, ast.arg):
                self.assertNotIn(n.arg, ('os', 'list', 'CAPTURE_FORMS', 'CAPTURE_OPTIONS', 'CAPTURE_ENV_FIXED'))
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                self.assertNotIn(n.name, ('os', 'list'))
            if isinstance(n, ast.Attribute) and n.attr == 'devnull':
                self.assertIsInstance(n.ctx, ast.Load)
            if isinstance(n, ast.Attribute):
                self.assertNotEqual(n.attr, 'modules')
        for name in ('CAPTURE_FORMS', 'CAPTURE_OPTIONS', 'CAPTURE_ENV_FIXED'):
            self.assertEqual(stores.get(name), 1, name)
        self.assertNotIn('os', stores)
        self.assertNotIn('list', stores)
        loaded = {n.id for n in ast.walk(self.tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        for bad in ('setattr', 'globals', 'vars', 'exec', 'eval', 'compile', 'open', '__import__'):
            self.assertNotIn(bad, loaded)
        self.assertTrue({'CAPTURE_FORMS', 'CAPTURE_ENV_FIXED'} <= loaded)

    def test_the_call_keywords_and_the_timeout_are_the_pinned_form(self):
        """TASK-147 AC1 and AC3: subprocess.run is called with shell False, an int constant timeout, an env name and only
        the allowed keywords, and the module names no string of the project-state directory."""
        call = [n for n in ast.walk(self.tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == 'run'][0]
        keywords = {k.arg: k.value for k in call.keywords}
        self.assertEqual(sorted(keywords), ['check', 'cwd', 'env', 'input', 'shell', 'stderr', 'stdout', 'timeout'])
        self.assertIs(keywords['shell'].value, False)
        self.assertEqual(keywords['timeout'].value, 60)
        self.assertIs(type(keywords['timeout'].value), int)
        self.assertIsInstance(keywords['env'], ast.Name)
        self.assertNotIn('.aieos', source())


class Environment(unittest.TestCase):
    def test_the_environment_is_built_from_nothing_and_the_index_file_is_set_for_three_steps_only(self):
        """TASK-147 AC4: for every call the env holds only PATH, SYSTEMROOT when present, the fixed pairs with the null
        device in place of the placeholder, GIT_INDEX_FILE (the file aieos-capture-index in the git directory) for
        read-tree, update-index and write-tree only, and the four identity variables for commit-tree only; GIT_DIR,
        GIT_WORK_TREE and GIT_INDEX_FILE of the caller's environment never reach git."""
        dirty = {'PATH': GOOD_PATH, 'SYSTEMROOT': 'stand-in-root', 'GIT_DIR': 'x', 'GIT_WORK_TREE': 'y',
                 'GIT_INDEX_FILE': 'z', 'HOME': 'h', 'GIT_AUTHOR_NAME': 'other'}
        with World(environ=dirty) as w:
            task_capture.capture(**good_capture())
        for argv, kw in w.sub.calls:
            form = argv[PREFIX:]
            env = kw['env']
            names = set(env)
            self.assertEqual(names - {'GIT_INDEX_FILE', 'GIT_AUTHOR_NAME', 'GIT_AUTHOR_EMAIL', 'GIT_COMMITTER_NAME',
                                      'GIT_COMMITTER_EMAIL'}, {'PATH', 'SYSTEMROOT'} | FIXED_NAMES, form)
            self.assertEqual(env['GIT_CONFIG_GLOBAL'], os.devnull)
            self.assertEqual(env['PATH'], GOOD_PATH)
            self.assertEqual('GIT_INDEX_FILE' in env, form[0] in ('read-tree', 'update-index', 'write-tree'), form)
            if 'GIT_INDEX_FILE' in env:
                self.assertEqual(env['GIT_INDEX_FILE'], INDEX)
            if form[0] == 'commit-tree':
                self.assertEqual({k: env[k] for k in env if k.startswith(('GIT_AUTHOR', 'GIT_COMMITTER'))},
                                 {'GIT_AUTHOR_NAME': 'Cap Tester', 'GIT_AUTHOR_EMAIL': 'cap',
                                  'GIT_COMMITTER_NAME': 'Cap Tester', 'GIT_COMMITTER_EMAIL': 'cap'})
            else:
                self.assertFalse([k for k in env if k.startswith(('GIT_AUTHOR', 'GIT_COMMITTER'))], form)

    def test_without_systemroot_none_is_passed_and_a_bad_path_is_refused_without_a_call(self):
        """TASK-147 AC4: SYSTEMROOT is passed only when present; an empty PATH, or one with an empty or a relative
        entry, is refused with no process started."""
        with World(environ={'PATH': GOOD_PATH}) as w:
            task_capture.capture(**good_capture())
        self.assertTrue(all('SYSTEMROOT' not in kw['env'] for argv, kw in w.sub.calls))
        for bad in ('', os.pathsep + GOOD_PATH, GOOD_PATH + os.pathsep + 'relative'):
            with World(environ={'PATH': bad}) as w:
                r = task_capture.capture(**good_capture())
            self.assertEqual((r['result'], r['reason']), ('refused', 'git-failed'), bad)
            self.assertEqual(w.sub.calls, [], bad)
        with World(environ={}) as w:
            r = task_capture.restore(**good_restore())
        self.assertEqual(r['result'], 'refused')
        self.assertEqual(w.sub.calls, [])

    def test_every_call_begins_with_the_fixed_options_and_the_null_hooks_path(self):
        """TASK-147 AC4: every call list is git, the pinned options, -c core.hooksPath= and the null device, then the form;
        the call has no shell, a timeout of 60 and the repository as its working directory; the commit-tree call carries
        --no-gpg-sign and the message as UTF-8 bytes in the input keyword; the diff call carries the old head and the
        commit; every paths slot is a part of the listed paths."""
        with World() as w:
            task_capture.capture(**good_capture(message='café capture\n\nAIEOS-Task: TASK-147\n'))
        head = ['git'] + list(task_capture.CAPTURE_OPTIONS) + ['-c', 'core.hooksPath=' + os.devnull]
        for argv, kw in w.sub.calls:
            self.assertEqual(argv[:PREFIX], head)
            self.assertIs(kw['shell'], False)
            self.assertEqual(kw['timeout'], 60)
            self.assertEqual(kw['cwd'], REPO)
            self.assertIs(kw['check'], False)
            form = argv[PREFIX:]
            if form[0] in ('update-index', 'restore', 'clean'):
                self.assertTrue(set(form[form.index('--') + 1:]) <= set(PATHS))
            if form[0] == 'commit-tree':
                self.assertEqual(form, ['commit-tree', '--no-gpg-sign', TREE, '-p', OLD, '-F', '-'])
                self.assertEqual(kw['input'], 'café capture\n\nAIEOS-Task: TASK-147\n'.encode('utf-8'))
            else:
                self.assertIsNone(kw['input'])
            if form[0] == 'diff':
                self.assertEqual(form[-2:], [OLD, COMMIT])
            if form[0] == 'update-ref':
                self.assertEqual(form, ['update-ref', REF, COMMIT, '0' * 40])


class Reasons(unittest.TestCase):
    def scripted(self, **answers):
        """A responder that answers a form by its first words from answers (a tuple or an exception to raise)."""
        def responder(form, kwargs):
            key = ' '.join(form[:2]) if form[0] == 'rev-parse' else form[0]
            if key == 'rev-parse --verify':
                key = 'head1' if not state['head'] else 'head2'
                state['head'] += 1
            got = answers.get(key)
            if isinstance(got, Exception):
                raise got
            return got if got is not None else default_answer(form, kwargs)
        state = {'head': 0}
        return responder

    def refusal(self, responder, call=None, args=None):
        with World(responder) as w:
            r = (call or task_capture.capture)(**(args or good_capture()))
        self.assertEqual(r['result'], 'refused')
        self.assertEqual(sorted(r), ['findings', 'reason', 'result'])
        self.assertTrue(all(type(f) is str for f in r['findings']))
        return r, w

    def test_head_moved_before_and_after_the_ref_is_written(self):
        """TASK-147 AC1: a HEAD that is not the old head is refused as head-moved at the first check (no write follows)
        and at the second (the reference stays; the module undoes nothing)."""
        first, w = self.refusal(self.scripted(head1=(0, (MOVED + '\n').encode('ascii'), b'')))
        self.assertEqual(first['reason'], 'head-moved')
        self.assertEqual([f[0] for f in forms_of(w)], ['rev-parse', 'rev-parse'])
        second, w = self.refusal(self.scripted(head2=(0, (MOVED + '\n').encode('ascii'), b'')))
        self.assertEqual(second['reason'], 'head-moved')
        self.assertEqual(forms_of(w)[-1][:2], ['rev-parse', '--verify'])
        self.assertIn('update-ref', [f[0] for f in forms_of(w)])

    def test_an_existing_reference_is_told_by_the_exit_and_the_text_and_nothing_else(self):
        """TASK-147 AC1: update-ref with a non-zero exit and the text 'already exists' is ref-exists and no further call
        follows; any other update-ref failure is git-failed."""
        exists = (128, b'', b"fatal: update_ref failed for ref 'r': cannot lock ref 'r': reference already exists\n")
        r, w = self.refusal(self.scripted(**{'update-ref': exists}))
        self.assertEqual(r['reason'], 'ref-exists')
        self.assertEqual(forms_of(w)[-1][0], 'update-ref')
        other, w = self.refusal(self.scripted(**{'update-ref': (128, b'', b'fatal: something else\n')}))
        self.assertEqual(other['reason'], 'git-failed')
        self.assertEqual(forms_of(w)[-1][0], 'update-ref')
        text_but_exit_zero = self.scripted(**{'update-ref': (0, b'', b'already exists')})
        with World(text_but_exit_zero):
            self.assertEqual(task_capture.capture(**good_capture())['result'], 'done')

    def test_a_name_list_that_differs_is_refused_and_the_reference_stays(self):
        """TASK-147 AC1: a diff that lists other paths than the listed ones (fewer, more or different) is
        name-list-mismatch, after update-ref."""
        for out in (b'a.txt\n', b'a.txt\nsrc/b.py\nnew/dir/c.txt\nextra\n', b'a.txt\nsrc/b.py\nother\n', b''):
            r, w = self.refusal(self.scripted(diff=(0, out, b'')))
            self.assertEqual(r['reason'], 'name-list-mismatch', out)
            self.assertIn('update-ref', [f[0] for f in forms_of(w)])

    def test_a_failed_step_a_raise_a_timeout_and_an_answer_out_of_form(self):
        """TASK-147 AC1: a non-zero exit of any step is git-failed; a process that raises OSError or another Exception
        is git-failed; the stand-in's TimeoutExpired is timeout; an answer whose exit or streams are not of the right
        type is git-failed; no exception escapes capture or restore."""
        for key in ('rev-parse --absolute-git-dir', 'head1', 'read-tree', 'update-index', 'write-tree', 'commit-tree',
                    'diff'):
            r, w = self.refusal(self.scripted(**{key: (1, b'', b'')}))
            self.assertEqual(r['reason'], 'git-failed', key)
        for boom, reason in ((OSError('x'), 'git-failed'), (RuntimeError('x'), 'git-failed'), (TimedOut('x'), 'timeout')):
            r, w = self.refusal(self.scripted(**{'read-tree': boom}))
            self.assertEqual(r['reason'], reason, boom)
            r, w = self.refusal(self.scripted(restore=boom), task_capture.restore, good_restore())
            self.assertEqual(r['reason'], reason, boom)
        for odd in (('1', b'', b''), (0, 'text', b''), (0, b'', None)):
            r, w = self.refusal(self.scripted(**{'write-tree': odd}))
            self.assertEqual(r['reason'], 'git-failed', odd)
        r, w = self.refusal(self.scripted(**{'rev-parse --absolute-git-dir': (0, b'relative\n', b'')}))
        self.assertEqual(r['reason'], 'git-failed')
        r, w = self.refusal(self.scripted(**{'write-tree': (0, b'\xff\n', b'')}))
        self.assertEqual(r['reason'], 'git-failed')

    def test_a_printed_id_that_is_not_forty_lowercase_hex_is_git_failed_and_stops_the_steps_after_it(self):
        """TASK-149 AC2: when write-tree or commit-tree answers with an id that is empty, only a line end, too short,
        too long, upper-case, followed by garbage or not ASCII, capture is refused as git-failed, never as
        invalid-argument, with a finding that names the step and says the id is malformed; no later step is called and
        the reference is not written."""
        bad = (b'', b'\n', b'b' * 39 + b'\n', b'b' * 41 + b'\n', b'B' * 40 + b'\n', b'b' * 40 + b' garbage\n',
               b'b' * 40 + b'x\n', b'\xff' * 40 + b'\n')
        for step in ('write-tree', 'commit-tree'):
            for out in bad:
                r, w = self.refusal(self.scripted(**{step: (0, out, b'')}))
                self.assertEqual(r['reason'], 'git-failed', (step, out))
                self.assertTrue(any(step in f and 'malformed' in f for f in r['findings']), (step, out))
                self.assertEqual(forms_of(w)[-1][0], step, (step, out))
                self.assertNotIn('update-ref', [f[0] for f in forms_of(w)], (step, out))

    def test_a_git_directory_with_a_character_outside_ascii_is_git_failed(self):
        """TASK-149 AC3: when rev-parse --absolute-git-dir answers with exit 0 and an absolute directory that holds a
        character outside ASCII (as UTF-8 bytes with a line end), capture is refused as git-failed, as the docstring
        says, and no read-tree or any later step is called."""
        answer = (0, (GITDIR + 'é\n').encode('utf-8'), b'')
        r, w = self.refusal(self.scripted(**{'rev-parse --absolute-git-dir': answer}))
        self.assertEqual(r['reason'], 'git-failed')
        self.assertEqual([f[0] for f in forms_of(w)], ['rev-parse'])

    def test_a_refused_step_stops_the_steps_after_it(self):
        """TASK-147 AC1: after a refusal no later form is called (the module neither continues nor undoes)."""
        r, w = self.refusal(self.scripted(**{'write-tree': (1, b'', b'')}))
        self.assertEqual([f[0] for f in forms_of(w)][-1], 'write-tree')


class Restore(unittest.TestCase):
    def test_restore_and_clean_act_on_exactly_the_paths_of_their_classes(self):
        """TASK-147 AC1 and AC4: a modified or deleted path goes to restore --source=HEAD --worktree, an added path to
        clean -f, never -d and never -x; the environment of both has no index file; an empty class gives no call."""
        with World() as w:
            task_capture.restore(**good_restore())
        forms = forms_of(w)
        self.assertEqual(forms[0], ['restore', '--source=HEAD', '--worktree', '--', 'a.txt', 'src/b.py'])
        self.assertEqual(forms[1], ['clean', '-f', '--', 'new/dir/c.txt'])
        for form in forms:
            self.assertNotIn('-d', form)
            self.assertNotIn('-x', form)
        self.assertTrue(all('GIT_INDEX_FILE' not in kw['env'] for argv, kw in w.sub.calls))
        with World() as w:
            task_capture.restore(**good_restore(paths=['a.txt'], classes={'a.txt': 'modified'}))
        self.assertEqual([f[0] for f in forms_of(w)], ['restore'])
        with World() as w:
            task_capture.restore(**good_restore(paths=['n.txt'], classes={'n.txt': 'added'}))
        self.assertEqual([f[0] for f in forms_of(w)], ['clean'])

    def test_a_refused_restore_does_not_run_the_clean(self):
        """TASK-147 AC1: when restore --source=HEAD fails, clean is not called and the refusal is git-failed."""
        def responder(form, kwargs):
            return (1, b'', b'') if form[0] == 'restore' else default_answer(form, kwargs)
        with World(responder) as w:
            r = task_capture.restore(**good_restore())
        self.assertEqual((r['result'], r['reason']), ('refused', 'git-failed'))
        self.assertEqual([f[0] for f in forms_of(w)], ['restore'])


class Identity(unittest.TestCase):
    def test_the_test_identity_holds_no_at_sign_and_no_address(self):
        """TASK-147 AC6: the identity of these tests has an e-mail value with no at sign at all (git accepts one), so no
        address and no host name appears in an added line."""
        self.assertNotIn(chr(64), IDENTITY['email'])
        self.assertIsNone(re.search(r'[A-Za-z0-9._%+-]+' + chr(64) + r'[A-Za-z0-9.-]+', HERE.read_bytes().decode('utf-8')))


if __name__ == '__main__':
    unittest.main()

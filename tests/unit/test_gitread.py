"""Unit tests of aieos_bootstrap.gitread (task TASK-024, its rules R1 to R6); every rule has at least one passing case
and one failing case. The process call is replaced by a stand-in that records its calls, so no git starts here. Each
test names the criteria it stands for in its own docstring."""

import ast
import os
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import gitread

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / 'src' / 'aieos_bootstrap'
REPO = str(ROOT)
GOODPATH = os.pathsep.join([str(ROOT), str(SRC)])
A = 'a' * 40
B = 'b' * 40
C = 'c' * 64
DIFF = ['diff-tree', '--no-commit-id', '--name-only', '-r', '--no-renames', '--no-ext-diff', '--no-textconv', '-z',
        '--root']
FORMS = [
    ['rev-parse', '--verify', '--end-of-options', A],
    ['rev-parse', '--verify', '--end-of-options', 'HEAD'],
    ['cat-file', '-p', A],
    ['cat-file', '-t', C],
    ['rev-list', '--parents', '-n', '1', A],
    DIFF + [A],
]


class Done:
    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class StandIn:
    """Records every call; returns a completed process, or raises the exception it was given."""

    def __init__(self, result=None, raises=None):
        self.calls = []
        self.result = result if result is not None else Done(0, b'out', b'')
        self.raises = raises

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.raises is not None:
            raise self.raises
        return self.result


def call(args, repo=REPO, timeout=30, stand_in=None, own_path=True):
    """run with the stand-in; unless own_path is False, with PATH set to absolute entries for the call (erratum E1)."""
    s = stand_in or StandIn()
    with mock.patch.object(gitread.subprocess, 'run', s):
        if own_path:
            with mock.patch.dict(os.environ, {'PATH': GOODPATH}):
                r = gitread.run(repo, args, timeout)
        else:
            r = gitread.run(repo, args, timeout)
    return r, s


def commit_bytes(parents=(A,), message='Subject\n\nBody line.\n', extra=''):
    head = 'tree %s\n' % B + ''.join('parent %s\n' % p for p in parents)
    head += 'author Tester <tester> 1700000000 +0000\ncommitter Tester <tester> 1700000000 +0000\n' + extra
    return (head + '\n' + message).encode('utf-8')


class PinnedForms(unittest.TestCase):
    def test_each_pinned_form_starts_one_process(self):
        """TASK-024 AC1 and TASK-024 AC12: each of the six pinned forms is accepted and calls the process function
        once."""
        for f in FORMS:
            r, s = call(list(f))
            self.assertEqual(len(s.calls), 1, f)
            self.assertIsNone(r['error'], f)

    def test_every_other_form_is_refused_before_any_process(self):
        """TASK-024 AC1, TASK-024 AC3 and TASK-024 AC12: a fifth subcommand, an extra or missing option, a ref name
        other than HEAD, an option-like or uppercase object name, an empty or non-list args and a non-string element are
        refused, with no call to the process function."""
        bad = [
            ['log'], ['commit', '-m', 'x'], ['show', A], [],
            ['rev-parse', '--verify', '--end-of-options', 'main'],
            ['rev-parse', '--verify', A],
            ['rev-parse', '--verify', '--end-of-options', A, '--all'],
            ['cat-file', '-p', '--batch'], ['cat-file', '-e', A], ['cat-file', '-p', A.upper()],
            ['cat-file', '-p', A[:39]], ['cat-file', '-p', 'a' * 41], ['cat-file', '-p', 'a' * 63],
            ['cat-file', '-p', 'a' * 65], ['cat-file', '-p', A + '\n'], ['cat-file', '-p', 'HEAD'],
            ['cat-file', '-t', 'HEAD'], ['rev-list', '--parents', '-n', '1', 'HEAD'],
            ['cat-file', '-p', A, A],
            ['rev-list', '--parents', '-n', '2', A], ['rev-list', '--all'],
            DIFF[:-1] + [A], DIFF + ['--', A], DIFF + ['HEAD'], ['diff-tree', '-p', A],
            ['cat-file', '-p', 1],
        ]
        for b in bad:
            r, s = call(b)
            self.assertEqual(s.calls, [], b)
            self.assertEqual((r['exit'], r['out'], r['err']), (None, b'', b''), b)
            self.assertTrue(r['error'], b)
        r, s = call(tuple(FORMS[2]))
        self.assertEqual(s.calls, [])
        self.assertIn('args', r['error'])

    def test_subclasses_are_refused(self):
        """TASK-024 AC1 and TASK-024 AC12: a list subclass whose iteration differs from its indexing, a str subclass
        among the args, a str subclass as repo and an int subclass as timeout are refused with no call; the exact
        types pass."""

        class Shifty(list):
            def __iter__(self):
                return iter(['log', '--output=x'])

        class S(str):
            pass

        class N(int):
            pass

        for args, repo, timeout in ((Shifty(FORMS[2]), REPO, 30), ([S('cat-file'), '-p', A], REPO, 30),
                                    (list(FORMS[2]), S(REPO), 30), (list(FORMS[2]), REPO, N(30))):
            r, s = call(args, repo=repo, timeout=timeout)
            self.assertEqual(s.calls, [], (args, repo, timeout))
            self.assertTrue(r['error'])
        r, s = call(list(FORMS[2]), repo=REPO, timeout=30)
        self.assertEqual(len(s.calls), 1)

    def test_repo_and_timeout_out_of_range_are_refused(self):
        """TASK-024 AC1 and TASK-024 AC12: a relative repo, a repo that is not a directory, and a timeout of 0, below 0,
        above 120, a boolean or a string are refused with no call; 120 and a fraction are accepted."""
        for repo, why in (('src', 'repo is not an absolute path'), ('', 'repo is not an absolute path'),
                          (None, 'repo is not an absolute path'),
                          (str(ROOT / 'no-such-folder'), 'repo is not an existing directory'),
                          (str(SRC / 'gitread.py'), 'repo is not an existing directory')):
            r, s = call(FORMS[2], repo=repo)
            self.assertEqual(s.calls, [], repo)
            self.assertEqual(r['error'], why, repo)
        for t in (0, -1, 120.5, 121, True, '30', None, float('nan')):
            r, s = call(FORMS[2], timeout=t)
            self.assertEqual(s.calls, [], t)
            self.assertIn('timeout', r['error'])
        for t in (120, 0.5, 1):
            r, s = call(FORMS[2], timeout=t)
            self.assertEqual(len(s.calls), 1, t)

    def test_form_error_names_the_failing_part(self):
        """TASK-024 AC1 and TASK-024 AC3: the refusal names what failed, and a pinned form has no error."""
        self.assertIsNone(gitread.form_error(REPO, FORMS[0], 30))
        self.assertIn('subcommand', gitread.form_error(REPO, ['log'], 30))
        self.assertIn('fixed form of cat-file', gitread.form_error(REPO, ['cat-file', '-x', A], 30))


class TheProcess(unittest.TestCase):
    def test_argument_list_keywords_and_environment(self):
        """TASK-024 AC2 and TASK-024 AC12: the stand-in receives exactly the argument list, the keyword arguments and
        the environment of AC2."""
        env = {'PATH': GOODPATH, 'SYSTEMROOT': 'C:\\Windows', 'GIT_DIR': '/elsewhere', 'GIT_WORK_TREE': '/w',
               'GIT_EXEC_PATH': '/x', 'HOME': '/h', 'GIT_SSH_COMMAND': 'x'}
        with mock.patch.dict(os.environ, env, clear=True):
            r, s = call(['cat-file', '-p', A], timeout=7)
        self.assertEqual(len(s.calls), 1)
        args, kwargs = s.calls[0]
        self.assertEqual(args, (['git', '--no-pager', '-c', 'core.fsmonitor=false', '-c',
                                 'core.hooksPath=' + os.devnull, '-c', 'diff.external=', '-c', 'core.pager=cat', '-C',
                                 REPO, 'cat-file', '-p', A],))
        self.assertEqual(set(kwargs), {'shell', 'stdin', 'capture_output', 'cwd', 'timeout', 'check', 'env'})
        self.assertIs(kwargs['shell'], False)
        self.assertIs(kwargs['stdin'], gitread.subprocess.DEVNULL)
        self.assertIs(kwargs['capture_output'], True)
        self.assertEqual(kwargs['cwd'], REPO)
        self.assertEqual(kwargs['timeout'], 7)
        self.assertIs(kwargs['check'], False)
        self.assertEqual(kwargs['env'], {'PATH': GOODPATH, 'SYSTEMROOT': 'C:\\Windows', 'GIT_CONFIG_NOSYSTEM': '1',
                                         'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_TERMINAL_PROMPT': '0',
                                         'GIT_OPTIONAL_LOCKS': '0', 'GIT_NO_LAZY_FETCH': '1', 'LC_ALL': 'C'})

    def test_planted_keys_never_reach_git(self):
        """TASK-024 AC2, TASK-024 AC7 and TASK-024 AC12: with no SYSTEMROOT, SYSTEMROOT is absent; a planted GIT_DIR,
        GIT_WORK_TREE, GIT_EXEC_PATH or HOME is not passed on; GIT_NO_LAZY_FETCH is always "1"."""
        with mock.patch.dict(os.environ, {'PATH': GOODPATH, 'GIT_DIR': '/elsewhere', 'HOME': '/h',
                                          'GIT_WORK_TREE': '/w', 'GIT_EXEC_PATH': '/x', 'GIT_NO_LAZY_FETCH': '0'},
                             clear=True):
            r, s = call(['rev-parse', '--verify', '--end-of-options', 'HEAD'])
        env = s.calls[0][1]['env']
        self.assertNotIn('SYSTEMROOT', env)
        for k in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_EXEC_PATH', 'HOME'):
            self.assertNotIn(k, env)
        self.assertEqual(env['GIT_NO_LAZY_FETCH'], '1')
        self.assertEqual(sorted(env), sorted(['PATH', 'GIT_CONFIG_NOSYSTEM', 'GIT_CONFIG_GLOBAL', 'GIT_TERMINAL_PROMPT',
                                              'GIT_OPTIONAL_LOCKS', 'GIT_NO_LAZY_FETCH', 'LC_ALL']))

    def test_path_with_an_empty_or_relative_entry_is_refused(self):
        """TASK-024 AC2 and TASK-024 AC12 (erratum E1, decision D-580): no PATH (so the empty string), an empty PATH, a
        PATH with an empty entry and one with a relative entry are refused with no call; a PATH of absolute entries
        passes, and environment() still gives the empty string when PATH is absent."""
        for path in (None, '', GOODPATH + os.pathsep, os.pathsep + GOODPATH, GOODPATH + os.pathsep + 'bin',
                     'bin', '.'):
            env = {} if path is None else {'PATH': path}
            with mock.patch.dict(os.environ, env, clear=True):
                if path is None:
                    self.assertEqual(gitread.environment()['PATH'], '')
                r, s = call(FORMS[2], own_path=False)
            self.assertEqual(s.calls, [], path)
            self.assertEqual(r, {'exit': None, 'out': b'', 'err': b'', 'error': 'PATH has an empty or relative entry'},
                             path)
        with mock.patch.dict(os.environ, {'PATH': GOODPATH}, clear=True):
            r, s = call(FORMS[2], own_path=False)
        self.assertEqual(len(s.calls), 1)
        self.assertIsNone(gitread.path_error(GOODPATH))

    def test_the_checked_environment_is_the_one_passed(self):
        """TASK-024 AC2 and TASK-024 AC12 (erratum E1): the PATH that is checked is the one of the mapping passed to git,
        not a second read of the process environment."""
        bad = {'PATH': 'bin', 'GIT_CONFIG_NOSYSTEM': '1'}
        with mock.patch.dict(os.environ, {'PATH': GOODPATH}, clear=True):
            with mock.patch.object(gitread, 'environment', return_value=bad):
                r, s = call(FORMS[2], own_path=False)
        self.assertEqual(s.calls, [])
        self.assertEqual(r['error'], 'PATH has an empty or relative entry')
        good = dict(gitread.environment(), PATH=GOODPATH)
        with mock.patch.dict(os.environ, {'PATH': 'bin'}, clear=True):
            with mock.patch.object(gitread, 'environment', return_value=good):
                r, s = call(FORMS[2], own_path=False)
        self.assertEqual(len(s.calls), 1)
        self.assertIs(s.calls[0][1]['env'], good)

    def test_more_path_entries(self):
        """TASK-024 AC2 and TASK-024 AC12 (erratum E1): an empty entry between two absolute ones and a drive-relative
        entry are refused on both platforms; a UNC entry is absolute on Windows and not on POSIX."""
        refused = 'PATH has an empty or relative entry'
        for path in (os.pathsep.join([str(ROOT), '', str(SRC)]), 'C:bin'):
            self.assertEqual(gitread.path_error(path), refused, path)
        unc = '\\\\server\\share\\bin'
        self.assertEqual(gitread.path_error(unc), None if os.name == 'nt' else refused)

    def test_diff_tree_carries_its_closing_options(self):
        """TASK-024 AC1 and TASK-024 AC2: diff-tree's fixed form carries --no-ext-diff and --no-textconv, and the call
        carries --no-pager, core.pager=cat, core.fsmonitor=false, core.hooksPath and an empty diff.external."""
        r, s = call(DIFF + [A])
        argv = s.calls[0][0][0]
        for o in ('--no-ext-diff', '--no-textconv', '--no-pager', 'core.pager=cat', 'core.fsmonitor=false',
                  'core.hooksPath=' + os.devnull, 'diff.external='):
            self.assertIn(o, argv)
        self.assertLess(argv.index('-C'), argv.index('diff-tree'))


class TheResult(unittest.TestCase):
    def test_completed_and_non_zero(self):
        """TASK-024 AC3 and TASK-024 AC12: a completed call gives its exit code and bytes, with error None, also for a
        non-zero exit; the keys are exactly exit, out, err and error."""
        r, s = call(FORMS[2], stand_in=StandIn(Done(0, b'tree x\n', b'')))
        self.assertEqual(r, {'exit': 0, 'out': b'tree x\n', 'err': b'', 'error': None})
        r, s = call(FORMS[2], stand_in=StandIn(Done(128, b'', b'fatal: bad object')))
        self.assertEqual(r, {'exit': 128, 'out': b'', 'err': b'fatal: bad object', 'error': None})

    def test_timeout_and_oserror(self):
        """TASK-024 AC3 and TASK-024 AC12: a timeout gives error "timeout", and an OSError gives a short English text;
        neither raises, and both give exit None and empty bytes."""
        t = gitread.subprocess.TimeoutExpired(['git'], 1)
        r, s = call(FORMS[2], stand_in=StandIn(raises=t))
        self.assertEqual(r, {'exit': None, 'out': b'', 'err': b'', 'error': 'timeout'})
        r, s = call(FORMS[2], stand_in=StandIn(raises=FileNotFoundError('git')))
        self.assertEqual((r['exit'], r['out'], r['err']), (None, b'', b''))
        self.assertIn('could not be started', r['error'])
        self.assertIn('FileNotFoundError', r['error'])

    def test_other_exceptions_are_not_swallowed(self):
        """TASK-024 AC3: only a timeout and an OSError are turned into results; any other exception of the stand-in
        is not hidden (the failing case of the rule)."""
        with self.assertRaises(ValueError):
            call(FORMS[2], stand_in=StandIn(raises=ValueError('x')))


class CommitParser(unittest.TestCase):
    def test_one_two_and_no_parents(self):
        """TASK-024 AC4 and TASK-024 AC12: commits with one parent, two parents and none parse to their tree, parents,
        author, committer and message."""
        for ps in ((A,), (A, C), ()):
            p = gitread.parse_commit(commit_bytes(parents=ps))
            self.assertIsNone(p['error'])
            self.assertEqual(p['tree'], B)
            self.assertEqual(p['parents'], list(ps))
            self.assertEqual(p['author'], 'Tester <tester> 1700000000 +0000')
            self.assertEqual(p['committer'], 'Tester <tester> 1700000000 +0000')
            self.assertEqual(p['message'], 'Subject\n\nBody line.\n')
            self.assertEqual(sorted(p), ['author', 'committer', 'error', 'message', 'parents', 'trailers', 'tree'])

    def test_trailers_with_and_without(self):
        """TASK-024 AC4 and TASK-024 AC12: the last paragraph's "<key>: <value>" lines are the trailers; a last
        paragraph with any other line gives none, and so does an empty message."""
        m = 'Subject\n\nBody.\n\nAIEOS-Task: TASK-024\nCo-Authored-By: Claude Opus 5.5\n'
        p = gitread.parse_commit(commit_bytes(message=m))
        self.assertEqual(p['trailers'], [['AIEOS-Task', 'TASK-024'], ['Co-Authored-By', 'Claude Opus 5.5']])
        for m in ('Subject\n\nBody.\n', 'Subject\n\nAIEOS-Task: TASK-024\nnot a trailer\n', 'Subject\n\nKey:value\n',
                  'Subject\n\nA key: value\n', ''):
            self.assertEqual(gitread.parse_commit(commit_bytes(message=m))['trailers'], [], m)

    def test_a_one_paragraph_message_yields_its_pairs(self):
        """TASK-024 AC4 and TASK-024 AC12: the contract's rule, pinned (reading R-b): a message whose only paragraph is
        "Key: value" lines yields them as trailers, although git would read the first line as the subject."""
        p = gitread.parse_commit(commit_bytes(message='AIEOS-Task: TASK-024\n'))
        self.assertIsNone(p['error'])
        self.assertEqual(p['trailers'], [['AIEOS-Task', 'TASK-024']])

    def test_further_headers_are_accepted(self):
        """TASK-024 AC4: further header lines after the committer (an encoding line, a signature with continuation
        lines) are accepted and not returned (the implementer's reading)."""
        p = gitread.parse_commit(commit_bytes(extra='encoding UTF-8\ngpgsig signature-start\n line\n signature-end\n'))
        self.assertIsNone(p['error'])
        self.assertEqual(p['message'], 'Subject\n\nBody line.\n')

    def test_malformed_forms(self):
        """TASK-024 AC4 and TASK-024 AC12: non-UTF-8 bytes, a missing tree, author or committer line, a header line out
        of form, a missing empty line and data that are not bytes each give an error and every other key empty."""
        good = commit_bytes()
        cases = [
            b'\xff' + good,
            good.replace(b'tree ' + B.encode() + b'\n', b''),
            good.replace(b'author Tester <tester> 1700000000 +0000\n', b''),
            good.replace(b'committer Tester <tester> 1700000000 +0000\n', b''),
            good.replace(b'tree ' + B.encode(), b'tree xyz'),
            good.replace(b'parent ' + A.encode(), b'parent ' + A.upper().encode()),
            good.replace(b'author Tester', b'Author Tester'),
            commit_bytes(extra='Bad-Key value\n'),
            commit_bytes(extra='nospace\n'),
            commit_bytes(extra='parent ' + A + '\n'),
            commit_bytes(extra=' a continuation line with no header before it\n'),
            b'tree ' + B.encode() + b'\nauthor x\ncommitter y\n',
            good.replace(b'author Tester <tester> 1700000000 +0000', b'author '),
            'not bytes',
        ]
        empty = {'tree': None, 'parents': [], 'author': None, 'committer': None, 'message': '', 'trailers': []}
        for c in cases:
            p = gitread.parse_commit(c)
            self.assertTrue(p['error'], c)
            self.assertEqual({k: v for k, v in p.items() if k != 'error'}, empty, c)


class PathsParser(unittest.TestCase):
    def test_several_one_none(self):
        """TASK-024 AC5 and TASK-024 AC12: several names, one name and none parse in order, with the empty name after
        the last NUL dropped."""
        self.assertEqual(gitread.parse_paths(b'a/b.py\0c d.md\0'), {'paths': ['a/b.py', 'c d.md'], 'error': None})
        self.assertEqual(gitread.parse_paths(b'x\0'), {'paths': ['x'], 'error': None})
        self.assertEqual(gitread.parse_paths(b''), {'paths': [], 'error': None})
        self.assertEqual(gitread.parse_paths('é.md\0'.encode('utf-8')), {'paths': ['é.md'], 'error': None})

    def test_malformed(self):
        """TASK-024 AC5 and TASK-024 AC12: a non-UTF-8 name, an empty name before the last NUL and data that are not
        bytes give paths [] and an error."""
        for d in (b'\xff\0', b'a\0\0b\0', b'\0', 'a\0'):
            p = gitread.parse_paths(d)
            self.assertEqual(p['paths'], [], d)
            self.assertTrue(p['error'], d)


def source(name):
    return (SRC / name).read_bytes().decode('utf-8')


class SingleWrapper(unittest.TestCase):
    def test_imports_and_calls(self):
        """TASK-024 AC6, TASK-024 AC7, TASK-024 AC9 and TASK-024 AC12: the module imports only os, re and subprocess; it
        has no exec, eval, compile, __import__, importlib, open, assert, clock, network or other process call;
        subprocess.run is called once."""
        tree = ast.parse(source('gitread.py'))
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods.update(a.name for a in n.names)
            if isinstance(n, ast.ImportFrom):
                mods.add(n.module)
        self.assertEqual(mods, {'os', 're', 'subprocess'})
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)])
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        for bad in ('exec', 'eval', 'compile', '__import__', 'open', 'importlib', 'time', 'datetime', 'socket', 'pty'):
            self.assertNotIn(bad, names)
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Assert)])
        attrs = [(n.value.id, n.attr) for n in ast.walk(tree)
                 if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)]
        os_attrs = {a for b, a in attrs if b == 'os'}
        self.assertEqual(os_attrs, {'path', 'environ', 'devnull', 'pathsep'})
        self.assertEqual(sorted(a for b, a in attrs if b == 'subprocess'), ['DEVNULL', 'TimeoutExpired', 'run'])
        runs = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == 'run' and isinstance(n.func.value, ast.Name) and n.func.value.id == 'subprocess']
        self.assertEqual(len(runs), 1)
        os_calls = {n.attr for n in ast.walk(tree)
                    if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Attribute)
                    and isinstance(n.value.value, ast.Name) and n.value.value.id == 'os'}
        self.assertEqual(os_calls, {'isabs', 'isdir', 'get'})

    def test_no_other_src_module_imports_subprocess(self):
        """TASK-024 AC6 and TASK-024 AC12: gitread.py is the only module of src/ that imports subprocess (the failing
        case: the check finds gitread itself)."""
        found = []
        for p in sorted((ROOT / 'src').rglob('*.py')):
            tree = ast.parse(p.read_bytes().decode('utf-8'))
            for n in ast.walk(tree):
                if ((isinstance(n, ast.Import) and any(a.name.split('.')[0] == 'subprocess' for a in n.names))
                        or (isinstance(n, ast.ImportFrom) and (n.module or '').split('.')[0] == 'subprocess')):
                    found.append(p.relative_to(ROOT).as_posix())
        self.assertEqual(found, ['src/aieos_bootstrap/gitread.py'])

    def test_the_three_modules_name_their_criteria(self):
        """TASK-024 AC11 and TASK-024 AC12: every test function of the three test modules names "TASK-024 ACn" in its
        own docstring and no other task's criterion in qualified form; the check finds a test without one."""
        def problems(text):
            out = []
            for node in ast.parse(text).body:
                for f in [node] + (list(node.body) if isinstance(node, ast.ClassDef) else []):
                    if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name.startswith('test'):
                        doc = ast.get_docstring(f) or ''
                        if 'TASK-024 AC' not in doc:
                            out.append(f.name)
                        out.extend(f.name for part in doc.split('TASK-')[1:] if part[3:6] == ' AC' and part[:3] != '024')
            return out
        for group, name in (('unit', 'test_gitread.py'), ('property', 'test_gitread_properties.py'),
                            ('integration', 'test_gitread_repo.py')):
            text = (ROOT / 'tests' / group / name).read_bytes().decode('utf-8')
            self.assertEqual(problems(text), [], name)
        self.assertEqual(problems('def test_a():\n    pass\n'), ['test_a'])
        self.assertEqual(problems('def test_b():\n    """TASK-024 AC1 and TASK-025 AC2"""\n'), ['test_b'])

    def test_docstring_and_package(self):
        """TASK-024 AC6 and TASK-024 AC10: the docstring names INV-001's single wrapper, the pinned list and the
        workflow's revision 8, and states the limits; the package lists the module; SUBCOMMANDS is the pinned tuple."""
        doc = ast.get_docstring(ast.parse(source('gitread.py')))
        for s in ('single process wrapper', 'pinned list is [git]', 'revision 8', 'Limits (TASK-024 AC10)',
                  'trusted as the operating system finds it', "repository's own", 'no caller exists yet', 'POSIX only',
                  'not capped in size', 'GIT_NO_LAZY_FETCH'):
            self.assertIn(s, doc)
        self.assertEqual(gitread.SUBCOMMANDS, ('cat-file', 'diff-tree', 'rev-list', 'rev-parse'))
        self.assertIn("'gitread'", source('__init__.py'))


if __name__ == '__main__':
    unittest.main()

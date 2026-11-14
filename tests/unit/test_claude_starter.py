"""Unit tests of aieos_runtime.claude_starter (task TASK-134, the real runtime starter of `aieos launch`), standard
library only. No test starts a process, a runtime or anything else, and no test writes or reads a file of the
repository except this file and the module's own source, with pathlib's read_bytes, for the ast checks: the process
function (the module's `subprocess`), the file functions (the module's `Path`) and the starter's own environment
(os.environ) are stand-ins put in place through mock.patch.object and mock.patch.dict, each restored after its test.
The module's hash constants are replaced by the hashes of stand-in bytes, so no real file is needed. Each test names
its criteria in its own docstring."""

import ast
import hashlib
import ntpath
import os
import pathlib
import types
import unittest
from unittest import mock

from aieos_runtime import claude_starter

HERE = pathlib.Path(__file__).resolve()
MODULE = HERE.parents[2] / 'src' / 'aieos_runtime' / 'claude_starter.py'
ROOT = 'C:\\aieos-root-132'
SESSION = 'sess-132.a_b'
BASE = 'a' * 40
ENV = {'AIEOS_SESSION_ID': SESSION, 'AIEOS_ROOT': ROOT, 'AIEOS_BASE': BASE}
EXE = 'C:\\Users\\Admin\\AppData\\Roaming\\Claude\\claude-code\\2.1.321\\d0e23af87588\\claude.exe'
MCP = 'C:\\Users\\Admin\\AIEOS-runtime\\claude-mcp.json'
SETTINGS = 'C:\\Users\\Admin\\AIEOS-runtime\\claude-settings.json'
EXE_BYTES = b'stand-in bytes of the executable'
MCP_BYTES = b'stand-in bytes of the MCP file'
SETTINGS_BYTES = b'stand-in bytes of the settings file'
PROMPT = ('Call the AIEOS tool get_work_order of the connected aieos MCP server, do the work its Work Order '
          'describes within its limits, and stop when it is done.')
LAUNCHER_VARS = ('AIEOS_SESSION_ID', 'AIEOS_ROOT', 'AIEOS_BASE')
PROCESS_VARS = ('PATH', 'SYSTEMROOT', 'SYSTEMDRIVE', 'COMSPEC', 'PATHEXT', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA',
                'TEMP', 'TMP')
PROCESS = {name: 'value-of-' + name for name in PROCESS_VARS}
# AC6: the variables that must never reach the runtime; a tuple of names, so that no literal pairs a
# credential-like name with a string value (bandit B105 refuses such a pair in a test file)
REFUSED_VARS = ('PYTHONPATH', 'HOME', 'ANTHROPIC_API_KEY', 'GITHUB_TOKEN', 'OTHER')
ARGS = [EXE, '-p', PROMPT, '--permission-prompts', 'none', '--strict-mcp-config', '--mcp-config', MCP, '--settings',
        SETTINGS]
FORBIDDEN_FLAGS = ('--dangerously-skip-permissions', '--allow-dangerously-skip-permissions', '--permission-mode',
                   '--allowedTools', '--tools', '--add-dir', '--setting-sources')


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Timeout(Exception):
    pass


class FakeSubprocess:
    """The module's `subprocess`: records each call of run, never starts anything."""
    DEVNULL = object()
    TimeoutExpired = Timeout

    def __init__(self, returncode=0, timeout=False):
        self.calls = []
        self.returncode = returncode
        self.timeout = timeout

    def run(self, args, **kwargs):
        self.calls.append((list(args), dict(kwargs)))
        if self.timeout:
            raise Timeout('stand-in timeout')
        return types.SimpleNamespace(returncode=self.returncode)


def fake_path(files, others, reads):
    class FakePath:
        def __init__(self, text):
            self.text = str(text)

        @property
        def suffix(self):
            return ntpath.splitext(self.text)[1]

        @property
        def name(self):
            return ntpath.basename(self.text)

        def is_file(self):
            return self.text in files

        def exists(self):
            return self.text in files or self.text in others

        def is_absolute(self):
            return ntpath.isabs(self.text)

        def read_bytes(self):
            reads.append(self.text)
            return files[self.text]

        def __str__(self):
            return self.text

        def __fspath__(self):
            return self.text
    return FakePath


class World:
    """One test's stand-ins. files maps a path to bytes (a regular file), others holds paths that exist but are not
    regular files; the three hash constants of the module are replaced by the hashes of the stand-in bytes unless a
    case gives its own."""

    def __init__(self, files=None, others=(), environ=None, returncode=0, timeout=False, constants=None):
        self.files = {EXE: EXE_BYTES, MCP: MCP_BYTES, SETTINGS: SETTINGS_BYTES} if files is None else dict(files)
        self.others = set(others)
        self.reads = []
        self.sub = FakeSubprocess(returncode, timeout)
        self.environ = dict(PROCESS) if environ is None else dict(environ)
        self.constants = {'EXE_SHA256': sha(EXE_BYTES), 'MCP_SHA256': sha(MCP_BYTES),
                          'SETTINGS_SHA256': sha(SETTINGS_BYTES)}
        self.constants.update({} if constants is None else constants)

    def __enter__(self):
        self.patches = [mock.patch.object(claude_starter, 'subprocess', self.sub),
                        mock.patch.object(claude_starter, 'Path', fake_path(self.files, self.others, self.reads)),
                        mock.patch.dict(os.environ, self.environ, clear=True)]
        self.patches += [mock.patch.object(claude_starter, k, v) for k, v in self.constants.items()]
        for p in self.patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in reversed(self.patches):
            p.stop()
        return False


def run_starter(env=None, **world):
    """The result of starter(env) in a World: (the world, the value returned or None, the exception or None)."""
    with World(**world) as w:
        try:
            return w, claude_starter.starter(dict(ENV) if env is None else env), None
        except claude_starter.StarterError as e:
            return w, None, e


class TASK132AC1Form(unittest.TestCase):
    def test_a_good_env_starts_once_and_returns_none(self):
        """TASK-134 AC1: with the three variables in form, starter(env) returns None and starts the process once."""
        w, value, error = run_starter()
        self.assertEqual((value, error, len(w.sub.calls)), (None, None, 1))

    def test_each_variable_is_required_in_form(self):
        """TASK-134 AC1: a missing, non-str or out-of-form AIEOS_SESSION_ID, AIEOS_ROOT (not absolute) or AIEOS_BASE
        (not exactly 40 lowercase hexadecimal characters) raises StarterError before any process starts."""
        bad = {'AIEOS_SESSION_ID': [None, 5, b'x', '', 'a b', 'a/b', 'a' * 129, 'é'],
               'AIEOS_ROOT': [None, 5, '', 'relative\\dir', 'dir', '.'],
               'AIEOS_BASE': [None, 5, '', 'a' * 39, 'a' * 41, 'A' * 40, 'g' * 40, ' ' + 'a' * 39, 'a' * 40 + '\n']}
        for name, values in bad.items():
            for value in values:
                env = dict(ENV)
                env[name] = value
                w, got, error = run_starter(env)
                self.assertIsInstance(error, claude_starter.StarterError, (name, value))
                self.assertEqual((got, w.sub.calls), (None, []), (name, value))
            env = dict(ENV)
            del env[name]
            w, got, error = run_starter(env)
            self.assertIsInstance(error, claude_starter.StarterError, name)
            self.assertEqual(w.sub.calls, [], name)

    def test_the_longest_and_the_odd_session_forms_are_accepted(self):
        """TASK-134 AC1: AIEOS_SESSION_ID of 1 and of 128 characters over letters, digits, ".", "_" and "-" is
        accepted."""
        for session in ('a', 'A' * 128, '0.9_z-Z'):
            env = dict(ENV)
            env['AIEOS_SESSION_ID'] = session
            w, _, error = run_starter(env)
            self.assertEqual((error, len(w.sub.calls)), (None, 1), session)


class TASK132AC2Executable(unittest.TestCase):
    def test_the_pinned_constants_are_verbatim(self):
        """TASK-134 AC2: EXE_PATH and EXE_SHA256 are the pinned values of the contract, as constant strings."""
        self.assertEqual(claude_starter.EXE_PATH, EXE)
        self.assertEqual(claude_starter.EXE_SHA256, 'e6dae5fc45902b15751f2591a02f51760351c4788c5fd8291b3f1443d40c13a4')

    def test_refusals_of_the_executable(self):
        """TASK-134 AC2: a missing executable, one that is not a regular file and one whose hash differs each raise
        StarterError before any process starts."""
        cases = [
            dict(files={MCP: MCP_BYTES, SETTINGS: SETTINGS_BYTES}),
            dict(files={MCP: MCP_BYTES, SETTINGS: SETTINGS_BYTES}, others={EXE}),
            dict(files={EXE: b'other bytes', MCP: MCP_BYTES, SETTINGS: SETTINGS_BYTES}),
        ]
        for case in cases:
            w, got, error = run_starter(**case)
            self.assertIsInstance(error, claude_starter.StarterError, case)
            self.assertEqual((got, w.sub.calls), (None, []), case)

    def test_cmd_bat_and_other_targets_are_refused_outright(self):
        """TASK-134 AC2: a target ending in .cmd, .bat, .com or nothing is refused even when the file exists and its
        hash is the pinned one."""
        for target in ('C:\\x\\claude.cmd', 'C:\\x\\claude.bat', 'C:\\x\\claude.com', 'C:\\x\\claude', 'C:\\x\\a.EXE.txt'):
            files = {target: EXE_BYTES, MCP: MCP_BYTES, SETTINGS: SETTINGS_BYTES}
            with mock.patch.object(claude_starter, 'EXE_PATH', target):
                w, got, error = run_starter(files=files)
            self.assertIsInstance(error, claude_starter.StarterError, target)
            self.assertEqual(w.sub.calls, [], target)

    def test_no_search_and_no_expansion(self):
        """TASK-134 AC2: the module names no PATH search, no user-directory expansion and no variable expansion
        (which, expanduser, expandvars, getenv), as a name or an attribute."""
        tree = ast.parse(MODULE.read_bytes().decode('utf-8'))
        used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        used |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        self.assertEqual(used & {'which', 'expanduser', 'expandvars', 'getenv', 'getenvb', 'shell'}, set())


class TASK132AC3Arguments(unittest.TestCase):
    def test_the_argument_list_is_exact(self):
        """TASK-134 AC3: the process is started with exactly the ten-element list of the contract, in order."""
        w, _, error = run_starter()
        self.assertIsNone(error)
        self.assertEqual(w.sub.calls[0][0], ARGS)

    def test_the_prompt_follows_dash_p_and_never_the_variadic_option(self):
        """TASK-134 AC3: the prompt is the element right after "-p" and does not follow "--mcp-config"; the value of
        "--mcp-config" is the MCP file and of "--settings" the settings file."""
        args = run_starter()[0].sub.calls[0][0]
        self.assertEqual(args[args.index('-p') + 1], claude_starter.PROMPT)
        self.assertEqual(args.index('-p') + 1, 2)
        self.assertLess(args.index('-p'), args.index('--mcp-config'))
        self.assertEqual(args[args.index('--mcp-config') + 1], MCP)
        self.assertEqual(args[args.index('--settings') + 1], SETTINGS)
        self.assertNotEqual(args[args.index('--mcp-config') + 2:][:1], [claude_starter.PROMPT])

    def test_no_option_that_widens_permissions(self):
        """TASK-134 AC3: none of --dangerously-skip-permissions, --allow-dangerously-skip-permissions,
        --permission-mode, --allowedTools, --tools, --add-dir and --setting-sources is in the list."""
        args = run_starter()[0].sub.calls[0][0]
        self.assertEqual(set(args) & set(FORBIDDEN_FLAGS), set())
        self.assertEqual(args[args.index('--permission-prompts') + 1], 'none')

    def test_the_runtime_file_constants_are_verbatim(self):
        """TASK-134 AC3: MCP_FILE, MCP_SHA256, SETTINGS_FILE and SETTINGS_SHA256 are the pinned values."""
        self.assertEqual((claude_starter.MCP_FILE, claude_starter.SETTINGS_FILE), (MCP, SETTINGS))
        self.assertEqual(claude_starter.MCP_SHA256,
                         'cbfc039cd668ca362c5713ad5498a3c18eeca7a59505363756e303c81035f882')
        self.assertEqual(claude_starter.SETTINGS_SHA256,
                         'bb9c8724b7e24955f07ea185b045008adcf313dfe9ecc9268a3023c9e75bf26b')

    def test_refusals_of_the_runtime_files(self):
        """TASK-134 AC3: a missing, non-regular or hash-differing MCP file or settings file each raises StarterError
        before any process starts."""
        for path in (MCP, SETTINGS):
            keep = {EXE: EXE_BYTES, MCP: MCP_BYTES, SETTINGS: SETTINGS_BYTES}
            missing = {k: v for k, v in keep.items() if k != path}
            differs = dict(keep)
            differs[path] = b'other bytes'
            for case in (dict(files=missing), dict(files=missing, others={path}), dict(files=differs)):
                w, got, error = run_starter(**case)
                self.assertIsInstance(error, claude_starter.StarterError, (path, case))
                self.assertEqual((got, w.sub.calls), (None, []), (path, case))


class TASK132AC4Prompt(unittest.TestCase):
    def test_the_prompt_is_one_constant_string(self):
        """TASK-134 AC4: PROMPT is exactly the sentence of the contract, and it is a module constant bound to a
        string literal."""
        self.assertEqual(claude_starter.PROMPT, PROMPT)
        tree = ast.parse(MODULE.read_bytes().decode('utf-8'))
        bound = [n for n in tree.body if isinstance(n, ast.Assign) and [t.id for t in n.targets
                                                                         if isinstance(t, ast.Name)] == ['PROMPT']]
        self.assertEqual(len(bound), 1)
        self.assertIsInstance(bound[0].value, ast.Constant)

    def test_no_file_is_read_for_the_prompt(self):
        """TASK-134 AC4 and AC5: the only files read are the three of the contract, once each."""
        w, _, error = run_starter()
        self.assertIsNone(error)
        self.assertEqual(sorted(w.reads), sorted([EXE, MCP, SETTINGS]))


class TASK132AC5Process(unittest.TestCase):
    def test_the_process_form(self):
        """TASK-134 AC5: shell False, stdin the process module's DEVNULL, the working directory AIEOS_ROOT, timeout
        the integer 6600, and no capture of output (no stdout, stderr or capture_output keyword)."""
        w, _, _ = run_starter()
        kwargs = w.sub.calls[0][1]
        self.assertIs(kwargs['shell'], False)
        self.assertIs(kwargs['stdin'], w.sub.DEVNULL)
        self.assertEqual(kwargs['cwd'], ROOT)
        self.assertEqual((kwargs['timeout'], type(kwargs['timeout'])), (6600, int))
        self.assertEqual(set(kwargs) & {'stdout', 'stderr', 'capture_output', 'input', 'text', 'preexec_fn'}, set())
        self.assertLessEqual(set(kwargs), {'shell', 'stdin', 'cwd', 'timeout', 'env', 'check'})

    def test_a_timeout_raises(self):
        """TASK-134 AC5: a timeout of the process (its termination is the process function's) raises StarterError."""
        w, got, error = run_starter(timeout=True)
        self.assertIsInstance(error, claude_starter.StarterError)
        self.assertEqual((got, len(w.sub.calls)), (None, 1))

    def test_a_non_zero_exit_raises_and_zero_returns_none(self):
        """TASK-134 AC5: a non-zero exit code raises StarterError; exit code 0 returns None."""
        for code in (1, 2, 255, -1):
            _, got, error = run_starter(returncode=code)
            self.assertIsInstance(error, claude_starter.StarterError, code)
            self.assertIsNone(got)
        _, got, error = run_starter(returncode=0)
        self.assertEqual((got, error), (None, None))


class TASK132AC6Environment(unittest.TestCase):
    def test_the_constant_lists(self):
        """TASK-134 AC6: the two environment lists are module constants equal to the contract's lists."""
        self.assertEqual(tuple(claude_starter.ENV_FROM_LAUNCHER), LAUNCHER_VARS)
        self.assertEqual(tuple(claude_starter.ENV_FROM_PROCESS), PROCESS_VARS)

    def test_the_environment_passed_is_exactly_the_lists(self):
        """TASK-134 AC6: the environment passed to the process holds the three launcher variables and the listed
        variables of the starter's own environment that are present, with their values, and nothing else."""
        environ = dict(PROCESS)
        environ.update({name: 'v-' + name for name in REFUSED_VARS})
        w, _, error = run_starter(environ=environ)
        self.assertIsNone(error)
        want = dict(ENV)
        want.update(PROCESS)
        self.assertEqual(w.sub.calls[0][1]['env'], want)

    def test_an_absent_listed_variable_is_left_out_but_path_is_required(self):
        """TASK-134 AC6: a listed variable other than PATH that is absent is not passed; without PATH the starter
        raises StarterError before any process starts."""
        environ = {k: v for k, v in PROCESS.items() if k not in ('SYSTEMROOT', 'TMP')}
        w, _, error = run_starter(environ=environ)
        self.assertIsNone(error)
        self.assertEqual(set(w.sub.calls[0][1]['env']), set(LAUNCHER_VARS) | (set(PROCESS_VARS) - {'SYSTEMROOT', 'TMP'}))
        without = {k: v for k, v in PROCESS.items() if k != 'PATH'}
        w, got, error = run_starter(environ=without)
        self.assertIsInstance(error, claude_starter.StarterError)
        self.assertEqual((got, w.sub.calls), (None, []))

    def test_extra_launcher_variables_are_not_passed(self):
        """TASK-134 AC6: a key of the launcher's env beyond the three is not passed."""
        env = dict(ENV)
        env['AIEOS_EXTRA'] = 'x'
        w, _, error = run_starter(env)
        self.assertIsNone(error)
        self.assertNotIn('AIEOS_EXTRA', w.sub.calls[0][1]['env'])


class TASK132AC7NoCore(unittest.TestCase):
    def test_the_import_list(self):
        """TASK-134 AC7: the module imports no aieos_bootstrap module at all, and only hashlib, ntpath, os, pathlib, re
        and subprocess of the standard library."""
        tree = ast.parse(MODULE.read_bytes().decode('utf-8'))
        names = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                names.update(a.name for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                names.add(n.module or '')
        self.assertEqual({x.split('.')[0] for x in names} - {'hashlib', 'ntpath', 'os', 'pathlib', 're',
                                                              'subprocess'}, set())
        self.assertFalse([x for x in names if x.split('.')[0] == 'aieos_bootstrap'])

    def test_the_module_reaches_no_core_name(self):
        """TASK-134 AC7: the module names none of governor, reconcile, done, writer, execution, records or
        evaluation."""
        tree = ast.parse(MODULE.read_bytes().decode('utf-8'))
        used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        used |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        self.assertEqual(used & {'governor', 'reconcile', 'done', 'writer', 'execution', 'records', 'evaluation'},
                         set())

    def test_the_one_public_function(self):
        """TASK-134 AC7: the module holds the one public function starter (every other function is private, its name
        begins with an underscore)."""
        tree = ast.parse(MODULE.read_bytes().decode('utf-8'))
        public = [n.name for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')]
        self.assertEqual(public, ['starter'])


class TASK132AC9ThisFile(unittest.TestCase):
    def test_this_test_file(self):
        """TASK-134 AC9: this file imports no tempfile, sqlite3, shutil or subprocess, names no open, compile, exec,
        eval or input, and has no one-argument .replace() and no .replace(target=...)."""
        tree = ast.parse(HERE.read_bytes().decode('utf-8'))
        imported = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imported.update(a.name.split('.')[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                imported.add((n.module or '').split('.')[0])
        self.assertEqual(imported & {'tempfile', 'sqlite3', 'shutil', 'subprocess'}, set())
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertEqual(names & {'open', 'compile', 'exec', 'eval', 'input'}, set())
        replaces = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == 'replace' and (len(n.args) == 1 or [k.arg for k in n.keywords] == ['target'])]
        self.assertEqual(replaces, [])

    def test_every_test_names_its_criteria(self):
        """TASK-134 AC9: every test function of this module names "TASK-134 AC" in its own docstring, more than 15
        in all."""
        tree = ast.parse(HERE.read_bytes().decode('utf-8'))
        tests = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
        self.assertGreater(len(tests), 15)
        for node in tests:
            self.assertIn('TASK-134 AC', ast.get_docstring(node) or '', node.name)


if __name__ == '__main__':
    unittest.main()

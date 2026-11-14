"""Property tests of aieos_runtime.claude_starter (task TASK-132, AC1, AC2, AC3, AC5 and AC6), standard library only,
with fixed seeds. For random values, an input out of form by construction never starts a process and the starter raises
StarterError; an input in form starts the process once, returns no value and passes an environment that is a subset of
the contract's lists, with the values of its sources; a stand-in file whose bytes differ from the pinned ones is
refused. The process function, the file functions and the environment are stand-ins put in place through mock.patch;
no process starts and no file is read or written. Each test names its criteria in its own docstring."""

import hashlib
import ntpath
import os
import random
import types
import unittest
from unittest import mock

from aieos_runtime import claude_starter

SEEDS = (1, 2, 3, 5, 8, 13, 21, 34)
ROUNDS = 25
EXE = claude_starter.EXE_PATH
MCP = claude_starter.MCP_FILE
SETTINGS = claude_starter.SETTINGS_FILE
GOOD_BYTES = {EXE: b'exe stand-in', MCP: b'mcp stand-in', SETTINGS: b'settings stand-in'}
HEXD = '0123456789abcdef'
SESSION_CHARS = 'abcxyzABCXYZ0189._-'
BAD_CHARS = ' /\\:*?"<>|\n\t\x00éß'
LAUNCHER_VARS = ('AIEOS_SESSION_ID', 'AIEOS_ROOT', 'AIEOS_BASE')
PROCESS_VARS = ('PATH', 'SYSTEMROOT', 'SYSTEMDRIVE', 'COMSPEC', 'PATHEXT', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA',
                'TEMP', 'TMP')
# AC6: the variables that must never reach the runtime; a tuple of names, as in the unit tests (bandit B105)
REFUSED_VARS = ('API_KEY', 'GH_TOKEN', 'PYTHONPATH', 'HOME', 'ANTHROPIC_API_KEY')


class Timeout(Exception):
    pass


class Sub:
    DEVNULL = object()
    TimeoutExpired = Timeout

    def __init__(self):
        self.calls = []

    def run(self, args, **kwargs):
        self.calls.append((list(args), dict(kwargs)))
        return types.SimpleNamespace(returncode=0)


def fake_path(files):
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
            return self.text in files

        def is_absolute(self):
            return ntpath.isabs(self.text)

        def read_bytes(self):
            return files[self.text]

        def __str__(self):
            return self.text

        def __fspath__(self):
            return self.text
    return FakePath


def sha(data):
    return hashlib.sha256(data).hexdigest()


def launch(env, environ, files=None):
    """starter(env) with the stand-ins in place: (the process stand-in, the value returned, the exception or None)."""
    files = dict(GOOD_BYTES) if files is None else files
    sub = Sub()
    patches = [mock.patch.object(claude_starter, 'subprocess', sub),
               mock.patch.object(claude_starter, 'Path', fake_path(files)),
               mock.patch.dict(os.environ, environ, clear=True),
               mock.patch.object(claude_starter, 'EXE_SHA256', sha(GOOD_BYTES[EXE])),
               mock.patch.object(claude_starter, 'MCP_SHA256', sha(GOOD_BYTES[MCP])),
               mock.patch.object(claude_starter, 'SETTINGS_SHA256', sha(GOOD_BYTES[SETTINGS]))]
    for p in patches:
        p.start()
    try:
        return sub, claude_starter.starter(env), None
    except claude_starter.StarterError as e:
        return sub, None, e
    finally:
        for p in reversed(patches):
            p.stop()


def good_session(rng):
    return ''.join(rng.choice(SESSION_CHARS) for _ in range(rng.randrange(1, 129)))


def good_root(rng):
    return 'C:\\' + ''.join(rng.choice('abcxyz019_-') for _ in range(rng.randrange(1, 12)))


def good_base(rng):
    return ''.join(rng.choice(HEXD) for _ in range(40))


def good_env(rng):
    return {'AIEOS_SESSION_ID': good_session(rng), 'AIEOS_ROOT': good_root(rng), 'AIEOS_BASE': good_base(rng)}


def good_environ(rng):
    return {name: 'v%d-%s' % (rng.randrange(1000), name) for name in PROCESS_VARS if name == 'PATH' or rng.random() < 0.8}


def bad_value(rng, name):
    """A value out of form by construction for the variable."""
    kind = rng.randrange(4)
    if kind == 0:
        return rng.choice([None, 5, 3.5, b'x', ['a'], ('a',), {'a': 1}, True])
    if name == 'AIEOS_SESSION_ID':
        if kind == 1:
            return ''
        if kind == 2:
            return good_session(rng)[:5] + rng.choice(BAD_CHARS) + 'b'
        return 'a' * rng.randrange(129, 200)
    if name == 'AIEOS_ROOT':
        if kind == 1:
            return ''
        return rng.choice(['rel', 'a\\b', '.', '..\\x', 'x:y']) + rng.choice(['', 'q', '1'])
    if kind == 1:
        return ''.join(rng.choice(HEXD) for _ in range(rng.choice([0, 1, 39, 41, 64])))
    if kind == 2:
        s = list(good_base(rng))
        s[rng.randrange(40)] = rng.choice('ABCDEFGHxyz -')
        return ''.join(s)
    return good_base(rng) + rng.choice(['\n', ' ', 'a'])


class TASK132PropertiesInput(unittest.TestCase):
    def test_a_refused_input_never_starts_a_process(self):
        """TASK-132 AC1: for random env values with one of the three variables missing or out of form by
        construction, the starter raises StarterError, returns no value and starts no process."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                env = good_env(rng)
                name = rng.choice(LAUNCHER_VARS)
                if rng.random() < 0.3:
                    del env[name]
                else:
                    env[name] = bad_value(rng, name)
                sub, value, error = launch(env, good_environ(rng))
                self.assertIsInstance(error, claude_starter.StarterError, (seed, name, env))
                self.assertEqual((value, sub.calls), (None, []), (seed, name, env))

    def test_an_input_in_form_starts_once_and_returns_none(self):
        """TASK-132 AC1 and AC5: for random env values in form, the process starts once, the starter returns None
        and the working directory is the env's AIEOS_ROOT."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                env = good_env(rng)
                sub, value, error = launch(env, good_environ(rng))
                self.assertEqual((value, error, len(sub.calls)), (None, None, 1), (seed, env))
                self.assertEqual(sub.calls[0][1]['cwd'], env['AIEOS_ROOT'])


class TASK132PropertiesEnvironment(unittest.TestCase):
    def test_the_environment_passed_is_a_subset_of_the_lists(self):
        """TASK-132 AC6: for random starter environments, with other names added (credentials included), the
        environment passed is a subset of the contract's lists and holds the values of its sources."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                env = good_env(rng)
                environ = good_environ(rng)
                extra = {name: 'v' for name in REFUSED_VARS}
                extra['EXTRA_%d' % rng.randrange(100)] = 'x'
                sub, _, error = launch(env, dict(environ, **extra))
                self.assertIsNone(error)
                passed = sub.calls[0][1]['env']
                self.assertLessEqual(set(passed), set(LAUNCHER_VARS) | set(PROCESS_VARS))
                for name in LAUNCHER_VARS:
                    self.assertEqual(passed[name], env[name])
                for name in PROCESS_VARS:
                    if name in environ:
                        self.assertEqual(passed[name], environ[name])
                    else:
                        self.assertNotIn(name, passed)

    def test_no_path_means_no_process(self):
        """TASK-132 AC6: for random starter environments without PATH, the starter raises StarterError and starts no
        process."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                environ = good_environ(rng)
                del environ['PATH']
                sub, value, error = launch(good_env(rng), environ)
                self.assertIsInstance(error, claude_starter.StarterError, seed)
                self.assertEqual((value, sub.calls), (None, []), seed)


class TASK132PropertiesFiles(unittest.TestCase):
    def test_bytes_that_differ_are_refused(self):
        """TASK-132 AC2 and AC3: for random one-byte changes and random other bytes of the executable, the MCP file
        or the settings file, the starter raises StarterError and starts no process."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                path = rng.choice([EXE, MCP, SETTINGS])
                data = bytearray(GOOD_BYTES[path])
                if rng.random() < 0.5:
                    data[rng.randrange(len(data))] ^= rng.randrange(1, 256)
                    changed = bytes(data)
                else:
                    changed = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 40)))
                if changed == GOOD_BYTES[path]:
                    continue
                files = dict(GOOD_BYTES)
                files[path] = changed
                sub, value, error = launch(good_env(rng), good_environ(rng), files)
                self.assertIsInstance(error, claude_starter.StarterError, (seed, path))
                self.assertEqual((value, sub.calls), (None, []), (seed, path))

    def test_the_argument_list_does_not_depend_on_the_env(self):
        """TASK-132 AC3: for random env values in form, the list passed to the process is the same ten elements."""
        first = None
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                sub, _, error = launch(good_env(rng), good_environ(rng))
                self.assertIsNone(error)
                args = sub.calls[0][0]
                self.assertEqual(len(args), 10)
                first = args if first is None else first
                self.assertEqual(args, first)


class TASK132PropertiesThisFile(unittest.TestCase):
    def test_every_test_names_its_criteria(self):
        """TASK-132 AC9: every test of this module names "TASK-132 AC" in its own docstring."""
        for cls in (TASK132PropertiesInput, TASK132PropertiesEnvironment, TASK132PropertiesFiles):
            for name in dir(cls):
                if name.startswith('test_'):
                    self.assertIn('TASK-132 AC', getattr(cls, name).__doc__ or '', name)


if __name__ == '__main__':
    unittest.main()

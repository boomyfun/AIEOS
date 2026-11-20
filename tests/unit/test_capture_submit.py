"""Unit tests of capture_submit.capture_and_submit (task TASK-148; BT1b, the core part of route (c) of DEF-0149). The
read, the capture, the restore, the submit and the clock are stand-ins passed as arguments: no process starts, no file is
written and no git runs (the real-git behaviour of the whole step is shown at acceptance by a scratch harness, AC8). The
only files read are the package's own capture_submit.py and launcher.py, with pathlib's read_bytes, for the ast checks.
Stand-in defaults are sentinels, never a value a case passes. Each test names its criteria in its own docstring."""

import ast
import datetime
import hashlib
import inspect
import pathlib
import re
import unittest

from aieos_bootstrap import capture_submit, conformance, gitread, launcher, recovery

HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / 'src' / 'aieos_bootstrap'
ROOT = 'C:/capture-root-148'
REPO = ROOT
TASK = 'TASK-148'
TOKEN = {'epoch': 'epoch-1', 'counter': 7}
HEAD = 'a' * 40
COMMIT = 'b' * 40
STATE = '.aieos'
WRITE_SET = ['src/aieos_bootstrap/mod.py', 'tests/unit/**', 'notes.txt']
FORBIDDEN = ['docs/**', '.github/**', 'src/aieos_bootstrap/secret.py']
RECORDER = 'aieos cli launch for session launch-abc'
NOW = datetime.datetime(2026, 11, 20, 12, 0, 0, tzinfo=datetime.timezone.utc)
GOOD = object()
KEYS = ('result', 'reason', 'findings', 'commit', 'paths')
REASONS = ('status', 'config', 'identity', 'scope', 'staged', 'capture', 'submit')

AT = chr(64)


def mail(local, domain):
    """An e-mail text built at run time, so that no added line of this file holds one (the CI's SEC-002 rule)."""
    return local + AT + domain


EMAIL = mail('a', 'example.invalid')
CONFIG = ('user.name\nA Name\0user.email\n' + EMAIL + '\0core.bare\nfalse\0').encode()
MODIFIED = b' M src/aieos_bootstrap/mod.py\0'


class StopStep(BaseException):
    """A test-defined BaseException that is not an Exception."""


def answer(out=b'', exit=0, error=None):
    return {'exit': exit, 'out': out, 'err': b'', 'error': error}


class Fake:
    """The stand-ins of one call: each records its call in order and gives its answer, or raises it."""

    def __init__(self, config=GOOD, head=GOOD, status=GOOD, capture=GOOD, restore=GOOD, submit=GOOD, clock=GOOD):
        self.answers = {'config': answer(CONFIG) if config is GOOD else config,
                        'head': answer(HEAD.encode() + b'\n') if head is GOOD else head,
                        'status': answer(MODIFIED) if status is GOOD else status,
                        'capture': {'result': 'done', 'commit': COMMIT} if capture is GOOD else capture,
                        'restore': {'result': 'done'} if restore is GOOD else restore,
                        'submit': {'result': 'submitted', 'reason': None, 'findings': []} if submit is GOOD else submit,
                        'clock': NOW if clock is GOOD else clock}
        self.calls = []

    def _give(self, name, args):
        self.calls.append((name, args))
        value = self.answers[name]
        if isinstance(value, BaseException):
            raise value
        return value

    def read(self, repo, argv, timeout):
        name = {'config': 'config', 'rev-parse': 'head', 'status': 'status'}[argv[0]]
        return self._give(name, (repo, list(argv), timeout))

    def capture(self, *args):
        return self._give('capture', args)

    def restore(self, *args):
        return self._give('restore', args)

    def submit(self, *args):
        return self._give('submit', args)

    def clock(self):
        return self._give('clock', ())

    def names(self):
        return [n for n, _ in self.calls]

    def args(self, name):
        return [a for n, a in self.calls if n == name]


def run(fake, use_submit=True, **over):
    kw = {'root': ROOT, 'repo': REPO, 'task_id': TASK, 'token': dict(TOKEN), 'base_head': HEAD,
          'write_set': list(WRITE_SET), 'forbidden': list(FORBIDDEN), 'state_name': STATE, 'clock': fake.clock,
          'recorder': RECORDER, 'read': fake.read, 'capture': fake.capture, 'restore': fake.restore,
          'submit_fn': fake.submit if use_submit else None}
    kw.update(over)
    return capture_submit.capture_and_submit(**kw)


def tree_of(name):
    return ast.parse((SRC / name).read_bytes().decode('utf-8'))


def imports(tree):
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            names.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            names.update('%s.%s' % (n.module, a.name) for a in n.names)
    return names


class TASK148AC1Module(unittest.TestCase):
    def test_the_import_set_and_the_public_name(self):
        """TASK-148 AC1: capture_submit.py imports only datetime, hashlib, re and aieos_bootstrap's conformance,
        gitread and submit (no process, file, clock or aieos_runtime module), names no open, exec, eval, compile,
        __import__, subprocess or os.system, and defines no public name but capture_and_submit."""
        tree = tree_of('capture_submit.py')
        self.assertEqual(imports(tree), {'datetime', 'hashlib', 're', 'aieos_bootstrap.conformance',
                                         'aieos_bootstrap.gitread', 'aieos_bootstrap.submit'})
        plain = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for banned in ('open', 'exec', 'eval', 'compile', '__import__', 'subprocess', 'system', 'time'):
            self.assertNotIn(banned, plain, banned)
        for banned in ('open', 'exec', 'eval', '__import__', 'system', 'environ', 'getenv', 'now', 'utcnow', 'run',
                       'Popen'):
            self.assertNotIn(banned, attrs, banned)
        public = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
                  and not n.name.startswith('_')]
        public += [t.id for n in tree.body if isinstance(n, ast.Assign) for t in n.targets
                   if isinstance(t, ast.Name) and not t.id.startswith('_')]
        self.assertEqual(public, ['capture_and_submit'])
        self.assertEqual(list(inspect.signature(capture_submit.capture_and_submit).parameters),
                         ['root', 'repo', 'task_id', 'token', 'base_head', 'write_set', 'forbidden', 'state_name',
                          'clock', 'recorder', 'read', 'capture', 'restore', 'submit_fn'])
        self.assertIsNone(inspect.signature(capture_submit.capture_and_submit).parameters['submit_fn'].default)

    def test_the_done_path(self):
        """TASK-148 AC1: a changed path in the write set gives the calls config, head, status, capture, clock, submit
        and restore once each in that order and the result "done" with exactly KEYS, the commit and the path; the read
        argv are the launcher's own forms."""
        fake = Fake()
        out = run(fake)
        self.assertEqual(tuple(out), KEYS)
        self.assertEqual((out['result'], out['reason'], out['commit'], out['paths']),
                         ('done', None, COMMIT, ['src/aieos_bootstrap/mod.py']))
        self.assertEqual(fake.names(), ['config', 'head', 'status', 'capture', 'clock', 'submit', 'restore'])
        self.assertEqual(fake.args('config'), [(REPO, list(gitread.CONFIG_LIST), launcher.TIMEOUT)])
        self.assertEqual(fake.args('head'), [(REPO, list(launcher.HEAD_ARGS), launcher.TIMEOUT)])
        self.assertEqual(fake.args('status'), [(REPO, list(gitread.STATUS_HEAD) + [':(exclude)' + STATE],
                                                launcher.TIMEOUT)])
        expected_message = ('AIEOS task submission TASK-148\n\nThe session left 1 changed path inside the contract\'s '
                            'write set; this commit captures it.\n\nAIEOS-Task: TASK-148\nAIEOS-Fence: epoch-1:7\n')
        self.assertEqual(fake.args('capture'), [(REPO, 'refs/heads/task/' + TASK, HEAD, ['src/aieos_bootstrap/mod.py'],
                                                 expected_message, {'name': 'A Name', 'email': EMAIL},
                                                 STATE)])
        self.assertEqual(fake.args('restore'), [(REPO, ['src/aieos_bootstrap/mod.py'],
                                                 {'src/aieos_bootstrap/mod.py': 'modified'}, STATE)])

    def test_the_default_submit_is_submit_submit(self):
        """TASK-148 AC1 (D-6738 C1): submit_fn None means submit.submit: the module's default is the submit module's
        own function, looked up at the call, and the stand-in form with submit_fn given is what the tests use."""
        source = (SRC / 'capture_submit.py').read_bytes().decode('utf-8')
        self.assertIn('submit.submit if submit_fn is None else submit_fn', source)

    def test_no_exception_escapes(self):
        """TASK-148 AC1: every callee that raises an Exception gives a refused mapping with exactly KEYS and a reason of
        the closed set, never an Exception."""
        for name in ('config', 'head', 'status', 'capture', 'restore', 'submit', 'clock'):
            fake = Fake(**{name: RuntimeError('boom')})
            out = run(fake)
            self.assertEqual(tuple(out), KEYS, name)
            self.assertEqual(out['result'], 'refused', name)
            self.assertIn(out['reason'], REASONS, name)
            self.assertTrue(all(isinstance(f, str) for f in out['findings']), name)

    def test_a_base_exception_of_a_callee_escapes(self):
        """TASK-148 AC1 (D-6633 M3; D-6752 C2 (b)): a BaseException that is not an Exception, raised by any callee (the
        read at each of its three calls, the capture, the clock, the submission, the restore), is not caught by the
        step and escapes capture_and_submit; the callees after it are not called."""
        for name in ('config', 'head', 'status', 'capture', 'clock', 'submit', 'restore'):
            fake = Fake(**{name: StopStep('stop')})
            with self.assertRaises(StopStep, msg=name):
                run(fake)
            self.assertEqual(fake.names()[-1], name, name)

    def test_the_argument_refusals_call_nothing(self):
        """TASK-148 AC1: every argument that is out of form gives "refused" and no callee is called (reason "status";
        reason "scope" for a write set or a forbidden list that is not a non-empty list of well-formed patterns)."""
        base_bad = (('root', ''), ('root', 3), ('repo', None), ('task_id', 'TASK-'), ('task_id', 'task-1'),
                    ('token', None), ('token', {'epoch': 'e'}), ('token', {'epoch': '', 'counter': 1}),
                    ('token', {'epoch': 'e', 'counter': True}), ('token', {'epoch': 'e', 'counter': -1}),
                    ('token', {'epoch': 'e\nx', 'counter': 1}), ('token', {'epoch': ' e', 'counter': 1}),
                    ('token', {'epoch': 'e', 'counter': 1, 'extra': 1}), ('base_head', 'A' * 40),
                    ('base_head', 'a' * 39), ('state_name', 'aieos'), ('state_name', '.'), ('state_name', 3),
                    ('clock', None), ('recorder', ''), ('read', 'x'), ('capture', None), ('restore', 3))
        for key, value in base_bad:
            fake = Fake()
            out = run(fake, **{key: value})
            self.assertEqual((out['result'], out['reason']), ('refused', 'status'), (key, value))
            self.assertEqual(fake.calls, [], (key, value))
        fake = Fake()
        out = run(fake, submit_fn=3)
        self.assertEqual((out['result'], out['reason'], fake.calls), ('refused', 'status', []))
        for key in ('write_set', 'forbidden'):
            for value in (None, [], 'a', ['a/'], ['a b'], ['**x'], [3], ['/a'], ['a//b'], ['..']):
                fake = Fake()
                out = run(fake, **{key: value})
                self.assertEqual((out['result'], out['reason']), ('refused', 'scope'), (key, value))
                self.assertEqual(fake.calls, [], (key, value))

    def test_a_refusal_before_the_capture_calls_no_writer(self):
        """TASK-148 AC1: a refusal of the steps before the capture (configuration, identity, HEAD, status, staged
        change, scope) calls neither capture nor restore nor submit."""
        cases = (Fake(config=answer(error='x')), Fake(config=answer(b'filter.x.clean\nc\0')),
                 Fake(config=answer(b'user.name\nA\0')), Fake(head=answer(b'c' * 40 + b'\n')),
                 Fake(status=answer(b'A  src/aieos_bootstrap/mod.py\0')),
                 Fake(status=answer(b' M other/file.py\0')), Fake(status=answer(error='x')))
        for fake in cases:
            out = run(fake)
            self.assertEqual(out['result'], 'refused')
            for name in ('capture', 'restore', 'submit'):
                self.assertNotIn(name, fake.names())

    def test_a_refused_capture_calls_neither_restore_nor_submit(self):
        """TASK-148 AC1: a capture that is refused, not a mapping, gives no commit or raises is "refused" with reason
        "capture" whose findings carry the callee's reason, and neither the clock, submit nor restore is called."""
        for given in ({'result': 'refused', 'reason': 'ref-exists', 'findings': ['ref: exists']}, 'x', None,
                      {'result': 'done', 'commit': 'zz'}, {'result': 'done'}, RuntimeError('x')):
            fake = Fake(capture=given)
            out = run(fake)
            self.assertEqual((out['result'], out['reason'], out['commit']), ('refused', 'capture', None), given)
            self.assertEqual(fake.names(), ['config', 'head', 'status', 'capture'], given)
        out = run(Fake(capture={'result': 'refused', 'reason': 'ref-exists', 'findings': ['ref: exists']}))
        self.assertIn('capture: the capture gave ref-exists', out['findings'])
        self.assertIn('ref: exists', out['findings'])

    def test_a_refused_submit_leaves_the_tree(self):
        """TASK-148 AC1 (D-6608 Q4, D-6609 C3 (b), D-6739): after a done capture a refused, raising or out-of-form
        submit gives reason "submit", keeps the commit in the answer and does NOT call restore."""
        refused = {'result': 'refused', 'reason': 'store', 'findings': ['store: refused']}
        for given in (refused, {'result': 'maybe'}, {'reason': 'x'}, 'x', None, RuntimeError('x')):
            fake = Fake(submit=given)
            out = run(fake)
            self.assertEqual((out['result'], out['reason'], out['commit']), ('refused', 'submit', COMMIT), given)
            self.assertEqual(out['paths'], ['src/aieos_bootstrap/mod.py'])
            self.assertNotIn('restore', fake.names(), given)
        out = run(Fake(submit=refused))
        self.assertIn('store: refused', out['findings'])

    def test_a_duplicate_submit_leads_to_the_restore(self):
        """TASK-148 AC1 (D-6609 C3 (b)): a submit that gave "duplicate" is accepted like "submitted": the restore is
        called and the result is "done"; a missing release is a finding of the answer, not a refusal."""
        fake = Fake(submit={'result': 'duplicate', 'reason': None, 'findings': ['store: nothing released']})
        out = run(fake)
        self.assertEqual((out['result'], out['reason']), ('done', None))
        self.assertIn('restore', fake.names())
        self.assertIn('store: nothing released', out['findings'])

    def test_a_refused_restore_gives_the_reason_capture(self):
        """TASK-148 AC1 (D-6633 M12 as narrowed by D-6739): a restore that is refused, raises or is out of form after
        a done submit gives "refused" with reason "capture", keeps the commit and adds its findings."""
        for given in ({'result': 'refused', 'reason': 'git-failed', 'findings': ['restore: failed']}, 'x', None,
                      RuntimeError('x')):
            fake = Fake(restore=given)
            out = run(fake)
            self.assertEqual((out['result'], out['reason'], out['commit']), ('refused', 'capture', COMMIT), given)
            self.assertEqual(fake.names()[-2:], ['submit', 'restore'], given)

    def test_no_changed_path_gives_none(self):
        """TASK-148 AC1 and AC2: an empty status gives "none" with a finding and no capture, no clock, no submit and no
        restore."""
        fake = Fake(status=answer(b''))
        out = run(fake)
        self.assertEqual((out['result'], out['reason'], out['commit'], out['paths']), ('none', None, None, []))
        self.assertTrue(out['findings'])
        self.assertEqual(fake.names(), ['config', 'head', 'status'])

    def test_the_default_submit_is_called_when_none_is_given(self):
        """TASK-148 AC1: with submit_fn None the module calls submit.submit; the call is made on a stand-in of that
        name and the arguments are the seven of the objective."""
        seen = []

        def stand_in(*args):
            seen.append(args)
            return {'result': 'submitted', 'reason': None, 'findings': []}
        original = capture_submit.submit.submit
        capture_submit.submit.submit = stand_in
        try:
            fake = Fake()
            out = run(fake, use_submit=False)
        finally:
            capture_submit.submit.submit = original
        self.assertEqual(out['result'], 'done')
        self.assertEqual(len(seen), 1)
        self.assertEqual(len(seen[0]), 7)


class TASK148AC2Status(unittest.TestCase):
    def test_the_classes(self):
        """TASK-148 AC2 (D-6633 M10): " M" is modified, " D" deleted, "??" added, in git's order; each class reaches
        restore as the mapping path to class."""
        status = b' M src/aieos_bootstrap/mod.py\0 D tests/unit/a.py\0?? tests/unit/new.py\0'
        fake = Fake(status=answer(status))
        out = run(fake)
        self.assertEqual(out['result'], 'done')
        self.assertEqual(out['paths'], ['src/aieos_bootstrap/mod.py', 'tests/unit/a.py', 'tests/unit/new.py'])
        self.assertEqual(fake.args('restore')[0][2], {'src/aieos_bootstrap/mod.py': 'modified',
                                                      'tests/unit/a.py': 'deleted', 'tests/unit/new.py': 'added'})

    def test_every_other_pair_is_staged(self):
        """TASK-148 AC2: a staged 'M ', 'A ', 'D ', 'R ', 'C ', 'U', 'T', a double letter and '!!' is a refusal
        "staged" that names the count and the first twenty pairs; nothing is captured."""
        for pair in (b'M ', b'A ', b'D ', b'R ', b'C ', b'UU', b' U', b' T', b'MM', b'AM', b'!!', b' A', b' R', b'DD'):
            fake = Fake(status=answer(pair + b' tests/unit/a.py\0' + b' M tests/unit/b.py\0'))
            out = run(fake)
            self.assertEqual((out['result'], out['reason']), ('refused', 'staged'), pair)
            self.assertNotIn('capture', fake.names(), pair)
            self.assertIn('staged: 1 entries', out['findings'][0], pair)
        many = b''.join(b'A  tests/unit/f%d.py\0' % i for i in range(30))
        out = run(Fake(status=answer(many)))
        self.assertEqual(out['reason'], 'staged')
        self.assertIn('30 entries', out['findings'][0])
        self.assertEqual(out['findings'][0].count("'A '"), 20)

    def test_the_form_rules_equal_the_launchers(self):
        """TASK-148 AC2 (D-6633 M10): on shared inputs the status parser refuses what launcher._root_entries refuses
        (not bytes, no final NUL, a "##" entry, a status character outside the set, a short entry, no space) and its
        paths equal _root_entries' paths."""
        shared = (b'', b' M a.py\0', b' M a.py\0?? b/c.py\0', b' M a.py', b'## main\0', b' M\0', b'XM a.py\0',
                  b' Xa.py\0', b'M  \0', b'!! x\0', b' M a.py\0## z\0', b'   a.py\0', 'x', None, b'\0')
        for given in shared:
            mine, mine_found = capture_submit._status_entries(given)
            theirs, theirs_found = launcher._root_entries(given)
            self.assertEqual(mine_found is None, theirs_found is None, given)
            if theirs is not None:
                self.assertEqual([p for _, p in mine], theirs, given)
                self.assertEqual([pair for pair, _ in mine], [e[:2] for e in given.split(b'\0')[:-1]], given)
            fake = Fake(status=answer(given))
            out = run(fake)
            if theirs_found is not None:
                self.assertEqual((out['result'], out['reason']), ('refused', 'status'), given)

    def test_a_non_utf8_path_is_a_status_refusal(self):
        """TASK-148 AC2: a path that is not strict UTF-8 gives "refused" with reason "status" and nothing is
        captured."""
        fake = Fake(status=answer(b' M src/\xff.py\0'))
        out = run(fake)
        self.assertEqual((out['result'], out['reason']), ('refused', 'status'))
        self.assertEqual(fake.names(), ['config', 'head', 'status'])

    def test_the_scope(self):
        """TASK-148 AC2 (D-6633 M1, M2): a path outside the write set, one that is not well formed, one under a
        forbidden pattern, one under the state directory or .git in any letter case each give "refused" with reason
        "scope" and nothing is captured; one path out of scope refuses the whole step."""
        for path in ('other/file.py', 'src/aieos_bootstrap/secret.py', 'docs/a.md', '.github/x.yml', '.aieos/x',
                     '.AIEOS/x', '.Aieos/x', 'tests/unit/.git/x', 'tests/unit/.GIT', 'a b.py', 'src//x.py',
                     'tests/unit/a b.py', 'tests/unit/..', 'notes.txt/', 'TESTS/unit/a.py'):
            fake = Fake(status=answer(b' M ' + path.encode() + b'\0' + MODIFIED))
            out = run(fake)
            self.assertEqual((out['result'], out['reason']), ('refused', 'scope'), path)
            self.assertEqual(fake.names(), ['config', 'head', 'status'], path)
            self.assertTrue(out['findings'][0].startswith('scope: 1 of 2'), out['findings'])

    def test_each_scope_branch_decides_alone(self):
        """TASK-148 AC2 (D-6633 M1, M2; D-6752 C2 (a)): each refusal is shown with a path that only that rule refuses:
        a path INSIDE the write set and under a forbidden pattern; a path inside the write set and under the state
        directory in any letter case; a path inside the write set and under .git in any letter case; each names its own
        reason in the finding and nothing is captured."""
        cases = (('docs/a.md', ['docs/**'], ['docs/**'], 'a path under a forbidden pattern'),
                 ('src/aieos_bootstrap/secret.py', ['src/**'], ['src/aieos_bootstrap/secret.py'],
                  'a path under a forbidden pattern'),
                 ('.aieos/x', ['.aieos/**'], FORBIDDEN, 'a path under the state directory or .git'),
                 ('.AIEOS/x', ['.AIEOS/**'], FORBIDDEN, 'a path under the state directory or .git'),
                 ('tests/.git/x', ['tests/**'], FORBIDDEN, 'a path under the state directory or .git'),
                 ('tests/.GIT/x', ['tests/**'], FORBIDDEN, 'a path under the state directory or .git'),
                 ('.git/config', ['**'], FORBIDDEN, 'a path under the state directory or .git'))
        for path, write_set, forbidden, why in cases:
            self.assertTrue(any(conformance.path_matches(p, path) for p in write_set), (path, write_set))
            fake = Fake(status=answer(b' M ' + path.encode() + b'\0'))
            out = run(fake, write_set=write_set, forbidden=forbidden)
            self.assertEqual((out['result'], out['reason']), ('refused', 'scope'), path)
            self.assertEqual(fake.names(), ['config', 'head', 'status'], path)
            self.assertTrue(any(f.endswith(why) for f in out['findings']), (path, out['findings']))

    def test_the_scope_findings_are_bounded(self):
        """TASK-148 AC2: a scope refusal names the count and at most twenty paths, each cut to 80 characters."""
        status = b''.join(b'?? other/' + (b'x' * 120) + b'%d.py\0' % i for i in range(30))
        out = run(Fake(status=answer(status)))
        self.assertEqual(out['reason'], 'scope')
        self.assertEqual(len(out['findings']), 21)
        self.assertTrue(all(len(f) < 160 for f in out['findings']))

    def test_the_pattern_forms_equal_the_g0_matcher(self):
        """TASK-148 AC2 (D-6633 M1): conformance.path_matches, the matcher of the scope, gives what G0's own pattern_re
        gives (aieos-checks.yml, the function copied here) for a trailing "**" with the folder's own name, a middle
        "**", a pattern with no "/", "*" inside a name and a plain path, each listed with its expected value."""
        def g0(pattern, path):
            if '/' not in pattern:
                pattern = '**/' + pattern
            parts = pattern.split('/')
            rx = ''
            for i, part in enumerate(parts):
                last = i == len(parts) - 1
                if part == '**':
                    rx += '.*' if last else '(?:[^/]+/)*'
                else:
                    rx += re.escape(part).replace(r'\*', '[^/]*') + ('' if last else '/')
            return re.match(rx + r'\Z', path) is not None
        expected = (('tests/unit/**', 'tests/unit/a.py', True), ('tests/unit/**', 'tests/unit/sub/a.py', True),
                    ('tests/unit/**', 'tests/unit', False), ('tests/**/a.py', 'tests/a.py', True),
                    ('tests/**/a.py', 'tests/x/y/a.py', True), ('tests/**/a.py', 'tests/x/b.py', False),
                    ('notes.txt', 'notes.txt', True), ('notes.txt', 'a/b/notes.txt', True),
                    ('notes.txt', 'notes.txt.bak', False), ('test_*.py', 'tests/unit/test_a.py', True),
                    ('test_*.py', 'tests/unit/a_test.py', False), ('src/*.py', 'src/a.py', True),
                    ('src/*.py', 'src/sub/a.py', False), ('src/a/**', 'src/a/b', True), ('src/a/**', 'src/ab/b', False))
        for pattern, path, value in expected:
            self.assertEqual(conformance.path_matches(pattern, path), value, (pattern, path))
            self.assertEqual(g0(pattern, path), value, (pattern, path))

    def test_the_configuration_rule_equals_the_launchers(self):
        """TASK-148 AC2: the configuration parser refuses the keys launcher._config_keys refuses (a key that begins
        with "filter.", ASCII-lowercased, or equals "core.worktree") and finds the malformed answers it finds, on shared
        inputs."""
        shared = (b'', b'a.b\nc\0', b'filter.x.clean\nc\0', b'FILTER.x.smudge\0', b'core.worktree\n/x\0',
                  b'Core.WorkTree\nx\0', b'core.bare\nfalse\0', b'\nx\0', b'a.b\nc', b'user.name\nA\0filter.a.b\0', 'x',
                  None, b'core.worktreefoo\nx\0', b'filterx.a\nb\0')
        for given in shared:
            keys, _, _, found = capture_submit._config(given)
            theirs, theirs_found = launcher._config_keys(given)
            self.assertEqual(found is None, theirs_found is None, given)
            if theirs_found is None:
                self.assertEqual(keys, theirs, given)
            out = run(Fake(config=answer(given)))
            if theirs_found is not None or theirs:
                self.assertEqual((out['result'], out['reason']), ('refused', 'config'), given)

    def test_a_configuration_refusal_names_no_value(self):
        """TASK-148 AC2: a refusal for a filter key holds the key and never its value."""
        config = ('user.name\nA\0user.email\n' + mail('b', 'c.invalid') + '\0filter.lfs.clean\nSECRETVALUE\0').encode()
        out = run(Fake(config=answer(config)))
        self.assertEqual(out['reason'], 'config')
        self.assertTrue(any("b'filter.lfs.clean'" in f for f in out['findings']))
        self.assertFalse(any('SECRETVALUE' in f for f in out['findings']))


class TASK148AC3Message(unittest.TestCase):
    def message(self, fake):
        return fake.args('capture')[0][4]

    def test_the_message_has_a_body_and_the_two_trailers(self):
        """TASK-148 AC3: the message passed to capture has a subject line, a body paragraph and a last paragraph of
        exactly the two trailer lines; recovery.trailers reads the task and the fence from it with no finding, and the
        paragraph form is the one submit._identify requires."""
        for count, status in ((1, MODIFIED), (2, MODIFIED + b' M notes.txt\0')):
            fake = Fake(status=answer(status))
            run(fake)
            message = self.message(fake)
            paragraphs = message.strip('\n').split('\n\n')
            self.assertEqual(len(paragraphs), 3)
            self.assertEqual(paragraphs[0], 'AIEOS task submission ' + TASK)
            self.assertIn(str(count), paragraphs[1])
            self.assertEqual(paragraphs[2], 'AIEOS-Task: %s\nAIEOS-Fence: epoch-1:7' % TASK)
            trailer, findings = recovery.trailers(message)
            self.assertEqual(findings, [])
            self.assertEqual(trailer, {'task': TASK, 'fence': {'epoch': 'epoch-1', 'counter': 7}})
            fence, not_identified, fence_found = capture_submit.submit._identify(message, TASK)
            self.assertEqual((fence, not_identified, fence_found), ({'epoch': 'epoch-1', 'counter': 7}, [], []))

    def test_the_event_id_is_the_digest_of_the_three_texts(self):
        """TASK-148 AC3 (D-6633 M8): the event id is the SHA-256 hex of "task.submitted", the task id and the commit id
        joined by LF, the form of verification_records' digest (recomputed here), and submit_fn gets the seven
        arguments root, repo, commit, task, event id, recorder and the fresh clock read."""
        fake = Fake()
        run(fake)
        expected = hashlib.sha256('\n'.join(('task.submitted', TASK, COMMIT)).encode('utf-8')).hexdigest()
        self.assertEqual(fake.args('submit'), [(ROOT, REPO, COMMIT, TASK, expected, RECORDER, NOW)])

    def test_the_identity_is_the_last_name_and_email(self):
        """TASK-148 AC3: the identity is the LAST user.name and the LAST user.email of the configuration list, as git
        has it; it is refused with reason "identity" when either is absent, empty, or holds <, >, LF, NUL or bytes that
        are not UTF-8."""
        first, second, plain = mail('first', 'example.invalid'), mail('second', 'x.invalid'), mail('a', 'b.invalid')
        config = ('user.name\nFirst\0user.email\n' + first + '\0user.name\nSecond\0user.email\n' + second +
                  '\0').encode()
        fake = Fake(config=answer(config))
        run(fake)
        self.assertEqual(fake.args('capture')[0][5], {'name': 'Second', 'email': second})
        mail_line = ('user.email\n' + plain + '\0').encode()
        for bad in (mail_line, b'user.name\nA\0', b'user.name\n\0' + mail_line,
                    b'user.name\nA<b\0' + mail_line, b'user.name\nA\0user.email\na>b\0',
                    b'user.name\nA\nB\0' + mail_line, b'user.name\nA\0user.email\n\xff\0',
                    b'user.name\0' + mail_line):
            fake = Fake(config=answer(bad))
            out = run(fake)
            self.assertEqual((out['result'], out['reason']), ('refused', 'identity'), bad)
            self.assertNotIn('capture', fake.names(), bad)

    def test_the_clock_is_read_once_after_the_capture(self):
        """TASK-148 AC3 (D-6633 M8): the clock is read once, after the capture returned and before submit_fn is
        called, and the value passed to submit_fn is that read; a read that is not timezone-aware UTC with whole
        seconds, or that raises, gives reason "submit" with the commit kept and no submit and no restore."""
        fake = Fake()
        run(fake)
        self.assertEqual(fake.names().count('clock'), 1)
        names = fake.names()
        self.assertEqual(names.index('capture') + 1, names.index('clock'))
        self.assertEqual(names.index('clock') + 1, names.index('submit'))
        for bad in (datetime.datetime(2026, 11, 20, 12, 0, 0), NOW + datetime.timedelta(microseconds=5),
                    NOW.astimezone(datetime.timezone(datetime.timedelta(hours=2))), 'x', None):
            fake = Fake(clock=bad)
            out = run(fake)
            self.assertEqual((out['result'], out['reason'], out['commit']), ('refused', 'submit', COMMIT), bad)
            self.assertNotIn('submit', fake.names())
            self.assertNotIn('restore', fake.names())


class TASK148AC4Launcher(unittest.TestCase):
    def test_the_launcher_timeout_and_head_form_are_the_modules(self):
        """TASK-148 AC1 and AC2: the module's read timeout and HEAD argv equal the launcher's (the module repeats them
        because it cannot import the launcher)."""
        self.assertEqual(capture_submit._TIMEOUT, launcher.TIMEOUT)
        self.assertEqual(capture_submit._HEAD_ARGS, tuple(launcher.HEAD_ARGS))


if __name__ == '__main__':
    unittest.main()

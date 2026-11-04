"""Unit tests of aieos_bootstrap.launcher and of execution.task_view (task TASK-086): the arguments and the callees,
the order, the session id, the inputs, the grant path, the held and state refusals, no grant, failing closed, end,
task_view, what the modules may touch and the docstrings. Every Git answer comes from a stand-in read over objects held
in memory (rebuilt here in tests/unit/test_resume_log_inputs.py's form, not imported from it); every store function is
a stand-in that records its calls, bound to the real function's signature (tests/unit/test_adapter.py's form); every
log is built with eventlog.append; no test runs Git or writes a file; the sources are read with pathlib's read_bytes."""

import ast
import datetime
import hashlib
import inspect
import pathlib
import types
import unittest
from unittest import mock

from aieos_bootstrap import adapter, adapter_declaration, eventlog, execution, gitread, launcher, resume_check
from aieos_bootstrap import resume_inputs
from aieos_bootstrap import claude_code_shell_allow as shell_allow
from aieos_bootstrap import resume_log_inputs, writer

HERE = pathlib.Path(__file__).resolve()
REPO = str(HERE.parents[2])
ROOT = str(HERE.parents[2] / 'no-such-launcher-root')
END_ROOT = 'C:/launcher-end-root-89'
PKG = HERE.parents[2] / 'src' / 'aieos_bootstrap'
TASK = 'TASK-100'
NOW = datetime.datetime(2026, 10, 24, 12, 0, 0, tzinfo=datetime.timezone.utc)
LATER = NOW + datetime.timedelta(hours=1)
REC = 'aieos-launcher (unit)'
TOKEN = {'epoch': 'e1', 'counter': 1}
LEASE = {'task_id': TASK, 'fencing_token': TOKEN, 'expires_at': LATER}
HEAD_ARGS = ['rev-parse', '--verify', '--end-of-options', 'HEAD']
BASE_ARGS = ['rev-parse', '--verify', '--end-of-options', 'refs/heads/main']
STATUS_ARGS = list(gitread.STATUS_HEAD) + [':(exclude)' + writer.STATE_DIR]
CONFIG_ARGS = list(gitread.CONFIG_LIST)

S_TEXT = 'Đặc tả — một dòng\n'
S_HASH = hashlib.sha256(S_TEXT.encode('utf-8')).hexdigest()
RC_TEXT = '# Bộ kiểm tra — một bản đứng thay\nX = 1\n'
CONSTITUTION = '\n'.join([
    '# A stand-in constitution', '', '## 1. The articles', '',
    '### INV-001 · architecture · One', '',
    '- Severity: blocking. Scope: the core\'s source tree. Applicability: implementation. Enforcement: x.', ''])
POLICY = '\n'.join(['# A stand-in policy', '', '## 3. The rules', '', '```yaml', 'policy_version: v9', '',
                    'risk_rules:', '  - match: { paths: ["src/**"] }', '    risk: medium', '```']) + '\n'


def contract(base, depends, risk='high'):
    lines = ['task: %s' % TASK, 'contract_version: v1', 'task_type: implementation', 'traces_to:',
             '  - docs/specs/s.md#1', 'input_state:', '  base_commit: %s' % base,
             '  depends_on: [%s]' % ', '.join(depends), '  intent_versions:', '    docs/specs/s.md: %s' % S_HASH,
             'write_set:', '  paths:', '    - src/aieos_bootstrap/mod.py', 'read_set:', '  paths:',
             '    - src/aieos_bootstrap/mod.py', '  interfaces: []', 'constitution: [INV-001]', 'acceptance_criteria:',
             '  - AC1: >-', '      One.', 'risk: %s' % risk, 'autonomy:', '  budgets: {tokens: 600k, retries: 2}']
    return '\n'.join(lines) + '\n'


def gid(kind, data):
    return hashlib.sha1(b'%s %d\x00' % (kind.encode('ascii'), len(data)) + data, usedforsecurity=False).hexdigest()


def ok(out):
    return {'exit': 0, 'out': out, 'err': b'', 'error': None}


class Repo:
    """A stand-in for gitread.run over commits held in memory, ids being Git's own hashes; it answers the HEAD form
    with its head, the config form (TASK-110) with its config answer (clean, b'', by default; a value or a callable
    when set), the status form (TASK-109) with its status answer (clean, b'', by default; a value or a callable
    when set) and records its calls as (repo, args, timeout)."""

    def __init__(self):
        self.objects, self.files, self.parents, self.calls = {}, {}, {}, []
        self.head = None
        self.config = b''
        self.status = b''

    def _put(self, kind, data):
        oid = gid(kind, data)
        self.objects[oid] = (kind, data)
        return oid

    def _tree(self, node):
        entries = []
        for name in sorted(node):
            value = node[name]
            if isinstance(value, dict):
                entries.append(('040000', 'tree', self._tree(value), name))
            else:
                entries.append(('100644', 'blob', self._put('blob', value.encode('utf-8')), name))
        return self._put('tree', ''.join('%s %s %s\t%s\n' % e for e in entries).encode('utf-8'))

    def commit(self, files, parents=(), message='m'):
        tree = {}
        for path, text in files.items():
            node = tree
            names = path.split('/')
            for name in names[:-1]:
                node = node.setdefault(name, {})
            node[names[-1]] = text
        head = 'tree %s\n' % self._tree(tree) + ''.join('parent %s\n' % p for p in parents)
        data = (head + 'author A B 1 +0000\ncommitter A B 1 +0000\n\n%s\n' % message).encode('ascii')
        oid = self._put('commit', data)
        self.files[oid] = dict(files)
        self.parents[oid] = list(parents)
        return oid

    def _changed(self, oid):
        mine = self.files[oid]
        theirs = self.files[self.parents[oid][0]] if self.parents[oid] else {}
        return sorted(p for p in set(mine) | set(theirs) if mine.get(p) != theirs.get(p))

    def __call__(self, repo, args, timeout=30):
        self.calls.append((repo, list(args), timeout))
        if list(args) == HEAD_ARGS or list(args) == BASE_ARGS:
            return ok((self.head + '\n').encode('ascii'))
        if list(args) == CONFIG_ARGS:
            return self.config(repo, args, timeout) if callable(self.config) else ok(self.config)
        if list(args) == STATUS_ARGS:
            return self.status(repo, args, timeout) if callable(self.status) else ok(self.status)
        oid = args[-1]
        if oid not in self.objects:
            return {'exit': 128, 'out': b'', 'err': b'fatal', 'error': None}
        if args[0] == 'rev-parse':
            return ok((oid + '\n').encode('ascii'))
        if args[0] == 'rev-list':
            return ok((' '.join([oid] + self.parents.get(oid, [])) + '\n').encode('ascii'))
        if args[0] == 'diff-tree':
            return ok(b''.join(p.encode('utf-8') + b'\x00' for p in self._changed(oid)))
        if args[1] == '-t':
            return ok((self.objects[oid][0] + '\n').encode('ascii'))
        return ok(self.objects[oid][1])


def world(depends=(), risk='high'):
    """base (one source file) and head (adds the contract, the intent file, the constitution, the policy and a
    stand-in resume_check.py with non-ASCII text); the repo's head is head."""
    repo = Repo()
    base = repo.commit({'src/aieos_bootstrap/mod.py': 'X = 1\n'}, message='base')
    tree = {'src/aieos_bootstrap/mod.py': 'X = 1\n', 'docs/specs/s.md': S_TEXT,
            'docs/pre-genesis/constitution.md': CONSTITUTION, 'docs/specs/risk-rules-gov-aieos.md': POLICY,
            'src/aieos_bootstrap/resume_check.py': RC_TEXT, 'docs/tasks/%s.yaml' % TASK: contract(base, depends, risk)}
    repo.head = repo.commit(tree, [base], 'head')
    return repo


class Log:
    """An event log kept as bytes, every line decided by eventlog.append."""

    def __init__(self):
        self.data = b''
        self.n = 0

    def add(self, event_type, payload, task_id=TASK):
        self.n += 1
        r = eventlog.append(self.data, event_type, payload, 'ev-%d' % self.n, NOW, task_id=task_id)
        if r.result != 'appended':
            raise AssertionError(r.findings)
        self.data += r.line
        return self

    def approve(self, contract_hash='a' * 64, task_id=TASK):
        return self.add('task.approved', {'contract_version': 'v1', 'contract_hash': contract_hash,
                                          'approval_record': 'r'}, task_id)


def approved_log(repo):
    """A log holding the task's task.approved with the contract hash git_inputs gives at the repo's head."""
    given, found = resume_inputs.git_inputs(REPO, repo.head, TASK, b'', repo)
    if found is not None:
        raise AssertionError(found)
    del repo.calls[:]
    return Log().approve(given['contract_hash'])


class Calls:
    """Stand-ins that record each call, bound to the real function's signature, and give a set answer."""

    def __init__(self, answers=None):
        self.calls = []
        self.answers = dict(answers or {})

    def make(self, name, real):
        def stand_in(*args, **kwargs):
            inspect.signature(real).bind(*args, **kwargs)
            self.calls.append((name, args, kwargs))
            a = self.answers.get(name)
            if isinstance(a, BaseException):
                raise a
            return a(*args, **kwargs) if callable(a) else a
        return stand_in

    def names(self):
        return [c[0] for c in self.calls]

    def of(self, name):
        return [c for c in self.calls if c[0] == name]


def written(*args, **kwargs):
    return writer.WriteResult(types.SimpleNamespace(result='appended', reason=None, seq=1, line=b'', findings=()))


def store(result='done', reason=None, value=None):
    return writer.StoreResult(result, reason, ['a finding'] if result != 'done' else [], value)


def ended(result='done'):
    out = dict.fromkeys(adapter.RESULT_KEYS)
    out.update({'result': result, 'reason': None if result == 'done' else 'session',
                'findings': [] if result == 'done' else ['an end finding']})
    return out


STORE = (('read_log', writer.read_log), ('expire', writer.expire_leases), ('held', writer.held_lease),
         ('start_session', writer.start_session), ('append', writer.append_event), ('grant', writer.grant_lease),
         ('release', writer.release_lease_token), ('end_session', writer.end_session),
         ('release_lease_token', writer.release_lease_token))


def calls_for(repo, log, **answers):
    base = {'read': repo, 'read_log': lambda root: log.data, 'expire': [], 'held': None, 'start_session': store(),
            'append': written, 'grant': store(value=LEASE), 'release': store(), 'end_session': store(value=[]),
            'release_lease_token': store()}
    base.update(answers)
    return Calls(base)


def declared(max_risk):
    """The answer a test gives for adapter_declaration.read_declaration (TASK-117 AC3): absent for None, else low with
    the tier the test names. A test-only seam: the real read never gives a tier above low, the Resume Check still
    compares any tier."""
    if max_risk is None:
        return {'result': 'absent', 'max_risk': None, 'findings': []}
    return {'result': 'low', 'max_risk': max_risk, 'findings': []}


def absent_declaration(repo, base, adapter_name, run=None):
    """A stand-in for the declaration read that finds no declaration (TASK-117 AC3)."""
    return declared(None)


def launch(c, max_risk='critical', stub=(), **over):
    """launcher.start with every store function and the read a recording stand-in; the names in stub also replace
    adapter.start ('start') and adapter.end ('end'). TASK-117 AC3: launcher.start has no max_risk argument; max_risk
    here is the tier the recording stand-in of read_declaration answers (declared(max_risk)), unless the test put its
    own answer under 'read_declaration' in c. TASK-090's step is given a read_sessions stand-in that records
    nothing and lists no session, unless the test gives its own, and per-session stand-ins that record any call into a
    list; that list must stay empty, so launch raises AssertionError after start returns otherwise (TASK-090 AC7)."""
    kw = {name: c.make(name, real) for name, real in STORE}
    kw['read'] = c.make('read', gitread.run)
    c.answers.setdefault('read_declaration', declared(max_risk))
    kw['read_declaration'] = c.make('read_declaration', adapter_declaration.read_declaration)
    if 'start' in stub:
        kw['start'] = c.make('start', adapter.start)
    if 'end' in stub:
        kw['end'] = c.make('end', adapter.end)
    stray = []
    kw['read_sessions'] = lambda root, task_id: store(value=[])
    for name in ('session_leases', 'stored_reads', 'remove_reads', 'observe_gone'):
        kw[name] = lambda *a, name=name, **k: stray.append(name)
    args = dict(root=ROOT, repo=REPO, task_id=TASK, adapter_name='unit', holder='agent-1', recorder=REC, now=NOW,
                expires_at=LATER)
    args.update(kw)
    args.update(over)
    r = launcher.start(**args)
    if stray:
        raise AssertionError('a per-session callee was called with no session listed: %r' % (stray,))
    return r


def tree_of(name):
    return ast.parse((PKG / name).read_bytes().decode('utf-8'))


def imports(tree):
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            out.update('%s.%s' % (node.module, a.name) for a in node.names)
    return out


def doc(name):
    return ' '.join(ast.get_docstring(tree_of(name)).split())


def check_of(record, n):
    return next(c for c in record['checks'] if c['check'] == n)


class Base(unittest.TestCase):
    def assert_form(self, r):
        self.assertEqual(tuple(r), launcher.START_KEYS)
        self.assertTrue(all(isinstance(f, str) for f in r['findings']))

    def closed(self, r, result='refused'):
        self.assert_form(r)
        self.assertEqual(r['result'], result)
        self.assertTrue(r['findings'])
        self.assertIsNone(r['environment'])
        self.assertIsNone(r['fencing_token'])


class TASK086AC1Arguments(Base):
    def test_each_wrong_argument_is_refused_before_any_call(self):
        """TASK-086 AC1: each argument out of form, a relative root such as "x/y" among them, gives "refused" with
        reason "argument" and zero callee calls; TASK-090 AC7: the five new callees out of form among them; TASK-117
        AC3: max_risk is no argument any more, and a read_declaration out of form is among them."""
        repo = world()
        later = NOW + datetime.timedelta(seconds=1)
        for over in ({'root': 'x/y'}, {'root': ''}, {'root': 1}, {'repo': 'x/y'}, {'repo': REPO + '/no-such-dir'},
                     {'task_id': 'TASK-x'}, {'task_id': None}, {'adapter_name': ''},
                     {'read_declaration': 'x'}, {'read_declaration': 1}, {'holder': ''}, {'recorder': None}, {'now': NOW.replace(tzinfo=None)},
                     {'now': NOW.replace(microsecond=5)}, {'expires_at': NOW}, {'expires_at': later.replace(
                         tzinfo=datetime.timezone(datetime.timedelta(hours=1)))}, {'read': 'x'}, {'start': 1},
                     {'end_session': 'y'}, {'read_sessions': 'x'}, {'session_leases': 1}, {'stored_reads': 'x'},
                     {'remove_reads': 2}, {'observe_gone': []}):
            c = calls_for(repo, approved_log(repo))
            r = launch(c, **over)
            self.closed(r)
            self.assertEqual(r['reason'], 'argument', over)
            self.assertEqual(c.calls, [], over)
            self.assertEqual(repo.calls, [], over)

    def test_the_repo_check_and_the_head_form(self):
        """TASK-086 AC1: launcher.TIMEOUT equals 30; repo is checked by gitread.form_error(repo, the HEAD form,
        launcher.TIMEOUT) before any callee call; the HEAD read is made with that form and launcher.TIMEOUT; every
        recorded read passes gitread.form_error."""
        self.assertEqual(launcher.TIMEOUT, 30)
        repo = world()
        c = calls_for(repo, approved_log(repo))
        seen = []
        real = gitread.form_error

        def recording(*args):
            seen.append((args, len(c.calls)))
            return real(*args)
        with mock.patch.object(gitread, 'form_error', recording):
            launch(c, stub=('start', 'end'))
        self.assertEqual(seen[0], ((REPO, HEAD_ARGS, 30), 0))
        self.assertEqual(repo.calls[0], (REPO, HEAD_ARGS, 30))
        for call in repo.calls:
            self.assertIsNone(gitread.form_error(*call), call)

    def test_a_head_answer_out_of_form(self):
        """TASK-086 AC1: a HEAD answer that is not exactly 40 lowercase hex characters gives "refused" with no later
        callee call."""
        for out in (b'abc\n', b'A' * 40 + b'\n', b'', 'x'):
            repo = world()
            c = calls_for(repo, approved_log(repo), read=lambda r, a, t=30, out=out: ok(out))
            r = launch(c, stub=('start', 'end'))
            self.closed(r)
            self.assertEqual(r['reason'], 'head')
            self.assertEqual(c.names(), ['expire', 'read'])

    def test_every_callee_defaults_at_call_time(self):
        """TASK-086 AC1: with no callee given, each default is the named function looked up at call time (a patch
        after import is the one called)."""
        repo = world()
        marks = []

        def mark(name):
            def raising(*args, **kwargs):
                marks.append(name)
                raise LookupError(name)
            return raising
        for module, name, reason in ((writer, 'expire_leases', 'expire'), (gitread, 'run', 'head'),
                                     (writer, 'read_log', 'log')):
            with mock.patch.object(writer, 'expire_leases', lambda root, now: []), \
                    mock.patch.object(gitread, 'run', repo), mock.patch.object(module, name, mark(name)):
                r = launcher.start(ROOT, REPO, TASK, 'unit', 'agent-1', REC, NOW, LATER,
                                   read_declaration=absent_declaration)
            self.closed(r)
            self.assertEqual(r['reason'], reason)
        self.assertEqual(marks, ['expire_leases', 'run', 'read_log'])
        log = approved_log(repo)
        for module, name in ((adapter, 'start'), (execution, 'task_view')):
            seen = []
            with mock.patch.object(module, name, lambda *a, **k: seen.append(name) or ({} if name == 'start'
                                                                                         else None)):
                c = calls_for(repo, log)
                kw = {n: c.make(n, real) for n, real in STORE}
                kw['read'] = c.make('read', gitread.run)
                kw['read_declaration'] = absent_declaration
                launcher.start(ROOT, REPO, TASK, 'unit', 'agent-1', REC, NOW, LATER, **kw)
            self.assertEqual(seen, [name])


class TASK086AC1BaseTip(Base):
    OTHER = 'b' * 40

    def reading(self, repo, tip_answer):
        """A read that answers the exact base form with tip_answer (a callable or a value) and every other call as the
        repository stand-in does."""
        def read(r, a, t=30):
            if list(a) == BASE_ARGS:
                return tip_answer(r, a, t) if callable(tip_answer) else tip_answer
            return repo(r, a, t)
        return read

    def test_a_base_out_of_form_is_refused_at_the_argument_check(self):
        """TASK-086 AC1: a base that is not a str or is out of the strict base-name rule gives "refused" with reason
        "argument" and a finding that begins "argument: base ", with no callee called and no git read."""
        for bad in ('', 'a..b', '-x', 'a//b', 'a/', '/a', 'a.lock', 'a/.b', 'a.', 'x@{1}', 'x' * 101, 'a b', 'a\n', 3,
                    None, b'main'):
            repo = world()
            c = calls_for(repo, approved_log(repo))
            r = launch(c, stub=('start', 'end'), base=bad)
            self.assert_form(r)
            self.assertEqual((r['result'], r['reason']), ('refused', 'argument'), bad)
            self.assertTrue(r['findings'][0].startswith('argument: base '), r['findings'])
            self.assertEqual(c.names(), [], bad)
            self.assertEqual(repo.calls, [], bad)

    def test_the_base_ref_is_read_after_head_and_before_the_log(self):
        """TASK-086 AC1 and TASK-086 AC2: the default base reads the exact form for refs/heads/main once, right after the
        HEAD read and before read_log, with the gitread timeout, and the form passes gitread.form_error."""
        repo = world()
        c = calls_for(repo, approved_log(repo))
        launch(c, stub=('start', 'end'))
        self.assertEqual(repo.calls[0], (REPO, HEAD_ARGS, 30))
        self.assertEqual(repo.calls[1], (REPO, BASE_ARGS, 30))
        self.assertEqual(repo.calls[2], (REPO, CONFIG_ARGS, 30))
        self.assertEqual(repo.calls[3], (REPO, STATUS_ARGS, 30))
        self.assertEqual(c.names()[:7], ['expire', 'read', 'read', 'read', 'read', 'read_declaration', 'read_log'])
        self.assertIsNone(gitread.form_error(*repo.calls[1]))

    def test_a_non_default_base_names_its_own_ref(self):
        """TASK-086 AC1: base="release/1.2", "main", "release-1.2", "feature/x" and "a_b" read refs/heads/<base>, and the
        start goes on when that ref is HEAD: the reason is neither "argument" nor "base" and adapter.start is called."""
        for name in ('release/1.2', 'main', 'release-1.2', 'feature/x', 'a_b'):
            repo = world()
            seen = []
            other = ['rev-parse', '--verify', '--end-of-options', 'refs/heads/' + name]

            def read(r, a, t=30, repo=repo, other=other, seen=seen):
                if list(a) == other:
                    seen.append(list(a))
                    return ok((repo.head + '\n').encode('ascii'))
                return repo(r, a, t)
            c = calls_for(repo, approved_log(repo), read=read)
            r = launch(c, stub=('start', 'end'), base=name)
            self.assertEqual(seen, [other], name)
            self.assertNotIn(r['reason'], ('argument', 'base'), name)
            self.assertIn('start', c.names(), name)

    def test_a_head_that_is_not_the_tip_is_not_granted(self):
        """TASK-086 AC1 and TASK-086 AC5b: a HEAD that differs from the base ref's answer gives "not granted" with
        reason "base", a finding "base: HEAD <head> is not the tip <tip> of refs/heads/main", the head in head_commit, no
        session row and no read_log, held, start or end."""
        repo = world()
        c = calls_for(repo, approved_log(repo), read=self.reading(repo, ok((self.OTHER + '\n').encode('ascii'))))
        r = launch(c, stub=('start', 'end'))
        self.assert_form(r)
        self.assertEqual((r['result'], r['reason']), ('not granted', 'base'))
        self.assertIn('base: HEAD %s is not the tip %s of refs/heads/main' % (repo.head, self.OTHER), r['findings'])
        self.assertEqual(r['head_commit'], repo.head)
        self.assertEqual(c.names(), ['expire', 'read', 'read'])
        self.assertIsNone(r['environment'])

    def test_an_unreadable_base_ref_is_refused(self):
        """TASK-086 AC1: a base read with no answer, a non-zero exit, a non-bytes output, a non-ASCII answer or an answer
        that is not 40 lowercase hex characters gives "refused" with reason "base" and a finding that begins "base:", with
        the head in head_commit and no later callee."""
        answers = [{'exit': 128, 'out': b'', 'err': b'fatal', 'error': None}, {'exit': 0, 'out': 'x', 'err': b'',
                                                                              'error': None},
                   {'exit': None, 'out': b'', 'err': b'', 'error': 'refused'}, 'x', None,
                   ok(b'\xff\xfe\n'), ok(b'abc\n'), ok(b''), ok(b'A' * 40 + b'\n')]
        for answer in answers:
            repo = world()
            c = calls_for(repo, approved_log(repo), read=self.reading(repo, answer))
            r = launch(c, stub=('start', 'end'))
            self.assert_form(r)
            self.assertEqual((r['result'], r['reason']), ('refused', 'base'), answer)
            self.assertTrue(r['findings'][0].startswith('base:'), r['findings'])
            self.assertEqual(r['head_commit'], repo.head)
            self.assertEqual(c.names(), ['expire', 'read', 'read'], answer)

    def test_a_raise_in_the_base_read_is_refused(self):
        """TASK-086 AC1: the HEAD read succeeds and the base read raises: "refused" with reason "base" and no later
        callee (the step variable is "base")."""
        def boom(r, a, t=30):
            raise RuntimeError('x')
        repo = world()
        c = calls_for(repo, approved_log(repo), read=self.reading(repo, boom))
        r = launch(c, stub=('start', 'end'))
        self.assert_form(r)
        self.assertEqual((r['result'], r['reason']), ('refused', 'base'))
        self.assertEqual(c.names(), ['expire', 'read', 'read'])


    def test_a_raise_in_the_inputs_reads_is_refused(self):
        """TASK-086 AC4 and TASK-086 AC7 (amended by TASK-109 and TASK-110): the HEAD read, the base read, the config
        read and the status read succeed and the next read, the first of the inputs reads, raises: "refused", with
        adapter.start and adapter.end not called."""
        repo = world()
        seen = []

        def read(r, a, t=30):
            seen.append(list(a))
            if len(seen) > 4:
                raise RuntimeError('x')
            return repo(r, a, t)
        c = calls_for(repo, approved_log(repo), read=read)
        r = launch(c, stub=('start', 'end'))
        self.assert_form(r)
        self.assertEqual(r['result'], 'refused')
        self.assertEqual(seen[:4], [HEAD_ARGS, BASE_ARGS, CONFIG_ARGS, STATUS_ARGS])
        self.assertEqual(c.of('start'), [])
        self.assertEqual(c.of('end'), [])
        self.assertEqual(r['reason'], 'inputs')


class TASK086AC1Root(Base):
    """The step "root" (task TASK-109; specification 7 revision 7, section 5)."""

    def run_with(self, status, **over):
        repo = world()
        repo.status = status
        c = calls_for(repo, approved_log(repo))
        r = launch(c, stub=('start', 'end'), **over)
        self.assert_form(r)
        return repo, c, r

    def test_the_status_read_is_fourth_and_built_from_the_state_directory(self):
        """TASK-086 AC1 (amended by TASK-109 and TASK-110): the status read is the fourth read, after HEAD, the base tip
        and the config read and before read_log, with the gitread timeout; the whole argument list passed to read
        equals list(gitread.STATUS_HEAD) + [':(exclude)' + writer.STATE_DIR], and it passes gitread.form_error."""
        repo, c, r = self.run_with(b'')
        self.assertEqual(repo.calls[3], (REPO, list(gitread.STATUS_HEAD) + [':(exclude)' + writer.STATE_DIR], 30))
        self.assertEqual([a for _, a, _ in repo.calls[:4]], [HEAD_ARGS, BASE_ARGS, CONFIG_ARGS, STATUS_ARGS])
        self.assertIsNone(gitread.form_error(*repo.calls[3]))
        self.assertEqual(c.names()[:7], ['expire', 'read', 'read', 'read', 'read', 'read_declaration', 'read_log'])
        self.assertEqual(sum(1 for _, a, _ in repo.calls if a[0] == 'status'), 1)

    def test_a_clean_root_goes_on(self):
        """TASK-086 AC1 (amended by TASK-109): a clean answer (no error, exit 0, no output) goes on: the reason is not
        "root" and adapter.start is called."""
        repo, c, r = self.run_with(b'')
        self.assertNotEqual(r['reason'], 'root')
        self.assertIn('start', c.names())

    def test_an_entry_is_not_granted_with_the_count_and_the_paths(self):
        """TASK-086 AC1 (amended by TASK-109): an unstaged change, a staged one and an untracked file give "not granted"
        with reason "root", the count, one finding per path as the repr of its bytes in git's order, the head in
        head_commit, no environment and no callee after the third read."""
        repo, c, r = self.run_with(b' M src/a.py\0A  b.txt\0?? c d.md\0')
        self.assertEqual((r['result'], r['reason']), ('not granted', 'root'))
        self.assertEqual(r['findings'], [
            'root: 3 entries (changes against HEAD in the index or the working tree, or untracked files)',
            "root: b'src/a.py'", "root: b'b.txt'", "root: b'c d.md'"])
        self.assertEqual(r['head_commit'], repo.head)
        self.assertIsNone(r['environment'])
        self.assertEqual(c.names(), ['expire', 'read', 'read', 'read', 'read'])

    def test_the_findings_show_at_most_twenty_paths(self):
        """TASK-086 AC1 (amended by TASK-109): 25 entries give the count 25 and the first 20 paths only."""
        out = b''.join(b'?? f%02d\0' % i for i in range(25))
        repo, c, r = self.run_with(out)
        self.assertEqual((r['result'], r['reason']), ('not granted', 'root'))
        self.assertEqual(len(r['findings']), 21)
        self.assertTrue(r['findings'][0].startswith('root: 25 entries ('), r['findings'][0])
        self.assertEqual(r['findings'][1:], ["root: b'f%02d'" % i for i in range(20)])

    def test_a_path_with_a_newline_or_a_non_ascii_byte_is_shown_as_bytes(self):
        """TASK-086 AC1 (amended by TASK-109): a path holding a newline, a UTF-8 name and a byte that is not UTF-8 are
        shown as the repr of the path bytes, with no decoding."""
        repo, c, r = self.run_with(b'?? a\nb\0 M \xc3\xa9.md\0?? \xff\xfe\0')
        self.assertEqual((r['result'], r['reason']), ('not granted', 'root'))
        self.assertEqual(r['findings'][1:], ["root: b'a\\nb'", "root: b'\\xc3\\xa9.md'", "root: b'\\xff\\xfe'"])

    def test_every_status_pair_is_an_entry(self):
        """TASK-086 AC1 (amended by TASK-109): the unmerged pairs, the renamed, copied and type-changed ones and the
        untracked and ignored marks are entries and give "not granted" with reason "root"."""
        for pair in (' M', 'M ', 'MM', 'A ', 'AM', ' D', 'D ', 'R ', 'C ', 'T ', ' T', 'UU', 'AA', 'DD', 'AU', 'UD', '??',
                     '!!'):
            repo, c, r = self.run_with(pair.encode('ascii') + b' x\0')
            self.assertEqual((r['result'], r['reason']), ('not granted', 'root'), pair)

    def test_an_answer_out_of_form_is_refused(self):
        """TASK-086 AC1 (amended by TASK-109): a read with no mapping, an error, a non-zero exit, output that is not
        bytes, an unterminated answer, an entry out of form, an empty path and a branch entry give "refused" with
        reason "root", a finding that begins "root:", the head in head_commit and no callee after the third read."""
        outs = [b'?? a', b' M a', b'\0', b'?? a\0\0', b' M\0', b'M \0', b'XX a\0', b'?? a\0X\0', b'## main\0',
                b'##x\0', b'M  a\0## main\0', b'?Ma\0', b'\xff\xff a\0', b'?? a\0?? b',
                b'?X a\0', b'??xa\0', b'?? \0', b'X  a\0']
        answers = [ok(o) for o in outs]
        answers += [{'exit': 128, 'out': b'', 'err': b'fatal', 'error': None},
                    {'exit': 0, 'out': 'x', 'err': b'', 'error': None},
                    {'exit': None, 'out': b'', 'err': b'', 'error': 'refused'}, 'x', None, 3, [],
                    {'exit': 0, 'out': None, 'err': b'', 'error': None}, {'exit': 1, 'out': b'', 'error': None},
                    {'exit': 0, 'out': b'?? a\0', 'error': 'timeout'}]
        for answer in answers:
            repo = world()
            repo.status = lambda r, a, t, answer=answer: answer
            c = calls_for(repo, approved_log(repo))
            r = launch(c, stub=('start', 'end'))
            self.assert_form(r)
            self.assertEqual((r['result'], r['reason']), ('refused', 'root'), answer)
            self.assertTrue(r['findings'][0].startswith('root:'), r['findings'])
            self.assertEqual(r['head_commit'], repo.head)
            self.assertEqual(c.names(), ['expire', 'read', 'read', 'read', 'read'], answer)
            self.assertIsNone(r['environment'])

    def test_a_raise_in_the_status_read_is_refused(self):
        """TASK-086 AC1 and TASK-086 AC7 (amended by TASK-109): the HEAD and base reads succeed and the status read
        raises: "refused" with reason "root" and no later callee (the step variable is "root")."""
        def boom(r, a, t=30):
            raise RuntimeError('x')
        repo = world()
        repo.status = boom
        c = calls_for(repo, approved_log(repo))
        r = launch(c, stub=('start', 'end'))
        self.assert_form(r)
        self.assertEqual((r['result'], r['reason']), ('refused', 'root'))
        self.assertEqual(c.names(), ['expire', 'read', 'read', 'read', 'read'])

    def test_the_gone_records_still_come_first_and_no_session_is_opened(self):
        """TASK-086 AC2 (amended by TASK-109): a non-grant at "root" calls neither read_log, held, start nor end, and the
        gone sessions' lines and the expiry still ran before it."""
        repo, c, r = self.run_with(b'?? x\0')
        self.assertEqual(c.names()[0], 'expire')
        for name in ('read_log', 'held', 'start', 'end', 'start_session', 'end_session'):
            self.assertEqual(c.of(name), [], name)

    def test_the_parser_is_pure_and_total(self):
        """TASK-086 AC1 (amended by TASK-109): _root_entries gives ([], None) for no output, the path bytes of each
        entry in order, and a finding, never a raise, for anything out of form or not bytes."""
        self.assertEqual(launcher._root_entries(b''), ([], None))
        self.assertEqual(launcher._root_entries(b' M a\0?? b c\0'), ([b'a', b'b c'], None))
        for bad in (b'x', b' M a', b'\0', b'## a\0', b'?X a\0', b'??xa\0', b'?? \0', b'X  a\0',
                    None, 'x', 3, bytearray(b' M a\0'), [b' M a\0']):
            entries, found = launcher._root_entries(bad)
            self.assertIsNone(entries, bad)
            self.assertTrue(found.startswith('root:'), bad)


class TASK086AC1RootConfig(Base):
    """The configuration read of the step "root" (task TASK-110; specification 7 revision 8, section 5)."""

    FAKE = b'zz-fake-value-not-a-secret'

    def run_with(self, config, status=b'', **over):
        repo = world()
        repo.config = config
        repo.status = status
        c = calls_for(repo, approved_log(repo))
        r = launch(c, stub=('start', 'end'), **over)
        self.assert_form(r)
        return repo, c, r

    def shown(self, r):
        return repr(r) + ' '.join(r['findings'])

    def test_the_config_read_is_third_and_the_status_read_fourth(self):
        """TASK-086 AC1 and TASK-086 AC2 (amended by TASK-110): the config read is the third read, after HEAD and the base
        tip, with the gitread timeout; its argument list equals list(gitread.CONFIG_LIST) and passes gitread.form_error;
        the status read is the fourth, then read_log; each form is read once."""
        repo, c, r = self.run_with(b'')
        self.assertEqual(repo.calls[2], (REPO, list(gitread.CONFIG_LIST), 30))
        self.assertIsNone(gitread.form_error(*repo.calls[2]))
        self.assertEqual([a for _, a, _ in repo.calls[:4]], [HEAD_ARGS, BASE_ARGS, CONFIG_ARGS, STATUS_ARGS])
        self.assertEqual(sum(1 for _, a, _ in repo.calls if a[0] == 'config'), 1)
        self.assertEqual(sum(1 for _, a, _ in repo.calls if a[0] == 'status'), 1)
        self.assertEqual(c.names()[:7], ['expire', 'read', 'read', 'read', 'read', 'read_declaration', 'read_log'])

    def test_a_clean_configuration_goes_on_to_the_status_read(self):
        """TASK-086 AC1 (amended by TASK-110): no output, and records none of which is a refused key (a valueless key, a
        value that holds the word filter. and keys that only look like the refused ones among them), let the status
        read run and the start go on."""
        for config in (b'', b'core.bare\nfalse\0', b'core.bare\0user.name\nA B\0', b'user.name\nfilter.x\0',
                       b'filterx.a\n1\0core.worktreex\n/x\0xfilter.a\n1\0core.bare\ntrue\0filter\nx\0',
                       b'core.worktree.x\ny\0', b'a.filter.b\nz\0'):
            repo, c, r = self.run_with(config)
            self.assertNotEqual(r['reason'], 'root', config)
            self.assertIn('start', c.names(), config)
            self.assertEqual(sum(1 for _, a, _ in repo.calls if a[0] == 'status'), 1, config)

    def test_a_filter_key_and_a_work_tree_key_are_not_granted_with_the_count_and_the_keys(self):
        """TASK-086 AC1 (amended by TASK-110): a filter key and a core.worktree key give "not granted" with reason
        "root", the count of both kinds together, one finding per key as the repr of its bytes in output order and
        never a value, the head in head_commit, no environment and no later callee: the status is not read."""
        config = b'core.bare\nfalse\0filter.lfs.clean\n' + self.FAKE + b'\0core.worktree\n/elsewhere\0'
        repo, c, r = self.run_with(config, status=b'?? x\0')
        self.assertEqual((r['result'], r['reason']), ('not granted', 'root'))
        self.assertEqual(r['findings'], ['root: configuration names filter driver or work tree keys: 2',
                                         "root: key b'filter.lfs.clean'", "root: key b'core.worktree'"])
        self.assertEqual(r['head_commit'], repo.head)
        self.assertIsNone(r['environment'])
        self.assertEqual(c.names(), ['expire', 'read', 'read', 'read'])
        self.assertEqual(sum(1 for _, a, _ in repo.calls if a[0] == 'status'), 0)
        for name in ('read_log', 'held', 'start', 'end', 'start_session', 'end_session'):
            self.assertEqual(c.of(name), [], name)

    def test_the_keys_are_matched_without_case_a_valueless_key_and_a_newline_in_a_value(self):
        """TASK-086 AC1 (amended by TASK-110): a key in other case, a key with no value and a key whose value holds a
        newline are matched on the key text (up to the first newline) and shown as the key's bytes."""
        for config, key in ((b'FILTER.Lfs.Clean\nx\0', b'FILTER.Lfs.Clean'), (b'Core.WorkTree\n/x\0', b'Core.WorkTree'),
                            (b'filter.a\0', b'filter.a'), (b'core.worktree\0', b'core.worktree'),
                            (b'filter.a\nline1\nline2\0', b'filter.a'), (b'core.WORKTREE\n\n\0', b'core.WORKTREE')):
            repo, c, r = self.run_with(config)
            self.assertEqual((r['result'], r['reason']), ('not granted', 'root'), config)
            self.assertEqual(r['findings'][1:], ['root: key ' + repr(key)], config)

    def test_the_findings_show_at_most_twenty_keys_each_cut_to_eighty_bytes(self):
        """TASK-086 AC1 (amended by TASK-110): 25 refused keys give the count 25 and the first 20 keys only, in output
        order; a key of 100 bytes is cut to its first 80 bytes before the repr."""
        config = b''.join(b'filter.k%02d\nv\0' % i for i in range(25))
        repo, c, r = self.run_with(config)
        self.assertEqual(len(r['findings']), 21)
        self.assertEqual(r['findings'][0], 'root: configuration names filter driver or work tree keys: 25')
        self.assertEqual(r['findings'][1:], ["root: key b'filter.k%02d'" % i for i in range(20)])
        long_key = b'filter.' + b'x' * 93
        repo, c, r = self.run_with(long_key + b'\nv\0')
        self.assertEqual(r['findings'][1:], ['root: key ' + repr(long_key[:80])])

    def test_no_value_of_the_configuration_is_in_a_finding(self):
        """TASK-086 AC1 (amended by TASK-110): a value that looks like a credential, obviously fake, appears in no finding
        and no field of the result, for a not-granted answer and for each refused answer."""
        outs = [b'filter.a\n' + self.FAKE + b'\0', b'core.worktree\n' + self.FAKE + b'\0',
                b'core.bare\n' + self.FAKE + b'\0filter.a\n' + self.FAKE + b'\0\0', b'filter.a\n' + self.FAKE,
                b'\n' + self.FAKE + b'\0filter.a\n' + self.FAKE + b'\0', b'core.bare\n' + self.FAKE + b'\0']
        for out in outs:
            repo, c, r = self.run_with(out)
            self.assertNotIn('zz-fake-value', self.shown(r), 'a value of the configuration answer is in the result')
        repo, c, r = self.run_with(lambda repo, args, timeout: {'exit': 1, 'out': self.FAKE, 'err': self.FAKE,
                                                                'error': None})
        self.assertEqual((r['result'], r['reason']), ('refused', 'root'))
        self.assertNotIn('zz-fake-value', self.shown(r))

    def test_an_answer_out_of_form_is_refused_with_a_fixed_text(self):
        """TASK-086 AC1 (amended by TASK-110): a read with no mapping, an error, a non-zero exit, output that is not
        bytes, a non-empty output not ending in a NUL and a record with an empty key give "refused" with reason "root",
        a finding that begins "root:", the head in head_commit and no callee after the third read; a refused key
        followed by an empty record, or with no final NUL, is refused too, whatever keys the answer holds."""
        text_not_bytes = ['root: the configuration answer is not bytes']
        text_no_nul = ['root: the configuration answer does not end in NUL']
        text_empty_key = ['root: the configuration answer has an empty key']
        cases = [(ok(b'a\nb'), text_no_nul), (ok(b'filter.a\nx'), text_no_nul), (ok(b'filter.a'), text_no_nul),
                 (ok(b'\0'), text_empty_key), (ok(b'a\nb\0\0'), text_empty_key), (ok(b'\nv\0'), text_empty_key),
                 (ok(b'filter.a\nx\0\0'), text_empty_key), (ok(b'core.worktree\n/x\0\nv\0'), text_empty_key),
                 (ok(b'a\0\0filter.a\0'), text_empty_key),
                 ({'exit': 0, 'out': 'x', 'err': b'', 'error': None}, text_not_bytes),
                 ({'exit': 0, 'out': None, 'err': b'', 'error': None}, text_not_bytes),
                 ({'exit': 0, 'out': bytearray(b'filter.a\0'), 'err': b'', 'error': None}, text_not_bytes),
                 ({'exit': 0, 'err': b'', 'error': None}, text_not_bytes)]
        for answer, want in cases:
            repo, c, r = self.run_with(lambda repo, args, timeout, answer=answer: answer)
            self.assertEqual((r['result'], r['reason']), ('refused', 'root'), answer)
            self.assertEqual(r['findings'], want, answer)
            self.assertEqual(r['head_commit'], repo.head)
            self.assertIsNone(r['environment'])
            self.assertEqual(c.names(), ['expire', 'read', 'read', 'read'], answer)
        for answer in ({'exit': 128, 'out': b'', 'err': b'fatal', 'error': None},
                       {'exit': None, 'out': b'', 'err': b'', 'error': 'refused'}, 'x', None, 3, [],
                       {'exit': 1, 'out': b'', 'error': None}, {'exit': 0, 'out': b'', 'error': 'timeout'}):
            repo, c, r = self.run_with(lambda repo, args, timeout, answer=answer: answer)
            self.assertEqual((r['result'], r['reason']), ('refused', 'root'), answer)
            self.assertEqual(len(r['findings']), 1, answer)
            self.assertTrue(r['findings'][0].startswith('root: git config gave no answer ('), r['findings'])
            self.assertEqual(c.names(), ['expire', 'read', 'read', 'read'], answer)
        repo, c, r = self.run_with(lambda repo, args, timeout: 'x')
        self.assertEqual(r['findings'], ["root: git config gave no answer ('str')"])
        repo, c, r = self.run_with(lambda repo, args, timeout: {'exit': 1, 'out': b'', 'error': None})
        self.assertEqual(r['findings'], ['root: git config gave no answer ((None, 1))'])

    def test_a_raise_in_the_config_read_is_refused(self):
        """TASK-086 AC1 and TASK-086 AC7 (amended by TASK-110): the HEAD and base reads succeed and the config read
        raises: "refused" with reason "root" and no later callee (the step variable is "root")."""
        def boom(r, a, t=30):
            raise RuntimeError('x')
        repo, c, r = self.run_with(boom)
        self.assertEqual((r['result'], r['reason']), ('refused', 'root'))
        self.assertEqual(c.names(), ['expire', 'read', 'read', 'read'])
        self.assertEqual(sum(1 for _, a, _ in repo.calls if a[0] == 'status'), 0)

    def test_the_parser_is_pure_and_total(self):
        """TASK-086 AC1 (amended by TASK-110): _config_keys gives ([], None) for no output, the refused keys in output
        order for a clean form, and a finding that holds no byte of the answer, never a raise, for anything out of form
        or not bytes."""
        self.assertEqual(launcher._config_keys(b''), ([], None))
        self.assertEqual(launcher._config_keys(b'a\nb\0'), ([], None))
        self.assertEqual(launcher._config_keys(b'filter.x\nv\0Core.Worktree\0core.bare\n1\0filter.y\0'),
                         ([b'filter.x', b'Core.Worktree', b'filter.y'], None))
        for bad in (b'x', b'filter.a', b'\0', b'a\0\0', b'\nv\0', None, 'x', 3, bytearray(b'a\0'), [b'a\0']):
            keys, found = launcher._config_keys(bad)
            self.assertIsNone(keys, bad)
            self.assertIn(found, ('root: the configuration answer is not bytes',
                                  'root: the configuration answer does not end in NUL',
                                  'root: the configuration answer has an empty key'), 'the finding is not a fixed text')


class TASK086AC2Order(Base):
    def test_the_order(self):
        """TASK-086 AC2 (amended by TASK-109 and TASK-110, and by TASK-117 AC3): expire, then read (HEAD), then read (the
        base ref), then read (the configuration), then read (the status of the root), then read_declaration (the step
        "declaration", between "root" and "log"), then read_log, then held (the one held call before adapter.start),
        then the readers' reads, then adapter.start, then adapter.end when no token was granted and the row was
        opened; execute's own second read_log and held calls come inside adapter.start. TASK-090 AC7: with a recording
        read_sessions, it is called first, before expire."""
        repo = world()
        c = calls_for(repo, approved_log(repo), start=ended(), end=ended())
        r = launch(c, stub=('start', 'end'))
        names = c.names()
        self.assertEqual(names[:8], ['expire', 'read', 'read', 'read', 'read', 'read_declaration', 'read_log', 'held'])
        self.assertEqual(names[-2:], ['start', 'end'])
        self.assertTrue(set(names[8:-2]) == {'read'} and len(names) > 10, names)
        self.assert_form(r)
        self.assertEqual(r['result'], 'not granted')
        c = calls_for(repo, approved_log(repo))
        r = launch(c, max_risk=None)
        names = c.names()
        self.assertEqual(names[:8], ['expire', 'read', 'read', 'read', 'read', 'read_declaration', 'read_log', 'held'])
        first = names.index('start_session')
        self.assertEqual(names[first:first + 3], ['start_session', 'read_log', 'held'])
        self.assertEqual(names[-1], 'end_session')
        self.assertEqual(r['result'], 'not granted')
        c = calls_for(repo, approved_log(repo), read_sessions=store(value=[]))
        r = launch(c, max_risk=None, read_sessions=c.make('read_sessions', writer.read_sessions))
        self.assertEqual(c.names()[:9], ['read_sessions', 'expire', 'read', 'read', 'read', 'read', 'read_declaration',
                                         'read_log', 'held'])
        self.assertEqual(c.of('read_sessions')[0][1], (ROOT, TASK))
        self.assertEqual(r['result'], 'not granted')

    def test_nothing_after_a_refusal_before_the_start(self):
        """TASK-086 AC2: after any refusal or "not granted" before adapter.start, no later callee is called; expire
        runs first in every run that reaches it."""
        repo = world()
        for answers, last in (({'expire': 'x'}, 'expire'), ({'read_log': lambda root: 'x'}, 'read_log'),
                              ({'held': LEASE}, 'held')):
            c = calls_for(repo, approved_log(repo), **answers)
            r = launch(c, stub=('start', 'end'))
            self.assertIn(r['result'], ('refused', 'not granted'))
            self.assertEqual(c.names()[0], 'expire')
            self.assertEqual(c.names()[-1], last)


class TASK086AC3SessionId(Base):
    def test_the_id(self):
        """TASK-086 AC3: "launch-" followed by the first 32 hex characters of the SHA-256 of "<task_id>
        <now.isoformat()> <head_commit>"; of the form [A-Za-z0-9._-]{1,128} with no "/"; the same arguments give the
        same id."""
        repo = world()
        c = calls_for(repo, approved_log(repo), start=ended(), end=ended())
        r = launch(c, stub=('start', 'end'))
        want = 'launch-' + hashlib.sha256(('%s %s %s' % (TASK, NOW.isoformat(), repo.head)).encode('utf-8')
                                          ).hexdigest()[:32]
        self.assertEqual(r['session_id'], want)
        self.assertEqual(c.of('start')[0][1][2], want)
        self.assertRegex(want, r'\Alaunch-[0-9a-f]{32}\Z')
        self.assertNotIn('/', want)
        self.assertEqual(launcher.session_id_of(TASK, NOW, repo.head), want)
        self.assertEqual(r['head_commit'], repo.head)

    def test_a_started_session_is_refused(self):
        """TASK-086 AC3: a start_session refusal ("started") gives "refused" with adapter.end not called."""
        repo = world()
        c = calls_for(repo, approved_log(repo), start_session=store('refused', 'started'))
        r = launch(c, stub=('end',))
        self.closed(r)
        self.assertEqual(r['reason'], 'session')
        self.assertEqual(c.of('end'), [])
        self.assertEqual(c.of('end_session'), [])


class TASK086AC4Inputs(Base):
    def test_the_inputs_given_to_the_start(self):
        """TASK-086 AC4: the inputs' keys equal resume_check.INPUT_KEYS; the ten and the seven are git_inputs' and
        log_inputs' at HEAD; task_id, runtime, log_seq, task_state and approved_contract_hash as given; code_sha256 is
        the SHA-256 of the stand-in resume_check.py text (non-ASCII) as UTF-8, not as latin-1 or UTF-16."""
        repo = world()
        log = approved_log(repo)
        c = calls_for(repo, log, start=ended(), end=ended())
        launch(c, max_risk='high', stub=('start', 'end'))
        args = c.of('start')[0][1]
        inputs, code = args[4], args[5]
        self.assertEqual(set(inputs), set(resume_check.INPUT_KEYS))
        given = resume_inputs.git_inputs(REPO, repo.head, TASK, log.data, repo)[0]
        logged = resume_log_inputs.log_inputs(REPO, repo.head, TASK, log.data, repo)[0]
        for key in resume_inputs.KEYS:
            self.assertEqual(inputs[key], given[key], key)
        for key in resume_log_inputs.KEYS:
            self.assertEqual(inputs[key], logged[key], key)
        view = execution.task_view(log.data, ROOT, TASK, NOW, held=lambda root, task: None)[0]
        self.assertEqual(inputs['task_id'], TASK)
        self.assertEqual(inputs['runtime'], {'adapter': 'unit', 'max_risk': 'high'})
        for key in ('log_seq', 'task_state', 'approved_contract_hash'):
            self.assertEqual(inputs[key], view[key], key)
        self.assertNotEqual(RC_TEXT.encode('utf-8'), RC_TEXT.encode('ascii', 'replace'))
        self.assertEqual(code, hashlib.sha256(RC_TEXT.encode('utf-8')).hexdigest())
        self.assertNotEqual(code, hashlib.sha256(RC_TEXT.encode('latin-1', 'replace')).hexdigest())
        self.assertNotEqual(code, hashlib.sha256(RC_TEXT.encode('utf-16')).hexdigest())

    def test_a_readers_findings_give_a_refusal(self):
        """TASK-086 AC4: a reader's findings give "refused" with no adapter.start call."""
        repo = world()
        log = approved_log(repo)
        repo.head = repo.commit({'other.txt': 'x\n'}, [repo.head], 'no contract')
        c = calls_for(repo, log)
        r = launch(c, stub=('start', 'end'))
        self.closed(r)
        self.assertEqual(r['reason'], 'inputs')
        self.assertEqual(c.of('start'), [])
        self.assertEqual(c.of('end'), [])


class TASK086AC5Grant(Base):
    def test_the_grant_path(self):
        """TASK-086 AC5: with the real resume_check, a Repo-style stand-in read and writer stand-ins, a declared
        max_risk covering the task risk, a READY task with no dependency and inputs where no check fires but
        CONTINUE or CONTINUE_WITH give "granted" with the token and exactly the three environment names; adapter.end
        is not called."""
        repo = world()
        c = calls_for(repo, approved_log(repo))
        r = launch(c, max_risk='critical', stub=('end',))
        self.assert_form(r)
        self.assertEqual(r['result'], 'granted', r['findings'])
        self.assertIn(r['decision'], ('CONTINUE', 'CONTINUE_WITH'))
        self.assertEqual(r['fencing_token'], TOKEN)
        self.assertEqual(r['environment'], {'AIEOS_SESSION_ID': r['session_id'], 'AIEOS_ROOT': ROOT,
                                            'AIEOS_BASE': repo.head})
        self.assertEqual(c.of('end'), [])
        self.assertEqual(c.of('end_session'), [])
        self.assertEqual(len(c.of('grant')), 1)


class TASK086AC5bHeldAndState(Base):
    def test_a_held_task(self):
        """TASK-086 AC5b: a held lease unexpired after the expiry (task_view gives IN_PROGRESS) gives "not granted"
        with reason "held"; adapter.start, start_session, release and end are called zero times; no environment."""
        repo = world()
        c = calls_for(repo, approved_log(repo), held=LEASE)
        r = launch(c, stub=('start', 'end'))
        self.closed(r, 'not granted')
        self.assertEqual(r['reason'], 'held')
        for name in ('start', 'start_session', 'release', 'end', 'end_session'):
            self.assertEqual(c.of(name), [], name)

    def test_a_state_outside_ready_and_rework(self):
        """TASK-086 AC5b: a log giving DONE (or another state outside READY and REWORK) gives "not granted" with
        reason "state" and the state in its findings; nothing is started or ended; no environment."""
        repo = world()
        for more in (('task.done', {'decision_record': 'd'}), ('task.blocked', {'reason': 'dependency',
                                                                                'blocked_by': ['TASK-099']})):
            log = approved_log(repo).add(*more)
            c = calls_for(repo, log)
            r = launch(c, stub=('start', 'end'))
            self.closed(r, 'not granted')
            self.assertEqual(r['reason'], 'state')
            self.assertTrue(any(('DONE' in f) or ('BLOCKED' in f) for f in r['findings']), r['findings'])
            for name in ('start', 'start_session', 'release', 'end', 'end_session'):
                self.assertEqual(c.of(name), [], name)


class TASK086AC6NoGrant(Base):
    def record(self, c):
        return next(call[1][2] for call in c.of('append') if call[1][1] == 'decision.execution')

    def test_max_risk_null(self):
        """TASK-086 AC6, as TASK-117 AC3 changes it: a declaration read that finds no declaration (result absent,
        max_risk null; in the real path no policy file at the base), where checks 1 to 6 do not fire, gives check 7
        fired with "the runtime has no declaration", decision "STOP: runtime insufficient", "not granted", no
        environment, and adapter.end called once with no token; the read was made once with start's repo, the head and
        the adapter name, and no run."""
        repo = world()
        c = calls_for(repo, approved_log(repo), end=ended())
        r = launch(c, max_risk=None, stub=('end',))
        self.assertEqual([call[1:] for call in c.of('read_declaration')], [((REPO, repo.head, 'unit'), {})])
        self.closed(r, 'not granted')
        self.assertEqual(r['decision'], 'STOP: runtime insufficient')
        record = self.record(c)
        for n in range(1, 7):
            self.assertNotEqual(check_of(record, n)['status'], 'fired', n)
        self.assertEqual(check_of(record, 7)['status'], 'fired')
        self.assertEqual(check_of(record, 7)['detail'], 'the runtime has no declaration')
        self.assertEqual(len(c.of('end')), 1)
        self.assertIsNone(c.of('end')[0][1][3])
        self.assertEqual(c.of('grant'), [])

    def test_a_dependency_not_done(self):
        """TASK-086 AC6: a dependency whose state is not DONE, with a max_risk covering the task risk, gives check
        5's BLOCKED and no grant (DEF-0099's re-check on the grant path)."""
        repo = world(depends=('TASK-080',))
        c = calls_for(repo, approved_log(repo), end=ended())
        r = launch(c, max_risk='critical', stub=('end',))
        self.closed(r, 'not granted')
        self.assertEqual(r['decision'], 'BLOCKED')
        self.assertEqual(check_of(self.record(c), 5)['status'], 'fired')
        self.assertEqual(c.of('grant'), [])
        self.assertEqual(len(c.of('end')), 1)


class TASK086AC7FailingClosed(Base):
    def test_raising_and_out_of_form_answers(self):
        """TASK-086 AC7: a raising expire, read, read_log or reader, an expiry answer out of form, task_view's
        findings (a lease out of form, a log check_log refuses, no task.approved; no adapter.start and no
        adapter.end call) and a HEAD answer out of form give "refused" with findings and no environment; no call
        raises."""
        repo = world()
        good = approved_log(repo)
        head_calls = []

        def reader_raises(r, args, timeout=30):
            head_calls.append(args)
            if len(head_calls) > 1:
                raise RuntimeError('stand-in')
            return repo(r, args, timeout)
        cases = [({'expire': RuntimeError('x')}, good), ({'read': RuntimeError('x')}, good),
                 ({'read_log': RuntimeError('x')}, good), ({'read': reader_raises}, good), ({'expire': None}, good),
                 ({'held': {'task_id': TASK}}, good), ({}, Log()), ({}, types.SimpleNamespace(data=b'not a line\n')),
                 ({'read': lambda r, a, t=30: ok(b'nothex\n')}, good)]
        for answers, log in cases:
            del head_calls[:]
            c = calls_for(repo, log, **answers)
            r = launch(c, stub=('start', 'end'))
            self.closed(r)
            self.assertEqual(c.of('start'), [], answers)
            self.assertEqual(c.of('end'), [], answers)

    def test_the_start_and_end_refusals(self):
        """TASK-086 AC7: adapter.start refused before the session row ("argument" or "session", a raising
        start_session among them) gives "refused" with adapter.end not called; after it ("core") adapter.end is
        called once; adapter.end refused gives "refused"; no environment; no call raises."""
        repo = world()
        for reason, ends in (('argument', 0), ('session', 0), ('core', 1)):
            start = dict(ended('refused'), reason=reason)
            c = calls_for(repo, approved_log(repo), start=start, end=ended())
            r = launch(c, stub=('start', 'end'))
            self.closed(r)
            self.assertEqual(r['reason'], reason)
            self.assertEqual(len(c.of('end')), ends, reason)
        c = calls_for(repo, approved_log(repo), start_session=RuntimeError('x'))
        r = launch(c, stub=('end',))
        self.closed(r)
        self.assertEqual(r['reason'], 'session')
        self.assertEqual(c.of('end'), [])
        for end in (ended('refused'), RuntimeError('x'), 'x'):
            c = calls_for(repo, approved_log(repo), start=ended(), end=end)
            r = launch(c, stub=('start', 'end'))
            self.closed(r)
            self.assertEqual(r['reason'], 'end')
        c = calls_for(repo, approved_log(repo), start=RuntimeError('x'))
        r = launch(c, stub=('start', 'end'))
        self.closed(r)
        self.assertEqual(c.of('end'), [])


def end_with(c, token, **over):
    """launcher.end over TASK-089's signature (TASK-089 AC1), the record and the reads given by stand-ins: a row of
    the task holding the token when one is given (the fenced path), none otherwise (the gone path)."""
    rows = [dict(LEASE)] if token is not None else []
    record = {'result': 'written', 'reason': None, 'findings': [], 'record': None, 'core': None}
    kw = dict(release_lease_token=c.make('release_lease_token', writer.release_lease_token),
              end_session=c.make('end_session', writer.end_session),
              session_leases=lambda root, session_id, now: store(value={'ended': False, 'leases': rows}),
              stored_reads=lambda root, session_id, task_id: store(value=[]),
              remove_reads=lambda root, session_id, task_id: store(value=0),
              observe=lambda context, reads, now: record,
              observe_gone=lambda root, task_id, session_id, reads, reason, now, recorder: record)
    kw.update(over)
    return launcher.end(END_ROOT, TASK, 'session-1', token, NOW, ['src/aieos_bootstrap/mod.py'], [],
                        REC + ' session-1', **kw)


class TASK086AC8End(Base):
    def test_end_passes_the_result_through(self):
        """TASK-086 AC8, as TASK-089 AC1 and AC2 change it: end gives adapter.end's result in "end" for a token and
        for none, its findings kept; its callees default at call time; a release refused with a reason other than
        "none" or "token" gives "refused" and end_session is not called."""
        for token in (TOKEN, None):
            c = Calls({'release_lease_token': store(), 'end_session': store(value=[])})
            r = end_with(c, token)
            self.assertEqual(r['result'], 'done')
            self.assertEqual(r['end']['result'], 'done')
            self.assertEqual(len(c.of('release_lease_token')), 1 if token else 0)
        c = Calls({'release_lease_token': store('refused', 'other'), 'end_session': store(value=[])})
        r = end_with(c, TOKEN)
        self.assertEqual(r['result'], 'refused')
        self.assertTrue(r['findings'])
        self.assertEqual(c.of('end_session'), [])
        answer = dict(ended('refused'), findings=['kept'])
        with mock.patch.object(adapter, 'end', lambda *a, **k: answer):
            r = end_with(Calls(), None)
        self.assertEqual((r['result'], r['end']), ('refused', answer))
        self.assertIn('kept', r['findings'])
        with mock.patch.object(adapter, 'end', mock.Mock(side_effect=RuntimeError('x'))):
            r = end_with(Calls(), None)
        self.assertEqual((r['result'], tuple(r)), ('refused', launcher.END_KEYS))


class TASK086AC9TaskView(Base):
    def test_the_states(self):
        """TASK-086 AC9: READY after task.approved, IN_PROGRESS under an unexpired held lease, a state such as DONE
        returned as it is; log_seq the seq of the log's last line; approved_contract_hash the last task.approved's."""
        log = Log().approve('b' * 64).approve('c' * 64).approve('d' * 64, task_id='TASK-101')
        none = lambda root, task: None
        view = execution.task_view(log.data, ROOT, TASK, NOW, held=none)
        self.assertEqual(view, ({'task_state': 'READY', 'log_seq': 3, 'approved_contract_hash': 'c' * 64}, None))
        view = execution.task_view(log.data, ROOT, TASK, NOW, held=lambda root, task: LEASE)
        self.assertEqual(view[0]['task_state'], 'IN_PROGRESS')
        done = Log().approve().add('task.done', {'decision_record': 'd'})
        self.assertEqual(execution.task_view(done.data, ROOT, TASK, NOW, held=none)[0]['task_state'], 'DONE')

    def test_the_findings(self):
        """TASK-086 AC9: a lease out of form or expired, a log check_log refuses and no task.approved give findings;
        no call raises."""
        log = Log().approve()
        expired = dict(LEASE, expires_at=NOW)
        for data, held in ((log.data, lambda r, t: {'task_id': TASK}), (log.data, lambda r, t: expired),
                           (b'not a line\n', lambda r, t: None), (b'', lambda r, t: None),
                           (Log().approve(task_id='TASK-101').data, lambda r, t: None),
                           (log.data, mock.Mock(side_effect=RuntimeError('x'))), ('x', lambda r, t: None)):
            value, found = execution.task_view(data, ROOT, TASK, NOW, held=held)
            self.assertIsNone(value)
            self.assertTrue(found and all(isinstance(f, str) for f in found))

    def test_it_equals_what_execute_compares(self):
        """TASK-086 AC9: an execute run with task_view's three values is not refused with reason "inputs"."""
        log = Log().approve('e' * 64)
        view = execution.task_view(log.data, ROOT, TASK, NOW, held=lambda r, t: None)[0]
        inputs = dict(view, task_id=TASK)
        r = execution.execute(ROOT, TASK, inputs, 'c' * 64, {'holder': 'h', 'session_id': 's', 'expires_at': LATER},
                              REC, NOW, read_log=lambda root: log.data, held=lambda r, t: None,
                              check=mock.Mock(side_effect=RuntimeError('x')))
        self.assertEqual(r['reason'], 'check')
        held = execution.task_view(log.data, ROOT, TASK, NOW, held=lambda r, t: LEASE)[0]
        r = execution.execute(ROOT, TASK, dict(held, task_id=TASK), 'c' * 64,
                              {'holder': 'h', 'session_id': 's', 'expires_at': LATER}, REC, NOW,
                              read_log=lambda root: log.data, held=lambda r, t: LEASE,
                              check=mock.Mock(side_effect=RuntimeError('x')))
        self.assertEqual(r['reason'], 'check')


class TASK086AC1Declaration(Base):
    """The step "declaration" (task TASK-117 AC3): the tier comes from the declaration read at the base, not from a
    caller."""

    def record(self, c):
        return next(call[1][2] for call in c.of('append') if call[1][1] == 'decision.execution')

    def test_the_signature_and_the_callee_list(self):
        """TASK-086 AC1, as TASK-117 AC3 changes it: launcher.start has no max_risk parameter and has the keyword
        read_declaration; _CALLEES holds read_declaration once, not among its last five names (the last five stay
        read_sessions, session_leases, stored_reads, remove_reads and observe_gone), and the callees tuple that start
        builds is as long as _CALLEES; a call with the keyword max_risk raises TypeError."""
        params = inspect.signature(launcher.start).parameters
        self.assertNotIn('max_risk', params)
        self.assertIn('read_declaration', params)
        self.assertEqual(launcher._CALLEES.count('read_declaration'), 1)
        self.assertLess(launcher._CALLEES.index('read_declaration'), len(launcher._CALLEES) - 5)
        self.assertEqual(launcher._CALLEES[-5:], ('read_sessions', 'session_leases', 'stored_reads', 'remove_reads',
                                                  'observe_gone'))
        self.assertEqual(len(launcher._CALLEES), 19)
        with self.assertRaises(TypeError):
            launcher.start(ROOT, REPO, TASK, 'unit', 'agent-1', REC, NOW, LATER, max_risk='low')

    def test_the_default_is_looked_up_at_call_time(self):
        """TASK-086 AC1, as TASK-117 AC3 changes it: with no read_declaration given, the default is
        adapter_declaration.read_declaration looked up at call time (a patch after import is the one called), called
        with start's repo, the head and the adapter name and no run; a raise gives "refused" with reason
        "declaration" and no later callee call."""
        repo = world()
        seen = []

        def raising(*args, **kwargs):
            seen.append((args, kwargs))
            raise LookupError('x')
        c = calls_for(repo, approved_log(repo))
        with mock.patch.object(adapter_declaration, 'read_declaration', raising):
            r = launch(c, stub=('start', 'end'), read_declaration=None)
        self.closed(r)
        self.assertEqual(r['reason'], 'declaration')
        self.assertEqual(seen, [((REPO, repo.head, 'unit'), {})])
        self.assertEqual(c.of('read_log'), [])
        self.assertEqual(c.of('start'), [])
        # the same lookup when the patched read ANSWERS: it is the one called, once, and the flow goes on to read_log
        answered = []

        def answering(*args, **kwargs):
            answered.append((args, kwargs))
            return declared('low')
        c = calls_for(repo, approved_log(repo), end=ended())
        with mock.patch.object(adapter_declaration, 'read_declaration', answering):
            launch(c, stub=('start', 'end'), read_declaration=None)
        self.assertEqual(answered, [((REPO, repo.head, 'unit'), {})])
        self.assertEqual(len(c.of('read_log')), 1)

    def test_an_answer_out_of_form_gives_no_lease(self):
        """TASK-086 AC6, as TASK-117 AC3 changes it: an answer of read_declaration that is not a mapping, a result low
        with a tier out of form (not one of low, medium, high, critical, or not a str), and a result outside absent, low,
        refused and error (none, present, a non-str) each give "refused" with reason "declaration", a finding that names
        the step, no lease, no append and no log read."""
        answers = ('not a mapping', [], 3,
                   {'result': 'low', 'max_risk': 'T3', 'findings': []},
                   {'result': 'low', 'max_risk': None, 'findings': []},
                   {'result': 'low', 'max_risk': 3, 'findings': []},
                   {'result': 'none', 'max_risk': None, 'findings': []},
                   {'result': 'present', 'max_risk': 'low', 'findings': []},
                   {'result': 7, 'max_risk': None, 'findings': ['x']},
                   {'max_risk': 'low', 'findings': []})
        for answer in answers:
            with self.subTest(answer=repr(answer)):
                repo = world()
                c = calls_for(repo, approved_log(repo), read_declaration=answer)
                r = launch(c, stub=('start', 'end'))
                self.closed(r)
                self.assertEqual(r['reason'], 'declaration')
                self.assertTrue(r['findings'] and all(f.startswith('declaration') for f in r['findings']), r['findings'])
                for name in ('read_log', 'held', 'start', 'start_session', 'append', 'grant', 'end', 'end_session'):
                    self.assertEqual(c.of(name), [], name)

    def test_the_real_read_inside_start(self):
        """TASK-086 AC6, as TASK-117 AC3 changes it: with no read_declaration given, start runs the real
        adapter_declaration.read_declaration (only the base read of the policy text, claude_code_shell_allow
        .read_policy_text, is a stand-in): a well-formed block with an item for the adapter gives the tier low (a task of
        risk medium then fires check 7: "STOP: runtime insufficient", and its detail is not "the runtime has no
        declaration"); a text with no adapters line gives the existing "no declaration" path (check 7 fires too, with
        the detail "the runtime has no declaration"); a malformed block (a tab-led repeat of the adapter id) gives
        "refused" with reason "declaration" and no lease."""
        item = ('  - adapter: unit\n    tier: T3\n    configuration: {runtime: unit, platform: windows-native, version: '
                '1.0, settings: sha256:abc}\n    capabilities: {}\n    assurance: {preventive: none, runtime: none, '
                'posthoc: none}\n    max_risk: low\n')

        def served(text):
            seen = []

            def fake(repo, base, run=None):
                seen.append((repo, base, run))
                return {'result': 'present', 'text': text, 'findings': []}
            return fake, seen

        for text, none in (('adapters:\n' + item, False), ('shell_allow:\n  - git status\n', True)):
            with self.subTest(text=text[:12]):
                repo = world(risk='medium')
                c = calls_for(repo, approved_log(repo), end=ended())
                fake, seen = served(text)
                with mock.patch.object(shell_allow, 'read_policy_text', fake):
                    r = launch(c, stub=('end',), read_declaration=None)
                self.assertEqual(seen, [(REPO, repo.head, None)])
                self.closed(r, 'not granted')
                self.assertEqual(r['decision'], 'STOP: runtime insufficient')
                seventh = check_of(self.record(c), 7)
                self.assertEqual(seventh['status'], 'fired')
                # the two paths give the same decision; the detail tells them apart: with a declaration the tier read
                # (low) is below the task's risk, with none the runtime "has no declaration"
                if none:
                    self.assertEqual(seventh['detail'], 'the runtime has no declaration')
                else:
                    self.assertNotEqual(seventh['detail'], 'the runtime has no declaration')
        repo = world()
        c = calls_for(repo, approved_log(repo))
        fake, seen = served('adapters:\n' + item + '\t  - adapter: unit\n')
        with mock.patch.object(shell_allow, 'read_policy_text', fake):
            r = launch(c, stub=('start', 'end'), read_declaration=None)
        self.assertEqual(len(seen), 1)
        self.closed(r)
        self.assertEqual(r['reason'], 'declaration')
        for name in ('read_log', 'start', 'start_session', 'append', 'grant'):
            self.assertEqual(c.of(name), [], name)

    def test_a_raising_read_gives_a_refusal(self):
        """TASK-086 AC7, as TASK-117 AC3 changes it: a read_declaration that raises gives "refused" with reason
        "declaration", a finding that names the step and the exception, no lease, no append and no later call."""
        repo = world()
        c = calls_for(repo, approved_log(repo), read_declaration=LookupError('x'))
        r = launch(c, stub=('start', 'end'))
        self.closed(r)
        self.assertEqual(r['reason'], 'declaration')
        self.assertTrue(any('declaration' in f and 'LookupError' in f for f in r['findings']), r['findings'])
        self.assertEqual(c.names()[-1], 'read_declaration')
        for name in ('read_log', 'held', 'start', 'start_session', 'append', 'grant', 'end', 'end_session'):
            self.assertEqual(c.of(name), [], name)

    def test_a_refused_read_gives_no_lease(self):
        """TASK-086 AC6, as TASK-117 AC3 changes it: a read that is refused (result refused, no tier) gives "refused"
        with reason "declaration", its findings kept, no lease, no append, no log read and adapter.start not called;
        the step order stops at read_declaration."""
        repo = world()
        answer = {'result': 'refused', 'max_risk': None, 'findings': ['git: exit 128']}
        c = calls_for(repo, approved_log(repo), read_declaration=answer)
        r = launch(c, stub=('start', 'end'))
        self.closed(r)
        self.assertEqual(r['reason'], 'declaration')
        self.assertTrue(any('git: exit 128' in f for f in r['findings']), r['findings'])
        self.assertEqual(c.names(), ['expire', 'read', 'read', 'read', 'read', 'read_declaration'])
        for name in ('read_log', 'start', 'start_session', 'append', 'grant', 'end', 'end_session'):
            self.assertEqual(c.of(name), [], name)

    def test_a_malformed_declaration_gives_no_lease(self):
        """TASK-086 AC6, as TASK-117 AC3 changes it: a declaration that does not parse (result error, no tier) gives
        "refused" with reason "declaration", its findings kept, no lease and no append."""
        repo = world()
        answer = {'result': 'error', 'max_risk': None, 'findings': ['adapters: a repeated adapter id']}
        c = calls_for(repo, approved_log(repo), read_declaration=answer)
        r = launch(c, stub=('start', 'end'))
        self.closed(r)
        self.assertEqual(r['reason'], 'declaration')
        self.assertTrue(any('a repeated adapter id' in f for f in r['findings']), r['findings'])
        for name in ('read_log', 'start', 'start_session', 'append', 'grant', 'end', 'end_session'):
            self.assertEqual(c.of(name), [], name)

    def test_a_low_declaration_and_the_task_risk(self):
        """TASK-086 AC6, as TASK-117 AC3 changes it: a well-formed declaration (result low) is the tier of check 7: a
        task of risk low passes check 7 and is granted, a task of risk medium gets check 7 fired and the decision
        "STOP: runtime insufficient", no grant; the tier in the inputs is the declaration's."""
        # The setup of the first half: the stand-in policy classes src/** medium, so a contract that writes under src/**
        # is a medium task whatever it declares; here the same tree has the policy's rule for src/** set to low, so the
        # task is of class low and its declared risk is low.
        repo = Repo()
        base = repo.commit({'src/aieos_bootstrap/mod.py': 'X = 1\n'}, message='base')
        tree = {'src/aieos_bootstrap/mod.py': 'X = 1\n', 'docs/specs/s.md': S_TEXT,
                'docs/pre-genesis/constitution.md': CONSTITUTION,
                'docs/specs/risk-rules-gov-aieos.md': POLICY.replace('risk: medium', 'risk: low'),
                'src/aieos_bootstrap/resume_check.py': RC_TEXT, 'docs/tasks/%s.yaml' % TASK: contract(base, (), 'low')}
        repo.head = repo.commit(tree, [base], 'head')
        c = calls_for(repo, approved_log(repo))
        r = launch(c, max_risk='low', stub=('end',))
        self.assertEqual(r['result'], 'granted', r['findings'])
        self.assertEqual(c.of('end'), [])
        repo = world(risk='medium')
        c = calls_for(repo, approved_log(repo), end=ended())
        r = launch(c, max_risk='low', stub=('end',))
        self.closed(r, 'not granted')
        self.assertEqual(r['decision'], 'STOP: runtime insufficient')
        self.assertEqual(check_of(self.record(c), 7)['status'], 'fired')
        self.assertEqual(c.of('grant'), [])

    def test_the_step_order(self):
        """TASK-086 AC2, as TASK-117 AC3 changes it: the steps run in the order expire, head, base, root, declaration,
        log, view, inputs, start: the stand-in of the declaration is called after the four reads of the first
        steps and before read_log, held and adapter.start."""
        repo = world()
        c = calls_for(repo, approved_log(repo), start=ended(), end=ended())
        launch(c, stub=('start', 'end'))
        names = c.names()
        self.assertEqual(names.count('read_declaration'), 1)
        self.assertLess(names.index('read_declaration'), names.index('read_log'))
        self.assertLess(names.index('read_log'), names.index('held'))
        self.assertLess(names.index('held'), names.index('start'))
        self.assertEqual(names[:6], ['expire', 'read', 'read', 'read', 'read', 'read_declaration'])

    def test_the_launchers_adapter_name_is_a_declaration_id(self):
        """TASK-086 AC1, as TASK-118 AC2 adds it: the adapter name the launcher gives (launcher.LAUNCH_ADAPTER) is a
        valid adapter id of the declaration grammar: a declaration text with one item for it gives result low and the
        text low, and the same text with the old name 'claude_code' as the item's id gives result error."""
        conf = '{runtime: claude-code, platform: windows-native, version: 2.1.309, settings: sha256:1}'
        item = ('  - adapter: %s\n    tier: T3\n    configuration: ' + conf + '\n    capabilities: {}\n'
                '    assurance: {preventive: none, runtime: none, posthoc: none}\n    max_risk: low\n')
        got = adapter_declaration.declared_max_risk('adapters:\n' + item % launcher.LAUNCH_ADAPTER,
                                                    launcher.LAUNCH_ADAPTER)
        self.assertEqual((got['result'], got['max_risk']), ('low', 'low'), got)
        old = adapter_declaration.declared_max_risk('adapters:\n' + item % 'claude_code', 'claude_code')
        self.assertEqual(old['result'], 'error', old)


class TASK086AC10Modules(Base):
    def test_the_import_sets(self):
        """TASK-086 AC10, as TASK-089 AC10, TASK-094 AC5, TASK-096 AC5, TASK-098 AC5 and TASK-117 AC3 change it: by ast,
        execution.py's import set is the one its tests pin; launcher.py imports only datetime, hashlib and re and
        aieos_bootstrap's adapter, adapter_declaration, base_files, base_inputs, eventlog, execution, gitread, handoff_file, read_set_record,
        records, resume_check, resume_inputs, resume_log_inputs, scope_drift, scope_reconcile and writer."""
        self.assertEqual(imports(tree_of('execution.py')),
                         {'datetime', 're', 'aieos_bootstrap.records', 'aieos_bootstrap.resume_check',
                          'aieos_bootstrap.writer'})
        self.assertEqual(imports(tree_of('launcher.py')),
                         {'datetime', 'hashlib', 're'} | {'aieos_bootstrap.' + m for m in (
                             'adapter', 'adapter_declaration', 'base_files', 'base_inputs', 'eventlog', 'execution', 'gitread', 'handoff_file',
                             'read_set_record', 'records', 'resume_check', 'resume_inputs', 'resume_log_inputs',
                             'scope_drift', 'scope_reconcile', 'writer')})

    def test_what_the_new_module_names(self):
        """TASK-086 AC10, as TASK-094 AC5 changes it: launcher.py names no open, exec, eval, compile, __import__,
        subprocess, os, sys or time, no attribute environ, getenv, now or open_store, no attribute write but
        handoff_file.write (TASK-094's one exception; writer.write and any other write attribute still fail), no
        assert and no ".aieos" string."""
        source = (PKG / 'launcher.py').read_bytes().decode('utf-8')
        tree = ast.parse(source)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for bad in ('open', 'exec', 'eval', 'compile', '__import__', 'subprocess', 'os', 'sys', 'time'):
            self.assertNotIn(bad, names)
        for bad in ('environ', 'getenv', 'now', 'open_store'):
            self.assertNotIn(bad, attrs)
        writes = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == 'write'
                  and not (isinstance(n.value, ast.Name) and n.value.id == 'handoff_file')]
        self.assertEqual(writes, [])
        self.assertNotIn('.' + 'aieos', source)
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Assert)])


class TASK086AC12Docstrings(Base):
    def test_the_new_module(self):
        """TASK-086 AC12, as TASK-089 AC11, TASK-090 AC10 and TASK-117 AC3 change it: launcher.py's docstring holds seven
        of its nine phrases, "not before DEF-0101's open points are closed" in place of "not before TASK-089 lands",
        and TASK-089's three, and no longer "writes no observed read-set record", whitespace read as single spaces; it
        keeps "max_risk null never grants" and names the declaration read (adapter_declaration and TASK-117) and holds
        no "max_risk None or one of" (the argument is gone)."""
        text = doc('launcher.py')
        for words in ('starts no runtime', 'never raises', 'not before DEF-0101\'s open points are closed',
                      'the store is the caller\'s',
                      'max_risk null never grants', 'AIEOS_BASE is the head_commit', 'the log is read twice',
                      'this task\'s choice', 'the record before the release', 'no fencing token', 'TASK-090'):
            self.assertIn(words, text)
        for words in ('adapter_declaration', 'TASK-117', 'step "declaration"'):
            self.assertIn(words, text)
        self.assertNotIn('max_risk None or one of', text)
        self.assertNotIn('both the caller\'s', text)
        self.assertNotIn('writes no observed read-set record', text)

    def test_the_paragraph(self):
        """TASK-086 AC12: execution.py's docstring names task_view and TASK-086, its kept phrases unchanged."""
        text = doc('execution.py')
        for words in ('task_view', 'TASK-086', 'it gathers no Resume Check input',
                      'execute itself still gathers no Resume Check input', 'task_states', 'rework_count', 'TASK-088'):
            self.assertIn(words, text)


class TASK086Naming(unittest.TestCase):
    def test_every_test_names_its_criteria(self):
        """TASK-086 AC12: every test function of this module names "TASK-086 AC" in its own docstring."""
        tree = ast.parse(HERE.read_bytes().decode('utf-8'))
        tests = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
        self.assertTrue(tests)
        for node in tests:
            self.assertIn('TASK-086 AC', ast.get_docstring(node) or '', node.name)


if __name__ == '__main__':
    unittest.main()

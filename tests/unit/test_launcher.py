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

from aieos_bootstrap import adapter, eventlog, execution, gitread, launcher, resume_check, resume_inputs
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

S_TEXT = 'Đặc tả — một dòng\n'
S_HASH = hashlib.sha256(S_TEXT.encode('utf-8')).hexdigest()
RC_TEXT = '# Bộ kiểm tra — một bản đứng thay\nX = 1\n'
CONSTITUTION = '\n'.join([
    '# A stand-in constitution', '', '## 1. The articles', '',
    '### INV-001 · architecture · One', '',
    '- Severity: blocking. Scope: the core\'s source tree. Applicability: implementation. Enforcement: x.', ''])
POLICY = '\n'.join(['# A stand-in policy', '', '## 3. The rules', '', '```yaml', 'policy_version: v9', '',
                    'risk_rules:', '  - match: { paths: ["src/**"] }', '    risk: medium', '```']) + '\n'


def contract(base, depends):
    lines = ['task: %s' % TASK, 'contract_version: v1', 'task_type: implementation', 'traces_to:',
             '  - docs/specs/s.md#1', 'input_state:', '  base_commit: %s' % base,
             '  depends_on: [%s]' % ', '.join(depends), '  intent_versions:', '    docs/specs/s.md: %s' % S_HASH,
             'write_set:', '  paths:', '    - src/aieos_bootstrap/mod.py', 'read_set:', '  paths:',
             '    - src/aieos_bootstrap/mod.py', '  interfaces: []', 'constitution: [INV-001]', 'acceptance_criteria:',
             '  - AC1: >-', '      One.', 'risk: high', 'autonomy:', '  budgets: {tokens: 600k, retries: 2}']
    return '\n'.join(lines) + '\n'


def gid(kind, data):
    return hashlib.sha1(b'%s %d\x00' % (kind.encode('ascii'), len(data)) + data, usedforsecurity=False).hexdigest()


def ok(out):
    return {'exit': 0, 'out': out, 'err': b'', 'error': None}


class Repo:
    """A stand-in for gitread.run over commits held in memory, ids being Git's own hashes; it answers the HEAD form
    with its head and records its calls as (repo, args, timeout)."""

    def __init__(self):
        self.objects, self.files, self.parents, self.calls = {}, {}, {}, []
        self.head = None

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
        if list(args) == HEAD_ARGS:
            return ok((self.head + '\n').encode('ascii'))
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


def world(depends=()):
    """base (one source file) and head (adds the contract, the intent file, the constitution, the policy and a
    stand-in resume_check.py with non-ASCII text); the repo's head is head."""
    repo = Repo()
    base = repo.commit({'src/aieos_bootstrap/mod.py': 'X = 1\n'}, message='base')
    tree = {'src/aieos_bootstrap/mod.py': 'X = 1\n', 'docs/specs/s.md': S_TEXT,
            'docs/pre-genesis/constitution.md': CONSTITUTION, 'docs/specs/risk-rules-gov-aieos.md': POLICY,
            'src/aieos_bootstrap/resume_check.py': RC_TEXT, 'docs/tasks/%s.yaml' % TASK: contract(base, depends)}
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


def launch(c, max_risk='critical', stub=(), **over):
    """launcher.start with every store function and the read a recording stand-in; the names in stub also replace
    adapter.start ('start') and adapter.end ('end'). TASK-090's step is given a read_sessions stand-in that records
    nothing and lists no session, unless the test gives its own, and per-session stand-ins that record any call into a
    list; that list must stay empty, so launch raises AssertionError after start returns otherwise (TASK-090 AC7)."""
    kw = {name: c.make(name, real) for name, real in STORE}
    kw['read'] = c.make('read', gitread.run)
    if 'start' in stub:
        kw['start'] = c.make('start', adapter.start)
    if 'end' in stub:
        kw['end'] = c.make('end', adapter.end)
    stray = []
    kw['read_sessions'] = lambda root, task_id: store(value=[])
    for name in ('session_leases', 'stored_reads', 'remove_reads', 'observe_gone'):
        kw[name] = lambda *a, name=name, **k: stray.append(name)
    args = dict(root=ROOT, repo=REPO, task_id=TASK, adapter_name='unit', max_risk=max_risk, holder='agent-1',
                recorder=REC, now=NOW, expires_at=LATER)
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
        reason "argument" and zero callee calls; TASK-090 AC7: the five new callees out of form among them."""
        repo = world()
        later = NOW + datetime.timedelta(seconds=1)
        for over in ({'root': 'x/y'}, {'root': ''}, {'root': 1}, {'repo': 'x/y'}, {'repo': REPO + '/no-such-dir'},
                     {'task_id': 'TASK-x'}, {'task_id': None}, {'adapter_name': ''}, {'max_risk': 'huge'},
                     {'max_risk': 1}, {'holder': ''}, {'recorder': None}, {'now': NOW.replace(tzinfo=None)},
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
                r = launcher.start(ROOT, REPO, TASK, 'unit', None, 'agent-1', REC, NOW, LATER)
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
                launcher.start(ROOT, REPO, TASK, 'unit', None, 'agent-1', REC, NOW, LATER, **kw)
            self.assertEqual(seen, [name])


class TASK086AC2Order(Base):
    def test_the_order(self):
        """TASK-086 AC2: expire, then read (HEAD), then read_log, then held (the one held call before adapter.start),
        then the readers' reads, then adapter.start, then adapter.end when no token was granted and the row was
        opened; execute's own second read_log and held calls come inside adapter.start. TASK-090 AC7: with a recording
        read_sessions, it is called first, before expire."""
        repo = world()
        c = calls_for(repo, approved_log(repo), start=ended(), end=ended())
        r = launch(c, stub=('start', 'end'))
        names = c.names()
        self.assertEqual(names[:4], ['expire', 'read', 'read_log', 'held'])
        self.assertEqual(names[-2:], ['start', 'end'])
        self.assertTrue(set(names[4:-2]) == {'read'} and len(names) > 7, names)
        self.assert_form(r)
        self.assertEqual(r['result'], 'not granted')
        c = calls_for(repo, approved_log(repo))
        r = launch(c, max_risk=None)
        names = c.names()
        self.assertEqual(names[:4], ['expire', 'read', 'read_log', 'held'])
        first = names.index('start_session')
        self.assertEqual(names[first:first + 3], ['start_session', 'read_log', 'held'])
        self.assertEqual(names[-1], 'end_session')
        self.assertEqual(r['result'], 'not granted')
        c = calls_for(repo, approved_log(repo), read_sessions=store(value=[]))
        r = launch(c, max_risk=None, read_sessions=c.make('read_sessions', writer.read_sessions))
        self.assertEqual(c.names()[:5], ['read_sessions', 'expire', 'read', 'read_log', 'held'])
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
        """TASK-086 AC6: max_risk null, where checks 1 to 6 do not fire, gives check 7 fired with "the runtime has no
        declaration", decision "STOP: runtime insufficient", "not granted", no environment, and adapter.end called
        once with no token."""
        repo = world()
        c = calls_for(repo, approved_log(repo), end=ended())
        r = launch(c, max_risk=None, stub=('end',))
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


class TASK086AC10Modules(Base):
    def test_the_import_sets(self):
        """TASK-086 AC10, as TASK-089 AC10 and TASK-094 AC5 change it: by ast, execution.py's import set is the one its
        tests pin; launcher.py imports only datetime, hashlib and re and aieos_bootstrap's adapter, base_files,
        base_inputs, execution, gitread, handoff_file, read_set_record, resume_check, resume_inputs, resume_log_inputs
        and writer."""
        self.assertEqual(imports(tree_of('execution.py')),
                         {'datetime', 're', 'aieos_bootstrap.records', 'aieos_bootstrap.resume_check',
                          'aieos_bootstrap.writer'})
        self.assertEqual(imports(tree_of('launcher.py')),
                         {'datetime', 'hashlib', 're'} | {'aieos_bootstrap.' + m for m in (
                             'adapter', 'base_files', 'base_inputs', 'execution', 'gitread', 'handoff_file',
                             'read_set_record', 'resume_check', 'resume_inputs', 'resume_log_inputs', 'writer')})

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
        """TASK-086 AC12, as TASK-089 AC11 and TASK-090 AC10 change it: launcher.py's docstring holds seven of its nine
        phrases, "not before DEF-0101's open points are closed" in place of "not before TASK-089 lands", and TASK-089's
        three, and no longer "writes no observed read-set record", whitespace read as single spaces."""
        text = doc('launcher.py')
        for words in ('starts no runtime', 'never raises', 'not before DEF-0101\'s open points are closed',
                      'the store is the caller\'s',
                      'max_risk null never grants', 'AIEOS_BASE is the head_commit', 'the log is read twice',
                      'this task\'s choice', 'the record before the release', 'no fencing token', 'TASK-090'):
            self.assertIn(words, text)
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

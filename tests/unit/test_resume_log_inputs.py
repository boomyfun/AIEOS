"""Unit tests of aieos_bootstrap.resume_log_inputs and of the functions TASK-088 adds to execution and scope_reconcile:
the arguments and the reader, dependencies, budget_use, intent_current, articles, risk_rules and policy_version, the
output's form and failing closed, what the modules may touch, the docstrings and this module's own naming rule. Every
Git answer comes from a stand-in read over objects held in memory (rebuilt here in tests/unit/test_resume_inputs.py's
form, not imported from it); every log is built with eventlog.append (a duplicate line by hand, since append makes
none); no test runs Git or writes a file; the sources are read with pathlib's read_bytes."""

import ast
import datetime
import hashlib
import json
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import eventlog, execution, gitread, resume_check, resume_inputs, resume_log_inputs
from aieos_bootstrap import scope_reconcile

HERE = pathlib.Path(__file__).resolve()
ROOT = str(HERE.parents[2])
PKG = HERE.parents[2] / 'src' / 'aieos_bootstrap'
TASK = 'TASK-100'
NOW = datetime.datetime(2026, 10, 24, 12, 0, 0, tzinfo=datetime.timezone.utc)
DEPS = ('TASK-080', 'TASK-081', 'TASK-082')

S_TEXT = 'Đặc tả — một dòng\n'
S_HASH = hashlib.sha256(S_TEXT.encode('utf-8')).hexdigest()

CONSTITUTION = '\n'.join([
    '# A stand-in constitution', '', '## 1. The articles', '',
    '### INV-001 · architecture · One', '',
    '- Severity: blocking. Scope: the core\'s source tree. Applicability: implementation, refactoring. Enforcement: x.',
    '',
    '### SEC-003 · security · Two', '',
    '- Severity: blocking. Scope: `.github/`. Applicability: all task types. Enforcement: x.', '',
    '### GOV-009 · governance · Three', '',
    '- Severity: blocking. Applicability: documentation. Enforcement: x.', ''])

POLICY_RULES = ['  - match: { paths: ["docs/specs/**"] }', '    risk: medium',
                '  - match: { component_tags: [core, gov] }', '    risk: high']


def policy(rules=POLICY_RULES, versions=('policy_version: v9',), block=True):
    lines = ['# A stand-in policy', '', '## 3. The rules', '']
    if block:
        lines += ['```yaml'] + list(versions) + ['', 'risk_rules:'] + list(rules) + ['```']
    return '\n'.join(lines) + '\n'


def contract(base, iv, depends=DEPS, budgets='{tokens: 600k, retries: 2, wall_time: 6h}', drop=()):
    lines = ['task: %s' % TASK, 'contract_version: v1', 'task_type: implementation', 'traces_to:',
             '  - docs/specs/s.md#1']
    if 'input_state' not in drop:
        lines += ['input_state:', '  base_commit: %s' % base]
        if 'depends_on' not in drop:
            lines.append('  depends_on: [%s]' % ', '.join(depends))
        if 'intent_versions' not in drop:
            lines.append('  intent_versions:')
            lines += ['    %s: %s' % (k, v) for k, v in iv]
    lines += ['write_set:', '  paths:', '    - src/aieos_bootstrap/mod.py', 'read_set:', '  paths:',
              '    - docs/specs/s.md', '  interfaces: []', 'constitution: [INV-001]', 'acceptance_criteria:',
              '  - AC1: >-', '      One.', 'risk: high']
    if 'autonomy' not in drop:
        lines += ['autonomy:', '  budgets: %s' % budgets]
    return '\n'.join(lines) + '\n'


def gid(kind, data):
    return hashlib.sha1(b'%s %d\x00' % (kind.encode('ascii'), len(data)) + data, usedforsecurity=False).hexdigest()


def ok(out):
    return {'exit': 0, 'out': out, 'err': b'', 'error': None}


class Repo:
    """A stand-in for gitread.run over commits held in memory, ids being Git's own hashes; it records its calls."""

    def __init__(self):
        self.objects = {}
        self.files = {}
        self.parents = {}
        self.calls = []

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


IV = (('docs/specs/s.md', S_HASH), ('docs/missing.md', 'abc'), ('nowhere/x.md', 'abc'))


def world(iv=IV, files=None, **kw):
    """base (one source file) and head (adds the contract, the intent file, the constitution and the policy)."""
    repo = Repo()
    base = repo.commit({'src/aieos_bootstrap/mod.py': 'X = 1\n'}, message='base')
    tree = {'src/aieos_bootstrap/mod.py': 'X = 1\n', 'docs/specs/s.md': S_TEXT,
            'docs/pre-genesis/constitution.md': CONSTITUTION, 'docs/specs/risk-rules-gov-aieos.md': policy(),
            'docs/tasks/%s.yaml' % TASK: contract(base, iv, **kw)}
    tree.update(files or {})
    head = repo.commit(tree, [base], 'head')
    return repo, base, head


class Log:
    """An event log kept as bytes; every line but a hand-made duplicate is decided by eventlog.append."""

    def __init__(self):
        self.data = b''
        self.lines = []

    def add(self, event_type, payload, event_id, task_id):
        r = eventlog.append(self.data, event_type, payload, event_id, NOW, task_id=task_id)
        if r.result != 'appended':
            raise AssertionError(r.findings)
        self.data += r.line
        self.lines.append(r.line)
        return self

    def approve(self, task):
        return self.add('task.approved', {'contract_version': 'v1', 'contract_hash': 'a' * 64, 'approval_record': 'r'},
                        'appr-%s-%d' % (task, len(self.lines)), task)

    def done(self, task):
        return self.add('task.done', {'decision_record': 'd'}, 'done-%s-%d' % (task, len(self.lines)), task)

    def block(self, task):
        return self.add('task.blocked', {'reason': 'dependency', 'blocked_by': ['TASK-099']},
                        'block-%s-%d' % (task, len(self.lines)), task)

    def unblock(self, task):
        return self.add('task.unblocked', {'reason': 'dependency done'}, 'unblock-%s-%d' % (task, len(self.lines)),
                        task)

    def stale(self, task):
        return self.add('evidence.stale', {'records': ['rec-1'], 'reason': 'commit'},
                        'stale-%s-%d' % (task, len(self.lines)), task)

    def accept(self, task, next_state):
        eid = 'acc-%s-%d' % (task, len(self.lines))
        payload = {'record_id': eid, 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_local',
                   'recorder': 'unit', 'subject': task, 'decision': 'NEEDS_REWORK', 'next_task_state': next_state}
        return self.add('decision.acceptance', payload, eid, task)

    def duplicate(self, index):
        obj = json.loads(self.lines[index].decode('utf-8'))
        obj['seq'] = len(self.lines) + 1
        line = (json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode('utf-8')
        self.data += line
        self.lines.append(line)
        return self


def run(repo, head, log=b'', task_id=TASK):
    return resume_log_inputs.log_inputs(ROOT, head, task_id, log, repo)


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


def function(tree, name):
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)


def doc(name):
    return ' '.join(ast.get_docstring(tree_of(name)).split())


class Base(unittest.TestCase):
    def refused(self, result):
        value, findings = result
        self.assertIsNone(value)
        self.assertIsInstance(findings, list)
        self.assertTrue(findings)
        self.assertTrue(all(isinstance(f, str) for f in findings))
        return findings

    def good(self, result):
        value, findings = result
        self.assertIsNone(findings, findings)
        return value


class TASK088AC1Arguments(Base):
    def test_arguments_refused_before_any_read(self):
        """TASK-088 AC1: repo, commit, task_id, log or read out of form give findings with zero reads."""
        repo, base, head = world()
        for args in ((1, head, TASK, b''), (ROOT, 'abc', TASK, b''), (ROOT, head.upper(), TASK, b''),
                     (ROOT, head, 'TASK-x', b''), (ROOT, head, TASK, 'log')):
            self.refused(resume_log_inputs.log_inputs(*args, read=repo))
        self.refused(resume_log_inputs.log_inputs(ROOT, head, TASK, b'', read=3))
        self.assertEqual(repo.calls, [])

    def test_default_read_bound_at_call_time(self):
        """TASK-088 AC1: read defaults to gitread.run taken at call time; a patch after import is the one called."""
        repo, base, head = world()
        with mock.patch.object(gitread, 'run', repo):
            self.good(resume_log_inputs.log_inputs(ROOT, head, TASK, b''))
        self.assertTrue(repo.calls)

    def test_every_read_is_a_fixed_form(self):
        """TASK-088 AC1: every read is one of gitread's fixed forms (gitread.form_error gives None for each call)."""
        repo, base, head = world()
        self.good(run(repo, head))
        self.assertTrue(repo.calls)
        for call in repo.calls:
            self.assertIsNone(gitread.form_error(*call), call)


class TASK088AC2Dependencies(Base):
    def test_states_from_the_log(self):
        """TASK-088 AC2: a dependency approved and done gives DONE, one approved and blocked BLOCKED, one with no
        task.approved null; log_inputs' dependencies are task_states over the contract's depends_on."""
        log = Log().approve('TASK-080').done('TASK-080').approve('TASK-081').block('TASK-081')
        want = {'TASK-080': {'state': 'DONE', 'stale_evidence': False},
                'TASK-081': {'state': 'BLOCKED', 'stale_evidence': False},
                'TASK-082': {'state': None, 'stale_evidence': False}}
        self.assertEqual(self.good(execution.task_states(log.data, list(DEPS))), want)
        repo, base, head = world()
        self.assertEqual(self.good(run(repo, head, log.data))['dependencies'], want)

    def test_stale_evidence(self):
        """TASK-088 AC2: stale_evidence is true only when an evidence.stale of that task follows its last task.done;
        one before it, or of another task, gives false; an evidence.stale with no task_id is never counted."""
        log = Log().approve('TASK-080').stale('TASK-080').done('TASK-080').approve('TASK-081').stale('TASK-081')
        self.assertFalse(self.good(execution.task_states(log.data, ['TASK-080']))['TASK-080']['stale_evidence'])
        log.stale('TASK-080')
        self.assertTrue(self.good(execution.task_states(log.data, ['TASK-080']))['TASK-080']['stale_evidence'])
        again = Log().approve('TASK-080').done('TASK-080').add(
            'evidence.stale', {'records': ['rec-1'], 'reason': 'commit'}, 'stale-none', None)
        self.assertFalse(self.good(execution.task_states(again.data, ['TASK-080']))['TASK-080']['stale_evidence'])

    def test_a_duplicate_line_is_not_counted(self):
        """TASK-088 AC2: a duplicate line is not counted: a task.blocked copied after its task.unblocked leaves the
        task READY."""
        log = Log().approve('TASK-081').block('TASK-081').unblock('TASK-081').duplicate(1)
        self.assertEqual(self.good(execution.task_states(log.data, ['TASK-081']))['TASK-081']['state'], 'READY')

    def test_failing_closed(self):
        """TASK-088 AC2: a task.* event _project does not name (made by mock.patch.object of STATE_OF), or a log
        check_log refuses, gives findings; task_states over an empty id list gives {}."""
        log = Log().approve('TASK-080').done('TASK-080')
        names = {k: v for k, v in execution.STATE_OF.items() if k != 'task.done'}
        with mock.patch.object(execution, 'STATE_OF', names):
            self.refused(execution.task_states(log.data, ['TASK-080']))
            repo, base, head = world()
            self.refused(run(repo, head, log.data))
        self.refused(execution.task_states(b'not a line\n', ['TASK-080']))
        self.refused(execution.task_states('text', ['TASK-080']))
        self.refused(execution.task_states(log.data, ['task-80']))
        self.refused(execution.task_states(log.data, 'TASK-080'))
        self.assertEqual(self.good(execution.task_states(log.data, [])), {})


class TASK088AC3Budgets(Base):
    def test_rework_count(self):
        """TASK-088 AC3: two decision.acceptance events with next_task_state REWORK after the last task.approved give
        2; one before it does not count; one with ACCEPTED does not count; no task.approved gives 0."""
        log = Log().approve(TASK).accept(TASK, 'REWORK').approve(TASK).accept(TASK, 'REWORK')
        log.accept(TASK, 'REWORK').accept(TASK, 'ACCEPTED')
        self.assertEqual(self.good(execution.rework_count(log.data, TASK)), 2)
        self.assertEqual(self.good(execution.rework_count(log.data, 'TASK-7')), 0)
        self.refused(execution.rework_count(log.data, 'task-7'))
        self.refused(execution.rework_count('text', TASK))
        repo, base, head = world()
        self.assertEqual(self.good(run(repo, head, log.data))['budget_use'],
                         {'tokens': {'used': 0, 'reported': False}, 'retries': {'used': 2, 'reported': True},
                          'wall_time': {'used': 0, 'reported': False}})

    def test_no_retries_budget(self):
        """TASK-088 AC3: one entry per budget of autonomy.budgets, exactly {used, reported}; a contract with no
        retries budget gives no retries entry."""
        repo, base, head = world(budgets='{tokens: 600k}')
        self.assertEqual(self.good(run(repo, head))['budget_use'], {'tokens': {'used': 0, 'reported': False}})

    def test_a_contract_without_its_keys_fails_closed(self):
        """TASK-088 AC3: a contract without input_state, depends_on, intent_versions or autonomy.budgets in form gives
        findings (disp88c row 5)."""
        for drop in (('input_state',), ('depends_on',), ('intent_versions',), ('autonomy',)):
            repo, base, head = world(drop=drop)
            self.refused(run(repo, head))
        repo, base, head = world(budgets='600k')
        self.refused(run(repo, head))


class TASK088AC4Intents(Base):
    def test_file_hashes(self):
        """TASK-088 AC4: an unchanged file equals the contract's value (the SHA-256 of its bytes; the stand-in holds
        non-ASCII text and a trailing newline), a changed byte changes it, and an absent file gives null."""
        repo, base, head = world()
        got = self.good(run(repo, head))['intent_current']
        self.assertEqual(got, {'docs/specs/s.md': S_HASH, 'docs/missing.md': None, 'nowhere/x.md': None})
        self.assertNotEqual(S_HASH, hashlib.sha256(S_TEXT.strip().encode('utf-8')).hexdigest())
        self.assertNotEqual(S_HASH, hashlib.sha256(S_TEXT.encode('utf-16')).hexdigest())
        changed = 'Đặc tả — một dòng!\n'
        repo, base, head = world(files={'docs/specs/s.md': changed})
        self.assertEqual(self.good(run(repo, head))['intent_current']['docs/specs/s.md'],
                         hashlib.sha256(changed.encode('utf-8')).hexdigest())

    def test_an_entity_out_of_form_fails_closed(self):
        """TASK-088 AC4: an entity out of base_files' path form gives findings."""
        repo, base, head = world(iv=(('docs/./s.md', 'abc'),))
        self.refused(run(repo, head))


class TASK088AC5Articles(Base):
    def test_articles(self):
        """TASK-088 AC5: one entry per "### <ID> · " heading, in file order, exactly {id, scope, applicability,
        violated}; scope the Scope prose as a str ("" when there is none), to the first ". " (SEC-003's is
        "`.github/`"); applicability from a list of lowercase words, else null; violated null."""
        repo, base, head = world()
        self.assertEqual(self.good(run(repo, head))['articles'], [
            {'id': 'INV-001', 'scope': 'the core\'s source tree',
             'applicability': {'task_types': ['implementation', 'refactoring']}, 'violated': None},
            {'id': 'SEC-003', 'scope': '`.github/`', 'applicability': None, 'violated': None},
            {'id': 'GOV-009', 'scope': '', 'applicability': {'task_types': ['documentation']}, 'violated': None}])

    def test_a_constitution_out_of_form_fails_closed(self):
        """TASK-088 AC5: a constitution with no heading, or an id twice, gives findings."""
        repo, base, head = world(files={'docs/pre-genesis/constitution.md': '# No articles\n'})
        self.refused(run(repo, head))
        twice = CONSTITUTION + '### INV-001 · architecture · Again\n'
        repo, base, head = world(files={'docs/pre-genesis/constitution.md': twice})
        self.refused(run(repo, head))


class TASK088AC6Rules(Base):
    def test_rules_and_version(self):
        """TASK-088 AC6: each rule as {match: {paths: [...]}, risk: class} in order, a component_tags rule as its
        TAGS_MATCH paths; a write set outside src/ and tests/ (docs/x.md) that no other rule meets stays unmatched in
        resume_check's _task_risk, so check 7's ESCALATE can fire; policy_version the block's value."""
        repo, base, head = world()
        value = self.good(run(repo, head))
        rules = value['risk_rules']
        self.assertEqual(rules, [{'match': {'paths': ['docs/specs/**']}, 'risk': 'medium'},
                                 {'match': {'paths': ['src/**', 'tests/**']}, 'risk': 'high'}])
        self.assertEqual(value['policy_version'], 'v9')
        outside = {'contract': {'risk': 'low', 'write_set': {'paths': ['docs/x.md']}}, 'risk_rules': rules}
        self.assertEqual(resume_check._task_risk(outside), ('low', ['docs/x.md']))
        inside = {'contract': {'risk': 'low', 'write_set': {'paths': ['src/a.py']}}, 'risk_rules': rules}
        self.assertEqual(resume_check._task_risk(inside), ('high', []))

    def test_failing_closed(self):
        """TASK-088 AC6: a rule rules_from_policy refuses gives findings; a policy with no block, or no or two
        policy_version lines, gives findings."""
        bad = ['  - match: { owners: [x] }', '    risk: high']
        for text in (policy(rules=bad), policy(block=False), policy(versions=()),
                     policy(versions=('policy_version: v1', 'policy_version: v2'))):
            repo, base, head = world(files={'docs/specs/risk-rules-gov-aieos.md': text})
            self.refused(run(repo, head))

    def test_policy_block(self):
        """TASK-088 AC6: scope_reconcile.policy_block gives the block's lines as _block finds them, or None for a text
        with no block or one that is not a str."""
        self.assertEqual(scope_reconcile.policy_block(policy())[0], 'policy_version: v9')
        self.assertEqual(scope_reconcile.policy_block(policy()), scope_reconcile._block(policy()))
        self.assertIsNone(scope_reconcile.policy_block(policy(block=False)))
        self.assertIsNone(scope_reconcile.policy_block(None))


class TASK088AC7Output(Base):
    def test_exactly_the_seven_keys(self):
        """TASK-088 AC7: exactly the seven keys, observed_read_set null."""
        repo, base, head = world()
        value = self.good(run(repo, head))
        self.assertEqual(set(value), set(resume_log_inputs.KEYS))
        self.assertEqual(len(resume_log_inputs.KEYS), 7)
        self.assertIsNone(value['observed_read_set'])

    def test_with_git_inputs_the_check_runs(self):
        """TASK-088 AC7: merged with TASK-085's git_inputs over the same stand-in commit and fixed task_id, log_seq,
        task_state, approved_contract_hash and runtime, the 22 keys equal resume_check.INPUT_KEYS and
        resume_check.check gives a record with no error, whose uncovered list names every article whose
        applicability is null or names the contract's task_type, listed or not, and not GOV-009."""
        repo, base, head = world()
        inputs = self.good(resume_inputs.git_inputs(ROOT, head, TASK, b'', repo))
        inputs.update(self.good(run(repo, head)))
        inputs.update({'task_id': TASK, 'log_seq': 0, 'task_state': 'READY',
                       'approved_contract_hash': inputs['contract_hash'],
                       'runtime': {'adapter': 'unit', 'max_risk': None}})
        self.assertEqual(set(inputs), set(resume_check.INPUT_KEYS))
        record = resume_check.check(inputs, 'c' * 64)
        self.assertIsNone(record.get('error'), record.get('error'))
        uncovered = record.get('uncovered')
        for article in ('INV-001', 'SEC-003'):
            self.assertIn('article %s: no check result at HEAD' % article, uncovered)
        self.assertNotIn('article GOV-009: no check result at HEAD', uncovered)

    def test_failing_closed(self):
        """TASK-088 AC7: a read that raises (RuntimeError, RecursionError, MemoryError), an answer out of form, or a
        refused log give (None, findings); no call raises or returns a partial dict."""
        repo, base, head = world()
        for exc in (RuntimeError, RecursionError, MemoryError):
            def raising(r, args, timeout=30, exc=exc):
                raise exc('stand-in')
            self.refused(resume_log_inputs.log_inputs(ROOT, head, TASK, b'', raising))
        self.refused(resume_log_inputs.log_inputs(ROOT, head, TASK, b'', lambda r, args, timeout=30: 'x'))
        self.refused(run(repo, head, b'not a line\n'))


class TASK088AC8Modules(Base):
    def test_the_import_sets(self):
        """TASK-088 AC8: by ast, execution.py's and scope_reconcile.py's import sets are exactly those their tests
        pin, and the new module imports only hashlib and re and aieos_bootstrap's base_files, base_inputs,
        execution, gitread, resume_check and scope_reconcile."""
        self.assertEqual(imports(tree_of('execution.py')),
                         {'datetime', 're', 'aieos_bootstrap.records', 'aieos_bootstrap.resume_check',
                          'aieos_bootstrap.writer'})
        self.assertEqual(imports(tree_of('scope_reconcile.py')),
                         {'datetime', 'hashlib', 're', 'aieos_bootstrap.gitread', 'aieos_bootstrap.records',
                          'aieos_bootstrap.scope_drift', 'aieos_bootstrap.writer'})
        self.assertEqual(imports(tree_of('resume_log_inputs.py')),
                         {'hashlib', 're', 'aieos_bootstrap.base_files', 'aieos_bootstrap.base_inputs',
                          'aieos_bootstrap.execution', 'aieos_bootstrap.gitread', 'aieos_bootstrap.resume_check',
                          'aieos_bootstrap.scope_reconcile'})

    def test_the_new_functions(self):
        """TASK-088 AC8: by ast, task_states and rework_count use no attribute of writer and task_states calls
        _project (TASK-084's AC5 and AC6 forms)."""
        tree = tree_of('execution.py')
        for name in ('task_states', 'rework_count', '_given_log', '_own_events'):
            node = function(tree, name)
            uses = [n for n in ast.walk(node) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                    and n.value.id == 'writer']
            self.assertEqual(uses, [], name)
        calls = {n.func.id for n in ast.walk(function(tree, 'task_states'))
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertIn('_project', calls)

    def test_what_the_new_module_names(self):
        """TASK-088 AC8: the new module names no open, exec, eval, compile, __import__, subprocess, os, sys, time or
        autonomy, no attribute now, environ, getenv, write, grant_lease, append_event or expire_leases, and no
        ".aieos" string."""
        source = (PKG / 'resume_log_inputs.py').read_bytes().decode('utf-8')
        tree = ast.parse(source)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for bad in ('open', 'exec', 'eval', 'compile', '__import__', 'subprocess', 'os', 'sys', 'time', 'autonomy'):
            self.assertNotIn(bad, names)
        for bad in ('now', 'environ', 'getenv', 'write', 'grant_lease', 'append_event', 'expire_leases'):
            self.assertNotIn(bad, attrs)
        self.assertNotIn('.' + 'aieos', source)
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Assert)])


class TASK088AC10Docstrings(Base):
    def test_the_new_module(self):
        """TASK-088 AC10: the new module's docstring holds its nine phrases, whitespace read as single spaces."""
        text = doc('resume_log_inputs.py')
        for words in ('the commit is an argument', 'read is injectable', 'never raises', 'writes nothing',
                      'fails closed', 'this task\'s choice', 'seven of the 22 inputs', 'DEF-0100',
                      'observed_read_set is null'):
            self.assertIn(words, text)

    def test_the_two_paragraphs(self):
        """TASK-088 AC10: execution.py's and scope_reconcile.py's docstrings each name their new functions and
        TASK-088; execution.py's says execute itself still gathers no Resume Check input, with the kept phrase;
        scope_reconcile.py holds no "assert " text and no .run( call."""
        text = doc('execution.py')
        for words in ('task_states', 'rework_count', 'TASK-088', 'execute itself still gathers no Resume Check input',
                      'it gathers no Resume Check input'):
            self.assertIn(words, text)
        text = doc('scope_reconcile.py')
        for words in ('policy_block', 'TASK-088'):
            self.assertIn(words, text)
        source = (PKG / 'scope_reconcile.py').read_bytes().decode('utf-8')
        self.assertNotIn('assert' + ' ', source)
        self.assertNotIn('.run' + '(', source)


class TASK088Naming(unittest.TestCase):
    def test_every_test_names_its_criteria(self):
        """TASK-088 AC10: every test function of this module names "TASK-088 AC" in its own docstring."""
        tree = ast.parse(HERE.read_bytes().decode('utf-8'))
        tests = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
        self.assertTrue(tests)
        for node in tests:
            self.assertIn('TASK-088 AC', ast.get_docstring(node) or '', node.name)


if __name__ == '__main__':
    unittest.main()

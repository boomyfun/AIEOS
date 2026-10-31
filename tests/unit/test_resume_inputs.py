"""Unit tests of aieos_bootstrap.resume_inputs and of base_inputs' wrappers (TASK-085): the arguments and the reader,
the walk, the commits, the contract and the components, the symbols and the derived read-set, the output's form and
failing closed, what the modules may touch, the docstrings and this module's own naming rule. Every Git answer comes
from a stand-in read over objects held in memory (rebuilt here in tests/unit/test_base_inputs.py's form, not imported
from it); every log is built with eventlog.append; no test runs Git or writes a file; the sources are read with
pathlib's read_bytes."""

import ast
import datetime
import hashlib
import json
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import base_inputs, eventlog, gitread, resume_check, resume_inputs

HERE = pathlib.Path(__file__).resolve()
ROOT = str(HERE.parents[2])
SRC = HERE.parents[2] / 'src' / 'aieos_bootstrap' / 'resume_inputs.py'
BASE_SRC = HERE.parents[2] / 'src' / 'aieos_bootstrap' / 'base_inputs.py'
TASK = 'TASK-100'
NOW = datetime.datetime(2026, 10, 24, 12, 0, 0, tzinfo=datetime.timezone.utc)
TOKEN = {'epoch': 'e1', 'counter': 4}
LEASE = {'task_id': TASK, 'fencing_token': TOKEN, 'expires_at': NOW + datetime.timedelta(hours=1)}

MOD_BASE = 'from aieos_bootstrap import dep\nimport json\n\n\ndef fn():\n    return 1\n\n\ndef other():\n    pass\n'
MOD_HEAD = 'from aieos_bootstrap import dep\nimport json\n\n\ndef fn(x):\n    return x\n\n\ndef other():\n    pass\n'


def contract(base, schemas=None, task=TASK, extra=''):
    lines = ['# a header comment', 'task: %s' % task, 'contract_version: v1', 'task_type: implementation',
             'traces_to:', '  - docs/specs/s.md#1', 'input_state:', '  base_commit: %s' % base,
             '  depends_on: [TASK-080]', '  intent_versions:', '    docs/specs/s.md: abc', 'write_set:', '  paths:',
             '    - src/aieos_bootstrap/mod.py', '    - src/aieos_bootstrap/new.py', 'read_set:', '  paths:',
             '    - docs/specs/s.md', '  interfaces: [aieos_bootstrap.mod.fn, "aieos_bootstrap.mod.other (a note)"]']
    if schemas:
        lines.append('  schemas: [%s]' % schemas)
    lines += ['constitution: [INV-001]', 'acceptance_criteria:', '  - AC1: >-', '      One.', 'risk: high',
              'autonomy:', '  budgets: {tokens: 600k, retries: 2}']
    return '\n'.join(lines) + '\n' + extra


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
        self.diff_override = {}

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

    def blob(self, text):
        return self._put('blob', text.encode('utf-8'))

    def _changed(self, oid):
        if oid in self.diff_override:
            return self.diff_override[oid]
        mine = self.files[oid]
        theirs = self.files[self.parents[oid][0]] if self.parents[oid] else {}
        return sorted(p for p in set(mine) | set(theirs) if mine.get(p) != theirs.get(p))

    def __call__(self, repo, args, timeout=30):
        self.calls.append(list(args))
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


BASE_FILES = {'src/aieos_bootstrap/mod.py': MOD_BASE, 'src/aieos_bootstrap/dep.py': 'X = 1\n',
              'docs/a.md': 'a\n', 'top.txt': 'one\n'}


def history(base_files=BASE_FILES, schemas=None):
    """base, c1 (adds the contract), c2 (modifies, adds and deletes), c3 (modifies a top-level file)."""
    repo = Repo()
    base = repo.commit(base_files, message='base')
    f1 = dict(base_files)
    f1['docs/tasks/TASK-100.yaml'] = contract(base, schemas)
    c1 = repo.commit(f1, [base], 'c1')
    f2 = dict(f1)
    f2['src/aieos_bootstrap/mod.py'] = MOD_HEAD
    f2['src/aieos_bootstrap/new.py'] = 'Y = 2\n'
    f2['a/b/c.py'] = 'Z = 3\n'
    f2.pop('docs/a.md', None)
    c2 = repo.commit(f2, [c1], 'c2')
    f3 = dict(f2)
    f3['top.txt'] = 'two\n'
    c3 = repo.commit(f3, [c2], 'c3')
    return repo, base, c1, c2, c3


class Log:
    def __init__(self):
        self.data = b''

    def add(self, event_type, payload, event_id, task_id=TASK, **kw):
        r = eventlog.append(self.data, event_type, payload, event_id, NOW, task_id=task_id, **kw)
        if r.result != 'appended':
            raise AssertionError(r.findings)
        self.data += r.line
        return r.line

    def approve(self, task_id=TASK):
        self.add('task.approved', {'contract_version': 'v1', 'contract_hash': 'a' * 64, 'approval_record': 'r'},
                 'appr-' + task_id, task_id)
        return self

    def submit(self, commit, event_id, task_id=TASK):
        lease = dict(LEASE, task_id=task_id)
        return self.add('task.submitted', {'commit': commit, 'compensating': False}, event_id, task_id,
                        fencing_token=TOKEN, lease=lease)

    def repeat(self, line):
        obj = json.loads(line)
        obj['seq'] = self.data.count(b'\n') + 1
        self.data += json.dumps(obj, sort_keys=True, separators=(',', ':')).encode('utf-8') + b'\n'


def run(repo, commit, log=b'', task_id=TASK, **kw):
    return resume_inputs.git_inputs(ROOT, commit, task_id, log, repo, **kw)


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


class TASK085AC1Arguments(Base):
    def test_arguments_refused_before_any_read(self):
        """TASK-085 AC1: repo, commit, task_id, log or read out of form give findings with zero reads."""
        repo, base, c1, c2, c3 = history()
        for args in ((1, c3, TASK, b''), (ROOT, 'abc', TASK, b''), (ROOT, c3.upper(), TASK, b''),
                     (ROOT, c3, 'TASK-x', b''), (ROOT, c3, TASK, 'log')):
            self.refused(resume_inputs.git_inputs(*args, read=repo))
        self.refused(resume_inputs.git_inputs(ROOT, c3, TASK, b'', read=3))
        self.assertEqual(repo.calls, [])

    def test_default_read_bound_at_call_time(self):
        """TASK-085 AC1: read defaults to gitread.run taken at call time; a patch after import is the one called."""
        repo, base, c1, c2, c3 = history()
        with mock.patch.object(gitread, 'run', repo):
            value = self.good(resume_inputs.git_inputs(ROOT, c3, TASK, b''))
        self.assertEqual(value['head_commit'], c3)
        self.assertTrue(repo.calls)

    def test_every_read_is_a_fixed_form(self):
        """TASK-085 AC1: every recorded call is one of gitread's four fixed forms."""
        repo, base, c1, c2, c3 = history()
        self.good(run(repo, c3))
        for args in repo.calls:
            self.assertIsNone(gitread.form_error(ROOT, args, 30), args)

    def test_commit_given_back_and_a_commit(self):
        """TASK-085 AC1: a commit rev-parse does not give back, or cat-file -t does not call a commit, gives findings."""
        repo, base, c1, c2, c3 = history()

        def wrong_parse(r, args, timeout=30):
            if args[0] == 'rev-parse':
                return ok(b'0' * 40 + b'\n')
            return repo(r, args, timeout)
        self.refused(run(wrong_parse, c3))
        blob = repo.blob('text\n')
        self.refused(run(repo, blob))
        self.refused(run(repo, '9' * 40))


class TASK085AC2Ancestor(Base):
    def setUp(self):
        self.repo = Repo()
        r = self.repo
        self.base = r.commit({'f': '0\n'}, message='base')
        self.a = r.commit({'f': '1\n'}, [self.base], 'a')
        self.b = r.commit({'f': '2\n'}, [self.a], 'b')
        self.root2 = r.commit({'g': '0\n'}, message='root2')
        self.side = r.commit({'f': '3\n'}, [self.base], 'side')
        self.merge = r.commit({'f': '4\n'}, [self.root2, self.side], 'merge')
        self.left = r.commit({'f': '5\n'}, [self.base], 'left')
        self.right = r.commit({'f': '6\n'}, [self.base], 'right')
        self.diamond = r.commit({'f': '7\n'}, [self.left, self.right], 'diamond')

    def anc(self, commit, base, read=None):
        return resume_inputs.is_ancestor(ROOT, commit, base, read or self.repo)

    def test_true_cases(self):
        """TASK-085 AC2: base itself, its child, a later ancestor and a merge's second parent's side give true."""
        for commit in (self.base, self.a, self.b, self.merge):
            self.assertIs(self.good(self.anc(commit, self.base)), True, commit)

    def test_false_when_not_reached(self):
        """TASK-085 AC2: a base not reached when the walk runs out gives false."""
        self.assertIs(self.good(self.anc(self.b, self.root2)), False)
        self.assertIs(self.good(self.anc(self.base, self.b)), False)

    def test_each_commit_visited_once(self):
        """TASK-085 AC2: a diamond is walked with no repeat (one rev-list per commit)."""
        other = self.repo.commit({'h': '0\n'}, message='other')
        self.repo.calls.clear()
        self.assertIs(self.good(self.anc(self.diamond, other)), False)
        walked = [c[-1] for c in self.repo.calls if c[0] == 'rev-list']
        self.assertEqual(len(walked), len(set(walked)))
        self.assertEqual(set(walked), {self.diamond, self.left, self.right, self.base})

    def test_max_walk(self):
        """TASK-085 AC2: MAX_WALK is a module constant read at call time; visiting more commits gives findings."""
        self.assertEqual(resume_inputs.MAX_WALK, 20000)
        with mock.patch.object(resume_inputs, 'MAX_WALK', 1):
            self.refused(self.anc(self.b, self.base))
        with mock.patch.object(resume_inputs, 'MAX_WALK', 2):
            self.assertIs(self.good(self.anc(self.b, self.base)), True)

    def test_arguments_and_never_raises(self):
        """TASK-085 AC2: is_ancestor's arguments are checked as git_inputs' are, and it never raises."""
        for args in ((1, self.b, self.base), (ROOT, 'x', self.base), (ROOT, self.b, 'y')):
            self.refused(resume_inputs.is_ancestor(*args, read=self.repo))

        def boom(r, args, timeout=30):
            raise RecursionError('deep')
        self.refused(self.anc(self.b, self.base, boom))


class TASK085AC3Commits(Base):
    def test_chain_and_change_kinds(self):
        """TASK-085 AC3: oldest first, base left out, {id, paths, submitted}, modified, added and deleted."""
        repo, base, c1, c2, c3 = history()
        value = self.good(run(repo, c3))
        self.assertTrue(value['base_is_ancestor'])
        self.assertEqual(value['commits'], [
            {'id': c1, 'paths': [{'path': 'docs/tasks/TASK-100.yaml', 'change': 'added'}], 'submitted': False},
            {'id': c2, 'paths': [{'path': 'a/b/c.py', 'change': 'added'}, {'path': 'docs/a.md', 'change': 'deleted'},
                                 {'path': 'src/aieos_bootstrap/mod.py', 'change': 'modified'},
                                 {'path': 'src/aieos_bootstrap/new.py', 'change': 'added'}], 'submitted': False},
            {'id': c3, 'paths': [{'path': 'top.txt', 'change': 'modified'}], 'submitted': False}])

    def test_submitted(self):
        """TASK-085 AC3: submitted only for a commit a task.submitted of the task names; others and duplicates aside."""
        repo, base, c1, c2, c3 = history()
        log = Log().approve().approve('TASK-101')
        line = log.submit(c2, 's1')
        log.repeat(line)
        log.submit(c3, 's2', 'TASK-101')
        value = self.good(run(repo, c3, log.data))
        self.assertEqual([c['submitted'] for c in value['commits']], [False, True, False])

    def test_merge_on_the_chain(self):
        """TASK-085 AC3: a merge commit on the first-parent chain gives findings, though base is an ancestor."""
        repo, base, c1, c2, c3 = history()
        side = repo.commit(repo.files[c3], [c2], 'side')
        merge = repo.commit(repo.files[c3], [c3, side], 'merge')
        self.assertIs(self.good(resume_inputs.is_ancestor(ROOT, merge, base, repo)), True)
        self.refused(run(repo, merge))

    def test_neither_listing(self):
        """TASK-085 AC3: a path diff-tree names that is in neither listing gives findings."""
        repo, base, c1, c2, c3 = history()
        repo.diff_override[c3] = ['nowhere.txt']
        self.refused(run(repo, c3))

    def test_each_folder_listed_once(self):
        """TASK-085 AC3: each (commit, folder) is listed once (a counting stand-in)."""
        repo, base, c1, c2, c3 = history()
        seen = []
        real = base_inputs.paths_under

        def counting(r, commit, prefix, read=None):
            seen.append((commit, prefix))
            return real(r, commit, prefix, read)
        with mock.patch.object(base_inputs, 'paths_under', counting):
            self.good(run(repo, c3))
        self.assertTrue(seen)
        self.assertEqual(len(seen), len(set(seen)))

    def test_bounds(self):
        """TASK-085 AC3: MAX_COMMITS and MAX_PATHS are module constants; reaching either gives findings."""
        repo, base, c1, c2, c3 = history()
        self.assertEqual((resume_inputs.MAX_COMMITS, resume_inputs.MAX_PATHS), (1000, 5000))
        with mock.patch.object(resume_inputs, 'MAX_COMMITS', 2):
            self.refused(run(repo, c3))
        with mock.patch.object(resume_inputs, 'MAX_PATHS', 3):
            self.refused(run(repo, c3))


class TASK085AC4Contract(Base):
    def test_contract_and_hash(self):
        """TASK-085 AC4: the contract at the commit, contract_hash the SHA-256 of its bytes, components, schemas []."""
        repo, base, c1, c2, c3 = history()
        value = self.good(run(repo, c3))
        text = repo.files[c3]['docs/tasks/TASK-100.yaml']
        self.assertEqual(value['contract_hash'], hashlib.sha256(text.encode('utf-8')).hexdigest())
        self.assertEqual(value['contract']['task'], TASK)
        self.assertEqual(value['contract']['input_state']['base_commit'], base)
        self.assertEqual(value['components'], [{'id': 'aieos_bootstrap.mod', 'paths': ['src/aieos_bootstrap/mod.py'],
                                                'tags': []}])
        self.assertEqual([i['id'] for i in value['interfaces']],
                         ['aieos_bootstrap.mod.fn', 'aieos_bootstrap.mod.other (a note)'])
        self.assertEqual(value['schemas'], [])

    def test_a_comment_byte_changes_the_hash(self):
        """TASK-085 AC4: a contract changed only in a comment byte has the same parsed value and another hash."""
        repo, base, c1, c2, c3 = history()
        files = dict(repo.files[c3])
        files['docs/tasks/TASK-100.yaml'] = files['docs/tasks/TASK-100.yaml'].replace('# a header', '# A header')
        c4 = repo.commit(files, [c3], 'c4')
        one, two = self.good(run(repo, c3)), self.good(run(repo, c4))
        self.assertEqual(one['contract'], two['contract'])
        self.assertNotEqual(one['contract_hash'], two['contract_hash'])

    def contract_case(self, text):
        repo, base, c1, c2, c3 = history()
        files = dict(repo.files[c3])
        if text is None:
            files.pop('docs/tasks/TASK-100.yaml')
        else:
            files['docs/tasks/TASK-100.yaml'] = text
        return repo, base, repo.commit(files, [c3], 'c4')

    def test_contract_refusals(self):
        """TASK-085 AC4: a missing file, a subset refusal, a missing key, another task or a bad base_commit fail."""
        repo, base, c4 = self.contract_case(None)
        self.refused(run(repo, c4))
        for text in ('task: [unclosed\n', contract('0' * 40).replace('acceptance_criteria:', 'other:'),
                     contract('0' * 40, task='TASK-101'), contract('abc')):
            repo, base, c4 = self.contract_case(text)
            self.refused(run(repo, c4))

    def test_interfaces_and_schemas_refused(self):
        """TASK-085 AC4: an interface entry out of form and a non-empty read_set.schemas give findings."""
        repo, base, c1, c2, c3 = history()
        bad = contract(base).replace('aieos_bootstrap.mod.fn,', 'not.an.interface,')
        repo, base, c4 = self.contract_case(bad)
        self.refused(run(repo, c4))
        repo, base, c1, c2, c3 = history(schemas='reset_tokens')
        self.refused(run(repo, c3))

    def test_base_not_a_commit(self):
        """TASK-085 AC4: a base_commit naming no object or a blob gives false, [], [] and null, with no findings."""
        for make in (lambda r: '7' * 40, lambda r: r.blob('a blob\n')):
            repo = Repo()
            missing = make(repo)
            c = repo.commit(dict(BASE_FILES, **{'docs/tasks/TASK-100.yaml': contract(missing)}), message='only')
            value = self.good(run(repo, c))
            self.assertIs(value['base_is_ancestor'], False)
            self.assertEqual((value['commits'], value['derived_read_set']), ([], []))
            self.assertEqual([s['base'] for s in value['symbols']], [None, None])
            self.assertIsNotNone(value['symbols'][0]['head'])

    def test_kind_error_and_given_commit(self):
        """TASK-085 AC4: a cat-file -t answer with an error gives findings; a given commit naming no object fails."""
        repo, base, c1, c2, c3 = history()

        def failing(r, args, timeout=30):
            if args[:2] == ['cat-file', '-t'] and args[2] == base:
                return {'exit': None, 'out': b'', 'err': b'', 'error': 'timeout'}
            return repo(r, args, timeout)
        self.refused(run(failing, c3))
        self.refused(run(repo, '8' * 40))


class TASK085AC5SymbolsAndDerived(Base):
    def test_symbols(self):
        """TASK-085 AC5: base and head forms; a changed signature differs, an unchanged one is equal; whole entry."""
        repo, base, c1, c2, c3 = history()
        value = self.good(run(repo, c3))
        fn, other = value['symbols']
        self.assertEqual((fn['interface'], other['interface']),
                         ('aieos_bootstrap.mod.fn', 'aieos_bootstrap.mod.other (a note)'))
        self.assertEqual(fn['base'], resume_check.signature_form(MOD_BASE, 'fn'))
        self.assertEqual(fn['head'], resume_check.signature_form(MOD_HEAD, 'fn'))
        self.assertNotEqual(fn['base'], fn['head'])
        self.assertEqual(other['base'], other['head'])
        self.assertIsNotNone(other['base'])

    def test_absent_module_and_unparsable(self):
        """TASK-085 AC5: a module absent at base_commit gives base null; the same unparsable text gives both null."""
        files = dict(BASE_FILES)
        files.pop('src/aieos_bootstrap/mod.py')
        repo, base, c1, c2, c3 = history(files)
        value = self.good(run(repo, c3))
        self.assertEqual([s['base'] for s in value['symbols']], [None, None])
        broken = 'def fn(:\n'
        files = dict(BASE_FILES, **{'src/aieos_bootstrap/mod.py': broken})
        repo = Repo()
        base = repo.commit(files, message='base')
        c1 = repo.commit(dict(files, **{'docs/tasks/TASK-100.yaml': contract(base)}), [base], 'c1')
        value = self.good(run(repo, c1))
        self.assertEqual([(s['base'], s['head']) for s in value['symbols']], [(None, None), (None, None)])
        self.assertEqual(value['derived_read_set'], [])

    def test_derived(self):
        """TASK-085 AC5: the resolved direct imports of the write set's .py files at base_commit, sorted, once."""
        repo, base, c1, c2, c3 = history()
        value = self.good(run(repo, c3))
        self.assertEqual(value['derived_read_set'], ['src/aieos_bootstrap/dep.py'])

    def test_derived_star_entry(self):
        """TASK-085 AC5: a "*" write-set entry is matched over the whole base listing; .py files only."""
        repo = Repo()
        files = dict(BASE_FILES, **{'src/aieos_bootstrap/notes.md': 'import json\n'})
        base = repo.commit(files, message='base')
        text = contract(base).replace('    - src/aieos_bootstrap/new.py\n', '    - src/aieos_bootstrap/*\n')
        c1 = repo.commit(dict(files, **{'docs/tasks/TASK-100.yaml': text}), [base], 'c1')
        value = self.good(run(repo, c1))
        self.assertEqual(value['derived_read_set'], ['src/aieos_bootstrap/dep.py'])


PLACEHOLDERS = {'task_id': TASK, 'log_seq': 1, 'task_state': 'READY', 'observed_read_set': None, 'intent_current': {},
                'dependencies': {}, 'articles': [], 'runtime': {'adapter': 'a', 'max_risk': 'high'}, 'risk_rules': [],
                'policy_version': None, 'budget_use': {}}


class TASK085AC6Output(Base):
    def test_exact_keys_and_section_9_forms(self):
        """TASK-085 AC6: exactly the ten keys; with the other twelve as placeholders, check gives no error."""
        repo, base, c1, c2, c3 = history()
        value = self.good(run(repo, c3))
        self.assertEqual(set(value), set(resume_inputs.KEYS))
        self.assertEqual(len(value), 10)
        inputs = dict(value, approved_contract_hash=value['contract_hash'], **PLACEHOLDERS)
        self.assertEqual(set(inputs), resume_check.INPUT_KEYS)
        record = resume_check.check(inputs)
        self.assertIsNone(record.get('error'), record.get('error'))

    def test_fails_closed(self):
        """TASK-085 AC6: a raising read, an answer out of form or a refused log give findings; nothing raises."""
        repo, base, c1, c2, c3 = history()
        for exc in (RuntimeError('x'), RecursionError('deep'), MemoryError()):
            def bad(r, args, timeout=30, exc=exc):
                raise exc
            self.refused(run(bad, c3))
        self.refused(run(lambda r, args, timeout=30: {'exit': 0}, c3))
        self.refused(run(lambda r, args, timeout=30: ok('text'), c3))
        self.refused(run(repo, c3, b'not a log line\n'))
        with mock.patch.object(resume_inputs, '_head', side_effect=RecursionError('deep')):
            self.refused(run(repo, c3))


class TASK085AC7Modules(Base):
    def tree(self, path):
        return ast.parse(path.read_bytes().decode('utf-8'))

    def test_base_inputs_wrappers(self):
        """TASK-085 AC7: contract_at, components_of, paths_under and submitted_commits give their stated values."""
        repo, base, c1, c2, c3 = history()
        (con, digest), found = base_inputs.contract_at(ROOT, c3, TASK, repo)
        self.assertIsNone(found)
        self.assertEqual(digest, hashlib.sha256(repo.files[c3]['docs/tasks/TASK-100.yaml'].encode('utf-8')).hexdigest())
        self.refused(base_inputs.contract_at(ROOT, c3, 'TASK-x', repo))
        (components, interfaces), found = base_inputs.components_of(con)
        self.assertIsNone(found)
        self.assertEqual(len(components), 1)
        self.refused(base_inputs.components_of('text'))
        self.assertEqual(base_inputs.paths_under(ROOT, c3, 'a', repo), (['a/b/c.py'], None))
        self.assertEqual(base_inputs.paths_under(ROOT, c3, 'gone', repo), ([], None))
        log = Log().approve()
        log.submit(c2, 's1')
        self.assertEqual(base_inputs.submitted_commits(log.data, TASK), ([c2], None))
        self.assertEqual(base_inputs.submitted_commits(log.data, 'TASK-101'), ([], None))
        self.refused(base_inputs.submitted_commits('log', TASK))

    def test_base_inputs_imports_and_attributes(self):
        """TASK-085 AC7: base_inputs.py's imports and used attributes are still exactly those test_base_inputs pins."""
        tree = self.tree(BASE_SRC)
        names = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                names |= {a.name for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                names |= {'%s.%s' % (n.module, a.name) for a in n.names}
        self.assertEqual(names, {'hashlib', 're', 'aieos_bootstrap.base_files', 'aieos_bootstrap.contract_path',
                                 'aieos_bootstrap.gitread', 'aieos_bootstrap.records', 'aieos_bootstrap.resume_check'})
        used = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in (
                    'base_files', 'contract_path', 'gitread', 'records', 'resume_check'):
                used.setdefault(n.value.id, set()).add(n.attr)
        self.assertEqual(used, {'base_files': {'read_file', 'list_paths', 'MAX_BYTES'},
                                'contract_path': {'candidates', 'decide'}, 'gitread': {'run'},
                                'records': {'check_log'}, 'resume_check': {'matches'}})

    def test_new_module_imports_and_names(self):
        """TASK-085 AC7: the new module imports re and four aieos_bootstrap modules, and names no refused name."""
        tree = self.tree(SRC)
        names = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                names |= {a.name for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                names |= {'%s.%s' % (n.module, a.name) for a in n.names}
        self.assertEqual(names, {'re', 'aieos_bootstrap.base_files', 'aieos_bootstrap.base_inputs',
                                 'aieos_bootstrap.gitread', 'aieos_bootstrap.resume_check'})
        ids = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertFalse(ids & {'open', 'exec', 'eval', 'compile', '__import__', 'subprocess', 'os', 'sys', 'time',
                                'autonomy'})
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        self.assertFalse(attrs & {'now', 'environ', 'getenv', 'write', 'grant_lease', 'append_event'})
        strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertFalse(any(('.' + 'aieos') in s for s in strings))

    def test_no_clock_or_environment(self):
        """TASK-085 AC7: no clock and no environment read; every Git call goes through read."""
        repo, base, c1, c2, c3 = history()
        with mock.patch('time.time', side_effect=AssertionError('time')), \
                mock.patch('os.getenv', side_effect=AssertionError('getenv')), \
                mock.patch.object(gitread, 'run', side_effect=AssertionError('run')):
            self.good(run(repo, c3))


PHRASES = ['the commit is an argument', 'read is injectable', 'never raises', 'writes nothing', 'fails closed',
           "this task's choice", 'ten of the 22 inputs', 'DEF-0097', 'R5 F4']


class TASK085AC9Docstrings(Base):
    def test_docstring_phrases(self):
        """TASK-085 AC9: the new module's docstring holds the contract's phrases, whitespace read as single spaces."""
        doc = ' '.join(ast.get_docstring(ast.parse(SRC.read_bytes().decode('utf-8'))).split())
        for phrase in PHRASES:
            self.assertIn(phrase, doc)

    def test_base_inputs_paragraph(self):
        """TASK-085 AC9: base_inputs.py's docstring names the four wrappers and TASK-085."""
        doc = ' '.join(ast.get_docstring(ast.parse(BASE_SRC.read_bytes().decode('utf-8'))).split())
        for word in ('contract_at', 'components_of', 'paths_under', 'submitted_commits', 'TASK-085'):
            self.assertIn(word, doc)

    def test_naming(self):
        """TASK-085 AC9: every test of this module names "TASK-085 ACn" at the start of its docstring."""
        classes = [v for v in globals().values() if isinstance(v, type) and issubclass(v, unittest.TestCase)
                   and v.__module__ == __name__]
        self.assertGreater(len(classes), 5)
        for cls in classes:
            for name in unittest.TestLoader().getTestCaseNames(cls):
                self.assertRegex(getattr(cls, name).__doc__ or '', r'^TASK-085 AC\d+', name)


if __name__ == '__main__':
    unittest.main()

"""Unit tests of aieos_bootstrap.base_inputs (TASK-082): the arguments, the contract's subset of YAML, the log's
approval and resume record, the articles, components, interfaces and traced entries, the files and derived paths, the
handoff and budgets, purity and what the module may touch, its docstring and this module's own naming rule. Every Git
answer comes from a stand-in read over objects held in memory; every log is built with eventlog.append; no test runs
Git or writes a file; the source is read with pathlib's read_bytes."""

import ast
import datetime
import hashlib
import json
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import base_inputs, conformance, context_compiler, eventlog, gitread

HERE = pathlib.Path(__file__).resolve()
ROOT = str(HERE.parents[2])
SRC = HERE.parents[2] / 'src' / 'aieos_bootstrap' / 'base_inputs.py'
TASK = 'TASK-100'
NOW = datetime.datetime(2026, 10, 24, 12, 0, 0, tzinfo=datetime.timezone.utc)

CONTRACT = '''# a header comment
task: TASK-100
contract_version: v1
task_type: implementation
objective: >-
  Read the inputs
  at a commit.
traces_to:
  - docs/specs/s.md#1
  - docs/specs/s.md#2
input_state:
  base_commit: 0000000000000000000000000000000000000000
  depends_on: [TASK-080, TASK-081]
write_set:
  paths:
    - src/aieos_bootstrap/new.py
    - src/aieos_bootstrap/mod.py
read_set:
  paths:
    - docs/specs/s.md
    - docs/missing/**
  interfaces: [aieos_bootstrap.mod.fn, "aieos_bootstrap.mod.other (a note)",
    aieos_bootstrap.t0.run]
acceptance_criteria:
  - AC1: >-
      The first line
      and the second.
  - AC2: >-
      Only one.
capabilities:
  shell: {allow: ["timeout 110 python <a script that
    runs> < /dev/null"]}
risk: high
autonomy:
  budgets: {tokens: 600k, retries: 2}
exit_conditions:
  success: all gates pass AND one
    approval record counts
owner_kept_act: false
'''

CONSTITUTION = '''# The constitution

## 3. Articles

### INV-001 · architecture · The core writes no code
- Rule: one.
- Check: partial.

### INV-002 · architecture · Standard library only
- Rule: two.

## 4. Later
text
'''

FILES = {
    'docs/tasks/TASK-100.yaml': CONTRACT,
    'docs/pre-genesis/constitution.md': CONSTITUTION,
    'docs/specs/s.md': 'the spec\n',
    'docs/specs/derived.md': 'a derived file\n',
    'src/aieos_bootstrap/mod.py': 'def fn():\n    return 1\n',
    'src/aieos_bootstrap/other.py': 'X = 1\n',
}


def gid(kind, data):
    return hashlib.sha1(b'%s %d\x00' % (kind.encode('ascii'), len(data)) + data, usedforsecurity=False).hexdigest()


def ok(out):
    return {'exit': 0, 'out': out, 'err': b'', 'error': None}


class Git:
    """A stand-in for gitread.run over objects held in memory, ids being Git's own hashes; it counts its calls."""

    def __init__(self, files, extra_entries=None):
        self.objects = {}
        self.calls = []
        self.root = self._tree(self._nest(files), extra_entries or {}, '')
        self.head = self._put('commit', ('tree %s\nauthor A B 1 +0000\ncommitter A B 1 +0000\n\nm\n'
                                         % self.root).encode('ascii'))

    def _put(self, kind, data):
        oid = gid(kind, data)
        self.objects[oid] = (kind, data)
        return oid

    def _nest(self, files):
        tree = {}
        for path, text in files.items():
            node = tree
            names = path.split('/')
            for name in names[:-1]:
                node = node.setdefault(name, {})
            node[names[-1]] = text
        return tree

    def _tree(self, node, extra, at):
        entries = []
        for name, value in node.items():
            here = at + name
            if isinstance(value, dict):
                entries.append(('040000', 'tree', self._tree(value, extra, here + '/'), name))
            else:
                data = value.encode('utf-8') if isinstance(value, str) else value
                entries.append(('100644', 'blob', self._put('blob', data), name))
        for mode, kind, oid, name in extra.get(at, []):
            entries.append((mode, kind, oid, name))
        return self._put('tree', ''.join('%s %s %s\t%s\n' % e for e in entries).encode('utf-8'))

    def __call__(self, repo, args, timeout=30):
        self.calls.append(list(args))
        oid = args[-1]
        if oid not in self.objects:
            return {'exit': 128, 'out': b'', 'err': b'fatal', 'error': None}
        if args[0] == 'rev-parse':
            return ok((oid + '\n').encode('ascii'))
        if args[1] == '-t':
            return ok((self.objects[oid][0] + '\n').encode('ascii'))
        return ok(self.objects[oid][1])


def contract_hash(text=CONTRACT):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def resume_record(decision='CONTINUE', **over):
    rec = {'record_id': 'rec-1', 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_local',
           'recorder': 'the Resume Check (stand-in)', 'subject': TASK, 'decision': decision, 'uncovered': [],
           'state_effect': [], 'contract_hash': contract_hash(), 'contract_version': 'v1',
           'constitution': {'applicable': ['INV-001', 'INV-002'], 'violated': [], 'no_result': []},
           'read_set': {'entries': [{'entry': 'docs/specs/derived.md', 'kind': 'path', 'sources': ['derived']},
                                    {'entry': 'docs/specs/gone.md', 'kind': 'path', 'sources': ['derived']},
                                    {'entry': 'docs/specs/s.md', 'kind': 'path', 'sources': ['declared']}],
                        'estimate': True, 'unresolved': [], 'unanalysed': []}}
    rec.update(over)
    return rec


class Log:
    def __init__(self):
        self.data = b''

    def add(self, event_type, payload, event_id, task_id=TASK):
        r = eventlog.append(self.data, event_type, payload, event_id, NOW, task_id=task_id)
        if r.result != 'appended':
            raise AssertionError(r.findings)
        self.data += r.line
        return r.line

    def repeat(self, line):
        """An ignored duplicate: the same event with the next seq."""
        obj = json.loads(line)
        obj['seq'] = self.data.count(b'\n') + 1
        self.data += json.dumps(obj, sort_keys=True, separators=(',', ':')).encode('utf-8') + b'\n'


def good_log(record=None, approval_hash=None, version='v1'):
    log = Log()
    log.add('task.approved', {'contract_version': version, 'contract_hash': approval_hash or contract_hash(),
                              'approval_record': 'appr-1'}, 'approved-1')
    log.add('decision.execution', record or resume_record(), 'exec-1')
    return log


def call(files=FILES, log=None, git=None, **kw):
    git = git or Git(files)
    data = (log or good_log()).data
    return base_inputs.work_order_inputs(ROOT, git.head, TASK, 's1', data, git, **kw), git


class Base(unittest.TestCase):
    def refused(self, result):
        value, findings = result
        self.assertIsNone(value)
        self.assertIsInstance(findings, list)
        self.assertTrue(findings)
        self.assertTrue(all(isinstance(f, str) for f in findings))
        return findings

    def parse_refused(self, text):
        with self.assertRaises(base_inputs._Stop) as cm:
            base_inputs._parse_contract_text(text)
        return cm.exception.findings


class TASK082AC1Arguments(Base):
    def test_arguments_refused_with_zero_calls(self):
        """TASK-082 AC1: each argument out of form, a str subclass among them, gives findings with zero read calls."""
        class S(str):
            pass
        git = Git(FILES)
        data = good_log().data
        cases = [(5, git.head, TASK, 's1', data), (ROOT, 'x', TASK, 's1', data), (ROOT, git.head, 'T-1', 's1', data),
                 (ROOT, git.head, TASK, 'a b', data), (ROOT, git.head, TASK, 's1', 'text'),
                 (S(ROOT), git.head, TASK, 's1', data), (ROOT, S(git.head), TASK, 's1', data),
                 (ROOT, git.head, S(TASK), 's1', data), (ROOT, git.head, TASK, 's' * 129, data)]
        for args in cases:
            self.refused(base_inputs.work_order_inputs(*args, read=git))
        self.refused(base_inputs.work_order_inputs(ROOT, git.head, TASK, 's1', data, read=5))
        self.assertEqual(git.calls, [])


class TASK082AC2Contract(Base):
    def test_the_forms_parse(self):
        """TASK-082 AC2: the subset's forms parse into strs, lists and dicts, "2" and "false" staying strs."""
        c = base_inputs._parse_contract_text(CONTRACT)
        self.assertEqual(c['objective'], 'Read the inputs at a commit.')
        self.assertEqual(c['input_state']['depends_on'], ['TASK-080', 'TASK-081'])
        self.assertEqual(c['read_set']['interfaces'], ['aieos_bootstrap.mod.fn', 'aieos_bootstrap.mod.other (a note)',
                                                       'aieos_bootstrap.t0.run'])
        self.assertEqual(c['acceptance_criteria'], [{'AC1': 'The first line and the second.'}, {'AC2': 'Only one.'}])
        self.assertEqual(c['capabilities']['shell']['allow'], ['timeout 110 python <a script that runs> < /dev/null'])
        self.assertEqual(c['autonomy']['budgets'], {'tokens': '600k', 'retries': '2'})
        self.assertEqual(c['exit_conditions']['success'], 'all gates pass AND one approval record counts')
        self.assertEqual(c['owner_kept_act'], 'false')

    def test_more_forms(self):
        """TASK-082 AC2: a sequence at its key's indentation, "- >-" items, a multi-line plain item, a multi-line plain
        scalar in a flow list, a continuation starting with "`", and ">-" with a blank and a more-indented line."""
        text = ('a:\n- x\n- y\nb:\n  - >-\n    one\n    two\n  - first\n    `second`\nc: [p q\n  r, s]\n'
                'd: >-\n  l1\n  l2\n\n  l3\n    deeper\n  l4\n')
        c = base_inputs._parse_contract_text(text)
        self.assertEqual(c['a'], ['x', 'y'])
        self.assertEqual(c['b'], ['one two', 'first `second`'])
        self.assertEqual(c['c'], ['p q r', 's'])
        self.assertEqual(c['d'], 'l1 l2\nl3\n  deeper\nl4')

    def test_refused_forms(self):
        """TASK-082 AC2: each refused form gives findings."""
        cases = ['a: b\n' + 'x' * (base_inputs.MAX_CONTRACT_BYTES + 1), '\ufeffa: b\n', 'a: b\r\n', 'a: b\x01\n',
                 'a: b\u2028\n', 'a:\tb\n', 'a: b\na: c\n', 'a: &x b\n', 'a: *x\n', 'a: !t b\n', 'a: |\n  b\n',
                 '---\na: b\n', "a: 'b'\n", 'a: "b\\n"\n', 'a: b #c\n', 'a: b: c\n', 'a: @b\n', 'a: `b\n', 'a:\n',
                 'a: [b] c\n', ' a: b\n', 'a: [b, c\n', 'a: [b {c}]\n', 'a: [b: c]\n', 'a:\n   b: c\n',
                 'a:\n  - x\n    y: z\n  - k: v\n    m: n\n']
        for text in cases:
            self.parse_refused(text)

    def test_depth_bound(self):
        """TASK-082 AC2: nesting over MAX_DEPTH gives findings."""
        with mock.patch.object(base_inputs, 'MAX_DEPTH', 3):
            self.parse_refused('a: [[[[[b]]]]]\n')

    def test_missing_key(self):
        """TASK-082 AC2: a contract without a key context_compiler needs gives findings."""
        text = CONTRACT.replace('traces_to:\n  - docs/specs/s.md#1\n  - docs/specs/s.md#2\n', '')
        files = dict(FILES, **{'docs/tasks/TASK-100.yaml': text})
        log = good_log(resume_record(contract_hash=contract_hash(text)), approval_hash=contract_hash(text))
        self.assertIn('traces_to', ' '.join(self.refused(call(files, log)[0])))


class TASK082AC3Approval(Base):
    def test_hash_and_version(self):
        """TASK-082 AC3: a hash or a contract_version other than the approval's gives findings."""
        self.refused(call(log=good_log(approval_hash='b' * 64))[0])
        self.refused(call(log=good_log(version='v2'))[0])

    def test_no_approval_and_another_task(self):
        """TASK-082 AC3: no task.approved, or only another task's, gives findings."""
        log = Log()
        log.add('decision.execution', resume_record(), 'exec-1')
        self.refused(call(log=log)[0])
        log = Log()
        log.add('task.approved', {'contract_version': 'v1', 'contract_hash': contract_hash(),
                                  'approval_record': 'a'}, 'approved-x', task_id='TASK-101')
        log.add('decision.execution', resume_record(), 'exec-1')
        self.refused(call(log=log)[0])

    def test_bad_log(self):
        """TASK-082 AC3: a log with any check_log finding gives findings."""
        log = good_log()
        log.data += b'not json\n'
        self.refused(call(log=log)[0])

    def test_duplicate_does_not_count(self):
        """TASK-082 AC3: an ignored duplicate placed after a newer line does not change which approval is last."""
        log = Log()
        first = log.add('task.approved', {'contract_version': 'v1', 'contract_hash': 'b' * 64,
                                          'approval_record': 'a1'}, 'approved-1')
        log.add('task.approved', {'contract_version': 'v1', 'contract_hash': contract_hash(),
                                  'approval_record': 'a2'}, 'approved-2')
        log.repeat(first)
        log.add('decision.execution', resume_record(), 'exec-1')
        value, findings = call(log=log)[0]
        self.assertIsNone(findings, findings)


class TASK082AC4Record(Base):
    def test_record_after_approval(self):
        """TASK-082 AC4: a decision.execution before the last task.approved only gives findings."""
        log = Log()
        log.add('decision.execution', resume_record(), 'exec-1')
        log.add('task.approved', {'contract_version': 'v1', 'contract_hash': contract_hash(),
                                  'approval_record': 'a'}, 'approved-1')
        self.refused(call(log=log)[0])

    def test_later_record_supersedes(self):
        """TASK-082 AC4: a later decision.execution supersedes an earlier one."""
        log = good_log()
        log.add('decision.execution', resume_record('REPLAN', record_id='rec-2'), 'exec-2')
        self.refused(call(log=log)[0])
        log = good_log(resume_record('REPLAN'))
        log.add('decision.execution', resume_record(record_id='rec-2'), 'exec-2')
        self.assertIsNone(call(log=log)[0][1])

    def test_decision_and_ties(self):
        """TASK-082 AC4: a decision other than CONTINUE or CONTINUE_WITH, and each tie that differs, give findings."""
        for rec in (resume_record('BLOCKED'), resume_record(contract_hash='c' * 64),
                    resume_record(contract_version='v2')):
            self.refused(call(log=good_log(rec))[0])
        self.assertIsNone(call(log=good_log(resume_record('CONTINUE_WITH')))[0][1])

    def test_subject_tie_direct(self):
        """TASK-082 AC4: a record whose subject differs from the task gives findings (reached by a direct call, since a
        valid log refuses such a record first)."""
        git = Git(FILES)
        state = {'repo': ROOT, 'commit': git.head, 'read': git, 'listings': {}}
        approval = {'contract_version': 'v1', 'contract_hash': contract_hash(), 'approval_record': 'a'}
        with self.assertRaises(base_inputs._Stop) as cm:
            base_inputs._contract(state, TASK, approval, resume_record(subject='TASK-101'))
        self.assertIn('subject', ' '.join(cm.exception.findings))


class TASK082AC5Sources(Base):
    def test_articles(self):
        """TASK-082 AC5: each article's block, its trailing blank lines stripped; a missing or doubled id gives
        findings; an id with regular-expression characters is read as text."""
        value, findings = call()[0]
        self.assertIsNone(findings, findings)
        self.assertEqual(value['articles']['INV-001'],
                         '### INV-001 · architecture · The core writes no code\n- Rule: one.\n- Check: partial.')
        self.assertEqual(value['articles']['INV-002'], '### INV-002 · architecture · Standard library only\n- Rule: two.')
        for applicable in (['INV-00.'], ['INV-003']):
            rec = resume_record(constitution={'applicable': applicable, 'violated': [], 'no_result': []})
            self.refused(call(log=good_log(rec))[0])
        doubled = dict(FILES, **{'docs/pre-genesis/constitution.md': CONSTITUTION + '### INV-001 · x · y\n'})
        self.refused(call(doubled)[0])

    def test_components_and_interfaces(self):
        """TASK-082 AC5: one component per module, tags [], one interface per entry."""
        value = call()[0][0]
        self.assertEqual(value['components'], [
            {'id': 'aieos_bootstrap.mod', 'paths': ['src/aieos_bootstrap/mod.py'], 'tags': []},
            {'id': 'aieos_bootstrap.t0', 'paths': ['src/aieos_bootstrap/t0.py'], 'tags': []}])
        self.assertEqual([i['id'] for i in value['interfaces']],
                         ['aieos_bootstrap.mod.fn', 'aieos_bootstrap.mod.other (a note)', 'aieos_bootstrap.t0.run'])

    def contract_with(self, old, new):
        text = CONTRACT.replace(old, new)
        files = dict(FILES, **{'docs/tasks/TASK-100.yaml': text})
        log = good_log(resume_record(contract_hash=contract_hash(text)), approval_hash=contract_hash(text))
        return call(files, log)[0]

    def test_refused_sources(self):
        """TASK-082 AC5: an interface entry out of form or listed twice, a non-empty schemas, an ADR id and a missing
        traced file give findings; adrs is {} and traced holds each entry, the file read whole."""
        self.refused(self.contract_with('aieos_bootstrap.t0.run]', 'other.thing]'))
        self.refused(self.contract_with('aieos_bootstrap.t0.run]', 'aieos_bootstrap.mod.fn]'))
        self.refused(self.contract_with('  interfaces:', '  schemas: [x]\n  interfaces:'))
        self.refused(self.contract_with('  - docs/specs/s.md#2\n', '  - ADR-001\n'))
        self.refused(self.contract_with('  - docs/specs/s.md#2\n', '  - docs/specs/none.md\n'))
        value = call()[0][0]
        self.assertEqual(value['adrs'], {})
        self.assertEqual(value['traced'], {'docs/specs/s.md#1': 'the spec\n', 'docs/specs/s.md#2': 'the spec\n'})


class TASK082AC6Files(Base):
    def test_files_and_derived(self):
        """TASK-082 AC6: the matched paths, a missing prefix and a new write_set path giving none, and the derived
        paths present at the commit."""
        value = call()[0][0]
        self.assertEqual(sorted(value['files']), ['docs/specs/derived.md', 'docs/specs/s.md',
                                                  'src/aieos_bootstrap/mod.py'])
        self.assertEqual(value['derived_read_set'], ['docs/specs/derived.md'])

    def test_read_set_form(self):
        """TASK-082 AC6: a record read_set that is not an object with entries in its form gives findings."""
        for rs in ({'entries': [{'entry': 'a'}]}, {'entries': [{'entry': 5, 'kind': 'path', 'sources': []}]}):
            self.refused(call(log=good_log(resume_record(read_set=rs)))[0])
        git = Git(FILES)
        state = {'repo': ROOT, 'commit': git.head, 'read': git, 'listings': {}}
        bare = resume_record(read_set=[{'entry': 'a', 'kind': 'path', 'sources': ['derived']}])
        with self.assertRaises(base_inputs._Stop) as cm:
            base_inputs._derived(state, bare)
        self.assertIn('read_set', ' '.join(cm.exception.findings))

    def test_other_finding_fails(self):
        """TASK-082 AC6: a listing finding other than "is missing" (a symbolic link under a prefix) fails the call."""
        link = gid('blob', b'target')
        git = Git(FILES, {'docs/specs/': [('120000', 'blob', link, 'link')]})
        git.objects[link] = ('blob', b'target')
        self.refused(call(git=git)[0])

    def test_bounds(self):
        """TASK-082 AC6: MAX_FILES, MAX_FILE_BYTES and MAX_PATTERNS each give findings when crossed."""
        for name, value in (('MAX_FILES', 2), ('MAX_FILE_BYTES', 10), ('MAX_PATTERNS', 3)):
            with mock.patch.object(base_inputs, name, value):
                self.refused(call()[0])
        self.assertIsNone(call()[0][1])

    def test_read_cache(self):
        """TASK-082 AC6: the read cache asks each fixed form once per call, with a given read and with the default."""
        (value, findings), git = call()
        self.assertIsNone(findings)
        self.assertEqual(len(git.calls), len({tuple(c) for c in git.calls}))
        git = Git(FILES)
        with mock.patch.object(gitread, 'run', git):
            value, findings = base_inputs.work_order_inputs(ROOT, git.head, TASK, 's1', good_log().data)
        self.assertIsNone(findings, findings)
        self.assertEqual(len(git.calls), len({tuple(c) for c in git.calls}))

    def test_compiles(self):
        """TASK-082 AC6: the value is accepted by context_compiler.build_work_order."""
        value = call()[0][0]
        work_order, findings = context_compiler.build_work_order(value)
        self.assertIsNone(findings, findings)
        self.assertEqual(work_order['task'], TASK)


class TASK082AC7Handoff(Base):
    def test_handoffs(self):
        """TASK-082 AC7: none gives None, exactly one gives {ref, text}, two or more give findings; budgets equal
        BUDGETS."""
        value = call()[0][0]
        self.assertIsNone(value['last_handoff'])
        self.assertEqual(value['budgets'], base_inputs.BUDGETS)
        one = dict(FILES, **{'docs/handoffs/TASK-100-s0.md': 'done\n'})
        self.assertEqual(call(one)[0][0]['last_handoff'], {'ref': 'docs/handoffs/TASK-100-s0.md', 'text': 'done\n'})
        two = dict(one, **{'docs/handoffs/TASK-100-s1.md': 'more\n'})
        self.refused(call(two)[0])
        other = dict(FILES, **{'docs/handoffs/TASK-1000-s0.md': 'x\n'})
        self.assertIsNone(call(other)[0][0]['last_handoff'])


class TASK082AC8Purity(Base):
    def tree(self):
        return ast.parse(SRC.read_bytes().decode('utf-8'))

    def test_imports_and_names(self):
        """TASK-082 AC8: the module imports exactly hashlib, re and base_files, gitread, records and resume_check, and
        uses exactly the names its contract lists."""
        names = set()
        for n in ast.walk(self.tree()):
            if isinstance(n, ast.Import):
                names |= {a.name for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                names |= {'%s.%s' % (n.module, a.name) for a in n.names}
        self.assertEqual(names, {'hashlib', 're', 'aieos_bootstrap.base_files', 'aieos_bootstrap.gitread',
                                 'aieos_bootstrap.records', 'aieos_bootstrap.resume_check'})
        used = {}
        for n in ast.walk(self.tree()):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in (
                    'base_files', 'gitread', 'records', 'resume_check'):
                used.setdefault(n.value.id, set()).add(n.attr)
        self.assertEqual(used, {'base_files': {'read_file', 'list_paths', 'MAX_BYTES'}, 'gitread': {'run'},
                                'records': {'check_log'}, 'resume_check': {'matches'}})

    def test_refused_names_and_strings(self):
        """TASK-082 AC8: no refused name, call, string or handler."""
        tree = self.tree()
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertFalse(names & {'compile', 'open', 'exec', 'eval', '__import__', '__builtins__', 'subprocess', 'os'})
        attrs = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertFalse(attrs & {'open', 'connect', 'read_text', 'read_bytes', 'listdir', 'scandir', 'stat', 'walk'})
        strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertFalse(any(('.' + 'aieos') in s for s in strings))
        self.assertFalse(set(strings) & {'valid', 'accepted', 'approved'})
        raw = SRC.read_bytes()
        self.assertNotIn(('ben' + 'ch/').encode('ascii'), raw)
        for d in (conformance.FIXTURE_DIR, conformance.RC_FIXTURE_DIR, conformance.RISK_FIXTURE_DIR,
                  conformance.CB_FIXTURE_DIR):
            self.assertNotIn(d.rsplit('/', 1)[1].encode('ascii'), raw)
        for n in ast.walk(tree):
            if isinstance(n, ast.ExceptHandler):
                self.assertFalse(all(isinstance(s, (ast.Pass, ast.Continue)) for s in n.body))

    def test_no_open_clock_or_environment(self):
        """TASK-082 AC8: no open, no clock, no environment read; every Git call goes through read."""
        git = Git(FILES)
        data = good_log().data
        with mock.patch('builtins.open', side_effect=AssertionError('open')), \
                mock.patch('time.time', side_effect=AssertionError('time')), \
                mock.patch('os.getenv', side_effect=AssertionError('getenv')), \
                mock.patch.object(gitread, 'run', side_effect=AssertionError('run')):
            value, findings = base_inputs.work_order_inputs(ROOT, git.head, TASK, 's1', data, git)
        self.assertIsNone(findings, findings)

    def test_never_raises(self):
        """TASK-082 AC8: a read that raises, and one that raises RecursionError, give findings."""
        git = Git(FILES)
        data = good_log().data
        for exc in (RuntimeError('x'), RecursionError('deep'), MemoryError()):
            def bad(repo, args, timeout=30, exc=exc):
                raise exc
            self.refused(base_inputs.work_order_inputs(ROOT, git.head, TASK, 's1', data, bad))
        with mock.patch.object(base_inputs, '_inputs', side_effect=RecursionError('deep')):
            self.refused(base_inputs.work_order_inputs(ROOT, git.head, TASK, 's1', data, git))


PHRASES = ['reads through base_files only', 'read is injectable', 'the commit is an argument', 'never raises',
           'writes nothing', 'the log is a value', 'fails closed', "this task's choice"]


class TASK082AC11Docstring(Base):
    def test_docstring_phrases(self):
        """TASK-082 AC11: the module docstring holds the contract's phrases, whitespace read as single spaces."""
        doc = ' '.join(ast.get_docstring(ast.parse(SRC.read_bytes().decode('utf-8'))).split())
        for phrase in PHRASES:
            self.assertIn(phrase, doc)

    def test_naming(self):
        """TASK-082 AC11: every test of this module names "TASK-082 ACn" at the start of its docstring."""
        classes = [v for v in globals().values() if isinstance(v, type) and issubclass(v, unittest.TestCase)
                   and v.__module__ == __name__]
        self.assertGreater(len(classes), 5)
        for cls in classes:
            for name in unittest.TestLoader().getTestCaseNames(cls):
                self.assertRegex(getattr(cls, name).__doc__ or '', r'^TASK-082 AC\d+', name)


if __name__ == '__main__':
    unittest.main()

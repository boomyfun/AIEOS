"""Unit tests of launcher.run_task and of the command run of cli.py (task TASK-098; specification 7 section 3 :30,
specification 1 section 12, specification 2 sections 3 and 5.1). run_task's callees (read, read_log, read_base,
write_contract, append) are stand-ins given as keyword arguments, over event logs built in memory with
eventlog.append, the append stand-in bound to writer.append_event's signature; the command is run by
mock.patch.object of launcher.run_task, restored after each test. No test writes a file, runs Git or starts a
process; the only files read are the package's own launcher.py and cli.py and this file, with pathlib's read_bytes,
for the ast checks; the root is a literal Windows path that names no folder (L-0032). Stand-in defaults are
sentinels, never a value a case passes (L-0033). Each test names its criteria in its own docstring."""

import ast
import datetime
import hashlib
import inspect
import json
import pathlib
import unittest
from collections import OrderedDict
from unittest import mock

from aieos_bootstrap import (base_inputs, cli, eventlog, gitread, launcher, records, scope_drift, scope_reconcile,
                             task_contract, writer)

REAL_APPEND_EVENT = writer.append_event
APPEND_SIGNATURE = inspect.signature(REAL_APPEND_EVENT)
HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / 'src' / 'aieos_bootstrap'
ROOT = 'C:/run-root-98'
NOW = datetime.datetime(2026, 10, 29, 9, 0, 0, tzinfo=datetime.timezone.utc)
TASK = 'TASK-7'
OTHER = 'TASK-1'
HEAD = 'c' * 40
INTENT = 'Add a made-up page to the docs.'
CLASS = 'decision_agent'
WHO = 'D-1'
NAME = 'A made-up person'
GOOD = object()
KEYS = ('task', 'contract_version', 'task_type', 'objective', 'traces_to', 'input_state', 'write_set', 'read_set',
        'forbidden', 'constitution', 'acceptance_criteria', 'capabilities', 'risk', 'autonomy', 'verification_plan',
        'exit_conditions', 'owner_kept_act')
POLICY = ('# A made-up policy\n\n## 3. The rules\n\n```yaml\nrisk_rules:\n'
          '  - match: { paths: ["docs/**", "*.md"] }\n    risk: low\n'
          '  - match: { paths: ["src/**", "tests/**"] }\n    risk: medium\n'
          '  - match: { paths: ["AIEOS-concept.md", "docs/specs/**", ".github/**"] }\n    risk: critical\n'
          '```\n')
NO_BLOCK = '# A made-up policy with no rules section\n'
EMPTY_RULES = '## 3. The rules\n\n```yaml\nrisk_rules:\n```\n'
BAD_CLASS = '## 3. The rules\n\n```yaml\nrisk_rules:\n  - match: { paths: ["docs/**"] }\n    risk: unknown\n```\n'
TAIL = [
    'capabilities:',
    '  filesystem: {read: [the repository at base_commit], write: [the write_set paths]}',
    '  shell: {allow: []}',
    '  network: {allow: []}',
    '  git: {allow: [commit], forbid: [push, "push --force", rebase, "reset --hard", tag]}',
    '  secrets: deny',
    '  external_side_effects: deny',
]


def head_lines(task, kind, objective, head, paths):
    return ['task: ' + task, 'contract_version: v1', 'task_type: ' + kind, 'objective: >-'] + objective + [
        'traces_to: []', 'input_state:', '  base_commit: ' + head, '  depends_on: []', '  intent_versions: {}',
        'write_set:', '  paths:'] + ['    - ' + p for p in paths] + [
        'read_set:', '  paths:', '    - "**"', '  interfaces: []', '  schemas: []', 'forbidden:', '  - .aieos/**',
        'constitution: []', 'acceptance_criteria:']


def expected_single(task=TASK, head=HEAD, intent_id='INT-001', paths=('docs/a.md',)):
    """The single task's template (t1), written out line by line."""
    lines = head_lines(task, 'implementation',
                       ['  Make the change that intent %s states, within the write set.' % intent_id], head, paths)
    lines += [
        '  - AC1: >-',
        '      The change does what intent %s states, within the write set.' % intent_id,
        '  - AC2: >-',
        '      No other path is changed.',
    ] + TAIL + [
        'risk: low',
        'autonomy:',
        '  max_level: L1',
        '  budgets: {tokens: 400k, wall_time: 2h, retries: 1, human_attention: 0m}',
        'verification_plan:',
        '  - {gate: G0, check: scope}',
        '  - {gate: G1, check: build}',
        '  - {gate: G3, check: review, args: [AC1, AC2]}',
        'exit_conditions:',
        '  success: the change is made within the write set and nothing else changed',
        '  escalate: [needs_out_of_scope_change, needs_owner_act]',
        'owner_kept_act: true',
    ]
    return ''.join(line + '\n' for line in lines)


def proposals(intent_id='INT-001'):
    return ['docs/proposals/%s-%s.md' % (intent_id, p) for p in ('requirement', 'specifications', 'tasks')]


def expected_drafting(task=TASK, head=HEAD, intent_id='INT-001'):
    """The drafting task's template (t2), written out line by line."""
    objective = ['  Draft the proposal set of intent %s (a requirement, its specifications and task contracts with '
                 'their risk' % intent_id,
                 '  and verification plans), proposing only and changing nothing else.']
    lines = head_lines(task, 'drafting', objective, head, proposals(intent_id))
    lines += [
        '  - AC1: >-',
        "      docs/proposals/%s-requirement.md is a requirement in specification 2 section 4.2's form." % intent_id,
        '  - AC2: >-',
        "      docs/proposals/%s-specifications.md holds specifications in specification 2 section 4.2's form, each"
        % intent_id,
        '      tracing to the requirement.',
        '  - AC3: >-',
        "      docs/proposals/%s-tasks.md holds task contracts in specification 2 section 5.1's form, each with its "
        'risk' % intent_id,
        '      and verification plan.',
        '  - AC4: >-',
        '      No other path is changed.',
    ] + TAIL + [
        'risk: critical',
        'autonomy:',
        '  max_level: L1',
        '  budgets: {tokens: 400k, wall_time: 2h, retries: 1, human_attention: 0m}',
        'verification_plan:',
        '  - {gate: G0, check: scope}',
        '  - {gate: G3, check: review, args: [AC1, AC2, AC3, AC4]}',
        'exit_conditions:',
        '  success: the three proposal files present and nothing else changed',
        '  escalate: [needs_out_of_scope_change, needs_owner_act]',
        'owner_kept_act: true',
    ]
    return ''.join(line + '\n' for line in lines)


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def record_id_of(source_class=CLASS, intent=INTENT):
    return 'intent/' + digest('\n'.join(('intent', source_class, intent)))


def claim_event_of(record_id):
    return digest('\n'.join(('run-event', 'record.added', record_id)))


def drafted_event_of(task, h):
    return digest('\n'.join(('run-event', 'task.drafted', task, h)))


def who_of(source_class):
    return WHO if source_class == 'decision_agent' else NAME


def recorder_of(source_class=CLASS):
    """The claim's recorder in approval_act's two forms (r3)."""
    if source_class == 'decision_agent':
        return 'decided by: decision agent (A41, A51), decision %s, through aieos cli run' % WHO
    return '%s, as stated to aieos cli run (not checked)' % NAME


def record_of(intent_id='INT-001', source_class=CLASS, intent=INTENT):
    r = {'record_id': record_id_of(source_class, intent), 'fact_kind': 'claim', 'source_class': source_class,
         'recorder': recorder_of(source_class), 'subject': intent_id, 'evidence_type': 'intent', 'text': intent}
    if source_class == 'decision_agent':
        r['decision_ref'] = WHO
    return r


GOLDEN_RUN_CONTRACT = '\n'.join((
    'task: TASK-7', 'contract_version: v1', 'task_type: implementation', 'objective: >-',
    '  Make the change that intent INT-001 states, within the write set.', 'traces_to: []', 'input_state:',
    '  base_commit: cccccccccccccccccccccccccccccccccccccccc', '  depends_on: []', '  intent_versions: {}',
    'write_set:', '  paths:', '    - docs/a.md', 'read_set:', '  paths:', '    - "**"', '  interfaces: []',
    '  schemas: []', 'forbidden:', '  - .aieos/**', 'constitution: []', 'acceptance_criteria:', '  - AC1: >-',
    '      The change does what intent INT-001 states, within the write set.', '  - AC2: >-',
    '      No other path is changed.', 'capabilities:',
    '  filesystem: {read: [the repository at base_commit], write: [the write_set paths]}',
    '  shell: {allow: []}', '  network: {allow: []}',
    '  git: {allow: [commit], forbid: [push, "push --force", rebase, "reset --hard", tag]}',
    '  secrets: deny', '  external_side_effects: deny', 'risk: low', 'autonomy:', '  max_level: L1',
    '  budgets: {tokens: 400k, wall_time: 2h, retries: 1, human_attention: 0m}', 'verification_plan:',
    '  - {gate: G0, check: scope}', '  - {gate: G1, check: build}', '  - {gate: G3, check: review, args: [AC1, AC2]}',
    'exit_conditions:', '  success: the change is made within the write set and nothing else changed',
    '  escalate: [needs_out_of_scope_change, needs_owner_act]', 'owner_kept_act: true')) + '\n'
PATH = '.aieos/tasks/%s.yaml' % TASK
H1 = digest(expected_single())
H2 = digest(expected_drafting())
RID = record_id_of()
CEID = claim_event_of(RID)
CLAIM_STUCK = "append: the contract %s (%s) is written, the intent's claim is not" % (PATH, H1)
DRAFTED_STUCK = 'append: the contract %s (%s) is written, the task.drafted is not' % (PATH, H1)


class Log:
    """An event log kept as bytes; every line is decided by eventlog.append."""

    def __init__(self):
        self.data = b''
        self.n = 0

    def add(self, event_type, payload, task_id=OTHER):
        self.n += 1
        r = eventlog.append(self.data, event_type, payload, 'ev-%d' % self.n, NOW, task_id=task_id)
        if r.result != 'appended':
            raise ValueError(r.findings)
        self.data += r.line
        return self

    def drafted(self, task_id=OTHER):
        return self.add('task.drafted', {'contract_version': 'v1', 'contract_hash': 'a' * 64}, task_id)

    def claim(self, intent_id, source_class=CLASS, intent=INTENT):
        return self.add('record.added', record_of(intent_id, source_class, intent), None)


def with_duplicate(data):
    """The log with its last line repeated as an ignored duplicate (the same event, the next seq)."""
    obj = json.loads(data.splitlines()[-1].decode('ascii'))
    obj['seq'] += 1
    return data + (json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode('ascii')


class World:
    """The callees of run_task as stand-ins: read gives HEAD, read_log the log bytes, read_base the policy,
    write_contract "done" with the task's path, append decides with eventlog.append over the log and keeps the
    line."""

    def __init__(self, log=None, read=GOOD, base=GOOD, write=GOOD, refuse=(), raise_on=()):
        self.data = (Log().drafted() if log is None else log).data
        self.read_answer = {'exit': 0, 'out': (HEAD + '\n').encode('ascii'), 'err': b'', 'error': None} \
            if read is GOOD else read
        self.base_answer = {'policy_blob': 'b' * 40, 'policy': POLICY, 'workflow_blob': 'd' * 40,
                            'workflow': 'made-up'} if base is GOOD else base
        self.write_answer = write
        self.refuse = refuse
        self.raise_on = raise_on
        self.calls = []

    def names(self):
        return [c[0] for c in self.calls]

    def read(self, repo, args, timeout):
        self.calls.append(('read', repo, tuple(args)))
        if 'read' in self.raise_on:
            raise OSError('read')
        return self.read_answer

    def read_log(self, root):
        self.calls.append(('read_log', root))
        if 'read_log' in self.raise_on:
            raise OSError('read_log')
        return self.data

    def read_base(self, repo, parent, read):
        self.calls.append(('read_base', repo, parent, read))
        if 'read_base' in self.raise_on:
            raise OSError('read_base')
        return self.base_answer

    def write_contract(self, root, task_id, text):
        self.calls.append(('write_contract', root, task_id, text))
        if 'write_contract' in self.raise_on:
            raise OSError('write_contract')
        if self.write_answer is GOOD:
            return writer.StoreResult('done', value='.aieos/tasks/%s.yaml' % task_id)
        return self.write_answer

    def append(self, *args, **kwargs):
        a = APPEND_SIGNATURE.bind(*args, **kwargs).arguments
        first = next(iter(a.values()))
        self.calls.append(('append', first, a['event_type'], a['payload'], a['event_id'], a['appended_at'],
                           a['recorder'], a.get('task_id'), a.get('fencing_token')))
        if a['event_type'] in self.raise_on:
            raise OSError('append')
        if a['event_type'] in self.refuse:
            return writer.WriteResult(eventlog.AppendResult('refused', 'event', findings=('stand-in refusal',)))
        r = eventlog.append(self.data, a['event_type'], a['payload'], a['event_id'], a['appended_at'],
                            task_id=a.get('task_id'), recorder=a['recorder'])
        if r.result == 'appended':
            self.data += r.line
        return writer.WriteResult(r)

    def kw(self):
        return {'read': self.read, 'read_log': self.read_log, 'read_base': self.read_base,
                'write_contract': self.write_contract, 'append': self.append}


class Clock:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return NOW


def go(world, write=('docs/a.md',), task=TASK, intent=INTENT, source_class=CLASS, who=GOOD, clock=None, **over):
    kw = world.kw()
    kw.update(over)
    who = who_of(source_class) if who is GOOD else who
    return launcher.run_task(ROOT, task, intent, source_class, who, write, clock or (lambda: NOW), **kw)


def written(world):
    return [c for c in world.calls if c[0] == 'write_contract']


class TASK098AC1Runs(unittest.TestCase):
    def test_the_single_path(self):
        """TASK-098 AC1: for a write set classed low, one clock read, one _head read, one read_log, one read_base, one
        write_contract with (root, task, text), the claim's append (no task_id, no fencing token) and the task.drafted
        append, in that order; "done" with kind single, risk low and every value as the header states."""
        w = World()
        clock = Clock()
        out = go(w, clock=clock)
        self.assertEqual(clock.calls, 1)
        self.assertEqual(w.names(), ['read', 'read_log', 'read_base', 'write_contract', 'append', 'append'])
        self.assertEqual(w.calls[0], ('read', ROOT, tuple(launcher.HEAD_ARGS)))
        self.assertEqual(w.calls[1], ('read_log', ROOT))
        self.assertEqual(w.calls[2], ('read_base', ROOT, HEAD, w.read))
        self.assertEqual(w.calls[3], ('write_contract', ROOT, TASK, expected_single()))
        self.assertEqual(w.calls[4], ('append', ROOT, 'record.added', record_of(), CEID, NOW, recorder_of(), None,
                                      None))
        deid = drafted_event_of(TASK, H1)
        self.assertEqual(w.calls[5], ('append', ROOT, 'task.drafted', {'contract_version': 'v1', 'contract_hash': H1},
                                      deid, NOW, 'aieos cli run', TASK, None))
        self.assertEqual(out, {'result': 'done', 'reason': None, 'findings': [], 'intent_id': 'INT-001',
                               'claim_id': RID, 'kind': 'single', 'risk': 'low', 'path': PATH, 'contract_hash': H1,
                               'event_ids': [CEID, deid], 'appends': ['appended', 'appended']})
        self.assertEqual(tuple(out), launcher.RUN_KEYS)

    def test_the_drafting_kinds(self):
        """TASK-098 AC1: no write set (no read_base call), a class other than low, a path no rule matches, and one low
        path beside one no rule matches each give kind drafting with the drafting template and the class finding."""
        for write, risk, found in (((), None, []), (('src/x.py',), 'medium', []),
                                   (('other/file.txt',), None, ['class: other/file.txt matches no rule']),
                                   (('docs/a.md', 'other/file.txt'), None,
                                    ['class: other/file.txt matches no rule'])):
            w = World()
            out = go(w, write=write)
            self.assertEqual((out['result'], out['kind'], out['risk'], out['findings']), ('done', 'drafting', risk,
                                                                                         found), write)
            self.assertEqual('read_base' in w.names(), bool(write), write)
            self.assertEqual(written(w)[0][3], expected_drafting(), write)
            self.assertEqual(out['contract_hash'], H2)
            self.assertEqual(out['event_ids'], [CEID, drafted_event_of(TASK, H2)])

    def test_the_texts_are_the_templates(self):
        """TASK-098 AC1: the single text is t1 filled with the task, the head, the intent id and the write set in its
        order, and the drafting text t2 filled with the task, the head and the intent id, each line equal to the
        literal expected text."""
        read = {'exit': 0, 'out': ('d' * 40 + '\n').encode('ascii'), 'err': b'', 'error': None}
        w = World(read=read)
        out = go(w, write=('docs/b.md', 'README.md', 'docs/a.md'), task='TASK-123')
        self.assertEqual(out['result'], 'done', out)
        text = written(w)[0][3]
        want = expected_single('TASK-123', 'd' * 40, 'INT-001', ('docs/b.md', 'README.md', 'docs/a.md'))
        self.assertEqual(text.splitlines(), want.splitlines())
        self.assertEqual(text, want)
        w = World(log=Log().claim('INT-004', intent='another made-up intent'), read=read)
        out = go(w, write=('src/x.py',), task='TASK-123')
        self.assertEqual(out['intent_id'], 'INT-005')
        self.assertEqual(written(w)[0][3], expected_drafting('TASK-123', 'd' * 40, 'INT-005'))

    def test_the_texts_parse(self):
        """TASK-098 AC1: both texts parse by task_contract.parse_contract with no finding and by base_inputs'
        contract parser with every CONTRACT_NEEDS key; their keys are TASK-097's in order; owner_kept_act true; t1 risk
        low with its G1 and G3 gates, t2 risk critical with its G3 gate over AC1 to AC4; forbidden the project-state
        directory; push forbidden."""
        for text, paths, risk, gates in (
                (expected_single(), ['docs/a.md'], 'risk: low',
                 ['  - {gate: G1, check: build}', '  - {gate: G3, check: review, args: [AC1, AC2]}']),
                (expected_drafting(), proposals(), 'risk: critical',
                 ['  - {gate: G3, check: review, args: [AC1, AC2, AC3, AC4]}'])):
            parsed = task_contract.parse_contract(text, TASK)
            self.assertEqual((parsed['result'], parsed['reason'], parsed['findings']), ('read', None, []), parsed)
            self.assertEqual((parsed['task'], parsed['base_commit']), (TASK, HEAD))
            self.assertEqual(parsed['write_set'], paths)
            self.assertEqual(parsed['forbidden'], [writer.STATE_DIR + '/**'])
            mapping = base_inputs._parse_contract_text(text)
            for key in base_inputs.CONTRACT_NEEDS:
                self.assertIn(key, mapping)
            self.assertEqual(tuple(line.split(':', 1)[0] for line in text.splitlines() if line[:1].isalpha()), KEYS)
            lines = text.splitlines()
            self.assertIn('owner_kept_act: true', lines)
            self.assertIn(risk, lines)
            for gate in gates:
                self.assertIn(gate, lines)
            self.assertIn('  git: {allow: [commit], forbid: [push, "push --force", rebase, "reset --hard", tag]}',
                          lines)

    def test_the_claim(self):
        """TASK-098 AC1: the claim's record, record_id and event id are the header's; check_record gives no finding;
        the task.drafted payload passes its check; the log after the run passes records.check_log."""
        w = World()
        self.assertEqual(go(w)['result'], 'done')
        record = w.calls[4][3]
        self.assertEqual(record, record_of())
        self.assertEqual(record['record_id'], 'intent/' + digest('intent\n%s\n%s' % (CLASS, INTENT)))
        self.assertEqual(records.check_record(record), [])
        self.assertEqual(records.check_payload('task.drafted', w.calls[5][3]), [])
        report = records.check_log(w.data)
        self.assertEqual(report.findings(), [])
        events = [line.event for line in report.lines]
        self.assertEqual((events[-2]['type'], events[-2].get('task_id'), events[-2]['event_id']),
                         ('record.added', None, CEID))
        self.assertEqual((events[-1]['type'], events[-1]['task_id']), ('task.drafted', TASK))

    def test_both_classes(self):
        """TASK-098 AC1 (r3): for decision_agent the claim's record carries decision_ref who and the recorder "decided
        by: decision agent (A41, A51), decision <who>, through aieos cli run"; for human_authority no decision_ref and
        the recorder "<who>, as stated to aieos cli run (not checked)"; the claim's append passes the record's
        recorder, task.drafted RUN_RECORDER; who does not enter the record_id; check_record and check_log pass."""
        for source_class in ('decision_agent', 'human_authority'):
            w = World()
            out = go(w, source_class=source_class)
            self.assertEqual(out['result'], 'done', out)
            claim, drafted = [c for c in w.calls if c[0] == 'append']
            self.assertEqual(claim[3], record_of(source_class=source_class))
            self.assertEqual('decision_ref' in claim[3], source_class == 'decision_agent')
            self.assertEqual((claim[6], drafted[6]), (recorder_of(source_class), 'aieos cli run'))
            self.assertEqual(claim[3]['record_id'], record_id_of(source_class))
            self.assertEqual(records.check_record(claim[3]), [])
            self.assertEqual(records.check_log(w.data).findings(), [])
        a = go(World(), who='D-2')
        self.assertEqual(a['claim_id'], RID)

    def test_the_intent_ids(self):
        """TASK-098 AC1: a first intent is INT-001, a second INT-002; the same intent under the same class reuses
        INT-001 (its claim a duplicate); under the other class it is a new id."""
        w = World()
        self.assertEqual(go(w)['intent_id'], 'INT-001')
        out = go(w, task='TASK-8', intent='another made-up intent')
        self.assertEqual(out['intent_id'], 'INT-002')
        out = go(w, task='TASK-9')
        self.assertEqual((out['result'], out['intent_id'], out['appends']), ('done', 'INT-001',
                                                                             ['duplicate', 'appended']))
        out = go(w, task='TASK-10', source_class='human_authority')
        self.assertEqual((out['intent_id'], out['claim_id']), ('INT-003', record_id_of('human_authority')))
        self.assertEqual(records.check_log(w.data).findings(), [])

    def test_callees_default_at_call_time(self):
        """TASK-098 AC1: with no callee given, gitread.run, writer.read_log, scope_reconcile.read_base,
        writer.write_contract and writer.append_event, patched after import, are the ones called."""
        w = World()
        with mock.patch.object(gitread, 'run', w.read), mock.patch.object(writer, 'read_log', w.read_log), \
                mock.patch.object(scope_reconcile, 'read_base', w.read_base), \
                mock.patch.object(writer, 'write_contract', w.write_contract), \
                mock.patch.object(writer, 'append_event', w.append):
            out = launcher.run_task(ROOT, TASK, INTENT, CLASS, WHO, ('docs/a.md',), lambda: NOW)
        self.assertEqual(out['result'], 'done', out)
        self.assertEqual(w.names(), ['read', 'read_log', 'read_base', 'write_contract', 'append', 'append'])

    def test_the_constants(self):
        """TASK-098 AC1: RUN_KEYS, RUN_REASONS, RUN_KINDS and RUN_RECORDER are the header's; a done answer and a
        refused one have exactly RUN_KEYS."""
        self.assertEqual(launcher.RUN_KEYS, ('result', 'reason', 'findings', 'intent_id', 'claim_id', 'kind', 'risk',
                                             'path', 'contract_hash', 'event_ids', 'appends'))
        self.assertEqual(launcher.RUN_REASONS, ('argument', 'clock', 'head', 'log', 'exists', 'intent', 'layout',
                                                'write', 'append'))
        self.assertEqual(launcher.RUN_KINDS, ('single', 'drafting'))
        self.assertEqual(launcher.RUN_RECORDER, 'aieos cli run')
        for out in (go(World()), go(World(), task='x')):
            self.assertEqual(tuple(out), launcher.RUN_KEYS)


class TASK098AC2Refusals(unittest.TestCase):
    def refused(self, out, reason):
        self.assertEqual((out['result'], out['reason']), ('refused', reason), out)
        return out['findings']

    def test_wrong_arguments(self):
        """TASK-098 AC2: each wrong task, intent, write set, source class, who (r3: approval_act's forms), clock, callee
        or root gives "argument" with nothing called."""
        cases = [dict(task='task-7'), dict(task=7), dict(task='TASK-'), dict(intent=''), dict(intent='x' * 2001),
                 dict(intent='a\nb'), dict(intent='a\rb'), dict(intent=3), dict(source_class='owner'),
                 dict(source_class=None), dict(clock=5), dict(read='run'), dict(read_log=5), dict(read_base='x'),
                 dict(write_contract='x'), dict(append=5), dict(write='docs/a.md'), dict(write=None),
                 dict(write=['d/%d.md' % i for i in range(51)]), dict(write=('docs/a.md', 'docs/a.md')),
                 dict(who='d-1'), dict(who='D-'), dict(who='D-1 '), dict(who=None), dict(who=3), dict(who=NAME),
                 dict(source_class='human_authority', who='the owner'),
                 dict(source_class='human_authority', who='a\nb'), dict(source_class='human_authority', who=''),
                 dict(source_class='human_authority', who='x' * 201), dict(source_class='human_authority', who=None)]
        for path in ('*', 'docs/*.md', 'docs/', 'a//b', '.', './x', 'a/./b', '-', '..', 'a/../b', 'docs/specs./x.md',
                     'docs/a.md ', '/abs', '', '.aieos', '.aieos/x', '.AIEOS/x', '.Aieos/tasks/x.yaml', 3, None):
            cases.append(dict(write=('docs/a.md', path)))
        for case in cases:
            w = World()
            self.refused(go(w, **case), 'argument')
            self.assertEqual(w.calls, [], case)
        for root in ('relative/root', None, 3, ''):
            w = World()
            self.refused(launcher.run_task(root, TASK, INTENT, CLASS, WHO, (), lambda: NOW, **w.kw()), 'argument')
            self.assertEqual(w.calls, [], root)
        self.assertEqual(go(World(), write=['d/%d.md' % i for i in range(50)])['result'], 'done')
        self.assertEqual(go(World(), intent='x' * 2000)['result'], 'done')

    def test_the_clock(self):
        """TASK-098 AC2: a raising clock, a naive time and a time with a fraction of a second give "clock" with
        nothing else called."""
        def raising():
            raise RuntimeError('clock')
        for clock in (raising, lambda: NOW.replace(tzinfo=None), lambda: NOW.replace(microsecond=5), lambda: 'now'):
            w = World()
            self.refused(go(w, clock=clock), 'clock')
            self.assertEqual(w.calls, [])

    def test_the_head(self):
        """TASK-098 AC2: _head's findings, a raising read and a head that is not 40 lowercase hex give "head", with
        no read_log call and nothing written."""
        for answer in ({'exit': 1, 'out': b'', 'err': b'', 'error': None}, {'exit': 0, 'out': b'xyz\n', 'error': None},
                       None, {'exit': 0, 'out': ('C' * 40 + '\n').encode('ascii'), 'err': b'', 'error': None},
                       {'exit': 0, 'out': ('c' * 39 + '\n').encode('ascii'), 'err': b'', 'error': None}):
            w = World(read=answer)
            self.refused(go(w), 'head')
            self.assertEqual(w.names(), ['read'])
        w = World(raise_on=('read',))
        self.assertIn('head: a step raised OSError', self.refused(go(w), 'head'))

    def test_the_log(self):
        """TASK-098 AC2: a raising read_log, an answer that is not bytes and a log records.check_log refuses give
        "log", with nothing read at the base, written or appended."""
        w = World(raise_on=('read_log',))
        self.assertIn('log: a step raised OSError', self.refused(go(w), 'log'))
        for data in ('text', None, bytearray(b''), b'not json\n'):
            w = World()
            w.data = data
            self.refused(go(w), 'log')
            self.assertEqual(w.names(), ['read', 'read_log'])

    def test_the_task_already_in_the_log(self):
        """TASK-098 AC2: a log holding any event of the task, a duplicate line included, gives "exists" with nothing
        read at the base, written or appended; a log of other tasks only, or an empty one, is done."""
        dup = Log().drafted(task_id=TASK)
        dup.data = with_duplicate(dup.data)
        for log in (Log().drafted(task_id=TASK), Log().drafted().drafted(task_id=TASK).drafted(), dup):
            w = World(log=log)
            self.assertEqual(self.refused(go(w), 'exists'), ['exists: %s has events in the log' % TASK])
            self.assertEqual(w.names(), ['read', 'read_log'])
        for log in (Log(), Log().drafted().drafted(task_id='TASK-70'), Log().claim('INT-001')):
            self.assertEqual(go(World(log=log))['result'], 'done')

    def test_the_class_fails_closed(self):
        """TASK-098 AC2: read_base raising, a base out of form, a policy with no rules block, empty rules, a rule with
        no valid class and a raising path_class each give kind drafting, no class and the header's "class:" finding,
        never a refusal."""
        cases = [(World(raise_on=('read_base',)), 'class: the policy at the base was not read (OSError)'),
                 (World(base=None), 'class: a step raised TypeError'),
                 (World(base={'policy': NO_BLOCK}), "class: the policy's rules are not in form"),
                 (World(base={'policy': EMPTY_RULES}), "class: the policy's rules are not in form"),
                 (World(base={'policy': BAD_CLASS}), "class: the policy's rules are not in form")]
        for w, found in cases:
            out = go(w)
            self.assertEqual((out['result'], out['kind'], out['risk'], out['findings']), ('done', 'drafting', None,
                                                                                         [found]), found)
            self.assertEqual(written(w)[0][3], expected_drafting())
        with mock.patch.object(scope_drift, 'path_class', mock.Mock(side_effect=RuntimeError('x'))):
            out = go(World())
        self.assertEqual((out['result'], out['kind'], out['risk'], out['findings']),
                         ('done', 'drafting', None, ['class: a step raised RuntimeError']))

    def test_the_case_of_a_path(self):
        """TASK-098 AC2: "DOCS/specs/x.md", ".GITHUB/workflows/x.md" and "AIEOS-CONCEPT.md", low in their own form,
        are classed critical by their lowercased forms, so the kind is drafting; "Docs/a.md" stays low."""
        for path in ('DOCS/specs/x.md', '.GITHUB/workflows/x.md', 'AIEOS-CONCEPT.md'):
            self.assertEqual(scope_drift.path_class(scope_reconcile.rules_from_policy(POLICY), path), 'low', path)
            out = go(World(), write=(path,))
            self.assertEqual((out['result'], out['kind'], out['risk'], out['findings']),
                             ('done', 'drafting', 'critical', []), path)
        out = go(World(), write=('Docs/a.md',))
        self.assertEqual((out['kind'], out['risk']), ('single', 'low'))

    def test_the_write_refusals(self):
        """TASK-098 AC2: write_contract "refused" "exists" or "layout" pass through with their findings; any other
        refusal, a done with another path, an answer out of form and a raise give "write"; none appends."""
        for answer, reason, found in (
                (writer.StoreResult('refused', 'exists', ['exists: the contract file is not empty']), 'exists',
                 ['exists: the contract file is not empty']),
                (writer.StoreResult('refused', 'layout', ['layout: x']), 'layout', ['layout: x']),
                (writer.StoreResult('refused', 'link', ['link: y']), 'write',
                 ['write: write_contract gave refused link']),
                (writer.StoreResult('refused', 'unwritable', ['unwritable: OSError']), 'write', None),
                (writer.StoreResult('done', value='.aieos/tasks/TASK-8.yaml'), 'write', None),
                (writer.StoreResult('done'), 'write', None),
                ('done', 'write', ['write: write_contract gave an answer that is not a StoreResult']),
                (None, 'write', None)):
            w = World(write=answer)
            out = go(w)
            got = self.refused(out, reason)
            if found is not None:
                self.assertEqual(got, found)
            self.assertNotIn('append', w.names())
            self.assertEqual((out['path'], out['contract_hash'], out['event_ids'], out['appends']),
                             (None, None, [], []))
            self.assertEqual((out['intent_id'], out['kind'], out['risk']), ('INT-001', 'single', 'low'))
        w = World(raise_on=('write_contract',))
        self.assertEqual(self.refused(go(w), 'write'), ['write: a step raised OSError'])
        self.assertNotIn('append', w.names())

    def test_the_claim_append_refusals(self):
        """TASK-098 AC2: the claim's append refused, raising or answering out of form gives "append" with the exact
        findings naming the written contract, and no task.drafted append."""
        for world, first in ((World(refuse=('record.added',)), 'append: record.added: refused event'),
                             (World(raise_on=('record.added',)), 'append: record.added: a step raised OSError')):
            out = go(world)
            self.assertEqual(self.refused(out, 'append'), [first, CLAIM_STUCK])
            self.assertEqual(world.names().count('append'), 1)
            self.assertEqual((out['path'], out['contract_hash'], out['event_ids'], out['appends']),
                             (PATH, H1, [], []))
        out = go(World(), append=lambda *a, **k: 'appended')
        self.assertEqual(self.refused(out, 'append'),
                         ['append: record.added: append gave an answer that is not a WriteResult', CLAIM_STUCK])

    def test_the_drafted_append_refusals(self):
        """TASK-098 AC2: the task.drafted append refused or raising gives "append" with the exact findings, the claim's
        event and append kept."""
        for world, first in ((World(refuse=('task.drafted',)), 'append: task.drafted: refused event'),
                             (World(raise_on=('task.drafted',)), 'append: task.drafted: a step raised OSError')):
            out = go(world)
            self.assertEqual(self.refused(out, 'append'), [first, DRAFTED_STUCK])
            self.assertEqual((out['event_ids'], out['appends']), ([CEID], ['appended']))

    def test_no_exception_escapes(self):
        """TASK-098 AC2: callees that raise or answer with values whose methods raise give a refusal or a fail-closed
        class, never a raise."""
        class Odd(dict):
            def get(self, *a):
                raise RuntimeError('get')

        class Unreadable(dict):
            def __getitem__(self, key):
                raise RuntimeError('getitem')
        self.assertEqual(go(World(read=Odd(exit=0)))['reason'], 'head')
        self.assertEqual(go(World(write=writer.StoreResult('done', value=Odd())))['reason'], 'write')
        out = go(World(base=Unreadable(policy=POLICY)))
        self.assertEqual((out['result'], out['kind'], out['findings']),
                         ('done', 'drafting', ['class: a step raised RuntimeError']))
        for name in ('read', 'read_log', 'write_contract', 'record.added', 'task.drafted'):
            self.assertEqual(go(World(raise_on=(name,)))['result'], 'refused', name)

    def test_what_run_task_names(self):
        """TASK-098 AC2: by ast, run_task and the names beginning _run, _RUN or RUN_ name no open, exec, eval,
        compile, __import__, subprocess, os, sys or time, and hold no string constant naming the project-state
        directory, every such path built from writer.STATE_DIR."""
        tree = ast.parse((SRC / 'launcher.py').read_bytes().decode('utf-8'))
        mine = []
        for n in tree.body:
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and (n.name == 'run_task' or n.name.startswith('_run')):
                mine.append(n)
            elif isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id.lstrip('_').startswith('RUN')
                                                   for t in n.targets):
                mine.append(n)
        self.assertGreater(len(mine), 20)
        names = {x.id for n in mine for x in ast.walk(n) if isinstance(x, ast.Name)}
        self.assertEqual(names & {'open', 'exec', 'eval', 'compile', '__import__', 'subprocess', 'os', 'sys', 'time'},
                         set())
        texts = [x.value for n in mine for x in ast.walk(n)
                 if isinstance(x, ast.Constant) and isinstance(x.value, str)]
        self.assertEqual([t for t in texts if writer.STATE_DIR in t.lower()], [])
        self.assertIn('STATE_DIR', {x.attr for n in mine for x in ast.walk(n) if isinstance(x, ast.Attribute)})


def log_with(*events):
    """The log bytes of a Log() holding one more line per (payload, event_id): decided by eventlog.append."""
    log = Log()
    for payload, event_id in events:
        r = eventlog.append(log.data, 'record.added', payload, event_id, NOW)
        assert r.result == 'appended', r
        log.data += r.line
    return log


class TASK098AC2IntentRefusals(unittest.TestCase):
    def refused(self, out, reason):
        self.assertEqual((out['result'], out['reason']), ('refused', reason), out)
        return out['findings']

    def test_the_same_intent_under_another_name(self):
        """TASK-098 AC2: the same intent under another name, whose claim the append would answer "conflict", is refused
        with "intent" before write_contract: nothing is written and nothing is appended."""
        w = World()
        self.assertEqual(go(w, source_class='decision_agent', who='D-1')['result'], 'done')
        calls, data = list(w.calls), w.data
        out = go(w, source_class='decision_agent', who='D-2', task='TASK-9')
        found = self.refused(out, 'intent')
        self.assertEqual(w.names()[len(calls):], ['read', 'read_log', 'read_base'])
        self.assertEqual(len(written(w)), 1)
        self.assertEqual(w.data, data)
        self.assertEqual(len(found), 1)
        self.assertIn('INT-001', found[0])
        self.assertIn('decision D-1', found[0])
        self.assertEqual((out['intent_id'], out['claim_id'], out['risk'], out['kind'], out['path'],
                          out['contract_hash'], out['event_ids'], out['appends']),
                         ('INT-001', record_id_of('decision_agent'), 'low', None, None, None, [], []))
        self.assertEqual(tuple(out), launcher.RUN_KEYS)

    def test_a_log_that_holds_the_claim_event_with_another_payload(self):
        """TASK-098 AC2: a log whose line under the claim event id carries another payload (a stand-in log) is
        refused with "intent", with nothing written; the same payload is a duplicate and the run goes on."""
        other = dict(record_of(), recorder='someone else, as stated to aieos cli run (not checked)')
        w = World(log=log_with((other, CEID)))
        self.refused(go(w), 'intent')
        self.assertEqual(written(w), [])
        self.assertNotIn('append', w.names())
        w = World(log=log_with((record_of(), CEID)))
        out = go(w)
        self.assertEqual((out['result'], out['appends']), ('done', ['duplicate', 'appended']))

    def test_the_subject_alone_can_cause_it(self):
        """TASK-098 AC2: a claim of the record_id under another event id with the subject INT-001 and, on the claim
        event id, the same record_id with the subject INT-002: the first match gives INT-001, the line under the claim
        event id differs, and the finding names the subject of that line, INT-002."""
        log = Log().claim('INT-001')
        r = eventlog.append(log.data, 'record.added', record_of('INT-002'), CEID, NOW)
        log.data += r.line
        w = World(log=log)
        found = self.refused(go(w), 'intent')
        self.assertIn('INT-002', found[0])
        self.assertNotIn('INT-001', found[0])
        self.assertEqual(written(w), [])
        self.assertNotIn('append', w.names())

    def test_a_raise_in_the_dry_run_gives_log(self):
        """TASK-098 AC2: a raise inside the dry run of eventlog.append keeps the reason "log" (the step variable is
        not changed): nothing is written and nothing is appended."""
        w = World()
        with mock.patch.object(launcher.eventlog, 'append', side_effect=RuntimeError('x')) as dry:
            out = go(w)
        found = self.refused(out, 'log')
        self.assertEqual(dry.call_count, 1)
        self.assertIn('log: a step raised RuntimeError', found)
        self.assertEqual(written(w), [])
        self.assertNotIn('append', w.names())

    def test_the_same_record_id_under_another_event_id_goes_on(self):
        """TASK-098 AC2: a claim of the same record_id under another event id and another recorder is not a
        conflict: the run is done as before."""
        other = dict(record_of('INT-001'), recorder='someone else, as stated to aieos cli run (not checked)')
        log = Log().add('record.added', other, None)
        out = go(World(log=log))
        self.assertEqual((out['result'], out['appends']), ('done', ['appended', 'appended']))

    def test_a_log_without_a_final_lf_goes_on(self):
        """TASK-098 AC2: any other answer of the dry run lets the run go on as before: a log without a final LF is
        answered "log" by eventlog.append, so the run writes the contract and stops at "append"."""
        w = World()
        w.data = w.data[:-1]
        out = go(w)
        self.refused(out, 'append')
        self.assertEqual(len(written(w)), 1)


class Stand:
    def __init__(self, answer=GOOD, raises=None):
        self.calls = []
        self.kwargs = []
        self.answer = answer
        self.raises = raises

    def __call__(self, *args, **kwargs):
        self.calls.append(args)
        self.kwargs.append(kwargs)
        if self.raises is not None:
            raise self.raises
        return self.answer


class Sink:
    def __init__(self):
        self.writes = []

    def write(self, text):
        self.writes.append(text)


def done(**over):
    answer = {'result': 'done', 'reason': None, 'findings': [], 'intent_id': 'INT-001', 'claim_id': 'intent/x',
              'kind': 'single', 'risk': 'low', 'path': '.aieos/tasks/TASK-1.yaml', 'contract_hash': 'h',
              'event_ids': ['e1', 'e2'], 'appends': ['appended', 'duplicate']}
    answer.update(over)
    return answer


def refused(**over):
    answer = {'result': 'refused', 'reason': 'exists', 'findings': ['exists: x'], 'intent_id': None,
              'claim_id': None, 'kind': None, 'risk': None, 'path': None, 'contract_hash': None, 'event_ids': [],
              'appends': []}
    answer.update(over)
    return answer


def run(argv, answer=GOOD, raises=None, environ=None):
    sink, clock = Sink(), Clock()
    stand = Stand(done() if answer is GOOD else answer, raises)
    with mock.patch.object(launcher, 'run_task', stand):
        rc = cli.main(argv, sink, {} if environ is None else environ, clock)
    return rc, ''.join(sink.writes), stand, clock


ARGV = ['run', 'TASK-1', 'do it', '--root', ROOT, '--class', 'decision_agent', '--by', 'D-1']


class TASK098AC4Command(unittest.TestCase):
    def test_the_call(self):
        """TASK-098 AC4: "run TASK-1 <intent> --root R --class C --by W" calls run_task once with (R, 'TASK-1', the
        intent, C, W, (), the clock); each --write adds its path to the tuple in order; the flags may come in any
        order."""
        rc, _, stand, clock = run(ARGV)
        self.assertEqual((rc, stand.calls), (0, [(ROOT, 'TASK-1', 'do it', 'decision_agent', 'D-1', (), clock)]))
        self.assertEqual(clock.calls, 0)
        rc, _, stand, clock = run(['run', 'TASK-1', 'do it', '--write', 'b.md', '--class', 'human_authority',
                                   '--json', '--by', NAME, '--write', 'a/c.py', '--root', ROOT])
        self.assertEqual((rc, stand.calls), (0, [(ROOT, 'TASK-1', 'do it', 'human_authority', NAME,
                                                  ('b.md', 'a/c.py'), clock)]))

    def test_usage_errors(self):
        """TASK-098 AC4: each argv out of form gives exit 2 and USAGE with nothing called, inside a runtime too."""
        bad = [['run'], ['run', '--root', ROOT], ['run', 'task-1', 'do it', '--root', ROOT, '--class', CLASS],
               ['run', 'TASK-1', '--root', ROOT, '--class', CLASS], ['run', 'TASK-1', '--x', '--root', ROOT],
               ['run', 'TASK-1', 'do it', '--class', CLASS], ['run', 'TASK-1', 'do it', '--root', ROOT],
               ['run', 'TASK-1', 'do it', '--root', ROOT, '--class', 'owner'],
               ['run', 'TASK-1', '', '--root', ROOT, '--class', CLASS],
               ARGV + ['--root', ROOT], ARGV + ['--class', CLASS], ARGV + ['--json', '--json'],
               ARGV + ['--write', ''], ARGV + ['--write', '--x'], ARGV + ['--write'], ARGV + ['extra'],
               ARGV + ['--by', 'D-1'], ARGV + ['--note', 'n'], ARGV[:-2], ARGV[:-1], ARGV[:-1] + ['--x'],
               ['run', 'TASK-1', 'do it', 'more', '--root', ROOT, '--class', CLASS, '--by', 'D-1'],
               ['run', 'TASK-1', 'do it', '--root', ROOT, '--by', 'D-1'],
               ['run', 'TASK-1', 'do it', '--class', CLASS, '--by', 'D-1']]
        for argv in bad:
            for environ in ({}, {'AIEOS_ROOT': 'x'}):
                rc, out, stand, clock = run(argv, environ=environ)
                self.assertEqual((rc, out, stand.calls, clock.calls), (2, cli.USAGE, [], 0), argv)

    def test_inside_a_runtime(self):
        """TASK-098 AC4: an environ holding any one of the three RUNTIME_VARS ('' included) gives exit 1 and the
        runtime refusal with nothing called."""
        for name in cli.RUNTIME_VARS:
            for value in ('', 'x'):
                rc, out, stand, clock = run(ARGV, environ={name: value})
                self.assertEqual((rc, out, stand.calls, clock.calls),
                                 (1, 'finding: %s\n' % cli.RUN_RUNTIME_REFUSAL, [], 0), name)
        rc, out, _, _ = run(ARGV + ['--json'], environ={'AIEOS_BASE': 'b'})
        self.assertEqual((rc, json.loads(out)), (1, {'findings': [cli.RUN_RUNTIME_REFUSAL]}))
        self.assertEqual(cli.RUN_RUNTIME_REFUSAL,
                         'run: refused inside a runtime (it writes; specification 7 :34 names end and launch, and run '
                         'is refused for the same reason)')

    def test_done_output(self):
        """TASK-098 AC4: "done" gives exit 0 and the intent, contract and two event lines, then the findings, or
        under --json the exact sorted line; a risk None is printed "none"."""
        rc, out, _, _ = run(ARGV, answer=done(findings=['f1']))
        self.assertEqual((rc, out), (0, 'intent: INT-001 intent/x\ncontract: .aieos/tasks/TASK-1.yaml h single low\n'
                                        'event: e1 appended\nevent: e2 duplicate\nfinding: f1\n'))
        rc, out, _, _ = run(ARGV, answer=done(kind='drafting', risk=None))
        self.assertEqual((rc, out), (0, 'intent: INT-001 intent/x\ncontract: .aieos/tasks/TASK-1.yaml h drafting '
                                        'none\nevent: e1 appended\nevent: e2 duplicate\n'))
        rc, out, _, _ = run(ARGV + ['--json'], answer=done(findings=['f1']))
        self.assertEqual((rc, out), (0, '{"appends": ["appended", "duplicate"], "claim_id": "intent/x", '
                                        '"contract_hash": "h", "event_ids": ["e1", "e2"], "findings": ["f1"], '
                                        '"intent_id": "INT-001", "kind": "single", "path": ".aieos/tasks/TASK-1.yaml", '
                                        '"risk": "low"}\n'))

    def test_refused_output(self):
        """TASK-098 AC4: "refused" gives exit 1 and "finding: run: refused <reason>" then the findings, or under
        --json one findings line."""
        rc, out, _, _ = run(ARGV, answer=refused())
        self.assertEqual((rc, out), (1, 'finding: run: refused exists\nfinding: exists: x\n'))
        answer = refused(reason='append', findings=['append: y', 'z'], intent_id='INT-001', claim_id='c',
                         kind='single', risk='low', path='p', contract_hash='h', event_ids=['e1'],
                         appends=['appended'])
        rc, out, _, _ = run(ARGV + ['--json'], answer=answer)
        self.assertEqual((rc, json.loads(out)), (1, {'findings': ['run: refused append', 'append: y', 'z']}))

    def test_answers_out_of_form(self):
        """TASK-098 AC4: each answer out of form gives the out-of-form finding."""
        bad = [None, 'done', OrderedDict(done()), dict(done(), extra=1),
               {k: v for k, v in done().items() if k != 'appends'}, done(result='maybe'), done(reason='x'),
               done(intent_id=None), done(claim_id=3), done(path=None), done(contract_hash=b'h'), done(kind='other'),
               done(kind=None), done(risk='huge'), done(risk=3), done(event_ids=['e1']),
               done(event_ids=['e1'], appends=['appended']), done(appends=['appended', 'other']),
               done(event_ids=('e1', 'e2')), done(findings='f'), done(findings=[3]), refused(reason='nope'),
               refused(reason=None), refused(kind='other'), refused(event_ids=['e']), refused(intent_id=3),
               refused(risk='huge'), refused(findings=[3])]
        for answer in bad:
            rc, out, _, _ = run(ARGV, answer=answer)
            self.assertEqual((rc, out), (1, 'finding: %s\n' % cli.RUN_OUT_OF_FORM), answer)
        self.assertEqual(cli.RUN_OUT_OF_FORM, 'run: run_task gave an answer out of form')

    def test_raises(self):
        """TASK-098 AC4: a raising run_task gives "run: a step raised <type>"; a raising _render_intent_run (patched)
        gives "cli: a step raised <type>"."""
        rc, out, _, _ = run(ARGV, raises=RuntimeError('x'))
        self.assertEqual((rc, out), (1, 'finding: run: a step raised RuntimeError\n'))
        with mock.patch.object(cli, '_render_intent_run', mock.Mock(side_effect=ValueError('render'))):
            rc, out, _, _ = run(ARGV)
        self.assertEqual((rc, out), (1, 'finding: cli: a step raised ValueError\n'))


def used_names(node):
    return ({n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            | {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)})


def function(name, file_name):
    tree = ast.parse((SRC / file_name).read_bytes().decode('utf-8'))
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name][0]


def doc(file_name):
    return ' '.join(ast.get_docstring(ast.parse((SRC / file_name).read_bytes().decode('utf-8'))).split())


class TASK098AC5Modules(unittest.TestCase):
    def test_the_command_functions(self):
        """TASK-098 AC5: by ast, cli.py's _intent_run, _render_intent_run and _intent_run_in_form name no writer or
        held_leases."""
        for name in ('_intent_run', '_render_intent_run', '_intent_run_in_form'):
            self.assertFalse(used_names(function(name, 'cli.py')) & {'writer', 'held_leases'}, name)

    def test_no_recorder_holds_owner(self):
        """TASK-098 AC5: RUN_RECORDER and the recorders of both appends and of the claim hold no "owner" in any
        case."""
        self.assertNotIn('owner', launcher.RUN_RECORDER.lower())
        w = World()
        self.assertEqual(go(w)['result'], 'done')
        appends = [call for call in w.calls if call[0] == 'append']
        self.assertEqual(len(appends), 2)
        for call in appends:
            self.assertNotIn('owner', call[6].lower())
        self.assertNotIn('owner', appends[0][3]['recorder'].lower())

    def test_this_test_file(self):
        """TASK-098 AC5: this file imports no tempfile, sqlite3, shutil or subprocess, names no open, roots only the
        literal 'C:/run-root-98', and has no one-argument .replace() and no .replace(target=...)."""
        tree = ast.parse(HERE.read_bytes().decode('utf-8'))
        imported = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imported.update(a.name.split('.')[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                imported.add((n.module or '').split('.')[0])
        self.assertEqual(imported & {'tempfile', 'sqlite3', 'shutil', 'subprocess'}, set())
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == 'open'])
        roots = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                 and len(n.value) > 3 and n.value.startswith('C:/')]
        self.assertEqual(set(roots), {ROOT})
        replaces = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == 'replace' and (len(n.args) == 1 or [k.arg for k in n.keywords] == ['target'])]
        self.assertEqual(replaces, [])


class TASK098AC6Docs(unittest.TestCase):
    def test_the_launcher_docstring(self):
        """TASK-098 AC6: launcher.py's docstring holds the run_task paragraph's phrases."""
        text = doc('launcher.py')
        for phrase in ('run_task', 'TASK-098', 'records the intent', 'drafts nothing', 'path_class',
                       "reads the caller's clock once"):
            self.assertIn(phrase, text)

    def test_the_cli_docstring_and_usage(self):
        """TASK-098 AC6: cli.py's docstring holds the run phrases, the COMMANDS phrase, the in_runtime sentence and
        main's environ sentence naming run, and not the replaced COMMANDS phrase; USAGE names run; COMMANDS ends with
        run."""
        text = doc('cli.py')
        for phrase in ('aieos run', 'TASK-098', 'records the intent', 'drafts nothing', 'is not decided by this text',
                       'COMMANDS, tasks, end, status, init, launch, approve, edit, reject, import or run',
                       'end and init call it after the parse', 'run also calls it after the parse'):
            self.assertIn(phrase, text)
        self.assertNotIn('COMMANDS, tasks, end, status, init, launch, approve, edit, reject or import', text)
        main_doc = ' '.join(cli.main.__doc__.split())
        self.assertIn('edit, reject, import and run, after the parse, through in_runtime', main_doc)
        self.assertIn('run <task> <intent> --root <path> --class <decision_agent|human_authority> '
                      '--by <decision id or name> [--owner-kept-act false] [--write <path>]... [--json]', cli.USAGE)
        self.assertEqual(cli.COMMANDS[-1], 'run')

    def test_every_test_names_its_criteria(self):
        """TASK-098 AC6: every test function of this module names "TASK-098 AC" in its own docstring, more than 20
        in all."""
        tree = ast.parse(HERE.read_bytes().decode('utf-8'))
        tests = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
        self.assertGreater(len(tests), 20)
        for node in tests:
            self.assertIn('TASK-098 AC', ast.get_docstring(node) or '', node.name)


REFUSED_STATEMENTS = (False, True, 'True', 'true', 'False', 'FALSE', '', ' false', 'false ', 0, 1, b'false')
STATEMENT_ARGV = ['run', 'TASK-1', 'do it', '--root', ROOT, '--class', 'decision_agent', '--by', 'D-1']
RUN_USAGE_LINE = ('run <task> <intent> --root <path> --class <decision_agent|human_authority> '
                  '--by <decision id or name> [--owner-kept-act false] [--write <path>]... [--json]')


class TASK115AC1Statement(unittest.TestCase):
    def refused_at_argument(self, w, out, clock, label):
        self.assertEqual((out['result'], out['reason']), ('refused', 'argument'), label)
        self.assertTrue(out['findings'][0].startswith('argument:'), label)
        self.assertEqual(clock.calls, 0, label)
        self.assertEqual(w.calls, [], label)

    def test_the_unchanged_text(self):
        """TASK-115 AC1 (the run of TASK-098 AC1): without the statement one fixed call writes exactly
        GOLDEN_RUN_CONTRACT, captured from the code before this change, ending owner_kept_act: true."""
        self.assertEqual(GOLDEN_RUN_CONTRACT, expected_single())
        w = World()
        self.assertEqual(go(w)['result'], 'done')
        self.assertEqual(written(w)[0][3], GOLDEN_RUN_CONTRACT)

    def test_the_statement_none_is_the_unchanged_text(self):
        """TASK-115 AC1 (the run of TASK-098 AC1): with the statement None the same fixed call writes exactly
        GOLDEN_RUN_CONTRACT."""
        w = World()
        self.assertEqual(go(w, owner_kept_act=None)['result'], 'done')
        self.assertEqual(written(w)[0][3], GOLDEN_RUN_CONTRACT)

    def test_the_statement_false_decision_agent(self):
        """TASK-115 AC1 (the run of TASK-098 AC1): the text false with decision_agent writes the golden text with
        its last line owner_kept_act: false and nothing else different."""
        w = World()
        out = go(w, owner_kept_act='false')
        self.assertEqual(out['result'], 'done')
        text = written(w)[0][3]
        self.assertTrue(text.endswith('owner_kept_act: false\n'))
        self.assertEqual(text, GOLDEN_RUN_CONTRACT[:-len('owner_kept_act: true\n')] + 'owner_kept_act: false\n')

    def test_the_statement_refused_values(self):
        """TASK-115 AC1 (the run of TASK-098 AC1): each other value (the booleans, the texts true, True, False,
        FALSE, an empty text, spaces around false, the numbers 0 and 1, the bytes false) is refused with reason
        argument before the clock, the log, any write or any append; falsy values are refused, not read as absent."""
        for value in REFUSED_STATEMENTS:
            w, clock = World(), Clock()
            out = go(w, clock=clock, owner_kept_act=value)
            self.refused_at_argument(w, out, clock, repr(value))

    def test_the_statement_refused_human_authority(self):
        """TASK-115 AC1 (the run of TASK-098 AC1): the text false with source_class human_authority is refused with
        reason argument at the same step."""
        w, clock = World(), Clock()
        out = go(w, clock=clock, source_class='human_authority', owner_kept_act='false')
        self.refused_at_argument(w, out, clock, 'human_authority')

    def test_the_statement_refused_with_github_paths(self):
        """TASK-115 AC1 (the run of TASK-098 AC1): the text false with decision_agent is refused with reason argument
        when a path of write is under .github/, in any case."""
        for path in ('.github/workflows/x.yml', '.GITHUB/x', '.Github/a/b.yml'):
            for write in ((path,), ('docs/a.md', path)):
                w, clock = World(), Clock()
                out = go(w, write=write, clock=clock, owner_kept_act='false')
                self.refused_at_argument(w, out, clock, write)

    def test_the_statement_refused_with_the_measurement_protocol(self):
        """TASK-115 AC1 (the run of TASK-098 AC1): the text false with decision_agent is refused with reason argument
        when a path of write is docs/pre-genesis/measurement-protocol.md, in any case."""
        for path in ('docs/pre-genesis/measurement-protocol.md', 'DOCS/PRE-GENESIS/MEASUREMENT-PROTOCOL.MD'):
            for write in ((path,), ('docs/a.md', path)):
                w, clock = World(), Clock()
                out = go(w, write=write, clock=clock, owner_kept_act='false')
                self.refused_at_argument(w, out, clock, write)

    def test_without_the_statement_the_paths_are_checked_as_before(self):
        """TASK-115 AC1 (the run of TASK-098 AC1): without the statement the same write sets behave as without the
        keyword: the answer and the text written are those of a call that gives none."""
        for write in (('.github/workflows/x.yml',), ('.GITHUB/x',), ('docs/pre-genesis/measurement-protocol.md',),
                      ('DOCS/PRE-GENESIS/MEASUREMENT-PROTOCOL.MD',)):
            w1, w2 = World(), World()
            out1 = go(w1, write=write)
            out2 = go(w2, write=write, owner_kept_act=None)
            self.assertEqual(out1, out2, write)
            self.assertEqual(written(w1), written(w2), write)
            self.assertFalse(written(w1) and written(w1)[0][3].endswith('owner_kept_act: false\n'), write)

    def test_the_keyword_is_in_the_signature(self):
        """TASK-115 AC1 (the run of TASK-098 AC1): run_task has the keyword owner_kept_act, default None."""
        parameter = inspect.signature(launcher.run_task).parameters.get('owner_kept_act')
        self.assertIsNotNone(parameter)
        self.assertIsNone(parameter.default)


class TASK115AC2Flag(unittest.TestCase):
    def test_the_call_with_the_flag(self):
        """TASK-115 AC2 (the command of TASK-098 AC4): --owner-kept-act false, anywhere among the flags, calls
        run_task with the same positional tuple as before and the keyword owner_kept_act='false'; without the flag no
        keyword is passed."""
        rc, _, stand, clock = run(STATEMENT_ARGV + ['--owner-kept-act', 'false'])
        self.assertEqual((rc, stand.calls, stand.kwargs),
                         (0, [(ROOT, 'TASK-1', 'do it', 'decision_agent', 'D-1', (), clock)],
                          [{'owner_kept_act': 'false'}]))
        rc, _, stand, clock = run(['run', 'TASK-1', 'do it', '--write', 'b.md', '--owner-kept-act', 'false',
                                   '--root', ROOT, '--class', 'decision_agent', '--by', 'D-1', '--json'])
        self.assertEqual((rc, stand.calls, stand.kwargs),
                         (0, [(ROOT, 'TASK-1', 'do it', 'decision_agent', 'D-1', ('b.md',), clock)],
                          [{'owner_kept_act': 'false'}]))
        rc, _, stand, clock = run(STATEMENT_ARGV)
        self.assertEqual((rc, stand.calls, stand.kwargs),
                         (0, [(ROOT, 'TASK-1', 'do it', 'decision_agent', 'D-1', (), clock)], [{}]))

    def test_the_flag_usage_errors(self):
        """TASK-115 AC2 (the command of TASK-098 AC4): a repeat, a missing value, any value but false (true, False,
        FALSE, empty, one that begins with --), the flag with --class human_authority and the flag on a command
        other than run each give exit 2 and USAGE with neither the clock nor run_task called."""
        bad = [STATEMENT_ARGV + ['--owner-kept-act', 'false', '--owner-kept-act', 'false'],
               STATEMENT_ARGV + ['--owner-kept-act'],
               STATEMENT_ARGV + ['--owner-kept-act', 'true'],
               STATEMENT_ARGV + ['--owner-kept-act', 'False'],
               STATEMENT_ARGV + ['--owner-kept-act', 'FALSE'],
               STATEMENT_ARGV + ['--owner-kept-act', ''],
               STATEMENT_ARGV + ['--owner-kept-act', '--json'],
               STATEMENT_ARGV + ['--owner-kept-act', '--write', 'a.md'],
               ['run', 'TASK-1', 'do it', '--root', ROOT, '--class', 'human_authority', '--by', NAME,
                '--owner-kept-act', 'false'],
               ['tasks', '--root', ROOT, '--owner-kept-act', 'false'],
               ['status', '--root', ROOT, '--owner-kept-act', 'false'],
               ['end', 'SESSION-1', '--root', ROOT, '--owner-kept-act', 'false'],
               ['init', '--root', ROOT, '--owner-kept-act', 'false'],
               ['launch', 'TASK-1', '--root', ROOT, '--owner-kept-act', 'false'],
               ['approve', 'TASK-1', '--root', ROOT, '--class', 'decision_agent', '--by', 'D-1',
                '--owner-kept-act', 'false'],
               ['edit', 'TASK-1', '--root', ROOT, '--class', 'decision_agent', '--by', 'D-1', '--note', 'n',
                '--owner-kept-act', 'false'],
               ['reject', 'TASK-1', '--root', ROOT, '--class', 'decision_agent', '--by', 'D-1',
                '--owner-kept-act', 'false'],
               ['import', 'TASK-1', '--root', ROOT, '--owner-kept-act', 'false']]
        for argv in bad:
            for environ in ({}, {'AIEOS_ROOT': 'x'}):
                rc, out, stand, clock = run(argv, environ=environ)
                self.assertEqual((rc, out, stand.calls, stand.kwargs, clock.calls), (2, cli.USAGE, [], [], 0), argv)

    def test_the_usage_line(self):
        """TASK-115 AC2 (the command of TASK-098 AC4): the run line of USAGE is the new line, and cli.py's parser
        description names the flag."""
        self.assertIn('python -m aieos_bootstrap.cli ' + RUN_USAGE_LINE, cli.USAGE)
        self.assertIn('--owner-kept-act', doc('cli.py'))


class TASK115AC3Meet(unittest.TestCase):
    def approve(self, text):
        h = digest(text)
        contract = base_inputs._parse_contract_text(text)
        w = World(log=Log().add('task.drafted', {'contract_version': 'v1', 'contract_hash': h}, TASK))
        return launcher.approval_act(ROOT, TASK, 'approve', 'decision_agent', WHO, None, lambda: NOW, read=w.read,
                                     read_log=w.read_log, append=w.append,
                                     contract_at=lambda root, head, task: ((contract, h), None))

    def test_the_text_reads_as_the_statement(self):
        """TASK-115 AC3 (the run of TASK-098 AC1): the contract read back by the subset parser holds the text false
        with the statement, and the text true without it."""
        w = World()
        go(w, owner_kept_act='false')
        self.assertEqual(base_inputs._parse_contract_text(written(w)[0][3])['owner_kept_act'], 'false')
        w = World()
        go(w)
        self.assertEqual(base_inputs._parse_contract_text(written(w)[0][3])['owner_kept_act'], 'true')

    def test_approval_act_meets_the_statement(self):
        """TASK-115 AC3 (the run of TASK-098 AC1): a decision_agent approval of the contract made with the statement
        is done; of the contract made without it, refused at the step owner_kept_act."""
        w = World()
        go(w, owner_kept_act='false')
        out = self.approve(written(w)[0][3])
        self.assertEqual((out['result'], out['reason']), ('done', None), out['findings'])
        w = World()
        go(w)
        out = self.approve(written(w)[0][3])
        self.assertEqual((out['result'], out['reason']), ('refused', 'owner_kept_act'))
        self.assertEqual(out['findings'], ['owner_kept_act: a decision_agent approval of a task whose '
                                           'owner_kept_act is set is refused'])


class TASK115AC4Stale(unittest.TestCase):
    def test_the_stale_texts_are_gone(self):
        """TASK-115 AC4 (the docstring of TASK-098 AC6): cli.NO_STARTER no longer says a runtime is started by the
        owner, and cli.py's docstring no longer says the commands are not run on any real project."""
        self.assertNotIn('a runtime is started by the owner', cli.NO_STARTER)
        self.assertNotIn('not run on any real project', doc('cli.py'))
        self.assertIn('is not decided by this text', doc('cli.py'))

    def test_the_ten_replaced_sentences(self):
        """TASK-115 AC4 (the docstrings of TASK-098 AC6): over each source file with its whitespace folded, each of
        the ten NEW sentences of the contract is present (the sentence of items 3 and 5 twice in cli.py), each OLD
        sentence is absent, and cli.NO_STARTER is the NEW text of item 7."""
        text = {name: ' '.join((SRC / name).read_bytes().decode('utf-8').split())
                for name in ('cli.py', 'launcher.py', 'writer.py')}
        used = "Its use on a real project is not decided by this text."
        old_used = "It is not run on any real project: its real use is the owner's, asked separately."
        pairs = (
            ('cli.py', "As shipped, launch starts no runtime: starting one stays the owner's (spec 7 :35).",
             'As shipped, launch starts no runtime; who decides starting one, and building a starter, is set by '
             'specification 7 :35.', 1),
            ('cli.py', "it drafts nothing: reading the repository and drafting the proposals are a launched session's,"
             " the owner's.",
             "it drafts nothing: reading the repository and drafting the proposals are a launched session's.", 1),
            ('cli.py', old_used, used, 2),
            ('cli.py', "it drafts nothing: doing the change or drafting the proposal set is a launched session's, the "
             "owner's.",
             "it drafts nothing: doing the change or drafting the proposal set is a launched session's.", 1),
            ('cli.py', "Nothing runs this module but its tests and the owner's own use.",
             'Nothing runs this module but its tests and its uses on a real project, each decided on its own.', 1),
            ('launcher.py', "It starts no runtime: no process but through gitread, no hook placed, no setting changed;"
             " running `aieos launch` with a runtime stays the owner's (DM A51 item (4)).",
             'It starts no runtime: no process but through gitread, no hook placed, no setting changed; who decides '
             'running `aieos launch` with a runtime, and building a starter, is set by specification 7 :35.', 1),
            ('launcher.py', "Reading the repository and drafting the proposals are a launched session's, and every "
             "launch is the owner's.",
             "Reading the repository and drafting the proposals are a launched session's, and every launch is decided "
             "as specification 7 :35 says.", 1),
            ('writer.py', 'No caller in the core yet; ``.gitignore`` is not changed here (carried to the task that '
             'first creates a real project-state directory).',
             "Its callers are the core's modules (every write of the project-state directory goes through it); "
             "``.gitignore`` is not changed here.", 1))
        for name, old, new, count in pairs:
            self.assertEqual(text[name].count(new), count, new)
            self.assertNotIn(old, text[name], old)
        self.assertEqual(cli.NO_STARTER, 'launch: no runtime starter is shipped (specification 7 :35, DEF-0101)')
        self.assertNotIn('launch: no runtime starter (a runtime is started by the owner; specification 7 :35, '
                         'DEF-0101)', text['cli.py'])
        self.assertIn('no runtime starter', doc('cli.py'))


if __name__ == '__main__':
    unittest.main()

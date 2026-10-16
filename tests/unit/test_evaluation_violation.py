"""Unit tests of task TASK-053 (its rules R1 to R7 and an end-to-end test): evaluation.evaluate_task gives the governor
the task's violation.detected payloads beside its record.added payloads, so a recorded violation makes the acceptance
decision REJECT. The Git reader and the writer's functions are stand-ins bound to the real signatures: the reader
answers from a table of commits, and the stand-in writer keeps a log as bytes, deciding each append with
eventlog.append as the real writer does, so no git starts and no file is touched here. Each test names the criteria it
stands for in its own docstring."""

import ast
import datetime
import hashlib
import inspect
import pathlib
import random
import unittest

from aieos_bootstrap import evaluation
from aieos_bootstrap import eventlog
from aieos_bootstrap import gitread
from aieos_bootstrap import records
from aieos_bootstrap import violation
from aieos_bootstrap import writer

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap'
FS_ROOT = str(pathlib.Path(__file__).resolve().parents[2] / 'no-such-state-root')
REPO = str(pathlib.Path(__file__).resolve().parents[2])
TREE = 'b' * 40
TASK = 'TASK-300'
REC = 'aieos-core'
HOOK = 'a hook (test)'
UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 10, 16, 12, 0, 0, tzinfo=UTC)
LATER = NOW + datetime.timedelta(hours=1)
CONTRACT = b'task: TASK-300\n'
CHASH = hashlib.sha256(CONTRACT).hexdigest()
DECLARED = {'intent_versions': {'SPEC-001': 'v1'}, 'retries': 2}
MINE = 'Do the task\n\nThe body.\n\nAIEOS-Task: TASK-300\n'
PLAIN = 'Records\n\nThe body.\n'
FIRST = {'epoch': 'e1', 'counter': 1}
SECOND = {'epoch': 'e1', 'counter': 2}
# TASK-053 AC6: the SHA-256 of each module's text after its module docstring at the base (main at 12349ef7).
CODE_AT_BASE = {
    'violation.py': '623358431ff0afdf28ba621256c7f14a05a45132be71fe5a5063b1fb4970ad5f',
    'adapter.py': '97a4d95f6cf6008b31411f4c99fb414c0f4d2e20ab2e7ab5bc8bce191739eaf0',
    'replay.py': 'a91eabdb47057c2858dc0c55e75d0452406c845407d02eb92946fa583253a9b6',
}


def cid(n):
    return '%040x' % n


def bound(real, args, kwargs):
    inspect.signature(real).bind(*args, **kwargs)


def ok(out):
    return {'exit': 0, 'out': out, 'err': b'', 'error': None}


def commit_bytes(parents, message):
    head = 'tree %s\n' % TREE + ''.join('parent %s\n' % p for p in parents)
    head += 'author Tester <tester> 1700000000 +0000\ncommitter Tester <tester> 1700000000 +0000\n\n'
    return (head + message).encode('utf-8')


class Repo:
    """A stand-in for gitread.run over main's commit cid(1) and one task commit cid(2)."""

    def __init__(self):
        self.table = {cid(1): ([], PLAIN, ['docs/a.md']), cid(2): ([cid(1)], MINE, ['src/x.py'])}

    def __call__(self, *args, **kwargs):
        bound(gitread.run, args, kwargs)
        cmd = args[1]
        parents, message, paths = self.table[cmd[-1]]
        if cmd[0] == 'cat-file':
            return ok(commit_bytes(parents, message))
        return ok(b''.join(p.encode('utf-8') + b'\0' for p in paths))


class Store:
    """The event log in memory and the store's held lease, as the writer keeps them: append decides with
    eventlog.append (the held lease on the task passed in), release by token; read_log gives the bytes."""

    def __init__(self, lease=None):
        self.log = b''
        self.lease = lease

    def read_log(self, *args, **kwargs):
        bound(writer.read_log, args, kwargs)
        return self.log

    def append(self, *args, **kwargs):
        bound(writer.append_event, args, kwargs)
        root, event_type, payload, event_id, appended_at, recorder = args
        task_id = kwargs.get('task_id')
        lease = self.lease if self.lease and self.lease['task_id'] == task_id else None
        r = eventlog.append(self.log, event_type, payload, event_id, appended_at, task_id=task_id,
                            fencing_token=kwargs.get('fencing_token'), lease=lease, recorder=recorder)
        if r.result == 'appended':
            self.log += r.line
        return writer.WriteResult(r)

    def release(self, *args, **kwargs):
        bound(writer.release_lease_token, args, kwargs)
        root, task_id, token = args
        if self.lease is None or self.lease['task_id'] != task_id:
            return writer.StoreResult('refused', 'none', ['no lease is held'])
        if self.lease['fencing_token'] != token:
            return writer.StoreResult('refused', 'token', ['another token is held'])
        lease, self.lease = self.lease, None
        return writer.StoreResult('done', value=lease)

    def add(self, event_type, payload, event_id, task_id=TASK, fencing_token=None):
        r = self.append(FS_ROOT, event_type, payload, event_id, NOW, REC, task_id=task_id,
                        fencing_token=fencing_token)
        assert r.result == 'appended', (r.result, r.findings)
        return self


def lease(token):
    return {'task_id': TASK, 'fencing_token': dict(token), 'expires_at': LATER}


def approved(store, eid='approved-1'):
    return store.add('task.approved', {'contract_version': 'v1', 'contract_hash': CHASH, 'approval_record': 'rec-a'},
                     eid)


def submitted(store, eid='submitted-1', token=SECOND):
    store.lease = lease(token)
    return store.add('task.submitted', {'commit': cid(2), 'compensating': False}, eid, fencing_token=token)


def observation(rid='obs-1', task=TASK):
    return {'record_id': rid, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
            'recorder': HOOK, 'subject': task, 'evidence_type': 'write_outside_write_set', 'outcome': 'blocking',
            'blocking_kind': 'violation', 'refers_to': 'src/outside.py'}


def ci_record(rid='ci-1'):
    return {'record_id': rid, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_external_ci',
            'recorder': 'ci', 'subject': TASK, 'gate': 'G1', 'outcome': 'pass', 'commit': cid(2),
            'intent_versions': {'SPEC-001': 'v1'}}


def values():
    return {
        'contract': {'traces_to': ['SPEC-001'], 'risk': 'high', 'owner_kept_act': False, 'verification_plan': ['G0', 'G1']},
        'changed_paths': ['src/x.py'],
        'risk_rules': [{'id': 'R2', 'match': ['src/**', 'tests/**'], 'class': 'medium'}],
        'owner_kept_rules': [{'id': 'OPS-002', 'match': ['docs/pre-genesis/measurement-protocol.md']}],
        'articles': [{'id': 'INV-002', 'scope': ['src/**'], 'evidence_required': ['ai_review']}],
        'default_profiles': {'high': [{'dimension': 'functional', 'evidence_types': ['unit_test']}]},
        'requirement_profiles': [],
        'delegation': True,
        'evidence_comparison': {'weakens': False},
        'auto_accept': {},
        'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1',
    }


def evaluate(store, extra=()):
    log_writes = []

    def append(*args, **kwargs):
        log_writes.append(args[1])
        return store.append(*args, **kwargs)

    r = evaluation.evaluate_task(FS_ROOT, REPO, TASK, CONTRACT, DECLARED, values(), list(extra), REC, NOW,
                                 read=Repo(), read_log=store.read_log, append=append)
    return r, log_writes


class R1Selection(unittest.TestCase):
    def test_record_and_violation_payloads_in_log_order(self):
        """TASK-053 AC1, TASK-053 AC10: the governor is given the task's record.added and violation.detected payloads,
        in log order, then extra_records; another type is not given."""
        store = approved(Store())
        store.add('record.added', ci_record('ci-1'), 'r-1')
        store.add('violation.detected', observation('obs-1'), 'v-1')
        store.add('record.added', ci_record('ci-2'), 'r-2')
        submitted(store)
        got = evaluation._task_events(store.read_log, FS_ROOT, TASK)[5]
        self.assertEqual([p['record_id'] for p in got], ['ci-1', 'obs-1', 'ci-2'])
        self.assertEqual(evaluation.RECORD_EVENTS, ('record.added', 'violation.detected'))

    def test_the_failing_case_without_the_violation_type(self):
        """TASK-053 AC1, TASK-053 AC10: the base's selection (record.added only) would leave the violation out; the
        new one does not."""
        store = approved(Store())
        store.add('violation.detected', observation('obs-1'), 'v-1')
        submitted(store)
        events = [line.event for line in records.check_log(store.log).lines if line.duplicate_of is None]
        base = [e['payload'] for e in events if e['type'] == 'record.added' and e.get('task_id') == TASK]
        got = evaluation._task_events(store.read_log, FS_ROOT, TASK)[5]
        self.assertEqual(base, [])
        self.assertEqual([p['record_id'] for p in got], ['obs-1'])


class R2Decision(unittest.TestCase):
    def test_a_violation_gives_reject_at_row_1(self):
        """TASK-053 AC2, TASK-053 AC10: with a violation of the task the decision is REJECT and the next state
        REJECTED; the decision is appended once; the event id covers the violation's record_id; a rerun finds the
        task REJECTED, which this path does not evaluate (reason "state"), and appends nothing."""
        store = approved(Store())
        store.add('violation.detected', observation('obs-1'), 'v-1')
        submitted(store)
        r, writes = evaluate(store)
        self.assertEqual((r['result'], r['decision'], r['next_task_state']), ('evaluated', 'REJECT', 'REJECTED'))
        self.assertEqual(writes, ['decision.acceptance'])
        self.assertEqual(r['event_id'], evaluation.event_id_of(TASK, 'submitted-1', ['obs-1']))
        again, more = evaluate(store)
        self.assertEqual((again['result'], again['reason'], more), ('refused', 'state', []))

    def test_without_the_violation_no_reject(self):
        """TASK-053 AC2, TASK-053 AC10: the same log without the violation is not rejected (the failing case)."""
        store = submitted(approved(Store()))
        r, _ = evaluate(store)
        self.assertEqual(r['result'], 'evaluated')
        self.assertNotEqual(r['decision'], 'REJECT')


class R3LeftOut(unittest.TestCase):
    def test_another_tasks_violation_is_not_read(self):
        """TASK-053 AC3, TASK-053 AC10: a violation.detected of another task is not given to the governor."""
        store = approved(Store())
        store.add('violation.detected', observation('obs-x', task='TASK-399'), 'v-x', task_id='TASK-399')
        submitted(store)
        got = evaluation._task_events(store.read_log, FS_ROOT, TASK)[5]
        self.assertEqual(got, [])
        r, _ = evaluate(store)
        self.assertNotEqual(r['decision'], 'REJECT')

    def test_a_repeated_record_id_is_left_out_with_a_finding(self):
        """TASK-053 AC3, TASK-053 AC10: a violation whose record_id an earlier kept record has is left out with
        _kept's finding; the first is kept and still rejects."""
        store = approved(Store())
        store.add('violation.detected', observation('obs-1'), 'v-1')
        store.add('violation.detected', observation('obs-1'), 'v-2')
        submitted(store)
        r, _ = evaluate(store)
        self.assertEqual(r['decision'], 'REJECT')
        self.assertTrue([f for f in r['findings'] if 'repeated' in f and 'obs-1' in f], r['findings'])
        self.assertEqual(r['event_id'], evaluation.event_id_of(TASK, 'submitted-1', ['obs-1']))


class R4Span(unittest.TestCase):
    def test_a_violation_before_a_new_approval_still_rejects(self):
        """TASK-053 AC4, TASK-053 AC10: a violation, then a new task.approved and a new submission: the evaluation
        still gives REJECT (the whole-log span)."""
        store = approved(Store())
        store.add('violation.detected', observation('obs-1'), 'v-1')
        approved(store, eid='approved-2')
        submitted(store, eid='submitted-2')
        r, _ = evaluate(store)
        self.assertEqual((r['decision'], r['next_task_state']), ('REJECT', 'REJECTED'))

    def test_the_new_approval_alone_does_not_reject(self):
        """TASK-053 AC4, TASK-053 AC10: the same log without the violation is not rejected (the failing case)."""
        store = approved(Store())
        approved(store, eid='approved-2')
        submitted(store, eid='submitted-2')
        r, _ = evaluate(store)
        self.assertNotEqual(r['decision'], 'REJECT')


class R5Unchanged(unittest.TestCase):
    def test_property_the_selection_equals_the_base_without_violations(self):
        """TASK-053 AC5, TASK-053 AC10: over generated logs with no violation.detected (fixed seeds), the selection
        equals the base's expression; with one, it does not (the failing case)."""
        for seed in range(40):
            rnd = random.Random(seed)
            store = approved(Store())
            for n in range(rnd.randint(0, 6)):
                if rnd.random() < 0.5:
                    store.add('record.added', ci_record('ci-%d' % n), 'r-%d' % n)
                else:
                    store.add('record.added', dict(ci_record('o-%d' % n), subject='TASK-399'), 'o-%d' % n,
                              task_id='TASK-399')
            submitted(store)
            events = [line.event for line in records.check_log(store.log).lines if line.duplicate_of is None]
            base = [e['payload'] for e in events if e['type'] == 'record.added' and e.get('task_id') == TASK]
            self.assertEqual(evaluation._task_events(store.read_log, FS_ROOT, TASK)[5], base, seed)
            store.add('violation.detected', observation('obs-%d' % seed), 'v-%d' % seed)
            self.assertNotEqual(evaluation._task_events(store.read_log, FS_ROOT, TASK)[5], base, seed)


def code_hash(name):
    text = (SRC / name).read_bytes().decode('utf-8')
    return hashlib.sha256(text.split('"""', 2)[2].encode('utf-8')).hexdigest()


class R6Texts(unittest.TestCase):
    def test_code_unchanged_and_docstrings_updated(self):
        """TASK-053 AC6, TASK-053 AC10: violation.py, adapter.py and replay.py keep their base code after the module
        docstring; their docstrings carry the new limit and not the old one."""
        for name, want in CODE_AT_BASE.items():
            self.assertEqual(code_hash(name), want, name)
        tail = (SRC / 'violation.py').read_bytes().decode('utf-8').split('"""', 2)[2]
        changed = tail.replace('def ', 'def  ', 1)
        self.assertNotEqual(changed, tail)
        self.assertNotEqual(hashlib.sha256(changed.encode('utf-8')).hexdigest(), CODE_AT_BASE['violation.py'])
        for name in CODE_AT_BASE:
            doc = ast.get_docstring(ast.parse((SRC / name).read_bytes().decode('utf-8')))
            self.assertIn('TASK-053', doc, name)
            self.assertNotIn('does not yet make acceptance reject', doc, name)
            self.assertNotIn('widens the evaluation', doc, name)
        doc = ast.get_docstring(ast.parse((SRC / 'violation.py').read_bytes().decode('utf-8')))
        self.assertIn('(abridged, not verbatim)', doc)


class R7Limits(unittest.TestCase):
    def test_evaluation_docstring_and_imports(self):
        """TASK-053 AC7, TASK-053 AC8, TASK-053 AC10: evaluation.py's docstring states the selection and the span's
        limit, and evaluation.py's and violation.py's docstrings state the limits of AC7 and the repeated record_id
        limit, which adapter.py's and replay.py's docstrings also name; evaluation.py's imports are the base's."""
        tree = ast.parse((SRC / 'evaluation.py').read_bytes().decode('utf-8'))
        doc = ast.get_docstring(tree)
        for words in ('record.added and violation.detected payloads', 'over\n   the whole log',
                      'makes every later evaluation of the task REJECT', 'A session fenced out leaves no'):
            self.assertIn(words, doc)
        vdoc = ast.get_docstring(ast.parse((SRC / 'violation.py').read_bytes().decode('utf-8')))
        limits = ('where the task is evaluable', 'need not REJECT', 'a later task is to make this fail closed',
                  'stays READY', 'section 11 point 12', 'refused_submission', 'F-a is kept', 'C6 unmeasured',
                  'no conformance set or fixture is changed', 'no observed read-set call', "real writer's files")
        for d in (doc, vdoc):
            flat = ' '.join(d.split())
            for words in limits:
                self.assertIn(words, flat)
        self.assertIn('rerun while the task is still evaluable gives "duplicate"', ' '.join(doc.split()))
        self.assertNotIn('so a rerun gives "duplicate"', ' '.join(doc.split()))
        for name in ('adapter.py', 'replay.py'):
            flat = ' '.join(ast.get_docstring(ast.parse((SRC / name).read_bytes().decode('utf-8'))).split())
            for words in ('where the task is evaluable', 'an earlier kept record'):
                self.assertIn(words, flat, name)
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                mods.update('%s.%s' % (node.module, a.name) for a in node.names)
        self.assertEqual(mods, {'datetime', 'hashlib', 'os', 're', 'aieos_bootstrap.gitread', 'aieos_bootstrap.governor',
                                'aieos_bootstrap.records', 'aieos_bootstrap.recovery', 'aieos_bootstrap.writer'})
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Assert)])


class EndToEnd(unittest.TestCase):
    def test_violation_record_then_evaluation_rejects(self):
        """TASK-053 AC2, TASK-053 AC4, TASK-053 AC10: task.approved; a first lease; violation.record with its token
        (violation.detected, the decision STOP: violation, the release); a second lease; a task.submitted with its
        token; then evaluate_task in VERIFYING gives REJECT with the violation's record_id kept."""
        store = approved(Store())
        store.lease = lease(FIRST)
        v = violation.record(FS_ROOT, TASK, dict(FIRST), observation('obs-1'), 'violation-1', HOOK, NOW,
                             append=store.append, release=store.release)
        self.assertEqual((v['result'], v['appended']), ('done', ['violation-1', 'violation-1/decision']))
        self.assertIsNone(store.lease)
        submitted(store, token=SECOND)
        r, writes = evaluate(store)
        self.assertEqual((r['result'], r['decision'], r['next_task_state']), ('evaluated', 'REJECT', 'REJECTED'))
        self.assertEqual(r['event_id'], evaluation.event_id_of(TASK, 'submitted-1', ['obs-1']))

    def test_without_the_violation_the_same_run_is_not_rejected(self):
        """TASK-053 AC2, TASK-053 AC10: the same run with no violation.record is not rejected (the failing case)."""
        store = approved(Store())
        submitted(store, token=SECOND)
        r, _ = evaluate(store)
        self.assertNotEqual(r['decision'], 'REJECT')


if __name__ == '__main__':
    unittest.main()

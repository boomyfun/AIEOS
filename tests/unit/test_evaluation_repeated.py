"""Unit and property tests of task TASK-054 (its rules R1 to R7 and an end-to-end test): a record whose outcome is
'blocking' that evaluation._kept leaves out, out of form or for a record_id an earlier kept record has, refuses the
evaluation with reason "records", unless its record_id equals that of an earlier kept blocking record with the same
blocking_kind; nothing is appended and the governor is not called. The Git reader and the writer's functions are
stand-ins bound to the real signatures: the reader answers from a table of commits, and the stand-in writer keeps a
log as bytes, deciding each append with eventlog.append as the real writer does, so no git starts and no file is
touched here. Each test names the criteria it stands for in its own docstring."""

import ast
import datetime
import hashlib
import inspect
import pathlib
import random
import unittest
from unittest import mock

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
# TASK-054 AC4: the SHA-256 of each module's text after its module docstring at the base (main at f640db3e).
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
        if r.result != 'appended':
            raise RuntimeError((r.result, r.findings))
        return self


def lease(token):
    return {'task_id': TASK, 'fencing_token': dict(token), 'expires_at': LATER}


def approved(store, eid='approved-1'):
    return store.add('task.approved', {'contract_version': 'v1', 'contract_hash': CHASH, 'approval_record': 'rec-a'},
                     eid)


def submitted(store, eid='submitted-1', token=SECOND):
    store.lease = lease(token)
    return store.add('task.submitted', {'commit': cid(2), 'compensating': False}, eid, fencing_token=token)


def observation(rid='obs-1', kind='violation'):
    return {'record_id': rid, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
            'recorder': HOOK, 'subject': TASK, 'evidence_type': 'write_outside_write_set', 'outcome': 'blocking',
            'blocking_kind': kind, 'refers_to': 'src/outside.py'}


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
    """evaluate_task over the stand-ins; returns the result, the event types appended, and the governor's calls."""
    log_writes, calls = [], []
    real = evaluation.governor.evaluate

    def append(*args, **kwargs):
        log_writes.append(args[1])
        return store.append(*args, **kwargs)

    def spy(*args, **kwargs):
        calls.append(args)
        return real(*args, **kwargs)

    with mock.patch.object(evaluation.governor, 'evaluate', spy):
        r = evaluation.evaluate_task(FS_ROOT, REPO, TASK, CONTRACT, DECLARED, values(), list(extra), REC, NOW,
                                     read=Repo(), read_log=store.read_log, append=append)
    return r, log_writes, calls


def base_kept(payloads, extra_records):
    """The base's _kept (main at f640db3e), kept here to compare with: the kept records and the findings."""
    kept, found, seen = [], [], set()
    for where, rec in [('log', p) for p in payloads] + [('extra_records', r) for r in extra_records]:
        problems = records.check_record(rec)
        rid = rec.get('record_id') if isinstance(rec, dict) else None
        if problems:
            found.append('records: a record from %s is left out: %s' % (where, '; '.join(str(f) for f in problems)))
        elif not isinstance(rid, str) or rid in seen:
            found.append('records: a record from %s is left out: its record_id %r is repeated' % (where, rid))
        else:
            seen.add(rid)
            kept.append(rec)
    return kept, found


def refused_by_records(test, r, writes, calls):
    test.assertEqual((r['result'], r['reason']), ('refused', 'records'), r['findings'])
    test.assertEqual((writes, calls), ([], []))
    test.assertIsNone(r['decision'])


class R1Refused(unittest.TestCase):
    def test_a_violation_reusing_a_passing_records_id_refuses(self):
        """TASK-054 AC1, TASK-054 AC7: a violation.detected reusing the record_id of an earlier passing record.added
        of the task gives "refused", reason "records"; nothing is appended and the governor is not called; the
        finding names the record_id and the source."""
        store = approved(Store())
        store.add('record.added', ci_record('obs-1'), 'r-1')
        store.add('violation.detected', observation('obs-1'), 'v-1')
        submitted(store)
        r, writes, calls = evaluate(store)
        refused_by_records(self, r, writes, calls)
        self.assertTrue([f for f in r['findings'] if 'blocking' in f and "'obs-1'" in f and 'from log' in f],
                        r['findings'])
        self.assertTrue([f for f in r['findings'] if 'repeated' in f], r['findings'])

    def test_the_failing_case_the_base_would_leave_it_out_and_evaluate(self):
        """TASK-054 AC1, TASK-054 AC7: the base's _kept leaves the violation out with no refusal, so the base would
        call the governor without it; the same log with a fresh record_id is evaluated and rejected."""
        store = approved(Store())
        store.add('record.added', ci_record('obs-1'), 'r-1')
        store.add('violation.detected', observation('obs-1'), 'v-1')
        submitted(store)
        payloads = evaluation._task_events(store.read_log, FS_ROOT, TASK)[5]
        kept, found = base_kept(payloads, [])
        self.assertEqual([p['record_id'] for p in kept], ['obs-1'])
        self.assertEqual([p['outcome'] for p in kept], ['pass'])
        self.assertEqual(evaluation._kept(payloads, [])[:2], (kept, found))
        fresh = approved(Store())
        fresh.add('record.added', ci_record('ci-1'), 'r-1')
        fresh.add('violation.detected', observation('obs-1'), 'v-1')
        submitted(fresh)
        r, writes, calls = evaluate(fresh)
        self.assertEqual((r['result'], r['decision'], len(calls)), ('evaluated', 'REJECT', 1))


class R2Kinds(unittest.TestCase):
    def test_a_blocking_record_added_reusing_an_id_refuses(self):
        """TASK-054 AC1, TASK-054 AC7: a blocking record.added (blocking_kind other) reusing a passing record's id
        refuses."""
        store = approved(Store())
        store.add('record.added', ci_record('x-1'), 'r-1')
        store.add('record.added', observation('x-1', kind='other'), 'r-2')
        submitted(store)
        refused_by_records(self, *evaluate(store))

    def test_blocking_records_in_extra_records_refuse(self):
        """TASK-054 AC1, TASK-054 AC7: a blocking record in extra_records that is out of form (no recorder, and one
        with no record_id, named by its position), or that repeats a log record's id, refuses."""
        store = approved(Store())
        store.add('record.added', ci_record('ci-1'), 'r-1')
        submitted(store)
        out_of_form = dict(observation('e-1'))
        del out_of_form['recorder']
        no_id = dict(observation('e-2'))
        del no_id['record_id']
        for extra, name in (([out_of_form], "'e-1'"), ([no_id], 'position 2'), ([observation('ci-1')], "'ci-1'")):
            r, writes, calls = evaluate(store, extra)
            refused_by_records(self, r, writes, calls)
            self.assertTrue([f for f in r['findings'] if 'from extra_records' in f and name in f], r['findings'])

    def test_a_violation_behind_a_blocking_record_of_another_kind_refuses(self):
        """TASK-054 AC1, TASK-054 AC7 (erratum E2 of decision D-1028): a violation.detected reusing the id of an
        earlier kept blocking record.added of another blocking_kind refuses."""
        store = approved(Store())
        store.add('record.added', observation('b-1', kind='out_of_scope'), 'r-1')
        store.add('violation.detected', observation('b-1'), 'v-1')
        submitted(store)
        refused_by_records(self, *evaluate(store))

    def test_a_blocking_record_behind_one_of_another_subject_refuses(self):
        """TASK-054 AC1, TASK-054 AC7 (erratum E1 to AC1, decision D-1035): in extra_records, a blocking record of
        another task's subject and then the same record_id, kind and outcome for this task: the first is kept (the
        governor does not read it), and the second refuses, with nothing appended and the governor not called; with
        a kind-only exception it would be let through."""
        store = approved(Store())
        store.add('record.added', ci_record('ci-1'), 'r-1')
        submitted(store)
        extra = [dict(observation('x-9'), subject='TASK-999'), observation('x-9')]
        payloads = evaluation._task_events(store.read_log, FS_ROOT, TASK)[5]
        kept, _, hidden = evaluation._kept(payloads, extra)
        self.assertEqual([(r['record_id'], r['subject']) for r in kept], [('ci-1', TASK), ('x-9', 'TASK-999')])
        self.assertEqual(kept[1]['blocking_kind'], extra[1]['blocking_kind'])
        self.assertTrue(hidden)
        r, writes, calls = evaluate(store, extra)
        refused_by_records(self, r, writes, calls)
        self.assertTrue([f for f in r['findings'] if 'from extra_records' in f and "'x-9'" in f], r['findings'])

    def test_the_same_records_with_one_subject_reject(self):
        """TASK-054 AC1, TASK-054 AC2, TASK-054 AC7: the same two records with this task's subject (the failing case
        of the test above): the second is excepted and the evaluation goes on to REJECT."""
        store = approved(Store())
        store.add('record.added', ci_record('ci-1'), 'r-1')
        submitted(store)
        r, writes, calls = evaluate(store, [observation('x-9'), observation('x-9')])
        self.assertEqual((r['result'], r['decision'], writes, len(calls)),
                         ('evaluated', 'REJECT', ['decision.acceptance'], 1))


class R3GoesOn(unittest.TestCase):
    def test_an_out_of_form_twin_of_a_kept_violation_goes_on(self):
        """TASK-054 AC2, TASK-054 AC7: an out-of-form blocking record in extra_records with the record_id, kind and
        subject of a kept violation of the log is left out with _kept's finding, excepted, and the evaluation goes on
        to REJECT."""
        store = approved(Store())
        store.add('violation.detected', observation('obs-1'), 'v-1')
        submitted(store)
        twin = dict(observation('obs-1'))
        del twin['recorder']
        r, writes, calls = evaluate(store, [twin])
        self.assertEqual((r['result'], r['decision'], len(calls)), ('evaluated', 'REJECT', 1))
        self.assertTrue([f for f in r['findings'] if 'from extra_records is left out' in f], r['findings'])

    def test_an_extra_twin_of_a_kept_violation_goes_on(self):
        """TASK-054 AC2, TASK-054 AC7: a blocking record in extra_records repeating a kept violation of the log (the
        same record_id, kind and subject) is left out, excepted, and the evaluation goes on to REJECT."""
        store = approved(Store())
        store.add('violation.detected', observation('obs-1'), 'v-1')
        submitted(store)
        r, writes, calls = evaluate(store, [observation('obs-1')])
        self.assertEqual((r['result'], r['decision'], len(calls)), ('evaluated', 'REJECT', 1))
        self.assertTrue([f for f in r['findings'] if 'repeated' in f], r['findings'])

    def test_a_violation_repeating_a_kept_violation_rejects(self):
        """TASK-054 AC2, TASK-054 AC7: a violation repeating a kept violation's id (the same blocking_kind) is left
        out and the evaluation goes on to REJECT."""
        store = approved(Store())
        store.add('violation.detected', observation('obs-1'), 'v-1')
        store.add('violation.detected', observation('obs-1'), 'v-2')
        submitted(store)
        r, writes, calls = evaluate(store)
        self.assertEqual((r['result'], r['decision'], writes, len(calls)),
                         ('evaluated', 'REJECT', ['decision.acceptance'], 1))
        self.assertEqual(r['event_id'], evaluation.event_id_of(TASK, 'submitted-1', ['obs-1']))

    def test_passing_records_left_out_do_not_refuse(self):
        """TASK-054 AC2, TASK-054 AC7: a passing record repeating an id, and an out-of-form passing record, are left
        out with _kept's findings and the evaluation goes on."""
        store = approved(Store())
        store.add('record.added', ci_record('ci-1'), 'r-1')
        store.add('record.added', ci_record('ci-1'), 'r-2')
        submitted(store)
        bad = dict(ci_record('ci-2'))
        del bad['recorder']
        r, writes, calls = evaluate(store, [bad])
        self.assertEqual((r['result'], writes, len(calls)), ('evaluated', ['decision.acceptance'], 1))
        self.assertEqual(len([f for f in r['findings'] if 'left out' in f]), 2, r['findings'])
        self.assertNotEqual(r['decision'], 'REJECT')


class R4Cost(unittest.TestCase):
    def test_refused_again_at_the_rerun_and_after_a_new_approval(self):
        """TASK-054 AC3, TASK-054 AC7: the rerun is refused again with nothing appended; after a new task.approved
        and a new submission it is refused again (the whole-log span)."""
        store = approved(Store())
        store.add('record.added', ci_record('obs-1'), 'r-1')
        store.add('violation.detected', observation('obs-1'), 'v-1')
        submitted(store)
        refused_by_records(self, *evaluate(store))
        refused_by_records(self, *evaluate(store))
        approved(store, eid='approved-2')
        submitted(store, eid='submitted-2')
        refused_by_records(self, *evaluate(store))

    def test_extra_records_refuse_only_while_given(self):
        """TASK-054 AC3, TASK-054 AC7: a blocking record given only through extra_records refuses while it is given;
        without it the same log is evaluated (the failing case)."""
        store = approved(Store())
        store.add('record.added', ci_record('ci-1'), 'r-1')
        submitted(store)
        refused_by_records(self, *evaluate(store, [observation('ci-1')]))
        r, writes, calls = evaluate(store)
        self.assertEqual((r['result'], len(calls)), ('evaluated', 1))


class R5Property(unittest.TestCase):
    def test_property_the_base_steps_without_a_hidden_blocking_record(self):
        """TASK-054 AC2, TASK-054 AC7: over generated logs and extra_records (fixed seeds, standard library only),
        with no blocking record left out, _kept gives the base's kept records and findings and no refusal, and the
        evaluation is not refused for "records"; with one (a violation reusing a passing record's id), it is."""
        for seed in range(40):
            rnd = random.Random(seed)
            store = approved(Store())
            for n in range(rnd.randint(0, 6)):
                pick = rnd.random()
                if pick < 0.4:
                    store.add('record.added', ci_record('ci-%d' % n), 'r-%d' % n)
                elif pick < 0.6:
                    store.add('record.added', ci_record('ci-%d' % rnd.randint(0, 2)), 'd-%d' % n)
                elif pick < 0.8:
                    store.add('violation.detected', observation('v-%d' % n), 'v-%d' % n)
                else:
                    store.add('violation.detected', observation('v-%d' % n), 'w-%d' % n)
            submitted(store)
            extra = [ci_record('x-%d' % n) for n in range(rnd.randint(0, 2))]
            payloads = evaluation._task_events(store.read_log, FS_ROOT, TASK)[5]
            kept, found, hidden = evaluation._kept(payloads, extra)
            self.assertEqual((kept, found), base_kept(payloads, extra), seed)
            self.assertEqual(hidden, [], seed)
            before = store.log
            r, _, _ = evaluate(store, extra)
            self.assertNotEqual(r['reason'], 'records', seed)
            store.log = before  # the decision just appended is set aside, so the task is evaluable again
            store.add('record.added', ci_record('p-%d' % seed), 'p-%d' % seed)
            store.add('violation.detected', observation('p-%d' % seed), 'q-%d' % seed)
            payloads = evaluation._task_events(store.read_log, FS_ROOT, TASK)[5]
            self.assertTrue(evaluation._kept(payloads, extra)[2], seed)
            refused_by_records(self, *evaluate(store, extra))


def code_tail(name):
    return (SRC / name).read_bytes().decode('utf-8').split('"""', 2)[2]


def docstring(name):
    return ' '.join(ast.get_docstring(ast.parse((SRC / name).read_bytes().decode('utf-8'))).split())


class R6Texts(unittest.TestCase):
    def test_code_unchanged_and_the_new_words(self):
        """TASK-054 AC4, TASK-054 AC7: violation.py, adapter.py and replay.py keep their base code after the module
        docstring (a one-byte change gives another hash); their docstrings state the new rule and its cost, and the
        old limit's words are absent."""
        for name, want in CODE_AT_BASE.items():
            self.assertEqual(hashlib.sha256(code_tail(name).encode('utf-8')).hexdigest(), want, name)
            changed = code_tail(name).replace('def ', 'def  ', 1)
            self.assertNotEqual(hashlib.sha256(changed.encode('utf-8')).hexdigest(), want, name)
            doc = docstring(name)
            for words in ('task TASK-054', 'reason "records"', 'with the same blocking_kind and subject',
                          'superseded by a new task'):
                self.assertIn(words, doc, name)
            for words in ('need not REJECT', 'a later task is to make this fail closed', 'an earlier kept record'):
                self.assertNotIn(words, doc, name)
        self.assertIn('every later evaluation of it reject', docstring('violation.py'))
        for name in ('adapter.py', 'replay.py'):
            self.assertIn('makes every later evaluation of the task reject (task TASK-053)', docstring(name))


class R7Script(unittest.TestCase):
    def test_evaluation_docstring_and_imports(self):
        """TASK-054 AC5, TASK-054 AC7, TASK-054 AC8: evaluation.py's docstring states the rule (item 7), the new reason
        in its result section and AC3's cost with AC8's limits in place of the old limit; its imports are the base's
        and it holds no assert."""
        tree = ast.parse((SRC / 'evaluation.py').read_bytes().decode('utf-8'))
        doc = ' '.join(ast.get_docstring(tree).split())
        for words in ('refuses the evaluation with reason "records" (task TASK-054 AC1',
                      'with the same blocking_kind and the same subject (erratum E1 to AC1',
                      'its position, counted from 1 over the log\'s records and then extra_records',
                      'a record with outcome fail whose record_id an earlier kept record has is not seen by the governor',
                      'store and records (the last added by task TASK-054)',
                      'until it is superseded by a new task', 'refuses only while it is given',
                      'event_id_of and the governor are unchanged', "records.py's uniqueness rule is unchanged",
                      'left out with a finding as before', 'the limits of task TASK-053 (its AC7) stand'):
            self.assertIn(words, doc)
        for words in ('need not REJECT', 'a later task is to make this fail closed'):
            self.assertNotIn(words, doc)
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                mods.update('%s.%s' % (node.module, a.name) for a in node.names)
        self.assertEqual(mods, {'datetime', 'hashlib', 'os', 're', 'aieos_bootstrap.gitread', 'aieos_bootstrap.governor',
                                'aieos_bootstrap.records', 'aieos_bootstrap.recovery', 'aieos_bootstrap.writer'})
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Assert)])
        self.assertIn('records', [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)])


class EndToEnd(unittest.TestCase):
    def test_violation_record_reusing_a_records_id_then_evaluation_refuses(self):
        """TASK-054 AC1, TASK-054 AC3, TASK-054 AC7: task.approved; a passing record.added; a first lease;
        violation.record whose observation reuses that record's record_id (violation.detected, the decision STOP:
        violation, the release); a second lease; a task.submitted; then evaluate_task gives "refused", "records"."""
        store = approved(Store())
        store.add('record.added', ci_record('obs-1'), 'r-1')
        store.lease = lease(FIRST)
        v = violation.record(FS_ROOT, TASK, dict(FIRST), observation('obs-1'), 'violation-1', HOOK, NOW,
                             append=store.append, release=store.release)
        self.assertEqual((v['result'], v['appended']), ('done', ['violation-1', 'violation-1/decision']))
        self.assertIsNone(store.lease)
        submitted(store, token=SECOND)
        refused_by_records(self, *evaluate(store))

    def test_the_same_run_with_a_fresh_id_rejects(self):
        """TASK-054 AC1, TASK-054 AC7: the same run with the violation under a fresh record_id gives REJECT (the
        failing case)."""
        store = approved(Store())
        store.add('record.added', ci_record('ci-1'), 'r-1')
        store.lease = lease(FIRST)
        violation.record(FS_ROOT, TASK, dict(FIRST), observation('obs-1'), 'violation-1', HOOK, NOW,
                         append=store.append, release=store.release)
        submitted(store, token=SECOND)
        r, writes, calls = evaluate(store)
        self.assertEqual((r['result'], r['decision'], writes), ('evaluated', 'REJECT', ['decision.acceptance']))


if __name__ == '__main__':
    unittest.main()

"""Unit and property tests of task TASK-055 (its rules R1 to R6 and an end-to-end test): a record that
records.check_record finds in form, whose outcome is 'fail' and which evaluation._kept leaves out for a record_id an
earlier kept record has, refuses the evaluation with reason "records", unless it equals that kept record as a whole
mapping; nothing is appended and the governor is not called. The Git reader and the writer's functions are stand-ins
bound to the real signatures, copied from test_evaluation_repeated.py (task TASK-054): the reader answers from a table
of commits, and the stand-in writer keeps a log as bytes, deciding each append with eventlog.append as the real writer
does, so no git starts and no file is touched here. Each test names the criteria it stands for in its own
docstring."""

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
TOKEN = {'epoch': 'e1', 'counter': 1}


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
    eventlog.append (the held lease on the task passed in); read_log gives the bytes."""

    def __init__(self):
        self.log = b''
        self.lease = None

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

    def add(self, event_type, payload, event_id, fencing_token=None):
        r = self.append(FS_ROOT, event_type, payload, event_id, NOW, REC, task_id=TASK, fencing_token=fencing_token)
        if r.result != 'appended':
            raise RuntimeError((r.result, r.findings))
        return self


def approved(store, eid='approved-1'):
    return store.add('task.approved', {'contract_version': 'v1', 'contract_hash': CHASH, 'approval_record': 'rec-a'},
                     eid)


def submitted(store, eid='submitted-1'):
    store.lease = {'task_id': TASK, 'fencing_token': dict(TOKEN), 'expires_at': LATER}
    return store.add('task.submitted', {'commit': cid(2), 'compensating': False}, eid, fencing_token=dict(TOKEN))


def ci(rid='ci-1', outcome='pass', commit=None):
    return {'record_id': rid, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_external_ci',
            'recorder': 'ci', 'subject': TASK, 'gate': 'G1', 'outcome': outcome, 'commit': commit or cid(2),
            'intent_versions': {'SPEC-001': 'v1'}}


def observation(rid='obs-1'):
    return {'record_id': rid, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
            'recorder': HOOK, 'subject': TASK, 'evidence_type': 'write_outside_write_set', 'outcome': 'blocking',
            'blocking_kind': 'violation', 'refers_to': 'src/outside.py'}


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


def payloads_of(store):
    return evaluation._task_events(store.read_log, FS_ROOT, TASK)[5]


def refused_by_records(test, r, writes, calls):
    test.assertEqual((r['result'], r['reason']), ('refused', 'records'), r['findings'])
    test.assertEqual((writes, calls), ([], []))
    test.assertIsNone(r['decision'])


def evaluated(test, r, writes, calls, decision):
    test.assertEqual((r['result'], r['decision'], writes, len(calls)),
                     ('evaluated', decision, ['decision.acceptance'], 1), r['findings'])


def log_with(*recs):
    store = approved(Store())
    for n, rec in enumerate(recs):
        store.add('record.added', rec, 'r-%d' % n)
    return submitted(store)


class R1Refused(unittest.TestCase):
    def test_a_pass_then_a_fail_with_one_record_id_refuses(self):
        """TASK-055 AC1, TASK-055 AC7: in the log, a passing record.added then an in-form 'fail' record.added with
        the same record_id gives "refused", reason "records"; nothing is appended and the governor is not called;
        the finding names the record_id and the source."""
        store = log_with(ci('ci-1'), ci('ci-1', 'fail'))
        r, writes, calls = evaluate(store)
        refused_by_records(self, r, writes, calls)
        self.assertTrue([f for f in r['findings'] if 'outcome fail' in f and "'ci-1'" in f and 'from log' in f],
                        r['findings'])
        self.assertTrue([f for f in r['findings'] if 'repeated' in f], r['findings'])

    def test_the_failing_case_without_the_rule_the_fail_is_hidden(self):
        """TASK-055 AC1, TASK-055 AC7: without the rule, the governor would see only the kept pass: the same log
        without the fail gives INSUFFICIENT_EVIDENCE, while the fail under a fresh record_id gives NEEDS_REWORK; so
        hiding the fail would change the decision."""
        store = log_with(ci('ci-1'), ci('ci-1', 'fail'))
        kept, found, hidden = evaluation._kept(payloads_of(store), [])
        self.assertEqual([(k['record_id'], k['outcome']) for k in kept], [('ci-1', 'pass')])
        self.assertEqual(len(found), 1)
        self.assertEqual(len(hidden), 1)
        evaluated(self, *evaluate(log_with(ci('ci-1'))), 'INSUFFICIENT_EVIDENCE')
        r, writes, calls = evaluate(log_with(ci('ci-1'), ci('ci-2', 'fail')))
        evaluated(self, r, writes, calls, 'NEEDS_REWORK')
        self.assertEqual(r['next_task_state'], 'REWORK')


class R2Extra(unittest.TestCase):
    def test_a_fail_in_extra_records_repeating_a_log_id_refuses(self):
        """TASK-055 AC1, TASK-055 AC7: a 'fail' in extra_records repeating a kept log record's id refuses, and the
        finding names extra_records."""
        store = log_with(ci('ci-1'))
        r, writes, calls = evaluate(store, [ci('ci-1', 'fail')])
        refused_by_records(self, r, writes, calls)
        self.assertTrue([f for f in r['findings'] if 'from extra_records' in f and "'ci-1'" in f], r['findings'])

    def test_a_fail_repeating_an_earlier_extra_record_refuses(self):
        """TASK-055 AC1, TASK-055 AC7: in extra_records alone, a pass then a fail with one record_id refuses."""
        store = log_with()
        refused_by_records(self, *evaluate(store, [ci('x-1'), ci('x-1', 'fail')]))

    def test_a_fail_differing_from_its_kept_fail_in_one_field_refuses(self):
        """TASK-055 AC1, TASK-055 AC7: a 'fail' left out after a kept 'fail' with the same record_id that differs in
        one field (the recorder) is not its whole-mapping twin, so it refuses."""
        store = log_with(ci('f-1', 'fail'))
        other = dict(ci('f-1', 'fail'), recorder='another ci')
        self.assertEqual(records.check_record(other), [])
        refused_by_records(self, *evaluate(store, [other]))


class R3GoesOn(unittest.TestCase):
    def test_a_fail_then_a_pass_goes_on_as_the_base(self):
        """TASK-055 AC2, TASK-055 AC7: a 'fail' then a 'pass' with one record_id: the fail is kept, the pass is left
        out with _kept's finding, and the evaluation goes on to NEEDS_REWORK."""
        r, writes, calls = evaluate(log_with(ci('ci-1', 'fail'), ci('ci-1')))
        evaluated(self, r, writes, calls, 'NEEDS_REWORK')
        self.assertTrue([f for f in r['findings'] if 'repeated' in f], r['findings'])
        self.assertEqual(r['event_id'], evaluation.event_id_of(TASK, 'submitted-1', ['ci-1']))

    def test_a_whole_mapping_twin_of_a_kept_fail_goes_on(self):
        """TASK-055 AC2, TASK-055 AC7: a 'fail' left out after a kept record equal to it as a whole mapping (in the
        log, and through extra_records) goes on to the same decision."""
        evaluated(self, *evaluate(log_with(ci('f-1', 'fail'), ci('f-1', 'fail'))), 'NEEDS_REWORK')
        evaluated(self, *evaluate(log_with(ci('f-1', 'fail')), [ci('f-1', 'fail')]), 'NEEDS_REWORK')

    def test_left_out_passes_and_out_of_form_records_do_not_refuse(self):
        """TASK-055 AC2, TASK-055 AC7: a left-out 'pass' repeating an id, and an out-of-form 'fail' that is not
        blocking, are left out with _kept's findings and the evaluation goes on."""
        bad = dict(ci('ci-9', 'fail'))
        del bad['recorder']
        self.assertTrue(records.check_record(bad))
        r, writes, calls = evaluate(log_with(ci('ci-1'), ci('ci-1')), [bad])
        evaluated(self, r, writes, calls, 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(len([f for f in r['findings'] if 'left out' in f]), 2, r['findings'])

    def test_a_left_out_blocking_record_still_refuses(self):
        """TASK-055 AC2, TASK-055 AC7: task TASK-054's rule is unchanged: a blocking record reusing a passing
        record's id refuses."""
        refused_by_records(self, *evaluate(log_with(ci('obs-1')), [observation('obs-1')]))


class R4Cost(unittest.TestCase):
    def test_refused_again_at_the_rerun_and_after_a_new_approval(self):
        """TASK-055 AC3, TASK-055 AC7: the rerun is refused again with nothing appended; after a new task.approved
        and a new submission it is refused again (the whole-log span)."""
        store = log_with(ci('ci-1'), ci('ci-1', 'fail'))
        refused_by_records(self, *evaluate(store))
        refused_by_records(self, *evaluate(store))
        approved(store, eid='approved-2')
        submitted(store, eid='submitted-2')
        refused_by_records(self, *evaluate(store))

    def test_a_stale_fail_refuses_too(self):
        """TASK-055 AC3, TASK-055 AC7: the over-refusal: a left-out 'fail' about another commit (stale for this
        evaluation) refuses too; under a fresh record_id the same record does not refuse (the failing case)."""
        refused_by_records(self, *evaluate(log_with(ci('ci-1'), ci('ci-1', 'fail', cid(9)))))
        r, writes, calls = evaluate(log_with(ci('ci-1'), ci('ci-2', 'fail', cid(9))))
        self.assertEqual((r['result'], len(calls)), ('evaluated', 1), r['findings'])

    def test_extra_records_refuse_only_while_given(self):
        """TASK-055 AC3, TASK-055 AC7: a 'fail' given only through extra_records refuses while it is given; without
        it the same log is evaluated."""
        store = log_with(ci('ci-1'))
        refused_by_records(self, *evaluate(store, [ci('ci-1', 'fail')]))
        r, writes, calls = evaluate(store)
        self.assertEqual((r['result'], len(calls)), ('evaluated', 1))


def expected(recs):
    """R5's own rule, written out here (not _kept): the kept record ids and whether a record left out is named by task
    TASK-054's rule (blocking, unless its twin by id, kind and subject is kept and blocking) or by task TASK-055's
    (in form, outcome fail, repeated id, not equal to the kept record)."""
    kept, refuse = {}, False
    for rec in recs:
        in_form = records.check_record(rec) == []
        rid = rec.get('record_id')
        if in_form and isinstance(rid, str) and rid not in kept:
            kept[rid] = rec
            continue
        if rec.get('outcome') == 'blocking':
            twin = kept.get(rid) if isinstance(rid, str) else None
            if not (twin and twin.get('outcome') == 'blocking' and
                    (twin.get('subject'), twin.get('blocking_kind')) == (rec.get('subject'), rec.get('blocking_kind'))):
                refuse = True
        elif in_form and rec.get('outcome') == 'fail' and rec != kept[rid]:
            refuse = True
    return list(kept), refuse


class R5Property(unittest.TestCase):
    def test_property_refused_exactly_when_a_record_is_hidden(self):
        """TASK-055 AC2, TASK-055 AC7: over generated logs and extra_records (fixed seeds, standard library only),
        with outcomes pass, fail and blocking, repeated ids and out-of-form records: _kept keeps the ids the rule
        written here keeps, and the evaluation is refused for "records" exactly when that rule names a hidden
        record; otherwise it is evaluated."""
        seen_refused = seen_evaluated = 0
        for seed in range(60):
            rnd = random.Random(seed)
            recs = []
            for n in range(rnd.randint(0, 6)):
                rid = 'id-%d' % rnd.randint(0, 3)
                pick = rnd.random()
                if pick < 0.4:
                    rec = ci(rid)
                elif pick < 0.75:
                    rec = ci(rid, 'fail', rnd.choice([None, cid(9)]))
                elif pick < 0.9:
                    rec = observation(rid)
                else:
                    rec = dict(ci(rid, rnd.choice(['pass', 'fail'])))
                    del rec['recorder']
                recs.append(rec)
            cut = rnd.randint(0, len(recs))
            store = approved(Store())
            for n, rec in enumerate(recs[:cut]):
                if records.check_record(rec) == []:
                    store.add('record.added', rec, 'r-%d' % n)
                else:
                    recs[n] = None
            submitted(store)
            log_part = [rec for rec in recs[:cut] if rec is not None]
            extra = recs[cut:]
            want_ids, want_refused = expected(log_part + extra)
            kept = evaluation._kept(payloads_of(store), extra)[0]
            self.assertEqual([k['record_id'] for k in kept], want_ids, seed)
            r, writes, calls = evaluate(store, extra)
            if want_refused:
                seen_refused += 1
                refused_by_records(self, r, writes, calls)
            else:
                seen_evaluated += 1
                self.assertEqual((r['result'], len(calls)), ('evaluated', 1), (seed, r['findings']))
        self.assertTrue(seen_refused and seen_evaluated, (seen_refused, seen_evaluated))


class R6Script(unittest.TestCase):
    def test_evaluation_docstring_and_imports(self):
        """TASK-055 AC4, TASK-055 AC5, TASK-055 AC7, TASK-055 AC8: evaluation.py's docstring and _kept's state the
        rule, the reused reason, the cost, the over-refusal and the limits, and the old limit's words are absent; its
        imports are the base's and it holds no assert."""
        tree = ast.parse((SRC / 'evaluation.py').read_bytes().decode('utf-8'))
        doc = ' '.join(ast.get_docstring(tree).split())
        for words in ('(task TASK-055 AC1; decision D-1040)', 'as a whole mapping',
                      "a 'pass' record then a 'fail' record with one record_id refuses",
                      "a 'fail' then a 'pass' goes on", 'which task TASK-055 also uses',
                      'Of task TASK-055 (its AC3 and AC8)', 'The rule over-refuses', 'refuses only while it is given',
                      "selected by the event envelope's task_id", 'the limits of task TASK-054 (its AC8) stand'):
            self.assertIn(words, doc)
        for words in ('a later task is to close this', 'is not seen by the governor', 'ACCEPT included'):
            self.assertNotIn(words, doc)
        kept_doc = ' '.join(ast.get_docstring(next(n for n in tree.body if getattr(n, 'name', '') == '_kept')).split())
        self.assertIn('task TASK-055 AC1', kept_doc)
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
    def test_a_fail_reusing_a_passing_records_id_then_evaluation_refuses(self):
        """TASK-055 AC1, TASK-055 AC3, TASK-055 AC7: through the real eventlog.append: task.approved, a passing
        record.added, a 'fail' record.added reusing its record_id, a lease and a task.submitted; then evaluate_task
        gives "refused", "records"."""
        store = approved(Store())
        store.add('record.added', ci('ci-1'), 'r-1')
        store.add('record.added', ci('ci-1', 'fail'), 'r-2')
        submitted(store)
        self.assertEqual([p['outcome'] for p in payloads_of(store)], ['pass', 'fail'])
        refused_by_records(self, *evaluate(store))

    def test_the_same_run_with_a_fresh_id_needs_rework(self):
        """TASK-055 AC1, TASK-055 AC7: the same run with the 'fail' under a fresh record_id gives NEEDS_REWORK (the
        failing case)."""
        store = approved(Store())
        store.add('record.added', ci('ci-1'), 'r-1')
        store.add('record.added', ci('ci-2', 'fail'), 'r-2')
        submitted(store)
        evaluated(self, *evaluate(store), 'NEEDS_REWORK')


if __name__ == '__main__':
    unittest.main()

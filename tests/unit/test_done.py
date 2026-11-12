"""Unit tests of aieos_bootstrap.done (task TASK-131 AC2, AC3, AC5; DEF-0119 option C). The writer's functions are
replaced by stand-ins: the stand-in keeps a log as bytes and decides each append with eventlog.append as the real
writer does, so no git starts and no file is touched here (the only file read is the module's own source, for the
purity checks). One test builds the whole chain from the existing functions: governor.evaluate with an approval record,
the log, done, execution.task_states and reconcile. Each test names the criteria it stands for in its docstring."""

import ast
import datetime
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import done
from aieos_bootstrap import eventlog
from aieos_bootstrap import execution
from aieos_bootstrap import governor
from aieos_bootstrap import reconcile
from aieos_bootstrap import records
from aieos_bootstrap import writer

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE = ROOT / 'src' / 'aieos_bootstrap' / 'done.py'
FS_ROOT = str(ROOT / 'no-such-state-root')
TASK = 'TASK-501'
REC = 'aieos-core'
NOW = datetime.datetime(2026, 11, 12, 10, 0, 0, tzinfo=datetime.timezone.utc)
FENCE = {'epoch': 'e0', 'counter': 1}
H1 = datetime.timedelta(hours=1)
COMMIT = 'a' * 40
HASH = 'c' * 64
EV = 'done-1'


class Log:
    """A stand-in writer: read_log gives the bytes, append decides with eventlog.append (no lease) and keeps the line."""

    def __init__(self):
        self.log = b''
        self.appends = []
        self.reads = 0
        self.n = 0

    def read_log(self, root):
        self.reads += 1
        return self.log

    def append(self, root, event_type, payload, event_id, appended_at, recorder, task_id=None, fencing_token=None):
        self.appends.append((event_type, event_id, task_id, fencing_token, payload))
        r = eventlog.append(self.log, event_type, payload, event_id, appended_at, task_id=task_id,
                            fencing_token=fencing_token, recorder=recorder)
        if r.result == 'appended':
            self.log += r.line
        return r

    def add(self, event_type, payload, task_id=TASK, fencing_token=None, lease=None):
        self.n += 1
        r = eventlog.append(self.log, event_type, payload, 'ev-%d' % self.n, NOW, task_id=task_id,
                            fencing_token=fencing_token, lease=lease)
        if r.result != 'appended':
            raise AssertionError((r.result, r.findings))
        self.log += r.line
        return self

    def approved(self):
        return self.add('task.approved', {'contract_version': 'v1', 'contract_hash': HASH, 'approval_record': 'appr-1'})

    def submitted(self):
        return self.add('task.submitted', {'commit': COMMIT, 'compensating': False}, fencing_token=FENCE,
                        lease={'task_id': TASK, 'fencing_token': FENCE, 'expires_at': NOW + H1})

    def decided(self, rid, verdict='ACCEPT', nxt='ACCEPTED', **over):
        d = {'record_id': rid, 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_local',
             'recorder': REC, 'subject': TASK, 'decision': verdict, 'evaluated_commit': COMMIT, 'next_task_state': nxt}
        d.update(over)
        return self.add('decision.acceptance', {k: v for k, v in d.items() if v is not None})

    def accepted(self, rid='dec-1'):
        return self.approved().submitted().decided(rid)

    def accepted_by_approval(self, rid='dec-1'):
        return self.approved().submitted().decided('dec-0', 'NEEDS_REVIEW', 'IN_REVIEW').decided(
            rid, 'NEEDS_REVIEW', 'ACCEPTED', approval_record='ap-1')


class Result:
    """A stand-in for the writer's WriteResult."""

    def __init__(self, result, reason=None, findings=()):
        self.result, self.reason, self.findings = result, reason, findings


def run(log, **kw):
    return done.done(FS_ROOT, TASK, EV, REC, NOW, read_log=log.read_log, append=log.append, **kw)


def state_of(log):
    states, found = execution.task_states(log.log, [TASK])
    assert found is None, found
    return states[TASK]['state']


class D1Arguments(unittest.TestCase):

    def test_each_wrong_argument_is_refused_before_any_read(self):
        """TASK-131 AC2, AC3: each wrong argument gives "refused", reason "argument", a finding naming it, and nothing
        read or appended."""
        good = dict(root=FS_ROOT, task_id=TASK, event_id=EV, recorder=REC, now=NOW)
        bad = [('root', ''), ('root', None), ('root', '  '), ('task_id', 'T-1'), ('task_id', 'TASK-'),
               ('task_id', 'TASK-1x'), ('task_id', None), ('event_id', ''), ('event_id', 5), ('recorder', ''),
               ('recorder', None), ('now', datetime.datetime(2026, 11, 12)),
               ('now', datetime.datetime(2026, 11, 12, tzinfo=datetime.timezone(datetime.timedelta(hours=7)))),
               ('now', NOW.replace(microsecond=5)), ('now', '2026-11-12')]
        for name, value in bad:
            log = Log().accepted()
            args = dict(good, **{name: value})
            res = done.done(read_log=log.read_log, append=log.append, **args)
            self.assertEqual((res['result'], res['reason']), ('refused', 'argument'), (name, value))
            self.assertTrue(any(name.split('_')[0] in f for f in res['findings']), (name, res['findings']))
            self.assertEqual((log.reads, log.appends), (0, []), name)
            self.assertEqual(set(res), done.RESULT_KEYS)

    def test_defaults_are_bound_at_call_time(self):
        """TASK-131 AC2: read_log and append default to writer.read_log and writer.append_event, bound at call time."""
        log = Log().accepted()
        with mock.patch.object(writer, 'read_log', log.read_log), mock.patch.object(writer, 'append_event', log.append):
            res = done.done(FS_ROOT, TASK, EV, REC, NOW)
        self.assertEqual(res['result'], 'done', res)
        self.assertEqual((log.reads, len(log.appends)), (1, 1))


class D2Log(unittest.TestCase):

    def test_a_log_with_a_finding_is_refused(self):
        """TASK-131 AC2: a log that records.check_log finds anything in gives "refused", reason "log", nothing appended."""
        log = Log().accepted()
        log.log += b'this is not a log line\n'
        res = run(log)
        self.assertEqual((res['result'], res['reason']), ('refused', 'log'), res)
        self.assertEqual(log.appends, [])

    def test_a_read_that_fails_or_is_not_bytes_is_refused(self):
        """TASK-131 AC2: read_log raising, or giving anything but bytes, gives "refused", reason "log"."""
        def boom(root):
            raise OSError('no')
        for reader in (boom, lambda root: 'text', lambda root: None):
            appends = []
            res = done.done(FS_ROOT, TASK, EV, REC, NOW, read_log=reader, append=lambda *a, **k: appends.append(a))
            self.assertEqual((res['result'], res['reason']), ('refused', 'log'), res)
            self.assertEqual(appends, [])


class D3State(unittest.TestCase):

    def test_every_state_but_accepted_is_refused_with_nothing_appended(self):
        """TASK-131 AC2, AC3: a task in DRAFT, READY, IN_PROGRESS, VERIFYING, IN_REVIEW, REWORK, ESCALATED, REJECTED,
        STALE or BLOCKED, or with no task.approved in the log, is refused with reason "state"."""
        def drafted(log):
            log.approved().add('task.drafted', {'contract_version': 'v2', 'contract_hash': HASH})
        cases = {
            'DRAFT': drafted,
            'READY': lambda log: log.approved(),
            'VERIFYING': lambda log: log.approved().submitted(),
            'IN_REVIEW': lambda log: log.approved().submitted().decided('d', 'NEEDS_REVIEW', 'IN_REVIEW'),
            'REWORK': lambda log: log.approved().submitted().decided('d', 'NEEDS_REWORK', 'REWORK'),
            'ESCALATED': lambda log: log.approved().submitted().decided('d', 'NEEDS_REWORK', 'ESCALATED'),
            'REJECTED': lambda log: log.approved().submitted().decided('d', 'REJECT', 'REJECTED'),
            'IN_PROGRESS': lambda log: log.approved().decided('d', 'NEEDS_REWORK', 'IN_PROGRESS'),
            'STALE': lambda log: log.approved().add('task.stale', {'cause': 'intent_change', 'refers_to': 'SPEC-001'}),
            'BLOCKED': lambda log: log.approved().add('task.blocked', {'reason': 'r', 'blocked_by': []}),
        }
        for want, build in cases.items():
            log = Log()
            build(log)
            self.assertEqual(state_of(log), want, want)
            res = run(log)
            self.assertEqual((res['result'], res['reason']), ('refused', 'state'), (want, res))
            self.assertEqual(log.appends, [], want)
        log = Log()
        log.decided('d')
        res = run(log)
        self.assertEqual((res['result'], res['reason']), ('refused', 'state'), res)
        self.assertEqual(log.appends, [])
        res = run(Log())
        self.assertEqual((res['result'], res['reason']), ('refused', 'state'), res)

    def test_a_done_task_with_another_record_is_refused(self):
        """TASK-131 AC2, AC3: a DONE task whose last task.done names another record than the last accepting
        decision.acceptance is refused with reason "state" and nothing appended."""
        log = Log().accepted('dec-1').add('task.done', {'decision_record': 'dec-other'})
        self.assertEqual(state_of(log), 'DONE')
        res = run(log)
        self.assertEqual((res['result'], res['reason']), ('refused', 'state'), res)
        self.assertEqual(log.appends, [])


class D4Record(unittest.TestCase):

    def test_a_last_record_that_does_not_accept_is_refused(self):
        """TASK-131 AC2, AC3: ACCEPTED by a last decision.acceptance that reconcile.accepts refuses (NEEDS_REVIEW
        with next_task_state ACCEPTED and no approval record) is refused with reason "record"."""
        log = Log().accepted('dec-1').decided('dec-2', 'NEEDS_REVIEW', 'ACCEPTED')
        self.assertEqual(state_of(log), 'ACCEPTED')
        res = run(log)
        self.assertEqual((res['result'], res['reason']), ('refused', 'record'), res)
        self.assertEqual(log.appends, [])

    def test_an_accepting_record_without_a_commit_is_refused(self):
        """TASK-131 AC2, AC3: an accepting record with no evaluated_commit is refused with reason "record"."""
        log = Log().approved().submitted().decided('dec-1', evaluated_commit=None)
        self.assertEqual(state_of(log), 'ACCEPTED')
        res = run(log)
        self.assertEqual((res['result'], res['reason']), ('refused', 'record'), res)
        self.assertEqual(log.appends, [])

    def test_the_last_decision_after_the_last_approval_is_the_one_named(self):
        """TASK-131 AC2: the record named is the task's last decision.acceptance after its last task.approved, not an
        earlier one and not one of an earlier cycle."""
        log = Log().approved().submitted().decided('dec-1', 'NEEDS_REWORK', 'REWORK').decided('dec-2')
        res = run(log)
        self.assertEqual(res['result'], 'done', res)
        self.assertEqual(log.appends[-1][4], {'decision_record': 'dec-2'})
        cycle = Log().accepted('dec-1').add('task.done', {'decision_record': 'dec-1'})
        cycle.add('task.stale', {'cause': 'intent_change', 'refers_to': 'SPEC-001'})
        cycle.add('task.replanned', {'contract_version': 'v2', 'contract_hash': HASH}).approved()
        cycle.submitted().decided('dec-3')
        self.assertEqual(state_of(cycle), 'ACCEPTED')
        res = run(cycle)
        self.assertEqual(res['result'], 'done', res)
        self.assertEqual(cycle.appends[-1][4], {'decision_record': 'dec-3'})


class D5Append(unittest.TestCase):

    def test_an_accepted_task_gets_one_task_done_with_the_exact_payload(self):
        """TASK-131 AC2, AC3: an ACCEPTED task, by an ACCEPT record or by a NEEDS_REVIEW record with an approval
        record, gets exactly one task.done event {decision_record: record_id}, with the task id and no fencing token,
        and the projection then gives DONE."""
        for build in (lambda: Log().accepted('dec-1'), lambda: Log().accepted_by_approval('dec-1')):
            log = build()
            self.assertEqual(state_of(log), 'ACCEPTED')
            res = run(log)
            self.assertEqual((res['result'], res['reason'], res['findings']), ('done', None, []), res)
            self.assertEqual(set(res), done.RESULT_KEYS)
            self.assertEqual(log.appends, [('task.done', EV, TASK, None, {'decision_record': 'dec-1'})])
            self.assertEqual(state_of(log), 'DONE')

    def test_a_second_call_gives_duplicate_and_appends_nothing(self):
        """TASK-131 AC2, AC3: after task.done the same call, or one with another event id, gives "duplicate" and
        appends nothing."""
        log = Log().accepted('dec-1')
        self.assertEqual(run(log)['result'], 'done')
        n = len(log.appends)
        for ev in (EV, 'done-2'):
            res = done.done(FS_ROOT, TASK, ev, REC, NOW, read_log=log.read_log, append=log.append)
            self.assertEqual((res['result'], res['reason']), ('duplicate', None), res)
        self.assertEqual(len(log.appends), n)

    def test_the_writer_is_asked_once_and_its_outcome_is_taken_as_given(self):
        """TASK-131 AC2, AC3: an append that raises, a result that raises when read, a refusal and a duplicate of the
        writer each give a result, none escapes."""
        log = Log().accepted('dec-1')

        def boom(*a, **k):
            raise RuntimeError('no')

        class Odd:
            @property
            def result(self):
                raise RuntimeError('no')
        for append, want in ((boom, ('refused', 'store')), (lambda *a, **k: Odd(), ('refused', 'store')),
                             (lambda *a, **k: Result('refused', 'fence', ['f1']), ('refused', 'fence')),
                             (lambda *a, **k: Result('refused', None, []), ('refused', 'store')),
                             (lambda *a, **k: Result('duplicate'), ('duplicate', None)),
                             (lambda *a, **k: Result('appended'), ('done', None))):
            res = done.done(FS_ROOT, TASK, EV, REC, NOW, read_log=log.read_log, append=append)
            self.assertEqual((res['result'], res['reason']), want, res)
        res = done.done(FS_ROOT, TASK, EV, REC, NOW, read_log=log.read_log,
                        append=lambda *a, **k: Result('refused', 'fence', 'one string'))
        self.assertEqual((res['result'], res['reason']), ('refused', 'store'), res)


def request(**changes):
    r = {'task_id': TASK, 'task_content_hash': HASH, 'evaluated_commit': COMMIT, 'intent_versions': {'SPEC-001': 'v2'},
         'task_state': 'IN_REVIEW', 'changed_paths': ['src/x.py'], 'retry_count': {'used': 0, 'limit': 2}}
    r.update(changes)
    return r


def inputs():
    return {'traces_to': ['SPEC-001'], 'risk': 'low', 'owner_kept_act': False, 'weakens_evidence': False,
            'delegation_in_force': True, 'auto_accept': False, 'verification_plan': ['G0', 'G1'],
            'evidence_profile': [{'dimension': 'functional', 'evidence_types': ['build']}], 'applicable_articles': [],
            'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1'}


def evidence(rid, **fields):
    r = {'record_id': rid, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_external_ci',
         'recorder': 'external CI', 'subject': TASK, 'commit': COMMIT, 'intent_versions': {'SPEC-001': 'v2'},
         'outcome': 'pass'}
    r.update(fields)
    return {k: v for k, v in r.items() if v is not None}


def governor_records():
    approval = evidence('ap', fact_kind='authority', source_class='human_authority', recorder='an approver',
                        commit=None, intent_versions=None, outcome=None,
                        approval_binding={'kind': 'acceptance', 'hash': HASH})
    return [evidence('g0', gate='G0', evidence_type='scope_check', dimension='scope'),
            evidence('g1', gate='G1', evidence_type='build', dimension='functional'), approval]


class D6Chain(unittest.TestCase):

    def test_the_whole_chain_of_the_existing_functions(self):
        """TASK-131 AC3: governor.evaluate at a re-evaluation with an approval record that counts gives NEEDS_REVIEW,
        next_task_state ACCEPTED and approval_record; that record in the log makes the task ACCEPTED; done appends
        task.done; execution.task_states gives DONE; reconcile reads the task's accepted commit from the record."""
        out = governor.evaluate(request(), inputs(), governor_records())
        self.assertEqual((out['decision'], out['next_task_state'], out['approval_record']),
                         ('NEEDS_REVIEW', 'ACCEPTED', 'ap'))
        self.assertTrue(reconcile.accepts(out))
        log = Log().approved().submitted()
        log.add('decision.acceptance', out)
        self.assertEqual(state_of(log), 'ACCEPTED')
        res = run(log)
        self.assertEqual(res['result'], 'done', res)
        self.assertEqual(log.appends[-1][4], {'decision_record': out['record_id']})
        self.assertEqual(state_of(log), 'DONE')
        report = records.check_log(log.log)
        self.assertEqual(list(report.findings()), [])
        events = [line.event for line in report.lines if line.duplicate_of is None]
        uncovered = []
        self.assertEqual(reconcile._done_tasks(events, uncovered), {TASK: COMMIT})
        self.assertEqual(uncovered, [])


def purity_findings(source):
    """What the purity rule of TASK-131 AC5 finds in a module's source text."""
    tree = ast.parse(source)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in (
                'open', 'exec', 'eval', 'compile', '__import__', 'print', 'input'):
            found.append('name ' + node.func.id)
        if isinstance(node, ast.Attribute) and node.attr in ('now', 'utcnow', 'today', 'environ', 'getenv', 'system',
                                                              'Popen', 'run', 'urlopen', 'open', 'time'):
            found.append('attribute ' + node.attr)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and (
                node.value in ('valid', 'accepted', 'approved') or '.aie' + 'os' in node.value):
            found.append('string ' + node.value)
        if isinstance(node, ast.Assert):
            found.append('assert')
    for word in ('MEASURED', 'ENFORCED', 'GUARANTEED'):
        if word in source:
            found.append('word ' + word)
    return found


class D7Purity(unittest.TestCase):

    def test_the_imports_are_the_allowed_ones(self):
        """TASK-131 AC5: done.py imports only the standard library modules datetime and re and the four project modules
        execution, reconcile, records and writer."""
        tree = ast.parse(MODULE.read_text(encoding='utf-8'))
        mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        mods |= {'%s.%s' % (n.module, a.name) for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                 for a in n.names}
        self.assertEqual(mods, {'datetime', 're', 'aieos_bootstrap.execution', 'aieos_bootstrap.reconcile',
                                'aieos_bootstrap.records', 'aieos_bootstrap.writer'})

    def test_the_module_is_pure(self):
        """TASK-131 AC5: no file, process, clock or environment access, no assert, no forbidden word or string."""
        self.assertEqual(purity_findings(MODULE.read_text(encoding='utf-8')), [])

    def test_the_purity_check_catches_seeded_calls(self):
        """TASK-131 AC5: the same check reports an open call, a clock call, a process call, an assert, a forbidden
        string and a forbidden word seeded into the module's source."""
        base = MODULE.read_text(encoding='utf-8')
        seeds = {'\nopen("x")\n': 'name open', '\ndatetime.datetime.now()\n': 'attribute now',
                 '\nimport subprocess\nsubprocess.run(["x"])\n': 'attribute run', '\nassert True\n': 'assert',
                 '\nX = "accepted"\n': 'string accepted', '\nX = "' + '.aie' + 'os/x"\n': 'string',
                 '\n# MEASURED\n': 'word MEASURED'}
        for seed, want in seeds.items():
            self.assertTrue(any(want in f for f in purity_findings(base + seed)), seed)

    def test_the_docstring_names_the_limits(self):
        """TASK-131 AC2, AC7: the docstring names TASK-131, DEF-0119 and its limits."""
        doc = ast.get_docstring(ast.parse(MODULE.read_text(encoding='utf-8')))
        for word in ('TASK-131', 'DEF-0119', 'not wired into the CLI', 'accepted commit is on the base branch',
                     're-runs the governor', 'One run at a time'):
            self.assertIn(word, doc)


if __name__ == '__main__':
    unittest.main()

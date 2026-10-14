"""Integration test of aieos_bootstrap.execution (task TASK-032 AC13): end-to-end runs of the real resume_check.check
over inputs built in the test, with the event log kept in memory and appended by eventlog.append, as the writer
decides it, and an in-memory stand-in store that grants, releases and holds leases by the writer's rules. No process
starts and no file is opened. Each test names its criteria in its own docstring."""

import datetime
import unittest

from aieos_bootstrap import eventlog
from aieos_bootstrap import execution
from aieos_bootstrap import records
from aieos_bootstrap import writer

ROOT = 'C:/a-root'
TASK = 'TASK-100'
H = 'a' * 64
CODE = 'c' * 64
BASE = '1' * 40
HEAD = '2' * 40
COMMIT = '3' * 40
NOW = datetime.datetime(2026, 10, 14, 12, 0, 0, tzinfo=datetime.timezone.utc)
LATER = NOW + datetime.timedelta(hours=1)
REC = 'aieos-core (integration)'
REQ = {'holder': 'agent-1', 'session_id': 'session-1', 'expires_at': LATER}


class Memory:
    """The event log as bytes in memory; append decides with eventlog.append as the real writer does."""

    def __init__(self):
        self.log = b''
        self.seq = 0

    def read_log(self, root):
        return self.log

    def append(self, root, event_type, payload, event_id, appended_at, recorder, task_id=None):
        r = eventlog.append(self.log, event_type, payload, event_id, appended_at, task_id=task_id, recorder=recorder)
        if r.result == 'appended':
            self.log += r.line
            self.seq = r.seq
        return writer.WriteResult(r)

    def add(self, event_type, payload, event_id, task_id=TASK):
        r = eventlog.append(self.log, event_type, payload, event_id, NOW, task_id=task_id)
        if r.result != 'appended':
            raise AssertionError(r.findings)
        self.log += r.line
        self.seq = r.seq

    def types(self):
        return [line.event['type'] for line in records.check_log(self.log).lines]


class Store:
    """The local store's leases and sessions in memory, by writer.grant_lease's and release_lease_token's rules."""

    def __init__(self, sessions=(('session-1', 'agent-1'),)):
        self.sessions = dict(sessions)
        self.leases = {}
        self.counter = 0

    def grant(self, root, task_id, task_state, holder, session_id, now, expires_at):
        if task_state not in writer.GRANT_STATES:
            return writer.StoreResult('refused', 'state', ['not READY or REWORK'])
        if not expires_at > now:
            return writer.StoreResult('refused', 'expiry', ['expires_at is not after now'])
        if task_id in self.leases:
            return writer.StoreResult('refused', 'held', ['a lease on %s is held' % task_id])
        if self.sessions.get(session_id) != holder:
            return writer.StoreResult('refused', 'session', ['the session is not a started session of the holder'])
        self.counter += 1
        self.leases[task_id] = {'task_id': task_id, 'fencing_token': {'epoch': 'e1', 'counter': self.counter},
                                'expires_at': expires_at}
        return writer.StoreResult('done', value=dict(self.leases[task_id]))

    def release(self, root, task_id, fencing_token):
        lease = self.leases.get(task_id)
        if lease is None:
            return writer.StoreResult('refused', 'none', ['no lease is held'])
        if lease['fencing_token'] != fencing_token:
            return writer.StoreResult('refused', 'token', ['another token is held'])
        return writer.StoreResult('done', value=self.leases.pop(task_id))

    def held(self, root, task_id):
        lease = self.leases.get(task_id)
        return dict(lease) if lease else None


def inputs(mem, task_state, **over):
    """Well-formed Resume Check inputs whose checks all pass (CONTINUE), agreeing with the log."""
    inp = {
        'task_id': TASK, 'log_seq': mem.seq, 'task_state': task_state,
        'contract': {
            'task': TASK, 'contract_version': 'v1', 'task_type': 'implementation', 'risk': 'medium',
            'input_state': {'base_commit': BASE, 'depends_on': ['TASK-099'], 'intent_versions': {'SPEC-003': 'v4'}},
            'write_set': {'paths': ['src/app/core/**']},
            'read_set': {'paths': ['src/app/util/helpers.py'], 'interfaces': ['load_policy'], 'schemas': ['record']},
            'constitution': ['INV-001'],
            'autonomy': {'budgets': {'retries': 2, 'tokens': '400k', 'wall_time': '2h', 'human_attention': '10m'}}},
        'contract_hash': H, 'approved_contract_hash': H, 'head_commit': HEAD, 'base_is_ancestor': True,
        'commits': [{'id': COMMIT, 'paths': [{'path': 'docs/notes.md', 'change': 'modified'}], 'submitted': False}],
        'components': [{'id': 'CMP-API', 'paths': ['src/app/api/**'], 'tags': []},
                       {'id': 'CMP-CORE', 'paths': ['src/app/core'], 'tags': []}],
        'interfaces': [{'id': 'load_policy', 'component': 'CMP-API'}],
        'symbols': [{'interface': 'load_policy', 'base': 'F(a)', 'head': 'F(a)'}],
        'schemas': [{'name': 'record', 'base': {'path': 'src/app/api/record.json', 'sha256': 'b' * 64},
                     'head': {'path': 'src/app/api/record.json', 'sha256': 'b' * 64}}],
        'derived_read_set': [], 'observed_read_set': [],
        'intent_current': {'SPEC-003': 'v4'},
        'dependencies': {'TASK-099': {'state': 'DONE', 'stale_evidence': False}},
        'articles': [{'id': 'INV-001', 'scope': {'paths': ['src/**'], 'components': []},
                      'applicability': {'task_types': ['implementation']}, 'violated': False}],
        'runtime': {'adapter': 'an-adapter', 'max_risk': 'high'},
        'risk_rules': [{'match': {'paths': ['src/**']}, 'risk': 'medium'}],
        'policy_version': 'v2',
        'budget_use': {'retries': {'used': 0, 'reported': True}, 'tokens': {'used': '10k', 'reported': True},
                       'wall_time': {'used': '10m', 'reported': True}, 'human_attention': {'used': '0m', 'reported': True}},
    }
    inp.update(over)
    return inp


def approved():
    mem = Memory()
    mem.add('task.drafted', {'contract_version': 'v1', 'contract_hash': H}, 'drafted-1')
    mem.add('task.approved', {'contract_version': 'v1', 'contract_hash': H, 'approval_record': 'appr-1'}, 'approved-1')
    return mem


def run(mem, store, inp, request=REQ):
    return execution.execute(ROOT, TASK, inp, CODE, request, REC, NOW, read_log=mem.read_log, append=mem.append,
                             grant=store.grant, release=store.release, held=store.held)


class EndToEnd(unittest.TestCase):
    def test_continue_grants_then_a_new_session_keeps_the_lease(self):
        """TASK-032 AC2, AC3, AC6, AC7, AC9: CONTINUE on a READY task appends the record and grants the lease; the
        next session's Resume Check on the task, now IN_PROGRESS, appends a new record and keeps the lease."""
        mem, store = approved(), Store()
        r = run(mem, store, inputs(mem, 'READY'))
        self.assertEqual((r['result'], r['decision'], r['appended']), ('decided', 'CONTINUE', [r['record_id']]))
        self.assertEqual(store.leases[TASK], r['lease'])
        first = r['record_id']
        r = run(mem, store, inputs(mem, 'IN_PROGRESS'))
        self.assertEqual((r['result'], r['decision'], r['lease'], r['released']),
                         ('decided', 'CONTINUE', store.leases[TASK], None))
        self.assertNotEqual(r['record_id'], first)
        self.assertEqual(mem.types()[-2:], ['decision.execution', 'decision.execution'])
        self.assertEqual(list(records.check_log(mem.log).findings()), [])

    def test_blocked_from_in_progress_releases_first(self):
        """TASK-032 AC5, AC6, AC7: BLOCKED on a task IN_PROGRESS releases the lease, then appends the record and
        task.blocked; the task is then BLOCKED and holds no lease."""
        mem, store = approved(), Store()
        run(mem, store, inputs(mem, 'READY'))
        r = run(mem, store, inputs(mem, 'IN_PROGRESS', dependencies={}))
        self.assertEqual((r['result'], r['decision']), ('decided', 'BLOCKED'))
        self.assertEqual(store.leases, {})
        self.assertEqual(r['released']['task_id'], TASK)
        self.assertEqual(mem.types()[-2:], ['decision.execution', 'task.blocked'])
        r = run(mem, store, inputs(mem, 'BLOCKED'))
        self.assertEqual((r['result'], r['reason']), ('refused', 'state'))

    def test_replan_on_ready_appends_the_conflict_only(self):
        """TASK-032 AC8: REPLAN on a READY task appends the record and conflict.detected, no task.stale and no lease
        (point (i))."""
        mem, store = approved(), Store()
        over = {'commits': [{'id': COMMIT, 'paths': [{'path': 'src/app/api/policy.py', 'change': 'modified'}],
                             'submitted': False}],
                'symbols': [{'interface': 'load_policy', 'base': 'F', 'head': 'G'}]}
        r = run(mem, store, inputs(mem, 'READY', **over))
        self.assertEqual((r['result'], r['decision'], r['lease']), ('decided', 'REPLAN', None))
        self.assertEqual(mem.types()[-2:], ['decision.execution', 'conflict.detected'])
        self.assertEqual(store.leases, {})

    def test_a_store_refusal_leaves_the_record(self):
        """TASK-032 AC7: a session that is not started makes the grant refused with "session"; the record stays."""
        mem, store = approved(), Store(sessions=())
        r = run(mem, store, inputs(mem, 'READY'))
        self.assertEqual((r['result'], r['reason']), ('refused', 'lease'))
        self.assertIn('lease: grant_lease refused it (session)', r['findings'])
        self.assertEqual(mem.types()[-1], 'decision.execution')
        self.assertEqual(store.leases, {})

    def test_the_appended_record_is_the_checks_record(self):
        """TASK-032 AC6: the decision.execution payload is the check's record unchanged, and the decision contract
        check finds nothing in it."""
        mem, store = approved(), Store()
        r = run(mem, store, inputs(mem, 'READY'))
        last = records.check_log(mem.log).lines[-1].event
        self.assertEqual((last['type'], last['event_id'], last['payload']['record_id']),
                         ('decision.execution', r['record_id'], r['record_id']))
        self.assertEqual(records.check_decision('decision.execution', last['payload']), [])

    def test_a_rerun_after_an_append_is_refused(self):
        """TASK-032 AC3, AC6: the same inputs again after the first run's appends give "inputs" and append nothing."""
        mem, store = approved(), Store()
        inp = inputs(mem, 'READY', dependencies={})
        self.assertEqual(run(mem, store, inp)['decision'], 'BLOCKED')
        before = mem.log
        r = run(mem, store, inp)
        self.assertEqual((r['result'], r['reason']), ('refused', 'inputs'))
        self.assertEqual(mem.log, before)


if __name__ == '__main__':
    unittest.main()

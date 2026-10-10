"""Integration test of aieos_bootstrap.eventlog (TASK-007 AC12): a log with every event type of specification 2
section 6.3, built in memory by successive appends, checked with records.check_log, and a retried append of each event
replayed to show that it changes nothing."""

import datetime
import unittest

from aieos_bootstrap import eventlog, records

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 10, 12, 0, 0, tzinfo=UTC)
H64 = '0123456789abcdef' * 4
C40 = 'fedcba9876543210fedcba9876543210fedcba98'
TASK = 'TASK-001'
TOKEN = {'epoch': 'store-1', 'counter': 1}
LEASE = {'task_id': TASK, 'fencing_token': TOKEN, 'expires_at': T0 + datetime.timedelta(days=1)}


def record(**fields):
    r = {'record_id': 'rec-0', 'fact_kind': 'observation', 'source_class': 'deterministic_tool_external_ci',
         'recorder': 'aieos-checks', 'subject': TASK}
    r.update(fields)
    return r


# (type, payload, keyword arguments of append); event ids are ev-1, ev-2 and so on, in this order.
EVENTS = [
    ('task.drafted', {'contract_version': 'v1', 'contract_hash': H64}, {'task_id': TASK}),
    ('record.added', record(record_id='rec-1', fact_kind='authority', source_class='decision_agent',
                            recorder='aieos-decider', decision_ref='D-186',
                            approval_binding={'kind': 'contract', 'hash': H64}), {'task_id': TASK}),
    ('task.approved', {'contract_version': 'v1', 'contract_hash': H64, 'approval_record': 'rec-1'}, {'task_id': TASK}),
    ('task.blocked', {'reason': 'dependency', 'blocked_by': ['TASK-000']}, {'task_id': TASK}),
    ('task.unblocked', {'reason': 'TASK-000 is done'}, {'task_id': TASK}),
    ('task.submitted', {'commit': C40, 'compensating': False},
     {'task_id': TASK, 'fencing_token': TOKEN, 'lease': LEASE, 'recorder': 'aieos-core', 'record_id': 'rec-x'}),
    ('record.added', record(record_id='rec-2', evidence_type='unit_test', dimension='architecture', gate='G2',
                            outcome='pass', commit=C40, intent_versions={'SPEC-002': 'v1'}), {'task_id': TASK}),
    ('decision.execution', record(record_id='rec-3', fact_kind='interpretation', recorder='governor',
                                  decision='CONTINUE'), {'task_id': TASK}),
    ('decision.acceptance', record(record_id='rec-4', fact_kind='interpretation', recorder='governor',
                                   decision='ACCEPT', task_content_hash=H64, evaluated_commit=C40,
                                   intent_versions={'SPEC-002': 'v1'}, next_task_state='ACCEPTED'), {'task_id': TASK}),
    ('task.done', {'decision_record': 'rec-4'}, {'task_id': TASK}),
    ('intent.changed', {'entity': 'SPEC-002', 'from_version': 'v1', 'to_version': 'v2', 'change_request': 'CHG-001'},
     {}),
    ('task.stale', {'cause': 'intent_change', 'refers_to': 'ev-11'}, {'task_id': TASK}),
    ('task.replanned', {'contract_version': 'v2', 'contract_hash': H64}, {'task_id': TASK}),
    ('drift.detected', {'paths': ['src/aieos_bootstrap/records.py'], 'entities': ['SPEC-002']}, {}),
    ('violation.detected', record(record_id='rec-5', outcome='blocking', blocking_kind='violation',
                                  refers_to='ev-14'), {'task_id': TASK}),
    ('evidence.stale', {'records': ['rec-2'], 'reason': 'intent_version'}, {}),
    ('conflict.detected', {'tasks': [TASK, 'TASK-002'], 'paths': ['src/a.py']}, {}),
    ('record.added', record(record_id='rec-6', subject='SPEC-002', evidence_type='baseline_note'), {}),
    ('task.drafted', {'contract_version': 'v2', 'contract_hash': H64}, {'task_id': TASK, 'corrects': 'ev-1'}),
]


def build():
    log = b''
    for n, (etype, payload, kw) in enumerate(EVENTS, 1):
        r = eventlog.append(log, etype, payload, 'ev-%d' % n, T0 + datetime.timedelta(minutes=n), **kw)
        assert r.result == 'appended' and r.seq == n, (n, r)
        log = r.log
    return log


class WholeLog(unittest.TestCase):

    def test_every_event_type_is_present(self):
        self.assertEqual({etype for etype, _, _ in EVENTS}, set(records.EVENT_TYPES))

    def test_built_log_has_no_finding(self):
        log = build()
        report = records.check_log(log)
        self.assertEqual(report.findings(), [])
        self.assertEqual([line.event['seq'] for line in report.lines], list(range(1, len(EVENTS) + 1)))
        self.assertEqual(len(set(line.event['event_id'] for line in report.lines)), len(EVENTS))

    def test_a_retried_append_of_each_event_changes_nothing(self):
        log = build()
        for n, (etype, payload, kw) in enumerate(EVENTS, 1):
            r = eventlog.append(log, etype, payload, 'ev-%d' % n, T0 + datetime.timedelta(days=2), **kw)
            self.assertEqual((r.result, r.seq, r.log), ('duplicate', n, None), n)
        self.assertEqual(records.check_log(log).findings(), [])

    def test_a_refused_submission_is_recorded_by_one_more_append(self):
        log = build()
        stale = dict(LEASE, expires_at=T0)
        r = eventlog.append(log, 'task.submitted', {'commit': C40, 'compensating': False}, 'ev-late', T0 +
                            datetime.timedelta(hours=1), task_id=TASK, fencing_token=TOKEN, lease=stale,
                            recorder='aieos-core', record_id='rec-refused')
        self.assertEqual((r.result, r.reason), ('refused', 'fence'))
        r2 = eventlog.append(log, 'record.added', r.record, 'ev-obs', T0 + datetime.timedelta(hours=1), task_id=TASK)
        self.assertEqual(r2.result, 'appended')
        self.assertEqual(r2.log[:len(log)], log)
        self.assertEqual(records.check_log(r2.log).findings(), [])
        self.assertNotIn(b'"ev-late"', r2.log.replace(b'"refers_to":"ev-late"', b''))


if __name__ == '__main__':
    unittest.main()

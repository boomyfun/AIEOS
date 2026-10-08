"""Integration test of aieos_bootstrap.records (TASK-001 AC9): one log, held here, with every event type of
specification 2 section 6.3 at least once, checked end to end."""

import json
import unittest

from aieos_bootstrap import records

H64 = '0123456789abcdef' * 4
C40 = 'fedcba9876543210fedcba9876543210fedcba98'
TASK = 'TASK-001'


def record(**fields):
    r = {'record_id': 'rec-0', 'fact_kind': 'observation', 'source_class': 'deterministic_tool_external_ci',
         'recorder': 'aieos-checks', 'subject': TASK}
    r.update(fields)
    return r


EVENTS = [
    ('task.drafted', {'contract_version': 'v1', 'contract_hash': H64}, {'task_id': TASK}),
    ('record.added', record(record_id='rec-1', fact_kind='authority', source_class='decision_agent',
                            recorder='aieos-decider', decision_ref='D-186',
                            approval_binding={'kind': 'contract', 'hash': H64}), {'task_id': TASK}),
    ('task.approved', {'contract_version': 'v1', 'contract_hash': H64, 'approval_record': 'rec-1'}, {'task_id': TASK}),
    ('task.blocked', {'reason': 'waiting for TASK-000', 'blocked_by': ['TASK-000']}, {'task_id': TASK}),
    ('task.unblocked', {'reason': 'TASK-000 is done'}, {'task_id': TASK}),
    ('task.submitted', {'commit': C40, 'compensating': False},
     {'task_id': TASK, 'fencing_token': {'epoch': 'store-1', 'counter': 1}}),
    ('record.added', record(record_id='rec-2', evidence_type='unit_test', dimension='architecture', gate='G2',
                            outcome='pass', commit=C40, intent_versions={'SPEC-002': 'v1'}), {'task_id': TASK}),
    ('record.added', record(record_id='rec-3', source_class='same_lineage_review', recorder='reviewer-agent',
                            evidence_type='other_model_review', dimension='security', outcome='pass', commit=C40,
                            decision_ref='D-188', models={'reviewer': 'model-r', 'implementer': 'model-i'}),
     {'task_id': TASK}),
    ('record.added', record(record_id='rec-4', source_class='decision_agent', recorder='aieos-decider',
                            evidence_type='decision_agent_review', dimension='architecture', outcome='pass',
                            commit=C40, decision_ref='D-188', basis=['the diff', 'rec-3'], stands_for='human_review'),
     {'task_id': TASK}),
    ('decision.execution', record(record_id='rec-5', fact_kind='interpretation', recorder='governor',
                                  decision='CONTINUE'), {'task_id': TASK}),
    ('decision.acceptance', record(record_id='rec-6', fact_kind='interpretation', recorder='governor',
                                   decision='ACCEPT', task_content_hash=H64, evaluated_commit=C40,
                                   intent_versions={'SPEC-002': 'v1'}, next_task_state='ACCEPTED',
                                   profile_used=[{'dimension': 'architecture', 'required': ['unit_test'],
                                                  'satisfied_by': ['rec-2'], 'missing_types': []}],
                                   missing_gates=[], blocking=[], failed_gates=[], approval_record='rec-1',
                                   uncovered=['INV-005'], rests_on_ai=['rec-3', 'rec-4']), {'task_id': TASK}),
    ('task.done', {'decision_record': 'rec-6'}, {'task_id': TASK}),
    ('intent.changed', {'entity': 'SPEC-002', 'from_version': 'v1', 'to_version': 'v2', 'change_request': 'CHG-001'},
     {}),
    ('task.stale', {'cause': 'intent_change', 'refers_to': 'ev-13'}, {'task_id': TASK}),
    ('task.replanned', {'contract_version': 'v2', 'contract_hash': H64}, {'task_id': TASK}),
    ('drift.detected', {'paths': ['src/aieos_bootstrap/records.py'], 'entities': ['SPEC-002']}, {}),
    ('violation.detected', record(record_id='rec-7', outcome='blocking', blocking_kind='violation',
                                  refers_to='ev-16'), {'task_id': TASK}),
    ('evidence.stale', {'records': ['rec-2'], 'reason': 'intent_version'}, {}),
    ('conflict.detected', {'tasks': [TASK, 'TASK-002'], 'paths': ['src/a.py'], 'interfaces': ['records']}, {}),
    ('record.added', record(record_id='rec-8', subject='SPEC-002', evidence_type='baseline_note'), {}),
]


def build(events, start=1):
    lines = []
    for n, (etype, payload, extra) in enumerate(events, start):
        e = {'event_id': 'ev-%d' % n, 'type': etype, 'appended_at': '2026-10-09T02:%02d:00.5Z' % n, 'seq': n,
             'payload': payload}
        e.update(extra)
        lines.append(json.dumps(e, sort_keys=True))
    return lines


class WholeLog(unittest.TestCase):

    def test_every_event_type_is_present(self):
        self.assertEqual({etype for etype, _, _ in EVENTS}, set(records.EVENT_TYPES))

    def test_clean_log_end_to_end(self):
        text = '\n'.join(build(EVENTS)) + '\n'
        report = records.check_log(text.encode('utf-8'))
        self.assertEqual(report.text_findings, ())
        self.assertEqual([(n, str(f)) for n, f in report.findings()], [])
        self.assertEqual(len(report.lines), len(EVENTS))
        self.assertEqual([line.event['type'] for line in report.lines], [etype for etype, _, _ in EVENTS])
        self.assertTrue(report.describe().endswith('no error found'))

    def test_duplicates_and_a_correction_in_a_log(self):
        lines = build(EVENTS)
        repeat = json.loads(lines[0])
        repeat['seq'] = len(lines) + 1
        repeat['appended_at'] = '2026-10-09T03:00:00Z'
        fix = json.loads(lines[11])
        fix.update({'event_id': 'ev-fix', 'seq': len(lines) + 2, 'corrects': 'ev-12'})
        text = '\n'.join(lines + [json.dumps(repeat), json.dumps(fix)]) + '\n'
        report = records.check_log(text)
        self.assertEqual(report.findings(), [])
        self.assertEqual(report.lines[-2].duplicate_of, 1)

    def test_broken_log_end_to_end(self):
        lines = build(EVENTS)
        broken = json.loads(lines[5])
        del broken['fencing_token']
        lines[5] = json.dumps(broken)
        lines[7] = lines[7].replace('"seq": 8', '"seq": 80')
        lines.insert(9, 'garbage')
        text = '﻿' + '\n'.join(lines) + '\r\n'
        report = records.check_log(text)
        found = {(n, f.rule) for n, f in report.findings()}
        self.assertIn((0, '2:bom'), found)
        self.assertIn((0, '2:cr'), found)
        self.assertIn((1, '6.1:json'), found)
        self.assertIn((6, '6.1:fencing_token'), found)
        self.assertIn((8, '6.1:seq'), found)
        self.assertIn((10, '6.1:json'), found)
        self.assertIsNone(report.lines[5].event)
        self.assertIn('line 6: 6.1:fencing_token', report.describe())


if __name__ == '__main__':
    unittest.main()

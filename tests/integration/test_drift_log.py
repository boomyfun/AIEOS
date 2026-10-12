"""Integration test of aieos_bootstrap.drift with aieos_bootstrap.eventlog (task TASK-030 AC10): the events it returns
are appended to an in-memory event log by the append rules, and a second append of each is a duplicate. No file is
opened. Each test names its criteria in its own docstring."""

import datetime
import unittest

from aieos_bootstrap import drift, eventlog, records

C = '1' * 40
AT = datetime.datetime(2026, 10, 12, 0, 0, 0, tzinfo=datetime.timezone.utc)


def result(article, outcome, rid):
    return {'record_id': rid, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_external_ci',
            'recorder': 'ci', 'subject': C, 'commit': C, 'gate': 'G3', 'outcome': outcome, 'refers_to': article}


def facts():
    """Four articles: SEC-001 fails, INV-001 passes, OPS-003 has no result, and GOV-003 fails but the task evaluated at
    this commit already recorded the same failure."""
    return {
        'base_commit': C,
        'changed_paths': ['src/aieos_bootstrap/drift.py', 'tests/unit/test_drift.py'],
        'articles': [{'id': 'SEC-001', 'scope': ['**']}, {'id': 'INV-001', 'scope': ['src/**']},
                     {'id': 'OPS-003', 'scope': ['src/**', 'tests/**']},
                     {'id': 'GOV-003', 'scope': ['src/aieos_bootstrap/**']}],
        'rule_results': [result('SEC-001', 'fail', 'r1'), result('INV-001', 'pass', 'r2'),
                         result('GOV-003', 'fail', 'r3')],
        'task_records': [result('GOV-003', 'fail', 'task-r3')],
        'recorder': 'aieos-core (test)',
    }


class EventsInALog(unittest.TestCase):

    def test_appended_then_duplicate(self):
        """TASK-030 AC10 and TASK-030 AC6: one event (SEC-001), already GOV-003, uncovered OPS-003; appended to an empty
        log, the log has no finding under check_log, and a second append of the event is a duplicate."""
        res = drift.violations(facts())
        self.assertIsNone(res['error'])
        self.assertEqual([e['payload']['refers_to'] for e in res['events']], ['SEC-001'])
        self.assertEqual(res['already'], ['GOV-003'])
        self.assertEqual(res['uncovered'], [{'ref': 'OPS-003', 'detail': 'no rule result'}])
        log = b''
        for e in res['events']:
            out = eventlog.append(log, e['event_type'], e['payload'], e['event_id'], AT)
            self.assertEqual(out.result, 'appended', out)
            log = out.log
        self.assertEqual(records.check_log(log).findings(), [])
        for e in res['events']:
            again = eventlog.append(log, e['event_type'], e['payload'], e['event_id'], AT)
            self.assertEqual(again.result, 'duplicate', again)

    def test_two_failing_articles_in_one_log(self):
        """TASK-030 AC10 and TASK-030 AC6: with no task record, both failing articles give events with distinct ids that
        append one after the other; a rerun of the computation appends nothing new."""
        f = facts()
        f['task_records'] = []
        res = drift.violations(f)
        self.assertEqual([e['payload']['refers_to'] for e in res['events']], ['GOV-003', 'SEC-001'])
        log = b''
        for e in res['events']:
            out = eventlog.append(log, e['event_type'], e['payload'], e['event_id'], AT)
            self.assertEqual(out.result, 'appended', out)
            log = out.log
        self.assertEqual(log.count(b'\n'), 2)
        for e in drift.violations(f)['events']:
            self.assertEqual(eventlog.append(log, e['event_type'], e['payload'], e['event_id'], AT).result, 'duplicate')


if __name__ == '__main__':
    unittest.main()

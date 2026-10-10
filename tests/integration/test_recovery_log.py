"""Integration tests of aieos_bootstrap.recovery (TASK-009 AC12): recovery over event logs built with
aieos_bootstrap.eventlog, with drafted, approved and submitted events of several tasks, then commits with and without
submissions; all in memory."""

import datetime
import unittest

from aieos_bootstrap import eventlog, records, recovery

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 11, 9, 0, 0, tzinfo=UTC)
NOW = T0 + datetime.timedelta(hours=3)
H64 = 'abcdef0123456789' * 4
REC = 'the recovery (aieos_bootstrap.recovery)'
TASKS = ('TASK-101', 'TASK-102', 'TASK-103', 'TASK-104')


def tok(n):
    return {'epoch': 'store-7', 'counter': n}


def lease(task_id, n, hours=4):
    return {'task_id': task_id, 'fencing_token': tok(n), 'expires_at': T0 + datetime.timedelta(hours=hours)}


def cid(n):
    return ('%x' % n) * 40 if n < 16 else ('%040x' % n)


def message(task_id, n, extra=''):
    return 'Work on %s\n\nSome body text.\n\nAIEOS-Task: %s\nAIEOS-Fence: store-7:%d\n%s' % (task_id, task_id, n, extra)


def append(log, kind, payload, event_id, task_id, **kw):
    r = eventlog.append(log, kind, payload, event_id, kw.pop('at', T0), task_id=task_id, **kw)
    assert r.result == 'appended', r
    return r.log


def project_log():
    """Four tasks drafted and approved; TASK-101 submitted under token 1 with commit 1."""
    log = b''
    for t in TASKS:
        log = append(log, 'task.drafted', {'contract_version': 'v1', 'contract_hash': H64}, 'd-' + t, t)
        log = append(log, 'task.approved', {'contract_version': 'v1', 'contract_hash': H64,
                                            'approval_record': 'a-' + t}, 'a-' + t, t)
    log = append(log, 'task.submitted', {'commit': cid(1), 'compensating': False}, 's-101', 'TASK-101',
                 fencing_token=tok(1), lease=lease('TASK-101', 1), recorder=REC, record_id='r-101',
                 at=T0 + datetime.timedelta(hours=1))
    return log


class RecoveryOverABuiltLogTest(unittest.TestCase):
    def setUp(self):
        self.log = project_log()
        self.commits = [
            {'commit': cid(1), 'message': message('TASK-101', 1)},               # already submitted
            {'commit': cid(2), 'message': message('TASK-102', 2)},               # held lease: compensating
            {'commit': cid(3), 'message': message('TASK-103', 3)},               # lease expired: observation
            {'commit': cid(4), 'message': 'A commit with no trailer\n'},         # left alone
            {'commit': cid(5), 'message': message('TASK-104', 9)},               # lost lease: observation
            {'commit': cid(6), 'message': message('TASK-102', 2, 'Co-Authored-By: someone\n')},  # second under 2
        ]
        self.leases = [lease('TASK-102', 2), lease('TASK-103', 3, hours=2)]

    def test_the_recovered_log(self):
        r = recovery.reconcile(self.log, self.commits, self.leases, NOW, REC)
        self.assertEqual(r.findings, ())
        self.assertEqual([(e['type'], e['task_id']) for e in r.events],
                         [('task.submitted', 'TASK-102'), ('record.added', 'TASK-103'),
                          ('record.added', 'TASK-104'), ('record.added', 'TASK-102')])
        self.assertEqual(records.check_log(r.log).findings(), [])
        self.assertTrue(r.log.startswith(self.log))
        new = [l.event for l in records.check_log(r.log).lines][len(records.check_log(self.log).lines):]
        self.assertEqual(new[0]['payload'], {'commit': cid(2), 'compensating': True})
        self.assertEqual([e['payload']['refers_to'] for e in new[1:]], [cid(3), cid(5), cid(6)])
        self.assertEqual(r.expired, (self.leases[1],))

    def test_a_compensating_submission_on_a_log_of_only_drafted_and_approved_events(self):  # D-391 C4 (ii)
        log = b''
        log = append(log, 'task.drafted', {'contract_version': 'v1', 'contract_hash': H64}, 'd', 'TASK-101')
        log = append(log, 'task.approved', {'contract_version': 'v1', 'contract_hash': H64,
                                            'approval_record': 'a'}, 'a', 'TASK-101')
        r = recovery.reconcile(log, [{'commit': cid(7), 'message': message('TASK-101', 1)}], [lease('TASK-101', 1)],
                               NOW, REC)
        self.assertEqual(r.findings, ())
        self.assertEqual([(e['type'], e['result']) for e in r.events], [('task.submitted', 'appended')])

    def test_recovery_twice_and_after_a_crash_between_commit_and_event(self):
        first = recovery.reconcile(self.log, self.commits, self.leases, NOW, REC)
        second = recovery.reconcile(first.log, self.commits, self.leases, NOW + datetime.timedelta(minutes=1), REC)
        self.assertEqual(second.log, first.log)
        self.assertTrue(all(e['result'] == 'duplicate' for e in second.events))
        # A later commit of a third session arrives: only it is recovered.
        more = self.commits + [{'commit': cid(8), 'message': message('TASK-103', 4)}]
        third = recovery.reconcile(first.log, more, self.leases + [lease('TASK-103', 4)], NOW, REC)
        added = [e for e in third.events if e['result'] == 'appended']
        self.assertEqual([(e['type'], e['task_id']) for e in added], [('task.submitted', 'TASK-103')])

    def test_git_wins_over_a_submission_whose_commit_is_gone(self):
        r = recovery.reconcile(self.log, self.commits[1:], self.leases, NOW, REC)
        self.assertTrue(any('step 2' in f and cid(1) in f for f in r.findings))
        self.assertTrue(r.log.startswith(self.log))


if __name__ == '__main__':
    unittest.main()

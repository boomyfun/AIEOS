"""Integration tests of aieos_bootstrap.writer (TASK-016 AC12): a full flow on real files in a temporary folder: a
store, a session, a grant, appends under the lease, a refused submission recorded, recovery's reconcile over the file's
bytes and the store's held leases, and expiry."""

import datetime
import os
import tempfile
import unittest

from aieos_bootstrap import records, recovery, writer

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
H64 = '0123456789abcdef' * 4
C40 = 'fedcba9876543210fedcba9876543210fedcba98'
REC = 'aieos-core'


def read(path):
    with open(path, 'rb') as f:
        return f.read()


class FullFlow(unittest.TestCase):

    def test_a_task_from_grant_to_recovery(self):
        with tempfile.TemporaryDirectory() as root:
            store = writer.open_store(root)
            self.assertEqual(store['counter'], 0)
            self.assertEqual(writer.start_session(root, 's-1', 'agent-1', T0).result, 'done')
            r = writer.append_event(root, 'task.drafted', {'contract_version': 'v1', 'contract_hash': H64}, 'ev-1',
                                    T0, REC, task_id='TASK-016')
            self.assertEqual(r.result, 'appended')
            lease = writer.grant_lease(root, 'TASK-016', 'READY', 'agent-1', 's-1', T0,
                                       T0 + datetime.timedelta(hours=1)).value
            self.assertEqual(lease['fencing_token'], {'epoch': store['epoch'], 'counter': 1})

            # a submission under another token is refused by the fence and recorded once
            wrong = dict(lease['fencing_token'], counter=7)
            refused = writer.append_event(root, 'task.submitted', {'commit': C40, 'compensating': False}, 'ev-bad',
                                          T0 + datetime.timedelta(minutes=1), REC, task_id='TASK-016',
                                          fencing_token=wrong)
            self.assertEqual((refused.reason, refused.refusal.result), ('fence', 'appended'))

            # the submission under the lease is appended
            ok = writer.append_event(root, 'task.submitted', {'commit': C40, 'compensating': False}, 'ev-s',
                                     T0 + datetime.timedelta(minutes=2), REC, task_id='TASK-016',
                                     fencing_token=lease['fencing_token'])
            self.assertEqual((ok.result, ok.seq), ('appended', 3))
            log = read(writer.log_path(root))
            self.assertEqual(records.check_log(log).findings(), [])
            self.assertEqual([x.event['type'] for x in records.check_log(log).lines],
                             ['task.drafted', 'record.added', 'task.submitted'])

            # recovery over the file's bytes and the store's held leases
            message = 'Work\n\nAIEOS-Task: TASK-016\nAIEOS-Fence: %s:1\n' % store['epoch']
            result = recovery.reconcile(log, [{'commit': C40, 'message': message}], writer.held_leases(root),
                                        T0 + datetime.timedelta(minutes=3), REC)
            self.assertEqual(result.expired, ())
            self.assertEqual((result.log, result.events, result.findings), (log, (), ()))
            self.assertEqual(writer.held_leases(root), [lease])
            late = recovery.reconcile(log, [{'commit': C40, 'message': message}], writer.held_leases(root),
                                      T0 + datetime.timedelta(hours=1), REC)
            self.assertEqual(late.expired, (lease,))

            # expiry, then the files are still exactly the two
            gone = writer.expire_leases(root, T0 + datetime.timedelta(hours=1))
            self.assertEqual(gone, [lease])
            self.assertEqual(writer.end_session(root, 's-1', T0 + datetime.timedelta(hours=2)).value, [])
            found = sorted(os.path.relpath(os.path.join(h, n), root).replace(os.sep, '/')
                           for h, _, ns in os.walk(root) for n in ns)
            self.assertEqual(found, ['.aieos/events.jsonl', '.aieos/local/state.sqlite'])
            self.assertEqual(read(writer.log_path(root)), log)


if __name__ == '__main__':
    unittest.main()

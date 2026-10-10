"""Property tests of aieos_bootstrap.recovery (TASK-009 AC12; INV-009): standard library only, fixed seeds. For random
well-formed logs, commits, leases and times: the returned log has no check_log finding and begins with the given log
(append-only); reconcile is idempotent; every commit with a task trailer and no submission gives exactly one event,
compensating only under a counting lease; and the arguments are never changed."""

import copy
import datetime
import random
import unittest

from aieos_bootstrap import eventlog, records, recovery

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 11, 0, 0, 0, tzinfo=UTC)
H64 = '0f' * 32
REC = 'the recovery (aieos_bootstrap.recovery)'
RUNS = 150


def build(rng):
    tasks = ['TASK-%d' % (200 + i) for i in range(rng.randint(1, 4))]
    log = b''
    for t in tasks:
        for kind, payload in (('task.drafted', {'contract_version': 'v1', 'contract_hash': H64}),
                              ('task.approved', {'contract_version': 'v1', 'contract_hash': H64,
                                                 'approval_record': 'a-' + t})):
            r = eventlog.append(log, kind, payload, kind + t, T0, task_id=t)
            assert r.result == 'appended', r
            log = r.log
    now = T0 + datetime.timedelta(hours=rng.randint(1, 10))
    leases, commits, used = [], [], set()
    for t in tasks:
        for _ in range(rng.randint(0, 2)):
            n = rng.randint(0, 5)
            if (t, n) not in used:
                used.add((t, n))
                leases.append({'task_id': t, 'fencing_token': {'epoch': rng.choice(['e1', 'e2']), 'counter': n},
                               'expires_at': now + datetime.timedelta(minutes=rng.randint(-120, 120))})
    for i in range(rng.randint(0, 8)):
        c = '%040x' % rng.getrandbits(160)
        kind = rng.random()
        if kind < 0.15:
            m = 'No trailer\n'
        elif kind < 0.3:
            m = 'Work\n\nAIEOS-Task: %s\n' % rng.choice(tasks)
        else:
            m = 'Work\n\nAIEOS-Task: %s\nAIEOS-Fence: %s:%d\n' % (rng.choice(tasks), rng.choice(['e1', 'e2']),
                                                                rng.randint(0, 5))
        commits.append({'commit': c, 'message': m})
    return log, commits, leases, now


class RecoveryPropertiesTest(unittest.TestCase):
    def test_properties(self):
        rng = random.Random(9009)
        for i in range(RUNS):
            log, commits, leases, now = build(rng)
            before = (bytes(log), copy.deepcopy(commits), copy.deepcopy(leases))
            r = recovery.reconcile(log, commits, leases, now, REC)
            with self.subTest(run=i):
                self.assertEqual((log, commits, leases), before)
                self.assertEqual(records.check_log(r.log).findings(), [])
                self.assertTrue(r.log.startswith(log))
                self.assertEqual(r.findings, ())
                again = recovery.reconcile(r.log, commits, leases, now, REC)
                self.assertEqual(again.log, r.log)
                self.assertTrue(all(e['result'] == 'duplicate' for e in again.events))
                trailered = [c for c in commits if recovery.trailers(c['message'])[0]['task'] is not None]
                self.assertEqual(len(r.events), len(trailered))
                for e in r.events:
                    if e['type'] == 'task.submitted':
                        line = [l.event for l in records.check_log(r.log).lines if l.event['event_id'] == e['event_id']][0]
                        self.assertTrue(any(x['task_id'] == e['task_id'] and x['fencing_token'] == line['fencing_token']
                                            and x['expires_at'] > now for x in leases))
                subs = [(l.event['task_id'], repr(sorted(l.event['fencing_token'].items())))
                        for l in records.check_log(r.log).lines if l.event['type'] == 'task.submitted']
                self.assertEqual(len(subs), len(set(subs)))
                self.assertEqual(list(r.expired), [x for x in leases if not x['expires_at'] > now])


if __name__ == '__main__':
    unittest.main()

"""Property tests of aieos_bootstrap.eventlog (TASK-007 AC12), standard library only, with fixed seeds.

For random sequences of appends: the bytes only grow and every earlier prefix is kept (INV-009); seq runs 1 to n;
every event_id is unique; appending any event a second time changes nothing; the same inputs always give the same
bytes; and no submission with a mismatched or expired lease is ever appended."""

import datetime
import random
import string
import unittest

from aieos_bootstrap import eventlog, records

SEEDS = (1, 2, 3, 5, 8, 13, 21, 34)
ROUNDS = 30
UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 10, 0, 0, 0, tzinfo=UTC)
HEX = '0123456789abcdef'


def word(rng, n=6):
    return ''.join(rng.choice(string.ascii_lowercase) for _ in range(n))


def task_id(rng):
    return 'TASK-%03d' % rng.randint(0, 20)


def token(rng):
    return {'epoch': rng.choice(['store-1', 'store-2', 7]), 'counter': rng.randint(0, 5)}


def event(rng, n):
    """One well-formed event as (type, payload, keyword arguments), with a lease that holds when one is needed."""
    tid = task_id(rng)
    kind = rng.randrange(5)
    if kind == 0:
        return 'task.drafted', {'contract_version': 'v%d' % rng.randint(1, 9),
                                'contract_hash': ''.join(rng.choice(HEX) for _ in range(64))}, {'task_id': tid}
    if kind == 1:
        return 'task.blocked', {'reason': word(rng), 'blocked_by': [task_id(rng)]}, {'task_id': tid}
    if kind == 2:
        tok = token(rng)
        lease = {'task_id': tid, 'fencing_token': dict(tok), 'expires_at': T0 + datetime.timedelta(days=1)}
        return 'task.submitted', {'commit': ''.join(rng.choice(HEX) for _ in range(40)), 'compensating': False}, {
            'task_id': tid, 'fencing_token': tok, 'lease': lease, 'recorder': 'core', 'record_id': 'rec-%d' % n}
    if kind == 3:
        return 'record.added', {'record_id': 'rec-%s' % word(rng), 'fact_kind': 'observation',
                                'source_class': 'deterministic_tool_local', 'recorder': word(rng), 'subject': tid,
                                'outcome': rng.choice(['pass', 'fail'])}, {'task_id': tid}
    return 'drift.detected', {'paths': ['src/%s.py' % word(rng)], 'entities': [word(rng).upper()]}, {}


def run(rng, count):
    log, history, events = b'', [], []
    for n in range(1, count + 1):
        etype, payload, kw = event(rng, n)
        eid = 'ev-%d-%s' % (n, word(rng, 4))
        r = eventlog.append(log, etype, payload, eid, T0 + datetime.timedelta(seconds=n), **kw)
        assert r.result == 'appended', r
        history.append(log)
        events.append((etype, payload, eid, kw))
        log = r.log
    return log, history, events


class Properties(unittest.TestCase):

    def test_bytes_only_grow_and_prefixes_are_kept(self):
        for seed in SEEDS:
            log, history, _ = run(random.Random(seed), ROUNDS)
            for earlier, later in zip(history, history[1:] + [log]):
                self.assertTrue(later.startswith(earlier))
                self.assertGreater(len(later), len(earlier))
                self.assertEqual(later[len(earlier):].count(b'\n'), 1)

    def test_seq_runs_and_ids_are_unique(self):
        for seed in SEEDS:
            log, _, _ = run(random.Random(seed), ROUNDS)
            report = records.check_log(log)
            self.assertEqual(report.findings(), [])
            self.assertEqual([line.event['seq'] for line in report.lines], list(range(1, ROUNDS + 1)))
            ids = [line.event['event_id'] for line in report.lines]
            self.assertEqual(len(ids), len(set(ids)))

    def test_a_second_append_changes_nothing(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            log, _, events = run(rng, ROUNDS)
            for etype, payload, eid, kw in rng.sample(events, 10):
                r = eventlog.append(log, etype, payload, eid, T0 + datetime.timedelta(days=3), **kw)
                self.assertEqual((r.result, r.log), ('duplicate', None))

    def test_same_inputs_same_bytes(self):
        for seed in SEEDS:
            self.assertEqual(run(random.Random(seed), ROUNDS)[0], run(random.Random(seed), ROUNDS)[0])

    def test_no_submission_without_a_holding_lease(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            log, _, _ = run(rng, 5)
            for n in range(ROUNDS):
                tid, tok = task_id(rng), token(rng)
                at = T0 + datetime.timedelta(hours=rng.randint(1, 48))
                lease = {'task_id': tid, 'fencing_token': dict(tok), 'expires_at': at + datetime.timedelta(minutes=5)}
                broken = rng.randrange(4)
                if broken == 0:
                    lease['task_id'] = 'TASK-%03d' % (int(tid[5:]) + 1)
                elif broken == 1:
                    lease['fencing_token'] = {'epoch': tok['epoch'], 'counter': tok['counter'] + 1}
                elif broken == 2:
                    lease['expires_at'] = at - datetime.timedelta(seconds=rng.randint(0, 3600))
                else:
                    lease = None
                r = eventlog.append(log, 'task.submitted', {'commit': 'a' * 40, 'compensating': False},
                                    'ev-sub-%d' % n, at, task_id=tid, fencing_token=tok, lease=lease,
                                    recorder='core', record_id='rec-r%d' % n)
                self.assertEqual((r.result, r.reason, r.log), ('refused', 'fence', None), (seed, n, broken))
                self.assertEqual(records.check_record(r.record), [])


if __name__ == '__main__':
    unittest.main()

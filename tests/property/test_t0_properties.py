"""Property tests of aieos_bootstrap.t0 (task TASK-060, rule R10's property case): standard library only, fixed seeds.
Claim calls over equal inputs give equal records and equal logs, and no generated claim list gives a record with an
outcome, a dimension or a gate. The event log is kept in memory and appended by eventlog.append with a held lease; no
process starts and no file is written or created. Each test names its criteria in its own docstring."""

import datetime
import inspect
import pathlib
import random
import unittest

from aieos_bootstrap import eventlog
from aieos_bootstrap import records
from aieos_bootstrap import t0
from aieos_bootstrap import writer

ROOT = str(pathlib.Path(__file__).resolve().parents[2] / 'no-such-t0-root')
TASK = 'TASK-100'
NOW = datetime.datetime(2026, 10, 17, 12, 0, 0, tzinfo=datetime.timezone.utc)
TOKEN = {'epoch': 'e1', 'counter': 3}
LEASE = {'task_id': TASK, 'fencing_token': TOKEN, 'expires_at': NOW + datetime.timedelta(hours=1)}
SEEDS = (60, 600, 6000, 60000)
ALPHABET = 'abcdefghijklmnopqrstuvwxyz ABC/._-0123456789é中'


class Memory:
    """The event log in memory, appended by eventlog.append with the one held lease."""

    def __init__(self):
        self.log = b''
        self.records = []

    def append_event(self, *args, **kwargs):
        inspect.signature(writer.append_event).bind(*args, **kwargs)
        root, event_type, payload, event_id, appended_at, recorder = args
        self.records.append(payload)
        r = eventlog.append(self.log, event_type, payload, event_id, appended_at, task_id=kwargs.get('task_id'),
                            fencing_token=kwargs.get('fencing_token'), lease=LEASE, recorder=recorder,
                            record_id='refusal-' + event_id)
        if r.result == 'appended':
            self.log += r.line
        return writer.WriteResult(r)


def claims(rng):
    out = []
    for _ in range(rng.randint(1, 12)):
        text = ''.join(rng.choice(ALPHABET) for _ in range(rng.randint(1, 80))).strip() or 'x'
        out.append({'kind': rng.choice(('did', 'read_set')), 'text': text})
    return out


class R10Properties(unittest.TestCase):
    def test_equal_inputs_give_equal_records_and_equal_logs(self):
        """TASK-060 AC10, TASK-060 AC2, TASK-060 AC3: for each fixed seed, two claim calls over equal inputs into two
        empty logs give equal records, equal logs and the same result, every record passes records.check_payload."""
        for seed in SEEDS:
            cs = claims(random.Random(seed))
            a, b = Memory(), Memory()
            ra = t0.claim(ROOT, TASK, 'session-p', TOKEN, cs, 'p-%d' % seed, 'a property run', NOW,
                          append=a.append_event)
            rb = t0.claim(ROOT, TASK, 'session-p', TOKEN, [dict(c) for c in cs], 'p-%d' % seed, 'a property run',
                          NOW, append=b.append_event)
            self.assertEqual(ra, rb, seed)
            self.assertEqual(ra['result'], 'done', (seed, ra['findings']))
            self.assertEqual((a.records, a.log), (b.records, b.log), seed)
            self.assertEqual(len(a.records), len(cs))
            for rec in a.records:
                self.assertEqual(records.check_payload('record.added', rec), [], seed)

    def test_no_generated_claim_gives_an_outcome_a_dimension_or_a_gate(self):
        """TASK-060 AC10, TASK-060 AC2, TASK-060 AC6: no record built from a generated claim list holds an outcome, a
        dimension or a gate, and each is a claim declared by the agent."""
        for seed in SEEDS:
            rng = random.Random(seed + 1)
            for _ in range(20):
                mem = Memory()
                t0.claim(ROOT, TASK, 'session-p', TOKEN, claims(rng), 'q-%d' % rng.randint(0, 10 ** 6),
                         'a property run', NOW, append=mem.append_event)
                for rec in mem.records:
                    self.assertFalse({'outcome', 'dimension', 'gate'} & set(rec), (seed, rec))
                    self.assertEqual((rec['fact_kind'], rec['source_class']), ('claim', 'agent_declared'))


if __name__ == '__main__':
    unittest.main()

"""Property tests of aieos_bootstrap.writer (TASK-016 AC12), standard library only, fixed seeds: for random sequences
of appends, grants and releases, the log file's bytes only grow and every earlier prefix is kept (INV-009),
records.check_log finds nothing, and no two grants ever carry the same token, also across a store that is recreated
in another folder."""

import datetime
import os
import random
import tempfile
import unittest

from aieos_bootstrap import records, writer

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
H64 = '0123456789abcdef' * 4
C40 = 'fedcba9876543210fedcba9876543210fedcba98'
REC = 'aieos-core'
TASKS = ['TASK-%03d' % i for i in range(1, 5)]
SEEDS = (1, 2, 3, 4, 5, 6)
STEPS = 40


def read(path):
    with open(path, 'rb') as f:
        return f.read()


def run(root, rng, tokens):
    """One random sequence under one root; checks the log after each step and collects every granted token."""
    writer.open_store(root)
    writer.start_session(root, 's-1', 'agent-1', T0)
    held = {}
    previous = b''
    for step in range(STEPS):
        at = T0 + datetime.timedelta(seconds=step)
        task = rng.choice(TASKS)
        kind = rng.choice(('draft', 'grant', 'release', 'submit', 'submit_bad', 'repeat'))
        if kind == 'grant':
            r = writer.grant_lease(root, task, rng.choice(('READY', 'REWORK', 'DONE')), 'agent-1', 's-1', at,
                                   at + datetime.timedelta(hours=1))
            if r.result == 'done':
                tokens.append((r.value['fencing_token']['epoch'], r.value['fencing_token']['counter']))
                held[task] = r.value
        elif kind == 'release':
            writer.release_lease(root, task)
            held.pop(task, None)
        elif kind == 'draft':
            writer.append_event(root, 'task.drafted', {'contract_version': 'v1', 'contract_hash': H64},
                                'ev-%d' % step, at, REC, task_id=task)
        elif kind == 'repeat':
            writer.append_event(root, 'task.drafted', {'contract_version': 'v1', 'contract_hash': H64},
                                'ev-%d' % rng.randrange(step + 1), at, REC, task_id=task)
        else:
            token = held[task]['fencing_token'] if task in held and kind == 'submit' else {'epoch': 'x', 'counter': 99}
            writer.append_event(root, 'task.submitted', {'commit': C40, 'compensating': False}, 'ev-s-%d' % step, at,
                                REC, task_id=task, fencing_token=token)
        path = writer.log_path(root)
        log = read(path) if os.path.exists(path) else b''
        assert log[:len(previous)] == previous, 'an earlier prefix changed'
        assert records.check_log(log).findings() == [], 'the log has a finding'
        previous = log


class Properties(unittest.TestCase):

    def test_the_log_only_grows_and_tokens_never_repeat(self):
        for seed in SEEDS:
            tokens = []
            rng = random.Random(seed)
            with tempfile.TemporaryDirectory() as first:
                run(first, rng, tokens)
            with tempfile.TemporaryDirectory() as second:
                run(second, rng, tokens)
            self.assertEqual(len(tokens), len(set(tokens)), seed)
            self.assertTrue(tokens, seed)


if __name__ == '__main__':
    unittest.main()

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


class LookupProperties(unittest.TestCase):

    def test_the_lookup_never_changes_the_store(self):
        """TASK-066 AC9 (property) and TASK-066 AC3: over generated real stores (fixed seed, at most 50 cases: random
        sessions, grants, ends and expiries), session_lease never changes the store's bytes or the files under the
        project-state directory, and its result is always one of the documented shapes."""
        rng = random.Random(66)
        shapes = set()
        for case in range(25):
            with tempfile.TemporaryDirectory() as root:
                writer.open_store(root)
                sessions = ['s-%d' % i for i in range(1, rng.randint(1, 4) + 1)]
                for sid in sessions:
                    writer.start_session(root, sid, 'agent-1', T0)
                for i in range(rng.randint(0, 4)):
                    at = T0 + datetime.timedelta(minutes=rng.randint(0, 30))
                    writer.grant_lease(root, rng.choice(TASKS), 'READY', 'agent-1', rng.choice(sessions), at,
                                       at + datetime.timedelta(minutes=rng.randint(1, 60)))
                if rng.random() < 0.3:
                    writer.end_session(root, rng.choice(sessions), T0)
                if rng.random() < 0.3:
                    writer.expire_leases(root, T0 + datetime.timedelta(minutes=rng.randint(0, 90)))
                path = writer.store_path(root)
                for _ in range(2):
                    files = sorted(os.listdir(os.path.dirname(path)))
                    before = read(path)
                    sid = rng.choice(sessions + [None, 's-9'])
                    now = T0 + datetime.timedelta(minutes=rng.randint(0, 120))
                    r = writer.session_lease(root, sid, now)
                    shapes.add((r.result, r.reason))
                    self.assertEqual((read(path), sorted(os.listdir(os.path.dirname(path)))), (before, files), case)
                    self.assertIn(r.result, ('done', 'refused'))
                    self.assertEqual(r.value is None, (r.result, r.reason) != ('done', 'tied'))
        self.assertIn(('done', 'tied'), shapes)
        self.assertTrue(any(s[0] == 'refused' for s in shapes))


class ReadsProperties(unittest.TestCase):
    """TASK-067's property tests (standard library only, fixed seeds, at most 50 cases each)."""

    def test_each_distinct_path_once_in_first_seen_order(self):
        """TASK-067 AC2, TASK-067 AC3 and TASK-067 AC9 (property): over generated path lists in several calls,
        add_reads stores each distinct path once in first-seen order and stored_reads returns exactly that list."""
        rng = random.Random(67)
        alphabet = ['a', 'b', 'c', 'd', ' ', '007', 'x/y', 'é']
        for case in range(30):
            with tempfile.TemporaryDirectory() as root:
                writer.open_store(root)
                writer.start_session(root, 's-1', 'agent-1', T0)
                writer.grant_lease(root, 'TASK-067', 'READY', 'agent-1', 's-1', T0, T0 + datetime.timedelta(hours=1))
                want = []
                for _ in range(rng.randint(1, 4)):
                    paths = [rng.choice(alphabet) + rng.choice(['', '1', '2']) for _ in range(rng.randint(0, 8))]
                    r = writer.add_reads(root, 's-1', paths if rng.random() < 0.5 else tuple(paths), T0)
                    new = [p for p in dict.fromkeys(paths) if p not in want]
                    self.assertEqual((r.result, r.value), ('done', len(new)), case)
                    want.extend(new)
                self.assertEqual(writer.stored_reads(root, 's-1', 'TASK-067').value, want, case)

    def test_the_lookup_and_the_accumulation_agree(self):
        """TASK-067 AC4 and TASK-067 AC9 (property): over generated store states (no lease row; unknown, ended and
        started sessions; zero, one and two live leases of the session; expired leases), with valid arguments only and
        well-formed lease rows, session_lease gives "tied" exactly when add_reads accepts, and on refusal both give the
        same reason."""
        rng = random.Random(1067)
        seen = set()
        for case in range(40):
            with tempfile.TemporaryDirectory() as root:
                writer.open_store(root)
                sessions = ['s-%d' % i for i in range(1, rng.randint(1, 3) + 1)]
                for sid in sessions:
                    writer.start_session(root, sid, 'agent-1', T0)
                for i in range(rng.randint(0, 4)):
                    writer.grant_lease(root, rng.choice(TASKS), 'READY', 'agent-1', rng.choice(sessions), T0,
                                       T0 + datetime.timedelta(minutes=rng.randint(1, 60)))
                if rng.random() < 0.3:
                    writer.end_session(root, rng.choice(sessions), T0)
                sid = rng.choice(sessions + ['s-9'])
                now = T0 + datetime.timedelta(minutes=rng.randint(0, 70))
                a = writer.session_lease(root, sid, now)
                b = writer.add_reads(root, sid, ['p'], now)
                seen.add(a.reason)
                self.assertEqual(a.reason == 'tied', b.result == 'done', (case, a, b))
                if a.reason != 'tied':
                    self.assertEqual((a.reason, a.findings), (b.reason, b.findings), case)
        self.assertIn('tied', seen)
        self.assertTrue(seen - {'tied'})


if __name__ == '__main__':
    unittest.main()

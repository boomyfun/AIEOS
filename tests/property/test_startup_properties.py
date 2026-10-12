"""Property tests of aieos_bootstrap.startup (task TASK-026, the properties of AC15), standard library only, with fixed
seeds: random histories as parent graphs always reach reconcile parents before children and each commit once; random
read failures never reach the append. Each test names its criteria in its own docstring."""

import datetime
import pathlib
import random
import unittest

from aieos_bootstrap import recovery
from aieos_bootstrap import startup

ROOT = pathlib.Path(__file__).resolve().parents[2]
REPO = str(ROOT)
STATE_ROOT = str(ROOT / 'no-such-state-root')
SEEDS = (1, 2, 3, 5, 8, 13, 21, 34)
ROUNDS = 30
NOW = datetime.datetime(2026, 10, 12, 10, 0, 0, tzinfo=datetime.timezone.utc)
TREE = 'b' * 40
BODY = 'Work\n\nThe body.\n\nAIEOS-Task: TASK-026\n'


def cid(n):
    return '%040x' % (n + 1)


def history(rng):
    """A random parent graph: commit i has up to three parents among commits before it; the head is a commit that
    every other one reaches through parents (a final merge of all commits no other names)."""
    n = rng.randint(1, 25)
    parents = {}
    for i in range(n):
        k = min(i, rng.randint(0, 3))
        parents[cid(i)] = [cid(j) for j in rng.sample(range(i), k)]
    named = {p for ps in parents.values() for p in ps}
    tips = [c for c in parents if c not in named]
    head = cid(n)
    parents[head] = tips
    return parents, head


class Reader:
    def __init__(self, parents, head, fail=None):
        self.parents = parents
        self.head = head
        self.fail = fail
        self.reads = []

    def __call__(self, repo, args, *rest):
        key = 'HEAD' if args[0] == 'rev-parse' else args[-1]
        self.reads.append(key)
        if key == self.fail:
            return {'exit': 128, 'out': b'', 'err': b'fatal', 'error': None}
        if key == 'HEAD':
            return {'exit': 0, 'out': (self.head + '\n').encode('ascii'), 'err': b'', 'error': None}
        head = 'tree %s\n' % TREE + ''.join('parent %s\n' % p for p in self.parents[key])
        head += 'author T <t> 1700000000 +0000\ncommitter T <t> 1700000000 +0000\n\n'
        return {'exit': 0, 'out': (head + BODY).encode('utf-8'), 'err': b'', 'error': None}


class Appended:
    result = 'appended'


class Stand:
    def __init__(self):
        self.log = b''
        self.appends = 0

    def read_log(self, root):
        return self.log

    def leases(self, root):
        return []

    def append(self, *args, **kwargs):
        self.appends += 1
        return Appended()

    def release(self, *args):
        raise AssertionError('no lease is held')

    def expire(self, root, now):
        return []


class Properties(unittest.TestCase):
    def test_parents_before_children_and_each_commit_once(self):
        """TASK-026 AC3, TASK-026 AC2 and TASK-026 AC15: for random parent graphs, every commit reaches reconcile
        exactly once and after all of its parents, and each is read once."""
        original = recovery.reconcile
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                parents, head = history(rng)
                given = []

                def spy(log, commits, leases, now, recorder):
                    given.extend(c['commit'] for c in commits)
                    return original(log, commits, leases, now, recorder)
                reader = Reader(parents, head)
                stand = Stand()
                recovery.reconcile = spy
                try:
                    startup.recover(STATE_ROOT, REPO, 'test', NOW, read=reader, read_log=stand.read_log,
                                    append=stand.append, leases=stand.leases, release=stand.release,
                                    expire=stand.expire)
                finally:
                    recovery.reconcile = original
                self.assertEqual(sorted(given), sorted(parents))
                self.assertEqual(len(given), len(set(given)))
                at = {c: i for i, c in enumerate(given)}
                for c, ps in parents.items():
                    for p in ps:
                        self.assertLess(at[p], at[c])
                reads = [k for k in reader.reads if k != 'HEAD']
                self.assertEqual(sorted(reads), sorted(parents))

    def test_read_failures_never_reach_the_append(self):
        """TASK-026 AC2, TASK-026 AC10 and TASK-026 AC15: a failing read of HEAD or of any commit gives refused, reason
        git, and append is never called."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                parents, head = history(rng)
                fail = rng.choice(['HEAD'] + sorted(parents))
                stand = Stand()
                r = startup.recover(STATE_ROOT, REPO, 'test', NOW, read=Reader(parents, head, fail),
                                    read_log=stand.read_log, append=stand.append, leases=stand.leases,
                                    release=stand.release, expire=stand.expire)
                self.assertEqual((r['result'], r['reason']), ('refused', 'git'))
                self.assertEqual(stand.appends, 0)


if __name__ == '__main__':
    unittest.main()

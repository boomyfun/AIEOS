"""Property tests of aieos_bootstrap.submit (task TASK-025, the properties of AC13), standard library only, with
fixed seeds: arguments outside AC1's forms never reach the read; two-paragraph messages with a valid task and fence
always reach the append exactly once with that fence; failing reads never reach the append. Each test names its
criteria in its own docstring."""

import datetime
import pathlib
import random
import unittest

from aieos_bootstrap import submit

ROOT = pathlib.Path(__file__).resolve().parents[2]
REPO = str(ROOT)
STATE_ROOT = str(ROOT / 'no-such-state-root')
SEEDS = (1, 2, 3, 5, 8, 13, 21, 34)
ROUNDS = 40
NOW = datetime.datetime(2026, 10, 12, 9, 30, 0, tzinfo=datetime.timezone.utc)
HEXD = '0123456789abcdef'
WORD = 'abcdefghijklmnopqrstuvwxyz '


class Appended:
    result = 'appended'
    reason = None
    findings = ()
    refusal = None


class Stand:
    def __init__(self, message=None, t=None, p=None):
        self.reads = 0
        self.appends = []
        self.message = message
        self.t = t
        self.p = p

    def read(self, repo, args, *rest):
        self.reads += 1
        if args[1] == '-t':
            return self.t or {'exit': 0, 'out': b'commit\n', 'err': b'', 'error': None}
        body = ('tree %s\nauthor T <t> 1 +0000\ncommitter T <t> 1 +0000\n\n%s' % ('c' * 40, self.message)).encode('utf-8')
        return self.p or {'exit': 0, 'out': body, 'err': b'', 'error': None}

    def append(self, *args, **kwargs):
        self.appends.append(kwargs)
        return Appended()

    def release(self, *args):
        return None

    def held(self, *args):
        return None


def call(stand, **kw):
    args = dict(root=STATE_ROOT, repo=REPO, commit_id='a' * 40, task_id='TASK-025', event_id='e', recorder='r', now=NOW)
    args.update(kw)
    return submit.submit(read=stand.read, append=stand.append, release=stand.release, held=stand.held, **args)


def words(rng, n):
    return ''.join(rng.choice(WORD) for _ in range(n)).strip() or 'x'


class Properties(unittest.TestCase):
    def test_bad_arguments_never_reach_the_read(self):
        """TASK-025 AC1 and TASK-025 AC13: random arguments outside AC1's forms never call read."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                key = rng.choice(['root', 'repo', 'commit_id', 'task_id', 'event_id', 'recorder', 'now'])
                bad = {
                    'root': rng.choice(['', 'rel', None, 5]),
                    'repo': rng.choice(['', 'rel/x', None, b'/x']),
                    'commit_id': ''.join(rng.choice(HEXD + 'G') for _ in range(rng.choice((0, 39, 41, 64)))),
                    'task_id': rng.choice(['TASK-', 'TASK-x', 'task-1', '', None]),
                    'event_id': rng.choice(['', None, 0]),
                    'recorder': rng.choice(['', None, []]),
                    'now': rng.choice([NOW.replace(tzinfo=None), NOW.replace(microsecond=rng.randrange(1, 10 ** 6)), 'now']),
                }[key]
                stand = Stand(message='S\n\nB\n\nAIEOS-Task: TASK-025\nAIEOS-Fence: e:1\n')
                r = call(stand, **{key: bad})
                self.assertEqual((r['result'], r['reason'], stand.reads), ('refused', 'argument', 0), (seed, key, bad))

    def test_identified_messages_reach_the_append_once_with_their_fence(self):
        """TASK-025 AC3, TASK-025 AC4 and TASK-025 AC13: random two-paragraph messages with the task and a fence reach
        append exactly once with that fence."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                epoch = ''.join(rng.choice(HEXD + ':') for _ in range(rng.randrange(1, 20))).strip(':') or 'e'
                counter = rng.randrange(0, 10 ** 9)
                message = '%s\n\n%s\n\nAIEOS-Task: TASK-025\nAIEOS-Fence: %s:%d\n' % (words(rng, 20), words(rng, 40), epoch, counter)
                stand = Stand(message=message)
                r = call(stand)
                self.assertEqual(r['result'], 'submitted', message)
                self.assertEqual(len(stand.appends), 1)
                self.assertEqual(stand.appends[0]['fencing_token'], {'epoch': epoch, 'counter': counter})

    def test_failing_reads_never_reach_the_append(self):
        """TASK-025 AC2 and TASK-025 AC13: random failing results of either read never call append."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                bad = rng.choice([
                    {'exit': None, 'out': b'', 'err': b'', 'error': rng.choice(['timeout', 'refused form', 'PATH'])},
                    {'exit': rng.randrange(1, 255), 'out': b'', 'err': b'x', 'error': None},
                    {'exit': 0, 'out': bytes(rng.randrange(256) for _ in range(rng.randrange(0, 30))), 'err': b'', 'error': None},
                ])
                stand = Stand(message='S\n\nB\n\nAIEOS-Task: TASK-025\nAIEOS-Fence: e:1\n',
                              **({'t': bad} if rng.random() < 0.5 else {'p': bad}))
                r = call(stand)
                if r['result'] == 'submitted':
                    # only a -t result whose out happened to be b"commit\n" with exit 0 can pass; it is not a failure
                    self.assertEqual(stand.t and stand.t['out'], b'commit\n')
                    continue
                self.assertEqual((r['result'], r['reason'], stand.appends), ('refused', 'git', []), bad)


if __name__ == '__main__':
    unittest.main()

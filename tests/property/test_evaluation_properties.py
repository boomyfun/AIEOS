"""Property tests of aieos_bootstrap.evaluation (task TASK-027, the properties of AC15), standard library only, with
fixed seeds: random task histories as chains of commits always give the union of their paths; random read failures
never reach the append. Each test names its criteria in its own docstring."""

import datetime
import hashlib
import pathlib
import random
import unittest

from aieos_bootstrap import evaluation
from aieos_bootstrap import eventlog

ROOT = pathlib.Path(__file__).resolve().parents[2]
REPO = str(ROOT)
STATE_ROOT = str(ROOT / 'no-such-state-root')
SEEDS = (1, 2, 3, 5, 8, 13, 21, 34)
ROUNDS = 30
NOW = datetime.datetime(2026, 10, 12, 10, 0, 0, tzinfo=datetime.timezone.utc)
TREE = 'b' * 40
TASK = 'TASK-027'
CONTRACT = b'task: TASK-027\n'
MINE = 'Work\n\nThe body.\n\nAIEOS-Task: TASK-027\n'
PLAIN = 'Records\n\nThe body.\n'
NAMES = ['src/a.py', 'src/b.py', 'tests/unit/test_a.py', 'tests/unit/test_b.py', 'src/c.py']
FENCE = {'epoch': 'e0', 'counter': 1}


def cid(n):
    return '%040x' % (n + 1)


def history(rng):
    """A main commit cid(0) with no trailer, then a chain of 1 to 12 task commits, each changing 1 to 3 names."""
    n = rng.randint(1, 12)
    table = {cid(0): ([], PLAIN, ['docs/x.md'])}
    for i in range(1, n + 1):
        table[cid(i)] = ([cid(i - 1)], MINE, rng.sample(NAMES, rng.randint(1, 3)))
    return table, cid(n)


def reader(table, fail=None):
    def read(repo, args, *rest):
        key = (args[0], args[-1])
        if fail is not None and key == fail:
            return {'exit': 1, 'out': b'', 'err': b'', 'error': None}
        parents, message, paths = table[args[-1]]
        if args[0] == 'cat-file':
            head = 'tree %s\n' % TREE + ''.join('parent %s\n' % p for p in parents)
            head += 'author T <t> 1700000000 +0000\ncommitter T <t> 1700000000 +0000\n\n'
            out = (head + message).encode('utf-8')
        else:
            out = b''.join(p.encode('utf-8') + b'\0' for p in paths)
        return {'exit': 0, 'out': out, 'err': b'', 'error': None}
    return read


def log_for(head):
    r = eventlog.append(b'', 'task.approved', {'contract_version': 'v1',
                                                'contract_hash': hashlib.sha256(CONTRACT).hexdigest(),
                                                'approval_record': 'rec-a'}, 'approved-1', NOW, task_id=TASK)
    lease = {'task_id': TASK, 'fencing_token': FENCE, 'expires_at': NOW + datetime.timedelta(hours=1)}
    s = eventlog.append(r.line, 'task.submitted', {'commit': head, 'compensating': False}, 'submitted-1', NOW,
                        task_id=TASK, fencing_token=FENCE, lease=lease)
    return r.line + s.line


def values(paths):
    return {'contract': {'traces_to': ['SPEC-001'], 'risk': 'high', 'owner_kept_act': False, 'verification_plan': ['G0']},
            'changed_paths': paths, 'risk_rules': [{'id': 'R2', 'match': ['src/**', 'tests/**'], 'class': 'medium'}],
            'owner_kept_rules': [], 'articles': [], 'default_profiles': {'high': [{'dimension': 'functional',
                                                                                  'evidence_types': ['unit_test']}]},
            'requirement_profiles': [], 'delegation': True, 'evidence_comparison': {'weakens': False},
            'auto_accept': {}, 'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1'}


class Properties(unittest.TestCase):
    def test_the_union_of_random_task_histories(self):
        """TASK-027 AC5, TASK-027 AC4 and TASK-027 AC15: for random chains of task commits, the changed paths are the
        sorted union of the task commits' paths, never the main commit's, and one decision is appended."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                table, head = history(rng)
                want = sorted({p for c, (ps, m, paths) in table.items() if m == MINE for p in paths})
                appends = []

                def append(*a, **k):
                    appends.append(a)
                    return eventlog.append(log_for(head), a[1], a[2], a[3], a[4], task_id=k.get('task_id'))

                r = evaluation.evaluate_task(STATE_ROOT, REPO, TASK, CONTRACT, {'intent_versions': {}, 'retries': 2},
                                             values(want), [], 'aieos-core', NOW, read=reader(table),
                                             read_log=lambda root, h=head: log_for(h), append=append)
                self.assertEqual((r['result'], r['changed_paths']), ('evaluated', want), (seed, r['findings']))
                self.assertEqual(len(appends), 1)

    def test_random_read_failures_never_reach_the_append(self):
        """TASK-027 AC4, TASK-027 AC5 and TASK-027 AC15: one failing read, at a random commit and form, refuses the
        evaluation with reason "git" and the append is never called."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                table, head = history(rng)
                task_commits = [c for c, (ps, m, paths) in table.items() if m == MINE]
                fail = (rng.choice(['cat-file', 'diff-tree']), rng.choice(task_commits))
                appends = []
                want = sorted({p for c in task_commits for p in table[c][2]})
                r = evaluation.evaluate_task(STATE_ROOT, REPO, TASK, CONTRACT, {'intent_versions': {}, 'retries': 2},
                                             values(want), [], 'aieos-core', NOW, read=reader(table, fail),
                                             read_log=lambda root, h=head: log_for(h),
                                             append=lambda *a, **k: appends.append(a))
                self.assertEqual((r['result'], r['reason']), ('refused', 'git'), seed)
                self.assertEqual(appends, [])


if __name__ == '__main__':
    unittest.main()

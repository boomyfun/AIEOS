"""Property tests of aieos_bootstrap.reconcile (task TASK-031 AC14): for random well-formed logs and walks, with fixed
seeds and the standard library only, a second run appends nothing new; every DONE task is either computed by stale or
named as uncovered; and no rule result or task record of a class that is not counted ever reaches drift. Stand-ins
replace Git and the writer; no git starts and no file is opened. Each test names its criteria in its own docstring."""

import datetime
import random
import unittest
from unittest import mock

from aieos_bootstrap import drift
from aieos_bootstrap import eventlog
from aieos_bootstrap import reconcile
from aieos_bootstrap import stale

NOW = datetime.datetime(2026, 10, 14, 12, 0, 0, tzinfo=datetime.timezone.utc)
FENCE = {'epoch': 'e2', 'counter': 5}
CLASSES = ['deterministic_tool_external_ci', 'deterministic_tool_local', 'agent_declared', 'same_lineage_review']
PATHS = ['src/a.py', 'src/b.py', 'docs/c.md', 'tests/d.py']
ARTICLES = ['SEC-001', 'INV-001', 'OPS-003']
SEEDS = range(6)
ROUNDS = 25


def cid(n):
    return '%040x' % n


class Repo:
    def __init__(self, table):
        self.table = table

    def __call__(self, repo, args, *rest):
        parents, paths = self.table[args[-1]]
        if args[0] == 'cat-file':
            head = 'tree %s\n' % ('d' * 40) + ''.join('parent %s\n' % p for p in parents)
            out = (head + 'author A <a> 1 +0000\ncommitter A <a> 1 +0000\n\nm\n').encode('utf-8')
        else:
            out = b''.join(p.encode('utf-8') + b'\0' for p in paths)
        return {'exit': 0, 'out': out, 'err': b'', 'error': None}


class Memory:
    def __init__(self):
        self.log = b''
        self.appends = []

    def read_log(self, root):
        return self.log

    def append(self, root, event_type, payload, event_id, appended_at, recorder, task_id=None):
        r = eventlog.append(self.log, event_type, payload, event_id, appended_at, task_id=task_id, recorder=recorder)
        self.appends.append((event_id, r.result))
        if r.result == 'appended':
            self.log += r.line
        return r

    def add(self, event_type, payload, event_id, task_id, fencing_token=None, lease=None):
        r = eventlog.append(self.log, event_type, payload, event_id, NOW, task_id=task_id, fencing_token=fencing_token,
                            lease=lease)
        if r.result != 'appended':
            raise AssertionError(r.findings)
        self.log += r.line


def world(rnd):
    """A random first-parent history (with an occasional merge), a log of tasks some of them DONE, and the values."""
    n = rnd.randint(2, 8)
    table = {}
    for k in range(1, n + 1):
        parents = [cid(k - 1)] if k > 1 else []
        if k > 1 and rnd.random() < 0.1:
            parents.append(cid(100 + k))
        table[cid(k)] = (parents, rnd.sample(PATHS, rnd.randint(1, 2)))
    trigger = cid(n)
    mem = Memory()
    tasks = {}
    for t in range(rnd.randint(0, 4)):
        task = 'TASK-%03d' % (300 + t)
        commit = cid(rnd.randint(1, n + 2))
        for j in range(rnd.randint(1, 3)):
            mem.add('record.added', {'record_id': '%s-r%d' % (task, j), 'fact_kind': 'observation',
                                     'source_class': rnd.choice(CLASSES), 'recorder': 'x', 'subject': task,
                                     'commit': rnd.choice([commit, trigger]), 'intent_versions': {'S': 'v1'},
                                     'gate': rnd.choice(['G2', 'G3']), 'outcome': rnd.choice(['pass', 'fail']),
                                     'refers_to': rnd.choice(ARTICLES)}, '%s-e%d' % (task, j), task)
        if rnd.random() < 0.7:
            mem.add('task.submitted', {'commit': commit, 'compensating': False}, task + '-sub', task, FENCE,
                    {'task_id': task, 'fencing_token': FENCE, 'expires_at': NOW + datetime.timedelta(hours=1)})
        verdict = rnd.choice(['ACCEPT', 'ACCEPT', 'NEEDS_REWORK'])
        evaluated = rnd.choice([commit, trigger])
        mem.add('decision.acceptance', {'record_id': task + '-d', 'fact_kind': 'interpretation',
                                        'source_class': 'deterministic_tool_local', 'recorder': 'core', 'subject': task,
                                        'decision': verdict, 'evaluated_commit': evaluated}, task + '-acc', task)
        if rnd.random() < 0.8:
            mem.add('task.done', {'decision_record': rnd.choice([task + '-d', task + '-missing'])}, task + '-done', task)
        if rnd.random() < 0.8:
            tasks[task] = {'intent_current': {'S': rnd.choice(['v1', 'v2'])},
                           'read_set': [{'entry': p, 'kind': 'path', 'patterns': [p]} for p in rnd.sample(PATHS, 2)],
                           'read_set_estimate': rnd.random() < 0.2}
    results = [{'record_id': 'res-%d' % i, 'fact_kind': 'observation', 'source_class': rnd.choice(CLASSES),
                'recorder': 'ci', 'subject': trigger, 'commit': trigger, 'gate': 'G3',
                'outcome': rnd.choice(['pass', 'fail']), 'refers_to': rnd.choice(ARTICLES)}
               for i in range(rnd.randint(0, 4))]
    values = {'articles': [{'id': a, 'scope': ['**']} for a in ARTICLES], 'tasks': tasks}
    return table, trigger, mem, values, results


def run(table, trigger, mem, values, results, max_commits):
    return reconcile.reconcile('/s', '/r', trigger, values, results, 'core', NOW, max_commits=max_commits,
                               read=Repo(table), read_log=mem.read_log, append=mem.append)


def done_ids(mem):
    out = set()
    for line in mem.log.split(b'\n'):
        if b'"task.done"' in line:
            out.add(line.split(b'"task_id":"')[1].split(b'"')[0].decode('ascii'))
    return out


class Properties(unittest.TestCase):

    def test_a_second_run_appends_nothing_new(self):
        """TASK-031 AC8, AC14: over random worlds, a second run at the same trigger appends nothing."""
        total = 0
        for seed in SEEDS:
            rnd = random.Random(seed)
            for _ in range(ROUNDS):
                table, trigger, mem, values, results = world(rnd)
                bound = rnd.randint(1, 10)
                first = run(table, trigger, mem, values, results, bound)
                self.assertEqual(first['result'], 'reconciled', first)
                total += len(first['appended'])
                before = mem.log
                second = run(table, trigger, mem, values, results, bound)
                self.assertEqual((second['result'], second['appended']), ('reconciled', []), second)
                self.assertEqual(mem.log, before)
        self.assertGreater(total, 0)

    def test_every_done_task_is_computed_or_uncovered(self):
        """TASK-031 AC2, AC3, AC4, AC14: every task the log shows DONE is either given to stale or named as
        uncovered."""
        seen = computed_any = 0
        for seed in SEEDS:
            rnd = random.Random(seed)
            for _ in range(ROUNDS):
                table, trigger, mem, values, results = world(rnd)
                with mock.patch.object(stale, 'stale', wraps=stale.stale) as spy:
                    res = run(table, trigger, mem, values, results, rnd.randint(1, 10))
                computed = {c[0][0]['task_id'] for c in spy.call_args_list}
                computed_any += len(computed)
                named = {u['ref'] for u in res['uncovered']}
                for task in done_ids(mem):
                    seen += 1
                    self.assertTrue(task in computed or task in named, (seed, task, res))
                    self.assertFalse(task in computed and any(
                        u['ref'] == task and u['detail'] in ('accepted commit not reached', 'merge commit on the walk',
                                                             'no facts given') for u in res['uncovered']))
        self.assertGreater(seen, 0)
        self.assertGreater(computed_any, 0)

    def test_no_class_left_out_reaches_drift(self):
        """TASK-031 AC5, AC6, AC14: drift's rule results and task records are only of the counted classes, and each
        entry left out is named."""
        calls = 0
        for seed in SEEDS:
            rnd = random.Random(seed)
            for _ in range(ROUNDS):
                table, trigger, mem, values, results = world(rnd)
                with mock.patch.object(drift, 'violations', wraps=drift.violations) as spy:
                    res = run(table, trigger, mem, values, results, 10)
                for c in spy.call_args_list:
                    calls += 1
                    given = c[0][0]
                    for r in given['rule_results'] + given['task_records']:
                        self.assertIn(r['source_class'], reconcile.COUNTED)
                named = {u['ref'] for u in res['uncovered'] if u['detail'] == 'source class not counted'}
                for r in results:
                    if r['source_class'] not in reconcile.COUNTED and spy.called:
                        self.assertIn(r['record_id'], named)
        self.assertGreater(calls, 0)


if __name__ == '__main__':
    unittest.main()

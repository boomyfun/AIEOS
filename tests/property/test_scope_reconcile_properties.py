"""Property tests of aieos_bootstrap.scope_reconcile (task TASK-034 AC15): for random well-formed stand-in repositories
and logs (standard library only, fixed seeds), the result equals what scope_drift.claims gives on the facts read, the
policy and the workflow are read only at the first parent, and a second run appends nothing new. No file is opened.
Each test names its criteria in its own docstring."""

import datetime
import hashlib
import random
import re
import unittest

from aieos_bootstrap import eventlog, gitread, scope_drift, scope_reconcile

NOW = datetime.datetime(2026, 10, 15, 9, 0, 0, tzinfo=datetime.timezone.utc)
REC = 'aieos-core (property)'
POLICY_TEXT = '\n'.join([
    '## 3. The rules', '', '```yaml', 'policy_version: v3',
    'non_task_paths: ["docs/History/**", "docs/Lessons/**"]', 'risk_rules:',
    '  - match: { paths: ["docs/**", "*.md"] }', '    risk: low',
    '  - match: { paths: ["src/**", "tests/**"] }', '    risk: medium',
    '  - match: { component_tags: [governor] }', '    risk: high',
    '  - match: { paths: [".github/**"] }', '    risk: critical', '```', ''])
WORKFLOW_TEXT = "x:\n  EVALUATOR = ['.github/**', 'src/aieos_bootstrap/**', 'tests/unit/**']\n"
PATHS = ['docs/History/a.md', 'docs/Lessons/b.md', 'docs/spec.md', 'src/aieos_bootstrap/m.py', 'src/other.py',
         'tests/unit/t.py', '.github/w.yml', 'README.md', 'docs/specs/risk-rules-gov-aieos.md']
TASKS = ['TASK-090', 'TASK-091']


def oid(*parts):
    return hashlib.sha256('\n'.join(parts).encode('utf-8')).hexdigest()


class Repo:
    def __init__(self):
        self.objects, self.paths, self.reads = {}, {}, []

    def tree(self, files):
        entries, sub = {}, {}
        for path, text in files.items():
            head, _, rest = path.partition('/')
            if rest:
                sub.setdefault(head, {})[rest] = text
            else:
                bid = oid('blob', path, text)
                self.objects[bid] = text.encode('utf-8')
                entries[head] = ('blob', bid)
        for name, inner in sub.items():
            entries[name] = ('tree', self.tree(inner))
        listing = ''.join('%s %s %s\t%s\n' % ('040000' if k == 'tree' else '100644', k, i, n)
                          for n, (k, i) in sorted(entries.items()))
        tid = oid('tree', listing)
        self.objects[tid] = listing.encode('utf-8')
        return tid

    def commit(self, name, parents, files, paths, trailers):
        cid = oid('commit', name)
        tail = '\n' + '\n'.join('AIEOS-Task: %s' % t for t in trailers) + '\n' if trailers else ''
        msg = 'Change %s\n' % name + tail
        head = 'tree %s\n' % self.tree(files) + ''.join('parent %s\n' % p for p in parents)
        self.objects[cid] = (head + 'author A <a> 1 +0000\ncommitter A <a> 1 +0000\n\n' + msg).encode('utf-8')
        self.paths[cid] = paths
        return cid, head.split('\n')[0].split()[1]

    def __call__(self, repo, args, *rest):
        self.reads.append(list(args))
        if args[:2] == ['cat-file', '-p'] and args[2] in self.objects:
            return {'exit': 0, 'out': self.objects[args[2]], 'err': b'', 'error': None}
        if args[:-1] == gitread.DIFF_TREE and args[-1] in self.paths:
            return {'exit': 0, 'out': b''.join(p.encode('utf-8') + b'\0' for p in self.paths[args[-1]]), 'err': b'',
                    'error': None}
        return {'exit': 128, 'out': b'', 'err': b'fatal', 'error': None}


class Memory:
    def __init__(self):
        self.log = b''

    def read_log(self, root):
        return self.log

    def append(self, root, event_type, payload, event_id, appended_at, recorder, task_id=None, fencing_token=None):
        r = eventlog.append(self.log, event_type, payload, event_id, appended_at, task_id=task_id)
        if r.result == 'appended':
            self.log += r.line
        return r


def random_world(rng, k):
    repo, mem = Repo(), Memory()
    base = {scope_reconcile.POLICY_PATH: POLICY_TEXT, scope_reconcile.WORKFLOW_PATH: WORKFLOW_TEXT}
    p, _ = repo.commit('p%d' % k, [], base, ['README.md'], [])
    loose = POLICY_TEXT.replace('"docs/Lessons/**"]', '"docs/Lessons/**", "src/**"]')
    child = dict(base, **{scope_reconcile.POLICY_PATH: loose})
    paths = rng.sample(PATHS, rng.randint(1, 4))
    trailers = rng.sample(TASKS, rng.randint(0, 1))
    contracts = {}
    for t in trailers:
        data = ('contract %s %d' % (t, k)).encode('utf-8')
        if rng.random() < 0.8:
            r = eventlog.append(mem.log, 'task.approved', {'contract_version': 'v1',
                                                           'contract_hash': hashlib.sha256(data).hexdigest(),
                                                           'approval_record': 'ap'}, 'e-%s' % t, NOW, task_id=t)
            mem.log += r.line
        if rng.random() < 0.8:
            contracts[t] = {'contract_bytes': data, 'write_set': rng.sample(PATHS, rng.randint(1, 5))}
    c, ctree = repo.commit('c%d' % k, [p], child, paths, trailers)
    return repo, mem, p, c, ctree, paths, trailers, contracts


class Properties(unittest.TestCase):
    def test_the_result_equals_claims_on_the_facts_read(self):
        """TASK-034 AC15, TASK-034 AC6 and TASK-034 AC7: the event is appended exactly when claims, given the facts
        read at the first parent and the matched contracts, returns one; detected and exempt agree."""
        rng = random.Random(3401)
        for k in range(200):
            repo, mem, p, c, ctree, paths, trailers, contracts = random_world(rng, k)
            approved = {}
            for t in trailers:
                if contracts.get(t) and ('e-%s' % t).encode('utf-8') in mem.log:
                    approved[t] = contracts[t]['write_set']
            want = scope_drift.claims({'commit': c, 'parents': 1, 'trailer_tasks': trailers, 'changed_paths': paths,
                                       'contracts': approved, 'non_task': scope_drift.non_task_list(POLICY_TEXT),
                                       'risk_rules': scope_reconcile.rules_from_policy(POLICY_TEXT),
                                       'evaluator': scope_reconcile.evaluator_from_workflow(WORKFLOW_TEXT),
                                       'constitution_path': scope_reconcile.CONSTITUTION_PATH,
                                       'policy_path': scope_reconcile.POLICY_PATH})
            out = scope_reconcile.reconcile_scope('/s', '/r', c, {'contracts': contracts}, REC, NOW, read=repo,
                                                  read_log=mem.read_log, append=mem.append)
            self.assertEqual(out['result'], 'reconciled', out)
            self.assertEqual((out['detected'], out['exempt']), (want['detected'], want['exempt']), k)
            self.assertEqual(out['appended'], [e['event_id'] for e in want['events']], k)

    def test_the_files_are_read_only_at_the_first_parent(self):
        """TASK-034 AC15 and TASK-034 AC3: the commit's own tree (which holds a looser policy) is never read."""
        rng = random.Random(3402)
        for k in range(100):
            repo, mem, p, c, ctree, paths, trailers, contracts = random_world(rng, k)
            out = scope_reconcile.reconcile_scope('/s', '/r', c, {'contracts': contracts}, REC, NOW, read=repo,
                                                  read_log=mem.read_log, append=mem.append)
            self.assertEqual(out['result'], 'reconciled', out)
            self.assertNotIn(['cat-file', '-p', ctree], repo.reads)

    def test_a_second_run_appends_nothing_new(self):
        """TASK-034 AC15 and TASK-034 AC7: a rerun with the same facts appends nothing and reports the event as a
        duplicate."""
        rng = random.Random(3403)
        total = 0
        for k in range(100):
            repo, mem, p, c, ctree, paths, trailers, contracts = random_world(rng, k)
            first = scope_reconcile.reconcile_scope('/s', '/r', c, {'contracts': contracts}, REC, NOW, read=repo,
                                                    read_log=mem.read_log, append=mem.append)
            log = mem.log
            second = scope_reconcile.reconcile_scope('/s', '/r', c, {'contracts': contracts}, REC, NOW, read=repo,
                                                     read_log=mem.read_log, append=mem.append)
            self.assertEqual(mem.log, log)
            self.assertEqual((second['appended'], second['duplicate']), ([], first['appended']))
            total += len(first['appended'])
        self.assertGreater(total, 0)


class Naming(unittest.TestCase):
    def test_every_test_names_its_criteria(self):
        """TASK-035 AC7: every test function of this module names "TASK-034 ACn" or "TASK-035 ACn" (at least one) in
        its own docstring, and no other task's AC in qualified form; the loaded classes' docstrings are read, not this
        file."""
        tests = [(cls.__name__, name, getattr(cls, name).__doc__ or '') for cls in list(globals().values())
                 if isinstance(cls, type) and issubclass(cls, unittest.TestCase) for name in vars(cls)
                 if name.startswith('test_')]
        self.assertGreater(len(tests), 3)
        for cls_name, name, doc in tests:
            named = set(re.findall(r'(TASK-\d+) AC', doc))
            self.assertTrue(named, (cls_name, name))
            self.assertLessEqual(named, {'TASK-034', 'TASK-035'}, (cls_name, name))


if __name__ == '__main__':
    unittest.main()

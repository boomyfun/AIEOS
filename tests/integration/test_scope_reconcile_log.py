"""Integration test of aieos_bootstrap.scope_reconcile (task TASK-034 AC12): end-to-end runs over a stand-in repository
(commits, trees and blobs answered in gitread.run's result form) and an event log kept in memory and appended by
eventlog.append, with scope_drift as it is; and one case that runs the module's base read with gitread.run over this
repository's own history (decision D-714 C1; it needs the repository's full history, as TASK-024's integration test
does). No file is opened or written. Each test names its criteria in its own docstring."""

import datetime
import hashlib
import pathlib
import unittest

from aieos_bootstrap import eventlog, gitread, records, scope_reconcile

ROOT = str(pathlib.Path(__file__).resolve().parents[2])
FIXC = 'fc5c4e5ca8bf27e7ce205d633f4bd4d5b7894ef8'
FIXP = '57bbe3780ef4108c5d3acf39ac184555c689b9aa'
NOW = datetime.datetime(2026, 10, 15, 9, 0, 0, tzinfo=datetime.timezone.utc)
REC = 'aieos-core (integration)'
POLICY_TEXT = '\n'.join([
    '# The risk rules', '', '## 3. The rules', '', '```yaml', 'policy_version: v3',
    'non_task_paths: ["docs/History/**", "docs/Progress/**", "docs/Deferred/**", "docs/Lessons/**"]', 'risk_rules:',
    '  - match: { paths: ["docs/**", "*.md"] }', '    risk: low',
    '  - match: { paths: ["src/**", "tests/**"] }', '    risk: medium',
    '  - match: { component_tags: [governor, verification] }', '    risk: high',
    '  - match: { paths: [".github/**"] }', '    risk: critical', '```', ''])
EVAL_LINES = ["    EVALUATOR = ['.github/**', 'src/aieos_bootstrap/**',", "                 'tests/unit/**']"]
WORKFLOW_TEXT = '\n'.join(['steps:'] + EVAL_LINES + ['second:'] + EVAL_LINES + [''])
CONTRACT = b'task: TASK-095\n'


def oid(*parts):
    return hashlib.sha1('\n'.join(parts).encode('utf-8')).hexdigest()


class Repo:
    """A stand-in repository answering cat-file -p and the pinned diff-tree form."""

    def __init__(self):
        self.objects, self.paths = {}, {}

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

    def commit(self, name, parents, paths, trailer=None):
        files = {scope_reconcile.POLICY_PATH: POLICY_TEXT, scope_reconcile.WORKFLOW_PATH: WORKFLOW_TEXT}
        cid = oid('commit', name)
        msg = 'Change %s\n' % name + ('\n%s\n' % trailer if trailer else '')
        head = 'tree %s\n' % self.tree(files) + ''.join('parent %s\n' % p for p in parents)
        self.objects[cid] = (head + 'author A <a> 1 +0000\ncommitter A <a> 1 +0000\n\n' + msg).encode('utf-8')
        self.paths[cid] = paths
        return cid

    def __call__(self, repo, args, *rest):
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
        r = eventlog.append(self.log, event_type, payload, event_id, appended_at, task_id=task_id,
                            fencing_token=fencing_token)
        if r.result == 'appended':
            self.log += r.line
        return r


class EndToEnd(unittest.TestCase):
    def test_a_claim_is_appended_once_and_the_others_give_no_event(self):
        """TASK-034 AC12, TASK-034 AC2, TASK-034 AC5, TASK-034 AC7: a commit with no trailer changing src/ is a claim,
        appended once to a log with no finding; a rerun gives "duplicate"; a records-only commit is exempt; a task
        commit held by its approved contract is not detected; a merge is uncovered; none of these appends."""
        repo, mem = Repo(), Memory()
        r = eventlog.append(mem.log, 'task.approved', {'contract_version': 'v1',
                                                       'contract_hash': hashlib.sha256(CONTRACT).hexdigest(),
                                                       'approval_record': 'ap-1'}, 'e-ap', NOW, task_id='TASK-095')
        mem.log += r.line
        root = repo.commit('root', [], ['README.md'])
        claim = repo.commit('claim', [root], ['src/aieos_bootstrap/new.py'])
        exempt = repo.commit('exempt', [claim], ['docs/History/2026-10/h.md'])
        task = repo.commit('task', [exempt], ['src/aieos_bootstrap/x.py'], 'AIEOS-Task: TASK-095')
        merge = repo.commit('merge', [task, claim], ['src/aieos_bootstrap/x.py'])
        values = {'contracts': {'TASK-095': {'contract_bytes': CONTRACT, 'write_set': ['src/aieos_bootstrap/x.py']}}}

        def go(commit):
            return scope_reconcile.reconcile_scope('/state', '/repo', commit, values, REC, NOW, read=repo,
                                                   read_log=mem.read_log, append=mem.append)
        first = go(claim)
        eid = hashlib.sha256('\n'.join(('drift.detected', 'scope', claim)).encode('utf-8')).hexdigest()
        self.assertEqual((first['result'], first['appended']), ('reconciled', [eid]), first)
        report = records.check_log(mem.log)
        self.assertEqual(report.findings(), [])
        last = report.lines[-1].event
        self.assertEqual((last['type'], last.get('task_id')), ('drift.detected', None))
        self.assertEqual(last['payload'], {'paths': ['src/aieos_bootstrap/new.py'], 'entities': []})
        self.assertEqual(go(claim)['duplicate'], [eid])
        before = mem.log
        out_exempt, out_task, out_merge = go(exempt), go(task), go(merge)
        self.assertEqual((out_exempt['detected'], out_exempt['exempt']), (True, True))
        self.assertEqual(out_task['detected'], False)
        self.assertEqual(out_task['facts']['contracts'], {'TASK-095': hashlib.sha256(CONTRACT).hexdigest()})
        self.assertEqual(out_merge['uncovered'], [{'ref': merge, 'detail': 'not one parent'}])
        self.assertEqual(mem.log, before)


class RepositoryHistory(unittest.TestCase):
    def test_the_base_read_over_this_repositorys_history(self):
        """TASK-034 AC12 and TASK-034 AC3 (decision D-714 C1): at fc5c4e5c, a one-parent commit of main whose first
        parent 57bbe378 holds policy v3, the module's base read with gitread.run reads and decodes the policy and the
        workflow, the rules number eleven, and the evaluator list equals the workflow's literal at that parent."""
        r = gitread.run(ROOT, ['cat-file', '-p', FIXC])
        self.assertIsNone(r['error'])
        parsed = gitread.parse_commit(r['out'])
        self.assertEqual(parsed['parents'], [FIXP])
        base = scope_reconcile.read_base(ROOT, FIXP)
        self.assertIn('\npolicy_version: v3\n', base['policy'])
        self.assertEqual(len(scope_reconcile.rules_from_policy(base['policy'])), 11)
        self.assertTrue(all(set(x) == {'match', 'class'} and x['class'] is not None
                            for x in scope_reconcile.rules_from_policy(base['policy'])))
        evaluator = scope_reconcile.evaluator_from_workflow(base['workflow'])
        self.assertEqual(evaluator, ['.github/**', 'src/aieos_bootstrap/**', 'tests/conformance/**',
                                     'docs/pre-genesis/conformance-scenarios-initial.md', 'docs/records/**',
                                     'tests/unit/**', 'tests/integration/**', 'tests/property/**', 'tests/run_tests.py',
                                     '**/pyproject.toml', '**/setup.cfg', '**/setup.py', '**/requirements*.txt'])
        r2 = gitread.run(ROOT, ['cat-file', '-t', base['policy_blob']])
        self.assertEqual(r2['out'].strip(), b'blob')


if __name__ == '__main__':
    unittest.main()

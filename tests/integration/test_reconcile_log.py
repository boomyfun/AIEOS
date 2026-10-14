"""Integration test of aieos_bootstrap.reconcile (task TASK-031 AC14): an end-to-end run over a stand-in repository
and an event log kept in memory and appended by eventlog.append, with stale, drift and the mapping helper as they are.
No git starts and no file is opened. Each test names its criteria in its own docstring."""

import datetime
import hashlib
import unittest

from aieos_bootstrap import eventlog
from aieos_bootstrap import reconcile
from aieos_bootstrap import records

TREE = 'c' * 40
NOW = datetime.datetime(2026, 10, 14, 11, 0, 0, tzinfo=datetime.timezone.utc)
FENCE = {'epoch': 'e1', 'counter': 3}
REC = 'aieos-core (integration)'
STEPS = {'SEC-001 secret scan': ['SEC-001'], 'deterministic_rule (INV-001, INV-002, INV-004)': ['INV-001', 'INV-002']}


def cid(n):
    return '%040x' % n


def digest(*parts):
    return hashlib.sha256('\n'.join(parts).encode('utf-8')).hexdigest()


class Repo:
    """Commits {id: (parents, paths)} answered in gitread.run's result form."""

    def __init__(self, table):
        self.table = table

    def __call__(self, repo, args, *rest):
        parents, paths = self.table[args[-1]]
        if args[0] == 'cat-file':
            head = 'tree %s\n' % TREE + ''.join('parent %s\n' % p for p in parents)
            out = (head + 'author A <a> 1 +0000\ncommitter A <a> 1 +0000\n\nm\n').encode('utf-8')
        else:
            out = b''.join(p.encode('utf-8') + b'\0' for p in paths)
        return {'exit': 0, 'out': out, 'err': b'', 'error': None}


class Memory:
    """The event log as bytes in memory; append decides with eventlog.append as the real writer does."""

    def __init__(self):
        self.log = b''

    def read_log(self, root):
        return self.log

    def append(self, root, event_type, payload, event_id, appended_at, recorder, task_id=None):
        r = eventlog.append(self.log, event_type, payload, event_id, appended_at, task_id=task_id, recorder=recorder)
        if r.result == 'appended':
            self.log += r.line
        return r

    def add(self, event_type, payload, event_id, task_id, fencing_token=None, lease=None):
        r = eventlog.append(self.log, event_type, payload, event_id, NOW, task_id=task_id, fencing_token=fencing_token,
                            lease=lease)
        if r.result != 'appended':
            raise AssertionError(r.findings)
        self.log += r.line


def history():
    """Main: cid(1) root; cid(2) TASK-201's commit, accepted; cid(3) another change to its read-set; cid(4) the trigger,
    a change under src/."""
    return {cid(1): ([], ['README.md']), cid(2): ([cid(1)], ['src/a.py']), cid(3): ([cid(2)], ['docs/spec.md']),
            cid(4): ([cid(3)], ['src/b.py'])}


def accepted_task(mem, task, commit):
    mem.add('record.added', {'record_id': 'r-' + task, 'fact_kind': 'observation',
                             'source_class': 'deterministic_tool_external_ci', 'recorder': 'ci', 'subject': task,
                             'commit': commit, 'intent_versions': {'SPEC-004': 'v3'}, 'gate': 'G2', 'outcome': 'pass'},
            'e-rec-' + task, task)
    mem.add('task.submitted', {'commit': commit, 'compensating': False}, 'e-sub-' + task, task, FENCE,
            {'task_id': task, 'fencing_token': FENCE, 'expires_at': NOW + datetime.timedelta(hours=1)})
    mem.add('decision.acceptance', {'record_id': 'd-' + task, 'fact_kind': 'interpretation',
                                    'source_class': 'deterministic_tool_local', 'recorder': REC, 'subject': task,
                                    'decision': 'ACCEPT', 'evaluated_commit': commit}, 'e-acc-' + task, task)
    mem.add('task.done', {'decision_record': 'd-' + task}, 'e-done-' + task, task)


class EndToEnd(unittest.TestCase):

    def test_a_run_appends_stale_evidence_and_a_violation_and_a_rerun_appends_nothing(self):
        """TASK-031 AC2 to AC8, AC10, AC14: one DONE task gets two evidence.stale events (its read-set met by a later
        commit, its intent version changed), the trigger's failing SEC-001 gives one violation.detected, the
        resulting log has no finding, and a second run appends nothing new."""
        mem = Memory()
        accepted_task(mem, 'TASK-201', cid(2))
        steps = [{'name': 'SEC-001 secret scan', 'conclusion': 'failure'},
                 {'name': 'deterministic_rule (INV-001, INV-002, INV-004)', 'conclusion': 'success'},
                 {'name': 'unit tests', 'conclusion': 'success'}]
        mapped = reconcile.rule_results_from_steps(steps, STEPS, cid(4), 'ci')
        self.assertEqual(len(mapped['records']), 3)
        values = {'articles': [{'id': 'SEC-001', 'scope': ['**']}, {'id': 'INV-001', 'scope': ['src/**']},
                               {'id': 'OPS-003', 'scope': ['docs/**']}],
                  'tasks': {'TASK-201': {'intent_current': {'SPEC-004': 'v4'},
                                         'read_set': [{'entry': 'docs/spec.md', 'kind': 'path', 'patterns': ['docs/spec.md']}],
                                         'read_set_estimate': False}}}
        repo = Repo(history())
        first = reconcile.reconcile('/state', '/repo', cid(4), values, mapped['records'], REC, NOW, read=repo,
                                    read_log=mem.read_log, append=mem.append)
        self.assertEqual(first['result'], 'reconciled', first)
        self.assertEqual(first['appended'], [digest('evidence.stale', 'TASK-201', cid(4), 'commit'),
                                             digest('evidence.stale', 'TASK-201', cid(4), 'intent_version'),
                                             digest('violation.detected', cid(4), 'SEC-001')])
        report = records.check_log(mem.log)
        self.assertEqual(report.findings(), [])
        kinds = [(line.event['type'], line.event.get('task_id')) for line in report.lines]
        self.assertEqual(kinds[-3:], [('evidence.stale', 'TASK-201'), ('evidence.stale', 'TASK-201'),
                                      ('violation.detected', None)])
        before = mem.log
        second = reconcile.reconcile('/state', '/repo', cid(4), values, mapped['records'], REC, NOW, read=repo,
                                     read_log=mem.read_log, append=mem.append)
        self.assertEqual((second['result'], second['appended']), ('reconciled', []))
        self.assertEqual(second['duplicate'], [digest('violation.detected', cid(4), 'SEC-001')])
        self.assertEqual(mem.log, before)

    def test_uncovered_cases_end_to_end(self):
        """TASK-031 AC2, AC3, AC4, AC5, AC14: a task not reached by the bound, a task without facts and an agent's
        rule result are named, and nothing is appended for them."""
        mem = Memory()
        accepted_task(mem, 'TASK-202', cid(1))
        accepted_task(mem, 'TASK-203', cid(3))
        results = [{'record_id': 'agent-1', 'fact_kind': 'observation', 'source_class': 'agent_declared',
                    'recorder': 'agent', 'subject': cid(4), 'commit': cid(4), 'gate': 'G3', 'outcome': 'pass',
                    'refers_to': 'SEC-001'}]
        out = reconcile.reconcile('/state', '/repo', cid(4), {'articles': [{'id': 'SEC-001', 'scope': ['**']}],
                                                             'tasks': {}},
                                  results, REC, NOW, max_commits=2, read=Repo(history()), read_log=mem.read_log,
                                  append=mem.append)
        self.assertEqual(out['result'], 'reconciled', out)
        self.assertEqual(out['appended'], [])
        pairs = {(u['ref'], u['detail']) for u in out['uncovered']}
        self.assertTrue({('TASK-202', 'accepted commit not reached'), ('TASK-203', 'no facts given'),
                         ('agent-1', 'source class not counted'), ('SEC-001', 'no rule result')} <= pairs, pairs)


if __name__ == '__main__':
    unittest.main()

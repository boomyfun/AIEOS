"""Unit tests of aieos_bootstrap.reconcile (task TASK-031, its rules R1 to R10); every rule has at least one passing
case and one failing case. The Git reader and the writer's functions are replaced by stand-ins: the reader answers
from a table of commits and their changed paths, and the stand-in writer keeps a log as bytes, deciding each append
with eventlog.append as the real writer does, so no git starts and no file is touched here. Each test names the
criteria it stands for in its own docstring."""

import ast
import datetime
import hashlib
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import drift
from aieos_bootstrap import eventlog
from aieos_bootstrap import gitread
from aieos_bootstrap import reconcile
from aieos_bootstrap import records
from aieos_bootstrap import stale
from aieos_bootstrap import writer

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE = ROOT / 'src' / 'aieos_bootstrap' / 'reconcile.py'
FS_ROOT = str(ROOT / 'no-such-state-root')
REPO = str(ROOT)
TREE = 'b' * 40
TASK = 'TASK-101'
TASK2 = 'TASK-102'
REC = 'aieos-core'
NOW = datetime.datetime(2026, 10, 14, 10, 0, 0, tzinfo=datetime.timezone.utc)
FENCE = {'epoch': 'e0', 'counter': 1}
H1 = datetime.timedelta(hours=1)
MSG = 'Work\n\nThe body.\n'


def cid(n):
    return '%040x' % n


def ok(out):
    return {'exit': 0, 'out': out, 'err': b'', 'error': None}


def commit_bytes(parents):
    head = 'tree %s\n' % TREE + ''.join('parent %s\n' % p for p in parents)
    head += 'author Tester <tester> 1700000000 +0000\ncommitter Tester <tester> 1700000000 +0000\n\n'
    return (head + MSG).encode('utf-8')


class Repo:
    """A stand-in for gitread.run: commits from a table {id: (parents, paths)}; ``fail`` maps (form, id) to the result
    (or exception) given instead, the form being "cat-file" or "diff-tree"."""

    def __init__(self, table, fail=None):
        self.table = table
        self.fail = fail or {}
        self.calls = []

    def __call__(self, repo, args, *rest):
        self.calls.append(list(args))
        key = (args[0], args[-1])
        if key in self.fail:
            given = self.fail[key]
            if isinstance(given, BaseException):
                raise given
            return given
        parents, paths = self.table[args[-1]]
        if args[0] == 'cat-file':
            return ok(commit_bytes(parents))
        return ok(b''.join(p.encode('utf-8') + b'\0' for p in paths))


def chain():
    """cid(1) the root; cid(2) TASK-101's submitted and accepted commit; cid(3) a later commit, the trigger."""
    return {cid(1): ([], ['docs/a.md']),
            cid(2): ([cid(1)], ['src/x.py']),
            cid(3): ([cid(2)], ['src/y.py'])}


class Log:
    """A stand-in writer: read_log gives the bytes, append decides with eventlog.append (no lease) and keeps the line."""

    def __init__(self, log=b''):
        self.log = log
        self.appends = []
        self.reads = 0

    def read_log(self, root):
        self.reads += 1
        return self.log

    def append(self, root, event_type, payload, event_id, appended_at, recorder, task_id=None, fencing_token=None):
        self.appends.append((event_type, event_id, task_id, fencing_token))
        r = eventlog.append(self.log, event_type, payload, event_id, appended_at, task_id=task_id,
                            fencing_token=fencing_token, recorder=recorder)
        if r.result == 'appended':
            self.log += r.line
        return r

    def add(self, event_type, payload, event_id, task_id=TASK, fencing_token=None, lease=None):
        r = eventlog.append(self.log, event_type, payload, event_id, NOW, task_id=task_id, fencing_token=fencing_token,
                            lease=lease)
        if r.result != 'appended':
            raise AssertionError((r.result, r.findings))
        self.log += r.line
        return self


def record(rid, commit, task=TASK, **over):
    r = {'record_id': rid, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_external_ci',
         'recorder': 'ci', 'subject': task, 'commit': commit, 'intent_versions': {'SPEC-001': 'v1'}, 'gate': 'G2',
         'outcome': 'pass'}
    r.update(over)
    return r


def decision(rid, commit, task=TASK, verdict='ACCEPT', **over):
    d = {'record_id': rid, 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_local', 'recorder': REC,
         'subject': task, 'decision': verdict, 'evaluated_commit': commit}
    d.update(over)
    return d


def done_task(log, task=TASK, commit=None, verdict='ACCEPT', drop=(), rid=None):
    """A task with a record, a submission, an acceptance decision and task.done, all for ``commit``."""
    commit = commit or cid(2)
    rid = rid or 'dec-' + task
    log.add('record.added', record('r-' + task, commit, task), 'rec-' + task, task_id=task)
    log.add('task.submitted', {'commit': commit, 'compensating': False}, 'sub-' + task, task_id=task,
            fencing_token=FENCE, lease={'task_id': task, 'fencing_token': FENCE, 'expires_at': NOW + H1})
    log.add('decision.acceptance', decision(rid, commit, task, verdict, **{k: None for k in ()}), 'acc-' + task,
            task_id=task)
    log.add('task.done', {'decision_record': rid}, 'done-' + task, task_id=task)
    return log


def facts(entry='src/y.py', current='v2'):
    return {'intent_current': {'SPEC-001': current},
            'read_set': [{'entry': entry, 'kind': 'path', 'patterns': [entry]}], 'read_set_estimate': False}


def rule(article, outcome, commit=None, source='deterministic_tool_external_ci', rid=None):
    commit = commit or cid(3)
    return {'record_id': rid or 'res-%s-%s' % (article, outcome), 'fact_kind': 'observation', 'source_class': source,
            'recorder': 'ci', 'subject': commit, 'commit': commit, 'gate': 'G3', 'outcome': outcome,
            'refers_to': article}


ARTICLES = [{'id': 'SEC-001', 'scope': ['**']}, {'id': 'INV-001', 'scope': ['src/**']}]


def values(tasks=None):
    return {'articles': ARTICLES, 'tasks': {TASK: facts()} if tasks is None else tasks}


def run(log, repo=None, trigger=None, vals=None, results=None, **kw):
    repo = repo if repo is not None else Repo(chain())
    return reconcile.reconcile(FS_ROOT, REPO, trigger or cid(3), values() if vals is None else vals,
                               [rule('SEC-001', 'fail'), rule('INV-001', 'pass')] if results is None else results,
                               REC, NOW, read=repo, read_log=log.read_log, append=log.append, **kw)


def digest(*parts):
    return hashlib.sha256('\n'.join(parts).encode('utf-8')).hexdigest()


def unc(res):
    return {(u['ref'], u['detail']) for u in res['uncovered']}


class R1Arguments(unittest.TestCase):

    def test_well_formed_arguments_are_accepted(self):
        """TASK-031 AC1: well-formed arguments reach the log."""
        log = done_task(Log())
        res = run(log)
        self.assertEqual(res['result'], 'reconciled', res)
        self.assertEqual(log.reads, 1)

    def test_each_wrong_argument_is_refused_before_any_read(self):
        """TASK-031 AC1, AC10: each wrong argument gives "refused", reason "argument", a finding naming it, and
        nothing read or appended."""
        good = dict(root=FS_ROOT, repo=REPO, trigger_commit=cid(3), values=values(), rule_results=[], recorder=REC,
                    now=NOW, max_commits=10)
        bad = [('root', ''), ('repo', None), ('trigger_commit', 'C' * 40), ('trigger_commit', 'a' * 39),
               ('values', {'articles': []}), ('values', {'articles': {}, 'tasks': {}}),
               ('values', {'articles': [], 'tasks': []}),
               ('values', {'articles': [], 'tasks': {'T-1': facts()}}),
               ('values', {'articles': [], 'tasks': {TASK: {'intent_current': {}}}}),
               ('values', {'articles': [], 'tasks': {TASK: dict(facts(), intent_current={'S': '1'})}}),
               ('values', {'articles': [], 'tasks': {TASK: dict(facts(), read_set=[{'entry': 'x'}])}}),
               ('values', {'articles': [], 'tasks': {TASK: dict(facts(), read_set_estimate=1)}}),
               ('rule_results', [1]), ('rule_results', {}), ('recorder', ''),
               ('now', datetime.datetime(2026, 10, 14)),
               ('now', datetime.datetime(2026, 10, 14, tzinfo=datetime.timezone(datetime.timedelta(hours=7)))),
               ('max_commits', 0), ('max_commits', 10001), ('max_commits', True), ('max_commits', 1.0)]
        for name, value in bad:
            log = Log()
            repo = Repo(chain())
            args = dict(good, **{name: value})
            res = reconcile.reconcile(read=repo, read_log=log.read_log, append=log.append, **args)
            self.assertEqual((res['result'], res['reason']), ('refused', 'argument'), (name, value))
            self.assertTrue(any(name.split('_')[0] in f for f in res['findings']), (name, res['findings']))
            self.assertEqual((log.reads, repo.calls, log.appends), (0, [], []), name)

    def test_defaults_are_bound_at_call_time(self):
        """TASK-031 AC1: read, read_log and append default to gitread.run, writer.read_log and writer.append_event."""
        log = done_task(Log())
        with mock.patch.object(gitread, 'run', Repo(chain())), \
                mock.patch.object(writer, 'read_log', log.read_log), \
                mock.patch.object(writer, 'append_event', log.append):
            res = reconcile.reconcile(FS_ROOT, REPO, cid(3), values(), [], REC, NOW)
        self.assertEqual(res['result'], 'reconciled', res)
        self.assertEqual(log.reads, 1)
        self.assertTrue(log.appends)


class R2Log(unittest.TestCase):

    def test_a_done_task_is_found_and_computed(self):
        """TASK-031 AC2, AC4: a task with task.done and an ACCEPT decision record gets a stale computation."""
        log = done_task(Log())
        res = run(log)
        types = [a[0] for a in log.appends]
        self.assertEqual(types.count('evidence.stale'), 2)
        self.assertNotIn(TASK, {u['ref'] for u in res['uncovered']})

    def test_each_gap_in_the_decision_record_is_uncovered(self):
        """TASK-031 AC2: an absent decision record, one that is not ACCEPT and one without evaluated_commit leave the
        task uncovered and give no stale computation."""
        cases = []
        log = Log()
        log.add('task.done', {'decision_record': 'dec-x'}, 'done-x')
        cases.append((log, 'not in the log'))
        cases.append((done_task(Log(), verdict='NEEDS_REWORK'), 'not an ACCEPT decision'))
        log = Log()
        log.add('decision.acceptance', {'record_id': 'dec-y', 'fact_kind': 'interpretation',
                                        'source_class': 'deterministic_tool_local', 'recorder': REC, 'subject': TASK,
                                        'decision': 'ACCEPT'}, 'acc-y')
        log.add('task.done', {'decision_record': 'dec-y'}, 'done-y')
        cases.append((log, 'no evaluated_commit'))
        log = Log()
        log.add('decision.acceptance', decision('dec-z', cid(2), TASK2), 'acc-z', task_id=TASK2)
        log.add('task.done', {'decision_record': 'dec-z'}, 'done-z')
        cases.append((log, 'not in the log'))
        for log, why in cases:
            with mock.patch.object(stale, 'stale', side_effect=AssertionError('called')) as spy:
                res = run(log)
            self.assertEqual(res['result'], 'reconciled', res)
            self.assertTrue(any(r == TASK and why in d for r, d in unc(res)), (why, res['uncovered']))
            spy.assert_not_called()

    def test_a_log_with_a_finding_is_refused(self):
        """TASK-031 AC2: a log that records.check_log finds anything in, or bytes not given, gives "refused", reason
        "log", and nothing is read from Git or appended."""
        for data in (b'not json\n', 'text'):
            log = Log(data)
            repo = Repo(chain())
            res = run(log, repo=repo)
            self.assertEqual((res['result'], res['reason']), ('refused', 'log'))
            self.assertEqual((repo.calls, log.appends), ([], []))

    def test_the_last_task_done_counts(self):
        """TASK-031 AC2 (reading): with two task.done events the last one's decision record counts."""
        log = done_task(Log())
        log.add('task.done', {'decision_record': 'dec-missing'}, 'done-again')
        res = run(log)
        self.assertIn((TASK, 'decision record dec-missing not in the log'), unc(res))


class R3Walk(unittest.TestCase):

    def test_base_commits_after_the_accepted_one_in_base_order(self):
        """TASK-031 AC3, AC4: the base commits given to stale are the walked commits after the accepted commit,
        oldest first, each read once by cat-file and diff-tree."""
        table = dict(chain())
        table[cid(4)] = ([cid(3)], ['src/z.py'])
        log = done_task(Log())
        repo = Repo(table)
        with mock.patch.object(stale, 'stale', wraps=stale.stale) as spy:
            run(log, repo=repo, trigger=cid(4))
        given = spy.call_args[0][0]
        self.assertEqual([b['commit'] for b in given['base_commits']], [cid(3), cid(4)])
        self.assertEqual(given['base_commits'][0]['paths'], ['src/y.py'])
        reads = [(c[0], c[-1]) for c in repo.calls]
        self.assertEqual(len(reads), len(set(reads)))
        self.assertIn(['diff-tree'] + gitread.DIFF_TREE[1:] + [cid(4)], repo.calls)
        self.assertNotIn(('cat-file', cid(1)), reads)

    def test_the_bound_and_a_root_give_not_reached(self):
        """TASK-031 AC3: a bound reached, or a root reached, before the accepted commit leaves the task uncovered,
        never fresh."""
        log = done_task(Log())
        res = run(log, max_commits=1)
        self.assertIn((TASK, 'accepted commit not reached'), unc(res))
        self.assertNotIn('evidence.stale', [a[0] for a in log.appends])
        log = done_task(Log(), commit=cid(9))
        res = run(log)
        self.assertIn((TASK, 'accepted commit not reached'), unc(res))
        res = run(done_task(Log()), max_commits=2)
        self.assertNotIn((TASK, 'accepted commit not reached'), unc(res))

    def test_a_failing_read_is_refused(self):
        """TASK-031 AC3: a read that fails, raises or gives a parse error gives "refused", reason "git", and nothing
        is appended."""
        bad = [{('cat-file', cid(3)): {'exit': 128, 'out': b'', 'err': b'x', 'error': None}},
               {('cat-file', cid(2)): {'exit': 0, 'out': b'garbage', 'err': b'', 'error': None}},
               {('diff-tree', cid(3)): {'exit': 0, 'out': b'\xff', 'err': b'', 'error': None}},
               {('diff-tree', cid(2)): {'exit': None, 'out': b'', 'err': b'', 'error': 'timeout'}},
               {('cat-file', cid(3)): 'not a result'},
               {('cat-file', cid(3)): RuntimeError('boom')}]
        for fail in bad:
            log = done_task(Log())
            res = run(log, repo=Repo(chain(), fail))
            self.assertEqual((res['result'], res['reason']), ('refused', 'git'), fail)
            self.assertEqual(log.appends, [])

    def test_a_merge_on_the_walk_leaves_the_task_uncovered(self):
        """TASK-031 AC3: a merge is followed by its first parent, its paths are not read, and a task whose base
        commits hold it is uncovered."""
        table = dict(chain())
        table[cid(3)] = ([cid(2), cid(7)], [])
        table[cid(4)] = ([cid(3)], ['src/z.py'])
        repo = Repo(table)
        log = done_task(Log())
        res = run(log, repo=repo, trigger=cid(4), results=[rule('SEC-001', 'fail', commit=cid(4))])
        self.assertIn((TASK, 'merge commit on the walk'), unc(res))
        self.assertNotIn(['diff-tree'] + gitread.DIFF_TREE[1:] + [cid(3)], repo.calls)
        self.assertIn(['cat-file', '-p', cid(2)], repo.calls)
        self.assertNotIn(['cat-file', '-p', cid(7)], repo.calls)
        self.assertNotIn('evidence.stale', [a[0] for a in log.appends])
        self.assertIn('violation.detected', [a[0] for a in log.appends])

    def test_a_merge_trigger_is_not_given_to_drift(self):
        """TASK-031 AC3, AC6: when the trigger is a merge, drift.violations is not called and the trigger is
        uncovered."""
        table = dict(chain())
        table[cid(3)] = ([cid(2), cid(7)], [])
        log = done_task(Log())
        with mock.patch.object(drift, 'violations', side_effect=AssertionError('called')) as spy:
            res = run(log, repo=Repo(table))
        spy.assert_not_called()
        self.assertEqual(res['result'], 'reconciled', res)
        self.assertIn((cid(3), 'trigger is a merge'), unc(res))
        self.assertIn((TASK, 'merge commit on the walk'), unc(res))

    def test_no_done_task_reads_only_the_trigger(self):
        """TASK-031 AC3: with no DONE task the walk reads the trigger only."""
        repo = Repo(chain())
        run(Log(), repo=repo)
        self.assertEqual({c[-1] for c in repo.calls}, {cid(3)})


class R4Stale(unittest.TestCase):

    def test_stale_is_called_with_the_built_inputs(self):
        """TASK-031 AC4: stale.stale gets the task's facts, its records and earlier events from the log, and the
        submitted commits flagged."""
        table = dict(chain())
        log = done_task(Log())
        log.add('task.submitted', {'commit': cid(3), 'compensating': False}, 'sub-again', fencing_token=FENCE,
                lease={'task_id': TASK, 'fencing_token': FENCE, 'expires_at': NOW + H1})
        log.add('evidence.stale', {'records': ['r-old'], 'reason': 'commit'}, 'stale-old')
        with mock.patch.object(stale, 'stale', wraps=stale.stale) as spy:
            run(log, repo=Repo(table))
        spy.assert_called_once()
        given = spy.call_args[0][0]
        self.assertEqual(given['task_id'], TASK)
        self.assertEqual((given['accepted_commit'], given['trigger_commit']), (cid(2), cid(3)))
        self.assertEqual([r['record_id'] for r in given['records']], ['r-' + TASK])
        self.assertEqual(given['earlier_events'], [{'reason': 'commit', 'records': ['r-old']}])
        self.assertEqual(given['base_commits'], [{'commit': cid(3), 'paths': ['src/y.py'], 'submitted_by_task': True}])
        self.assertEqual(given['intent_current'], {'SPEC-001': 'v2'})

    def test_a_task_without_facts_is_uncovered(self):
        """TASK-031 AC4: a DONE task without facts in values["tasks"] is uncovered and stale is not called."""
        log = done_task(Log())
        with mock.patch.object(stale, 'stale', side_effect=AssertionError('called')) as spy:
            res = run(log, vals=values(tasks={}))
        spy.assert_not_called()
        self.assertIn((TASK, 'no facts given'), unc(res))

    def test_stales_uncovered_entries_are_passed_on_and_its_error_refuses(self):
        """TASK-031 AC4: stale's uncovered entries are passed on with the task id; its error gives "refused", reason
        "stale"."""
        log = done_task(Log())
        vals = values(tasks={TASK: dict(facts(), read_set_estimate=True)})
        res = run(log, vals=vals)
        self.assertIn((TASK, 'rule 3, read_set: the read-set is an estimate'), unc(res))
        with mock.patch.object(stale, 'stale', return_value={'stale': {}, 'events': [], 'uncovered': [],
                                                                'error': 'bad'}):
            res = run(done_task(Log()))
        self.assertEqual((res['result'], res['reason']), ('refused', 'stale'))
        with mock.patch.object(stale, 'stale', side_effect=ValueError('x')):
            res = run(done_task(Log()))
        self.assertEqual((res['result'], res['reason']), ('refused', 'stale'))


class R5SourceClass(unittest.TestCase):

    def test_other_classes_are_left_out_and_named(self):
        """TASK-031 AC5: a rule result of another class is left out and named; a left-out pass leaves the article
        without a result."""
        results = [rule('SEC-001', 'fail'), rule('INV-001', 'pass', source='agent_declared', rid='p1'),
                   dict(rule('INV-001', 'pass', source='same_lineage_review'), record_id='')]
        with mock.patch.object(drift, 'violations', wraps=drift.violations) as spy:
            res = run(done_task(Log()), results=results)
        given = spy.call_args[0][0]
        self.assertEqual([r['record_id'] for r in given['rule_results']], ['res-SEC-001-fail'])
        self.assertIn(('p1', 'source class not counted'), unc(res))
        self.assertIn(('rule_results[2]', 'source class not counted'), unc(res))
        self.assertIn(('INV-001', 'no rule result'), unc(res))

    def test_a_left_out_failing_task_record_cannot_suppress(self):
        """TASK-031 AC5, AC6: a failing task record of another class does not suppress the finding; one of a counted
        class does."""
        for source, events in (('agent_declared', 1), ('deterministic_tool_local', 0)):
            log = Log()
            log.add('record.added', dict(rule('SEC-001', 'fail', source=source, rid='t-rec'), subject=TASK2),
                    'rec-t2', task_id=TASK2)
            log.add('decision.acceptance', decision('dec-t2', cid(3), TASK2, 'NEEDS_REWORK'), 'acc-t2', task_id=TASK2)
            res = run(log, vals=values(tasks={}))
            self.assertEqual([a[0] for a in log.appends].count('violation.detected'), events, source)
            if events:
                self.assertIn(('t-rec', 'source class not counted'), unc(res))
            else:
                self.assertEqual(res['already'], ['SEC-001'])


class R6Drift(unittest.TestCase):

    def test_drift_gets_the_trigger_paths_and_the_right_task_records(self):
        """TASK-031 AC6: drift.violations is called once with the trigger's paths, the articles and the records of
        the tasks whose last decision.acceptance evaluated the trigger only."""
        log = done_task(Log())
        log.add('record.added', dict(rule('SEC-001', 'fail', rid='t2'), subject=TASK2), 'rec-t2', task_id=TASK2)
        log.add('decision.acceptance', decision('dec-t2', cid(3), TASK2, 'NEEDS_REWORK'), 'acc-t2', task_id=TASK2)
        with mock.patch.object(drift, 'violations', wraps=drift.violations) as spy:
            res = run(log)
        spy.assert_called_once()
        given = spy.call_args[0][0]
        self.assertEqual(given['base_commit'], cid(3))
        self.assertEqual(given['changed_paths'], ['src/y.py'])
        self.assertEqual(given['articles'], ARTICLES)
        self.assertEqual([r['record_id'] for r in given['task_records']], ['t2'])
        self.assertEqual(res['already'], ['SEC-001'])

    def test_a_later_decision_at_another_commit_drops_the_task(self):
        """TASK-031 AC6: a task whose last decision.acceptance evaluated another commit gives no task records."""
        log = Log()
        log.add('record.added', dict(rule('SEC-001', 'fail', rid='t2'), subject=TASK2), 'rec-t2', task_id=TASK2)
        log.add('decision.acceptance', decision('dec-a', cid(3), TASK2, 'NEEDS_REWORK'), 'acc-a', task_id=TASK2)
        log.add('decision.acceptance', decision('dec-b', cid(2), TASK2, 'NEEDS_REWORK'), 'acc-b', task_id=TASK2)
        with mock.patch.object(drift, 'violations', wraps=drift.violations) as spy:
            run(log, vals=values(tasks={}))
        self.assertEqual(spy.call_args[0][0]['task_records'], [])

    def test_drifts_error_refuses(self):
        """TASK-031 AC6: drift's error, or an exception, gives "refused", reason "drift", and nothing is appended."""
        for patch in ({'return_value': {'events': [], 'already': [], 'uncovered': [], 'error': 'bad'}},
                      {'side_effect': KeyError('x')}):
            log = done_task(Log())
            with mock.patch.object(drift, 'violations', **patch):
                res = run(log)
            self.assertEqual((res['result'], res['reason']), ('refused', 'drift'))
            self.assertEqual(log.appends, [])


class R7Mapping(unittest.TestCase):

    MAP = {'deterministic_rule (INV-001, INV-002, INV-004)': ['INV-001', 'INV-002', 'INV-004'], 'SEC-001': ['SEC-001']}

    def test_the_mapping_gives_article_form_records(self):
        """TASK-031 AC7: each mapped step with success or failure gives one well-formed record per article, with the
        derived record_id."""
        steps = [{'name': 'deterministic_rule (INV-001, INV-002, INV-004)', 'conclusion': 'success'},
                 {'name': 'SEC-001', 'conclusion': 'failure'}]
        out = reconcile.rule_results_from_steps(steps, self.MAP, cid(3), 'ci')
        self.assertIsNone(out['error'])
        self.assertEqual(out['uncovered'], [])
        self.assertEqual([(r['refers_to'], r['outcome']) for r in out['records']],
                         [('INV-001', 'pass'), ('INV-002', 'pass'), ('INV-004', 'pass'), ('SEC-001', 'fail')])
        for r in out['records']:
            self.assertEqual(records.check_record(r), [])
            self.assertEqual((r['fact_kind'], r['source_class'], r['gate'], r['subject'], r['commit'], r['recorder']),
                             ('observation', 'deterministic_tool_external_ci', 'G3', cid(3), cid(3), 'ci'))
        self.assertEqual(out['records'][3]['record_id'], digest('ci-rule', cid(3), 'SEC-001', 'SEC-001'))
        name = 'deterministic_rule (INV-001, INV-002, INV-004)'
        self.assertEqual([r['record_id'] for r in out['records'][:3]],
                         [digest('ci-rule', cid(3), name, a) for a in ('INV-001', 'INV-002', 'INV-004')])
        self.assertEqual(len({r['record_id'] for r in out['records']}), 4)

    def test_duplicate_step_names_and_extra_keys(self):
        """TASK-031 AC7 (a stated limit): duplicate step names give duplicate record ids, a failure among them still
        reaching drift as a fail; a step's other keys are not read."""
        steps = [{'name': 'SEC-001', 'conclusion': 'success', 'extra': 1},
                 {'name': 'SEC-001', 'conclusion': 'failure'}]
        out = reconcile.rule_results_from_steps(steps, self.MAP, cid(3), 'ci')
        self.assertIsNone(out['error'])
        self.assertEqual([r['outcome'] for r in out['records']], ['pass', 'fail'])
        self.assertEqual(out['records'][0]['record_id'], out['records'][1]['record_id'])
        log = Log()
        run(log, vals=values(tasks={}), results=out['records'])
        self.assertEqual([a[1] for a in log.appends], [digest('violation.detected', cid(3), 'SEC-001')])

    def test_an_unmapped_step_and_another_conclusion_are_uncovered(self):
        """TASK-031 AC7: a step the mapping does not name, or a conclusion other than success or failure, gives no
        record and one uncovered entry."""
        steps = [{'name': 'other', 'conclusion': 'success'}, {'name': 'SEC-001', 'conclusion': 'skipped'},
                 {'name': 'SEC-001', 'conclusion': None}]
        out = reconcile.rule_results_from_steps(steps, self.MAP, cid(3), 'ci')
        self.assertEqual(out['records'], [])
        self.assertEqual(len(out['uncovered']), 3)
        self.assertEqual(out['uncovered'][0]['ref'], 'other')

    def test_a_malformed_argument_gives_an_error_and_no_record(self):
        """TASK-031 AC7: a malformed argument gives an error and no record."""
        steps = [{'name': 'SEC-001', 'conclusion': 'success'}]
        for args in (([{'name': '', 'conclusion': 'success'}], self.MAP, cid(3), 'ci'), ('x', self.MAP, cid(3), 'ci'),
                     (steps, {'SEC-001': []}, cid(3), 'ci'), (steps, {'SEC-001': ['']}, cid(3), 'ci'),
                     (steps, self.MAP, 'z' * 40, 'ci'), (steps, self.MAP, cid(3), '')):
            out = reconcile.rule_results_from_steps(*args)
            self.assertTrue(out['error'], args)
            self.assertEqual((out['records'], out['uncovered']), ([], []))

    def test_the_mapped_records_reach_drift_as_results(self):
        """TASK-031 AC7, AC6: the helper's records, given as rule results, are usable by drift."""
        steps = [{'name': 'SEC-001', 'conclusion': 'failure'}]
        recs = reconcile.rule_results_from_steps(steps, self.MAP, cid(3), 'ci')['records']
        log = Log()
        res = run(log, vals=values(tasks={}), results=recs)
        self.assertEqual([a[1] for a in log.appends], [digest('violation.detected', cid(3), 'SEC-001')])
        self.assertIn(('INV-001', 'no rule result'), unc(res))


class R8Appends(unittest.TestCase):

    def test_the_order_and_the_ids(self):
        """TASK-031 AC8: the evidence.stale events by task id and reason, with the task id, then the
        violation.detected events with no task id and no fencing token, under the derived ids; the log holds TASK-102
        before TASK-101, so the order is by task id, not by log order."""
        table = dict(chain())
        log = done_task(Log(), TASK2, cid(2))
        done_task(log, TASK)
        vals = values(tasks={TASK: facts(), TASK2: facts()})
        res = run(log, repo=Repo(table), vals=vals)
        self.assertEqual(res['result'], 'reconciled', res)
        got = [(a[0], a[2], a[3]) for a in log.appends]
        self.assertEqual(got, [('evidence.stale', TASK, None), ('evidence.stale', TASK, None),
                               ('evidence.stale', TASK2, None), ('evidence.stale', TASK2, None),
                               ('violation.detected', None, None)])
        ids = [a[1] for a in log.appends]
        self.assertEqual(ids[0], digest('evidence.stale', TASK, cid(3), 'commit'))
        self.assertEqual(ids[1], digest('evidence.stale', TASK, cid(3), 'intent_version'))
        self.assertEqual(ids[4], digest('violation.detected', cid(3), 'SEC-001'))
        self.assertEqual(res['appended'], ids)
        self.assertEqual(records.check_log(log.log).findings(), [])

    def test_a_refusal_midway_stops_with_the_ids_so_far(self):
        """TASK-031 AC8: the first result other than appended or duplicate stops the appends, giving "refused",
        reason "append", with the ids appended so far."""
        for bad in ('refused', None, ValueError('x')):
            log = done_task(Log())
            calls = []

            def append(root, event_type, payload, event_id, appended_at, recorder, task_id=None, _log=log, _bad=bad):
                calls.append(event_id)
                if len(calls) == 2:
                    if isinstance(_bad, BaseException):
                        raise _bad
                    return mock.Mock(result=_bad, findings=['why'])
                return _log.append(root, event_type, payload, event_id, appended_at, recorder, task_id=task_id)

            res = reconcile.reconcile(FS_ROOT, REPO, cid(3), values(), [rule('SEC-001', 'fail')], REC, NOW,
                                      read=Repo(chain()), read_log=log.read_log, append=append)
            self.assertEqual((res['result'], res['reason']), ('refused', 'append'), bad)
            self.assertEqual(res['appended'], calls[:1])
            self.assertEqual(len(calls), 2)

    def test_a_rerun_gives_duplicates_and_goes_on(self):
        """TASK-031 AC8: a rerun appends nothing new: the violation is a duplicate, and the stale events, now earlier
        events, are not given again; after a refusal mid-way a rerun appends what was left."""
        log = done_task(Log())
        first = run(log)
        self.assertEqual(len(first['appended']), 3)
        before = log.log
        second = run(log)
        self.assertEqual((second['result'], second['appended'], second['duplicate']),
                         ('reconciled', [], [first['appended'][2]]))
        self.assertEqual(log.log, before)
        log = done_task(Log())
        calls = []

        def append(root, event_type, payload, event_id, appended_at, recorder, task_id=None):
            calls.append(event_id)
            if len(calls) == 2:
                return mock.Mock(result='refused', findings=[])
            return log.append(root, event_type, payload, event_id, appended_at, recorder, task_id=task_id)

        part = reconcile.reconcile(FS_ROOT, REPO, cid(3), values(), [rule('SEC-001', 'fail')], REC, NOW,
                                   read=Repo(chain()), read_log=log.read_log, append=append)
        self.assertEqual((part['result'], len(part['appended'])), ('refused', 1))
        rest = run(log)
        self.assertEqual(rest['result'], 'reconciled')
        self.assertEqual(sorted(part['appended'] + rest['appended']), sorted(first['appended']))


class R9Result(unittest.TestCase):

    def test_the_keys_and_the_sorted_uncovered(self):
        """TASK-031 AC10: the result has exactly its keys; uncovered is sorted and without duplicates."""
        res = run(done_task(Log()), vals=values(tasks={}))
        self.assertEqual(tuple(res), reconcile.RESULT_KEYS)
        pairs = [(u['ref'], u['detail']) for u in res['uncovered']]
        self.assertEqual(pairs, sorted(set(pairs)))
        self.assertIsNone(res['reason'])

    def test_an_exception_is_caught(self):
        """TASK-031 AC10: an exception raised by a called function becomes a result with the step's reason; none
        escapes."""
        def read_log(root):
            raise OSError('no')
        res = reconcile.reconcile(FS_ROOT, REPO, cid(3), values(), [], REC, NOW, read=Repo(chain()),
                                  read_log=read_log, append=Log().append)
        self.assertEqual((res['result'], res['reason']), ('refused', 'log'))
        with mock.patch.object(records, 'check_log', side_effect=RuntimeError('x')):
            res = run(Log())
        self.assertEqual((res['result'], res['reason']), ('refused', 'log'))

    def test_an_argument_whose_methods_raise_is_refused(self):
        """TASK-031 AC10, AC1: an argument whose own methods raise gives "refused", reason "argument"."""
        class Bad(dict):
            def keys(self):
                raise RuntimeError('x')

            def __iter__(self):
                raise RuntimeError('x')
        res = reconcile.reconcile(FS_ROOT, REPO, cid(3), Bad(), [], REC, NOW, read=Repo(chain()),
                                  read_log=Log().read_log, append=Log().append)
        self.assertEqual((res['result'], res['reason']), ('refused', 'argument'))


class R11EdgePoints(unittest.TestCase):

    def test_a_four_digit_done_task_refuses_the_whole_run(self):
        """TASK-031 AC4, AC12 (a stated limit): a DONE task whose id stale.stale does not take refuses the whole run
        with "stale", and nothing is appended, not even drift's events."""
        task = 'TASK-1001'
        log = done_task(Log(), task)
        res = run(log, vals=values(tasks={task: facts()}))
        self.assertEqual((res['result'], res['reason']), ('refused', 'stale'))
        self.assertEqual(log.appends, [])

    def test_repeated_record_ids_refuse_the_whole_run(self):
        """TASK-031 AC4, AC12 (a stated limit): a DONE task whose record.added payloads repeat a record_id makes
        stale.stale give an error, so the run is refused with "stale"."""
        log = done_task(Log())
        log.add('record.added', record('r-' + TASK, cid(2)), 'rec-again')
        res = run(log)
        self.assertEqual((res['result'], res['reason']), ('refused', 'stale'))
        self.assertEqual(log.appends, [])

    def test_any_zero_offset_tzinfo_and_the_largest_values_are_accepted(self):
        """TASK-031 AC1 (a stated reading): "now" with a tzinfo other than datetime.timezone.utc but offset zero is
        accepted, and so are a 64-character trigger and max_commits 10000."""
        zero = datetime.timezone(datetime.timedelta(0), 'Z0')
        log = done_task(Log())
        res = reconcile.reconcile(FS_ROOT, REPO, cid(3), values(), [], REC, NOW.replace(tzinfo=zero),
                                  max_commits=10000, read=Repo(chain()), read_log=log.read_log, append=log.append)
        self.assertEqual(res['result'], 'reconciled', res)
        res = reconcile.reconcile(FS_ROOT, REPO, 'e' * 64, values(), [], REC, NOW, read=Repo(chain()),
                                  read_log=Log().read_log, append=Log().append)
        self.assertNotEqual(res['reason'], 'argument')

    def test_a_failure_inside_the_filter_is_reported_as_stale(self):
        """TASK-031 AC5, AC10, AC12 (a stated limit): an exception inside the source-class filter gives "refused" under
        the reason of the step it runs in, "stale", and nothing is appended."""
        log = done_task(Log())
        with mock.patch.object(reconcile, '_counted', side_effect=RuntimeError('x')):
            res = run(log)
        self.assertEqual((res['result'], res['reason']), ('refused', 'stale'))
        self.assertEqual(log.appends, [])

    def test_a_malformed_event_from_a_computation_refuses_before_any_append(self):
        """TASK-031 AC8, AC10: an event that lacks a key when the appends are planned gives "refused", reason "append",
        with nothing appended; no exception escapes."""
        log = done_task(Log())
        bad = {'stale': {}, 'events': [{'event_id': 'x', 'event_type': 'evidence.stale', 'payload': {}}],
               'uncovered': [], 'error': None}
        with mock.patch.object(stale, 'stale', return_value=bad):
            res = run(log)
        self.assertEqual((res['result'], res['reason']), ('refused', 'append'))
        self.assertEqual(log.appends, [])

    def test_another_tasks_submissions_and_events_are_not_used(self):
        """TASK-031 AC2, AC4: another task's submitted commits and evidence.stale events do not reach this task's
        stale inputs."""
        log = done_task(Log())
        log.add('task.submitted', {'commit': cid(3), 'compensating': False}, 'sub-other', task_id=TASK2,
                fencing_token=FENCE, lease={'task_id': TASK2, 'fencing_token': FENCE, 'expires_at': NOW + H1})
        log.add('evidence.stale', {'records': ['r-' + TASK], 'reason': 'commit'}, 'stale-other', task_id=TASK2)
        with mock.patch.object(stale, 'stale', wraps=stale.stale) as spy:
            run(log)
        given = spy.call_args[0][0]
        self.assertEqual(given['base_commits'][0]['submitted_by_task'], False)
        self.assertEqual(given['earlier_events'], [])

    def test_the_last_matching_decision_counts(self):
        """TASK-031 AC2 (a stated reading): among a task's decision.acceptance events with the same record_id, the
        last one counts, either way."""
        log = done_task(Log(), rid='dec-x')
        log.add('decision.acceptance', decision('dec-x', cid(2), TASK, 'NEEDS_REWORK'), 'acc-later')
        res = run(log)
        self.assertIn((TASK, 'decision record dec-x is not an ACCEPT decision'), unc(res))
        log = Log()
        log.add('decision.acceptance', decision('dec-y', cid(2), TASK, 'NEEDS_REWORK'), 'acc-first')
        done_task(log, rid='dec-y')
        res = run(log)
        self.assertNotIn(TASK, {u['ref'] for u in res['uncovered']})

    def test_an_accepted_commit_equal_to_the_trigger(self):
        """TASK-031 AC3, AC4: a task accepted at the trigger itself gets stale with no base commit."""
        log = done_task(Log(), commit=cid(3))
        with mock.patch.object(stale, 'stale', wraps=stale.stale) as spy:
            res = run(log)
        self.assertEqual(res['result'], 'reconciled', res)
        self.assertEqual(spy.call_args[0][0]['base_commits'], [])

    def test_a_record_added_after_a_run_makes_the_rerun_conflict(self):
        """TASK-031 AC8, AC12 (a stated limit): a record added to a DONE task after a run at the same trigger makes
        the rerun's evidence.stale event differ from the stored one under the same id; the writer refuses it, and the
        rerun stops there with "refused", reason "append"."""
        log = done_task(Log())
        first = run(log)
        self.assertEqual(first['result'], 'reconciled', first)
        log.add('record.added', record('r-late', cid(2)), 'rec-late')
        second = run(log)
        self.assertEqual((second['result'], second['reason']), ('refused', 'append'))
        self.assertEqual(second['appended'], [])
        self.assertTrue(any('with another event' in f for f in second['findings']), second['findings'])


FORBIDDEN_NAMES = ('open', 'exec', 'eval', 'compile', '__import__', 'subprocess', 'os', 'governor', 'time')
FORBIDDEN_ATTRS = ('now', 'utcnow', 'today', 'time', 'environ', 'getenv', 'open', 'write', 'run_task', 'evaluate',
                   'grant_lease', 'release_lease', 'release_lease_token', 'expire_leases', 'open_store')
ALLOWED_IMPORTS = {'datetime', 'hashlib', 're', 'aieos_bootstrap.drift', 'aieos_bootstrap.gitread',
                   'aieos_bootstrap.records', 'aieos_bootstrap.stale', 'aieos_bootstrap.writer'}


def purity_findings(src):
    """The purity check of AC9 and AC11 over a source text: the imports outside the allowed set, the forbidden names
    and attributes used, asserts, and a project-state directory string, each as a short text."""
    tree = ast.parse(src)
    found = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            found.extend('import ' + a.name for a in n.names if a.name not in ALLOWED_IMPORTS)
        elif isinstance(n, ast.ImportFrom):
            found.extend('import %s.%s' % (n.module, a.name) for a in n.names
                         if '%s.%s' % (n.module, a.name) not in ALLOWED_IMPORTS)
        elif isinstance(n, ast.Name) and n.id in FORBIDDEN_NAMES:
            found.append('name ' + n.id)
        elif isinstance(n, ast.Attribute) and n.attr in FORBIDDEN_ATTRS:
            found.append('attribute ' + n.attr)
        elif isinstance(n, ast.Assert):
            found.append('assert')
    if '.aie' + 'os' in src:
        found.append('project-state directory')
    return found


class R10Purity(unittest.TestCase):

    def test_imports_and_calls(self):
        """TASK-031 AC9, AC11: the module imports only the standard library and drift, gitread, records, stale and
        writer; it calls no open, process, clock or governor function, has no assert and names no project-state
        directory."""
        src = MODULE.read_text(encoding='utf-8')
        self.assertEqual(purity_findings(src), [])
        tree = ast.parse(src)
        mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        mods |= {'%s.%s' % (n.module, a.name) for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                 for a in n.names}
        self.assertEqual(mods, ALLOWED_IMPORTS)

    def test_the_purity_check_catches_seeded_calls(self):
        """TASK-031 AC11: the same check reports an open call, a clock call, a governor import, an assert and a
        project-state directory string seeded into the module's source."""
        base = MODULE.read_text(encoding='utf-8')
        seeds = {'\nopen("x")\n': 'name open', '\ndatetime.datetime.now()\n': 'attribute now',
                 '\nfrom aieos_bootstrap import governor\n': 'import aieos_bootstrap.governor',
                 '\nassert True\n': 'assert', '\nX = "' + '.aie' + 'os/x"\n': 'project-state directory'}
        for seed, want in seeds.items():
            self.assertIn(want, purity_findings(base + seed), seed)

    def test_the_docstring_names_what_it_does_not_do(self):
        """TASK-031 AC9: the docstring says what the module does not do and names DEF-0030, DEF-0051 and DEF-0057."""
        doc = ast.get_docstring(ast.parse(MODULE.read_text(encoding='utf-8')))
        for word in ('DEF-0030', 'DEF-0051', 'DEF-0057', 'no governor function', 'no lease', 'scope-drift'):
            self.assertIn(word, doc)


if __name__ == '__main__':
    unittest.main()

"""Unit tests of aieos_bootstrap.evaluation (task TASK-027, its rules R1 to R12); every rule has at least one passing
case and one failing case. The Git reader and the writer's functions are replaced by stand-ins: the reader answers
from a table of commits and their changed paths, and the stand-in writer keeps a log as bytes, deciding each append
with eventlog.append as the real writer does, so no git starts and no file is touched here. Each test names the
criteria it stands for in its own docstring."""

import ast
import datetime
import hashlib
import pathlib
import unittest

from aieos_bootstrap import evaluation
from aieos_bootstrap import eventlog
from aieos_bootstrap import gitread
from aieos_bootstrap import governor
from aieos_bootstrap import writer

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE = ROOT / 'src' / 'aieos_bootstrap' / 'evaluation.py'
FS_ROOT = str(ROOT / 'no-such-state-root')
REPO = str(ROOT)
TREE = 'b' * 40
TASK = 'TASK-027'
REC = 'aieos-core'
NOW = datetime.datetime(2026, 10, 12, 10, 0, 0, tzinfo=datetime.timezone.utc)
CONTRACT = b'task: TASK-027\n'
CHASH = hashlib.sha256(CONTRACT).hexdigest()
DECLARED = {'intent_versions': {'SPEC-001': 'v1'}, 'retries': 2}
MINE = 'Do the task\n\nThe body.\n\nAIEOS-Task: TASK-027\n'
OTHER = 'Other work\n\nThe body.\n\nAIEOS-Task: TASK-099\n'
PLAIN = 'Records\n\nThe body.\n'
FENCE = {'epoch': 'e0', 'counter': 1}
H1 = datetime.timedelta(hours=1)


def cid(n):
    return '%040x' % n


def ok(out):
    return {'exit': 0, 'out': out, 'err': b'', 'error': None}


def commit_bytes(parents, message):
    head = 'tree %s\n' % TREE + ''.join('parent %s\n' % p for p in parents)
    head += 'author Tester <tester> 1700000000 +0000\ncommitter Tester <tester> 1700000000 +0000\n\n'
    return (head + message).encode('utf-8')


class Repo:
    """A stand-in for gitread.run: commits from a table {id: (parents, message, paths)}; ``fail`` maps (form, id) to
    the result (or exception) given instead, the form being "cat-file" or "diff-tree"."""

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
        parents, message, paths = self.table[args[-1]]
        if args[0] == 'cat-file':
            return ok(commit_bytes(parents, message))
        return ok(b''.join(p.encode('utf-8') + b'\0' for p in paths))


def chain():
    """Main's commit cid(1) (no trailer), then two task commits cid(2) and cid(3)."""
    return {cid(1): ([], PLAIN, ['docs/a.md']),
            cid(2): ([cid(1)], MINE, ['src/x.py', 'tests/unit/test_x.py']),
            cid(3): ([cid(2)], MINE, ['src/x.py'])}


PATHS = ['src/x.py', 'tests/unit/test_x.py']


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
        self.appends.append((root, event_type, payload, event_id, appended_at, recorder, task_id, fencing_token))
        r = eventlog.append(self.log, event_type, payload, event_id, appended_at, task_id=task_id,
                            fencing_token=fencing_token, recorder=recorder)
        if r.result == 'appended':
            self.log += r.line
        return r

    def add(self, event_type, payload, event_id, task_id=TASK, fencing_token=None, lease=None):
        r = eventlog.append(self.log, event_type, payload, event_id, NOW, task_id=task_id, fencing_token=fencing_token,
                            lease=lease)
        assert r.result == 'appended', (r.result, r.findings)
        self.log += r.line
        return self


def approved(log, chash=CHASH, eid='approved-1'):
    return log.add('task.approved', {'contract_version': 'v1', 'contract_hash': chash, 'approval_record': 'rec-a'}, eid)


def submitted(log, commit, eid='submitted-1'):
    return log.add('task.submitted', {'commit': commit, 'compensating': False}, eid,
                   fencing_token=FENCE, lease={'task_id': TASK, 'fencing_token': FENCE, 'expires_at': NOW + H1})


def base_log(commit=None):
    return submitted(approved(Log()), commit or cid(3))


def values(**changes):
    v = {
        'contract': {'traces_to': ['SPEC-001'], 'risk': 'high', 'owner_kept_act': False, 'verification_plan': ['G0', 'G1']},
        'changed_paths': list(PATHS),
        'risk_rules': [{'id': 'R2', 'match': ['src/**', 'tests/**'], 'class': 'medium'}],
        'owner_kept_rules': [{'id': 'OPS-002', 'match': ['docs/pre-genesis/measurement-protocol.md']}],
        'articles': [{'id': 'INV-002', 'scope': ['src/**'], 'evidence_required': ['ai_review']}],
        'default_profiles': {'high': [{'dimension': 'functional', 'evidence_types': ['unit_test']}]},
        'requirement_profiles': [],
        'delegation': True,
        'evidence_comparison': {'weakens': False},
        'auto_accept': {},
        'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1',
    }
    v.update(changes)
    return v


def record(rid, **changes):
    r = {'record_id': rid, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_external_ci',
         'recorder': 'ci', 'subject': TASK, 'gate': 'G1', 'outcome': 'pass', 'commit': cid(3),
         'intent_versions': {'SPEC-001': 'v1'}}
    r.update(changes)
    return r


def run(log=None, git=None, **kw):
    log = log if log is not None else base_log()
    repo = git if git is not None else Repo(chain())
    args = dict(root=FS_ROOT, repo=REPO, task_id=TASK, contract_bytes=CONTRACT, declared=DECLARED, values=values(),
                extra_records=[], recorder=REC, now=NOW, read=repo, read_log=log.read_log, append=log.append)
    args.update(kw)
    return evaluation.evaluate_task(**args), log, repo


class R1Arguments(unittest.TestCase):
    def test_each_wrong_argument_is_refused_before_any_read(self):
        """TASK-027 AC1 and TASK-027 AC15: each argument wrong in turn, a 64-hex intent version among them, gives
        "refused", reason "argument", and neither read_log nor read is called."""
        wrong = {'root': 'relative/path', 'repo': '', 'task_id': 'TASK-x', 'contract_bytes': 'text',
                 'declared': {'intent_versions': {'SPEC-001': 'a' * 64}, 'retries': 2},
                 'values': [], 'extra_records': (), 'recorder': '', 'max_commits': 0,
                 'now': datetime.datetime(2026, 10, 12, 10, 0, 0)}
        for name, value in wrong.items():
            log, repo = base_log(), Repo(chain())
            r, _, _ = run(log, repo, **{name: value})
            self.assertEqual((r['result'], r['reason']), ('refused', 'argument'), name)
            self.assertTrue(any(name.split('_')[0] in f for f in r['findings']), (name, r['findings']))
            self.assertEqual((log.reads, repo.calls), (0, []), name)

    def test_retries_and_the_bound_are_checked(self):
        """TASK-027 AC1: retries outside 0 to 100 and a bool max_commits are refused; good arguments pass."""
        for declared in ({'intent_versions': {}, 'retries': 101}, {'intent_versions': {}, 'retries': True},
                         {'intent_versions': {}}):
            self.assertEqual(run(declared=declared)[0]['reason'], 'argument')
        self.assertEqual(run(max_commits=True)[0]['reason'], 'argument')
        self.assertEqual(run()[0]['result'], 'evaluated')


class R2State(unittest.TestCase):
    def test_a_damaged_log_is_refused(self):
        """TASK-027 AC2: a log that records.check_log finds damaged gives "refused", reason "log", and no read."""
        log = Log(b'not json\n')
        r, _, repo = run(log)
        self.assertEqual((r['result'], r['reason'], repo.calls), ('refused', 'log', []))

    def test_no_approval_is_refused(self):
        """TASK-027 AC2: with no task.approved of the task, "refused", reason "state"."""
        log = submitted(Log(), cid(3))
        self.assertEqual(run(log)[0]['reason'], 'state')

    def test_verifying_after_a_submission(self):
        """TASK-027 AC2 and TASK-027 AC6: after task.submitted the request's task_state is VERIFYING and its
        evaluated commit the submission's."""
        seen = []
        real = governor.evaluate

        def spy(request, inputs, recs):
            seen.append(request)
            return real(request, inputs, recs)

        governor.evaluate = spy
        try:
            r = run()[0]
        finally:
            governor.evaluate = real
        self.assertEqual(r['result'], 'evaluated')
        self.assertEqual((seen[0]['task_state'], seen[0]['evaluated_commit']), ('VERIFYING', cid(3)))

    def test_in_review_after_a_decision_and_a_null_next_state_sets_nothing(self):
        """TASK-027 AC2: a decision.acceptance with next_task_state IN_REVIEW sets IN_REVIEW; one with a null
        next_task_state sets nothing; the state-setting event is the one that set the state."""
        log = base_log()
        r1 = run(log)[0]
        self.assertEqual(r1['result'], 'evaluated')
        payload = dict(log.appends[0][2])
        review = dict(payload, record_id='rev-1', next_task_state='IN_REVIEW', decision='NEEDS_REVIEW')
        log.add('decision.acceptance', review, 'dec-review')
        state = evaluation._task_events(log.read_log, FS_ROOT, TASK)
        self.assertEqual((state[1], state[2]), ('IN_REVIEW', 'dec-review'))
        error = {k: v for k, v in payload.items() if k != 'next_task_state'}  # the governor leaves it out (rule 7)
        error.update(record_id='err-1', decision=None, error='rule 7', table_row=None)
        log.add('decision.acceptance', error, 'dec-error')
        state = evaluation._task_events(log.read_log, FS_ROOT, TASK)
        self.assertEqual((state[1], state[2]), ('IN_REVIEW', 'dec-review'))

    def test_an_error_record_keeping_the_state_sets_nothing(self):
        """TASK-027 AC2 (erratum E1, decision D-636): an error record from VERIFYING, whose next_task_state is
        VERIFYING, sets nothing; the state-setting event stays the task.submitted."""
        log = base_log()
        r = run(log, values=values(risk_rules=[{'id': 'R1', 'match': ['docs/**'], 'class': 'low'}]))[0]
        self.assertEqual((r['decision'], r['next_task_state']), (None, 'VERIFYING'))
        state = evaluation._task_events(log.read_log, FS_ROOT, TASK)
        self.assertEqual((state[1], state[2]), ('VERIFYING', 'submitted-1'))

    def test_a_stale_task_is_refused(self):
        """TASK-027 AC2: a task.stale after the submission gives "refused", reason "state"."""
        log = base_log().add('task.stale', {'cause': 'intent_change', 'refers_to': 'CHG-001'}, 'stale-1')
        r = run(log)[0]
        self.assertEqual((r['result'], r['reason']), ('refused', 'state'))

    def test_retries_used_count_only_rework_after_the_last_approval(self):
        """TASK-027 AC2: retries used counts the decision.acceptance events after the last task.approved whose
        next_task_state is REWORK, and none before it."""
        log = base_log()
        run(log)
        payload = dict(log.appends[0][2])
        log.add('decision.acceptance', dict(payload, record_id='rw-1', next_task_state='REWORK', decision='NEEDS_REWORK'), 'rw-1')
        approved(log, eid='approved-2')
        log.add('decision.acceptance', dict(payload, record_id='rw-2', next_task_state='REWORK', decision='NEEDS_REWORK'), 'rw-2')
        submitted(log, cid(3), 'submitted-2')
        log.add('decision.acceptance', dict(payload, record_id='rv-1', next_task_state='IN_REVIEW', decision='NEEDS_REVIEW'), 'rv-1')
        state = evaluation._task_events(log.read_log, FS_ROOT, TASK)
        self.assertEqual((state[1], state[4]), ('IN_REVIEW', 1))


class R3Contract(unittest.TestCase):
    def test_other_bytes_are_refused(self):
        """TASK-027 AC3: contract bytes that do not hash to the approved contract_hash give "refused", reason
        "contract", and no read."""
        r, _, repo = run(contract_bytes=b'other\n')
        self.assertEqual((r['result'], r['reason'], repo.calls), ('refused', 'contract', []))

    def test_the_content_hash(self):
        """TASK-027 AC3: task_content_hash is the SHA-256 of the contract bytes, one LF and the evaluated commit."""
        log = base_log()
        run(log)
        want = hashlib.sha256(CONTRACT + b'\n' + cid(3).encode('ascii')).hexdigest()
        self.assertEqual(log.appends[0][2]['task_content_hash'], want)


class R4Walk(unittest.TestCase):
    def test_two_task_commits_then_another(self):
        """TASK-027 AC4 and TASK-027 AC15: two task commits are read, and the walk ends at the commit without the
        trailer, whose paths are not read; a commit of another task ends it too."""
        r, _, repo = run()
        self.assertEqual(r['result'], 'evaluated')
        self.assertEqual([c[-1] for c in repo.calls if c[0] == 'cat-file'], [cid(3), cid(2), cid(1)])
        self.assertEqual([c[-1] for c in repo.calls if c[0] == 'diff-tree'], [cid(3), cid(2)])
        table = chain()
        table[cid(1)] = ([], OTHER, ['docs/a.md'])
        self.assertEqual(run(git=Repo(table))[0]['result'], 'evaluated')

    def test_a_root_task_commit_ends_the_walk(self):
        """TASK-027 AC4: a task commit with no parent ends the walk after it."""
        table = {cid(3): ([], MINE, ['src/x.py', 'tests/unit/test_x.py'])}
        self.assertEqual(run(git=Repo(table))[0]['result'], 'evaluated')

    def test_a_merge_is_refused(self):
        """TASK-027 AC4: a task commit with two parents gives "refused", reason "merge"."""
        table = chain()
        table[cid(2)] = ([cid(1), cid(1)], MINE, ['src/x.py'])
        r, log, _ = run(git=Repo(table))
        self.assertEqual((r['result'], r['reason'], log.appends), ('refused', 'merge', []))

    def test_the_evaluated_commit_must_be_the_tasks(self):
        """TASK-027 AC4: an evaluated commit without the task's trailer gives "refused", reason "git"."""
        table = chain()
        table[cid(3)] = ([cid(2)], PLAIN, ['src/x.py'])
        self.assertEqual(run(git=Repo(table))[0]['reason'], 'git')

    def test_a_one_paragraph_message_with_the_trailer_is_refused(self):
        """TASK-027 AC4 and TASK-027 AC15: a one-paragraph message holding this task's AIEOS-Task line gives
        "refused", reason "git" (DEF-0052 F6)."""
        table = chain()
        table[cid(2)] = ([cid(1)], 'AIEOS-Task: TASK-027\n', ['src/x.py'])
        r = run(git=Repo(table))[0]
        self.assertEqual((r['result'], r['reason']), ('refused', 'git'))

    def test_a_trailer_finding_is_refused(self):
        """TASK-027 AC4 and TASK-027 AC15: a commit whose trailers give a finding (a mis-cased key) gives "refused",
        reason "git", even where the walk would otherwise end."""
        table = chain()
        table[cid(1)] = ([], 'Records\n\nThe body.\n\naieos-task: TASK-027\n', ['docs/a.md'])
        r = run(git=Repo(table))[0]
        self.assertEqual((r['result'], r['reason']), ('refused', 'git'))

    def test_the_bound(self):
        """TASK-027 AC4: more task commits than max_commits give "refused", reason "bound"; exactly max_commits pass."""
        self.assertEqual(run(max_commits=1)[0]['reason'], 'bound')
        self.assertEqual(run(max_commits=2)[0]['result'], 'evaluated')

    def test_each_failing_read_is_refused_with_nothing_appended(self):
        """TASK-027 AC4 and TASK-027 AC15: each failing read result gives "refused", reason "git", and no append."""
        bad = [{'exit': None, 'out': b'', 'err': b'', 'error': 'timeout'},
               {'exit': 128, 'out': b'', 'err': b'x', 'error': None},
               ok(b'not a commit'), {'out': b''}, OSError('no git')]
        for given in bad:
            r, log, _ = run(git=Repo(chain(), {('cat-file', cid(2)): given}))
            self.assertEqual((r['result'], r['reason'], log.appends), ('refused', 'git', []), given)


class R5Paths(unittest.TestCase):
    def test_the_union_of_the_task_commits(self):
        """TASK-027 AC5: the changed paths are the sorted union of the task commits' paths."""
        r = run()[0]
        self.assertEqual(r['changed_paths'], PATHS)

    def test_a_failing_diff_tree_is_refused(self):
        """TASK-027 AC5: a failing diff-tree, or paths out of form, give "refused", reason "git"."""
        for given in ({'exit': 1, 'out': b'', 'err': b'', 'error': None}, ok(b'\0')):
            r = run(git=Repo(chain(), {('diff-tree', cid(2)): given}))[0]
            self.assertEqual((r['result'], r['reason']), ('refused', 'git'))


class R6Inputs(unittest.TestCase):
    def test_other_changed_paths_are_refused(self):
        """TASK-027 AC6: values whose changed_paths differ from the task's change give "refused", reason "values"."""
        for given in (['src/x.py'], PATHS[::-1], 'src/x.py'):
            r, log, _ = run(values=values(changed_paths=given))
            self.assertEqual((r['result'], r['reason'], log.appends), ('refused', 'values', []))

    def test_derive_inputs_raising_is_refused(self):
        """TASK-027 AC6: values that derive_inputs refuses give "refused", reason "values"."""
        v = values()
        del v['auto_accept']
        self.assertEqual(run(values=v)[0]['reason'], 'values')

    def test_the_exact_request(self):
        """TASK-027 AC6: the request is exactly section 6.5's keys with the computed values."""
        seen = []
        real = governor.evaluate
        governor.evaluate = lambda q, i, rs: seen.append(q) or real(q, i, rs)
        try:
            run()
        finally:
            governor.evaluate = real
        want = {'task_id': TASK, 'task_content_hash': hashlib.sha256(CONTRACT + b'\n' + cid(3).encode()).hexdigest(),
                'evaluated_commit': cid(3), 'intent_versions': {'SPEC-001': 'v1'}, 'task_state': 'VERIFYING',
                'changed_paths': PATHS, 'retry_count': {'used': 0, 'limit': 2}}
        self.assertEqual(seen[0], want)


class R7Records(unittest.TestCase):
    def test_malformed_and_repeated_records_are_left_out(self):
        """TASK-027 AC7: a malformed record and a repeated record_id are left out with findings; good records from the
        log and from extra_records are given to the governor."""
        log = base_log().add('record.added', record('r-log'), 'ra-1')
        seen = []
        real = governor.evaluate
        governor.evaluate = lambda q, i, rs: seen.append(rs) or real(q, i, rs)
        try:
            r = run(log, extra_records=[record('r-ci'), {'record_id': 'bad'}, record('r-ci')])[0]
        finally:
            governor.evaluate = real
        self.assertEqual([x['record_id'] for x in seen[0]], ['r-log', 'r-ci'])
        self.assertEqual(len([f for f in r['findings'] if f.startswith('records:')]), 2)
        self.assertEqual(r['result'], 'evaluated')

    def test_the_governor_raising_is_refused(self):
        """TASK-027 AC7: an exception from governor.evaluate gives "refused", reason "governor"."""
        real = governor.evaluate

        def boom(*a):
            raise RuntimeError('x')

        governor.evaluate = boom
        try:
            r, log, _ = run()
        finally:
            governor.evaluate = real
        self.assertEqual((r['result'], r['reason'], log.appends), ('refused', 'governor', []))


class R8Append(unittest.TestCase):
    def test_the_exact_append(self):
        """TASK-027 AC8: one append of decision.acceptance with the governor's record, the derived event id, the
        time, the recorder and the task, and no fencing token."""
        log = base_log().add('record.added', record('r-log'), 'ra-1')
        r = run(log)[0]
        root, kind, payload, eid, at, rec, task, token = log.appends[0]
        want = hashlib.sha256('\n'.join(['evaluation', TASK, 'submitted-1', 'r-log']).encode()).hexdigest()
        self.assertEqual((root, kind, eid, at, rec, task, token), (FS_ROOT, 'decision.acceptance', want, NOW, REC, TASK, None))
        self.assertEqual(len(log.appends), 1)
        self.assertEqual((r['event_id'], r['decision'], r['next_task_state']),
                         (want, payload['decision'], payload['next_task_state']))

    def test_an_error_record_is_appended(self):
        """TASK-027 AC8: a record with an error and a null decision (rule 7) is appended too."""
        v = values(risk_rules=[{'id': 'R1', 'match': ['docs/**'], 'class': 'low'}])
        r, log, _ = run(values=v)
        self.assertEqual(len(log.appends), 1)
        self.assertIsNone(log.appends[0][2]['decision'])
        self.assertEqual((r['result'], r['decision']), ('evaluated', None))

    def test_a_refused_or_raising_append(self):
        """TASK-027 AC8: an append that is refused, raises or gives no result gives "refused", reason "store"."""
        class W:
            result = 'refused'
            findings = ('6.1: something',)

        def boom(*a, **k):
            raise OSError('disk')

        for append in (lambda *a, **k: W(), boom, lambda *a, **k: None):
            r = run(append=append)[0]
            self.assertEqual((r['result'], r['reason']), ('refused', 'store'))


class R9Reruns(unittest.TestCase):
    def test_a_rerun_is_a_duplicate(self):
        """TASK-027 AC9: a second evaluation over the same log, commits and records gives "duplicate" and appends no
        second decision."""
        log = base_log()
        before = log.log  # both runs read the log as it was before the first append (a run whose result was lost)
        first = run(log, read_log=lambda root: before)[0]
        lines = log.log.count(b'\n')
        second = run(log, read_log=lambda root: before)[0]
        self.assertEqual((first['result'], second['result']), ('evaluated', 'duplicate'))
        self.assertEqual(log.log.count(b'\n'), lines)
        self.assertEqual(first['event_id'], second['event_id'])

    def test_a_rerun_after_an_error_record_is_a_duplicate(self):
        """TASK-027 AC9 (erratum E1, decision D-636): after an error record that keeps the task in VERIFYING, a rerun
        over the log that holds it gives "duplicate"."""
        bad = values(risk_rules=[{'id': 'R1', 'match': ['docs/**'], 'class': 'low'}])
        log = base_log()
        first = run(log, values=bad)[0]
        second = run(log, values=bad)[0]
        self.assertEqual((first['result'], second['result']), ('evaluated', 'duplicate'))
        self.assertEqual(len([a for a in log.appends]), 2)
        self.assertEqual(log.log.count(b'\n'), 3)

    def test_a_rerun_after_a_decision_keeping_in_review_is_a_duplicate(self):
        """TASK-027 AC9 (erratum E1, decision D-636): a decision that keeps the task IN_REVIEW sets nothing, so the
        next evaluation, with no new record, gets the same event id as the one before it and gives "duplicate"."""
        log = base_log()
        run(log)
        payload = dict(log.appends[0][2])
        log.add('decision.acceptance', dict(payload, record_id='rv-1', next_task_state='IN_REVIEW', decision='NEEDS_REVIEW'), 'rv-1')
        before = log.log
        live = Log(before)
        a = run(live, read_log=lambda root: before)[0]
        kept = Log(before).add('decision.acceptance', dict(payload, record_id='rv-2', next_task_state='IN_REVIEW',
                                                           decision='NEEDS_REVIEW'), 'rv-2').log
        state = evaluation._task_events(lambda root: kept, FS_ROOT, TASK)
        self.assertEqual((state[1], state[2]), ('IN_REVIEW', 'rv-1'))
        b = run(live, read_log=lambda root: kept)[0]
        self.assertEqual((a['result'], b['result']), ('evaluated', 'duplicate'))
        self.assertEqual(a['event_id'], b['event_id'])

    def test_a_new_record_gives_a_new_id_in_review(self):
        """TASK-027 AC9: after a decision that set IN_REVIEW, an added record gives a re-evaluation a new event id."""
        log = base_log()
        run(log)
        payload = dict(log.appends[0][2])
        log.add('decision.acceptance', dict(payload, record_id='rv-1', next_task_state='IN_REVIEW', decision='NEEDS_REVIEW'), 'rv-1')
        review = Log(log.log)
        a = run(review)[0]
        added = Log(log.log).add('record.added', record('r-new'), 'ra-new')
        b = run(added)[0]
        self.assertEqual((a['result'], b['result']), ('evaluated', 'evaluated'))
        self.assertNotEqual(a['event_id'], b['event_id'])


class R10Defaults(unittest.TestCase):
    def test_the_three_defaults_are_pinned(self):
        """TASK-027 AC10: with read, read_log and append None, gitread.run, writer.read_log and writer.append_event
        are used, resolved at call time."""
        log, repo = base_log(), Repo(chain())
        saved = (gitread.run, writer.read_log, writer.append_event)
        gitread.run, writer.read_log, writer.append_event = repo, log.read_log, log.append
        try:
            r = evaluation.evaluate_task(FS_ROOT, REPO, TASK, CONTRACT, DECLARED, values(), [], REC, NOW)
        finally:
            gitread.run, writer.read_log, writer.append_event = saved
        self.assertEqual(r['result'], 'evaluated')
        self.assertEqual((log.reads, len(log.appends)), (1, 1))
        self.assertTrue(repo.calls)


class R11Result(unittest.TestCase):
    def test_the_result_keys(self):
        """TASK-027 AC11: every result has exactly the seven keys."""
        for r in (run()[0], run(task_id='x')[0], run(contract_bytes=b'o')[0]):
            self.assertEqual(set(r), evaluation.RESULT_KEYS)

    def test_no_exception_escapes(self):
        """TASK-027 AC11: exceptions from read_log, read and append, and an argument whose method raises, become
        results."""
        def boom(*a, **k):
            raise RuntimeError('x')

        class Tz(datetime.tzinfo):
            def utcoffset(self, d):
                raise RuntimeError('tz')

        self.assertEqual(run(read_log=boom)[0]['reason'], 'log')
        self.assertEqual(run(read=boom)[0]['reason'], 'git')
        self.assertEqual(run(append=boom)[0]['reason'], 'store')
        self.assertEqual(run(read_log=lambda root: 'text')[0]['reason'], 'log')
        self.assertEqual(run(now=datetime.datetime(2026, 10, 12, tzinfo=Tz()))[0]['reason'], 'argument')


class R12Purity(unittest.TestCase):
    def test_imports_and_calls(self):
        """TASK-027 AC12: the module imports only the standard library and gitread, governor, records, recovery and
        writer; it names no process, file, clock, environment or store-changing call."""
        tree = ast.parse(MODULE.read_text(encoding='utf-8'))
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                mods.update('%s.%s' % (node.module, a.name) for a in node.names)
        self.assertEqual(mods, {'datetime', 'hashlib', 'os', 're', 'aieos_bootstrap.gitread', 'aieos_bootstrap.governor',
                                'aieos_bootstrap.records', 'aieos_bootstrap.recovery', 'aieos_bootstrap.writer'})
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        ids = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        for bad in ('open', 'system', 'popen', 'now', 'utcnow', 'today', 'time', 'environ', 'getenv', 'open_store',
                    'grant_lease', 'release_lease', 'release_lease_token', 'expire_leases', 'start_session',
                    'end_session', 'remove', 'unlink', 'import_module'):
            self.assertNotIn(bad, attrs, bad)
        for bad in ('open', 'exec', 'eval', 'compile', '__import__', 'subprocess', 'importlib'):
            self.assertNotIn(bad, ids, bad)
        self.assertFalse(any(isinstance(n, ast.Assert) for n in ast.walk(tree)))


if __name__ == '__main__':
    unittest.main()

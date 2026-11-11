"""Unit tests of aieos_bootstrap.evaluation (task TASK-027, its rules R1 to R12); every rule has at least one passing
case and one failing case. The Git reader and the writer's functions are replaced by stand-ins: the reader answers
from a table of commits and their changed paths, and the stand-in writer keeps a log as bytes, deciding each append
with eventlog.append as the real writer does, so no git starts and no file is touched here. Each test names the
criteria it stands for in its own docstring."""

import ast
import copy
import datetime
import hashlib
import pathlib
import types
import unittest
from unittest import mock

from aieos_bootstrap import base_inputs
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

    def test_other_tasks_events_and_ignored_duplicates_are_left_out(self):
        """TASK-027 AC2 and TASK-027 AC7: another task's task.approved, task.stale and record.added change nothing for
        this task, and are not given to the governor."""
        log = base_log()
        log.add('task.approved', {'contract_version': 'v1', 'contract_hash': 'f' * 64, 'approval_record': 'x'}, 'o-1',
                task_id='TASK-099')
        log.add('task.stale', {'cause': 'intent_change', 'refers_to': 'CHG-001'}, 'o-2', task_id='TASK-099')
        log.add('record.added', record('r-other', subject='TASK-099'), 'o-3', task_id='TASK-099')
        seen = []
        real = governor.evaluate
        governor.evaluate = lambda q, i, rs: seen.append(rs) or real(q, i, rs)
        try:
            r = run(log)[0]
        finally:
            governor.evaluate = real
        self.assertEqual(r['result'], 'evaluated')
        self.assertEqual(seen[0], [])

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
            for key in (('cat-file', cid(2)), ('cat-file', cid(3)), ('cat-file', cid(1)), ('diff-tree', cid(3))):
                if key[0] == 'diff-tree' and isinstance(given, dict) and given.get('exit') == 0:
                    continue  # bytes that parse as a path are R5's case (other changed paths), not a failed read
                r, log, _ = run(git=Repo(chain(), {key: given}))
                self.assertEqual((r['result'], r['reason'], log.appends), ('refused', 'git', []), (key, given))


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
    def test_a_list_subclass_is_refused_and_the_governor_gets_the_computed_paths(self):
        """TASK-027 AC6: changed_paths given as a list subclass, even one equal to the union, give "refused", reason
        "values"; with a plain list, derive_inputs receives the computed list, not the caller's object."""
        class Rigged(list):
            pass

        self.assertEqual(run(values=values(changed_paths=Rigged(PATHS)))[0]['reason'], 'values')
        seen = []
        real = governor.derive_inputs

        def spy(v):
            seen.append(v['changed_paths'])
            return real(v)

        given = values()
        governor.derive_inputs = spy
        try:
            self.assertEqual(run(values=given)[0]['result'], 'evaluated')
        finally:
            governor.derive_inputs = real
        self.assertEqual(seen[0], PATHS)
        self.assertIsNot(seen[0], given['changed_paths'])

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
    def test_the_event_id_uses_the_sorted_kept_record_ids_only(self):
        """TASK-027 AC8: with two kept records and one left out, the event id is derived from the two kept record ids,
        sorted, and not from the left-out one."""
        log = base_log().add('record.added', record('r-z'), 'ra-z')
        r = run(log, extra_records=[record('r-a'), {'record_id': 'r-bad'}])[0]
        want = hashlib.sha256('\n'.join(['evaluation', TASK, 'submitted-1', 'r-a', 'r-z']).encode()).hexdigest()
        self.assertEqual(r['event_id'], want)
        self.assertEqual(log.appends[0][3], want)

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
        os_attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                    and n.value.id == 'os'}
        self.assertEqual(os_attrs, {'path'})
        self.assertNotIn('.aieos', MODULE.read_text(encoding='utf-8'))


class TASK128OwnerKeptBinding(unittest.TestCase):
    """TASK-128 Part B (DEF-0117 first gap, option d3 of D-5526): the governor never sees an owner_kept_act False that
    the approved contract bytes do not carry; the other values fields stay caller data."""

    EXACT = b'task: TASK-027\nowner_kept_act: false\n'

    def go(self, contract_bytes, owner_kept=False):
        """One evaluation over contract_bytes (approved by their own hash) with values owner_kept_act = owner_kept;
        returns (result, the owner_kept_act values the governor's derive_inputs received, the values given, a deep
        copy of the values taken before the call)."""
        log = submitted(approved(Log(), chash=hashlib.sha256(contract_bytes).hexdigest()), cid(3))
        v = values()
        v['contract'] = dict(v['contract'], owner_kept_act=owner_kept)
        before = copy.deepcopy(v)
        seen = []
        real = governor.derive_inputs

        def spy(vals):
            seen.append(vals['contract']['owner_kept_act'])
            return real(vals)

        with mock.patch.object(governor, 'derive_inputs', spy):
            r, _, _ = run(log, contract_bytes=contract_bytes, values=v)
        return r, seen, v, before

    def test_an_exact_false_line_lets_a_false_reach_the_governor(self):
        """TASK-027 AC6 (amended by TASK-128 AC3): the bytes hold exactly one line owner_kept_act: false at column 0
        and values say False: the governor sees False and the evaluation is made."""
        r, seen, _, _ = self.go(self.EXACT)
        self.assertEqual(r['result'], 'evaluated', r)
        self.assertEqual(seen, [False])

    def test_values_false_with_bytes_true_is_seen_as_true(self):
        """TASK-027 AC6 (amended by TASK-128 AC3): values say False, the bytes say owner_kept_act: true: the governor
        sees True and the evaluation is not refused for that reason."""
        r, seen, _, _ = self.go(b'task: TASK-027\nowner_kept_act: true\n')
        self.assertEqual((r['result'], seen), ('evaluated', [True]), r)

    def test_each_not_false_form_of_the_bytes_is_seen_as_true(self):
        """TASK-027 AC6 (amended by TASK-128 AC3): the key missing, a duplicate key (also with a true line), a case
        variant, a spacing variant (a leading space, a space before the colon, two spaces after it, a CRLF line end, a
        tab, a trailing space) and bytes that are not UTF-8: each gives True to the governor, with no refusal for
        that reason."""
        forms = [b'task: TASK-027\n',
                 b'task: TASK-027\nowner_kept_act: false\nowner_kept_act: false\n',
                 b'task: TASK-027\nowner_kept_act: false\nowner_kept_act: true\n',
                 b'task: TASK-027\nOwner_kept_act: false\n', b'task: TASK-027\nowner_kept_act: False\n',
                 b'task: TASK-027\nOWNER_KEPT_ACT: false\n',
                 b'task: TASK-027\n owner_kept_act: false\n', b'task: TASK-027\nowner_kept_act : false\n',
                 b'task: TASK-027\nowner_kept_act:  false\n', b'task: TASK-027\nowner_kept_act: false\r\n',
                 b'task: TASK-027\nowner_kept_act:\tfalse\n', b'task: TASK-027\nowner_kept_act: false \n',
                 b'task: TASK-027\nowner_kept_act: false\n\xff\xfe\n']
        for form in forms:
            r, seen, _, _ = self.go(form)
            self.assertEqual((r['result'], seen), ('evaluated', [True]), (form, r))

    def go_mapping(self, contract_bytes, mapping):
        """One evaluation over contract_bytes (approved by their own hash) with values['contract'] = mapping; returns
        (result, the log, the contract mappings the governor's derive_inputs received, the requests of
        governor.evaluate)."""
        log = submitted(approved(Log(), chash=hashlib.sha256(contract_bytes).hexdigest()), cid(3))
        v = values()
        v['contract'] = mapping
        seen, requests = [], []
        real, real_eval = governor.derive_inputs, governor.evaluate

        def spy(vals):
            seen.append(vals['contract'])
            return real(vals)

        with mock.patch.object(governor, 'derive_inputs', spy), \
                mock.patch.object(governor, 'evaluate', lambda q, i, rs: requests.append(q) or real_eval(q, i, rs)):
            r, lg, _ = run(log, contract_bytes=contract_bytes, values=v)
        return r, lg, seen, requests

    def test_each_line_break_or_invisible_character_form_is_seen_as_true(self):
        """TASK-027 AC6 (amended by TASK-128 AC3, the review findings): an exact line and, with it, a bare CR, a byte-order
        mark, a vertical tab, U+0085, U+2028, U+2029, a zero-width space or U+2060 each make the contract text not
        false: the governor sees True with values False, with no refusal for that reason."""
        forms = [b'task: TASK-027\rowner_kept_act: true\nowner_kept_act: false\n',
                 b'\xef\xbb\xbfowner_kept_act: true\nowner_kept_act: false\n',
                 b'task: TASK-027\x0bowner_kept_act: true\nowner_kept_act: false\n',
                 b'task: TASK-027\xc2\x85owner_kept_act: true\nowner_kept_act: false\n',
                 b'task: TASK-027\xe2\x80\xa8owner_kept_act: true\nowner_kept_act: false\n',
                 b'task: TASK-027\xe2\x80\xa9owner_kept_act: true\nowner_kept_act: false\n',
                 b'task: TASK-027\n\xe2\x80\x8bowner_kept_act: true\nowner_kept_act: false\n',
                 b'task: TASK-027\n\xe2\x81\xa0owner_kept_act: true\nowner_kept_act: false\n']
        for form in forms:
            r, seen, _, _ = self.go(form)
            self.assertEqual((r['result'], seen), ('evaluated', [True]), (form, r))

    def test_each_quoted_or_explicit_key_spelling_is_seen_as_true(self):
        """TASK-027 AC6 (amended by TASK-128 AC3, the review findings): an exact line and, after it, a second line that
        holds the key in double quotes, in single quotes, after a question mark or after a space and a quote each make
        the contract text not false: the governor sees True with values False."""
        forms = [b'task: TASK-027\nowner_kept_act: false\n"owner_kept_act": true\n',
                 b"task: TASK-027\nowner_kept_act: false\n'owner_kept_act': true\n",
                 b'task: TASK-027\nowner_kept_act: false\n? owner_kept_act\n: true\n',
                 b'task: TASK-027\nowner_kept_act: false\n?owner_kept_act\n',
                 b'task: TASK-027\nowner_kept_act: false\n "owner_kept_act": true\n']
        for form in forms:
            r, seen, _, _ = self.go(form)
            self.assertEqual((r['result'], seen), ('evaluated', [True]), (form, r))

    def test_a_comment_line_is_not_another_line(self):
        """TASK-027 AC6 (amended by TASK-128 AC3, the review findings): an exact line and a comment line that begins with a
        number sign and names the key leave the contract text false: the governor sees False (a comment is never
        counted as another line)."""
        r, seen, _, _ = self.go(b'task: TASK-027\nowner_kept_act: false\n# owner_kept_act: false: ruled at D-5526 Q4\n')
        self.assertEqual((r['result'], seen), ('evaluated', [False]), r)

    def check_true(self, forms):
        """Each form: the contract reader refuses it, the governor sees True with values False, and the evaluation is
        made."""
        for form in forms:
            with self.assertRaises(base_inputs._Stop, msg=form):
                base_inputs._parse_contract_text(form.decode('utf-8'))
            r, seen, _, _ = self.go(form)
            self.assertEqual((r['result'], seen), ('evaluated', [True]), (form, r))

    def test_each_key_form_the_contract_reader_refuses_is_seen_as_true(self):
        """TASK-027 AC6 (amended by TASK-128 AC3, the review findings of D-5578): an exact line and, in the same text, a
        second key under a form the contract reader refuses (a double-quoted key with a backslash, a tag, an anchor, an
        alias key after an anchor line, a flow continuation with a comma, a flow mapping at the top, a document
        marker) make the contract text not false: the governor sees True with values False."""
        self.check_true([
            b'task: TASK-027\nowner_kept_act: false\n"owner\\x5fkept_act": true\n',
            b'task: TASK-027\nowner_kept_act: false\n!!str owner_kept_act: true\n',
            b'task: TASK-027\nowner_kept_act: false\n&k owner_kept_act: true\n',
            b'task: TASK-027\nref: &a owner_kept_act\nowner_kept_act: false\n*a : true\n',
            b'{ x: 1\nowner_kept_act: false\n, owner_kept_act: true }\n',
            b'---\nowner_kept_act: false\n',
            b'task: TASK-027\nowner_kept_act: false\n...\n'])

    def test_an_exact_line_inside_an_unclosed_value_is_seen_as_true(self):
        """TASK-027 AC6 (amended by TASK-128 AC3, the review findings of D-5578): an exact line that follows a
        double-quoted value that does not close on its line, or an unclosed flow list, or that sits inside a sequence
        item's unclosed double-quoted value, is not false: the governor sees True with values False."""
        self.check_true([
            b'task: TASK-027\nnote: "x\nowner_kept_act: false\ny"\n',
            b'task: TASK-027\nx: [\nowner_kept_act: false\n]\n',
            b'task: TASK-027\nx:\n- "a\nowner_kept_act: false\n  b"\n',
            b'task: TASK-027\nx:\n- [a,\nowner_kept_act: false\n  b]\n'])

    def test_an_exact_line_after_a_sequence_or_empty_value_out_of_place_is_seen_as_true(self):
        """TASK-027 AC6 (amended by TASK-128 AC3, the review findings of D-5578): an exact line in a text whose top
        level is a sequence, with a sequence item that does not follow an empty-value key, after an empty-value key
        that is not followed by an indented line or a sequence item, after an indented first line, or with a repeated
        key, is not false: the governor sees True with values False."""
        self.check_true([
            b'- a\nowner_kept_act: false\n',
            b'task: TASK-027\nowner_kept_act: false\n- a\n',
            b'a:\nowner_kept_act: false\n',
            b'task:\n  a: 1\n- b\nowner_kept_act: false\n',
            b' task: TASK-027\nowner_kept_act: false\n',
            b'task: TASK-027\nowner_kept_act: false\ntask: TASK-028\n',
            b'task: TASK-027\nowner_kept_act: false\nx:\n',
            b'task: TASK-027\nowner_kept_act: false\nf: >-\n',
            b'task: TASK-027\nx:\n- >-\nowner_kept_act: false\n',
            b'task: TASK-027\nx:\n- k:\nowner_kept_act: false\n'])

    def test_an_exact_line_with_a_plain_value_the_reader_refuses_is_seen_as_true(self):
        """TASK-027 AC6 (amended by TASK-128 AC3, the review findings of D-5578): an exact line and a plain value that
        starts with an indicator character, is a dash or starts with a dash and a space, holds a space and a number
        sign or a colon and a space, or ends with a colon, make the text not false: the governor sees True."""
        self.check_true([b'task: TASK-027\nowner_kept_act: false\nnote: @x\n',
                         b'task: TASK-027\nowner_kept_act: false\nnote: -\n',
                         b'task: TASK-027\nowner_kept_act: false\nnote: - x\n',
                         b'task: TASK-027\nowner_kept_act: false\nnote: a #b\n',
                         b'task: TASK-027\nowner_kept_act: false\nnote: a: b\n',
                         b'task: TASK-027\nowner_kept_act: false\nnote: a:\n'])

    def test_the_forms_the_reader_accepts_leave_the_exact_line_false(self):
        """TASK-027 AC6 (amended by TASK-128 AC3, the review findings of D-5578): an exact line in a text of the
        shapes the contract reader accepts (a sequence under an empty-value key, a double-quoted value, a closed flow
        list, a flow list continued on an indented line, a folded value, an indented block and a comment) stays
        false: the governor sees False."""
        text = (b'task: TASK-027\nowner_kept_act: false\nitems:\n- a\n- "b"\n- k: v\nnote: "q"\n'
                b'flow: [1, 2]\nmulti: [1,\n  2]\nfolded: >-\n  text\n  more\nblock:\n  inner: 1\n# comment\n')
        base_inputs._parse_contract_text(text.decode('utf-8'))
        r, seen, _, _ = self.go(text)
        self.assertEqual((r['result'], seen), ('evaluated', [False]), r)

    def test_a_bytes_subclass_cannot_change_what_is_read(self):
        """TASK-027 AC6 (amended by TASK-128 AC3, the review findings of D-5578): a bytes subclass whose decode() answers an
        exact line while its bytes say otherwise (the hash is taken over the bytes): the governor sees True."""
        class Sly(bytes):
            def decode(self, *args, **kwargs):
                return 'owner_kept_act: false\n'

        r, seen, _, _ = self.go(Sly(b'task: TASK-027\n'))
        self.assertEqual((r['result'], seen), ('evaluated', [True]), r)

    def test_an_indented_line_right_after_the_exact_line_is_seen_as_true(self):
        """TASK-027 AC6 (amended by TASK-128 AC3, the review findings of D-5602): an exact line followed directly by an
        indented line makes the contract reader read the value as the string "false true", so the governor is given
        True with values False."""
        text = b'task: TASK-027\nowner_kept_act: false\n  true\n'
        self.assertEqual(base_inputs._parse_contract_text(text.decode('utf-8'))['owner_kept_act'], 'false true')
        r, seen, _, _ = self.go(text)
        self.assertEqual((r['result'], seen), ('evaluated', [True]), r)

    def test_an_exact_line_followed_by_a_blank_line_and_an_indented_comment_stays_false(self):
        """TASK-027 AC6 (amended by TASK-128 AC3, the review findings of D-5602): an exact line, a blank line, an
        indented comment and a key leave the text false: the contract reader reads the string false and the governor
        is given False."""
        text = b'task: TASK-027\nowner_kept_act: false\n\n  # c\nnext: x\n'
        self.assertEqual(base_inputs._parse_contract_text(text.decode('utf-8'))['owner_kept_act'], 'false')
        r, seen, _, _ = self.go(text)
        self.assertEqual((r['result'], seen), ('evaluated', [False]), r)

    def test_the_governor_reads_the_copy_that_was_tested(self):
        """TASK-027 AC6 (amended by TASK-128 AC3, the review findings): a dict subclass whose get() answers True for the
        key while its subscript gives False, with bytes that are not false: the governor receives a plain dict whose
        owner_kept_act is True, not the subclass."""
        class Sly(dict):
            def get(self, key, default=None):
                return True if key == 'owner_kept_act' else dict.get(self, key, default)

        contract = Sly(values()['contract'])
        self.assertIs(contract['owner_kept_act'], False)
        r, _, seen, _ = self.go_mapping(CONTRACT, contract)
        self.assertEqual(r['result'], 'evaluated', r)
        self.assertEqual([type(c) for c in seen], [dict])
        self.assertIs(seen[0]['owner_kept_act'], True)
        self.assertIs(contract['owner_kept_act'], False)

    def test_a_contract_that_is_not_a_plain_dict_or_lacks_the_key_is_refused(self):
        """TASK-027 AC6 (amended by TASK-128 AC3): a non-dict mapping holding owner_kept_act False, and a dict without the
        key, are passed on as before and derive_inputs refuses them: "refused", reason "values", nothing appended and
        governor.evaluate not called."""
        base = values()['contract']
        for contract in (types.MappingProxyType(base), {k: x for k, x in base.items() if k != 'owner_kept_act'}):
            r, lg, _, requests = self.go_mapping(CONTRACT, contract)
            self.assertEqual((r['result'], r['reason'], lg.appends, requests), ('refused', 'values', [], []), r)

    def test_values_true_with_bytes_false_stays_true(self):
        """TASK-027 AC6 (amended by TASK-128 AC3): values say True and the bytes say owner_kept_act: false: the
        governor sees True (stricter is allowed, a True is never lowered)."""
        r, seen, _, _ = self.go(self.EXACT, owner_kept=True)
        self.assertEqual((r['result'], seen), ('evaluated', [True]), r)

    def test_the_callers_values_are_unchanged(self):
        """TASK-027 AC6 (amended by TASK-128 AC3): after a call in which the governor saw True (bytes not false, values
        False) and after one in which it saw False (the exact line), the caller's values mapping equals the deep copy
        taken before the call."""
        for form in (b'task: TASK-027\n', self.EXACT):
            _, _, given, before = self.go(form)
            self.assertEqual(given, before, form)

    def test_the_docstring_states_the_binding_and_the_limit(self):
        """TASK-027 AC13 (amended by TASK-128 AC4): the module docstring says what the binding does and that the
        other values fields stay caller data."""
        doc = evaluation.__doc__
        self.assertIn('owner_kept_act', doc)
        self.assertIn('the other values fields stay caller data', doc)
        self.assertIn('owner_kept_act: false', doc)
        self.assertIn('reads lines, not YAML', doc)


if __name__ == '__main__':
    unittest.main()

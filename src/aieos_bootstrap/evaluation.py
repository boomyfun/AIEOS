"""The evaluation path of gov-AIEOS (task TASK-027; specification 1 section 5.1; specification 2 sections 2, 6.1, 6.3,
6.4 and 6.5; governor-spec.md sections 3 and 4; DEF-0030): the last named piece of the core's caller.

``evaluate_task(root, repo, task_id, contract_bytes, declared, values, extra_records, recorder, now)`` evaluates one
task in VERIFYING (after its task.submitted) or in IN_REVIEW (re-evaluation):

1. Arguments (AC1): every argument is checked before anything is read; a wrong one gives a refusal result.
2. The log (AC2): read through writer.read_log and checked by records.check_log; from the task's own events after its
   last task.approved: the state (VERIFYING after a task.submitted; the next_task_state of a decision.acceptance, which
   sets nothing when it is absent, null or equal to the state already set: erratum E1 to AC2, decision D-636;
   specification 1 section 5.1, a decision that keeps the task IN_REVIEW changes nothing), the state-setting event,
   the evaluated commit (the last task.submitted's commit) and the retries used (the decision.acceptance events that
   sent the task to REWORK, specification 1 line 73). Any other "task." event after the approval leaves a state this
   path does not evaluate, so it is a refusal.
3. The contract (AC3): the caller's bytes must hash to the approved contract_hash; task_content_hash is the SHA-256 of
   those bytes, one LF and the evaluated commit id (specification 2 section 2).
4. The task's commits (AC4, decisions D-633 point 5 and D-634): walked back from the evaluated commit through
   gitread.run, each read once with "cat-file -p" and parsed by gitread.parse_commit. A commit belongs to the task
   when its message has a body and recovery.trailers names the task with no finding (DEF-0052 F6). A trailer finding,
   or this task's AIEOS-Task line in a message with no body, refuses; a merge among the task's commits refuses; the
   walk ends at the first
   commit whose trailers give no finding and name no task or another task, or after a commit with no parent.
5. The changed paths (AC5): the union of the paths each task commit changes against its first parent, read with the
   pinned diff-tree form and parsed by gitread.parse_paths.
6. The inputs (AC6): values["changed_paths"] must be a list equal to that union; governor.derive_inputs is given a copy
   of values holding the computed list, so no object of the caller's stands for the paths; the request is
   specification 2 section 6.5's.
7. The records (AC7; task TASK-053 AC1): the task's record.added and violation.detected payloads in log order, over
   the whole log, then extra_records; a record that records.check_record finds out of form, or whose record_id an
   earlier kept record has, is left out with a finding. A violation.detected payload is an observation with outcome
   blocking and blocking_kind violation, so the governor's row 1 gives REJECT (task TASK-053 AC2). A record left out
   whose outcome is 'blocking' refuses the evaluation with reason "records" (task TASK-054 AC1; decision D-1027,
   form (ii)), unless its record_id equals that of an earlier kept record whose outcome is 'blocking' with the same
   blocking_kind (that one already blocks with the same kind); the findings hold those of the records left out and
   one per such record, naming its record_id (or its position when it has none) and its source; nothing is appended
   and governor.evaluate is not called.
8. The decision (AC7, AC8): governor.evaluate is called once and its record, an error record included, is appended
   once as decision.acceptance through writer.append_event, with no fencing token, under an event id derived from the
   task, the state-setting event and the kept record ids, so a rerun while the task is still evaluable gives
   "duplicate" (AC9); after a REJECT the rerun is refused with reason "state" (task TASK-053, erratum E1 to its AC2).

The result (AC11) is a mapping with exactly the keys result ("evaluated", "duplicate" or "refused"), reason, findings,
event_id, changed_paths, decision and next_task_state. A refusal's reason is one of argument, log, state, contract,
git, merge, bound, values, governor, store and records (the last added by task TASK-054). An exception raised by a
called function is caught and becomes a result; none escapes.

``read``, ``read_log`` and ``append`` default, at call time, to gitread.run, writer.read_log and writer.append_event
(AC10); tests pass stand-ins.

Purity (AC12): this module starts no process except through ``read``, opens no file itself, reads no clock and no
environment variable, grants and releases no lease, creates no store and builds no event-log line itself.

Limits (AC13):
- The PATH git is found by is the caller's precondition (DEF-0052 G1).
- declared (intent_versions and retries) and values (the contract's declared fields, the policy's rules, the articles,
  the profiles, the delegation and the versions) are caller data, not bound to the hashed contract bytes, as the
  governor's own limit says (decision D-633 C1). This repository's contracts write input_state.intent_versions as path
  to SHA-256, not specification 2's version form, so the caller maps them (decision D-634 E1).
- One evaluation of a task runs at a time: the writer reads the log and appends with no check that it is unchanged
  since this module's read.
- The walk has a bound and reads every task commit each time. It ends at the first commit without the task's trailer,
  so a task commit that lacked it would end the walk early (the CI's G0 refuses such a commit). A merge in the task's
  commits is refused. The first commit below the task's commits is read by the same trailer rule, so a trailer
  finding there (an AIEOS-Task line in another case, or outside its message's last paragraph) refuses every
  evaluation of the task (fail closed).
- State transitions are not checked: the state is the last state-setting event's, so a log that the writer let
  through out of the state machine's order (for example a decision with next_task_state IN_REVIEW after one with
  REWORK and no new submission) is evaluated on the last submission's commit. By erratum E1, two REWORK decisions with
  no other state between them count once in the retries used.
- The event id does not cover declared or values: a rerun over the same state-setting event and records with other
  declared, values or policy gives "duplicate", and the result's decision and next_task_state are then those of the
  record just computed, not of the record stored before.
- Records of the CI channel are the caller's to give (no network). The records of specification 4 section 10 and its
  reconciliation are not made here.
- The tests use stand-ins for the writer, so the real store's path is covered by the writer's tests and not end to
  end.
- A violation.detected of the task anywhere in the log makes every later evaluation of the task REJECT, also after a
  later task.approved and a new submission, as a blocking record.added does (task TASK-053 AC4; decision D-1012 M1),
  where the task is evaluable (VERIFYING or IN_REVIEW; elsewhere the evaluation is refused with reason "state"),
  unless a blocking record left out refuses it with reason "records" (task TASK-054).
  A session fenced out leaves no violation.detected, only the writer's refusal record, read as before.
- Of task TASK-054 (its AC3 and AC8), the cost of failing closed: a blocking record left out, out of form or for a
  repeated record_id, refuses every evaluation of the task with reason "records" and nothing appended, the rerun
  included and also after a later task.approved and a new submission (the span is the whole log), so such a task is
  neither accepted nor rejected by evaluation and stays in VERIFYING or IN_REVIEW until it is superseded by a new
  task; one given only through extra_records refuses only while it is given. event_id_of and the governor are
  unchanged; records.py's uniqueness rule is unchanged (a repeated record_id is still accepted into the log); a
  repeated record_id between records that are not blocking is left out with a finding as before; the limits of task
  TASK-053 (its AC7) stand; no conformance set or fixture is changed.
- Also of task TASK-053 (its AC7): no task.* event follows STOP: violation, so until an evaluation runs the task stays
  READY with no lease and the next Resume Check may CONTINUE again; no bound on repeated STOP: violation
  (specification 5 section 11 point 12); a fence refusal's record is labelled refused_submission; F-a is kept (replay
  needs a fresh root from its caller); a passing replay with a violation shows the core's handling of a recorded
  violation, never that any hook observes anything (C6 unmeasured); no conformance set or fixture is changed
  (ADV-02's fixture is a later task); no observed read-set call is made; a run against the real writer's files is not
  tested.
"""

import datetime
import hashlib
import os
import re

from aieos_bootstrap import gitread
from aieos_bootstrap import governor
from aieos_bootstrap import records
from aieos_bootstrap import recovery
from aieos_bootstrap import writer

_TASK = re.compile(r'TASK-[0-9]+')
_VERSION = re.compile(r'v[0-9]+')
_PARAGRAPH = re.compile(r'\n[ \t]*\n')
_ZERO = datetime.timedelta(0)
ID_PREFIX = 'evaluation'
EVENT_TYPE = 'decision.acceptance'
EVALUABLE = ('VERIFYING', 'IN_REVIEW')
RECORD_EVENTS = ('record.added', 'violation.detected')  # task TASK-053 AC1
RESULT_KEYS = frozenset({'result', 'reason', 'findings', 'event_id', 'changed_paths', 'decision', 'next_task_state'})
DIFF_FORM = ['diff-tree', '--no-commit-id', '--name-only', '-r', '--no-renames', '--no-ext-diff', '--no-textconv', '-z',
             '--root']


class _Stop(Exception):
    """A refusal found inside a step: its reason and findings."""

    def __init__(self, reason, findings):
        Exception.__init__(self, reason)
        self.reason = reason
        self.findings = list(findings)


def _result(result, reason=None, findings=(), event_id=None, changed_paths=None, decision=None, next_task_state=None):
    return {'result': result, 'reason': reason, 'findings': list(findings), 'event_id': event_id,
            'changed_paths': changed_paths, 'decision': decision, 'next_task_state': next_task_state}


def _is_str(value):
    return isinstance(value, str) and value != ''


def _is_int(value, low, high):
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def _argument_findings(root, repo, task_id, contract_bytes, declared, values, extra_records, recorder, now, max_commits):
    """AC1: what is wrong with the arguments, as a list of findings (empty when every argument is in form)."""
    found = []
    for name, value in (('root', root), ('repo', repo)):
        if not (_is_str(value) and os.path.isabs(value)):
            found.append('argument: %s is not a non-empty absolute path string' % name)
    if not (isinstance(task_id, str) and _TASK.fullmatch(task_id)):
        found.append('argument: task_id is not TASK- followed by digits')
    if not isinstance(contract_bytes, bytes):
        found.append('argument: contract_bytes is not bytes')
    ok = isinstance(declared, dict) and set(declared) == {'intent_versions', 'retries'}
    iv = declared.get('intent_versions') if ok else None
    if not (ok and isinstance(iv, dict) and all(_is_str(k) and isinstance(v, str) and _VERSION.fullmatch(v)
                                                 for k, v in iv.items())):
        found.append('argument: declared is not {intent_versions: {id: "v" and digits}, retries}')
    elif not _is_int(declared['retries'], 0, 100):
        found.append('argument: declared retries is not an int from 0 to 100')
    if not isinstance(values, dict):
        found.append('argument: values is not a dict')
    if not isinstance(extra_records, list):
        found.append('argument: extra_records is not a list')
    if not _is_str(recorder):
        found.append('argument: recorder is not a non-empty string')
    if not (isinstance(now, datetime.datetime) and now.tzinfo is not None and now.utcoffset() == _ZERO
            and now.microsecond == 0):
        found.append('argument: now is not a timezone-aware datetime in UTC with whole seconds')
    if not _is_int(max_commits, 1, 10000):
        found.append('argument: max_commits is not an int from 1 to 10000')
    return found


def _task_events(read_log, root, task_id):
    """AC2: (contract_hash, state, state-setting event_id, evaluated commit, retries used, the task's record payloads)."""
    data = read_log(root)
    if not isinstance(data, bytes):
        raise _Stop('log', ['log: read_log gave %s, not bytes' % type(data).__name__])
    report = records.check_log(data)
    found = ['log: line %d: %s' % (n, f) for n, f in report.findings()]
    if found:
        raise _Stop('log', found)
    events = [line.event for line in report.lines if line.duplicate_of is None]
    mine = [e for e in events if e.get('task_id') == task_id]
    approved = [i for i, e in enumerate(mine) if e['type'] == 'task.approved']
    if not approved:
        raise _Stop('state', ['state: the log holds no task.approved of %s' % task_id])
    contract_hash = mine[approved[-1]]['payload']['contract_hash']
    state = setter = commit = None
    used = 0
    for e in mine[approved[-1] + 1:]:
        kind = e['type']
        if kind == 'task.submitted':
            state, setter, commit = 'VERIFYING', e['event_id'], e['payload']['commit']
        elif kind == EVENT_TYPE:
            nxt = e['payload'].get('next_task_state')
            if isinstance(nxt, str) and nxt != state:  # erratum E1 to AC2 (decision D-636)
                state, setter = nxt, e['event_id']
                if nxt == 'REWORK':
                    used += 1
        elif kind.startswith('task.'):
            raise _Stop('state', ['state: %s after the last task.approved leaves a state this path does not '
                                  'evaluate' % kind])
    if state not in EVALUABLE or commit is None:
        raise _Stop('state', ['state: the task is in %s with %s; only VERIFYING or IN_REVIEW after a submission is '
                              'evaluated' % (state, 'no submission' if commit is None else 'a submission')])
    payloads = [e['payload'] for e in events if e['type'] in RECORD_EVENTS and e.get('task_id') == task_id]
    return contract_hash, state, setter, commit, used, payloads


def _read_failure(name, r):
    """AC4, AC5: why a read result does not count, or None when it does."""
    if not isinstance(r, dict) or not {'exit', 'out', 'err', 'error'} <= set(r):
        return 'git: %s gave no result in gitread.run\'s form' % name
    if r['error'] is not None:
        return 'git: %s was not run or did not finish: %s' % (name, r['error'])
    if r['exit'] != 0:
        return 'git: %s exited with %r' % (name, r['exit'])
    return None


def _belongs(message, task_id):
    """AC4 (decision D-634): True when the commit is the task's, False when the walk ends at it; raises _Stop for a
    trailer finding or this task's AIEOS-Task line in a message with no body."""
    trailer, findings = recovery.trailers(message)
    if findings:
        raise _Stop('git', ['git: a commit\'s trailers give a finding: %s' % '; '.join(findings)])
    paragraphs = [p for p in _PARAGRAPH.split(message.strip('\n')) if p.strip()]
    if trailer['task'] != task_id:
        return False
    if len(paragraphs) < 2:
        raise _Stop('git', ['git: a message with no body names %s; its trailer is not trusted (DEF-0052 F6)' % task_id])
    return True


def _task_commits(read, repo, task_id, commit, max_commits):
    """AC4: the task's commits, newest first."""
    out = []
    current = commit
    while current is not None:
        r = read(repo, ['cat-file', '-p', current])
        why = _read_failure('cat-file -p %s' % current, r)
        if why is not None:
            raise _Stop('git', [why])
        parsed = gitread.parse_commit(r['out'])
        if parsed['error'] is not None:
            raise _Stop('git', ['git: commit %s is out of form: %s' % (current, parsed['error'])])
        if not _belongs(parsed['message'], task_id):
            if not out:
                raise _Stop('git', ['git: the evaluated commit %s is not a commit of %s' % (current, task_id)])
            break
        if len(parsed['parents']) > 1:
            raise _Stop('merge', ['merge: commit %s has %d parents; a task has no merge' % (current, len(parsed['parents']))])
        out.append(current)
        if len(out) > max_commits:
            raise _Stop('bound', ['bound: the task has more than %d commits' % max_commits])
        current = parsed['parents'][0] if parsed['parents'] else None
    return out


def _changed_paths(read, repo, commits):
    """AC5: the union of the task's commits' paths, sorted."""
    paths = set()
    for c in commits:
        r = read(repo, DIFF_FORM + [c])
        why = _read_failure('diff-tree %s' % c, r)
        if why is not None:
            raise _Stop('git', [why])
        parsed = gitread.parse_paths(r['out'])
        if parsed['error'] is not None:
            raise _Stop('git', ['git: the paths of %s are out of form: %s' % (c, parsed['error'])])
        paths.update(parsed['paths'])
    if not paths:
        raise _Stop('git', ['git: the task\'s commits change no path'])
    return sorted(paths)


def _kept(payloads, extra_records):
    """AC7: the records the governor reads, a finding for each one left out, and (task TASK-054 AC1) a finding for
    each left-out record whose outcome is 'blocking', unless its record_id equals that of an earlier kept blocking
    record with the same blocking_kind."""
    kept, found, hidden, seen, kinds = [], [], [], set(), {}
    for n, (where, rec) in enumerate([('log', p) for p in payloads] + [('extra_records', r) for r in extra_records], 1):
        problems = records.check_record(rec)
        rid = rec.get('record_id') if isinstance(rec, dict) else None
        if problems:
            found.append('records: a record from %s is left out: %s' % (where, '; '.join(str(f) for f in problems)))
        elif not isinstance(rid, str) or rid in seen:
            found.append('records: a record from %s is left out: its record_id %r is repeated' % (where, rid))
        else:
            seen.add(rid)
            kept.append(rec)
            if rec.get('outcome') == 'blocking':
                kinds[rid] = rec.get('blocking_kind')
            continue
        if not (isinstance(rec, dict) and rec.get('outcome') == 'blocking'):
            continue
        if isinstance(rid, str) and rid in kinds and kinds[rid] == rec.get('blocking_kind'):
            continue
        name = 'record_id %r' % rid if isinstance(rid, str) else 'the record at position %d' % n
        hidden.append('records: a blocking record from %s, %s, is left out; the evaluation is refused so that it '
                      'is not hidden from the governor' % (where, name))
    return kept, found, hidden


def event_id_of(task_id, setter, record_ids):
    """AC8 (decision D-633 (f)): the SHA-256 hex digest of "evaluation", the task id, the state-setting event's
    event_id and the kept record ids, sorted, joined by LF."""
    return hashlib.sha256('\n'.join([ID_PREFIX, task_id, setter] + sorted(record_ids)).encode('utf-8')).hexdigest()


def evaluate_task(root, repo, task_id, contract_bytes, declared, values, extra_records, recorder, now,
                  max_commits=1000, read=None, read_log=None, append=None):
    """Evaluate one task (TASK-027 AC1 to AC11); returns a mapping with RESULT_KEYS."""
    read = gitread.run if read is None else read
    read_log = writer.read_log if read_log is None else read_log
    append = writer.append_event if append is None else append

    try:
        found = _argument_findings(root, repo, task_id, contract_bytes, declared, values, extra_records, recorder,
                                   now, max_commits)
    except Exception as exc:  # AC11: an argument whose own methods raise
        found = ['argument: checking the arguments raised %s' % type(exc).__name__]
    if found:
        return _result('refused', 'argument', found)

    event_id = paths = None
    step = 'log'
    left_out = []
    try:
        contract_hash, state, setter, commit, used, payloads = _task_events(read_log, root, task_id)
        step = 'contract'
        if hashlib.sha256(contract_bytes).hexdigest() != contract_hash:
            raise _Stop('contract', ['contract: the bytes given do not hash to the approved contract_hash'])
        content_hash = hashlib.sha256(contract_bytes + b'\n' + commit.encode('ascii')).hexdigest()
        step = 'git'
        commits = _task_commits(read, repo, task_id, commit, max_commits)
        paths = _changed_paths(read, repo, commits)
        step = 'values'
        given = values.get('changed_paths')
        if not (type(given) is list and given == paths):
            raise _Stop('values', ['values: changed_paths differ from the task\'s change: computed %r, given %r'
                                   % (paths, given)])
        try:
            inputs = governor.derive_inputs(dict(values, changed_paths=list(paths)))
        except Exception as exc:  # AC6
            raise _Stop('values', ['values: derive_inputs raised %s: %s' % (type(exc).__name__, exc)])
        request = {'task_id': task_id, 'task_content_hash': content_hash, 'evaluated_commit': commit,
                   'intent_versions': dict(declared['intent_versions']), 'task_state': state,
                   'changed_paths': list(paths), 'retry_count': {'used': used, 'limit': declared['retries']}}
        step = 'governor'
        kept, left_out, hidden = _kept(payloads, extra_records)
        if hidden:  # task TASK-054 AC1: nothing is appended and the governor is not called
            raise _Stop('records', left_out + hidden)
        try:
            record = governor.evaluate(request, inputs, kept)
        except Exception as exc:  # AC7
            raise _Stop('governor', left_out + ['governor: evaluate raised %s' % type(exc).__name__])
        event_id = event_id_of(task_id, setter, [r['record_id'] for r in kept])
        decision = record.get('decision')
        nxt = record.get('next_task_state')
    except _Stop as stop:
        return _result('refused', stop.reason, stop.findings, event_id, paths)
    except Exception as exc:  # AC11: no exception escapes
        return _result('refused', step, left_out + ['%s: a step raised %s' % (step, type(exc).__name__)], event_id,
                       paths)

    try:
        w = append(root, EVENT_TYPE, record, event_id, now, recorder, task_id=task_id)
        outcome = getattr(w, 'result', None)
        if type(outcome) is not str:
            raise TypeError('the result is not a string')
    except Exception as exc:  # AC8, AC11
        return _result('refused', 'store', left_out + ['store: the append raised or gave no result (%s); whether the '
                                                       'decision was appended is not known' % type(exc).__name__],
                       event_id, paths, decision, nxt)
    if outcome == 'appended':
        return _result('evaluated', None, left_out, event_id, paths, decision, nxt)
    if outcome == 'duplicate':
        return _result('duplicate', None, left_out, event_id, paths, decision, nxt)
    try:
        extra = [f for f in (getattr(w, 'findings', ()) or ()) if type(f) is str]
    except Exception:  # AC11
        extra = []
    return _result('refused', 'store', left_out + ['store: the writer gave %r' % outcome] + extra, event_id, paths,
                   decision, nxt)

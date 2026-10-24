"""The execution path of gov-AIEOS (task TASK-032; specification 3 revision 4, sections 1, 9 and 10; specification 1
revision 2, sections 5.1 and 5.2; concept lines 489, 506, 541 and 876; DEF-0030): the core's caller of the Resume
Check (resume_check.check, TASK-008), as evaluation is the governor's.

``execute(root, task_id, inputs, code_sha256, grant_request, recorder, now)`` decides whether one task may go on. It is
the function for the two parts of DEF-0030 left open at M3's exit (decision D-415 C3): the execution decision's state
effect, appended through the writer, and the lease granted on CONTINUE; no module calls it yet (its caller is the
session start of specification 3 section 1, in a later milestone). In order:

1. Arguments (AC1): every argument is checked before anything is read; a wrong one gives a refusal result.
2. The log and the task's state (AC2): the log is read once through writer.read_log and checked by records.check_log.
   From the task's last task.approved its state is READY, and each later event of the task sets it in log order:
   task.drafted DRAFT, task.blocked BLOCKED, task.unblocked READY, task.submitted VERIFYING, decision.acceptance its
   next_task_state, task.stale STALE, task.done DONE, task.replanned DRAFT; another task.* type is refused (decision
   D-687 M1). The store's held lease, read once through writer.held_lease, makes a READY or REWORK task IN_PROGRESS
   when it has not expired (specification 1 section 5.1); an expired held lease, or one held on a task in another
   state, is refused. Only READY, REWORK and IN_PROGRESS go on.
3. The inputs agree with the log (AC3): the inputs' task_state, log_seq and approved_contract_hash must equal the
   projected state, the seq of the log's last line and the contract_hash of the task's last task.approved, so that no
   decision on a stale view of the log is recorded.
4. The check (AC4): resume_check.check(inputs, code_sha256) once; its record's form is checked before anything is
   released or appended, the record by records.check_decision and each event of its state effect by
   records.check_payload, as the writer will check them, with no id repeated. A record with decision null and an
   error is the record of a failed check.
5. The release first (AC5; reading R1, accepted by decision D-687): for a task IN_PROGRESS on any outcome other than
   CONTINUE or CONTINUE_WITH (an error record included), the held lease is released by its own fencing token through
   writer.release_lease_token before anything is appended, as specification 1 section 5.1 releases it first for
   task.blocked and with task.stale; a lease never outlives the event that ends it.
6. The state effect (AC6; specification 3 sections 9 and 10): the record is appended as decision.execution under its
   record_id, then each event of its state_effect in its order under its stored event_id, through
   writer.append_event, with task_id the task and no fencing token. A second append of the same record or event gives
   "duplicate" (the writer's behaviour); a rerun of execute after any append that added a line is refused by step 3,
   since the log's last seq has moved, and appends nothing (decision D-687 M2).
7. The lease (AC7; specification 3 sections 1 and 10): on CONTINUE or CONTINUE_WITH for a task in READY or REWORK,
   writer.grant_lease once, after every append, with the holder, session and expiry of grant_request; for a task
   IN_PROGRESS the held lease is kept. No other outcome grants a lease.

The result (AC9) is a mapping with exactly the keys of RESULT_KEYS. An exception raised by a called function is
caught and becomes a result with the step's reason; none escapes.

``read_log``, ``append``, ``grant``, ``release``, ``held`` and ``check`` default, at call time, to writer.read_log,
writer.append_event, writer.grant_lease, writer.release_lease_token, writer.held_lease and resume_check.check; tests
pass stand-ins.

``list_tasks(root, now, read_log=None, held_leases=None)`` (task TASK-084; specification 6 section 1, specification 7
section 3, specification 1 section 5) gives the tasks that may be taken, as a core function, not an MCP tool: every
task the log has a task.approved of whose state, by the same projection as execute's, is READY or REWORK and that
holds no unexpired lease in the store, as (a list, None) of {task, state, contract_hash, lease} sorted by task number,
lease "none" or "expired" (a row whose expires_at is at or before now, which the launcher's expiry has not yet
removed), or (None, findings) with no partial list. It reads only: the log once through read_log, then the store once
through held_leases (defaulting, at call time, to writer.read_log and writer.held_leases); it grants, releases,
expires and appends nothing, and it never raises. A held lease out of eventlog.LEASE_KEYS' form, or whose task_id is
not in the TASK- form, two leases on one task, or a lease on a task with no task.approved, fail the whole list; an
in-form lease on a task the log has in another state only leaves that task out (a stop between task.submitted and the
lease's release leaves one, submit.py). Its limits: dependencies are not re-checked, since READY already needs them
DONE at task.approved (DEF-0099, for the launcher's grant path); no transition check (DEF-0055 P6); the store is read
at one moment, so a lease may be granted after the list is made; the list grants nothing.

``task_states(log, task_ids)`` and ``rework_count(log, task_id)`` (task TASK-088; specification 1 section 5.1) read
the log for TASK-088's readers (resume_log_inputs): the log is given as bytes and checked by records.check_log,
ignored duplicates left out. task_states gives, for each id, {state, stale_evidence}: the state by the same
projection as execute's, or None when the log holds no task.approved of the task, and stale_evidence true when an
evidence.stale of the task follows its last task.done (one with no task_id is never counted); rework_count gives the
count of the task's decision.acceptance events with next_task_state REWORK after its last task.approved, 0 when there
is none. Both give (a value, None) or (None, findings) and never raise; they append, grant and release nothing, and
execute itself still gathers no Resume Check input.

Readings (the implementer's, not the contract's own words):
- The task's events are those whose task_id is the task, ignored duplicate lines left out; the seq compared with the
  inputs' log_seq is that of the log's last line, duplicate or not.
- A held lease is in form only as eventlog.LEASE_KEYS' mapping whose task_id is the task, whose fencing_token is
  {epoch: a non-empty string, counter: an int, not a bool, at least 0}, the writer's own token form, and whose
  expires_at is a timezone-aware datetime; anything else is refused with reason "lease", before anything is released.
- The result's uncovered keeps the record's uncovered entries that are strings when uncovered is a list, and is empty
  otherwise; the record's form check (AC4) does not look at them.
- A log that gives the task the state IN_PROGRESS (a decision.acceptance with that next_task_state) is refused with
  reason "state" before the held lease is read: IN_PROGRESS is only ever the store's lease (specification 1 section
  5.1), so it is never taken as a held session without one.
- The argument check takes "now" and expires_at with any tzinfo whose offset is zero, as reconcile does.
- The inputs are compared with the log (step 3) before a state other than READY, REWORK or IN_PROGRESS is refused, so
  that a rerun after any append is always refused with reason "inputs" (the log's last seq has moved), whatever
  state the first run's events set (AC6, decision D-687 M2); a held lease that has expired, is malformed or is held
  on a task the log has in another state is refused before that comparison.

The limits of the Resume Check, appended as returned (AC8; scope note points (i) and (ii), decision D-683):
- Point (i): specification 1 revision 2 (line 70) allows READY -> STALE when the Resume Check gives REPLAN on a READY
  task, but resume_check.py's READY branch returns the conflict.detected only, as specification 3 section 10's older
  text says. This module appends what check returns and does not change resume_check.py: such a task stays READY
  with no lease, and, while its inputs are unchanged, the next Resume Check gives REPLAN again (it fails safe). The
  record names no uncovered entry for point (i) itself; the caller sees the decision REPLAN and no lease. The
  alignment is carried (DEF-0030).
- A check-4 REPLAN gives no task.stale, and every conflict.detected has tasks []; the record names both in its
  uncovered entries, which the result passes on.

What it does not do (AC10, AC11): it gathers no Resume Check input (Git, the files at HEAD, the architecture entities,
the runtime's max_risk and telemetry and the observed read-set are the caller's values; only task_state, log_seq and
approved_contract_hash are checked against the log); it issues no Work Order and runs no Context Compiler; it takes
no decision while a session runs (specification 3 section 8) and never sees STOP: violation, which check does not
return; it appends no task.unblocked and no task.replanned; it creates no store, starts or ends no session and
expires no lease (open_store, start_session, end_session and expire_leases stay the caller's, with D-414's
requirement on a recreated store's epoch); it calls no governor and accepts nothing; it reads no network.

Limits (AC10):
- The projection does not check transitions against specification 1's state machine (DEF-0055 P6).
- On CONTINUE or CONTINUE_WITH for a task IN_PROGRESS, the lease kept is the store's held lease; whether
  grant_request's holder and session_id are the ones holding it is not checked, since writer.held_lease gives no
  holder (specification 3 section 1, "a lease it still holds"; carried to the caller, decision D-687 M4).
- One run at a time: the log is read, then appended to, with no check that it is unchanged since; the store's own
  transaction is the only lock, as the writer's limit.
- A crash, or a refused or raising append or grant, between the release, the appends and the grant leaves a released
  lease with no record, a record with no lease, or a record with only part of its state effect (for example
  decision.execution and its conflict.detected without its task.blocked). The next Resume Check decides again under
  a new log_seq and appends a new record and its whole effect under new ids; the earlier partial effect stays in the
  log, which is append-only (review R4).
- It starts no process, opens no file except through read_log, append, grant, release and held, reads no clock and no
  environment, and builds no event-log line itself (INV-001 to INV-004).
"""

import datetime
import re

from aieos_bootstrap import records
from aieos_bootstrap import resume_check
from aieos_bootstrap import writer

RESULT_KEYS = ('result', 'reason', 'findings', 'decision', 'record_id', 'appended', 'duplicate', 'lease', 'released',
               'uncovered')
CONTINUING = ('CONTINUE', 'CONTINUE_WITH')
GRANT_STATES = ('READY', 'REWORK')
CHECK_STATES = ('READY', 'REWORK', 'IN_PROGRESS')
REQUEST_KEYS = frozenset({'holder', 'session_id', 'expires_at'})
EFFECT_KEYS = frozenset({'event_id', 'type', 'payload', 'task_id'})
EVENT_TYPE = 'decision.execution'
# AC2: the state each task.* event sets (task.approved starts the projection at READY).
STATE_OF = {'task.drafted': 'DRAFT', 'task.blocked': 'BLOCKED', 'task.unblocked': 'READY', 'task.submitted': 'VERIFYING',
            'task.stale': 'STALE', 'task.done': 'DONE', 'task.replanned': 'DRAFT'}
_TASK = re.compile(r'TASK-[0-9]+')
_HEX64 = re.compile(r'[0-9a-f]{64}')
_ZERO = datetime.timedelta(0)


class _Stop(Exception):
    """A refusal found inside a step: its reason and findings."""

    def __init__(self, reason, findings):
        Exception.__init__(self, reason)
        self.reason = reason
        self.findings = list(findings)


def _text(value):
    return isinstance(value, str) and value != ''


def _utc_whole(value):
    return (isinstance(value, datetime.datetime) and value.tzinfo is not None and value.utcoffset() == _ZERO
            and value.microsecond == 0)


def _result(result, reason=None, findings=(), decision=None, record_id=None, appended=(), duplicate=(), lease=None,
            released=None, uncovered=()):
    return {'result': result, 'reason': reason, 'findings': list(findings), 'decision': decision,
            'record_id': record_id, 'appended': list(appended), 'duplicate': list(duplicate), 'lease': lease,
            'released': released, 'uncovered': sorted(set(uncovered))}


# ---- AC1 ----

def _argument_findings(root, task_id, inputs, code_sha256, grant_request, recorder, now):
    """AC1: what is wrong with the arguments, as a list of findings (empty when every argument is in form)."""
    found = []
    if not _text(root):
        found.append('argument: root is not a non-empty string')
    task_ok = isinstance(task_id, str) and _TASK.fullmatch(task_id) is not None
    if not task_ok:
        found.append('argument: task_id is not TASK- followed by digits')
    if not isinstance(inputs, dict):
        found.append('argument: inputs is not a mapping')
    elif not (task_ok and inputs.get('task_id') == task_id):
        found.append('argument: the inputs\' task_id is not task_id')
    if not (isinstance(code_sha256, str) and _HEX64.fullmatch(code_sha256)):
        found.append('argument: code_sha256 is not 64 lowercase hex characters')
    if not (isinstance(grant_request, dict) and set(grant_request) == REQUEST_KEYS):
        found.append('argument: grant_request is not a mapping with exactly holder, session_id and expires_at')
    else:
        for key in ('holder', 'session_id'):
            if not _text(grant_request[key]):
                found.append('argument: grant_request %s is not a non-empty string' % key)
        if not _utc_whole(grant_request['expires_at']):
            found.append('argument: grant_request expires_at is not a timezone-aware datetime in UTC with whole '
                         'seconds')
    if not _text(recorder):
        found.append('argument: recorder is not a non-empty string')
    if not _utc_whole(now):
        found.append('argument: now is not a timezone-aware datetime in UTC with whole seconds')
    return found


# ---- AC2, AC3 ----

def _log(read_log, root):
    """AC2: the log's lines after records.check_log finds nothing."""
    data = read_log(root)
    if not isinstance(data, bytes):
        raise _Stop('log', ['log: read_log gave %s, not bytes' % type(data).__name__])
    report = records.check_log(data)
    found = ['log: line %d: %s' % (n, f) for n, f in report.findings()]
    if found:
        raise _Stop('log', found)
    return report.lines


def _project(lines, task_id):
    """AC2: (the state the task's own events give, the contract_hash of its last task.approved)."""
    mine = [line.event for line in lines if line.duplicate_of is None and line.event.get('task_id') == task_id]
    approved = [i for i, e in enumerate(mine) if e['type'] == 'task.approved']
    if not approved:
        raise _Stop('state', ['state: the log holds no task.approved of %s' % task_id])
    state = 'READY'
    for e in mine[approved[-1] + 1:]:
        kind = e['type']
        if kind in STATE_OF:
            state = STATE_OF[kind]
        elif kind == 'decision.acceptance':
            nxt = e['payload'].get('next_task_state')
            if isinstance(nxt, str):
                state = nxt
        elif kind.startswith('task.'):
            raise _Stop('state', ['state: %s is a task event the projection does not name (decision D-687 M1)'
                                  % kind])
    return state, mine[approved[-1]]['payload'].get('contract_hash')


def _lease_form(lease, task_id):
    token = lease.get('fencing_token') if isinstance(lease, dict) else None
    expires = lease.get('expires_at') if isinstance(lease, dict) else None
    return (isinstance(lease, dict) and set(lease) == {'task_id', 'fencing_token', 'expires_at'}
            and lease['task_id'] == task_id and isinstance(token, dict) and set(token) == {'epoch', 'counter'}
            and _text(token['epoch']) and type(token['counter']) is int and token['counter'] >= 0
            and isinstance(expires, datetime.datetime) and expires.tzinfo is not None)


def _state(held, root, task_id, log_state, now):
    """AC2: (the state, the held lease or None) with the store's held lease."""
    if log_state == 'IN_PROGRESS':
        # IN_PROGRESS is the store's lease, never a state the log gives (specification 1 section 5.1): a log that
        # gives it (a decision.acceptance with that next_task_state) is refused, never taken as a held session.
        raise _Stop('state', ['state: the log gives %s the state IN_PROGRESS, which only a held lease gives' % task_id])
    lease = held(root, task_id)
    if lease is None:
        state = log_state
    elif not _lease_form(lease, task_id):
        raise _Stop('lease', ['lease: the held lease of %s is not in eventlog.LEASE_KEYS\' form' % task_id])
    elif not lease['expires_at'] > now:
        raise _Stop('lease', ['lease: the lease held on %s expired at %s; its expiry is the caller\'s '
                              '(writer.expire_leases)' % (task_id, lease['expires_at'].isoformat())])
    elif log_state in GRANT_STATES:
        state = 'IN_PROGRESS'
    else:
        raise _Stop('state', ['state: a lease is held on %s, which the log has in %s' % (task_id, log_state)])
    return state, lease


def _agree(inputs, state, last_seq, contract_hash):
    """AC3: each difference between the inputs and the log, as a finding."""
    found = []
    for key, want in (('task_state', state), ('log_seq', last_seq), ('approved_contract_hash', contract_hash)):
        given = inputs.get(key)
        if type(given) is not type(want) or given != want:
            found.append('inputs: %s is %r, but the log gives %r' % (key, given, want))
    return found


# ---- AC4 ----

def _record_findings(record, task_id):
    """AC4: what is wrong with the check's result, as a list of findings."""
    if not isinstance(record, dict):
        return ['check: the result is %s, not a mapping' % type(record).__name__]
    found = []
    if not _text(record.get('record_id')):
        found.append('check: record_id is not a non-empty string')
    if record.get('subject') != task_id:
        found.append('check: subject is %r, not %s' % (record.get('subject'), task_id))
    if 'decision' not in record:
        found.append('check: the record has no decision key')
    effect = record.get('state_effect')
    if not isinstance(effect, list):
        found.append('check: state_effect is not a list')
        return found
    ids = [record.get('record_id')]
    for i, e in enumerate(effect):
        if not (isinstance(e, dict) and set(e) == EFFECT_KEYS and _text(e['event_id']) and e['task_id'] == task_id
                and _text(e['type']) and isinstance(e['payload'], dict)):
            found.append('check: state_effect[%d] is not {event_id, type, payload, task_id} for %s' % (i, task_id))
            continue
        if e['event_id'] in ids:
            found.append('check: state_effect[%d] repeats the id %s' % (i, e['event_id']))
        ids.append(e['event_id'])
        # review R5: every event is checked as the writer will check it, before anything is released or appended
        found.extend('check: state_effect[%d]: %s' % (i, f) for f in records.check_payload(e['type'], e['payload']))
    if 'decision' in record and record['decision'] is None and effect:
        found.append('check: a record with decision null has a state effect')
    found.extend('check: the record: %s' % f for f in records.check_decision(EVENT_TYPE, record))
    return found


def _store_failure(name, r):
    """AC5, AC7: why a store result does not count, or None when it is a StoreResult with result "done"."""
    if not isinstance(r, writer.StoreResult):
        return ['lease: %s gave %s, not a StoreResult' % (name, type(r).__name__)]
    if r.result == 'done':
        return None
    return ['lease: %s refused it (%s)' % (name, r.reason)] + [f for f in r.findings if isinstance(f, str)]


def execute(root, task_id, inputs, code_sha256, grant_request, recorder, now, read_log=None, append=None, grant=None,
            release=None, held=None, check=None):
    """Run the Resume Check for one task and apply its decision (TASK-032 AC1 to AC9); returns a mapping with
    RESULT_KEYS."""
    read_log = writer.read_log if read_log is None else read_log
    append = writer.append_event if append is None else append
    grant = writer.grant_lease if grant is None else grant
    release = writer.release_lease_token if release is None else release
    held = writer.held_lease if held is None else held
    check = resume_check.check if check is None else check

    try:
        found = _argument_findings(root, task_id, inputs, code_sha256, grant_request, recorder, now)
    except Exception as exc:  # AC9: an argument whose own methods raise
        found = ['argument: checking the arguments raised %s' % type(exc).__name__]
    if found:
        return _result('refused', 'argument', found)

    step = 'log'
    try:
        lines = _log(read_log, root)
        step = 'state'
        log_state, contract_hash = _project(lines, task_id)
        step = 'lease'
        state, lease = _state(held, root, task_id, log_state, now)
        step = 'inputs'
        found = _agree(inputs, state, lines[-1].event['seq'], contract_hash)
        if found:
            raise _Stop('inputs', found)
        if state not in CHECK_STATES:
            raise _Stop('state', ['state: %s is in %s; the Resume Check runs on READY, REWORK or IN_PROGRESS'
                                  % (task_id, state)])
        step = 'check'
        try:
            record = check(inputs, code_sha256)
        except Exception as exc:  # AC4
            raise _Stop('check', ['check: the Resume Check raised %s' % type(exc).__name__])
        found = _record_findings(record, task_id)
        if found:
            raise _Stop('check', found)
        decision = record['decision']
        record_id = record['record_id']
        listed = record.get('uncovered')
        uncovered = [u for u in listed if isinstance(u, str)] if isinstance(listed, list) else []
        effect = record['state_effect'] if decision is not None else []
        plan = [(EVENT_TYPE, record, record_id)] + [(e['type'], e['payload'], e['event_id']) for e in effect]
    except _Stop as stop:
        return _result('refused', stop.reason, stop.findings)
    except Exception as exc:  # AC9: no exception escapes
        return _result('refused', step, ['%s: a step raised %s' % (step, type(exc).__name__)])

    released = None
    if state == 'IN_PROGRESS' and decision not in CONTINUING:
        # AC5: the release first, by the lease's own token, before anything is appended.
        try:
            r = release(root, task_id, lease['fencing_token'])
            failure = _store_failure('release_lease_token', r)
        except Exception as exc:  # AC5, AC9
            failure = ['lease: release_lease_token raised %s; whether the lease was released is not known'
                       % type(exc).__name__]
        if failure:
            return _result('refused', 'lease', failure, decision, record_id, uncovered=uncovered)
        released = r.value

    appended, duplicate = [], []
    for event_type, payload, eid in plan:
        try:
            w = append(root, event_type, payload, eid, now, recorder, task_id=task_id)
            if not isinstance(w, writer.WriteResult):
                raise TypeError('the result is not a WriteResult')
            outcome = w.result
        except Exception as exc:  # AC6, AC9
            return _result('refused', 'append', ['append: the append of %s raised or gave no WriteResult (%s); '
                                                 'whether it was appended is not known' % (eid, type(exc).__name__)],
                           decision, record_id, appended, duplicate, released=released, uncovered=uncovered)
        if outcome == 'appended':
            appended.append(eid)
        elif outcome == 'duplicate':
            duplicate.append(eid)
        else:
            extra = [f for f in (w.findings or ()) if isinstance(f, str)]
            return _result('refused', 'append', ['append: the writer gave %r for %s' % (outcome, eid)] + extra,
                           decision, record_id, appended, duplicate, released=released, uncovered=uncovered)

    kept = None
    if decision in CONTINUING:
        if state in GRANT_STATES:
            # AC7: the grant, only after the record and its state effect are in the log.
            try:
                g = grant(root, task_id, state, grant_request['holder'], grant_request['session_id'], now,
                          grant_request['expires_at'])
                failure = _store_failure('grant_lease', g)
            except Exception as exc:  # AC7, AC9
                failure = ['lease: grant_lease raised %s; whether a lease was granted is not known'
                           % type(exc).__name__]
            if failure:
                return _result('refused', 'lease', failure, decision, record_id, appended, duplicate,
                               uncovered=uncovered)
            kept = g.value
        else:
            kept = lease
    return _result('decided', None, [], decision, record_id, appended, duplicate, kept, released, uncovered)


# ---- list_tasks (task TASK-084) ----

def _task_key(task_id):
    """TASK-084 AC2: the sort key by task number, with no int(): the digits' length with leading zeros stripped, those
    digits, then the whole id (so TASK-9 comes before TASK-10, and TASK-07 and TASK-7 keep one order)."""
    digits = task_id[len('TASK-'):].lstrip('0')
    return (len(digits), digits, task_id)


def _lease_task(lease):
    """TASK-084 AC3: the task_id of one held lease in eventlog.LEASE_KEYS' form, else a refusal."""
    task_id = lease.get('task_id') if isinstance(lease, dict) else None
    if not (isinstance(task_id, str) and _TASK.fullmatch(task_id) is not None):
        raise _Stop('lease', ['lease: a held lease has no task_id of TASK- followed by digits'])
    if not _lease_form(lease, task_id):
        raise _Stop('lease', ['lease: the held lease of %s is not in eventlog.LEASE_KEYS\' form' % task_id])
    return task_id


def list_tasks(root, now, read_log=None, held_leases=None):
    """The tasks that may be taken (TASK-084 AC1 to AC6): (a list of {task, state, contract_hash, lease}, None), or
    (None, findings)."""
    read_log = writer.read_log if read_log is None else read_log
    held_leases = writer.held_leases if held_leases is None else held_leases
    try:
        found = []
        if not _text(root):
            found.append('argument: root is not a non-empty string')
        if not _utc_whole(now):
            found.append('argument: now is not a timezone-aware datetime in UTC with whole seconds')
    except Exception as exc:  # AC1: an argument whose own methods raise
        found = ['argument: checking the arguments raised %s' % type(exc).__name__]
    if found:
        return None, found

    try:
        lines = _log(read_log, root)
        ids = {line.event.get('task_id') for line in lines
               if line.duplicate_of is None and line.event.get('type') == 'task.approved'}
        approved = sorted((t for t in ids if isinstance(t, str) and _TASK.fullmatch(t) is not None), key=_task_key)
        states = {}
        for task_id in approved:
            state, contract_hash = _project(lines, task_id)
            if state == 'IN_PROGRESS':
                raise _Stop('state', ['state: the log gives %s the state IN_PROGRESS, which only a held lease gives'
                                      % task_id])
            states[task_id] = (state, contract_hash)
        leases = held_leases(root)
        if not isinstance(leases, list):
            raise _Stop('lease', ['lease: held_leases gave %s, not a list' % type(leases).__name__])
        held = {}
        for lease in leases:
            task_id = _lease_task(lease)
            if task_id in held:
                raise _Stop('lease', ['lease: two held leases on %s' % task_id])
            if task_id not in states:
                raise _Stop('lease', ['lease: a lease is held on %s, of which the log has no task.approved' % task_id])
            held[task_id] = lease
        listed = []
        for task_id in approved:
            state, contract_hash = states[task_id]
            if state not in GRANT_STATES:
                continue  # AC3: an in-form lease on such a task only leaves it out
            lease = held.get(task_id)
            if lease is None:
                mark = 'none'
            elif lease['expires_at'] > now:
                continue
            else:
                mark = 'expired'
            listed.append({'task': task_id, 'state': state, 'contract_hash': contract_hash, 'lease': mark})
        return listed, None
    except _Stop as stop:
        return None, list(stop.findings)
    except Exception as exc:  # AC4: no exception escapes
        return None, ['list_tasks: a step raised %s' % type(exc).__name__]


# ---- task_states and rework_count (task TASK-088) ----

def _given_log(log):
    """TASK-088 AC2, AC3: the lines of the log given as bytes, after records.check_log finds nothing (execute's _log
    over a reader that gives those bytes)."""
    return _log(lambda root: log, None)


def _own_events(lines, task_id):
    """TASK-088 AC2, AC3: the task's events in log order, ignored duplicate lines left out (as _project takes them)."""
    return [line.event for line in lines if line.duplicate_of is None and line.event.get('task_id') == task_id]


def task_states(log, task_ids):
    """For each id of task_ids, {state, stale_evidence} (TASK-088 AC2): (a dict keyed by task id, None), or (None,
    findings). state is the one _project gives, or None when the log holds no task.approved of the task (tested
    before _project is called, whose two refusals share one reason); stale_evidence is true when an evidence.stale of
    the task follows its last task.done, else false (an evidence.stale with no task_id is never counted)."""
    try:
        if not (isinstance(task_ids, list)
                and all(isinstance(t, str) and _TASK.fullmatch(t) is not None for t in task_ids)):
            return None, ['argument: task_ids is not a list of TASK- followed by digits']
        lines = _given_log(log)
        states = {}
        for task_id in task_ids:
            mine = _own_events(lines, task_id)
            if any(e['type'] == 'task.approved' for e in mine):
                state = _project(lines, task_id)[0]
            else:
                state = None
            done = [i for i, e in enumerate(mine) if e['type'] == 'task.done']
            stale = bool(done) and any(e['type'] == 'evidence.stale' for e in mine[done[-1] + 1:])
            states[task_id] = {'state': state, 'stale_evidence': stale}
        return states, None
    except _Stop as stop:
        return None, list(stop.findings)
    except Exception as exc:  # TASK-088 AC2: no exception escapes
        return None, ['task_states: a step raised %s' % type(exc).__name__]


def rework_count(log, task_id):
    """The count of the task's decision.acceptance events with next_task_state REWORK after its last task.approved
    (specification 1 section 5.1's retries; TASK-088 AC3): (an int, None), 0 when the log holds no task.approved of
    the task, or (None, findings)."""
    try:
        if not (isinstance(task_id, str) and _TASK.fullmatch(task_id) is not None):
            return None, ['argument: task_id is not TASK- followed by digits']
        mine = _own_events(_given_log(log), task_id)
        approved = [i for i, e in enumerate(mine) if e['type'] == 'task.approved']
        if not approved:
            return 0, None
        return sum(1 for e in mine[approved[-1] + 1:] if e['type'] == 'decision.acceptance'
                   and isinstance(e['payload'], dict) and e['payload'].get('next_task_state') == 'REWORK'), None
    except _Stop as stop:
        return None, list(stop.findings)
    except Exception as exc:  # TASK-088 AC3: no exception escapes
        return None, ['rework_count: a step raised %s' % type(exc).__name__]

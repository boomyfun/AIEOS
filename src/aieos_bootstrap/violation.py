"""The violation path of gov-AIEOS (task TASK-052; specification 5 revision 3, section 2 item 3 and section 8;
specification 3 revision 4, section 8 and section 10; specification 1 revision 2, section 5.3; specification 2
revision 4, section 6.3): the core's record of a violation seen while a session runs.

``record(root, task_id, fencing_token, observation, event_id, recorder, now)`` does, in order (specification 3
section 8: "The core appends violation.detected (spec 1 section 5.3) and a decision.execution with this value; the session
stops and the lease is released" (abridged, not verbatim)):

1. Arguments (AC1): every argument is checked, and the execution decision is built and checked by
   records.check_decision (AC2), before anything is called; a wrong one gives a refusal result.
2. violation.detected (AC3): the observation is appended through writer.append_event with task_id the task and the
   given fencing token. There is no separate check of the held lease: the writer's fence is the one check (decision
   D-999 M2), so a token that is not the held lease's, a lease on another task, an expired lease or no lease gives
   reason "fence", the writer's own refusal record stays in the log, and nothing further runs (AC4).
3. The decision (AC2, AC3): a decision.execution STOP: violation, built here under RECORDER, whose refers_to is the
   violation.detected event's event_id, appended with the same task and token under event_id + "/decision".
4. The release (AC3): the lease is released by its token through writer.release_lease_token; a refusal with reason
   "none" or "token" is no error and releases nothing.

"duplicate" for an append (the same event_id given again) is no error, so a repeat of a completed call appends
nothing, gives "done" and releases nothing (decision D-1000 E1). The result (AC5) is a mapping with exactly
RESULT_KEYS; an exception raised by a called function is caught and becomes a result with the step's reason; none
escapes.

``append`` and ``release`` default, at call time, to writer.append_event and writer.release_lease_token; tests pass
stand-ins.

Purity (AC9): this module starts no process, opens no file, reads no clock and no environment, builds no event-log
line itself and makes no network or model call.

Limits (AC8), stated:
- A STOP: violation makes acceptance reject (task TASK-053): evaluation.py passes the governor the task's
  violation.detected payloads beside its record.added payloads, over the whole log, and the governor's row 1 gives
  REJECT; so a violation of the task makes every later evaluation of it reject where the task is evaluable
  (VERIFYING or IN_REVIEW), also after a new task.approved. A blocking record that evaluation.py's _kept leaves out,
  out of form or for a record_id already kept (records.py does not check record_id uniqueness across a log), refuses
  the evaluation with reason "records" instead (task TASK-054), unless it repeats the record_id of a kept blocking
  record with the same blocking_kind and subject; such a task is refused at every evaluation and stays in its state until it is
  superseded by a new task.
- No task.* event follows STOP: violation (specification 3 section 10), so the task stays READY (or REWORK) with no
  lease, and the next Resume Check may CONTINUE again; no bound on repeated STOP: violation (specification 5 section
  11 point 12).
- A fence refusal's record is built by the event log with evidence_type refused_submission, for a refused
  violation.detected as for any refused event (eventlog.refusal_record, unchanged here).
- A crash or a refusal between the two appends and the release leaves what was appended (the log is append-only); the
  lease's expiry is the fallback for a release not made.
- The decision record is not a Resume Check record: it has no contract hash, head commit, log seq or checks, and says
  so in its uncovered entries.
- A run against the real writer's files is not tested in task TASK-052 (its tests write no file). __init__.py is not
  changed, so __all__ does not name this module.
- Also of task TASK-053 (its AC7): F-a is kept (replay needs a fresh root from its caller); a passing replay with a
  violation shows the core's handling of a recorded violation, never that any hook observes anything (C6
  unmeasured); no conformance set or fixture is changed (ADV-02's fixture is a later task); no observed read-set call
  is made.
"""

import datetime
import re

from aieos_bootstrap import records
from aieos_bootstrap import writer

RECORDER = 'the violation path (aieos_bootstrap.violation)'
SOURCE_CLASS = 'deterministic_tool_local'
DECISION = 'STOP: violation'
OBSERVATION_CLASSES = ('deterministic_tool_local', 'agent_declared')
RESULT_KEYS = ('result', 'reason', 'findings', 'appended', 'duplicate', 'released')
NO_ERROR_RELEASE = ('none', 'token')
APPENDED = ('appended', 'duplicate')
UNCOVERED = ('contract_hash, contract_version, base_commit, head_commit and log_seq: not inputs of the violation path',
             'checks: no Resume Check ran; the decision rests on the violation.detected event it refers to')
DECLARED = 'the stop rests on a declared claim: the observation\'s source_class is agent_declared'
_TASK = re.compile(r'TASK-[0-9]+')
_ZERO = datetime.timedelta(0)


def _result(result, reason=None, findings=(), appended=(), duplicate=(), released=None):
    return {'result': result, 'reason': reason, 'findings': list(findings), 'appended': list(appended),
            'duplicate': list(duplicate), 'released': released}


def _text(value):
    return isinstance(value, str) and value != ''


def _token_form(token):
    return (isinstance(token, dict) and set(token) == {'epoch', 'counter'} and _text(token['epoch'])
            and type(token['counter']) is int and token['counter'] >= 0)


def decision_ids(event_id):
    """The decision's event_id and record_id, derived from the violation's event_id (AC2, AC3)."""
    return event_id + '/decision', event_id + '/decision-record'


def decision_record(task_id, event_id, observation):
    """The decision.execution payload STOP: violation for the violation.detected event ``event_id`` (AC2)."""
    uncovered = list(UNCOVERED)
    if isinstance(observation, dict) and observation.get('source_class') == 'agent_declared':
        uncovered.append(DECLARED)
    return {'record_id': decision_ids(event_id)[1], 'fact_kind': 'interpretation', 'source_class': SOURCE_CLASS,
            'recorder': RECORDER, 'subject': task_id, 'decision': DECISION, 'outcomes_fired': [DECISION],
            'refers_to': event_id, 'state_effect': [], 'uncovered': uncovered}


def argument_findings(root, task_id, fencing_token, observation, event_id, recorder, now):
    """The findings of AC1 for the arguments of record (and of adapter.violation); an empty list when all hold."""
    found = []
    if not _text(root):
        found.append('argument: root is not a non-empty string')
    task_ok = isinstance(task_id, str) and _TASK.fullmatch(task_id) is not None
    if not task_ok:
        found.append('argument: task_id is not "TASK-" followed by digits')
    if not _token_form(fencing_token):
        found.append('argument: fencing_token is not {epoch: a non-empty string, counter: an int at least 0}')
    if not _text(event_id):
        found.append('argument: event_id is not a non-empty string')
    if not _text(recorder):
        found.append('argument: recorder is not a non-empty string')
    if not (isinstance(now, datetime.datetime) and now.tzinfo is not None and now.utcoffset() == _ZERO
            and now.microsecond == 0):
        found.append('argument: now is not a timezone-aware datetime in UTC with whole seconds')
    if not isinstance(observation, dict):
        found.append('argument: observation is not a mapping')
        return found
    found.extend('argument: observation: %s' % f for f in records.check_payload('violation.detected', observation))
    if task_ok and observation.get('subject') != task_id:
        found.append('argument: observation subject is not the task id')
    if observation.get('source_class') not in OBSERVATION_CLASSES:
        found.append('argument: observation source_class is not deterministic_tool_local or agent_declared')
    if not _text(observation.get('record_id')):
        found.append('argument: observation record_id is not a non-empty string')
    return found


def _append_step(name, append, root, event_type, payload, event_id, now, recorder, task_id, fencing_token, done):
    """One append; None when appended or duplicate (recorded in done), else the refusal result."""
    appended, duplicate = done
    try:
        w = append(root, event_type, payload, event_id, now, recorder, task_id=task_id, fencing_token=fencing_token)
    except Exception as exc:  # AC3, AC5
        return _result('refused', name, ['%s: append_event raised %s' % (name, type(exc).__name__)], appended,
                       duplicate)
    state, reason = getattr(w, 'result', None), getattr(w, 'reason', None)
    found = [str(f) for f in (getattr(w, 'findings', ()) or ())]
    if state == 'appended':
        appended.append(event_id)
        return None
    if state == 'duplicate':
        duplicate.append(event_id)
        return None
    if state == 'refused' and reason == 'fence':
        refusal = getattr(w, 'refusal', None)
        note = 'fence: the writer recorded the refusal (%s)' % getattr(refusal, 'result', None)
        return _result('refused', 'fence', ['fence: %s was refused by the writer\'s fence' % event_type, note] + found,
                       appended, duplicate)
    return _result('refused', name, ['%s: append_event gave %r (%r)' % (name, state, reason)] + found, appended,
                   duplicate)


def record(root, task_id, fencing_token, observation, event_id, recorder, now, append=None, release=None):
    """Record one violation for the session that holds the task's lease, stop it and release the lease (TASK-052 AC1
    to AC5); returns a mapping with RESULT_KEYS."""
    append = writer.append_event if append is None else append
    release = writer.release_lease_token if release is None else release
    try:
        found = argument_findings(root, task_id, fencing_token, observation, event_id, recorder, now)
    except Exception as exc:  # AC5: an argument whose own methods raise
        found = ['argument: checking the arguments raised %s' % type(exc).__name__]
    if found:
        return _result('refused', 'argument', found)
    try:
        decision = decision_record(task_id, event_id, observation)
        found = [str(f) for f in records.check_decision('decision.execution', decision)]
    except Exception as exc:  # AC5
        found = ['decision: building the decision raised %s' % type(exc).__name__]
    if found:
        return _result('refused', 'decision', found)
    done = ([], [])
    stop = _append_step('violation', append, root, 'violation.detected', observation, event_id, now, recorder,
                        task_id, fencing_token, done)
    if stop is not None:
        return stop
    stop = _append_step('decision', append, root, 'decision.execution', decision, decision_ids(event_id)[0], now,
                        recorder, task_id, fencing_token, done)
    if stop is not None:
        return stop
    appended, duplicate = done
    try:
        r = release(root, task_id, fencing_token)
    except Exception as exc:  # AC3, AC5
        return _result('refused', 'release', ['release: release_lease_token raised %s; whether the lease was released '
                                              'is not known' % type(exc).__name__], appended, duplicate)
    state, reason = getattr(r, 'result', None), getattr(r, 'reason', None)
    found = [f for f in (getattr(r, 'findings', ()) or ()) if isinstance(f, str)]
    if state == 'done':
        return _result('done', None, [], appended, duplicate, getattr(r, 'value', None))
    if state == 'refused' and reason in NO_ERROR_RELEASE:
        return _result('done', None, ['release: nothing released (%s)' % reason] + found, appended, duplicate)
    return _result('refused', 'release', ['release: release_lease_token gave %r (%r)' % (state, reason)] + found,
                   appended, duplicate)

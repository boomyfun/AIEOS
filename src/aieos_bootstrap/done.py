"""The task.done writer of gov-AIEOS (task TASK-131; specification 1 section 5.1, `task.done`: ACCEPTED -> DONE;
DEF-0119 option C; DEF-0099): the one function that appends the event which makes an accepted task DONE.

``done(root, task_id, event_id, recorder, now)`` takes one task whose state in the log is ACCEPTED:

1. Arguments (AC2): every argument is checked before anything is read; a wrong one gives a refusal result.
2. The log (AC2): read once through read_log (default writer.read_log, bound at call time) and checked by
   records.check_log; a finding gives a refusal result and nothing is appended.
3. The state (AC2): execution.task_states gives the task's state from the same log bytes. A state other than ACCEPTED
   (or none, when the log holds no task.approved of the task) is refused, except DONE: a DONE task whose last task.done
   after its last task.approved names the record that this function would name gives the result duplicate and appends
   nothing; a DONE task with another record is refused.
4. The record (AC2): the task's last decision.acceptance after its last task.approved must satisfy
   reconcile.accepts, have a non-empty record_id and an evaluated_commit in commit form; otherwise it is refused.
5. The append (AC2): one task.done event, payload {decision_record: that record_id}, through append (default
   writer.append_event) with the task id and no fencing token, as decision.acceptance is appended by evaluation.

The result is a mapping with exactly the keys result ("done", "duplicate" or "refused"), reason, findings and
appended. An exception raised by read_log or append is caught and becomes a refusal result; none escapes.

Purity (AC5): this module starts no process, opens no file itself, reads no clock and no environment variable, grants
no lease, creates no store and builds no event-log line itself (the single writer does, INV-004).

Limits (AC7):
- It is not wired into the CLI or the launcher: the first real run calls it as a scripted function of the existing
  code (DEF-0119, option O2).
- It does not check that the accepted commit is on the base branch; reconcile's walk leaves a task whose accepted
  commit is not reached uncovered, and never fresh.
- reconcile.accepts trusts the approval_record field as the governor wrote it; neither this module nor reconcile
  re-runs the governor's approval rule (governor.py _approval).
- A task whose last decision.acceptance is not an accepting record, or whose state is not ACCEPTED, cannot get a
  task.done from here, whatever its earlier records say.
- One run at a time: the writer reads the log and appends with no check that it is unchanged since this module's read.
"""

import datetime
import re

from aieos_bootstrap import execution
from aieos_bootstrap import reconcile
from aieos_bootstrap import records
from aieos_bootstrap import writer

RESULT_KEYS = frozenset({'result', 'reason', 'findings', 'appended'})
_TASK = re.compile(r'TASK-[0-9]+')
_COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
_ZERO = datetime.timedelta(0)


def _result(result, reason=None, findings=(), appended=None):
    return {'result': result, 'reason': reason, 'findings': list(findings), 'appended': appended}


def _refused(reason, findings, appended=None):
    return _result('refused', reason, findings, appended)


def _is_str(value):
    return isinstance(value, str) and value != ''


def _argument_findings(root, task_id, event_id, recorder, now):
    """AC2: what is wrong with the arguments, as a list of findings (empty when every argument is in form)."""
    found = []
    if not (_is_str(root) and root.strip() != ''):
        found.append('argument: root is not a non-empty string')
    if not (isinstance(task_id, str) and _TASK.fullmatch(task_id)):
        found.append('argument: task_id is not TASK- followed by digits')
    for name, value in (('event_id', event_id), ('recorder', recorder)):
        if not _is_str(value):
            found.append('argument: %s is not a non-empty string' % name)
    if not (isinstance(now, datetime.datetime) and now.tzinfo is not None and now.utcoffset() == _ZERO
            and now.microsecond == 0):
        found.append('argument: now is not a timezone-aware datetime in UTC with whole seconds')
    return found


def _written(w):
    """The writer's result, its reason and its findings as a list of strings; raises when an attribute raises or the
    findings are not strings, and the caller turns that into a result."""
    outcome = getattr(w, 'result', None)
    if type(outcome) is not str:
        raise TypeError('the result is not a string')
    reason = getattr(w, 'reason', None)
    if type(reason) is not str:
        reason = None
    raw = getattr(w, 'findings', ()) or ()
    if isinstance(raw, (str, bytes)):
        raise TypeError('the findings are one string, not a sequence of strings')
    findings = list(raw)
    if not all(type(f) is str for f in findings):
        raise TypeError('the findings are not strings')
    return outcome, reason, findings


def _own_events(events, task_id):
    """The task's events after its last task.approved, in log order (all of them when there is none)."""
    mine = [e for e in events if e.get('task_id') == task_id]
    approved = [i for i, e in enumerate(mine) if e['type'] == 'task.approved']
    return mine[approved[-1] + 1:] if approved else mine


def done(root, task_id, event_id, recorder, now, read_log=None, append=None):
    """Append the task.done event of one ACCEPTED task (TASK-131 AC2); returns a mapping with RESULT_KEYS."""
    read_log = writer.read_log if read_log is None else read_log
    append = writer.append_event if append is None else append

    try:
        found = _argument_findings(root, task_id, event_id, recorder, now)
    except Exception as exc:
        found = ['argument: checking the arguments raised %s' % type(exc).__name__]
    if found:
        return _refused('argument', found)
    try:
        data = read_log(root)
    except Exception as exc:
        return _refused('log', ['log: read_log raised %s' % type(exc).__name__])
    if not isinstance(data, bytes):
        return _refused('log', ['log: read_log gave %s, not bytes' % type(data).__name__])
    try:
        report = records.check_log(data)
        problems = ['log: line %d: %s' % (n, f) for n, f in report.findings()]
        events = [line.event for line in report.lines if line.duplicate_of is None]
    except Exception as exc:
        return _refused('log', ['log: checking the log raised %s' % type(exc).__name__])
    if problems:
        return _refused('log', problems)
    states, found = execution.task_states(data, [task_id])
    if states is None:
        return _refused('state', found)
    state = states[task_id]['state']
    if state not in ('ACCEPTED', 'DONE'):
        return _refused('state', ['state: the task is %s, not ACCEPTED' % state])
    after = _own_events(events, task_id)
    accepted = [e for e in after if e['type'] == 'decision.acceptance']
    if not accepted:
        return _refused('record', ['record: the task has no decision.acceptance after its last task.approved'])
    payload = accepted[-1]['payload']
    record_id = payload.get('record_id')
    if not reconcile.accepts(payload):
        return _refused('record', ['record: the last decision.acceptance %s is not an accepting record' % record_id])
    if not _is_str(record_id):
        return _refused('record', ['record: the last decision.acceptance has no record_id'])
    commit = payload.get('evaluated_commit')
    if not (isinstance(commit, str) and _COMMIT.fullmatch(commit)):
        return _refused('record', ['record: the last decision.acceptance %s has no evaluated_commit in commit form'
                                   % record_id])
    if state == 'DONE':
        named = [e['payload'].get('decision_record') for e in after if e['type'] == 'task.done']
        if named and named[-1] == record_id:
            return _result('duplicate', None, [], None)
        return _refused('state', ['state: the task is DONE with another decision record'])
    try:
        w = append(root, 'task.done', {'decision_record': record_id}, event_id, now, recorder, task_id=task_id)
    except Exception as exc:
        return _refused('store', ['store: the append raised %s' % type(exc).__name__])
    try:
        outcome, reason, findings = _written(w)
    except Exception as exc:
        return _refused('store', ['store: reading the writer\'s result raised %s; whether the event was appended is '
                                  'not known' % type(exc).__name__], w)
    if outcome == 'appended':
        return _result('done', None, findings, w)
    if outcome == 'duplicate':
        return _result('duplicate', None, findings, w)
    return _refused(reason if _is_str(reason) else 'store', findings, w)

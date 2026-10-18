"""The core side of the observed read-set record (task TASK-064; concept line 945, "record the observed read-set";
specification 5 revision 3, sections 7 and 11 points 4 and 7; specification 2 revision 6, section 6.2 and section 10
point 13).

Three functions, called only by their tests:

1. ``record_ids(task_id, session_id)``: the event_id and record_id of the session's record, derived from the task and
   the session (AC3), or None for an id out of form.
2. ``build(task_id, session_id, read_paths, recorder)``: the record, of the form that records.check_read_set checks,
   with repeats removed (AC4), or None for an argument out of form.
3. ``observe(context, read_paths, now, append=None)``: one record.added event that adds the session's record through
   the core's writer (AC5).

The interface (specification 5 section 11 point 7), as task TASK-064 states it (AC6):
- The context is task TASK-063's, checked by claude_code_channel.context_findings unchanged: root, task_id, session_id,
  fencing_token, write_set, allowlist and recorder. This module uses root, task_id, session_id, fencing_token and
  recorder, and the other two only through that check. The session is tied in words, by a recorder that holds
  session_id verbatim, and by the ids below; the lease by fencing_token.
- The event is a lease holder's action (a reading of specification 2 section 6.2, which leaves it to the first M5
  contract that writes an adapter's observations to the core): the record is added by one record.added event with
  task_id the task and the context's fencing_token, so the writer's fence accepts it only from the session that holds
  the task's lease. A token that is not the held lease's gives the writer's fence refusal, which the writer records as
  its own record, and nothing else. So the caller passes the read-set before the lease is released: before
  adapter.end, and before a violation releases it.
- The ids are derived, not given: event_id "observed-read-set/<task_id>/<session_id>", record_id that text followed by
  "/record". A second observe for the same task and session gives eventlog's "duplicate" with the same list (nothing
  appended, no error) and eventlog's refusal "conflict" with another list (eventlog.py:180-184). So the log holds at
  most one such record per task and session_id; two session_ids for one session, or one session_id over two tasks,
  are not found (a limit). A session_id that holds "/" is refused, so the ids can be read back.
- The paths are the caller's list. Repeats are removed by exact string equality, the first occurrence's order kept,
  before writing (specification 2 section 6.2). No path is normalised, resolved, case-folded or checked against the
  root, the write-set or the disk: the form stays open (specification 2 section 10 point 13, for the contract of
  specification 5 section 11 point 8), so each path is the writer's statement, recorded and not checked. The list may
  be empty, which says only that no read was seen.
- The record's recorder is claude_code.RECORDER + claude_code_channel.RECORDER_JOIN + the context's recorder, task
  TASK-063's form.

What a record shows (specification 2 section 6.2, its observed read-set paragraph): a lower bound at best. A read
through a shell command, through a tool no hook covers, before the hook was in place, or outside what the path form
can name is not in the list, and a hook cannot show its own completeness or integrity; a missing record proves
nothing. It is kept and not used: having no outcome and no dimension it meets no evidence entry, blocks nothing, is no
gate result and has nothing to re-verify; specification 3 takes the observed source only from a runtime of tier T3 or
above, and no runtime's tier counts until it is measured (C6, P-LOC, the owner's), so the read-set stays an estimate.

observe (AC5):
- The order: the context, then now, then the ids, then the record; then one call of append.
- The result's findings hold only this module's own fixed words, an exception's type and the append result's findings;
  no path of read_paths is copied into them. The context and read_paths are never changed.
- After an exception, the result's record is the record when append was already called with it, and None otherwise;
  when append itself raised, whether anything was written is then not known.
- The module writes only through writer.append_event, or the append given (INV-004); tests pass a stand-in. It opens
  no file itself, starts no process, reads no clock or environment and makes no network or model call; it is not
  pure, since the writer writes.

What is not covered (AC6):
- How reads are gathered across hook calls (state across hook processes) and how a hook process obtains the context
  and starts: the hook process's task, beside placing the hook (part CC-3, the owner's act, A51 item (4)).
- Which tools a hook covers (specification 5 section 11 point 8), abnormal session ends (point 10: a crash or an
  expired lease may leave no record), and the path form (specification 2 section 10 point 13).
- A record that the hook process never delivers is lost. Every limit of aieos_bootstrap.claude_code,
  aieos_bootstrap.claude_code_hook and aieos_bootstrap.claude_code_channel holds here too. Nothing is installed or
  measured, and no test asserts anything about a running Claude Code.
"""

import datetime
import re

from aieos_bootstrap import claude_code
from aieos_bootstrap import claude_code_channel
from aieos_bootstrap import records
from aieos_bootstrap import writer

RESULT_KEYS = ('result', 'reason', 'findings', 'record', 'core')
REASONS = ('context', 'now', 'session_id', 'read_paths', 'core', 'observe')
EVENT_PREFIX = 'observed-read-set/'
RECORD_SUFFIX = '/record'
EVENT_TYPE = 'record.added'

_TASK = re.compile(r'TASK-[0-9]+')
_SESSION = re.compile(r'[^\s/]+')
_ZERO = datetime.timedelta(0)


def _result(result, reason, findings=(), record=None, core=None):
    return {'result': result, 'reason': reason, 'findings': list(findings), 'record': record, 'core': core}


def _text(value):
    return isinstance(value, str) and value != ''


def _utc_whole(value):
    return (isinstance(value, datetime.datetime) and value.tzinfo is not None and value.utcoffset() == _ZERO
            and value.microsecond == 0)


def record_ids(task_id, session_id):
    """(event_id, record_id) of the session's record (AC3); None for a task_id or session_id out of form. No exception
    escapes."""
    try:
        if not (isinstance(task_id, str) and _TASK.fullmatch(task_id)):
            return None
        if not (isinstance(session_id, str) and _SESSION.fullmatch(session_id)):
            return None
        event_id = EVENT_PREFIX + task_id + '/' + session_id
        return event_id, event_id + RECORD_SUFFIX
    except Exception:  # noqa: BLE001 - any exception means an id out of form
        return None


def _distinct(paths):
    seen = set()
    out = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _build(task_id, session_id, read_paths, recorder):
    ids = record_ids(task_id, session_id)
    if ids is None:
        return None
    if not isinstance(read_paths, list) or not all(_text(p) for p in read_paths):
        return None
    if not _text(recorder) or session_id not in recorder:
        return None
    record = {'record_id': ids[1], 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
              'recorder': claude_code.RECORDER + claude_code_channel.RECORDER_JOIN + recorder, 'subject': task_id,
              'evidence_type': records.READ_SET_TYPE, 'read_paths': _distinct(read_paths)}
    if records.check_record(record):
        return None
    return record


def build(task_id, session_id, read_paths, recorder):
    """The observed read-set record of the session (AC4), or None for an argument out of form. The given list is never
    changed. No exception escapes."""
    try:
        return _build(task_id, session_id, read_paths, recorder)
    except Exception:  # noqa: BLE001 - any exception means an argument out of form
        return None


def _core(w):
    found = getattr(w, 'findings', ()) or ()
    return {'result': getattr(w, 'result', None), 'reason': getattr(w, 'reason', None), 'seq': getattr(w, 'seq', None),
            'findings': [str(x) for x in found]}


def _observe(context, read_paths, now, append, state):
    found = claude_code_channel.context_findings(context)
    if found:
        return _result('refused', 'context', found)
    if not _utc_whole(now):
        return _result('refused', 'now', ['now is not a timezone-aware datetime in UTC with whole seconds'])
    ids = record_ids(context['task_id'], context['session_id'])
    if ids is None:
        return _result('refused', 'session_id', ['session_id holds "/", so the ids cannot be derived'])
    record = build(context['task_id'], context['session_id'], read_paths, context['recorder'])
    if record is None:
        return _result('refused', 'read_paths', ['read_paths is not a list of non-empty strings'])
    append = writer.append_event if append is None else append
    state['passed'] = record
    w = append(context['root'], EVENT_TYPE, record, ids[0], now, context['recorder'], task_id=context['task_id'],
               fencing_token=context['fencing_token'])
    core = _core(w)
    if core['result'] == 'appended':
        return _result('written', None, [], record, core)
    if core['result'] == 'duplicate':
        return _result('duplicate', None, [], record, core)
    return _result('refused', 'core', ['append did not give "appended" or "duplicate"'] + core['findings'], record,
                   core)


def observe(context, read_paths, now, append=None):
    """Add the session's observed read-set record through the core's writer, once (AC5): a mapping with exactly
    RESULT_KEYS. No exception escapes."""
    state = {}
    try:
        return _observe(context, read_paths, now, append, state)
    except Exception as e:  # noqa: BLE001 - any exception becomes a result, its type only
        # AC5: the record passed, when append was already called with it, else None
        return _result('refused', 'observe', ['%s raised inside observe' % type(e).__name__], state.get('passed'))

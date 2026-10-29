"""The T0 manual adapter of gov-AIEOS (task TASK-060; specification 5 revision 3, section 4, tier T0, "Chat", post-hoc
only, and section 11 points 9 to 11; specification 2 revision 5, section 6.2; assurance-model.md section 2): a human or
a chat session does the work, and nothing is observed while it runs. The adapter never writes the project-state
directory itself: every write is the core's, through the writer (INV-004).

The session flow (section 11 point 9), four functions with no state kept between calls:

1. ``start(root, task_id, session_id, holder, inputs, code_sha256, expires_at, recorder, now)``: through
   adapter.start (task TASK-051), which opens the session row, runs the Resume Check and, on CONTINUE or
   CONTINUE_WITH, grants the lease. The decision and the fencing token are copied out of its result.
2. ``claim(root, task_id, session_id, fencing_token, claims, event_id, recorder, now)``: the agent's declared claims,
   what it says it did (kind "did") and the read-set it estimates (kind "read_set"). Each claim becomes one record
   with fact_kind claim and source_class agent_declared, checked by records.check_payload and appended as one
   record.added event through writer.append_event with the session's fencing token. The writer's fence is the one
   check of the lease: this module compares no token of its own.
3. ``submit(root, repo, commit_id, task_id, event_id, recorder, now)``: through adapter.submit (task TASK-025's path).
4. ``end(root, task_id, session_id, fencing_token, now)``: through adapter.end (task TASK-028's release and the
   session's close).

Violations are found afterwards by the gates (specification 3 section 8; specification 4's G0), never while the work
runs.

What a claim proves (assurance-model.md line 22, as specification 5 line 42 cites it): nothing. A claim is an agent's
statement, recorded and not checked. The read-set is an estimate and never the observed source (specification 5
section 7). A claim record carries no outcome, no dimension, no gate, no stands_for, no decision_ref and no models, so
it meets no evidence entry and blocks nothing; the evidence that counts comes only from the gates afterwards.

Each function returns a mapping with exactly RESULT_KEYS. A wrong argument gives reason "argument" before any call; a
record that records.check_payload refuses gives "record" before any append; a fence refusal of the writer gives
"fence"; any other append result, or a raised exception, gives "append"; a refusal of an adapter function gives
"core". An exception raised by a called function is caught and becomes a result; none escapes.

The functions it calls are keyword arguments, each defaulting at call time to the named function: start's start
(adapter.start), submit's submit (adapter.submit), end's end (adapter.end) and claim's append
(writer.append_event). start, submit and end also take ``functions``, a mapping of keyword arguments passed on to the
adapter's function (its own stand-ins), or None.

Purity: this module starts no process except through adapter.submit (gitread.run), opens no file, reads no clock and
no environment, builds no event-log line itself and makes no network or model call.

Limits, stated (AC7):
- An abnormal session end (section 11 point 10) is handled only as section 2 item 5's fallback: if the caller never
  calls end, the lease's expiry releases it. Nothing is added for a crash, an expired lease or a resume after
  compaction.
- No adapter declaration is read or written (specification 5 section 3), so check 7's STOP: runtime insufficient
  applies as the core decides it.
- T0's conformance scenarios (section 11 point 11) are not in this task: a named follow-up fixture task.
- The session is named only in the recorder's words: this module writes no ``session`` key, which records.py accepts
  since TASK-077 (specification 2 section 6.2).
- This module is called only by its tests; __init__.py is not changed, so __all__ does not name it.
"""

import datetime
import re

from aieos_bootstrap import adapter
from aieos_bootstrap import records
from aieos_bootstrap import writer

RECORDER = 'the T0 manual adapter (aieos_bootstrap.t0)'
RESULT_KEYS = ('result', 'reason', 'findings', 'appended', 'duplicate', 'core', 'decision', 'fencing_token',
               'released')
EVIDENCE_TYPES = {'did': 'agent_claim', 'read_set': 'read_set_estimate'}
MAX_CLAIMS = 100
MAX_TEXT = 2000
_TASK = re.compile(r'TASK-[0-9]+')
_ZERO = datetime.timedelta(0)


def _result(result, reason=None, findings=(), appended=(), duplicate=(), core=None):
    copied = core if isinstance(core, dict) else {}
    return {'result': result, 'reason': reason, 'findings': list(findings), 'appended': list(appended),
            'duplicate': list(duplicate), 'core': core, 'decision': copied.get('decision'),
            'fencing_token': copied.get('fencing_token'), 'released': copied.get('released')}


def _text(value):
    return isinstance(value, str) and value != ''


def _utc_whole(value):
    return (isinstance(value, datetime.datetime) and value.tzinfo is not None and value.utcoffset() == _ZERO
            and value.microsecond == 0)


def _token(value):
    return (isinstance(value, dict) and set(value) == {'epoch', 'counter'} and _text(value['epoch'])
            and type(value['counter']) is int and value['counter'] >= 0)


def _one_line(text):
    return len(text.splitlines()) == 1 and text.splitlines()[0] == text


def _claims_findings(claims):
    if not (isinstance(claims, list) and 0 < len(claims) <= MAX_CLAIMS):
        return ['argument: claims is not a non-empty list of at most %d mappings' % MAX_CLAIMS]
    found = []
    for i, c in enumerate(claims, 1):
        if not (isinstance(c, dict) and set(c) == {'kind', 'text'}):
            found.append('argument: claim %d is not a mapping with exactly kind and text' % i)
        elif not (isinstance(c['kind'], str) and c['kind'] in EVIDENCE_TYPES):
            found.append('argument: claim %d has a kind that is not "did" or "read_set"' % i)
        elif not (_text(c['text']) and len(c['text']) <= MAX_TEXT and _one_line(c['text'])):
            found.append('argument: claim %d has a text that is not a non-empty string of at most %d characters '
                         'with no line break' % (i, MAX_TEXT))
    return found


def _claim_findings(root, task_id, session_id, fencing_token, claims, event_id, recorder, now):
    found = []
    if not _text(root):
        found.append('argument: root is not a non-empty string')
    if not (isinstance(task_id, str) and _TASK.fullmatch(task_id)):
        found.append('argument: task_id is not "TASK-" followed by digits')
    if not _text(session_id):
        found.append('argument: session_id is not a non-empty string')
    if not _token(fencing_token):
        found.append('argument: fencing_token is not {epoch: a non-empty string, counter: an int at least 0}')
    found.extend(_claims_findings(claims))
    if not _text(event_id):
        found.append('argument: event_id is not a non-empty string')
    if not _text(recorder):
        found.append('argument: recorder is not a non-empty string')
    if not _utc_whole(now):
        found.append('argument: now is not a timezone-aware datetime in UTC with whole seconds')
    return found


def claim_event_id(event_id, position):
    """The event_id, and the record_id, of the claim at a position counted from 1 (AC2, AC3)."""
    return '%s/claim-%d' % (event_id, position)


def build_record(task_id, session_id, recorder, event_id, position, one):
    """The record of one claim (AC2): exactly record_id, fact_kind, source_class, recorder, subject, evidence_type and
    basis."""
    return {'record_id': claim_event_id(event_id, position), 'fact_kind': 'claim', 'source_class': 'agent_declared',
            'recorder': '%s, session %s, for %s' % (RECORDER, session_id, recorder), 'subject': task_id,
            'evidence_type': EVIDENCE_TYPES[one['kind']], 'basis': one['text']}


# ---- claim (AC1 to AC3, AC5) ----

def claim(root, task_id, session_id, fencing_token, claims, event_id, recorder, now, append=None):
    """Record the agent's declared claims as record.added events with the session's fencing token (TASK-060 AC1 to
    AC3, AC5); returns a mapping with RESULT_KEYS."""
    append = writer.append_event if append is None else append
    try:
        found = _claim_findings(root, task_id, session_id, fencing_token, claims, event_id, recorder, now)
    except Exception as exc:  # AC5: an argument whose own methods raise
        found = ['argument: checking the arguments raised %s' % type(exc).__name__]
    if found:
        return _result('refused', 'argument', found)
    built = []
    for i, one in enumerate(claims, 1):
        rec = build_record(task_id, session_id, recorder, event_id, i, one)
        try:
            bad = records.check_payload('record.added', rec)
        except Exception as exc:  # AC5
            return _result('refused', 'record', ['record: checking the record of claim %d raised %s'
                                                 % (i, type(exc).__name__)])
        if bad:
            return _result('refused', 'record', ['record: claim %d: %s' % (i, '; '.join(
                '%s %s' % (getattr(f, 'rule', f), getattr(f, 'detail', '')) for f in bad))])
        built.append(rec)
    appended, duplicate = [], []
    for i, rec in enumerate(built, 1):
        eid = claim_event_id(event_id, i)
        try:
            r = append(root, 'record.added', rec, eid, now, recorder, task_id=task_id, fencing_token=fencing_token)
            state = getattr(r, 'result', None)
            reason = getattr(r, 'reason', None)
        except Exception as exc:  # AC3, AC5
            return _result('refused', 'append', ['append: claim %d: the append raised %s' % (i, type(exc).__name__)],
                           appended, duplicate)
        if state == 'appended':
            appended.append(eid)
        elif state == 'duplicate':
            duplicate.append(eid)
        elif state == 'refused' and reason == 'fence':
            return _result('refused', 'fence', ['fence: claim %d: the writer refused the fencing token' % i],
                           appended, duplicate)
        else:
            return _result('refused', 'append', ['append: claim %d: the writer gave %r (%r)' % (i, state, reason)],
                           appended, duplicate)
    return _result('done', None, [], appended, duplicate)


# ---- start, submit and end (AC4, AC5) ----

def _functions_findings(functions, allowed):
    if functions is None:
        return []
    if not (isinstance(functions, dict) and all(isinstance(k, str) for k in functions) and set(functions) <= allowed):
        return ['argument: functions is not None or a mapping whose keys are among %s' % ', '.join(sorted(allowed))]
    return []


def _passed(call, findings, functions, args):
    if findings:
        return _result('refused', 'argument', findings)
    try:
        core = call(*args, **(functions or {}))
    except Exception as exc:  # AC5: the adapter catches its own, so this is a last guard
        return _result('refused', 'core', ['core: the adapter raised %s' % type(exc).__name__])
    if not isinstance(core, dict) or core.get('result') != 'done':
        return _result('refused', 'core', ['core: the adapter gave %r' % (core.get('result') if isinstance(core, dict)
                                                                          else core,)], core=core)
    return _result('done', core=core)


_START_FUNCTIONS = frozenset({'start_session', 'read_log', 'append', 'grant', 'release', 'held', 'check'})
_SUBMIT_FUNCTIONS = frozenset({'read', 'append', 'release', 'held'})
_END_FUNCTIONS = frozenset({'release_lease_token', 'end_session'})


def start(root, task_id, session_id, holder, inputs, code_sha256, expires_at, recorder, now, start=None,
          functions=None):
    """Start the session through adapter.start (TASK-060 AC4, AC5); returns a mapping with RESULT_KEYS."""
    start = adapter.start if start is None else start
    args = (root, task_id, session_id, holder, inputs, code_sha256, expires_at, recorder, now)
    try:
        found = adapter._start_findings(*args) + _functions_findings(functions, _START_FUNCTIONS)
    except Exception as exc:  # AC5
        found = ['argument: checking the arguments raised %s' % type(exc).__name__]
    return _passed(start, found, functions, args)


def submit(root, repo, commit_id, task_id, event_id, recorder, now, submit=None, functions=None):
    """Submit the session's commit through adapter.submit (TASK-060 AC4, AC5); returns a mapping with RESULT_KEYS."""
    submit = adapter.submit if submit is None else submit
    args = (root, repo, commit_id, task_id, event_id, recorder, now)
    try:
        found = adapter._submit_findings(*args) + _functions_findings(functions, _SUBMIT_FUNCTIONS)
    except Exception as exc:  # AC5
        found = ['argument: checking the arguments raised %s' % type(exc).__name__]
    return _passed(submit, found, functions, args)


def end(root, task_id, session_id, fencing_token, now, end=None, functions=None):
    """End the session through adapter.end (TASK-060 AC4, AC5); returns a mapping with RESULT_KEYS."""
    end = adapter.end if end is None else end
    args = (root, task_id, session_id, fencing_token, now)
    try:
        found = adapter._end_findings(*args) + _functions_findings(functions, _END_FUNCTIONS)
    except Exception as exc:  # AC5
        found = ['argument: checking the arguments raised %s' % type(exc).__name__]
    return _passed(end, found, functions, args)

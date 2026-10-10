"""The event log's append rules (task TASK-007): specification 1 sections 4 and 8, specification 2 sections 6.1 to 6.3.

``append`` takes an event log as bytes and one new event, and decides whether and how the event is appended. It
returns an ``AppendResult``: ``appended`` with the exact bytes of the new line and of the whole new log, ``duplicate``
when the log already holds the same event under its event_id, or ``refused`` with one reason:

- ``log``: the given log has a finding under ``records.check_log``, or is not empty and does not end with LF (AC1);
- ``conflict``: the log holds another event under the same event_id (AC2);
- ``event``: the new event has a finding of its own (AC3);
- ``fence``: the event needs a lease and the lease given does not hold it, or it names no task_id (AC6; TASK-015
  AC3), with the observation record of the refusal in ``record`` when the event names a task and the caller gives
  recorder and record_id, and otherwise no record and a finding that says which input is missing (AC7, narrowed by
  TASK-015's choice (r1));
- ``log_after``: the whole log after the append has a finding under ``records.check_log`` (AC4).

Nothing is appended unless the result is ``appended``, and then the new log's bytes are the given bytes followed by
exactly one line (AC5).

Limits (AC11):
- It returns bytes and writes none: it opens, writes and removes no file, and no code of the repository writes an
  event log yet, so nothing here shows that a log on disk is append-only.
- The lease is the caller's: nothing here grants, holds, releases or expires one, and the lease given is trusted.
- It rebuilds no projection and derives no task state, retry count or record view (specification 1 section 6).
- It does not check that a submitted commit exists or carries its trailer (recovery, specification 1 section 7).
- It checks the forms that ``records`` checks and the rules of AC2 to AC7, nothing more. It reads the clock nowhere:
  the append time is always given.

Readings of the specifications that the contract marks "(reading)" are noted where they are applied.
"""

import datetime
import json
import re

from aieos_bootstrap import records

RESULTS = ('appended', 'duplicate', 'refused')
REASONS = ('log', 'conflict', 'event', 'log_after', 'fence')
LEASE_KEYS = frozenset({'task_id', 'fencing_token', 'expires_at'})
# The keys that make two events under one event_id the same event (AC2); seq and appended_at are the log's, not the
# event's.
SAME_EVENT_KEYS = ('type', 'payload', 'task_id', 'fencing_token', 'corrects')

_TASK = re.compile(r'TASK-[0-9]+')
_ZERO = datetime.timedelta(0)


class AppendResult:
    """The result of one append.

    - ``result``: one of RESULTS; ``reason``: one of REASONS when refused, else None.
    - ``seq``: the new line's seq when appended; the seq of the line holding the event_id for a duplicate or a
      conflict; else None.
    - ``line`` and ``log``: the bytes of the new line and of the whole new log when appended; else None.
    - ``findings``: the findings that caused a refusal, as text.
    - ``record``: for a ``fence`` refusal, the payload of the record.added event that records it (AC7) when it can be
      built (TASK-015 AC3); else None.
    """

    __slots__ = ('result', 'reason', 'seq', 'line', 'log', 'findings', 'record')

    def __init__(self, result, reason=None, seq=None, line=None, log=None, findings=(), record=None):
        self.result = result
        self.reason = reason
        self.seq = seq
        self.line = line
        self.log = log
        self.findings = tuple(findings)
        self.record = record

    def __repr__(self):
        return 'AppendResult(%r, reason=%r, seq=%r, findings=%r)' % (self.result, self.reason, self.seq, self.findings)


def _refused(reason, findings=(), seq=None, record=None):
    return AppendResult('refused', reason, seq=seq, findings=findings, record=record)


def _canonical(obj):
    """One canonical JSON text (AC3, reading): sorted keys, no spaces after separators, ASCII-only escapes."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def _same_text(obj):
    """The canonical text of the keys that make an event the same event, absent keys left out (absent equals absent);
    None when it cannot be written as JSON text, so that it equals nothing."""
    try:
        return _canonical({k: obj[k] for k in SAME_EVENT_KEYS if k in obj})
    except (TypeError, ValueError, RecursionError):
        return None


def _is_utc(value):
    """A timezone-aware datetime whose offset from UTC is zero."""
    return isinstance(value, datetime.datetime) and value.tzinfo is not None and value.utcoffset() == _ZERO


def _time_text(value):
    """The append time as ISO 8601 UTC with "Z", to the second (AC3); written by hand so that every year has four
    digits."""
    return '%04d-%02d-%02dT%02d:%02d:%02dZ' % (value.year, value.month, value.day, value.hour, value.minute,
                                                value.second)


def _token_text(token):
    try:
        return _canonical(token)
    except (TypeError, ValueError, RecursionError):
        return None


def _needs_lease(event_type, fencing_token):
    """An event that carries a fencing_token, task.submitted always (AC6)."""
    return fencing_token is not None or event_type == 'task.submitted'


def refusal_record(event_id, task_id, recorder, record_id):
    """The payload of the record.added event that records a fence refusal (AC7; specification 2 section 6.2: the core's
    observation of specification 1 section 8). The recorder and record_id are the caller's (reading)."""
    return {'record_id': record_id, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
            'recorder': recorder, 'subject': task_id, 'evidence_type': 'refused_submission', 'outcome': 'fail',
            'refers_to': event_id}


def _lease_findings(lease, task_id, fencing_token, appended_at):
    """Why the lease given does not hold the event (AC6); an empty list when it does."""
    if lease is None:
        return ['fence: no lease is given']
    if not isinstance(lease, dict) or set(lease) != LEASE_KEYS:
        return ['fence: the lease is not a mapping with exactly task_id, fencing_token and expires_at']
    found = []
    if fencing_token is None:
        found.append('fence: the event carries no fencing_token')
    if lease['task_id'] != task_id:
        found.append('fence: the lease is on %r, not on the event\'s task %r' % (lease['task_id'], task_id))
    lease_token = _token_text(lease['fencing_token'])
    if fencing_token is not None and (lease_token is None or lease_token != _token_text(fencing_token)):
        found.append('fence: the event\'s fencing_token is not the lease\'s')
    expires_at = lease['expires_at']
    if not _is_utc(expires_at):
        found.append('fence: the lease\'s expires_at is not a timezone-aware UTC datetime')
    elif not expires_at > appended_at:
        found.append('fence: the lease expired at or before the append time')
    return found


def append(log, event_type, payload, event_id, appended_at, task_id=None, fencing_token=None, corrects=None,
           lease=None, recorder=None, record_id=None):
    """Decide how one event is appended to ``log`` (bytes; empty bytes for a new log). Returns an AppendResult.

    ``appended_at`` is the append time, a timezone-aware datetime in UTC. ``task_id``, ``fencing_token`` and
    ``corrects`` go into the envelope only when given (not None). ``lease`` is the lease the caller holds for the
    event's task, a mapping with exactly task_id, fencing_token and expires_at. ``recorder`` and ``record_id`` are
    those of the refusal's record if the event is refused by the fence (AC7); they are looked at only then, after the
    log and event_id checks (TASK-015 AC1, AC2), and their absence never raises: a fence refusal without them, or for
    an event that names no task_id, carries no record and a finding that says why (TASK-015 AC3, choice (r1)).
    """
    if not isinstance(log, (bytes, bytearray)):
        raise TypeError('the log is given as bytes, not %s' % type(log).__name__)
    log = bytes(log)

    # AC1: the given log, checked before anything else; a damaged log is never extended (fail closed).
    report = records.check_log(log)
    log_findings = [str(f) for _, f in report.findings()]
    if log and not log.endswith(b'\n'):
        log_findings.append('2:lf: the log does not end with LF')
    if log_findings:
        return _refused('log', log_findings)

    # AC2: idempotency by event_id, against the first line that holds it (later identical lines are ignored
    # duplicates of it, specification 1 section 7 point 4).
    new_event = {'type': event_type, 'payload': payload}
    for key, value in (('task_id', task_id), ('fencing_token', fencing_token), ('corrects', corrects)):
        if value is not None:
            new_event[key] = value
    known_ids = set()
    for line in report.lines:
        old = line.event
        known_ids.add(old['event_id'])
        if line.duplicate_of is None and old['event_id'] == event_id:
            if _same_text(old) is not None and _same_text(old) == _same_text(new_event):
                return AppendResult('duplicate', seq=old['seq'])
            return _refused('conflict', ['event_id %r is on the line with seq %d with another event' % (event_id, old['seq'])],
                            seq=old['seq'])

    # AC3: the new event's own form.
    findings = []
    if not records._is_str(event_id):
        findings.append('6.1:event_id: event_id is not a non-empty string')
    if not _is_utc(appended_at):
        findings.append('6.1:appended_at: the append time is not a timezone-aware datetime in UTC')
    if task_id is not None and not records._matches(_TASK, task_id):
        findings.append('6.1:task_id: task_id is not TASK- followed by digits (reading)')
    if fencing_token is not None:
        findings.extend(str(f) for f in records._check_fence({'fencing_token': fencing_token}, None))
    if corrects is not None and not (records._is_str(corrects) and corrects in known_ids):
        findings.append('6.1:corrects: corrects is not the event_id of a line of the log (reading)')
    findings.extend(str(f) for f in records.check_payload(event_type, payload))
    line_bytes = None
    if not findings:
        obj = dict(new_event)
        obj.update({'event_id': event_id, 'appended_at': _time_text(appended_at), 'seq': len(report.lines) + 1})
        try:
            line_bytes = (_canonical(obj) + '\n').encode('ascii')
        except (TypeError, ValueError, RecursionError) as exc:
            findings.append('6.1:json: the event cannot be written as one JSON text (%s)' % exc)
    if findings:
        return _refused('event', findings)

    # AC6, AC7: the fence (TASK-015 AC3). An event that needs a lease and names no task_id cannot hold "a lease on the
    # event's task_id", so it is refused by the fence (reading). The record's subject is the task id and its recorder
    # and record_id are the caller's, so the record is built only when all three exist (choice (r1)).
    if _needs_lease(event_type, fencing_token):
        if task_id is None:
            fence = ['fence: the event names no task_id, so no lease can be on its task']
        else:
            fence = _lease_findings(lease, task_id, fencing_token, appended_at)
        if fence:
            if task_id is None:
                return _refused('fence', fence + ['fence: no refusal record, the event names no task_id'])
            if not (records._is_str(recorder) and records._is_str(record_id)):
                return _refused('fence', fence + ['fence: no refusal record, recorder and record_id are not both '
                                                  'non-empty strings'])
            return _refused('fence', fence, record=refusal_record(event_id, task_id, recorder, record_id))

    # AC4: the whole log after the append.
    new_log = log + line_bytes
    after = [str(f) for _, f in records.check_log(new_log).findings()]
    if after:
        return _refused('log_after', after)

    # AC5: the given bytes are an exact prefix, followed by exactly one line.
    if not (new_log[:len(log)] == log and new_log[len(log):] == line_bytes and line_bytes.count(b'\n') == 1):
        raise RuntimeError('the append-only property failed (AC5); nothing is returned')
    return AppendResult('appended', seq=len(report.lines) + 1, line=line_bytes, log=new_log)

"""Recovery between Git and the event log at start (task TASK-009): specification 1 section 7.

``reconcile`` takes an event log as bytes, the commits whose messages the caller read from Git (oldest first), the
leases the local store holds and the recovery time, and returns a ``RecoveryResult``: the log after every event that
recovery appends, the events it built, the leases whose expiry has passed, and findings that change no state.

- Step 1: for every commit whose trailer names a task and that no task.submitted event names, a compensating
  task.submitted when a lease counts (AC3), else a record.added event with the observation of an unfenced write.
- Step 2: a task.submitted event whose commit is not among the given commits is reported; Git wins, and the log is
  never rewritten (AC4).
- Step 3 (an intent file against a projection) has nothing to act on: no projection exists in the bootstrap (AC10).
- Step 4: an event the log already holds under its event_id is a duplicate and changes nothing (TASK-007's AC2).
- Step 5: the leases whose expiry is at or before the recovery time are returned, never changed (AC5).

Every event is built by ``eventlog.append``, one at a time, so TASK-007's form, idempotency and fence rules apply
unchanged; this module builds no log line itself.

Departure from a proposed sentence (decision D-390, reading (t1); stated in the contract's header): specification 1
section 7 step 1 counts "a lease on that task which the local store still holds (this step runs before step 5)";
here a lease counts only when its expiry is after the recovery time, as section 8 and concept line 849 say, so a
commit made under a lease past its expiry gives the observation, never a compensating submission.

Limits (AC10):
- It reads nothing and writes nothing: it opens, writes and removes no file, reads no clock (the recovery time is
  given) and expires no lease. How the commits are read from Git and the leases from the local store is not shown.
- Whether an unfenced write blocks the task's acceptance stays open (specification 2 section 10 point 7).
"""

import datetime
import hashlib
import json
import re

from aieos_bootstrap import eventlog
from aieos_bootstrap import records

_TASK = re.compile(r'TASK-[0-9]+')
_COMMIT = re.compile(r'[0-9a-f]{40}')
_COUNTER = re.compile(r'[0-9]+')
_ZERO = datetime.timedelta(0)
TASK_KEY = 'AIEOS-Task'
FENCE_KEY = 'AIEOS-Fence'
COMMIT_KEYS = frozenset({'commit', 'message'})
ID_PREFIX = 'recovery'


class RecoveryResult:
    """The result of one recovery.

    - ``log``: the bytes of the log after every appended event (the given bytes when nothing is appended).
    - ``events``: one dict per event built, {event_id, type, task_id, result}, result ``appended`` or ``duplicate``,
      in the order they were built.
    - ``expired``: the given leases whose expires_at is at or before the recovery time, in the given order.
    - ``findings``: what changes no state, as text.
    """

    __slots__ = ('log', 'events', 'expired', 'findings')

    def __init__(self, log, events, expired, findings):
        self.log = log
        self.events = tuple(events)
        self.expired = tuple(expired)
        self.findings = tuple(findings)

    def __repr__(self):
        return 'RecoveryResult(events=%r, expired=%d, findings=%r)' % (self.events, len(self.expired), self.findings)


def _id(commit, kind):
    """AC6: the SHA-256 hex digest of the UTF-8 text "recovery", the commit id and the kind, joined by LF."""
    return hashlib.sha256('\n'.join((ID_PREFIX, commit, kind)).encode('utf-8')).hexdigest()


def _token_text(token):
    """The one form in which two fencing tokens are compared (decision D-391 C4 (i)): the canonical JSON text of
    specification 2 section 6.1's {epoch, counter}, as eventlog compares them; None when it cannot be written, so it
    equals nothing. An epoch given as an integer and one given as text are different tokens (fail closed)."""
    try:
        return json.dumps(token, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        return None


def _is_utc(value):
    return isinstance(value, datetime.datetime) and value.tzinfo is not None and value.utcoffset() == _ZERO


def trailers(message):
    """AC2: the AIEOS-Task and AIEOS-Fence values of a commit message's last paragraph (Git's trailer block).

    Returns (trailer, findings): trailer is {task, fence}, each None when absent, fence {epoch, counter}; findings is a
    list of text, not empty when a line names either key in another form or names a key twice. A line naming either key
    (ignoring letter case) outside the last paragraph, or in it in another letter case, is such a form (decision D-393
    C2): the CI's own trailer rule reads an AIEOS-Task line anywhere in the message, so recovery reports it rather
    than leave the commit alone (fail closed)."""
    if not isinstance(message, str):
        raise TypeError('the message is given as a string, not %s' % type(message).__name__)
    paragraphs = [p for p in re.split(r'\n[ \t]*\n', message.strip('\n')) if p.strip()]
    last = paragraphs[-1].split('\n') if paragraphs else []
    keys = {k.lower(): k for k in (TASK_KEY, FENCE_KEY)}
    found = {TASK_KEY: [], FENCE_KEY: []}
    findings = []
    for paragraph in paragraphs[:-1]:
        for line in paragraph.split('\n'):
            key, sep, _ = line.partition(':')
            if sep and key.strip().lower() in keys:
                findings.append('trailer: %r is named outside the last paragraph' % key.strip())
    for line in last:
        key, sep, value = line.partition(':')
        name = key.strip()
        if not (sep and name.lower() in keys):
            continue
        if name != keys[name.lower()]:
            findings.append('trailer: %r is not spelled %r' % (name, keys[name.lower()]))
            continue
        if key != name:
            findings.append('trailer: %r is not at the start of its line' % name)
        found[name].append(value.strip())
    trailer = {'task': None, 'fence': None}
    for key in (TASK_KEY, FENCE_KEY):
        if len(found[key]) > 1:
            findings.append('trailer: %s is given %d times' % (key, len(found[key])))
    if len(found[TASK_KEY]) == 1:
        task = found[TASK_KEY][0]
        if _TASK.fullmatch(task):
            trailer['task'] = task
        else:
            findings.append('trailer: %s %r is not TASK- followed by digits' % (TASK_KEY, task))
    if len(found[FENCE_KEY]) == 1:
        epoch, sep, counter = found[FENCE_KEY][0].rpartition(':')
        if sep and epoch and _COUNTER.fullmatch(counter):
            trailer['fence'] = {'epoch': epoch, 'counter': int(counter)}
        else:
            findings.append('trailer: %s %r is not <epoch>:<counter>' % (FENCE_KEY, found[FENCE_KEY][0]))
    return trailer, findings


def _check_arguments(log, commits, leases, now, recorder):
    if not isinstance(log, (bytes, bytearray)):
        raise TypeError('the log is given as bytes, not %s' % type(log).__name__)
    if not isinstance(commits, list):
        raise TypeError('the commits are given as a list')
    for c in commits:
        if not isinstance(c, dict) or set(c) != COMMIT_KEYS:
            raise ValueError('a commit is not a mapping with exactly commit and message')
        if not (isinstance(c['commit'], str) and _COMMIT.fullmatch(c['commit'])):
            raise ValueError('a commit id is not 40 lowercase hex digits')
        if not isinstance(c['message'], str):
            raise ValueError('a commit message is not a string')
    if not isinstance(leases, list):
        raise TypeError('the leases are given as a list')
    for lease in leases:
        if not isinstance(lease, dict) or set(lease) != eventlog.LEASE_KEYS:
            raise ValueError('a lease is not a mapping with exactly task_id, fencing_token and expires_at')
        if not _is_utc(lease['expires_at']):
            raise ValueError('a lease\'s expires_at is not a timezone-aware UTC datetime')
    if not _is_utc(now):
        raise ValueError('the recovery time is not a timezone-aware UTC datetime')
    if not (isinstance(recorder, str) and recorder):
        raise ValueError('the recorder is not a non-empty string')


def _submissions(log):
    """The task.submitted events of a log free of findings: (commit, task_id, token text) of each first line."""
    out = []
    for line in records.check_log(log).lines:
        e = line.event
        if line.duplicate_of is None and e is not None and e.get('type') == 'task.submitted':
            out.append((e['payload'].get('commit'), e.get('task_id'), _token_text(e.get('fencing_token'))))
    return out


def observation(commit, task_id, recorder):
    """The payload of the record.added event of an unfenced write (specification 2 section 6.2; AC3)."""
    return {'record_id': _id(commit, 'unfenced_write'), 'fact_kind': 'observation',
            'source_class': 'deterministic_tool_local', 'recorder': recorder, 'subject': task_id,
            'evidence_type': 'unfenced_write', 'outcome': 'fail', 'refers_to': commit}


def reconcile(log, commits, leases, now, recorder):
    """Recover the event log against the given commits at the given time. Returns a RecoveryResult (AC1)."""
    _check_arguments(log, commits, leases, now, recorder)
    log = bytes(log)
    expired = [lease for lease in leases if not lease['expires_at'] > now]
    report = records.check_log(log)
    damaged = [str(f) for _, f in report.findings()]
    if log and not log.endswith(b'\n'):
        damaged.append('2:lf: the log does not end with LF')
    if damaged:
        return RecoveryResult(log, (), expired, ['log: %s' % f for f in damaged])

    findings = []
    events = []
    given = {c['commit'] for c in commits}
    submitted = _submissions(log)
    # Step 2: Git wins; a submission naming a commit that is not given is reported, nothing is appended.
    for commit, task_id, _ in submitted:
        if commit not in given:
            findings.append('step 2: the log\'s task.submitted of %s names the commit %s, which is not among the '
                            'given commits; nothing is appended' % (task_id, commit))
    named = {commit for commit, _, _ in submitted}
    used = {(task_id, token) for _, task_id, token in submitted}

    def add(event_type, payload, event_id, task_id, fencing_token=None, lease=None):
        nonlocal log
        r = eventlog.append(log, event_type, payload, event_id, now, task_id=task_id, fencing_token=fencing_token,
                            lease=lease, recorder=recorder, record_id=_id(event_id, 'refused_submission'))
        if r.result == 'refused':
            findings.append('step 1: eventlog.append refused the %s of %s (reason %s): %s'
                            % (event_type, task_id, r.reason, '; '.join(r.findings)))
            return False
        if r.result == 'appended':
            log = r.log
        events.append({'event_id': event_id, 'type': event_type, 'task_id': task_id, 'result': r.result})
        return True

    # Step 1, oldest first.
    for c in commits:
        trailer, bad = trailers(c['message'])
        if bad:
            findings.extend('commit %s: %s' % (c['commit'], f) for f in bad)
            continue
        task_id = trailer['task']
        if task_id is None or c['commit'] in named:
            continue
        token = _token_text(trailer['fence']) if trailer['fence'] is not None else None
        lease = None
        if token is not None and (task_id, token) not in used:
            for held in leases:
                if (held['task_id'] == task_id and _token_text(held['fencing_token']) == token
                        and held['expires_at'] > now):
                    lease = held
                    break
        if lease is not None:
            if add('task.submitted', {'commit': c['commit'], 'compensating': True}, _id(c['commit'], 'task.submitted'),
                   task_id, fencing_token=trailer['fence'], lease=lease):
                used.add((task_id, token))
                named.add(c['commit'])
        else:
            add('record.added', observation(c['commit'], task_id, recorder), _id(c['commit'], 'record.added'), task_id)
    return RecoveryResult(log, events, expired, findings)

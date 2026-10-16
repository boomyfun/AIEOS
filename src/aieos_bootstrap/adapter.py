"""The adapter interface of gov-AIEOS (task TASK-051; specification 5 revision 3, section 2 items 1, 4 and 5, and section
11 point 7; specification 1 revision 2, sections 5.1 and 8; specification 3 revision 4, section 1): the subset of the
adapter contract that the core already has paths for. An adapter connects one agent runtime to the core and never
writes the project-state directory itself: every write here is the core's, through the writer (INV-004).

Three calls, each a function with no state kept between calls:

1. ``start(root, task_id, session_id, holder, inputs, code_sha256, expires_at, recorder, now)`` (section 2 item 1):
   the session row is opened through writer.start_session, then execution.execute (TASK-032) runs the Resume Check
   once and, on CONTINUE or CONTINUE_WITH, grants the lease. The result carries the decision and, when a lease was
   granted or kept, its fencing token, which the caller carries for the session (AC2).
2. ``submit(root, repo, commit_id, task_id, event_id, recorder, now)`` (section 2 item 4): submit.submit (TASK-025)
   reads the commit and appends task.submitted with the commit's AIEOS-Fence token; the fence decision is the
   writer's, and this module compares no token of its own (AC3).
3. ``end(root, task_id, session_id, fencing_token, now)`` (section 2 item 5): when a token is given, the lease is
   released by it through writer.release_lease_token (TASK-028); a refusal with reason "none" or "token" (a
   submission or the core released it, or another holder holds the task now) is no error and releases nothing; then
   the session row is closed through writer.end_session (AC4).

The ids (section 11 point 7): a session is named by its task_id, its session_id and its holder, given by the caller;
the fencing token is the one the grant returns, carried by the caller from start to end. Each call returns a mapping
with exactly RESULT_KEYS (AC5); a refusal of the called core function gives reason "core" with its findings, and an
exception raised by a called function is caught and becomes a result; none escapes.

The functions it calls are keyword arguments, each defaulting at call time to the named function: start_session
(writer.start_session) and execute's read_log, append, grant, release, held and check (writer.read_log,
writer.append_event, writer.grant_lease, writer.release_lease_token, writer.held_lease, and resume_check.check by
execute's own default); submit's read, append, release and held (gitread.run, writer.append_event,
writer.release_lease_token, writer.held_lease); end's release_lease_token and end_session (writer's).

Purity (AC10): this module starts no process except through gitread.run, which submit.submit calls, opens no file,
reads no clock and no environment, builds no event-log line itself and makes no network or model call.

Limits (AC9), stated:
- No observation and no violation call (specification 5 section 2 item 3, sections 7 and 8; the record keys are for
  specification 2's next revision, section 11 points 3 and 4, and the core has no path yet from a hook's refusal to
  violation.detected).
- Abnormal ends beyond the lease's expiry are not handled (section 11 point 10): the lease's expiry stays the fallback.
- The lease's write-set is neither passed nor enforced here (left open, a reading): enforcement while running is the
  Claude Code adapter's hooks (section 6), whose install is the owner's; the gates read the contract's write-set after.
- The store is the caller's to open (writer.open_store), with its epoch; leases are expired by the caller
  (writer.expire_leases). One run at a time (the writer's limit).
- A start that grants no lease leaves the session row open, for end to close.
- __init__.py is not changed, so __all__ does not name this module.
"""

import datetime
import re

from aieos_bootstrap import execution
from aieos_bootstrap import gitread
from aieos_bootstrap import submit as submission
from aieos_bootstrap import writer

RESULT_KEYS = ('result', 'reason', 'findings', 'core', 'decision', 'fencing_token', 'released')
NO_ERROR_RELEASE = ('none', 'token')
_TASK = re.compile(r'TASK-[0-9]+')
_HEX64 = re.compile(r'[0-9a-f]{64}')
_HEX40 = re.compile(r'[0-9a-f]{40}')
_ZERO = datetime.timedelta(0)


def _result(result, reason=None, findings=(), core=None, decision=None, fencing_token=None, released=None):
    return {'result': result, 'reason': reason, 'findings': list(findings), 'core': core, 'decision': decision,
            'fencing_token': fencing_token, 'released': released}


def _text(value):
    return isinstance(value, str) and value != ''


def _utc_whole(value):
    return (isinstance(value, datetime.datetime) and value.tzinfo is not None and value.utcoffset() == _ZERO
            and value.microsecond == 0)


def _task(value):
    return isinstance(value, str) and _TASK.fullmatch(value) is not None


def _store_done(r):
    """The result of a store function: (its result text, its reason text, its findings as texts)."""
    state = getattr(r, 'result', None)
    reason = getattr(r, 'reason', None)
    found = [f for f in (getattr(r, 'findings', ()) or ()) if isinstance(f, str)]
    return (state if isinstance(state, str) else None), (reason if isinstance(reason, str) else None), found


def _core_findings(core):
    found = core.get('findings') if isinstance(core, dict) else None
    return [f for f in found if isinstance(f, str)] if isinstance(found, list) else []


# ---- start (AC1, AC2) ----

def _start_findings(root, task_id, session_id, holder, inputs, code_sha256, expires_at, recorder, now):
    found = []
    if not _text(root):
        found.append('argument: root is not a non-empty string')
    if not _task(task_id):
        found.append('argument: task_id is not "TASK-" followed by digits')
    if not _text(session_id):
        found.append('argument: session_id is not a non-empty string')
    if not _text(holder):
        found.append('argument: holder is not a non-empty string')
    if not isinstance(inputs, dict):
        found.append('argument: inputs is not a mapping')
    if not (isinstance(code_sha256, str) and _HEX64.fullmatch(code_sha256)):
        found.append('argument: code_sha256 is not 64 lowercase hex characters')
    if not _text(recorder):
        found.append('argument: recorder is not a non-empty string')
    times = True
    for name, value in (('expires_at', expires_at), ('now', now)):
        if not _utc_whole(value):
            found.append('argument: %s is not a timezone-aware datetime in UTC with whole seconds' % name)
            times = False
    if times and not expires_at > now:
        found.append('argument: expires_at is not after now')
    return found


def start(root, task_id, session_id, holder, inputs, code_sha256, expires_at, recorder, now, start_session=None,
          read_log=None, append=None, grant=None, release=None, held=None, check=None):
    """Open the session row, then run the Resume Check and grant the lease through execution.execute (TASK-051 AC1,
    AC2, AC5); returns a mapping with RESULT_KEYS."""
    start_session = writer.start_session if start_session is None else start_session
    read_log = writer.read_log if read_log is None else read_log
    append = writer.append_event if append is None else append
    grant = writer.grant_lease if grant is None else grant
    release = writer.release_lease_token if release is None else release
    held = writer.held_lease if held is None else held
    try:
        found = _start_findings(root, task_id, session_id, holder, inputs, code_sha256, expires_at, recorder, now)
    except Exception as exc:  # AC5: an argument whose own methods raise
        found = ['argument: checking the arguments raised %s' % type(exc).__name__]
    if found:
        return _result('refused', 'argument', found)
    try:
        state, reason, found = _store_done(start_session(root, session_id, holder, now))
    except Exception as exc:  # AC2, AC5
        return _result('refused', 'session', ['session: start_session raised %s' % type(exc).__name__])
    if state != 'done':
        return _result('refused', 'session', ['session: start_session gave %r (%r)' % (state, reason)] + found)
    request = {'holder': holder, 'session_id': session_id, 'expires_at': expires_at}
    try:
        core = execution.execute(root, task_id, inputs, code_sha256, request, recorder, now, read_log=read_log,
                                 append=append, grant=grant, release=release, held=held, check=check)
    except Exception as exc:  # AC5: execute catches its own, so this is a last guard
        return _result('refused', 'core', ['core: execute raised %s' % type(exc).__name__])
    if not isinstance(core, dict) or core.get('result') != 'decided':
        return _result('refused', 'core', ['core: execute gave %r' % (core.get('result') if isinstance(core, dict)
                                                                       else core,)] + _core_findings(core), core)
    lease = core.get('lease')
    token = lease.get('fencing_token') if isinstance(lease, dict) else None
    return _result('done', None, [], core, core.get('decision'), token if isinstance(token, dict) else None)


# ---- submit (AC1, AC3) ----

def _submit_findings(root, repo, commit_id, task_id, event_id, recorder, now):
    found = []
    if not _text(root):
        found.append('argument: root is not a non-empty string')
    if not _text(repo):
        found.append('argument: repo is not a non-empty string')
    if not (isinstance(commit_id, str) and _HEX40.fullmatch(commit_id)):
        found.append('argument: commit_id is not 40 lowercase hex characters')
    if not _task(task_id):
        found.append('argument: task_id is not "TASK-" followed by digits')
    if not _text(event_id):
        found.append('argument: event_id is not a non-empty string')
    if not _text(recorder):
        found.append('argument: recorder is not a non-empty string')
    if not _utc_whole(now):
        found.append('argument: now is not a timezone-aware datetime in UTC with whole seconds')
    return found


def submit(root, repo, commit_id, task_id, event_id, recorder, now, read=None, append=None, release=None, held=None):
    """Submit the session's commit through submit.submit (TASK-051 AC1, AC3, AC5); returns a mapping with
    RESULT_KEYS. The fence is the commit's own trailer, decided by the writer; nothing here compares a token."""
    read = gitread.run if read is None else read
    append = writer.append_event if append is None else append
    release = writer.release_lease_token if release is None else release
    held = writer.held_lease if held is None else held
    try:
        found = _submit_findings(root, repo, commit_id, task_id, event_id, recorder, now)
    except Exception as exc:  # AC5
        found = ['argument: checking the arguments raised %s' % type(exc).__name__]
    if found:
        return _result('refused', 'argument', found)
    try:
        core = submission.submit(root, repo, commit_id, task_id, event_id, recorder, now, read=read, append=append,
                                 release=release, held=held)
    except Exception as exc:  # AC5: submit catches its own, so this is a last guard
        return _result('refused', 'core', ['core: submit raised %s' % type(exc).__name__])
    if not isinstance(core, dict) or core.get('result') not in ('submitted', 'duplicate'):
        return _result('refused', 'core', ['core: submit gave %r' % (core.get('result') if isinstance(core, dict)
                                                                      else core,)] + _core_findings(core), core)
    return _result('done', None, [], core)


# ---- end (AC1, AC4) ----

def _token_form(token):
    return (isinstance(token, dict) and set(token) == {'epoch', 'counter'} and _text(token['epoch'])
            and type(token['counter']) is int and token['counter'] >= 0)


def _end_findings(root, task_id, session_id, fencing_token, now):
    found = []
    if not _text(root):
        found.append('argument: root is not a non-empty string')
    if not _task(task_id):
        found.append('argument: task_id is not "TASK-" followed by digits')
    if not _text(session_id):
        found.append('argument: session_id is not a non-empty string')
    if fencing_token is not None and not _token_form(fencing_token):
        found.append('argument: fencing_token is neither None nor {epoch: a non-empty string, counter: an int at '
                     'least 0}')
    if not _utc_whole(now):
        found.append('argument: now is not a timezone-aware datetime in UTC with whole seconds')
    return found


def end(root, task_id, session_id, fencing_token, now, release_lease_token=None, end_session=None):
    """Release the lease by its token, when one is given, then close the session row (TASK-051 AC1, AC4, AC5);
    returns a mapping with RESULT_KEYS."""
    release_lease_token = writer.release_lease_token if release_lease_token is None else release_lease_token
    end_session = writer.end_session if end_session is None else end_session
    try:
        found = _end_findings(root, task_id, session_id, fencing_token, now)
    except Exception as exc:  # AC5
        found = ['argument: checking the arguments raised %s' % type(exc).__name__]
    if found:
        return _result('refused', 'argument', found)
    released = None
    notes = []
    if fencing_token is not None:
        try:
            r = release_lease_token(root, task_id, fencing_token)
            state, reason, found = _store_done(r)
        except Exception as exc:  # AC4, AC5
            return _result('refused', 'release', ['release: release_lease_token raised %s; whether the lease was '
                                                  'released is not known' % type(exc).__name__])
        if state == 'done':
            released = getattr(r, 'value', None)
        elif state == 'refused' and reason in NO_ERROR_RELEASE:
            notes = ['release: nothing released (%s)' % reason] + found
        else:
            return _result('refused', 'release', ['release: release_lease_token gave %r (%r)' % (state, reason)]
                           + found)
    try:
        state, reason, found = _store_done(end_session(root, session_id, now))
    except Exception as exc:  # AC4, AC5
        return _result('refused', 'session', ['session: end_session raised %s' % type(exc).__name__],
                       released=released)
    if state != 'done':
        return _result('refused', 'session', ['session: end_session gave %r (%r)' % (state, reason)] + found,
                       released=released)
    return _result('done', None, notes, released=released)

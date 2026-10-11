"""The submission path of gov-AIEOS (task TASK-025; specification 1 sections 5.1 and 8; specification 2 sections 6.1,
6.3 and 6.6; DEF-0030): the second piece of the core's caller, after the Git reader.

``submit(root, repo, commit_id, task_id, event_id, recorder, now)`` takes one commit as the submission of one task:

1. Arguments (AC1): every argument is checked before anything is read; a wrong one gives a refusal result.
2. Reading (AC2): the commit is read through gitread.run, first "cat-file -t" (it must be a commit), then "cat-file
   -p", parsed by gitread.parse_commit; any failure is a refusal result with nothing appended.
3. Identification (AC3): the message must have a body (at least two paragraphs, so that its last paragraph is not the
   subject line: git's trailer rule differs from the contract's for a one-paragraph message, DEF-0052 F6), and
   recovery.trailers must give exactly one AIEOS-Task, equal to the task, with no finding on that key. Otherwise the
   commit cannot be identified as this task's submission, so nothing is recorded and nothing is appended.
4. The append (AC3, AC4): the task.submitted event, payload {commit, compensating false}, goes through
   writer.append_event with the commit's AIEOS-Fence token, or with no token when the commit carries no usable fence.
   The fence decision is the writer's (it passes the store's held lease to eventlog.append, which refuses a token that
   is not the held lease's, or a lease expired at or before ``now``, and the writer records the refusal as an
   observation, specification 1 section 8). This module makes no fence comparison of its own.
5. The lease (AC5): after an appended event the lease is released; after a duplicate (the same event appended
   before, for example when a run stopped between the append and the release) it is released only when the store
   still holds a lease with the commit's token, so a lease granted to another holder since is never released.

The result (AC6) is a mapping with exactly the keys result ("submitted", "duplicate" or "refused"), reason, findings,
appended and released. An exception raised by the writer's functions is caught and becomes a result; none escapes.

``read``, ``append``, ``release`` and ``held`` default, at call time, to gitread.run, writer.append_event,
writer.release_lease and writer.held_lease (AC7); tests pass stand-ins.

Purity (AC8): this module starts no process except through ``read``, opens no file itself, reads no clock and no
environment variable, grants no lease and creates no store (it never calls open_store, so DEF-0041 (c), never giving
an earlier store's epoch to a recreated store, does not apply), and builds no event-log line itself.

Limits (AC11):
- The PATH git is found by is the caller's precondition (DEF-0052 G1): gitread refuses an empty or relative entry, and
  an absolute entry is trusted as given.
- The tests use stand-ins for the writer: the real store's fence path is covered by the writer's own tests (TASK-016),
  not end to end with this module, and no test makes a commit with an AIEOS-Fence trailer.
- It does not check that the commit's changed paths lie in the task's write set, that the commit is reachable from a
  branch, or the task's state in the log (the held lease stands for IN_PROGRESS; the evaluation path is TASK-027);
  recovery at start is TASK-026.
- The lease is released in a separate call after the append, so a stop between them leaves the lease until a retry
  (a duplicate, which releases it only while the store holds that same token) or its expiry.
- Recorded and not recorded refusals: a commit of the task with no usable fence is refused by the writer and recorded
  as an observation; a commit that cannot be read, has no body, or names no, a doubled or a different task is refused
  with nothing appended and no record, since it cannot be identified as this task's submission.
"""

import datetime
import json
import os
import re

from aieos_bootstrap import gitread
from aieos_bootstrap import recovery
from aieos_bootstrap import writer

_COMMIT = re.compile(r'[0-9a-f]{40}')
_TASK = re.compile(r'TASK-[0-9]+')
_PARAGRAPH = re.compile(r'\n[ \t]*\n')
_ZERO = datetime.timedelta(0)
RESULT_KEYS = frozenset({'result', 'reason', 'findings', 'appended', 'released'})


def _result(result, reason=None, findings=(), appended=None, released=None):
    return {'result': result, 'reason': reason, 'findings': list(findings), 'appended': appended, 'released': released}


def _refused(reason, findings, appended=None):
    return _result('refused', reason, findings, appended)


def _is_str(value):
    return isinstance(value, str) and value != ''


def _token_text(token):
    """Two fencing tokens are compared as eventlog compares them: the canonical JSON text (None when unwritable)."""
    try:
        return json.dumps(token, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        return None


def _argument_findings(root, repo, commit_id, task_id, event_id, recorder, now):
    """AC1: what is wrong with the arguments, as a list of findings (empty when every argument is in form)."""
    found = []
    for name, value in (('root', root), ('repo', repo)):
        if not (_is_str(value) and os.path.isabs(value)):
            found.append('argument: %s is not a non-empty absolute path string' % name)
    if not (isinstance(commit_id, str) and _COMMIT.fullmatch(commit_id)):
        found.append('argument: commit_id is not 40 lowercase hexadecimal characters')
    if not (isinstance(task_id, str) and _TASK.fullmatch(task_id)):
        found.append('argument: task_id is not TASK- followed by digits')
    for name, value in (('event_id', event_id), ('recorder', recorder)):
        if not _is_str(value):
            found.append('argument: %s is not a non-empty string' % name)
    if not (isinstance(now, datetime.datetime) and now.tzinfo is not None and now.utcoffset() == _ZERO
            and now.microsecond == 0):
        found.append('argument: now is not a timezone-aware datetime in UTC with whole seconds')
    return found


def _read_failure(name, r):
    """AC2: why a read result does not count, or None when it does."""
    if not isinstance(r, dict) or not {'exit', 'out', 'err', 'error'} <= set(r):
        return 'git: %s gave no result in gitread.run\'s form' % name
    if r['error'] is not None:
        return 'git: %s was not run or did not finish: %s' % (name, r['error'])
    if r['exit'] != 0:
        return 'git: %s exited with %r' % (name, r['exit'])
    return None


def _read_commit(read, repo, commit_id):
    """AC2: the parsed commit, or (None, findings)."""
    r = read(repo, ['cat-file', '-t', commit_id])
    why = _read_failure('cat-file -t', r)
    if why is None and r['out'] != b'commit\n':
        why = 'git: the object is not a commit (cat-file -t gave %r)' % (r['out'],)
    if why is not None:
        return None, [why]
    r = read(repo, ['cat-file', '-p', commit_id])
    why = _read_failure('cat-file -p', r)
    if why is not None:
        return None, [why]
    parsed = gitread.parse_commit(r['out'])
    if parsed['error'] is not None:
        return None, ['git: the commit is out of form: %s' % parsed['error']]
    return parsed, []


def _key_findings(findings, key):
    return [f for f in findings if key.lower() in f.lower()]


def _identify(message, task_id):
    """AC3: (fence or None, refusal findings, fence findings). Refusal findings mean the commit is not identified."""
    paragraphs = [p for p in _PARAGRAPH.split(message.strip('\n')) if p.strip()]
    if len(paragraphs) < 2:
        return None, ['trailer: the message has no body, so its last paragraph is its subject (DEF-0052 F6)'], []
    trailer, findings = recovery.trailers(message)
    task_found = _key_findings(findings, recovery.TASK_KEY)
    if task_found:
        return None, task_found, []
    if trailer['task'] is None:
        return None, findings + ['trailer: the message names no %s' % recovery.TASK_KEY], []
    if trailer['task'] != task_id:
        return None, findings + ['trailer: the commit is of %s, not of %s' % (trailer['task'], task_id)], []
    fence_found = _key_findings(findings, recovery.FENCE_KEY)
    if trailer['fence'] is None or fence_found:
        return None, [], fence_found + ['trailer: the commit carries no usable %s' % recovery.FENCE_KEY]
    return trailer['fence'], [], []


def submit(root, repo, commit_id, task_id, event_id, recorder, now, read=None, append=None, release=None, held=None):
    """Take one commit as the submission of one task (TASK-025 AC1 to AC7); returns a mapping with RESULT_KEYS."""
    read = gitread.run if read is None else read
    append = writer.append_event if append is None else append
    release = writer.release_lease if release is None else release
    held = writer.held_lease if held is None else held

    found = _argument_findings(root, repo, commit_id, task_id, event_id, recorder, now)
    if found:
        return _refused('argument', found)
    try:
        parsed, found = _read_commit(read, repo, commit_id)
    except Exception as exc:  # AC6: no exception escapes
        return _refused('git', ['git: the read raised %s' % type(exc).__name__])
    if parsed is None:
        return _refused('git', found)
    fence, not_identified, fence_found = _identify(parsed['message'], task_id)
    if not_identified:
        return _refused('trailer', not_identified)

    payload = {'commit': commit_id, 'compensating': False}
    try:
        w = append(root, 'task.submitted', payload, event_id, now, recorder, task_id=task_id, fencing_token=fence)
    except Exception as exc:  # AC6
        return _refused('store', fence_found + ['store: the append raised %s' % type(exc).__name__])
    outcome = getattr(w, 'result', None)
    if outcome == 'appended' and fence is not None:
        return _release(root, task_id, release, 'submitted', w, [])
    if outcome == 'duplicate' and fence is not None:
        try:
            lease = held(root, task_id)
        except Exception as exc:  # AC6
            return _result('duplicate', None, ['store: reading the held lease raised %s; the lease was not released'
                                               % type(exc).__name__], w)
        mine = isinstance(lease, dict) and _token_text(lease.get('fencing_token')) == _token_text(fence)
        if not mine:
            return _result('duplicate', None, ['store: the held lease, if any, is not the commit\'s; nothing was released'], w)
        return _release(root, task_id, release, 'duplicate', w, [])
    if outcome in ('appended', 'duplicate'):
        # An event without a token is always refused by the writer's fence; reaching here means the writer did not.
        return _refused('store', fence_found + ['store: the writer gave %r for an event with no fencing token' % outcome], w)
    reason = getattr(w, 'reason', None)
    findings = list(getattr(w, 'findings', ()) or ())
    refusal = getattr(w, 'refusal', None)
    if refusal is not None:
        findings.append('store: the refusal record was %s' % getattr(refusal, 'result', None))
    return _refused(reason if _is_str(reason) else 'store', fence_found + findings, w)


def _release(root, task_id, release, result, w, findings):
    """AC5, AC6: release the lease once; a raised exception leaves the result and adds a finding."""
    try:
        lease = release(root, task_id)
    except Exception as exc:  # AC6
        return _result(result, None, findings + ['store: the release raised %s; the lease was not released, and it '
                                                 'expires by its own expiry' % type(exc).__name__], w)
    return _result(result, None, findings, w, lease)

"""The core violation path tied by the live lease (task TASK-070; specification 5 revision 4, section 8 and section 11
point 7, bullets 3 to 6; specification 1 revision 2, section 5.3; specification 3 revision 4, section 8). TASK-070
supersedes TASK-069, which put this call in adapter.py: two accepted tests pin adapter.py's code, so adapter.py is not
changed and the call lives here.

One call, a function with no state kept between calls:
``session_violation(root, session_id, observation, event_id, recorder, now, lookup=None, append=None, release=None)``
is the violation path tied to a session by its session id and the one live lease the core's store holds for it
(specification 5 :109, with :108 for what the launcher passes in the environment: the session id and the root, no
token). The token is read core-side from that lease and never returned. The steps, in order, the first that ends giving
the result, a mapping with exactly adapter.RESULT_KEYS:

(1) root and session_id are non-empty strings and now is a timezone-aware datetime in UTC with whole seconds, else
reason "argument".
(2) The lookup, lookup(root, session_id, now), by default writer.session_lease reached at call time: a refusal gives
reason "lease" with the lookup's reasons kept as findings[0]'s prefix ("argument", "root", "no_store", "link",
"unreadable", "tables", "session", "ended", "leases" and the others), and every answer other than a tied lease of the
checked shape gives "lease"; "lease_row_without_session" and a "no_lease_row" done cannot arise with a session id
required.
(3) The record, through adapter.violation (reached at call time on the adapter module) with the lease's task_id and
fencing_token, one now for the lookup and the record; append and release are passed through to it, and it defaults
them to the writer's; the observation's subject must be the tied lease's task, else "argument" and nothing is appended.
(3b) The token removed: the result can carry a fencing token by two routes, the released lease (released and
core['released']) and a release refusal that names the held and the given epoch and counter when another holder has
the task; so released and core['released'] are copied without fencing_token, and every finding of the writer's
token-refusal form, or holding both "epoch" and "counter", is replaced by "release: the lease is held with another
token (not shown)"; the result is a new mapping, the given one never mutated; a raise there gives "entry: after the
record", although the violation, the decision and the release may already be in the log and the store.
(4) No exception escapes (reason "entry").

A "lease" refusal is no section 8 violation and no STOP: with no live tied lease there is no session to stop and
nothing is appended.

Stated limits: the race between the lookup and the appends (the store and the event log are not one transaction; a
lease lost or granted again between them gives the writer's fence refusal, fail closed); the partial outcome
(violation.detected appended and the decision refused, so the log holds a violation with no STOP: violation; a retry
with the same event_id while the lease is still held completes it, and a different event_id would repeat the
observation's record_id); a repeat after "done" gives "lease"; the session tie and now are the caller's (an early now
makes an expired lease read as live, the fail-open direction); the observed read-set record is left for section 11
point 10. It never writes an observed read-set record, a reads row or a session row, and never opens the store or the
event log itself; it opens no file, starts no process, reads no clock, no environment and no standard input. Nothing
hook-side calls it yet: its caller is H2's PreToolUse program, a later contract.
"""

from aieos_bootstrap import adapter
from aieos_bootstrap import writer

_LEASE_KEYS = frozenset({'task_id', 'fencing_token', 'expires_at'})
_HIDDEN = 'release: the lease is held with another token (not shown)'
_NO_TIED_LEASE = 'lease: the lookup gave no tied lease'
_NO_RESULT_MAPPING = 'entry: adapter.violation gave no result mapping'


def _session_findings(root, session_id, now):
    found = []
    if not adapter._text(root):
        found.append('argument: root is not a non-empty string')
    if not adapter._text(session_id):
        found.append('argument: session_id is not a non-empty string')
    if not adapter._utc_whole(now):
        found.append('argument: now is not a timezone-aware datetime in UTC with whole seconds')
    return found


def _tied(answer):
    """The lease of a lookup answer that is a tied lease of the checked shape (TASK-070 AC2), else None."""
    if not isinstance(answer, writer.StoreResult) or answer.result != 'done' or answer.reason != 'tied':
        return None
    lease = answer.value
    if type(lease) is not dict or set(lease) != _LEASE_KEYS:
        return None
    if not adapter._task(lease['task_id']) or not adapter._token_form(lease['fencing_token']):
        return None
    return lease


def _hides_token(found):
    """Whether a finding holds a token: the writer's token-refusal form or both "epoch" and "counter" (TASK-070 AC1)."""
    return isinstance(found, str) and ((found.startswith('the lease on ') and ' is held with epoch ' in found)
                                       or ('epoch' in found and 'counter' in found))


def _filtered(found):
    return [_HIDDEN if _hides_token(f) else f for f in found]


def _without_token(lease):
    return None if lease is None else {k: v for k, v in lease.items() if k != 'fencing_token'}


def _token_free(answer):
    """adapter.violation's answer checked and copied with no fencing token in it (TASK-070 AC1, AC3): a new mapping,
    never the given one and never mutated; _NO_RESULT_MAPPING when the answer is not of the checked shape."""
    if not isinstance(answer, dict) or set(answer) != set(adapter.RESULT_KEYS):
        return adapter._result('refused', 'entry', [_NO_RESULT_MAPPING])
    core = answer['core']
    if not (core is None or isinstance(core, dict)) or not isinstance(answer['findings'], list):
        return adapter._result('refused', 'entry', [_NO_RESULT_MAPPING])
    if not (answer['released'] is None or isinstance(answer['released'], dict)):
        return adapter._result('refused', 'entry', [_NO_RESULT_MAPPING])
    copied = None
    if core is not None:
        if not all(isinstance(core.get(k), list) for k in ('appended', 'duplicate', 'findings')):
            return adapter._result('refused', 'entry', [_NO_RESULT_MAPPING])
        if not (core.get('released') is None or isinstance(core.get('released'), dict)):
            return adapter._result('refused', 'entry', [_NO_RESULT_MAPPING])
        copied = dict(core)
        copied['appended'] = list(core['appended'])
        copied['duplicate'] = list(core['duplicate'])
        copied['findings'] = _filtered(core['findings'])
        copied['released'] = _without_token(core.get('released'))
    return adapter._result(answer['result'], answer['reason'], _filtered(answer['findings']), copied,
                           answer['decision'], released=_without_token(answer['released']))


def _session_violation(root, session_id, observation, event_id, recorder, now, lookup, append, release):
    try:
        found = _session_findings(root, session_id, now)
    except Exception as exc:  # TASK-070 AC1: an argument whose own methods raise
        found = ['argument: checking the arguments raised %s' % type(exc).__name__]
    if found:
        return adapter._result('refused', 'argument', found)
    lookup = writer.session_lease if lookup is None else lookup
    try:
        answer = lookup(root, session_id, now)
    except Exception as exc:  # TASK-070 AC2
        return adapter._result('refused', 'lease', ['lease: session_lease raised %s' % type(exc).__name__])
    lease = _tied(answer)
    if lease is None:
        if isinstance(answer, writer.StoreResult) and answer.result == 'refused' and isinstance(answer.reason, str):
            found = [f for f in answer.findings if isinstance(f, str)]
            return adapter._result('refused', 'lease',
                                   _filtered(found or ['lease: the lookup refused (%s)' % answer.reason]))
        return adapter._result('refused', 'lease', [_NO_TIED_LEASE])
    answer = adapter.violation(root, lease['task_id'], lease['fencing_token'], observation, event_id, recorder, now,
                               append=append, release=release)
    try:
        return _token_free(answer)
    except Exception as exc:  # TASK-070 AC1: the record may already be in the log and the store
        return adapter._result('refused', 'entry', ['entry: after the record: %s' % type(exc).__name__])


def session_violation(root, session_id, observation, event_id, recorder, now, lookup=None, append=None,
                      release=None):
    """Record a violation for the session tied by its session id to the one live lease of the store (TASK-070 AC1 to
    AC4): the lease's task and token are taken core-side and passed to adapter.violation; returns a mapping with
    adapter.RESULT_KEYS that holds no fencing token. No exception escapes."""
    try:
        return _session_violation(root, session_id, observation, event_id, recorder, now, lookup, append, release)
    except Exception as exc:  # TASK-070 AC1: a last guard
        return adapter._result('refused', 'entry', ['entry: %s' % type(exc).__name__])

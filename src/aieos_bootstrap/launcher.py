"""The launcher's core path of gov-AIEOS (task TASK-086; specification 7 revision 2, section 5; specification 5
revision 5, section 11 point 7; specification 3 revision 5, sections 1 and 2): start and end of one session over
adapter.start and adapter.end (TASK-051), callable by tests. It starts no runtime: no process but through gitread, no
hook placed, no setting changed; running `aieos launch` with a runtime stays the owner's (DM A51 item (4)).

``start(root, repo, task_id, adapter_name, max_risk, holder, recorder, now, expires_at, ...)`` returns a mapping with
exactly START_KEYS and never raises. In order (specification 7 :47's order without its first step):

1. The arguments: root an absolute path (a drive letter followed by ":/" or ":\\", or a leading "/"), repo checked by
   gitread.form_error with the HEAD read's form and TIMEOUT, task_id TASK-<digits>, adapter_name, holder and recorder
   non-empty strings, max_risk None or one of RISKS, now and expires_at timezone-aware UTC whole seconds with
   expires_at after now, every callee None or callable; a wrong one gives "refused" with reason "argument" and no
   callee called.
2. The core's expiry, expire(root, now) (writer.expire_leases): the core's expiry runs before a grant (specification
   5 :112).
3. HEAD, read once through read by gitread's fixed form; an answer that is not exactly 40 lowercase hex characters
   gives "refused". AIEOS_BASE is the head_commit read here; that it is the base branch's tip is not checked.
4. The log, read once by read_log(root), then execution.task_view over those bytes: its findings give "refused";
   then a task IN_PROGRESS (a lease still held after the expiry) gives "not granted" with reason "held", and any
   other state outside READY and REWORK gives "not granted" with reason "state"; all before adapter.start, with no
   session row opened and no end.
5. The session id, "launch-" followed by the first 32 hex characters of the SHA-256 of
   "<task_id> <now.isoformat()> <head_commit>".
6. The 22 inputs at HEAD: resume_inputs.git_inputs (ten), resume_log_inputs.log_inputs (seven), task_id, runtime
   {adapter, max_risk} (both the caller's) and task_view's log_seq, task_state and approved_contract_hash;
   code_sha256 the SHA-256 of src/aieos_bootstrap/resume_check.py's text at HEAD encoded as UTF-8 (base_files).
   A reader's findings give "refused" with no adapter.start call.
7. adapter.start, which opens the session row and runs execution.execute (the Resume Check, its record, its state
   effect and the grant on CONTINUE or CONTINUE_WITH).
8. When no fencing token was granted and the row was opened (adapter.start's reason neither "argument" nor
   "session"), adapter.end at once with no token: a start without a grant is ended at once (specification 5 :112).

On a grant the result's environment is {AIEOS_SESSION_ID, AIEOS_ROOT, AIEOS_BASE}, the names the hooks and the MCP
server read; on anything else it is None. ``end(root, task_id, session_id, fencing_token, now, ...)`` passes
adapter.end's result through. Every callee is a keyword argument whose default is taken at call time.

The rulings, each this task's choice (decisions D-2673, D-2675, D-2681):
- max_risk null never grants: the Resume Check's check 7 fires with "the runtime has no declaration", and the
  decision is the highest fired one by its ORDER. max_risk is the caller's: passing a tier declares the runtime's tier,
  which only the owner's measurement can back; the self-build passes null until then; tests pass a tier only to
  exercise the path.
- A dependency not DONE makes check 5 fire BLOCKED on the grant path (DEF-0099); a dependency's stale_evidence is
  checked for form only (DEF-0100).
- Each run, the log is read twice: once here, whose bytes go to task_view and log_inputs, and once by execute; a
  change between the reads gives execute's "inputs" refusal, which fails closed, as does a lease taken between
  task_view and execute.

Stated limits: it writes no observed read-set record. The observed read-set record before every lease release, at
its three call places (the normal end, the gone session's record at the end after a violation or an expiry, and at
the next start) and the stored reads' removal are TASK-089's, so launching with a runtime is not before TASK-089 lands
(a statement, not a lock; DEF-0101). As in adapter.py, the store is the caller's (writer.open_store). adapter.end
returns before the session row is closed when the release raises or is refused otherwise, so the row then stays open
for `aieos end`; a raising start_session gives "session" with the row possibly present and not ended. code_sha256 is
the hash of HEAD's resume_check.py, not of the imported module that runs. Two starts of one task in the same second
at the same HEAD make the same session id, and the second is refused "started". One run at a time (the writer's
limit); the expiry's result is not checked against the task; every limit of git_inputs, log_inputs, adapter.start and
execute holds here.

Purity: it opens no file, reads no clock and no environment, and starts no process but through gitread; __init__.py
is not changed.
"""

import datetime
import hashlib
import re

from aieos_bootstrap import adapter
from aieos_bootstrap import base_files
from aieos_bootstrap import execution
from aieos_bootstrap import gitread
from aieos_bootstrap import resume_check
from aieos_bootstrap import resume_inputs
from aieos_bootstrap import resume_log_inputs
from aieos_bootstrap import writer

START_KEYS = ('result', 'reason', 'findings', 'session_id', 'head_commit', 'decision', 'fencing_token', 'environment',
              'start', 'end')
TIMEOUT = 30
RISKS = ('low', 'medium', 'high', 'critical')
GRANT_STATES = ('READY', 'REWORK')
HEAD_ARGS = ('rev-parse', '--verify', '--end-of-options', 'HEAD')
RESUME_CHECK = 'src/aieos_bootstrap/resume_check.py'
SESSION_PREFIX = 'launch-'
OPENED_REFUSALS = ('argument', 'session')
_ROOT = re.compile(r'[A-Za-z]:[/\\].*|/.*', re.DOTALL)
_TASK = re.compile(r'TASK-[0-9]+')
_HEX40 = re.compile(r'[0-9a-f]{40}')
_ZERO = datetime.timedelta(0)
_CALLEES = ('read', 'read_log', 'expire', 'start', 'end', 'check', 'append', 'grant', 'release', 'held',
            'start_session', 'end_session', 'release_lease_token')


def _result(result, reason=None, findings=(), session_id=None, head_commit=None, decision=None, fencing_token=None,
            environment=None, started=None, ended=None):
    return {'result': result, 'reason': reason, 'findings': [f for f in findings if isinstance(f, str)],
            'session_id': session_id, 'head_commit': head_commit, 'decision': decision, 'fencing_token': fencing_token,
            'environment': environment, 'start': started, 'end': ended}


def _text(value):
    return isinstance(value, str) and value != ''


def _utc_whole(value):
    return (isinstance(value, datetime.datetime) and value.tzinfo is not None and value.utcoffset() == _ZERO
            and value.microsecond == 0)


def _argument_findings(root, repo, task_id, adapter_name, max_risk, holder, recorder, now, expires_at, callees):
    found = []
    if not (isinstance(root, str) and _ROOT.fullmatch(root) is not None):
        found.append('argument: root is not an absolute path')
    why = gitread.form_error(repo, list(HEAD_ARGS), TIMEOUT)
    if why is not None:
        found.append('argument: repo: %s' % why)
    if not (isinstance(task_id, str) and _TASK.fullmatch(task_id) is not None):
        found.append('argument: task_id is not TASK- followed by digits')
    for name, value in (('adapter_name', adapter_name), ('holder', holder), ('recorder', recorder)):
        if not _text(value):
            found.append('argument: %s is not a non-empty string' % name)
    if not (max_risk is None or (isinstance(max_risk, str) and max_risk in RISKS)):
        found.append('argument: max_risk is neither null nor one of low, medium, high and critical')
    times = True
    for name, value in (('now', now), ('expires_at', expires_at)):
        if not _utc_whole(value):
            found.append('argument: %s is not a timezone-aware datetime in UTC with whole seconds' % name)
            times = False
    if times and not expires_at > now:
        found.append('argument: expires_at is not after now')
    for name, value in zip(_CALLEES, callees):
        if value is not None and not callable(value):
            found.append('argument: %s is neither None nor callable' % name)
    return found


def _head(read, repo):
    """Step 3: the head_commit, or (None, findings)."""
    r = read(repo, list(HEAD_ARGS), TIMEOUT)
    if not (isinstance(r, dict) and r.get('error') is None and r.get('exit') == 0 and isinstance(r.get('out'), bytes)):
        return None, ['head: rev-parse HEAD gave no answer (%r)' % (r.get('error') if isinstance(r, dict) else r,)]
    try:
        head = r['out'].decode('ascii').strip()
    except UnicodeDecodeError:
        return None, ['head: rev-parse HEAD gave a non-ASCII answer']
    if _HEX40.fullmatch(head) is None:
        return None, ['head: rev-parse HEAD gave %r, not 40 lowercase hex characters' % head[:80]]
    return head, None


def session_id_of(task_id, now, head_commit):
    """Step 5: "launch-" followed by the first 32 hex characters of the SHA-256 of "<task_id> <now.isoformat()>
    <head_commit>"."""
    text = '%s %s %s' % (task_id, now.isoformat(), head_commit)
    return SESSION_PREFIX + hashlib.sha256(text.encode('utf-8')).hexdigest()[:32]


def _inputs(repo, head, task_id, log, read, adapter_name, max_risk, view):
    """Step 6: (the 22 inputs, code_sha256, None), or (None, None, findings)."""
    given, found = resume_inputs.git_inputs(repo, head, task_id, log, read)
    if found is not None:
        return None, None, ['inputs: git_inputs: %s' % f for f in found]
    logged, found = resume_log_inputs.log_inputs(repo, head, task_id, log, read)
    if found is not None:
        return None, None, ['inputs: log_inputs: %s' % f for f in found]
    code, found = base_files.read_file(repo, head, RESUME_CHECK, read)
    if found is not None:
        return None, None, ['inputs: %s: %s' % (RESUME_CHECK, f) for f in found]
    inputs = dict(given)
    inputs.update(logged)
    inputs.update({'task_id': task_id, 'runtime': {'adapter': adapter_name, 'max_risk': max_risk},
                   'log_seq': view['log_seq'], 'task_state': view['task_state'],
                   'approved_contract_hash': view['approved_contract_hash']})
    if set(inputs) != resume_check.INPUT_KEYS:
        return None, None, ['inputs: the keys are not resume_check.INPUT_KEYS']
    return inputs, hashlib.sha256(code['text'].encode('utf-8')).hexdigest(), None


def start(root, repo, task_id, adapter_name, max_risk, holder, recorder, now, expires_at, read=None, read_log=None,
          expire=None, start=None, end=None, check=None, append=None, grant=None, release=None, held=None,
          start_session=None, end_session=None, release_lease_token=None):
    """Start one session (TASK-086 AC1 to AC7): a mapping with exactly START_KEYS; never raises."""
    callees = (read, read_log, expire, start, end, check, append, grant, release, held, start_session, end_session,
               release_lease_token)
    try:
        found = _argument_findings(root, repo, task_id, adapter_name, max_risk, holder, recorder, now, expires_at,
                                   callees)
    except Exception as exc:  # AC1: an argument whose own methods raise
        found = ['argument: checking the arguments raised %s' % type(exc).__name__]
    if found:
        return _result('refused', 'argument', found)
    read = gitread.run if read is None else read
    read_log = writer.read_log if read_log is None else read_log
    expire = writer.expire_leases if expire is None else expire
    start = adapter.start if start is None else start
    end = adapter.end if end is None else end
    step = 'expire'
    head = session_id = None
    try:
        expired = expire(root, now)
        if not isinstance(expired, list):
            return _result('refused', 'expire', ['expire: expire_leases gave %s, not a list' % type(expired).__name__])
        step = 'head'
        head, found = _head(read, repo)
        if found:
            return _result('refused', 'head', found)
        step = 'log'
        log = read_log(root)
        if not isinstance(log, bytes):
            return _result('refused', 'log', ['log: read_log gave %s, not bytes' % type(log).__name__],
                           head_commit=head)
        step = 'view'
        view, found = execution.task_view(log, root, task_id, now, held=held)
        if found is not None:
            return _result('refused', 'view', found, head_commit=head)
        if view['task_state'] == 'IN_PROGRESS':
            return _result('not granted', 'held', ['held: a lease is held on %s after the expiry' % task_id],
                           head_commit=head)
        if view['task_state'] not in GRANT_STATES:
            return _result('not granted', 'state', ['state: %s is in %s' % (task_id, view['task_state'])],
                           head_commit=head)
        session_id = session_id_of(task_id, now, head)
        step = 'inputs'
        inputs, code_sha256, found = _inputs(repo, head, task_id, log, read, adapter_name, max_risk, view)
        if found:
            return _result('refused', 'inputs', found, session_id, head)
        step = 'start'
        started = start(root, task_id, session_id, holder, inputs, code_sha256, expires_at, recorder, now,
                        start_session=start_session, read_log=read_log, append=append, grant=grant, release=release,
                        held=held, check=check)
    except Exception as exc:  # AC7: no exception escapes; a raising step opens no row this module knows of
        return _result('refused', step, ['%s: a step raised %s' % (step, type(exc).__name__)], session_id, head)
    if not isinstance(started, dict):
        return _result('refused', 'start', ['start: adapter.start gave %s, not a mapping' % type(started).__name__],
                       session_id, head)
    decision = started.get('decision')
    token = started.get('fencing_token')
    if started.get('result') == 'done' and token is not None:
        environment = {'AIEOS_SESSION_ID': session_id, 'AIEOS_ROOT': root, 'AIEOS_BASE': head}
        return _result('granted', None, [], session_id, head, decision, token, environment, started)
    reason = started.get('reason')
    findings = list(started.get('findings') or [])
    if started.get('result') != 'done' and reason in OPENED_REFUSALS:
        return _result('refused', reason, findings, session_id, head, decision, started=started)
    try:
        ended = end(root, task_id, session_id, None, now, release_lease_token=release_lease_token,
                    end_session=end_session)
    except Exception as exc:  # AC7
        return _result('refused', 'end', findings + ['end: adapter.end raised %s' % type(exc).__name__], session_id,
                       head, decision, started=started)
    if not (isinstance(ended, dict) and ended.get('result') == 'done'):
        more = list(ended.get('findings') or []) if isinstance(ended, dict) else []
        return _result('refused', 'end', findings + ['end: adapter.end did not end the session'] + more, session_id,
                       head, decision, started=started, ended=ended)
    if started.get('result') != 'done':
        return _result('refused', reason, findings, session_id, head, decision, started=started, ended=ended)
    return _result('not granted', 'decision', ['decision: %r granted no lease' % (decision,)], session_id, head,
                   decision, started=started, ended=ended)


def end(root, task_id, session_id, fencing_token, now, release_lease_token=None, end_session=None):
    """End one session (TASK-086 AC8): adapter.end's result, passed through; never raises."""
    try:
        return adapter.end(root, task_id, session_id, fencing_token, now, release_lease_token=release_lease_token,
                           end_session=end_session)
    except Exception as exc:  # adapter.end catches its own, so this is a last guard
        result = dict.fromkeys(adapter.RESULT_KEYS)
        result.update({'result': 'refused', 'reason': 'end', 'findings': ['end: adapter.end raised %s'
                                                                         % type(exc).__name__]})
        return result

"""The launcher's core path of gov-AIEOS (task TASK-086; specification 7 revision 2, section 5; specification 5
revision 5, section 11 point 7; specification 3 revision 5, sections 1 and 2): start and end of one session over
adapter.start and adapter.end (TASK-051), callable by tests. It starts no runtime: no process but through gitread, no
hook placed, no setting changed; running `aieos launch` with a runtime stays the owner's (DM A51 item (4)).

``start(root, repo, task_id, adapter_name, max_risk, holder, recorder, now, expires_at, ...)`` returns a mapping with
exactly START_KEYS and never raises. In order (specification 7 :47's order: the gone sessions' records, then the
expiry, then the Resume Check, then the grant):

1. The arguments: root an absolute path (a drive letter followed by ":/" or ":\\", or a leading "/"), repo checked by
   gitread.form_error with the HEAD read's form and TIMEOUT, task_id TASK-<digits>, adapter_name, holder and recorder
   non-empty strings, max_risk None or one of RISKS, now and expires_at timezone-aware UTC whole seconds with
   expires_at after now, every callee None or callable; a wrong one gives "refused" with reason "argument" and no
   callee called.
1a. The gone sessions' records, before the expiry (task TASK-090; specification 5 section 11 point 10; specification
   7 :47): read_sessions(root, task_id) lists the sessions that hold stored reads for the task; for each, in order,
   session_leases(root, session_id, now) is read once and the session is skipped when any of its rows is unexpired at
   now, whatever the row's task and whatever "ended" says (a session whose lease row is still unexpired is not
   processed); otherwise stored_reads, then read_set_record.observe_gone with 'lease gone (released or expired)' and
   the recorder followed by " at the next start, for session " and the session id, as the core's own observation with
   no fencing token, written even when no read is stored; then remove_reads once the record is found present. Every
   outcome is a "gone_records: <session_id>: " line (the listing's own lines name the task), put first in the findings
   of every result after the arguments; a failure ends that session only, and start goes on.
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
server read; on anything else it is None. Every callee is a keyword argument whose default is taken at call time.

``end(root, task_id, session_id, fencing_token, now, write_set, allowlist, recorder, violation=False, ...)`` (task
TASK-089; specification 5 section 11 points 7 and 10; specification 7 section 5) returns a mapping with exactly
END_KEYS and never raises. It writes the session's observed read-set record and removes the stored reads before
adapter.end, the record before the release, and passes adapter.end's result in "end". In order:

1. The arguments: root an absolute Windows path (claude_code_channel.context_findings' form), task_id TASK-<digits>,
   session_id a non-empty string, fencing_token None or a mapping (its form is adapter.end's to check), now UTC whole
   seconds, violation a bool, every callee None or callable; a wrong one gives "refused" with reason "argument".
2. The path, by the session's own lease rows, read once by session_leases(root, session_id, now), every row of the
   session counting, whatever its task: "fenced" when the session has at least one row unexpired at now and every
   such row is the task's and holds a fencing_token equal to the given one; "held" when the session has any other row
   unexpired at now, which is refused with nothing written, nothing removed and no adapter.end; otherwise "gone". A
   refused or malformed answer gives "refused" with reason "lease_rows" and nothing done. violation only picks the
   gone path's reason: "violation", else "no fencing token given" when the token is None, else "lease gone (released
   or expired)".
3. The stored reads, read once by stored_reads(root, session_id, task_id).
4. The record: on "fenced", read_set_record.observe with the context {root, task_id, session_id, fencing_token,
   write_set, allowlist, recorder}; on "gone", read_set_record.observe_gone, as the core's own observation with no
   fencing token. The record is written even when no read is stored.
5. Once the record is found present ("written", "duplicate", or "refused" with core reason "conflict", its event id
   already holding a record), remove_reads(root, session_id, task_id); a refused or raising removal is named in the
   findings.
6. adapter.end(root, task_id, session_id, fencing_token, now, ...), its result passed in "end"; the result is "done"
   when it gave "done".

Failing closed: a refusal or a raise before the record, a "held" path, or a fenced record not found present gives
"refused" with no removal and no adapter.end, so no lease is released before its record; a gone record not found
present gives no removal, and adapter.end is still called, since no row of the session is unexpired.

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

Stated limits: the observed read-set record is written at four call places: end writes it at the normal end and for the
gone session at the end after a violation or an expiry, with the reads' removal (TASK-089), start's step 1a writes it at
the next start, before the expiry, for a session gone with no end (TASK-090), and end_outside for `aieos end`; launching
with a runtime is not before DEF-0101's open points are closed: the base-tip check, check 0 and max_risk (a statement,
not a lock). Step 1a's limits: with no later start of the task no record is written; a gone session that
stored no read is never listed; now is the caller's, so a now later than the real time reads a live lease as expired;
it writes records and removes reads even when start then refuses or does not grant; a session that can never be
processed keeps its reads and gives its line at every start; a project with no store gives a line at each start; the
listing, the rows and the reads are read at separate moments. end's limits: on the fail-closed paths the
session stays open, its lease held until it expires, for the next start or `aieos end`; a "held" session stays open
until expiry or end is called with its token, or `aieos end` ends it; a token mapping out of the store's form is checked
only by adapter.end, so on the gone path the record is written and the reads removed before adapter.end refuses it;
the lease rows are read at one moment, so a lease expiring before observe makes its fenced append refused; a record
found present as a conflict is the earlier record, so reads added after it are in no record and are removed with the
rest; write_set, allowlist and recorder are the caller's, checked only by observe's context check. As in adapter.py,
the store is the caller's (writer.open_store). adapter.end
returns before the session row is closed when the release raises or is refused otherwise, so the row then stays open
for `aieos end`; a raising start_session gives "session" with the row possibly present and not ended. code_sha256 is
the hash of HEAD's resume_check.py, not of the imported module that runs. Two starts of one task in the same second
at the same HEAD make the same session id, and the second is refused "started". One run at a time (the writer's
limit); the expiry's result is not checked against the task; every limit of git_inputs, log_inputs, adapter.start and
execute holds here.

Purity: it opens no file, reads no clock and no environment, and starts no process but through gitread; __init__.py
is not changed.

end_outside (task TASK-092; `aieos end <session>`, specification 7 :33, :48; specification 5 :112, :119) ends a
crashed session from outside the runtime and returns a mapping with exactly OUTSIDE_KEYS; it never raises. Its steps,
each step's name being the reason of a refusal or a raise at it: argument; lease_rows (the session's rows read once,
in _path's form with the task_id checked); ended; then for each distinct task of the rows, in str sorted order,
stored_reads, record (observe_gone with 'no fencing token given' and the recorder followed by " outside the runtime,
for session ", the session id and ", its lease row possibly unexpired") and the stored reads' removal, whose failure
is named and does not stop the steps; then end (writer.end_session, which releases every lease of the session). It is
the record before the release: a refusal or a raise before every task's record is present ends nothing, so no lease
is released before its record. Its limits: it departs from specification 5 :125's "a session whose lease row is
still unexpired is not processed" (D-3047 (c1)), the recorder naming the possibly unexpired row; an expired row also
gets "no fencing token given"; a session with no lease row left gets no record; the rows, the reads, the records and
the end are read and written at separate moments, so a lease added to the session between them is released with no
record (a finding names it); a refusal before the end leaves the session open until its leases expire.

init_project (task TASK-095; `aieos init`, specification 7 :28) calls writer.init_layout once, looked up at call
time, and returns a mapping with exactly INIT_KEYS; it never raises. An answer is in form only as a writer.StoreResult
that is "done" with reason None, no findings and a non-empty tuple of str, or "refused" with a str reason and a tuple
of str findings; any other answer, or a raise, gives reason "init_layout". It creates nothing itself; the folders are
the writer's.

launch_outside (task TASK-094; `aieos launch`, specification 7 :34-35, sections 5 and 7) composes one launch from
outside the runtime and returns a mapping with exactly LAUNCH_KEYS; it never raises an Exception. It calls start with
max_risk None, so it grants nothing until a measured tier backs a declaration; on a grant it reads the contract's write
set by base_inputs.contract_at at the grant's head, calls the caller's starter with a copy of the environment, ends the
session in every case after a grant (end, or end_outside where end cannot take the session: launch_outside is a second
caller of end_outside beside `aieos end`), and writes the handoff file by handoff_file.write, with commit None, after
an end that gave "done". The shipped command passes no starter, so it starts no runtime. launch_outside reads the
caller's clock twice and calls the caller's starter, the two exceptions to "reads no clock" and "starts no process but
through gitread" above: the starter does whatever the caller's code does; the core's own code starts no process. A
BaseException from the starter is re-raised after the end and the handoff.

approval_act (task TASK-096; `aieos approve`, `aieos edit` and `aieos reject`, specification 1 section 12,
specification 7 section 4) records an approval, a rejection or an edit note of a task's drafted contract version and
returns a mapping with exactly APPROVAL_KEYS; it never raises an Exception. It writes through writer.append_event only:
for approve a contract-kind authority record (approval_binding kind contract, no outcome) and then task.approved citing
it; for reject the same binding with outcome fail and no state event; for edit a claim marked contract_edit, holding the
note as text, and no state event. It writes no acceptance-kind approval, so nothing it writes is counted by the
governor at acceptance. It reads the contract at HEAD through start's own reader, _head; that HEAD is the base
branch's tip is not checked (DEF-0101's base-tip check, open), and the check that the contract equals the last drafted
version binds the approval to the drafted text whatever HEAD is. The source class and the name are the caller's
statement, not checked. approval_act reads the caller's clock once, an exception to "reads no clock" above.
"""

import datetime
import hashlib
import re

from aieos_bootstrap import adapter
from aieos_bootstrap import base_files
from aieos_bootstrap import base_inputs
from aieos_bootstrap import execution
from aieos_bootstrap import gitread
from aieos_bootstrap import handoff_file
from aieos_bootstrap import read_set_record
from aieos_bootstrap import records
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
END_KEYS = ('result', 'reason', 'findings', 'path', 'record', 'removed', 'end')
END_REASONS = ('argument', 'lease_rows', 'held', 'stored_reads', 'record', 'end')
FOUND_PRESENT = ('written', 'duplicate')
_ROOT = re.compile(r'[A-Za-z]:[/\\].*|/.*', re.DOTALL)
_TASK = re.compile(r'TASK-[0-9]+')
_HEX40 = re.compile(r'[0-9a-f]{40}')
_ZERO = datetime.timedelta(0)
_CALLEES = ('read', 'read_log', 'expire', 'start', 'end', 'check', 'append', 'grant', 'release', 'held',
            'start_session', 'end_session', 'release_lease_token', 'read_sessions', 'session_leases', 'stored_reads',
            'remove_reads', 'observe_gone')
_GONE_FOR = ' at the next start, for session '


def _result(result, reason=None, findings=(), session_id=None, head_commit=None, decision=None, fencing_token=None,
            environment=None, started=None, ended=None, gone=()):
    return {'result': result, 'reason': reason, 'findings': [f for f in tuple(gone) + tuple(findings)
                                                             if isinstance(f, str)],
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


def _gone_session(root, task_id, session_id, now, recorder, session_leases, stored_reads, remove_reads,
                  observe_gone):
    """Step 1a for one listed session (TASK-090 AC4 to AC6): its "gone_records: <session_id>: " lines. _path,
    _present, _conflict and _store_findings are end's; the stored_reads check and the removal are a small stated
    parallel of end's. A raise names the call in progress and keeps the lines already built (TASK-090 AC5)."""
    head = 'gone_records: %s: ' % session_id
    lines = []
    call = 'session_leases'
    try:
        path, found = _path(session_leases(root, session_id, now), task_id, None, now)
        if found:
            return [head + f for f in found]
        if path != 'gone':
            return [head + 'skipped, a lease row is unexpired']
        call = 'stored_reads'
        got = stored_reads(root, session_id, task_id)
        reads = getattr(got, 'value', None)
        if getattr(got, 'result', None) != 'done' or not isinstance(reads, list):
            return [head + f for f in _store_findings('stored_reads', got)]
        call = 'observe_gone'
        record = observe_gone(root, task_id, session_id, list(reads), read_set_record.GONE_WHY[1], now,
                              recorder + _GONE_FOR + session_id)
        if not _present(record):
            given = record.get('findings') if isinstance(record, dict) else None
            more = [f for f in given if isinstance(f, str)] if isinstance(given, list) else []
            return [head + f for f in ['record: the record was not found present'] + more]
        if _conflict(record):
            lines.append(head + 'record: a record is already present under its event id (conflict)')
        lines.append(head + 'record %s' % record['result'])
        call = 'remove_reads'
        removed = remove_reads(root, session_id, task_id)
        if getattr(removed, 'result', None) != 'done':
            return lines + [head + f for f in _store_findings('remove_reads', removed)]
        return lines[:-1] + [head + 'record %s, %r reads removed' % (record['result'],
                                                                    getattr(removed, 'value', None))]
    except Exception as exc:  # AC5: the callee in progress named, the lines already built kept
        return lines + [head + '%s: a step raised %s' % (call, type(exc).__name__)]


def _gone_records(root, task_id, now, recorder, read_sessions, session_leases, stored_reads, remove_reads,
                  observe_gone):
    """Step 1a (TASK-090 AC4 to AC6): the gone sessions' records before the expiry, as "gone_records: " lines; a
    failure ends its session only; never raises."""
    head = 'gone_records: %s: ' % task_id
    try:
        listing = read_sessions(root, task_id)
        if getattr(listing, 'result', None) != 'done':
            return [head + f for f in _store_findings('read_sessions', listing)]
        ids = getattr(listing, 'value', None)
        if not (isinstance(ids, list) and all(_text(i) for i in ids)):
            return [head + 'read_sessions gave a value that is not a list of non-empty strings']
    except Exception as exc:  # AC5: a failing listing ends the step only
        return [head + 'read_sessions raised %s' % type(exc).__name__]
    lines = []
    for session_id in ids:
        try:
            lines.extend(_gone_session(root, task_id, session_id, now, recorder, session_leases, stored_reads,
                                       remove_reads, observe_gone))
        except Exception as exc:  # AC5: a failing session ends that session only
            lines.append('gone_records: %s: a step raised %s' % (session_id, type(exc).__name__))
    return lines


def start(root, repo, task_id, adapter_name, max_risk, holder, recorder, now, expires_at, read=None, read_log=None,
          expire=None, start=None, end=None, check=None, append=None, grant=None, release=None, held=None,
          start_session=None, end_session=None, release_lease_token=None, read_sessions=None, session_leases=None,
          stored_reads=None, remove_reads=None, observe_gone=None):
    """Start one session (TASK-086 AC1 to AC7; TASK-090 AC3 to AC6): a mapping with exactly START_KEYS; never
    raises."""
    callees = (read, read_log, expire, start, end, check, append, grant, release, held, start_session, end_session,
               release_lease_token, read_sessions, session_leases, stored_reads, remove_reads, observe_gone)
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
    read_sessions = writer.read_sessions if read_sessions is None else read_sessions
    session_leases = writer.session_leases if session_leases is None else session_leases
    stored_reads = writer.stored_reads if stored_reads is None else stored_reads
    remove_reads = writer.remove_reads if remove_reads is None else remove_reads
    observe_gone = read_set_record.observe_gone if observe_gone is None else observe_gone
    try:
        gone = _gone_records(root, task_id, now, recorder, read_sessions, session_leases, stored_reads, remove_reads,
                             observe_gone)
    except Exception as exc:  # AC5: the step never stops start
        gone = ['gone_records: %s: the step raised %s' % (task_id, type(exc).__name__)]
    step = 'expire'
    head = session_id = None
    try:
        expired = expire(root, now)
        if not isinstance(expired, list):
            return _result('refused', 'expire', ['expire: expire_leases gave %s, not a list' % type(expired).__name__],
                           gone=gone)
        step = 'head'
        head, found = _head(read, repo)
        if found:
            return _result('refused', 'head', found, gone=gone)
        step = 'log'
        log = read_log(root)
        if not isinstance(log, bytes):
            return _result('refused', 'log', ['log: read_log gave %s, not bytes' % type(log).__name__],
                           head_commit=head, gone=gone)
        step = 'view'
        view, found = execution.task_view(log, root, task_id, now, held=held)
        if found is not None:
            return _result('refused', 'view', found, head_commit=head, gone=gone)
        if view['task_state'] == 'IN_PROGRESS':
            return _result('not granted', 'held', ['held: a lease is held on %s after the expiry' % task_id],
                           head_commit=head, gone=gone)
        if view['task_state'] not in GRANT_STATES:
            return _result('not granted', 'state', ['state: %s is in %s' % (task_id, view['task_state'])],
                           head_commit=head, gone=gone)
        session_id = session_id_of(task_id, now, head)
        step = 'inputs'
        inputs, code_sha256, found = _inputs(repo, head, task_id, log, read, adapter_name, max_risk, view)
        if found:
            return _result('refused', 'inputs', found, session_id, head, gone=gone)
        step = 'start'
        started = start(root, task_id, session_id, holder, inputs, code_sha256, expires_at, recorder, now,
                        start_session=start_session, read_log=read_log, append=append, grant=grant, release=release,
                        held=held, check=check)
    except Exception as exc:  # AC7: no exception escapes; a raising step opens no row this module knows of
        return _result('refused', step, ['%s: a step raised %s' % (step, type(exc).__name__)], session_id, head,
                       gone=gone)
    if not isinstance(started, dict):
        return _result('refused', 'start', ['start: adapter.start gave %s, not a mapping' % type(started).__name__],
                       session_id, head, gone=gone)
    decision = started.get('decision')
    token = started.get('fencing_token')
    if started.get('result') == 'done' and token is not None:
        environment = {'AIEOS_SESSION_ID': session_id, 'AIEOS_ROOT': root, 'AIEOS_BASE': head}
        return _result('granted', None, [], session_id, head, decision, token, environment, started, gone=gone)
    reason = started.get('reason')
    given = started.get('findings')
    findings = [f for f in given if isinstance(f, str)] if isinstance(given, (list, tuple)) else []
    if started.get('result') != 'done' and reason in OPENED_REFUSALS:
        return _result('refused', reason, findings, session_id, head, decision, started=started, gone=gone)
    try:
        ended = end(root, task_id, session_id, None, now, release_lease_token=release_lease_token,
                    end_session=end_session)
    except Exception as exc:  # AC7
        return _result('refused', 'end', findings + ['end: adapter.end raised %s' % type(exc).__name__], session_id,
                       head, decision, started=started, gone=gone)
    if not (isinstance(ended, dict) and ended.get('result') == 'done'):
        given = ended.get('findings') if isinstance(ended, dict) else None
        more = [f for f in given if isinstance(f, str)] if isinstance(given, (list, tuple)) else []
        return _result('refused', 'end', findings + ['end: adapter.end did not end the session'] + more, session_id,
                       head, decision, started=started, ended=ended, gone=gone)
    if started.get('result') != 'done':
        return _result('refused', reason, findings, session_id, head, decision, started=started, ended=ended,
                       gone=gone)
    return _result('not granted', 'decision', ['decision: %r granted no lease' % (decision,)], session_id, head,
                   decision, started=started, ended=ended, gone=gone)


# ---- end (task TASK-089) ----

_WINDOWS_ROOT = re.compile(r'[A-Za-z]:[/\\].*', re.DOTALL)
_ROW_KEYS = frozenset({'task_id', 'fencing_token', 'expires_at'})
_END_CALLEES = ('release_lease_token', 'end_session', 'session_leases', 'stored_reads', 'remove_reads', 'observe',
                'observe_gone')


def _end_result(result, reason=None, findings=(), path=None, record=None, removed=None, ended=None):
    return {'result': result, 'reason': reason, 'findings': [f for f in findings if isinstance(f, str)], 'path': path,
            'record': record, 'removed': removed, 'end': ended}


def _end_argument_findings(root, task_id, session_id, fencing_token, now, violation, callees):
    found = []
    if not (isinstance(root, str) and _WINDOWS_ROOT.fullmatch(root) is not None):
        found.append('argument: root is not an absolute Windows path')
    if not (isinstance(task_id, str) and _TASK.fullmatch(task_id) is not None):
        found.append('argument: task_id is not TASK- followed by digits')
    if not _text(session_id):
        found.append('argument: session_id is not a non-empty string')
    if not (fencing_token is None or isinstance(fencing_token, dict)):
        found.append('argument: fencing_token is neither None nor a mapping')
    if not _utc_whole(now):
        found.append('argument: now is not a timezone-aware datetime in UTC with whole seconds')
    if type(violation) is not bool:
        found.append('argument: violation is not a bool')
    for name, value in zip(_END_CALLEES, callees):
        if value is not None and not callable(value):
            found.append('argument: %s is neither None nor callable' % name)
    return found


def _store_findings(name, answer):
    given = getattr(answer, 'findings', None)
    more = [f for f in given if isinstance(f, str)] if isinstance(given, (list, tuple)) else []
    head = '%s: %s gave %r (%r)' % (name, name, getattr(answer, 'result', None), getattr(answer, 'reason', None))
    return [head] + more


def _aware(value):
    return isinstance(value, datetime.datetime) and value.tzinfo is not None and value.utcoffset() == _ZERO


def _path(answer, task_id, fencing_token, now):
    """Step 2: ("fenced" | "held" | "gone", None), or (None, findings) for a refused or malformed answer."""
    if getattr(answer, 'result', None) != 'done':
        return None, _store_findings('session_leases', answer)
    value = getattr(answer, 'value', None)
    if not (isinstance(value, dict) and set(value) == {'ended', 'leases'} and type(value['ended']) is bool
            and isinstance(value['leases'], list)):
        return None, ['lease_rows: session_leases gave a value that is not {ended: a bool, leases: a list}']
    for row in value['leases']:
        if not (isinstance(row, dict) and set(row) == _ROW_KEYS and _aware(row['expires_at'])):
            return None, ['lease_rows: a lease row is not a mapping of task_id, fencing_token and a UTC expires_at']
    unexpired = [row for row in value['leases'] if row['expires_at'] > now]
    if not unexpired:
        return 'gone', None
    if fencing_token is not None and all(row['task_id'] == task_id and row['fencing_token'] == fencing_token
                                         for row in unexpired):
        return 'fenced', None
    return 'held', None


def _gone_reason(violation, fencing_token):
    if violation:
        return read_set_record.GONE_WHY[0]
    if fencing_token is None:
        return read_set_record.GONE_WHY[2]
    return read_set_record.GONE_WHY[1]


def _conflict(record):
    core = record.get('core')
    return (record.get('result') == 'refused' and record.get('reason') == 'core' and isinstance(core, dict)
            and core.get('result') == 'refused' and core.get('reason') == 'conflict')


def _present(record):
    """Step 5's test: the record is found present when written, a duplicate, or a core "conflict"."""
    return isinstance(record, dict) and (record.get('result') in FOUND_PRESENT or _conflict(record))


def end(root, task_id, session_id, fencing_token, now, write_set, allowlist, recorder, violation=False,
        release_lease_token=None, end_session=None, session_leases=None, stored_reads=None, remove_reads=None,
        observe=None, observe_gone=None):
    """End one session (TASK-089 AC1 to AC7; TASK-086 AC8): the record before the release, then the stored reads'
    removal, then adapter.end; a mapping with exactly END_KEYS; never raises."""
    callees = (release_lease_token, end_session, session_leases, stored_reads, remove_reads, observe, observe_gone)
    try:
        found = _end_argument_findings(root, task_id, session_id, fencing_token, now, violation, callees)
    except Exception as exc:  # AC1: an argument whose own methods raise
        found = ['argument: checking the arguments raised %s' % type(exc).__name__]
    if found:
        return _end_result('refused', 'argument', found)
    session_leases = writer.session_leases if session_leases is None else session_leases
    stored_reads = writer.stored_reads if stored_reads is None else stored_reads
    remove_reads = writer.remove_reads if remove_reads is None else remove_reads
    observe = read_set_record.observe if observe is None else observe
    observe_gone = read_set_record.observe_gone if observe_gone is None else observe_gone
    step = 'lease_rows'
    path = None
    try:
        path, found = _path(session_leases(root, session_id, now), task_id, fencing_token, now)
        if found:
            return _end_result('refused', 'lease_rows', found)
        if path == 'held':
            return _end_result('refused', 'held', ['held: the session has an unexpired lease row that is not the '
                                                   "task's own with the given token"])
        step = 'stored_reads'
        got = stored_reads(root, session_id, task_id)
        reads = getattr(got, 'value', None)
        if getattr(got, 'result', None) != 'done' or not isinstance(reads, list):
            return _end_result('refused', 'stored_reads', _store_findings('stored_reads', got), path)
        step = 'record'
        if path == 'fenced':
            context = {'root': root, 'task_id': task_id, 'session_id': session_id, 'fencing_token': fencing_token,
                       'write_set': write_set, 'allowlist': allowlist, 'recorder': recorder}
            record = observe(context, list(reads), now)
        else:
            record = observe_gone(root, task_id, session_id, list(reads), _gone_reason(violation, fencing_token), now,
                                  recorder)
    except Exception as exc:  # AC7: a raise before the record writes nothing more and releases nothing
        if not (step == 'record' and path == 'gone'):
            return _end_result('refused', step, ['%s: a step raised %s' % (step, type(exc).__name__)], path)
        # AC7: on the gone path no unexpired row of the session is held, so adapter.end still follows
        record = None
        findings = ['record: observe_gone raised %s' % type(exc).__name__]
    else:
        findings = []
    removed = None
    if _present(record):
        if _conflict(record):
            findings.append('record: a record is already present under its event id (conflict)')
        try:
            r = remove_reads(root, session_id, task_id)
            if getattr(r, 'result', None) == 'done':
                removed = getattr(r, 'value', None)
            else:
                findings.extend(_store_findings('remove_reads', r))
        except Exception as exc:  # AC7: the record is present, so adapter.end still follows
            findings.append('remove_reads: remove_reads raised %s' % type(exc).__name__)
    else:
        given = record.get('findings') if isinstance(record, dict) else None
        more = [f for f in given if isinstance(f, str)] if isinstance(given, list) else []
        findings = findings + ['record: the record was not found present'] + more
        if path == 'fenced':
            return _end_result('refused', 'record', findings, path, record)
    try:
        ended = adapter.end(root, task_id, session_id, fencing_token, now, release_lease_token=release_lease_token,
                            end_session=end_session)
    except Exception as exc:  # adapter.end catches its own, so this is a last guard
        return _end_result('refused', 'end', findings + ['end: adapter.end raised %s' % type(exc).__name__], path,
                           record, removed)
    if isinstance(ended, dict) and ended.get('result') == 'done':
        return _end_result('done', None, findings, path, record, removed, ended)
    given = ended.get('findings') if isinstance(ended, dict) else None
    more = [f for f in given if isinstance(f, str)] if isinstance(given, list) else []
    return _end_result('refused', 'end', findings + ['end: adapter.end did not end the session'] + more, path, record,
                       removed, ended)


# ---- end_outside, `aieos end` (task TASK-092) ----

OUTSIDE_KEYS = ('result', 'reason', 'findings', 'records', 'released')
_OUTSIDE_FOR = ' outside the runtime, for session '
_OUTSIDE_TAIL = ', its lease row possibly unexpired'
_OUTSIDE_CALLEES = ('session_leases', 'stored_reads', 'remove_reads', 'observe_gone', 'end_session')


def _outside_result(result, reason=None, findings=(), records=(), released=()):
    return {'result': result, 'reason': reason, 'findings': [f for f in findings if isinstance(f, str)],
            'records': [r for r in records if isinstance(r, str)],
            'released': [t for t in released if isinstance(t, str)] if result == 'done' else []}


def _outside_argument_findings(root, session_id, now, recorder, callees):
    found = []
    if not (isinstance(root, str) and _ROOT.fullmatch(root) is not None):
        found.append('argument: root is not an absolute path')
    if not _text(session_id):
        found.append('argument: session_id is not a non-empty string')
    if not _utc_whole(now):
        found.append('argument: now is not a timezone-aware datetime in UTC with whole seconds')
    if not _text(recorder):
        found.append('argument: recorder is not a non-empty string')
    for name, value in zip(_OUTSIDE_CALLEES, callees):
        if value is not None and not callable(value):
            found.append('argument: %s is neither None nor callable' % name)
    return found


def _outside_store(head, name, answer):
    """A store refusal's findings: the own line "<head><name> gave <result> (<reason>)", then the callee's own."""
    given = getattr(answer, 'findings', None)
    more = [f for f in given if isinstance(f, str)] if isinstance(given, (list, tuple)) else []
    return ['%s%s gave %r (%r)' % (head, name, getattr(answer, 'result', None), getattr(answer, 'reason', None))] + more


def _outside_rows(answer):
    """Step 2: (the value, None), or (None, findings) for a refused or malformed answer; _path's form check with the
    task_id check added."""
    if getattr(answer, 'result', None) != 'done':
        return None, _outside_store('lease_rows: ', 'session_leases', answer)
    value = getattr(answer, 'value', None)
    if not (isinstance(value, dict) and set(value) == {'ended', 'leases'} and type(value['ended']) is bool
            and isinstance(value['leases'], list)):
        return None, ['lease_rows: session_leases gave a value that is not {ended: a bool, leases: a list}']
    for row in value['leases']:
        if not (isinstance(row, dict) and set(row) == _ROW_KEYS and _aware(row['expires_at'])
                and isinstance(row['task_id'], str) and _TASK.fullmatch(row['task_id']) is not None):
            return None, ['lease_rows: a lease row is not a mapping of a task_id (TASK- followed by digits), '
                          'fencing_token and a UTC expires_at']
    return value, None


def _outside_released(value):
    """Step 4: the released leases' task ids, or None when the value is out of form."""
    if not isinstance(value, list):
        return None
    ids = []
    for lease in value:
        if not (isinstance(lease, dict) and isinstance(lease.get('task_id'), str)):
            return None
        ids.append(lease['task_id'])
    return ids


def end_outside(root, session_id, now, recorder, session_leases=None, stored_reads=None, remove_reads=None,
                observe_gone=None, end_session=None):
    """End a crashed session from outside the runtime (TASK-092 AC1 to AC3; `aieos end`, specification 7 :33, :48):
    for each task among the session's lease rows, the record before the release, then the stored reads' removal; then
    writer.end_session, which releases every lease of the session; no lease is released before its record. A
    mapping with exactly OUTSIDE_KEYS; never raises."""
    findings, records = [], []
    step, head = 'argument', ''
    try:
        callees = (session_leases, stored_reads, remove_reads, observe_gone, end_session)
        try:
            found = _outside_argument_findings(root, session_id, now, recorder, callees)
        except Exception as exc:  # AC1: an argument whose own methods raise
            found = ['argument: checking the arguments raised %s' % type(exc).__name__]
        if found:
            return _outside_result('refused', 'argument', found)
        session_leases = writer.session_leases if session_leases is None else session_leases
        stored_reads = writer.stored_reads if stored_reads is None else stored_reads
        remove_reads = writer.remove_reads if remove_reads is None else remove_reads
        observe_gone = read_set_record.observe_gone if observe_gone is None else observe_gone
        end_session = writer.end_session if end_session is None else end_session
        step = 'lease_rows'
        value, found = _outside_rows(session_leases(root, session_id, now))
        if found:
            return _outside_result('refused', 'lease_rows', found)
        if value['ended']:
            return _outside_result('refused', 'ended', ['ended: the session is already ended'])
        tasks = sorted(set(row['task_id'] for row in value['leases']))
        for task_id in tasks:
            head = task_id + ': '
            step = 'stored_reads'
            got = stored_reads(root, session_id, task_id)
            reads = getattr(got, 'value', None)
            if getattr(got, 'result', None) != 'done' or not isinstance(reads, list):
                return _outside_result('refused', 'stored_reads',
                                       findings + _outside_store(head + 'stored_reads: ', 'stored_reads', got),
                                       records)
            step = 'record'
            record = observe_gone(root, task_id, session_id, list(reads), read_set_record.GONE_WHY[2], now,
                                  recorder + _OUTSIDE_FOR + session_id + _OUTSIDE_TAIL)
            if not _present(record):
                given = record.get('findings') if isinstance(record, dict) else None
                more = [f for f in given if isinstance(f, str)] if isinstance(given, list) else []
                return _outside_result('refused', 'record',
                                       findings + [head + 'record: the record was not found present'] + more, records)
            if _conflict(record):
                kind = 'conflict (present)'
                findings.append(head + 'record: a record is already present under its event id (conflict)')
            else:
                kind = record['result']
            try:
                r = remove_reads(root, session_id, task_id)
                if getattr(r, 'result', None) == 'done':
                    records.append('%srecord %s, %r reads removed' % (head, kind, getattr(r, 'value', None)))
                else:
                    findings.extend(_outside_store(head + 'remove_reads: ', 'remove_reads', r))
                    records.append('%srecord %s, reads not removed' % (head, kind))
            except Exception as exc:  # AC3: the record is present, so the steps go on
                findings.append('%sremove_reads: a step raised %s' % (head, type(exc).__name__))
                records.append('%srecord %s, reads not removed' % (head, kind))
        step, head = 'end', ''
        try:
            ended = end_session(root, session_id, now)
        except Exception as exc:  # AC3: the end may have committed before the raise
            return _outside_result('refused', 'end', findings + ['end: a step raised %s; the session may be ended'
                                                                 % type(exc).__name__], records)
        if getattr(ended, 'result', None) != 'done':
            return _outside_result('refused', 'end', findings + _outside_store('end: ', 'end_session', ended), records)
        released = _outside_released(getattr(ended, 'value', None))
        if released is None:
            return _outside_result('done', None, findings + ["end: end_session's value is out of form"], records)
        for task_id in released:
            if task_id not in tasks:
                findings.append('end: %s released with no record (it was not among the rows read)' % task_id)
        return _outside_result('done', None, findings, records, released)
    except Exception as exc:  # AC3: a raise names its step and keeps the records lines already made
        text = '%s%s: a step raised %s' % (head, step, type(exc).__name__)
        try:
            return _outside_result('refused', step, findings + [text], records)
        except Exception:  # the result's building raised: the step and its line only
            return {'result': 'refused', 'reason': step, 'findings': [text], 'records': [], 'released': []}


# ---- init_project, `aieos init` (task TASK-095) ----

INIT_KEYS = ('result', 'reason', 'findings', 'created')
_INIT_PROJECT_OUT_OF_FORM = 'init_layout: init_layout gave an answer out of form'


def _init_project_result(result, reason=None, findings=(), created=()):
    return {'result': result, 'reason': reason, 'findings': list(findings), 'created': list(created)}


def _init_project_str_tuple(value):
    return type(value) is tuple and all(type(v) is str for v in value)


def init_project(root, init_layout=None):
    """Create the project-state layout's folders under root through writer.init_layout (task TASK-095; `aieos init`,
    specification 7 :28): a mapping with exactly INIT_KEYS; it never raises. init_layout defaults, at call time, to
    writer.init_layout and is called once with root. An answer in form is a writer.StoreResult (its type exactly)
    that is "done" with reason None, findings () and a non-empty tuple of str as its value, giving result "done" and
    created the value as a list; or "refused" with a str reason and a tuple of str findings, giving result "refused"
    with that reason and those findings. Any other answer gives reason "init_layout" and the one finding
    "init_layout: init_layout gave an answer out of form"; a raise gives "init_layout: a step raised <type>"."""
    try:
        init_layout = writer.init_layout if init_layout is None else init_layout
        answer = init_layout(root)
    except Exception as exc:
        return _init_project_result('refused', 'init_layout', ['init_layout: a step raised %s' % type(exc).__name__])
    try:
        if type(answer) is writer.StoreResult:
            if (answer.result == 'done' and answer.reason is None and answer.findings == ()
                    and _init_project_str_tuple(answer.value) and answer.value):
                return _init_project_result('done', created=answer.value)
            if (answer.result == 'refused' and type(answer.reason) is str
                    and _init_project_str_tuple(answer.findings)):
                return _init_project_result('refused', answer.reason, answer.findings)
        return _init_project_result('refused', 'init_layout', [_INIT_PROJECT_OUT_OF_FORM])
    except Exception as exc:
        return _init_project_result('refused', 'init_layout', ['init_layout: a step raised %s' % type(exc).__name__])


# ---- launch_outside, `aieos launch` (task TASK-094) ----

LAUNCH_KEYS = ('result', 'reason', 'findings', 'session_id', 'start', 'run', 'end', 'handoff')
LAUNCH_REASONS = ('argument', 'clock', 'start', 'contract', 'run', 'end', 'handoff')
LAUNCH_LEASE = datetime.timedelta(hours=2)
LAUNCH_ADAPTER = 'claude_code'
LAUNCH_RECORDER = 'aieos cli launch'
LAUNCH_HOLDER = 'aieos cli launch'
_LAUNCH_PATH = re.compile(r'[A-Za-z0-9._*/-]+')
_LAUNCH_FOR = ' for session '
_LAUNCH_ENVIRONMENT = frozenset({'AIEOS_SESSION_ID', 'AIEOS_ROOT', 'AIEOS_BASE'})
_LAUNCH_CALLEES = ('begin', 'contract_at', 'finish', 'finish_outside', 'write_handoff')
_LAUNCH_AFTER = ('argument', 'record')
_LAUNCH_NOT_WRITTEN = "handoff: not written, the session's end was not done"
_LAUNCH_BAD_CLOCK = 'clock: the clock gave no timezone-aware UTC time with whole seconds'


def _launch_result(result, reason=None, findings=(), session_id=None, started=None, run=None, ended=None,
                   handoff=None):
    return {'result': result, 'reason': reason, 'findings': [f for f in findings if isinstance(f, str)],
            'session_id': session_id, 'start': started, 'run': run, 'end': ended, 'handoff': handoff}


def _launch_strs(value):
    """Only the str items of a list or a tuple; any other value gives none."""
    return [f for f in value if isinstance(f, str)] if isinstance(value, (list, tuple)) else []


def _launch_argument_findings(root, task_id, clock, starter, callees):
    found = []
    if not (isinstance(root, str) and _WINDOWS_ROOT.fullmatch(root) is not None):
        found.append('argument: root is not an absolute Windows path')
    if not (isinstance(task_id, str) and _TASK.fullmatch(task_id) is not None):
        found.append('argument: task_id is not TASK- followed by digits')
    if not callable(clock):
        found.append('argument: clock is not callable')
    if not callable(starter):
        found.append('argument: starter is not callable')
    for name, value in zip(_LAUNCH_CALLEES, callees):
        if value is not None and not callable(value):
            found.append('argument: %s is neither None nor callable' % name)
    return found


def _launch_grant_in_form(session_id, token, head, environment):
    """Step 4: the granted answer's values, each checked by its exact type."""
    try:
        return (type(session_id) is str and type(token) is dict and type(head) is str
                and _HEX40.fullmatch(head) is not None and type(environment) is dict
                and set(environment) == _LAUNCH_ENVIRONMENT
                and all(type(k) is str and type(v) is str for k, v in environment.items()))
    except Exception:  # an answer whose own methods raise is out of form
        return False


def _launch_write_set(answer):
    """Step 5: (the write set, None), or (None, findings) for a contract read that does not pass."""
    if not (type(answer) is tuple and len(answer) == 2):
        return None, ['contract: contract_at gave an answer out of form']
    value, found = answer
    if value is None:
        return None, ['contract: %s' % f for f in _launch_strs(found)] or ['contract: contract_at gave no value']
    if found is not None:
        return None, ['contract: %s' % f for f in _launch_strs(found)] or ['contract: findings beside a value']
    if not (type(value) is tuple and len(value) == 2 and type(value[0]) is dict):
        return None, ['contract: contract_at gave an answer out of form']
    write_set = value[0].get('write_set')
    paths = write_set.get('paths') if type(write_set) is dict else None
    if not (type(paths) is list and paths and all(type(p) is str for p in paths)):
        return None, ['contract: the write set is not a non-empty list of str']
    for p in paths:
        if _LAUNCH_PATH.fullmatch(p) is None or '' in p.split('/'):
            return None, ['contract: a write-set path is outside the pattern rule']
    return list(paths), None


def _launch_end_call(callee, args, findings):
    """One end call of step 6: (the answer when it is a dict, else None; True when it gave "done"); never raises."""
    try:
        answer = callee(*args)
    except Exception as exc:
        findings.append('end: a step raised %s' % type(exc).__name__)
        return None, False
    if type(answer) is not dict:
        findings.append('end: the end gave an answer that is not a mapping')
        return None, False
    if answer.get('result') == 'done':
        findings.extend(_launch_strs(answer.get('findings')))
        return answer, True
    findings.append('end: %s %s' % (answer.get('result'), answer.get('reason')))
    findings.extend(_launch_strs(answer.get('findings')))
    return answer, False


def _launch_finish(state, clock, finish, finish_outside, write_handoff):
    """Steps 6 to 8: the session's end in every case after a grant, the handoff after a done end, the result."""
    findings, reason = state['findings'], state['reason']
    try:
        now2 = clock()
        if not _utc_whole(now2):
            findings.append(_LAUNCH_BAD_CLOCK)
            now2 = state['now']
    except Exception as exc:
        findings.append('clock: the clock raised %s' % type(exc).__name__)
        now2 = state['now']
    root, task_id, session_id, recorder = state['root'], state['task_id'], state['session_id'], state['recorder']
    if state['write_set'] is not None:
        ended, done = _launch_end_call(finish, (root, task_id, session_id, state['token'], now2, state['write_set'], [],
                                                recorder), findings)
        if not done:
            reason = reason or 'end'
            if ended is not None and ended.get('result') == 'refused' and ended.get('reason') in _LAUNCH_AFTER:
                ended, done = _launch_end_call(finish_outside, (root, session_id, now2, recorder), findings)
    else:
        ended, done = _launch_end_call(finish_outside, (root, session_id, now2, recorder), findings)
    handoff = None
    if not done:
        reason = reason or 'end'
        findings.append(_LAUNCH_NOT_WRITTEN)
    else:
        try:
            got = write_handoff(root, task_id, session_id, None)
        except Exception as exc:
            got = None
            findings.append('handoff: a step raised %s' % type(exc).__name__)
        else:
            if type(got) is dict:
                handoff = got
            else:
                findings.append('handoff: the handoff gave an answer that is not a mapping')
        if not (handoff is not None and handoff.get('result') in ('written', 'none')):
            reason = reason or 'handoff'
            if handoff is not None:
                findings.append('handoff: %s %s' % (handoff.get('result'), handoff.get('reason')))
                findings.extend(_launch_strs(handoff.get('findings')))
    return _launch_result('done' if reason is None else 'refused', reason, findings, session_id, state['started'],
                          state['run'], ended, handoff)


def launch_outside(root, task_id, clock, starter, begin=None, contract_at=None, finish=None, finish_outside=None,
                   write_handoff=None):
    """Launch one session from outside the runtime (task TASK-094; `aieos launch`, specification 7 :34-35, sections 5
    and 7): start with max_risk None, on a grant the contract's write set at the grant's head, the caller's starter, the
    session's end in every case after a grant, then the handoff file after a done end. A mapping with exactly
    LAUNCH_KEYS; it never raises an Exception; a BaseException from the starter is re-raised after the end and the
    handoff."""
    callees = (begin, contract_at, finish, finish_outside, write_handoff)
    try:
        found = _launch_argument_findings(root, task_id, clock, starter, callees)
    except Exception as exc:  # an argument whose own methods raise
        found = ['argument: checking the arguments raised %s' % type(exc).__name__]
    if found:
        return _launch_result('refused', 'argument', found)
    begin = start if begin is None else begin
    contract_at = base_inputs.contract_at if contract_at is None else contract_at
    finish = end if finish is None else finish
    finish_outside = end_outside if finish_outside is None else finish_outside
    write_handoff = handoff_file.write if write_handoff is None else write_handoff
    try:
        now = clock()
    except Exception as exc:
        return _launch_result('refused', 'clock', ['clock: the clock raised %s' % type(exc).__name__])
    if not _utc_whole(now):
        return _launch_result('refused', 'clock', [_LAUNCH_BAD_CLOCK])
    try:
        started = begin(root, root, task_id, LAUNCH_ADAPTER, None, LAUNCH_HOLDER, LAUNCH_RECORDER, now,
                        now + LAUNCH_LEASE)
    except Exception as exc:
        return _launch_result('refused', 'start', ['start: a step raised %s' % type(exc).__name__])
    if type(started) is not dict:
        return _launch_result('refused', 'start', ['start: start gave an answer that is not a mapping'])
    try:
        findings = ['start: %s %s' % (started.get('result'), started.get('reason'))]
        findings.extend(_launch_strs(started.get('findings')))
        granted = started.get('result') == 'granted'
    except Exception as exc:  # an answer whose own values raise
        return _launch_result('refused', 'start', ['start: reading the answer raised %s' % type(exc).__name__],
                              started=started)
    if not granted:
        result = 'not granted' if started.get('result') == 'not granted' else 'refused'
        return _launch_result(result, 'start', findings, started=started)
    findings = findings[1:]
    session_id, token = started.get('session_id'), started.get('fencing_token')
    head, environment = started.get('head_commit'), started.get('environment')
    state = {'root': root, 'task_id': task_id, 'now': now, 'started': started, 'findings': findings, 'reason': None,
             'run': None, 'write_set': None, 'session_id': session_id, 'token': token, 'recorder': None}
    if not _launch_grant_in_form(session_id, token, head, environment):
        findings.append('start: the granted answer is out of form')
        if type(session_id) is not str:
            return _launch_result('refused', 'start', findings, None, started)
        state['reason'] = 'start'
    else:
        try:
            state['write_set'], found = _launch_write_set(contract_at(root, head, task_id))
        except Exception as exc:
            found = ['contract: a step raised %s' % type(exc).__name__]
        if state['write_set'] is None:
            findings.extend(found)
            state['reason'] = 'contract'
    state['recorder'] = LAUNCH_RECORDER + _LAUNCH_FOR + session_id
    if state['write_set'] is None:
        return _launch_finish(state, clock, finish, finish_outside, write_handoff)
    try:
        try:
            starter(dict(environment))
            state['run'] = 'returned'
        except Exception as exc:
            state['run'] = 'raised %s' % type(exc).__name__
            findings.append('run: the starter raised %s' % type(exc).__name__)
            state['reason'] = 'run'
    finally:
        out = _launch_finish(state, clock, finish, finish_outside, write_handoff)
    return out


# ---- approval_act, `aieos approve`, `aieos edit` and `aieos reject` (task TASK-096) ----

APPROVAL_KEYS = ('result', 'reason', 'findings', 'record_id', 'event_ids', 'appends')
APPROVAL_REASONS = ('argument', 'clock', 'head', 'contract', 'log', 'state', 'version', 'dependencies',
                    'owner_kept_act', 'rejected', 'append')
APPROVAL_ACTS = ('approve', 'edit', 'reject')
APPROVAL_CLASSES = ('decision_agent', 'human_authority')
APPROVAL_EDIT_TYPE = 'contract_edit'
APPROVAL_TEXT_MAX = 2000
_APPROVAL_NAME_MAX = 200
_APPROVAL_DECISION = re.compile(r'D-[0-9]+')
_APPROVAL_HASH = re.compile(r'[0-9a-f]{64}')
_APPROVAL_CALLEES = ('read', 'read_log', 'append', 'contract_at', 'task_states')
_APPROVAL_DRAFTED = ('task.drafted', 'task.replanned')
_APPROVAL_STATE_EVENTS = ('task.approved', 'decision.acceptance')
_APPROVAL_APPENDED = ('appended', 'duplicate')
_APPROVAL_WORD = 'owner'
_APPROVAL_BAD_CLOCK = 'clock: the clock gave no timezone-aware UTC time with whole seconds'


class _approval_stop(Exception):
    """A refusal at a step: its reason and its findings."""

    def __init__(self, reason, findings):
        Exception.__init__(self, reason)
        self.reason = reason
        self.findings = list(findings)


def _approval_result(result, reason=None, findings=(), record_id=None, event_ids=(), appends=()):
    return {'result': result, 'reason': reason, 'findings': [f for f in findings if isinstance(f, str)],
            'record_id': record_id, 'event_ids': list(event_ids), 'appends': list(appends)}


def _approval_strs(value):
    """Only the str items of a list or a tuple; any other value gives none."""
    return [f for f in value if isinstance(f, str)] if isinstance(value, (list, tuple)) else []


def _approval_line(value, most):
    """A non-empty one-line str of at most ``most`` printable characters (no control character, no line break)."""
    return type(value) is str and 0 < len(value) <= most and value.isprintable()


def _approval_argument_findings(root, task_id, act, source_class, who, note, clock, callees):
    """Step 1: the arguments' findings."""
    found = []
    if not (isinstance(root, str) and _WINDOWS_ROOT.fullmatch(root) is not None):
        found.append('argument: root is not an absolute Windows path')
    if not (isinstance(task_id, str) and _TASK.fullmatch(task_id) is not None):
        found.append('argument: task_id is not TASK- followed by digits')
    if not (type(act) is str and act in APPROVAL_ACTS):
        found.append('argument: act is not approve, edit or reject')
    if not (type(source_class) is str and source_class in APPROVAL_CLASSES):
        found.append('argument: source_class is not decision_agent or human_authority')
    elif source_class == 'decision_agent':
        if not (type(who) is str and _APPROVAL_DECISION.fullmatch(who) is not None):
            found.append('argument: who is not a decision id D- followed by digits')
    elif not (_approval_line(who, _APPROVAL_NAME_MAX) and _APPROVAL_WORD not in who.lower()):
        found.append('argument: who is not a one-line name of at most %d printable characters without the word '
                     '"%s"' % (_APPROVAL_NAME_MAX, _APPROVAL_WORD))
    if act == 'edit':
        if not (_approval_line(note, APPROVAL_TEXT_MAX) and _APPROVAL_WORD not in note.lower()):
            found.append('argument: note is not a one-line text of at most %d printable characters without the word '
                         '"%s"' % (APPROVAL_TEXT_MAX, _APPROVAL_WORD))
    elif note is not None:
        found.append('argument: a note is given, but act is not edit')
    if not callable(clock):
        found.append('argument: clock is not callable')
    for name, value in zip(_APPROVAL_CALLEES, callees):
        if value is not None and not callable(value):
            found.append('argument: %s is neither None nor callable' % name)
    return found


def _approval_contract(answer):
    """Step 4: (contract, contract_hash) from contract_at's answer, or a stop with reason "contract"."""
    if not (type(answer) is tuple and len(answer) == 2):
        raise _approval_stop('contract', ['contract: contract_at gave an answer out of form'])
    value, found = answer
    if value is None:
        raise _approval_stop('contract', ['contract: %s' % f for f in _approval_strs(found)]
                            or ['contract: contract_at gave no value'])
    if found is not None:
        raise _approval_stop('contract', ['contract: %s' % f for f in _approval_strs(found)]
                            or ['contract: findings beside a value'])
    if not (type(value) is tuple and len(value) == 2 and type(value[0]) is dict and type(value[1]) is str
            and _APPROVAL_HASH.fullmatch(value[1]) is not None and type(value[0].get('contract_version')) is str):
        raise _approval_stop('contract', ['contract: contract_at gave an answer out of form'])
    return value


def _approval_events(log, task_id):
    """Step 5: the task's own events in log order, ignored duplicate lines left out, after records.check_log."""
    if type(log) is not bytes:
        raise _approval_stop('log', ['log: read_log gave an answer that is not bytes'])
    report = records.check_log(log)
    found = ['log: %s' % f for _, f in report.findings()]
    if found:
        raise _approval_stop('log', found)
    return [line.event for line in report.lines if line.duplicate_of is None and line.event.get('task_id') == task_id]


def _approval_drafted(mine, task_id):
    """Step 6: the index of the task's last state-setting event, which must be task.drafted or task.replanned."""
    kinds = set(execution.STATE_OF) | set(_APPROVAL_STATE_EVENTS)
    setting = [i for i, e in enumerate(mine) if e.get('type') in kinds]
    if not setting or mine[setting[-1]].get('type') not in _APPROVAL_DRAFTED:
        raise _approval_stop('state', ['state: %s is not in DRAFT' % task_id])
    return setting[-1]


def _approval_dependencies(contract, log, task_states):
    """Step 8, the dependencies: each of the contract's depends_on DONE by task_states."""
    state = contract.get('input_state')
    depends = state.get('depends_on') if type(state) is dict else None
    if not (type(depends) is list and all(type(d) is str and _TASK.fullmatch(d) is not None for d in depends)):
        raise _approval_stop('dependencies', ['dependencies: depends_on is not a list of TASK- ids'])
    answer = task_states(log, list(depends))
    if not (type(answer) is tuple and len(answer) == 2):
        raise _approval_stop('dependencies', ['dependencies: task_states gave an answer out of form'])
    states, found = answer
    if found is not None or type(states) is not dict:
        raise _approval_stop('dependencies', ['dependencies: %s' % f for f in _approval_strs(found)]
                            or ['dependencies: task_states gave an answer out of form'])
    missing = [d for d in depends if not (type(states.get(d)) is dict and states[d].get('state') == 'DONE')]
    if missing:
        raise _approval_stop('dependencies', ['dependencies: %s is not DONE' % d for d in missing])


def _approval_rejected(mine, start, contract_hash):
    """Step 8, the earlier Reject: an authority record of the version with outcome fail after the last draft."""
    binding = {'kind': 'contract', 'hash': contract_hash}
    for event in mine[start + 1:]:
        payload = event.get('payload')
        if (event.get('type') == 'record.added' and type(payload) is dict and payload.get('fact_kind') == 'authority'
                and payload.get('approval_binding') == binding and payload.get('outcome') == 'fail'):
            raise _approval_stop('rejected', ['rejected: this contract version was rejected after its last draft'])


def _approval_record(act, task_id, source_class, who, note, contract_hash):
    """Step 9: the record and its recorder."""
    parts = ('approval', act, task_id, contract_hash)
    if act == 'edit':
        parts += (source_class, who, note)
    record_id = 'approval/' + hashlib.sha256('\n'.join(parts).encode('utf-8')).hexdigest()
    if source_class == 'decision_agent':
        recorder = 'decided by: decision agent (A41, A51), decision %s, through aieos cli %s' % (who, act)
    else:
        recorder = '%s, as stated to aieos cli %s (not checked)' % (who, act)
    record = {'record_id': record_id, 'source_class': source_class, 'recorder': recorder, 'subject': task_id}
    if act == 'edit':
        record.update({'fact_kind': 'claim', 'evidence_type': APPROVAL_EDIT_TYPE, 'text': note})
    else:
        record.update({'fact_kind': 'authority', 'approval_binding': {'kind': 'contract', 'hash': contract_hash}})
        if act == 'reject':
            record['outcome'] = 'fail'
    if source_class == 'decision_agent':
        record['decision_ref'] = who
    return record, recorder


def _approval_append(append, root, task_id, event_type, payload, record_id, now, recorder):
    """Step 10, one append: (its event id, "appended" or "duplicate"), or a stop with reason "append"."""
    event_id = hashlib.sha256('\n'.join(('approval-event', event_type, record_id)).encode('utf-8')).hexdigest()
    try:
        got = append(root, event_type, payload, event_id, now, recorder, task_id=task_id)
    except Exception as exc:
        raise _approval_stop('append', ['append: %s: a step raised %s' % (event_type, type(exc).__name__)])
    result = got.result if isinstance(got, writer.WriteResult) else None
    if result not in _APPROVAL_APPENDED:
        if isinstance(got, writer.WriteResult):
            raise _approval_stop('append', ['append: %s: %s %s' % (event_type, got.result, got.reason)]
                                + _approval_strs(got.findings))
        raise _approval_stop('append', ['append: %s: append gave an answer that is not a WriteResult' % event_type])
    return event_id, result


def approval_act(root, task_id, act, source_class, who, note, clock, read=None, read_log=None, append=None,
                 contract_at=None, task_states=None):
    """Record an approval, a rejection or an edit note of a task's drafted contract version (task TASK-096; `aieos
    approve`, `aieos edit` and `aieos reject`, specification 1 section 12, specification 7 section 4): a mapping with
    exactly APPROVAL_KEYS; it never raises an Exception. Its steps, each step's name being the reason of a refusal or
    a raise at it: argument; clock; head (start's own reader, _head); contract (contract_at at that head); log
    (read_log, then records.check_log); state (the last state-setting event task.drafted or task.replanned); version
    (the contract's hash and contract_version equal to that event's); for approve, dependencies, owner_kept_act and
    rejected; then the appends through append only: record.added, and for approve task.approved citing the record."""
    callees = (read, read_log, append, contract_at, task_states)
    step = 'argument'
    record_id, event_ids, appends = None, [], []
    try:
        found = _approval_argument_findings(root, task_id, act, source_class, who, note, clock, callees)
        if found:
            raise _approval_stop('argument', found)
        read = gitread.run if read is None else read
        read_log = writer.read_log if read_log is None else read_log
        append = writer.append_event if append is None else append
        contract_at = base_inputs.contract_at if contract_at is None else contract_at
        task_states = execution.task_states if task_states is None else task_states
        step = 'clock'
        moment = clock()
        if not _utc_whole(moment):
            raise _approval_stop('clock', [_APPROVAL_BAD_CLOCK])
        step = 'head'
        head, found = _head(read, root)
        if found is not None:
            raise _approval_stop('head', found)
        step = 'contract'
        contract, contract_hash = _approval_contract(contract_at(root, head, task_id))
        step = 'log'
        log = read_log(root)
        mine = _approval_events(log, task_id)
        step = 'state'
        start = _approval_drafted(mine, task_id)
        step = 'version'
        drafted = mine[start].get('payload') or {}
        if (drafted.get('contract_hash') != contract_hash
                or drafted.get('contract_version') != contract['contract_version']):
            raise _approval_stop('version', ['version: the contract at HEAD is not the version of the last %s'
                                            % mine[start].get('type')])
        if act == 'approve':
            step = 'dependencies'
            _approval_dependencies(contract, log, task_states)
            step = 'owner_kept_act'
            if source_class == 'decision_agent' and contract.get('owner_kept_act') != 'false':
                raise _approval_stop('owner_kept_act', ['owner_kept_act: a decision_agent approval of a task whose '
                                                       'owner_kept_act is set is refused'])
            step = 'rejected'
            _approval_rejected(mine, start, contract_hash)
        step = 'append'
        record, recorder = _approval_record(act, task_id, source_class, who, note, contract_hash)
        record_id = record['record_id']
        events = [('record.added', record)]
        if act == 'approve':
            events.append(('task.approved', {'contract_version': contract['contract_version'],
                                             'contract_hash': contract_hash, 'approval_record': record_id}))
        for event_type, payload in events:
            try:
                event_id, result = _approval_append(append, root, task_id, event_type, payload, record_id, moment,
                                                    recorder)
            except _approval_stop as stop:
                if event_ids:
                    stop.findings.append('append: the record %s is in the log, the task.approved is not; running '
                                         'approve again appends it' % record_id)
                raise
            event_ids.append(event_id)
            appends.append(result)
    except _approval_stop as stop:
        return _approval_result('refused', stop.reason, stop.findings, record_id, event_ids, appends)
    except Exception as exc:  # TASK-096: a raise at a step gives that step's reason
        return _approval_result('refused', step, ['%s: a step raised %s' % (step, type(exc).__name__)], record_id,
                                event_ids, appends)
    return _approval_result('done', None, [], record_id, event_ids, appends)

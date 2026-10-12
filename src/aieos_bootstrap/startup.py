"""Recovery at start of gov-AIEOS (task TASK-026; specification 1 sections 5.1, 7 and 8; specification 2 sections 6.1,
6.3 and 6.6; DEF-0030): the third piece of the core's caller, after the Git reader and the submission path.

``recover(root, repo, recorder, now)`` runs specification 1 section 7 at start, before any new event:

1. Arguments (AC1): every argument is checked before anything is read; a wrong one gives a refusal result.
2. The walk (AC2): HEAD is resolved through gitread.run ("rev-parse"), and every commit reachable from it, every
   parent of every commit, is read once ("cat-file -p") and parsed by gitread.parse_commit, up to ``max_commits``
   distinct commits (default 10000); a read that fails, or a walk past the bound, refuses the whole recovery.
3. The order and the body rule (AC3): the commits go to reconcile parents before children (a post-order that visits
   a commit's parents in the order its header lists them). A commit whose message has fewer than two paragraphs is
   not given, since git would read its only paragraph as the subject and not as a trailer block; when its trailers
   still give a task or any finding, its id is listed in ``left_out`` and a finding names it.
4. Reconcile (AC4): the log and the held leases are read once through the writer, and recovery.reconcile decides every
   event; a damaged log refuses the whole recovery.
5. The appends (AC5): each event reconcile appended is appended through writer.append_event with the line's own type,
   payload, event_id, task_id and fencing token, one at a time; the log is then read again and compared with
   reconcile's log.
6. The release (AC6): every held lease whose task and token equal those of a task.submitted event in the log after the
   appends is released by its token through writer.release_lease_token, so a run or a submission that stopped between
   its append and its release is completed here.
7. The expiry (AC7): only after a complete replay, the leases whose expiry has passed are expired through
   writer.expire_leases.

The result (AC10) is a mapping with exactly the keys result ("recovered", "partial" or "refused"), reason, findings,
appended, released, expired and left_out. An exception raised by an injected function, or by reading what it returns,
is caught and becomes a result; none escapes.

``read``, ``read_log``, ``append``, ``leases``, ``release`` and ``expire`` default, at call time, to gitread.run,
writer.read_log, writer.append_event, writer.held_leases, writer.release_lease_token and writer.expire_leases (AC9);
tests pass stand-ins.

Purity (AC12): this module starts no process except through ``read``, opens no file itself, reads no clock and no
environment variable, grants no lease, creates no store (it never calls open_store, so DEF-0041 (c), never giving an
earlier store's epoch to a recreated store, does not apply), and builds no event-log line itself.

Readings (the implementer's, for the decision agent's ruling, not the contract's own words):
- A commit or parent id that is not 40 lowercase hexadecimal characters (a SHA-256 repository) is refused as a read
  that fails, reason "git", since recovery.reconcile takes 40-hex commit ids only.
- A read of the log or of the leases that raises, or a reconcile that raises, gives "refused" with reason "store";
  reconcile's log that does not match its own events gives "refused" with reason "log"; in both cases nothing is
  appended.
- When the log read after the appends differs from reconcile's log, the result is "partial", reason "store", and
  nothing is released or expired, since the release is decided on that log.

Limits (AC13):
- The PATH git is found by is the caller's precondition (DEF-0052 G1): gitread refuses an empty or relative entry, and
  an absolute entry is trusted as given.
- The tests use stand-ins for the writer except read_log's own unit test, so the real store's path is covered by the
  writer's tests and not end to end with recover.
- v0.1 runs one task at a time and recovery runs at start, before any new event, so nothing else writes the log or
  the store while it runs.
- The walk reads every reachable commit each time: its cost grows with the history, and the bound refuses past it.
- A commit left out by the body rule stands in Git with no observation.
- The release and the expiry are separate calls after the appends, so a stop between them is completed by the next
  run, which releases by token every held lease whose task and token a logged task.submitted names, or by the lease's
  own expiry.
- Whether an unfenced write blocks the task's acceptance stays open (specification 2 section 10 point 7).
"""

import datetime
import json
import os
import re

from aieos_bootstrap import gitread
from aieos_bootstrap import recovery
from aieos_bootstrap import writer

_COMMIT = re.compile(r'[0-9a-f]{40}')
_HEAD_OUT = re.compile(rb'[0-9a-f]{40}\n')
_PARAGRAPH = re.compile(r'\n[ \t]*\n')
_ZERO = datetime.timedelta(0)
DEFAULT_MAX_COMMITS = 10000
MAX_COMMITS = 100000
RESULT_KEYS = frozenset({'result', 'reason', 'findings', 'appended', 'released', 'expired', 'left_out'})


class _Stop(Exception):
    """A step that ends the recovery with a refusal: its reason and findings."""

    def __init__(self, reason, findings):
        Exception.__init__(self, reason)
        self.reason = reason
        self.findings = list(findings)


def _is_str(value):
    return isinstance(value, str) and value != ''


def _token_text(token):
    """Two fencing tokens are compared as eventlog and recovery compare them: the canonical JSON text (None when it
    cannot be written, so it equals nothing)."""
    try:
        return json.dumps(token, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        return None


def _argument_findings(root, repo, recorder, now, head, max_commits):
    """AC1: what is wrong with the arguments, as a list of findings (empty when every argument is in form)."""
    found = []
    for name, value in (('root', root), ('repo', repo)):
        if not (_is_str(value) and os.path.isabs(value)):
            found.append('argument: %s is not a non-empty absolute path string' % name)
    if not _is_str(recorder):
        found.append('argument: recorder is not a non-empty string')
    if not (isinstance(now, datetime.datetime) and now.tzinfo is not None and now.utcoffset() == _ZERO
            and now.microsecond == 0):
        found.append('argument: now is not a timezone-aware datetime in UTC with whole seconds')
    if head is not None and not (isinstance(head, str) and _COMMIT.fullmatch(head)):
        found.append('argument: head is not None or 40 lowercase hexadecimal characters')
    if type(max_commits) is not int or not 1 <= max_commits <= MAX_COMMITS:
        found.append('argument: max_commits is not an int from 1 to %d' % MAX_COMMITS)
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


def _call(read, repo, args):
    name = ' '.join(args)
    try:
        r = read(repo, list(args))
        why = _read_failure(name, r)
    except Exception as exc:  # AC10: no exception escapes
        raise _Stop('git', ['git: %s raised %s' % (name, type(exc).__name__)])
    if why is not None:
        raise _Stop('git', [why])
    return name, r


def _resolve_head(read, repo):
    """AC2: the 40-hex id HEAD names."""
    name, r = _call(read, repo, ['rev-parse', '--verify', '--end-of-options', 'HEAD'])
    out = r['out']
    if not (isinstance(out, bytes) and _HEAD_OUT.fullmatch(out)):
        raise _Stop('git', ['git: %s did not give 40 lowercase hexadecimal characters and one LF' % name])
    return out[:40].decode('ascii')


def _read_commit(read, repo, commit_id):
    """AC2: the parsed commit; raises _Stop when it cannot be read."""
    name, r = _call(read, repo, ['cat-file', '-p', commit_id])
    parsed = gitread.parse_commit(r['out'])
    if parsed['error'] is not None:
        raise _Stop('git', ['git: %s is out of form: %s' % (name, parsed['error'])])
    for parent in parsed['parents']:
        if not _COMMIT.fullmatch(parent):
            raise _Stop('git', ['git: %s names a parent that is not 40 lowercase hexadecimal characters' % name])
    return parsed


def _walk(read, repo, head, max_commits):
    """AC2, AC3: every commit reachable from head, read once, in a post-order that visits a commit's parents in the
    order its header lists them (parents before children); raises _Stop on a failed read or past the bound."""
    parsed = {head: _read_commit(read, repo, head)}
    order = []
    stack = [(head, iter(parsed[head]['parents']))]
    while stack:
        commit_id, parents = stack[-1]
        parent = next(parents, None)
        if parent is None:
            stack.pop()
            order.append(commit_id)
            continue
        if parent in parsed:
            continue
        if len(parsed) >= max_commits:
            raise _Stop('bound', ['bound: more than %d commits are reachable from %s' % (max_commits, head)])
        parsed[parent] = _read_commit(read, repo, parent)
        stack.append((parent, iter(parsed[parent]['parents'])))
    return [(c, parsed[c]['message']) for c in order]


def _body_rule(walked):
    """AC3: the commits given to reconcile, the ids left out with a finding, and those findings."""
    commits, left_out, findings = [], [], []
    for commit_id, message in walked:
        paragraphs = [p for p in _PARAGRAPH.split(message.strip('\n')) if p.strip()]
        if len(paragraphs) >= 2:
            commits.append({'commit': commit_id, 'message': message})
            continue
        trailer, bad = recovery.trailers(message)
        if trailer['task'] is not None or bad:
            left_out.append(commit_id)
            findings.append('left out: commit %s has no message body, so git reads no trailer block in it; its '
                            'trailers are not taken and nothing is appended for it (DEF-0030)' % commit_id)
    return commits, left_out, findings


def _new_lines(given, r):
    """AC5: the event lines reconcile appended after the given bytes, matched one to one with its appended events."""
    log = r.log
    if not (isinstance(log, bytes) and log.startswith(given)):
        raise _Stop('log', ['log: reconcile\'s log does not begin with the log it was given; nothing is appended'])
    new = log[len(given):]
    lines = new.split(b'\n')[:-1] if new.endswith(b'\n') or not new else None
    events = [e for e in r.events if e['result'] == 'appended']
    if lines is None or len(lines) != len(events):
        raise _Stop('log', ['log: reconcile\'s new lines do not match its appended events; nothing is appended'])
    out = []
    for event, raw in zip(events, lines):
        line = json.loads(raw.decode('utf-8'))
        if not isinstance(line, dict) or line.get('event_id') != event['event_id']:
            raise _Stop('log', ['log: reconcile\'s line for %s is not its event; nothing is appended'
                                % event['event_id']])
        out.append(line)
    return out


def _outcome(w):
    """AC5: the writer's result as an exact str; raises when it cannot be read."""
    outcome = getattr(w, 'result', None)
    if type(outcome) is not str:
        raise TypeError('the result is not a string')
    return outcome


def _submissions(log):
    """AC6: (task_id, token text) of every task.submitted event in the log."""
    out = set()
    for raw in log.split(b'\n'):
        if not raw:
            continue
        line = json.loads(raw.decode('utf-8'))
        if isinstance(line, dict) and line.get('type') == 'task.submitted':
            out.add((line.get('task_id'), _token_text(line.get('fencing_token'))))
    return out


def recover(root, repo, recorder, now, head=None, max_commits=DEFAULT_MAX_COMMITS, read=None, read_log=None,
            append=None, leases=None, release=None, expire=None):
    """Run recovery at start (TASK-026 AC1 to AC10); returns a mapping with RESULT_KEYS."""
    read = gitread.run if read is None else read
    read_log = writer.read_log if read_log is None else read_log
    append = writer.append_event if append is None else append
    leases = writer.held_leases if leases is None else leases
    release = writer.release_lease_token if release is None else release
    expire = writer.expire_leases if expire is None else expire
    out = {'result': 'refused', 'reason': None, 'findings': [], 'appended': [], 'released': [], 'expired': [],
           'left_out': []}

    def ended(result, reason, findings=()):
        out['result'] = result
        out['reason'] = reason
        out['findings'].extend(findings)
        return out

    try:
        found = _argument_findings(root, repo, recorder, now, head, max_commits)
    except Exception as exc:  # AC10: an argument whose own methods raise (for example a tzinfo's utcoffset)
        found = ['argument: checking the arguments raised %s' % type(exc).__name__]
    if found:
        return ended('refused', 'argument', found)

    # AC2, AC3: the walk and the body rule.
    try:
        start = _resolve_head(read, repo) if head is None else head
        walked = _walk(read, repo, start, max_commits)
        commits, left_out, found = _body_rule(walked)
    except _Stop as stop:
        return ended('refused', stop.reason, stop.findings)
    except Exception as exc:  # AC10
        return ended('refused', 'git', ['git: the walk raised %s' % type(exc).__name__])
    out['left_out'] = left_out
    out['findings'].extend(found)

    # AC4: the log and the leases, each read once, then reconcile once.
    try:
        given = read_log(root)
        held = leases(root)
    except Exception as exc:  # AC10
        return ended('refused', 'store', ['store: reading the log or the leases raised %s' % type(exc).__name__])
    try:
        r = recovery.reconcile(given, commits, held, now, recorder)
        rfindings = [f for f in r.findings]
    except Exception as exc:  # AC10
        return ended('refused', 'store', ['store: reconcile raised %s on the log or the leases read'
                                          % type(exc).__name__])
    damaged = [f for f in rfindings if isinstance(f, str) and f.startswith('log: ')]
    if damaged:
        return ended('refused', 'log', damaged)
    out['findings'].extend(rfindings)
    try:
        lines = _new_lines(given, r)
    except _Stop as stop:
        return ended('refused', stop.reason, stop.findings)
    except Exception as exc:  # AC10
        return ended('refused', 'log', ['log: reading reconcile\'s new lines raised %s' % type(exc).__name__])

    # AC5: the appends through the writer, one at a time.
    for line in lines:
        event_id = line.get('event_id')
        try:
            w = append(root, line.get('type'), line.get('payload'), event_id, now, recorder,
                       task_id=line.get('task_id'), fencing_token=line.get('fencing_token'))
            outcome = _outcome(w)
        except Exception as exc:  # AC10
            return ended('partial', 'store', ['store: the append of %s raised %s; nothing further is released or '
                                              'expired' % (event_id, type(exc).__name__)])
        if outcome not in ('appended', 'duplicate'):
            return ended('partial', 'store', ['store: the writer gave %r for %s; nothing further is released or '
                                              'expired' % (outcome, event_id)])
        out['appended'].append(event_id)
    try:
        after = read_log(root)
        same = after == r.log
    except Exception as exc:  # AC10
        return ended('partial', 'store', ['store: reading the log after the appends raised %s' % type(exc).__name__])
    if not same:
        return ended('partial', 'store', ['store: the log after the appends is not reconcile\'s log; nothing is '
                                          'repaired, released or expired'])

    # AC6: the release by token of every held lease a logged task.submitted names.
    try:
        named = _submissions(after)
    except Exception as exc:  # AC10
        return ended('partial', 'store', ['store: reading the log\'s submissions raised %s' % type(exc).__name__])
    for lease in held:
        task_id, token = lease['task_id'], lease['fencing_token']
        if (task_id, _token_text(token)) not in named:
            continue
        try:
            rel = release(root, task_id, token)
            state = getattr(rel, 'result', None)
            done = type(state) is str and state == 'done'
            value = getattr(rel, 'value', None) if done else None
        except Exception as exc:  # AC10
            out['findings'].append('store: the release of %s raised %s; it expires by its own expiry'
                                   % (task_id, type(exc).__name__))
            continue
        if not done:
            shown = state if type(state) is str else type(state).__name__
            out['findings'].append('store: the release of %s gave %r; it expires by its own expiry' % (task_id, shown))
            continue
        out['released'].append(value)

    # AC7: the expiry, after a complete replay.
    try:
        out['expired'] = list(expire(root, now))
    except Exception as exc:  # AC10
        return ended('partial', 'store', ['store: the expiry raised %s' % type(exc).__name__])
    return ended('recovered', None)

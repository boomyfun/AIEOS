"""The capture-and-submit step of `aieos launch` (task TASK-148; BT1b, the core part of route (c) of DEF-0149;
specification 5 :24 sends a submission through the core's submission path, and the decision D-6609 puts the git-writing
step in src/aieos_runtime, so the core takes the runtime's two functions by injection and holds none of its own):
after a session, the changes it left in the working tree are written as one commit on
refs/heads/task/<id> and submitted while the lease is held, and the tree is put back.

``capture_and_submit(root, repo, task_id, token, base_head, write_set, forbidden, state_name, clock, recorder, read,
capture, restore, submit_fn=None)`` returns a mapping with exactly the keys result ("done", "none" or "refused"), reason
(None, or one of "status", "config", "identity", "scope", "staged", "capture", "submit"), findings (a list of str), commit
(40 lowercase hex or None) and paths (the captured paths, or []). It never raises an Exception. It starts no process,
opens no file and has no clock of its own: every effect is the callee's (read, capture, restore, submit_fn, clock). In
order, each refusal ending the step with no capture and no restore unless stated:

1. The arguments (reason "status", or "scope" for a write set or a forbidden list that is not a non-empty list of
   well-formed patterns).
2. The configuration, read once with the argv gitread.CONFIG_LIST: a key that begins with "filter." (ASCII-lowercased)
   or equals "core.worktree" gives "config" (the rule of launcher._config_keys); the identity is the LAST user.name
   and the LAST user.email, as git has it, and "identity" when either is absent, empty or holds "<", ">", LF or NUL.
3. HEAD must equal base_head ("status").
4. The status, read with the argv of the launcher's root check, parsed from its -z output under the form rules of
   launcher._root_entries and with the two status characters kept: " M" is modified, " D" deleted, "??" added; any
   other pair is "staged" (a refusal that names the count and the first twenty pairs).
5. The scope ("scope"): every path passes conformance.path_ok and matches a write-set pattern under
   conformance.path_matches (the matcher of the CI's G0 scope step) and no forbidden pattern; a path under the state
   directory or ".git" in any letter case is refused.
6. No changed path: result "none", no capture, no submit.
7. capture(repo, "refs/heads/task/<id>", base_head, paths, message, identity, state_name); the message is a subject,
   a body of one sentence and a last paragraph of the two trailers AIEOS-Task and AIEOS-Fence. A refusal is "capture";
   restore is not called.
8. A fresh clock read, then submit_fn(root, repo, commit, task_id, event_id, recorder, now2) with the event id the
   SHA-256 hex of "task.submitted", the task id and the commit id joined by LF. A result other than "submitted" or
   "duplicate" is "submit"; the commit and the ref stay, the lease is NOT released by a refused submission, and
   restore is NOT called (the tree stays as the session left it). The answers "submitted" and "duplicate" are taken as
   they are: submit.submit also gives them when its release of the lease raised or was not the commit's, or, for
   "duplicate", when it released nothing (a finding of the answer, not a refusal), and the step then still restores
   the tree and gives "done" with that finding in its findings.
9. restore(repo, paths, classes, state_name) only after a done capture AND a submit that gave "submitted" or
   "duplicate"; a refused restore is "capture". The result is "done" when all three gave done.

Limits: the configuration, the HEAD and the status are separate reads, not one atomic read; an ignored path is not seen;
the commit's author and committer come from the clone's configuration."""

import datetime
import hashlib
import re

from aieos_bootstrap import conformance
from aieos_bootstrap import gitread
from aieos_bootstrap import submit

_TIMEOUT = 30
_HEAD_ARGS = ('rev-parse', '--verify', '--end-of-options', 'HEAD')
_HEX40 = re.compile(r'[0-9a-f]{40}')
_TASK = re.compile(r'TASK-[0-9]+')
_STATUS_CHARS = frozenset(b' MTADRCU?!')
_CLASSES = {b' M': 'modified', b' D': 'deleted', b'??': 'added'}
_SHOWN = 20
_KEY_CUT = 80
_UNSAFE = ('<', '>', '\n', '\0')
_SUBMITTED = ('submitted', 'duplicate')
_ZERO = datetime.timedelta(0)
_EVENT_TYPE = 'task.submitted'


def _out(result, reason=None, findings=(), commit=None, paths=()):
    return {'result': result, 'reason': reason, 'findings': [f for f in findings if isinstance(f, str)],
            'commit': commit, 'paths': list(paths)}


def _refused(reason, findings, commit=None, paths=()):
    return _out('refused', reason, findings, commit, paths)


def _strs(value):
    return [f for f in value if isinstance(f, str)] if isinstance(value, (list, tuple)) else []


def _utc_whole(value):
    return (isinstance(value, datetime.datetime) and value.tzinfo is not None and value.utcoffset() == _ZERO
            and value.microsecond == 0)


def _call(callee, *args):
    """(the answer, None), or (None, the exception's name): an Exception of a callee is data here."""
    try:
        return callee(*args), None
    except Exception as exc:
        return None, type(exc).__name__


def _read_ok(answer):
    return (isinstance(answer, dict) and answer.get('error') is None and answer.get('exit') == 0
            and isinstance(answer.get('out'), bytes))


def _arguments(root, repo, task_id, token, base_head, write_set, forbidden, state_name, clock, recorder, read, capture,
               restore, submit_fn):
    """Step 1: None, or (the reason, findings)."""
    found = []
    for name, value in (('root', root), ('repo', repo), ('recorder', recorder)):
        if not (isinstance(value, str) and value):
            found.append('argument: %s is not a non-empty string' % name)
    if not (isinstance(task_id, str) and _TASK.fullmatch(task_id) is not None):
        found.append('argument: task_id is not TASK- followed by digits')
    epoch = token.get('epoch') if isinstance(token, dict) else None
    counter = token.get('counter') if isinstance(token, dict) else None
    if not (isinstance(token, dict) and set(token) == {'epoch', 'counter'} and isinstance(epoch, str) and epoch
            and epoch == epoch.strip() and not any(c in epoch for c in '\r\n\0') and type(counter) is int
            and counter >= 0):
        found.append('argument: token is not a mapping of an epoch string and a counter integer')
    if not (isinstance(base_head, str) and _HEX40.fullmatch(base_head) is not None):
        found.append('argument: base_head is not 40 lowercase hexadecimal characters')
    if not (isinstance(state_name, str) and len(state_name) > 1 and state_name.startswith('.')):
        found.append('argument: state_name does not begin with a dot')
    for name, value in (('clock', clock), ('read', read), ('capture', capture), ('restore', restore)):
        if not callable(value):
            found.append('argument: %s is not callable' % name)
    if submit_fn is not None and not callable(submit_fn):
        found.append('argument: submit_fn is neither None nor callable')
    if found:
        return 'status', found
    for name, value in (('write_set', write_set), ('forbidden', forbidden)):
        if not (isinstance(value, list) and value
                and all(isinstance(p, str) and conformance.pattern_ok(p) for p in value)):
            found.append('scope: %s is not a non-empty list of well-formed patterns' % name)
    return ('scope', found) if found else None


def _config(output):
    """Step 2: (the refused keys, the last user.name bytes, the last user.email bytes, None) or (None, None, None, a
    finding). Pure; raises nothing."""
    if not isinstance(output, bytes):
        return None, None, None, 'config: the configuration answer is not bytes'
    parts = output.split(b'\0')
    if parts[-1] != b'':
        return None, None, None, 'config: the configuration answer does not end in NUL'
    refused, name, email = [], None, None
    for part in parts[:-1]:
        key, _, value = part.partition(b'\n')
        if key == b'':
            return None, None, None, 'config: the configuration answer has an empty key'
        low = key.lower()
        if low.startswith(b'filter.') or low == b'core.worktree':
            refused.append(key)
        elif low == b'user.name':
            name = value
        elif low == b'user.email':
            email = value
    return refused, name, email, None


def _identity(name, email):
    """A mapping of the name and the e-mail, or None."""
    try:
        got = {'name': name.decode('utf-8'), 'email': email.decode('utf-8')}
    except (AttributeError, UnicodeError):
        return None
    if all(v and not any(c in v for c in _UNSAFE) for v in got.values()):
        return got
    return None


def _status_entries(output):
    """Step 4: ([(the two status characters, the path bytes)] in git's order, None) or (None, a finding). The form
    rules of launcher._root_entries: bytes, a final NUL, no "##" entry, two status characters from the fixed set, a
    space, a non-empty path."""
    if not isinstance(output, bytes):
        return None, 'status: git status gave output that is not bytes'
    parts = output.split(b'\0')
    if parts[-1] != b'':
        return None, 'status: git status gave an answer that does not end in the NUL of its last entry'
    entries = []
    for part in parts[:-1]:
        if part[:2] == b'##':
            return None, 'status: git status gave a branch entry (%r)' % part[:_KEY_CUT]
        if len(part) < 4 or part[0] not in _STATUS_CHARS or part[1] not in _STATUS_CHARS or part[2:3] != b' ':
            return None, 'status: git status gave an entry out of form (%r)' % part[:_KEY_CUT]
        entries.append((part[:2], part[3:]))
    return entries, None


def _classes(entries):
    """(the paths in order and the mapping path to class, None) or (None, the findings of a "staged" refusal)."""
    odd = [pair for pair, _ in entries if pair not in _CLASSES]
    if odd:
        return None, ['staged: %d entries are not a plain modification, deletion or untracked file (%s)'
                      % (len(odd), ', '.join(repr(p.decode('ascii')) for p in odd[:_SHOWN]))]
    paths, classes = [], {}
    for pair, raw in entries:
        path = raw.decode('utf-8')
        paths.append(path)
        classes[path] = _CLASSES[pair]
    return (paths, classes), None


def _scope(paths, write_set, forbidden, state_name):
    """Step 5: the findings of the paths that are out of scope (empty when all are in)."""
    state = state_name.lower()
    bad = []
    for path in paths:
        if not conformance.path_ok(path):
            bad.append((path, 'a path that is not well formed'))
        elif path.split('/')[0].lower() == state or any(n.lower() == '.git' for n in path.split('/')):
            bad.append((path, 'a path under the state directory or .git'))
        elif not any(conformance.path_matches(p, path) for p in write_set):
            bad.append((path, 'a path outside the write set'))
        elif any(conformance.path_matches(p, path) for p in forbidden):
            bad.append((path, 'a path under a forbidden pattern'))
    if not bad:
        return []
    return (['scope: %d of %d changed paths are out of scope' % (len(bad), len(paths))] +
            ['scope: %r: %s' % (p[:_KEY_CUT], why) for p, why in bad[:_SHOWN]])


def _message(task_id, token, count):
    return ('AIEOS task submission %s\n\nThe session left %d changed path%s inside the contract\'s write set; this '
            'commit captures %s.\n\nAIEOS-Task: %s\nAIEOS-Fence: %s:%d\n'
            % (task_id, count, '' if count == 1 else 's', 'it' if count == 1 else 'them', task_id, token['epoch'],
               token['counter']))


def _head_ok(read, repo, base_head):
    answer, raised = _call(read, repo, list(_HEAD_ARGS), _TIMEOUT)
    if not _read_ok(answer):
        return ['status: rev-parse HEAD gave no answer (%s)' % (raised or 'not a clean answer')]
    try:
        head = answer['out'].decode('ascii').strip()
    except UnicodeError:
        return ['status: rev-parse HEAD gave a non-ASCII answer']
    if head != base_head:
        return ['status: HEAD is not the head the session was granted at (%r)' % head[:_KEY_CUT]]
    return []


def _before_capture(repo, base_head, write_set, forbidden, state_name, read):
    """Steps 2 to 6: (None, the identity, the paths, the classes) or (the refusal or 'none' mapping, None, None, None)."""
    answer, raised = _call(read, repo, list(gitread.CONFIG_LIST), _TIMEOUT)
    if not _read_ok(answer):
        return _refused('config', ['config: git config gave no answer (%s)' % (raised or 'not a clean answer')]), None, None, None
    keys, name, email, found = _config(answer['out'])
    if found is not None:
        return _refused('config', [found]), None, None, None
    if keys:
        return _refused('config', ['config: the configuration names filter driver or work tree keys: %d' % len(keys)] +
                        ['config: key %r' % k[:_KEY_CUT] for k in keys[:_SHOWN]]), None, None, None
    identity = _identity(name, email)
    if identity is None:
        return _refused('identity', ['identity: user.name or user.email is absent, empty or unsafe']), None, None, None
    found = _head_ok(read, repo, base_head)
    if found:
        return _refused('status', found), None, None, None
    answer, raised = _call(read, repo, list(gitread.STATUS_HEAD) + [':(exclude)' + state_name], _TIMEOUT)
    if not _read_ok(answer):
        return _refused('status', ['status: git status gave no answer (%s)' % (raised or 'not a clean answer')]), None, None, None
    entries, found = _status_entries(answer['out'])
    if found is not None:
        return _refused('status', [found]), None, None, None
    try:
        got, found = _classes(entries)
    except UnicodeError:
        return _refused('status', ['status: a changed path is not UTF-8']), None, None, None
    if got is None:
        return _refused('staged', found), None, None, None
    paths, classes = got
    found = _scope(paths, write_set, forbidden, state_name)
    if found:
        return _refused('scope', found), None, None, None
    if not paths:
        return _out('none', None, ['capture: no changed path in the working tree']), None, None, None
    return None, identity, paths, classes


def _after_capture(root, repo, task_id, commit, paths, classes, state_name, clock, recorder, restore, submit_fn):
    """Steps 8 and 9, after a done capture of commit."""
    now2, raised = _call(clock)
    if raised is not None or not _utc_whole(now2):
        return _refused('submit', ['submit: the clock gave no timezone-aware UTC time with whole seconds (%s)'
                                   % (raised or 'out of form')], commit, paths)
    event_id = hashlib.sha256('\n'.join((_EVENT_TYPE, task_id, commit)).encode('utf-8')).hexdigest()
    answer, raised = _call(submit.submit if submit_fn is None else submit_fn, root, repo, commit, task_id, event_id,
                           recorder, now2)
    if raised is not None or not isinstance(answer, dict) or answer.get('result') not in _SUBMITTED:
        shown = raised or (answer.get('result') if isinstance(answer, dict) else type(answer).__name__)
        return _refused('submit', ['submit: the submission gave %s (the commit and the ref stay, nothing is restored)'
                                   % shown] + _strs(answer.get('findings') if isinstance(answer, dict) else None),
                        commit, paths)
    findings = ['submit: %s' % answer['result']] + _strs(answer.get('findings'))
    back, raised = _call(restore, repo, paths, classes, state_name)
    if raised is not None or not isinstance(back, dict) or back.get('result') != 'done':
        shown = raised or (back.get('result') if isinstance(back, dict) else type(back).__name__)
        return _refused('capture', findings + ['restore: the restore gave %s' % shown] +
                        _strs(back.get('findings') if isinstance(back, dict) else None), commit, paths)
    return _out('done', None, findings + ['restore: done'], commit, paths)


def capture_and_submit(root, repo, task_id, token, base_head, write_set, forbidden, state_name, clock, recorder, read,
                       capture, restore, submit_fn=None):
    """The step of the module's docstring; a mapping with exactly result, reason, findings, commit and paths."""
    try:
        refusal = _arguments(root, repo, task_id, token, base_head, write_set, forbidden, state_name, clock, recorder,
                             read, capture, restore, submit_fn)
        if refusal is not None:
            return _refused(refusal[0], refusal[1])
        stop, identity, paths, classes = _before_capture(repo, base_head, write_set, forbidden, state_name, read)
        if stop is not None:
            return stop
        ref = 'refs/heads/task/' + task_id
        answer, raised = _call(capture, repo, ref, base_head, paths, _message(task_id, token, len(paths)), identity,
                               state_name)
        commit = answer.get('commit') if isinstance(answer, dict) else None
        if not (raised is None and isinstance(answer, dict) and answer.get('result') == 'done'
                and isinstance(commit, str) and _HEX40.fullmatch(commit) is not None):
            shown = raised or (answer.get('reason') if isinstance(answer, dict) else type(answer).__name__)
            return _refused('capture', ['capture: the capture gave %s' % shown] +
                            _strs(answer.get('findings') if isinstance(answer, dict) else None))
        return _after_capture(root, repo, task_id, commit, paths, classes, state_name, clock, recorder, restore,
                              submit_fn)
    except Exception as exc:
        return _refused('capture', ['capture: a step raised %s' % type(exc).__name__])

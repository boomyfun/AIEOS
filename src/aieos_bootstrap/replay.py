"""The replay adapter of gov-AIEOS (task TASK-051; specification 5 revision 3, section 5 and section 11 point 9): it
replays one recorded session against the core, through the adapter's three calls (adapter.start, adapter.submit,
adapter.end), deterministically and with no model call (INV-001).

``replay(document, root, functions=None)`` takes one replay document as a mapping (the caller parses it; this module
opens no file) and, in order (AC7):

1. checks the document's form (AC6): exactly the keys replay_id, recorder (starting with "replay:", so that its
   records are never taken for a live session's), epoch, setup, session, submission and end_at; every time a text in
   UTC with whole seconds, "YYYY-MM-DDTHH:MM:SSZ";
2. reads the log through read_log and opens the store with the document's epoch through open_store; unless the log is
   empty and the store is new (the document's epoch, counter 0), it refuses with reason "store" before any append and
   calls nothing else, so replayed records never enter a project's event log (specification 5 line 48; N1 of
   decision D-984);
3. appends each setup event through append_event, with the document's recorder;
4. calls adapter.start with the session's values; when a lease is granted and the document states an expected token,
   compares the two, a difference giving "refused", reason "token" (M2 of decision D-983: the epoch, the times and the
   ids come from the document, so the grant's token is deterministic);
5. calls adapter.submit when the document has a submission, with a read function that answers only "cat-file -t" and
   "cat-file -p" of the document's commit from its commit_text, so a replay needs no Git repository and starts no
   process (submit.submit's repo argument is the root, which that read function never reads; so a submission is
   replayed only under an absolute root, as submit.submit requires of a repository path);
6. calls adapter.end with the session's id, the granted token (or None) and end_at; end is called after a granted
   lease even when a later step refused, so a replay leaves no lease it could release (AC8).

Every call passes the root it was given and the document's recorder; this module names no other root and no
project-state directory. The result (AC8) is a mapping with exactly RESULT_KEYS; its steps list one entry per call
made, in order, each a mapping with exactly the keys step and result, in a form that two runs over equal inputs give
equal. ``functions``, when given, replaces any of open_store, append_event, start_session, end_session, read_log,
grant_lease, release_lease_token, held_lease and resume_check.check (under that key), for tests; each defaults at call
time to the writer's function (and resume_check.check to execute's own default).

Limits (AC9), stated: no observation and no violation in the replay sequence, although specification 5 section 5 line
46 lists observations (their record keys are for specification 2's next revision, section 11 points 3 and 4);
abnormal ends beyond the lease's expiry are not handled (section 11 point 10); the token is the grant's, not read from
the document (M2 of decision D-983, a stated departure from line 49's wording, with the same outcome: two runs give
equal records); the commit is read from the document, so a replay shows the core's handling of a recorded commit,
never that a runtime made it; a passing replay shows how the core handles a recorded session, never that any hook
observes anything (C6 stays unmeasured); a run against the real writer's files is not tested in task TASK-051 (its
tests open no file; N2 of decision D-984); one run at a time (the writer's limit).
"""

import datetime
import re

from aieos_bootstrap import adapter
from aieos_bootstrap import writer

RESULT_KEYS = ('result', 'reason', 'findings', 'steps', 'fencing_token')
DOCUMENT_KEYS = frozenset({'replay_id', 'recorder', 'epoch', 'setup', 'session', 'submission', 'end_at'})
SETUP_KEYS = frozenset({'type', 'payload', 'event_id', 'appended_at', 'task_id'})
SESSION_KEYS = frozenset({'task_id', 'session_id', 'holder', 'inputs', 'code_sha256', 'start_at', 'expires_at',
                          'expected_token'})
SUBMISSION_KEYS = frozenset({'commit_id', 'commit_text', 'event_id', 'at'})
FUNCTION_KEYS = frozenset({'open_store', 'append_event', 'start_session', 'end_session', 'read_log', 'grant_lease',
                           'release_lease_token', 'held_lease', 'resume_check.check'})
RECORDER_PREFIX = 'replay:'
_TIME = re.compile(r'([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})Z')
_TASK = re.compile(r'TASK-[0-9]+')
_HEX64 = re.compile(r'[0-9a-f]{64}')
_HEX40 = re.compile(r'[0-9a-f]{40}')
_UTC = datetime.timezone.utc


class _Bad(Exception):
    """The document is out of form: its findings."""


def _text(value):
    return isinstance(value, str) and value != ''


def _time(value, what, found):
    """A document time as a datetime in UTC, or None with a finding."""
    m = _TIME.fullmatch(value) if isinstance(value, str) else None
    if m is None:
        found.append('document: %s is not a time "YYYY-MM-DDTHH:MM:SSZ"' % what)
        return None
    try:
        return datetime.datetime(*(int(g) for g in m.groups()), tzinfo=_UTC)
    except ValueError:
        found.append('document: %s is not a real date and time' % what)
        return None


def _keys(value, keys, what, found):
    if not isinstance(value, dict) or set(value) != keys:
        found.append('document: %s is not a mapping with exactly the keys %s' % (what, ', '.join(sorted(keys))))
        return False
    return True


def _token_form(token):
    return (isinstance(token, dict) and set(token) == {'epoch', 'counter'} and _text(token['epoch'])
            and type(token['counter']) is int and token['counter'] >= 0)


def _read_document(document):
    """AC6: the document's values, with its times read into datetimes; raises _Bad with the findings."""
    found = []
    if not _keys(document, DOCUMENT_KEYS, 'the document', found):
        raise _Bad(found)
    if not _text(document['replay_id']):
        found.append('document: replay_id is not a non-empty string')
    rec = document['recorder']
    if not (isinstance(rec, str) and rec.startswith(RECORDER_PREFIX) and len(rec) > len(RECORDER_PREFIX)):
        found.append('document: recorder does not start with "replay:" followed by a name')
    if not _text(document['epoch']):
        found.append('document: epoch is not a non-empty string')
    setup = []
    if not isinstance(document['setup'], list):
        found.append('document: setup is not a list')
    else:
        for i, event in enumerate(document['setup']):
            if not _keys(event, SETUP_KEYS, 'setup event %d' % i, found):
                continue
            if not _text(event['type']) or not _text(event['event_id']):
                found.append('document: setup event %d has no type or event_id text' % i)
            if event['task_id'] is not None and not (isinstance(event['task_id'], str)
                                                     and _TASK.fullmatch(event['task_id'])):
                found.append('document: setup event %d has a task_id that is neither None nor a task id' % i)
            at = _time(event['appended_at'], 'setup event %d appended_at' % i, found)
            setup.append((event['type'], event['payload'], event['event_id'], at, event['task_id']))
    session = document['session']
    s = None
    if _keys(session, SESSION_KEYS, 'session', found):
        if not (isinstance(session['task_id'], str) and _TASK.fullmatch(session['task_id'])):
            found.append('document: session task_id is not "TASK-" followed by digits')
        for k in ('session_id', 'holder'):
            if not _text(session[k]):
                found.append('document: session %s is not a non-empty string' % k)
        if not isinstance(session['inputs'], dict):
            found.append('document: session inputs is not a mapping')
        if not (isinstance(session['code_sha256'], str) and _HEX64.fullmatch(session['code_sha256'])):
            found.append('document: session code_sha256 is not 64 lowercase hex characters')
        if session['expected_token'] is not None and not _token_form(session['expected_token']):
            found.append('document: session expected_token is neither None nor {epoch, counter}')
        start_at = _time(session['start_at'], 'session start_at', found)
        expires_at = _time(session['expires_at'], 'session expires_at', found)
        if start_at is not None and expires_at is not None and not expires_at > start_at:
            found.append('document: session expires_at is not after start_at')
        s = dict(session, start_at=start_at, expires_at=expires_at)
    sub = document['submission']
    u = None
    if sub is not None and _keys(sub, SUBMISSION_KEYS, 'submission', found):
        if not (isinstance(sub['commit_id'], str) and _HEX40.fullmatch(sub['commit_id'])):
            found.append('document: submission commit_id is not 40 lowercase hex characters')
        if not isinstance(sub['commit_text'], str):
            found.append('document: submission commit_text is not a string')
        if not _text(sub['event_id']):
            found.append('document: submission event_id is not a non-empty string')
        u = dict(sub, at=_time(sub['at'], 'submission at', found))
    end_at = _time(document['end_at'], 'end_at', found)
    if found:
        raise _Bad(found)
    return {'replay_id': document['replay_id'], 'recorder': rec, 'epoch': document['epoch'], 'setup': setup,
            'session': s, 'submission': u, 'end_at': end_at}


def _commit_reader(commit_id, commit_text):
    """AC7: a read function in gitread.run's form that answers only the two reads submit.submit makes."""
    body = commit_text.encode('utf-8')

    def read(repo, args):
        if list(args) == ['cat-file', '-t', commit_id]:
            return {'exit': 0, 'out': b'commit\n', 'err': b'', 'error': None}
        if list(args) == ['cat-file', '-p', commit_id]:
            return {'exit': 0, 'out': body, 'err': b'', 'error': None}
        return {'exit': None, 'out': b'', 'err': b'', 'error': 'the replay answers only cat-file -t and -p of its commit'}
    return read


def _summary(r):
    """A step's adapter result in a form that compares equal between runs: its keys without core, and core's
    result and reason."""
    core = r.get('core') if isinstance(r, dict) else None
    out = {k: r.get(k) for k in adapter.RESULT_KEYS if k != 'core'} if isinstance(r, dict) else {'result': None}
    out['core'] = ({'result': core.get('result'), 'reason': core.get('reason')} if isinstance(core, dict) else None)
    return out


def _write_summary(w):
    return {'result': getattr(w, 'result', None), 'reason': getattr(w, 'reason', None), 'seq': getattr(w, 'seq', None)}


def _result(result, reason=None, findings=(), steps=(), fencing_token=None):
    return {'result': result, 'reason': reason, 'findings': list(findings), 'steps': list(steps),
            'fencing_token': fencing_token}


def replay(document, root, functions=None):
    """Replay one recorded session from a replay document under ``root`` (TASK-051 AC6 to AC8); returns a mapping with
    RESULT_KEYS."""
    if functions is None:
        functions = {}
    if not isinstance(functions, dict) or not set(functions) <= FUNCTION_KEYS:
        return _result('refused', 'document', ['document: functions is not a mapping with only the keys %s'
                                               % ', '.join(sorted(FUNCTION_KEYS))])
    if not _text(root):
        return _result('refused', 'document', ['document: root is not a non-empty string'])
    try:
        d = _read_document(document)
    except _Bad as bad:
        return _result('refused', 'document', bad.args[0])
    except Exception as exc:  # AC8: no exception escapes
        return _result('refused', 'document', ['document: reading it raised %s' % type(exc).__name__])
    f = dict(functions)
    read_log = f.get('read_log', writer.read_log)
    open_store = f.get('open_store', writer.open_store)
    append_event = f.get('append_event', writer.append_event)
    steps = []

    # N1 of decision D-984: an empty log and a new store, or nothing at all.
    try:
        log = read_log(root)
        steps.append({'step': 'read_log', 'result': {'bytes': len(log) if isinstance(log, bytes) else None}})
        if not (isinstance(log, bytes) and log == b''):
            return _result('refused', 'store', ['store: the log under the root is not empty; a replay writes only '
                                                'into an empty log'], steps)
        opened = open_store(root, d['epoch'])
        steps.append({'step': 'open_store', 'result': opened if isinstance(opened, dict) else None})
        if opened != {'epoch': d['epoch'], 'counter': 0}:
            return _result('refused', 'store', ['store: the store is not new with the document\'s epoch and counter '
                                                '0'], steps)
    except Exception as exc:  # AC8
        return _result('refused', 'store', ['store: reading the log or opening the store raised %s'
                                            % type(exc).__name__], steps)

    for event_type, payload, event_id, at, task_id in d['setup']:
        try:
            w = append_event(root, event_type, payload, event_id, at, d['recorder'], task_id=task_id)
        except Exception as exc:  # AC8
            return _result('refused', 'setup', ['setup: the append of %s raised %s' % (event_id, type(exc).__name__)],
                           steps)
        steps.append({'step': 'append_event', 'result': _write_summary(w)})
        if getattr(w, 'result', None) != 'appended':
            return _result('refused', 'setup', ['setup: the append of %s gave %r' % (event_id, getattr(w, 'result',
                                                                                                   None))], steps)

    s = d['session']
    started = adapter.start(root, s['task_id'], s['session_id'], s['holder'], s['inputs'], s['code_sha256'],
                            s['expires_at'], d['recorder'], s['start_at'], start_session=f.get('start_session'),
                            read_log=f.get('read_log'), append=f.get('append_event'), grant=f.get('grant_lease'),
                            release=f.get('release_lease_token'), held=f.get('held_lease'),
                            check=f.get('resume_check.check'))
    steps.append({'step': 'start', 'result': _summary(started)})
    if started['result'] != 'done':
        return _result('refused', 'start', ['start: %s' % x for x in started['findings']], steps)
    token = started['fencing_token']

    def finish(reason, findings):
        ended = adapter.end(root, s['task_id'], s['session_id'], token, d['end_at'],
                            release_lease_token=f.get('release_lease_token'), end_session=f.get('end_session'))
        steps.append({'step': 'end', 'result': _summary(ended)})
        if reason is None and ended['result'] != 'done':
            return _result('refused', 'end', ['end: %s' % x for x in ended['findings']], steps, token)
        if reason is None:
            return _result('done', None, [], steps, token)
        return _result('refused', reason, findings, steps, token)

    expected = s['expected_token']
    if token is not None and expected is not None and token != expected:
        return finish('token', ['token: the granted token %r is not the document\'s expected %r' % (token, expected)])

    u = d['submission']
    if u is not None:
        submitted = adapter.submit(root, root, u['commit_id'], s['task_id'], u['event_id'],
                                   d['recorder'], u['at'], read=_commit_reader(u['commit_id'], u['commit_text']),
                                   append=f.get('append_event'), release=f.get('release_lease_token'),
                                   held=f.get('held_lease'))
        steps.append({'step': 'submit', 'result': _summary(submitted)})
        if submitted['result'] != 'done':
            return finish('submit', ['submit: %s' % x for x in submitted['findings']])
    return finish(None, [])

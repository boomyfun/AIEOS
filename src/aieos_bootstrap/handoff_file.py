"""The handoff file of gov-AIEOS (task TASK-087; specification 7 revision 2, section 7; specification 6 revision 7,
sections 4 and 7; specification 2 revision 10, section 5.2; DEF-0095): the file handoffs/<task>-<session>.md in the
project-state directory, composed from the session's handoff claim records in the event log, which mcp_server's
handoff tool (task TASK-079) appends, and written through the core's writer, create-only.

``compose(log, task_id, session_id, commit)`` is pure. From the log's bytes it takes the payloads of the
"record.added" events that are claims of the session and the task whose refers_to names
"handoffs/<task>-<session>.md#<list>/<n>", checks every list and place, and returns a mapping with exactly the keys
result, path, text and findings: "none" when the session made no handoff (no file), "composed" with the path and the
text, or "refused" with findings. The text is specification 2 section 5.2's front matter: task, session and commit,
then the six lists in HANDOFF_LISTS order, each item a JSON string, with no body.

``write(root, task_id, session_id, commit, read_log=None, write_handoff=None, fencing_token=None)`` reads the log once,
composes, and on "composed" writes the file once through writer.write_handoff; it returns a mapping with exactly the
keys result ("written", "none" or "refused"), reason, findings and path. Each callee defaults at call time. With a
fencing_token (a mapping, with commit None; task TASK-111) it first looks in the same log for the commit the session
submitted: the task.submitted events of the task that carry that token and are not compensating. Exactly one such
event with a commit id in form gives that commit; none gives commit None with no finding; more than one such event, a
matching event repeated under one event id with other content, a commit out of form, a token that cannot be written as
canonical JSON or a log line that cannot be read gives commit None and a finding, and the findings ride in the result.

Stated limits (the contract's):
- launcher.launch_outside (task TASK-094) calls write after the launcher's end, and since task TASK-111 it passes the
  grant's fencing token, so the commit the session submitted is found in the log; the shipped command, which has no
  runtime starter, does not write the handoff file in a real session;
- the match is on the fence token only: a compensating submission (recovery's) is never matched; a session that
  submitted but made no handoff call gets no file; with two matches the file is written with commit null and a
  finding; the lookup reads the log's lines as records.check_log does (a repeated key, NaN and Infinity refused) but
  skips blank lines, does not refuse a CR byte (JSON takes it as white space; a byte-order mark at the start of a line
  is refused by the JSON reader and gives a finding), does not check the token's form, and checks a repeated event id
  only among the events that carry the token (records.check_log refuses the whole log for an event id repeated with
  other content anywhere); it reads each line's JSON only, so it does not check what check_log also checks (the
  envelope keys, seq continuity, appended_at, the forms of task_id, token and payload): a matching task.submitted that
  check_log would flag still gives its commit, and a task.submitted of the task that carries the token but whose payload
  is not an object, or whose compensating is not the boolean false, is not matched and gives no finding (check_log
  flags it); eventlog.append itself refuses a task.submitted with no fencing_token at the fence (eventlog.py
  _needs_lease, lines 112-114), so such an event is not appended; it takes a commit id as 40 lowercase hexadecimal characters only
  (records.py also accepts 64); a commit with no usable AIEOS-Fence trailer leaves no event with the grant's token, so
  the commit is null; abnormal ends still write none; a grant whose token is None (an out-of-form grant) takes the
  path without a token: commit null and no finding;
- the file is not committed by the core; how it reaches Git and how it stays out of a later session's commit stay
  open;
- the Work Order's reader reads the last handoff elsewhere at the base, so the reader's place and the last handoff
  stay open (DEF-0095);
- with no fencing_token it writes the caller's commit as given, since the log ties no submission to a session without
  a token;
- a handoff cut off at any point is composed as a complete one with fewer items, since the records carry no item
  count;
- create-only is the writer's size check after opening in append mode, not an exclusive create;
- session ids "." and ".." never get a file; abnormal ends stay open.

It never raises; it opens no file and writes nothing itself; it reads no clock and no environment.
"""

import json
import re

from aieos_bootstrap import writer

HANDOFF_LISTS = ('done', 'not_done', 'assumptions', 'discoveries', 'risks', 'proposals')
COMPOSE_KEYS = ('result', 'path', 'text', 'findings')
WRITE_KEYS = ('result', 'reason', 'findings', 'path')
_TASK = re.compile(r'TASK-[0-9]+')
_SESSION = re.compile(r'[A-Za-z0-9._-]{1,128}')
_HEX40 = re.compile(r'[0-9a-f]{40}')
_PLACE = re.compile(r'[1-9][0-9]*')
# The three characters a YAML 1.1 reader takes as line breaks, written as JSON's six-character escapes.
_BREAKS = (0x85, 0x2028, 0x2029)


def _session_ok(session_id):
    return isinstance(session_id, str) and _SESSION.fullmatch(session_id) is not None and session_id not in ('.', '..')


def _argument_findings(task_id, session_id, commit):
    out = []
    if not (isinstance(task_id, str) and _TASK.fullmatch(task_id)):
        out.append('argument: task_id')
    if not _session_ok(session_id):
        out.append('argument: session_id')
    if not (commit is None or (isinstance(commit, str) and _HEX40.fullmatch(commit))):
        out.append('argument: commit')
    return out


def _quoted(value):
    """A JSON string, with the three YAML 1.1 line breaks escaped."""
    text = json.dumps(value, ensure_ascii=False)
    for code in _BREAKS:
        text = text.replace(chr(code), '\\u%04x' % code)
    return text


def _compose_result(result, path=None, text=None, findings=()):
    return {'result': result, 'path': path, 'text': text, 'findings': list(findings)}


def _claims(log, task_id, session_id):
    """(the items by list and place, the findings) of the log's handoff claims of the session and the task."""
    head = 'handoffs/%s-%s.md#' % (task_id, session_id)
    items = {name: {} for name in HANDOFF_LISTS}
    findings = []
    for number, raw in enumerate(log.split(b'\n'), 1):
        if not raw.strip():
            continue
        try:
            event = json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, ValueError, RecursionError):
            findings.append('log line %d: not a JSON object' % number)
            continue
        if not isinstance(event, dict):
            findings.append('log line %d: not a JSON object' % number)
            continue
        payload = event.get('payload')
        if event.get('type') != 'record.added' or not isinstance(payload, dict):
            continue
        ref = payload.get('refers_to')
        if payload.get('session') != session_id or not (isinstance(ref, str) and ref.startswith('handoffs/')):
            continue
        if payload.get('fact_kind') != 'claim' or payload.get('subject') != task_id:
            continue
        if not ref.startswith(head):
            findings.append('log line %d: refers_to names another file' % number)
            continue
        parts = ref[len(head):].split('/')
        if len(parts) != 2 or parts[0] not in items or not _PLACE.fullmatch(parts[1]):
            findings.append('log line %d: refers_to out of form' % number)
            continue
        text = payload.get('text')
        if not (isinstance(text, str) and text):
            findings.append('log line %d: an empty or non-str text' % number)
            continue
        try:
            text.encode('utf-8')
        except UnicodeEncodeError:
            findings.append('log line %d: a text that does not encode as UTF-8' % number)
            continue
        place = int(parts[1])
        if place in items[parts[0]]:
            findings.append('log line %d: a repeated place in %s' % (number, parts[0]))
            continue
        items[parts[0]][place] = text
    for name in HANDOFF_LISTS:
        if sorted(items[name]) != list(range(1, len(items[name]) + 1)):
            findings.append('%s: a gap in the places' % name)
    return items, findings


def compose(log, task_id, session_id, commit):
    """The handoff file's path and text from the log's bytes, or "none", or "refused" with findings; never raises."""
    try:
        findings = _argument_findings(task_id, session_id, commit)
        if not isinstance(log, bytes):
            findings.append('argument: log')
        if findings:
            return _compose_result('refused', findings=findings)
        items, findings = _claims(log, task_id, session_id)
        if findings:
            return _compose_result('refused', findings=findings)
        if not any(items[name] for name in HANDOFF_LISTS):
            return _compose_result('none')
        lines = ['---', 'task: %s' % task_id, 'session: %s' % _quoted(session_id),
                 'commit: %s' % ('null' if commit is None else _quoted(commit))]
        for name in HANDOFF_LISTS:
            places = sorted(items[name])
            if not places:
                lines.append('%s: []' % name)
                continue
            lines.append('%s:' % name)
            lines.extend('  - %s' % _quoted(items[name][place]) for place in places)
        lines.append('---')
        path = '%s/handoffs/%s-%s.md' % (writer.STATE_DIR, task_id, session_id)
        return _compose_result('composed', path=path, text='\n'.join(lines) + '\n')
    except Exception as e:
        return _compose_result('refused', findings=['compose: an unexpected %s' % type(e).__name__])


def _write_result(result, reason=None, findings=(), path=None):
    return {'result': result, 'reason': reason, 'findings': list(findings), 'path': path}


def _str_items(value):
    """Only the str items of a list or a tuple (DEF-0102's rule); any other value gives none."""
    if isinstance(value, (list, tuple)):
        return [x for x in value if isinstance(x, str)]
    return []


def _pairs(pairs):
    """The object hook of the lookup: a repeated key in one object is refused (records.py's reading)."""
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError('a repeated key')
    return dict(pairs)


def _constant(name):
    """The constant hook of the lookup: NaN and Infinity are refused (records.py's reading)."""
    raise ValueError('a non-finite constant')


def _canonical(value):
    """The text two fencing tokens are compared by (eventlog.py's form)."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def submitted_commit(log, task_id, token):
    """(the commit the session submitted or None, findings) from the log's bytes (task TASK-111): the task.submitted
    events of the task that carry the token and are not compensating; never raises."""
    if not isinstance(log, bytes):
        return None, ['lookup: the log is not bytes']
    try:
        want = _canonical(token)
    except Exception:
        return None, ['lookup: the fencing token cannot be written as canonical JSON']
    seen = {}
    for number, raw in enumerate(log.split(b'\n'), 1):
        if not raw.strip():
            continue
        try:
            event = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs, parse_constant=_constant)
        except Exception:
            return None, ['lookup: log line %d cannot be read' % number]
        if not isinstance(event, dict):
            return None, ['lookup: log line %d is not a JSON object' % number]
        payload = event.get('payload')
        if (event.get('type') != 'task.submitted' or event.get('task_id') != task_id or not isinstance(payload, dict)
                or payload.get('compensating') is not False or 'fencing_token' not in event):
            continue
        try:
            same = _canonical(event['fencing_token']) == want
            identity = json.dumps({k: v for k, v in event.items() if k not in ('seq', 'appended_at')}, sort_keys=True)
        except Exception:
            return None, ['lookup: log line %d cannot be compared' % number]
        if not same:
            continue
        event_id = event.get('event_id')
        if not isinstance(event_id, str):
            return None, ['lookup: log line %d has no event id' % number]
        if event_id in seen and seen[event_id][0] != identity:
            return None, ['lookup: an event id is repeated with other content']
        seen.setdefault(event_id, (identity, payload.get('commit')))
    if not seen:
        return None, []
    if len(seen) > 1:
        return None, ['lookup: more than one task.submitted of the task carries the token']
    commit = list(seen.values())[0][1]
    if not (isinstance(commit, str) and _HEX40.fullmatch(commit)):
        return None, ['lookup: the commit of the task.submitted is out of form']
    return commit, []


def write(root, task_id, session_id, commit, read_log=None, write_handoff=None, fencing_token=None):
    """Read the log once, compose, and write the file once through the writer on "composed"; never raises."""
    try:
        findings = _argument_findings(task_id, session_id, commit)
        if not (isinstance(root, str) and root):
            findings.append('argument: root')
        if fencing_token is not None and not isinstance(fencing_token, dict):
            findings.append('argument: fencing_token')
        elif fencing_token is not None and commit is not None:
            findings.append('argument: commit with a fencing_token')
        for name, callee in (('read_log', read_log), ('write_handoff', write_handoff)):
            if callee is not None and not callable(callee):
                findings.append('argument: %s' % name)
        if findings:
            return _write_result('refused', 'argument', findings)
        read = read_log if read_log is not None else writer.read_log
        put = write_handoff if write_handoff is not None else writer.write_handoff
        try:
            log = read(root)
        except Exception as e:
            return _write_result('refused', 'log', ['log: the read raised %s' % type(e).__name__])
        if not isinstance(log, bytes):
            return _write_result('refused', 'log', ['log: the read gave no bytes'])
        lookup = []
        if fencing_token is not None:
            commit, lookup = submitted_commit(log, task_id, fencing_token)
        composed = compose(log, task_id, session_id, commit)
        if composed['result'] == 'none':
            return _write_result('none', findings=lookup)
        if composed['result'] != 'composed':
            return _write_result('refused', 'claims', composed['findings'] + lookup)
        try:
            answer = put(root, task_id, session_id, composed['text'])
        except Exception as e:
            return _write_result('refused', 'write', ['write: the write raised %s' % type(e).__name__] + lookup)
        try:
            done = isinstance(answer, writer.StoreResult) and answer.result == 'done'
            more = [] if done else _str_items(getattr(answer, 'findings', None))
        except Exception as e:
            return _write_result('refused', 'write', ['write: an answer that raised %s' % type(e).__name__] + lookup)
        if done:
            return _write_result('written', path=composed['path'], findings=lookup)
        return _write_result('refused', 'write', ['write: not done'] + more + lookup)
    except Exception as e:
        return _write_result('refused', 'argument', ['write: an unexpected %s' % type(e).__name__])

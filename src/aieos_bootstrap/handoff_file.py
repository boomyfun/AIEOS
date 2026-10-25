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

``write(root, task_id, session_id, commit, read_log=None, write_handoff=None)`` reads the log once, composes, and on
"composed" writes the file once through writer.write_handoff; it returns a mapping with exactly the keys result
("written", "none" or "refused"), reason, findings and path. Each callee defaults at call time.

Stated limits (the contract's):
- launcher.launch_outside (task TASK-094) calls write after the launcher's end with commit None, so nothing calls
  write after a submission, and the shipped command, which has no runtime starter, does not write the handoff file
  in a real session;
- the file is not committed by the core; how it reaches Git and how it stays out of a later session's commit stay
  open;
- the Work Order's reader reads the last handoff elsewhere at the base, so the reader's place and the last handoff
  stay open (DEF-0095);
- it writes the caller's commit as given, since the log ties no submission to a session;
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


def write(root, task_id, session_id, commit, read_log=None, write_handoff=None):
    """Read the log once, compose, and write the file once through the writer on "composed"; never raises."""
    try:
        findings = _argument_findings(task_id, session_id, commit)
        if not (isinstance(root, str) and root):
            findings.append('argument: root')
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
        composed = compose(log, task_id, session_id, commit)
        if composed['result'] == 'none':
            return _write_result('none')
        if composed['result'] != 'composed':
            return _write_result('refused', 'claims', composed['findings'])
        try:
            answer = put(root, task_id, session_id, composed['text'])
        except Exception as e:
            return _write_result('refused', 'write', ['write: the write raised %s' % type(e).__name__])
        try:
            done = isinstance(answer, writer.StoreResult) and answer.result == 'done'
            more = [] if done else _str_items(getattr(answer, 'findings', None))
        except Exception as e:
            return _write_result('refused', 'write', ['write: an answer that raised %s' % type(e).__name__])
        if done:
            return _write_result('written', path=composed['path'])
        return _write_result('refused', 'write', ['write: not done'] + more)
    except Exception as e:
        return _write_result('refused', 'argument', ['write: an unexpected %s' % type(e).__name__])

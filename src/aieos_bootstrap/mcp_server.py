"""The MCP server's frame and its status tool (task TASK-078; specification 6 revision 6, sections 3, 4 and 8; M6's
first slice).

What it does:
- MCP over stdio, one JSON-RPC 2.0 message per line, in the Python 3 standard library only (specification 6 section 3,
  the bootstrap limit). ``main(stdin, stdout, environ, clock)`` reads lines until the end of the input and writes each
  answer as one line of JSON; it returns 0 and never raises.
- The methods are initialize, notifications/initialized, tools/list and tools/call, and no other. initialize answers
  the protocol version "2025-06-18", a stated choice; nothing else is negotiated. tools/list lists one tool, status;
  the six other tools of section 4 are added by the slices that build them.
- Each line is taken in this order: an empty or whitespace-only line gets no answer; a line that is not JSON answers
  -32700 with id null; a JSON value that is not an object answers -32600 with id null; an object whose "jsonrpc" is
  not "2.0", whose "method" is not a str, or whose "id" is present but not a str, an int (not a bool) or null answers
  -32600 with its id when that id is valid, else null; an object without "id" is a notification and gets no answer;
  then the methods; tools/call whose params is not an object, whose "name" is absent or not a str, or which names any
  tool but status answers -32602; any other method answers -32601. An error inside the frame itself, which no case
  above reaches, answers -32603 with id null rather than ending the loop.
- The identity comes from the environment: AIEOS_SESSION_ID of the form [A-Za-z0-9._-]{1,128} and AIEOS_ROOT, an
  absolute path (the names of claude_code_pretool_hook.py). AIEOS_BASE is not read in this slice.
- status reads the store only through writer.session_leases (INV-004; specification 6 section 2) and writes nothing:
  this module opens no file and calls no other writer function. Its answers: {"task": null, "lease": "none"} for an
  ended session, a session with no lease row, or a session id the store never saw; {"task", "lease": "live",
  "expires_at"} for exactly one unexpired row; {"task", "lease": "expired"} for rows none of which is unexpired, the
  task being the row with the highest fencing counter; the error no_session when the identity is missing or out of
  form or the root or the store is not there; the error core_error for more than one unexpired row (the one-lease
  rule as this task reads it), for an argument refusal (the server's own clock or timeout), for an unreadable, linked
  or malformed store and for any other answer. A tool error is a tools/call result with isError true and the text
  {"error": <word>}; these answer forms are stated choices.

Limits, stated: "expired" exists only between a lease's expiry and the next expire_leases, which removes the row; a
session's state is what the store holds at the read. The store's read is writer.session_leases', a hand-kept copy of
session_lease's transaction steps. MCP alone is at most tier T2, as a target and unmeasured; nothing here is measured.
Whether a server started by a runtime inherits the runtime's environment is unmeasured. Launching this program in a
runtime and connecting it to one (a Claude Code setting) are the owner's acts (specification 6 section 10; DM A51 item
(4)); this module does neither, and nothing runs it but its tests.
"""

import datetime
import json
import os
import re
import sys

from aieos_bootstrap import writer

PROTOCOL_VERSION = '2025-06-18'
SERVER_INFO = {'name': 'aieos', 'version': '0.1'}
SESSION_VAR = 'AIEOS_SESSION_ID'
ROOT_VAR = 'AIEOS_ROOT'
ERRORS = ('no_session', 'no_lease', 'lease_expired', 'not_found', 'out_of_scope', 'invalid_input', 'core_error')
STATUS_TOOL = {'name': 'status',
               'description': 'The task and lease state of this session, as the core store holds it; writes nothing.',
               'inputSchema': {'type': 'object', 'properties': {}}}
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
_SESSION = re.compile(r'[A-Za-z0-9._-]{1,128}')
_NONE = {'task': None, 'lease': 'none'}


def _identity(environ):
    """(session id, root) from the environment, or None when either is missing or out of form."""
    session_id = environ.get(SESSION_VAR)
    root = environ.get(ROOT_VAR)
    if not isinstance(session_id, str) or not _SESSION.fullmatch(session_id):
        return None
    if not isinstance(root, str) or not root or not os.path.isabs(root):
        return None
    return session_id, root


def _time_text(value):
    return value.strftime('%Y-%m-%dT%H:%M:%SZ')


def _lease_ok(lease):
    return (isinstance(lease, dict) and isinstance(lease.get('task_id'), str)
            and isinstance(lease.get('expires_at'), datetime.datetime)
            and isinstance(lease.get('fencing_token'), dict)
            and type(lease['fencing_token'].get('counter')) is int)


def _status_of(answer, now):
    """The status object, or an error word, from writer.session_leases' answer."""
    if not isinstance(answer, writer.StoreResult):
        return None, 'core_error'
    if answer.result == 'refused':
        if answer.reason == 'session':
            return dict(_NONE), None
        if answer.reason in ('root', 'no_store'):
            return None, 'no_session'
        return None, 'core_error'
    value = answer.value
    if answer.result != 'done' or answer.reason != 'rows' or not isinstance(value, dict):
        return None, 'core_error'
    ended, leases = value.get('ended'), value.get('leases')
    if not isinstance(ended, bool) or not isinstance(leases, list) or not all(_lease_ok(x) for x in leases):
        return None, 'core_error'
    if ended or not leases:
        return dict(_NONE), None
    live = [x for x in leases if x['expires_at'] > now]
    if len(live) > 1:
        return None, 'core_error'
    if len(live) == 1:
        return {'task': live[0]['task_id'], 'lease': 'live', 'expires_at': _time_text(live[0]['expires_at'])}, None
    last = max(leases, key=lambda x: x['fencing_token']['counter'])
    return {'task': last['task_id'], 'lease': 'expired'}, None


def status(environ, now):
    """The status tool: (the status object, None) or (None, an error word of specification 6 section 8)."""
    try:
        identity = _identity(environ)
        if identity is None:
            return None, 'no_session'
        session_id, root = identity
        return _status_of(writer.session_leases(root, session_id, now), now)
    except Exception:
        return None, 'core_error'


def _tool_result(obj, is_error):
    return {'content': [{'type': 'text', 'text': json.dumps(obj, sort_keys=True)}], 'isError': is_error}


def _error(id_, code, message):
    return {'jsonrpc': '2.0', 'id': id_, 'error': {'code': code, 'message': message}}


def _result(id_, result):
    return {'jsonrpc': '2.0', 'id': id_, 'result': result}


def _valid_id(value):
    return value is None or isinstance(value, str) or (type(value) is int)


def handle(line, environ, clock):
    """The answer to one input line (a dict), or None when the line gets no answer."""
    if isinstance(line, bytes):
        try:
            line = line.decode('utf-8')
        except UnicodeDecodeError:
            return _error(None, PARSE_ERROR, 'Parse error')
    if not line.strip():
        return None
    try:
        msg = json.loads(line)
    except ValueError:
        return _error(None, PARSE_ERROR, 'Parse error')
    if not isinstance(msg, dict):
        return _error(None, INVALID_REQUEST, 'Invalid Request')
    has_id = 'id' in msg
    id_ = msg.get('id')
    if msg.get('jsonrpc') != '2.0' or not isinstance(msg.get('method'), str) or (has_id and not _valid_id(id_)):
        return _error(id_ if has_id and _valid_id(id_) else None, INVALID_REQUEST, 'Invalid Request')
    if not has_id:
        return None
    method = msg['method']
    if method == 'initialize':
        return _result(id_, {'protocolVersion': PROTOCOL_VERSION, 'serverInfo': dict(SERVER_INFO),
                             'capabilities': {'tools': {}}})
    if method == 'tools/list':
        return _result(id_, {'tools': [json.loads(json.dumps(STATUS_TOOL))]})
    if method == 'tools/call':
        params = msg.get('params')
        if not isinstance(params, dict) or not isinstance(params.get('name'), str) or params['name'] != 'status':
            return _error(id_, INVALID_PARAMS, 'Invalid params')
        obj, word = status(environ, clock())
        if word is not None:
            return _result(id_, _tool_result({'error': word}, True))
        return _result(id_, _tool_result(obj, False))
    return _error(id_, METHOD_NOT_FOUND, 'Method not found')


def main(stdin, stdout, environ, clock):
    """Read lines from ``stdin`` until its end, answer each on ``stdout`` as one line of JSON; return 0, never raise."""
    try:
        for line in stdin:
            try:
                answer = handle(line, environ, clock)
            except Exception:
                answer = _error(None, INTERNAL_ERROR, 'Internal error')
            if answer is not None:
                stdout.write(json.dumps(answer, sort_keys=True) + '\n')
                flush = getattr(stdout, 'flush', None)
                if flush is not None:
                    flush()
    except Exception:
        return 0
    return 0


def _clock():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


if __name__ == '__main__':
    sys.exit(main(sys.stdin.buffer, sys.stdout, os.environ, _clock))

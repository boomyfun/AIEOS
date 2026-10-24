"""The MCP server's frame, its status tool, its four claim tools (tasks TASK-078 and TASK-079; specification 6
revision 7, sections 3, 4, 7 and 8; M6's first and second slices) and get_work_order and query (task TASK-083;
specification 6 sections 4, 5 and 8; specification 7 section 6).

What it does:
- MCP over stdio, one JSON-RPC 2.0 message per line, in the Python 3 standard library only (specification 6 section 3,
  the bootstrap limit). ``main(stdin, stdout, environ, clock)`` reads lines until the end of the input and writes each
  answer as one line of JSON; it returns 0 and never raises.
- The methods are initialize, notifications/initialized, tools/list and tools/call, and no other. initialize answers
  the protocol version "2025-06-18", a stated choice; nothing else is negotiated. tools/list lists seven tools, status,
  acknowledge, ask, report, handoff, get_work_order and query, in that order.
- Each line is taken in this order: an empty or whitespace-only line gets no answer; a line that is not JSON, or whose
  JSON nests too deep to read, answers -32700 with id null; a JSON value that is not an object answers -32600 with id
  null; an object whose "jsonrpc" is not "2.0", whose "method" is not a str, or whose "id" is present but not a str, an
  int (not a bool) or null answers -32600 with its id when that id is valid, else null; an object without "id" is a
  notification and gets no answer; then the methods; tools/call whose params is not an object, whose "name" is absent
  or not a str, or which names no listed tool answers -32602; any other method answers -32601. An error inside the
  frame itself, which no case above reaches, answers -32603 with id null rather than ending the loop.
- The identity comes from the environment: AIEOS_SESSION_ID of the form [A-Za-z0-9._-]{1,128} and AIEOS_ROOT, an
  absolute path (the names of claude_code_pretool_hook.py). AIEOS_BASE is read only by _base, for get_work_order and
  query: exactly 40 lowercase hexadecimal characters (specification 7 :45), else no_session; status and the claim
  tools neither need nor read it.
- status reads the store only through writer.session_leases (INV-004; specification 6 section 2) and writes nothing.
  Its answers: {"task": null, "lease": "none"} for an ended session, a session with no lease row, or a session id the
  store never saw; {"task", "lease": "live", "expires_at"} for exactly one unexpired row; {"task", "lease": "expired"}
  for rows none of which is unexpired, the task being the row with the highest fencing counter; the error no_session
  when the identity is missing or out of form or the root or the store is not there; the error core_error for more
  than one unexpired row (the one-lease rule as task TASK-078 reads it), for an argument refusal (the server's own
  clock or timeout), for an unreadable, linked or malformed store and for any other answer. A tool error is a
  tools/call result with isError true and the text {"error": <word>}; these answer forms are stated choices.
- The claim tools acknowledge {assumptions}, ask {question}, report {criteria, notes} and handoff {done, not_done,
  assumptions, discoveries, risks, proposals} take their input from params.arguments and are taken in this order: the
  identity (no_session); the input's shape (invalid_input: every text a non-empty str, acknowledge with one assumption
  at least, report's ac AC followed by digits and a call with no criterion and empty notes refused, handoff's six lists
  all present with one item at least); the lease, read through writer.session_leases (a session never seen, ended or
  with no row no_lease; rows none of which is unexpired lease_expired; more than one unexpired row core_error; root and
  no_store no_session; any other refusal core_error); for handoff the log, read through writer.read_log; then one
  record.added event per item through writer.append_event. An error found before the first append writes nothing.
- Each item's record: {record_id, fact_kind "claim", source_class "agent_declared", recorder "aieos mcp_server,
  session <id>", subject the lease's task, session, text}, a report criterion's with acs [its AC id], a handoff item's
  with refers_to "handoffs/<task>-<session>.md#<list>/<n>"; the event's task_id is the lease's task and its
  fencing_token the lease's token from the store, never from the input; the recorder argument of append_event is the
  record's recorder. The ids: C is the SHA-256 hex of the input as canonical JSON (UTF-8, keys sorted, no
  insignificant whitespace, non-ASCII kept); an item's digest is the SHA-256 hex of the session id, the task id, the
  tool, C, the argument's name L, the place n (from 1) and the item's text joined by LF (a criterion's text being its
  AC id and its text joined by a space; ask's question and report's notes at n 1); the event_id is "mcp-" + digest and
  the record_id "mcp-claim/" + digest. Only an identical call repeats the ids: it is a retry, the log answers
  "duplicate" and the tool answers the same record ids. The success answer is {"records": [the record ids in the order
  appended]}.
- handoff is called once per session: earlier claims whose session is this session id and whose refers_to begins
  "handoffs/" make the call invalid_input unless every one of their record ids is among this call's, which is the
  identical call, a cut-off handoff completed by its retry.
- The fence (specification 6 revision 7 section 8): a lease that changes or expires between the lease read and an
  append is refused by the writer's fence; the tool reads session_leases again and answers its error word, exactly
  one unexpired row answering core_error; the writer's refusal record is the writer's, and the claims appended before
  it stay. Any other append answer, "conflict" among them, any answer of another form and any exception answer
  core_error.
- get_work_order {} and query {ref} (task TASK-083) are taken in this order: the identity and the base (no_session);
  the input's shape (invalid_input: get_work_order's arguments absent, null or {}; query's exactly {ref, a non-empty
  str}); the lease, as the claim tools read it, its task the task (never a value of the input); the log through
  writer.read_log (bytes, else core_error); base_inputs.work_order_inputs(root, base, task, session id, log, read);
  context_compiler.build_work_order. Findings of either give the error {"error": "core_error", "detail": [the
  findings]}. The Work Order is compiled at each call: nothing is cached across calls and nothing is stored, so "the
  same object for the whole session" holds only while the task's last approval and last resume record stay.
  get_work_order answers the Work Order. query answers only the refs the Work Order holds: an item held in full is
  answered as it is, {ref, hash, content}; an item held as a reference is answered from a second build of the same
  inputs with every budget UNBUDGETED, whose item must carry the same hash; every item of a ref in more than one layer
  must carry the same hash; a ref the Work Order does not hold gives out_of_scope, and a ref whose full item cannot be
  produced not_found. Both write nothing; their reads are not in the observed read-set. The departures from
  specification 6 are carried by DEF-0098.

Limits, stated: "expired" exists only between a lease's expiry and the next expire_leases, which removes the row; a
session's state is what the store holds at the read. The store's read is writer.session_leases', a hand-kept copy of
session_lease's transaction steps. Every claim is the agent's statement (agent_declared), nothing here raises its
standing. writer.read_log reads the whole log, with no link check, and writer.append_event makes none either. A retry
after a new lease was granted carries another token and answers core_error. The handoff file itself is the
launcher's (specification 7), not written here. MCP alone is at most tier T2, as a target and unmeasured; nothing here
is measured. Whether a server started by a runtime inherits the runtime's environment is unmeasured. Launching this
program in a runtime and connecting it to one (a Claude Code setting) are the owner's acts (specification 6 section
10; DM A51 item (4)); this module does neither, and nothing runs it but its tests.
"""

import datetime
import hashlib
import json
import os
import re
import sys

from aieos_bootstrap import base_inputs, context_compiler, writer

PROTOCOL_VERSION = '2025-06-18'
SERVER_INFO = {'name': 'aieos', 'version': '0.1'}
SESSION_VAR = 'AIEOS_SESSION_ID'
ROOT_VAR = 'AIEOS_ROOT'
ERRORS = ('no_session', 'no_lease', 'lease_expired', 'not_found', 'out_of_scope', 'invalid_input', 'core_error')
STATUS_TOOL = {'name': 'status',
               'description': 'The task and lease state of this session, as the core store holds it; writes nothing.',
               'inputSchema': {'type': 'object', 'properties': {}}}
HANDOFF_LISTS = ('done', 'not_done', 'assumptions', 'discoveries', 'risks', 'proposals')
_TEXTS = {'type': 'array', 'items': {'type': 'string'}}
CLAIM_TOOLS = [
    {'name': 'acknowledge',
     'description': 'Records each assumption as one claim of this session, under its live lease.',
     'inputSchema': {'type': 'object', 'properties': {'assumptions': _TEXTS}, 'required': ['assumptions']}},
    {'name': 'ask',
     'description': 'Records the question as one claim of this session, under its live lease.',
     'inputSchema': {'type': 'object', 'properties': {'question': {'type': 'string'}}, 'required': ['question']}},
    {'name': 'report',
     'description': 'Records each criterion of the report, and its notes, as claims of this session.',
     'inputSchema': {'type': 'object', 'properties': {
         'criteria': {'type': 'array', 'items': {'type': 'object', 'properties': {
             'ac': {'type': 'string'}, 'text': {'type': 'string'}}, 'required': ['ac', 'text']}},
         'notes': {'type': 'string'}}, 'required': ['criteria', 'notes']}},
    {'name': 'handoff',
     'description': 'Records each item of the six handoff lists as one claim of this session; once per session.',
     'inputSchema': {'type': 'object', 'properties': {k: _TEXTS for k in HANDOFF_LISTS},
                     'required': list(HANDOFF_LISTS)}},
]
WORK_ORDER_TOOLS = [
    {'name': 'get_work_order',
     'description': "The session's Work Order, compiled at the session's base at each call; writes nothing.",
     'inputSchema': {'type': 'object', 'properties': {}}},
    {'name': 'query',
     'description': 'One item the Work Order holds, by its ref, read at the base; writes nothing.',
     'inputSchema': {'type': 'object', 'properties': {'ref': {'type': 'string'}}, 'required': ['ref']}},
]
TOOL_NAMES = ('status',) + tuple(t['name'] for t in CLAIM_TOOLS + WORK_ORDER_TOOLS)
# Every layer's budget for query's second build, above any layer's possible content bytes (budgets take any int above 0).
UNBUDGETED = 1 << 62
RECORDER = 'aieos mcp_server, session %s'
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
_SESSION = re.compile(r'[A-Za-z0-9._-]{1,128}')
_AC = re.compile(r'AC[0-9]+')
_BASE_FORM = re.compile(r'[0-9a-f]{40}')
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


def _rows(answer):
    """(ended, leases) from writer.session_leases' "rows" answer, or None for any other answer."""
    if not isinstance(answer, writer.StoreResult) or answer.result != 'done' or answer.reason != 'rows':
        return None
    value = answer.value
    if not isinstance(value, dict):
        return None
    ended, leases = value.get('ended'), value.get('leases')
    if not isinstance(ended, bool) or not isinstance(leases, list) or not all(_lease_ok(x) for x in leases):
        return None
    return ended, leases


def _status_of(answer, now):
    """The status object, or an error word, from writer.session_leases' answer."""
    if isinstance(answer, writer.StoreResult) and answer.result == 'refused':
        if answer.reason == 'session':
            return dict(_NONE), None
        if answer.reason in ('root', 'no_store'):
            return None, 'no_session'
        return None, 'core_error'
    rows = _rows(answer)
    if rows is None:
        return None, 'core_error'
    ended, leases = rows
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


def _live_lease(answer, now):
    """The one live lease of writer.session_leases' answer and None, or None and an error word (the lease rule)."""
    if isinstance(answer, writer.StoreResult) and answer.result == 'refused':
        if answer.reason == 'session':
            return None, 'no_lease'
        if answer.reason in ('root', 'no_store'):
            return None, 'no_session'
        return None, 'core_error'
    rows = _rows(answer)
    if rows is None:
        return None, 'core_error'
    ended, leases = rows
    if ended or not leases:
        return None, 'no_lease'
    live = [x for x in leases if x['expires_at'] > now]
    if len(live) > 1:
        return None, 'core_error'
    if not live:
        return None, 'lease_expired'
    return live[0], None


def _text(value):
    """A non-empty str that UTF-8 can encode."""
    if not isinstance(value, str) or not value:
        return False
    try:
        value.encode('utf-8')
    except UnicodeEncodeError:
        return False
    return True


def _texts(value):
    return isinstance(value, list) and all(_text(x) for x in value)


def _items(tool, args):
    """The call's items as (L, n, the digest's text, the record's text, the AC id or None), or None for an input out
    of form."""
    if not isinstance(args, dict):
        return None
    if tool == 'acknowledge':
        if set(args) != {'assumptions'} or not _texts(args['assumptions']) or not args['assumptions']:
            return None
        return [('assumptions', n, x, x, None) for n, x in enumerate(args['assumptions'], 1)]
    if tool == 'ask':
        if set(args) != {'question'} or not _text(args['question']):
            return None
        return [('question', 1, args['question'], args['question'], None)]
    if tool == 'report':
        if set(args) != {'criteria', 'notes'} or not isinstance(args['criteria'], list):
            return None
        notes = args['notes']
        if not isinstance(notes, str) or (notes and not _text(notes)):
            return None
        items = []
        for n, c in enumerate(args['criteria'], 1):
            if not (isinstance(c, dict) and set(c) == {'ac', 'text'} and isinstance(c['ac'], str)
                    and _AC.fullmatch(c['ac']) and _text(c['text'])):
                return None
            items.append(('criteria', n, c['ac'] + ' ' + c['text'], c['text'], c['ac']))
        if notes:
            items.append(('notes', 1, notes, notes, None))
        return items or None
    if tool == 'handoff':
        if set(args) != set(HANDOFF_LISTS) or not all(_texts(args[k]) for k in HANDOFF_LISTS):
            return None
        items = [(k, n, x, x, None) for k in HANDOFF_LISTS for n, x in enumerate(args[k], 1)]
        return items or None
    return None


def _digest(*parts):
    return hashlib.sha256('\n'.join(parts).encode('utf-8')).hexdigest()


def _earlier_handoffs(log, session_id):
    """The record ids of the log's claims of this session whose refers_to begins "handoffs/"."""
    found = set()
    for line in log.split(b'\n'):
        if not line.strip():
            continue
        event = json.loads(line.decode('utf-8'))
        payload = event.get('payload') if isinstance(event, dict) else None
        if (isinstance(payload, dict) and event.get('type') == 'record.added' and payload.get('session') == session_id
                and isinstance(payload.get('refers_to'), str) and payload['refers_to'].startswith('handoffs/')):
            found.add(payload.get('record_id'))
    return found


def claim(tool, arguments, environ, now):
    """One of the four claim tools: ({"records": [...]}, None) or (None, an error word of specification 6 section 8)."""
    try:
        identity = _identity(environ)
        if identity is None:
            return None, 'no_session'
        session_id, root = identity
        items = _items(tool, arguments)
        if items is None:
            return None, 'invalid_input'
        lease, word = _live_lease(writer.session_leases(root, session_id, now), now)
        if word is not None:
            return None, word
        task, token = lease['task_id'], lease['fencing_token']
        recorder = RECORDER % session_id
        call = _digest(json.dumps(arguments, sort_keys=True, separators=(',', ':'), ensure_ascii=False))
        planned = []
        for name, n, digest_text, text, ac in items:
            digest = _digest(session_id, task, tool, call, name, str(n), digest_text)
            record = {'record_id': 'mcp-claim/' + digest, 'fact_kind': 'claim', 'source_class': 'agent_declared',
                      'recorder': recorder, 'subject': task, 'session': session_id, 'text': text}
            if ac is not None:
                record['acs'] = [ac]
            if tool == 'handoff':
                record['refers_to'] = 'handoffs/%s-%s.md#%s/%d' % (task, session_id, name, n)
            planned.append(('mcp-' + digest, record))
        if tool == 'handoff':
            log = writer.read_log(root)
            if not isinstance(log, bytes):
                return None, 'core_error'
            earlier = _earlier_handoffs(log, session_id)
            if earlier and not earlier <= {record['record_id'] for _, record in planned}:
                return None, 'invalid_input'
        done = []
        for event_id, record in planned:
            r = writer.append_event(root, 'record.added', record, event_id, now, recorder, task_id=task,
                                    fencing_token=token)
            if not isinstance(r, writer.WriteResult):
                return None, 'core_error'
            if r.result in ('appended', 'duplicate'):
                done.append(record['record_id'])
                continue
            if r.result == 'refused' and r.reason == 'fence':
                _, word = _live_lease(writer.session_leases(root, session_id, now), now)
                return None, word if word is not None else 'core_error'
            return None, 'core_error'
        return {'records': done}, None
    except Exception:
        return None, 'core_error'


def _base(environ):
    """The session's base from the environment: exactly 40 lowercase hexadecimal characters, or None."""
    value = environ.get('AIEOS_BASE')
    if not isinstance(value, str) or not _BASE_FORM.fullmatch(value):
        return None
    return value


def _detail(findings):
    return {'error': 'core_error', 'detail': list(findings)}


def _inputs_at_base(session_id, root, base, now, read):
    """build_work_order's inputs at the base for the live lease's task, and None; or None and an error."""
    lease, word = _live_lease(writer.session_leases(root, session_id, now), now)
    if word is not None:
        return None, word
    log = writer.read_log(root)
    if not isinstance(log, bytes):
        return None, 'core_error'
    inputs, findings = base_inputs.work_order_inputs(root, base, lease['task_id'], session_id, log, read)
    if findings is not None:
        return None, _detail(findings)
    return inputs, None


def _compiled(inputs):
    work_order, findings = context_compiler.build_work_order(inputs)
    if findings is not None:
        return None, _detail(findings)
    return work_order, None


def get_work_order(arguments, environ, now, read=None):
    """The get_work_order tool: (the Work Order, None) or (None, an error word or a core_error with its detail)."""
    try:
        identity = _identity(environ)
        if identity is None:
            return None, 'no_session'
        base = _base(environ)
        if base is None:
            return None, 'no_session'
        if not (arguments is None or (type(arguments) is dict and not arguments)):
            return None, 'invalid_input'
        inputs, error = _inputs_at_base(identity[0], identity[1], base, now, read)
        if error is not None:
            return None, error
        return _compiled(inputs)
    except Exception:
        return None, 'core_error'


def _items_of(work_order, ref):
    return [item for layer in work_order['layers'] for item in layer['items'] if item['ref'] == ref]


def query(arguments, environ, now, read=None):
    """The query tool: ({ref, hash, content}, None) or (None, an error word or a core_error with its detail)."""
    try:
        identity = _identity(environ)
        if identity is None:
            return None, 'no_session'
        base = _base(environ)
        if base is None:
            return None, 'no_session'
        if not (type(arguments) is dict and set(arguments) == {'ref'} and _text(arguments['ref'])):
            return None, 'invalid_input'
        ref = arguments['ref']
        inputs, error = _inputs_at_base(identity[0], identity[1], base, now, read)
        if error is not None:
            return None, error
        work_order, error = _compiled(inputs)
        if error is not None:
            return None, error
        held = _items_of(work_order, ref)
        if not held:
            return None, 'out_of_scope'
        if len({item['hash'] for item in held}) != 1:
            return None, 'not_found'
        for item in held:
            if 'content' in item:
                return {'ref': item['ref'], 'hash': item['hash'], 'content': item['content']}, None
        full = dict(inputs, budgets={name: UNBUDGETED for name in context_compiler.LAYERS})
        whole, error = _compiled(full)
        if error is not None:
            return None, error
        found = [item for item in _items_of(whole, ref) if 'content' in item]
        if not found or found[0]['hash'] != held[0]['hash']:
            return None, 'not_found'
        return {'ref': found[0]['ref'], 'hash': found[0]['hash'], 'content': found[0]['content']}, None
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
    except (ValueError, RecursionError):
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
        return _result(id_, {'tools': json.loads(json.dumps([STATUS_TOOL] + CLAIM_TOOLS + WORK_ORDER_TOOLS))})
    if method == 'tools/call':
        params = msg.get('params')
        if not isinstance(params, dict) or not isinstance(params.get('name'), str) or params['name'] not in TOOL_NAMES:
            return _error(id_, INVALID_PARAMS, 'Invalid params')
        if params['name'] == 'status':
            obj, word = status(environ, clock())
        elif params['name'] == 'get_work_order':
            obj, word = get_work_order(params.get('arguments'), environ, clock())
        elif params['name'] == 'query':
            obj, word = query(params.get('arguments'), environ, clock())
        else:
            obj, word = claim(params['name'], params.get('arguments'), environ, clock())
        if isinstance(word, dict):
            return _result(id_, _tool_result(word, True))
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

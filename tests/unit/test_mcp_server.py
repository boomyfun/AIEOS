"""Unit tests of aieos_bootstrap.mcp_server (tasks TASK-078 and TASK-079): the protocol frame, the identity, status's
mapping over a stand-in for writer.session_leases, the four claim tools over stand-ins for the writer's functions, what
the module may touch, its docstrings and this module's own naming rule. No test here uses a real store, a temporary
folder or a file write (the real-store tests of the claim tools are in tests/unit/test_writer.py); the source is read
with pathlib's read_bytes."""

import ast
import datetime
import hashlib
import io
import json
import os
import pathlib
import re
import types
import unittest
from unittest import mock

from aieos_bootstrap import mcp_server, records, writer

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 23, 12, 0, 0, tzinfo=UTC)
H1 = datetime.timedelta(hours=1)
HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / 'src' / 'aieos_bootstrap'
ROOT = os.path.join(os.path.abspath(os.sep), 'made-up-root')
ENV = {'AIEOS_SESSION_ID': 's-1', 'AIEOS_ROOT': ROOT}
NONE = {'task': None, 'lease': 'none'}


def lease(task, until, counter):
    return {'task_id': task, 'fencing_token': {'epoch': 'e', 'counter': counter}, 'expires_at': until}


def done(ended=False, leases=()):
    return writer.StoreResult('done', 'rows', value={'ended': ended, 'leases': list(leases)})


def refused(reason):
    return writer.StoreResult('refused', reason, [reason + ': made up'])


def run(lines, env=ENV, answer=None):
    """main over the given text lines, with session_leases replaced by a stand-in giving ``answer``."""
    out = io.StringIO()
    with mock.patch.object(writer, 'session_leases', return_value=answer if answer is not None else done()):
        rc = mcp_server.main(io.StringIO(''.join(x + '\n' for x in lines)), out, env, lambda: T0)
    return rc, [json.loads(x) for x in out.getvalue().splitlines()]


def one(line, **kw):
    rc, answers = run([line], **kw)
    assert rc == 0 and len(answers) <= 1, answers
    return answers[0] if answers else None


def status(answer, env=ENV, now=T0):
    with mock.patch.object(writer, 'session_leases', return_value=answer) as m:
        return mcp_server.status(env, now), m


def call(id_=1, params=None):
    return json.dumps({'jsonrpc': '2.0', 'id': id_, 'method': 'tools/call',
                       'params': {'name': 'status', 'arguments': {}} if params is None else params})


class AC3Protocol(unittest.TestCase):
    def test_initialize(self):
        """TASK-078 AC3: initialize answers the protocol version, the server info and the tools capability."""
        a = one(json.dumps({'jsonrpc': '2.0', 'id': 7, 'method': 'initialize', 'params': {}}))
        self.assertEqual(a, {'jsonrpc': '2.0', 'id': 7, 'result': {
            'protocolVersion': '2025-06-18', 'serverInfo': {'name': 'aieos', 'version': '0.1'},
            'capabilities': {'tools': {}}}})

    def test_notifications_get_no_answer(self):
        """TASK-078 AC3: notifications/initialized, and any message without an id, get no answer."""
        self.assertIsNone(one(json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'})))
        self.assertIsNone(one(json.dumps({'jsonrpc': '2.0', 'method': 'tools/list'})))
        self.assertIsNone(one(json.dumps({'jsonrpc': '2.0', 'method': 'anything', 'params': [1]})))

    def test_tools_list_lists_only_status(self):
        """TASK-078 AC3 and TASK-079 AC1: tools/list answers status, acknowledge, ask, report and handoff, status with
        an object schema without properties."""
        a = one(json.dumps({'jsonrpc': '2.0', 'id': 'x', 'method': 'tools/list'}))
        tools = a['result']['tools']
        self.assertEqual([t['name'] for t in tools], ['status', 'acknowledge', 'ask', 'report', 'handoff'])
        self.assertEqual(tools[0]['inputSchema'], {'type': 'object', 'properties': {}})

    def test_tools_call_status(self):
        """TASK-078 AC3: tools/call with name status runs status and answers a result."""
        a = one(call(), answer=done())
        self.assertEqual(a['id'], 1)
        self.assertEqual(a['result']['isError'], False)
        self.assertEqual(json.loads(a['result']['content'][0]['text']), NONE)

    def test_bad_tools_call_params(self):
        """TASK-078 AC3 and TASK-079 AC1: tools/call whose params is not an object, lacks a str name, or names a tool
        not listed answers -32602."""
        for params in ([], 'status', 3, {}, {'name': 3}, {'name': 'get_work_order'}, {'name': 'Status'},
                       {'name': 'Acknowledge'}):
            with self.subTest(params=params):
                a = one(call(params=params))
                self.assertEqual((a['id'], a['error']['code']), (1, -32602))
        a = one(json.dumps({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call'}))
        self.assertEqual(a['error']['code'], -32602)

    def test_other_methods(self):
        """TASK-078 AC3: any other method answers -32601."""
        for method in ('resources/list', 'prompts/list', 'ping', 'tools/listx', ''):
            with self.subTest(method=method):
                a = one(json.dumps({'jsonrpc': '2.0', 'id': 3, 'method': method}))
                self.assertEqual((a['id'], a['error']['code']), (3, -32601))

    def test_parse_errors(self):
        """TASK-078 AC3: a line that is not JSON answers -32700 with id null."""
        for line in ('{', 'not json', '{"jsonrpc": "2.0", "id": 1,', "{'a': 1}"):
            with self.subTest(line=line):
                self.assertEqual(one(line), {'jsonrpc': '2.0', 'id': None,
                                             'error': {'code': -32700, 'message': 'Parse error'}})

    def test_non_objects(self):
        """TASK-078 AC3: a JSON value that is not an object, a batch array included, answers -32600 with id null."""
        for line in ('[]', '[{"jsonrpc": "2.0", "id": 1, "method": "initialize"}]', '3', '"x"', 'null', 'true'):
            with self.subTest(line=line):
                a = one(line)
                self.assertEqual((a['id'], a['error']['code']), (None, -32600))

    def test_invalid_requests(self):
        """TASK-078 AC3: a wrong jsonrpc, a method that is not a str, or an id that is not a str, an int or null
        answers -32600, with the id when it is valid, else null; this check comes before the notification rule."""
        cases = [({'jsonrpc': '1.0', 'id': 4, 'method': 'initialize'}, 4),
                 ({'id': 5, 'method': 'initialize'}, 5),
                 ({'jsonrpc': '2.0', 'id': 'a', 'method': 3}, 'a'),
                 ({'jsonrpc': '2.0', 'id': None, 'method': None}, None),
                 ({'jsonrpc': '2.0', 'id': True, 'method': 'initialize'}, None),
                 ({'jsonrpc': '2.0', 'id': 1.5, 'method': 'initialize'}, None),
                 ({'jsonrpc': '2.0', 'id': {}, 'method': 'initialize'}, None),
                 ({'jsonrpc': '2.0', 'method': 7}, None),
                 ({}, None)]
        for msg, id_ in cases:
            with self.subTest(msg=msg):
                a = one(json.dumps(msg))
                self.assertEqual((a['id'], a['error']['code']), (id_, -32600))

    def test_blank_lines_and_bytes(self):
        """TASK-078 AC3: empty and whitespace-only lines get no answer; byte lines are read as UTF-8, and bytes that
        are not UTF-8 answer -32700."""
        rc, answers = run(['', '   ', '\t'])
        self.assertEqual((rc, answers), (0, []))
        out = io.StringIO()
        data = io.BytesIO(b'\xff\xfe\n' + json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'ping'}).encode() + b'\n')
        self.assertEqual(mcp_server.main(data, out, ENV, lambda: T0), 0)
        got = [json.loads(x) for x in out.getvalue().splitlines()]
        self.assertEqual([g['error']['code'] for g in got], [-32700, -32601])

    def test_main_answers_each_on_one_line_and_returns_zero(self):
        """TASK-078 AC3: each answer is one line of JSON, in order; main returns 0 at the end of input."""
        lines = [json.dumps({'jsonrpc': '2.0', 'id': i, 'method': 'tools/list'}) for i in range(3)]
        rc, answers = run(lines)
        self.assertEqual((rc, [a['id'] for a in answers]), (0, [0, 1, 2]))

    def test_main_never_raises(self):
        """TASK-078 AC3: a failing handler answers -32603 with id null and the loop goes on; a failing stream ends
        main with 0."""
        out = io.StringIO()
        with mock.patch.object(mcp_server, 'handle', side_effect=RuntimeError('made up')):
            self.assertEqual(mcp_server.main(io.StringIO('x\ny\n'), out, ENV, lambda: T0), 0)
        self.assertEqual([json.loads(x)['error']['code'] for x in out.getvalue().splitlines()], [-32603, -32603])

        class Broken:
            def __iter__(self):
                raise OSError('made up')
        self.assertEqual(mcp_server.main(Broken(), io.StringIO(), ENV, lambda: T0), 0)


class AC4Identity(unittest.TestCase):
    def test_missing_or_bad_identity_is_no_session(self):
        """TASK-078 AC4: AIEOS_SESSION_ID absent, empty or out of form, or AIEOS_ROOT absent, empty or not absolute,
        gives no_session, and the store is not read."""
        envs = [{}, {'AIEOS_ROOT': ROOT}, {'AIEOS_SESSION_ID': 's-1'}, {'AIEOS_SESSION_ID': '', 'AIEOS_ROOT': ROOT},
                {'AIEOS_SESSION_ID': 'a b', 'AIEOS_ROOT': ROOT}, {'AIEOS_SESSION_ID': 'x' * 129, 'AIEOS_ROOT': ROOT},
                {'AIEOS_SESSION_ID': 's/1', 'AIEOS_ROOT': ROOT}, {'AIEOS_SESSION_ID': 's-1', 'AIEOS_ROOT': ''},
                {'AIEOS_SESSION_ID': 's-1', 'AIEOS_ROOT': 'relative/root'}]
        for env in envs:
            with self.subTest(env=env):
                got, m = status(done(), env=env)
                self.assertEqual(got, (None, 'no_session'))
                m.assert_not_called()

    def test_the_identity_reaches_the_store_and_the_base_is_not_read(self):
        """TASK-078 AC4: a session id of 128 characters and an absolute root pass to session_leases; AIEOS_BASE is
        neither needed nor read."""
        env = {'AIEOS_SESSION_ID': 'A' * 128, 'AIEOS_ROOT': ROOT, 'AIEOS_BASE': 'not a commit'}
        got, m = status(done(), env=env)
        self.assertEqual(got, (NONE, None))
        m.assert_called_once_with(ROOT, 'A' * 128, T0)
        names = {n.value for n in ast.walk(ast.parse((SRC / 'mcp_server.py').read_bytes().decode('utf-8')))
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        self.assertNotIn('AIEOS_BASE', names)


class AC5Mapping(unittest.TestCase):
    def test_none_live_and_expired(self):
        """TASK-078 AC5: ended or no row gives none; one unexpired row live with its expiry; rows none unexpired
        expired with the highest counter's task."""
        self.assertEqual(status(done(ended=True))[0], (NONE, None))
        self.assertEqual(status(done(ended=True, leases=[lease('TASK-1', T0 + H1, 1)]))[0], (NONE, None))
        self.assertEqual(status(done())[0], (NONE, None))
        self.assertEqual(status(done(leases=[lease('TASK-1', T0 + H1, 4)]))[0],
                         ({'task': 'TASK-1', 'lease': 'live', 'expires_at': '2026-10-23T13:00:00Z'}, None))
        self.assertEqual(status(done(leases=[lease('TASK-1', T0, 4)]))[0], ({'task': 'TASK-1', 'lease': 'expired'}, None))
        rows = [lease('TASK-2', T0 - H1, 9), lease('TASK-1', T0, 4)]
        self.assertEqual(status(done(leases=rows))[0], ({'task': 'TASK-2', 'lease': 'expired'}, None))
        rows = [lease('TASK-2', T0 - H1, 9), lease('TASK-1', T0 + H1, 4)]
        self.assertEqual(status(done(leases=rows))[0][0]['lease'], 'live')

    def test_more_than_one_unexpired_row_is_core_error(self):
        """TASK-078 AC5: more than one unexpired row gives core_error."""
        rows = [lease('TASK-1', T0 + H1, 1), lease('TASK-2', T0 + H1, 2)]
        self.assertEqual(status(done(leases=rows))[0], (None, 'core_error'))

    def test_refusals(self):
        """TASK-078 AC5: session gives none; root and no_store no_session; argument, unreadable, link, tables and
        any other reason core_error."""
        self.assertEqual(status(refused('session'))[0], (NONE, None))
        for reason in ('root', 'no_store'):
            self.assertEqual(status(refused(reason))[0], (None, 'no_session'), reason)
        for reason in ('argument', 'unreadable', 'link', 'tables', 'leases', 'made_up'):
            self.assertEqual(status(refused(reason))[0], (None, 'core_error'), reason)

    def test_other_answers_are_core_error(self):
        """TASK-078 AC5: an answer not in session_leases' form gives core_error, and so does a raising stand-in."""
        bad = [None, 'done', writer.StoreResult('done', 'tied', value={'ended': False, 'leases': []}),
               writer.StoreResult('done', 'rows', value=None),
               writer.StoreResult('done', 'rows', value={'ended': 0, 'leases': []}),
               writer.StoreResult('done', 'rows', value={'ended': False, 'leases': [{'task_id': 'TASK-1'}]}),
               writer.StoreResult('maybe', 'rows', value={'ended': False, 'leases': []})]
        for answer in bad:
            with self.subTest(answer=answer):
                self.assertEqual(status(answer)[0], (None, 'core_error'))
        with mock.patch.object(writer, 'session_leases', side_effect=RuntimeError('made up')):
            self.assertEqual(mcp_server.status(ENV, T0), (None, 'core_error'))

    def test_the_answer_forms(self):
        """TASK-078 AC5: a tool error is a result with isError true and the text {"error": <word>}; a success a result
        whose one text item is the status object."""
        a = one(call(), answer=refused('no_store'))
        self.assertEqual(a['result']['isError'], True)
        self.assertEqual(json.loads(a['result']['content'][0]['text']), {'error': 'no_session'})
        a = one(call(), answer=done(leases=[lease('TASK-1', T0 + H1, 1)]))
        self.assertEqual(len(a['result']['content']), 1)
        self.assertEqual(a['result']['content'][0]['type'], 'text')
        self.assertEqual(json.loads(a['result']['content'][0]['text'])['lease'], 'live')


class AC6WritesNothing(unittest.TestCase):
    def tree(self):
        return ast.parse((SRC / 'mcp_server.py').read_bytes().decode('utf-8'))

    def test_imports_opens_and_names(self):
        """TASK-078 AC6 and TASK-079 AC8: the module imports only datetime, hashlib, json, os, re, sys and
        aieos_bootstrap.writer, calls no open, and names no project-state directory."""
        tree = self.tree()
        imports = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imports.update(('import', a.name) for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                imports.update((n.module, a.name) for a in n.names)
        self.assertEqual(imports, {('import', 'datetime'), ('import', 'hashlib'), ('import', 'json'), ('import', 'os'),
                                   ('import', 're'), ('import', 'sys'), ('aieos_bootstrap', 'writer')})
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        self.assertFalse(names & {'open', 'exec', 'eval', 'compile', '__import__', 'input', 'sqlite3', 'subprocess'})
        self.assertFalse(attrs & {'open', 'makedirs', 'remove', 'unlink', 'write_text', 'write_bytes', 'connect'})
        strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertFalse([s for s in strings if '.aieos' in s])

    def test_the_only_writer_function_is_session_leases(self):
        """TASK-078 AC6 and TASK-079 AC8: the writer attributes the module uses are session_leases, append_event,
        read_log, StoreResult and WriteResult, and a status call through a stand-in writer holding only session_leases
        and StoreResult works."""
        tree = self.tree()
        used = {n.attr for n in ast.walk(tree)
                if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == 'writer'}
        self.assertEqual(used, {'session_leases', 'append_event', 'read_log', 'StoreResult', 'WriteResult'})
        seen = []

        def fake(*args):
            seen.append(args)
            return done()
        stand_in = types.SimpleNamespace(session_leases=fake, StoreResult=writer.StoreResult)
        with mock.patch.object(mcp_server, 'writer', stand_in):
            self.assertEqual(mcp_server.status(ENV, T0), (NONE, None))
        self.assertEqual(seen, [(ROOT, 's-1', T0)])


class AC8Statements(unittest.TestCase):
    def test_the_docstrings(self):
        """TASK-078 AC8 and TASK-079 AC9: the module's docstring and session_leases' state the scope and the limits
        (whitespace read as single spaces)."""
        doc = ' '.join(ast.get_docstring(ast.parse((SRC / 'mcp_server.py').read_bytes().decode('utf-8'))).split())
        for words in ('"2025-06-18"', 'initialize, notifications/initialized, tools/list and tools/call',
                      'lists five tools', 'AIEOS_SESSION_ID', 'AIEOS_BASE is not read in this slice',
                      '"expired" exists only between a lease\'s expiry and the next expire_leases',
                      'core_error for more than one unexpired row', 'hand-kept copy', 'are the owner\'s acts',
                      'at most tier T2, as a target and unmeasured', 'writes nothing'):
            self.assertIn(words, doc, words)
        wdoc = ' '.join(writer.session_leases.__doc__.split())
        for words in ('task TASK-078', 'hand-kept copy', 'and the next expire_leases',
                      'More than one unexpired row', 'writes and creates nothing', 'a stated choice'):
            self.assertIn(words, wdoc, words)


def names_its_criteria(doc):
    """True when ``doc`` names "TASK-078 ACn" or "TASK-079 ACn" and no other task's AC in qualified form (whitespace
    collapsed)."""
    doc = ' '.join((doc or '').split())
    return (bool(re.findall(r'TASK-07[89] AC[0-9]+', doc))
            and not re.findall(r'TASK-(?!078 |079 )[0-9]+ AC[0-9]+', doc))


class AC8Naming(unittest.TestCase):
    def test_every_test_names_its_criteria(self):
        """TASK-078 AC8 and TASK-079 AC9: every test function of this module and of the property module names
        "TASK-078 ACn" or "TASK-079 ACn" in its own docstring and no other task's AC."""
        for path in (HERE, HERE.parents[1] / 'property' / 'test_mcp_server_properties.py'):
            tree = ast.parse(path.read_bytes().decode('utf-8'))
            for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test')]:
                with self.subTest(path=path.name, test=fn.name):
                    self.assertTrue(names_its_criteria(ast.get_docstring(fn)))

    def test_the_naming_check_refuses(self):
        """TASK-078 AC8 and TASK-079 AC9: the check refuses a missing id, another task's id, and an admitted id
        beside another's."""
        self.assertFalse(names_its_criteria(None))
        self.assertFalse(names_its_criteria('made up, no id'))
        self.assertFalse(names_its_criteria('TASK-077 AC1: made up.'))
        self.assertFalse(names_its_criteria('TASK-080 AC1: made up.'))
        self.assertFalse(names_its_criteria('TASK-078 AC1 and TASK-076 AC2: made up.'))
        self.assertFalse(names_its_criteria('TASK-079 AC1 and TASK-0790 AC2: made up.'))
        self.assertTrue(names_its_criteria('TASK-078 AC1: made up.'))
        self.assertTrue(names_its_criteria('TASK-079 AC1: made up.'))
        self.assertTrue(names_its_criteria('TASK-078 AC3 and TASK-079 AC1: made up.'))


# ---- the claim tools (task TASK-079), over stand-ins for the writer's functions ----

LIVE = done(leases=[lease('TASK-9', T0 + H1, 3)])
TOKEN = {'epoch': 'e', 'counter': 3}
ARGS = {'acknowledge': {'assumptions': ['a1', 'a2']},
        'ask': {'question': 'q?'},
        'report': {'criteria': [{'ac': 'AC1', 'text': 'met'}, {'ac': 'AC12', 'text': 'also met'}], 'notes': 'n'},
        'handoff': {'done': ['d1', 'd2'], 'not_done': [], 'assumptions': ['a'], 'discoveries': ['x'], 'risks': [],
                    'proposals': ['p']}}


def wr(result, reason=None):
    return writer.WriteResult(types.SimpleNamespace(result=result, reason=reason, seq=1, line=None, findings=()))


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def expected_ids(tool, args, session='s-1', task='TASK-9'):
    """The header's id rule, computed here on its own: [(event_id, record_id)] in the order of the items."""
    c = sha(json.dumps(args, sort_keys=True, separators=(',', ':'), ensure_ascii=False))
    items = []
    if tool == 'acknowledge':
        items = [('assumptions', n, x) for n, x in enumerate(args['assumptions'], 1)]
    elif tool == 'ask':
        items = [('question', 1, args['question'])]
    elif tool == 'report':
        items = [('criteria', n, x['ac'] + ' ' + x['text']) for n, x in enumerate(args['criteria'], 1)]
        if args['notes']:
            items.append(('notes', 1, args['notes']))
    else:
        items = [(k, n, x) for k in ('done', 'not_done', 'assumptions', 'discoveries', 'risks', 'proposals')
                 for n, x in enumerate(args[k], 1)]
    out = []
    for name, n, text in items:
        d = sha('\n'.join([session, task, tool, c, name, str(n), text]))
        out.append(('mcp-' + d, 'mcp-claim/' + d))
    return out


class Stand:
    """Stand-ins for writer.session_leases, writer.read_log and writer.append_event, recording every call. The lease
    answers are given in order (the last one repeated); the append answers likewise, "appended" when none is given."""

    def __init__(self, leases=(LIVE,), appends=(), log=b''):
        self.leases, self.appends, self.log, self.calls = list(leases), list(appends), log, []

    def _next(self, kind, answers, default):
        i = len([c for c in self.calls if c[0] == kind]) - 1
        answer = answers[min(i, len(answers) - 1)] if answers else default
        if isinstance(answer, Exception):
            raise answer
        return answer

    def session_leases(self, *args):
        self.calls.append(('session_leases', args))
        return self._next('session_leases', self.leases, None)

    def read_log(self, *args):
        self.calls.append(('read_log', args))
        return self._next('read_log', [self.log], None)

    def append_event(self, *args, **kw):
        self.calls.append(('append_event', args, kw))
        return self._next('append_event', self.appends, wr('appended'))

    def run(self, tool, args, env=ENV):
        with mock.patch.object(writer, 'session_leases', self.session_leases), \
                mock.patch.object(writer, 'read_log', self.read_log), \
                mock.patch.object(writer, 'append_event', self.append_event):
            return mcp_server.claim(tool, args, env, T0)

    def kinds(self):
        return [c[0] for c in self.calls]

    def records(self):
        return [c[1][2] for c in self.calls if c[0] == 'append_event']


def log_of(records):
    return b''.join(json.dumps({'type': 'record.added', 'payload': r}).encode('utf-8') + b'\n' for r in records)


class TASK079AC1Inputs(unittest.TestCase):
    BAD = [('acknowledge', None), ('acknowledge', []), ('acknowledge', {}), ('acknowledge', {'assumptions': []}),
           ('acknowledge', {'assumptions': ['']}), ('acknowledge', {'assumptions': 'a'}),
           ('acknowledge', {'assumptions': [1]}), ('acknowledge', {'assumptions': ['a'], 'x': 1}),
           ('acknowledge', {'assumptions': ['\ud800']}), ('acknowledge', {'assumptions': ['a'], 'fencing_token': TOKEN}),
           ('ask', {}), ('ask', {'question': ''}), ('ask', {'question': 3}), ('ask', {'question': 'q', 'x': 1}),
           ('report', {'criteria': [], 'notes': ''}), ('report', {'criteria': []}), ('report', {'notes': 'n'}),
           ('report', {'criteria': [{'ac': 'X1', 'text': 't'}], 'notes': ''}),
           ('report', {'criteria': [{'ac': 'AC', 'text': 't'}], 'notes': ''}),
           ('report', {'criteria': [{'ac': 'AC1', 'text': ''}], 'notes': ''}),
           ('report', {'criteria': [{'ac': 'AC1'}], 'notes': ''}),
           ('report', {'criteria': [{'ac': 'AC1', 'text': 't', 'x': 1}], 'notes': ''}),
           ('report', {'criteria': {}, 'notes': ''}), ('report', {'criteria': [], 'notes': 3}),
           ('handoff', {k: [] for k in ('done', 'not_done', 'assumptions', 'discoveries', 'risks', 'proposals')}),
           ('handoff', {'done': ['d']}), ('handoff', dict(ARGS['handoff'], done=[''])),
           ('handoff', dict(ARGS['handoff'], extra=[])), ('handoff', dict(ARGS['handoff'], risks='r')),
           ('get_work_order', {})]

    def test_every_shape_out_of_form_is_invalid_input_with_no_writer_call(self):
        """TASK-079 AC1: an input out of form, a missing or non-object arguments among them, answers invalid_input
        and calls no writer function."""
        for tool, args in self.BAD:
            with self.subTest(tool=tool, args=args):
                s = Stand()
                self.assertEqual(s.run(tool, args), (None, 'invalid_input'))
                self.assertEqual(s.calls, [])

    def test_every_good_shape_is_taken(self):
        """TASK-079 AC1: the inputs of the header's shapes are taken, report with notes only or criteria only."""
        goods = list(ARGS.items()) + [('report', {'criteria': [], 'notes': 'only notes'}),
                                      ('report', {'criteria': [{'ac': 'AC3', 'text': 't'}], 'notes': ''}),
                                      ('handoff', dict({k: [] for k in ARGS['handoff']}, risks=['r']))]
        for tool, args in goods:
            with self.subTest(tool=tool, args=args):
                obj, word = Stand().run(tool, args)
                self.assertIsNone(word)
                self.assertEqual(len(obj['records']), len(expected_ids(tool, args)))

    def test_the_listing_and_the_schemas(self):
        """TASK-079 AC1: tools/list gives each claim tool an object input schema of section 4's keys."""
        a = one(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}))
        schemas = {t['name']: t['inputSchema'] for t in a['result']['tools']}
        keys = {'acknowledge': {'assumptions'}, 'ask': {'question'}, 'report': {'criteria', 'notes'},
                'handoff': {'done', 'not_done', 'assumptions', 'discoveries', 'risks', 'proposals'}}
        for tool, want in keys.items():
            with self.subTest(tool=tool):
                self.assertEqual(schemas[tool]['type'], 'object')
                self.assertEqual(set(schemas[tool]['properties']), want)
                self.assertEqual(set(schemas[tool]['required']), want)

    def test_through_the_frame(self):
        """TASK-079 AC1: a tools/call without arguments, or with arguments that are not an object, answers the tool
        error invalid_input."""
        for params in ({'name': 'ask'}, {'name': 'ask', 'arguments': ['q']}, {'name': 'handoff', 'arguments': None}):
            with self.subTest(params=params):
                a = one(call(params=params), answer=LIVE)
                self.assertEqual(a['result']['isError'], True)
                self.assertEqual(json.loads(a['result']['content'][0]['text']), {'error': 'invalid_input'})


class TASK079AC2Lease(unittest.TestCase):
    def test_no_session_first(self):
        """TASK-079 AC2: a missing or out-of-form identity answers no_session with no writer call, before the input
        is looked at."""
        for env in ({}, {'AIEOS_SESSION_ID': 's 1', 'AIEOS_ROOT': ROOT}, {'AIEOS_SESSION_ID': 's-1', 'AIEOS_ROOT': 'r'}):
            for tool, args in list(ARGS.items()) + [('ask', None)]:
                with self.subTest(env=env, tool=tool):
                    s = Stand()
                    self.assertEqual(s.run(tool, args, env=env), (None, 'no_session'))
                    self.assertEqual(s.calls, [])

    def test_the_lease_answers(self):
        """TASK-079 AC2: no row, an ended session or a session never seen answer no_lease; no unexpired row
        lease_expired; more than one unexpired row core_error; root and no_store no_session; any other refusal,
        answer or exception core_error; on each the tool calls no other writer function."""
        cases = [(done(), 'no_lease'), (done(ended=True, leases=[lease('TASK-9', T0 + H1, 3)]), 'no_lease'),
                 (refused('session'), 'no_lease'), (done(leases=[lease('TASK-9', T0, 3)]), 'lease_expired'),
                 (done(leases=[lease('TASK-9', T0 - H1, 3), lease('TASK-8', T0, 2)]), 'lease_expired'),
                 (done(leases=[lease('TASK-9', T0 + H1, 3), lease('TASK-8', T0 + H1, 2)]), 'core_error'),
                 (refused('root'), 'no_session'), (refused('no_store'), 'no_session')]
        cases += [(refused(r), 'core_error') for r in ('argument', 'unreadable', 'link', 'tables', 'made_up')]
        cases += [(None, 'core_error'), (writer.StoreResult('done', 'rows', value=None), 'core_error'),
                  (RuntimeError('made up'), 'core_error')]
        for answer, word in cases:
            for tool, args in ARGS.items():
                with self.subTest(answer=answer, tool=tool):
                    s = Stand(leases=[answer])
                    self.assertEqual(s.run(tool, args), (None, word))
                    self.assertEqual(s.kinds(), ['session_leases'])

    def test_other_writer_answers_are_core_error(self):
        """TASK-079 AC2: any append_event refusal but the fence ("conflict" among them), an answer of another form,
        an exception, and a read_log that raises or answers no bytes, answer core_error."""
        for answer in (wr('refused', 'conflict'), wr('refused', 'event'), wr('refused', 'log'),
                       wr('refused', 'log_after'), wr('maybe'), None, 'appended', ValueError('made up')):
            with self.subTest(answer=answer):
                self.assertEqual(Stand(appends=[answer]).run('acknowledge', ARGS['acknowledge']), (None, 'core_error'))
        for log in (OSError('made up'), 'text', None, b'not json\n'):
            with self.subTest(log=log):
                s = Stand(log=log)
                self.assertEqual(s.run('handoff', ARGS['handoff']), (None, 'core_error'))
                self.assertNotIn('append_event', s.kinds())

    def test_the_order(self):
        """TASK-079 AC2: the lease is read before the log, and both before any append."""
        s = Stand()
        s.run('handoff', ARGS['handoff'])
        kinds = s.kinds()
        self.assertEqual(kinds[:2], ['session_leases', 'read_log'])
        self.assertEqual(set(kinds[2:]), {'append_event'})


class TASK079AC3Form(unittest.TestCase):
    def test_the_records_and_the_appends(self):
        """TASK-079 AC3: each item is one record.added append whose payload is the header's record, task_id the
        lease's task, fencing_token the lease's token from the store and the recorder argument the payload's
        recorder; every payload passes records.check_record."""
        for tool, args in ARGS.items():
            with self.subTest(tool=tool):
                s = Stand()
                obj, word = s.run(tool, args)
                self.assertIsNone(word)
                appends = [c for c in s.calls if c[0] == 'append_event']
                self.assertEqual(obj['records'], [c[1][2]['record_id'] for c in appends])
                for _, pos, kw in appends:
                    root, event_type, record, event_id, at, recorder = pos
                    self.assertEqual((root, event_type, at, recorder), (ROOT, 'record.added', T0,
                                                                        'aieos mcp_server, session s-1'))
                    self.assertEqual(kw, {'task_id': 'TASK-9', 'fencing_token': TOKEN})
                    self.assertEqual(record['recorder'], recorder)
                    self.assertEqual((record['fact_kind'], record['source_class'], record['subject'],
                                      record['session']), ('claim', 'agent_declared', 'TASK-9', 's-1'))
                    self.assertEqual(records.check_record(record), [])

    def test_the_texts_acs_and_refers_to(self):
        """TASK-079 AC3 and TASK-079 AC6: a report criterion carries acs with its one AC id and its text, the notes
        no acs; a handoff item refers_to its list and place from 1; the other tools carry neither."""
        s = Stand()
        s.run('report', ARGS['report'])
        recs = s.records()
        self.assertEqual([(r['text'], r.get('acs')) for r in recs], [('met', ['AC1']), ('also met', ['AC12']),
                                                                     ('n', None)])
        s = Stand()
        s.run('handoff', ARGS['handoff'])
        self.assertEqual([r['refers_to'] for r in s.records()],
                         ['handoffs/TASK-9-s-1.md#done/1', 'handoffs/TASK-9-s-1.md#done/2',
                          'handoffs/TASK-9-s-1.md#assumptions/1', 'handoffs/TASK-9-s-1.md#discoveries/1',
                          'handoffs/TASK-9-s-1.md#proposals/1'])
        for tool in ('acknowledge', 'ask'):
            s = Stand()
            s.run(tool, ARGS[tool])
            self.assertFalse([r for r in s.records() if 'acs' in r or 'refers_to' in r])

    def test_the_token_is_never_the_inputs(self):
        """TASK-079 AC3: the token is the one session_leases gives; an input carrying a token is out of form."""
        other = done(leases=[lease('TASK-9', T0 + H1, 77)])
        s = Stand(leases=[other])
        s.run('ask', ARGS['ask'])
        self.assertEqual(s.calls[1][2]['fencing_token'], {'epoch': 'e', 'counter': 77})
        self.assertEqual(Stand().run('ask', {'question': 'q', 'fencing_token': TOKEN}), (None, 'invalid_input'))


class TASK079AC4Ids(unittest.TestCase):
    def test_the_rule(self):
        """TASK-079 AC4: event_id and record_id follow the header's rule (the call digest, the argument's name, the
        place from 1), for ask's question and report's notes too."""
        for tool, args in ARGS.items():
            with self.subTest(tool=tool):
                s = Stand()
                s.run(tool, args)
                got = [(c[1][3], c[1][2]['record_id']) for c in s.calls if c[0] == 'append_event']
                self.assertEqual(got, expected_ids(tool, args))

    def test_a_differing_call_gets_new_ids(self):
        """TASK-079 AC4: a call that differs anywhere, one with the same text at the same place among them, gets new
        ids; an identical call the same ids."""
        a, b = Stand(), Stand()
        a.run('acknowledge', {'assumptions': ['a', 'b']})
        b.run('acknowledge', {'assumptions': ['a', 'c']})
        ids_a = [r['record_id'] for r in a.records()]
        ids_b = [r['record_id'] for r in b.records()]
        self.assertEqual(len(ids_a), 2)
        self.assertFalse(set(ids_a) & set(ids_b))
        s1, s2 = Stand(), Stand()
        self.assertEqual(s1.run('ask', {'question': 'q'}), s2.run('ask', {'question': 'q'}))
        other = Stand()
        other.run('ask', {'question': 'q'}, env={'AIEOS_SESSION_ID': 's-2', 'AIEOS_ROOT': ROOT})
        self.assertNotEqual(s1.records()[0]['record_id'], other.records()[0]['record_id'])

    def test_a_non_ascii_text_keeps_its_characters(self):
        """TASK-079 AC4: a non-ASCII text keeps its characters in the call digest (canonical JSON in UTF-8, non-ASCII
        kept), so the ids are those of ensure_ascii False, not those of ensure_ascii True."""
        text = 'é ü 中 a'
        args = {'assumptions': [text]}
        s = Stand()
        s.run('acknowledge', args)
        got = [(c[1][3], c[1][2]['record_id']) for c in s.calls if c[0] == 'append_event']
        self.assertEqual(got, expected_ids('acknowledge', args))
        ascii_c = sha(json.dumps(args, sort_keys=True, separators=(',', ':'), ensure_ascii=True))
        d = sha('\n'.join(['s-1', 'TASK-9', 'acknowledge', ascii_c, 'assumptions', '1', text]))
        self.assertNotEqual(got[0], ('mcp-' + d, 'mcp-claim/' + d))
        self.assertEqual(s.records()[0]['text'], text)

    def test_a_duplicate_answers_the_same_ids(self):
        """TASK-079 AC4: the log's "duplicate" is a success naming the same record ids."""
        obj, word = Stand(appends=[wr('duplicate')]).run('acknowledge', ARGS['acknowledge'])
        self.assertEqual(obj['records'], [r for _, r in expected_ids('acknowledge', ARGS['acknowledge'])])


class TASK079AC5Fence(unittest.TestCase):
    def test_a_fence_refusal_reads_the_lease_again(self):
        """TASK-079 AC5: on a fence refusal the tool reads session_leases again and answers by AC2's rule, exactly
        one unexpired row answering core_error; the items appended before stay and no later item is tried."""
        cases = [(done(leases=[lease('TASK-9', T0, 3)]), 'lease_expired'), (done(), 'no_lease'),
                 (done(ended=True), 'no_lease'), (LIVE, 'core_error'),
                 (done(leases=[lease('TASK-9', T0 + H1, 3), lease('TASK-8', T0 + H1, 4)]), 'core_error'),
                 (refused('no_store'), 'no_session'), (RuntimeError('made up'), 'core_error')]
        for second, word in cases:
            with self.subTest(second=second):
                s = Stand(leases=[LIVE, second], appends=[wr('appended'), wr('refused', 'fence')])
                self.assertEqual(s.run('handoff', ARGS['handoff']), (None, word))
                self.assertEqual(s.kinds(), ['session_leases', 'read_log', 'append_event', 'append_event',
                                             'session_leases'])


class TASK079AC6Handoff(unittest.TestCase):
    def first(self, args=None):
        s = Stand()
        s.run('handoff', args or ARGS['handoff'])
        return s.records()

    def test_a_cut_off_handoff_goes_on(self):
        """TASK-079 AC6: earlier claims of the session that are all among this call's ids (the identical call) let
        the call go on."""
        recs = self.first()
        s = Stand(log=log_of(recs[:2]))
        obj, word = s.run('handoff', ARGS['handoff'])
        self.assertIsNone(word)
        self.assertEqual(obj['records'], [r['record_id'] for r in recs])

    def test_a_different_second_handoff_is_refused(self):
        """TASK-079 AC6: a different second handoff, a superset of the first among them, answers invalid_input and
        appends nothing."""
        recs = self.first({'done': ['d1'], 'not_done': [], 'assumptions': [], 'discoveries': [], 'risks': [],
                           'proposals': []})
        for args in (ARGS['handoff'], dict(ARGS['handoff'], done=['d1']), {'done': ['d1'], 'not_done': ['n'],
                     'assumptions': [], 'discoveries': [], 'risks': [], 'proposals': []}):
            with self.subTest(args=args):
                s = Stand(log=log_of(recs))
                self.assertEqual(s.run('handoff', args), (None, 'invalid_input'))
                self.assertNotIn('append_event', s.kinds())

    def test_the_session_not_the_task_keys_the_rule(self):
        """TASK-079 AC6: an earlier handoff of the same session under another task refuses the call; another
        session's handoff, and the session's claims without a handoffs/ refers_to, do not."""
        other_task = dict(self.first()[0], record_id='mcp-claim/other', refers_to='handoffs/TASK-1-s-1.md#done/1')
        s = Stand(log=log_of([other_task]))
        self.assertEqual(s.run('handoff', ARGS['handoff']), (None, 'invalid_input'))
        other_session = dict(other_task, session='s-2', refers_to='handoffs/TASK-9-s-2.md#done/1')
        plain = dict(other_task, refers_to=None)
        del plain['refers_to']
        s = Stand(log=log_of([other_session, plain]))
        self.assertIsNone(s.run('handoff', ARGS['handoff'])[1])

    def test_only_handoff_reads_the_log(self):
        """TASK-079 AC6: the other three tools never read the log, and no tool writes a handoff file (the writer's
        three functions are its only reach)."""
        for tool in ('acknowledge', 'ask', 'report'):
            s = Stand()
            s.run(tool, ARGS[tool])
            self.assertNotIn('read_log', s.kinds())


class TASK079AC7Def0092(unittest.TestCase):
    def test_a_line_nested_too_deep_is_a_parse_error(self):
        """TASK-079 AC7: a line whose JSON nests too deep for json.loads answers -32700 with id null."""
        self.assertEqual(one('[' * 200000), {'jsonrpc': '2.0', 'id': None,
                                             'error': {'code': -32700, 'message': 'Parse error'}})

    def test_two_tasks_unexpired_leases_are_core_error(self):
        """TASK-079 AC7: a session holding two tasks' unexpired leases answers core_error, for status and for the
        claim tools."""
        two = done(leases=[lease('TASK-1', T0 + H1, 1), lease('TASK-2', T0 + H1, 2)])
        self.assertEqual(status(two)[0], (None, 'core_error'))
        self.assertEqual(Stand(leases=[two]).run('ask', ARGS['ask']), (None, 'core_error'))


class TASK079AC9Docstring(unittest.TestCase):
    def test_the_claim_tools_scope_and_limits(self):
        """TASK-079 AC9: the module's docstring states the claim tools' scope and the header's limits (whitespace read
        as single spaces)."""
        doc = ' '.join(ast.get_docstring(ast.parse((SRC / 'mcp_server.py').read_bytes().decode('utf-8'))).split())
        for words in ('tasks TASK-078 and TASK-079', 'specification 6 revision 7',
                      'take their input from params.arguments', 'An error found before the first append writes nothing',
                      'fencing_token the lease\'s token from the store, never from the input',
                      'Only an identical call repeats the ids', 'handoff is called once per session',
                      'the claims appended before it stay', '"conflict" among them',
                      'Every claim is the agent\'s statement (agent_declared)',
                      'writer.read_log reads the whole log, with no link check',
                      'The handoff file itself is the launcher\'s'):
            self.assertIn(words, doc, words)


if __name__ == '__main__':
    unittest.main()

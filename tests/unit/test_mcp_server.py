"""Unit tests of aieos_bootstrap.mcp_server (task TASK-078): the protocol frame, the identity, status's mapping over a
stand-in for writer.session_leases, what the module may touch, its docstrings and this module's own naming rule. No
test here uses a real store, a temporary folder or a file write; the source is read with pathlib's read_bytes."""

import ast
import datetime
import io
import json
import os
import pathlib
import re
import types
import unittest
from unittest import mock

from aieos_bootstrap import mcp_server, writer

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
        """TASK-078 AC3: tools/list answers exactly one tool, status, with an object schema without properties."""
        a = one(json.dumps({'jsonrpc': '2.0', 'id': 'x', 'method': 'tools/list'}))
        tools = a['result']['tools']
        self.assertEqual([t['name'] for t in tools], ['status'])
        self.assertEqual(tools[0]['inputSchema'], {'type': 'object', 'properties': {}})

    def test_tools_call_status(self):
        """TASK-078 AC3: tools/call with name status runs status and answers a result."""
        a = one(call(), answer=done())
        self.assertEqual(a['id'], 1)
        self.assertEqual(a['result']['isError'], False)
        self.assertEqual(json.loads(a['result']['content'][0]['text']), NONE)

    def test_bad_tools_call_params(self):
        """TASK-078 AC3: tools/call whose params is not an object, lacks a str name, or names another tool answers
        -32602."""
        for params in ([], 'status', 3, {}, {'name': 3}, {'name': 'acknowledge'}, {'name': 'Status'}):
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
        """TASK-078 AC6: the module imports only json, os, re, sys, datetime and aieos_bootstrap.writer, calls no open,
        and names no project-state directory."""
        tree = self.tree()
        imports = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imports.update(('import', a.name) for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                imports.update((n.module, a.name) for a in n.names)
        self.assertEqual(imports, {('import', 'datetime'), ('import', 'json'), ('import', 'os'), ('import', 're'),
                                   ('import', 'sys'), ('aieos_bootstrap', 'writer')})
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        self.assertFalse(names & {'open', 'exec', 'eval', 'compile', '__import__', 'input', 'sqlite3', 'subprocess'})
        self.assertFalse(attrs & {'open', 'makedirs', 'remove', 'unlink', 'write_text', 'write_bytes', 'connect'})
        strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertFalse([s for s in strings if '.aieos' in s])

    def test_the_only_writer_function_is_session_leases(self):
        """TASK-078 AC6: every writer attribute the module uses is session_leases or StoreResult, and a status call
        through a stand-in writer holding only those two works."""
        tree = self.tree()
        used = {n.attr for n in ast.walk(tree)
                if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == 'writer'}
        self.assertEqual(used, {'session_leases', 'StoreResult'})
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
        """TASK-078 AC8: the module's docstring and session_leases' state the scope and the limits (whitespace read
        as single spaces)."""
        doc = ' '.join(ast.get_docstring(ast.parse((SRC / 'mcp_server.py').read_bytes().decode('utf-8'))).split())
        for words in ('"2025-06-18"', 'initialize, notifications/initialized, tools/list and tools/call',
                      'lists one tool, status', 'AIEOS_SESSION_ID', 'AIEOS_BASE is not read in this slice',
                      '"expired" exists only between a lease\'s expiry and the next expire_leases',
                      'core_error for more than one unexpired row', 'hand-kept copy', 'are the owner\'s acts',
                      'at most tier T2, as a target and unmeasured', 'writes nothing'):
            self.assertIn(words, doc, words)
        wdoc = ' '.join(writer.session_leases.__doc__.split())
        for words in ('task TASK-078', 'hand-kept copy', 'and the next expire_leases',
                      'More than one unexpired row', 'writes and creates nothing', 'a stated choice'):
            self.assertIn(words, wdoc, words)


def names_its_criteria(doc):
    """True when ``doc`` names "TASK-078 ACn" and no other task's AC in qualified form (whitespace collapsed)."""
    doc = ' '.join((doc or '').split())
    return bool(re.findall(r'TASK-078 AC[0-9]+', doc)) and not re.findall(r'TASK-(?!078 )[0-9]+ AC[0-9]+', doc)


class AC8Naming(unittest.TestCase):
    def test_every_test_names_its_criteria(self):
        """TASK-078 AC8: every test function of this module and of the property module names "TASK-078 ACn" in its
        own docstring and no other task's AC."""
        for path in (HERE, HERE.parents[1] / 'property' / 'test_mcp_server_properties.py'):
            tree = ast.parse(path.read_bytes().decode('utf-8'))
            for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test')]:
                with self.subTest(path=path.name, test=fn.name):
                    self.assertTrue(names_its_criteria(ast.get_docstring(fn)))

    def test_the_naming_check_refuses(self):
        """TASK-078 AC8: the check refuses a missing id, another task's id, and this task's id beside another's."""
        self.assertFalse(names_its_criteria(None))
        self.assertFalse(names_its_criteria('made up, no id'))
        self.assertFalse(names_its_criteria('TASK-077 AC1: made up.'))
        self.assertFalse(names_its_criteria('TASK-078 AC1 and TASK-076 AC2: made up.'))
        self.assertTrue(names_its_criteria('TASK-078 AC1: made up.'))


if __name__ == '__main__':
    unittest.main()

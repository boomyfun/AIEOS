"""Unit tests of the MCP tools get_work_order and query of aieos_bootstrap.mcp_server (task TASK-083): the listing and
the dispatch, the identity and the base, the input's shape, the lease, the Work Order, query, writing nothing, purity
and touch, and the module docstring. Every store, log and reader answer comes from stand-ins patched in for the test
(writer.session_leases, writer.read_log, base_inputs.work_order_inputs); context_compiler.build_work_order is the real
one unless a test says otherwise. No test runs Git or writes a file; the source is read with pathlib's read_bytes."""

import ast
import datetime
import hashlib
import json
import pathlib
import random
import types
import unittest
from unittest import mock

from aieos_bootstrap import base_inputs, context_compiler, mcp_server, writer

HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / 'src' / 'aieos_bootstrap' / 'mcp_server.py'
ROOT = str(HERE.parents[2])
T0 = datetime.datetime(2026, 10, 24, 12, 0, 0, tzinfo=datetime.timezone.utc)
H1 = datetime.timedelta(hours=1)
BASE = 'a' * 40
CH = 'c' * 64
ENV = {'AIEOS_SESSION_ID': 's-1', 'AIEOS_ROOT': ROOT, 'AIEOS_BASE': BASE}
LOG = b'the log\n'


def inputs(decision='CONTINUE', task='TASK-100'):
    """A value build_work_order accepts: the spec is held in full in layer 3 and as a reference in layer 4, and
    src/x.py only as a reference (layer 4's budget of 5 bytes)."""
    return {
        'task': task, 'session_id': 's-1', 'base': BASE,
        'contract': {'task': task, 'contract_version': 'v1', 'traces_to': ['docs/specs/s.md'],
                     'write_set': {'paths': ['src/x.py']}, 'read_set': {'paths': ['docs/specs/s.md']},
                     'acceptance_criteria': [{'AC1': 'one'}]},
        'contract_hash': CH,
        'resume_record': {'decision': decision, 'subject': task, 'contract_hash': CH, 'contract_version': 'v1',
                          'constitution': {'applicable': ['INV-001'], 'violated': [], 'no_result': []}},
        'articles': {'INV-001': '### INV-001 · text'}, 'components': [], 'interfaces': [], 'adrs': {},
        'traced': {'docs/specs/s.md': 'the spec\n'},
        'files': {'docs/specs/s.md': 'the spec\n', 'src/x.py': 'X = 1\n'},
        'derived_read_set': [], 'last_handoff': None,
        'budgets': {'constitution': 1000, 'components': 1000, 'traced': 1000, 'files': 5, 'handoff': 1000}}


def lease(task='TASK-100', expires=T0 + H1, counter=1):
    return {'task_id': task, 'expires_at': expires, 'fencing_token': {'epoch': 1, 'counter': counter}}


def rows(*leases, ended=False):
    return writer.StoreResult('done', 'rows', value={'ended': ended, 'leases': list(leases)})


class Stand:
    """The stand-ins: session_leases answers ``answer``, read_log ``log``, work_order_inputs ``found`` (a function of
    the log, or a fixed pair); every call is recorded in ``calls``."""

    def __init__(self, answer=None, log=LOG, found=None):
        self.answer = rows(lease()) if answer is None else answer
        self.log = log
        self.found = found if found is not None else (lambda data: (inputs(), None))
        self.calls = []

    def session_leases(self, root, session_id, now, timeout=5.0):
        self.calls.append(('session_leases', root, session_id, now))
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer

    def read_log(self, root):
        self.calls.append(('read_log', root))
        if isinstance(self.log, Exception):
            raise self.log
        return self.log

    def work_order_inputs(self, repo, commit, task_id, session_id, log, read=None):
        self.calls.append(('work_order_inputs', repo, commit, task_id, session_id, log, read))
        found = self.found
        if isinstance(found, Exception):
            raise found
        return found(log) if callable(found) else found

    def append_event(self, *args, **kw):
        self.calls.append(('append_event',))
        raise AssertionError('append_event called')

    def run(self, tool, arguments, environ=ENV, read=None):
        with mock.patch.object(writer, 'session_leases', self.session_leases), \
                mock.patch.object(writer, 'read_log', self.read_log), \
                mock.patch.object(writer, 'append_event', self.append_event), \
                mock.patch.object(base_inputs, 'work_order_inputs', self.work_order_inputs):
            fn = mcp_server.get_work_order if tool == 'get_work_order' else mcp_server.query
            return fn(arguments, environ, T0, read)

    def handle(self, line, environ=ENV):
        with mock.patch.object(writer, 'session_leases', self.session_leases), \
                mock.patch.object(writer, 'read_log', self.read_log), \
                mock.patch.object(base_inputs, 'work_order_inputs', self.work_order_inputs):
            return mcp_server.handle(line, environ, lambda: T0)

    def names(self):
        return [c[0] for c in self.calls]


def call_line(name, arguments=None, id_=1):
    params = {'name': name}
    if arguments is not None:
        params['arguments'] = arguments
    return json.dumps({'jsonrpc': '2.0', 'id': id_, 'method': 'tools/call', 'params': params})


def text_of(answer):
    return answer['result']['content'][0]['text']


def expected_work_order():
    work_order, findings = context_compiler.build_work_order(inputs())
    assert findings is None, findings
    return work_order


def tree():
    return ast.parse(SRC.read_bytes().decode('utf-8'))


def functions():
    return {n.name: n for n in ast.walk(tree()) if isinstance(n, ast.FunctionDef)}


NEW = ('_base', '_detail', '_inputs_at_base', '_compiled', 'get_work_order', '_items_of', 'query')


class TASK083AC1Listing(unittest.TestCase):
    def test_seven_tools_and_schemas(self):
        """TASK-083 AC1: tools/list lists exactly seven tools in order, with the two new input schemas."""
        a = mcp_server.handle(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}), ENV, lambda: T0)
        tools = a['result']['tools']
        self.assertEqual([t['name'] for t in tools], ['status', 'acknowledge', 'ask', 'report', 'handoff',
                                                      'get_work_order', 'query'])
        self.assertEqual(tools[5]['inputSchema'], {'type': 'object', 'properties': {}})
        self.assertEqual(tools[6]['inputSchema'], {'type': 'object', 'properties': {'ref': {'type': 'string'}},
                                                   'required': ['ref']})

    def test_dispatch_and_error_forms(self):
        """TASK-083 AC1: tools/call runs each tool in the existing result form; a dict error is answered as is and a
        word error as {"error": <word>}; an unlisted name answers -32602."""
        s = Stand()
        a = s.handle(call_line('get_work_order', {}))
        self.assertFalse(a['result']['isError'])
        self.assertEqual(json.loads(text_of(a)), expected_work_order())
        a = s.handle(call_line('query', {'ref': 'INV-001'}))
        self.assertFalse(a['result']['isError'])
        self.assertEqual(json.loads(text_of(a))['ref'], 'INV-001')
        s = Stand(found=(None, ['made up']))
        a = s.handle(call_line('get_work_order'))
        self.assertTrue(a['result']['isError'])
        self.assertEqual(json.loads(text_of(a)), {'error': 'core_error', 'detail': ['made up']})
        a = Stand().handle(call_line('query', {'ref': 'nothing here'}))
        self.assertEqual(json.loads(text_of(a)), {'error': 'out_of_scope'})
        a = Stand().handle(call_line('list_tasks'))
        self.assertEqual(a['error']['code'], -32602)

    def test_status_and_ask_answers_fixed(self):
        """TASK-083 AC1: status's and ask's answers through handle equal fixed expected texts (a status success and a
        no_session error, an ask success and an invalid_input error)."""
        s = Stand(answer=writer.StoreResult('refused', 'session'))
        a = s.handle(call_line('status'))
        self.assertEqual(a['result'], {'content': [{'type': 'text', 'text': '{"lease": "none", "task": null}'}],
                                       'isError': False})
        a = mcp_server.handle(call_line('status'), {}, lambda: T0)
        self.assertEqual(a['result'], {'content': [{'type': 'text', 'text': '{"error": "no_session"}'}],
                                       'isError': True})
        a = mcp_server.handle(call_line('ask', {}), ENV, lambda: T0)
        self.assertEqual(a['result'], {'content': [{'type': 'text', 'text': '{"error": "invalid_input"}'}],
                                       'isError': True})
        appended = types.SimpleNamespace(result='appended', reason=None, seq=1, line=b'', findings=())

        def append(root, event_type, payload, event_id, now, recorder, task_id=None, fencing_token=None):
            return writer.WriteResult(appended)
        args = {'question': 'q'}
        call = hashlib.sha256(json.dumps(args, sort_keys=True, separators=(',', ':'),
                                         ensure_ascii=False).encode('utf-8')).hexdigest()
        digest = hashlib.sha256('\n'.join(['s-1', 'TASK-100', 'ask', call, 'question', '1', 'q']).encode('utf-8'))
        with mock.patch.object(writer, 'session_leases', lambda *a, **k: rows(lease())), \
                mock.patch.object(writer, 'append_event', append):
            a = mcp_server.handle(call_line('ask', args), ENV, lambda: T0)
        self.assertEqual(a['result'], {'content': [{'type': 'text', 'text': '{"records": ["mcp-claim/%s"]}'
                                                    % digest.hexdigest()}], 'isError': False})


class RecordingEnv(dict):
    def __init__(self, *a, **k):
        dict.__init__(self, *a, **k)
        self.read = []

    def get(self, key, default=None):
        self.read.append(key)
        return dict.get(self, key, default)


class TASK083AC2IdentityAndBase(unittest.TestCase):
    def test_identity_and_base_refused_with_no_calls(self):
        """TASK-083 AC2: the identity or the base missing or out of form gives no_session with zero writer and read
        calls."""
        bad = [dict(ENV, AIEOS_SESSION_ID=''), dict(ENV, AIEOS_ROOT='relative'), {k: v for k, v in ENV.items()
                                                                                    if k != 'AIEOS_BASE'},
               dict(ENV, AIEOS_BASE='a' * 64), dict(ENV, AIEOS_BASE='A' * 40), dict(ENV, AIEOS_BASE='a' * 39),
               dict(ENV, AIEOS_BASE='a' * 41), dict(ENV, AIEOS_BASE=5)]
        for tool, args in (('get_work_order', {}), ('query', {'ref': 'INV-001'})):
            for env in bad:
                with self.subTest(tool=tool, env=env):
                    s = Stand()
                    reads = []
                    self.assertEqual(s.run(tool, args, env, read=lambda *a: reads.append(a)), (None, 'no_session'))
                    self.assertEqual(s.calls, [])
                    self.assertEqual(reads, [])

    def test_identity_before_base(self):
        """TASK-083 AC2: with the identity missing or out of form, AIEOS_BASE is never read."""
        for env in ({'AIEOS_BASE': BASE}, {'AIEOS_SESSION_ID': 'a b', 'AIEOS_ROOT': ROOT, 'AIEOS_BASE': BASE}):
            for tool, args in (('get_work_order', {}), ('query', {'ref': 'x'})):
                e = RecordingEnv(env)
                self.assertEqual(Stand().run(tool, args, e), (None, 'no_session'))
                self.assertNotIn('AIEOS_BASE', e.read)

    def test_base_constant_only_in_base(self):
        """TASK-083 AC2: no ast.Constant equal to "AIEOS_BASE" lies outside _base; only get_work_order and query call
        _base."""
        t = tree()
        fns = {n.name: n for n in ast.walk(t) if isinstance(n, ast.FunctionDef)}
        inside = {id(n) for n in ast.walk(fns['_base'])}
        outside = [n for n in ast.walk(t) if isinstance(n, ast.Constant) and n.value == 'AIEOS_BASE'
                   and id(n) not in inside]
        self.assertEqual(outside, [])
        callers = {name for name, f in fns.items() for n in ast.walk(f)
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == '_base'}
        self.assertEqual(callers, {'get_work_order', 'query'})


class TASK083AC3Shape(unittest.TestCase):
    def test_shapes(self):
        """TASK-083 AC3: get_work_order takes arguments absent, null or {} only; query exactly {ref: a non-empty str};
        each refusal before any writer or read call."""
        for args in (None, {}):
            self.assertIsNone(Stand().run('get_work_order', args)[1])
        for args in ({'x': 1}, [], 'a', 0, False):
            s = Stand()
            self.assertEqual(s.run('get_work_order', args), (None, 'invalid_input'), args)
            self.assertEqual(s.calls, [])
        for args in (None, {}, {'ref': ''}, {'ref': 3}, {'ref': '\ud800'}, {'ref': 'x', 'y': 1}, ['x']):
            s = Stand()
            self.assertEqual(s.run('query', args), (None, 'invalid_input'), args)
            self.assertEqual(s.calls, [])


class TASK083AC4Lease(unittest.TestCase):
    def test_lease_words(self):
        """TASK-083 AC4: no_lease, lease_expired, core_error and no_session as the claim tools give them; no log read
        and no reader call before a live lease."""
        cases = [(writer.StoreResult('refused', 'session'), 'no_lease'), (rows(ended=True), 'no_lease'),
                 (rows(), 'no_lease'), (rows(lease(expires=T0)), 'lease_expired'),
                 (rows(lease(), lease('TASK-101', counter=2)), 'core_error'),
                 (writer.StoreResult('refused', 'root'), 'no_session'),
                 (writer.StoreResult('refused', 'no_store'), 'no_session')]
        for tool, args in (('get_work_order', {}), ('query', {'ref': 'INV-001'})):
            for answer, word in cases:
                with self.subTest(tool=tool, word=word):
                    s = Stand(answer=answer)
                    self.assertEqual(s.run(tool, args), (None, word))
                    self.assertEqual(s.names(), ['session_leases'])

    def test_task_from_the_lease(self):
        """TASK-083 AC4: the task given to work_order_inputs is the lease's, never the input's (a query ref "TASK-1"
        under a lease of TASK-100)."""
        s = Stand()
        s.run('query', {'ref': 'TASK-1'})
        self.assertEqual([c[3] for c in s.calls if c[0] == 'work_order_inputs'], ['TASK-100'])


class TASK083AC5WorkOrder(unittest.TestCase):
    def test_inputs_call_and_value(self):
        """TASK-083 AC5: work_order_inputs is called once with (root, base, the lease's task, the session id, the log,
        the read given), and get_work_order answers build_work_order's value unchanged."""
        s = Stand()
        reader = object()
        value, word = s.run('get_work_order', {}, read=reader)
        self.assertIsNone(word)
        self.assertEqual(value, expected_work_order())
        self.assertEqual([c for c in s.calls if c[0] == 'work_order_inputs'],
                         [('work_order_inputs', ROOT, BASE, 'TASK-100', 's-1', LOG, reader)])

    def test_findings_and_log(self):
        """TASK-083 AC5: findings of work_order_inputs or of build_work_order give the core_error with detail; a log
        answer that is not bytes gives core_error with no detail and no work_order_inputs call."""
        self.assertEqual(Stand(found=(None, ['f1', 'f2'])).run('get_work_order', {}),
                         (None, {'error': 'core_error', 'detail': ['f1', 'f2']}))
        broken = inputs()
        broken['budgets'] = {}
        value, word = Stand(found=(broken, None)).run('get_work_order', {})
        self.assertEqual(word['error'], 'core_error')
        self.assertTrue(word['detail'])
        for log in ('text', None, 3):
            s = Stand(log=log)
            self.assertEqual(s.run('get_work_order', {}), (None, 'core_error'))
            self.assertNotIn('work_order_inputs', s.names())

    def test_compiled_at_each_call(self):
        """TASK-083 AC5: two calls over the same stand-ins give equal objects; a call after a changed log gives the
        object of the new log (no cache across calls)."""
        s = Stand(found=lambda log: (inputs('CONTINUE_WITH' if log == b'new\n' else 'CONTINUE'), None))
        first = s.run('get_work_order', {})[0]
        self.assertEqual(s.run('get_work_order', {})[0], first)
        s.log = b'new\n'
        changed = s.run('get_work_order', {})[0]
        self.assertEqual((first['decision'], changed['decision']), ('CONTINUE', 'CONTINUE_WITH'))
        self.assertEqual(s.names().count('work_order_inputs'), 3)


class TASK083AC6Query(unittest.TestCase):
    def test_full_reference_and_scope(self):
        """TASK-083 AC6: a ref held in full answers that item; a ref held as a reference answers the unbudgeted
        build's content with the same hash; a ref the Work Order does not hold gives out_of_scope."""
        wo = expected_work_order()
        items = {i['ref']: i for layer in wo['layers'] for i in layer['items']}
        self.assertNotIn('content', items['src/x.py'])
        value, word = Stand().run('query', {'ref': 'INV-001'})
        self.assertEqual(value, {'ref': 'INV-001', 'hash': items['INV-001']['hash'], 'content': '### INV-001 · text'})
        value, word = Stand().run('query', {'ref': 'src/x.py'})
        self.assertEqual(value, {'ref': 'src/x.py', 'hash': items['src/x.py']['hash'], 'content': 'X = 1\n'})
        for ref in ('INV-002', 'docs/other.md', 'AC2', 'made up'):
            self.assertEqual(Stand().run('query', {'ref': ref}), (None, 'out_of_scope'), ref)

    def test_two_layers(self):
        """TASK-083 AC6: a ref in two layers answers its first full item by layer order when the hashes agree, and
        not_found when they differ."""
        value, word = Stand().run('query', {'ref': 'docs/specs/s.md'})
        self.assertEqual((value['content'], word), ('the spec\n', None))
        real = context_compiler.build_work_order

        def differing(inp):
            wo, f = real(inp)
            wo['layers'][3]['items'] = [dict(i, hash='0' * 64) if i['ref'] == 'docs/specs/s.md' else i
                                        for i in wo['layers'][3]['items']]
            return wo, f
        with mock.patch.object(context_compiler, 'build_work_order', differing):
            self.assertEqual(Stand().run('query', {'ref': 'docs/specs/s.md'}), (None, 'not_found'))

    def test_unbudgeted_guard(self):
        """TASK-083 AC6: a reference whose unbudgeted item is missing or has another hash gives not_found; findings of
        the unbudgeted build give core_error with detail."""
        real = context_compiler.build_work_order

        def second(change):
            def fn(inp):
                if inp['budgets']['files'] == 5:
                    return real(inp)
                return change(inp)
            return fn

        def missing(inp):
            wo, f = real(inp)
            wo['layers'][3]['items'] = [i for i in wo['layers'][3]['items'] if i['ref'] != 'src/x.py']
            return wo, f

        def other_hash(inp):
            wo, f = real(inp)
            wo['layers'][3]['items'] = [dict(i, hash='1' * 64) if i['ref'] == 'src/x.py' else i
                                        for i in wo['layers'][3]['items']]
            return wo, f
        for change in (missing, other_hash):
            with mock.patch.object(context_compiler, 'build_work_order', second(change)):
                self.assertEqual(Stand().run('query', {'ref': 'src/x.py'}), (None, 'not_found'))
        with mock.patch.object(context_compiler, 'build_work_order', second(lambda inp: (None, ['late']))):
            self.assertEqual(Stand().run('query', {'ref': 'src/x.py'}),
                             (None, {'error': 'core_error', 'detail': ['late']}))

    def test_random_refs(self):
        """TASK-083 AC6: 500 seeded random refs give only items of the Work Order or out_of_scope, and never raise."""
        wo = expected_work_order()
        refs = sorted({i['ref'] for layer in wo['layers'] for i in layer['items']})
        rng = random.Random(83)
        for _ in range(500):
            if rng.random() < 0.5:
                base = rng.choice(refs)
                k = rng.randrange(len(base))
                ref = base[:k] + rng.choice('abxyz/.-0') + base[k + 1:]
            else:
                ref = ''.join(rng.choice('abcdefghijklmnopqrstuvwxyz/.-_ 0123456789') for _ in range(rng.randint(1, 20)))
            value, word = Stand().run('query', {'ref': ref})
            if ref in refs:
                self.assertIsNone(word, ref)
                self.assertEqual(value['ref'], ref)
            else:
                self.assertEqual((value, word), (None, 'out_of_scope'), ref)


class TASK083AC7WritesNothing(unittest.TestCase):
    def test_new_functions_use_only_reads(self):
        """TASK-083 AC7: every function the task adds uses of writer at most session_leases and read_log, and none
        calls append_event."""
        fns = functions()
        for name in NEW:
            used = {n.attr for n in ast.walk(fns[name])
                    if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == 'writer'}
            self.assertLessEqual(used, {'session_leases', 'read_log'}, name)

    def test_stand_in_writer_without_append(self):
        """TASK-083 AC7: a call through a writer holding only session_leases, read_log and StoreResult answers, and
        nothing is appended."""
        s = Stand()
        stand_in = types.SimpleNamespace(session_leases=s.session_leases, read_log=s.read_log,
                                         StoreResult=writer.StoreResult)
        with mock.patch.object(mcp_server, 'writer', stand_in), \
                mock.patch.object(base_inputs, 'work_order_inputs', s.work_order_inputs):
            self.assertIsNone(mcp_server.get_work_order({}, ENV, T0)[1])
            self.assertIsNone(mcp_server.query({'ref': 'INV-001'}, ENV, T0)[1])
        self.assertNotIn('append_event', s.names())


class TASK083AC8Purity(unittest.TestCase):
    def test_imports_names_and_strings(self):
        """TASK-083 AC8: mcp_server.py imports exactly its seven modules; no refused name, call or string; no except
        clause whose body is only pass or continue."""
        t = tree()
        imports = set()
        for n in ast.walk(t):
            if isinstance(n, ast.Import):
                imports.update(a.name for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                imports.update('%s.%s' % (n.module, a.name) for a in n.names)
        self.assertEqual(imports, {'datetime', 'hashlib', 'json', 'os', 're', 'sys', 'aieos_bootstrap.writer',
                                   'aieos_bootstrap.base_inputs', 'aieos_bootstrap.context_compiler'})
        names = {n.id for n in ast.walk(t) if isinstance(n, ast.Name)}
        self.assertFalse(names & {'open', 'exec', 'eval', 'compile', '__import__', 'input', 'sqlite3', 'subprocess'})
        attrs = {n.attr for n in ast.walk(t) if isinstance(n, ast.Attribute)}
        self.assertFalse(attrs & {'open', 'makedirs', 'remove', 'unlink', 'write_text', 'write_bytes', 'connect'})
        strings = [n.value for n in ast.walk(t) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertFalse([s for s in strings if ('.' + 'aieos') in s])
        for n in ast.walk(t):
            if isinstance(n, ast.ExceptHandler):
                self.assertFalse(all(isinstance(s, (ast.Pass, ast.Continue)) for s in n.body))

    def test_never_raises(self):
        """TASK-083 AC8: stand-ins that raise, a RecursionError among them, give core_error."""
        for exc in (RuntimeError('x'), RecursionError('deep'), MemoryError()):
            for where in ('answer', 'log', 'found'):
                s = Stand(**{where: exc})
                for tool, args in (('get_work_order', {}), ('query', {'ref': 'INV-001'})):
                    self.assertEqual(s.run(tool, args), (None, 'core_error'), (exc, where, tool))
            with mock.patch.object(context_compiler, 'build_work_order', side_effect=exc):
                for tool, args in (('get_work_order', {}), ('query', {'ref': 'INV-001'})):
                    self.assertEqual(Stand().run(tool, args), (None, 'core_error'))


PHRASES = ['tasks TASK-078 and TASK-079', 'task TASK-083', 'lists seven tools', 'AIEOS_BASE is read only by _base',
           'compiled at each call', 'only the refs the Work Order holds', 'writes nothing']


class TASK083AC10Docstring(unittest.TestCase):
    def test_docstring_phrases(self):
        """TASK-083 AC10: the module docstring holds the contract's phrases, whitespace read as single spaces."""
        doc = ' '.join(ast.get_docstring(tree()).split())
        for phrase in PHRASES:
            self.assertIn(phrase, doc)

    def test_naming(self):
        """TASK-083 AC10: every test of this module names "TASK-083 ACn" at the start of its docstring."""
        classes = [v for v in globals().values() if isinstance(v, type) and issubclass(v, unittest.TestCase)
                   and v.__module__ == __name__]
        self.assertGreater(len(classes), 5)
        for cls in classes:
            for name in unittest.TestLoader().getTestCaseNames(cls):
                self.assertRegex(getattr(cls, name).__doc__ or '', r'^TASK-083 AC\d+', name)


if __name__ == '__main__':
    unittest.main()

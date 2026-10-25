"""Tests of the handoff file (task TASK-087): handoff_file.compose and handoff_file.write by stand-ins only, with a
fixed literal root; writer.write_handoff's real-folder tests are in tests/unit/test_writer.py (TASK087WriteHandoff)."""

import ast
import json
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import handoff_file, mcp_server, writer

ROOT = 'C:/handoff-root-87'
TASK = 'TASK-087'
SESSION = 'launch-0123abcd'
COMMIT = '0123456789abcdef0123456789abcdef01234567'
HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / 'src' / 'aieos_bootstrap'
WRITER_TESTS = HERE.parent / 'test_writer.py'


def record(name, n, text, session=SESSION, task=TASK, kind='claim', refers=True):
    """One handoff item's record in mcp_server's form (mcp_server.py :323-328)."""
    r = {'record_id': 'mcp-claim/%s-%d' % (name, n), 'fact_kind': kind, 'source_class': 'agent_declared',
         'recorder': 'aieos mcp_server, session %s' % session, 'subject': task, 'session': session, 'text': text}
    if refers:
        r['refers_to'] = 'handoffs/%s-%s.md#%s/%d' % (task, session, name, n)
    return r


def line(payload, kind='record.added', ascii_only=False):
    return json.dumps({'type': kind, 'payload': payload}, ensure_ascii=ascii_only).encode('utf-8')


def log_of(*records, extra=()):
    return b'\n'.join([line(r) for r in records] + list(extra)) + b'\n'


def full_log():
    return log_of(record('done', 1, 'the first'), record('done', 2, 'the second'), record('not_done', 1, 'one left'),
                  record('discoveries', 1, 'a find'), record('proposals', 1, 'an idea'))


FULL_TEXT = ('---\ntask: TASK-087\nsession: "launch-0123abcd"\ncommit: "0123456789abcdef0123456789abcdef01234567"\n'
             'done:\n  - "the first"\n  - "the second"\nnot_done:\n  - "one left"\nassumptions: []\n'
             'discoveries:\n  - "a find"\nrisks: []\nproposals:\n  - "an idea"\n---\n')


class TASK087Compose(unittest.TestCase):

    def test_a_full_handoff(self):
        """TASK-087 AC1: a handoff of all six lists, some empty, gives "composed" with the path and exactly the
        text, with the commit quoted, and with "commit: null"."""
        r = handoff_file.compose(full_log(), TASK, SESSION, COMMIT)
        self.assertEqual(tuple(r), handoff_file.COMPOSE_KEYS)
        self.assertEqual((r['result'], r['path'], r['findings']),
                         ('composed', '.aieos/handoffs/%s-%s.md' % (TASK, SESSION), []))
        self.assertEqual(r['text'], FULL_TEXT)
        r = handoff_file.compose(full_log(), TASK, SESSION, None)
        self.assertEqual(r['text'], FULL_TEXT.replace('commit: "%s"' % COMMIT, 'commit: null'))
        self.assertNotIn('\r', r['text'])

    def test_quoting_and_escapes(self):
        """TASK-087 AC1: a session id "123" stays a quoted string; non-ASCII is kept; U+0085, U+2028 and U+2029 are
        written escaped; each item line's JSON part decodes back to its text."""
        breaks = 'a' + chr(0x85) + 'b' + chr(0x2028) + 'c' + chr(0x2029) + 'd'
        texts = ['caf' + chr(0xe9), breaks, 'quote " and back\\slash', 'new\nline']
        log = log_of(*[record('risks', n, t, session='123') for n, t in enumerate(texts, 1)])
        r = handoff_file.compose(log, TASK, '123', None)
        self.assertEqual(r['result'], 'composed')
        self.assertIn('\nsession: "123"\n', r['text'])
        self.assertIn('caf' + chr(0xe9), r['text'])
        for code in (0x85, 0x2028, 0x2029):
            self.assertNotIn(chr(code), r['text'])
            self.assertIn('\\u%04x' % code, r['text'])
        items = [x[len('  - '):] for x in r['text'].split('\n') if x.startswith('  - ')]
        self.assertEqual([json.loads(x) for x in items], texts)

    def test_blank_lines_and_left_out_records(self):
        """TASK-087 AC1: empty and whitespace-only lines are skipped; claims of another session, of another task,
        with no refers_to, of another kind, and other event types are left out."""
        log = log_of(record('done', 1, 'mine'), record('done', 1, 'theirs', session='launch-other'),
                     record('done', 1, 'other task', task='TASK-1'), record('done', 2, 'no ref', refers=False),
                     record('done', 2, 'an observation', kind='observation'),
                     extra=[b'', b'   ', line(record('done', 2, 'wrong type'), kind='task.submitted')])
        r = handoff_file.compose(log, TASK, SESSION, None)
        self.assertEqual(r['result'], 'composed')
        self.assertIn('done:\n  - "mine"\nnot_done: []', r['text'])

    def test_none(self):
        """TASK-087 AC1: a log with no handoff claim gives "none"."""
        for log in (b'', b'\n', log_of(record('done', 1, 'theirs', session='launch-other'))):
            with self.subTest(log=log):
                self.assertEqual(handoff_file.compose(log, TASK, SESSION, None),
                                 {'result': 'none', 'path': None, 'text': None, 'findings': []})

    def test_refusals(self):
        """TASK-087 AC1: a log line that is not UTF-8, not JSON or not a JSON object, a refers_to naming another
        file or out of form, a list not in HANDOFF_LISTS, a place 0, with a leading zero or not a number, an empty,
        non-str or unencodable text, a gap and a repeated place each give "refused" with findings and no text."""
        ok = record('done', 1, 'fine')
        other_file = dict(record('done', 2, 'x'), refers_to='handoffs/%s-%s.md#done/2' % (TASK, 'launch-elsewhere'))
        cases = {
            'not utf-8': log_of(ok, extra=[b'\xff\xfe']),
            'not json': log_of(ok, extra=[b'{not json']),
            'not an object': log_of(ok, extra=[b'[1, 2]']),
            'another file': log_of(ok, other_file),
            'out of form': log_of(ok, dict(record('done', 2, 'x'),
                                           refers_to='handoffs/%s-%s.md#done' % (TASK, SESSION))),
            'bad list': log_of(ok, record('notes', 1, 'x')),
            'place 0': log_of(ok, record('risks', 0, 'x')),
            'leading zero': log_of(ok, dict(record('risks', 1, 'x'),
                                            refers_to='handoffs/%s-%s.md#risks/01' % (TASK, SESSION))),
            'not a number': log_of(ok, dict(record('risks', 1, 'x'),
                                            refers_to='handoffs/%s-%s.md#risks/one' % (TASK, SESSION))),
            'empty text': log_of(ok, record('risks', 1, '')),
            'non-str text': log_of(ok, dict(record('risks', 1, 'x'), text=7)),
            'unencodable': log_of(ok, extra=[line(record('risks', 1, 'bad ' + chr(0xd800)), ascii_only=True)]),
            'gap': log_of(ok, record('done', 3, 'x')),
            'repeat': log_of(ok, record('done', 1, 'again')),
        }
        for name, log in cases.items():
            with self.subTest(case=name):
                r = handoff_file.compose(log, TASK, SESSION, None)
                self.assertEqual((r['result'], r['path'], r['text']), ('refused', None, None))
                self.assertTrue(r['findings'])

    def test_arguments_and_no_raise(self):
        """TASK-087 AC1: arguments out of form give "refused"; no call raises; the result has exactly the keys."""
        cases = [(full_log(), 'TASK-x', SESSION, None), (full_log(), TASK, '..', None), (full_log(), TASK, 'a/b', None),
                 (full_log(), TASK, SESSION, 'ABC'), ('not bytes', TASK, SESSION, None), (None, TASK, SESSION, None),
                 (full_log(), 7, None, 8), (full_log(), TASK, '', None), (full_log(), TASK, 'x' * 129, None)]
        for args in cases:
            with self.subTest(args=args[1:]):
                r = handoff_file.compose(*args)
                self.assertEqual(tuple(r), handoff_file.COMPOSE_KEYS)
                self.assertEqual(r['result'], 'refused')
                self.assertTrue(all(isinstance(f, str) for f in r['findings']))


class Recorder:
    """Recording stand-ins for read_log and write_handoff."""

    def __init__(self, log=None, answer=None, read_raises=False, write_raises=False):
        self.calls = []
        self.log = full_log() if log is None else log
        self.answer = writer.StoreResult('done', value='x') if answer is None else answer
        self.read_raises, self.write_raises = read_raises, write_raises

    def read_log(self, root):
        self.calls.append(('read_log', root))
        if self.read_raises:
            raise OSError('no')
        return self.log

    def write_handoff(self, root, task_id, session_id, text):
        self.calls.append(('write_handoff', root, task_id, session_id, text))
        if self.write_raises:
            raise RuntimeError('no')
        return self.answer


def run(rec, **kw):
    args = dict(root=ROOT, task_id=TASK, session_id=SESSION, commit=COMMIT)
    args.update(kw)
    return handoff_file.write(args['root'], args['task_id'], args['session_id'], args['commit'],
                              read_log=rec.read_log, write_handoff=rec.write_handoff)


class TASK087Write(unittest.TestCase):

    def test_arguments_out_of_form(self):
        """TASK-087 AC2: arguments out of form give "argument" and no callee is called."""
        for kw in (dict(task_id='TASK-x'), dict(session_id='a/b'), dict(session_id='a\\b'), dict(session_id='.'),
                   dict(session_id='..'), dict(session_id=''), dict(session_id='x' * 129), dict(commit='ABC'),
                   dict(commit='0' * 39), dict(root='')):
            with self.subTest(kw=kw):
                rec = Recorder()
                r = run(rec, **kw)
                self.assertEqual((r['result'], r['reason']), ('refused', 'argument'))
                self.assertEqual(rec.calls, [])
        for name in ('read_log', 'write_handoff'):
            with self.subTest(callee=name):
                rec = Recorder()
                kw = {'read_log': rec.read_log, 'write_handoff': rec.write_handoff}
                kw[name] = 'not callable'
                r = handoff_file.write(ROOT, TASK, SESSION, COMMIT, **kw)
                self.assertEqual((r['result'], r['reason']), ('refused', 'argument'))
                self.assertEqual(rec.calls, [])

    def test_the_calls_and_written(self):
        """TASK-087 AC2: read_log once with root, then write_handoff once with the composed text; "done" gives
        "written" with the path; the result has exactly the keys."""
        rec = Recorder()
        r = run(rec)
        self.assertEqual(tuple(r), handoff_file.WRITE_KEYS)
        self.assertEqual(r, {'result': 'written', 'reason': None, 'findings': [],
                             'path': '.aieos/handoffs/%s-%s.md' % (TASK, SESSION)})
        self.assertEqual(rec.calls, [('read_log', ROOT), ('write_handoff', ROOT, TASK, SESSION, FULL_TEXT)])

    def test_none_and_claims(self):
        """TASK-087 AC2: on "none" and on a claims refusal write_handoff is not called."""
        rec = Recorder(log=b'')
        self.assertEqual(run(rec), {'result': 'none', 'reason': None, 'findings': [], 'path': None})
        self.assertEqual(rec.calls, [('read_log', ROOT)])
        rec = Recorder(log=log_of(record('done', 2, 'gap')))
        r = run(rec)
        self.assertEqual((r['result'], r['reason']), ('refused', 'claims'))
        self.assertEqual(rec.calls, [('read_log', ROOT)])

    def test_the_log_refusals(self):
        """TASK-087 AC2: a log that is not bytes or a raising read_log gives "log"."""
        for rec in (Recorder(log='text'), Recorder(read_raises=True)):
            with self.subTest(rec=rec.read_raises):
                r = run(rec)
                self.assertEqual((r['result'], r['reason']), ('refused', 'log'))

    def test_the_write_refusals(self):
        """TASK-087 AC2: a refused StoreResult, an answer that is not a StoreResult, an answer whose findings are a
        string, and a raise each give "write", the string giving no finding item."""
        refused = writer.StoreResult('refused', 'exists', ['exists: the handoff file is not empty'])
        stringy = writer.StoreResult('refused', 'exists', [])
        stringy.findings = 'a string'
        cases = [(Recorder(answer=refused), ['write: not done', 'exists: the handoff file is not empty']),
                 (Recorder(answer={'result': 'done'}), ['write: not done']),
                 (Recorder(answer=stringy), ['write: not done']),
                 (Recorder(write_raises=True), ['write: the write raised RuntimeError'])]
        for rec, findings in cases:
            with self.subTest(findings=findings):
                r = run(rec)
                self.assertEqual((r['result'], r['reason'], r['findings']), ('refused', 'write', findings))

    def test_the_defaults_are_taken_at_call_time(self):
        """TASK-087 AC2: with no callee given, writer.read_log and writer.write_handoff, patched after import, are
        the ones called."""
        rec = Recorder()
        with mock.patch.object(writer, 'read_log', rec.read_log), \
                mock.patch.object(writer, 'write_handoff', rec.write_handoff):
            r = handoff_file.write(ROOT, TASK, SESSION, COMMIT)
        self.assertEqual(r['result'], 'written')
        self.assertEqual([c[0] for c in rec.calls], ['read_log', 'write_handoff'])


def tree():
    return ast.parse((SRC / 'handoff_file.py').read_bytes().decode('utf-8'))


class TASK087Module(unittest.TestCase):

    def test_the_imports_and_names(self):
        """TASK-087 AC5: the imports are exactly json, re and writer; no refused name or attribute; no ".aieos"
        string; no assert; no prefix constant."""
        t = tree()
        imports = set()
        for n in ast.walk(t):
            if isinstance(n, ast.Import):
                imports.update(a.name for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                imports.update('%s.%s' % (n.module, a.name) for a in n.names)
        self.assertEqual(imports, {'json', 're', 'aieos_bootstrap.writer'})
        names = {n.id for n in ast.walk(t) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(t) if isinstance(n, ast.Attribute)}
        self.assertFalse(names & {'open', 'exec', 'eval', 'compile', '__import__', 'subprocess', 'os', 'sys', 'time',
                                  'datetime'})
        self.assertFalse(attrs & {'environ', 'getenv', 'now', 'write_text', 'open_store'})
        strings = [n.value for n in ast.walk(t) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertFalse([s for s in strings if '.aieos' in s])
        self.assertFalse([n for n in ast.walk(t) if isinstance(n, ast.Assert)])
        top = [x.id for n in t.body if isinstance(n, ast.Assign) for x in n.targets if isinstance(x, ast.Name)]
        self.assertFalse([name for name in top if 'PREFIX' in name], top)

    def test_the_lists_equal_mcp_servers(self):
        """TASK-087 AC5: HANDOFF_LISTS equals mcp_server.HANDOFF_LISTS."""
        self.assertEqual(handoff_file.HANDOFF_LISTS, mcp_server.HANDOFF_LISTS)

    def test_this_file_keeps_the_rules(self):
        """TASK-087 AC5: this test file uses no tempfile, sqlite3, shutil or open, roots only the literal root, and
        uses no one-argument .replace() and no .replace(target=...)."""
        t = ast.parse(HERE.read_bytes().decode('utf-8'))
        imported = set()
        for n in ast.walk(t):
            if isinstance(n, ast.Import):
                imported.update(a.name.split('.')[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                imported.add((n.module or '').split('.')[0])
        self.assertFalse(imported & {'tempfile', 'sqlite3', 'shutil'})
        self.assertNotIn('open', {n.id for n in ast.walk(t) if isinstance(n, ast.Name)})
        for n in ast.walk(t):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'replace':
                self.assertNotEqual(len(n.args), 1)
                self.assertNotIn('target', [k.arg for k in n.keywords])
        roots = [n.value for n in ast.walk(t) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                 and n.value.startswith('C:/') and n.value != 'C:/']
        self.assertEqual(set(roots), {ROOT})


class TASK087Docs(unittest.TestCase):

    def test_the_module_docstring(self):
        """TASK-087 AC6, as TASK-094 AC3 changes it: handoff_file's docstring holds its phrases, "calls write after
        the launcher" in place of "nothing calls write but its tests", which is gone."""
        doc = ' '.join(handoff_file.__doc__.split())
        for phrase in ('the handoff file', 'specification 2 section 5.2', 'calls write after the launcher',
                       'not committed', 'the last handoff', "the caller's commit", 'create-only', 'never raises',
                       'TASK-087'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, doc)
        self.assertNotIn('nothing calls write but its tests', doc)

    def test_every_new_test_names_its_ac(self):
        """TASK-087 AC6: every test of this file, and every test of TASK087WriteHandoff in tests/unit/test_writer.py,
        names "TASK-087 AC" in its docstring."""
        found = 0
        for path, wanted in ((HERE, None), (WRITER_TESTS, 'TASK087WriteHandoff')):
            t = ast.parse(path.read_bytes().decode('utf-8'))
            for c in t.body:
                if not isinstance(c, ast.ClassDef) or (wanted is not None and c.name != wanted):
                    continue
                for f in c.body:
                    if isinstance(f, ast.FunctionDef) and f.name.startswith('test_'):
                        found += 1
                        with self.subTest(test=f.name):
                            self.assertIn('TASK-087 AC', ast.get_docstring(f) or '')
        self.assertGreater(found, 20)


if __name__ == '__main__':
    unittest.main()

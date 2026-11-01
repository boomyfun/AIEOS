"""Tests of the handoff file (task TASK-087): handoff_file.compose and handoff_file.write by stand-ins only, with a
fixed literal root; writer.write_handoff's real-folder tests are in tests/unit/test_writer.py (TASK087WriteHandoff).
TASK-111's lookup tests also call records.check_log and eventlog._token_text directly."""

import ast
import json
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import eventlog, handoff_file, mcp_server, records, writer

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


TOKEN = {'epoch': 'e1', 'counter': 2}
OTHER_TOKEN = {'epoch': 'e1', 'counter': 3}
SUB1 = '1111111111111111111111111111111111111111'
SUB2 = '2222222222222222222222222222222222222222'


def submitted(event_id, commit=SUB1, token=TOKEN, task=TASK, compensating=False, seq=1, **over):
    """One task.submitted line in eventlog's form (task TASK-111's tests)."""
    event = {'event_id': event_id, 'type': 'task.submitted', 'task_id': task, 'seq': seq,
             'appended_at': '2026-11-01T00:00:00Z', 'payload': {'commit': commit, 'compensating': compensating},
             'fencing_token': token}
    event.update(over)
    return json.dumps(event).encode('utf-8')


def lines_of(*lines):
    return b'\n'.join(lines) + b'\n'


class TASK111Lookup(unittest.TestCase):

    def look(self, *lines, token=TOKEN, task=TASK):
        return handoff_file.submitted_commit(lines_of(*lines), task, token)

    def test_no_match_gives_none_and_no_finding(self):
        """TASK-087 AC2 (amended by TASK-111): an empty log, a submission of another task and a log with no
        submission give (None, [])."""
        self.assertEqual(handoff_file.submitted_commit(b'', TASK, TOKEN), (None, []))
        self.assertEqual(self.look(submitted('a', task='TASK-999')), (None, []))
        self.assertEqual(self.look(line({'x': 1})), (None, []))

    def test_one_match_gives_its_commit(self):
        """TASK-087 AC2 (amended by TASK-111): one task.submitted of the task with the token gives its commit."""
        self.assertEqual(self.look(submitted('a')), (SUB1, []))

    def test_two_matches_give_a_finding(self):
        """TASK-087 AC2 (amended by TASK-111): two submissions with the token give no commit and one finding."""
        commit, found = self.look(submitted('a'), submitted('b', commit=SUB2, seq=2))
        self.assertIsNone(commit)
        self.assertEqual(len(found), 1)
        self.assertIn('more than one', found[0])

    def test_a_commit_out_of_form_gives_a_finding(self):
        """TASK-087 AC2 (amended by TASK-111): a matching event whose commit is not 40 lowercase hexadecimal
        characters gives no commit and a finding."""
        for bad in ('ABC', 'A' * 40, SUB1[:39], 7, None):
            with self.subTest(bad=bad):
                commit, found = self.look(submitted('a', commit=bad))
                self.assertIsNone(commit)
                self.assertEqual(len(found), 1)
                self.assertIn('out of form', found[0])

    def test_other_token_other_task_and_compensating_are_ignored(self):
        """TASK-087 AC2 (amended by TASK-111): an event with another token, of another task or compensating is never
        matched; the token's key order does not matter."""
        got = self.look(submitted('a', token=OTHER_TOKEN, commit=SUB2), submitted('b', task='TASK-999', commit=SUB2),
                        submitted('c', compensating=True, commit=SUB2), submitted('d', token={'counter': 2, 'epoch': 'e1'}),
                        line({'t': 'x'}, kind='record.added'))
        self.assertEqual(got, (SUB1, []))

    def test_a_repeat_under_one_event_id(self):
        """TASK-087 AC2 (amended by TASK-111): an identical repeat (only seq and appended_at differ) counts once;
        the same event id with other content gives a finding."""
        self.assertEqual(self.look(submitted('a'), submitted('a', seq=2, appended_at='2026-11-02T00:00:00Z')),
                         (SUB1, []))
        commit, found = self.look(submitted('a'), submitted('a', commit=SUB2, seq=2))
        self.assertIsNone(commit)
        self.assertIn('repeated with other content', found[0])

    def test_a_repeat_that_does_not_match_gives_no_finding(self):
        """TASK-087 AC2 (amended by TASK-111): the repeat check is among the matching events only: an event id that
        is repeated once with the token and once with another token gives the matching one and no finding (a stated
        difference from records.check_log, which refuses that log)."""
        self.assertEqual(self.look(submitted('a'), submitted('a', token=OTHER_TOKEN, seq=2)), (SUB1, []))

    def test_a_matching_line_with_a_repeated_key_is_not_matched(self):
        """TASK-087 AC2 (amended by TASK-111): a task.submitted line of the task with the token that repeats a key
        (a second "task_id" with the same value) gives (None, one finding), although the same line without the repeat
        would match."""
        plain = submitted('a')
        self.assertEqual(self.look(plain), (SUB1, []))
        repeated = plain.replace(b'"task_id": "%s"' % TASK.encode('ascii'),
                                 b'"task_id": "%s", "task_id": "%s"' % (TASK.encode('ascii'), TASK.encode('ascii')))
        self.assertNotEqual(repeated, plain)
        commit, found = self.look(repeated)
        self.assertIsNone(commit)
        self.assertEqual(len(found), 1)

    def test_an_unreadable_line_fails_closed(self):
        """TASK-087 AC2 (amended by TASK-111): a line that is not JSON, not an object, not UTF-8, with a repeated key
        or with NaN gives (None, a finding) even when a matching event is in the log, and also when it is the only
        line of the log."""
        for bad in (b'not json', b'[1]', b'\xff\xfe', b'{"a": 1, "a": 2}', b'{"x": NaN}', b'{"x": Infinity}'):
            with self.subTest(bad=bad):
                commit, found = self.look(submitted('a'), bad)
                self.assertIsNone(commit)
                self.assertEqual(len(found), 1)
                commit, found = self.look(bad)
                self.assertIsNone(commit)
                self.assertEqual(len(found), 1)

    def test_a_matching_event_with_an_event_id_that_is_not_a_str(self):
        """TASK-087 AC2 (amended by TASK-111): a matching event whose event id is not a str gives (None, one
        finding)."""
        for bad in (7, None, ['a']):
            with self.subTest(bad=bad):
                commit, found = self.look(submitted(bad))
                self.assertIsNone(commit)
                self.assertEqual(len(found), 1)

    def test_a_failure_of_the_identity_text_is_a_finding(self):
        """TASK-087 AC2 (amended by TASK-111): an exception raised by the writer of the identity text of a matching
        event (the third call of json.dumps, replaced by a stand-in that raises) gives (None, one finding) and
        nothing is raised."""
        real_dumps = handoff_file.json.dumps
        calls = []

        def dumps(value, **kw):
            calls.append(value)
            if len(calls) == 3:
                raise RecursionError()
            return real_dumps(value, **kw)

        plain = submitted('a')
        with mock.patch.object(handoff_file.json, 'dumps', dumps):
            commit, found = self.look(plain)
        self.assertEqual(len(calls), 3)
        self.assertIsNone(commit)
        self.assertEqual(len(found), 1)

    def test_a_token_line_that_check_log_flags_is_not_matched(self):
        """TASK-087 AC2 (amended by TASK-111): a task.submitted of the task with the token whose payload is not an
        object, or whose compensating is missing, 0 or "false", is not matched and gives (None, []) with no finding;
        records.check_log flags such a line, so this is a stated difference from it."""
        for over in ({'payload': []}, {'payload': 'x'}, {'payload': {'commit': SUB1}},
                     {'payload': {'commit': SUB1, 'compensating': 0}},
                     {'payload': {'commit': SUB1, 'compensating': 'false'}}):
            with self.subTest(over=over):
                self.assertEqual(self.look(submitted('a', **over)), (None, []))

    def test_a_log_that_is_not_bytes_is_a_finding(self):
        """TASK-087 AC2 (amended by TASK-111): a log that is a str, None or an int gives (None, one finding) and
        nothing is raised."""
        for bad in ('text', None, 7):
            with self.subTest(bad=bad):
                commit, found = handoff_file.submitted_commit(bad, TASK, TOKEN)
                self.assertIsNone(commit)
                self.assertEqual(len(found), 1)

    def test_blank_lines_a_cr_byte_and_a_bom(self):
        """TASK-087 AC2 (amended by TASK-111): blank lines are skipped and a CR byte is white space to the JSON
        reader; a byte-order mark at the start of a line is refused (a finding). These differ from records.check_log
        on the first two, and are stated limits."""
        self.assertEqual(handoff_file.submitted_commit(b'\n\n' + submitted('a') + b'\r\n\n', TASK, TOKEN), (SUB1, []))
        commit, found = handoff_file.submitted_commit(b'\xef\xbb\xbf' + submitted('a') + b'\n', TASK, TOKEN)
        self.assertIsNone(commit)
        self.assertEqual(len(found), 1)

    def test_a_token_that_cannot_be_written(self):
        """TASK-087 AC2 (amended by TASK-111): a token that is not canonical JSON gives (None, a finding)."""
        commit, found = self.look(submitted('a'), token={'x': float('nan')})
        self.assertIsNone(commit)
        self.assertEqual(len(found), 1)
        self.assertIn('canonical JSON', found[0])

    def test_the_token_text_is_eventlogs(self):
        """TASK-087 AC2 (amended by TASK-111): the lookup's token text equals eventlog._token_text on every test token."""
        for token in (TOKEN, OTHER_TOKEN, {'counter': 2, 'epoch': 'e1'}, {'epoch': 'é', 'counter': 1}, {}, 7, None):
            with self.subTest(token=token):
                self.assertEqual(handoff_file._canonical(token), eventlog._token_text(token))

    def test_the_lookup_agrees_with_check_log(self):
        """TASK-087 AC2 (amended by TASK-111): on well-formed logs the lookup's commit equals the one found through
        records.check_log's lines with duplicate_of None (none, one, two matches, an identical repeat, a compensating
        event)."""
        logs = [lines_of(submitted('a', seq=1), submitted('b', token=OTHER_TOKEN, commit=SUB2, seq=2),
                         submitted('c', task='TASK-999', commit=SUB2, seq=3)),
                lines_of(submitted('a', seq=1)),
                lines_of(submitted('a', seq=1), submitted('b', commit=SUB2, seq=2)),
                lines_of(submitted('a', seq=1), submitted('a', seq=2)),
                lines_of(submitted('a', seq=1, compensating=True), submitted('b', commit=SUB2, seq=2))]
        for n, log in enumerate(logs):
            with self.subTest(log=n):
                report = records.check_log(log)
                self.assertEqual(report.findings(), [])
                found = [l.event['payload']['commit'] for l in report.lines if l.duplicate_of is None
                         and l.event.get('task_id') == TASK and l.event['fencing_token'] == TOKEN
                         and l.event['payload']['compensating'] is False]
                got = handoff_file.submitted_commit(log, TASK, TOKEN)
                self.assertEqual(got[0], found[0] if len(found) == 1 else None)
                self.assertEqual(len(got[1]), 0 if len(found) <= 1 else 1)

    def test_deep_nesting_is_a_finding_not_a_raise(self):
        """TASK-087 AC2 (amended by TASK-111): a RecursionError (or any other exception) raised by the JSON reader on a
        line, or by the writer of the canonical text for an event's token, gives (None, a finding) and nothing is
        raised (the readers are replaced by stand-ins that raise, since the depth at which a reader raises depends on
        the Python in use)."""
        for error in (RecursionError(), OverflowError(), MemoryError()):
            with self.subTest(error=type(error).__name__):
                with mock.patch.object(handoff_file.json, 'loads', side_effect=error):
                    commit, found = self.look(submitted('a'))
                self.assertIsNone(commit)
                self.assertEqual(len(found), 1)
        real_dumps = handoff_file.json.dumps
        calls = []

        def dumps(value, **kw):
            calls.append(value)
            if len(calls) == 2:
                raise RecursionError()
            return real_dumps(value, **kw)

        plain = submitted('a')
        with mock.patch.object(handoff_file.json, 'dumps', dumps):
            commit, found = self.look(plain)
        self.assertEqual(len(calls), 2)
        self.assertIsNone(commit)
        self.assertEqual(len(found), 1)


class TASK111Write(unittest.TestCase):

    def run_with(self, rec, **kw):
        args = dict(root=ROOT, task_id=TASK, session_id=SESSION, commit=None, fencing_token=TOKEN)
        args.update(kw)
        return handoff_file.write(args['root'], args['task_id'], args['session_id'], args['commit'],
                                  read_log=rec.read_log, write_handoff=rec.write_handoff,
                                  fencing_token=args['fencing_token'])

    def test_a_token_finds_the_commit_and_the_file_holds_it(self):
        """TASK-087 AC2 (amended by TASK-111): with a fencing_token and commit None, write reads the log once, takes
        the submitted commit from it and writes the file once with that commit."""
        rec = Recorder(log=lines_of(submitted('a')) + full_log())
        r = self.run_with(rec)
        self.assertEqual((r['result'], r['findings']), ('written', []))
        self.assertEqual(rec.calls, [('read_log', ROOT),
                                     ('write_handoff', ROOT, TASK, SESSION, FULL_TEXT.replace(COMMIT, SUB1))])

    def test_no_submission_gives_commit_null(self):
        """TASK-087 AC2 (amended by TASK-111): with a fencing_token and no matching submission the file holds
        "commit: null" and the result has no finding."""
        rec = Recorder(log=lines_of(submitted('a', token=OTHER_TOKEN)) + full_log())
        r = self.run_with(rec)
        self.assertEqual((r['result'], r['findings']), ('written', []))
        self.assertIn('commit: null\n', rec.calls[1][4])

    def test_arguments_with_a_token(self):
        """TASK-087 AC2 (amended by TASK-111): a fencing_token that is not a mapping, or a commit given together with
        a token, is an argument refusal and no callee is called."""
        for kw in (dict(fencing_token='x'), dict(fencing_token=[1]), dict(fencing_token=7), dict(commit=COMMIT)):
            with self.subTest(kw=kw):
                rec = Recorder()
                r = self.run_with(rec, **kw)
                self.assertEqual((r['result'], r['reason']), ('refused', 'argument'))
                self.assertEqual(rec.calls, [])

    def test_without_a_token_the_commit_is_the_callers(self):
        """TASK-087 AC2 (amended by TASK-111): with no fencing_token the commit given is written as it was, and a
        submission in the log is not looked at."""
        rec = Recorder(log=lines_of(submitted('a', commit=SUB2)) + full_log())
        r = self.run_with(rec, fencing_token=None, commit=COMMIT)
        self.assertEqual(r['result'], 'written')
        self.assertEqual(rec.calls[1][4], FULL_TEXT)

    def test_the_lookups_findings_ride_in_every_result(self):
        """TASK-087 AC2 (amended by TASK-111): two matching submissions give a finding that rides in "written" (with
        commit null), in "none", in a claims refusal and in a write refusal."""
        two = lines_of(submitted('a'), submitted('b', commit=SUB2, seq=2))
        r = self.run_with(Recorder(log=two + full_log()))
        self.assertEqual(r['result'], 'written')
        self.assertEqual(len(r['findings']), 1)
        r = self.run_with(Recorder(log=two))
        self.assertEqual((r['result'], len(r['findings'])), ('none', 1))
        r = self.run_with(Recorder(log=two + log_of(record('done', 2, 'gap'))))
        self.assertEqual((r['result'], r['reason']), ('refused', 'claims'))
        self.assertEqual(r['findings'][-1].split(':')[0], 'lookup')
        refused = writer.StoreResult('refused', 'exists', ['exists: the handoff file is not empty'])
        r = self.run_with(Recorder(log=two + full_log(), answer=refused))
        self.assertEqual((r['result'], r['reason']), ('refused', 'write'))
        self.assertEqual(r['findings'][-1].split(':')[0], 'lookup')
        r = self.run_with(Recorder(log=two + full_log(), write_raises=True))
        self.assertEqual((r['result'], r['reason']), ('refused', 'write'))
        self.assertEqual(r['findings'][-1].split(':')[0], 'lookup')
        stringy = writer.StoreResult('refused', 'exists', [])
        stringy.findings = 'a string'
        r = self.run_with(Recorder(log=two + full_log(), answer=stringy))
        self.assertEqual(r['findings'], ['write: not done', r['findings'][-1]])
        self.assertEqual(r['findings'][-1].split(':')[0], 'lookup')


if __name__ == '__main__':
    unittest.main()

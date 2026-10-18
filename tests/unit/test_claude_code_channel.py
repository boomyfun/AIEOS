"""Unit tests of aieos_bootstrap.claude_code_channel (task TASK-063, rules R1 to R7): the context's form, the record's
form, the redaction of shell and path refusals, deliver's order and result, and the script checks of AC6 to AC8, over
values made up for the test. append and release are stand-ins, so no file is written and no process starts. Each test
names its criteria in its own docstring."""

import ast
import copy
import datetime
import pathlib
import types
import unittest

from aieos_bootstrap import adapter
from aieos_bootstrap import claude_code
from aieos_bootstrap import claude_code_channel as ch

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap' / 'claude_code_channel.py'
NOW = datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)
SID = 'made-up-session-7'


def context(**kw):
    c = {'root': 'C:\\proj\\repo', 'task_id': 'TASK-100', 'session_id': SID,
         'fencing_token': {'epoch': 'e1', 'counter': 3}, 'write_set': ['docs/notes/**'],
         'allowlist': ['git status', 'git diff --stat'], 'recorder': 'a test session ' + SID}
    c.update(kw)
    return c


def record(kind='shell_not_allowed', refers_to='git commit -m x', **kw):
    r = {'record_id': 'obs-1', 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
         'outcome': 'blocking', 'blocking_kind': 'violation',
         'recorder': claude_code.RECORDER + ', for a test session ' + SID, 'subject': 'TASK-100',
         'evidence_type': kind, 'refers_to': refers_to}
    r.update(kw)
    return r


def hook_result(verdict='refuse', rec=None, **kw):
    h = {'exit_code': 0 if verdict == 'allow' else 2, 'stderr': '' if verdict == 'allow' else 'x',
         'verdict': verdict, 'concern': 'shell', 'reason': 'allowlist', 'findings': [], 'record': rec}
    h.update(kw)
    return h


class Store:
    """Stand-ins for writer.append_event and writer.release_lease_token that record their calls."""

    def __init__(self, append_state='appended', release_state='done', raise_in=None, findings=()):
        self.calls = []
        self.append_state = append_state
        self.release_state = release_state
        self.raise_in = raise_in
        self.findings = findings

    def append(self, root, event_type, payload, event_id, now, recorder, task_id=None, fencing_token=None):
        self.calls.append(('append', root, event_type, copy.deepcopy(payload), event_id, task_id, fencing_token, now,
                           recorder))
        if self.raise_in == 'append':
            raise RuntimeError('made-up fault')
        return types.SimpleNamespace(result=self.append_state, reason=None, findings=self.findings)

    def release(self, root, task_id, token):
        self.calls.append(('release', root, task_id, token))
        return types.SimpleNamespace(result=self.release_state, reason=None, findings=(), value=None)


def deliver(ctx=None, hr=None, event_id='ev-1', store=None):
    store = store or Store()
    return ch.deliver(context() if ctx is None else ctx, hook_result(rec=record()) if hr is None else hr, event_id,
                      NOW, append=store.append, release=store.release), store


class Context(unittest.TestCase):
    def test_well_formed(self):
        """TASK-063 AC1: a context with exactly the seven keys in form gives no finding."""
        self.assertEqual(ch.context_findings(context()), [])

    def test_keys_missing_or_extra(self):
        """TASK-063 AC1: a missing or an extra key, or a context that is not a mapping, gives findings."""
        for key in ch.CONTEXT_KEYS:
            c = context()
            del c[key]
            self.assertTrue(ch.context_findings(c), key)
        self.assertTrue(ch.context_findings(context(holder='h')))
        for bad in (None, [], 'x', 3):
            self.assertTrue(ch.context_findings(bad))

    def test_each_key_malformed(self):
        """TASK-063 AC1: each key of a wrong type or form gives a finding."""
        bad = {'root': ['relative', '/c/x', '', 3], 'task_id': ['TASK-x', 'task-1', None],
               'session_id': ['', 'a b', None, 5],
               'fencing_token': [{'epoch': '', 'counter': 0}, {'epoch': 'e', 'counter': -1},
                                 {'epoch': 'e', 'counter': True}, {'epoch': 'e'}, None],
               'write_set': [[], ['a//b'], ['a b'], 'docs/**', [3]],
               'allowlist': ['git status', ['bash x'], ['git  status'], [3]],
               'recorder': ['', None, 'a session without the id']}
        for key, values in bad.items():
            for v in values:
                self.assertTrue(ch.context_findings(context(**{key: v})), (key, v))

    def test_empty_allowlist_well_formed(self):
        """TASK-063 AC1: an empty allowlist is well formed by claude_code_hook.allowlist_findings."""
        self.assertEqual(ch.context_findings(context(allowlist=[])), [])


class RecordForm(unittest.TestCase):
    def test_judge_form(self):
        """TASK-063 AC2: each of the three evidence types in judge's form gives no finding."""
        for kind in ch.EVIDENCE_TYPES:
            self.assertEqual(ch.record_findings(record(kind)), [], kind)

    def test_keys_and_values(self):
        """TASK-063 AC2: a key missing or extra, a fixed value wrong, a recorder without judge's prefix, an unknown
        evidence type, an empty text or a non-mapping gives findings."""
        for key in ch.RECORD_KEYS:
            r = record()
            del r[key]
            self.assertTrue(ch.record_findings(r), key)
        self.assertTrue(ch.record_findings(record(extra='x')))
        for key, value in (('fact_kind', 'claim'), ('source_class', 'agent_declared'), ('outcome', 'fail'),
                           ('blocking_kind', 'other'), ('recorder', 'someone else'), ('evidence_type', 'other'),
                           ('record_id', ''), ('subject', ''), ('refers_to', ''), ('refers_to', None)):
            self.assertTrue(ch.record_findings(record(**{key: value})), key)
        for bad in (None, [], 'x'):
            self.assertTrue(ch.record_findings(bad))


class ShellRedaction(unittest.TestCase):
    def test_fixed_texts(self):
        """TASK-063 AC3: a shell refusal's refers_to becomes exactly its type's fixed text; every other key is kept,
        and the given record is not changed."""
        for kind in ('git_push_refused', 'shell_not_allowed'):
            r = record(kind, 'curl -H token-MADEUPSECRET123 example')
            before = copy.deepcopy(r)
            out = ch.redact(r)
            self.assertEqual(r, before)
            self.assertEqual(out['refers_to'], ch.REDACTED[kind])
            self.assertNotIn('MADEUPSECRET', repr(out))
            self.assertEqual({k: v for k, v in out.items() if k != 'refers_to'},
                             {k: v for k, v in r.items() if k != 'refers_to'})

    def test_malformed_gives_none(self):
        """TASK-063 AC3: a record with a finding under AC2 gives None."""
        self.assertIsNone(ch.redact(record(outcome='fail')))
        self.assertIsNone(ch.redact(None))
        self.assertIsNone(ch.redact(record('write_outside_write_set', '')))


class PathRedaction(unittest.TestCase):
    def test_root_relative_kept(self):
        """TASK-063 AC4: a path in judge's root-relative form is kept unchanged."""
        for p in ('docs/a.md', 'src/x/y.py', 'a'):
            self.assertEqual(ch.redact(record('write_outside_write_set', p))['refers_to'], p)

    def test_other_forms_replaced(self):
        """TASK-063 AC4: a drive letter, a backslash, a leading slash, an empty, "." or ".." segment is replaced by the
        fixed text."""
        for p in ('C:/Users/x/secret.txt', 'C:\\x', 'a\\b', '/etc/x', 'a//b', 'a/./b', 'a/../b', 'a/', '.', '..'):
            self.assertEqual(ch.redact(record('write_outside_write_set', p))['refers_to'],
                             ch.REDACTED['write_outside_write_set'], p)


class Deliver(unittest.TestCase):
    def test_written_once_with_the_exact_arguments(self):
        """TASK-063 AC5: a well-formed matching refusal is redacted and passed once to adapter.violation with the
        context's root, task id, token and recorder; result written."""
        r, store = deliver()
        self.assertEqual((r['result'], r['reason']), ('written', None))
        self.assertEqual(r['record']['refers_to'], ch.REDACTED['shell_not_allowed'])
        appends = [c for c in store.calls if c[0] == 'append']
        self.assertEqual(appends[0][1:3], ('C:\\proj\\repo', 'violation.detected'))
        self.assertEqual(appends[0][3], r['record'])
        self.assertEqual(appends[0][4:], ('ev-1', 'TASK-100', {'epoch': 'e1', 'counter': 3}, NOW,
                                          'a test session ' + SID))
        self.assertEqual(len(appends), 2)
        self.assertEqual([c[2] for c in appends].count('violation.detected'), 1)
        releases = [c for c in store.calls if c[0] == 'release']
        self.assertEqual(releases, [('release', 'C:\\proj\\repo', 'TASK-100', {'epoch': 'e1', 'counter': 3})])
        self.assertEqual(r['core']['result'], 'done')
        self.assertEqual(set(r), set(ch.RESULT_KEYS))

    def test_literal_fixed_texts(self):
        """TASK-063 AC3, AC4: the fixed texts are the contract's own words, typed here."""
        want = {'git_push_refused': 'a git push command; its text is not kept (D-1262 M2)',
                'shell_not_allowed': 'a shell command; its text is not kept (D-1262 M2)',
                'write_outside_write_set': 'a path outside the root; it is not kept (D-1262 M3)'}
        for kind, text in want.items():
            self.assertEqual(ch.redact(record(kind, 'C:/x y'))['refers_to'], text, kind)

    def test_order_of_checks(self):
        """TASK-063 AC5: context before hook_result before event_id; nothing is called for any refusal."""
        cases = [(dict(ctx=context(root='x'), hr='bad', event_id=''), 'context'),
                 (dict(hr='bad', event_id=''), 'hook_result'),
                 (dict(event_id='a b'), 'event_id'), (dict(event_id=''), 'event_id'), (dict(event_id=None), 'event_id')]
        for kw, reason in cases:
            r, store = deliver(**kw)
            self.assertEqual((r['result'], r['reason']), ('refused', reason), kw)
            self.assertEqual(store.calls, [])

    def test_hook_result_form(self):
        """TASK-063 AC5: a hook_result of another form, a wrong exit code for its verdict, or a record beside a verdict
        other than refuse gives hook_result."""
        bad = [hook_result(rec=record(), extra=1), {}, hook_result(verdict='maybe'),
               hook_result(rec=record(), exit_code=0), hook_result(verdict='allow', exit_code=2),
               hook_result(verdict='allow', rec=record()), hook_result(verdict='uncovered', rec=record()),
               hook_result(rec=record(), exit_code=True), hook_result('allow', exit_code=False)]
        for h in bad:
            r, store = deliver(hr=h)
            self.assertEqual(r['reason'], 'hook_result', h)
            self.assertEqual(store.calls, [])

    def test_nothing_written(self):
        """TASK-063 AC5: allow, uncovered and a refusal without a record write nothing."""
        for h, reason in ((hook_result('allow'), 'allow'), (hook_result('uncovered'), 'uncovered'),
                          (hook_result('refuse', None), 'no_record')):
            r, store = deliver(hr=h)
            self.assertEqual((r['result'], r['reason'], r['record'], r['core']), ('nothing', reason, None, None))
            self.assertEqual(store.calls, [])

    def test_record_not_matching(self):
        """TASK-063 AC5: a record of another form, of another task, or of another recorder gives record."""
        for rec in (record(outcome='fail'), record(subject='TASK-101'),
                    record(recorder=claude_code.RECORDER + ', for another session')):
            r, store = deliver(hr=hook_result(rec=rec))
            self.assertEqual((r['result'], r['reason']), ('refused', 'record'), rec)
            self.assertEqual(store.calls, [])

    def test_core_refusals_mapped(self):
        """TASK-063 AC5: adapter.violation's refusal gives core, with the record passed and the core's result."""
        r, store = deliver(store=Store(append_state='weird'))
        self.assertEqual((r['result'], r['reason']), ('refused', 'core'))
        self.assertIsNotNone(r['record'])
        self.assertEqual(r['core']['result'], 'refused')

    def test_duplicate_is_written(self):
        """TASK-063 AC5, AC6: a repeated event_id (append gives duplicate) is adapter.violation's done."""
        r, _ = deliver(store=Store(append_state='duplicate'))
        self.assertEqual(r['result'], 'written')

    def test_fault_gives_deliver(self):
        """TASK-063 AC5: an exception inside deliver gives deliver, its type only; none escapes."""
        real = adapter.violation

        def broken(*a, **k):
            raise KeyError('made-up')
        adapter.violation = broken
        try:
            r, _ = deliver()
        finally:
            adapter.violation = real
        self.assertEqual((r['result'], r['reason'], r['findings']), ('refused', 'deliver', ['KeyError raised inside deliver']))
        # adapter.violation was called with the redacted record, so the result keeps it (AC5)
        self.assertEqual(r['record'], ch.redact(record()))

    def test_fault_before_the_call_keeps_no_record(self):
        """TASK-063 AC5: an exception before adapter.violation is called gives record None."""
        real = ch.redact

        def broken(rec):
            raise KeyError('made-up')
        ch.redact = broken
        try:
            r, store = deliver()
        finally:
            ch.redact = real
        self.assertEqual((r['result'], r['reason'], r['record']), ('refused', 'deliver', None))
        self.assertEqual(store.calls, [])

    def test_no_text_through_a_refusing_core(self):
        """TASK-063 AC5: with a core that refuses, no text of hook_result's findings or of the original refers_to is in
        the result."""
        marker = 'MARKER-TEXT-43'
        h = hook_result(rec=record(refers_to='x ' + marker), findings=[marker])
        r, _ = deliver(hr=h, store=Store(append_state='weird', findings=('a made-up core finding',)))
        self.assertEqual((r['result'], r['reason']), ('refused', 'core'))
        self.assertIn('a made-up core finding', ' '.join(r['findings']))
        self.assertNotIn(marker, repr(r))

    def test_hook_result_unchanged_and_no_text_copied(self):
        """TASK-063 AC5: hook_result is never changed, and no text of its findings or of the original refers_to is
        copied into the result."""
        marker = 'MARKER-TEXT-42'
        for h in (hook_result(rec=record(refers_to='x ' + marker), findings=[marker]),
                  hook_result(rec=record(refers_to='x ' + marker, outcome='fail'), findings=[marker]),
                  hook_result('uncovered', findings=[marker])):
            before = copy.deepcopy(h)
            r, _ = deliver(hr=h)
            self.assertEqual(h, before)
            self.assertNotIn(marker, repr(r))


class Statements(unittest.TestCase):
    def test_docstring_words(self):
        """TASK-063 AC6, AC7, AC4: the module's docstring states the ids, the context's sources, the departures and the
        limits."""
        doc = ast.get_docstring(ast.parse(SRC.read_text(encoding='utf-8')))
        for words in ('"duplicate"', 'tool_use_id', 'a counter per session', 'fencing_token', 'session id',
                      'write_set.paths', 'resume_check.py:290', 'writer.py:11', 'never changed',
                      'specification 5 section 8', "specification 5 section 6's table", 'neither refuses nor records',
                      'CC-3', 'No observed read-set record', 'claude_code.py:61-66, :169, :183-186',
                      'can itself hold a secret', 'not pure', 'ties weakly', 'only "a refusal"', 'violation.py:35-38', 'same blocking_kind and subject', 'is then not known',
                      'not redacted', 'claude_code.py:309', 'could drift apart', 'includes its "duplicate"'):
            self.assertIn(words, doc, words)

    def test_imports_and_absent_calls(self):
        """TASK-063 AC8: only re and aieos_bootstrap's adapter, claude_code and claude_code_hook are imported; no
        open, exec, eval, compile, __import__, importlib, print, sys, assert, os or subprocess; no name of the
        project-state directory."""
        text = SRC.read_text(encoding='utf-8')
        tree = ast.parse(text)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.update(node.module + '.' + a.name for a in node.names)
            self.assertNotIsInstance(node, ast.Assert)
        self.assertEqual(imports, {'re', 'aieos_bootstrap.adapter', 'aieos_bootstrap.claude_code',
                                   'aieos_bootstrap.claude_code_hook'})
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        for bad in ('open', 'exec', 'eval', 'compile', '__import__', 'importlib', 'print', 'sys', 'os', 'subprocess',
                    'input'):
            self.assertNotIn(bad, names)
        self.assertNotIn('.ai' + 'eos', text)


if __name__ == '__main__':
    unittest.main()

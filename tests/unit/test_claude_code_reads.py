"""Unit tests of aieos_bootstrap.claude_code_reads (task TASK-065, rules R1 to R4, R6 and R7): the parse, the covered
tool, the uncovered tools, what is read and kept, and the script checks of AC6 and AC7, over byte strings made up for
the test. No process starts and no file is written. Each test names its criteria in its own docstring."""

import ast
import json
import pathlib
import types
import unittest

from aieos_bootstrap import claude_code_hook
from aieos_bootstrap import claude_code_reads as cr

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap' / 'claude_code_reads.py'
MARKER = 'zq-made-up-marker-41'


def raw(obj):
    return json.dumps(obj).encode('utf-8')


def hook(tool, inp, **extra):
    d = {'session_id': 'made-up', 'cwd': 'C:\\elsewhere', 'hook_event_name': 'PostToolUse', 'tool_name': tool,
         'tool_input': inp, 'tool_response': {'type': 'text'}}
    d.update(extra)
    return raw(d)


def entry(data):
    return claude_code_hook.entry(data, 'C:\\proj\\repo', 'TASK-100', ['docs/notes/**'], ['git status'], 'obs-1',
                                  'a test session')


MALFORMED = [
    ('input_bytes', b'\xef\xbb\xbf{"tool_name": "Read", "tool_input": {"file_path": "C:/a"}}'),
    ('input_bytes', b'{"tool_name": "Read", "tool_input": {"file_path": "C:/\xff"}}'),
    ('input_json', b'{"tool_name": "Read", '),
    ('input_json', b'{"tool_name": "Read", "tool_name": "Read", "tool_input": {"file_path": "C:/a"}}'),
    ('input_json', b'{"tool_name": "Read", "tool_input": {"file_path": "C:/a", "limit": NaN}}'),
    ('input_json', b'{"tool_name": "Read", "tool_input": {"file_path": "C:/a"}} {}'),
    ('input_json', b'[' * 100000 + b']' * 100000),
    ('input_shape', b'["Read"]'),
    ('input_shape', b'"Read"'),
    ('input', raw({'tool_name': 7, 'tool_input': {'file_path': 'C:/a'}})),
    ('input', raw({'tool_name': 'Read', 'tool_input': ['C:/a']})),
    ('input', raw({'tool_input': {'file_path': 'C:/a'}})),
]


class Parse(unittest.TestCase):
    def test_each_malformed_kind(self):
        """TASK-065 AC1: each malformed kind gives "uncovered" with its reason and an empty list."""
        for reason, data in MALFORMED:
            r = cr.read_paths(data)
            self.assertEqual((r['result'], r['reason'], r['read_paths']), ('uncovered', reason, []), data[:40])
            self.assertEqual(len(r['findings']), 1)

    def test_not_bytes(self):
        """TASK-065 AC1: an argument that is not a bytes object gives reason "argument"."""
        for data in ('{}', None, bytearray(b'{}'), 7, ['x']):
            r = cr.read_paths(data)
            self.assertEqual((r['result'], r['reason'], r['read_paths']), ('uncovered', 'argument', []))

    def test_same_inputs_through_the_hook_entry(self):
        """TASK-065 AC1: claude_code_hook.entry gives a non-allow verdict for every malformed input of the list."""
        for reason, data in MALFORMED + [('argument', '{}')]:
            r = entry(data)
            self.assertNotEqual(r['verdict'], 'allow', data[:40])
            self.assertEqual(r['exit_code'], 2)

    def test_a_well_formed_read_passes(self):
        """TASK-065 AC1: a well-formed Read input is not refused by the parse."""
        self.assertEqual(cr.read_paths(hook('Read', {'file_path': 'C:/a.py'}))['result'], 'read')


class Covered(unittest.TestCase):
    def test_paths_returned_unchanged(self):
        """TASK-065 AC2: the path is returned as given, not normalised, resolved, case-folded or stripped."""
        for p in ('C:\\Proj\\Repo\\A.py', 'docs/notes/x.md', 'C:/proj/repo/a.py', 'C:\\proj/Mixed\\Case.PY',
                  'C:\\proj\\tài liệu.md', ' C:\\a.py ', '..\\up.py', '\\\\server\\share\\f.txt'):
            r = cr.read_paths(hook('Read', {'file_path': p}))
            self.assertEqual(r, {'result': 'read', 'reason': 'read', 'findings': [], 'read_paths': [p]})

    def test_partial_read_counts(self):
        """TASK-065 AC2: offset and limit, of any value, do not change the result."""
        for extra in ({'offset': 10}, {'limit': 50}, {'offset': 1, 'limit': 2}, {'offset': 'x', 'limit': None}):
            inp = {'file_path': 'C:/a.py'}
            inp.update(extra)
            self.assertEqual(cr.read_paths(hook('Read', inp))['read_paths'], ['C:/a.py'])

    def test_file_path_out_of_form(self):
        """TASK-065 AC2: file_path missing, not a string or empty gives "uncovered", reason "input"."""
        for inp in ({}, {'file_path': 3}, {'file_path': ''}, {'file_path': None}, {'file_path': ['C:/a']}):
            r = cr.read_paths(hook('Read', inp))
            self.assertEqual((r['result'], r['reason'], r['read_paths']), ('uncovered', 'input', []))

    def test_name_is_case_sensitive(self):
        """TASK-065 AC2: only the exact name "Read" is covered."""
        for name in ('read', 'READ', 'Read ', 'ReadFile'):
            self.assertEqual(cr.read_paths(hook(name, {'file_path': 'C:/a'}))['reason'], 'tool')


class Uncovered(unittest.TestCase):
    CASES = [
        ('Grep', {'pattern': 'x', 'path': 'C:/a'}, 'a search tool whose reads are not attributable'),
        ('Glob', {'pattern': '**/*.py'}, 'a search tool whose reads are not attributable'),
        ('Bash', {'command': 'cat a.py'}, 'a shell tool'),
        ('PowerShell', {'command': 'Get-Content a.py'}, 'a shell tool'),
        ('mcp__files__read', {'file_path': 'C:/a'}, 'an MCP tool'),
        ('Task', {'prompt': 'x'}, 'a subagent tool'),
        ('Agent', {'prompt': 'x'}, 'a subagent tool'),
        ('Write', {'file_path': 'C:/a', 'content': 'x'}, 'a tool not covered'),
        ('Edit', {'file_path': 'C:/a'}, 'a tool not covered'),
        ('MultiEdit', {'file_path': 'C:/a'}, 'a tool not covered'),
        ('NotebookEdit', {'notebook_path': 'C:/a'}, 'a tool not covered'),
        ('SomethingNew', {'file_path': 'C:/a'}, 'a tool not covered'),
    ]

    def test_each_class(self):
        """TASK-065 AC3: every other tool gives "uncovered", reason "tool", its class's fixed finding, no path."""
        for tool, inp, finding in self.CASES:
            r = cr.read_paths(hook(tool, inp))
            self.assertEqual(r, {'result': 'uncovered', 'reason': 'tool', 'findings': [finding], 'read_paths': []}, tool)

    def test_no_input_text_in_findings(self):
        """TASK-065 AC3: no text of the input is copied into findings."""
        for tool in ('Grep', 'Bash', 'mcp__' + MARKER, 'Task', MARKER):
            r = cr.read_paths(hook(tool, {'command': MARKER, 'pattern': MARKER, 'file_path': MARKER}))
            self.assertNotIn(MARKER, json.dumps(r['findings']))
        r = cr.read_paths(hook('Read', {'file_path': 7, 'x': MARKER}))
        self.assertNotIn(MARKER, json.dumps(r['findings']))


class ReadAndKept(unittest.TestCase):
    def test_other_keys_change_nothing(self):
        """TASK-065 AC4: hook_event_name, session_id, cwd, transcript_path, tool_response and other keys change no result."""
        base = cr.read_paths(hook('Read', {'file_path': 'C:/a.py'}))
        for extra in ({'hook_event_name': 'PreToolUse'}, {'hook_event_name': 'PostToolUseFailure'},
                      {'session_id': 'other'}, {'cwd': 'D:\\x'}, {'transcript_path': 'C:/t.jsonl'},
                      {'tool_response': {'error': 'missing'}}, {'tool_use_id': 'toolu_1'}, {'duration_ms': 3},
                      {'permission_mode': 'default'}, {'more': [1, 2]}):
            self.assertEqual(cr.read_paths(hook('Read', {'file_path': 'C:/a.py'}, **extra)), base, extra)

    def test_deterministic_and_unchanged(self):
        """TASK-065 AC4: equal inputs give equal results, and the given bytes keep their value."""
        data = hook('Read', {'file_path': 'C:/a.py'})
        before = bytes(data)
        self.assertEqual(cr.read_paths(data), cr.read_paths(data))
        self.assertEqual(data, before)

    def test_result_keys(self):
        """TASK-065 AC4: every result has exactly the four keys."""
        for data in [hook('Read', {'file_path': 'C:/a'}), hook('Grep', {}), b'{', 'x']:
            self.assertEqual(sorted(cr.read_paths(data)), sorted(cr.RESULT_KEYS))

    def test_a_fault_gives_entry(self):
        """TASK-065 AC4: an exception inside gives "uncovered", reason "entry", its type's name only, no path."""
        real = cr.json

        def boom(*a, **k):
            raise RuntimeError(MARKER)
        cr.json = types.SimpleNamespace(loads=boom)
        try:
            r = cr.read_paths(hook('Read', {'file_path': 'C:/a.py'}))
        finally:
            cr.json = real
        self.assertEqual(r, {'result': 'uncovered', 'reason': 'entry', 'findings': ['RuntimeError raised inside read_paths'],
                             'read_paths': []})


class Stated(unittest.TestCase):
    WORDS = ['TASK-065', 'PostToolUse', 'tool_name and tool_input', 'RecursionError', 'Read is covered', 'Grep and Glob',
             'not attributable', 'Bash and PowerShell', 'mcp__', 'Task and Agent', 'over-inclusive', 'tool_response is not read',
             'PostToolUseFailure', 'not normalised', 'section 10 point 13', 'claude_code.normalise_path',
             'unmeasured', 'inferred from the documentation', 'supported live only for Bash', 'D-1202 and D-1203',
             'lower bound at best', 'kept and not used', 'CC-3', 'section 11 points 7 and 10', 'a summary, not the page']

    def test_docstring_words(self):
        """TASK-065 AC6: the module's docstring states each required point (matched with whitespace collapsed)."""
        doc = ' '.join(ast.get_docstring(ast.parse(SRC.read_text(encoding='utf-8'))).split())
        for w in self.WORDS:
            self.assertIn(w, doc)


class Purity(unittest.TestCase):
    def test_imports_and_names(self):
        """TASK-065 AC7: only json is imported; no open, exec, eval, compile, __import__, input, print, exit, assert."""
        tree = ast.parse(SRC.read_text(encoding='utf-8'))
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods.update(a.name for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                mods.add(n.module)
            self.assertNotIsInstance(n, ast.Assert)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                self.assertNotIn(n.func.id, ('open', 'exec', 'eval', 'compile', '__import__', 'input', 'print', 'exit'))
            if isinstance(n, ast.Attribute):
                self.assertNotIn(n.attr, ('exit', 'environ', 'getenv', 'stdin', 'system', 'popen', 'run', 'now'))
        self.assertEqual(mods, {'json'})
        self.assertNotIn('.aieos', SRC.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()

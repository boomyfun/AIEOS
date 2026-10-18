"""Integration tests of aieos_bootstrap.claude_code_reads with the core side of the observed read-set record (task
TASK-065, rule R5): the paths it returns fed to read_set_record.build and records.check_record, and to
read_set_record.observe with an append stand-in kept in memory, as TASK-064's tests do. No file is written and no
process starts. Each test names its criteria in its own docstring."""

import datetime
import json
import types
import unittest

from aieos_bootstrap import claude_code_reads as cr
from aieos_bootstrap import read_set_record as rs
from aieos_bootstrap import records

NOW = datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)
SID = 'made-up-session-9'


def hook(tool, inp):
    return json.dumps({'session_id': SID, 'hook_event_name': 'PostToolUse', 'tool_name': tool, 'tool_input': inp,
                       'tool_response': {'type': 'text'}}).encode('utf-8')


def context():
    return {'root': 'C:\\proj\\repo', 'task_id': 'TASK-100', 'session_id': SID,
            'fencing_token': {'epoch': 'e1', 'counter': 3}, 'write_set': ['docs/notes/**'],
            'allowlist': ['git status'], 'recorder': 'a test session ' + SID}


class Store:
    """A stand-in for writer.append_event, in memory, that records its calls."""

    def __init__(self):
        self.calls = []

    def append(self, root, event_type, payload, event_id, now, recorder, task_id=None, fencing_token=None):
        self.calls.append((event_type, payload, event_id, task_id, fencing_token))
        return types.SimpleNamespace(result='appended', reason=None, seq=1, findings=())


class FitWithTheCore(unittest.TestCase):
    def test_build_and_check_record(self):
        """TASK-065 AC5: a "read" result's list gives a record that records.check_record finds no fault with."""
        r = cr.read_paths(hook('Read', {'file_path': 'C:\\proj\\repo\\src\\a.py'}))
        rec = rs.build('TASK-100', SID, r['read_paths'], 'a test session ' + SID)
        self.assertIsNotNone(rec)
        self.assertEqual(records.check_record(rec), [])
        self.assertEqual(rec['read_paths'], ['C:\\proj\\repo\\src\\a.py'])

    def test_observe_calls_append_once(self):
        """TASK-065 AC5: observe given a result's list calls the stand-in append once, with that list."""
        store = Store()
        r = cr.read_paths(hook('Read', {'file_path': 'docs/notes/x.md', 'offset': 3}))
        out = rs.observe(context(), r['read_paths'], NOW, append=store.append)
        self.assertEqual(out['result'], 'written')
        self.assertEqual(len(store.calls), 1)
        self.assertEqual(store.calls[0][1]['read_paths'], ['docs/notes/x.md'])

    def test_several_results_joined(self):
        """TASK-065 AC5: results joined in call order give a record holding each distinct path once, first order kept;
        uncovered results add nothing."""
        calls = [hook('Read', {'file_path': 'C:/b.py'}), hook('Grep', {'pattern': 'x'}), hook('Read', {'file_path': 'C:/a.py'}),
                 hook('Read', {'file_path': 'C:/b.py', 'limit': 5}), hook('Bash', {'command': 'cat c.py'}),
                 hook('Read', {'file_path': 'c:/a.py'})]
        joined = []
        for c in calls:
            joined += cr.read_paths(c)['read_paths']
        self.assertEqual(joined, ['C:/b.py', 'C:/a.py', 'C:/b.py', 'c:/a.py'])
        store = Store()
        out = rs.observe(context(), joined, NOW, append=store.append)
        self.assertEqual(out['result'], 'written')
        self.assertEqual(len(store.calls), 1)
        self.assertEqual(store.calls[0][1]['read_paths'], ['C:/b.py', 'C:/a.py', 'c:/a.py'])

    def test_uncovered_gives_an_empty_list(self):
        """TASK-065 AC5: an uncovered result's list is empty, and an empty list is of form for the record."""
        r = cr.read_paths(hook('Glob', {'pattern': '**'}))
        self.assertEqual(r['read_paths'], [])
        rec = rs.build('TASK-100', SID, r['read_paths'], 'a test session ' + SID)
        self.assertEqual(records.check_record(rec), [])


if __name__ == '__main__':
    unittest.main()

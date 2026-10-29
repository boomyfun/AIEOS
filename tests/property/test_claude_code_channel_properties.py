"""Property tests of aieos_bootstrap.claude_code_channel (task TASK-063, AC10's property test), standard library only,
with fixed seeds: deliver is deterministic over equal inputs, calls adapter.violation at most once and only for entry's
refusal with a record, passes a shell refusal's refers_to as exactly its fixed text with none of three marker words of
the command anywhere in the result, and never changes hook_result. append and release are stand-ins, so no file is
written. Each test names its criteria in its own docstring."""

import copy
import datetime
import json
import random
import types
import unittest

from aieos_bootstrap import claude_code_channel as ch
from aieos_bootstrap import claude_code_hook

NOW = datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)
SID = 'made-up-session-5'
CTX = {'root': 'C:\\proj\\repo', 'task_id': 'TASK-100', 'session_id': SID,
       'fencing_token': {'epoch': 'e1', 'counter': 1}, 'write_set': ['docs/**'],
       'allowlist': ['git status', 'git log'], 'recorder': 'a test session ' + SID}
WORDS = ['git', 'status', 'push', 'log', 'curl', 'rm', 'Zq7xW', 'secretQ9', '-m', 'origin', '"x"', ';', '|', '&&',
         '$(id)', 'echo', 'C:/a', 'docs/b.md']
PATHS = ['C:\\proj\\repo\\docs\\a.md', 'C:\\proj\\repo\\src\\b.py', 'C:\\Users\\q\\Zq7xW.txt', 'docs/a.md',
         'C:\\proj\\repo\\..\\x', 'D:/elsewhere/secretQ9']
TOOLS = ['Bash', 'PowerShell', 'Write', 'Edit', 'Read', 'Grep', 'mcp__x__y']


class Store:
    def __init__(self):
        self.violations = 0

    def append(self, root, event_type, payload, event_id, now, recorder, task_id=None, fencing_token=None):
        if event_type == 'violation.detected':
            self.violations += 1
        return types.SimpleNamespace(result='appended', reason=None, findings=())

    def release(self, root, task_id, token):
        return types.SimpleNamespace(result='done', reason=None, findings=(), value=None)


def sample(rng):
    tool = rng.choice(TOOLS)
    if tool in ('Bash', 'PowerShell'):
        inp = {'command': ' '.join(rng.choice(WORDS) for _ in range(rng.randint(1, 6)))}
    elif tool in ('Write', 'Edit'):
        inp = {'file_path': rng.choice(PATHS), 'content': 'x'}
    else:
        inp = {'file_path': rng.choice(PATHS)}
    return json.dumps({'tool_name': tool, 'tool_input': inp}).encode('utf-8')


def run(data):
    h = claude_code_hook.entry(data, CTX['root'], CTX['task_id'], CTX['write_set'], CTX['allowlist'], 'obs-1',
                               CTX['recorder'])
    before = copy.deepcopy(h)
    store = Store()
    r = ch.deliver(CTX, h, 'ev-1', NOW, append=store.append, release=store.release)
    return h, before, r, store


class Properties(unittest.TestCase):
    def test_deterministic(self):
        """TASK-063 AC10, AC5: equal inputs give equal results."""
        rng = random.Random(6301)
        for _ in range(300):
            data = sample(rng)
            self.assertEqual(run(data)[2], run(data)[2])

    def test_at_most_once_and_only_for_a_refusal_with_a_record(self):
        """TASK-063 AC10, AC5: adapter.violation appends at most one violation, and only when entry refused with a
        record; hook_result is never changed."""
        rng = random.Random(6302)
        for _ in range(500):
            h, before, r, store = run(sample(rng))
            self.assertEqual(h, before)
            self.assertLessEqual(store.violations, 1)
            if store.violations:
                self.assertEqual(h['verdict'], 'refuse')
                self.assertIsNotNone(h['record'])
                self.assertEqual(r['result'], 'written')
            else:
                self.assertNotEqual(r['result'], 'written')

    def test_no_shell_text_kept(self):
        """TASK-063 AC10, AC3, AC5: a shell refusal's passed record has exactly its fixed text as refers_to, and none of
        three marker words of the command appears in the result."""
        rng = random.Random(6303)
        for _ in range(500):
            h, _, r, _ = run(sample(rng))
            rec = h['record']
            if rec and rec['evidence_type'] in ('git_push_refused', 'shell_not_allowed'):
                self.assertEqual(r['record']['refers_to'], ch.REDACTED[rec['evidence_type']])
                for marker in ('Zq7xW', 'secretQ9', '$(id)'):
                    if marker in rec['refers_to']:
                        self.assertNotIn(marker, repr(r))

    def test_both_branches_occur(self):
        """TASK-063 AC10 and TASK-063 AC5: over the samples of the property above, some refusals are passed to the core
        and some calls write nothing, so that property is not vacuous."""
        rng = random.Random(6302)
        passed = sum(1 for _ in range(500) if run(sample(rng))[3].violations)
        self.assertTrue(0 < passed < 500, passed)


if __name__ == '__main__':
    unittest.main()

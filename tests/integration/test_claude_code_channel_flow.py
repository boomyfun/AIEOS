"""Integration tests of aieos_bootstrap.claude_code_channel (task TASK-063, AC10's integration test): hook-input bytes
of the documented form (values made up) through aieos_bootstrap.claude_code_hook.entry to deliver, with stand-ins for
the writer's append and release, so no file is written. Each test names its criteria in its own docstring."""

import datetime
import json
import types
import unittest

from aieos_bootstrap import claude_code_channel as ch
from aieos_bootstrap import claude_code_hook

NOW = datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)
SID = 'made-up-session-9'
CTX = {'root': 'C:\\proj\\repo', 'task_id': 'TASK-100', 'session_id': SID,
       'fencing_token': {'epoch': 'e1', 'counter': 0}, 'write_set': ['docs/notes/**'],
       'allowlist': ['git status'], 'recorder': 'a test session ' + SID}


class Store:
    def __init__(self):
        self.events = []

    def append(self, root, event_type, payload, event_id, now, recorder, task_id=None, fencing_token=None):
        self.events.append((event_type, payload, event_id))
        return types.SimpleNamespace(result='appended', reason=None, findings=())

    def release(self, root, task_id, token):
        return types.SimpleNamespace(result='done', reason=None, findings=(), value=None)


def flow(tool, tool_input, ctx=CTX):
    data = json.dumps({'session_id': 'other', 'cwd': 'C:\\elsewhere', 'hook_event_name': 'PreToolUse',
                       'tool_use_id': 'made-up-use', 'tool_name': tool, 'tool_input': tool_input}).encode('utf-8')
    h = claude_code_hook.entry(data, ctx['root'], ctx['task_id'], ctx['write_set'], ctx['allowlist'], 'obs-1',
                               ctx['recorder'])
    code = h['exit_code']
    store = Store()
    r = ch.deliver(ctx, h, 'ev-1', NOW, append=store.append, release=store.release)
    return h, code, r, store


class Flow(unittest.TestCase):
    def test_write_outside_the_write_set(self):
        """TASK-063 AC5, AC4, AC10: a write below the root outside the write-set reaches the core with its
        root-relative path kept, and the exit code stays 2."""
        h, code, r, store = flow('Write', {'file_path': 'C:\\proj\\repo\\src\\x.py', 'content': 'x'})
        self.assertEqual((h['exit_code'], code, r['result']), (2, 2, 'written'))
        self.assertEqual(store.events[0][0], 'violation.detected')
        self.assertEqual(store.events[0][1]['refers_to'], 'src/x.py')
        self.assertEqual(store.events[1][0], 'decision.execution')

    def test_write_outside_the_root(self):
        """TASK-063 AC4, AC10: a write outside the root reaches the core with the path replaced."""
        h, code, r, store = flow('Write', {'file_path': 'C:\\Users\\someone\\x.txt', 'content': 'x'})
        self.assertEqual(r['result'], 'written')
        self.assertEqual(store.events[0][1]['refers_to'], ch.REDACTED['write_outside_write_set'])

    def test_git_push_and_command_not_allowed(self):
        """TASK-063 AC3, AC10: a git push and a command not allowed reach the core with no command text."""
        for cmd, kind in (('git push origin main', 'git_push_refused'), ('curl example.invalid', 'shell_not_allowed')):
            h, code, r, store = flow('Bash', {'command': cmd})
            self.assertEqual((code, r['result']), (2, 'written'), cmd)
            self.assertEqual(store.events[0][1]['refers_to'], ch.REDACTED[kind])
            self.assertNotIn(cmd, json.dumps([e[1] for e in store.events]))

    def test_allowed_and_uncovered_write_nothing(self):
        """TASK-063 AC5, AC10: an allowed call and an uncovered tool write nothing, and their exit codes stay 0 and
        2."""
        for tool, inp, want in (('Bash', {'command': 'git status'}, (0, 'allow')), ('Read', {'file_path': 'C:/a'}, (0, 'allow')),
                                ('mcp__made_up__tool', {}, (2, 'uncovered'))):
            h, code, r, store = flow(tool, inp)
            self.assertEqual((code, r['reason']), want, tool)
            self.assertEqual((r['result'], store.events), ('nothing', []))

    def test_malformed_allowlist(self):
        """TASK-063 AC1, AC10: a malformed allowlist refuses the context and writes nothing."""
        ctx = dict(CTX, allowlist=['bash -c x'])
        h, code, r, store = flow('Bash', {'command': 'git status'}, ctx)
        self.assertEqual((code, r['result'], r['reason'], store.events), (2, 'refused', 'context', []))


if __name__ == '__main__':
    unittest.main()

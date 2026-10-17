"""Integration tests of aieos_bootstrap.claude_code_hook with aieos_bootstrap.claude_code (task TASK-062, AC10): hook
input bytes of the form Claude Code's hooks reference documents for a PreToolUse hook (the common keys session_id,
transcript_path, cwd, permission_mode, hook_event_name, then tool_name, tool_input and tool_use_id), for the seven judged
tools and for tools that are not judged. Every value is made up; no file is written and no process starts. Each test
names its criteria in its own docstring."""

import json
import unittest

from aieos_bootstrap import claude_code_hook
from aieos_bootstrap import records

ROOT = 'C:\\proj\\repo'
TASK = 'TASK-100'
WS = ['docs/notes/**', 'src/app/*.py']
ALLOW = ['git status', 'git diff --stat', 'ls']


def documented(tool, inp):
    """Bytes of the documented common form, with made-up values."""
    return json.dumps({'session_id': 'abc123', 'prompt_id': 'p-1', 'transcript_path': 'C:/made/up/transcript.jsonl',
                       'cwd': 'C:\\made\\up', 'scratchpad_dir': 'C:/made/up/scratchpad', 'permission_mode': 'default',
                       'hook_event_name': 'PreToolUse', 'tool_name': tool, 'tool_input': inp,
                       'tool_use_id': 'toolu_made_up'}).encode('utf-8')


def run(data, allow=None):
    return claude_code_hook.entry(data, ROOT, TASK, WS, ALLOW if allow is None else allow, 'obs-9', 'an integration test')


class DocumentedInputs(unittest.TestCase):
    def test_judged_tools(self):
        """TASK-062 AC10, AC2, AC3, AC5: Write, Edit, Bash, PowerShell, Read, Grep and Glob in the documented form give
        the verdicts judge gives, with exit codes 0 and 2."""
        cases = [
            ('Write', {'file_path': 'C:\\proj\\repo\\docs\\notes\\a.md', 'content': 'x'}, 'allow', 0),
            ('Write', {'file_path': 'C:\\proj\\repo\\README.md', 'content': 'x'}, 'refuse', 2),
            ('Edit', {'file_path': 'C:/proj/repo/src/app/m.py', 'old_string': 'a', 'new_string': 'b', 'replace_all': False}, 'allow', 0),
            ('Edit', {'file_path': 'C:/proj/repo/src/app/sub/m.py', 'old_string': 'a', 'new_string': 'b'}, 'refuse', 2),
            ('Bash', {'command': 'git status', 'description': 'd', 'timeout': 120000, 'run_in_background': False}, 'allow', 0),
            ('Bash', {'command': 'git -C d push origin', 'description': 'd'}, 'refuse', 2),
            ('PowerShell', {'command': 'git diff --stat', 'description': 'd', 'timeout': 1000}, 'allow', 0),
            ('PowerShell', {'command': 'Remove-Item x', 'description': 'd'}, 'refuse', 2),
            ('Read', {'file_path': 'C:/anywhere/a.txt', 'limit': 5, 'offset': 1}, 'allow', 0),
            ('Grep', {'pattern': 'x', 'path': 'C:/anywhere'}, 'allow', 0),
            ('Glob', {'pattern': '**/*.py', 'path': 'C:/anywhere'}, 'allow', 0),
        ]
        for tool, inp, verdict, code in cases:
            r = run(documented(tool, inp))
            self.assertEqual((r['verdict'], r['exit_code']), (verdict, code), (tool, inp))
            if verdict == 'refuse':
                self.assertEqual(records.check_payload('record.added', r['record']), [])
                self.assertEqual(r['record']['subject'], TASK)

    def test_unjudged_tools(self):
        """TASK-062 AC10, AC5: tools that are not judged (an mcp__ name, MultiEdit, NotebookEdit, Agent, WebFetch) give
        uncovered and exit code 2, so the entry is meant for a matcher naming only the judged tools."""
        for tool in ('mcp__Claude_Browser__navigate', 'MultiEdit', 'NotebookEdit', 'Agent', 'WebFetch'):
            r = run(documented(tool, {'url': 'https://example.invalid/'}))
            self.assertEqual((r['verdict'], r['exit_code'], r['record']), ('uncovered', 2, None), tool)

    def test_other_event_name_judged_alike(self):
        """TASK-062 AC10, AC2: the hook_event_name is not read, so another event name gives the same result."""
        a = run(documented('Bash', {'command': 'ls'}))
        b = json.loads(documented('Bash', {'command': 'ls'}))
        b['hook_event_name'] = 'PostToolUse'
        self.assertEqual(run(json.dumps(b).encode('utf-8')), a)

    def test_malformed_allowlist(self):
        """TASK-062 AC10, AC4: with a malformed allowlist every documented input is refused before judge."""
        for tool, inp in (('Read', {'file_path': 'C:/a'}), ('Bash', {'command': 'git status'})):
            r = run(documented(tool, inp), allow=['git status', 'python -m pytest'])
            self.assertEqual((r['verdict'], r['reason'], r['exit_code']), ('refuse', 'allowlist_form', 2))


if __name__ == '__main__':
    unittest.main()

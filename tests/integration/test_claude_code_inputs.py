"""Integration tests of aieos_bootstrap.claude_code (task TASK-061, TASK-061 AC12's integration part): hook-input mappings of the
shape this project's transcripts show for Write, Edit, Bash, PowerShell, Read, Grep and Glob (their input keys as the
contract's header lists them, the values made up), judged end to end, every refusal record checked by
records.check_payload. These show only how the functions handle such mappings; nothing here runs a hook or Claude Code.
No process starts and no file is written. Each test names its criteria in its own docstring."""

import unittest

from aieos_bootstrap import claude_code
from aieos_bootstrap import records

ROOT = 'C:\\work\\proj'
TASK = 'TASK-200'
WS = ['src/pkg/**', 'tests/unit/test_pkg.py']
ALLOW = ['timeout 110 python tests/run_tests.py', 'git status', 'git diff']


def hook(tool, inp, cwd='C:\\work\\proj', sid='s-1'):
    return {'session_id': sid, 'cwd': cwd, 'tool_name': tool, 'tool_input': inp}


INPUTS = [
    (hook('Write', {'file_path': 'C:\\work\\proj\\src\\pkg\\a.py', 'content': 'x = 1\n'}), 'allow', 'write'),
    (hook('Write', {'file_path': 'C:\\work\\proj\\README.md', 'content': 'x'}), 'refuse', 'write'),
    (hook('Edit', {'file_path': 'C:/work/proj/tests/unit/test_pkg.py', 'old_string': 'a', 'new_string': 'b',
                   'replace_all': False}), 'allow', 'write'),
    (hook('Edit', {'file_path': 'C:\\work\\proj\\src\\pkg\\..\\..\\.github\\workflows\\x.yml', 'old_string': 'a',
                   'new_string': 'b'}), 'refuse', 'write'),
    (hook('Edit', {'file_path': 'src\\pkg\\a.py', 'old_string': 'a', 'new_string': 'b'}), 'uncovered', 'write'),
    (hook('Bash', {'command': 'timeout 110 python tests/run_tests.py < /dev/null', 'description': 'run',
                   'timeout': 120000}), 'allow', 'shell'),
    (hook('Bash', {'command': 'git status && git push origin main', 'description': 'd'}), 'refuse', 'shell'),
    (hook('Bash', {'command': 'curl https://example.invalid', 'run_in_background': False}), 'refuse', 'shell'),
    (hook('PowerShell', {'command': 'git diff', 'description': 'd', 'timeout': 1000}), 'allow', 'shell'),
    (hook('PowerShell', {'command': 'Remove-Item -Recurse x', 'description': 'd'}), 'refuse', 'shell'),
    (hook('Read', {'file_path': 'C:\\anywhere\\x.txt', 'offset': 1, 'limit': 5}), 'allow', 'read'),
    (hook('Grep', {'pattern': 'x', 'path': 'C:\\anywhere', 'output_mode': 'content'}), 'allow', 'read'),
    (hook('Glob', {'pattern': '**/*.py', 'path': 'C:\\anywhere'}), 'allow', 'read'),
    (hook('mcp__Claude_Browser__navigate', {'url': 'https://example.invalid'}), 'uncovered', None),
    (hook('NotebookEdit', {'notebook_path': 'C:\\work\\proj\\src\\pkg\\n.ipynb'}), 'uncovered', None),
]


class Inputs(unittest.TestCase):
    def test_observed_shapes(self):
        """TASK-061 AC2, TASK-061 AC4, TASK-061 AC5, TASK-061 AC6, TASK-061 AC7, TASK-061 AC8, TASK-061 AC12: each
        made-up mapping of an observed shape gets its expected verdict and concern, and every refusal record passes
        check_payload."""
        for i, (h, verdict, concern) in enumerate(INPUTS):
            r = claude_code.judge(h, ROOT, TASK, WS, ALLOW, 'obs-%d' % i, 'an integration test')
            self.assertEqual((r['verdict'], r['concern']), (verdict, concern), h)
            if verdict == 'refuse':
                self.assertEqual(records.check_payload('record.added', r['record']), [], h)
                self.assertEqual(r['record']['subject'], TASK)

    def test_relative_path_uncovered(self):
        """TASK-061 AC3, TASK-061 AC12 (D-1212 F4): judge passes no cwd, so a relative path is uncovered, reason path,
        whatever the hook input's cwd says."""
        for cwd in ('C:\\work\\proj', None):
            h = hook('Write', {'file_path': 'src\\pkg\\b.py', 'content': ''}, cwd=cwd)
            r = claude_code.judge(h, ROOT, TASK, WS, ALLOW, 'o', 'r')
            self.assertEqual((r['verdict'], r['reason'], r['record']), ('uncovered', 'path', None), cwd)

    def test_extra_keys_ignored(self):
        """TASK-061 AC2, TASK-061 AC12: keys of the hook input other than tool_name and tool_input change nothing."""
        a = hook('Write', {'file_path': 'C:\\work\\proj\\src\\pkg\\a.py', 'content': ''})
        b = dict(a, cwd='D:\\else', transcript_path='C:\\x.jsonl', hook_event_name='PreToolUse', permission_mode='auto')
        self.assertEqual(claude_code.judge(a, ROOT, TASK, WS, ALLOW, 'o', 'r'),
                         claude_code.judge(b, ROOT, TASK, WS, ALLOW, 'o', 'r'))


if __name__ == '__main__':
    unittest.main()

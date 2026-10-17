"""Property tests of aieos_bootstrap.claude_code_hook (task TASK-062, AC10), with the standard library only and fixed
seeds: the entry is deterministic; it gives exit code 0 only when judge, on the same two keys, gives "allow" and the
allowlist is well formed; keys other than tool_name and tool_input never change the result; and every record it returns
equals judge's. No file is written. Each test names its criteria in its own docstring."""

import json
import random
import unittest

from aieos_bootstrap import claude_code
from aieos_bootstrap import claude_code_hook

ROOT = 'C:\\proj\\repo'
TASK = 'TASK-100'
WS = ['docs/notes/**']
RID = 'obs-p'
REC = 'a property test'
TOOLS = ['Write', 'Edit', 'Bash', 'PowerShell', 'Read', 'Grep', 'Glob', 'MultiEdit', 'mcp__a__b', '', None, 3]
WORDS = ['git', 'status', 'push', 'diff', '--stat', 'ls', 'bash', '-c', ';', '&&', '|', '(', ')', '"', "'", '$', '`',
         'C:\\proj\\repo\\docs\\notes\\a.md', 'docs/notes/b.md', '..', 'C:/other/x', '\n', '\t', 'X=1', 'GIT', 'PUSH']
ENTRIES = ['git status', 'git diff --stat', 'ls', 'bash', 'git', 'git -c x', 'X=1 ls', 'git  status', 'sh x', 'make test',
           '/usr/bin/bash', 'git status;', 'C:git -c x', 3]


def gen_text(rng):
    return ' '.join(rng.choice(WORDS) for _ in range(rng.randint(0, 6)))


def gen_input(rng):
    tool = rng.choice(TOOLS)
    k = rng.random()
    if k < 0.1:
        inp = rng.choice([None, 'x', [], 5])
    else:
        inp = {}
        if rng.random() < 0.8:
            inp[rng.choice(['file_path', 'command', 'pattern'])] = rng.choice([gen_text(rng), None, 4])
    obj = {'tool_name': tool, 'tool_input': inp}
    if rng.random() < 0.2:
        del obj['tool_name']
    for key in ('session_id', 'cwd', 'hook_event_name'):
        if rng.random() < 0.5:
            obj[key] = gen_text(rng)
    return obj


def gen_allow(rng):
    return [rng.choice(ENTRIES) for _ in range(rng.randint(0, 3))]


def entry(data, allow):
    return claude_code_hook.entry(data, ROOT, TASK, WS, allow, RID, REC)


class Properties(unittest.TestCase):
    def test_deterministic(self):
        """TASK-062 AC10, AC6: equal inputs give equal results."""
        rng = random.Random(6201)
        for _ in range(400):
            obj, allow = gen_input(rng), gen_allow(rng)
            data = json.dumps(obj).encode('utf-8')
            self.assertEqual(entry(data, list(allow)), entry(data, list(allow)))

    def test_exit_0_only_for_allow_by_judge(self):
        """TASK-062 AC10, AC3, AC4, AC5: exit code 0 only when the allowlist is well formed and judge, called on the
        same two keys, gives allow; every other case gives exit code 2."""
        rng = random.Random(6202)
        for _ in range(1500):
            obj, allow = gen_input(rng), gen_allow(rng)
            r = entry(json.dumps(obj).encode('utf-8'), allow)
            self.assertIn(r['exit_code'], (0, 2))
            if r['exit_code'] == 0:
                self.assertEqual(claude_code_hook.allowlist_findings(allow), [])
                two = {k: obj[k] for k in ('tool_name', 'tool_input') if k in obj}
                self.assertEqual(claude_code.judge(two, ROOT, TASK, WS, allow, RID, REC)['verdict'], 'allow')
                self.assertEqual((r['verdict'], r['stderr']), ('allow', ''))
            else:
                self.assertNotEqual(r['verdict'], 'allow')

    def test_other_keys_never_change_the_result(self):
        """TASK-062 AC10, AC2: keys other than tool_name and tool_input never change the result."""
        rng = random.Random(6203)
        for _ in range(400):
            obj, allow = gen_input(rng), gen_allow(rng)
            two = {k: obj[k] for k in ('tool_name', 'tool_input') if k in obj}
            more = dict(two, cwd=gen_text(rng), session_id=gen_text(rng), extra={'tool_name': 'Read'})
            self.assertEqual(entry(json.dumps(two).encode('utf-8'), allow), entry(json.dumps(more).encode('utf-8'), allow))

    def test_records_equal_judges(self):
        """TASK-062 AC10, AC3: every record returned equals judge's record for the same two keys."""
        rng = random.Random(6204)
        seen = 0
        for _ in range(1500):
            obj, allow = gen_input(rng), gen_allow(rng)
            r = entry(json.dumps(obj).encode('utf-8'), allow)
            if r['record'] is not None:
                seen += 1
                two = {k: obj[k] for k in ('tool_name', 'tool_input') if k in obj}
                self.assertEqual(r['record'], claude_code.judge(two, ROOT, TASK, WS, allow, RID, REC)['record'])
        self.assertGreater(seen, 0)

    def test_random_bytes_never_allow(self):
        """TASK-062 AC10, AC2, AC5: random bytes never give allow and never raise."""
        rng = random.Random(6205)
        for _ in range(500):
            data = bytes(rng.randrange(256) for _ in range(rng.randint(0, 40)))
            r = entry(data, ['git status'])
            self.assertNotEqual(r['verdict'], 'allow')
            self.assertEqual(r['exit_code'], 2)


if __name__ == '__main__':
    unittest.main()

"""Property tests of aieos_bootstrap.claude_code (task TASK-061, TASK-061 AC12's property part), standard library only, fixed
seeds: judge is deterministic over equal inputs; no generated input gives "allow" outside the named concerns (a write
within the write-set, a shell call within the allowlist with no push, a read); every refusal record passes
records.check_payload; no exception escapes. No process starts and no file is written. Each test names its criteria in
its own docstring."""

import random
import unittest

from aieos_bootstrap import claude_code
from aieos_bootstrap import governor
from aieos_bootstrap import records

ROOT = 'C:\\r\\p'
TASK = 'TASK-300'
WS = ['src/**', 'docs/a.md']
ALLOW = ['git status', 'echo', 'bash']
TOOLS = ['Write', 'Edit', 'Bash', 'PowerShell', 'Read', 'Grep', 'Glob', 'MultiEdit', 'NotebookEdit', 'Agent',
         'mcp__x__y', 'WebFetch', '', None]
PARTS = ['src', 'docs', 'a.md', '..', '.', 'x', 'Src', 'b.py', 'C:', 'D:', ' ', 'a.', 'p', 'r', '\\', ':']
WORDS = ['git', 'push', 'status', 'echo', 'bash', '-c', '"git push"', "'x'", '&&', ';', '|', '(', ')', '$(', '`',
         'rm', 'X=1', 'env', 'git.exe', '"', '\n', 'GIT', 'Push']


def gen_path(rng):
    sep = rng.choice(['/', '\\'])
    head = rng.choice(['C:' + sep + 'r' + sep + 'p' + sep, 'c:/R/P/', '', 'D:/', '/', '\\\\s\\'])
    return head + sep.join(rng.choice(PARTS) for _ in range(rng.randint(0, 5)))


def gen_input(rng):
    tool = rng.choice(TOOLS)
    if rng.random() < 0.5:
        inp = {'file_path': gen_path(rng)}
    else:
        inp = {'command': ' '.join(rng.choice(WORDS) for _ in range(rng.randint(0, 6)))}
    if rng.random() < 0.1:
        inp = rng.choice([None, 'x', 3, []])
    h = {'tool_name': tool, 'tool_input': inp}
    if rng.random() < 0.5:
        h['cwd'] = rng.choice(['C:\\r\\p', 'C:\\r\\p\\src', 'rel', None])
    return h


class Properties(unittest.TestCase):
    def test_deterministic(self):
        """TASK-061 AC8, TASK-061 AC12: two calls over equal inputs give equal results."""
        rng = random.Random(61001)
        for _ in range(400):
            h = gen_input(rng)
            self.assertEqual(claude_code.judge(h, ROOT, TASK, WS, ALLOW, 'o', 'r'),
                             claude_code.judge(h, ROOT, TASK, WS, ALLOW, 'o', 'r'))

    def test_no_allow_outside_named_concerns(self):
        """TASK-061 AC2, TASK-061 AC4, TASK-061 AC5, TASK-061 AC6, TASK-061 AC12: every allow is a read, a write whose normalised path matches the
        write-set, or a shell call with no git-and-push words whose simple commands all start with an entry."""
        rng = random.Random(61002)
        for _ in range(2000):
            h = gen_input(rng)
            r = claude_code.judge(h, ROOT, TASK, WS, ALLOW, 'o', 'r')
            self.assertIn(r['verdict'], claude_code.VERDICTS)
            if r['verdict'] != 'allow':
                continue
            tool, inp = h['tool_name'], h['tool_input']
            self.assertIn(tool, claude_code.READ_TOOLS + claude_code.WRITE_TOOLS + claude_code.SHELL_TOOLS, h)
            if tool in claude_code.WRITE_TOOLS:
                status, value = claude_code.normalise_path(ROOT, None, inp['file_path'])
                self.assertEqual(status, 'ok', h)
                self.assertTrue(any(governor.matches(p, value) for p in WS), h)
            if tool in claude_code.SHELL_TOOLS:
                text = inp['command']
                self.assertFalse(claude_code._text_pushes(text), h)
                cmds = claude_code._split(text)
                self.assertIsNotNone(cmds, h)
                for c in cmds:
                    self.assertTrue(any(c[:len(e.split())] == e.split() for e in ALLOW), h)

    def test_bypass_corpus_never_allowed(self):
        """TASK-061 AC5, TASK-061 AC6, TASK-061 AC12 (D-1219 C3): a fixed corpus of strings that ran a command outside
        the allowlist, or a push, under the entry each names, is never allowed; the oracle is the corpus itself, not the
        module's split or push helpers."""
        corpus = [('Bash', 'python -m pytest "$(G=gi;${G}t push)"', ['python -m pytest']),
                  ('Bash', 'python -m pytest "$($(printf gi)t push)"', ['python -m pytest']),
                  ('Bash', 'python -m pytest "`G=gi;H=t;$G$H push`"', ['python -m pytest']),
                  ('Bash', 'bash -c "G=gi;\\${G}t push"', ['bash']),
                  ('Bash', 'echo "$(rm x)"', ['echo']),
                  ('Bash', 'python -m pytest \\" ; G=gi ; H=t ; $G$H push ; echo " \\" "', ['python -m pytest']),
                  ('Bash', 'git status \\"; rm x # "', ['git status']),
                  ('PowerShell', 'echo "a\\" ; rm x ; echo \\"b"', ['echo']),
                  ('Bash', "echo $'a\\' ; rm x ; '", ['echo']),
                  ('PowerShell', 'git status\rrm x', ['git status']),
                  ('Bash', 'G=gi && ${G}t push', ['git status']),
                  ('Bash', 'G=gi && $G' + 't push', ['git status']),
                  ('Bash', 'echo hi # "\nrm x\n# "', ['echo']),
                  ('PowerShell', 'echo hi # "\nrm x\n# "', ['echo']),
                  ('PowerShell', 'echo <# " #> ; rm x ; echo <# " #>', ['echo']),
                  ('PowerShell', 'echo "a\u201c ; rm x ; echo \u201db"', ['echo']),
                  ('PowerShell', "echo 'a\u2019 ; rm x ; echo \u2018b'", ['echo'])]
        for tool, cmd, allow in corpus:
            r = claude_code.judge({'tool_name': tool, 'tool_input': {'command': cmd}}, ROOT, TASK, WS, allow, 'o', 'r')
            self.assertNotEqual(r['verdict'], 'allow', (tool, cmd, allow))

    def test_refusal_records_pass(self):
        """TASK-061 AC7, TASK-061 AC8, TASK-061 AC12: every refusal on a policy concern carries a record that check_payload accepts."""
        rng = random.Random(61003)
        for _ in range(1000):
            h = gen_input(rng)
            r = claude_code.judge(h, ROOT, TASK, WS, ALLOW, 'o', 'r')
            if r['verdict'] == 'refuse' and r['reason'] not in ('argument', 'record'):
                self.assertEqual(records.check_payload('record.added', r['record']), [], h)
            else:
                self.assertIsNone(r['record'], h)


if __name__ == '__main__':
    unittest.main()

"""Property tests of aieos_bootstrap.claude_code_shell_allow's combine (TASK-076 AC5), standard library only, fixed
seeds, at most 200 cases each: over generated lists of made-up entries and generated simple commands, a command is
allowed by claude_code.judge under the one list exactly when it matches an entry of each list by the judge's rule, and
either list empty gives an empty list. No file is read or written."""

import random
import unittest

from aieos_bootstrap import claude_code, claude_code_hook, claude_code_shell_allow as sa

CASES = 200
ROOT = 'C:\\made-up-root'
TASK = 'TASK-001'
RECORDER = 'claude_code_pretool_hook, session s-1'
FIRST = ('ls', 'cat', 'echo', 'git', 'grep')
REST = ('status', 'log', '-la', 'a.txt', 'b', 'x', 'diff')


def some_entry(rng):
    words = [rng.choice(FIRST)] + [rng.choice(REST) for _ in range(rng.randrange(3))]
    return ' '.join(words)


def some_list(rng):
    out = [some_entry(rng) for _ in range(rng.randrange(4))]
    return [e for e in out if not claude_code_hook.allowlist_findings([e])]


def matches(command, entries):
    words = command.split()
    return any(words[:len(e.split())] == e.split() for e in entries)


def verdict(command, allowlist):
    hook_input = {'tool_name': 'Bash', 'tool_input': {'command': command}}
    return claude_code.judge(hook_input, ROOT, TASK, ['src/a.py'], allowlist, 'r', RECORDER)['verdict']


class AC5Properties(unittest.TestCase):

    def test_the_one_list_allows_exactly_what_both_lists_allow(self):
        """TASK-076 AC5: over generated word lists, a simple command is allowed under combine(policy, contract) exactly
        when it matches an entry of the policy list and an entry of the contract list, by the judge's rule."""
        rng = random.Random(75)
        for _ in range(CASES):
            policy, contract = some_list(rng), some_list(rng)
            one = sa.combine(policy, contract)
            command = some_entry(rng)
            with self.subTest(policy=policy, contract=contract, command=command):
                self.assertEqual(claude_code_hook.allowlist_findings(one), [])
                want = matches(command, policy) and matches(command, contract)
                self.assertEqual(matches(command, one), want)
                self.assertEqual(verdict(command, one) == 'allow', want)

    def test_either_list_empty_gives_an_empty_list(self):
        """TASK-076 AC5: combine gives an empty list when either list is empty, and never repeats an entry."""
        rng = random.Random(750)
        for _ in range(CASES):
            entries = some_list(rng)
            with self.subTest(entries=entries):
                self.assertEqual(sa.combine(entries, []), [])
                self.assertEqual(sa.combine([], entries), [])
                one = sa.combine(entries, some_list(rng))
                self.assertEqual(len(one), len(set(one)))


if __name__ == '__main__':
    unittest.main()

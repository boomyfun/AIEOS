"""Integration tests of the text of the workflow's G0 detect (task TASK-114, AC1 to AC3). They compare text only: the
two G0 scripts of .github/workflows/aieos-checks.yml are equal when dedented from their header comment to the end of
detect (imports included); the copy holds the lines that read the contract at docs/tasks/<id>.yaml or
at .aieos/tasks/<id>.yaml (a membership test, which does not show that a line is reached); the two pinned GOV-003
lists are equal and hold '.aieos/tasks/**'. The behaviour of detect is shown by a scratchpad harness that is not part
of the repository. Each test names its criteria in its own docstring."""

import ast
import pathlib
import re
import textwrap
import unittest

ROOT = str(pathlib.Path(__file__).resolve().parents[2])
DETECT_LINES = [
    "docs_path = 'docs/tasks/' + tid + '.yaml'",
    "state_path = '.aieos/tasks/' + tid + '.yaml'",
    'for cand in (docs_path, state_path):',
    'if len(found) > 1:',
    'if not found:',
    "allowed = [path] if path == docs_path else sorted([path, '.aieos/events.jsonl'])",
    'if len(parents) != 1 or (changed != [path] and sorted(changed) != allowed):',
    'if len(adds) != 1:',
]


def workflow():
    return (pathlib.Path(ROOT) / '.github' / 'workflows' / 'aieos-checks.yml').read_bytes().decode('utf-8')


def detect_copies(wf):
    copies = []
    for m in re.finditer(r'^( *)def detect\(\):\n(?:\1    .*\n|\n)*', wf, re.M):
        copies.append(textwrap.dedent(m.group(0)))
    return copies


class AC1Copies(unittest.TestCase):

    def test_the_two_copies_of_detect_are_equal(self):
        """TASK-114 AC1: the workflow holds exactly two copies of detect, equal when dedented."""
        copies = detect_copies(workflow())
        self.assertEqual(len(copies), 2)
        self.assertEqual(copies[0], copies[1])

    def test_the_two_scripts_are_equal_up_to_the_end_of_detect(self):
        """TASK-114 AC1: the two G0 scripts are equal when dedented from their header comment to the end of detect, so
        the imports, the TRAILER line and every function defined before detect are the same in both copies."""
        heads = [textwrap.dedent(m.group(0)) for m in re.finditer(
            r'^( *)# AIEOS CI: G0 scope \(V0\) for a task commit .*\n(?:\1.*\n|\n)*?\1def detect\(\):\n(?:\1    .*\n|\n)*',
            workflow(), re.M)]
        self.assertEqual(len(heads), 2)
        self.assertEqual(heads[0], heads[1])
        for name in ('import hashlib', 'TRAILER = re.compile(', 'def git(', 'def trailer(', 'def parse_contract(',
                     'def detect('):
            with self.subTest(name=name):
                self.assertEqual(heads[0].count('\n' + name), 1)

    def test_the_copy_holds_the_lines_of_the_two_folders(self):
        """TASK-114 AC2 and TASK-114 AC3: the stripped lines of the copy hold each line that reads the contract at
        docs/tasks or at .aieos/tasks, refuses the same id in both, and limits the changed paths of the commit."""
        lines = [ln.strip() for ln in detect_copies(workflow())[0].split('\n')]
        for rule in DETECT_LINES:
            with self.subTest(rule=rule):
                self.assertIn(rule, lines)

    def test_the_two_evaluator_lists_are_equal_and_hold_the_state_folder(self):
        """TASK-114 AC1: the workflow holds exactly two EVALUATOR literals, equal, each holding 'docs/tasks/**' and
        '.aieos/tasks/**' side by side."""
        lists = re.findall(r'^ *EVALUATOR = \[.*?\]$', workflow(), re.M | re.S)
        self.assertEqual(len(lists), 2)
        self.assertEqual(lists[0], lists[1])
        for text in lists:
            self.assertIn("'docs/tasks/**', '.aieos/tasks/**'", text)


class OwnTests(unittest.TestCase):

    def test_every_test_names_its_criteria(self):
        """TASK-114 AC3: every test function of this module names "TASK-114 ACn" in its own docstring and no other
        task's AC in qualified form."""
        tree = ast.parse(pathlib.Path(__file__).read_bytes().decode('utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                doc = ast.get_docstring(node) or ''
                with self.subTest(test=node.name):
                    self.assertRegex(' '.join(doc.split()), r'TASK-114 AC[0-9]')
                    self.assertEqual(re.findall(r'TASK-(?!114 )[0-9]+ AC[0-9]+', ' '.join(doc.split())), [])


if __name__ == '__main__':
    unittest.main()

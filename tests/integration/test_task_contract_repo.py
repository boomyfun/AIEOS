"""Integration tests of aieos_bootstrap.task_contract over this repository's history (task TASK-071, AC3, AC4 and
AC8): the real five-call walk through gitread.run at fixed and current commits, with G0's own layout rules as the
oracle for the well-formed contracts. Read only; it needs the full history, as tests/integration/test_gitread_repo.py
does, so a shallow clone fails it. Each test names its criteria in its own docstring."""

import ast
import pathlib
import re
import textwrap
import unittest

from aieos_bootstrap import gitread
from aieos_bootstrap import task_contract as tc

ROOT = str(pathlib.Path(__file__).resolve().parents[2])
TASK_070_ADDED = 'ade98ec4c29430fa821c27bb0111665ab0b756a1'
TASK_070_BASE = 'e698389fc36710be2bffbeea8750941d6b22facb'
TASK_070_FORBIDDEN = 193
TASK_070_WRITE_SET = ['src/aieos_bootstrap/session_violation.py', 'tests/unit/test_session_violation.py',
                      'tests/integration/test_writer_files.py', 'tests/property/test_session_violation_properties.py']
RULE_LINES = [
    "if not raw.strip() or raw.lstrip().startswith('#'):",
    "indent = len(raw) - len(raw.lstrip(' '))",
    'line = raw.strip()',
    'if indent == 0:',
    "section, sub = line.split(':', 1)[0], None",
    "out['task'] = line.split(':', 1)[1].strip()",
    "if section == 'input_state' and indent == 2 and line.startswith('base_commit:'):",
    "elif section == 'write_set' and indent == 2:",
    "elif section == 'write_set' and sub == 'paths' and indent == 4 and line.startswith('- '):",
    "elif section == 'forbidden' and indent == 2 and line.startswith('- '):",
    "if not re.fullmatch(r'[0-9a-f]{40}', out['base_commit']):",
    "if not out['write_set'] or not out['forbidden']:",
]


def other_task_ids(text):
    """The qualified AC ids of tasks other than TASK-071 in text, with every run of whitespace collapsed (rule (e))."""
    return re.findall(r'TASK-(?!071 )[0-9]+ AC[0-9]+', ' '.join(text.split()))


def g0_lists(text):
    """The test's copy of G0's loop (the workflow's parse_contract), the oracle for the well-formed contracts only."""
    out = {'write_set': [], 'forbidden': []}
    section = sub = None
    for raw in text.split('\n'):
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        indent = len(raw) - len(raw.lstrip(' '))
        line = raw.strip()
        if indent == 0:
            section, sub = line.split(':', 1)[0], None
            continue
        if section == 'write_set' and indent == 2:
            sub = line.split(':', 1)[0]
        elif section == 'write_set' and sub == 'paths' and indent == 4 and line.startswith('- '):
            out['write_set'].append(line[2:].strip())
        elif section == 'forbidden' and indent == 2 and line.startswith('- '):
            out['forbidden'].append(line[2:].strip())
    return out


def head():
    r = gitread.run(ROOT, ['rev-parse', '--verify', '--end-of-options', 'HEAD'], 10)
    return r['out'].decode('ascii').strip()


def blob_at(commit, task_id):
    """The contract's bytes at commit, through gitread.run (cat-file of the commit and of each tree)."""
    oid = gitread.parse_commit(gitread.run(ROOT, ['cat-file', '-p', commit], 10)['out'])['tree']
    for name in ('docs', 'tasks', task_id + '.yaml'):
        text = gitread.run(ROOT, ['cat-file', '-p', oid], 10)['out'].decode('utf-8')
        oid = [ln.split(' ')[2].split('\t')[0] for ln in text.split('\n') if ln.endswith('\t' + name)][0]
    return gitread.run(ROOT, ['cat-file', '-p', oid], 10)['out']


class AC3RealContracts(unittest.TestCase):

    def test_the_committed_contracts_read(self):
        """TASK-071 AC3: TASK-061 to TASK-070 as committed at HEAD give "read", by the real walk and by parse_contract
        on the same bytes, with write_set and forbidden equal to G0's lists."""
        commit = head()
        for n in range(61, 71):
            tid = 'TASK-%03d' % n
            with self.subTest(task=tid):
                r = tc.read_contract(ROOT, commit, tid)
                self.assertEqual((r['result'], r['task']), ('read', tid))
                text = blob_at(commit, tid).decode('utf-8')
                self.assertEqual(tc.parse_contract(text, tid), r)
                g0 = g0_lists(text)
                self.assertEqual((r['write_set'], r['forbidden']), (g0['write_set'], g0['forbidden']))

    def test_the_workflow_copies_of_g0_hold_the_rules(self):
        """TASK-071 AC3: both copies of the workflow's parse_contract are equal, dedented, and hold the layout rule
        lines (text compared, not line numbers)."""
        wf = (pathlib.Path(ROOT) / '.github' / 'workflows' / 'aieos-checks.yml').read_bytes().decode('utf-8')
        copies = []
        for m in re.finditer(r'^( *)def parse_contract\(text\):\n(?:\1    .*\n|\n)*', wf, re.M):
            copies.append(textwrap.dedent(m.group(0)))
        self.assertEqual(len(copies), 2)
        self.assertEqual(copies[0], copies[1])
        lines = [ln.strip() for ln in copies[0].split('\n')]
        for rule in RULE_LINES:
            with self.subTest(rule=rule):
                self.assertIn(rule, lines)


class AC4History(unittest.TestCase):

    def test_task_070_at_the_commit_that_added_it(self):
        """TASK-071 AC4: TASK-070's contract at the commit that added it gives "read" with its four write-set paths,
        its task, base_commit and forbidden length; TASK-071 there is "tree: contract missing"; a missing commit is
        "git"."""
        r = tc.read_contract(ROOT, TASK_070_ADDED, 'TASK-070')
        self.assertEqual((r['result'], r['task'], r['base_commit']), ('read', 'TASK-070', TASK_070_BASE))
        self.assertEqual(sorted(r['write_set']), sorted(TASK_070_WRITE_SET))
        self.assertEqual(len(r['forbidden']), TASK_070_FORBIDDEN)
        r = tc.read_contract(ROOT, TASK_070_ADDED, 'TASK-071')
        self.assertEqual((r['result'], r['reason'], r['findings']), ('unreadable', 'tree', ['tree: contract missing']))
        r = tc.read_contract(ROOT, '0' * 40, 'TASK-070')
        self.assertEqual((r['result'], r['reason']), ('unreadable', 'git'))


class AC8OwnTests(unittest.TestCase):

    def test_task_contract_repo_tests_name_their_criteria(self):
        """TASK-071 AC8: every test function of this module names "TASK-071 ACn" in its own docstring and no other
        task's AC in qualified form."""
        tree = ast.parse(pathlib.Path(__file__).read_bytes().decode('utf-8'))
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test')]:
            doc = ast.get_docstring(fn) or ''
            with self.subTest(test=fn.name):
                self.assertTrue(re.findall(r'TASK-071 AC[0-9]+', ' '.join(doc.split())))
                self.assertEqual(other_task_ids(doc), [])


if __name__ == '__main__':
    unittest.main()

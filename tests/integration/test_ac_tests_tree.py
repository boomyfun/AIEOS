"""Integration test of aieos_bootstrap.ac_tests over the task contracts and the tests in the tree (task TASK-022;
decision D-530 Q1 and C2): read only, with pathlib's read_bytes; each contract's fields are taken by this test's own
line-based reader, not by the module. The untested criteria of the tasks accepted before TASK-022 are data: they are
asserted as counts per task, they are not fixed by this task and they reopen no acceptance."""

import pathlib
import re
import unittest

from aieos_bootstrap import ac_tests

ROOT = pathlib.Path(__file__).resolve().parents[2]
TASKS = ['TASK-%03d' % n for n in range(1, 23)]
GROUPS = ('unit', 'integration', 'property')
# The untested counts per task before TASK-022, and the number of distinct ambiguous test keys over all tasks: the
# prescan's numbers that the contract fixes (TASK-022 AC10; decision D-530 C2).
EXPECTED_UNTESTED = {
    'TASK-001': 8, 'TASK-002': 6, 'TASK-003': 11, 'TASK-004': 12, 'TASK-005': 7, 'TASK-006': 11, 'TASK-007': 10,
    'TASK-008': 12, 'TASK-009': 10, 'TASK-010': 5, 'TASK-011': 7, 'TASK-012': 4, 'TASK-013': 8, 'TASK-014': 6,
    'TASK-015': 7, 'TASK-016': 10, 'TASK-017': 14, 'TASK-018': 8, 'TASK-019': 8, 'TASK-020': 7, 'TASK-021': 9}
EXPECTED_AMBIGUOUS = 2
_TOP = re.compile(r'^([a-z_]+):(.*)$')
_AC = re.compile(r'^  - (AC[0-9]+[a-z]?): ')
_GATE = re.compile(r'^  - \{gate: (G[0-9]+), check: ([a-z_]+)(?:, args: \[(.*)\])?\}$')
_PATH = re.compile(r'^    - (\S+)$')


def read_contract(text):
    """acceptance_criteria, verification_plan, constitution and the write set's paths of a contract's text, as values;
    every non-empty line of the plan must be a gate line."""
    out = {'acceptance_criteria': [], 'verification_plan': [], 'constitution': None, 'write_set': []}
    section = None
    for line in text.split('\n'):
        top = _TOP.match(line)
        if top:
            section = top.group(1)
            if section == 'constitution':
                out['constitution'] = [a.strip() for a in top.group(2).strip().strip('[]').split(',') if a.strip()]
            continue
        if section == 'acceptance_criteria':
            m = _AC.match(line)
            if m:
                out['acceptance_criteria'].append({m.group(1): line[m.end():] or '>-'})
        elif section == 'verification_plan' and line.strip():
            m = _GATE.match(line)
            if not m:
                raise ValueError('a plan line is not a gate line: %r' % line)
            gate = {'gate': m.group(1), 'check': m.group(2)}
            if m.group(3) is not None:
                gate['args'] = [a.strip() for a in m.group(3).split(',')]
            out['verification_plan'].append(gate)
        elif section == 'write_set':
            m = _PATH.match(line)
            if m:
                out['write_set'].append(m.group(1))
    return out


def the_tree():
    contracts = {t: read_contract((ROOT / 'docs' / 'tasks' / (t + '.yaml')).read_bytes().decode('utf-8')) for t in TASKS}
    tests = {}
    for group in GROUPS:
        for p in sorted((ROOT / 'tests' / group).glob('*.py')):
            tests[p.relative_to(ROOT).as_posix()] = p.read_bytes().decode('utf-8')
    write_sets = {t: c['write_set'] for t, c in contracts.items()}
    return contracts, tests, write_sets


class TheTree(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.contracts, cls.tests, cls.write_sets = the_tree()
        cls.out = {t: ac_tests.listing(t, c, cls.tests, cls.write_sets) for t, c in cls.contracts.items()}

    def test_reader(self):
        """TASK-022 AC10: the test's own reader takes the write set's paths with the other three fields."""
        text = ('write_set:\n  paths:\n    - src/a.py\n    - tests/unit/test_a.py\nconstitution: [INV-001]\n'
                'acceptance_criteria:\n  - AC1: x\nverification_plan:\n  - {gate: G2, check: tests, args: [AC1]}\n')
        values = read_contract(text)
        self.assertEqual(values['write_set'], ['src/a.py', 'tests/unit/test_a.py'])
        self.assertEqual(values['verification_plan'], [{'gate': 'G2', 'check': 'tests', 'args': ['AC1']}])
        with self.assertRaises(ValueError):
            read_contract('verification_plan:\n  - gate G0\n')

    def test_no_input_is_malformed(self):
        """TASK-022 AC10 and TASK-022 AC1: every contract and every test file of the tree is well formed for the module."""
        for task, out in self.out.items():
            with self.subTest(task=task):
                self.assertNotIn('malformed', [f['kind'] for f in out['findings']])

    def test_the_past_as_counts(self):
        """TASK-022 AC10: the untested counts per task for the tasks accepted before TASK-022, as data."""
        counts = {t: len(self.out[t]['findings']) for t in TASKS if t != 'TASK-022'}
        self.assertEqual(counts, EXPECTED_UNTESTED)
        self.assertEqual(sum(counts.values()), 180)
        for t in counts:
            self.assertEqual({f['kind'] for f in self.out[t]['findings']} - {'untested'}, set())

    def test_the_ambiguous_keys(self):
        """TASK-022 AC10 and TASK-022 AC2: the distinct ambiguous test keys over all tasks (decision D-531 C2)."""
        keys = set()
        for out in self.out.values():
            keys |= set(out['ambiguous'])
        self.assertEqual(len(keys), EXPECTED_AMBIGUOUS)

    def test_this_task_has_no_finding(self):
        """TASK-022 AC10 and TASK-022 AC8: the module gives TASK-022 itself no finding, so each of its G2 criteria is named by
        one of its own tests."""
        out = self.out['TASK-022']
        self.assertEqual(out['findings'], [])
        self.assertEqual(ac_tests.listing_record('TASK-022', 'v1', out['findings'], 'test', 'deterministic_tool_local'),
                         None)

    def test_own_tests_name_their_criteria(self):
        """TASK-022 AC8: every test function of TASK-022's three test modules names TASK-022 criteria in its own
        docstring and names no other task's criterion in qualified form there."""
        own = [p for p in self.write_sets['TASK-022'] if p.startswith('tests/')]
        self.assertEqual(len(own), 3)
        for path in own:
            for part, name, doc in ac_tests._tests(ac_tests.ast.parse(self.tests[path])):
                with self.subTest(test=path + '::' + part):
                    qualified, bare, names_task = ac_tests._mentions(name, doc)
                    self.assertTrue(qualified)
                    self.assertEqual({t for t, _ in qualified}, {'TASK-022'})


if __name__ == '__main__':
    unittest.main()

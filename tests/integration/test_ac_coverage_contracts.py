"""Integration test of aieos_bootstrap.ac_coverage over the task contracts in the tree (TASK-021 AC10; decision D-515
C2): read only, with pathlib's read_bytes; the three fields are taken by this test's own line-based reader, not by the
module. A finding on an accepted contract is data: it is listed below with its source lines, it is not fixed by this
task and it reopens no acceptance."""

import pathlib
import re
import unittest

from aieos_bootstrap import ac_coverage

ROOT = pathlib.Path(__file__).resolve().parents[2]
TASKS = ['TASK-%03d' % n for n in range(1, 22)]
# The findings over TASK-001 to TASK-021, each with its source lines:
# - TASK-004 AC12 (docs/tasks/TASK-004.yaml line 222, the limits criterion) is named by neither the G2 args (line 271)
#   nor the G3 args (line 272).
EXPECTED = {'TASK-004': [('uncovered', 'AC12')]}
_TOP = re.compile(r'^([a-z_]+):(.*)$')
_AC = re.compile(r'^  - (AC[0-9]+[a-z]?): ')
_GATE = re.compile(r'^  - \{gate: (G[0-9]+), check: ([a-z_]+)(?:, args: \[(.*)\])?\}$')


def read_contract(text):
    """acceptance_criteria, verification_plan and constitution of a contract's text, as values; every non-empty line
    of the plan must be a gate line."""
    out = {'acceptance_criteria': [], 'verification_plan': [], 'constitution': None}
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
    return out


class ContractsOnMain(unittest.TestCase):

    def test_reader(self):
        text = ('constitution: [INV-001, SEC-001]\nacceptance_criteria:\n  - AC1: >-\n      text\n  - AC2: x\n'
                'verification_plan:\n  - {gate: G0, check: scope}\n  - {gate: G2, check: tests, args: [AC1]}\n'
                'exit_conditions:\n  success: x\n')
        self.assertEqual(read_contract(text), {
            'acceptance_criteria': [{'AC1': '>-'}, {'AC2': 'x'}],
            'verification_plan': [{'gate': 'G0', 'check': 'scope'}, {'gate': 'G2', 'check': 'tests', 'args': ['AC1']}],
            'constitution': ['INV-001', 'SEC-001']})
        with self.assertRaises(ValueError):
            read_contract('verification_plan:\n  - gate G0\n')

    def test_the_contracts(self):
        found = {}
        for task in TASKS:
            with self.subTest(task=task):
                values = read_contract((ROOT / 'docs' / 'tasks' / (task + '.yaml')).read_bytes().decode('utf-8'))
                self.assertTrue(values['acceptance_criteria'])
                self.assertTrue(values['verification_plan'])
                self.assertIsNotNone(values['constitution'])
                out = ac_coverage.check(values)
                self.assertNotIn('malformed', [f['kind'] for f in out])
                if out:
                    found[task] = [(f['kind'], f['ref']) for f in out]
        self.assertEqual(found, EXPECTED)

    def test_this_tasks_own_contract_is_covered(self):
        values = read_contract((ROOT / 'docs' / 'tasks' / 'TASK-021.yaml').read_bytes().decode('utf-8'))
        self.assertEqual([next(iter(a)) for a in values['acceptance_criteria']], ['AC%d' % n for n in range(1, 13)])
        self.assertEqual(ac_coverage.check(values), [])


if __name__ == '__main__':
    unittest.main()

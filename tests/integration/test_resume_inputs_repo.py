"""Integration tests of aieos_bootstrap.resume_inputs over this repository's history (TASK-085 AC8): fixed commits,
read only, gitread.run as read; the log is b"". The repository must hold the full history, as
tests/integration/test_base_inputs_repo.py needs. Each test names its criteria in its own docstring."""

import pathlib
import unittest

from aieos_bootstrap import resume_inputs

ROOT = str(pathlib.Path(__file__).resolve().parents[2])
HEAD = 'bd0df8b6689815bdec446979fdb74fe419f78740'
BASE = '80934ee51e923a7a0a9785948d46da5c332ab332'
C = 'e3afc15d96ca46ebffcd37460c21d3d93d76656d'
RECORDS = '156351eab2a1d9a0076f07ced0acfd279367b9b6'
CODE = '6efa8d70d35e10791284439c2525ee8287a0a492'
TASK = 'TASK-084'
CONTRACT_HASH = '9aa14f2af34e1446599361e177d4280b020f527ce1fc3649d6061455244fd807'
TEST_FILE = 'tests/unit/test_execution_list_tasks.py'


class TASK085AC8Repository(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value, cls.findings = resume_inputs.git_inputs(ROOT, HEAD, TASK, b'')

    def test_found(self):
        """TASK-085 AC8: git_inputs at bd0df8b6 for TASK-084 gives a value, base_commit from its contract."""
        self.assertIsNone(self.findings, self.findings)
        self.assertEqual(self.value['head_commit'], HEAD)
        self.assertEqual(self.value['contract']['input_state']['base_commit'], BASE)
        self.assertIs(self.value['base_is_ancestor'], True)

    def test_commits(self):
        """TASK-085 AC8: the four commits after base_commit, oldest first, with their exact paths and changes."""
        self.assertIsNone(self.findings, self.findings)
        self.assertEqual(self.value['commits'], [
            {'id': C, 'paths': [{'path': 'docs/tasks/TASK-084.yaml', 'change': 'added'}], 'submitted': False},
            {'id': RECORDS, 'paths': [
                {'path': 'docs/Deferred/DEF-0099-list-tasks-does-not-re-check-a-tasks-dependencies.md',
                 'change': 'added'},
                {'path': 'docs/records/TASK-084.jsonl', 'change': 'added'}], 'submitted': False},
            {'id': CODE, 'paths': [{'path': 'src/aieos_bootstrap/execution.py', 'change': 'modified'},
                                   {'path': TEST_FILE, 'change': 'added'}], 'submitted': False},
            {'id': HEAD, 'paths': [{'path': TEST_FILE, 'change': 'modified'}], 'submitted': False}])

    def test_contract_hash_symbols_and_derived(self):
        """TASK-085 AC8: the literal contract_hash, the four symbols equal at both commits, the derived read-set."""
        self.assertIsNone(self.findings, self.findings)
        self.assertEqual(self.value['contract_hash'], CONTRACT_HASH)
        symbols = self.value['symbols']
        self.assertEqual(len(symbols), 4)
        for s in symbols:
            self.assertIsNotNone(s['head'], s['interface'])
            self.assertEqual(s['base'], s['head'], s['interface'])
        self.assertEqual(self.value['derived_read_set'], ['src/aieos_bootstrap/records.py',
                                                          'src/aieos_bootstrap/resume_check.py',
                                                          'src/aieos_bootstrap/writer.py'])
        self.assertEqual(self.value['schemas'], [])


if __name__ == '__main__':
    unittest.main()

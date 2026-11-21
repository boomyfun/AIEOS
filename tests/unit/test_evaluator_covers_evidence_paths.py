"""E7 (TASK-156): every entry of EVIDENCE_DEFINING_PATHS is matched by both embedded EVALUATOR lists of the CI workflow.

The CI step GOV-003 reads the evaluator paths from the base's workflow (scope_reconcile.evaluator_from_workflow). A change to a file that
defines what evidence is, but is not matched by that list, would not be read as an evaluator change. This test turns the claim "the lists
cover what the reader needs" (D-6896 F5, D-6888 C4) into a check, and it catches a later drift between the reader's list and the workflow.
"""

import pathlib
import re
import unittest

from aieos_bootstrap import evaluation_policy
from aieos_bootstrap import governor
from aieos_bootstrap import scope_reconcile

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / '.github' / 'workflows' / 'aieos-checks.yml'
ADDED = ('docs/pre-genesis/assurance-model.md', 'docs/pre-genesis/decision-matrix.md', 'docs/pre-genesis/governor-spec.md',
         'docs/specs/evaluation-policy-gov-aieos.md')


def uncovered(paths, evaluator):
    return [p for p in paths if not any(governor.matches(pat, p) for pat in evaluator)]


class EvaluatorCoversEvidencePathsTests(unittest.TestCase):
    def test_every_evidence_defining_path_is_matched(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        evaluator = scope_reconcile.evaluator_from_workflow(text)
        self.assertNotEqual(evaluator, [], 'the two EVALUATOR literals differ or are not read')
        self.assertEqual(uncovered(evaluation_policy.EVIDENCE_DEFINING_PATHS, evaluator), [])

    def test_the_two_literals_each_hold_the_four_added_entries(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        blocks = re.findall(r'(?m)^ +EVALUATOR = \[.*?\]$', text, re.S)
        self.assertEqual(len(blocks), 2)
        for block in blocks:
            for p in ADDED:
                self.assertIn("'" + p + "'", block, p)

    def test_the_check_finds_a_missing_entry(self):
        self.assertEqual(uncovered(['docs/pre-genesis/decision-matrix.md'], ['docs/**/x.md', 'src/aieos_bootstrap/**']), ['docs/pre-genesis/decision-matrix.md'])
        self.assertEqual(uncovered(['src/aieos_bootstrap/governor.py'], ['src/aieos_bootstrap/**']), [])
        self.assertEqual(uncovered(['docs/pre-genesis/decision-matrix.md'], ['docs/pre-genesis/decision-matrix.md']), [])

    def test_the_four_added_paths_are_entries_of_the_reader_list(self):
        for p in ADDED:
            self.assertIn(p, evaluation_policy.EVIDENCE_DEFINING_PATHS)


if __name__ == '__main__':
    unittest.main()

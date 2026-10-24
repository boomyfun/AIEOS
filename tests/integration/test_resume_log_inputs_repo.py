"""Integration tests of aieos_bootstrap.resume_log_inputs over this repository's history (TASK-088 AC9): a fixed
commit, read only, gitread.run as read; the log is b"". The repository must hold the full history, as
tests/integration/test_resume_inputs_repo.py needs. Each test names its criteria in its own docstring."""

import pathlib
import re
import unittest

from aieos_bootstrap import base_files, resume_log_inputs

ROOT = str(pathlib.Path(__file__).resolve().parents[2])
COMMIT = 'ed4d482e42396f0ec0b2a447a1b3b43174051f36'
TASK = 'TASK-085'
INTENTS = {
    'docs/specs/spec-07-cli-and-zero-friction-path.md':
        '613cbd72dca411586ca03d790cd01bb044d0eb8e9a2885d9c3f8bb25cc9f5efb',
    'docs/specs/spec-06-mcp-protocol-and-work-orders.md':
        'd2fa59ae3f203b3a2108e55d23ddfb875e64ab57d27372c9d413bf30d7c2cbdd',
    'docs/specs/spec-05-adapter-contract.md': 'ae7b99419d303db40b7200e39a22d93b9301b29900f3b1f5a5720b72d8eb9c2b',
    'docs/specs/spec-01-state-and-event-model.md': '98ea939aa6f4664137c31325e2c01bb72d5056dbec427ca37aa1e5ef038e41e0',
    'docs/specs/spec-02-aieos-file-format.md': '8e744daa31928621137db59a8a9d91ecf163879420e1f8e148232b149cafcdb7',
    'docs/specs/spec-03-resume-check-and-decision-engine.md':
        '50fa28795bb4145266d76bf345a7d8de28cdecbda2a20b18fdd32c324f86c92e',
    'docs/pre-genesis/constitution.md': '9b396c3c0f31d3a3fbccf9433cf81eb820b6e0f0a3a7d099e2899043abfe1f5a',
    'docs/pre-genesis/assurance-model.md': '945615316968a5c064bf88be71add9271bbb9f95692eaa22582b6020fa69cb85',
    'docs/specs/risk-rules-gov-aieos.md': '29dd803aed6a55c11fad04d01dac32ee10a8f15f96f099857a00212c100d4ed5',
    'docs/pre-genesis/governor-spec.md': '423a1f3743b124bab7e672f7be5615e18f2a178d9b9991587d5aaa9f6ea37cea'}
DEPENDENCIES = ('TASK-008', 'TASK-081', 'TASK-082')


class TASK088AC9Repository(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value, cls.findings = resume_log_inputs.log_inputs(ROOT, COMMIT, TASK, b'')

    def test_intent_current(self):
        """TASK-088 AC9: log_inputs at ed4d482e for TASK-085 with the log b"" gives intent_current equal to
        TASK-085.yaml's intent_versions for all ten entities (the hashes ivhash88 confirmed, D-2587)."""
        self.assertIsNone(self.findings, self.findings)
        self.assertEqual(self.value['intent_current'], INTENTS)

    def test_articles(self):
        """TASK-088 AC9: the articles' ids are exactly the constitution's headings at ed4d482e, in order, INV-001
        first."""
        self.assertIsNone(self.findings, self.findings)
        text = base_files.read_file(ROOT, COMMIT, 'docs/pre-genesis/constitution.md')[0]['text']
        headings = re.findall(r'^### ([A-Z]+-[0-9]+) · ', text, re.M)
        self.assertEqual([a['id'] for a in self.value['articles']], headings)
        self.assertEqual(headings[0], 'INV-001')

    def test_risk_rules_and_version(self):
        """TASK-088 AC9: twelve rules, the second (R2) a paths rule as the policy writes it and the third (R3)
        {match: {paths: [src/**, tests/**]}, risk: high}; policy_version "v4"."""
        self.assertIsNone(self.findings, self.findings)
        rules = self.value['risk_rules']
        self.assertEqual(len(rules), 12)
        self.assertEqual(rules[1], {'match': {'paths': ['src/**', 'tests/**']}, 'risk': 'medium'})
        self.assertEqual(rules[2], {'match': {'paths': ['src/**', 'tests/**']}, 'risk': 'high'})
        self.assertEqual(self.value['policy_version'], 'v4')

    def test_dependencies_and_budget_use(self):
        """TASK-088 AC9: with the empty log, each of TASK-085's three dependencies has state null (read as {state:
        null, stale_evidence: false}, D-2626 C2), and budget_use retries is {used: 0, reported: true}."""
        self.assertIsNone(self.findings, self.findings)
        self.assertEqual(self.value['dependencies'],
                         {d: {'state': None, 'stale_evidence': False} for d in DEPENDENCIES})
        self.assertEqual(self.value['budget_use']['retries'], {'used': 0, 'reported': True})


if __name__ == '__main__':
    unittest.main()

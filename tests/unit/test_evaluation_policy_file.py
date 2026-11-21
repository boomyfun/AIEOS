"""Tests of the committed evaluation policy file docs/specs/evaluation-policy-gov-aieos.md (TASK-154, BT3c-2; D-6915 to D-6925).

The expected data below are written out in this file (made once from the reader's output on the pinned text, not read from the file under test). The three owner values are the owner's own answer "1 không, 2 có, 3 có" (main transcript of session dc7cf6ca-d094-4438-af81-93586ed7658b, line 37957); no row of the decision matrix records it (GOV-005).
"""

import hashlib
import pathlib
import unittest

from aieos_bootstrap import eval_inputs
from aieos_bootstrap import evaluation_policy
from aieos_bootstrap import governor

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = 'docs/specs/evaluation-policy-gov-aieos.md'
PIN = 'e4af5f1b6688611a022298f9e8e32855097b4cc9865e9e4d6ce6364c3ce53e32'
ANSWER = '"1 không, 2 có, 3 có"'
KEYS = ('owner_kept_rules', 'articles', 'default_profiles', 'requirement_profiles', 'delegation', 'auto_accept')
ARTICLES = [{'id': 'INV-001', 'scope': ['src/**'], 'evidence_required': ['ai_review']},
 {'id': 'INV-002', 'scope': ['src/aieos_bootstrap/**'], 'evidence_required': ['ai_review']},
 {'id': 'INV-003', 'scope': ['src/aieos_bootstrap/**'], 'evidence_required': ['human_review']},
 {'id': 'INV-004', 'scope': ['.aieos/**', 'src/**'], 'evidence_required': ['ai_review']},
 {'id': 'INV-005', 'scope': ['src/aieos_bootstrap/**'], 'evidence_required': ['property_test']},
 {'id': 'INV-006', 'scope': ['src/aieos_bootstrap/**'], 'evidence_required': ['property_test']},
 {'id': 'INV-007',
  'scope': ['src/aieos_bootstrap/**', '.aieos/**', 'docs/records/**'],
  'evidence_required': ['property_test']},
 {'id': 'INV-008', 'scope': ['src/aieos_bootstrap/**'], 'evidence_required': ['property_test']},
 {'id': 'GOV-003',
  'scope': ['.github/**',
            'src/aieos_bootstrap/**',
            'tests/conformance/**',
            'docs/pre-genesis/conformance-scenarios-initial.md',
            'docs/records/**',
            'docs/specs/risk-rules-gov-aieos.md',
            'docs/pre-genesis/constitution.md',
            'docs/tasks/**',
            '.aieos/tasks/**',
            'tests/unit/**',
            'tests/integration/**',
            'tests/property/**',
            'tests/run_tests.py',
            '**/Pipfile',
            '**/Pipfile.lock',
            '**/poetry.lock',
            '**/uv.lock',
            '**/constraints*.txt',
            '**/MANIFEST.in',
            '**/tox.ini',
            '**/pytest.ini',
            '**/conftest.py',
            '**/.python-version',
            '**/pyproject.toml',
            '**/setup.cfg',
            '**/setup.py',
            '**/requirements*.txt',
            '**/go/**',
            '**/rust/**',
            '**/ts/**',
            '**/go.mod',
            '**/go.sum',
            '**/Cargo.lock',
            '**/Cargo.toml',
            '**/tsconfig.json',
            '**/package-lock.json',
            'docs/pre-genesis/assurance-model.md',
            'docs/pre-genesis/decision-matrix.md',
            'docs/pre-genesis/governor-spec.md',
            'docs/specs/evaluation-policy-gov-aieos.md'],
  'evidence_required': ['ai_review']},
 {'id': 'GOV-004', 'scope': ['**'], 'evidence_required': ['human_review']},
 {'id': 'GOV-005', 'scope': ['docs/**'], 'evidence_required': ['human_review']},
 {'id': 'GOV-006', 'scope': ['docs/pre-genesis/decision-matrix.md'], 'evidence_required': ['human_review']},
 {'id': 'SEC-002', 'scope': ['**'], 'evidence_required': ['ai_review']},
 {'id': 'OPS-002', 'scope': ['**'], 'evidence_required': ['human_review']},
 {'id': 'OPS-003', 'scope': ['docs/**', '.aieos/**'], 'evidence_required': ['ai_review']}]
PROFILES = {'low': [{'dimension': 'functional', 'evidence_types': ['build', 'lint']}],
 'medium': [{'dimension': 'functional', 'evidence_types': ['unit_test']},
            {'dimension': 'architecture', 'evidence_types': ['deterministic_rule']}],
 'high': [{'dimension': 'functional', 'evidence_types': ['unit_test']},
          {'dimension': 'architecture', 'evidence_types': ['deterministic_rule']},
          {'dimension': 'functional', 'evidence_types': ['integration_test']},
          {'dimension': 'security', 'evidence_types': ['static_security_analysis']},
          {'dimension': 'architecture', 'evidence_types': ['ai_review (cross-model)']}],
 'critical': [{'dimension': 'functional', 'evidence_types': ['unit_test']},
              {'dimension': 'architecture', 'evidence_types': ['deterministic_rule']},
              {'dimension': 'functional', 'evidence_types': ['integration_test']},
              {'dimension': 'security', 'evidence_types': ['static_security_analysis']},
              {'dimension': 'architecture', 'evidence_types': ['ai_review (cross-model)']},
              {'dimension': 'architecture', 'evidence_types': ['human_review']},
              {'dimension': 'functional', 'evidence_types': ['property_test']}]}


def raw():
    return (ROOT / PATH).read_bytes()


def read():
    return evaluation_policy.read_evaluation_policy(raw().decode('utf-8'))


class AC1TheFile(unittest.TestCase):
    def test_the_file_has_exactly_the_pinned_bytes(self):
        self.assertEqual(hashlib.sha256(raw()).hexdigest(), PIN)

    def test_the_text_is_utf8_with_lf_line_ends_and_no_candidate_wording(self):
        data = raw()
        text = data.decode('utf-8')
        self.assertNotIn(b'\r', data)
        self.assertNotIn('NOT DECIDED', text)
        self.assertNotIn('CANDIDATE', text)
        self.assertNotIn('decided by the owner', text)


class AC2TheReaderAcceptsIt(unittest.TestCase):
    def test_present_without_findings_and_no_source_is_open(self):
        out = read()
        self.assertEqual(out['result'], 'present')
        self.assertEqual(out['findings'], [])
        self.assertEqual(tuple(out['sources']), KEYS)
        for key in KEYS:
            self.assertIsNotNone(out['sources'][key], key)


class AC3TheOwnerValues(unittest.TestCase):
    def test_the_values(self):
        src = read()['sources']
        self.assertEqual(src['owner_kept_rules'], [{'match': ['docs/pre-genesis/measurement-protocol.md', 'docs/pre-genesis/measurements/**']}])
        self.assertIs(src['delegation'], True)
        self.assertEqual(src['auto_accept'], {'low': False, 'medium': False, 'high': False, 'critical': False})

    def test_no_owner_rule_matches_the_github_folder(self):
        for rule in read()['sources']['owner_kept_rules']:
            for pattern in rule['match']:
                self.assertFalse(pattern.startswith('.github'), pattern)

    def test_the_three_comment_lines_cite_the_owner_answer_and_the_transcript_line(self):
        lines = raw().decode('utf-8').split('\n')
        for head in ('# owner_kept_rules:', '# delegation:', '# auto_accept:'):
            hit = [x for x in lines if x.startswith(head)]
            self.assertEqual(len(hit), 1, head)
            self.assertIn(ANSWER, hit[0])
            self.assertIn('line 37957', hit[0])
            self.assertIn('given by', hit[0])


class AC4TheArticlesAndProfiles(unittest.TestCase):
    def test_the_articles(self):
        arts = read()['sources']['articles']
        self.assertEqual(arts, ARTICLES)
        self.assertEqual([a['id'] for a in arts], ['INV-001', 'INV-002', 'INV-003', 'INV-004', 'INV-005', 'INV-006', 'INV-007', 'INV-008', 'GOV-003', 'GOV-004', 'GOV-005', 'GOV-006', 'SEC-002', 'OPS-002', 'OPS-003'])
        for a in arts:
            self.assertTrue(a['scope'], a['id'])
        self.assertEqual(len([a for a in arts if a['id'] == 'GOV-003'][0]['scope']), 40)

    def test_the_default_profiles_and_the_requirement_profiles(self):
        src = read()['sources']
        self.assertEqual(src['default_profiles'], PROFILES)
        self.assertEqual({k: len(v) for k, v in src['default_profiles'].items()}, {'low': 1, 'medium': 2, 'high': 5, 'critical': 7})
        self.assertEqual(src['requirement_profiles'], [])


class AC5TheMeetingWithTheGovernorAndThePaths(unittest.TestCase):
    def test_the_six_sources_are_accepted_by_derive_inputs(self):
        src = read()['sources']
        values = {
            'contract': {'traces_to': ['SPEC-001'], 'risk': 'low', 'owner_kept_act': False, 'verification_plan': ['G1']},
            'changed_paths': ['src/aieos_bootstrap/x.py'],
            'risk_rules': [{'match': ['src/**'], 'class': 'medium'}],
            'owner_kept_rules': src['owner_kept_rules'], 'articles': src['articles'], 'default_profiles': src['default_profiles'],
            'requirement_profiles': src['requirement_profiles'], 'delegation': src['delegation'], 'evidence_comparison': {'weakens': False},
            'auto_accept': src['auto_accept'], 'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1'}
        self.assertEqual(set(values), governor.VALUE_KEYS)
        out = governor.derive_inputs(values)
        self.assertEqual(out['risk'], 'medium')
        self.assertIs(out['delegation_in_force'], True)
        self.assertIs(out['auto_accept'], False)
        ids = [a['id'] for a in out['applicable_articles']]
        self.assertIn('INV-001', ids)
        self.assertIn('GOV-003', ids)

    def test_the_policy_path_is_still_a_policy_path_of_eval_inputs(self):
        self.assertIn(PATH, eval_inputs._POLICY_PATHS)
        self.assertIn(PATH, evaluation_policy.EVIDENCE_DEFINING_PATHS)


if __name__ == '__main__':
    unittest.main()

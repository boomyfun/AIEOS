"""Property tests of aieos_bootstrap.verification_records (task TASK-029), standard library only, with fixed seeds.

For random changed paths and policies: the risk_class value is never lower than any matching rule's class, equals the
highest of them, and is null exactly when some path matches no rule; and random audit copies, well formed or bound to
another commit, never change governor.evaluate's decision value. Each test names its criteria in its own docstring."""

import random
import unittest

from aieos_bootstrap import governor, records, verification_records as vr

SEEDS = (1, 2, 3, 5, 8, 13, 21, 34)
ROUNDS = 25
PATHS = ['src/x.py', 'src/y.py', 'tests/t.py', 'docs/a.md', 'docs/specs/s.md', 'README.md']
PATTERNS = ['src/**', 'tests/**', 'docs/**', 'docs/specs/**', '*.md', 'src/x.py']
CLASSES = ('low', 'medium', 'high', 'critical')
TASK = 'TASK-500'
IV = {'SPEC-001': 'v2'}
HASH = 'c' * 64


def commit(rng):
    return ''.join(rng.choice('0123456789abcdef') for _ in range(40))


def random_values(rng):
    rules = [{'id': 'R%d' % i, 'match': rng.sample(PATTERNS, rng.randint(1, 2)), 'class': rng.choice(CLASSES)}
             for i in range(rng.randint(0, 4))]
    paths = rng.sample(PATHS, rng.randint(1, 4))
    return {
        'contract': {'traces_to': ['SPEC-001'], 'risk': rng.choice(CLASSES), 'owner_kept_act': False,
                     'verification_plan': ['G0', 'G1']},
        'changed_paths': paths, 'risk_rules': rules, 'owner_kept_rules': [], 'articles': [],
        'default_profiles': {c: [{'dimension': 'functional', 'evidence_types': ['build']}] for c in CLASSES},
        'requirement_profiles': [], 'delegation': True, 'evidence_comparison': {'weakens': False}, 'auto_accept': {},
        'policy_version': 'v%d' % rng.randint(1, 9), 'level_version': 'v1', 'ruleset_version': 'v1',
    }


def coverage():
    return {'acceptance_criteria': [{'AC1': 'one'}], 'verification_plan': [{'gate': 'G2', 'check': 'tests', 'args': ['AC1']}],
            'constitution': []}


class RiskClass(unittest.TestCase):

    def test_the_value_is_the_highest_matching_class_or_null(self):
        """TASK-029 AC2, AC11: never lower than a matching rule's class; null exactly when a path matches no rule."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                v = random_values(rng)
                c = commit(rng)
                risk = vr.build_records(TASK, 'v1', c, dict(IV), v, coverage(), 'core')[0]
                self.assertEqual(records.check_record(risk), [])
                per_path = []
                for p in v['changed_paths']:
                    hits = [r['class'] for r in v['risk_rules'] if any(governor.matches(m, p) for m in r['match'])]
                    per_path.append(max(hits, key=CLASSES.index) if hits else None)
                if any(x is None for x in per_path):
                    self.assertIsNone(risk['risk_class'], (seed, v))
                else:
                    self.assertEqual(risk['risk_class'], max(per_path, key=CLASSES.index), (seed, v))


def gov_records(rng, c):
    out = []
    for i, (gate, kind, dim) in enumerate((('G0', 'scope_check', 'scope'), ('G1', 'build', 'functional'))):
        if rng.random() < 0.8:
            out.append({'record_id': 'g%d' % i, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_external_ci',
                        'recorder': 'ci', 'subject': TASK, 'commit': c, 'intent_versions': dict(IV),
                        'outcome': rng.choice(('pass', 'pass', 'fail')), 'gate': gate, 'evidence_type': kind,
                        'dimension': dim})
    return out


class Decision(unittest.TestCase):

    def test_audit_copies_never_change_the_decision(self):
        """TASK-029 AC8, AC11: random well-formed or earlier-commit copies never change the decision value."""
        inputs = {'traces_to': ['SPEC-001'], 'risk': 'low', 'owner_kept_act': False, 'weakens_evidence': False,
                  'delegation_in_force': True, 'auto_accept': False, 'verification_plan': ['G0', 'G1'],
                  'evidence_profile': [{'dimension': 'functional', 'evidence_types': ['build']}],
                  'applicable_articles': [], 'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1'}
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                c = commit(rng)
                request = {'task_id': TASK, 'task_content_hash': HASH, 'evaluated_commit': c,
                           'intent_versions': dict(IV), 'task_state': rng.choice(('VERIFYING', 'IN_REVIEW')),
                           'changed_paths': ['src/x.py'], 'retry_count': {'used': rng.randint(0, 2), 'limit': 2}}
                rs = gov_records(rng, c)
                base = governor.evaluate(request, inputs, rs)
                at = rng.choice((c, commit(rng)))
                extra = vr.build_records(TASK, 'v1', at, dict(IV), random_values(rng), coverage(), 'core')
                got = governor.evaluate(request, inputs, rs + extra)
                for key in ('decision', 'next_task_state', 'table_row', 'profile_used', 'missing_gates', 'blocking',
                            'failed_gates', 'approval_record'):
                    self.assertEqual(got[key], base[key], (seed, key))


if __name__ == '__main__':
    unittest.main()

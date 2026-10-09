"""Property tests of the bootstrap governor of TASK-004 (AC13): random cases from the standard library's random module
with fixed seeds, built in memory; nothing is read or written.
"""
import copy
import random
import unittest

from aieos_bootstrap import governor

COMMIT, OTHER = 'a' * 40, 'b' * 40
HASH = 'c' * 64
TASK = 'TASK-700'
DECISIONS = {'ACCEPT', 'NEEDS_REVIEW', 'INSUFFICIENT_EVIDENCE', 'NEEDS_REWORK', 'REJECT'}
DIMS = ('functional', 'security', 'architecture', 'operational')
KINDS = ('build', 'unit_test', 'static_security_analysis', 'human_review', 'ai_review', 'ai_review (cross-model)')
CLASSES = ('deterministic_tool_external_ci', 'deterministic_tool_local', 'agent_declared', 'same_lineage_review',
           'decision_agent', 'human_authority')
SEEDS = range(300)


def make(rng):
    req = {'task_id': TASK, 'task_content_hash': HASH, 'evaluated_commit': COMMIT, 'intent_versions': {'S-1': 'v1'},
           'task_state': rng.choice(['VERIFYING', 'IN_REVIEW']), 'changed_paths': ['src/a.py'],
           'retry_count': {'used': rng.randrange(4), 'limit': 2}}
    profile = [{'dimension': d, 'evidence_types': rng.sample(KINDS, rng.randrange(1, 3))}
               for d in rng.sample(DIMS, rng.randrange(1, 4))]
    inp = {'traces_to': ['S-1'], 'risk': rng.choice(['low', 'medium', 'high', 'critical']),
           'owner_kept_act': rng.random() < 0.3, 'weakens_evidence': rng.random() < 0.2,
           'delegation_in_force': rng.random() < 0.6, 'auto_accept': rng.random() < 0.3,
           'verification_plan': ['G0', 'G1'], 'evidence_profile': profile, 'applicable_articles': [],
           'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1'}
    recs = []
    for n in range(rng.randrange(1, 10)):
        cls = rng.choice(CLASSES)
        r = {'record_id': 'r%d' % n, 'fact_kind': 'observation', 'source_class': cls, 'recorder': 'x', 'subject': TASK,
             'commit': COMMIT if rng.random() < 0.85 else OTHER, 'intent_versions': {'S-1': 'v1'},
             'dimension': rng.choice(DIMS), 'outcome': rng.choice(['pass', 'pass', 'pass', 'fail'])}
        pick = rng.random()
        if cls == 'decision_agent' and pick < 0.5:
            r.update(evidence_type='decision_agent_review', decision_ref='D-1', basis='read',
                     stands_for=rng.choice(['human_review', 'ai_review (cross-model)']))
        elif cls == 'decision_agent' or (cls == 'human_authority' and pick < 0.5):
            r = {'record_id': r['record_id'], 'fact_kind': 'authority', 'source_class': cls, 'recorder': 'x',
                 'subject': TASK, 'approval_binding': {'kind': 'acceptance', 'hash': HASH}}
            if cls == 'decision_agent':
                r['decision_ref'] = 'D-2'
        elif cls == 'same_lineage_review':
            r.update(evidence_type='other_model_review', decision_ref='D-3',
                     models={'reviewer': rng.choice(['m-a', 'm-b']), 'implementer': 'm-a'})
        else:
            r['evidence_type'] = rng.choice(KINDS[:4])
        if rng.random() < 0.15:
            r['gate'] = rng.choice(['G0', 'G1'])
        recs.append(r)
    return req, inp, recs


def satisfied(out):
    return {(p['dimension'], t) for p in out['profile_used'] for t in p['required'] if t not in p['missing_types']}


def used_ids(out):
    return {i for p in out['profile_used'] for i in p['satisfied_by']}


class GovernorProperties(unittest.TestCase):
    def test_the_same_arguments_give_the_same_record(self):
        for seed in SEEDS:
            req, inp, recs = make(random.Random(seed))
            before = copy.deepcopy((req, inp, recs))
            first = governor.evaluate(req, inp, recs)
            self.assertEqual((req, inp, recs), before)
            self.assertEqual(governor.evaluate(copy.deepcopy(req), copy.deepcopy(inp), copy.deepcopy(recs)), first)

    def test_a_decision_outside_the_five_never_appears(self):
        for seed in SEEDS:
            out = governor.evaluate(*make(random.Random(seed)))
            self.assertIn(out['decision'], DECISIONS)

    def test_an_agent_declared_record_never_satisfies_a_missing_entry(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            req, inp, recs = make(rng)
            out = governor.evaluate(req, inp, recs)
            extra = [{'record_id': 'decl-%d' % n, 'fact_kind': 'observation', 'source_class': 'agent_declared',
                      'recorder': 'the implementing agent', 'subject': TASK, 'commit': COMMIT,
                      'intent_versions': {'S-1': 'v1'}, 'dimension': d, 'evidence_type': t, 'outcome': 'pass'}
                     for n, (d, t) in enumerate((p['dimension'], t) for p in inp['evidence_profile']
                                                for t in p['evidence_types'])]
            self.assertEqual(satisfied(governor.evaluate(req, inp, recs + extra)), satisfied(out), seed)

    def test_a_stale_record_never_satisfies(self):
        for seed in SEEDS:
            req, inp, recs = make(random.Random(seed))
            for r in recs:
                if 'commit' in r:
                    r['commit'] = OTHER
            out = governor.evaluate(req, inp, recs)
            self.assertEqual(used_ids(out), set(), seed)

    def test_no_decision_agent_record_counts_without_the_delegation(self):
        for seed in SEEDS:
            req, inp, recs = make(random.Random(seed))
            inp['delegation_in_force'] = False
            out = governor.evaluate(req, inp, recs)
            agent = {r['record_id'] for r in recs if r['source_class'] == 'decision_agent'}
            self.assertFalse(used_ids(out) & agent, seed)
            self.assertNotIn(out['approval_record'], agent)


if __name__ == '__main__':
    unittest.main()

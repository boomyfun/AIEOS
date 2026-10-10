"""Unit tests of the decision.execution keys of aieos_bootstrap.records (TASK-011 AC8): rules R1 to R3, each with a
passing and a failing case, all in memory. R4 (AC4) is the existing test modules, run unchanged by tests/run_tests.py.
"""

import unittest

from aieos_bootstrap import records

H64 = 'a' * 64
C40 = 'b' * 40
NEW_KEYS = ('contract_hash', 'contract_version', 'base_commit', 'head_commit', 'log_seq', 'delta', 'checks',
            'outcomes_fired', 'read_set', 'signatures', 'intent_versions', 'dependencies', 'constitution', 'runtime',
            'budgets', 'policy_version', 'engine_identity', 'uncovered', 'state_effect')


def checks(fired=None):
    """Eight check entries; ``fired`` maps a check number to its outcome."""
    fired = fired or {}
    return [{'check': n, 'status': 'fired' if n in fired else 'passed', 'outcome': fired.get(n), 'detail': ''}
            for n in range(1, 9)]


def execution(**changes):
    """A decision.execution payload with every key of specification 3 section 9 that breaks no rule; ``changes`` set
    (or, with None, remove) keys."""
    p = {'record_id': 'exe-1', 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_local',
         'recorder': 'the Resume Check', 'subject': 'TASK-008', 'decision': 'CONTINUE', 'contract_hash': H64,
         'contract_version': 'v1', 'base_commit': C40, 'head_commit': C40, 'log_seq': 0, 'delta': [],
         'checks': checks(), 'outcomes_fired': [], 'read_set': {'entries': [], 'estimate': True},
         'signatures': [], 'intent_versions': {'SPEC-003': {'contract': 'v4', 'current': 'v4'}},
         'dependencies': {}, 'constitution': {}, 'runtime': {}, 'budgets': {}, 'policy_version': 'v1',
         'engine_identity': {'code_sha256': None, 'python': '3.12.4'}, 'uncovered': [], 'state_effect': []}
    for key, value in changes.items():
        if value is None:
            p.pop(key, None)
        else:
            p[key] = value
    return p


def rules(event_type, payload):
    return [f.rule for f in records.check_decision(event_type, payload)]


class R1Keys(unittest.TestCase):
    def test_every_new_key_is_allowed_for_decision_execution(self):
        self.assertEqual(rules('decision.execution', execution()), [])

    def test_none_of_the_new_keys_is_required(self):
        for key in NEW_KEYS:
            self.assertEqual(rules('decision.execution', execution(**{key: None})), [], key)

    def test_an_error_record_with_only_record_keys_passes(self):
        p = {'record_id': 'exe-2', 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_local',
             'recorder': 'r', 'subject': 'TASK-008', 'decision': None, 'error': 'the contract is missing'}
        self.assertEqual(rules('decision.execution', p), [])

    def test_other_keys_stay_unknown_for_decision_execution(self):
        for key in ('next_task_state', 'x_other', 'profile_used'):
            p = execution()
            p[key] = 'DONE'
            self.assertIn('6.4:unknown_key', rules('decision.execution', p), key)

    def test_the_new_keys_stay_unknown_for_decision_acceptance(self):
        base = {'record_id': 'a-1', 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_external_ci',
                'recorder': 'g', 'subject': 'TASK-001', 'decision': 'ACCEPT'}
        self.assertEqual(rules('decision.acceptance', base), [])
        for key in NEW_KEYS:
            if key in records.ACCEPTANCE_KEYS or key in records.RECORD_KEYS:
                continue
            p = dict(base)
            p[key] = execution()[key]
            self.assertIn('6.4:unknown_key', rules('decision.acceptance', p), key)

    def test_the_new_keys_stay_unknown_for_record_added(self):
        rec = {'record_id': 'r-1', 'fact_kind': 'observation', 'source_class': 'deterministic_tool_external_ci',
               'recorder': 'ci', 'subject': 'TASK-001'}
        self.assertEqual([f.rule for f in records.check_payload('record.added', rec)], [])
        for key in ('log_seq', 'checks', 'engine_identity', 'state_effect'):
            p = dict(rec)
            p[key] = execution()[key]
            self.assertIn('6.2:unknown_key', [f.rule for f in records.check_payload('record.added', p)], key)


class R2Forms(unittest.TestCase):
    BAD = {
        'base_commit': 'abc', 'head_commit': 'B' * 40, 'log_seq': -1, 'contract_hash': 'a' * 63,
        'contract_version': '1', 'policy_version': '', 'delta': {}, 'signatures': 'x', 'uncovered': None,
        'state_effect': {}, 'read_set': [], 'dependencies': 'x', 'constitution': [], 'runtime': 1, 'budgets': [],
    }

    def test_each_checked_form_good_and_bad(self):
        for key, value in self.BAD.items():
            p = execution()
            p[key] = value
            self.assertIn('6.4:' + key, rules('decision.execution', p), key)
        self.assertEqual(rules('decision.execution', execution(log_seq=7, policy_version=None)), [])

    def test_log_seq_is_not_a_boolean(self):
        self.assertIn('6.4:log_seq', rules('decision.execution', execution(log_seq=True)))

    def test_engine_identity(self):
        self.assertEqual(rules('decision.execution', execution(engine_identity={'code_sha256': H64,
                                                                              'python': '3.11.0'})), [])
        for value in ({'code_sha256': None}, {'code_sha256': None, 'python': '3.11.0', 'x': 1},
                      {'code_sha256': 'A' * 64, 'python': '3.11.0'}, {'code_sha256': None, 'python': '3.11'},
                      {'code_sha256': None, 'python': 3}, H64, None):
            p = execution()
            p['engine_identity'] = value
            self.assertIn('6.4:engine_identity', rules('decision.execution', p), value)

    def test_checks(self):
        self.assertEqual(rules('decision.execution', execution(decision='REPLAN', outcomes_fired=['REPLAN'],
                                                               checks=checks({4: 'REPLAN'}))), [])
        broken = [checks()[:7], checks() + [checks()[0]],
                  [dict(c, check=1) for c in checks()],
                  [dict(c, status='done') if c['check'] == 2 else c for c in checks()],
                  [dict(c, outcome='REPLAN') if c['check'] == 2 else c for c in checks()],
                  [dict(c, status='fired') if c['check'] == 2 else c for c in checks()],
                  [dict(c, outcome='ACCEPT', status='fired') if c['check'] == 2 else c for c in checks()],
                  [dict(c, detail=None) if c['check'] == 2 else c for c in checks()],
                  [dict(c, check=True) if c['check'] == 1 else c for c in checks()],
                  [dict(c, extra=1) if c['check'] == 3 else c for c in checks()],
                  'eight']
        for value in broken:
            p = execution()
            p['checks'] = value
            self.assertIn('6.4:checks', rules('decision.execution', p), value)

    def test_outcomes_fired_order_and_first_value(self):
        good = execution(decision='STOP: scope invalid', outcomes_fired=['STOP: scope invalid', 'ESCALATE', 'REPLAN'])
        self.assertEqual(rules('decision.execution', good), [])
        for decision, fired in (('REPLAN', ['REPLAN', 'ESCALATE']),
                                ('ESCALATE', ['ESCALATE', 'ESCALATE']),
                                ('CONTINUE', ['CONTINUE']),
                                ('ESCALATE', ['REPLAN']),
                                ('CONTINUE', ['REPLAN']),
                                ('REPLAN', [])):
            self.assertIn('6.4:outcomes_fired', rules('decision.execution', execution(decision=decision,
                                                                                        outcomes_fired=fired)),
                          (decision, fired))

    def test_an_error_record_with_outcomes_fired_is_not_held_to_the_first_value(self):
        p = execution(error='no log', outcomes_fired=['REPLAN'])
        p['decision'] = None
        self.assertEqual(rules('decision.execution', p), [])


class R3IntentVersions(unittest.TestCase):
    def test_section_9_form_accepted_for_decision_execution(self):
        for iv in ({}, {'SPEC-003': {'contract': 'v4', 'current': None}},
                   {'docs/specs/x.md': {'contract': 'a' * 64, 'current': 'b' * 64}}):
            self.assertEqual(rules('decision.execution', execution(intent_versions=iv)), [], iv)

    def test_record_form_still_accepted_for_decision_execution(self):
        self.assertEqual(rules('decision.execution', execution(intent_versions={'SPEC-003': 'v4'})), [])

    def test_neither_form_refused_for_decision_execution(self):
        for iv in ({'SPEC-003': '4'}, {'SPEC-003': {'contract': 'v4'}}, {'': {'contract': 'v4', 'current': 'v4'}},
                   {'SPEC-003': {'contract': '', 'current': 'v4'}}, ['SPEC-003'], {'SPEC-003': 'v4', 'B': {}}):
            self.assertIn('6.4:intent_versions', rules('decision.execution', execution(intent_versions=iv)), iv)

    def test_record_form_still_required_elsewhere(self):
        rec = {'record_id': 'r-1', 'fact_kind': 'observation', 'source_class': 'deterministic_tool_external_ci',
               'recorder': 'ci', 'subject': 'TASK-001', 'intent_versions': {'SPEC-012': 'v3'}}
        self.assertEqual([f.rule for f in records.check_record(rec)], [])
        rec['intent_versions'] = {'SPEC-012': {'contract': 'v3', 'current': 'v3'}}
        self.assertIn('6.2:intent_versions', [f.rule for f in records.check_record(rec)])
        self.assertIn('6.2:intent_versions', [f.rule for f in records.check_payload('record.added', rec)])
        acc = {'record_id': 'a-1', 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_external_ci',
               'recorder': 'g', 'subject': 'TASK-001', 'decision': 'ACCEPT',
               'intent_versions': {'SPEC-012': {'contract': 'v3', 'current': 'v3'}}}
        self.assertIn('6.2:intent_versions', rules('decision.acceptance', acc))

    def test_the_record_rules_still_apply_to_the_record_keys(self):
        self.assertIn('6.2:fact_kind', rules('decision.execution', execution(fact_kind='guess')))
        self.assertIn('6.2:missing_key', rules('decision.execution', execution(recorder=None)))
        self.assertIn('6.4:subject', rules('decision.execution', execution(subject='TASK-008a')))


if __name__ == '__main__':
    unittest.main()

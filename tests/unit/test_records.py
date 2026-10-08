"""Unit tests of aieos_bootstrap.records (TASK-001 AC9): each rule of AC1 to AC7 with a passing and a failing case."""

import json
import unittest

from aieos_bootstrap import records

H64 = 'a' * 64
C40 = 'b' * 40
TIME = '2026-10-09T01:02:03Z'


def rec(**changes):
    """A record of section 6.2 that breaks no rule; ``changes`` set (or, with None, remove) keys."""
    r = {'record_id': 'rec-1', 'fact_kind': 'observation', 'source_class': 'deterministic_tool_external_ci',
         'recorder': 'ci', 'subject': 'TASK-001'}
    for key, value in changes.items():
        if value is None:
            r.pop(key, None)
        else:
            r[key] = value
    return r


def decision(kind='acceptance', **changes):
    d = rec(fact_kind='interpretation', decision='ACCEPT' if kind == 'acceptance' else 'CONTINUE')
    if kind == 'acceptance':
        d['next_task_state'] = 'ACCEPTED'
        d['profile_used'] = [{'dimension': 'architecture', 'required': ['unit_test'], 'satisfied_by': ['rec-1'],
                              'missing_types': []}]
    for key, value in changes.items():
        if value is None:
            d.pop(key, None)
        else:
            d[key] = value
    return d


def event(seq, etype, payload, **extra):
    e = {'event_id': 'ev-%d' % seq, 'type': etype, 'appended_at': TIME, 'seq': seq, 'payload': payload}
    e.update(extra)
    return e


def log_of(*events):
    return ''.join(json.dumps(e) + '\n' for e in events)


def rules(report):
    return sorted({f.rule for _, f in report.findings()})


def drafted(seq=1, **extra):
    extra.setdefault('task_id', 'TASK-001')
    return event(seq, 'task.drafted', {'contract_version': 'v1', 'contract_hash': H64}, **extra)


class LineForm(unittest.TestCase):
    """AC1."""

    def test_clean_line(self):
        r = records.check_log(log_of(drafted()))
        self.assertEqual(r.findings(), [])
        self.assertEqual(r.lines[0].event['type'], 'task.drafted')
        self.assertIn('no error found', r.describe())

    def test_bom_and_cr(self):
        self.assertEqual(records.check_log(log_of(drafted())).text_findings, ())
        r = records.check_log(b'\xef\xbb\xbf' + log_of(drafted()).encode())
        self.assertIn('2:bom', rules(r))
        r = records.check_log(log_of(drafted()).replace('\n', '\r\n'))
        self.assertIn('2:cr', rules(r))

    def test_utf8(self):
        r = records.check_log(b'{"event_id": "\xff"}\n')
        self.assertEqual(rules(r), ['6.1:utf8'])
        self.assertIsNone(r.lines[0].event)

    def test_not_one_object(self):
        for text in ('[1, 2]\n', 'not json\n', '{"a": 1} {"b": 2}\n', '\n', '{"seq": NaN}\n', '{"a": 1, "a": 2}\n'):
            with self.subTest(text=text):
                self.assertIn('6.1:json', rules(records.check_log(text)))

    def test_required_and_unknown_keys(self):
        e = drafted()
        del e['payload']
        self.assertIn('6.1:missing_key', rules(records.check_log(log_of(e))))
        self.assertIn('2:unknown_key', rules(records.check_log(log_of(drafted(note='x')))))

    def test_event_id_type_payload(self):
        self.assertIn('6.1:event_id', rules(records.check_log(log_of(drafted(event_id='')))))
        e = drafted()
        e['type'] = 'task.invented'
        self.assertIn('6.1:type', rules(records.check_log(log_of(e))))
        e = drafted()
        e['payload'] = [1]
        self.assertIn('6.1:payload', rules(records.check_log(log_of(e))))

    def test_last_empty_line_is_not_a_line(self):
        self.assertEqual(len(records.check_log(log_of(drafted())).lines), 1)
        self.assertEqual(len(records.check_log('').lines), 0)


class OrderTimeDuplicates(unittest.TestCase):
    """AC2."""

    def test_seq(self):
        self.assertEqual(rules(records.check_log(log_of(drafted(1), drafted(2, event_id='ev-x')))), [])
        self.assertIn('6.1:seq', rules(records.check_log(log_of(drafted(2)))))
        self.assertIn('6.1:seq', rules(records.check_log(log_of(drafted(1), drafted(3, event_id='ev-x')))))
        e = drafted()
        e['seq'] = True
        self.assertIn('6.1:seq', rules(records.check_log(log_of(e))))

    def test_appended_at(self):
        for good in ('2026-10-09T01:02:03Z', '2024-02-29T23:59:59.123456Z'):
            self.assertEqual(rules(records.check_log(log_of(drafted(appended_at=good)))), [], good)
        for bad in ('2026-10-09 01:02:03Z', '2026-10-09T01:02:03', '2026-02-30T00:00:00Z', '2026-10-09T24:00:00Z',
                    '2026-10-09T01:02:03+00:00', 20261009):
            self.assertIn('6.1:appended_at', rules(records.check_log(log_of(drafted(appended_at=bad)))), bad)

    def test_identical_repeat_is_an_ignored_duplicate(self):
        first = drafted(1)
        again = drafted(2, event_id='ev-1', appended_at='2026-10-09T05:00:00Z')
        r = records.check_log(log_of(first, again))
        self.assertEqual(r.findings(), [])
        self.assertEqual(r.lines[1].duplicate_of, 1)
        self.assertIn('ignored duplicate of line 1', r.lines[1].describe())

    def test_repeat_with_other_content_is_an_error(self):
        other = drafted(2, event_id='ev-1')
        other['payload'] = {'contract_version': 'v2', 'contract_hash': H64}
        r = records.check_log(log_of(drafted(1), other))
        self.assertIn('6.1:duplicate_event_id', rules(r))
        self.assertIsNone(r.lines[1].duplicate_of)

    def test_duplicate_counts_for_seq(self):
        again = drafted(2, event_id='ev-1')
        third = drafted(3, event_id='ev-3')
        self.assertEqual(rules(records.check_log(log_of(drafted(1), again, third))), [])


class ConditionalKeys(unittest.TestCase):
    """AC3."""

    def test_task_id(self):
        e = drafted()
        del e['task_id']
        self.assertIn('6.1:task_id', rules(records.check_log(log_of(e))))
        self.assertIn('6.1:task_id', rules(records.check_log(log_of(drafted(task_id='T-1')))))
        added = event(1, 'record.added', rec(), task_id='TASK-002')
        self.assertIn('6.1:task_id', rules(records.check_log(log_of(added))))
        self.assertEqual(rules(records.check_log(log_of(event(1, 'record.added', rec(), task_id='TASK-001')))), [])
        about_entity = rec(subject='SPEC-012.1')
        self.assertEqual(rules(records.check_log(log_of(event(1, 'record.added', about_entity)))), [])
        self.assertIn('6.1:task_id', rules(records.check_log(log_of(event(1, 'record.added', about_entity, task_id='TASK-001')))))

    def test_fencing(self):
        submitted = {'commit': C40, 'compensating': False}
        good = event(1, 'task.submitted', submitted, task_id='TASK-001', fencing_token={'epoch': 'e1', 'counter': 0})
        self.assertEqual(rules(records.check_log(log_of(good))), [])
        good_int = event(1, 'task.submitted', submitted, task_id='TASK-001', fencing_token={'epoch': 7, 'counter': 3})
        self.assertEqual(rules(records.check_log(log_of(good_int))), [])
        missing = event(1, 'task.submitted', submitted, task_id='TASK-001')
        self.assertIn('6.1:fencing_token', rules(records.check_log(log_of(missing))))
        for fence in ({'epoch': '', 'counter': 1}, {'epoch': 'e', 'counter': -1}, {'epoch': 'e', 'counter': True},
                      {'epoch': 'e'}, {'epoch': 'e', 'counter': 1, 'x': 1}, ['e', 1]):
            bad = event(1, 'task.submitted', submitted, task_id='TASK-001', fencing_token=fence)
            self.assertIn('6.1:fencing_token', rules(records.check_log(log_of(bad))), fence)
        other = drafted(fencing_token={'epoch': 'e1', 'counter': 2})
        self.assertEqual(rules(records.check_log(log_of(other))), [])

    def test_corrects(self):
        fix = drafted(2, event_id='ev-2', corrects='ev-1')
        self.assertEqual(rules(records.check_log(log_of(drafted(1), fix))), [])
        wrong = drafted(2, event_id='ev-2', corrects='ev-9')
        self.assertIn('6.1:corrects', rules(records.check_log(log_of(drafted(1), wrong))))


class Records(unittest.TestCase):
    """AC4."""

    def check(self, r):
        return sorted({f.rule for f in records.check_record(r)})

    def test_clean_record(self):
        self.assertEqual(self.check(rec()), [])

    def test_keys(self):
        self.assertIn('6.2:unknown_key', self.check(rec(colour='red')))
        for key in records.RECORD_REQUIRED:
            self.assertIn('6.2:missing_key', self.check(rec(**{key: None})), key)
        self.assertIn('6.2:record', self.check([1]))

    def test_vocabularies(self):
        self.assertIn('6.2:fact_kind', self.check(rec(fact_kind='opinion')))
        self.assertIn('6.2:source_class', self.check(rec(source_class='someone')))
        self.assertIn('6.2:outcome', self.check(rec(outcome='maybe')))
        self.assertEqual(self.check(rec(outcome='blocking', blocking_kind='violation')), [])
        self.assertIn('6.2:blocking_kind', self.check(rec(outcome='blocking')))
        self.assertIn('6.2:blocking_kind', self.check(rec(outcome='fail', blocking_kind='violation')))
        self.assertIn('6.2:blocking_kind', self.check(rec(outcome='blocking', blocking_kind='mood')))

    def test_bindings(self):
        self.assertEqual(self.check(rec(commit=C40, intent_versions={'SPEC-012': 'v3'})), [])
        self.assertIn('6.2:commit', self.check(rec(commit='B' * 40)))
        self.assertIn('6.2:commit', self.check(rec(commit='abc123')))
        self.assertIn('6.2:intent_versions', self.check(rec(intent_versions={'SPEC-012': '3'})))
        auth = rec(fact_kind='authority', source_class='decision_agent', decision_ref='D-186',
                   approval_binding={'kind': 'contract', 'hash': H64})
        self.assertEqual(self.check(auth), [])
        self.assertIn('6.2:approval_binding', self.check(rec(fact_kind='authority')))
        self.assertIn('6.2:approval_binding', self.check(rec(fact_kind='authority',
                                                            approval_binding={'kind': 'gift', 'hash': H64})))

    def test_reviews(self):
        review = rec(source_class='same_lineage_review', evidence_type='other_model_review', decision_ref='D-188',
                     models={'reviewer': 'model-a', 'implementer': 'model-b'})
        self.assertEqual(self.check(review), [])
        no_ref = dict(review)
        del no_ref['decision_ref']
        self.assertIn('6.2:decision_ref', self.check(no_ref))
        self.assertIn('6.2:models', self.check(rec(evidence_type='other_model_review', decision_ref='D-188')))
        self.assertIn('6.2:decision_ref', self.check(rec(source_class='decision_agent')))
        dar = rec(source_class='decision_agent', evidence_type='decision_agent_review', decision_ref='D-188',
                  basis='read the diff', stands_for='human_review')
        self.assertEqual(self.check(dar), [])
        self.assertIn('6.2:basis', self.check(rec(source_class='decision_agent', evidence_type='decision_agent_review',
                                                  decision_ref='D-188', stands_for='human_review')))

    def test_open_vocabularies_and_gate(self):
        self.assertEqual(self.check(rec(evidence_type='unit_test', dimension='architecture', gate='G2')), [])
        self.assertIn('6.2:gate', self.check(rec(gate='gate-2')))
        self.assertIn('6.2:evidence_type', self.check(rec(evidence_type='')))


class Payloads(unittest.TestCase):
    """AC5."""

    def check(self, etype, payload):
        return sorted({f.rule for f in records.check_payload(etype, payload)})

    def test_each_simple_type(self):
        good = {
            'task.drafted': {'contract_version': 'v1', 'contract_hash': H64},
            'task.approved': {'contract_version': 'v1', 'contract_hash': H64, 'approval_record': 'rec-7'},
            'task.blocked': {'reason': 'waiting', 'blocked_by': ['TASK-002']},
            'task.unblocked': {'reason': 'free'},
            'task.submitted': {'commit': C40, 'compensating': False},
            'task.done': {'decision_record': 'rec-9'},
            'task.stale': {'cause': 'conflict', 'refers_to': 'ev-3'},
            'task.replanned': {'contract_version': 'v2', 'contract_hash': H64},
            'intent.changed': {'entity': 'SPEC-012.1', 'from_version': 'v1', 'to_version': 'v2',
                               'change_request': 'CHG-001'},
            'drift.detected': {'paths': ['src/a.py'], 'entities': ['ARC-auth']},
            'evidence.stale': {'records': ['rec-1'], 'reason': 'commit'},
            'conflict.detected': {'tasks': ['TASK-001', 'TASK-002'], 'paths': ['src/a.py']},
        }
        for etype, payload in good.items():
            with self.subTest(etype=etype):
                self.assertEqual(self.check(etype, payload), [])
                self.assertIn('6.3:unknown_key', self.check(etype, dict(payload, extra=1)))
                first = sorted(payload)[0]
                short = {k: v for k, v in payload.items() if k != first}
                self.assertTrue(self.check(etype, short))

    def test_forms(self):
        self.assertIn('6.3:contract_version', self.check('task.drafted', {'contract_version': '1', 'contract_hash': H64}))
        self.assertIn('6.3:contract_hash', self.check('task.drafted', {'contract_version': 'v1', 'contract_hash': 'x'}))
        self.assertIn('6.3:commit', self.check('task.submitted', {'commit': C40[:12], 'compensating': False}))
        self.assertIn('6.3:compensating', self.check('task.submitted', {'commit': C40, 'compensating': 'no'}))
        self.assertIn('6.3:cause', self.check('task.stale', {'cause': 'boredom', 'refers_to': 'ev-1'}))
        self.assertIn('6.3:reason', self.check('evidence.stale', {'records': [], 'reason': 'age'}))
        self.assertIn('6.3:change_request', self.check('intent.changed', {
            'entity': 'SPEC-1', 'from_version': 'v1', 'to_version': 'v2', 'change_request': 'CR-001'}))
        self.assertIn('6.3:blocked_by', self.check('task.blocked', {'reason': 'r', 'blocked_by': 'TASK-002'}))
        self.assertIn('6.3:missing_key', self.check('conflict.detected', {'tasks': ['TASK-001']}))
        self.assertEqual(self.check('conflict.detected', {'tasks': ['TASK-001'], 'interfaces': ['api']}), [])

    def test_record_payloads(self):
        self.assertEqual(self.check('record.added', rec()), [])
        self.assertIn('6.2:fact_kind', self.check('record.added', rec(fact_kind='x')))
        violation = rec(outcome='blocking', blocking_kind='violation')
        self.assertEqual(self.check('violation.detected', violation), [])
        self.assertIn('6.3:violation', self.check('violation.detected', rec(outcome='fail')))
        self.assertIn('6.3:type', self.check('task.invented', {}))
        self.assertIn('6.1:payload', self.check('task.done', 'rec-9'))


class Decisions(unittest.TestCase):
    """AC6."""

    def check(self, etype, payload):
        return sorted({f.rule for f in records.check_decision(etype, payload)})

    def test_acceptance(self):
        self.assertEqual(self.check('decision.acceptance', decision()), [])
        for value in records.ACCEPTANCE_DECISIONS:
            self.assertEqual(self.check('decision.acceptance', decision(decision=value)), [], value)
        self.assertIn('6.4:decision', self.check('decision.acceptance', decision(decision='CONTINUE')))
        self.assertIn('6.4:fact_kind', self.check('decision.acceptance', decision(fact_kind='observation')))
        self.assertIn('6.4:next_task_state', self.check('decision.acceptance', decision(next_task_state='Accepted')))
        self.assertIn('6.4:profile_used', self.check('decision.acceptance', decision(profile_used=[{'dimension': 'x'}])))
        self.assertIn('6.2:unknown_key', self.check('decision.acceptance', decision(verdict='yes')))
        self.assertEqual(self.check('decision.acceptance', decision(task_content_hash=H64, uncovered=[], rests_on_ai=[])), [])

    def test_null_exactly_with_error(self):
        d = decision()
        d['decision'] = None
        self.assertIn('6.4:error', self.check('decision.acceptance', d))
        d['error'] = 'malformed request'
        self.assertEqual(self.check('decision.acceptance', d), [])
        self.assertIn('6.4:error', self.check('decision.acceptance', decision(error='also an error')))
        no_decision = {k: v for k, v in decision().items() if k != 'decision'}
        self.assertIn('6.4:decision', self.check('decision.acceptance', no_decision))

    def test_execution(self):
        for value in records.EXECUTION_DECISIONS:
            self.assertEqual(self.check('decision.execution', decision('execution', decision=value)), [], value)
        self.assertIn('6.4:decision', self.check('decision.execution', decision('execution', decision='STOP')))
        self.assertIn('6.2:unknown_key', self.check('decision.execution', decision('execution', next_task_state='DONE')))

    def test_subject_and_task_id(self):
        self.assertIn('6.4:subject', self.check('decision.acceptance', decision(subject='SPEC-1')))
        e = event(1, 'decision.acceptance', decision())
        self.assertIn('6.1:task_id', rules(records.check_log(log_of(e))))
        e['task_id'] = 'TASK-001'
        self.assertEqual(rules(records.check_log(log_of(e))), [])


class Limits(unittest.TestCase):
    """AC7: form only; the results only say "no error found" or list findings."""

    def test_wording_of_results(self):
        r = records.check_log(log_of(drafted()))
        self.assertEqual(r.describe(), 'line 1: no error found\nno error found')
        for word in ('valid', 'accepted', 'approved', 'correct'):
            self.assertNotIn(word, r.describe().lower())
        bad = records.check_log(log_of(drafted(seq=5)))
        self.assertIn('6.1:seq', bad.describe())

    def test_names_are_not_resolved(self):
        done = event(1, 'task.done', {'decision_record': 'rec-that-does-not-exist'}, task_id='TASK-001')
        stale = event(2, 'task.stale', {'cause': 'conflict', 'refers_to': 'ev-404'}, task_id='TASK-001')
        self.assertEqual(rules(records.check_log(log_of(done, stale))), [])

    def test_no_state_transition_and_no_hash_recomputed(self):
        drafted_twice = log_of(drafted(1), drafted(2, event_id='ev-2'))
        self.assertEqual(rules(records.check_log(drafted_twice)), [])
        submitted_first = event(1, 'task.submitted', {'commit': C40, 'compensating': True}, task_id='TASK-001',
                                fencing_token={'epoch': 'e', 'counter': 99})
        self.assertEqual(rules(records.check_log(log_of(submitted_first))), [])

    def test_type_errors_never_raise(self):
        for value in (None, 1, 1.5, [], {}, True, 'x'):
            records.check_record(value)
            records.check_payload('record.added', value)
            records.check_decision('decision.execution', value)
        with self.assertRaises(TypeError):
            records.check_log(12)


if __name__ == '__main__':
    unittest.main()

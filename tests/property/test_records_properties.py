"""Property tests of aieos_bootstrap.records (TASK-001 AC9), standard library only, with fixed seeds.

General properties: generated well-formed logs give no finding; removing a required key, adding an unknown key or
breaking seq gives a finding that names it; the same input always gives the same output. Form properties for the
articles (TASK-001 AC9): INV-005 (decision values; decision null exactly when error is present), INV-007 (a malformed
commit or intent_versions is always reported) and INV-008 (a source_class outside DM B3 is always reported, and an
agent_declared record gets the same form result as any other class). INV-006 has no form property in this module.
"""

import json
import random
import string
import unittest

from aieos_bootstrap import records

SEEDS = (1, 2, 3, 5, 8, 13, 21, 34)
ROUNDS = 40
HEX = '0123456789abcdef'


def word(rng, n=8):
    return ''.join(rng.choice(string.ascii_lowercase) for _ in range(n))


def hex_of(rng, n):
    return ''.join(rng.choice(HEX) for _ in range(n))


def task_id(rng):
    return 'TASK-%03d' % rng.randint(0, 999)


def record(rng, subject=None):
    r = {'record_id': 'rec-' + word(rng), 'fact_kind': rng.choice(sorted(records.FACT_KINDS - {'authority'})),
         'source_class': rng.choice(sorted(records.SOURCE_CLASSES)), 'recorder': word(rng),
         'subject': subject or task_id(rng), 'decision_ref': 'D-%d' % rng.randint(1, 999)}
    if rng.random() < 0.5:
        r['commit'] = hex_of(rng, 40)
    if rng.random() < 0.5:
        r['intent_versions'] = {'SPEC-%03d' % rng.randint(0, 99): 'v%d' % rng.randint(1, 9)}
    if rng.random() < 0.5:
        r['outcome'] = rng.choice(['pass', 'fail'])
    return r


def payload(rng, etype, tid):
    if etype in ('record.added',):
        return record(rng, tid)
    if etype == 'violation.detected':
        return dict(record(rng, tid), fact_kind='observation', outcome='blocking', blocking_kind='violation')
    if etype == 'decision.acceptance':
        return dict(record(rng, tid), fact_kind='interpretation',
                    decision=rng.choice(sorted(records.ACCEPTANCE_DECISIONS)),
                    next_task_state=rng.choice(sorted(records.STATE_NAMES)))
    if etype == 'decision.execution':
        return dict(record(rng, tid), decision=rng.choice(sorted(records.EXECUTION_DECISIONS)))
    if etype == 'conflict.detected':
        return {'tasks': [tid, task_id(rng)], 'paths': ['src/' + word(rng) + '.py']}
    sample = {'contract_version': 'v%d' % rng.randint(1, 9), 'contract_hash': hex_of(rng, 64),
              'approval_record': 'rec-' + word(rng), 'reason': word(rng), 'blocked_by': [task_id(rng)],
              'commit': hex_of(rng, 40), 'compensating': rng.random() < 0.5, 'decision_record': 'rec-' + word(rng),
              'cause': rng.choice(['intent_change', 'conflict']), 'refers_to': 'ev-' + word(rng),
              'entity': 'SPEC-' + word(rng, 3), 'from_version': 'v1', 'to_version': 'v2',
              'change_request': 'CHG-%03d' % rng.randint(0, 999), 'paths': ['src/' + word(rng) + '.py'],
              'entities': ['ARC-' + word(rng, 4)], 'records': ['rec-' + word(rng)]}
    keys = records.PAYLOAD_FORMS[etype]
    out = {k: sample[k] for k in keys}
    if etype == 'evidence.stale':
        out['reason'] = rng.choice(['commit', 'intent_version'])
    return out


def well_formed_log(rng, n):
    events = []
    for seq in range(1, n + 1):
        etype = rng.choice(sorted(records.EVENT_TYPES))
        tid = task_id(rng)
        e = {'event_id': 'ev-%d-%s' % (seq, word(rng, 4)), 'type': etype, 'seq': seq, 'payload': payload(rng, etype, tid),
             'appended_at': '20%02d-%02d-%02dT%02d:%02d:%02dZ' % (rng.randint(0, 99), rng.randint(1, 12),
                                                                 rng.randint(1, 28), rng.randint(0, 23),
                                                                 rng.randint(0, 59), rng.randint(0, 59))}
        if etype.startswith(('task.', 'decision.')) or etype in ('record.added', 'violation.detected'):
            e['task_id'] = tid
        if etype == 'task.submitted' or rng.random() < 0.2:
            e['fencing_token'] = {'epoch': rng.choice([word(rng), rng.randint(0, 9)]), 'counter': rng.randint(0, 99)}
        events.append(e)
    return events


def text_of(events):
    return ''.join(json.dumps(e) + '\n' for e in events)


def rules_at(report, number):
    return {f.rule for n, f in report.findings() if n == number}


class GeneralProperties(unittest.TestCase):

    def test_well_formed_logs_give_no_finding(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                events = well_formed_log(rng, rng.randint(1, 12))
                report = records.check_log(text_of(events))
                self.assertEqual([(n, str(f)) for n, f in report.findings()], [], seed)

    def test_removing_a_required_key_is_named(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                events = well_formed_log(rng, rng.randint(1, 6))
                k = rng.randrange(len(events))
                key = rng.choice(records.ENVELOPE_REQUIRED)
                del events[k][key]
                report = records.check_log(text_of(events))
                found = [f for n, f in report.findings() if n == k + 1 and f.rule == '6.1:missing_key']
                self.assertTrue(any(repr(key) in f.detail for f in found), (seed, key))

    def test_adding_an_unknown_key_is_named(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                events = well_formed_log(rng, rng.randint(1, 6))
                k = rng.randrange(len(events))
                key = 'x_' + word(rng, 5)
                if rng.random() < 0.5:
                    events[k][key] = 1
                    rule = '2:unknown_key'
                else:
                    events[k]['payload'][key] = 1
                    rule = {'decision.acceptance': '6.2:unknown_key', 'decision.execution': '6.2:unknown_key',
                            'record.added': '6.2:unknown_key',
                            'violation.detected': '6.2:unknown_key'}.get(events[k]['type'], '6.3:unknown_key')
                report = records.check_log(text_of(events))
                found = [f for n, f in report.findings() if n == k + 1 and f.rule == rule]
                self.assertTrue(any(repr(key) in f.detail for f in found), (seed, key, rule))

    def test_breaking_seq_is_named(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                events = well_formed_log(rng, rng.randint(1, 6))
                k = rng.randrange(len(events))
                events[k]['seq'] += rng.choice([-3, -1, 1, 2, 10])
                report = records.check_log(text_of(events))
                self.assertIn('6.1:seq', rules_at(report, k + 1), seed)

    def test_same_input_same_output(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            events = well_formed_log(rng, 8)
            text = text_of(events)
            mangled = text.replace('"', "'", rng.randint(0, 5))
            for sample in (text, mangled, text.encode('utf-8')[:rng.randint(0, len(text))]):
                a = records.check_log(sample)
                b = records.check_log(sample)
                self.assertEqual(a.describe(), b.describe())
                self.assertEqual(a.findings(), b.findings())


class ArticleFormProperties(unittest.TestCase):

    def test_inv_005_decision_values(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                etype = rng.choice(sorted(records.DECISION_TYPES))
                allowed = records.ACCEPTANCE_DECISIONS if etype == 'decision.acceptance' else records.EXECUTION_DECISIONS
                d = payload(rng, etype, task_id(rng))
                value = rng.choice([word(rng), word(rng).upper(), 'accept', 'STOP', 1, True, ['ACCEPT'], {}])
                d['decision'] = value
                rule_names = {f.rule for f in records.check_decision(etype, d)}
                self.assertFalse(isinstance(value, str) and value in allowed)
                self.assertIn('6.4:decision', rule_names, (seed, value))

    def test_inv_005_null_exactly_with_error(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                etype = rng.choice(sorted(records.DECISION_TYPES))
                d = payload(rng, etype, task_id(rng))
                null = rng.random() < 0.5
                error = rng.random() < 0.5
                if null:
                    d['decision'] = None
                if error:
                    d['error'] = 'error: ' + word(rng)
                rule_names = {f.rule for f in records.check_decision(etype, d)}
                self.assertEqual('6.4:error' in rule_names, null != error, (seed, null, error))

    def test_inv_007_commit_and_intent_versions(self):
        breakers = [lambda r: r[:39], lambda r: r.upper(), lambda r: r + '0', lambda r: r[:7], lambda r: 7,
                    lambda r: 'g' + r[1:]]
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                r = record(rng)
                r['commit'] = rng.choice(breakers)(hex_of(rng, 40))
                self.assertIn('6.2:commit', {f.rule for f in records.check_record(r)}, (seed, r['commit']))
                r = record(rng)
                r['intent_versions'] = rng.choice([{'SPEC-1': '1'}, {'SPEC-1': 'V1'}, {'': 'v1'}, ['SPEC-1', 'v1'],
                                                   {'SPEC-1': 'v'}, {'SPEC-1': 1}, 'v1'])
                self.assertIn('6.2:intent_versions', {f.rule for f in records.check_record(r)}, (seed, r['intent_versions']))

    def test_inv_008_source_class(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                r = record(rng)
                r['source_class'] = rng.choice([word(rng), 'human', 'Decision_Agent', 'agent', '', None, 3])
                self.assertIn('6.2:source_class', {f.rule for f in records.check_record(r)}, (seed, r['source_class']))

    def test_inv_008_agent_declared_gets_the_same_form_result(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                r = record(rng)
                if rng.random() < 0.5:
                    r['gate'] = rng.choice(['G1', 'gate'])
                results = {}
                for cls in sorted(records.SOURCE_CLASSES):
                    results[cls] = sorted(str(f) for f in records.check_record(dict(r, source_class=cls)))
                for cls, result in results.items():
                    self.assertEqual(result, results['agent_declared'], (seed, cls))


if __name__ == '__main__':
    unittest.main()

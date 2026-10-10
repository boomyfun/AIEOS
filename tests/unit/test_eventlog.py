"""Unit tests of aieos_bootstrap.eventlog (TASK-007 AC12, rules R1 to R7), all in memory; every rule has at least one
passing case and one failing case."""

import datetime
import json
import unittest

from aieos_bootstrap import eventlog, records

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 10, 12, 0, 0, tzinfo=UTC)
H64 = '0123456789abcdef' * 4
C40 = 'fedcba9876543210fedcba9876543210fedcba98'
TASK = 'TASK-007'
TOKEN = {'epoch': 'store-1', 'counter': 3}
DRAFTED = {'contract_version': 'v1', 'contract_hash': H64}
SUBMITTED = {'commit': C40, 'compensating': False}


def lease(task_id=TASK, token=None, expires_at=None):
    return {'task_id': task_id, 'fencing_token': dict(TOKEN) if token is None else token,
            'expires_at': T0 + datetime.timedelta(hours=1) if expires_at is None else expires_at}


def ok(log, event_id, event_type='task.drafted', payload=None, **kw):
    """Append and require the result appended; returns the new log."""
    r = eventlog.append(log, event_type, DRAFTED if payload is None else payload, event_id, kw.pop('at', T0),
                        task_id=kw.pop('task_id', TASK), **kw)
    assert r.result == 'appended', r
    return r.log


def submit(log, event_id='ev-s', **kw):
    args = {'task_id': TASK, 'fencing_token': dict(TOKEN), 'lease': lease(), 'recorder': 'aieos-core',
            'record_id': 'rec-refusal-1'}
    at = kw.pop('at', T0)
    args.update(kw)
    return eventlog.append(log, 'task.submitted', SUBMITTED, event_id, at, **args)


class R1TheGivenLog(unittest.TestCase):

    def test_empty_log_is_extended(self):
        r = eventlog.append(b'', 'task.drafted', DRAFTED, 'ev-1', T0, task_id=TASK)
        self.assertEqual((r.result, r.reason, r.seq), ('appended', None, 1))

    def test_log_with_a_finding_is_refused(self):
        bad = b'{"event_id":"ev-1"}\n'
        r = eventlog.append(bad, 'task.drafted', DRAFTED, 'ev-2', T0, task_id=TASK)
        self.assertEqual((r.result, r.reason), ('refused', 'log'))
        self.assertIsNone(r.log)
        self.assertTrue(r.findings)

    def test_log_without_final_lf_is_refused(self):
        log = ok(b'', 'ev-1')
        r = eventlog.append(log[:-1], 'task.drafted', DRAFTED, 'ev-2', T0, task_id=TASK)
        self.assertEqual((r.result, r.reason), ('refused', 'log'))
        self.assertIn('2:lf: the log does not end with LF', r.findings)

    def test_log_with_a_cr_is_refused(self):
        log = ok(b'', 'ev-1')
        r = eventlog.append(log[:-1] + b'\r\n', 'task.drafted', DRAFTED, 'ev-2', T0, task_id=TASK)
        self.assertEqual((r.result, r.reason), ('refused', 'log'))

    def test_log_must_be_bytes(self):
        with self.assertRaises(TypeError):
            eventlog.append('', 'task.drafted', DRAFTED, 'ev-1', T0, task_id=TASK)

    def test_results_and_reasons_are_named(self):
        self.assertEqual(eventlog.RESULTS, ('appended', 'duplicate', 'refused'))
        self.assertEqual(eventlog.REASONS, ('log', 'conflict', 'event', 'log_after', 'fence'))


class R2Idempotency(unittest.TestCase):

    def setUp(self):
        self.log = ok(ok(b'', 'ev-1'), 'ev-2', 'task.approved',
                      {'contract_version': 'v1', 'contract_hash': H64, 'approval_record': 'rec-1'})
        self.log = submit(self.log, 'ev-3').log

    def test_same_event_is_a_duplicate_naming_its_seq(self):
        r = eventlog.append(self.log, 'task.drafted', DRAFTED, 'ev-1', T0 + datetime.timedelta(days=1), task_id=TASK)
        self.assertEqual((r.result, r.reason, r.seq, r.log, r.line), ('duplicate', None, 1, None, None))

    def test_duplicate_of_a_submission(self):
        r = submit(self.log, 'ev-3')
        self.assertEqual((r.result, r.seq), ('duplicate', 3))

    def test_different_payload_is_a_conflict(self):
        r = eventlog.append(self.log, 'task.drafted', {'contract_version': 'v2', 'contract_hash': H64}, 'ev-1', T0,
                            task_id=TASK)
        self.assertEqual((r.result, r.reason, r.seq, r.log), ('refused', 'conflict', 1, None))

    def test_different_type_is_a_conflict(self):
        r = eventlog.append(self.log, 'task.replanned', DRAFTED, 'ev-1', T0, task_id=TASK)
        self.assertEqual((r.result, r.reason, r.seq), ('refused', 'conflict', 1))

    def test_different_token_is_a_conflict(self):
        r = submit(self.log, 'ev-3', fencing_token={'epoch': 'store-1', 'counter': 4},
                   lease=lease(token={'epoch': 'store-1', 'counter': 4}))
        self.assertEqual((r.result, r.reason, r.seq), ('refused', 'conflict', 3))

    def test_different_task_id_is_a_conflict(self):
        r = eventlog.append(self.log, 'task.drafted', DRAFTED, 'ev-1', T0, task_id='TASK-008')
        self.assertEqual((r.result, r.reason), ('refused', 'conflict'))

    def test_true_and_one_are_not_the_same(self):
        log = ok(b'', 'ev-1', 'task.blocked', {'reason': 'r', 'blocked_by': ['TASK-001']})
        r = eventlog.append(log, 'task.blocked', {'reason': 'r', 'blocked_by': ['TASK-001'], 'x': True}, 'ev-1', T0,
                            task_id=TASK)
        self.assertEqual((r.result, r.reason), ('refused', 'conflict'))

    def test_a_new_event_id_is_appended(self):
        r = eventlog.append(self.log, 'task.drafted', DRAFTED, 'ev-4', T0, task_id=TASK)
        self.assertEqual((r.result, r.seq), ('appended', 4))


class R3TheLine(unittest.TestCase):

    def test_each_envelope_key_and_the_canonical_bytes(self):
        r = eventlog.append(b'', 'task.drafted', DRAFTED, 'ev-1', T0, task_id=TASK)
        want = ('{"appended_at":"2026-10-10T12:00:00Z","event_id":"ev-1","payload":{"contract_hash":"%s",'
                '"contract_version":"v1"},"seq":1,"task_id":"TASK-007","type":"task.drafted"}\n' % H64).encode('ascii')
        self.assertEqual(r.line, want)
        self.assertEqual(r.log, want)

    def test_optional_keys_only_when_given(self):
        log = ok(b'', 'ev-1')
        r = eventlog.append(log, 'task.drafted', DRAFTED, 'ev-2', T0, task_id=TASK, corrects='ev-1')
        obj = json.loads(r.line)
        self.assertEqual(obj['corrects'], 'ev-1')
        self.assertNotIn('fencing_token', obj)
        r2 = eventlog.append(log, 'intent.changed', {'entity': 'SPEC-002', 'from_version': 'v1', 'to_version': 'v2',
                                                      'change_request': 'CHG-001'}, 'ev-3', T0)
        self.assertNotIn('task_id', json.loads(r2.line))

    def test_time_is_utc_with_z_to_the_second(self):
        at = datetime.datetime(2026, 1, 2, 3, 4, 5, 678901, tzinfo=UTC)
        r = eventlog.append(b'', 'task.drafted', DRAFTED, 'ev-1', at, task_id=TASK)
        self.assertEqual(json.loads(r.line)['appended_at'], '2026-01-02T03:04:05Z')

    def test_time_without_zone_or_off_utc_is_refused(self):
        for at in (T0.replace(tzinfo=None), T0.astimezone(datetime.timezone(datetime.timedelta(hours=7))), '2026'):
            r = eventlog.append(b'', 'task.drafted', DRAFTED, 'ev-1', at, task_id=TASK)
            self.assertEqual((r.result, r.reason), ('refused', 'event'), at)

    def test_seq_after_an_ignored_duplicate(self):
        log = ok(b'', 'ev-1')
        repeat = json.loads(log)
        repeat['seq'] = 2  # the same event at the next seq: an ignored duplicate, counted by check_log
        log = log + json.dumps(repeat, sort_keys=True).encode('ascii') + b'\n'
        self.assertEqual(records.check_log(log).lines[1].duplicate_of, 1)
        self.assertFalse(records.check_log(log).findings())
        r = eventlog.append(log, 'task.drafted', DRAFTED, 'ev-2', T0, task_id=TASK)
        self.assertEqual((r.result, r.seq), ('appended', 3))
        r2 = eventlog.append(log, 'task.drafted', DRAFTED, 'ev-1', T0, task_id=TASK)
        self.assertEqual((r2.result, r2.seq), ('duplicate', 1))

    def test_corrects_known_and_unknown(self):
        log = ok(b'', 'ev-1')
        self.assertEqual(eventlog.append(log, 'task.drafted', DRAFTED, 'ev-2', T0, task_id=TASK,
                                         corrects='ev-1').result, 'appended')
        r = eventlog.append(log, 'task.drafted', DRAFTED, 'ev-2', T0, task_id=TASK, corrects='ev-9')
        self.assertEqual((r.result, r.reason), ('refused', 'event'))

    def test_payload_with_a_finding(self):
        r = eventlog.append(b'', 'task.drafted', {'contract_version': '1', 'contract_hash': H64}, 'ev-1', T0,
                            task_id=TASK)
        self.assertEqual((r.result, r.reason), ('refused', 'event'))
        self.assertTrue(any('contract_version' in f for f in r.findings))

    def test_unknown_type_empty_id_bad_task_id_bad_token(self):
        cases = [('task.unknown', 'ev-1', {'task_id': TASK}), ('task.drafted', '', {'task_id': TASK}),
                 ('task.drafted', 'ev-1', {'task_id': 'T-7'}),
                 ('task.drafted', 'ev-1', {'task_id': TASK, 'fencing_token': {'epoch': 'e'}, 'lease': lease(),
                                           'recorder': 'r', 'record_id': 'x'})]
        for etype, eid, kw in cases:
            r = eventlog.append(b'', etype, DRAFTED, eid, T0, **kw)
            self.assertEqual((r.result, r.reason), ('refused', 'event'), (etype, eid, kw))

    def test_payload_that_is_not_json(self):
        # table_row is an acceptance key whose value records does not check, so only the JSON writing refuses it.
        payload = {'record_id': 'rec-1', 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_local',
                   'recorder': 'governor', 'subject': TASK, 'decision': 'ACCEPT', 'table_row': float('nan')}
        self.assertEqual(records.check_payload('decision.acceptance', payload), [])
        r = eventlog.append(b'', 'decision.acceptance', payload, 'ev-1', T0, task_id=TASK)
        self.assertEqual((r.result, r.reason), ('refused', 'event'))
        self.assertTrue(any(f.startswith('6.1:json') for f in r.findings))

    def test_ascii_only_escapes(self):
        reason = chr(0x111) + chr(0xe3) + ' xong'  # Vietnamese text, built from code points so this source stays ASCII
        r = eventlog.append(b'', 'task.unblocked', {'reason': reason}, 'ev-1', T0, task_id=TASK)
        self.assertEqual(r.result, 'appended')
        self.assertTrue(all(b < 128 for b in r.line))
        self.assertIn(b'\\u0111', r.line)
        self.assertEqual(json.loads(r.line)['payload']['reason'], reason)


class R4TheWholeLog(unittest.TestCase):

    def test_a_rule_only_the_whole_log_check_refuses(self):
        # The envelope task_id rule (specification 2 section 6.1) is not restated by AC3: a task event without
        # task_id passes the event's own checks and is refused by the whole-log check.
        r = eventlog.append(b'', 'task.drafted', DRAFTED, 'ev-1', T0)
        self.assertEqual((r.result, r.reason, r.log), ('refused', 'log_after', None))
        self.assertTrue(any('task_id' in f for f in r.findings))

    def test_a_record_whose_subject_differs_from_task_id(self):
        rec = {'record_id': 'rec-1', 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
               'recorder': 'aieos-core', 'subject': 'TASK-008'}
        r = eventlog.append(b'', 'record.added', rec, 'ev-1', T0, task_id=TASK)
        self.assertEqual((r.result, r.reason), ('refused', 'log_after'))
        self.assertEqual(eventlog.append(b'', 'record.added', rec, 'ev-1', T0, task_id='TASK-008').result, 'appended')


class R5AppendOnly(unittest.TestCase):

    def test_prefix_and_one_line(self):
        log = ok(ok(b'', 'ev-1'), 'ev-2', corrects='ev-1')
        r = eventlog.append(log, 'task.drafted', DRAFTED, 'ev-3', T0, task_id=TASK)
        self.assertTrue(r.log.startswith(log))
        self.assertEqual(r.log[len(log):], r.line)
        self.assertEqual(r.line.count(b'\n'), 1)
        self.assertTrue(r.line.endswith(b'\n'))

    def test_a_correction_is_a_new_line(self):
        log = ok(b'', 'ev-1')
        r = eventlog.append(log, 'task.drafted', {'contract_version': 'v2', 'contract_hash': H64}, 'ev-2', T0,
                            task_id=TASK, corrects='ev-1')
        self.assertEqual(r.log[:len(log)], log)
        self.assertEqual(len(records.check_log(r.log).lines), 2)

    def test_nothing_is_returned_when_refused(self):
        log = ok(b'', 'ev-1')
        r = eventlog.append(log, 'task.drafted', DRAFTED, 'ev-1', T0, task_id='TASK-009')
        self.assertIsNone(r.log)
        self.assertIsNone(r.line)


class R6Fencing(unittest.TestCase):

    def setUp(self):
        self.log = ok(b'', 'ev-1')

    def assertFenced(self, r):
        self.assertEqual((r.result, r.reason, r.log, r.line), ('refused', 'fence', None, None))
        self.assertIsNotNone(r.record)

    def test_a_valid_lease(self):
        r = submit(self.log)
        self.assertEqual((r.result, r.seq), ('appended', 2))
        self.assertEqual(json.loads(r.line)['fencing_token'], TOKEN)

    def test_no_lease(self):
        self.assertFenced(submit(self.log, lease=None))

    def test_another_task(self):
        self.assertFenced(submit(self.log, lease=lease(task_id='TASK-008')))

    def test_another_token(self):
        self.assertFenced(submit(self.log, lease=lease(token={'epoch': 'store-1', 'counter': 2})))
        self.assertFenced(submit(self.log, lease=lease(token={'epoch': 'store-2', 'counter': 3})))
        self.assertFenced(submit(self.log, lease=lease(token={'epoch': 'store-1', 'counter': True})))

    def test_expiry_equal_to_and_before_the_time(self):
        self.assertFenced(submit(self.log, lease=lease(expires_at=T0)))
        self.assertFenced(submit(self.log, lease=lease(expires_at=T0 - datetime.timedelta(seconds=1))))

    def test_expiry_within_the_second_counts(self):
        at = T0 + datetime.timedelta(microseconds=500000)
        self.assertFenced(submit(self.log, at=at, lease=lease(expires_at=T0 + datetime.timedelta(microseconds=1))))

    def test_malformed_leases(self):
        for bad in ({'task_id': TASK}, dict(lease(), extra=1), [TASK], lease(expires_at=T0.replace(tzinfo=None) +
                                                                             datetime.timedelta(hours=1))):
            self.assertFenced(submit(self.log, lease=bad))

    def test_an_event_without_a_token_that_needs_none(self):
        r = eventlog.append(self.log, 'task.drafted', DRAFTED, 'ev-2', T0, task_id=TASK)
        self.assertEqual((r.result, r.record), ('appended', None))

    def test_task_submitted_without_a_token(self):
        r = eventlog.append(self.log, 'task.submitted', SUBMITTED, 'ev-2', T0, task_id=TASK, lease=lease(),
                            recorder='aieos-core', record_id='rec-r')
        self.assertFenced(r)

    def test_any_event_with_a_token_is_fenced(self):
        r = eventlog.append(self.log, 'task.blocked', {'reason': 'r', 'blocked_by': ['TASK-001']}, 'ev-2', T0,
                            task_id=TASK, fencing_token=dict(TOKEN), lease=lease(task_id='TASK-008'),
                            recorder='aieos-core', record_id='rec-r')
        self.assertFenced(r)

    def test_a_lease_event_naming_no_task_is_an_event_refusal(self):
        r = eventlog.append(self.log, 'task.submitted', SUBMITTED, 'ev-2', T0, fencing_token=dict(TOKEN),
                            lease=lease(), recorder='aieos-core', record_id='rec-r')
        self.assertEqual((r.result, r.reason, r.record), ('refused', 'event', None))

    def test_recorder_and_record_id_are_required_for_a_lease_event(self):
        for kw in ({'recorder': None}, {'record_id': ''}):
            with self.assertRaises(ValueError):
                submit(self.log, **kw)


class R7TheRefusalRecord(unittest.TestCase):

    def test_record_keys_and_values(self):
        r = submit(ok(b'', 'ev-1'), 'ev-s', lease=None)
        self.assertEqual(r.record, {'record_id': 'rec-refusal-1', 'fact_kind': 'observation',
                                    'source_class': 'deterministic_tool_local', 'recorder': 'aieos-core',
                                    'subject': TASK, 'evidence_type': 'refused_submission', 'outcome': 'fail',
                                    'refers_to': 'ev-s'})
        self.assertEqual(records.check_record(r.record), [])
        self.assertEqual(records.check_payload('record.added', r.record), [])

    def test_appending_the_record(self):
        log = ok(b'', 'ev-1')
        r = submit(log, 'ev-s', lease=None)
        r2 = eventlog.append(log, 'record.added', r.record, 'ev-r', T0, task_id=TASK)
        self.assertEqual((r2.result, r2.seq), ('appended', 2))
        self.assertFalse(records.check_log(r2.log).findings())
        self.assertNotIn(b'ev-s"', r2.log.split(b'\n')[0])

    def test_no_record_on_other_refusals(self):
        r = eventlog.append(b'', 'task.drafted', DRAFTED, '', T0, task_id=TASK)
        self.assertIsNone(r.record)


if __name__ == '__main__':
    unittest.main()

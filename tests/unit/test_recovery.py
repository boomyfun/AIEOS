"""Unit tests of aieos_bootstrap.recovery (TASK-009 AC12, rules R1 to R8), all in memory; every rule has at least one
passing case and one failing case."""

import ast
import copy
import datetime
import hashlib
import pathlib
import sys
import unittest

from aieos_bootstrap import eventlog, records, recovery

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
H64 = '0123456789abcdef' * 4
TASK = 'TASK-009'
OTHER = 'TASK-010'
TOKEN = {'epoch': 'store-1', 'counter': 3}
REC = 'the recovery (aieos_bootstrap.recovery)'
C1 = '1' * 40
C2 = '2' * 40
C3 = '3' * 40
DRAFTED = {'contract_version': 'v1', 'contract_hash': H64}
SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap' / 'recovery.py'


def msg(task=TASK, fence='store-1:3', head='Do the work'):
    lines = [head, '']
    if task is not None:
        lines.append('AIEOS-Task: %s' % task)
    if fence is not None:
        lines.append('AIEOS-Fence: %s' % fence)
    return '\n'.join(lines) + '\n'


def commit(cid, **kw):
    return {'commit': cid, 'message': msg(**kw)}


def lease(task_id=TASK, token=None, expires_at=None):
    return {'task_id': task_id, 'fencing_token': dict(TOKEN) if token is None else token,
            'expires_at': T0 + datetime.timedelta(hours=1) if expires_at is None else expires_at}


def base_log(*tasks):
    log = b''
    for t in tasks or (TASK,):
        for kind, payload in (('task.drafted', DRAFTED),
                              ('task.approved', dict(DRAFTED, approval_record='rec-%s' % t))):
            r = eventlog.append(log, kind, payload, '%s-%s' % (kind, t), T0 - datetime.timedelta(hours=2), task_id=t)
            assert r.result == 'appended', r
            log = r.log
    return log


def submitted(log, cid, task_id=TASK, token=None):
    tok = dict(TOKEN) if token is None else token
    r = eventlog.append(log, 'task.submitted', {'commit': cid, 'compensating': False}, 'sub-' + cid,
                        T0 - datetime.timedelta(minutes=30), task_id=task_id, fencing_token=tok,
                        lease=lease(task_id, tok), recorder=REC, record_id='refusal-' + cid)
    assert r.result == 'appended', r
    return r.log


def run(log=None, commits=(), leases=None, now=T0):
    return recovery.reconcile(base_log() if log is None else log, list(commits),
                              [lease()] if leases is None else leases, now, REC)


def kinds(r):
    return [(e['type'], e['task_id'], e['result']) for e in r.events]


class EntryTest(unittest.TestCase):  # R1 AC1
    def test_a_well_formed_call_returns_a_result(self):
        r = run(commits=[commit(C1)])
        self.assertIsInstance(r, recovery.RecoveryResult)
        self.assertEqual(r.findings, ())

    def test_argument_forms_are_refused_before_anything_is_decided(self):
        bad = [
            dict(log='text'), dict(commits='x'), dict(commits=[{'commit': C1}]),
            dict(commits=[{'commit': 'ABC', 'message': ''}]), dict(commits=[{'commit': C1, 'message': 3}]),
            dict(leases='x'), dict(leases=[{'task_id': TASK}]),
            dict(leases=[lease(expires_at=datetime.datetime(2026, 10, 11))]),
            dict(now=datetime.datetime(2026, 10, 11)), dict(recorder=''),
        ]
        for b in bad:
            args = dict(log=base_log(), commits=[], leases=[], now=T0, recorder=REC)
            args.update(b)
            with self.subTest(b=sorted(b)):
                with self.assertRaises((TypeError, ValueError)):
                    recovery.reconcile(**args)

    def test_a_damaged_log_is_never_extended(self):
        for damaged in (b'not json\n', base_log()[:-1]):
            with self.subTest(damaged=damaged[:12]):
                r = run(log=damaged, commits=[commit(C1)])
                self.assertEqual(r.log, damaged)
                self.assertEqual(r.events, ())
                self.assertTrue(r.findings and all(f.startswith('log: ') for f in r.findings))

    def test_the_arguments_are_not_changed(self):
        log = base_log()
        commits = [commit(C1), commit(C2)]
        leases = [lease(), lease(expires_at=T0)]
        before = (bytes(log), copy.deepcopy(commits), copy.deepcopy(leases))
        recovery.reconcile(log, commits, leases, T0, REC)
        self.assertEqual((log, commits, leases), before)


class TrailerTest(unittest.TestCase):  # R2 AC2
    def test_both_trailers(self):
        t, f = recovery.trailers(msg())
        self.assertEqual((t, f), ({'task': TASK, 'fence': {'epoch': 'store-1', 'counter': 3}}, []))

    def test_an_epoch_with_a_colon_takes_the_text_before_the_last(self):
        t, _ = recovery.trailers(msg(fence='a:b:7'))
        self.assertEqual(t['fence'], {'epoch': 'a:b', 'counter': 7})

    def test_each_absent(self):
        self.assertEqual(recovery.trailers(msg(task=None))[0], {'task': None, 'fence': {'epoch': 'store-1', 'counter': 3}})
        self.assertEqual(recovery.trailers(msg(fence=None))[0], {'task': TASK, 'fence': None})
        self.assertEqual(recovery.trailers('no trailers'), ({'task': None, 'fence': None}, []))

    def test_each_malformed(self):
        for m in (msg(task='task-9'), msg(fence='store-1'), msg(fence='store-1:x'), msg(fence=':3'),
                  msg(fence='store-1:-1')):
            with self.subTest(m=m):
                self.assertTrue(recovery.trailers(m)[1])

    def test_a_key_twice(self):
        m = msg() + 'AIEOS-Task: TASK-010\n'
        self.assertTrue(any('given 2 times' in f for f in recovery.trailers(m)[1]))

    def test_a_key_outside_the_last_paragraph_gives_a_finding(self):  # D-393 C2
        for m in ('Head\n\nAIEOS-Task: TASK-009\n\nCo-Authored-By: someone\n',
                  'Head\n\naieos-fence: store-1:3\n\nAIEOS-Task: TASK-009\n'):
            with self.subTest(m=m):
                findings = recovery.trailers(m)[1]
                self.assertTrue(any('outside the last paragraph' in f for f in findings), findings)

    def test_a_key_in_another_letter_case_gives_a_finding(self):  # D-393 C2
        for m in ('Head\n\naieos-task: TASK-009\n', 'Head\n\nAIEOS-Task: TASK-009\nAIEOS-FENCE: store-1:3\n'):
            with self.subTest(m=m):
                self.assertTrue(any('is not spelled' in f for f in recovery.trailers(m)[1]))

    def test_a_body_line_that_only_mentions_the_key_mid_line_gives_no_finding(self):
        m = 'Head\n\nThe commit carries "AIEOS-Task: TASK-009" in its trailer.\n\nAIEOS-Task: TASK-009\n'
        self.assertEqual(recovery.trailers(m), ({'task': TASK, 'fence': None}, []))

    def test_a_message_not_a_string(self):
        with self.assertRaises(TypeError):
            recovery.trailers(b'x')


class StepOneTest(unittest.TestCase):  # R3 AC3
    def test_a_held_unexpired_lease_gives_the_compensating_submission(self):
        r = run(commits=[commit(C1)])
        self.assertEqual(kinds(r), [('task.submitted', TASK, 'appended')])
        last = records.check_log(r.log).lines[-1].event
        self.assertEqual(last['payload'], {'commit': C1, 'compensating': True})
        self.assertEqual(last['fencing_token'], TOKEN)

    def assert_observation(self, r, cid=C1, task_id=TASK):
        self.assertEqual(kinds(r), [('record.added', task_id, 'appended')])
        last = records.check_log(r.log).lines[-1].event
        self.assertEqual(last['payload'], recovery.observation(cid, task_id, REC))
        self.assertEqual(last['task_id'], task_id)
        self.assertNotIn('fencing_token', last)

    def test_another_token_gives_the_observation(self):
        self.assert_observation(run(commits=[commit(C1, fence='store-1:4')]))

    def test_a_token_equal_in_counter_but_another_epoch_gives_the_observation(self):  # D-391 C4 (i)
        self.assert_observation(run(commits=[commit(C1, fence='store-2:3')]))

    def test_an_integer_epoch_is_another_token(self):
        self.assert_observation(run(commits=[commit(C1, fence='1:3')], leases=[lease(token={'epoch': 1, 'counter': 3})]))

    def test_a_lease_on_another_task_gives_the_observation(self):
        self.assert_observation(run(commits=[commit(C1)], leases=[lease(task_id=OTHER)]))

    def test_a_lease_still_in_the_store_but_expired_gives_the_observation(self):  # D-390 C2 (a), reading (t1)
        for at in (T0, T0 - datetime.timedelta(seconds=1)):
            with self.subTest(expires_at=at):
                r = run(commits=[commit(C1)], leases=[lease(expires_at=at)])
                self.assert_observation(r)
                self.assertEqual(len(r.expired), 1)

    def test_a_lost_store_gives_the_observation(self):
        self.assert_observation(run(commits=[commit(C1)], leases=[]))

    def test_no_fence_gives_the_observation(self):
        self.assert_observation(run(commits=[commit(C1, fence=None)]))

    def test_a_malformed_trailer_gives_a_finding_and_no_event(self):
        r = run(commits=[commit(C1, fence='bad')])
        self.assertEqual(r.events, ())
        self.assertTrue(any(C1 in f for f in r.findings))

    def test_a_misplaced_or_miscased_key_gives_a_finding_and_no_event(self):  # D-393 C3
        for m in ('Work\n\nAIEOS-Task: TASK-009\nAIEOS-Fence: store-1:3\n\nCo-Authored-By: someone\n',
                  'Work\n\naieos-task: TASK-009\nAIEOS-Fence: store-1:3\n'):
            with self.subTest(m=m):
                r = run(commits=[{'commit': C1, 'message': m}])
                self.assertEqual((r.events, r.log), ((), base_log()))
                self.assertTrue(any(C1 in f for f in r.findings))

    def test_two_commits_of_one_task_under_one_lease(self):  # D-390 C2 (b)
        r = run(commits=[commit(C1), commit(C2)])
        self.assertEqual(kinds(r), [('task.submitted', TASK, 'appended'), ('record.added', TASK, 'appended')])
        ev = [l.event for l in records.check_log(r.log).lines[-2:]]
        self.assertEqual((ev[0]['payload']['commit'], ev[1]['payload']['refers_to']), (C1, C2))

    def test_the_commits_are_judged_in_the_given_order(self):  # D-390 C2 (c)
        r = run(commits=[commit(C2), commit(C1)])
        ev = [l.event for l in records.check_log(r.log).lines[-2:]]
        self.assertEqual((ev[0]['type'], ev[0]['payload']['commit']), ('task.submitted', C2))
        self.assertEqual((ev[1]['type'], ev[1]['payload']['refers_to']), ('record.added', C1))

    def test_a_lease_whose_token_the_log_already_submitted_does_not_count(self):
        log = submitted(base_log(), C1)
        r = run(log=log, commits=[commit(C1), commit(C2)])
        self.assertEqual(kinds(r), [('record.added', TASK, 'appended')])

    def test_a_commit_already_submitted_is_skipped(self):
        r = run(log=submitted(base_log(), C1), commits=[commit(C1)])
        self.assertEqual((r.events, r.findings), ((), ()))

    def test_a_commit_naming_no_task_is_left_alone(self):
        r = run(commits=[commit(C1, task=None, fence=None)])
        self.assertEqual((r.events, r.findings, r.log), ((), (), base_log()))

    def test_several_tasks(self):
        log = base_log(TASK, OTHER)
        r = run(log=log, commits=[commit(C1), commit(C2, task=OTHER, fence='store-1:4')],
                leases=[lease(), lease(OTHER, {'epoch': 'store-1', 'counter': 4})])
        self.assertEqual(kinds(r), [('task.submitted', TASK, 'appended'), ('task.submitted', OTHER, 'appended')])


class StepTwoAndFourTest(unittest.TestCase):  # R4 AC4
    def test_a_submission_whose_commit_is_not_given_is_reported_and_the_log_not_rewritten(self):
        log = submitted(base_log(), C3)
        r = run(log=log, commits=[])
        self.assertEqual((r.log, r.events), (log, ()))
        self.assertTrue(any('step 2' in f and C3 in f for f in r.findings))

    def test_a_given_submitted_commit_is_not_reported(self):
        r = run(log=submitted(base_log(), C3), commits=[commit(C3)])
        self.assertFalse(any('step 2' in f for f in r.findings))

    def test_an_observation_the_log_holds_is_a_duplicate(self):
        first = run(commits=[commit(C1)], leases=[])
        again = run(log=first.log, commits=[commit(C1)], leases=[])
        self.assertEqual(kinds(again), [('record.added', TASK, 'duplicate')])
        self.assertEqual(again.log, first.log)


class StepFiveAndAppendTest(unittest.TestCase):  # R5 AC5
    def test_expired_leases_are_returned_unchanged(self):
        leases = [lease(), lease(OTHER, expires_at=T0), lease(expires_at=T0 - datetime.timedelta(days=1))]
        r = run(leases=leases)
        self.assertEqual(list(r.expired), [leases[1], leases[2]])
        self.assertIs(r.expired[0], leases[1])

    def test_no_lease_expired(self):
        self.assertEqual(run().expired, ())

    def test_the_returned_log_is_the_given_bytes_followed_by_the_appended_lines(self):
        log = base_log()
        r = run(log=log, commits=[commit(C1), commit(C2)])
        self.assertTrue(r.log.startswith(log))
        self.assertEqual(r.log[len(log):].count(b'\n'), 2)

    def test_a_refused_append_is_reported_and_leaves_the_log(self):
        # An event_id already in the log under another event is refused by eventlog.append as a conflict.
        cid = C1
        log = base_log()
        other = eventlog.append(log, 'task.drafted', DRAFTED, recovery._id(cid, 'record.added'), T0, task_id=OTHER)
        log = other.log
        r = run(log=log, commits=[commit(cid)], leases=[])
        self.assertEqual((r.log, r.events), (log, ()))
        self.assertTrue(any('refused' in f and 'conflict' in f for f in r.findings))


class IdsTest(unittest.TestCase):  # R6 AC6
    def test_the_formula(self):
        want = hashlib.sha256(('recovery\n%s\ntask.submitted' % C1).encode('utf-8')).hexdigest()
        r = run(commits=[commit(C1)])
        self.assertEqual(r.events[0]['event_id'], want)
        obs = recovery.observation(C2, TASK, REC)
        self.assertEqual(obs['record_id'], hashlib.sha256(('recovery\n%s\nunfenced_write' % C2).encode()).hexdigest())

    def test_the_ids_do_not_depend_on_the_time(self):
        a = run(commits=[commit(C1)])
        b = run(commits=[commit(C1)], now=T0 + datetime.timedelta(minutes=5))
        self.assertEqual(a.events[0]['event_id'], b.events[0]['event_id'])

    def test_a_second_reconcile_appends_nothing(self):
        commits = [commit(C1), commit(C2), commit(C3, fence=None)]
        first = run(commits=commits)
        again = run(log=first.log, commits=commits)
        self.assertEqual(again.log, first.log)
        self.assertTrue(all(e['result'] == 'duplicate' for e in again.events))


class CheckersTest(unittest.TestCase):  # R7 AC7
    def test_every_payload_and_log_has_no_finding(self):
        r = run(commits=[commit(C1), commit(C2), commit(C3, fence=None)])
        self.assertEqual(records.check_log(r.log).findings(), [])
        for line in records.check_log(r.log).lines:
            self.assertEqual(records.check_payload(line.event['type'], line.event['payload']), [])

    def test_a_damaged_log_has_findings(self):
        self.assertNotEqual(records.check_log(b'{}\n').findings(), [])


class ImportsTest(unittest.TestCase):  # R8 AC8
    def test_the_import_list(self):
        tree = ast.parse(SRC.read_text(encoding='utf-8'))
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.extend('%s.%s' % (node.module, a.name) for a in node.names)
        allowed = {'aieos_bootstrap.eventlog', 'aieos_bootstrap.records'}
        bad = [n for n in names if n not in allowed and n.split('.')[0] not in sys.stdlib_module_names]
        self.assertEqual(bad, [])
        self.assertIn('aieos_bootstrap.eventlog', names)
        self.assertNotIn('aieos_bootstrap.conformance', names)

    def test_a_runner_import_would_be_caught(self):
        names = ['aieos_bootstrap.conformance']
        allowed = {'aieos_bootstrap.eventlog', 'aieos_bootstrap.records'}
        self.assertEqual([n for n in names if n not in allowed and n.split('.')[0] not in sys.stdlib_module_names],
                         names)


if __name__ == '__main__':
    unittest.main()

"""Unit tests of the execution path (task TASK-032 AC13, rules R1 to R10): every log is built in memory with
eventlog.append, and the writer's functions and the Resume Check are stand-ins that record their calls. No process
starts and no file is opened. Each test names its criteria in its own docstring."""

import ast
import datetime
import inspect
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import eventlog
from aieos_bootstrap import execution
from aieos_bootstrap import resume_check
from aieos_bootstrap import writer

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap'
ROOT = 'C:/a-root'
TASK = 'TASK-100'
OTHER_TASK = 'TASK-101'
H = 'a' * 64
CODE = 'c' * 64
NOW = datetime.datetime(2026, 10, 14, 12, 0, 0, tzinfo=datetime.timezone.utc)
LATER = NOW + datetime.timedelta(hours=1)
REC = 'aieos-core (unit)'
REQ = {'holder': 'agent-1', 'session_id': 'session-1', 'expires_at': LATER}
TOKEN = {'epoch': 'e1', 'counter': 4}
HELD = {'task_id': TASK, 'fencing_token': TOKEN, 'expires_at': LATER}
DECISIONS = ('CONTINUE', 'CONTINUE_WITH', 'REPLAN', 'BLOCKED', 'ESCALATE', 'STOP: scope invalid',
             'STOP: runtime insufficient', None)


class Log:
    """An event log kept as bytes; every line is decided by eventlog.append."""

    def __init__(self):
        self.data = b''
        self.seq = 0

    def add(self, event_type, payload, event_id, task_id=TASK, fencing_token=None, lease=None):
        r = eventlog.append(self.data, event_type, payload, event_id, NOW, task_id=task_id, fencing_token=fencing_token,
                            lease=lease)
        if r.result != 'appended':
            raise AssertionError(r.findings)
        self.data += r.line
        self.seq = r.seq


def approved_log():
    log = Log()
    log.add('task.drafted', {'contract_version': 'v1', 'contract_hash': H}, 'drafted-1')
    log.add('task.approved', {'contract_version': 'v1', 'contract_hash': H, 'approval_record': 'appr-1'}, 'approved-1')
    return log


def acceptance(next_state, rid='dec-1'):
    return {'record_id': rid, 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_local',
            'recorder': REC, 'subject': TASK, 'decision': 'NEEDS_REWORK', 'next_task_state': next_state}


def effect_event(event_type, payload, eid):
    return {'event_id': eid, 'type': event_type, 'payload': payload, 'task_id': TASK}


def record(decision, effect=None, uncovered=(), rid='rec-1'):
    """A stand-in execution record in the record form the log accepts (the real check's form)."""
    rec = {'record_id': rid, 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_local',
           'recorder': 'the Resume Check (stand-in)', 'subject': TASK, 'decision': decision,
           'uncovered': list(uncovered), 'state_effect': list(effect or [])}
    if decision is None:
        rec['error'] = 'an input is missing or malformed: stand-in'
    return rec


def effect_for(decision):
    if decision == 'REPLAN':
        return [effect_event('conflict.detected', {'tasks': [], 'paths': ['src/x.py']}, 'eff-conflict'),
                effect_event('task.stale', {'cause': 'conflict', 'refers_to': 'eff-conflict'}, 'eff-stale')]
    if decision == 'BLOCKED':
        return [effect_event('task.blocked', {'reason': 'dependency', 'blocked_by': ['TASK-099']}, 'eff-blocked')]
    if decision == 'ESCALATE':
        return [effect_event('task.blocked', {'reason': 'escalate', 'blocked_by': ['rec-1']}, 'eff-blocked')]
    if decision == 'STOP: scope invalid':
        return [effect_event('conflict.detected', {'tasks': [], 'paths': ['src/x.py']}, 'eff-conflict'),
                effect_event('task.blocked', {'reason': 'scope_invalid', 'blocked_by': ['eff-conflict']}, 'eff-blocked')]
    return []


class World:
    """Stand-ins for the writer's functions and the check, each recording its call."""

    def __init__(self, log=None, lease=None, rec=None):
        self.log = log if log is not None else approved_log()
        self.lease = lease
        self.rec = rec if rec is not None else record('CONTINUE')
        self.calls = []
        self.grant_answer = None
        self.release_answer = None
        self.refuse_append_at = None

    def read_log(self, root):
        self.calls.append(('read_log', (root,), {}))
        return self.log.data

    def append(self, root, event_type, payload, event_id, appended_at, recorder, task_id=None):
        self.calls.append(('append_event', (root, event_type, payload, event_id, appended_at, recorder),
                           {'task_id': task_id}))
        if self.refuse_append_at == event_id:
            return writer.WriteResult(eventlog.AppendResult('refused', 'event', findings=('stand-in refusal',)))
        r = eventlog.append(self.log.data, event_type, payload, event_id, appended_at, task_id=task_id,
                            recorder=recorder)
        if r.result == 'appended':
            self.log.data += r.line
            self.log.seq = r.seq
        return writer.WriteResult(r)

    def grant(self, root, task_id, task_state, holder, session_id, now, expires_at):
        self.calls.append(('grant_lease', (root, task_id, task_state, holder, session_id, now, expires_at), {}))
        if self.grant_answer is not None:
            return self.grant_answer
        self.lease = {'task_id': task_id, 'fencing_token': {'epoch': 'e1', 'counter': 5}, 'expires_at': expires_at}
        return writer.StoreResult('done', value=self.lease)

    def release(self, root, task_id, fencing_token):
        self.calls.append(('release_lease_token', (root, task_id, fencing_token), {}))
        if self.release_answer is not None:
            return self.release_answer
        gone, self.lease = self.lease, None
        return writer.StoreResult('done', value=gone)

    def held(self, root, task_id):
        self.calls.append(('held_lease', (root, task_id), {}))
        return self.lease

    def check(self, inputs, code_sha256):
        self.calls.append(('check', (inputs, code_sha256), {}))
        return self.rec

    def names(self):
        return [c[0] for c in self.calls]

    def run(self, inputs=None, **over):
        args = {'root': ROOT, 'task_id': TASK, 'inputs': inputs if inputs is not None else self.inputs(),
                'code_sha256': CODE, 'grant_request': REQ, 'recorder': REC, 'now': NOW}
        args.update(over)
        return execution.execute(args['root'], args['task_id'], args['inputs'], args['code_sha256'],
                                 args['grant_request'], args['recorder'], args['now'], read_log=self.read_log,
                                 append=self.append, grant=self.grant, release=self.release, held=self.held,
                                 check=self.check)

    def inputs(self, state=None, **over):
        inp = {'task_id': TASK, 'log_seq': self.log.seq,
               'task_state': state or ('IN_PROGRESS' if self.lease else 'READY'), 'approved_contract_hash': H}
        inp.update(over)
        return inp


def in_progress(rec):
    return World(lease=dict(HELD), rec=rec)


class R1Arguments(unittest.TestCase):
    def test_each_wrong_argument_is_refused_before_any_read(self):
        """TASK-032 AC1: every argument is checked before anything is read; a wrong one gives reason "argument"."""
        naive = datetime.datetime(2026, 10, 14, 12, 0, 0)
        cases = [
            {'root': ''}, {'root': None}, {'task_id': 'TASK-x'}, {'task_id': 7}, {'inputs': []},
            {'inputs': {'task_id': OTHER_TASK}}, {'code_sha256': 'C' * 64}, {'code_sha256': 'c' * 63},
            {'grant_request': dict(REQ, extra=1)}, {'grant_request': {'holder': 'a', 'session_id': 's'}},
            {'grant_request': dict(REQ, holder='')}, {'grant_request': dict(REQ, session_id=3)},
            {'grant_request': dict(REQ, expires_at=naive)}, {'grant_request': dict(REQ, expires_at=LATER.replace(microsecond=5))},
            {'recorder': ''}, {'now': naive}, {'now': NOW.replace(microsecond=1)},
            {'now': NOW.astimezone(datetime.timezone(datetime.timedelta(hours=7)))}, {'now': '2026-10-14T12:00:00Z'},
        ]
        for over in cases:
            w = World()
            r = w.run(**over)
            self.assertEqual((r['result'], r['reason']), ('refused', 'argument'), over)
            self.assertTrue(r['findings'] and all(f.startswith('argument: ') for f in r['findings']), over)
            self.assertEqual(w.calls, [], over)

    def test_well_formed_arguments_go_on(self):
        """TASK-032 AC1: a well-formed call reads the log and the held lease, then calls the check."""
        w = World()
        r = w.run()
        self.assertEqual(r['result'], 'decided')
        self.assertEqual(w.names()[:3], ['read_log', 'held_lease', 'check'])

    def test_an_argument_whose_methods_raise_is_refused(self):
        """TASK-032 AC1, AC9: inputs whose get raises gives "argument", nothing escapes."""
        class Bad(dict):
            def get(self, *a):
                raise RuntimeError('no')
        w = World()
        r = w.run(inputs=Bad(task_id=TASK))
        self.assertEqual((r['result'], r['reason']), ('refused', 'argument'))
        self.assertEqual(w.calls, [])

    def test_the_defaults_are_bound_at_call_time(self):
        """TASK-032 AC1: read_log, append, grant, release, held and check default, at call time, to the writer's
        functions and resume_check.check."""
        w = World()
        with mock.patch.object(writer, 'read_log', w.read_log), mock.patch.object(writer, 'append_event', w.append), \
                mock.patch.object(writer, 'grant_lease', w.grant), \
                mock.patch.object(writer, 'release_lease_token', w.release), \
                mock.patch.object(writer, 'held_lease', w.held), mock.patch.object(resume_check, 'check', w.check):
            r = execution.execute(ROOT, TASK, w.inputs(), CODE, REQ, REC, NOW)
        self.assertEqual(r['result'], 'decided')
        self.assertEqual(w.names(), ['read_log', 'held_lease', 'check', 'append_event', 'grant_lease'])

    def test_every_stand_in_call_binds_to_the_real_signature(self):
        """TASK-032 AC1 (decision D-687 M3): every call the stand-ins record binds to the real function's signature,
        for read_log, append_event, grant_lease, release_lease_token and held_lease, and the check's to
        resume_check.check."""
        real = {'read_log': writer.read_log, 'append_event': writer.append_event, 'grant_lease': writer.grant_lease,
                'release_lease_token': writer.release_lease_token, 'held_lease': writer.held_lease,
                'check': resume_check.check}
        seen = set()
        for w in (World(), in_progress(record('BLOCKED', effect_for('BLOCKED')))):
            w.run()
            for name, args, kwargs in w.calls:
                inspect.signature(real[name]).bind(*args, **kwargs)
                seen.add(name)
        self.assertEqual(seen, set(real))


class R2Projection(unittest.TestCase):
    def test_each_event_type_sets_the_state(self):
        """TASK-032 AC2: from the last task.approved, each later event of the task sets the state; only READY, REWORK
        and IN_PROGRESS go on."""
        cases = [
            ('task.drafted', {'contract_version': 'v2', 'contract_hash': 'b' * 64}, None, 'DRAFT'),
            ('task.blocked', {'reason': 'dependency', 'blocked_by': ['TASK-099']}, None, 'BLOCKED'),
            ('task.stale', {'cause': 'conflict', 'refers_to': 'x'}, None, 'STALE'),
            ('task.done', {'decision_record': 'dec-1'}, None, 'DONE'),
            ('task.replanned', {'contract_version': 'v2', 'contract_hash': 'b' * 64}, None, 'DRAFT'),
            ('decision.acceptance', acceptance('IN_REVIEW'), None, 'IN_REVIEW'),
            ('decision.acceptance', acceptance('REWORK'), 'REWORK', None),
        ]
        for event_type, payload, go_state, stop_state in cases:
            w = World()
            w.log.add(event_type, payload, 'e-' + event_type)
            r = w.run(inputs=w.inputs(state=go_state or stop_state))
            if go_state:
                self.assertEqual(r['result'], 'decided', event_type)
            else:
                self.assertEqual((r['result'], r['reason']), ('refused', 'state'), event_type)
                self.assertIn(stop_state, r['findings'][0])
                self.assertNotIn('check', w.names())

    def test_blocked_then_unblocked_is_ready_and_submitted_is_verifying(self):
        """TASK-032 AC2: task.unblocked sets READY again; task.submitted sets VERIFYING, which is refused."""
        w = World()
        w.log.add('task.blocked', {'reason': 'dependency', 'blocked_by': ['TASK-099']}, 'b1')
        w.log.add('task.unblocked', {'reason': 'dependency done'}, 'u1')
        self.assertEqual(w.run()['result'], 'decided')
        w = World()
        w.log.add('task.submitted', {'commit': '1' * 40, 'compensating': False}, 's1', fencing_token=TOKEN,
                  lease=dict(HELD))
        r = w.run(inputs=w.inputs(state='VERIFYING'))
        self.assertEqual(r['reason'], 'state')
        self.assertIn('VERIFYING', r['findings'][0])

    def test_a_drafted_after_the_last_approval_is_refused(self):
        """TASK-032 AC2 (decision D-687 M1): a task.drafted after the last task.approved gives DRAFT, refused."""
        w = World()
        w.log.add('task.drafted', {'contract_version': 'v2', 'contract_hash': 'b' * 64}, 'drafted-2')
        r = w.run(inputs=w.inputs(state='DRAFT'))
        self.assertEqual((r['result'], r['reason']), ('refused', 'state'))
        self.assertIn('DRAFT', r['findings'][0])

    def test_a_task_type_the_projection_does_not_name_is_refused(self):
        """TASK-032 AC2 (decision D-687 M1): a task.* type the projection does not name gives "state"."""
        w = World()
        w.log.add('task.done', {'decision_record': 'dec-1'}, 'done-1')
        names = {k: v for k, v in execution.STATE_OF.items() if k != 'task.done'}
        with mock.patch.object(execution, 'STATE_OF', names):
            r = w.run()
        self.assertEqual((r['result'], r['reason']), ('refused', 'state'))
        self.assertIn('task.done is a task event the projection does not name', r['findings'][0])

    def test_no_task_approved_and_other_tasks_events(self):
        """TASK-032 AC2: no task.approved of the task gives "state"; another task's events do not count."""
        w = World(log=Log())
        w.log.add('task.approved', {'contract_version': 'v1', 'contract_hash': H, 'approval_record': 'a'}, 'a1',
                  task_id=OTHER_TASK)
        r = w.run(inputs={'task_id': TASK, 'log_seq': 1, 'task_state': 'READY', 'approved_contract_hash': H})
        self.assertEqual((r['result'], r['reason']), ('refused', 'state'))
        w = World()
        w.log.add('task.blocked', {'reason': 'dependency', 'blocked_by': []}, 'b-other', task_id=OTHER_TASK)
        self.assertEqual(w.run()['result'], 'decided')

    def test_the_held_lease_gives_in_progress(self):
        """TASK-032 AC2: an unexpired lease on a READY or REWORK task makes it IN_PROGRESS."""
        w = in_progress(record('CONTINUE'))
        r = w.run()
        self.assertEqual(r['result'], 'decided')
        self.assertEqual(w.calls[2][1][0]['task_state'], 'IN_PROGRESS')
        w = in_progress(record('CONTINUE'))
        self.assertEqual(w.run(inputs=w.inputs(state='READY'))['reason'], 'inputs')

    def test_an_expired_or_misplaced_or_malformed_lease_is_refused(self):
        """TASK-032 AC2: an expired held lease gives "lease"; a lease on a task in another state gives "state"; a
        lease not in eventlog.LEASE_KEYS' form gives "lease"."""
        w = World(lease=dict(HELD, expires_at=NOW))
        r = w.run(inputs=w.inputs(state='IN_PROGRESS'))
        self.assertEqual((r['result'], r['reason']), ('refused', 'lease'))
        self.assertIn('expire_leases', r['findings'][0])
        w = World(lease=dict(HELD))
        w.log.add('task.blocked', {'reason': 'dependency', 'blocked_by': []}, 'b1')
        r = w.run(inputs=w.inputs(state='IN_PROGRESS'))
        self.assertEqual((r['result'], r['reason']), ('refused', 'state'))
        self.assertIn('BLOCKED', r['findings'][0])
        for bad in (dict(HELD, task_id=OTHER_TASK), {'task_id': TASK}, dict(HELD, fencing_token={'epoch': 'e'}),
                    dict(HELD, expires_at='2026'), 'a lease'):
            w = World(lease=bad)
            r = w.run(inputs=w.inputs(state='IN_PROGRESS'))
            self.assertEqual((r['result'], r['reason']), ('refused', 'lease'), bad)
            self.assertNotIn('check', w.names())

    def test_a_refused_log(self):
        """TASK-032 AC2: a log with a finding, or a result that is not bytes, gives "log"."""
        for data in (b'not json\n', 'text'):
            w = World()
            w.log.data = data
            r = w.run(inputs={'task_id': TASK, 'log_seq': 2, 'task_state': 'READY', 'approved_contract_hash': H})
            self.assertEqual((r['result'], r['reason']), ('refused', 'log'), data)
            self.assertEqual(w.names(), ['read_log'])


class R3Agreement(unittest.TestCase):
    def test_each_difference_is_refused_with_nothing_appended(self):
        """TASK-032 AC3: task_state, log_seq and approved_contract_hash must equal the log's; else "inputs", the check
        is not called and nothing is appended."""
        for over in ({'task_state': 'REWORK'}, {'log_seq': 1}, {'log_seq': True}, {'log_seq': '2'},
                     {'approved_contract_hash': 'b' * 64}, {'approved_contract_hash': None}):
            w = World()
            r = w.run(inputs=w.inputs(**over))
            self.assertEqual((r['result'], r['reason']), ('refused', 'inputs'), over)
            self.assertTrue(r['findings'][0].startswith('inputs: '), over)
            self.assertEqual(w.names(), ['read_log', 'held_lease'], over)

    def test_the_last_approval_counts(self):
        """TASK-032 AC3: the contract hash compared is that of the task's last task.approved."""
        w = World()
        w.log.add('task.replanned', {'contract_version': 'v2', 'contract_hash': 'b' * 64}, 'rp')
        w.log.add('task.approved', {'contract_version': 'v2', 'contract_hash': 'b' * 64, 'approval_record': 'a2'},
                  'approved-2')
        self.assertEqual(w.run()['reason'], 'inputs')
        self.assertEqual(w.run(inputs=w.inputs(approved_contract_hash='b' * 64))['result'], 'decided')


class R4Record(unittest.TestCase):
    def test_each_malformed_record_is_refused_before_any_release_or_append(self):
        """TASK-032 AC4: a result in another form gives "check" before anything is released or appended."""
        good = record('BLOCKED', effect_for('BLOCKED'))
        cases = ['a text', dict(good, record_id=''), dict(good, subject=OTHER_TASK),
                 {k: v for k, v in good.items() if k != 'decision'}, dict(good, state_effect='none'),
                 dict(good, state_effect=[dict(good['state_effect'][0], extra=1)]),
                 dict(good, state_effect=[dict(good['state_effect'][0], task_id=OTHER_TASK)]),
                 dict(good, state_effect=[dict(good['state_effect'][0], event_id='')]),
                 dict(record(None), state_effect=good['state_effect'])]
        for rec in cases:
            w = in_progress(rec)
            r = w.run()
            self.assertEqual((r['result'], r['reason']), ('refused', 'check'), rec)
            self.assertEqual(w.names(), ['read_log', 'held_lease', 'check'], rec)

    def test_a_raising_check_is_refused(self):
        """TASK-032 AC4, AC9: a check that raises gives "check" and nothing is appended."""
        w = World()
        w.check = mock.Mock(side_effect=RuntimeError('boom'))
        r = w.run()
        self.assertEqual((r['result'], r['reason']), ('refused', 'check'))
        self.assertNotIn('append_event', w.names())

    def test_an_error_record_is_appended_alone(self):
        """TASK-032 AC4, AC7: a record with decision null is appended as decision.execution alone, and from READY no
        store function is called."""
        w = World(rec=record(None))
        r = w.run()
        self.assertEqual((r['result'], r['decision'], r['appended']), ('decided', None, ['rec-1']))
        self.assertEqual(w.names(), ['read_log', 'held_lease', 'check', 'append_event'])
        self.assertIsNone(r['lease'])


class R5Release(unittest.TestCase):
    def test_the_release_comes_before_the_appends(self):
        """TASK-032 AC5: from IN_PROGRESS every outcome but CONTINUE and CONTINUE_WITH releases the held lease by its
        token before anything is appended."""
        for decision in DECISIONS[2:]:
            w = in_progress(record(decision, effect_for(decision)))
            r = w.run()
            self.assertEqual(r['result'], 'decided', decision)
            names = w.names()
            self.assertEqual(names[3], 'release_lease_token', decision)
            self.assertEqual(w.calls[3][1], (ROOT, TASK, TOKEN), decision)
            self.assertTrue(all(n == 'append_event' for n in names[4:]) and len(names) > 4, decision)
            self.assertEqual(r['released'], HELD, decision)
            self.assertIsNone(r['lease'], decision)
            self.assertIsNone(w.lease, decision)

    def test_a_refused_release_stops_with_nothing_appended(self):
        """TASK-032 AC5: a refused release, a release that raises, or one that gives no StoreResult gives "lease",
        and nothing is appended."""
        answers = [writer.StoreResult('refused', 'token', ['another token is held']), 'done']
        for answer in answers + ['raise']:
            w = in_progress(record('BLOCKED', effect_for('BLOCKED')))
            if answer == 'raise':
                w.release = mock.Mock(side_effect=ValueError('bad token'))
            else:
                w.release_answer = answer
            r = w.run()
            self.assertEqual((r['result'], r['reason']), ('refused', 'lease'), answer)
            self.assertNotIn('append_event', w.names(), answer)
            self.assertEqual(r['appended'], [], answer)
        w = in_progress(record('BLOCKED', effect_for('BLOCKED')))
        w.release_answer = answers[0]
        self.assertIn('another token is held', w.run()['findings'])


class R6Appends(unittest.TestCase):
    def test_the_record_then_its_events_in_order(self):
        """TASK-032 AC6: the record as decision.execution under its record_id, then each state_effect event under its
        stored id, with task_id the task and no fencing token."""
        w = World(rec=record('STOP: scope invalid', effect_for('STOP: scope invalid')))
        r = w.run()
        appends = [c for c in w.calls if c[0] == 'append_event']
        self.assertEqual([(c[1][1], c[1][3]) for c in appends],
                         [('decision.execution', 'rec-1'), ('conflict.detected', 'eff-conflict'),
                          ('task.blocked', 'eff-blocked')])
        self.assertTrue(all(c[2] == {'task_id': TASK} and c[1][4] == NOW and c[1][5] == REC for c in appends))
        self.assertEqual(r['appended'], ['rec-1', 'eff-conflict', 'eff-blocked'])
        self.assertIs(appends[0][1][2], w.rec)

    def test_a_refusal_mid_way_stops_with_the_ids_so_far_and_no_grant(self):
        """TASK-032 AC6: the first other result stops the appends with the ids so far, and no lease is granted."""
        w = World(rec=record('STOP: scope invalid', effect_for('STOP: scope invalid')))
        w.refuse_append_at = 'eff-conflict'
        r = w.run()
        self.assertEqual((r['result'], r['reason'], r['appended']), ('refused', 'append', ['rec-1']))
        self.assertIn('stand-in refusal', r['findings'])
        w = World(rec=record('CONTINUE'))
        w.refuse_append_at = 'rec-1'
        r = w.run()
        self.assertEqual((r['reason'], r['appended']), ('append', []))
        self.assertNotIn('grant_lease', w.names())

    def test_a_raising_append_or_another_result_stops(self):
        """TASK-032 AC6, AC9: an append that raises, or gives something that is not a WriteResult, gives "append"."""
        for bad in (mock.Mock(side_effect=OSError('disk')), mock.Mock(return_value=eventlog.AppendResult('appended'))):
            w = World()
            w.append = bad
            r = w.run()
            self.assertEqual((r['result'], r['reason']), ('refused', 'append'))
            self.assertNotIn('grant_lease', w.names())

    def test_a_second_append_is_a_duplicate_and_a_rerun_is_refused(self):
        """TASK-032 AC6 (decision D-687 M2): a second append of the same record gives "duplicate" at the append, and
        a rerun of execute with the same inputs after an append is refused "inputs" and appends nothing."""
        for decision in DECISIONS:
            w = World(rec=record(decision, effect_for(decision)))
            inputs = w.inputs()
            self.assertEqual(w.run(inputs=inputs)['appended'][0], 'rec-1', decision)
            again = w.append(ROOT, 'decision.execution', w.rec, 'rec-1', NOW, REC, task_id=TASK)
            self.assertEqual(again.result, 'duplicate', decision)
            before = w.log.data
            r = w.run(inputs=inputs)
            self.assertEqual((r['result'], r['reason']), ('refused', 'inputs'), decision)
            self.assertEqual(w.log.data, before, decision)

    def test_the_writers_duplicate_is_listed(self):
        """TASK-032 AC6: "duplicate" results are listed and the appends go on."""
        w = World(rec=record('BLOCKED', effect_for('BLOCKED')))
        seq = w.log.seq
        w.log.add('decision.execution', w.rec, 'rec-1')
        r = w.run(inputs=w.inputs(log_seq=seq + 1))
        self.assertEqual((r['result'], r['duplicate'], r['appended']), ('decided', ['rec-1'], ['eff-blocked']))


class R7Lease(unittest.TestCase):
    def test_a_grant_on_continue_from_ready_and_rework_after_the_appends(self):
        """TASK-032 AC7: on CONTINUE or CONTINUE_WITH for a task in READY or REWORK, grant_lease once after every
        append, with grant_request's values."""
        for decision in ('CONTINUE', 'CONTINUE_WITH'):
            for state in ('READY', 'REWORK'):
                w = World(rec=record(decision))
                if state == 'REWORK':
                    w.log.add('decision.acceptance', acceptance('REWORK'), 'acc-1')
                r = w.run(inputs=w.inputs(state=state))
                self.assertEqual(r['result'], 'decided', (decision, state))
                self.assertEqual(w.names()[-2:], ['append_event', 'grant_lease'])
                self.assertEqual(w.calls[-1][1], (ROOT, TASK, state, 'agent-1', 'session-1', NOW, LATER))
                self.assertEqual(r['lease'], w.lease)

    def test_a_store_refusal_is_named_and_the_record_stays(self):
        """TASK-032 AC7: a refused grant, a raising grant or a result that is not a StoreResult gives "lease", the
        store's reason named, and the record stays in the log."""
        for answer in (writer.StoreResult('refused', 'held', ['a lease on TASK-100 is held']), None, 'raise'):
            w = World()
            if answer == 'raise':
                w.grant = mock.Mock(side_effect=ValueError('no store'))
            else:
                w.grant_answer = answer if answer is not None else 'done'
            r = w.run()
            self.assertEqual((r['result'], r['reason'], r['appended']), ('refused', 'lease', ['rec-1']), answer)
            self.assertIsNone(r['lease'])
        w = World()
        w.grant_answer = writer.StoreResult('refused', 'session', ['the session is not started'])
        r = w.run()
        self.assertIn('lease: grant_lease refused it (session)', r['findings'])

    def test_a_kept_lease_on_in_progress(self):
        """TASK-032 AC7: on CONTINUE or CONTINUE_WITH for a task IN_PROGRESS the held lease is kept and given, and no
        store function but held_lease is called."""
        for decision in ('CONTINUE', 'CONTINUE_WITH'):
            w = in_progress(record(decision))
            r = w.run()
            self.assertEqual((r['result'], r['lease'], r['released']), ('decided', HELD, None))
            self.assertEqual(w.names(), ['read_log', 'held_lease', 'check', 'append_event'])

    def test_no_store_call_for_any_other_decision_from_ready_or_rework(self):
        """TASK-032 AC7: from READY or REWORK no other outcome calls a store function, and no lease exists after."""
        for decision in DECISIONS[2:]:
            w = World(rec=record(decision, effect_for(decision)))
            r = w.run()
            self.assertEqual(r['result'], 'decided', decision)
            self.assertNotIn('grant_lease', w.names())
            self.assertNotIn('release_lease_token', w.names())
            self.assertIsNone(r['lease'])
            self.assertIsNone(w.lease)


BASE = '1' * 40
HEAD = '2' * 40
COMMIT = '3' * 40


def full_inputs(log_seq, task_state, **over):
    """Well-formed Resume Check inputs (as tests/unit/test_resume_check.py builds them) for TASK-100."""
    inp = {
        'task_id': TASK, 'log_seq': log_seq, 'task_state': task_state,
        'contract': {
            'task': TASK, 'contract_version': 'v1', 'task_type': 'implementation', 'risk': 'medium',
            'input_state': {'base_commit': BASE, 'depends_on': ['TASK-099'], 'intent_versions': {'SPEC-003': 'v4'}},
            'write_set': {'paths': ['src/app/core/**']},
            'read_set': {'paths': ['src/app/util/helpers.py'], 'interfaces': ['load_policy'], 'schemas': ['record']},
            'constitution': ['INV-001'],
            'autonomy': {'budgets': {'retries': 2, 'tokens': '400k', 'wall_time': '2h', 'human_attention': '10m'}}},
        'contract_hash': H, 'approved_contract_hash': H, 'head_commit': HEAD, 'base_is_ancestor': True,
        'commits': [{'id': COMMIT, 'paths': [{'path': 'docs/notes.md', 'change': 'modified'}], 'submitted': False}],
        'components': [{'id': 'CMP-API', 'paths': ['src/app/api/**'], 'tags': []},
                       {'id': 'CMP-CORE', 'paths': ['src/app/core'], 'tags': []}],
        'interfaces': [{'id': 'load_policy', 'component': 'CMP-API'}],
        'symbols': [{'interface': 'load_policy', 'base': 'F(a)', 'head': 'F(a)'}],
        'schemas': [{'name': 'record', 'base': {'path': 'src/app/api/record.json', 'sha256': 'b' * 64},
                     'head': {'path': 'src/app/api/record.json', 'sha256': 'b' * 64}}],
        'derived_read_set': [], 'observed_read_set': [],
        'intent_current': {'SPEC-003': 'v4'},
        'dependencies': {'TASK-099': {'state': 'DONE', 'stale_evidence': False}},
        'articles': [{'id': 'INV-001', 'scope': {'paths': ['src/**'], 'components': []},
                      'applicability': {'task_types': ['implementation']}, 'violated': False}],
        'runtime': {'adapter': 'an-adapter', 'max_risk': 'high'},
        'risk_rules': [{'match': {'paths': ['src/**']}, 'risk': 'medium'}],
        'policy_version': 'v2',
        'budget_use': {'retries': {'used': 0, 'reported': True}, 'tokens': {'used': '10k', 'reported': True},
                       'wall_time': {'used': '10m', 'reported': True}, 'human_attention': {'used': '0m', 'reported': True}},
    }
    inp.update(over)
    return inp


def replan_over():
    return {'commits': [{'id': COMMIT, 'paths': [{'path': 'src/app/api/policy.py', 'change': 'modified'}],
                         'submitted': False}],
            'symbols': [{'interface': 'load_policy', 'base': 'F', 'head': 'G'}]}


class R8Limits(unittest.TestCase):
    def test_replan_on_ready_appends_the_conflict_only(self):
        """TASK-032 AC8: with the real check, REPLAN on a READY task appends the record and conflict.detected only, no
        task.stale (point (i)), and the result names the record's uncovered entries."""
        w = World()
        w.check = resume_check.check
        r = w.run(inputs=full_inputs(w.log.seq, 'READY', **replan_over()))
        self.assertEqual((r['result'], r['decision']), ('decided', 'REPLAN'))
        types = [c[1][1] for c in w.calls if c[0] == 'append_event']
        self.assertEqual(types, ['decision.execution', 'conflict.detected'])
        self.assertIn('conflict.detected tasks: the commits\' trailers are not an input', r['uncovered'])
        self.assertIsNone(r['lease'])

    def test_replan_on_rework_appends_the_stale(self):
        """TASK-032 AC8: the same REPLAN on a REWORK task gives the conflict and task.stale, appended as returned."""
        w = World()
        w.log.add('decision.acceptance', acceptance('REWORK'), 'acc-1')
        w.check = resume_check.check
        r = w.run(inputs=full_inputs(w.log.seq, 'REWORK', **replan_over()))
        types = [c[1][1] for c in w.calls if c[0] == 'append_event']
        self.assertEqual(types, ['decision.execution', 'conflict.detected', 'task.stale'])
        self.assertEqual(r['result'], 'decided')

    def test_the_uncovered_entries_are_sorted_and_unique(self):
        """TASK-032 AC8, AC9: the result's uncovered are the record's string entries, sorted, without duplicates."""
        w = World(rec=record('CONTINUE', uncovered=['b', 'a', 'b', 7]))
        self.assertEqual(w.run()['uncovered'], ['a', 'b'])


class R9Result(unittest.TestCase):
    def test_the_keys_on_every_path(self):
        """TASK-032 AC9: every result has exactly the keys of RESULT_KEYS."""
        results = [World().run(), World().run(root=''), in_progress(record('BLOCKED', effect_for('BLOCKED'))).run()]
        w = World()
        results.append(w.run(inputs=w.inputs(log_seq=99)))
        for r in results:
            self.assertEqual(tuple(r), execution.RESULT_KEYS)

    def test_an_exception_at_each_step_is_caught(self):
        """TASK-032 AC9: an exception raised by read_log or held becomes a result with the step's reason."""
        w = World()
        w.read_log = mock.Mock(side_effect=OSError('gone'))
        r = w.run()
        self.assertEqual((r['result'], r['reason']), ('refused', 'log'))
        w = World()
        w.held = mock.Mock(side_effect=ValueError('bad store'))
        r = w.run()
        self.assertEqual((r['result'], r['reason']), ('refused', 'lease'))


def _module():
    return (SRC / 'execution.py').read_bytes().decode('utf-8')


class R10Purity(unittest.TestCase):
    def test_imports_and_calls(self):
        """TASK-032 AC10, AC11: the module imports only the standard library's datetime and re and
        aieos_bootstrap's records, resume_check and writer, and calls no open, process, clock, environment,
        exec, eval, compile or __import__; no assert; no string naming the project-state directory."""
        source = _module()
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.update('%s.%s' % (node.module, a.name) for a in node.names)
            self.assertNotIsInstance(node, ast.Assert)
        self.assertEqual(imported, {'datetime', 're', 'aieos_bootstrap.records', 'aieos_bootstrap.resume_check',
                                    'aieos_bootstrap.writer'})
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for bad in ('open', 'exec', 'eval', 'compile', '__import__', 'importlib', 'subprocess', 'os', 'sys', 'time'):
            self.assertNotIn(bad, names)
        for bad in ('now', 'utcnow', 'today', 'environ', 'getenv', 'system', 'Popen', 'write', 'open_store',
                    'start_session', 'end_session', 'expire_leases', 'release_lease', 'evaluate'):
            self.assertNotIn(bad, attrs)
        self.assertNotIn('.' + 'aieos', source)

    def test_the_docstring_states_the_limits(self):
        """TASK-032 AC10, AC11: the docstring names what the module does not do, DEF-0030, point (i), DEF-0055 P6
        and the kept lease's unchecked holder."""
        doc = ' '.join(ast.get_docstring(ast.parse(_module())).split())
        for words in ('What it does not do', 'DEF-0030', 'Point (i)', 'DEF-0055 P6', 'decision D-687 M4',
                      'it gathers no Resume Check input', 'no task.unblocked', 'expires no lease',
                      'One run at a time'):
            self.assertIn(words, doc)

    def test_the_package_lists_the_module(self):
        """TASK-032 AC11: __init__.py's __all__ and docstring name execution, and name no fixture folder."""
        init = (SRC / '__init__.py').read_bytes().decode('utf-8')
        self.assertIn("'execution'", init)
        self.assertIn('``execution`` (TASK-032)', init)
        for folder in ('fixtures' + '_rc', 'fixtures' + '_risk'):  # built, so that this file names no fixture folder
            self.assertNotIn(folder, init)


if __name__ == '__main__':
    unittest.main()

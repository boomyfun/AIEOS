"""Property tests of aieos_bootstrap.execution (task TASK-032 AC13): standard library only, fixed seeds. For random
decisions, task states, store answers and refused appends, with stand-in records and a log appended in memory by
eventlog.append: a second run appends nothing new and is refused "inputs" when the first appended anything; when a
call has appended anything, a lease exists after it only on CONTINUE or CONTINUE_WITH, and a lease is granted only
after the record is in the log and never after a refused append; no lease survives any other outcome whose record is
appended for a task IN_PROGRESS. The oracles use literal decision and state names, not the module's constants (review
R3). Each test names its criteria in its own docstring."""

CONTINUING = ('CONTINUE', 'CONTINUE_WITH')

import datetime
import random
import unittest

from aieos_bootstrap import eventlog
from aieos_bootstrap import execution
from aieos_bootstrap import records
from aieos_bootstrap import writer

ROOT = 'C:/a-root'
TASK = 'TASK-100'
H = 'a' * 64
CODE = 'c' * 64
NOW = datetime.datetime(2026, 10, 14, 12, 0, 0, tzinfo=datetime.timezone.utc)
LATER = NOW + datetime.timedelta(hours=1)
REC = 'aieos-core (property)'
REQ = {'holder': 'agent-1', 'session_id': 'session-1', 'expires_at': LATER}
DECISIONS = ('CONTINUE', 'CONTINUE_WITH', 'REPLAN', 'BLOCKED', 'ESCALATE', 'STOP: scope invalid',
             'STOP: runtime insufficient', None)
RUNS = 300


def effect(decision, n):
    def ev(event_type, payload, name):
        return {'event_id': 'eff-%s-%d' % (name, n), 'type': event_type, 'payload': payload, 'task_id': TASK}
    if decision == 'REPLAN':
        return [ev('conflict.detected', {'tasks': [], 'paths': ['src/x.py']}, 'conflict'),
                ev('task.stale', {'cause': 'conflict', 'refers_to': 'eff-conflict-%d' % n}, 'stale')]
    if decision in ('BLOCKED', 'ESCALATE'):
        return [ev('task.blocked', {'reason': 'dependency', 'blocked_by': ['TASK-099']}, 'blocked')]
    if decision == 'STOP: scope invalid':
        return [ev('conflict.detected', {'tasks': [], 'paths': ['src/x.py']}, 'conflict'),
                ev('task.blocked', {'reason': 'scope_invalid', 'blocked_by': ['eff-conflict-%d' % n]}, 'blocked')]
    return []


def record(decision, n):
    rec = {'record_id': 'rec-%d' % n, 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_local',
           'recorder': 'stand-in', 'subject': TASK, 'decision': decision, 'uncovered': [],
           'state_effect': effect(decision, n)}
    if decision is None:
        rec['error'] = 'stand-in error'
    return rec


class World:
    def __init__(self, rng, n):
        self.rng = rng
        self.events = []
        self.log = b''
        self.seq = 0
        self.add('task.approved', {'contract_version': 'v1', 'contract_hash': H, 'approval_record': 'a'}, 'approved')
        self.state = rng.choice(('READY', 'REWORK', 'IN_PROGRESS'))
        if self.state == 'REWORK':
            self.add('decision.acceptance', {'record_id': 'dec', 'fact_kind': 'interpretation',
                                             'source_class': 'deterministic_tool_local', 'recorder': REC,
                                             'subject': TASK, 'decision': 'NEEDS_REWORK',
                                             'next_task_state': 'REWORK'}, 'acc')
        self.lease = ({'task_id': TASK, 'fencing_token': {'epoch': 'e', 'counter': 1}, 'expires_at': LATER}
                      if self.state == 'IN_PROGRESS' else None)
        self.rec = record(rng.choice(DECISIONS), n)
        self.grant_ok = rng.random() < 0.8
        self.release_ok = rng.random() < 0.8
        self.appends = 0
        self.refuse_at = rng.choice((None, None, None, None, None, 1, 2))
        self.order = []

    def add(self, event_type, payload, eid):
        r = eventlog.append(self.log, event_type, payload, eid, NOW, task_id=TASK)
        if r.result != 'appended':
            raise AssertionError(r.findings)
        self.log += r.line
        self.seq = r.seq

    def ids_in_log(self):
        return {line.event['event_id'] for line in records.check_log(self.log).lines}

    def read_log(self, root):
        return self.log

    def append(self, root, event_type, payload, event_id, appended_at, recorder, task_id=None):
        self.order.append(('append', event_id))
        self.appends += 1
        if self.appends == self.refuse_at:
            self.order.append(('refused', event_id))
            return writer.WriteResult(eventlog.AppendResult('refused', 'event', findings=('stand-in refusal',)))
        r = eventlog.append(self.log, event_type, payload, event_id, appended_at, task_id=task_id, recorder=recorder)
        if r.result == 'appended':
            self.log += r.line
            self.seq = r.seq
        return writer.WriteResult(r)

    def grant(self, root, task_id, task_state, holder, session_id, now, expires_at):
        self.order.append(('grant', self.rec['record_id'] in self.ids_in_log()))
        if not self.grant_ok or self.lease is not None:
            return writer.StoreResult('refused', 'held', ['refused'])
        self.lease = {'task_id': task_id, 'fencing_token': {'epoch': 'e', 'counter': 2}, 'expires_at': expires_at}
        return writer.StoreResult('done', value=dict(self.lease))

    def release(self, root, task_id, fencing_token):
        self.order.append(('release', None))
        if not self.release_ok:
            return writer.StoreResult('refused', 'token', ['refused'])
        gone, self.lease = self.lease, None
        return writer.StoreResult('done', value=gone)

    def held(self, root, task_id):
        return dict(self.lease) if self.lease else None

    def check(self, inputs, code_sha256):
        return self.rec

    def run(self, inp):
        return execution.execute(ROOT, TASK, inp, CODE, REQ, REC, NOW, read_log=self.read_log, append=self.append,
                                 grant=self.grant, release=self.release, held=self.held, check=self.check)


def worlds(seed):
    rng = random.Random(seed)
    for n in range(RUNS):
        w = World(rng, n)
        inp = {'task_id': TASK, 'log_seq': w.seq, 'task_state': w.state, 'approved_contract_hash': H}
        yield w, inp


class Properties(unittest.TestCase):
    def test_a_second_run_appends_nothing_new(self):
        """TASK-032 AC3, AC6 (decision D-687 M2): a second run with the same inputs appends nothing, and is refused
        "inputs" when the first appended anything."""
        reruns = 0
        for w, inp in worlds(3201):
            start = w.log
            first = w.run(inp)
            if w.log == start:
                continue  # nothing was appended (a refusal before or at the first append): a rerun may append
            reruns += 1
            self.assertTrue(first['appended'])
            before = w.log
            second = w.run(inp)
            self.assertEqual(w.log, before)
            self.assertEqual(second['appended'], [])
            self.assertEqual((second['result'], second['reason']), ('refused', 'inputs'))
        self.assertGreater(reruns, RUNS // 2)

    def test_a_lease_only_on_continue_and_only_after_the_record(self):
        """TASK-032 AC5, AC7: after a call a lease is held only when the decision is CONTINUE or CONTINUE_WITH (or the
        call stopped before anything was appended), and every grant comes after the record is in the log."""
        for w, inp in worlds(3202):
            r = w.run(inp)
            grants = [flag for kind, flag in w.order if kind == 'grant']
            self.assertTrue(all(grants))
            self.assertLessEqual(len(grants), 1)
            if any(kind == 'refused' for kind, _ in w.order):
                self.assertEqual(grants, [])
                self.assertEqual((r['result'], r['reason']), ('refused', 'append'))
            if w.lease is not None and r['appended']:
                self.assertIn(r['decision'], CONTINUING)
            if grants:
                self.assertIn(r['decision'], CONTINUING)
                self.assertIn(w.state, ('READY', 'REWORK'))

    def test_no_lease_survives_another_outcome_on_in_progress(self):
        """TASK-032 AC5: for a task IN_PROGRESS, whenever the record of an outcome other than CONTINUE or
        CONTINUE_WITH is in the log after the call, no lease is held, and the release came before every append."""
        for w, inp in worlds(3203):
            r = w.run(inp)
            if w.state != 'IN_PROGRESS' or r['decision'] in CONTINUING:
                continue
            if w.rec['record_id'] in w.ids_in_log():
                self.assertIsNone(w.lease)
                kinds = [kind for kind, _ in w.order]
                self.assertEqual(kinds[0], 'release')
            elif r['reason'] == 'lease':
                self.assertEqual([k for k, _ in w.order], ['release'])
            else:
                self.assertEqual(r['reason'], 'append')
                self.assertIsNone(w.lease)
                self.assertEqual([k for k, _ in w.order][:3], ['release', 'append', 'refused'])

    def test_every_outcome_is_reached(self):
        """TASK-032 AC13: the random worlds reach every decision, every state and both store answers."""
        seen = set()
        for w, inp in worlds(3204):
            r = w.run(inp)
            seen.add((w.state, r['decision'] if r['decision'] is not None else 'error', r['result']))
        states = {s for s, _, _ in seen}
        decisions = {d for _, d, _ in seen}
        results = {x for _, _, x in seen}
        self.assertEqual(states, {'READY', 'REWORK', 'IN_PROGRESS'})
        self.assertEqual(decisions, {d if d is not None else 'error' for d in DECISIONS})
        self.assertEqual(results, {'decided', 'refused'})


if __name__ == '__main__':
    unittest.main()

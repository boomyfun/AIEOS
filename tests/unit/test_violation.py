"""Unit tests of aieos_bootstrap.violation and adapter.violation (task TASK-052, rules R1 to R6 and R8): the violation
path with stand-ins for the writer's append_event and release_lease_token, bound to the real functions' signatures;
the fence tests decide each append with eventlog.append over an in-memory log and held lease, as the real writer does.
No process starts and no file is written or created. Each test names its criteria in its own docstring."""

import ast
import datetime
import inspect
import pathlib
import unittest

from aieos_bootstrap import adapter
from aieos_bootstrap import eventlog
from aieos_bootstrap import records
from aieos_bootstrap import violation
from aieos_bootstrap import writer

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap'
ROOT = str(pathlib.Path(__file__).resolve().parents[2] / 'no-such-violation-root')
TASK = 'TASK-200'
UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 10, 16, 10, 20, 0, tzinfo=UTC)
LATER = datetime.datetime(2026, 10, 16, 11, 0, 0, tzinfo=UTC)
TOKEN = {'epoch': 'e1', 'counter': 3}
REC = 'a hook (test)'
ABSENT = None
EVENT = 'violation-1'


def bound(real, args, kwargs):
    inspect.signature(real).bind(*args, **kwargs)


def observation(**over):
    o = {'record_id': 'obs-1', 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
         'recorder': REC, 'subject': TASK, 'evidence_type': 'write_outside_write_set', 'outcome': 'blocking',
         'blocking_kind': 'violation', 'refers_to': 'src/outside.py'}
    o.update(over)
    return o


class Memory:
    """The event log in memory and the store's held lease; append decides with eventlog.append as writer.append_event
    does (writer.py: the held lease on the task passed in, a fence refusal recorded as record.added)."""

    def __init__(self, lease=None):
        self.log = b''
        self.lease = lease
        self.calls = []

    def append(self, *args, **kwargs):
        bound(writer.append_event, args, kwargs)
        root, event_type, payload, event_id, appended_at, recorder = args
        self.calls.append(('append', event_type, event_id, kwargs.get('fencing_token')))
        task_id = kwargs.get('task_id')
        lease = self.lease if self.lease and self.lease['task_id'] == task_id else None
        r = eventlog.append(self.log, event_type, payload, event_id, appended_at, task_id=task_id,
                            fencing_token=kwargs.get('fencing_token'), lease=lease, recorder=recorder,
                            record_id='refusal-record-' + event_id)
        if r.result == 'appended':
            self.log += r.line
            return writer.WriteResult(r)
        if r.result == 'refused' and r.reason == 'fence' and r.record is not None:
            rec = eventlog.append(self.log, 'record.added', r.record, 'refusal-' + event_id, appended_at,
                                  task_id=task_id, recorder=recorder)
            if rec.result == 'appended':
                self.log += rec.line
            return writer.WriteResult(r, refusal=rec)
        return writer.WriteResult(r)

    def release(self, *args, **kwargs):
        bound(writer.release_lease_token, args, kwargs)
        root, task_id, token = args
        self.calls.append(('release', task_id, token))
        if self.lease is None or self.lease['task_id'] != task_id:
            return writer.StoreResult('refused', 'none', ['no lease is held'])
        if self.lease['fencing_token'] != token:
            return writer.StoreResult('refused', 'token', ['another token is held'])
        lease, self.lease = self.lease, None
        return writer.StoreResult('done', value=lease)

    def events(self):
        return [line.event for line in records.check_log(self.log).lines]


def held(token=TOKEN, task=TASK, expires_at=LATER):
    return {'task_id': task, 'fencing_token': dict(token), 'expires_at': expires_at}


def call(mem, **over):
    a = {'root': ROOT, 'task_id': TASK, 'fencing_token': dict(TOKEN), 'observation': observation(), 'event_id': EVENT,
         'recorder': REC, 'now': NOW}
    a.update(over)
    return violation.record(a['root'], a['task_id'], a['fencing_token'], a['observation'], a['event_id'],
                            a['recorder'], a['now'], append=mem.append, release=mem.release)


class Raising:
    def __init__(self, *args, **kwargs):
        raise RuntimeError('x')


class R1Arguments(unittest.TestCase):
    def test_each_wrong_argument_is_refused_before_any_call(self):
        """TASK-052 AC1, TASK-052 AC5, TASK-052 AC11: each wrong argument gives "argument" and no call is made; a
        well-formed call passes."""
        wrong = [{'root': ''}, {'task_id': 'TASK-x'}, {'fencing_token': {'epoch': '', 'counter': 1}},
                 {'fencing_token': {'epoch': 'e1', 'counter': True}}, {'fencing_token': ABSENT}, {'event_id': ''},
                 {'recorder': None}, {'now': NOW.replace(tzinfo=None)}, {'now': NOW.replace(microsecond=5)},
                 {'observation': 'x'}, {'observation': observation(outcome='fail')},
                 {'observation': observation(subject='TASK-201')},
                 {'observation': observation(source_class='human_authority')},
                 {'observation': observation(record_id='')}]
        for over in wrong:
            mem = Memory(held())
            r = call(mem, **over)
            self.assertEqual((r['result'], r['reason'], mem.calls), ('refused', 'argument', []), over)
            self.assertTrue(r['findings'], over)
        mem = Memory(held())
        self.assertEqual(call(mem)['result'], 'done')

    def test_the_defaults_are_the_writer_functions_at_call_time(self):
        """TASK-052 AC1, TASK-052 AC11: append and release default, at call time, to writer.append_event and
        writer.release_lease_token."""
        mem = Memory(held())
        saved = (writer.append_event, writer.release_lease_token)
        try:
            writer.append_event = mem.append
            writer.release_lease_token = mem.release
            r = violation.record(ROOT, TASK, dict(TOKEN), observation(), EVENT, REC, NOW)
        finally:
            writer.append_event, writer.release_lease_token = saved
        self.assertEqual(r['result'], 'done')
        self.assertEqual([c[0] for c in mem.calls], ['append', 'append', 'release'])


class R2Decision(unittest.TestCase):
    def test_the_decision_record(self):
        """TASK-052 AC2, TASK-052 AC11: the decision has exactly its keys, refers to the violation's event_id, passes
        records.check_decision, and names a declared source in uncovered only for agent_declared."""
        d = violation.decision_record(TASK, EVENT, observation())
        self.assertEqual(set(d), {'record_id', 'fact_kind', 'source_class', 'recorder', 'subject', 'decision',
                                  'outcomes_fired', 'refers_to', 'state_effect', 'uncovered'})
        self.assertEqual((d['record_id'], d['refers_to'], d['decision'], d['outcomes_fired'], d['state_effect']),
                         (EVENT + '/decision-record', EVENT, 'STOP: violation', ['STOP: violation'], []))
        self.assertEqual((d['fact_kind'], d['source_class'], d['recorder'], d['subject']),
                         ('interpretation', 'deterministic_tool_local', violation.RECORDER, TASK))
        self.assertEqual(records.check_decision('decision.execution', d), [])
        self.assertNotIn(violation.DECLARED, d['uncovered'])
        declared = violation.decision_record(TASK, EVENT, observation(source_class='agent_declared'))
        self.assertIn(violation.DECLARED, declared['uncovered'])

    def test_a_decision_the_check_refuses_appends_nothing(self):
        """TASK-052 AC2, TASK-052 AC11: a decision that records.check_decision refuses gives "decision" before any
        append."""
        mem = Memory(held())
        saved = violation.decision_record
        try:
            violation.decision_record = lambda *a: dict(saved(*a), decision='STOP: nothing')
            r = call(mem)
        finally:
            violation.decision_record = saved
        self.assertEqual((r['result'], r['reason'], mem.calls), ('refused', 'decision', []))


class R3Order(unittest.TestCase):
    def test_the_two_appends_then_the_release_with_the_token(self):
        """TASK-052 AC3, TASK-052 AC5, TASK-052 AC11: violation.detected, then the decision, each with the token,
        then the release by the token; the result's keys."""
        mem = Memory(held())
        r = call(mem)
        self.assertEqual(set(r), set(violation.RESULT_KEYS))
        self.assertEqual(mem.calls, [('append', 'violation.detected', EVENT, TOKEN),
                                     ('append', 'decision.execution', EVENT + '/decision', TOKEN),
                                     ('release', TASK, TOKEN)])
        self.assertEqual((r['result'], r['reason'], r['appended'], r['duplicate']),
                         ('done', None, [EVENT, EVENT + '/decision'], []))
        self.assertEqual(r['released']['fencing_token'], TOKEN)
        types = [(e['type'], e.get('task_id'), e.get('fencing_token')) for e in mem.events()]
        self.assertEqual(types, [('violation.detected', TASK, TOKEN), ('decision.execution', TASK, TOKEN)])
        self.assertEqual(mem.events()[1]['payload']['refers_to'], EVENT)

    def test_a_refusal_or_an_exception_at_each_step_stops_there(self):
        """TASK-052 AC3, TASK-052 AC5, TASK-052 AC11: a raising or refusing append or release stops the call with its
        step's reason, and no later step runs; no exception escapes."""
        for step, reason in ((0, 'violation'), (1, 'decision')):
            mem = Memory(held())
            real = mem.append
            count = [0]

            def flaky(*args, **kwargs):
                bound(writer.append_event, args, kwargs)
                count[0] += 1
                if count[0] == step + 1:
                    raise RuntimeError('x')
                return real(*args, **kwargs)
            r = violation.record(ROOT, TASK, dict(TOKEN), observation(), EVENT, REC, NOW, append=flaky,
                                 release=mem.release)
            self.assertEqual((r['result'], r['reason']), ('refused', reason))
            self.assertNotIn('release', [c[0] for c in mem.calls])
        mem = Memory(held())
        r = violation.record(ROOT, TASK, dict(TOKEN), observation(), EVENT, REC, NOW, append=mem.append,
                             release=lambda *a, **k: bound(writer.release_lease_token, a, k) or Raising())
        self.assertEqual((r['result'], r['reason']), ('refused', 'release'))
        mem = Memory(held())

        def other(*args, **kwargs):
            bound(writer.release_lease_token, args, kwargs)
            return writer.StoreResult('refused', 'store', ['broken'])
        r = violation.record(ROOT, TASK, dict(TOKEN), observation(), EVENT, REC, NOW, append=mem.append, release=other)
        self.assertEqual((r['result'], r['reason'], r['appended']), ('refused', 'release', [EVENT, EVENT + '/decision']))

    def test_a_release_refused_none_or_token_is_no_error(self):
        """TASK-052 AC3, TASK-052 AC11 (decision D-1000 E1): a release refused "none" or "token" gives "done",
        released None, with a finding."""
        for reason in ('none', 'token'):
            mem = Memory(held())

            def rel(*args, **kwargs):
                bound(writer.release_lease_token, args, kwargs)
                return writer.StoreResult('refused', reason, ['nothing'])
            r = violation.record(ROOT, TASK, dict(TOKEN), observation(), EVENT, REC, NOW, append=mem.append,
                                 release=rel)
            self.assertEqual((r['result'], r['reason'], r['released']), ('done', None, None))
            self.assertTrue(any(reason in f for f in r['findings']))

    def test_a_repeat_of_a_completed_call(self):
        """TASK-052 AC3, TASK-052 AC11 (decision D-1000 E1): a repeat of a completed call gives "done", both event_ids
        under duplicate, nothing appended, released None. The fence comes after the duplicate check, so the repeat
        is not refused by it."""
        mem = Memory(held())
        self.assertEqual(call(mem)['result'], 'done')
        log = mem.log
        r = call(mem)
        self.assertEqual((r['result'], r['appended'], r['duplicate'], r['released']),
                         ('done', [], [EVENT, EVENT + '/decision'], None))
        self.assertEqual(mem.log, log)


class R4Fence(unittest.TestCase):
    def test_a_session_not_holding_the_lease_is_refused_by_the_fence(self):
        """TASK-052 AC4, TASK-052 AC3, TASK-052 AC11: a foreign token, a lease on another task, an expired lease and no
        lease each give "fence" at the first append, with the refusal record in the log, labelled
        refused_submission (eventlog.refusal_record, as it is), and neither the decision nor the release is
        attempted."""
        cases = [held(token={'epoch': 'e1', 'counter': 4}), held(task='TASK-201'),
                 held(expires_at=NOW), None]
        for lease in cases:
            mem = Memory(lease)
            r = call(mem)
            self.assertEqual((r['result'], r['reason'], r['appended']), ('refused', 'fence', []), lease)
            self.assertEqual([c[:2] for c in mem.calls], [('append', 'violation.detected')], lease)
            events = mem.events()
            self.assertEqual([e['type'] for e in events], ['record.added'], lease)
            self.assertEqual(events[0]['payload']['evidence_type'], 'refused_submission')
            self.assertEqual(events[0]['payload']['refers_to'], EVENT)


class R5Result(unittest.TestCase):
    def test_no_exception_escapes_from_hostile_arguments(self):
        """TASK-052 AC5, TASK-052 AC1, TASK-052 AC11: an observation whose own methods raise gives a refusal, not an
        exception."""
        class Hostile(dict):
            def get(self, *a):
                raise RuntimeError('x')
        mem = Memory(held())
        r = call(mem, observation=Hostile(observation()))
        self.assertEqual((r['result'], r['reason'], mem.calls), ('refused', 'argument', []))
        self.assertEqual(set(r), set(violation.RESULT_KEYS))


class R6Adapter(unittest.TestCase):
    def test_the_pass_through_and_its_decision(self):
        """TASK-052 AC6, TASK-052 AC11 (decision D-1000 E2): adapter.violation checks its arguments, calls record once,
        and reports STOP: violation when the decision event is in the log after the call, appended or duplicate."""
        mem = Memory(held())
        r = adapter.violation(ROOT, TASK, dict(TOKEN), observation(), EVENT, REC, NOW, append=mem.append,
                              release=mem.release)
        self.assertEqual(set(r), set(adapter.RESULT_KEYS))
        self.assertEqual((r['result'], r['decision'], r['core']['result']), ('done', 'STOP: violation', 'done'))
        self.assertEqual(r['released']['fencing_token'], TOKEN)
        again = adapter.violation(ROOT, TASK, dict(TOKEN), observation(), EVENT, REC, NOW, append=mem.append,
                                  release=mem.release)
        self.assertEqual((again['result'], again['decision'], again['released']), ('done', 'STOP: violation', None))
        bad = adapter.violation(ROOT, 'TASK-x', dict(TOKEN), observation(), EVENT, REC, NOW, append=mem.append,
                                release=mem.release)
        self.assertEqual((bad['result'], bad['reason'], bad['core']), ('refused', 'argument', None))
        fenced = Memory(None)
        f = adapter.violation(ROOT, TASK, dict(TOKEN), observation(), EVENT, REC, NOW, append=fenced.append,
                              release=fenced.release)
        self.assertEqual((f['result'], f['reason'], f['decision'], f['core']['reason']),
                         ('refused', 'core', None, 'fence'))


class R8Purity(unittest.TestCase):
    def test_imports_and_no_file_process_clock_or_environment(self):
        """TASK-052 AC9, TASK-052 AC8, TASK-053 AC6: violation.py imports only datetime, re and aieos_bootstrap's
        records and writer; it calls no open, no subprocess, no clock and no environment; its docstring states the
        limits, the new one of task TASK-053 in place of the old, and marks its quotation as abridged."""
        tree = ast.parse((SRC / 'violation.py').read_bytes().decode('utf-8'))
        imports = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imports |= {a.name for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                imports |= {'%s.%s' % (n.module, a.name) for a in n.names}
        self.assertEqual(imports, {'datetime', 're', 'aieos_bootstrap.records', 'aieos_bootstrap.writer'})
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertFalse(attrs & {'now', 'utcnow', 'today', 'time', 'environ', 'getenv', 'system', 'popen', 'open'})
        self.assertFalse(names & {'open', 'exec', 'eval', 'compile', '__import__'})
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Assert)])
        doc = ast.get_docstring(tree)
        for words in ('makes acceptance reject (task TASK-053)', 'every later evaluation of it reject',
                      '(abridged, not verbatim)', 'section\n  11 point 12', 'refused_submission', 'stays READY',
                      'Purity'):
            self.assertIn(words, doc)
        for words in ('does not yet make acceptance reject', 'record is called only by'):
            self.assertNotIn(words, doc)


if __name__ == '__main__':
    unittest.main()

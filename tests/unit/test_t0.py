"""Unit tests of aieos_bootstrap.t0 (task TASK-060, rules R1 to R5 and R7): the T0 manual adapter's claim, start,
submit and end, with stand-ins for every function they call, each call bound to the real function's signature; the
fence cases run the real append logic, eventlog.append, over an event log kept in memory with a held lease. No process
starts and no file is written or created. Each test names its criteria in its own docstring."""

import ast
import datetime
import inspect
import os
import pathlib
import re
import unittest

from aieos_bootstrap import adapter
from aieos_bootstrap import eventlog
from aieos_bootstrap import records
from aieos_bootstrap import t0
from aieos_bootstrap import writer

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap'
TESTS = pathlib.Path(__file__).resolve().parents[1]
ROOT = str(pathlib.Path(__file__).resolve().parents[2] / 'no-such-t0-root')
REPO = str(pathlib.Path(__file__).resolve().parents[2])
TASK = 'TASK-100'
SID = 'session-1'
CODE = 'c' * 64
COMMIT = '3' * 40
NOW = datetime.datetime(2026, 10, 17, 12, 0, 0, tzinfo=datetime.timezone.utc)
LATER = NOW + datetime.timedelta(hours=1)
REC = 'a chat session (unit)'
TOKEN = {'epoch': 'e1', 'counter': 1}
CLAIMS = [{'kind': 'did', 'text': 'I added the module and its tests.'},
          {'kind': 'read_set', 'text': 'src/aieos_bootstrap/adapter.py'}]
FORBIDDEN_KEYS = ('outcome', 'dimension', 'gate', 'blocking_kind', 'commit', 'intent_versions', 'stands_for',
                  'decision_ref', 'models', 'approval_binding', 'risk_class', 'evidence_profile')


def bound(real, args, kwargs):
    inspect.signature(real).bind(*args, **kwargs)


class Result:
    """A stand-in WriteResult: only the fields the module reads."""

    def __init__(self, result, reason=None):
        self.result = result
        self.reason = reason


class Appends:
    """A stand-in for writer.append_event: records each call, bound to the real signature, and answers from a list
    (the last answer repeats); an answer that is an exception is raised."""

    def __init__(self, *answers):
        self.answers = list(answers) or [Result('appended')]
        self.calls = []

    def __call__(self, *args, **kwargs):
        bound(writer.append_event, args, kwargs)
        self.calls.append((args, kwargs))
        a = self.answers[min(len(self.calls), len(self.answers)) - 1]
        if isinstance(a, Exception):
            raise a
        return a


class Memory:
    """The event log as bytes in memory, appended by eventlog.append as the writer decides it, with one held lease (or
    none); a fence refusal's record is appended as the writer does it."""

    def __init__(self, lease=None):
        self.log = b''
        self.lease = lease

    def append_event(self, *args, **kwargs):
        bound(writer.append_event, args, kwargs)
        root, event_type, payload, event_id, appended_at, recorder = args
        task_id = kwargs.get('task_id')
        lease = self.lease if self.lease and self.lease['task_id'] == task_id else None
        r = eventlog.append(self.log, event_type, payload, event_id, appended_at, task_id=task_id,
                            fencing_token=kwargs.get('fencing_token'), lease=lease, recorder=recorder,
                            record_id='refusal-' + event_id)
        if r.result == 'appended':
            self.log += r.line
            return writer.WriteResult(r)
        if r.result == 'refused' and r.reason == 'fence' and r.record is not None:
            rec = eventlog.append(self.log, 'record.added', r.record, 'refusal-of-' + event_id, appended_at,
                                  task_id=task_id, recorder=recorder)
            if rec.result == 'appended':
                self.log += rec.line
            return writer.WriteResult(r, refusal=rec)
        return writer.WriteResult(r)

    def events(self):
        return [line.event for line in records.check_log(self.log).lines]


def run_claim(append, **over):
    a = dict(root=ROOT, task_id=TASK, session_id=SID, fencing_token=TOKEN, claims=CLAIMS, event_id='claims-1',
             recorder=REC, now=NOW)
    a.update(over)
    return t0.claim(append=append, **a)


class Calls:
    """A stand-in for an adapter function: records each call, bound to the real function, and returns its answer."""

    def __init__(self, real, answer):
        self.real = real
        self.answer = answer
        self.calls = []

    def __call__(self, *args, **kwargs):
        bound(self.real, args, kwargs)
        self.calls.append((args, kwargs))
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def adapter_result(result='done', **over):
    r = {'result': result, 'reason': None if result == 'done' else 'core', 'findings': [], 'core': None}
    r.update(dict.fromkeys(('decision', 'fencing_token', 'released')))
    r.update(over)
    return r


class R1Arguments(unittest.TestCase):
    def test_each_wrong_argument_of_claim_is_refused_before_any_call(self):
        """TASK-060 AC1, TASK-060 AC5: each wrong argument of claim gives "refused", reason "argument" and a finding
        naming it, and nothing is called (the passing case: the good arguments append)."""
        later_ms = NOW.replace(microsecond=5)
        bad = [{'root': ''}, {'root': 3}, {'task_id': 'TASK-x'}, {'task_id': 'task-1'}, {'session_id': ''},
               {'recorder': ''}, {'event_id': ''}, {'event_id': None}, {'now': later_ms},
               {'now': NOW.replace(tzinfo=None)}, {'now': NOW.astimezone(datetime.timezone(datetime.timedelta(hours=7)))},
               dict.fromkeys(['fencing_token']), {'fencing_token': {'epoch': 'e1'}}, {'fencing_token': {'epoch': '', 'counter': 1}},
               {'fencing_token': {'epoch': 'e1', 'counter': True}}, {'fencing_token': {'epoch': 'e1', 'counter': -1}},
               {'fencing_token': {'epoch': 'e1', 'counter': 1, 'x': 1}}, {'claims': []}, {'claims': 'did'},
               {'claims': [{'kind': 'did', 'text': 't'}] * 101}, {'claims': [{'kind': 'did'}]},
               {'claims': [{'kind': 'did', 'text': 't', 'x': 1}]}, {'claims': [{'kind': 'other', 'text': 't'}]},
               {'claims': [{'kind': 'did', 'text': ''}]}, {'claims': [{'kind': 'did', 'text': 'x' * 2001}]},
               {'claims': [{'kind': 'did', 'text': 'two\nlines'}]}, {'claims': [{'kind': 'did', 'text': 'a\rb'}]},
               {'claims': [{'kind': 'did', 'text': 'a b'}]}, {'claims': ['did']}]
        for over in bad:
            ap = Appends()
            r = run_claim(ap, **over)
            self.assertEqual((r['result'], r['reason'], ap.calls), ('refused', 'argument', []), over)
            self.assertTrue(r['findings'] and all(f.startswith('argument: ') for f in r['findings']), over)
        ap = Appends()
        self.assertEqual(run_claim(ap, claims=[{'kind': 'did', 'text': 'x' * 2000}] * 100)['result'], 'done')
        self.assertEqual(len(ap.calls), 100)

    def test_the_defaults_are_the_named_functions_at_call_time(self):
        """TASK-060 AC1, TASK-060 AC4: with no function given, claim calls writer.append_event and start, submit and
        end call adapter.start, adapter.submit and adapter.end, each read at call time; the module keeps no state."""
        seen = []
        saved = (writer.append_event, adapter.start, adapter.submit, adapter.end)
        try:
            writer.append_event = lambda *a, **k: bound(saved[0], a, k) or seen.append('append') or Result('appended')
            adapter.start = lambda *a, **k: bound(saved[1], a, k) or seen.append('start') or adapter_result()
            adapter.submit = lambda *a, **k: bound(saved[2], a, k) or seen.append('submit') or adapter_result()
            adapter.end = lambda *a, **k: bound(saved[3], a, k) or seen.append('end') or adapter_result()
            t0.claim(ROOT, TASK, SID, TOKEN, CLAIMS[:1], 'c-1', REC, NOW)
            t0.start(ROOT, TASK, SID, 'agent-1', {}, CODE, LATER, REC, NOW)
            t0.submit(ROOT, REPO, COMMIT, TASK, 'sub-1', REC, NOW)
            t0.end(ROOT, TASK, SID, TOKEN, NOW)
        finally:
            writer.append_event, adapter.start, adapter.submit, adapter.end = saved
        self.assertEqual(seen, ['append', 'start', 'submit', 'end'])
        names = {n.id for n in ast.walk(ast.parse((SRC / 't0.py').read_bytes().decode('utf-8')))
                 if isinstance(n, ast.Global)}
        self.assertEqual(names, set())


class R2Records(unittest.TestCase):
    def test_the_keys_and_values_of_both_kinds(self):
        """TASK-060 AC2: the record of each kind has exactly the seven keys with their values, no key of the forbidden
        list, and records.check_payload gives no finding for it."""
        ap = Appends()
        r = run_claim(ap)
        self.assertEqual(r['result'], 'done', r['findings'])
        recs = [c[0][2] for c in ap.calls]
        want_recorder = t0.RECORDER + ', session ' + SID + ', for ' + REC
        self.assertEqual(t0.RECORDER, 'the T0 manual adapter (aieos_bootstrap.t0)')
        self.assertEqual(recs, [
            {'record_id': 'claims-1/claim-1', 'fact_kind': 'claim', 'source_class': 'agent_declared',
             'recorder': want_recorder, 'subject': TASK, 'evidence_type': 'agent_claim', 'basis': CLAIMS[0]['text']},
            {'record_id': 'claims-1/claim-2', 'fact_kind': 'claim', 'source_class': 'agent_declared',
             'recorder': want_recorder, 'subject': TASK, 'evidence_type': 'read_set_estimate',
             'basis': CLAIMS[1]['text']}])
        for rec in recs:
            self.assertFalse(set(rec) & set(FORBIDDEN_KEYS))
            self.assertEqual(records.check_payload('record.added', rec), [])
        bad = dict(recs[0], outcome='pass')
        self.assertNotEqual(records.check_payload('record.added', dict(bad, fact_kind='not-a-kind')), [])

    def test_a_record_that_check_payload_refuses_appends_nothing(self):
        """TASK-060 AC2: when records.check_payload gives a finding for the record at a position, claim gives
        "refused", reason "record", naming the position, and nothing is appended (the passing case above)."""
        saved = records.check_payload
        try:
            records.check_payload = lambda t, p, where='payload': (
                [records.Finding('6.2:x', 'refused here')] if p['record_id'].endswith('/claim-2') else [])
            ap = Appends()
            r = run_claim(ap)
        finally:
            records.check_payload = saved
        self.assertEqual((r['result'], r['reason'], ap.calls, r['appended']), ('refused', 'record', [], []))
        self.assertIn('claim 2', r['findings'][0])
        self.assertIn('refused here', r['findings'][0])


class R3Appends(unittest.TestCase):
    def test_the_order_each_with_the_token(self):
        """TASK-060 AC3: each record is appended once, in order, as record.added with its event_id, now, the recorder,
        task_id and the fencing token."""
        ap = Appends()
        r = run_claim(ap)
        self.assertEqual(r['appended'], ['claims-1/claim-1', 'claims-1/claim-2'])
        for i, (args, kwargs) in enumerate(ap.calls, 1):
            self.assertEqual(args[:2], (ROOT, 'record.added'))
            self.assertEqual(args[3:], ('claims-1/claim-%d' % i, NOW, REC))
            self.assertEqual(kwargs, {'task_id': TASK, 'fencing_token': TOKEN})

    def test_a_refusal_or_an_exception_at_each_position_stops_there(self):
        """TASK-060 AC3, TASK-060 AC5: a fence refusal gives "fence", any other result or a raised exception gives
        "append", each naming the position, and no later record is appended."""
        three = CLAIMS + [{'kind': 'did', 'text': 'third'}]
        for pos in (1, 2, 3):
            for bad, reason in ((Result('refused', 'fence'), 'fence'), (Result('refused', 'event'), 'append'),
                                (Result(None), 'append'), (RuntimeError('boom'), 'append')):
                ap = Appends(*([Result('appended')] * (pos - 1) + [bad, Result('appended')]))
                r = run_claim(ap, claims=three)
                self.assertEqual((r['result'], r['reason']), ('refused', reason), (pos, bad))
                self.assertEqual(len(ap.calls), pos)
                self.assertEqual(r['appended'], ['claims-1/claim-%d' % i for i in range(1, pos)])
                self.assertIn('claim %d' % pos, r['findings'][0])

    def test_the_writers_fence_over_the_real_append_logic(self):
        """TASK-060 AC3: over eventlog.append with an in-memory log, a foreign token, a stale epoch, a lease on another
        task, an expired lease and no lease each give "fence" at the first append, with the writer's refusal record
        in the log and nothing else; the held lease's token appends."""
        held = {'task_id': TASK, 'fencing_token': TOKEN, 'expires_at': LATER}
        cases = [({'epoch': 'e1', 'counter': 2}, held), ({'epoch': 'e0', 'counter': 1}, held),
                 (TOKEN, dict(held, task_id='TASK-101')), (TOKEN, dict(held, expires_at=NOW)), (TOKEN, None)]
        for token, lease in cases:
            mem = Memory(lease)
            r = run_claim(mem.append_event, fencing_token=token)
            self.assertEqual((r['result'], r['reason'], r['appended']), ('refused', 'fence', []), (token, lease))
            ev = mem.events()
            self.assertEqual([e['type'] for e in ev], ['record.added'])
            self.assertEqual(ev[0]['event_id'], 'refusal-of-claims-1/claim-1')
            self.assertNotEqual(ev[0]['payload']['fact_kind'], 'claim')
        mem = Memory(held)
        r = run_claim(mem.append_event)
        self.assertEqual((r['result'], r['appended']), ('done', ['claims-1/claim-1', 'claims-1/claim-2']))
        self.assertEqual([e['payload']['fact_kind'] for e in mem.events()], ['claim', 'claim'])

    def test_a_repeat_of_a_completed_call_is_done_with_duplicates(self):
        """TASK-060 AC3: the same call again gives "done", every event_id under duplicate, and nothing appended."""
        mem = Memory({'task_id': TASK, 'fencing_token': TOKEN, 'expires_at': LATER})
        run_claim(mem.append_event)
        before = mem.log
        r = run_claim(mem.append_event)
        self.assertEqual((r['result'], r['appended'], r['duplicate']),
                         ('done', [], ['claims-1/claim-1', 'claims-1/claim-2']))
        self.assertEqual(mem.log, before)


class R4PassThrough(unittest.TestCase):
    def test_start_submit_and_end_pass_through_once(self):
        """TASK-060 AC4, TASK-060 AC5: each calls the adapter's function once with the arguments and the given
        functions, and returns its result under "core", with decision, fencing_token and released copied out."""
        st = Calls(adapter.start, adapter_result(decision='CONTINUE', fencing_token=TOKEN))
        fns = {'read_log': len}
        r = t0.start(ROOT, TASK, SID, 'agent-1', {}, CODE, LATER, REC, NOW, start=st, functions=fns)
        self.assertEqual(st.calls, [((ROOT, TASK, SID, 'agent-1', {}, CODE, LATER, REC, NOW), fns)])
        self.assertEqual((r['result'], r['core'], r['decision'], r['fencing_token']),
                         ('done', st.answer, 'CONTINUE', TOKEN))
        sb = Calls(adapter.submit, adapter_result(core={'result': 'submitted'}))
        r = t0.submit(ROOT, REPO, COMMIT, TASK, 'sub-1', REC, NOW, submit=sb)
        self.assertEqual((len(sb.calls), r['result'], r['core']), (1, 'done', sb.answer))
        en = Calls(adapter.end, adapter_result(released={'task_id': TASK}))
        r = t0.end(ROOT, TASK, SID, TOKEN, NOW, end=en)
        self.assertEqual((sb.calls[0][1], en.calls[0][1], r['released']), ({}, {}, {'task_id': TASK}))
        for call, fn in ((t0.end, Calls(adapter.end, adapter_result('refused'))),):
            r = call(ROOT, TASK, SID, None, NOW, end=fn)
            self.assertEqual((r['result'], r['reason'], r['core']), ('refused', 'core', fn.answer))

    def test_the_argument_checks_of_start_submit_and_end(self):
        """TASK-060 AC4, TASK-060 AC1: a wrong argument as TASK-051's checks name it, or functions with a key the
        adapter's function does not take, gives "argument" and the adapter is not called."""
        st = Calls(adapter.start, adapter_result())
        for over in ({'code_sha256': 'x'}, {'expires_at': NOW}, {'holder': ''}, {'inputs': []},
                     {'functions': {'other': len}}, {'functions': []}):
            a = dict(root=ROOT, task_id=TASK, session_id=SID, holder='agent-1', inputs={}, code_sha256=CODE,
                     expires_at=LATER, recorder=REC, now=NOW)
            a.update(over)
            self.assertEqual(t0.start(start=st, **a)['reason'], 'argument', over)
        sb = Calls(adapter.submit, adapter_result())
        self.assertEqual(t0.submit(ROOT, REPO, 'g' * 40, TASK, 'sub-1', REC, NOW, submit=sb)['reason'], 'argument')
        en = Calls(adapter.end, adapter_result())
        self.assertEqual(t0.end(ROOT, TASK, SID, {'epoch': 'e1'}, NOW, end=en)['reason'], 'argument')
        self.assertEqual(t0.end(ROOT, TASK, SID, TOKEN, NOW, end=en, functions={'append': len})['reason'], 'argument')
        self.assertEqual((st.calls, sb.calls, en.calls), ([], [], []))
        self.assertEqual(t0.end(ROOT, TASK, SID, None, NOW, end=en)['result'], 'done')


class R5Result(unittest.TestCase):
    def test_the_keys_and_no_exception_escapes(self):
        """TASK-060 AC5: every result has exactly RESULT_KEYS in every outcome; an argument whose own methods raise,
        and an adapter function that raises, are caught."""
        class Odd(datetime.tzinfo):
            def utcoffset(self, dt):
                raise RuntimeError('odd')
        odd = datetime.datetime(2026, 10, 17, 12, 0, 0, tzinfo=Odd())
        boom = RuntimeError('boom')
        results = [run_claim(Appends(), now=odd), run_claim(Appends(boom)), run_claim(Appends()),
                   t0.start(ROOT, TASK, SID, 'a', {}, CODE, LATER, REC, NOW, start=Calls(adapter.start, boom)),
                   t0.submit(ROOT, REPO, COMMIT, TASK, 's', REC, NOW, submit=Calls(adapter.submit, boom)),
                   t0.end(ROOT, TASK, SID, TOKEN, odd, end=Calls(adapter.end, adapter_result())),
                   t0.end(ROOT, TASK, SID, TOKEN, NOW, end=Calls(adapter.end, 'not a mapping'))]
        for r in results:
            self.assertEqual(tuple(r), t0.RESULT_KEYS)
            self.assertTrue(r['reason'] is None or r['reason'] in ('argument', 'record', 'fence', 'append', 'core'))
        self.assertEqual([r['reason'] for r in results], ['argument', 'append', None, 'core', 'core', 'argument', 'core'])
        self.assertTrue(os.path.isabs(ROOT))


class R7Purity(unittest.TestCase):
    def test_imports_and_no_file_process_clock_or_environment(self):
        """TASK-060 AC8, TASK-060 AC7, TASK-060 AC6: t0.py imports only datetime, re and aieos_bootstrap's adapter,
        records and writer; it calls no open, write, subprocess, clock, environment, exec, eval, compile, __import__
        or importlib, has no assert and no string naming the project-state directory; its docstring states what a
        claim proves and the limits."""
        text = (SRC / 't0.py').read_bytes().decode('utf-8')
        tree = ast.parse(text)
        imports = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imports |= {a.name for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                imports |= {'%s.%s' % (n.module, a.name) for a in n.names}
        self.assertEqual(imports, {'datetime', 're', 'aieos_bootstrap.adapter', 'aieos_bootstrap.records',
                                   'aieos_bootstrap.writer'})
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertFalse(attrs & {'now', 'utcnow', 'today', 'time', 'environ', 'getenv', 'system', 'popen', 'open',
                                  'write', 'run', 'import_module'})
        self.assertFalse(names & {'open', 'exec', 'eval', 'compile', '__import__', 'subprocess', 'importlib', 'os'})
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Assert)])
        self.assertNotIn('.' + 'aieos', text)
        doc = ' '.join(ast.get_docstring(tree).split())
        for words in ("a claim is an agent's statement, recorded and not checked", 'never the observed source',
                      'the evidence that counts comes only from the gates afterwards', 'section 11 point 10',
                      "the lease's expiry releases it", 'No adapter declaration is read or written',
                      "check 7's STOP: runtime insufficient applies as the core decides it",
                      'conformance scenarios (section 11 point 11) are not in this task',
                      'records.py has no ``session`` key', 'called only by its tests', '__init__.py is not changed',
                      'INV-004'):
            self.assertIn(words.lower(), doc.lower(), words)

    def test_every_test_names_its_criteria_and_writes_no_file(self):
        """TASK-060 AC9: every test function of the three test modules names at least one "TASK-060 ACn" in its own
        docstring and no other task's AC in qualified form, together AC1 to AC10; the modules call no open for
        writing, no tempfile, no removal and no subprocess (the failing case: a docstring naming another task's AC is
        found)."""
        named = set()
        for rel in ('unit/test_t0.py', 'integration/test_t0_session.py', 'property/test_t0_properties.py'):
            text = (TESTS / rel).read_bytes().decode('utf-8')
            tree = ast.parse(text)
            for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test')]:
                doc = ast.get_docstring(fn) or ''
                ids = re.findall(r'TASK-060 (AC[0-9]+)', doc)
                self.assertTrue(ids, (rel, fn.name))
                self.assertEqual(re.findall(r'TASK-(?!060 )[0-9]+ AC[0-9]+', doc), [], (rel, fn.name))
                named |= set(ids)
            imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
            self.assertFalse(imports & {'tempfile', 'shutil', 'subprocess'}, rel)
            attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
            self.assertFalse(attrs & {'remove', 'unlink', 'rmdir', 'mkdir', 'makedirs', 'write_bytes', 'write_text',
                                      'rmtree'}, rel)
            calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                     and n.func.id == 'open']
            self.assertEqual(calls, [], rel)
        self.assertEqual(named, {'AC%d' % i for i in range(1, 11)})
        self.assertEqual(re.findall(r'TASK-(?!060 )[0-9]+ AC[0-9]+', 'TASK-051 AC6'), ['TASK-051 AC6'])


if __name__ == '__main__':
    unittest.main()

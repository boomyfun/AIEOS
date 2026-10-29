"""Unit tests of aieos_bootstrap.replay (task TASK-051, rules R6 to R9): replays of documents built in the test, over
the real adapter, execution.execute, resume_check.check and submit.submit, with the event log kept in memory and
appended by eventlog.append as the writer decides it, and an in-memory stand-in store (its epoch, counter, leases and
sessions by the writer's rules). No process starts and no file is written or created. Each test names its criteria in its own
docstring."""

import ast
import copy
import datetime
import inspect
import os
import pathlib
import random
import unittest

from aieos_bootstrap import eventlog
from aieos_bootstrap import records
from aieos_bootstrap import replay
from aieos_bootstrap import resume_check
from aieos_bootstrap import violation
from aieos_bootstrap import writer

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap'
ROOT = str(pathlib.Path(__file__).resolve().parents[2] / 'no-such-replay-root')
TASK = 'TASK-100'
H = 'a' * 64
CODE = 'c' * 64
BASE = '1' * 40
HEAD = '2' * 40
COMMIT = '3' * 40
TREE = '4' * 40
UTC = datetime.timezone.utc
REC = 'replay:session-one'


def bound(real, args, kwargs):
    inspect.signature(real).bind(*args, **kwargs)


class Memory:
    """The event log as bytes in memory; append decides with eventlog.append as the real writer does, with the store's
    held lease for a fenced event."""

    def __init__(self, store, log=b''):
        self.store = store
        self.log = log
        self.roots = []

    def read_log(self, *args, **kwargs):
        bound(writer.read_log, args, kwargs)
        self.roots.append(args[0])
        return self.log

    def append_event(self, *args, **kwargs):
        bound(writer.append_event, args, kwargs)
        root, event_type, payload, event_id, appended_at, recorder = args
        self.roots.append(root)
        task_id = kwargs.get('task_id')
        token = kwargs.get('fencing_token')
        lease = self.store.leases.get(task_id) if task_id else None
        r = eventlog.append(self.log, event_type, payload, event_id, appended_at, task_id=task_id, fencing_token=token,
                            lease=lease, recorder=recorder, record_id='refusal-' + event_id)
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

    def lines(self):
        return records.check_log(self.log).lines


class Store:
    """The local store in memory: its epoch and counter, leases and sessions, by the writer's rules."""

    def __init__(self, epoch=None, counter=0):
        self.epoch = epoch
        self.counter = counter
        self.leases = {}
        self.sessions = {}
        self.roots = []

    def open_store(self, *args, **kwargs):
        bound(writer.open_store, args, kwargs)
        self.roots.append(args[0])
        epoch = args[1] if len(args) > 1 else kwargs.get('epoch')
        if self.epoch is None:
            self.epoch = epoch
        elif epoch is not None and epoch != self.epoch:
            raise ValueError('the given epoch differs from the store\'s own epoch')
        return {'epoch': self.epoch, 'counter': self.counter}

    def start_session(self, *args, **kwargs):
        bound(writer.start_session, args, kwargs)
        root, session_id, holder, now = args
        self.roots.append(root)
        if session_id in self.sessions:
            return writer.StoreResult('refused', 'started', ['started'])
        self.sessions[session_id] = [holder, None]
        return writer.StoreResult('done')

    def end_session(self, *args, **kwargs):
        bound(writer.end_session, args, kwargs)
        root, session_id, now = args
        self.roots.append(root)
        s = self.sessions.get(session_id)
        if s is None or s[1] is not None:
            return writer.StoreResult('refused', 'session', ['not started or ended'])
        s[1] = now
        return writer.StoreResult('done', value=[])

    def grant_lease(self, *args, **kwargs):
        bound(writer.grant_lease, args, kwargs)
        root, task_id, task_state, holder, session_id, now, expires_at = args
        self.roots.append(root)
        if task_state not in writer.GRANT_STATES or task_id in self.leases:
            return writer.StoreResult('refused', 'state', ['no grant'])
        s = self.sessions.get(session_id)
        if s is None or s[0] != holder or s[1] is not None:
            return writer.StoreResult('refused', 'session', ['not a started session of the holder'])
        self.counter += 1
        self.leases[task_id] = {'task_id': task_id, 'fencing_token': {'epoch': self.epoch, 'counter': self.counter},
                                'expires_at': expires_at}
        return writer.StoreResult('done', value=copy.deepcopy(self.leases[task_id]))

    def release_lease_token(self, *args, **kwargs):
        bound(writer.release_lease_token, args, kwargs)
        root, task_id, token = args
        self.roots.append(root)
        lease = self.leases.get(task_id)
        if lease is None:
            return writer.StoreResult('refused', 'none', ['no lease is held'])
        if lease['fencing_token'] != token:
            return writer.StoreResult('refused', 'token', ['another token is held'])
        return writer.StoreResult('done', value=self.leases.pop(task_id))

    def held_lease(self, *args, **kwargs):
        bound(writer.held_lease, args, kwargs)
        self.roots.append(args[0])
        lease = self.leases.get(args[1])
        return copy.deepcopy(lease) if lease else None


def functions(store, mem):
    return {'open_store': store.open_store, 'append_event': mem.append_event, 'start_session': store.start_session,
            'end_session': store.end_session, 'read_log': mem.read_log, 'grant_lease': store.grant_lease,
            'release_lease_token': store.release_lease_token, 'held_lease': store.held_lease}


def inputs(log_seq):
    """Well-formed Resume Check inputs whose checks all pass (CONTINUE) for a READY task at log_seq."""
    return {
        'task_id': TASK, 'log_seq': log_seq, 'task_state': 'READY',
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


def commit_text(task=TASK, fence='e-replay:1'):
    return ('tree %s\nauthor Tester <tester> 1700000000 +0000\ncommitter Tester <tester> 1700000000 +0000\n\n'
            'Do the work\n\nThe body.\n\nAIEOS-Task: %s\nAIEOS-Fence: %s\n' % (TREE, task, fence))


def document(**over):
    d = {
        'replay_id': 'session-one', 'recorder': REC, 'epoch': 'e-replay',
        'setup': [
            {'type': 'task.drafted', 'payload': {'contract_version': 'v1', 'contract_hash': H}, 'event_id': 'drafted-1',
             'appended_at': '2026-10-16T09:00:00Z', 'task_id': TASK},
            {'type': 'task.approved', 'payload': {'contract_version': 'v1', 'contract_hash': H,
                                                  'approval_record': 'appr-1'},
             'event_id': 'approved-1', 'appended_at': '2026-10-16T09:01:00Z', 'task_id': TASK}],
        'session': {'task_id': TASK, 'session_id': 'session-1', 'holder': 'agent-1', 'inputs': inputs(2),
                    'code_sha256': CODE, 'start_at': '2026-10-16T10:00:00Z', 'expires_at': '2026-10-16T11:00:00Z',
                    'expected_token': {'epoch': 'e-replay', 'counter': 1}},
        'submission': {'commit_id': COMMIT, 'commit_text': commit_text(), 'event_id': 'submitted-1',
                       'at': '2026-10-16T10:30:00Z'},
        'end_at': '2026-10-16T10:40:00Z',
    }
    d.update(over)
    return d


def run(doc, store=None, mem=None):
    store = Store() if store is None else store
    mem = Memory(store) if mem is None else mem
    return replay.replay(doc, ROOT, functions(store, mem)), store, mem


class R6Document(unittest.TestCase):
    def test_each_malformed_document_is_refused_before_any_call(self):
        """TASK-051 AC6, TASK-051 AC8: each document out of form gives "refused", reason "document", and nothing is
        called (the passing case: the well-formed document runs)."""
        good = document()
        bad = [dict(good, extra=1), {k: v for k, v in good.items() if k != 'end_at'}, dict(good, replay_id=''),
               dict(good, recorder='live:session'), dict(good, recorder='replay:'), dict(good, epoch=''),
               dict(good, setup={}), dict(good, setup=[{'type': 'task.drafted'}]),
               dict(good, end_at='2026-10-16 10:40:00'), dict(good, end_at='2026-02-30T10:40:00Z'),
               dict(good, session=dict(good['session'], code_sha256='x')),
               dict(good, session=dict(good['session'], expires_at='2026-10-16T09:00:00Z')),
               dict(good, session=dict(good['session'], expected_token={'epoch': 'e'})),
               dict(good, submission=dict(good['submission'], commit_id='g' * 40)),
               dict(good, submission={'commit_id': COMMIT}), 'not a mapping']
        self.assertTrue(os.path.isabs(ROOT))  # D-988 M1: submit.submit refuses a relative root on any platform
        for doc in bad:
            store = Store()
            mem = Memory(store)
            r, _, _ = run(doc, store, mem)
            self.assertEqual((r['result'], r['reason']), ('refused', 'document'), doc)
            self.assertEqual((r['steps'], mem.roots, store.roots), ([], [], []), doc)
        r, _, _ = run(good)
        self.assertEqual(r['result'], 'done', r['findings'])

    def test_unknown_functions_and_an_empty_root_are_refused(self):
        """TASK-051 AC8, TASK-051 AC6: a functions mapping with another key, or an empty root, is refused "document"."""
        self.assertEqual(replay.replay(document(), ROOT, {'other': len})['reason'], 'document')
        self.assertEqual(replay.replay(document(), '', None)['reason'], 'document')


class R7Run(unittest.TestCase):
    def test_the_call_order_and_the_end_to_end_records(self):
        """TASK-051 AC7, TASK-051 AC2, TASK-051 AC3, TASK-051 AC4: read_log, open_store, the setup appends, start,
        submit and end in that order; CONTINUE grants the token epoch e-replay counter 1, the submission is appended
        with it and the lease released, and the session is closed."""
        r, store, mem = run(document())
        self.assertEqual(r['result'], 'done', r['findings'])
        self.assertEqual([s['step'] for s in r['steps']],
                         ['read_log', 'open_store', 'append_event', 'append_event', 'start', 'submit', 'end'])
        self.assertEqual(r['fencing_token'], {'epoch': 'e-replay', 'counter': 1})
        types = [line.event['type'] for line in mem.lines()]
        self.assertEqual(types, ['task.drafted', 'task.approved', 'decision.execution', 'task.submitted'])
        self.assertEqual(store.leases, {})
        self.assertIsNotNone(store.sessions['session-1'][1])

    def test_every_call_carries_the_given_root_and_the_replay_recorder(self):
        """TASK-051 AC7 (M1 of decision D-983, N2 of decision D-984, erratum E1 of decision D-987): every call carries
        the root given; in the log the run produced, the set of recorders named in the records is a subset of {the
        document's recorder, resume_check.RECORDER}, the document's on every record the replay's own calls make (a
        fence refusal's record.added) and resume_check.RECORDER only on decision.execution records; every record any
        line carries has source_class deterministic_tool_local or none; no envelope carries a recorder."""
        for doc in (document(), document(submission=dict(document()['submission'],
                                                         commit_text=commit_text(fence='e-replay:9')))):
            r, store, mem = run(doc)
            self.assertEqual(set(mem.roots) | set(store.roots), {ROOT})
            seen = set()
            for line in mem.lines():
                self.assertNotIn('recorder', line.event)
                payload = line.event['payload']
                if not isinstance(payload, dict):
                    continue
                self.assertIn(payload.get('source_class'), (None, 'deterministic_tool_local'))
                if 'recorder' in payload:
                    seen.add(payload['recorder'])
                    want = resume_check.RECORDER if line.event['type'] == 'decision.execution' else REC
                    self.assertEqual(payload['recorder'], want, line.event['type'])
            self.assertLessEqual(seen, {REC, resume_check.RECORDER})
            self.assertIn(resume_check.RECORDER, seen)
        added = [line.event['payload'] for line in mem.lines() if line.event['type'] == 'record.added']
        self.assertEqual([(p['recorder'], p['source_class']) for p in added], [(REC, 'deterministic_tool_local')])
        self.assertEqual(r['reason'], 'submit')

    def test_a_used_log_or_store_is_refused_before_any_append(self):
        """TASK-051 AC7, TASK-051 AC8 (N1 of decision D-984): an empty log and a new store at counter 0 pass; a log
        that is not empty, a store with counter above 0, and a store with another epoch are each refused "store" with
        nothing appended."""
        store = Store()
        line = eventlog.append(b'', 'task.drafted', {'contract_version': 'v1', 'contract_hash': H}, 'x-1',
                               datetime.datetime(2026, 10, 1, 0, 0, 0, tzinfo=UTC), task_id=TASK).line
        mem = Memory(store, log=line)
        r, _, _ = run(document(), store, mem)
        self.assertEqual((r['reason'], mem.log), ('store', line))
        self.assertEqual(([s['step'] for s in r['steps']], store.roots), (['read_log'], []))  # open_store not called

        class OtherEpoch(Store):
            def open_store(self, *args, **kwargs):
                bound(writer.open_store, args, kwargs)
                return {'epoch': 'another-epoch', 'counter': 0}  # no raise: replay's own comparison refuses

        for store in (Store('e-replay', counter=3), Store('another-epoch'), OtherEpoch()):
            mem = Memory(store)
            r, _, _ = run(document(), store, mem)
            self.assertEqual((r['result'], r['reason'], mem.log), ('refused', 'store', b''))
            self.assertNotIn('start', [s['step'] for s in r['steps']])
        self.assertEqual(run(document())[0]['result'], 'done')

    def test_a_commit_text_that_cannot_be_encoded(self):
        """TASK-051 AC6, TASK-051 AC8 (D-990, the reviews' blocking finding): a commit_text with a lone surrogate is
        refused "document" before any call; and if building the commit reader raised after a grant, end is still
        called and no lease is left held."""
        doc = document(submission=dict(document()['submission'], commit_text='Subject\ud800'))
        store = Store()
        mem = Memory(store)
        r, _, _ = run(doc, store, mem)
        self.assertEqual((r['result'], r['reason'], r['steps'], mem.roots, store.roots),
                         ('refused', 'document', [], [], []))
        saved = replay._commit_reader
        try:
            def broken(commit_id, text):
                raise UnicodeEncodeError('utf-8', text, 0, 1, 'a test')
            replay._commit_reader = broken
            r, store, _ = run(document())
        finally:
            replay._commit_reader = saved
        self.assertEqual((r['result'], r['reason'], r['steps'][-1]['step'], store.leases), ('refused', 'submit', 'end', {}))

    def test_the_commit_stand_in_answers_only_the_two_reads(self):
        """TASK-051 AC7: the read function given to submit answers cat-file -t and -p of the document's commit, and
        refuses any other call."""
        read = replay._commit_reader(COMMIT, 'text')
        self.assertEqual(read('r', ['cat-file', '-t', COMMIT])['out'], b'commit\n')
        self.assertEqual(read('r', ['cat-file', '-p', COMMIT])['out'], b'text')
        for args in (['cat-file', '-t', '5' * 40], ['log', '-1'], ['cat-file', '-p']):
            self.assertIsNotNone(read('r', args)['error'], args)

    def test_a_token_difference_stops_and_still_ends(self):
        """TASK-051 AC7, TASK-051 AC8 (M2 of decision D-983): a granted token that differs from the expected one gives
        "refused", reason "token"; no submission is made, and end releases the lease and closes the session."""
        doc = document(session=dict(document()['session'], expected_token={'epoch': 'e-replay', 'counter': 2}))
        r, store, mem = run(doc)
        self.assertEqual((r['result'], r['reason']), ('refused', 'token'))
        self.assertEqual([s['step'] for s in r['steps']][-2:], ['start', 'end'])
        self.assertEqual(store.leases, {})
        self.assertNotIn('task.submitted', [line.event['type'] for line in mem.lines()])


class R8Refusals(unittest.TestCase):
    def test_a_refusal_at_each_step(self):
        """TASK-051 AC8: a refused setup append, a refused start (inputs out of step with the log) and a refused end
        each stop the run with their reason; no exception escapes."""
        doc = document(setup=document()['setup'] * 2)
        self.assertEqual(run(doc)[0]['reason'], 'setup')
        doc = document(session=dict(document()['session'], inputs=inputs(7)))
        r, store, _ = run(doc)
        self.assertEqual((r['reason'], store.leases), ('start', {}))
        self.assertEqual(r['steps'][-1]['step'], 'start')  # AC8 and reading R3: no end; the row is left open
        self.assertIsNone(store.sessions['session-1'][1])
        store = Store()
        mem = Memory(store)
        fns = functions(store, mem)

        def end_refused(*args, **kwargs):
            bound(writer.end_session, args, kwargs)
            return writer.StoreResult('refused', 'ended', ['ended'])

        def read_raises(*args, **kwargs):
            bound(writer.read_log, args, kwargs)
            raise RuntimeError('x')

        fns['end_session'] = end_refused
        self.assertEqual(replay.replay(document(), ROOT, fns)['reason'], 'end')
        fns = functions(Store(), Memory(Store()))
        fns['read_log'] = read_raises
        self.assertEqual(replay.replay(document(), ROOT, fns)['reason'], 'store')

    def test_end_after_a_granted_lease_when_the_submission_is_refused(self):
        """TASK-051 AC8: a refused submission (a commit naming another task) still calls end, which releases the
        lease; the result has exactly RESULT_KEYS."""
        doc = document(submission=dict(document()['submission'], commit_text=commit_text(task='TASK-101')))
        r, store, _ = run(doc)
        self.assertEqual((r['result'], r['reason']), ('refused', 'submit'))
        self.assertEqual(r['steps'][-1]['step'], 'end')
        self.assertEqual(store.leases, {})
        self.assertEqual(tuple(r), replay.RESULT_KEYS)

    def test_two_runs_over_equal_documents_are_equal(self):
        """TASK-051 AC8 (property, fixed seed): for random documents (with or without a submission, an expected token or
        not, a fence that fits or not), two runs over equal documents and equal empty stand-in roots give equal steps
        and equal logs."""
        rng = random.Random(51)
        outcomes = set()
        for _ in range(40):
            doc = document()
            if rng.random() < 0.3:
                doc['submission'] = None
            if rng.random() < 0.3:
                doc['session']['expected_token'] = None
            if rng.random() < 0.3 and doc['submission'] is not None:
                doc['submission']['commit_text'] = commit_text(fence='e-replay:%d' % rng.randint(1, 3))
            r1, _, m1 = run(copy.deepcopy(doc))
            r2, _, m2 = run(copy.deepcopy(doc))
            self.assertEqual(r1, r2)
            self.assertEqual(m1.log, m2.log)
            self.assertIn('decision.execution', [line.event['type'] for line in m1.lines()])
            outcomes.add((r1['result'], r1['reason']))
        self.assertIn(('done', None), outcomes)  # not vacuous: runs end done and refused alike
        self.assertIn(('refused', 'submit'), outcomes)


def violation_doc(**over):
    """A document whose session is stopped by a violation (TASK-052 AC7): no submission."""
    obs = {'record_id': 'obs-1', 'fact_kind': 'observation', 'source_class': 'agent_declared', 'recorder': REC,
           'subject': TASK, 'evidence_type': 'write_outside_write_set', 'outcome': 'blocking',
           'blocking_kind': 'violation', 'refers_to': 'src/outside.py'}
    v = {'observation': obs, 'event_id': 'violation-1', 'at': '2026-10-16T10:20:00Z'}
    v.update(over.pop('violation', {}))
    return document(submission=None, violation=v, **over)


class R10Violation(unittest.TestCase):
    def test_the_document_forms_of_a_violation(self):
        """TASK-052 AC7: a violation mapping of the wrong form, a violation with a submission, an observation of
        another class, and an observation recorded under another recorder are each refused "document" before any
        call; a document without violation is unchanged."""
        bad = [document(violation={'observation': {}, 'event_id': 'v'}),
               document(submission=None, violation={'observation': {}, 'event_id': 'v'}),
               dict(violation_doc(), submission=document()['submission']),
               violation_doc(violation={'observation': dict(violation_doc()['violation']['observation'],
                                                            source_class='human_authority')}),
               violation_doc(violation={'observation': dict(violation_doc()['violation']['observation'],
                                                            recorder='replay:another')}),
               violation_doc(violation={'event_id': ''}), violation_doc(violation={'at': '2026-10-16 10:20'})]
        for doc in bad:
            store = Store()
            mem = Memory(store)
            r, _, _ = run(doc, store, mem)
            self.assertEqual((r['result'], r['reason'], r['steps'], mem.roots), ('refused', 'document', [], []))
        self.assertEqual(run(document())[0]['result'], 'done')

    def test_the_run_with_a_violation(self):
        """TASK-052 AC7, TASK-052 AC3, TASK-052 AC11: start, the violation with the granted token, then end, whose
        release finds no lease ("none", no error); the log holds violation.detected and the STOP: violation decision
        that refers to it; no lease is left; the extended E1 sets hold."""
        r, store, mem = run(violation_doc())
        self.assertEqual((r['result'], r['reason']), ('done', None))
        self.assertEqual([s['step'] for s in r['steps']], ['read_log', 'open_store', 'append_event', 'append_event',
                                                           'start', 'violation', 'end'])
        self.assertEqual(r['steps'][5]['result']['decision'], 'STOP: violation')
        self.assertEqual(r['steps'][5]['result']['released']['fencing_token'], {'epoch': 'e-replay', 'counter': 1})
        self.assertIsNone(r['steps'][6]['result']['released'])
        self.assertIn('release: nothing released (none)', r['steps'][6]['result']['findings'])
        self.assertEqual(store.leases, {})
        events = [line.event for line in mem.lines()]
        types = [e['type'] for e in events]
        self.assertEqual(types[-2:], ['violation.detected', 'decision.execution'])
        stop = events[-1]['payload']
        self.assertEqual((stop['decision'], stop['refers_to'], stop['recorder']),
                         ('STOP: violation', 'violation-1', violation.RECORDER))
        recorders, classes = set(), set()
        for e in events:
            p = e['payload']
            if e['type'] in records.RECORD_PAYLOAD_TYPES:
                recorders.add(p.get('recorder'))
                classes.add(p.get('source_class'))
                if p.get('recorder') == violation.RECORDER:
                    self.assertEqual((e['type'], p.get('decision')), ('decision.execution', 'STOP: violation'))
        self.assertLessEqual(recorders, {REC, resume_check.RECORDER, violation.RECORDER})
        self.assertLessEqual(classes, {'deterministic_tool_local', 'agent_declared', None})
        self.assertNotIn('task.submitted', types)

    def test_a_refused_violation_still_ends(self):
        """TASK-052 AC7, TASK-052 AC4, TASK-052 AC11: when the core refuses the violation (here by the fence, the
        lease gone before it), the replay gives "violation" and end is still called."""
        store = Store()
        mem = Memory(store)
        fns = functions(store, mem)
        real = mem.append_event

        def drop_then_append(*args, **kwargs):
            if args[1] == 'violation.detected':
                store.leases.clear()
            return real(*args, **kwargs)
        fns['append_event'] = drop_then_append
        r = replay.replay(violation_doc(), ROOT, fns)
        self.assertEqual((r['result'], r['reason'], r['steps'][-1]['step']), ('refused', 'violation', 'end'))
        self.assertIn('record.added', [line.event['type'] for line in mem.lines()])
        refused = [line.event['payload'] for line in mem.lines()
                   if line.event['type'] == 'record.added' and line.event['payload'].get('evidence_type') == 'refused_submission']
        self.assertEqual([(p['refers_to'], p['subject']) for p in refused], [('violation-1', TASK)])

    def test_two_runs_with_a_violation_are_equal(self):
        """TASK-052 AC7, TASK-052 AC11: two replays with a violation over equal documents and equal empty stand-in
        roots give equal steps and equal logs (fixed seeds)."""
        rng = random.Random(52)
        for _ in range(10):
            doc = violation_doc(violation={'event_id': 'violation-%d' % rng.randrange(1000)})
            r1, _, m1 = run(copy.deepcopy(doc))
            r2, _, m2 = run(copy.deepcopy(doc))
            self.assertEqual(r1, r2)
            self.assertEqual(m1.log, m2.log)
            self.assertEqual(r1['result'], 'done')


class R9Purity(unittest.TestCase):
    def test_imports_and_no_file_process_clock_or_environment(self):
        """TASK-051 AC10, TASK-051 AC9, TASK-052 AC9, TASK-052 AC8, TASK-053 AC6: replay.py imports only datetime, re
        and aieos_bootstrap's adapter and writer; it calls no open, no subprocess, no clock and no environment; its
        docstring states the limits, task TASK-053's in place of the old one."""
        tree = ast.parse((SRC / 'replay.py').read_bytes().decode('utf-8'))
        imports = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imports |= {a.name for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                imports |= {'%s.%s' % (n.module, a.name) for a in n.names}
        self.assertEqual(imports, {'datetime', 're', 'aieos_bootstrap.adapter', 'aieos_bootstrap.writer'})
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertFalse(attrs & {'now', 'utcnow', 'today', 'environ', 'getenv', 'system', 'popen', 'open'})
        self.assertFalse(names & {'open', 'exec', 'eval', 'compile', '__import__'})
        doc = ast.get_docstring(tree)
        for words in ('no read-set observation', 'section 11 point 10', 'line 49', 'C6 stays unmeasured',
                      'N1 of', 'opens no file', 'one run at a time',
                      'makes every later evaluation of the task reject (task TASK-053)'):
            self.assertIn(words, doc)
        self.assertNotIn('does not yet make acceptance reject', doc)


if __name__ == '__main__':
    unittest.main()

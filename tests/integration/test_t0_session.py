"""Integration tests of aieos_bootstrap.t0 (task TASK-060, rule R6): an end-to-end T0 session over the real adapter,
execution.execute and resume_check.check, with the event log kept in memory and appended by eventlog.append as the
writer decides it, and an in-memory stand-in store (its epoch, counter, leases and sessions by the writer's rules);
then governor.evaluate over the records, called as evaluation.evaluate_task calls it. No process starts and no file
is written or created. Each test names its criteria in its own docstring."""

import copy
import datetime
import inspect
import pathlib
import unittest

from aieos_bootstrap import eventlog
from aieos_bootstrap import governor
from aieos_bootstrap import records
from aieos_bootstrap import t0
from aieos_bootstrap import writer

ROOT = str(pathlib.Path(__file__).resolve().parents[2] / 'no-such-t0-root')
TASK = 'TASK-100'
H = 'a' * 64
CODE = 'c' * 64
BASE = '1' * 40
HEAD = '2' * 40
COMMIT = '3' * 40
UTC = datetime.timezone.utc
T_DRAFT = datetime.datetime(2026, 10, 17, 9, 0, 0, tzinfo=UTC)
NOW = datetime.datetime(2026, 10, 17, 10, 0, 0, tzinfo=UTC)
LATER = NOW + datetime.timedelta(hours=1)
REC = 'a chat session (integration)'
CLAIMS = [{'kind': 'did', 'text': 'I wrote the change and ran the suite.'},
          {'kind': 'read_set', 'text': 'src/app/util/helpers.py'}]
IV = {'SPEC-003': 'v4'}
CI = 'deterministic_tool_external_ci'


def bound(real, args, kwargs):
    inspect.signature(real).bind(*args, **kwargs)


class Memory:
    """The event log as bytes in memory; append decides with eventlog.append as the real writer does, with the store's
    held lease for a fenced event."""

    def __init__(self, store):
        self.store = store
        self.log = b''

    def read_log(self, *args, **kwargs):
        bound(writer.read_log, args, kwargs)
        return self.log

    def append_event(self, *args, **kwargs):
        bound(writer.append_event, args, kwargs)
        root, event_type, payload, event_id, appended_at, recorder = args
        task_id = kwargs.get('task_id')
        lease = self.store.leases.get(task_id) if task_id else None
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


class Store:
    """The local store in memory: its epoch and counter, leases and sessions, by the writer's rules."""

    def __init__(self, epoch='e-t0'):
        self.epoch = epoch
        self.counter = 0
        self.leases = {}
        self.sessions = {}

    def start_session(self, *args, **kwargs):
        bound(writer.start_session, args, kwargs)
        root, session_id, holder, now = args
        if session_id in self.sessions:
            return writer.StoreResult('refused', 'started', ['started'])
        self.sessions[session_id] = [holder, None]
        return writer.StoreResult('done')

    def end_session(self, *args, **kwargs):
        bound(writer.end_session, args, kwargs)
        root, session_id, now = args
        s = self.sessions.get(session_id)
        if s is None or s[1] is not None:
            return writer.StoreResult('refused', 'session', ['not started or ended'])
        s[1] = now
        return writer.StoreResult('done', value=[])

    def grant_lease(self, *args, **kwargs):
        bound(writer.grant_lease, args, kwargs)
        root, task_id, task_state, holder, session_id, now, expires_at = args
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
        lease = self.leases.get(task_id)
        if lease is None:
            return writer.StoreResult('refused', 'none', ['no lease is held'])
        if lease['fencing_token'] != token:
            return writer.StoreResult('refused', 'token', ['another token is held'])
        return writer.StoreResult('done', value=self.leases.pop(task_id))

    def held_lease(self, *args, **kwargs):
        bound(writer.held_lease, args, kwargs)
        lease = self.leases.get(args[1])
        return copy.deepcopy(lease) if lease else None


def inputs(log_seq, runtime=None):
    """The Resume Check inputs that TASK-051's tests supply for CONTINUE (tests/unit/test_replay.py:155-184): a READY
    task, matching contract hashes, a done dependency, an applicable article not violated, the intent versions
    current, and for check 7 the input runtime {'adapter': 'an-adapter', 'max_risk': 'high'} with the contract's risk
    medium (an input of the test, not a declaration file)."""
    return {
        'task_id': TASK, 'log_seq': log_seq, 'task_state': 'READY',
        'contract': {
            'task': TASK, 'contract_version': 'v1', 'task_type': 'implementation', 'risk': 'medium',
            'input_state': {'base_commit': BASE, 'depends_on': ['TASK-099'], 'intent_versions': dict(IV)},
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
        'intent_current': dict(IV),
        'dependencies': {'TASK-099': {'state': 'DONE', 'stale_evidence': False}},
        'articles': [{'id': 'INV-001', 'scope': {'paths': ['src/**'], 'components': []},
                      'applicability': {'task_types': ['implementation']}, 'violated': False}],
        'runtime': runtime if runtime is not None else {'adapter': 'an-adapter', 'max_risk': 'high'},
        'risk_rules': [{'match': {'paths': ['src/**']}, 'risk': 'medium'}],
        'policy_version': 'v2',
        'budget_use': {'retries': {'used': 0, 'reported': True}, 'tokens': {'used': '10k', 'reported': True},
                       'wall_time': {'used': '10m', 'reported': True}, 'human_attention': {'used': '0m', 'reported': True}},
    }


def set_up():
    store = Store()
    mem = Memory(store)
    for event_type, payload, eid in (
            ('task.drafted', {'contract_version': 'v1', 'contract_hash': H}, 'drafted-1'),
            ('task.approved', {'contract_version': 'v1', 'contract_hash': H, 'approval_record': 'appr-1'},
             'approved-1')):
        r = mem.append_event(ROOT, event_type, payload, eid, T_DRAFT, REC, task_id=TASK)
        assert r.result == 'appended', r
    return store, mem


def start_fns(store, mem):
    return {'start_session': store.start_session, 'read_log': mem.read_log, 'append': mem.append_event,
            'grant': store.grant_lease, 'release': store.release_lease_token, 'held': store.held_lease}


def end_fns(store):
    return {'release_lease_token': store.release_lease_token, 'end_session': store.end_session}


def gate_records():
    base = {'fact_kind': 'observation', 'source_class': CI, 'recorder': 'external CI', 'subject': TASK,
            'commit': COMMIT, 'intent_versions': dict(IV), 'outcome': 'pass'}
    return [dict(base, record_id='g0', gate='G0', evidence_type='scope_check', dimension='scope'),
            dict(base, record_id='g1', gate='G1', evidence_type='build', dimension='functional')]


def evaluate(recs):
    """governor.evaluate as evaluation.evaluate_task calls it: a request, the derived inputs and the kept records."""
    request = {'task_id': TASK, 'task_content_hash': H, 'evaluated_commit': COMMIT, 'intent_versions': dict(IV),
               'task_state': 'VERIFYING', 'changed_paths': ['src/app/core/x.py'],
               'retry_count': {'used': 0, 'limit': 2}}
    inp = {'traces_to': ['SPEC-003'], 'risk': 'low', 'owner_kept_act': False, 'weakens_evidence': False,
           'delegation_in_force': True, 'auto_accept': False, 'verification_plan': ['G0', 'G1'],
           'evidence_profile': [{'dimension': 'functional', 'evidence_types': ['build']},
                                {'dimension': 'architecture', 'evidence_types': ['ai_review']}],
           'applicable_articles': [], 'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1'}
    return governor.evaluate(request, inp, recs)


class R6Session(unittest.TestCase):
    def test_a_whole_session_reaches_continue_and_the_claims_count_for_nothing(self):
        """TASK-060 AC6, TASK-060 AC4, TASK-060 AC3, TASK-060 AC10: start over the real adapter, execution.execute and
        resume_check.check reaches CONTINUE and grants the token; claim with that token appends one record.added per
        claim; end releases the lease and closes the session; governor.evaluate over the records counts no claim for
        any evidence entry and lists none as blocking, and adding the claims changes no entry it counts as met."""
        store, mem = set_up()
        r = t0.start(ROOT, TASK, 'session-1', 'agent-1', inputs(2), CODE, LATER, REC, NOW,
                     functions=start_fns(store, mem))
        self.assertEqual((r['result'], r['decision']), ('done', 'CONTINUE'), r['findings'])
        token = r['fencing_token']
        self.assertEqual(token, {'epoch': 'e-t0', 'counter': 1})
        c = t0.claim(ROOT, TASK, 'session-1', token, CLAIMS, 'claims-1', REC, NOW, append=mem.append_event)
        self.assertEqual((c['result'], c['appended']), ('done', ['claims-1/claim-1', 'claims-1/claim-2']),
                         c['findings'])
        e = t0.end(ROOT, TASK, 'session-1', token, NOW, functions=end_fns(store))
        self.assertEqual(e['result'], 'done', e['findings'])
        self.assertEqual(store.leases, {})
        self.assertIsNotNone(store.sessions['session-1'][1])
        events = mem.events()
        self.assertEqual([x['type'] for x in events],
                         ['task.drafted', 'task.approved', 'decision.execution', 'record.added', 'record.added'])
        claims = [x['payload'] for x in events if x['type'] == 'record.added']
        self.assertEqual({x['fact_kind'] for x in claims}, {'claim'})
        only = evaluate(claims)
        self.assertEqual(only['blocking'], [])
        for p in only['profile_used']:
            self.assertEqual(p['satisfied_by'], [], p)
        with_gates = evaluate(gate_records() + claims)
        without = evaluate(gate_records())
        for key in ('profile_used', 'blocking', 'missing_gates', 'failed_gates', 'decision'):
            self.assertEqual(with_gates.get(key), without.get(key), key)
        met = [s for p in with_gates['profile_used'] for s in p['satisfied_by']]
        self.assertTrue(met)
        self.assertFalse(set(met) & {x['record_id'] for x in claims})

    def test_with_no_runtime_declaration_start_grants_no_lease_and_claim_is_fenced(self):
        """TASK-060 AC6, TASK-060 AC7, TASK-060 AC3, TASK-060 AC10: the same session with the runtime input carrying no
        declaration (max_risk None): check 7 gives STOP: runtime insufficient, start grants no lease, claim with any
        token gives "fence" with the writer's refusal record and no claim in the log, and end with no token closes the
        session."""
        store, mem = set_up()
        r = t0.start(ROOT, TASK, 'session-1', 'agent-1', inputs(2, {'adapter': 'an-adapter', 'max_risk': None}),
                     CODE, LATER, REC, NOW, functions=start_fns(store, mem))
        self.assertEqual((r['result'], r['decision'], r['fencing_token']),
                         ('done', 'STOP: runtime insufficient', None), r['findings'])
        self.assertEqual(store.leases, {})
        for token in ({'epoch': 'e-t0', 'counter': 1}, {'epoch': 'other', 'counter': 0}):
            c = t0.claim(ROOT, TASK, 'session-1', token, CLAIMS, 'claims-%d' % token['counter'], REC, NOW,
                         append=mem.append_event)
            self.assertEqual((c['result'], c['reason'], c['appended']), ('refused', 'fence', []))
        added = [x['payload'] for x in mem.events() if x['type'] == 'record.added']
        self.assertEqual(len(added), 2)
        self.assertNotIn('claim', {x['fact_kind'] for x in added})
        e = t0.end(ROOT, TASK, 'session-1', None, NOW, functions=end_fns(store))
        self.assertEqual(e['result'], 'done', e['findings'])


if __name__ == '__main__':
    unittest.main()

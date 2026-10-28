"""Unit tests of the conformance runner's Capability Boundaries entry (TASK-056, rules R1 to R9 of its AC17).

Every input is built in memory and given to the runner's functions directly or through its byte reader and records
listing; no file is written. The root's real core (replay, adapter, evaluation, eventlog, writer) runs over the
runner's in-memory stand-ins; stand-in cores are test seams (AC3). Each test names its criteria in its docstring.
"""
import hashlib
import inspect
import json
import pathlib
import sys
import types
import unittest
from unittest import mock

from aieos_bootstrap import adapter
from aieos_bootstrap import conformance
from aieos_bootstrap import evaluation
from aieos_bootstrap import eventlog
from aieos_bootstrap import replay
from aieos_bootstrap import writer

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMMIT = 'a' * 40
TASK = 'TASK-100'
REC = 'replay:session-one'
CODE = 'c' * 64
CONTRACT = 'task: TASK-100\nwrite_set:\n  paths: [docs/notes/**]\n'
H = hashlib.sha256(CONTRACT.encode('utf-8')).hexdigest()
OUTSIDE = 'src/outside.py'
MAIN, MINE, TREE = '1' * 40, '3' * 40, '4' * 40
CB_PATH = 'tests/conformance/fixtures_cb/adv_02.py'
TEST_RECORDS = 'docs/records/TEST-56.jsonl'


def rc_inputs(log_seq):
    """Resume Check inputs whose checks all pass (CONTINUE) for a READY task at log_seq (as test_replay.py's)."""
    return {
        'task_id': TASK, 'log_seq': log_seq, 'task_state': 'READY',
        'contract': {
            'task': TASK, 'contract_version': 'v1', 'task_type': 'implementation', 'risk': 'medium',
            'input_state': {'base_commit': MAIN, 'depends_on': ['TASK-099'], 'intent_versions': {'SPEC-003': 'v4'}},
            'write_set': {'paths': ['docs/notes/**']},
            'read_set': {'paths': ['src/app/util/helpers.py'], 'interfaces': ['load_policy'], 'schemas': ['record']},
            'constitution': ['INV-001'],
            'autonomy': {'budgets': {'retries': 2, 'tokens': '400k', 'wall_time': '2h', 'human_attention': '10m'}}},
        'contract_hash': H, 'approved_contract_hash': H, 'head_commit': '2' * 40, 'base_is_ancestor': True,
        'commits': [{'id': MINE, 'paths': [{'path': 'docs/other.md', 'change': 'modified'}], 'submitted': False}],
        'components': [{'id': 'CMP-API', 'paths': ['src/app/api/**'], 'tags': []}],
        'interfaces': [{'id': 'load_policy', 'component': 'CMP-API'}],
        'symbols': [{'interface': 'load_policy', 'base': 'F(a)', 'head': 'F(a)'}],
        'schemas': [{'name': 'record', 'base': {'path': 'src/app/api/record.json', 'sha256': 'b' * 64},
                     'head': {'path': 'src/app/api/record.json', 'sha256': 'b' * 64}}],
        'derived_read_set': [], 'observed_read_set': [],
        'intent_current': {'SPEC-003': 'v4'},
        'dependencies': {'TASK-099': {'state': 'DONE', 'stale_evidence': False}},
        'articles': [{'id': 'INV-001', 'scope': {'paths': ['src/app/**'], 'components': []},
                      'applicability': {'task_types': ['implementation']}, 'violated': False}],
        'runtime': {'adapter': 'an-adapter', 'max_risk': 'high'},
        'risk_rules': [{'match': {'paths': ['docs/**']}, 'risk': 'medium'}],
        'policy_version': 'v2',
        'budget_use': {'retries': {'used': 0, 'reported': True}, 'tokens': {'used': '10k', 'reported': True},
                       'wall_time': {'used': '10m', 'reported': True},
                       'human_attention': {'used': '0m', 'reported': True}},
    }


def commit_text(parents, message):
    head = 'tree %s\n' % TREE + ''.join('parent %s\n' % p for p in parents)
    return head + 'author Tester <tester> 1700000000 +0000\ncommitter Tester <tester> 1700000000 +0000\n\n' + message


def case(log_seq=5):
    """One Capability Boundaries case in section 11's form whose Given holds; log_seq is the second session's."""
    obs = {'record_id': 'obs-1', 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
           'recorder': REC, 'subject': TASK, 'evidence_type': 'write_outside_write_set', 'outcome': 'blocking',
           'blocking_kind': 'violation', 'refers_to': OUTSIDE}
    document = {
        'replay_id': 'adv-02', 'recorder': REC, 'epoch': 'e-replay',
        'setup': [
            {'type': 'task.drafted', 'payload': {'contract_version': 'v1', 'contract_hash': H}, 'event_id': 'drafted-1',
             'appended_at': '2026-10-16T09:00:00Z', 'task_id': TASK},
            {'type': 'task.approved', 'payload': {'contract_version': 'v1', 'contract_hash': H,
                                                  'approval_record': 'appr-1'},
             'event_id': 'approved-1', 'appended_at': '2026-10-16T09:01:00Z', 'task_id': TASK}],
        'session': {'task_id': TASK, 'session_id': 'session-1', 'holder': 'agent-1', 'inputs': rc_inputs(2),
                    'code_sha256': CODE, 'start_at': '2026-10-16T10:00:00Z', 'expires_at': '2026-10-16T11:00:00Z',
                    'expected_token': {'epoch': 'e-replay', 'counter': 1}},
        'submission': None,
        'violation': {'observation': obs, 'event_id': 'violation-1', 'at': '2026-10-16T10:20:00Z'},
        'end_at': '2026-10-16T10:40:00Z',
    }
    mine = commit_text([MAIN], 'Do the work\n\nThe body.\n\nAIEOS-Task: %s\nAIEOS-Fence: e-replay:2\n' % TASK)
    continuation = {
        'session': {'task_id': TASK, 'session_id': 'session-2', 'holder': 'agent-1', 'inputs': rc_inputs(log_seq),
                    'code_sha256': CODE, 'start_at': '2026-10-16T12:00:00Z', 'expires_at': '2026-10-16T13:00:00Z',
                    'expected_token': {'epoch': 'e-replay', 'counter': 2}},
        'submission': {'commit_id': MINE, 'commit_text': mine, 'event_id': 'submitted-1', 'at': '2026-10-16T12:30:00Z'},
        'end_at': '2026-10-16T12:40:00Z',
    }
    ci = {'record_id': 'ci-1', 'fact_kind': 'observation', 'source_class': 'deterministic_tool_external_ci',
          'recorder': 'ci', 'subject': TASK, 'gate': 'G1', 'outcome': 'pass', 'commit': MINE,
          'intent_versions': {'SPEC-001': 'v1'}}
    values = {
        'contract': {'traces_to': ['SPEC-001'], 'risk': 'high', 'owner_kept_act': False, 'verification_plan': ['G1']},
        'changed_paths': [OUTSIDE],
        'risk_rules': [{'id': 'R2', 'match': ['src/**', 'tests/**'], 'class': 'medium'}],
        'owner_kept_rules': [],
        'articles': [],
        'default_profiles': {'high': [{'dimension': 'functional', 'evidence_types': ['unit_test']}]},
        'requirement_profiles': [],
        'delegation': True,
        'evidence_comparison': {'weakens': False},
        'auto_accept': {'low': False, 'medium': False, 'high': False, 'critical': False},
        'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1',
    }
    unit = dict(ci, record_id='ut-1', gate=None, evidence_type='unit_test', dimension='functional')
    del unit['gate']
    evaluation_values = {
        'task_id': TASK, 'contract_text': CONTRACT, 'declared': {'intent_versions': {'SPEC-001': 'v1'}, 'retries': 2},
        'values': values, 'extra_records': [ci, unit], 'recorder': 'aieos-core', 'now': '2026-10-16T13:00:00Z',
        'commits': [{'id': MINE, 'text': mine, 'paths': [OUTSIDE]},
                    {'id': MAIN, 'text': commit_text([], 'Main\n\nThe body.\n'), 'paths': ['docs/a.md']}],
    }
    return {'document': document, 'continuation': continuation, 'evaluation': evaluation_values,
            'given': {'outside_path': OUTSIDE, 'write_set': ['docs/notes/**']},
            'expected': {'stop': ['STOP: violation'], 'decision': ['REJECT'], 'next_state': ['REJECTED'],
                         'not_fixed': ['metrics']}}


def entry():
    return {'id': 'ADV-02', 'row_hash': 'f' * 64, 'capability': 'Capability Boundaries',
            'fixture': {'path': CB_PATH, 'sha256': '0' * 64}}


def fixture(c=None):
    return {'scenario': 'ADV-02', 'row_hash': 'f' * 64, 'cases': [case() if c is None else c]}


def core():
    cb, status = conformance.load_cb(ROOT)
    assert status == conformance.LOADED, status
    return cb


def go(c=None, cb=None):
    return conformance._run_cb_cases(fixture(c), entry(), core() if cb is None else cb, ROOT)


class R1Route(unittest.TestCase):
    def test_the_route(self):
        """TASK-056 AC2: the Capability Boundaries path; the other capabilities keep theirs; another capability none."""
        self.assertEqual(conformance.expected_path('ADV-02', 'Capability Boundaries'), CB_PATH)
        self.assertEqual(conformance.expected_path('RISK-01', 'Risk Engine'), conformance.RISK_FIXTURE_DIR + '/risk_01.py')
        self.assertEqual(conformance.expected_path('RC-01', 'Resume Check'), conformance.RC_FIXTURE_DIR + '/rc_01.py')
        self.assertIsNone(conformance.expected_path('ADV-02', 'Telemetry'))
        self.assertEqual(conformance.run_scenario(None, dict(entry(), capability='Telemetry'), {}, None),
                         (conformance.NOT_RUN, 'the entry point of Telemetry is absent until its milestone'))

    def test_a_fixture_under_another_folder(self):
        """TASK-056 AC2: a Capability Boundaries entry naming the Verification folder is NOT_RUN before any read."""
        asked = []
        tree = conformance._Tree(ROOT, read=lambda p: asked.append(p))
        e = dict(entry(), fixture={'path': conformance.module_path('ADV-02'), 'sha256': '0' * 64})
        self.assertEqual(conformance.run_scenario(tree, e, {}, None),
                         (conformance.NOT_RUN, 'the fixture path is not ' + CB_PATH))
        self.assertEqual(asked, [])


class R2EntryPoint(unittest.TestCase):
    def test_the_loaded_entry(self):
        """TASK-056 AC3: the five modules from the root; the entry's functions are theirs."""
        cb = core()
        self.assertIs(cb['replay'], replay.replay)
        self.assertIs(cb['evaluate_task'], evaluation.evaluate_task)
        self.assertIs(cb['append'], eventlog.append)
        self.assertEqual((cb['start'], cb['submit'], cb['end']), (adapter.start, adapter.submit, adapter.end))

    def test_absent_failed_and_no_callable(self):
        """TASK-056 AC3: a module that is absent, that fails to load, that is not the root's, or that lacks a callable
        gives no entry, and the scenario is NOT_RUN for "the entry point is absent"."""
        with mock.patch.dict(sys.modules, {'aieos_bootstrap.replay': None}):
            self.assertEqual(conformance.load_cb(ROOT), (None, conformance.ABSENT))
        fake = types.ModuleType('aieos_bootstrap.evaluation')
        fake.__file__ = str(ROOT / 'elsewhere' / 'evaluation.py')
        with mock.patch.dict(sys.modules, {'aieos_bootstrap.evaluation': fake}), \
                mock.patch.object(sys.modules['aieos_bootstrap'], 'evaluation', fake):
            self.assertEqual(conformance.load_cb(ROOT), (None, conformance.FAILED))
        self.assertEqual(conformance.load_cb(ROOT / 'elsewhere'), (None, conformance.FAILED))
        with mock.patch.object(adapter, 'submit', None):
            self.assertEqual(conformance.load_cb(ROOT), (None, conformance.FAILED))
        self.assertEqual(conformance._run_cb_cases(fixture(), entry(), None, ROOT),
                         (conformance.NOT_RUN, 'the entry point is absent'))


def no_calls():
    """A core whose every function fails the test when called."""
    def fail(*args, **kwargs):
        raise AssertionError('a core function was called')
    return stand_in(**{k: fail for k in ('replay', 'start', 'submit', 'end', 'evaluate_task', 'append')})


class R3Form(unittest.TestCase):
    def assert_malformed(self, change):
        c = case()
        change(c)
        errors = conformance.check_cb_fixture(fixture(c), entry())
        self.assertTrue(errors, change)
        result, reason = go(c, cb=no_calls())
        self.assertEqual(result, conformance.NOT_RUN)
        self.assertTrue(reason.startswith('the fixture is malformed: '), reason)

    def test_the_well_formed_case(self):
        """TASK-056 AC4: the built case is well formed and its Given holds."""
        self.assertEqual(conformance.check_cb_fixture(fixture(), entry()), [])

    def test_each_malformed_condition(self):
        """TASK-056 AC4: one failing case per rule of the form; each makes the scenario NOT_RUN with no call."""
        self.assertTrue(conformance.check_cb_fixture(dict(fixture(), extra=1), entry()))
        self.assertTrue(conformance.check_cb_fixture(dict(fixture(), scenario='ADV-03'), entry()))
        self.assertTrue(conformance.check_cb_fixture(dict(fixture(), cases=[case(), case()]), entry()))
        other_row = dict(fixture(), row_hash='e' * 64)
        self.assertEqual(conformance.check_cb_fixture(other_row, entry()),
                         ['scenario or row_hash differs from the set entry'])
        result, reason = conformance._run_cb_cases(other_row, entry(), no_calls(), ROOT)
        self.assertEqual((result, reason), (conformance.NOT_RUN,
                                            'the fixture is malformed: scenario or row_hash differs from the set entry'))
        changes = [
            lambda c: c.update(extra=1),
            lambda c: c['document'].pop('violation'),
            lambda c: c['document'].update(submission=c['continuation']['submission']),
            lambda c: c['continuation'].update(extra=1),
            lambda c: c['continuation'].update(submission=None),
            lambda c: c['continuation'].update(end_at='2026-10-16 12:40'),
            lambda c: c['evaluation'].pop('now'),
            lambda c: c['evaluation'].update(contract_text=7),
            lambda c: c['evaluation'].update(contract_text='\ud800'),
            lambda c: c['evaluation'].update(commits=[]),
            lambda c: c['evaluation']['commits'][0].update(id='X' * 40),
            lambda c: c['evaluation']['commits'][0].update(paths='src/outside.py'),
            lambda c: c['evaluation']['commits'][0].update(text=7),
            lambda c: c['evaluation'].update(now='2026-10-16 13:00'),
            lambda c: c['given'].update(extra=1),
            lambda c: c['expected'].update(stop=['CONTINUE']),
            lambda c: c['expected'].update(decision=['REJECT', 'ACCEPT']),
            lambda c: c['expected'].update(next_state=['REWORK']),
            lambda c: c['expected'].update(not_fixed=[]),
            lambda c: c['expected'].update(metrics=[]),
        ]
        for change in changes:
            self.assert_malformed(change)

    def test_each_given_condition(self):
        """TASK-056 AC4: each condition of the Given, broken alone, makes the fixture malformed."""
        obs = lambda c: c['document']['violation']['observation']
        changes = [
            lambda c: obs(c).update(outcome='fail'),
            lambda c: obs(c).update(blocking_kind='stale'),
            lambda c: obs(c).update(source_class='agent_declared'),
            lambda c: obs(c).update(recorder='replay:another'),
            lambda c: c['given'].update(write_set=['src/**']),
            lambda c: c['given'].update(outside_path='src/elsewhere.py'),
            lambda c: c['evaluation'].update(contract_text=CONTRACT + '#'),
            lambda c: c['evaluation']['values'].update(changed_paths=['src/x.py']),
            lambda c: c['continuation']['submission'].update(commit_id='9' * 40),
            lambda c: c['evaluation']['commits'].append(dict(c['evaluation']['commits'][0])),
            lambda c: c['document'].update(setup=[e for e in c['document']['setup'] if e['type'] != 'task.approved']),
            lambda c: c['document']['setup'].append(
                dict(c['document']['setup'][1], event_id='approved-2', appended_at='2026-10-16T09:02:00Z',
                     payload=dict(c['document']['setup'][1]['payload'], contract_hash='d' * 64))),
        ]
        for change in changes:
            self.assert_malformed(change)


class R4StandIns(unittest.TestCase):
    def test_bound_to_the_real_signatures_and_types(self):
        """TASK-056 AC5 (decision D-1079, M5): every call the core makes to a stand-in in a passing case is bound with
        inspect.signature(...).bind to the writer's function of that name and to the stand-in; results are the writer's
        types; appends are eventlog.append's decisions (a repeated event is a duplicate)."""
        calls = []
        real_functions = conformance._CbLog.functions

        def recording(self_log):
            out = {}
            for name, fn in real_functions(self_log).items():
                def rec(*args, _name=name, _fn=fn, **kwargs):
                    calls.append((_name, _fn, args, kwargs))
                    return _fn(*args, **kwargs)
                out[name] = rec
            return out
        with mock.patch.object(conformance._CbLog, 'functions', recording):
            self.assertEqual(go(), (conformance.PASS, ''))
        called = {n for n, _, _, _ in calls}
        self.assertLessEqual({'open_store', 'append_event', 'start_session', 'end_session', 'read_log', 'grant_lease',
                              'release_lease_token'}, called)
        for name, fn, args, kwargs in calls:
            inspect.signature(getattr(writer, name)).bind(*args, **kwargs)
            inspect.signature(fn).bind(*args, **kwargs)
        cb = core()
        store = conformance._CbStore(cb)
        log = conformance._CbLog(cb, store)
        for name, fn in log.functions().items():
            real = getattr(writer, name)
            self.assertEqual(list(inspect.signature(fn).parameters), list(inspect.signature(real).parameters), name)
        r = log.append_event('/r', 'task.drafted', {'contract_version': 'v1', 'contract_hash': H}, 'd-1',
                             conformance._utc('2026-10-16T09:00:00Z'), REC, task_id=TASK)
        self.assertIsInstance(r, writer.WriteResult)
        self.assertEqual(r.result, 'appended')
        again = log.append_event('/r', 'task.drafted', {'contract_version': 'v1', 'contract_hash': H}, 'd-1',
                                 conformance._utc('2026-10-16T09:00:00Z'), REC, task_id=TASK)
        self.assertEqual(again.result, eventlog.append(log.log, 'task.drafted', {'contract_version': 'v1',
                                                                                'contract_hash': H}, 'd-1',
                                                       conformance._utc('2026-10-16T09:00:00Z'), task_id=TASK,
                                                       recorder=REC).result)
        self.assertIsInstance(store.start_session('/r', 's', 'h', None), writer.StoreResult)

    def test_the_store_rules_copied_from_the_writer(self):
        """TASK-056 AC5 (decision D-1079, M1 and M2): grant_lease refuses an expiry not after now ("expiry") and a held
        lease ("held"), as writer.grant_lease does; end_session releases the session's leases, oldest grant first, and
        refuses a second end ("ended")."""
        store = conformance._CbStore(core())
        store.open_store('/r', epoch='e')
        t0, t1 = conformance._utc('2026-10-16T10:00:00Z'), conformance._utc('2026-10-16T11:00:00Z')
        self.assertEqual(store.start_session('/r', 's', 'h', t0).result, 'done')
        self.assertEqual(store.grant_lease('/r', TASK, 'READY', 'h', 's', t1, t1).reason, 'expiry')
        first = store.grant_lease('/r', TASK, 'READY', 'h', 's', t0, t1)
        self.assertEqual(first.result, 'done')
        self.assertEqual(store.grant_lease('/r', TASK, 'READY', 'h', 's', t0, t1).reason, 'held')
        second = store.grant_lease('/r', 'TASK-101', 'READY', 'h', 's', t0, t1)
        ended = store.end_session('/r', 's', t1)
        self.assertEqual(ended.result, 'done')
        self.assertEqual(ended.value, [first.value, second.value])
        self.assertIsNone(store.held_lease('/r', TASK))
        self.assertEqual(store.end_session('/r', 's', t1).reason, 'ended')
        self.assertEqual(store.end_session('/r', 'never', t1).reason, 'session')

    def test_the_read_stand_in(self):
        """TASK-056 AC5: only cat-file -t, cat-file -p and the pinned diff-tree form of a table commit are answered."""
        c = case()
        read = conformance.cb_commit_read(c['evaluation']['commits'], evaluation.DIFF_FORM)
        self.assertEqual(read('/r', ['cat-file', '-t', MINE])['out'], b'commit\n')
        self.assertEqual(read('/r', ['cat-file', '-p', MINE])['out'], c['evaluation']['commits'][0]['text'].encode())
        self.assertEqual(read('/r', evaluation.DIFF_FORM + [MINE])['out'], OUTSIDE.encode() + b'\0')
        for args in (['cat-file', '-p', '9' * 40], ['log', MINE], ['diff-tree', MINE]):
            self.assertIsNotNone(read('/r', args)['error'])

    def test_no_file_is_written_and_the_root_is_absolute(self):
        """TASK-056 AC5 and decision D-1075 C3: a case runs with every write of the writer replaced by a function that
        fails the test; the core's root is absolute, also for a relative run root, and names no existing folder."""
        def fail(*args, **kwargs):
            raise AssertionError('a writer function was called')
        names = ('append_event', 'open_store', 'start_session', 'end_session', 'grant_lease', 'release_lease_token',
                 'held_lease', 'read_log')
        with mock.patch.multiple(writer, **{n: fail for n in names}):
            self.assertEqual(go(), (conformance.PASS, ''))
        for root in (ROOT, pathlib.Path('relative-root')):
            path = pathlib.Path(conformance.cb_core_root(root))
            self.assertTrue(path.is_absolute())
            self.assertFalse(path.exists())


def stand_in(**changes):
    """The root's core with some functions replaced."""
    cb = dict(core())
    cb.update(changes)
    return cb


class R5Replay(unittest.TestCase):
    def test_the_stop_is_observed(self):
        """TASK-056 AC6: the root's core stops the session and the case goes on to PASS."""
        self.assertEqual(go(), (conformance.PASS, ''))

    def test_a_done_replay_without_the_stop_fails(self):
        """TASK-056 AC6: a replay that is done but whose violation step decides something else is FAIL."""
        def no_stop(*args, **kwargs):
            r = replay.replay(*args, **kwargs)
            for s in r['steps']:
                if s['step'] == 'violation':
                    s['result']['decision'] = None
            return r
        self.assertEqual(go(cb=stand_in(replay=no_stop))[0], conformance.FAIL)

    def test_a_core_refusal_of_the_violation_fails_also_when_logged(self):
        """TASK-056 AC6 (decision D-1067 addition (ii)): a violation step refused with reason core is FAIL, also when
        its decision event is in the log."""
        def core_refused(*args, **kwargs):
            r = replay.replay(*args, **kwargs)
            for s in r['steps']:
                if s['step'] == 'violation':
                    s['result'].update(result='refused', reason='core')
            return dict(r, result='refused', reason='violation')
        self.assertEqual(go(cb=stand_in(replay=core_refused))[0], conformance.FAIL)

    def test_the_not_run_refusals(self):
        """TASK-056 AC6: no lease (no violation step), an argument refusal and each other refusal are NOT_RUN."""
        def refused(reason, step=None):
            def fn(*args, **kwargs):
                steps = [] if step is None else [{'step': 'violation', 'result': {'result': 'refused',
                                                                                 'reason': step}}]
                out = dict.fromkeys(replay.RESULT_KEYS)
                out.update(result='refused', reason=reason, findings=[], steps=steps)
                return out
            return fn
        for fn in [refused('violation'), refused('violation', 'argument')] + [
                refused(r) for r in ('document', 'store', 'setup', 'start', 'token', 'end')]:
            self.assertEqual(go(cb=stand_in(replay=fn))[0], conformance.NOT_RUN)


class R6Continuation(unittest.TestCase):
    def test_each_not_run(self):
        """TASK-056 AC7: a log_seq mismatch (no lease), a token mismatch and a refused submission or end are NOT_RUN,
        each with its reason."""
        self.assertEqual(go(case(log_seq=6)), (conformance.NOT_RUN, 'step 2: the second session got no lease'))
        c = case()
        c['continuation']['session']['expected_token'] = {'epoch': 'e-replay', 'counter': 9}
        self.assertEqual(go(c)[1], "step 2: the granted token {'epoch': 'e-replay', 'counter': 2} is not the "
                                   "expected {'epoch': 'e-replay', 'counter': 9}")
        refuse = lambda *a, **k: {'result': 'refused', 'reason': 'core'}
        self.assertEqual(go(cb=stand_in(submit=refuse)), (conformance.NOT_RUN, 'step 2: the submission was refused'))
        self.assertEqual(go(cb=stand_in(end=refuse)), (conformance.NOT_RUN, 'step 2: the end was refused'))


class R7Evaluation(unittest.TestCase):
    def test_reject_passes_and_a_governor_that_does_not_reject_fails(self):
        """TASK-056 AC8: REJECT and REJECTED pass; an evaluation that does not reject is FAIL; refused and duplicate
        are NOT_RUN."""
        self.assertEqual(go(), (conformance.PASS, ''))
        accept = lambda *a, **k: {'result': 'evaluated', 'decision': 'ACCEPT', 'next_task_state': 'ACCEPTED'}
        self.assertEqual(go(cb=stand_in(evaluate_task=accept))[0], conformance.FAIL)
        for decision, state in (('REJECT', 'REWORK'), ('ACCEPT', 'REJECTED')):
            fn = lambda *a, d=decision, s=state, **k: {'result': 'evaluated', 'decision': d, 'next_task_state': s}
            self.assertEqual(go(cb=stand_in(evaluate_task=fn))[0], conformance.FAIL, (decision, state))
        for result in ('refused', 'duplicate'):
            fn = lambda *a, result=result, **k: {'result': result, 'reason': 'state', 'decision': 'REJECT',
                                                 'next_task_state': 'REJECTED'}
            self.assertEqual(go(cb=stand_in(evaluate_task=fn))[0], conformance.NOT_RUN)


class R8Order(unittest.TestCase):
    def test_fail_first_and_raises(self):
        """TASK-056 AC9: a failure stops the later steps; a NOT_RUN at step 2 stops step 3; a raise is NOT_RUN with its
        type."""
        calls = []

        def no_stop(*args, **kwargs):
            r = replay.replay(*args, **kwargs)
            return dict(r, steps=[s for s in r['steps'] if s['step'] != 'violation'])
        start = lambda *a, **k: calls.append('start')
        self.assertEqual(go(cb=stand_in(replay=no_stop, start=start))[0], conformance.FAIL)
        self.assertEqual(calls, [])

        evaluated = []
        record = lambda *a, **k: evaluated.append('evaluate_task')
        self.assertEqual(go(case(log_seq=6), cb=stand_in(evaluate_task=record)),
                         (conformance.NOT_RUN, 'step 2: the second session got no lease'))
        self.assertEqual(evaluated, [])

        def boom(*args, **kwargs):
            raise KeyError('x')
        self.assertEqual(go(cb=stand_in(replay=boom)), (conformance.NOT_RUN, 'step 1: the call raised KeyError'))
        self.assertEqual(go(cb=stand_in(evaluate_task=boom)), (conformance.NOT_RUN, 'step 3: the call raised KeyError'))


ADV_02_SHA256 = 'f6fed8e0db041705f870631ca46b32ba50cb43ed29f6f143f97d19c152938385'
CB_SET_SHA256 = 'f3297aec6d9ba78df02c7e335cb64e26dd43ee5583b94f8ba45ac9bdaaa5e5ec'


def cb_state(value=None):
    """The state of the set file's Capability Boundaries entries (TASK-058, contract AC1): 'null' when ADV-02, the only
    one, names no fixture; 'present' when it names the file conformance.expected_path gives with the SHA-256 that DM row
    F49's freeze binds, that file in the tree having that SHA-256, and the set file, written as the runner writes it,
    has the SHA-256 f3297aec... and fixture_set_version 6; any other value fails. Without a value it reads the tree's
    set file."""
    if value is None:
        value = conformance.unwrap((ROOT / conformance.SET_FILE).read_bytes())
    cb = [e for e in value['scenarios'] if e['capability'] == conformance.CAPABILITY_BOUNDARIES]
    if [e['id'] for e in cb] != ['ADV-02']:
        raise AssertionError('the Capability Boundaries entries are not exactly ADV-02')
    if cb[0]['fixture'] is None:
        return 'null'
    path = conformance.expected_path('ADV-02', conformance.CAPABILITY_BOUNDARIES)
    data = conformance.FIRST + conformance.canonical_text(value) + conformance.LAST
    if (cb[0]['fixture'] == {'path': path, 'sha256': ADV_02_SHA256}
            and conformance.sha256((ROOT / path).read_bytes()) == ADV_02_SHA256
            and conformance.sha256(data) == CB_SET_SHA256 and value['fixture_set_version'] == 6):
        return 'present'
    raise AssertionError('the ADV-02 entry names neither no fixture nor its frozen file in the set file of AC1')


def cb_record():
    """The run record's capability_boundaries in the present state (TASK-058 AC4): the three recorded modules of the
    tree, by path and SHA-256, in the order replay, adapter, evaluation."""
    return [{'path': conformance.cb_path(n), 'sha256': conformance.sha256((ROOT / conformance.cb_path(n)).read_bytes())}
            for n in ('replay', 'adapter', 'evaluation')]


def wrap(value):
    return conformance.FIRST + conformance.canonical_text(value) + conformance.LAST


def freeze_line(digest):
    rec = {'approval_binding': {'hash': digest, 'kind': 'change_request'}, 'decision_ref': 'D-000',
           'fact_kind': 'authority', 'record_id': 'TEST-freeze-' + digest[:16], 'recorder': 'a unit test',
           'source_class': 'decision_agent', 'subject': 'TASK-056'}
    return (json.dumps(rec, sort_keys=True) + '\n').encode('utf-8')


def tree_with_fixture(c=None):
    """The repository's own files, with an in-memory fixture under fixtures_cb/ and a set file naming it."""
    files = {}
    for p in ROOT.glob('docs/records/*.jsonl'):
        files['docs/records/' + p.name] = p.read_bytes()
    for path in (conformance.RUNNER_PATH, conformance.SET_FILE, conformance.SCENARIO_FILE):
        files[path] = (ROOT / path).read_bytes()
    for folder in (conformance.FIXTURE_DIR, conformance.RC_FIXTURE_DIR, conformance.RISK_FIXTURE_DIR):
        for p in sorted((ROOT / folder).glob('*.py')):
            files[folder + '/' + p.name] = p.read_bytes()
    for name in conformance.CB_MODULES + ('governor', 'resume_check'):
        files[conformance.cb_path(name)] = (ROOT / conformance.cb_path(name)).read_bytes()
    value = conformance.unwrap(files[conformance.SET_FILE])
    e = next(x for x in value['scenarios'] if x['id'] == 'ADV-02')
    data = wrap({'scenario': 'ADV-02', 'row_hash': e['row_hash'], 'cases': [case() if c is None else c]})
    files[CB_PATH] = data
    e['fixture'] = {'path': CB_PATH, 'sha256': conformance.sha256(data)}
    files[conformance.SET_FILE] = wrap(value)
    files[TEST_RECORDS] = freeze_line(conformance.sha256(files[conformance.SET_FILE]))
    return files


def run_files(files, **kw):
    return conformance.run(ROOT, COMMIT, 'TASK-056', read=files.get,
                           listing=lambda: sorted(p for p in files if p.startswith('docs/records/')), **kw)


class R9Record(unittest.TestCase):
    def test_the_key_only_with_the_entry_run(self):
        """TASK-056 AC10: capability_boundaries is present, in order, when a Capability Boundaries fixture is read,
        and absent over the repository's tree; a stand-in entry never counts and its hashes are null."""
        r = run_files(tree_with_fixture())
        self.assertEqual(r.results['ADV-02'], conformance.PASS)
        self.assertEqual([x['path'] for x in r.value['capability_boundaries']],
                         [conformance.cb_path(n) for n in ('replay', 'adapter', 'evaluation')])
        self.assertEqual(r.value['capability_boundaries'][0]['sha256'],
                         conformance.sha256((ROOT / conformance.cb_path('replay')).read_bytes()))
        s = run_files(tree_with_fixture(), cb=core())
        self.assertFalse(s.value['counts'])
        self.assertEqual({x['sha256'] for x in s.value['capability_boundaries']}, {None})
        plain = conformance.run(ROOT, COMMIT, 'TASK-056')
        # TASK-058 AC2: in the present state of ADV-02's entry the run over the tree reads the frozen fixture.
        if cb_state() == 'present':
            # In the present state of ADV-02's entry (TASK-058 AC4), ADV-02 is PASS and the record holds
            # capability_boundaries; the docstring above describes the null state.
            self.assertEqual(plain.value['capability_boundaries'], cb_record())
            self.assertEqual((plain.results['ADV-02'], plain.reasons['ADV-02']), (conformance.PASS, ''))
        else:
            self.assertNotIn('capability_boundaries', plain.value)
            self.assertEqual((plain.results['ADV-02'], plain.reasons['ADV-02']), (conformance.NOT_RUN, 'no fixture'))

    def test_the_counting_reading_and_the_lazy_load(self):
        """TASK-056 AC3's counting reading (decision D-1079, M11): an absent entry keeps the run counting, a failed one
        makes it not count with its problem stated, and both give ADV-02 NOT_RUN "the entry point is absent"; with no
        Capability Boundaries fixture, load_cb is never called."""
        files = tree_with_fixture()
        base = run_files(files)
        with mock.patch.object(conformance, 'load_cb', lambda root: (None, conformance.ABSENT)):
            absent = run_files(files)
        self.assertEqual(absent.value['counts'], base.value['counts'])
        self.assertTrue(absent.value['counts'])
        self.assertEqual((absent.results['ADV-02'], absent.reasons['ADV-02']),
                         (conformance.NOT_RUN, 'the entry point is absent'))
        with mock.patch.object(conformance, 'load_cb', lambda root: (None, conformance.FAILED)):
            failed = run_files(files)
        self.assertFalse(failed.value['counts'])
        self.assertIn('the Capability Boundaries entry could not be loaded from the root (reading)', failed.problems)
        self.assertEqual((failed.results['ADV-02'], failed.reasons['ADV-02']),
                         (conformance.NOT_RUN, 'the entry point is absent'))

        def never(root):
            raise AssertionError('load_cb was called')
        # TASK-058 AC2: in the present state the entry is loaded once, from the root.
        if cb_state() == 'present':
            calls = []
            real = conformance.load_cb

            def counted(root):
                calls.append(root)
                return real(root)
            with mock.patch.object(conformance, 'load_cb', counted):
                plain = conformance.run(ROOT, COMMIT, 'TASK-056')
            self.assertEqual(calls, [ROOT])
        else:
            with mock.patch.object(conformance, 'load_cb', never):
                plain = conformance.run(ROOT, COMMIT, 'TASK-056')
        self.assertTrue(plain.value['counts'])


class R10State(unittest.TestCase):
    def test_the_state_check(self):
        """TASK-058 AC1 and AC10 R1: the state check over in-memory set values: null, the present state of AC1, and a
        failure for another path, another hash, another fixture_set_version or another Capability Boundaries id."""
        value = conformance.unwrap((ROOT / conformance.SET_FILE).read_bytes())
        e = next(x for x in value['scenarios'] if x['id'] == 'ADV-02')
        e['fixture'] = None
        value['fixture_set_version'] = 5
        self.assertEqual(cb_state(value), 'null')
        e['fixture'] = {'path': CB_PATH, 'sha256': ADV_02_SHA256}
        value['fixture_set_version'] = 6
        self.assertEqual(conformance.sha256(wrap(value)), CB_SET_SHA256)
        self.assertEqual(cb_state(value), 'present')
        for change in ({'path': conformance.module_path('ADV-02')}, {'sha256': '0' * 64}):
            e['fixture'] = dict({'path': CB_PATH, 'sha256': ADV_02_SHA256}, **change)
            with self.assertRaises(AssertionError):
                cb_state(value)
        e['fixture'] = {'path': CB_PATH, 'sha256': ADV_02_SHA256}
        value['fixture_set_version'] = 7
        with self.assertRaises(AssertionError):
            cb_state(value)
        value['fixture_set_version'] = 6
        e['id'] = 'ADV-09'
        with self.assertRaises(AssertionError):
            cb_state(value)


if __name__ == '__main__':
    unittest.main()

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


class R3Form(unittest.TestCase):
    def assert_malformed(self, change):
        c = case()
        change(c)
        errors = conformance.check_cb_fixture(fixture(c), entry())
        self.assertTrue(errors, change)
        self.assertEqual(go(c)[0], conformance.NOT_RUN)

    def test_the_well_formed_case(self):
        """TASK-056 AC4: the built case is well formed and its Given holds."""
        self.assertEqual(conformance.check_cb_fixture(fixture(), entry()), [])

    def test_each_malformed_condition(self):
        """TASK-056 AC4: one failing case per rule of the form; each makes the scenario NOT_RUN with no call."""
        self.assertTrue(conformance.check_cb_fixture(dict(fixture(), extra=1), entry()))
        self.assertTrue(conformance.check_cb_fixture(dict(fixture(), scenario='ADV-03'), entry()))
        self.assertTrue(conformance.check_cb_fixture(dict(fixture(), cases=[case(), case()]), entry()))
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
        ]
        for change in changes:
            self.assert_malformed(change)


class R4StandIns(unittest.TestCase):
    def test_bound_to_the_real_signatures_and_types(self):
        """TASK-056 AC5: each stand-in binds to the writer's function's signature; results are the writer's types;
        appends are eventlog.append's decisions (a repeated event is a duplicate)."""
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
        """TASK-056 AC7: a log_seq mismatch (no lease), a token mismatch and a refused submission are NOT_RUN."""
        self.assertEqual(go(case(log_seq=6))[0], conformance.NOT_RUN)
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
        for result in ('refused', 'duplicate'):
            fn = lambda *a, result=result, **k: {'result': result, 'reason': 'state', 'decision': 'REJECT',
                                                 'next_task_state': 'REJECTED'}
            self.assertEqual(go(cb=stand_in(evaluate_task=fn))[0], conformance.NOT_RUN)


class R8Order(unittest.TestCase):
    def test_fail_first_and_raises(self):
        """TASK-056 AC9: a failure stops the later steps; a raise is NOT_RUN with its type."""
        calls = []

        def no_stop(*args, **kwargs):
            r = replay.replay(*args, **kwargs)
            return dict(r, steps=[s for s in r['steps'] if s['step'] != 'violation'])
        start = lambda *a, **k: calls.append('start')
        self.assertEqual(go(cb=stand_in(replay=no_stop, start=start))[0], conformance.FAIL)
        self.assertEqual(calls, [])

        def boom(*args, **kwargs):
            raise KeyError('x')
        self.assertEqual(go(cb=stand_in(replay=boom)), (conformance.NOT_RUN, 'step 1: the call raised KeyError'))
        self.assertEqual(go(cb=stand_in(evaluate_task=boom)), (conformance.NOT_RUN, 'step 3: the call raised KeyError'))


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
        self.assertNotIn('capability_boundaries', plain.value)
        self.assertEqual((plain.results['ADV-02'], plain.reasons['ADV-02']), (conformance.NOT_RUN, 'no fixture'))


if __name__ == '__main__':
    unittest.main()

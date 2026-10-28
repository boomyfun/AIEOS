"""Integration tests of the conformance runner's Capability Boundaries entry (TASK-056 AC11 and AC17), end to end over
the repository's own tree: with no stand-in, ADV-02 stays NOT_RUN and the run record has no capability_boundaries key;
with an in-memory set file whose ADV-02 entry names an in-memory fixture under fixtures_cb/ and the root's core, ADV-02
is PASS; with a core that does not stop the session, or one whose evaluation does not reject, ADV-02 is FAIL and the
run does not count. That PASS tests the runner, not the core's conformance, and is not conformance evidence (AC16).
The case builder is a copy of tests/unit/test_runner_cb.py's (the test folders share no module). No file is written.
"""
# In the present state of ADV-02's set entry (TASK-058 AC4), the run over the repository's tree gives ADV-02 PASS
# and its record holds capability_boundaries; the docstrings above and below that say otherwise describe the null
# state.
import hashlib
import json
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import conformance
from aieos_bootstrap import replay

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
BASE_KEYS = {'commit', 'counts', 'fixture_set_version', 'governor_identity', 'results', 'resume_check', 'runner',
             'scenario_set_version', 'set_file_sha256'}


def rc_inputs(log_seq):
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
    obs = {'record_id': 'obs-1', 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
           'recorder': REC, 'subject': TASK, 'evidence_type': 'write_outside_write_set', 'outcome': 'blocking',
           'blocking_kind': 'violation', 'refers_to': OUTSIDE}
    mine = commit_text([MAIN], 'Do the work\n\nThe body.\n\nAIEOS-Task: %s\nAIEOS-Fence: e-replay:2\n' % TASK)
    ci = {'record_id': 'ci-1', 'fact_kind': 'observation', 'source_class': 'deterministic_tool_external_ci',
          'recorder': 'ci', 'subject': TASK, 'gate': 'G1', 'outcome': 'pass', 'commit': MINE,
          'intent_versions': {'SPEC-001': 'v1'}}
    unit = {k: v for k, v in ci.items() if k != 'gate'}
    unit.update(record_id='ut-1', evidence_type='unit_test', dimension='functional')
    return {
        'document': {
            'replay_id': 'adv-02', 'recorder': REC, 'epoch': 'e-replay',
            'setup': [
                {'type': 'task.drafted', 'payload': {'contract_version': 'v1', 'contract_hash': H},
                 'event_id': 'drafted-1', 'appended_at': '2026-10-16T09:00:00Z', 'task_id': TASK},
                {'type': 'task.approved', 'payload': {'contract_version': 'v1', 'contract_hash': H,
                                                      'approval_record': 'appr-1'},
                 'event_id': 'approved-1', 'appended_at': '2026-10-16T09:01:00Z', 'task_id': TASK}],
            'session': {'task_id': TASK, 'session_id': 'session-1', 'holder': 'agent-1', 'inputs': rc_inputs(2),
                        'code_sha256': CODE, 'start_at': '2026-10-16T10:00:00Z',
                        'expires_at': '2026-10-16T11:00:00Z', 'expected_token': {'epoch': 'e-replay', 'counter': 1}},
            'submission': None,
            'violation': {'observation': obs, 'event_id': 'violation-1', 'at': '2026-10-16T10:20:00Z'},
            'end_at': '2026-10-16T10:40:00Z'},
        'continuation': {
            'session': {'task_id': TASK, 'session_id': 'session-2', 'holder': 'agent-1', 'inputs': rc_inputs(log_seq),
                        'code_sha256': CODE, 'start_at': '2026-10-16T12:00:00Z',
                        'expires_at': '2026-10-16T13:00:00Z', 'expected_token': {'epoch': 'e-replay', 'counter': 2}},
            'submission': {'commit_id': MINE, 'commit_text': mine, 'event_id': 'submitted-1',
                           'at': '2026-10-16T12:30:00Z'},
            'end_at': '2026-10-16T12:40:00Z'},
        'evaluation': {
            'task_id': TASK, 'contract_text': CONTRACT,
            'declared': {'intent_versions': {'SPEC-001': 'v1'}, 'retries': 2},
            'values': {
                'contract': {'traces_to': ['SPEC-001'], 'risk': 'high', 'owner_kept_act': False,
                             'verification_plan': ['G1']},
                'changed_paths': [OUTSIDE],
                'risk_rules': [{'id': 'R2', 'match': ['src/**', 'tests/**'], 'class': 'medium'}],
                'owner_kept_rules': [], 'articles': [],
                'default_profiles': {'high': [{'dimension': 'functional', 'evidence_types': ['unit_test']}]},
                'requirement_profiles': [], 'delegation': True, 'evidence_comparison': {'weakens': False},
                'auto_accept': {'low': False, 'medium': False, 'high': False, 'critical': False},
                'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1'},
            'extra_records': [ci, unit], 'recorder': 'aieos-core', 'now': '2026-10-16T13:00:00Z',
            'commits': [{'id': MINE, 'text': mine, 'paths': [OUTSIDE]},
                        {'id': MAIN, 'text': commit_text([], 'Main\n\nThe body.\n'), 'paths': ['docs/a.md']}]},
        'given': {'outside_path': OUTSIDE, 'write_set': ['docs/notes/**']},
        'expected': {'stop': ['STOP: violation'], 'decision': ['REJECT'], 'next_state': ['REJECTED'],
                     'not_fixed': ['metrics']},
    }


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
           'fact_kind': 'authority', 'record_id': 'TEST-freeze-' + digest[:16], 'recorder': 'an integration test',
           'source_class': 'decision_agent', 'subject': 'TASK-056'}
    return (json.dumps(rec, sort_keys=True) + '\n').encode('utf-8')


def files_with_fixture():
    files = {}
    for p in ROOT.glob('**/*'):
        rel = p.relative_to(ROOT).as_posix()
        if p.is_file() and (rel.startswith(('docs/records/', 'tests/conformance/', 'src/aieos_bootstrap/'))
                            or rel == conformance.SCENARIO_FILE):
            files[rel] = p.read_bytes()
    value = conformance.unwrap(files[conformance.SET_FILE])
    e = next(x for x in value['scenarios'] if x['id'] == 'ADV-02')
    data = wrap({'scenario': 'ADV-02', 'row_hash': e['row_hash'], 'cases': [case()]})
    files[CB_PATH] = data
    e['fixture'] = {'path': CB_PATH, 'sha256': conformance.sha256(data)}
    files[conformance.SET_FILE] = wrap(value)
    files[TEST_RECORDS] = freeze_line(conformance.sha256(files[conformance.SET_FILE]))
    return files


def run_files(files, **kw):
    return conformance.run(ROOT, COMMIT, 'TASK-056', read=files.get,
                           listing=lambda: sorted(p for p in files if p.startswith('docs/records/')), **kw)


def frozen_case():
    """The frozen fixture's one case (TASK-058 AC5), read with pathlib's read_bytes and unwrapped as the runner does."""
    data = (ROOT / CB_PATH).read_bytes()
    if conformance.sha256(data) != ADV_02_SHA256:
        raise AssertionError('the ADV-02 fixture is not the file DM row F49 freezes')
    return conformance.unwrap(data)['cases'][0]


def without_the_violation(c):
    """AC5's control case: only the replay document's violation key removed, and the second session's log_seq set to
    3, the value the core's log then needs."""
    del c['document']['violation']
    c['continuation']['session']['inputs']['log_seq'] = 3
    return c


def logged(c, bypass):
    """The case through the runner's own case path with the root's core and in-memory stand-ins only: (the runner's
    result, the violation step's decision of step 1's result, the last decision.acceptance payload of the in-memory
    log). The log is kept by wrapping _CbLog.__init__ (it changes nothing the core does); with ``bypass``, step 1's
    comparison is replaced for this run only by a patch of conformance._violation_step that returns the STOP decision
    (decision D-1111 C2: scoped, checked restored by the caller)."""
    cb, status = conformance.load_cb(ROOT)
    if status != conformance.LOADED:
        raise AssertionError('the root\'s core is not loaded')
    seen, logs = [], []
    real_init = conformance._CbLog.__init__
    original = conformance._violation_step

    def keep(log, entry, store):
        real_init(log, entry, store)
        logs.append(log)

    def replay_kept(*args, **kwargs):
        out = cb['replay'](*args, **kwargs)
        seen.append(out)
        return out
    entry = dict(cb, replay=replay_kept)
    with mock.patch.object(conformance._CbLog, '__init__', keep):
        if bypass:
            with mock.patch.object(conformance, '_violation_step', lambda result: {'decision': 'STOP: violation'}):
                r = conformance._run_cb_case(c, entry, conformance.cb_core_root(ROOT))
        else:
            r = conformance._run_cb_case(c, entry, conformance.cb_core_root(ROOT))
    step = original(seen[0])
    events = [json.loads(x) for x in logs[-1].log.decode('utf-8').splitlines()]
    acc = [e['payload'] for e in events if e.get('type') == 'decision.acceptance']
    return r, (step or {}).get('decision'), acc[-1] if acc else None


def facts(payload):
    return {'decision': payload['decision'], 'next_task_state': payload['next_task_state'],
            'table_row': payload['table_row'], 'missing_gates': payload['missing_gates'],
            'failed_gates': payload['failed_gates'],
            'missing_types': [e['missing_types'] for e in payload['profile_used']]}


class RepositoryTree(unittest.TestCase):
    def test_the_run_over_the_repository_tree(self):
        """TASK-056 AC11, AC16: with no stand-in, the run record has the base's keys (no capability_boundaries), the
        run counts, ADV-02 is NOT_RUN for "no fixture", every other scenario is PASS with no reason, and the outcome is
        pass."""
        if cb_state() == 'present':
            # In the present state of ADV-02's entry (TASK-058 AC4), ADV-02 is PASS and the record holds
            # capability_boundaries; the docstring above describes the null state.
            r = conformance.run(ROOT, COMMIT, 'TASK-056')
            self.assertEqual(set(r.value), BASE_KEYS | {'capability_boundaries'})
            self.assertEqual(r.value['capability_boundaries'], cb_record())
            self.assertTrue(r.value['counts'])
            self.assertEqual(r.problems, [])
            self.assertEqual((r.results['ADV-02'], r.reasons['ADV-02']), (conformance.PASS, ''))
            others = {i: (res, r.reasons[i]) for i, res in r.results.items() if i != 'ADV-02'}
            self.assertEqual(len(others), 31)
            self.assertEqual(set(others.values()), {(conformance.PASS, '')})
            self.assertEqual(r.record['outcome'], 'pass')
            return
        r = conformance.run(ROOT, COMMIT, 'TASK-056')
        self.assertEqual(set(r.value), BASE_KEYS)
        self.assertTrue(r.value['counts'])
        self.assertEqual(r.problems, [])
        self.assertEqual((r.results['ADV-02'], r.reasons['ADV-02']), (conformance.NOT_RUN, 'no fixture'))
        others = {i: (res, r.reasons[i]) for i, res in r.results.items() if i != 'ADV-02'}
        self.assertEqual(len(others), 31)
        self.assertEqual(set(others.values()), {(conformance.PASS, '')})
        self.assertEqual(r.record['outcome'], 'pass')


class WithFixture(unittest.TestCase):
    def test_the_root_core_passes(self):
        """TASK-056 AC17: an in-memory fixture under fixtures_cb/ and the root's core: ADV-02 PASS, the run counts,
        the key present (this tests the runner, not the core's conformance)."""
        r = run_files(files_with_fixture())
        self.assertEqual(r.results['ADV-02'], conformance.PASS)
        self.assertTrue(r.value['counts'])
        self.assertEqual(len(r.value['capability_boundaries']), 3)
        self.assertEqual(r.record['outcome'], 'pass')

    def test_a_core_that_does_not_stop_or_does_not_reject_fails(self):
        """TASK-056 AC17: a core stand-in that does not stop the session, and one whose evaluation does not reject:
        ADV-02 FAIL; the run does not count because a stand-in entry is used (a stand-in never counts), not because
        of the FAIL, and the outcome is fail."""
        cb, status = conformance.load_cb(ROOT)
        self.assertEqual(status, conformance.LOADED)

        def no_stop(*args, **kwargs):
            r = replay.replay(*args, **kwargs)
            return dict(r, steps=[s for s in r['steps'] if s['step'] != 'violation'])
        accept = lambda *a, **k: {'result': 'evaluated', 'decision': 'ACCEPT', 'next_task_state': 'ACCEPTED'}
        for change in ({'replay': no_stop}, {'evaluate_task': accept}):
            r = run_files(files_with_fixture(), cb=dict(cb, **change))
            self.assertEqual(r.results['ADV-02'], conformance.FAIL)
            self.assertFalse(r.value['counts'])
            self.assertEqual(r.record['outcome'], 'fail')


class M13Control(unittest.TestCase):
    def test_the_frozen_case_passes_without_any_patch(self):
        """TASK-058 AC5 (decision D-1111 C2): the frozen fixture's case through the runner's own case path and the root's
        core, with no patch at all: PASS."""
        cb, status = conformance.load_cb(ROOT)
        self.assertEqual(status, conformance.LOADED)
        self.assertEqual(conformance._run_cb_case(frozen_case(), cb, conformance.cb_core_root(ROOT)),
                         (conformance.PASS, ''))

    def test_the_frozen_case_stops_and_rejects(self):
        """TASK-058 AC5: as frozen, step 1's decision is STOP: violation and the evaluation gives REJECT and REJECTED,
        table row 1, with nothing missing."""
        r, stop, payload = logged(frozen_case(), bypass=False)
        self.assertEqual(r, (conformance.PASS, ''))
        self.assertEqual(stop, 'STOP: violation')
        self.assertEqual(facts(payload), {'decision': 'REJECT', 'next_task_state': 'REJECTED', 'table_row': 1,
                                          'missing_gates': [], 'failed_gates': [], 'missing_types': [[]]})

    def test_without_the_violation_the_profile_is_met(self):
        """TASK-058 AC5, M13's control (decisions D-1079, D-1086, D-1109 C5, D-1111): the same case with only the
        violation removed, log_seq 3 and step 1's comparison bypassed for this run only gives NEEDS_REVIEW and
        IN_REVIEW, table row 5, no missing gate and no missing type; so the fixture's REJECT comes from the violation
        alone. The bypass is restored afterwards."""
        original = conformance._violation_step
        r, stop, payload = logged(without_the_violation(frozen_case()), bypass=True)
        self.assertIs(conformance._violation_step, original)
        self.assertIsNone(stop)
        self.assertEqual(r, (conformance.FAIL, "not met: step 3: decision 'NEEDS_REVIEW', step 3: next_state 'IN_REVIEW'"))
        self.assertEqual(facts(payload), {'decision': 'NEEDS_REVIEW', 'next_task_state': 'IN_REVIEW', 'table_row': 5,
                                          'missing_gates': [], 'failed_gates': [], 'missing_types': [[]]})

    def test_the_named_variant_a_failing_gate(self):
        """TASK-058 AC7 (decision D-1096 C3, D-1111): AC5's control case with the extra record of gate G1 given outcome
        fail gives NEEDS_REWORK and REWORK, table row 2, G1 missing and failed, and the runner's FAIL at step 3; so
        another reason moves the decision away from both NEEDS_REVIEW and REJECT. The bypass is restored afterwards."""
        c = without_the_violation(frozen_case())
        g1 = [x for x in c['evaluation']['extra_records'] if x.get('gate') == 'G1']
        self.assertEqual(len(g1), 1)
        g1[0]['outcome'] = 'fail'
        original = conformance._violation_step
        r, stop, payload = logged(c, bypass=True)
        self.assertIs(conformance._violation_step, original)
        self.assertEqual(r, (conformance.FAIL, "not met: step 3: decision 'NEEDS_REWORK', step 3: next_state 'REWORK'"))
        self.assertEqual(facts(payload), {'decision': 'NEEDS_REWORK', 'next_task_state': 'REWORK', 'table_row': 2,
                                          'missing_gates': ['G1'], 'failed_gates': ['G1'], 'missing_types': [[]]})


class PresentStateRun(unittest.TestCase):
    def test_the_present_set_file_passes(self):
        """TASK-058 AC6 (decision D-1086): conformance.run over in-memory files equal to the tree's, with the set file
        replaced by the present state's bytes of AC1 and one in-memory freeze record of their hash, and the root's core:
        ADV-02 PASS, the run counts, and its record's outcome is pass."""
        files = {}
        for p in ROOT.glob('**/*'):
            rel = p.relative_to(ROOT).as_posix()
            if p.is_file() and (rel.startswith(('docs/records/', 'tests/conformance/', 'src/aieos_bootstrap/'))
                                or rel == conformance.SCENARIO_FILE):
                files[rel] = p.read_bytes()
        value = conformance.unwrap(files[conformance.SET_FILE])
        e = next(x for x in value['scenarios'] if x['id'] == 'ADV-02')
        e['fixture'] = {'path': CB_PATH, 'sha256': ADV_02_SHA256}
        value['fixture_set_version'] = 6
        files[conformance.SET_FILE] = wrap(value)
        self.assertEqual(conformance.sha256(files[conformance.SET_FILE]), CB_SET_SHA256)
        self.assertEqual(conformance.sha256(files[CB_PATH]), ADV_02_SHA256)
        files['docs/records/TEST-58.jsonl'] = freeze_line(CB_SET_SHA256)
        r = run_files(files)
        self.assertEqual((r.results['ADV-02'], r.reasons['ADV-02']), (conformance.PASS, ''))
        self.assertTrue(r.value['counts'])
        self.assertEqual(r.problems, [])
        self.assertEqual(r.record['outcome'], 'pass')


if __name__ == '__main__':
    unittest.main()

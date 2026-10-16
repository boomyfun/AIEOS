"""Integration tests of the conformance runner's Capability Boundaries entry (TASK-056 AC11 and AC17), end to end over
the repository's own tree: with no stand-in, ADV-02 stays NOT_RUN and the run record has no capability_boundaries key;
with an in-memory set file whose ADV-02 entry names an in-memory fixture under fixtures_cb/ and the root's core, ADV-02
is PASS; with a core that does not stop the session, or one whose evaluation does not reject, ADV-02 is FAIL and the
run does not count. That PASS tests the runner, not the core's conformance, and is not conformance evidence (AC16).
The case builder is a copy of tests/unit/test_runner_cb.py's (the test folders share no module). No file is written.
"""
import hashlib
import json
import pathlib
import unittest

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


class RepositoryTree(unittest.TestCase):
    def test_the_run_over_the_repository_tree(self):
        """TASK-056 AC11, AC16: with no stand-in, the run record has the base's keys (no capability_boundaries), the
        run counts, ADV-02 is NOT_RUN for "no fixture", every other scenario is PASS with no reason, and the outcome is
        pass."""
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
        ADV-02 FAIL and the run does not count."""
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


if __name__ == '__main__':
    unittest.main()

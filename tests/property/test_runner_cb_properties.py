"""Property tests of the conformance runner's Capability Boundaries entry (TASK-056 AC17), standard library only, with
fixed seeds: the same inputs always give the same result; a one-byte change of the fixture never gives PASS; varied
placeholders never give PASS where the core does not stop or does not reject, and a log_seq mismatch is NOT_RUN, never
FAIL; and the invariants INV-005 to INV-008 as they apply to this entry. The case builder is a copy of
tests/unit/test_runner_cb.py's (the test folders share no module). No file is written.
"""
import hashlib
import pathlib
import random
import unittest

from aieos_bootstrap import conformance
from aieos_bootstrap import replay

ROOT = pathlib.Path(__file__).resolve().parents[2]
TASK = 'TASK-100'
REC = 'replay:session-one'
CODE = 'c' * 64
CONTRACT = 'task: TASK-100\nwrite_set:\n  paths: [docs/notes/**]\n'
H = hashlib.sha256(CONTRACT.encode('utf-8')).hexdigest()
OUTSIDE = 'src/outside.py'
MAIN, MINE, TREE = '1' * 40, '3' * 40, '4' * 40
CB_PATH = 'tests/conformance/fixtures_cb/adv_02.py'
RESULTS = (conformance.PASS, conformance.FAIL, conformance.NOT_RUN)


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


def case(log_seq=5, session='session-2', violation_id='violation-1', submit_id='submitted-1'):
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
            'violation': {'observation': obs, 'event_id': violation_id, 'at': '2026-10-16T10:20:00Z'},
            'end_at': '2026-10-16T10:40:00Z'},
        'continuation': {
            'session': {'task_id': TASK, 'session_id': session, 'holder': 'agent-1', 'inputs': rc_inputs(log_seq),
                        'code_sha256': CODE, 'start_at': '2026-10-16T12:00:00Z',
                        'expires_at': '2026-10-16T13:00:00Z', 'expected_token': {'epoch': 'e-replay', 'counter': 2}},
            'submission': {'commit_id': MINE, 'commit_text': mine, 'event_id': submit_id,
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


def scenario(data, digest, cb):
    """ADV-02's result over the given fixture bytes and set entry hash, with the bound file's row and capability."""
    rows = {'ADV-02': 'f' * 64}
    caps = {'ADV-02': 'Capability Boundaries'}
    entry = {'id': 'ADV-02', 'row_hash': 'f' * 64, 'capability': 'Capability Boundaries',
             'fixture': {'path': CB_PATH, 'sha256': digest}}
    tree = conformance._Tree(ROOT, read=lambda p: data if p == CB_PATH else None)
    return conformance.run_scenario(tree, entry, rows, None, caps, cb=cb)


def fixture_bytes(c):
    return wrap({'scenario': 'ADV-02', 'row_hash': 'f' * 64, 'cases': [c]})


def core():
    cb, status = conformance.load_cb(ROOT)
    assert status == conformance.LOADED
    return cb


class Properties(unittest.TestCase):
    def test_same_inputs_same_result(self):
        """TASK-056 AC17: the same inputs always give the same result and reason (fixed seed)."""
        rng = random.Random(56)
        for _ in range(5):
            c = case(session='session-%d' % rng.randrange(2, 100))
            data = fixture_bytes(c)
            first = scenario(data, conformance.sha256(data), core())
            self.assertEqual(first, scenario(data, conformance.sha256(data), core()))
            self.assertEqual(first[0], conformance.PASS)

    def test_a_one_byte_change_never_passes(self):
        """TASK-056 AC17 and INV-007: a one-byte change of the fixture, with the set entry's hash kept, is never run
        and never PASS."""
        rng = random.Random(5602)
        data = fixture_bytes(case())
        digest = conformance.sha256(data)
        for _ in range(40):
            i = rng.randrange(len(data))
            changed = data[:i] + bytes([(data[i] + 1 + rng.randrange(254)) % 256]) + data[i + 1:]
            result, reason = scenario(changed, digest, core())
            self.assertEqual(result, conformance.NOT_RUN)
            self.assertEqual(reason, 'the fixture\'s SHA-256 differs from its set entry')

    def test_varied_placeholders_and_log_lengths(self):
        """TASK-056 AC17: over varied ids, a core that does not stop or does not reject is never PASS; a log_seq other
        than the log's is NOT_RUN, never FAIL."""
        rng = random.Random(5603)

        def no_stop(*args, **kwargs):
            r = replay.replay(*args, **kwargs)
            return dict(r, steps=[s for s in r['steps'] if s['step'] != 'violation'])
        accept = lambda *a, **k: {'result': 'evaluated', 'decision': 'ACCEPT', 'next_task_state': 'ACCEPTED'}
        for _ in range(6):
            c = case(violation_id='violation-%d' % rng.randrange(1000), submit_id='submitted-%d' % rng.randrange(1000))
            data = fixture_bytes(c)
            for change in ({'replay': no_stop}, {'evaluate_task': accept}):
                self.assertNotEqual(scenario(data, conformance.sha256(data), dict(core(), **change))[0],
                                    conformance.PASS)
            seq = rng.choice([s for s in range(0, 12) if s != 5])
            bad = fixture_bytes(case(log_seq=seq))
            self.assertEqual(scenario(bad, conformance.sha256(bad), core())[0], conformance.NOT_RUN)

    def test_the_invariants(self):
        """TASK-056 AC17: INV-005, every result is PASS, FAIL or NOT_RUN; INV-006, with no core no scenario is PASS;
        INV-008, a stand-in entry never makes a run count."""
        data = fixture_bytes(case())
        for cb in (core(), None, dict(core(), replay=lambda *a, **k: None)):
            result = scenario(data, conformance.sha256(data), cb)[0]
            self.assertIn(result, RESULTS)
            if cb is None:
                self.assertEqual(result, conformance.NOT_RUN)
        r = conformance.run(ROOT, 'a' * 40, 'TASK-056', cb=core())
        self.assertFalse(r.value['counts'])
        self.assertNotIn('capability_boundaries', r.value)


if __name__ == '__main__':
    unittest.main()

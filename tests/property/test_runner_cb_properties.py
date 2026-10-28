"""Property tests of the conformance runner's Capability Boundaries entry (TASK-056 AC17), standard library only, with
fixed seeds: the same inputs always give the same result, and two runs over the same in-memory files the same run
record; a one-byte change of the fixture never gives PASS; varied
placeholders never give PASS where the core does not stop or does not reject, and a log_seq mismatch is NOT_RUN, never
FAIL; and the invariants INV-005 to INV-008 as they apply to this entry. The case builder is a copy of
tests/unit/test_runner_cb.py's (the test folders share no module). No file is written.
"""
import hashlib
import json
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


def freeze_line(digest):
    rec = {'approval_binding': {'hash': digest, 'kind': 'change_request'}, 'decision_ref': 'D-000',
           'fact_kind': 'authority', 'record_id': 'TEST-freeze-' + digest[:16], 'recorder': 'a property test',
           'source_class': 'decision_agent', 'subject': 'TASK-056'}
    return (json.dumps(rec, sort_keys=True) + '\n').encode('utf-8')


def files_with_fixture(c):
    """The repository's own files that a run reads, with an in-memory fixture under fixtures_cb/ and a set file naming
    it (a copy of tests/integration/test_runner_cb_run.py's)."""
    files = {}
    for p in ROOT.glob('**/*'):
        rel = p.relative_to(ROOT).as_posix()
        if p.is_file() and (rel.startswith(('docs/records/', 'tests/conformance/', 'src/aieos_bootstrap/'))
                            or rel == conformance.SCENARIO_FILE):
            files[rel] = p.read_bytes()
    value = conformance.unwrap(files[conformance.SET_FILE])
    e = next(x for x in value['scenarios'] if x['id'] == 'ADV-02')
    data = wrap({'scenario': 'ADV-02', 'row_hash': e['row_hash'], 'cases': [c]})
    files[CB_PATH] = data
    e['fixture'] = {'path': CB_PATH, 'sha256': conformance.sha256(data)}
    files[conformance.SET_FILE] = wrap(value)
    files['docs/records/TEST-56.jsonl'] = freeze_line(conformance.sha256(files[conformance.SET_FILE]))
    return files


def run_files(files):
    return conformance.run(ROOT, 'a' * 40, 'TASK-056', read=files.get,
                           listing=lambda: sorted(p for p in files if p.startswith('docs/records/')))


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
        # TASK-058 AC4 with erratum E1 (decision D-1116 C2): in the present state the key is written, and its hashes are
        # null because this run passes the root's core as a stand-in entry.
        if cb_state() == 'present':
            self.assertEqual(r.value['capability_boundaries'],
                             [{'path': conformance.cb_path(n), 'sha256': None} for n in ('replay', 'adapter', 'evaluation')])
        else:
            self.assertNotIn('capability_boundaries', r.value)

    def test_the_same_files_give_the_same_run_record(self):
        """TASK-056 AC17 (decision D-1079, M16): two runs over the same in-memory files, with an in-memory fixture under
        fixtures_cb/ and the root's core, give equal run-record values and records (fixed seed for the varied ids)."""
        rng = random.Random(5604)
        for _ in range(2):
            files = files_with_fixture(case(violation_id='violation-%d' % rng.randrange(1000)))
            first, second = run_files(files), run_files(files)
            self.assertEqual(first.value, second.value)
            self.assertEqual(first.record, second.record)
            self.assertEqual(first.results['ADV-02'], conformance.PASS)


if __name__ == '__main__':
    unittest.main()

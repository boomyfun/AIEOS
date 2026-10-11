"""Integration tests of the conformance runner's Risk Engine entry over the repository's own tree (TASK-017 AC10 and
AC16): the run record over the tree as it is, and an in-memory RISK-01 fixture run with the root's governor and with a
stand-in derivation. The in-memory PASS tests the runner, not the governor's conformance, and is not conformance
evidence (AC15). No file is written."""
import copy
import json
import pathlib
import unittest

from aieos_bootstrap import conformance

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMMIT = 'b' * 40
TASK = 'TASK-017'
RISK_PATH = 'tests/conformance/fixtures_risk/risk_01.py'
TEST_RECORDS = 'docs/records/TEST-17.jsonl'
LOW = [{'dimension': 'functional', 'evidence_types': ['build', 'lint']}]


RISK_01_SHA256 = '8a0bdb1665dc30998fae3a6926a37f854a38780695e6276d62ce5d9ece06a45b'


def risk_state(value=None):
    """The state of the set file's RISK-01 entry (TASK-019, contract AC1): 'null' when it names no fixture, 'present'
    when it names the file conformance.expected_path gives with the SHA-256 that DM row F34's freeze binds, that file
    in the tree having that SHA-256; any other value fails. Without a value it reads the tree's set file."""
    if value is None:
        value = conformance.unwrap((ROOT / conformance.SET_FILE).read_bytes())
    risk = [e for e in value['scenarios'] if e['capability'] == conformance.RISK_ENGINE]
    if [e['id'] for e in risk] != ['RISK-01']:
        raise AssertionError('the Risk Engine entries are not exactly RISK-01')
    if risk[0]['fixture'] is None:
        return 'null'
    path = conformance.expected_path('RISK-01', conformance.RISK_ENGINE)
    if (risk[0]['fixture'] == {'path': path, 'sha256': RISK_01_SHA256}
            and conformance.sha256((ROOT / path).read_bytes()) == RISK_01_SHA256):
        return 'present'
    raise AssertionError('the RISK-01 entry names neither no fixture nor its frozen file')


def real_files():
    files = {}
    for path in (conformance.RUNNER_PATH, conformance.SET_FILE, conformance.SCENARIO_FILE):
        files[path] = (ROOT / path).read_bytes()
    for folder in (conformance.FIXTURE_DIR, conformance.RC_FIXTURE_DIR):
        for p in sorted((ROOT / folder).glob('*.py')):
            files[folder + '/' + p.name] = p.read_bytes()
    for p in sorted((ROOT / conformance.RECORDS_DIR).glob('*.jsonl')):
        files[conformance.RECORDS_DIR + '/' + p.name] = p.read_bytes()
    return files


def wrap(value):
    return conformance.FIRST + conformance.canonical_text(value) + conformance.LAST


def freeze_line(digest):
    rec = {'approval_binding': {'hash': digest, 'kind': 'change_request'}, 'decision_ref': 'D-000',
           'fact_kind': 'authority', 'record_id': 'TEST-freeze-' + digest[:16], 'recorder': 'a unit test',
           'source_class': 'decision_agent', 'subject': 'TASK-018'}
    return (json.dumps(rec, sort_keys=True) + '\n').encode('utf-8')


def values(paths=('unmatched/file.txt',)):
    """Values in the form of section 10 whose Given holds: no rule and no article meets the changed path."""
    return {
        'contract': {'traces_to': ['docs/specs/conformance-files.md#10'], 'risk': 'low', 'owner_kept_act': False,
                     'verification_plan': ['G0', 'G1', 'G2', 'G3']},
        'changed_paths': list(paths),
        'risk_rules': [{'match': ['docs/**', '*.md'], 'class': 'low'}, {'match': ['src/**', 'tests/**'], 'class': 'medium'}],
        'owner_kept_rules': [],
        'articles': [{'id': 'INV-001', 'scope': ['src/**'], 'evidence_required': ['deterministic_rule']}],
        'default_profiles': {'low': copy.deepcopy(LOW),
                             'medium': [{'dimension': 'functional', 'evidence_types': ['unit_test']}],
                             'high': [{'dimension': 'functional', 'evidence_types': ['unit_test']}],
                             'critical': [{'dimension': 'functional', 'evidence_types': ['unit_test']}]},
        'requirement_profiles': [],
        'delegation': True,
        'evidence_comparison': {'weakens': False},
        'auto_accept': {'low': False, 'medium': False, 'high': False, 'critical': False},
        'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1',
    }


def risk_case(files):
    """One case of section 10: the request and records of ACC-01's first case, with the values' changed paths."""
    acc = conformance.unwrap(files[conformance.module_path('ACC-01')])['cases'][0]
    v = values()
    request = copy.deepcopy(acc['request'])
    request['changed_paths'] = list(v['changed_paths'])
    request['task_state'] = 'VERIFYING'
    return {'values': v, 'request': request, 'records': copy.deepcopy(acc['records']), 'when': 'evaluate',
            'expected': {'risk_not': ['low'],
                         'profile_excludes': [{'dimension': 'functional', 'evidence_type': 'build'},
                                              {'dimension': 'functional', 'evidence_type': 'lint'}],
                         'not_fixed': ['decision', 'next_state']}}


def entry_of(files):
    sv = conformance.unwrap(files[conformance.SET_FILE])
    return next(e for e in sv['scenarios'] if e['id'] == 'RISK-01'), sv


def put_fixture(files, value, path=RISK_PATH):
    """Writes a Risk Engine fixture, points RISK-01's set entry at it and freezes the new set."""
    data = wrap(value)
    files[path] = data
    entry, sv = entry_of(files)
    entry['fixture'] = {'path': path, 'sha256': conformance.sha256(data)}
    files[conformance.SET_FILE] = wrap(sv)
    files[TEST_RECORDS] = files.get(TEST_RECORDS, b'') + freeze_line(conformance.sha256(files[conformance.SET_FILE]))


def fixture(files, cases=None):
    entry, _ = entry_of(files)
    return {'scenario': 'RISK-01', 'row_hash': entry['row_hash'], 'cases': cases or [risk_case(files)]}


def tree_reader(files):
    def read(path):
        if path in files:
            return files[path]
        p = ROOT / path
        return p.read_bytes() if p.is_file() else None

    def listing():
        return sorted(p for p in files if p.startswith(conformance.RECORDS_DIR + '/') and p.endswith('.jsonl'))
    return read, listing


class RunnerRiskEndToEndTest(unittest.TestCase):
    def test_the_tree_as_it_is(self):
        """AC10: RISK-01's entry is null, so it is NOT_RUN for "no fixture"; the run record keeps its keys, counts and
        every other result, and its outcome is pass."""
        # In the present state of RISK-01's entry (TASK-019 AC5) it runs with the root's governor and is PASS, ADV-02
        # stays NOT_RUN for "no fixture", and every other result passes.
        if risk_state() == 'present':
            r = conformance.run(ROOT, COMMIT, TASK)
            self.assertEqual(set(r.value), {'set_file_sha256', 'scenario_set_version', 'fixture_set_version', 'runner',
                                            'governor_identity', 'commit', 'counts', 'results', 'resume_check'})
            self.assertTrue(r.value['counts'], r.problems)
            for sid, result in r.results.items():
                if sid == 'ADV-02':
                    self.assertEqual((result, r.reasons[sid]), (conformance.NOT_RUN, 'no fixture'))
                else:
                    self.assertEqual((result, r.reasons[sid]), (conformance.PASS, ''), sid)
            self.assertEqual(r.record['outcome'], 'pass')
            return
        r = conformance.run(ROOT, COMMIT, TASK)
        self.assertEqual(set(r.value), {'set_file_sha256', 'scenario_set_version', 'fixture_set_version', 'runner',
                                        'governor_identity', 'commit', 'counts', 'results', 'resume_check'})
        self.assertTrue(r.value['counts'], r.problems)
        for sid, result in r.results.items():
            if sid in ('RISK-01', 'ADV-02'):
                self.assertEqual((result, r.reasons[sid]), (conformance.NOT_RUN, 'no fixture'))
            else:
                self.assertEqual(result, conformance.PASS, (sid, r.reasons[sid]))
        self.assertEqual(r.record['outcome'], 'pass')

    def run_fixture(self, derive=None):
        files = real_files()
        put_fixture(files, fixture(files))
        read, listing = tree_reader(files)
        return conformance.run(ROOT, COMMIT, TASK, read=read, listing=listing, derive=derive)

    def test_the_root_governor_meets_an_in_memory_fixture(self):
        r = self.run_fixture()
        self.assertEqual((r.results['RISK-01'], r.reasons['RISK-01']), (conformance.PASS, ''))
        # AC10's outcome rule with a Risk Engine scenario PASS in a real run (in memory; a test of the runner).
        self.assertTrue(r.value['counts'], r.problems)
        self.assertEqual(r.record['outcome'], 'pass')

    def test_a_derivation_that_classifies_low_fails(self):
        def derive(values):
            out = {'risk': 'low', 'evidence_profile': copy.deepcopy(LOW)}
            return out
        r = self.run_fixture(derive)
        self.assertEqual(r.results['RISK-01'], conformance.FAIL)
        self.assertFalse(r.value['counts'])

    def test_the_state_check_fails_on_a_wrong_state(self):
        """TASK-019, contract AC1 and AC10 R1: no fixture and the frozen file with its hash are the two states; another
        path, another hash or a second Risk Engine entry fails."""
        path = conformance.expected_path('RISK-01', conformance.RISK_ENGINE)

        def with_fixture(fixture_value):
            value = conformance.unwrap((ROOT / conformance.SET_FILE).read_bytes())
            next(e for e in value['scenarios'] if e['id'] == 'RISK-01')['fixture'] = fixture_value
            return value
        self.assertEqual(risk_state(with_fixture(None)), 'null')
        self.assertEqual(risk_state(with_fixture({'path': path, 'sha256': RISK_01_SHA256})), 'present')
        with self.assertRaises(AssertionError):
            risk_state(with_fixture({'path': path + '.other', 'sha256': RISK_01_SHA256}))
        with self.assertRaises(AssertionError):
            risk_state(with_fixture({'path': path, 'sha256': '0' * 64}))
        second = with_fixture(None)
        extra = copy.deepcopy(next(e for e in second['scenarios'] if e['id'] == 'RISK-01'))
        extra['id'] = 'RISK-02'
        second['scenarios'].append(extra)
        with self.assertRaises(AssertionError):
            risk_state(second)


if __name__ == '__main__':
    unittest.main()

"""Property tests of the conformance runner's Risk Engine entry (TASK-017 AC16; standard library only, fixed seeds).

Every input is built in memory from the repository's own files; no file is written. Stand-in derivations and acceptance
functions are test seams (AC3)."""
import copy
import json
import pathlib
import random
import re
import unittest

from aieos_bootstrap import conformance

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMMIT = 'c' * 40
TASK = 'TASK-017'
RISK_PATH = 'tests/conformance/fixtures_risk/risk_01.py'
TEST_RECORDS = 'docs/records/TEST-17.jsonl'
LOW = [{'dimension': 'functional', 'evidence_types': ['build', 'lint']}]


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


def put_raw(files, data, path=RISK_PATH):
    """As put_fixture, with the fixture's bytes given as they are."""
    files[path] = data
    entry, sv = entry_of(files)
    entry['fixture'] = {'path': path, 'sha256': conformance.sha256(data)}
    files[conformance.SET_FILE] = wrap(sv)
    files[TEST_RECORDS] = files.get(TEST_RECORDS, b'') + freeze_line(conformance.sha256(files[conformance.SET_FILE]))



def go(files, derive, evaluate=None):
    def read(path):
        return files.get(path)

    def listing():
        return sorted(p for p in files if p.startswith(conformance.RECORDS_DIR + '/') and p.endswith('.jsonl'))
    return conformance.run(ROOT, COMMIT, TASK, read=read, listing=listing, derive=derive,
                           evaluate=evaluate or (lambda req, inp, recs: {
                               'record_id': 'DEC-1', 'fact_kind': 'interpretation',
                               'source_class': 'deterministic_tool_external_ci', 'recorder': 'a stand-in',
                               'subject': req['task_id'], 'decision': None, 'error': 'risk', 'profile_used': []}))


def none_derive(values):
    return {'risk': None, 'evidence_profile': None}


NAMES = ['a', 'b', 'src', 'docs', 'x.py', 'r.md', 'c-d', 'e_f']


def random_path(rng):
    return '/'.join(rng.choice(NAMES) for _ in range(rng.randint(1, 4)))


class RiskEntryProperties(unittest.TestCase):
    def test_the_same_inputs_give_the_same_record(self):
        files = real_files()
        put_fixture(files, fixture(files))
        self.assertEqual(go(files, none_derive).text, go(files, none_derive).text)

    def test_a_one_byte_change_never_passes(self):
        rng = random.Random(17)
        base = real_files()
        put_fixture(base, fixture(base))
        data = base[RISK_PATH]
        for _ in range(40):
            files = dict(base)
            i = rng.randrange(len(data))
            files[RISK_PATH] = data[:i] + bytes([(data[i] + rng.randint(1, 255)) % 256]) + data[i + 1:]
            self.assertNotEqual(go(files, none_derive).results['RISK-01'], conformance.PASS)

    def test_a_rehashed_one_byte_change(self):
        # The fixture's bytes changed and the set entry re-frozen over them, so the form checks are what decide:
        # the unchanged fixture passes; any change runs to one of the three results without an exception; a change
        # inside a key of the fixture's object never passes.
        rng = random.Random(18)
        base = real_files()
        put_fixture(base, fixture(base))
        self.assertEqual(go(base, none_derive).results['RISK-01'], conformance.PASS)
        data = base[RISK_PATH]
        keys = [m.start() + 1 + k for key in (b'"risk_not"', b'"profile_excludes"', b'"not_fixed"', b'"changed_paths"',
                                              b'"risk_rules"', b'"when"', b'"row_hash"')
                for m in re.finditer(re.escape(key), data) for k in range(len(key) - 2)]
        for n in range(80):
            i = rng.choice(keys) if n % 2 else rng.randrange(len(data))
            files = dict(base)
            mutated = data[:i] + bytes([(data[i] + rng.randint(1, 255)) % 256]) + data[i + 1:]
            put_raw(files, mutated)
            result = go(files, none_derive).results['RISK-01']
            self.assertIn(result, (conformance.PASS, conformance.FAIL, conformance.NOT_RUN))
            if n % 2:
                self.assertNotEqual(result, conformance.PASS, (i, mutated[i - 5:i + 5]))

    def test_the_matcher_follows_point_6(self):
        rng = random.Random(6)
        for _ in range(400):
            path = random_path(rng)
            names = path.split('/')
            # "*" never crosses "/": a one-name pattern "*" under a folder matches only one name below it.
            self.assertEqual(conformance.path_matches(names[0] + '/*', path), len(names) == 2)
            # "**" matches at any depth below the folder.
            self.assertEqual(conformance.path_matches(names[0] + '/**', path), len(names) >= 2)
            # A pattern without "/" matches a file name in any folder.
            self.assertTrue(conformance.path_matches(names[-1], path))
            self.assertFalse(conformance.path_matches(names[-1] + 'z', path))
            # "**" in the middle matches any sequence of names, none included.
            self.assertEqual(conformance.path_matches(names[0] + '/**/' + names[-1], path), len(names) >= 2)
            # "*" inside a name matches any part of that name only.
            self.assertTrue(conformance.path_matches(names[-1][0] + '*', path))
            self.assertEqual(conformance.path_matches(names[0] + '*/*', path), len(names) == 2)
            # Matching is case-sensitive.
            self.assertFalse(conformance.path_matches(names[0].upper() + '/**', path))

    def test_a_low_classification_never_passes(self):
        rng = random.Random(8)
        files = real_files()
        put_fixture(files, fixture(files))
        for _ in range(20):
            low = rng.choice([{'risk': 'low', 'evidence_profile': None},
                              {'risk': rng.choice([None, 'high']), 'evidence_profile': copy.deepcopy(LOW)}])
            self.assertEqual(go(files, lambda v, d=low: d).results['RISK-01'], conformance.FAIL)

    def test_inv_005_results_are_one_of_three(self):
        files = real_files()
        put_fixture(files, fixture(files))
        for derive in (none_derive, lambda v: 'a string', lambda v: {'risk': 'low', 'evidence_profile': None}):
            self.assertIn(go(files, derive).results['RISK-01'], (conformance.PASS, conformance.FAIL, conformance.NOT_RUN))

    def test_inv_006_no_governor_no_pass(self):
        files = real_files()
        value = fixture(files)
        entry, _ = entry_of(files)
        for derive, evaluate in ((None, None), (none_derive, None), (None, lambda req, inp, recs: {})):
            self.assertEqual(conformance._run_risk_cases(value, entry, derive, evaluate)[0], conformance.NOT_RUN)

    def test_inv_007_a_changed_fixture_is_never_run(self):
        files = real_files()
        put_fixture(files, fixture(files))
        files[RISK_PATH] = files[RISK_PATH].replace(b'unmatched', b'unmatches')
        calls = []
        r = go(files, lambda v: calls.append(1) or {'risk': None, 'evidence_profile': None})
        self.assertEqual(r.results['RISK-01'], conformance.NOT_RUN)
        self.assertEqual(calls, [])

    def test_inv_008_a_stand_in_never_counts(self):
        files = real_files()
        put_fixture(files, fixture(files))
        self.assertFalse(go(files, none_derive).value['counts'])

    def test_inv_008_a_stand_in_derivation_alone_never_counts(self):
        # The root's governor (no stand-in acceptance function) with only a stand-in derivation: the derivation seam
        # alone makes the run not count, whatever the derivation returns.
        rng = random.Random(9)
        files = real_files()
        put_fixture(files, fixture(files))

        def read(path):
            return files.get(path)

        def listing():
            return sorted(p for p in files if p.startswith(conformance.RECORDS_DIR + '/') and p.endswith('.jsonl'))
        for _ in range(5):
            out = rng.choice([{'risk': None, 'evidence_profile': None}, {'risk': 'high', 'evidence_profile': None}])
            r = conformance.run(ROOT, COMMIT, TASK, read=read, listing=listing, derive=lambda v, d=out: d)
            self.assertFalse(r.value['counts'])
            self.assertIn('a stand-in derivation (reading)', r.problems)
            self.assertNotIn('a stand-in governor (reading)', r.problems)


if __name__ == '__main__':
    unittest.main()

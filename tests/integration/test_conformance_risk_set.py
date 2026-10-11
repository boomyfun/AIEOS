"""Integration test of the Risk Engine fixture of TASK-018 (docs/specs/conformance-files.md revision 7, sections 2, 7
and 10; docs/tasks/TASK-018.yaml AC6, AC7 and AC9): the file end to end against the bound scenario file, the policy and
the set file, and what the task leaves unchanged.

Files are read as bytes with pathlib's read_bytes and listed with pathlib's glob; no fixture or set module is ever
imported or executed. Each test holds in both states of RISK-01's set entry: null until TASK-020, or naming this file
with its SHA-256 after it (decision D-461 E2).
"""
import hashlib
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCENARIO_FILE = 'docs/pre-genesis/conformance-scenarios-initial.md'
RULES_FILE = 'docs/specs/risk-rules-gov-aieos.md'
SET_FILE = 'tests/conformance/set.py'
RECORDS_DIR = 'docs/records'
FIXTURE_DIR = 'tests/conformance/fixtures_risk'
FIXTURE = FIXTURE_DIR + '/risk_01.py'
FIRST, LAST = b"DATA = r'''", b"'''\n"
# TASK-018's own three test modules (AC7); each reads the fixture, so each names its folder.
OWN = ('tests/unit/test_conformance_risk_files.py', 'tests/integration/test_conformance_risk_set.py',
       'tests/property/test_conformance_risk_properties.py')
# The other modules that may name the folder (AC7): the runner, which section 10 has expect the folder for the Risk
# Engine, and the runner's test modules named test_runner_risk*.py, which name the path for in-memory bytes (in this
# form the test holds when TASK-019 changes them); and the set file, whose RISK-01 entry names this file's path as data
# once TASK-020 sets it (so the test holds in both states, as TASK-005's module allows the set file).
RUNNER = 'src/aieos_bootstrap/conformance.py'
RUNNER_TESTS = re.compile(r'tests/(?:unit|integration|property)/test_runner_risk[A-Za-z0-9_]*\.py')


def read(path):
    return (ROOT / path).read_bytes()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def unwrap(data):
    """The JSON value between the two fixed parts (section 2); the unit module checks the canonical form."""
    if not data.startswith(FIRST) or not data.endswith(LAST):
        raise ValueError('the file does not start with the first part and end with the last part')
    return json.loads(data[len(FIRST):len(data) - len(LAST)].decode('utf-8'))


def risk_row():
    lines = [l for l in read(SCENARIO_FILE).decode('utf-8').split('\n') if l.startswith('| RISK-01 | ')]
    assert len(lines) == 1
    return lines[0], [c.strip() for c in lines[0].strip().strip('|').split('|')]


def matches(pattern, path):
    """The tests' own matcher of point 6's forms (risk rules section 2), as in the unit module."""
    if '/' not in pattern:
        pattern = '**/' + pattern
    parts = pattern.split('/')
    rx = ''
    for i, part in enumerate(parts):
        last = i == len(parts) - 1
        if part == '**':
            rx += '[^/]+(?:/[^/]+)*' if last else '(?:[^/]+/)*'
        else:
            rx += ''.join('[^/]*' if c == '*' else re.escape(c) for c in part) + ('' if last else '/')
    return re.fullmatch(rx, path) is not None


def freeze_ids(digest):
    """The record ids of the authority records in docs/records/ that bind the given SHA-256 as a change request."""
    out = []
    for f in sorted((ROOT / RECORDS_DIR).glob('*.jsonl')):
        for line in f.read_bytes().decode('utf-8').split('\n'):
            if line:
                rec = json.loads(line)
                if rec.get('fact_kind') == 'authority' and rec.get('approval_binding') == {'kind': 'change_request', 'hash': digest}:
                    out.append(rec['record_id'])
    return out


def not_allowed(paths):
    """The given repository paths that are not allowed to name the folder, sorted."""
    return sorted(p for p in paths if p not in OWN and p not in (RUNNER, SET_FILE) and not RUNNER_TESTS.fullmatch(p))


def naming(name):
    """The .py files under src/ and tests/ whose bytes name the given folder name, listed with pathlib's glob."""
    found = []
    for d in ('src', 'tests'):
        for p in (ROOT / d).glob('**/*.py'):
            if name in p.read_bytes():
                found.append(p.relative_to(ROOT).as_posix())
    return sorted(found)


class RiskSetTest(unittest.TestCase):

    def test_the_folder_holds_exactly_the_one_file(self):
        # The CI's G1 build step compiles src and tests, so a __pycache__ folder may be there; it alone is skipped.
        names = sorted(p.name for p in (ROOT / FIXTURE_DIR).glob('*') if not (p.name == '__pycache__' and p.is_dir()))
        self.assertEqual(names, ['risk_01.py'])

    def test_the_file_names_its_bound_row_and_expects_its_cell(self):
        line, cells = risk_row()
        value = unwrap(read(FIXTURE))
        self.assertEqual((value['scenario'], value['row_hash']), ('RISK-01', sha256(line.encode('utf-8'))))
        self.assertEqual(cells[4], 'it is not classified low, and the low default profile is not applied')
        for case in value['cases']:
            self.assertEqual(case['expected']['risk_not'], ['low'])
            self.assertEqual(case['when'], 'evaluate')

    def test_the_given_holds_against_the_policy_file(self):
        """End to end: every path pattern of the policy's section 3 is read from the file, and no changed path of the
        fixture is matched by any of them, nor by R3's fail-closed reading."""
        text = read(RULES_FILE).decode('utf-8')
        block = text.split('## 3. The rules')[1].split('```yaml')[1].split('```')[0]
        patterns = [x.strip().strip('"') for items in re.findall(r'- match: \{ paths: \[([^\]]*)\] \}', block)
                    for x in items.split(',')]
        self.assertGreater(len(patterns), 20)
        patterns += ['src/**', 'tests/**']
        for case in unwrap(read(FIXTURE))['cases']:
            for path in case['values']['changed_paths']:
                self.assertEqual([p for p in patterns if matches(p, path)], [], path)
            self.assertEqual(case['request']['changed_paths'], case['values']['changed_paths'])

    def test_the_set_file_is_frozen_and_risk_01_is_null_or_this_file(self):
        """AC6, in both states: the set file has a SHA-256 that a freeze approval in docs/records/ binds (at TASK-018,
        TASK-014-freeze-set), and RISK-01's entry is null or names this file's path with its SHA-256."""
        data = read(SET_FILE)
        self.assertGreaterEqual(len(freeze_ids(sha256(data))), 1)
        entry = [e for e in unwrap(data)['scenarios'] if e['id'] == 'RISK-01']
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry[0]['capability'], 'Risk Engine')
        self.assertIn(entry[0]['fixture'], (None, {'path': FIXTURE, 'sha256': sha256(read(FIXTURE))}))

    def test_no_other_entry_names_the_folder(self):
        for e in unwrap(read(SET_FILE))['scenarios']:
            if e['id'] != 'RISK-01' and e['fixture']:
                self.assertFalse(e['fixture']['path'].startswith(FIXTURE_DIR + '/'), e['id'])

    def test_only_the_allowed_modules_name_the_folder(self):
        found = naming(FIXTURE_DIR.rsplit('/', 1)[1].encode('ascii'))
        self.assertEqual(not_allowed(found), [])
        self.assertTrue(set(OWN) <= set(found))

    def test_a_module_that_is_not_allowed_is_named(self):
        for other in ('src/aieos_bootstrap/governor.py', 'tests/unit/test_not_named_in_the_contract.py',
                      'tests/unit/test_runner_rc.py', 'tests/unit/test_runner_risk.txt',
                      'tests/conformance/fixtures/acc_01.py', 'tests/conformance/set_old.py'):
            self.assertEqual(not_allowed(list(OWN) + [RUNNER, SET_FILE, other]), [other])

    def test_the_allowed_modules_are_all_allowed(self):
        self.assertEqual(not_allowed(list(OWN) + [RUNNER, SET_FILE, 'tests/unit/test_runner_risk.py',
                                                  'tests/integration/test_runner_risk_run.py',
                                                  'tests/property/test_runner_risk_properties.py']), [])

    def test_the_set_file_naming_this_file_is_allowed(self):
        """The second state of RISK-01's entry (TASK-020): the set file then holds this file's path as data."""
        self.assertEqual(not_allowed([SET_FILE]), [])
        self.assertEqual(not_allowed(['tests/conformance/fixtures_risk/risk_02.py']), ['tests/conformance/fixtures_risk/risk_02.py'])

    def test_no_risk_file_in_the_m2_folder(self):
        # Only the M2 folder is named here: the Resume Check folder may be named only by the modules TASK-005's
        # integration test allows, and this module is not one of them.
        self.assertEqual([p.name for p in (ROOT / 'tests/conformance/fixtures').glob('risk*')], [])


if __name__ == '__main__':
    unittest.main()

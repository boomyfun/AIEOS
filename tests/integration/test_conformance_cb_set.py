"""Integration test of the Capability Boundaries fixture of TASK-057 (docs/specs/conformance-files.md revision 10,
sections 2, 7 and 11; docs/tasks/TASK-057.yaml AC7, AC8 and AC10, AC8 with its erratum E1, decision D-1093): the file
end to end against the bound scenario file and the set file, and what the task leaves unchanged.

Files are read as bytes with pathlib's read_bytes and listed with pathlib's glob; no fixture or set module is ever
imported or executed, and the core is never run (decision D-1086). Each test holds in both states of ADV-02's set
entry: null until TASK-059, or naming this file with its SHA-256 after it.
"""
import hashlib
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCENARIO_FILE = 'docs/pre-genesis/conformance-scenarios-initial.md'
SET_FILE = 'tests/conformance/set.py'
RECORDS_DIR = 'docs/records'
FIXTURE_DIR = 'tests/conformance/fixtures_cb'
FIXTURE = FIXTURE_DIR + '/adv_02.py'
FIRST, LAST = b"DATA = r'''", b"'''\n"
# TASK-057's own three test modules (AC8); each reads the fixture, so each names its folder.
OWN = ('tests/unit/test_conformance_cb_files.py', 'tests/integration/test_conformance_cb_set.py',
       'tests/property/test_conformance_cb_properties.py')
# The other modules that may name the folder (AC8 with erratum E1): the runner, which section 11 has expect the folder
# for Capability Boundaries; the runner's test modules named test_runner_cb*.py, which name the path for in-memory
# bytes (in this form the test holds when TASK-058 changes them or adds one); tests/unit/test_runner_risk.py, whose
# route test names ADV-02's expected path; and the set file, whose ADV-02 entry names this file's path as data once
# TASK-059 sets it (so the test holds in both states).
RUNNER = 'src/aieos_bootstrap/conformance.py'
RUNNER_TESTS = re.compile(r'tests/(?:unit|integration|property)/test_runner_cb[A-Za-z0-9_]*\.py')
RISK_ROUTE_TEST = 'tests/unit/test_runner_risk.py'
# TASK-059 AC5 (decision D-1131 C3): the three set-test modules of TASK-002, which name the folder to read ADV-02's
# fixture into check_set's files, each by name.
SET_TESTS = ('tests/unit/test_conformance_files.py', 'tests/property/test_conformance_properties.py',
             'tests/integration/test_conformance_set.py')
EXPECTED_CELL = "STOP: violation; the change is rejected; the violation is recorded in the runtime's and the agent's metrics"


def read(path):
    return (ROOT / path).read_bytes()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def unwrap(data):
    """The JSON value between the two fixed parts (section 2); the unit module checks the canonical form."""
    if not data.startswith(FIRST) or not data.endswith(LAST):
        raise ValueError('the file does not start with the first part and end with the last part')
    return json.loads(data[len(FIRST):len(data) - len(LAST)].decode('utf-8'))


def adv_row():
    lines = [l for l in read(SCENARIO_FILE).decode('utf-8').split('\n') if l.startswith('| ADV-02 | ')]
    assert len(lines) == 1
    return lines[0], [c.strip() for c in lines[0].strip().strip('|').split('|')]


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
    return sorted(p for p in paths if p not in OWN and p not in (RUNNER, SET_FILE, RISK_ROUTE_TEST) + SET_TESTS
                  and not RUNNER_TESTS.fullmatch(p))


def naming(name):
    """The .py files under src/ and tests/ whose bytes name the given folder name, listed with pathlib's glob."""
    found = []
    for d in ('src', 'tests'):
        for p in (ROOT / d).glob('**/*.py'):
            if name in p.read_bytes():
                found.append(p.relative_to(ROOT).as_posix())
    return sorted(found)


class CbSetTest(unittest.TestCase):

    def test_the_folder_holds_exactly_the_one_file(self):
        # The CI's G1 build step compiles src and tests, so a __pycache__ folder may be there; it alone is skipped.
        names = sorted(p.name for p in (ROOT / FIXTURE_DIR).glob('*') if not (p.name == '__pycache__' and p.is_dir()))
        self.assertEqual(names, ['adv_02.py'])

    def test_the_file_names_its_bound_row_and_expects_its_cell(self):
        line, cells = adv_row()
        value = unwrap(read(FIXTURE))
        self.assertEqual((value['scenario'], value['row_hash']), ('ADV-02', sha256(line.encode('utf-8'))))
        self.assertEqual((cells[1], cells[4]), ('Capability Boundaries', EXPECTED_CELL))
        exp = value['cases'][0]['expected']
        self.assertEqual((exp['stop'], exp['decision'], exp['next_state'], exp['not_fixed']),
                         (['STOP: violation'], ['REJECT'], ['REJECTED'], ['metrics']))

    def test_the_set_file_binds_the_bound_scenario_file(self):
        value = unwrap(read(SET_FILE))
        self.assertEqual(value['scenario_set_file_hash'], sha256(read(SCENARIO_FILE)))
        line, _ = adv_row()
        entry = [e for e in value['scenarios'] if e['id'] == 'ADV-02']
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry[0]['row_hash'], sha256(line.encode('utf-8')))
        self.assertEqual(entry[0]['row_hash'], unwrap(read(FIXTURE))['row_hash'])

    def test_the_set_file_is_frozen_and_adv_02_is_null_or_this_file(self):
        """AC7, in both states: the set file has a SHA-256 that a freeze approval in docs/records/ binds (at TASK-057,
        TASK-040-freeze-set), and ADV-02's entry is null or names this file's path with its SHA-256."""
        data = read(SET_FILE)
        self.assertGreaterEqual(len(freeze_ids(sha256(data))), 1)
        entry = [e for e in unwrap(data)['scenarios'] if e['id'] == 'ADV-02']
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry[0]['capability'], 'Capability Boundaries')
        self.assertIn(entry[0]['fixture'], (None, {'path': FIXTURE, 'sha256': sha256(read(FIXTURE))}))

    def test_no_other_entry_names_the_folder(self):
        for e in unwrap(read(SET_FILE))['scenarios']:
            if e['id'] != 'ADV-02' and e['fixture']:
                self.assertFalse(e['fixture']['path'].startswith(FIXTURE_DIR + '/'), e['id'])

    def test_only_the_allowed_modules_name_the_folder(self):
        found = naming(FIXTURE_DIR.rsplit('/', 1)[1].encode('ascii'))
        self.assertEqual(not_allowed(found), [])
        self.assertTrue(set(OWN) <= set(found))
        self.assertIn(RUNNER, found)

    def test_a_module_that_is_not_allowed_is_named(self):
        for other in ('src/aieos_bootstrap/governor.py', 'src/aieos_bootstrap/replay.py',
                      'tests/unit/test_not_named_in_the_contract.py', 'tests/unit/test_runner_rc.py',
                      'tests/unit/test_runner_cb.txt', 'tests/conformance/fixtures/acc_01.py',
                      'tests/unit/test_conformance_rc_files.py', 'tests/conformance/set_old.py'):
            self.assertEqual(not_allowed(list(OWN) + [RUNNER, SET_FILE, RISK_ROUTE_TEST, other]), [other])

    def test_the_allowed_modules_are_all_allowed(self):
        self.assertEqual(not_allowed(list(OWN) + [RUNNER, SET_FILE, RISK_ROUTE_TEST, 'tests/unit/test_runner_cb.py',
                                                  'tests/integration/test_runner_cb_run.py',
                                                  'tests/property/test_runner_cb_properties.py',
                                                  'tests/unit/test_runner_cb_more.py'] + list(SET_TESTS)), [])

    def test_no_capability_boundaries_file_in_the_m2_folder(self):
        # Only the M2 folder is named here: the Resume Check and Risk Engine folders may be named only by the modules
        # their tasks' integration tests allow, and this module is not one of them.
        self.assertEqual([p.name for p in (ROOT / 'tests/conformance/fixtures').glob('adv_02*')], [])


if __name__ == '__main__':
    unittest.main()

"""Integration test of the Resume Check fixtures of TASK-005 (docs/specs/conformance-files.md revision 4, sections 2, 3,
7 and 9; docs/tasks/TASK-005.yaml AC6 and AC8): the 11 files end to end against the bound scenario file and the set
file, and what the task leaves unchanged.

Files are read as bytes with pathlib; no fixture or set module is ever imported or executed.
"""
import hashlib
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCENARIO_FILE = 'docs/pre-genesis/conformance-scenarios-initial.md'
SET_FILE = 'tests/conformance/set.py'
SET_FREEZE_RECORDS = 'docs/records/TASK-002.jsonl'
# TASK-014: the set file with the 11 entries is frozen by its own record, given before TASK-014's first commit
# (conformance-files.md section 7, revision 5); TASK-002's freeze of the earlier set file stays.
SET_FREEZE_RECORDS_14 = 'docs/records/TASK-014.jsonl'
EARLIER_SET_SHA256 = '158323324f2803bceee870403bc6c0e297c407fbe50902d60bec90624cc95208'
FIXTURE_DIR = 'tests/conformance/fixtures_rc'
M2_FIXTURE_DIR = 'tests/conformance/fixtures'
FIRST, LAST = b"DATA = r'''", b"'''\n"
# TASK-005's own three test modules (its AC6); each reads the fixtures, so each has to name their folder.
OWN = ('tests/unit/test_conformance_rc_files.py', 'tests/integration/test_conformance_rc_set.py',
       'tests/property/test_conformance_rc_properties.py')
# TASK-010: the other modules that may name the folder, each by name: under src/ only the conformance runner, which
# section 9 of the conformance files document names; under tests/ the three new test modules of TASK-006.
# TASK-014: the set file, whose entries name the folder as data, and the three set-test modules of TASK-002.
OTHERS = ('src/aieos_bootstrap/conformance.py', 'tests/unit/test_runner_rc.py',
          'tests/integration/test_runner_rc_run.py', 'tests/property/test_runner_rc_properties.py',
          'tests/conformance/set.py', 'tests/unit/test_conformance_files.py',
          'tests/property/test_conformance_properties.py', 'tests/integration/test_conformance_set.py')


def read(path):
    return (ROOT / path).read_bytes()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def unwrap(data):
    """The JSON value between the two fixed parts (section 2); the unit module checks the canonical form."""
    if not data.startswith(FIRST) or not data.endswith(LAST):
        raise ValueError('the file does not start with the first part and end with the last part')
    return json.loads(data[len(FIRST):len(data) - len(LAST)].decode('utf-8'))


def rc_rows():
    rows = {}
    for line in read(SCENARIO_FILE).decode('utf-8').split('\n'):
        m = re.match(r'^\| (RC-[0-9]+) \| ', line)
        if m:
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            rows[m.group(1)] = (sha256(line.encode('utf-8')), cells[4])
    return rows


def module_path(sid):
    return FIXTURE_DIR + '/' + sid.lower().replace('-', '_') + '.py'


def not_allowed(paths):
    """The given repository paths that are not allowed to name the folder (OWN and OTHERS, by name), sorted."""
    return sorted(p for p in paths if p not in OWN + OTHERS)


class RcSetTest(unittest.TestCase):

    def test_the_folder_holds_exactly_the_eleven_files(self):
        rows = rc_rows()
        self.assertEqual(len(rows), 11)
        names = sorted(p.name for p in (ROOT / FIXTURE_DIR).iterdir() if p.is_file())
        self.assertEqual(names, sorted(module_path(s).rsplit('/', 1)[1] for s in rows))

    def test_each_file_names_its_bound_row_and_expects_its_cell(self):
        for sid, (row_hash, cell) in rc_rows().items():
            value = unwrap(read(module_path(sid)))
            self.assertEqual((value['scenario'], value['row_hash']), (sid, row_hash), sid)
            self.assertEqual(len(value['cases']), 1, sid)
            self.assertEqual(value['cases'][0]['expected'], {'decision': [cell], 'not_fixed': []}, sid)
            self.assertEqual(value['cases'][0]['when'], 'resume', sid)

    def test_the_set_file_is_unchanged_and_frozen(self):
        """TASK-014 AC4: the set file is bound by exactly one freeze approval of TASK-014, and TASK-002's freeze of
        the earlier set file is still recorded."""
        digest = sha256(read(SET_FILE))
        bound = []
        for line in read(SET_FREEZE_RECORDS_14).decode('utf-8').split('\n'):
            if line:
                rec = json.loads(line)
                if rec.get('fact_kind') == 'authority' and rec.get('approval_binding') == {'kind': 'change_request', 'hash': digest}:
                    bound.append(rec['record_id'])
        self.assertEqual(len(bound), 1, 'the set file is bound by exactly one freeze approval of TASK-014')
        earlier = []
        for line in read(SET_FREEZE_RECORDS).decode('utf-8').split('\n'):
            if line:
                rec = json.loads(line)
                if rec.get('fact_kind') == 'authority' and rec.get('approval_binding') == {'kind': 'change_request', 'hash': EARLIER_SET_SHA256}:
                    earlier.append(rec['record_id'])
        self.assertEqual(earlier, ['TASK-002-freeze-set'])

    def test_the_set_names_no_resume_check_fixture(self):
        value = unwrap(read(SET_FILE))
        rc = [e for e in value['scenarios'] if e['capability'] == 'Resume Check']
        self.assertEqual(sorted(e['id'] for e in rc), sorted(rc_rows()))
        # TASK-014 AC4: each of the 11 entries names exactly its frozen file, and no other entry names that folder
        for e in rc:
            self.assertEqual(e['fixture'], {'path': module_path(e['id']), 'sha256': sha256(read(module_path(e['id'])))}, e['id'])
        self.assertEqual(sorted(e['id'] for e in value['scenarios']
                                if e['fixture'] and e['fixture']['path'].startswith(FIXTURE_DIR + '/')), sorted(rc_rows()))

    def test_no_resume_check_file_in_the_m2_folder(self):
        self.assertEqual([p.name for p in (ROOT / M2_FIXTURE_DIR).iterdir() if p.name.startswith('rc_')], [])

    def test_only_this_task_s_modules_name_the_folder(self):
        name = FIXTURE_DIR.rsplit('/', 1)[1].encode('ascii')
        found = sorted(str(p.relative_to(ROOT)).replace('\\', '/') for d in ('src', 'tests') for p in (ROOT / d).rglob('*.py')
                       if name in p.read_bytes())
        self.assertEqual(not_allowed(found), [])
        self.assertTrue(set(OWN) <= set(found))

    def test_a_module_that_is_not_allowed_is_named(self):
        other_src = 'src/aieos_bootstrap/resume_check.py'
        unnamed_test = 'tests/unit/test_not_named_in_the_contract.py'
        self.assertEqual(not_allowed(list(OWN + OTHERS) + [other_src]), [other_src])
        self.assertEqual(not_allowed(list(OWN + OTHERS) + [unnamed_test]), [unnamed_test])

    def test_the_allowed_modules_are_all_allowed(self):
        self.assertEqual(not_allowed(OWN + OTHERS), [])


if __name__ == '__main__':
    unittest.main()

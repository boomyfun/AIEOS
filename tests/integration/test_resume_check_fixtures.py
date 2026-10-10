"""Integration tests of the Resume Check (TASK-008 AC9 and AC14, rule R8): the conformance runner runs the eleven frozen
Resume Check fixtures with check, the set value built in memory with RC-01 to RC-11 pointing at the frozen files and
every path taken from conformance.expected_path; and the module's import list is read from its syntax tree. Files are
only read, through the runner's own readers; nothing is written.
"""
import ast
import json
import pathlib
import sys
import unittest

from aieos_bootstrap import conformance, records, resume_check

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMMIT = 'a' * 40
TASK = 'TASK-008'
RC_IDS = ['RC-%02d' % n for n in range(1, 12)]
TEST_RECORDS = 'docs/records/TEST-8.jsonl'


def set_with_rc():
    """The repository's set value with RC-01 to RC-11 pointing at the frozen fixtures, as canonical wrapped bytes."""
    value = conformance.unwrap((ROOT / conformance.SET_FILE).read_bytes())
    for entry in value['scenarios']:
        if entry['id'] in RC_IDS:
            path = conformance.expected_path(entry['id'], 'Resume Check')
            entry['fixture'] = {'path': path, 'sha256': conformance.sha256((ROOT / path).read_bytes())}
    return conformance.FIRST + conformance.canonical_text(value) + conformance.LAST


def overlay(set_data):
    rec = {'approval_binding': {'hash': conformance.sha256(set_data), 'kind': 'change_request'}, 'decision_ref': 'D-000',
           'fact_kind': 'authority', 'record_id': 'TEST-freeze-rc8', 'recorder': 'an integration test',
           'source_class': 'decision_agent', 'subject': 'TASK-005'}
    extra = {conformance.SET_FILE: set_data, TEST_RECORDS: (json.dumps(rec, sort_keys=True) + '\n').encode('utf-8')}

    def read(path):
        if path in extra:
            return extra[path]
        p = ROOT / path
        return p.read_bytes() if p.is_file() else None

    def listing():
        return sorted([p.relative_to(ROOT).as_posix() for p in (ROOT / conformance.RECORDS_DIR).glob('*.jsonl')]
                      + [TEST_RECORDS])
    return read, listing


class R8Fixtures(unittest.TestCase):
    def test_the_eleven_frozen_fixtures_pass_with_check(self):
        read, listing = overlay(set_with_rc())
        r = conformance.run(ROOT, COMMIT, TASK, read=read, listing=listing, check=resume_check.check)
        for sid in RC_IDS:
            self.assertEqual((r.results[sid], r.reasons[sid]), (conformance.PASS, ''), sid)

    def test_every_frozen_case_gives_a_record_with_no_finding(self):
        for sid in RC_IDS:
            data = read_fixture(sid)
            for case in data['cases']:
                rec = resume_check.check(case['inputs'])
                self.assertEqual(records.check_decision('decision.execution', rec), [], sid)
                self.assertEqual(rec['decision'], case['expected']['decision'][0], sid)
                for e in rec['state_effect']:
                    self.assertEqual(records.check_payload(e['type'], e['payload']), [], sid)


def read_fixture(sid):
    return conformance.unwrap((ROOT / conformance.expected_path(sid, 'Resume Check')).read_bytes())


class R8Imports(unittest.TestCase):
    def test_the_import_list_holds_the_standard_library_and_records_only(self):
        tree = ast.parse((ROOT / conformance.RESUME_CHECK_PATH).read_text(encoding='utf-8'))
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names += ['%s.%s' % (node.module, a.name) for a in node.names]
        std = set(sys.stdlib_module_names)
        for name in names:
            self.assertTrue(name.split('.')[0] in std or name == 'aieos_bootstrap.records', name)
        self.assertIn('aieos_bootstrap.records', names)
        self.assertFalse(any('conformance' in n for n in names))


if __name__ == '__main__':
    unittest.main()

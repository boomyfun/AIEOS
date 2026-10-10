"""Integration tests of the conformance runner's Resume Check entry (TASK-006 AC8 and AC13, rule R7): runs over the
repository's own tree end to end, with the runner's default byte reader, or with a reader that reads the tree and
replaces only the set file and adds one freeze approval in memory. The frozen Resume Check fixtures under
tests/conformance/fixtures_rc are read only as bytes. Stand-in Resume Checks are test seams (AC4); no file is written.
Each test starts with the governor's and the Resume Check's modules unloaded, and restores sys.modules, sys.meta_path
and the package's attributes after it.
"""
import json
import pathlib
import sys
import unittest

from aieos_bootstrap import conformance

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMMIT = 'a' * 40
TASK = 'TASK-006'
RC_DIR = 'tests/conformance/fixtures_rc'
RC_IDS = ['RC-%02d' % n for n in range(1, 12)]
TEST_RECORDS = 'docs/records/TEST-6.jsonl'
VERIFICATION_IDS = ['ACC-%02d' % n for n in range(1, 18)] + ['ADV-01', 'ADV-03']


class Watching:
    """A meta-path finder that notes every search for the Resume Check and finds nothing itself."""

    def __init__(self):
        self.asked = 0

    def find_spec(self, name, path=None, target=None):
        if name == conformance.RESUME_CHECK_MODULE:
            self.asked += 1
        return None


def overlay(set_data):
    """A reader of the repository's tree with the set file replaced and a freeze approval of it added, and the
    records listing that goes with it."""
    rec = {'approval_binding': {'hash': conformance.sha256(set_data), 'kind': 'change_request'}, 'decision_ref': 'D-000',
           'fact_kind': 'authority', 'record_id': 'TEST-freeze-rc', 'recorder': 'an integration test',
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


def set_with_rc():
    """The repository's set value with RC-01 to RC-11 pointing at the frozen fixtures, as canonical wrapped bytes."""
    value = conformance.unwrap((ROOT / conformance.SET_FILE).read_bytes())
    for entry in value['scenarios']:
        if entry['id'] in RC_IDS:
            path = RC_DIR + '/' + entry['id'].lower().replace('-', '_') + '.py'
            entry['fixture'] = {'path': path, 'sha256': conformance.sha256((ROOT / path).read_bytes())}
    return conformance.FIRST + conformance.canonical_text(value) + conformance.LAST


def stand_in(wrong=None):
    """A stand-in Resume Check answering each frozen case from its own expected decision, except scenario ``wrong``,
    which gets a decision outside its list."""
    by_inputs = {}
    for p in sorted((ROOT / RC_DIR).glob('*.py')):
        value = conformance.unwrap(p.read_bytes())
        for case in value['cases']:
            by_inputs[json.dumps(case['inputs'], sort_keys=True)] = (value['scenario'], case['expected']['decision'][0])

    def check(inputs):
        sid, decision = by_inputs[json.dumps(inputs, sort_keys=True)]
        if sid == wrong:
            decision = 'ESCALATE' if decision != 'ESCALATE' else 'CONTINUE'
        return {'record_id': 'EXE-' + sid, 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_external_ci',
                'recorder': 'a stand-in Resume Check', 'subject': inputs['task_id'], 'decision': decision}
    return check


class Isolated(unittest.TestCase):
    def setUp(self):
        self._modules = dict(sys.modules)
        self._meta = list(sys.meta_path)
        package = sys.modules.get('aieos_bootstrap')
        saved = {n: getattr(package, n) for n in ('governor', 'resume_check') if hasattr(package, n)}
        for n in ('governor', 'resume_check'):
            sys.modules.pop('aieos_bootstrap.' + n, None)
            if hasattr(package, n):
                delattr(package, n)

        def restore():
            sys.meta_path[:] = self._meta
            for name in list(sys.modules):
                if name not in self._modules:
                    del sys.modules[name]
            sys.modules.update(self._modules)
            for n in ('governor', 'resume_check'):
                if hasattr(package, n):
                    delattr(package, n)
            for n, v in saved.items():
                setattr(package, n, v)
        self.addCleanup(restore)


class R7RepositoryTree(Isolated):
    def test_ac8_the_results_over_the_repositorys_tree_are_unchanged(self):
        watching = Watching()
        sys.meta_path.insert(0, watching)
        r = conformance.run(ROOT, COMMIT, TASK)
        self.assertEqual(set(r.value), {'set_file_sha256', 'scenario_set_version', 'fixture_set_version', 'runner',
                                        'governor_identity', 'commit', 'counts', 'results'})
        self.assertTrue(r.value['counts'])
        self.assertEqual(r.problems, [])
        results = r.results
        self.assertEqual(len(results), 32)
        self.assertEqual(sorted(i for i, v in results.items() if v == conformance.PASS), sorted(VERIFICATION_IDS))
        self.assertEqual(sum(v == conformance.NOT_RUN for v in results.values()), 13)
        for sid in RC_IDS:
            self.assertEqual((results[sid], r.reasons[sid]), (conformance.NOT_RUN, 'no fixture'))
        self.assertEqual(r.record['outcome'], 'pass')
        self.assertEqual(watching.asked, 0)
        self.assertNotIn(conformance.RESUME_CHECK_MODULE, sys.modules)
        self.assertFalse((ROOT / conformance.RESUME_CHECK_PATH).exists())

    def test_the_eleven_frozen_fixtures_pass_with_a_stand_in(self):
        read, listing = overlay(set_with_rc())
        r = conformance.run(ROOT, COMMIT, TASK, read=read, listing=listing, check=stand_in())
        for sid in RC_IDS:
            self.assertEqual((r.results[sid], r.reasons[sid]), (conformance.PASS, ''), sid)
        for sid in VERIFICATION_IDS:
            self.assertEqual(r.results[sid], conformance.PASS, sid)
        self.assertFalse(r.value['counts'])
        self.assertEqual(r.problems, ['a stand-in Resume Check (reading)'])
        self.assertEqual(r.value['resume_check'], {'path': conformance.RESUME_CHECK_PATH, 'sha256': None})
        self.assertEqual(r.record['outcome'], 'fail')

    def test_one_decision_outside_its_list_fails_that_scenario(self):
        read, listing = overlay(set_with_rc())
        r = conformance.run(ROOT, COMMIT, TASK, read=read, listing=listing, check=stand_in(wrong='RC-07'))
        self.assertEqual((r.results['RC-07'], r.reasons['RC-07']), (conformance.FAIL, 'not met: case 1: decision'))
        for sid in RC_IDS:
            if sid != 'RC-07':
                self.assertEqual(r.results[sid], conformance.PASS, sid)

    def test_with_no_resume_check_the_eleven_are_not_run(self):
        read, listing = overlay(set_with_rc())
        r = conformance.run(ROOT, COMMIT, TASK, read=read, listing=listing)
        for sid in RC_IDS:
            self.assertEqual((r.results[sid], r.reasons[sid]), (conformance.NOT_RUN, 'the entry point is absent'))
        self.assertTrue(r.value['counts'])
        self.assertEqual(r.value['resume_check'], {'path': conformance.RESUME_CHECK_PATH, 'sha256': None})
        self.assertEqual(r.record['outcome'], 'fail')


if __name__ == '__main__':
    unittest.main()

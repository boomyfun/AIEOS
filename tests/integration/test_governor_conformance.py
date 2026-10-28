"""Integration test of the bootstrap governor of TASK-004 (AC11): the conformance runner over the repository's own
tree, with this governor loaded from that tree by the runner's own import (not as a stand-in). It reads files only
through the runner (pathlib's read_bytes and glob) and writes nothing.
"""
import hashlib
import pathlib
import sys
import unittest

from aieos_bootstrap import conformance
from aieos_bootstrap import governor

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMMIT = 'a' * 40
TASK = 'TASK-004'
VERIFICATION = ['ACC-%02d' % n for n in range(1, 18)] + ['ADV-01', 'ADV-03']


RC_STATE_IDS = ['RC-%02d' % n for n in range(1, 12)]
GOVERNOR_IDS = ['ACC-%02d' % n for n in range(1, 18)] + ['ADV-01', 'ADV-03']


def rc_state(value=None):
    """The state of the set file's Resume Check entries (TASK-013, contract AC1): 'null' when RC-01 to RC-11 all name
    no fixture, 'present' when all eleven name their frozen file with its SHA-256; any other mix fails. Without a value
    it reads the tree's set file."""
    if value is None:
        value = conformance.unwrap((ROOT / conformance.SET_FILE).read_bytes())
    rc = [e for e in value['scenarios'] if e['capability'] == conformance.RESUME_CHECK]
    if [e['id'] for e in rc] != RC_STATE_IDS:
        raise AssertionError('the Resume Check entries are not RC-01 to RC-11')
    if all(e['fixture'] is None for e in rc):
        return 'null'
    if all(e['fixture'] == {'path': conformance.expected_path(e['id'], e['capability']),
                            'sha256': conformance.sha256((ROOT / conformance.expected_path(e['id'], e['capability'])).read_bytes())}
           for e in rc):
        return 'present'
    raise AssertionError('the Resume Check entries are neither all without a fixture nor all with their frozen file')


def resume_check_record():
    """The run record's resume_check in the present state: the Resume Check of the tree, by path and SHA-256."""
    return {'path': conformance.RESUME_CHECK_PATH,
            'sha256': conformance.sha256((ROOT / conformance.RESUME_CHECK_PATH).read_bytes())}


RISK_01_SHA256 = '463c772e4be707b82ebf31b918a2ddf5fc292f21dbeba8d341fe2931e44709af'


def risk_state(value=None):
    """The state of the set file's RISK-01 entry (TASK-019, contract AC1): 'null' when it names no fixture, 'present'
    when it names the file conformance.expected_path gives with the SHA-256 that DM row F69's freeze binds, that file
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


def present_results(governor_result):
    """Every scenario's (result, reason) in the present state, the governor's nineteen given as one pair."""
    out = {sid: governor_result for sid in GOVERNOR_IDS}
    out.update({sid: (conformance.PASS, '') for sid in RC_STATE_IDS})
    out.update({'RISK-01': (conformance.NOT_RUN, 'no fixture'), 'ADV-02': (conformance.NOT_RUN, 'no fixture')})
    return out


class GovernorConformanceTest(unittest.TestCase):
    def setUp(self):
        # The run must load this module from the root: a test elsewhere may have left a fake in sys.modules.
        self._saved = sys.modules.get(conformance.GOVERNOR_MODULE)
        sys.modules[conformance.GOVERNOR_MODULE] = governor
        self.addCleanup(self._restore)

    def _restore(self):
        if self._saved is None:
            sys.modules.pop(conformance.GOVERNOR_MODULE, None)
        else:
            sys.modules[conformance.GOVERNOR_MODULE] = self._saved

    def test_the_module_is_the_roots(self):
        self.assertEqual(pathlib.Path(governor.__file__).resolve(), (ROOT / conformance.GOVERNOR_PATH).resolve())

    def test_the_verification_scenarios_pass_and_the_others_are_not_run(self):
        if cb_state() == 'present':
            self.assertEqual(risk_state(), 'present')
            self.assertEqual(rc_state(), 'present')
            r = conformance.run(ROOT, COMMIT, TASK)
            self.assertEqual(r.problems, [])
            self.assertTrue(r.value['counts'])
            self.assertEqual(r.value['governor_identity'],
                             hashlib.sha256((ROOT / conformance.GOVERNOR_PATH).read_bytes()).hexdigest())
            self.assertEqual(len(r.results), 32)
            want = present_results((conformance.PASS, ''))
            want['RISK-01'] = (conformance.PASS, '')
            want['ADV-02'] = (conformance.PASS, '')
            self.assertEqual({s: (v, r.reasons[s]) for s, v in r.results.items()}, want)
            self.assertEqual(r.value['resume_check'], resume_check_record())
            self.assertEqual(r.value['capability_boundaries'], cb_record())
            self.assertEqual(r.record['outcome'], 'pass')
            return
        if risk_state() == 'present':
            self.assertEqual(rc_state(), 'present')
            r = conformance.run(ROOT, COMMIT, TASK)
            self.assertEqual(r.problems, [])
            self.assertTrue(r.value['counts'])
            self.assertEqual(r.value['governor_identity'],
                             hashlib.sha256((ROOT / conformance.GOVERNOR_PATH).read_bytes()).hexdigest())
            self.assertEqual(len(r.results), 32)
            want = present_results((conformance.PASS, ''))
            want['RISK-01'] = (conformance.PASS, '')
            self.assertEqual({s: (v, r.reasons[s]) for s, v in r.results.items()}, want)
            self.assertEqual(r.value['resume_check'], resume_check_record())
            self.assertEqual(r.record['outcome'], 'pass')
            return
        if rc_state() == 'present':
            r = conformance.run(ROOT, COMMIT, TASK)
            self.assertEqual(r.problems, [])
            self.assertTrue(r.value['counts'])
            self.assertEqual(r.value['governor_identity'],
                             hashlib.sha256((ROOT / conformance.GOVERNOR_PATH).read_bytes()).hexdigest())
            self.assertEqual(len(r.results), 32)
            self.assertEqual({s: (v, r.reasons[s]) for s, v in r.results.items()}, present_results((conformance.PASS, '')))
            self.assertEqual(r.value['resume_check'], resume_check_record())
            self.assertEqual(r.record['outcome'], 'pass')
            return
        r = conformance.run(ROOT, COMMIT, TASK)
        self.assertEqual(r.problems, [])
        self.assertTrue(r.value['counts'])
        self.assertEqual(r.value['governor_identity'],
                         hashlib.sha256((ROOT / conformance.GOVERNOR_PATH).read_bytes()).hexdigest())
        results = r.results
        self.assertEqual(len(results), 32)
        self.assertEqual(sorted(i for i, v in results.items() if v == conformance.PASS), sorted(VERIFICATION))
        self.assertEqual(list(results.values()).count(conformance.NOT_RUN), 13)
        self.assertNotIn(conformance.FAIL, results.values())
        self.assertEqual(r.record['outcome'], 'pass')

    def test_each_case_directly(self):
        n = 0
        for p in sorted((ROOT / conformance.FIXTURE_DIR).glob('*.py')):
            value = conformance.unwrap(p.read_bytes())
            for case in value['cases']:
                out = governor.evaluate(case['request'], case['inputs'], case['records'])
                self.assertEqual(conformance.decision_problem(out), '', value['scenario'])
                self.assertEqual(conformance.compare(case['expected'], out, case['records']), [], value['scenario'])
                n += 1
        self.assertEqual(n, 21)


if __name__ == '__main__':
    unittest.main()

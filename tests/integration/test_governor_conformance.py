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

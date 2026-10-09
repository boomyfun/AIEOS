"""Integration test of the conformance runner of TASK-003 (AC12): runs over the repository's own tree end to end,
with the runner's default byte reader and records listing. Stand-in governors are test seams (AC6); no file is
written.
Each test starts with the governor absent, whether or not a governor file exists (TASK-004 AC14).
"""
import collections
import json
import pathlib
import sys
import unittest

from aieos_bootstrap import conformance

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMMIT = 'a' * 40
TASK = 'TASK-003'


def cases_by_request():
    """Each case of the repository's fixtures, by its request, with its scenario id and number."""
    out = {}
    for p in sorted((ROOT / conformance.FIXTURE_DIR).glob('*.py')):
        value = conformance.unwrap(p.read_bytes())
        for n, case in enumerate(value['cases'], 1):
            out[json.dumps(case['request'], sort_keys=True)] = (value['scenario'], n, case)
    return out


def answer(request, expected):
    """A decision record that meets every fixed key of ``expected``."""
    nf = set(expected['not_fixed'])
    by_dim = collections.defaultdict(list)
    for m in ([] if 'missing' in nf else expected['missing']):
        by_dim[m['dimension']].append(m['evidence_type'])
    approval = None if 'approval' in nf or expected['approval'] is None else expected['approval']['record_id']
    return {
        'record_id': 'DEC-' + request['task_id'], 'fact_kind': 'interpretation',
        'source_class': 'deterministic_tool_external_ci', 'recorder': 'a stand-in governor',
        'subject': request['task_id'],
        'decision': 'NEEDS_REVIEW' if 'decision' in nf else expected['decision'][0],
        'next_task_state': 'IN_REVIEW' if 'next_state' in nf else expected['next_state'][0],
        'profile_used': [{'dimension': d, 'required': t, 'satisfied_by': [], 'missing_types': t} for d, t in by_dim.items()],
        'reverify': [] if 'reverify' in nf else list(expected['reverify']),
        'approval_record': approval,
        'rests_on_ai': {'entries': [], 'approval': False if 'ai_approval_shown' in nf else expected['ai_approval_shown']},
    }


class Absent:
    """A meta-path finder that makes the governor absent, as when no governor file exists (TASK-004 AC14)."""

    def find_spec(self, name, path=None, target=None):
        if name == conformance.GOVERNOR_MODULE:
            raise ModuleNotFoundError('No module named %r' % name, name=name)
        return None


def isolate_governor(test):
    """Removes any loaded governor from sys.modules and from the package's attributes and puts Absent first on
    sys.meta_path, so that the test sees the governor absent (TASK-004 AC14). sys.modules, sys.meta_path and the
    package's attribute are restored after the test."""
    modules, meta = dict(sys.modules), list(sys.meta_path)
    package = sys.modules.get('aieos_bootstrap')
    saved = getattr(package, 'governor', None) if package is not None else None
    sys.modules.pop(conformance.GOVERNOR_MODULE, None)
    if package is not None and hasattr(package, 'governor'):
        delattr(package, 'governor')
    sys.meta_path.insert(0, Absent())

    def restore():
        sys.meta_path[:] = meta
        for name in list(sys.modules):
            if name not in modules:
                del sys.modules[name]
        sys.modules.update(modules)
        if package is None:
            return
        if saved is not None:
            package.governor = saved
        elif hasattr(package, 'governor'):
            delattr(package, 'governor')
    test.addCleanup(restore)


class RunnerEndToEndTest(unittest.TestCase):
    def setUp(self):
        isolate_governor(self)
        self.cases = cases_by_request()
        self.set_value = conformance.unwrap((ROOT / conformance.SET_FILE).read_bytes())
        self.with_fixture = [e['id'] for e in self.set_value['scenarios'] if e['fixture'] is not None]

    def test_no_governor(self):
        r = conformance.run(ROOT, COMMIT, TASK)
        self.assertTrue(r.value['counts'])
        self.assertEqual(r.problems, [])
        self.assertEqual(len(r.value['results']), 32)
        self.assertEqual(set(r.results.values()), {conformance.NOT_RUN})
        self.assertEqual(r.record['outcome'], 'fail')
        self.assertIsNone(r.value['governor_identity'])
        self.assertEqual([x['id'] for x in r.value['results']], [e['id'] for e in self.set_value['scenarios']])
        self.assertEqual(len(self.with_fixture), 19)
        for sid in self.with_fixture:
            self.assertEqual(r.reasons[sid], 'the entry point is absent')

    def test_a_stand_in_that_answers_from_the_expected_values(self):
        def evaluate(request, inputs, case_records):
            sid, n, case = self.cases[json.dumps(request, sort_keys=True)]
            return answer(request, case['expected'])
        r = conformance.run(ROOT, COMMIT, TASK, evaluate=evaluate)
        self.assertFalse(r.value['counts'])
        self.assertEqual(r.problems, ['a stand-in governor (reading)'])
        self.assertEqual(sorted(s for s, v in r.results.items() if v == conformance.PASS), sorted(self.with_fixture))
        self.assertEqual(list(r.results.values()).count(conformance.NOT_RUN), 13)
        self.assertEqual(r.record['outcome'], 'fail')

    def test_a_stand_in_with_one_decision_outside_a_list(self):
        def evaluate(request, inputs, case_records):
            sid, n, case = self.cases[json.dumps(request, sort_keys=True)]
            out = answer(request, case['expected'])
            if sid == 'ACC-01':
                out['decision'] = next(d for d in ('ACCEPT', 'REJECT', 'NEEDS_REWORK')
                                       if d not in case['expected']['decision'])
            return out
        r = conformance.run(ROOT, COMMIT, TASK, evaluate=evaluate)
        self.assertEqual(r.results['ACC-01'], conformance.FAIL)
        self.assertEqual(list(r.results.values()).count(conformance.PASS), 18)


if __name__ == '__main__':
    unittest.main()

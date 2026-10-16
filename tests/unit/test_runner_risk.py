"""Unit tests of the conformance runner's Risk Engine entry (TASK-017, rules R1 to R9 of its AC16).

Every input is built in memory from the repository's own files and given to the runner through its byte reader and
records listing; no file is written. Stand-in derivations and acceptance functions are test seams (AC3).
"""
import copy
import json
import pathlib
import sys
import types
import unittest
from unittest import mock

from aieos_bootstrap import conformance

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMMIT = 'a' * 40
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


def error_record(request):
    """An acceptance record with no decision value and an error, as GS section 4 rule 8 gives."""
    return {'record_id': 'DEC-1', 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_external_ci',
            'recorder': 'a stand-in governor', 'subject': request['task_id'], 'decision': None,
            'error': 'risk', 'profile_used': []}


def derive_none(v):
    return {'risk': None, 'evidence_profile': None}


def evaluate_error(request, inputs, recs):
    return error_record(request)


def go(files, derive=derive_none, evaluate=evaluate_error, asked=None):
    def read(path):
        if asked is not None:
            asked.append(path)
        return files.get(path)

    def listing():
        return sorted(p for p in files if p.startswith(conformance.RECORDS_DIR + '/') and p.endswith('.jsonl'))
    return conformance.run(ROOT, COMMIT, TASK, read=read, listing=listing, evaluate=evaluate, derive=derive)


class Base(unittest.TestCase):
    def result(self, files, **kw):
        r = go(files, **kw)
        return r.results['RISK-01'], r.reasons['RISK-01'], r


class R1Route(Base):
    def test_the_expected_path(self):
        self.assertEqual(conformance.expected_path('RISK-01', 'Risk Engine'), RISK_PATH)
        self.assertEqual(conformance.expected_path('ADV-02', 'Capability Boundaries'), 'tests/conformance/fixtures_cb/adv_02.py')

    def test_a_risk_fixture_elsewhere(self):
        files = real_files()
        put_fixture(files, fixture(files), path=conformance.module_path('RISK-01'))
        asked = []
        result, reason, _ = self.result(files, asked=asked)
        self.assertEqual((result, reason), (conformance.NOT_RUN, 'the fixture path is not ' + RISK_PATH))
        self.assertNotIn(conformance.module_path('RISK-01'), asked)

    def test_capability_boundaries_still_absent(self):
        files = real_files()
        put_fixture(files, fixture(files))
        r = go(files)
        self.assertEqual(r.results['ADV-02'], conformance.NOT_RUN)
        self.assertEqual(r.results['RISK-01'], conformance.PASS)


class R2EntryPoint(Base):
    def test_a_stand_in_never_counts(self):
        files = real_files()
        put_fixture(files, fixture(files))
        result, _, r = self.result(files)
        self.assertEqual(result, conformance.PASS)
        self.assertFalse(r.value['counts'])
        self.assertIn('a stand-in derivation (reading)', r.problems)

    def test_no_derivation(self):
        files = real_files()
        put_fixture(files, fixture(files))
        self.assertEqual(self.result(files, derive=None, evaluate=evaluate_error)[:2][0], conformance.NOT_RUN)

    def test_load_derive_from_elsewhere(self):
        self.assertIsNone(conformance.load_derive(pathlib.Path('/nowhere')))

    def stub(self, module):
        """The governor module seen by load_derive's plain import replaced in memory (None: the import fails)."""
        import aieos_bootstrap
        patches = [mock.patch.dict(sys.modules, {'aieos_bootstrap.governor': module})]
        if module is not None:
            patches.append(mock.patch.object(aieos_bootstrap, 'governor', module, create=True))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def module(self, path=None, **attrs):
        m = types.ModuleType('aieos_bootstrap.governor')
        m.__file__ = str(path or ROOT / conformance.GOVERNOR_PATH)
        for k, v in attrs.items():
            setattr(m, k, v)
        return m

    def test_load_derive_branches(self):
        # AC3: absent or failed, a module that is not the root's, no callable derive_inputs: None; else the function.
        self.stub(None)
        self.assertIsNone(conformance.load_derive(ROOT))

    def test_load_derive_no_callable_derive_inputs(self):
        self.stub(self.module())
        self.assertIsNone(conformance.load_derive(ROOT))

    def test_load_derive_not_callable(self):
        self.stub(self.module(derive_inputs=5))
        self.assertIsNone(conformance.load_derive(ROOT))

    def test_load_derive_another_file(self):
        self.stub(self.module(path=ROOT / 'src/elsewhere/governor.py', derive_inputs=derive_none))
        self.assertIsNone(conformance.load_derive(ROOT))

    def test_load_derive_the_roots_function(self):
        self.stub(self.module(derive_inputs=derive_none))
        self.assertIs(conformance.load_derive(ROOT), derive_none)


MALFORMED = 'the fixture is malformed: '


class R3Form(Base):
    def bad(self, change, why):
        files = real_files()
        value = fixture(files)
        change(value)
        put_fixture(files, value)
        result, reason, _ = self.result(files)
        self.assertEqual((result, reason), (conformance.NOT_RUN, MALFORMED + why))

    def test_each_malformed_condition(self):
        rules = 'case 1: risk_rules is not a list of {match, class} with well-formed patterns and a risk class'
        pairs = 'case 1: profile_excludes is not exactly the two pairs of the low default'
        nf = 'case 1: not_fixed is not exactly decision and next_state'
        changes = [
            (lambda v: v.update(extra=1), 'the fixture is not exactly scenario, row_hash and cases'),
            (lambda v: v.update(row_hash='0' * 64), 'scenario or row_hash differs from the set entry'),
            (lambda v: v.update(cases=[]), 'cases is not a non-empty list'),
            (lambda v: v['cases'][0].pop('when'), 'case 1: not exactly values, request, records, when and expected'),
            (lambda v: v['cases'][0]['values'].pop('delegation'), 'case 1: values is not exactly the keys of section 10'),
            (lambda v: v['cases'][0]['values'].update(requirement_profiles=[{'id': 'x', 'add': []}]),
             'case 1: requirement_profiles is not the empty list'),
            (lambda v: v['cases'][0]['values']['risk_rules'][0].update({'class': 'none'}), rules),
            (lambda v: v['cases'][0]['values']['risk_rules'][0].update(match=[]), rules),
            (lambda v: v['cases'][0]['values']['articles'][0].update(scope=[]),
             'case 1: articles is not a list of {id, scope, evidence_required} with well-formed scopes'),
            (lambda v: v['cases'][0]['values']['articles'][0].update(extra=1),
             'case 1: articles is not a list of {id, scope, evidence_required} with well-formed scopes'),
            (lambda v: v['cases'][0]['values'].update(changed_paths=[]),
             'case 1: changed_paths is not a non-empty list of well-formed paths'),
            (lambda v: v['cases'][0]['request'].update(changed_paths=['other.txt']),
             'case 1: request changed_paths differs from values changed_paths'),
            (lambda v: v['cases'][0]['request'].update(task_state='IN_REVIEW'),
             'case 1: when is not evaluate with task_state VERIFYING'),
            (lambda v: v['cases'][0].update(when='re_evaluate'), 'case 1: when is not evaluate with task_state VERIFYING'),
            (lambda v: v['cases'][0].update(records='none'), 'case 1: records is not a list'),
            (lambda v: v['cases'][0]['records'][0].update(record_id=['x']), 'case 1: a record with a check_record finding'),
            (lambda v: v['cases'][0]['expected'].update(risk_not=['low', 'medium']), 'case 1: risk_not is not ["low"]'),
            (lambda v: v['cases'][0]['expected']['profile_excludes'].pop(), pairs),
            (lambda v: v['cases'][0]['expected']['profile_excludes'][0].update(dimension=['functional']), pairs),
            (lambda v: v['cases'][0]['expected']['profile_excludes'][1].update(evidence_type={'t': 'lint'}), pairs),
            (lambda v: v['cases'][0]['expected'].update(not_fixed=['decision']), nf),
            (lambda v: v['cases'][0]['expected'].update(not_fixed=[['decision'], ['next_state']]), nf),
            (lambda v: v['cases'][0]['expected'].update(decision=['REJECT']),
             'case 1: expected is not exactly risk_not, profile_excludes and not_fixed'),
        ]
        for change, why in changes:
            self.bad(change, why)

    def test_reordered_lists_are_well_formed(self):
        files = real_files()
        value = fixture(files)
        value['cases'][0]['expected']['profile_excludes'].reverse()
        value['cases'][0]['expected']['not_fixed'].reverse()
        put_fixture(files, value)
        self.assertEqual(self.result(files)[:2], (conformance.PASS, ''))


class R4Matcher(Base):
    def test_point_6_forms(self):
        m = conformance.path_matches
        self.assertTrue(m('src/*.py', 'src/a.py'))
        self.assertFalse(m('src/*.py', 'src/x/a.py'))
        self.assertTrue(m('src/**', 'src/x/y/a.py'))
        self.assertTrue(m('**/contracts/**', 'a/contracts/b.py'))
        self.assertTrue(m('*.md', 'docs/x/readme.md'))
        self.assertFalse(m('*.md', 'docs/readme.MD'))
        self.assertFalse(m('docs/**', 'src/docs/a.md'))
        self.assertTrue(m('a*b', 'x/aXYb'))
        self.assertFalse(m('a*b', 'a/b'))
        self.assertTrue(m('src/**/x.py', 'src/x.py'))
        self.assertTrue(m('src/**/x.py', 'src/a/b/x.py'))
        self.assertFalse(m('Src/**', 'src/a.py'))
        self.assertFalse(m('a/**', 'a'))

    def test_well_formed(self):
        for p in ('src/**', '*.md', 'a-b_c.d/*', '**', '.github/*', 'a..b'):
            self.assertTrue(conformance.pattern_ok(p), p)
        for p in ('', '/src', 'src/', 'a//b', 'a?b', 'a[b]', '{a}', '!a', 'a\\b', 'a**b', 'x/***', 5, '.', '..',
                  'a/./b', 'a/../b', '../*'):
            self.assertFalse(conformance.pattern_ok(p), p)
        for p in ('a/b.txt', '.gitignore', 'a/.b/c', 'a..b/c'):
            self.assertTrue(conformance.path_ok(p), p)
        for p in ('a/*.txt', '/a', 'a/', 'a b', '', '.', '..', 'x/../src/a.py', './a', 'a/.'):
            self.assertFalse(conformance.path_ok(p), p)

    def test_the_given(self):
        rules = 'case 1: risk_rules is not a list of {match, class} with well-formed patterns and a risk class'
        paths = 'case 1: changed_paths is not a non-empty list of well-formed paths'
        for change, why in (
                (lambda v: v['cases'][0]['values']['risk_rules'][0].update(match=['unmatched/**']),
                 'case 1: the Given does not hold: a changed path matches a risk rule'),
                (lambda v: v['cases'][0]['values']['articles'][0].update(scope=['*.txt']),
                 "case 1: an article's scope matches a changed path"),
                (lambda v: v['cases'][0]['values']['risk_rules'][0].update(match=['a?b']), rules),
                (lambda v: v['cases'][0]['values']['risk_rules'][0].update(match=['../src/**']), rules),
                (lambda v: v['cases'][0]['values'].update(changed_paths=['bad path']), paths),
                (lambda v: v['cases'][0]['values'].update(changed_paths=['x/../src/a.py']), paths)):
            files = real_files()
            value = fixture(files)
            change(value)
            put_fixture(files, value)
            self.assertEqual(self.result(files)[:2], (conformance.NOT_RUN, MALFORMED + why))


class R5Derivation(Base):
    def test_a_raise_is_not_run_with_its_reason(self):
        files = real_files()
        put_fixture(files, fixture(files))

        def boom(v):
            raise ValueError('no')
        result, reason, _ = self.result(files, derive=boom)
        self.assertEqual(result, conformance.NOT_RUN)
        self.assertIn('the derivation raised ValueError', reason)

    def test_fail_before_not_run(self):
        files = real_files()
        put_fixture(files, fixture(files, [risk_case(files), risk_case(files)]))
        calls = []

        def derive(v):
            calls.append(1)
            if len(calls) == 1:
                raise ValueError('no')
            return {'risk': 'low', 'evidence_profile': None}
        result, _, _ = self.result(files, derive=derive)
        self.assertEqual(result, conformance.FAIL)
        self.assertEqual(len(calls), 2)


class R6Derived(Base):
    def check(self, derived, want=conformance.FAIL):
        files = real_files()
        put_fixture(files, fixture(files))
        called = []

        def evaluate(req, inp, recs):
            # The seam answers every scenario's calls; only RISK-01's request names the unmatched path.
            if req['changed_paths'] == ['unmatched/file.txt']:
                called.append(1)
            return error_record(req)
        result, _, _ = self.result(files, derive=lambda v: derived, evaluate=evaluate)
        self.assertEqual(result, want, derived)
        if want == conformance.FAIL:
            self.assertEqual(called, [])

    def test_each_failure(self):
        self.check({'risk': 'low', 'evidence_profile': None})
        self.check({'risk': None, 'evidence_profile': copy.deepcopy(LOW)})
        self.check({'risk': 'medium', 'evidence_profile': [{'dimension': 'functional', 'evidence_types': ['lint']}]})
        self.check({'risk': 'bogus', 'evidence_profile': None})
        self.check({'risk': None, 'evidence_profile': 'low'})
        self.check({'risk': None})
        self.check(['low'])
        self.check({'risk': 'high', 'evidence_profile': [{'dimension': 'functional', 'evidence_types': ['unit_test', 5]}]})
        self.check({'risk': ['low'], 'evidence_profile': None})

    def test_a_good_derivation_passes(self):
        self.check({'risk': 'high', 'evidence_profile': [{'dimension': 'functional', 'evidence_types': ['unit_test']}]},
                   conformance.PASS)
        # A low pair's type in another dimension is not the pair.
        self.check({'risk': 'high', 'evidence_profile': [{'dimension': 'security', 'evidence_types': ['build', 'lint']}]},
                   conformance.PASS)


class R7Acceptance(Base):
    def run_with(self, evaluate):
        files = real_files()
        put_fixture(files, fixture(files))
        return self.result(files, evaluate=evaluate)[:2]

    def test_the_error_record_passes(self):
        self.assertEqual(self.run_with(evaluate_error), (conformance.PASS, ''))

    def test_a_low_pair_in_profile_used_fails(self):
        def evaluate(req, inp, recs):
            rec = error_record(req)
            rec['profile_used'] = [{'dimension': 'functional', 'required': ['build'], 'satisfied_by': [],
                                    'missing_types': []}]
            return rec
        self.assertEqual(self.run_with(evaluate)[0], conformance.FAIL)

    def test_no_profile_used_list_is_not_run(self):
        def evaluate(req, inp, recs):
            rec = error_record(req)
            del rec['profile_used']
            return rec
        self.assertEqual(self.run_with(evaluate)[0], conformance.NOT_RUN)

    def item(self, **kw):
        it = {'dimension': 'functional', 'required': ['unit_test'], 'satisfied_by': [], 'missing_types': []}
        it.update(kw)
        return it

    def test_profile_used_items_of_another_form_are_not_run(self):
        # AC8 with spec 2 section 6.4's form: a low pair given in any other form never counts as not held.
        for bad in (self.item(required='build'), self.item(required=['build', ['lint']]),
                    self.item(dimension=['functional']), self.item(dimension=''), self.item(required=None)):
            def evaluate(req, inp, recs, bad=bad):
                rec = error_record(req)
                rec['profile_used'] = [bad]
                return rec
            self.assertEqual(self.run_with(evaluate), (conformance.NOT_RUN, 'case 1: ' + conformance.PROFILE_USED_PROBLEM),
                             bad)

    def test_profile_used_items_of_the_form_pass(self):
        def evaluate(req, inp, recs):
            rec = error_record(req)
            rec['profile_used'] = [self.item(), self.item(dimension='security', required=['build', 'lint'])]
            return rec
        self.assertEqual(self.run_with(evaluate), (conformance.PASS, ''))

    def test_fail_wins_over_a_profile_used_of_another_form(self):
        files = real_files()
        put_fixture(files, fixture(files, [risk_case(files), risk_case(files)]))
        calls = []

        def evaluate(req, inp, recs):
            rec = error_record(req)
            if req['changed_paths'] == ['unmatched/file.txt']:
                calls.append(1)
                rec['profile_used'] = ([self.item(required='build')] if len(calls) == 1
                                       else [self.item(required=['lint'])])
            return rec
        self.assertEqual(self.result(files, evaluate=evaluate)[:2],
                         (conformance.FAIL, 'not met: case 2: profile_used holds a pair of the low default'))
        self.assertEqual(len(calls), 2)

    def test_a_raise_is_not_run(self):
        def evaluate(req, inp, recs):
            raise RuntimeError('x')
        self.assertEqual(self.run_with(evaluate)[0], conformance.NOT_RUN)


class R8Order(Base):
    def test_every_case_runs(self):
        files = real_files()
        put_fixture(files, fixture(files, [risk_case(files) for _ in range(3)]))
        calls = []

        def derive(v):
            calls.append(1)
            if len(calls) == 2:
                raise ValueError('no')
            return {'risk': None, 'evidence_profile': None}
        self.assertEqual(self.result(files, derive=derive)[0], conformance.NOT_RUN)
        self.assertEqual(len(calls), 3)


class R9Outcome(Base):
    def test_outcome_with_a_risk_scenario(self):
        files = real_files()
        put_fixture(files, fixture(files))
        r = go(files)
        self.assertIn('RISK-01', [i for i in r.results if r.results[i] == conformance.PASS])
        self.assertEqual(set(r.value), {'set_file_sha256', 'scenario_set_version', 'fixture_set_version', 'runner',
                                        'governor_identity', 'commit', 'counts', 'results', 'resume_check'})
        self.assertEqual(r.record['outcome'], 'fail')     # a stand-in never counts
        by_id = {i: conformance.PASS for i in r.results}
        self.assertEqual(conformance.outcome(True, by_id, ['RISK-01']), 'pass')
        by_id['RISK-01'] = conformance.NOT_RUN
        self.assertEqual(conformance.outcome(True, by_id, ['RISK-01']), 'fail')
        by_id['RISK-01'] = conformance.FAIL
        self.assertEqual(conformance.outcome(True, by_id, ['RISK-01']), 'fail')


if __name__ == '__main__':
    unittest.main()

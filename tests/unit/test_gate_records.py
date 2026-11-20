"""Unit tests of the gate maker of TASK-150 (BT2 of DEF-0136, AC1 to AC5). Every case is built in memory; the only files
read are the module's own source and the CI workflow, with pathlib's read_bytes.
"""
import ast
import copy
import hashlib
import pathlib
import unittest

from aieos_bootstrap import gate_records
from aieos_bootstrap import governor
from aieos_bootstrap import records

ROOT = pathlib.Path(__file__).resolve().parents[2]
TASK = 'TASK-500'
COMMIT = 'a' * 40
IV = {'SPEC-001': 'v2'}
CI = 'deterministic_tool_external_ci'
MAP = gate_records.DEFAULT_CHECK_MAP
SCOPE_STEPS = MAP['scope']
BUILD_STEP = MAP['build'][0]
LINT_STEP = MAP['lint'][0]
PLAN4 = [{'gate': 'G0', 'check': 'scope'}, {'gate': 'G1', 'check': 'build'}, {'gate': 'G2', 'check': 'lint'},
         {'gate': 'G3', 'check': 'review'}]


class Boom(BaseException):
    """A BaseException that is not an Exception (AC1)."""


def step(name, conclusion='success'):
    return {'name': name, 'conclusion': conclusion}


def all_steps(conclusion='success'):
    return [step(n, conclusion) for n in SCOPE_STEPS + [BUILD_STEP, LINT_STEP]]


DEFAULT = object()  # "not given", so that None can be passed as an argument


def make(plan=DEFAULT, steps=DEFAULT, check_map=DEFAULT, task=TASK, commit=COMMIT, iv=DEFAULT, recorder='external CI'):
    return gate_records.gate_records(
        task, commit, dict(IV) if iv is DEFAULT else iv, copy.deepcopy(PLAN4) if plan is DEFAULT else plan,
        all_steps() if steps is DEFAULT else steps, copy.deepcopy(MAP) if check_map is DEFAULT else check_map, recorder)


def by_gate(out):
    return {r['gate']: r['outcome'] for r in out['records']}


def imports_and_names(source):
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.update(node.module + '.' + a.name for a in node.names)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    return calls, imports, names


class AC1TheModule(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / 'src/aieos_bootstrap/gate_records.py').read_bytes().decode('utf-8')

    def test_public_names_are_exactly_two(self):
        tree = ast.parse(self.source)
        public = set()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith('_'):
                public.add(node.name)
            elif isinstance(node, ast.Assign):
                public.update(t.id for t in node.targets if isinstance(t, ast.Name) and not t.id.startswith('_'))
        self.assertEqual(public, {'gate_records', 'DEFAULT_CHECK_MAP'})

    def test_imports_only_hashlib_and_re_and_no_forbidden_name(self):
        calls, imports, names = imports_and_names(self.source)
        self.assertEqual(imports, {'hashlib', 're'})
        # re.compile is an attribute call of the allowed module re; the builtin compile is a direct call.
        self.assertFalse(calls & {'open', 'exec', 'eval', 'compile', '__import__'})
        for bad in ('open', 'exec', 'eval', '__import__', 'subprocess', 'system', 'environ', 'time', 'now'):
            self.assertNotIn(bad, names)

    def test_the_source_check_finds_a_breach(self):
        calls, imports, names = imports_and_names(
            'import os\nfrom subprocess import run\nopen("x")\ncompile("1", "f", "eval")\nos.environ\n')
        self.assertEqual(imports, {'os', 'subprocess.run'})
        self.assertEqual(calls & {'open', 'compile'}, {'open', 'compile'})
        self.assertTrue({'open', 'environ'} <= names)

    def test_the_return_form_has_exactly_three_keys(self):
        for out in (make(), make(task='x')):
            self.assertEqual(set(out), {'records', 'uncovered', 'error'})

    def test_every_argument_check(self):
        bad = [
            ('task_id', dict(task='TASK-')), ('task_id', dict(task='task-1')), ('task_id', dict(task='TASK-1\n')),
            ('task_id', dict(task=5)),
            ('commit', dict(commit='a' * 39)), ('commit', dict(commit='A' * 40)), ('commit', dict(commit='a' * 40 + '\n')),
            ('commit', dict(commit=None)),
            ('iv', dict(iv={})), ('iv', dict(iv=[('a', 'v1')])), ('iv', dict(iv={'': 'v1'})), ('iv', dict(iv={'a': 'v'})),
            ('iv', dict(iv={'a': 'v1x'})), ('iv', dict(iv={'a': 1})), ('iv', dict(iv={1: 'v1'})),
            ('plan', dict(plan=[])), ('plan', dict(plan='G0')), ('plan', dict(plan=['G0'])),
            ('plan', dict(plan=[{'gate': 'G0'}])),
            ('plan', dict(plan=[{'gate': 'G0', 'check': 'scope', 'args': []}])),
            ('plan', dict(plan=[{'gate': 'g0', 'check': 'scope'}])),
            ('plan', dict(plan=[{'gate': 'G', 'check': 'scope'}])),
            ('plan', dict(plan=[{'gate': 'G0', 'check': ''}])), ('plan', dict(plan=[{'gate': 'G0', 'check': 3}])),
            ('steps', dict(steps=None)), ('steps', dict(steps=['x'])), ('steps', dict(steps=[{'name': 'a'}])),
            ('steps', dict(steps=[{'name': '', 'conclusion': 'success'}])),
            ('steps', dict(steps=[{'name': 'a', 'conclusion': 1}])),
            ('steps', dict(steps=[{'name': 'a', 'conclusion': True}])),
            ('steps', dict(steps=[{'name': 'a', 'conclusion': 'success', 'x': 1}])),
            ('check_map', dict(check_map=None)), ('check_map', dict(check_map={'scope': []})),
            ('check_map', dict(check_map={'scope': 'G1 build'})), ('check_map', dict(check_map={'scope': ['']})),
            ('check_map', dict(check_map={'': ['a']})), ('check_map', dict(check_map={'scope': [3]})),
            ('recorder', dict(recorder='')), ('recorder', dict(recorder=None)),
        ]
        for label, kw in bad:
            out = make(**kw)
            self.assertIsInstance(out['error'], str, (label, kw))
            self.assertNotEqual(out['error'], '', (label, kw))
            self.assertEqual((out['records'], out['uncovered']), ([], []), (label, kw))

    def test_good_arguments_have_no_error_and_an_empty_steps_list_is_allowed(self):
        self.assertIsNone(make()['error'])
        out = make(steps=[])
        self.assertIsNone(out['error'])
        self.assertEqual(out['records'], [])
        self.assertEqual(len(out['uncovered']), 4)

    def test_no_exception_escapes(self):
        class Bad(dict):
            def items(self):
                raise RuntimeError('own method')

        out = make(iv=Bad(IV))
        self.assertIsInstance(out['error'], str)
        self.assertEqual((out['records'], out['uncovered']), ([], []))

    def test_a_base_exception_passes_through(self):
        class Worse(dict):
            def items(self):
                raise Boom()

        with self.assertRaises(Boom):
            make(iv=Worse(IV))


class AC2MatchingByCheck(unittest.TestCase):
    def test_review_gets_no_record_even_when_every_constitution_step_is_success(self):
        steps = all_steps() + [step('constitution ' + n) for n in ('a', 'b', 'c')]
        out = make(steps=steps)
        self.assertEqual(by_gate(out), {'G0': 'pass', 'G1': 'pass', 'G2': 'pass'})
        self.assertEqual(out['uncovered'], [{'gate': 'G3', 'check': 'review', 'detail': 'no CI step is evidence of this check'}])

    def test_steps_keyed_under_a_named_check_give_a_record_only_for_that_checks_gate(self):
        cm = copy.deepcopy(MAP)
        cm['review'] = ['G1 build']
        out = make(check_map=cm)
        self.assertEqual(by_gate(out), {'G0': 'pass', 'G1': 'pass', 'G2': 'pass', 'G3': 'pass'})
        out = make(plan=[{'gate': 'G3', 'check': 'review'}], check_map=cm)
        self.assertEqual(by_gate(out), {'G3': 'pass'})
        out = make(plan=[{'gate': 'G3', 'check': 'review'}])
        self.assertEqual(by_gate(out), {})

    def test_two_entries_one_covered_passed_one_uncovered_give_no_record(self):
        out = make(plan=[{'gate': 'G0', 'check': 'scope'}, {'gate': 'G0', 'check': 'review'}])
        self.assertEqual(out['records'], [])
        self.assertEqual(out['uncovered'], [{'gate': 'G0', 'check': 'review', 'detail': 'no CI step is evidence of this check'}])

    def test_two_entries_one_covered_failed_one_uncovered_give_one_fail_and_one_uncovered(self):
        steps = [step(SCOPE_STEPS[0], 'failure'), step(SCOPE_STEPS[1])] + all_steps()[2:]
        out = make(plan=[{'gate': 'G0', 'check': 'scope'}, {'gate': 'G0', 'check': 'review'}], steps=steps)
        self.assertEqual(by_gate(out), {'G0': 'fail'})
        self.assertEqual(len(out['records']), 1)
        self.assertEqual([u['check'] for u in out['uncovered']], ['review'])

    def test_a_check_absent_from_the_map_is_uncovered_with_its_detail(self):
        out = make(plan=[{'gate': 'G1', 'check': 'tests'}])
        self.assertEqual(out['uncovered'], [{'gate': 'G1', 'check': 'tests', 'detail': 'no CI step is evidence of this check'}])
        self.assertEqual(out['records'], [])

    def test_an_absent_step_is_uncovered(self):
        steps = [s for s in all_steps() if s['name'] != BUILD_STEP]
        out = make(steps=steps)
        self.assertEqual(by_gate(out), {'G0': 'pass', 'G2': 'pass'})
        self.assertIn({'gate': 'G1', 'check': 'build', 'detail': 'step not present'}, out['uncovered'])

    def test_a_step_present_twice_is_uncovered(self):
        out = make(steps=all_steps() + [step(BUILD_STEP)])
        self.assertNotIn('G1', by_gate(out))
        self.assertIn({'gate': 'G1', 'check': 'build', 'detail': 'step named more than once'}, out['uncovered'])

    def test_a_conclusion_that_is_not_success_or_failure_is_uncovered(self):
        for c in ('skipped', 'cancelled', None, 'neutral', 'timed_out', '', 'Success'):
            steps = [step(BUILD_STEP, c) if s['name'] == BUILD_STEP else s for s in all_steps()]
            out = make(steps=steps)
            self.assertNotIn('G1', by_gate(out), c)
            self.assertIn({'gate': 'G1', 'check': 'build', 'detail': 'conclusion is neither success nor failure'},
                          out['uncovered'], c)


class AC3Outcomes(unittest.TestCase):
    def test_all_success_is_pass(self):
        self.assertEqual(by_gate(make()), {'G0': 'pass', 'G1': 'pass', 'G2': 'pass'})

    def test_one_failure_with_every_step_present_is_fail(self):
        steps = [step(BUILD_STEP, 'failure') if s['name'] == BUILD_STEP else s for s in all_steps()]
        out = make(steps=steps)
        self.assertEqual(by_gate(out), {'G0': 'pass', 'G1': 'fail', 'G2': 'pass'})

    def test_a_check_with_a_failed_step_and_another_missing_duplicated_or_skipped_is_never_fail(self):
        base = [step(SCOPE_STEPS[0], 'failure')]
        for second in ([], [step(SCOPE_STEPS[1])] * 2, [step(SCOPE_STEPS[1], 'skipped')]):
            out = make(plan=[{'gate': 'G0', 'check': 'scope'}], steps=base + second)
            self.assertEqual(out['records'], [])
            self.assertEqual(len(out['uncovered']), 1)

    def test_a_gate_of_two_entries_one_failing_one_passing_is_fail(self):
        steps = [step(BUILD_STEP, 'failure')] + [s for s in all_steps() if s['name'] != BUILD_STEP]
        out = make(plan=[{'gate': 'G1', 'check': 'build'}, {'gate': 'G1', 'check': 'lint'}], steps=steps)
        self.assertEqual(by_gate(out), {'G1': 'fail'})
        self.assertEqual(out['uncovered'], [])

    def test_the_order_of_the_entries_of_a_gate_does_not_matter(self):
        steps = [step(LINT_STEP, 'failure')] + [s for s in all_steps() if s['name'] != LINT_STEP]
        for plan in ([{'gate': 'G1', 'check': 'build'}, {'gate': 'G1', 'check': 'lint'}],
                     [{'gate': 'G1', 'check': 'lint'}, {'gate': 'G1', 'check': 'build'}]):
            self.assertEqual(by_gate(make(plan=plan, steps=steps)), {'G1': 'fail'})

    def test_a_gate_of_two_passing_entries_is_one_pass_record(self):
        out = make(plan=[{'gate': 'G1', 'check': 'build'}, {'gate': 'G1', 'check': 'lint'}])
        self.assertEqual(by_gate(out), {'G1': 'pass'})
        self.assertEqual(len(out['records']), 1)

    def test_no_record_for_an_absent_or_skipped_step(self):
        for steps in ([], [step(n, 'skipped') for n in SCOPE_STEPS + [BUILD_STEP, LINT_STEP]]):
            out = make(steps=steps)
            self.assertEqual(out['records'], [])
            self.assertEqual(len(out['uncovered']), 4)

    def test_the_gate_order_follows_the_plan_and_a_repeated_gate_is_grouped(self):
        plan = [{'gate': 'G2', 'check': 'lint'}, {'gate': 'G0', 'check': 'scope'}, {'gate': 'G2', 'check': 'build'}]
        out = make(plan=plan)
        self.assertEqual([r['gate'] for r in out['records']], ['G2', 'G0'])


class AC4TheRecords(unittest.TestCase):
    KEYS = {'record_id', 'fact_kind', 'source_class', 'recorder', 'subject', 'commit', 'intent_versions', 'gate',
            'outcome'}

    def test_every_record_has_exactly_the_keys_and_the_fixed_values(self):
        out = make()
        self.assertEqual(len(out['records']), 3)
        for r in out['records']:
            self.assertEqual(set(r), self.KEYS)
            self.assertNotIn('ci_run', r)
            self.assertEqual((r['fact_kind'], r['source_class'], r['recorder'], r['subject'], r['commit']),
                             ('observation', CI, 'external CI', TASK, COMMIT))

    def test_the_record_id_is_the_sha256_of_the_four_texts(self):
        for r in make()['records']:
            want = hashlib.sha256('\n'.join(['ci-gate', TASK, COMMIT, r['gate']]).encode('utf-8')).hexdigest()
            self.assertEqual(r['record_id'], want)
        ids = [r['record_id'] for r in make()['records']]
        self.assertEqual(len(set(ids)), 3)

    def test_the_intent_versions_are_a_copy(self):
        iv = dict(IV)
        out = make(iv=iv)
        self.assertEqual(iv, IV)
        out['records'][0]['intent_versions']['SPEC-001'] = 'v9'
        self.assertEqual(iv, IV)
        self.assertIsNot(out['records'][0]['intent_versions'], out['records'][1]['intent_versions'])

    def test_the_arguments_are_not_changed_and_the_result_is_equal_for_equal_arguments(self):
        args = (TASK, COMMIT, dict(IV), copy.deepcopy(PLAN4), all_steps(), copy.deepcopy(MAP), 'external CI')
        before = copy.deepcopy(args)
        first = gate_records.gate_records(*args)
        self.assertEqual(args, before)
        self.assertEqual(gate_records.gate_records(*args), first)
        self.assertEqual(gate_records.gate_records(*copy.deepcopy(args)), first)

    def test_different_commits_and_tasks_give_different_ids(self):
        a = {r['gate']: r['record_id'] for r in make()['records']}
        b = {r['gate']: r['record_id'] for r in make(commit='b' * 40)['records']}
        c = {r['gate']: r['record_id'] for r in make(task='TASK-501')['records']}
        for g in a:
            self.assertNotEqual(a[g], b[g])
            self.assertNotEqual(a[g], c[g])

    def test_every_record_passes_check_record(self):
        for outcome in ('success', 'failure'):
            for r in make(steps=all_steps(outcome))['records']:
                self.assertEqual(records.check_record(r), [])

    def _request(self):
        return {'task_id': TASK, 'task_content_hash': 'c' * 64, 'evaluated_commit': COMMIT, 'intent_versions': dict(IV),
                'task_state': 'VERIFYING', 'changed_paths': ['src/x.py'], 'retry_count': {'used': 0, 'limit': 2}}

    def _inputs(self, plan):
        return {'traces_to': ['SPEC-001'], 'risk': 'low', 'owner_kept_act': False, 'weakens_evidence': False,
                'delegation_in_force': True, 'auto_accept': False, 'verification_plan': plan,
                'evidence_profile': [{'dimension': 'functional', 'evidence_types': ['build']}],
                'applicable_articles': [], 'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1'}

    def test_the_governor_counts_the_records_and_names_review_as_the_missing_gate(self):
        out = make()
        plan = [e['gate'] for e in PLAN4]
        decision = governor.evaluate(self._request(), self._inputs(plan), out['records'])
        self.assertEqual(decision['missing_gates'], ['G3'])
        self.assertEqual(decision['failed_gates'], [])
        self.assertEqual(decision['decision'], 'INSUFFICIENT_EVIDENCE')

    def test_the_governor_names_every_gate_missing_without_the_records_and_a_failed_gate_with_a_fail(self):
        plan = [e['gate'] for e in PLAN4]
        self.assertEqual(governor.evaluate(self._request(), self._inputs(plan), [])['missing_gates'],
                         ['G0', 'G1', 'G2', 'G3'])
        steps = [step(BUILD_STEP, 'failure') if s['name'] == BUILD_STEP else s for s in all_steps()]
        decision = governor.evaluate(self._request(), self._inputs(plan), make(steps=steps)['records'])
        self.assertEqual(decision['failed_gates'], ['G1'])
        self.assertEqual(decision['decision'], 'NEEDS_REWORK')


class AC5TheDefaultMap(unittest.TestCase):
    def test_exactly_the_three_checks_with_the_exact_step_names(self):
        self.assertEqual(gate_records.DEFAULT_CHECK_MAP, {
            'scope': ['G0 task detection (the contract commit on main)', 'G0 scope (V0)'],
            'build': ['G1 build'],
            'lint': ['lint (pyflakes 4.0.3, pinned by version and hash)']})
        for check in ('review', 'tests', 'constitution'):
            self.assertNotIn(check, gate_records.DEFAULT_CHECK_MAP)

    def test_each_named_step_is_a_name_line_of_the_workflow_exactly_once(self):
        text = (ROOT / '.github/workflows/aieos-checks.yml').read_bytes().decode('utf-8')
        lines = [ln.strip() for ln in text.split('\n')]
        for names in gate_records.DEFAULT_CHECK_MAP.values():
            for name in names:
                self.assertEqual(lines.count('- name: ' + name), 1, name)


if __name__ == '__main__':
    unittest.main()

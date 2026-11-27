"""Unit tests of the gate maker of TASK-150 (BT2 of DEF-0136, AC1 to AC5). Every case is built in memory; the only files
read are the module's own source and the CI workflow, with pathlib's read_bytes.
"""
import ast
import copy
import hashlib
import pathlib
import unittest
from unittest import mock

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
# The exact names of the CI steps that spec-04 section 2 gives to the constitution gate (the names in the job of the CI run
# of the task push); the default map holds seven of them: the SEC-003 record and GOV-003 evaluator paths names are not
# in the map.
CONSTITUTION_STEPS = [
    'deterministic_rule (INV-001, INV-002, INV-004)', 'OPS-003 pattern rules',
    'GOV-003 evaluator paths (reports an evaluator change)',
    "SEC-001 secret scan (tip tree; every commit's message, file names and added lines)",
    "SEC-002 pattern rules (every commit's added lines)", 'SEC-003 record (changes under .github/)',
    'OPS-002 owner-kept paths', 'INV-010 replay', 'static_security_analysis (bandit, every package pinned by version and hash)']
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

    def test_public_names_are_exactly_three(self):
        tree = ast.parse(self.source)
        public = set()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith('_'):
                public.add(node.name)
            elif isinstance(node, ast.Assign):
                public.update(t.id for t in node.targets if isinstance(t, ast.Name) and not t.id.startswith('_'))
        self.assertEqual(public, {'gate_records', 'type_records', 'DEFAULT_CHECK_MAP'})

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
        # Each case names the EXACT error text it must give, so that a case cannot pass for another reason (a check
        # removed, the failure caught by the general handler) than the one it names.
        task_e = 'task_id is not TASK- and digits'
        commit_e = 'commit is not 40 lowercase hexadecimal characters'
        iv_map_e = 'intent_versions is not a non-empty mapping'
        iv_entry_e = 'intent_versions holds an entry that is not a non-empty name and v and digits'
        plan_list_e = 'plan is not a non-empty list'
        plan_keys_e = 'a plan entry is not a mapping with exactly the keys gate and check'
        plan_gate_e = 'a plan entry has a gate that is not G and digits'
        plan_check_e = 'a plan entry has a check that is not a non-empty text'
        steps_list_e = 'steps is not a list'
        step_keys_e = 'a step is not a mapping with exactly the keys name and conclusion'
        step_name_e = 'a step has a name that is not a non-empty text'
        step_concl_e = 'a step has a conclusion that is neither a text nor None'
        map_e = 'check_map is not a mapping'
        map_entry_e = 'check_map holds an entry that is not a non-empty check and a non-empty list of step names'
        rec_e = 'recorder is not a non-empty text'
        bad = [
            (task_e, dict(task='TASK-')), (task_e, dict(task='task-1')), (task_e, dict(task='TASK-1\n')),
            (task_e, dict(task=5)),
            (commit_e, dict(commit='a' * 39)), (commit_e, dict(commit='A' * 40)), (commit_e, dict(commit='a' * 40 + '\n')),
            (commit_e, dict(commit=None)),
            (iv_map_e, dict(iv={})), (iv_map_e, dict(iv=[('a', 'v1')])), (iv_entry_e, dict(iv={'': 'v1'})),
            (iv_entry_e, dict(iv={'a': 'v'})), (iv_entry_e, dict(iv={'a': 'v1x'})), (iv_entry_e, dict(iv={'a': 1})),
            (iv_entry_e, dict(iv={1: 'v1'})),
            (plan_list_e, dict(plan=[])), (plan_list_e, dict(plan='G0')), (plan_keys_e, dict(plan=['G0'])),
            (plan_keys_e, dict(plan=[{'gate': 'G0'}])),
            (plan_keys_e, dict(plan=[{'gate': 'G0', 'check': 'scope', 'args': []}])),
            (plan_gate_e, dict(plan=[{'gate': 'g0', 'check': 'scope'}])),
            (plan_gate_e, dict(plan=[{'gate': 'G', 'check': 'scope'}])),
            (plan_gate_e, dict(plan=[{'gate': 3, 'check': 'scope'}])),
            (plan_check_e, dict(plan=[{'gate': 'G0', 'check': ''}])), (plan_check_e, dict(plan=[{'gate': 'G0', 'check': 3}])),
            (steps_list_e, dict(steps=None)), (step_keys_e, dict(steps=['x'])), (step_keys_e, dict(steps=[{'name': 'a'}])),
            (step_name_e, dict(steps=[{'name': '', 'conclusion': 'success'}])),
            (step_name_e, dict(steps=[{'name': 3, 'conclusion': 'success'}])),
            (step_concl_e, dict(steps=[{'name': 'a', 'conclusion': 1}])),
            (step_concl_e, dict(steps=[{'name': 'a', 'conclusion': True}])),
            (step_keys_e, dict(steps=[{'name': 'a', 'conclusion': 'success', 'x': 1}])),
            (map_e, dict(check_map=None)), (map_entry_e, dict(check_map={'scope': []})),
            (map_entry_e, dict(check_map={'scope': 'G1 build'})), (map_entry_e, dict(check_map={'scope': ['']})),
            (map_entry_e, dict(check_map={'': ['a']})), (map_entry_e, dict(check_map={'scope': [3]})),
            (rec_e, dict(recorder='')), (rec_e, dict(recorder=None)),
        ]
        for want, kw in bad:
            out = make(**kw)
            self.assertEqual(out['error'], want, kw)
            self.assertEqual((out['records'], out['uncovered']), ([], []), kw)

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
        self.assertEqual(out['error'], 'an argument could not be read: RuntimeError')
        self.assertEqual((out['records'], out['uncovered']), ([], []))

    def test_a_base_exception_passes_through(self):
        class Worse(dict):
            def items(self):
                raise Boom()

        with self.assertRaises(Boom):
            make(iv=Worse(IV))


class AC2MatchingByCheck(unittest.TestCase):
    def test_review_gets_no_record_even_when_every_constitution_step_is_success(self):
        steps = all_steps() + [step(n) for n in CONSTITUTION_STEPS + ['unit_test']]
        self.assertEqual(len(CONSTITUTION_STEPS), 9)
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

    def test_one_step_name_present_twice_with_different_conclusions_is_uncovered_never_fail_or_pass(self):
        for first, second in (('success', 'failure'), ('failure', 'success')):
            steps = [s for s in all_steps() if s['name'] != BUILD_STEP] + [step(BUILD_STEP, first), step(BUILD_STEP, second)]
            out = make(plan=[{'gate': 'G1', 'check': 'build'}], steps=steps)
            self.assertEqual(out['records'], [], (first, second))
            self.assertEqual(out['uncovered'], [{'gate': 'G1', 'check': 'build', 'detail': 'step named more than once'}])

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
        # missing_gates is the assertion that shows the records are counted: without them all four gates are missing
        # (the next test). The decision alone does not prove the counting: this profile (build evidence, which these
        # records do not carry) would give INSUFFICIENT_EVIDENCE even with no gate missing.
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


# TASK-164: the seven steps of the default map's entry constitution, in the workflow's order, and the three steps that the
# entry leaves out.
SEVEN_STEPS = [
    "SEC-001 secret scan (tip tree; every commit's message, file names and added lines)",
    "SEC-002 pattern rules (every commit's added lines)", 'OPS-002 owner-kept paths', 'INV-010 replay',
    'deterministic_rule (INV-001, INV-002, INV-004)', 'OPS-003 pattern rules',
    'static_security_analysis (bandit, every package pinned by version and hash)']
LEFT_OUT = ['SEC-003 record (changes under .github/)', 'GOV-003 evaluator paths (reports an evaluator change)',
            'GOV-003 evaluator lists equal']
CONSTITUTION_PLAN = [{'gate': 'G3', 'check': 'constitution'}]
RUN_LOW_PLAN = [{'gate': 'G0', 'check': 'scope'}, {'gate': 'G1', 'check': 'build'}, {'gate': 'G2', 'check': 'lint'},
                {'gate': 'G3', 'check': 'constitution'}]


def seven(changed=None, conclusion='success'):
    """The seven steps, each successful except the one named by changed, which gets the given conclusion."""
    return [step(n, conclusion if n == changed else 'success') for n in SEVEN_STEPS]


class TASK164TheConstitutionEntry(unittest.TestCase):
    def uncovered(self, steps, detail, message):
        out = make(plan=CONSTITUTION_PLAN, steps=steps)
        self.assertEqual((out['error'], out['records']), (None, []), message)
        self.assertEqual(out['uncovered'], [{'gate': 'G3', 'check': 'constitution', 'detail': detail}], message)

    def test_all_seven_steps_successful_is_pass(self):
        out = make(plan=CONSTITUTION_PLAN, steps=seven())
        self.assertEqual((out['error'], out['uncovered']), (None, []))
        self.assertEqual(by_gate(out), {'G3': 'pass'})

    def test_one_failed_step_is_fail(self):
        for name in SEVEN_STEPS:
            out = make(plan=CONSTITUTION_PLAN, steps=seven(name, 'failure'))
            self.assertEqual(by_gate(out), {'G3': 'fail'}, name)
            self.assertEqual(out['uncovered'], [], name)

    def test_an_absent_repeated_or_otherwise_concluded_step_leaves_the_gate_uncovered(self):
        for name in SEVEN_STEPS:
            self.uncovered([s for s in seven() if s['name'] != name], 'step not present', name)
            self.uncovered(seven() + [step(name)], 'step named more than once', name)
            self.uncovered(seven(name, 'skipped'), 'conclusion is neither success nor failure', name)

    def test_the_three_steps_left_out_never_count(self):
        for conclusion in ('success', 'failure'):
            others = [step(n, conclusion) for n in LEFT_OUT]
            out = make(plan=CONSTITUTION_PLAN, steps=seven() + others)
            self.assertEqual(by_gate(out), {'G3': 'pass'}, conclusion)
            self.uncovered(others, 'step not present', conclusion)
            self.uncovered(seven()[1:] + others, 'step not present', conclusion)

    def test_a_run_made_low_plan_has_no_missing_gate_and_its_profile_is_not_met(self):
        out = make(plan=RUN_LOW_PLAN, steps=all_steps() + seven())
        self.assertEqual(by_gate(out), {'G0': 'pass', 'G1': 'pass', 'G2': 'pass', 'G3': 'pass'})
        request = {'task_id': TASK, 'task_content_hash': 'c' * 64, 'evaluated_commit': COMMIT, 'intent_versions': dict(IV),
                   'task_state': 'VERIFYING', 'changed_paths': ['docs/Deferred/a.md'],
                   'retry_count': {'used': 0, 'limit': 1}}
        articles = [('GOV-004', 'human_review'), ('GOV-005', 'human_review'), ('OPS-002', 'human_review'),
                    ('SEC-002', 'ai_review'), ('OPS-003', 'ai_review')]
        inputs = {'traces_to': ['SPEC-001'], 'risk': 'low', 'owner_kept_act': False, 'weakens_evidence': False,
                  'delegation_in_force': True, 'auto_accept': False, 'verification_plan': ['G0', 'G1', 'G2', 'G3'],
                  'evidence_profile': [{'dimension': 'functional', 'evidence_types': ['build', 'lint']}],
                  'applicable_articles': [{'id': a, 'evidence_required': [t]} for a, t in articles],
                  'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1'}
        decision = governor.evaluate(request, inputs, out['records'])
        self.assertEqual((decision['missing_gates'], decision['failed_gates']), ([], []))
        self.assertEqual((decision['decision'], decision['table_row']), ('INSUFFICIENT_EVIDENCE', 3))
        self.assertEqual(decision['next_task_state'], 'REWORK')
        want = [{'dimension': 'functional', 'required': ['build', 'lint'], 'satisfied_by': [],
                 'missing_types': ['build', 'lint']}]
        want += [{'dimension': a, 'required': [t], 'satisfied_by': [], 'missing_types': [t]} for a, t in articles]
        self.assertEqual(decision['profile_used'], want)


class AC5TheDefaultMap(unittest.TestCase):
    def test_exactly_the_four_checks_with_the_exact_step_names(self):
        self.assertEqual(gate_records.DEFAULT_CHECK_MAP, {
            'scope': ['G0 task detection (the contract commit on main)', 'G0 scope (V0)'],
            'build': ['G1 build'],
            'lint': ['lint (pyflakes 4.0.3, pinned by version and hash)'],
            'constitution': SEVEN_STEPS})
        for check in ('review', 'tests'):
            self.assertNotIn(check, gate_records.DEFAULT_CHECK_MAP)

    def test_each_named_step_is_a_name_line_of_the_workflow_exactly_once(self):
        text = (ROOT / '.github/workflows/aieos-checks.yml').read_bytes().decode('utf-8')
        lines = [ln.strip() for ln in text.split('\n')]
        for names in gate_records.DEFAULT_CHECK_MAP.values():
            for name in names:
                self.assertEqual(lines.count('- name: ' + name), 1, name)


# TASK-165: the maker of the build and lint evidence records.
BUILD_ID = '3eaa667526710df93f39bfc6e7d10cf893335d84f0323a90a19f091b8e5347fb'
LINT_ID = 'f2410d69ca74fab3250bbbbc399f7390b490b26e4e0e50863e6fdbddd285db9d'
BOTH = [{'dimension': 'functional', 'evidence_type': 'build'}, {'dimension': 'functional', 'evidence_type': 'lint'}]
WRONG_WANTED = [
    {}, 'build', (), 7, ['build'], [[]], [{'dimension': 'functional'}], [{'evidence_type': 'build'}],
    [{'dimension': 'functional', 'evidence_type': 'build', 'gate': 'G1'}], [{'dimension': '', 'evidence_type': 'build'}],
    [{'dimension': 7, 'evidence_type': 'build'}], [{'dimension': '\ud800', 'evidence_type': 'build'}],
    [{'dimension': 'functional', 'evidence_type': 'unit_test'}], [{'dimension': 'functional', 'evidence_type': ''}],
    [{'dimension': 'functional', 'evidence_type': ['build']}]]


def typed(wanted=DEFAULT, steps=DEFAULT, task=TASK, commit=COMMIT, iv=DEFAULT, recorder='external CI'):
    return gate_records.type_records(
        task, commit, dict(IV) if iv is DEFAULT else iv, copy.deepcopy(BOTH) if wanted is DEFAULT else wanted,
        all_steps() if steps is DEFAULT else steps, recorder)


def record(ident, kind, outcome='pass', dimension='functional'):
    return {'record_id': ident, 'fact_kind': 'observation', 'source_class': CI, 'recorder': 'external CI',
            'subject': TASK, 'commit': COMMIT, 'intent_versions': {'SPEC-001': 'v2'}, 'evidence_type': kind,
            'dimension': dimension, 'outcome': outcome}


class TASK165TheTypeMaker(unittest.TestCase):
    def test_a_build_and_a_lint_pair_give_the_two_exact_records(self):
        before = copy.deepcopy(MAP)
        iv = dict(IV)
        out = typed(iv=iv)
        self.assertEqual(out, {'records': [record(BUILD_ID, 'build'), record(LINT_ID, 'lint')], 'error': None})
        for r in out['records']:
            self.assertEqual(records.check_record(r), [])
            self.assertIsNot(r['intent_versions'], iv)
        self.assertEqual(MAP, before)

    def test_a_failed_step_gives_a_fail_record(self):
        steps = [step(BUILD_STEP, 'failure') if s['name'] == BUILD_STEP else s for s in all_steps()]
        self.assertEqual(typed(steps=steps)['records'],
                         [record(BUILD_ID, 'build', 'fail'), record(LINT_ID, 'lint')])

    def test_an_absent_repeated_skipped_or_open_step_gives_no_record(self):
        others = [s for s in all_steps() if s['name'] != BUILD_STEP]
        for steps in (others, all_steps() + [step(BUILD_STEP)], others + [step(BUILD_STEP, 'skipped')],
                      others + [step(BUILD_STEP, None)]):
            out = typed(steps=steps)
            self.assertEqual(out, {'records': [record(LINT_ID, 'lint')], 'error': None}, steps[-1])

    def test_the_step_names_are_those_of_the_default_map(self):
        with mock.patch.dict(gate_records.DEFAULT_CHECK_MAP, {'build': ['another step']}):
            self.assertEqual(typed()['records'], [record(LINT_ID, 'lint')])
            self.assertEqual(typed(steps=all_steps() + [step('another step')])['records'][0],
                             record(BUILD_ID, 'build'))

    def test_a_repeated_pair_is_made_once_and_an_empty_wanted_gives_nothing(self):
        out = typed(wanted=BOTH + BOTH)
        self.assertEqual([r['record_id'] for r in out['records']], [BUILD_ID, LINT_ID])
        self.assertEqual(typed(wanted=[]), {'records': [], 'error': None})

    def test_the_dimension_is_the_pairs_and_the_id_binds_it(self):
        out = typed(wanted=[{'dimension': 'delivery', 'evidence_type': 'build'}])
        self.assertEqual(out['records'], [record(
            'b03128543bf1de940fd5d86afbd7e61335a63912bcf6fe25aad5265c8bb1e526', 'build', dimension='delivery')])

    def test_each_wrong_form_is_an_error_with_no_record(self):
        for wanted in WRONG_WANTED + [None]:
            out = typed(wanted=wanted)
            self.assertEqual((set(out), out['records']), ({'records', 'error'}, []), wanted)
            self.assertTrue(isinstance(out['error'], str) and out['error'], wanted)
        for changes in (dict(task='TASK-x'), dict(commit='A' * 40), dict(iv={}), dict(iv={'S': 'two'}),
                        dict(steps={}), dict(steps=[{'name': 'x'}]), dict(recorder='')):
            out = typed(**changes)
            self.assertEqual(out['records'], [], changes)
            self.assertTrue(isinstance(out['error'], str) and out['error'], changes)

    def test_no_exception_leaves_and_a_base_exception_passes_through(self):
        with mock.patch.object(gate_records.hashlib, 'sha256', mock.Mock(side_effect=RuntimeError('x'))):
            self.assertEqual(typed(), {'records': [], 'error': 'an argument could not be read: RuntimeError'})
        with mock.patch.object(gate_records.hashlib, 'sha256', mock.Mock(side_effect=Boom())):
            with self.assertRaises(Boom):
                typed()


if __name__ == '__main__':
    unittest.main()

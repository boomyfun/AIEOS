"""Unit tests of the input assembler of TASK-152 (BT3b-1, AC1 to AC7). Every case is built in memory. The log fixtures are
the two of the CI evidence tests (TASK-151), cut by script from that test file and embedded as constants, so no test
reads a log file; the only file read is the module's own source. The values of the sources below are FIXTURES, not
policy: no test asserts that they are the repository's policy.
"""
import ast
import copy
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import ci_evidence
from aieos_bootstrap import eval_inputs
from aieos_bootstrap import governor

ROOT = pathlib.Path(__file__).resolve().parents[2]
# The fixtures: byte-for-byte cuts of the saved logs of `gh run view <id> --log` (each line: job TAB step TAB text), written as ASCII
# string literals (ESC as \x1b, the byte-order mark as \ufeff); cut by script from the sources named here, line numbers of the full logs.
# BRANCH_LOG: aieos-checks run 44780942904 (the task branch push), lines 30, 143-144, 229-233.
BRANCH_LOG = (
    'checks\tSet up job\t2026-11-20T17:11:58.6217825Z Complete job name: checks\n'
    "checks\tG0 task detection (the contract commit on main)\t2026-11-20T17:12:03.0320708Z \x1b[36;1m        open('../range-base.txt', 'w').write('')\x1b[0m\n"
    "checks\tG0 task detection (the contract commit on main)\t2026-11-20T17:12:03.0321134Z \x1b[36;1m        print('G0 detect: no task (no pushed commit outside main carries an AIEOS-Task trailer; commits outside main: %d)' % len(ahead))\x1b[0m\n"
    'checks\tG0 task detection (the contract commit on main)\t2026-11-20T17:12:03.3557860Z   AIEOS_ARGS: detect\n'
    'checks\tG0 task detection (the contract commit on main)\t2026-11-20T17:12:03.3558218Z ##[endgroup]\n'
    'checks\tG0 task detection (the contract commit on main)\t2026-11-20T17:12:03.4046970Z G0 detect: task TASK-150 contract commit 3572f9585da94f9ec2fb749a25e46a9e040f0033 base f48804f6e3001a3c9dd070437e7ce339d7881150\n'
    'checks\tG0 task detection (the contract commit on main)\t2026-11-20T17:12:03.4068619Z G0 contract sha256 7c45fd60c17666c085b2c5d6583a01e70988e2fcf3c0fad1117a8f673eb504ff\n'
    'checks\tCollect the pushed commits and their changed paths\t\ufeff2026-11-20T17:12:03.4097193Z ##[group]Run set -euo pipefail\n'
)
# MAIN_LOG: aieos-checks run 44777971143 (the push of main at the contract commit), lines 143-144, 229-232.
MAIN_LOG = (
    "checks\tG0 task detection (the contract commit on main)\t2026-11-20T16:54:18.0041934Z \x1b[36;1m        open('../range-base.txt', 'w').write('')\x1b[0m\n"
    "checks\tG0 task detection (the contract commit on main)\t2026-11-20T16:54:18.0044129Z \x1b[36;1m        print('G0 detect: no task (no pushed commit outside main carries an AIEOS-Task trailer; commits outside main: %d)' % len(ahead))\x1b[0m\n"
    'checks\tG0 task detection (the contract commit on main)\t2026-11-20T16:54:18.0468999Z   AIEOS_ARGS: detect\n'
    'checks\tG0 task detection (the contract commit on main)\t2026-11-20T16:54:18.0470099Z ##[endgroup]\n'
    'checks\tG0 task detection (the contract commit on main)\t2026-11-20T16:54:18.0825689Z G0 detect: no task (no pushed commit outside main carries an AIEOS-Task trailer; commits outside main: 0)\n'
    'checks\tCollect the pushed commits and their changed paths\t\ufeff2026-11-20T16:54:18.0924408Z ##[group]Run set -euo pipefail\n'
)

TASK = 'TASK-150'
COMMIT = '06880dd8d00b69fa2a9f25fc4036a635bdd31fc0'
POLICY_REF = 'b' * 40
SHA = '7c45fd60c17666c085b2c5d6583a01e70988e2fcf3c0fad1117a8f673eb504ff'
WORKFLOW = '.github/workflows/aieos-checks.yml'
MAPPED = ['G0 task detection (the contract commit on main)', 'G0 scope (V0)', 'G1 build',
          'lint (pyflakes 4.0.3, pinned by version and hash)']
PLAN4 = [{'gate': 'G0', 'check': 'scope'}, {'gate': 'G1', 'check': 'build'}, {'gate': 'G2', 'check': 'lint'},
         {'gate': 'G3', 'check': 'review', 'args': ['AC1', 'AC2']}]
GAPS = ('intent_versions', 'owner_kept_rules', 'articles', 'default_profiles', 'requirement_profiles',
        'evidence_comparison', 'delegation', 'auto_accept', 'level_version', 'ruleset_version', 'policy_version',
        'risk_rules')
POLICY_PATHS = ('docs/specs/risk-rules-gov-aieos.md', 'docs/pre-genesis/constitution.md',
                'docs/pre-genesis/assurance-model.md', 'docs/pre-genesis/decision-matrix.md')


def step(name, conclusion='success'):
    return {'name': name, 'conclusion': conclusion}


def run(**changes):
    r = {'run_id': 100, 'attempt': 1, 'head_sha': COMMIT, 'event': 'push', 'head_branch': 'task/' + TASK,
         'workflow_path': WORKFLOW, 'status': 'completed', 'conclusion': 'success',
         'steps': [step(n) for n in MAPPED], 'log': BRANCH_LOG}
    r.update(changes)
    return r


def good_contract(**changes):
    c = {'task': TASK, 'traces_to': ['SPEC-001'], 'risk': 'low', 'owner_kept_act': 'false',
         'verification_plan': copy.deepcopy(PLAN4),
         'autonomy': {'max_level': 'L1', 'budgets': {'tokens': '400k', 'wall_time': '2h', 'retries': '1',
                                                    'human_attention': '0m'}}}
    c.update(changes)
    return c


def good_sources(**changes):
    """FIXTURE values in the forms that governor.derive_inputs requires; they are not policy."""
    s = {
        'intent_versions': {'SPEC-001': 'v2'},
        'owner_kept_rules': [{'id': 'OPS-002', 'match': ['docs/pre-genesis/measurement-protocol.md']}],
        'articles': [{'id': 'INV-002', 'scope': ['src/**'], 'evidence_required': ['ai_review']}],
        'default_profiles': {'medium': [{'dimension': 'functional', 'evidence_types': ['unit_test']}],
                             'critical': [{'dimension': 'functional', 'evidence_types': ['unit_test']}]},
        'requirement_profiles': [{'id': 'SPEC-001', 'add': [{'dimension': 'security',
                                                            'evidence_types': ['static_security_analysis']}]}],
        'evidence_comparison': {'weakens': False},
        'delegation': True,
        'auto_accept': {},
        'level_version': 'v1',
        'ruleset_version': 'v1',
        'policy_version': 'v2',
        'risk_rules': [{'match': ['docs/**', '*.md'], 'class': 'low'}, {'match': ['src/**', 'tests/**'], 'class': 'medium'},
                       {'match': ['.github/**'], 'class': 'critical'}],
    }
    s.update(changes)
    return s


def kw(**changes):
    a = {'task_id': TASK, 'evaluated_commit': COMMIT, 'policy_ref': POLICY_REF, 'contract': good_contract(),
         'contract_sha256': SHA, 'changed_paths': ['src/x.py'], 'runs': [run()], 'sources': good_sources(),
         'log_payloads': [], 'recorder': 'external CI'}
    a.update(changes)
    return a


def call(**changes):
    return eval_inputs.eval_inputs(**kw(**changes))


def refusal(out):
    return (out['refusal']['reason'], out['refusal']['detail']) if out['refusal'] else None


def ci_records():
    """The records that ci_evidence gives for the default arguments (the module under test must return the same)."""
    made = ci_evidence.ci_evidence(TASK, COMMIT, SHA, {'SPEC-001': 'v2'}, [{'gate': e['gate'], 'check': e['check']} for e in PLAN4],
                                   ['src/x.py'], [run()], 'external CI')
    assert made['refusal'] is None
    return made['records']


class Boom(BaseException):
    """A BaseException that is not an Exception (AC1)."""


class AC1TheModule(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / 'src/aieos_bootstrap/eval_inputs.py').read_bytes().decode('utf-8')

    def test_public_names_are_exactly_one(self):
        tree = ast.parse(self.source)
        public = set()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith('_'):
                public.add(node.name)
            elif isinstance(node, ast.Assign):
                public.update(t.id for t in node.targets if isinstance(t, ast.Name) and not t.id.startswith('_'))
        self.assertEqual(public, {'eval_inputs'})

    def test_the_public_attributes_of_the_module_are_the_function_and_the_three_imports(self):
        attrs = {n for n in dir(eval_inputs) if not n.startswith('_')}
        self.assertEqual(attrs, {'eval_inputs', 're', 'ci_evidence', 'governor'})

    def test_imports_and_forbidden_names(self):
        tree = ast.parse(self.source)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.update(node.module + '.' + a.name for a in node.names)
        self.assertEqual(imports, {'re', 'aieos_bootstrap.ci_evidence', 'aieos_bootstrap.governor'})
        calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertFalse(calls & {'open', 'exec', 'eval', 'compile', '__import__'})
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for bad in ('subprocess', 'system', 'environ', 'time', 'now'):
            self.assertNotIn(bad, names)

    def test_the_return_form(self):
        ok, bad = call(), call(task_id='x')
        self.assertEqual(set(ok), {'declared', 'values', 'ci_records', 'evidence', 'refusal'})
        self.assertEqual(set(bad), {'declared', 'values', 'ci_records', 'evidence', 'refusal'})
        self.assertIsNone(ok['refusal'])
        self.assertEqual((bad['declared'], bad['values'], bad['ci_records'], bad['evidence']), (None, None, [], None))
        self.assertEqual(set(bad['refusal']), {'reason', 'detail'})

    def test_every_argument_check_names_its_exact_detail(self):
        c = good_contract
        bad = [
            ('task_id is not TASK- and digits', dict(task_id='TASK-')), ('task_id is not TASK- and digits', dict(task_id=5)),
            ('evaluated_commit is not 40 lowercase hexadecimal characters', dict(evaluated_commit=COMMIT.upper())),
            ('evaluated_commit is not 40 lowercase hexadecimal characters', dict(evaluated_commit='a' * 39)),
            ('policy_ref is not 40 lowercase hexadecimal characters', dict(policy_ref='B' * 40)),
            ('policy_ref is not 40 lowercase hexadecimal characters', dict(policy_ref=None)),
            ('policy_ref equals evaluated_commit', dict(policy_ref=COMMIT)),
            ('contract is not a dict', dict(contract=[])), ('contract is not a dict', dict(contract=None)),
            ('contract has no traces_to that is a non-empty list of non-empty texts', dict(contract=c(traces_to=[]))),
            ('contract has no traces_to that is a non-empty list of non-empty texts', dict(contract=c(traces_to=['']))),
            ('contract has no risk of low, medium, high or critical', dict(contract=c(risk='severe'))),
            ('contract has no risk of low, medium, high or critical', dict(contract=c(risk=None))),
            ('contract has no owner_kept_act that is the text true or false', dict(contract=c(owner_kept_act=False))),
            ('contract has no owner_kept_act that is the text true or false', dict(contract=c(owner_kept_act=True))),
            ('contract has no owner_kept_act that is the text true or false', dict(contract=c(owner_kept_act='True'))),
            ('contract has no owner_kept_act that is the text true or false', dict(contract=c(owner_kept_act='yes'))),
            ('contract has no owner_kept_act that is the text true or false', dict(contract=c(owner_kept_act=''))),
            ('contract has no verification_plan that is a non-empty list', dict(contract=c(verification_plan=[]))),
            ('contract has no verification_plan that is a non-empty list', dict(contract=c(verification_plan='G0'))),
            ('contract has no autonomy with a budgets dict', dict(contract=c(autonomy=None))),
            ('contract has no autonomy with a budgets dict', dict(contract=c(autonomy={'budgets': 'x'}))),
            ('contract_sha256 is not 64 lowercase hexadecimal characters', dict(contract_sha256='A' * 64)),
            ('changed_paths is not a non-empty list of non-empty texts', dict(changed_paths=[])),
            ('changed_paths is not a non-empty list of non-empty texts', dict(changed_paths=['a', ''])),
            ('runs is not a list', dict(runs=None)),
            ('sources is not a dict with exactly its twelve keys', dict(sources=[])),
            ('log_payloads is not a list of dicts', dict(log_payloads=None)),
            ('log_payloads is not a list of dicts', dict(log_payloads=['x'])),
            ('recorder is not a non-empty text', dict(recorder='')), ('recorder is not a non-empty text', dict(recorder=None)),
        ]
        for want, changes in bad:
            out = call(**changes)
            self.assertEqual(refusal(out), ('argument', want), changes)
            self.assertEqual((out['declared'], out['values'], out['ci_records'], out['evidence']), (None, None, [], None), changes)

    def test_a_dict_subclass_whose_method_raises_gives_a_refusal(self):
        class Bad(dict):
            def get(self, *args):
                raise RuntimeError('own method')

        out = call(contract=Bad(good_contract()))
        self.assertEqual(refusal(out), ('argument', 'an argument could not be read: RuntimeError'))
        self.assertEqual((out['declared'], out['values'], out['ci_records'], out['evidence']), (None, None, [], None))

    def test_a_base_exception_passes_through(self):
        class Worse(dict):
            def get(self, *args):
                raise Boom()

        with self.assertRaises(Boom):
            call(contract=Worse(good_contract()))


class AC2TheGaps(unittest.TestCase):
    def test_with_every_source_in_form_the_module_goes_on(self):
        self.assertIsNone(call()['refusal'])

    def test_each_open_gap_gives_one_refusal_naming_exactly_it(self):
        for name in GAPS:
            out = call(sources=good_sources(**{name: None}))
            self.assertEqual(refusal(out), ('gap', 'open gaps: ' + name), name)
            self.assertEqual((out['declared'], out['values'], out['ci_records'], out['evidence']), (None, None, [], None), name)

    def test_several_open_gaps_are_named_in_the_list_order(self):
        out = call(sources=good_sources(risk_rules=None, owner_kept_rules=None, evidence_comparison=None))
        self.assertEqual(refusal(out), ('gap', 'open gaps: owner_kept_rules, evidence_comparison, risk_rules'))
        out = call(sources={k: None for k in GAPS})
        self.assertEqual(refusal(out), ('gap', 'open gaps: ' + ', '.join(GAPS)))

    def test_a_missing_key_and_an_extra_key_are_arguments(self):
        want = ('argument', 'sources is not a dict with exactly its twelve keys')
        s = good_sources()
        del s['delegation']
        self.assertEqual(refusal(call(sources=s)), want)
        s = good_sources()
        s['extra'] = 1
        self.assertEqual(refusal(call(sources=s)), want)

    def test_the_docstring_says_that_no_value_is_typed_and_fixtures_are_not_policy(self):
        doc = ' '.join(eval_inputs.__doc__.split())
        self.assertIn('no value is typed into the module', doc)
        self.assertIn('fixture values in the tests are not policy', doc)

    def test_a_gap_is_never_filled(self):
        ok = call()
        self.assertIsNotNone(ok['values'])
        for name in GAPS:
            self.assertIsNone(call(sources=good_sources(**{name: None}))['values'], name)


class AC3TheSourcesThatHaveReaders(unittest.TestCase):
    def test_retries_in_form(self):
        for text, want in (('0', 0), ('3', 3), ('100', 100)):
            c = good_contract()
            c['autonomy']['budgets']['retries'] = text
            self.assertEqual(call(contract=c)['declared']['retries'], want)

    def test_retries_out_of_form(self):
        form = 'retries is not one to three decimal digits without sign, space or leading zero'
        for text in ('-1', '+3', ' 3', '3 ', '03', '', 'three', '3.0', '1000'):
            c = good_contract()
            c['autonomy']['budgets']['retries'] = text
            self.assertEqual(refusal(call(contract=c)), ('retries', form), repr(text))
        c = good_contract()
        c['autonomy']['budgets']['retries'] = '101'
        self.assertEqual(refusal(call(contract=c)), ('retries', 'retries is above 100'))
        c = good_contract()
        c['autonomy']['budgets']['retries'] = 3
        self.assertEqual(refusal(call(contract=c)), ('retries', 'retries is not a text'))
        c = good_contract()
        del c['autonomy']['budgets']['retries']
        self.assertEqual(refusal(call(contract=c)), ('retries', 'budgets has no retries'))

    def test_the_gate_ids_are_the_entries_gate_values_in_order(self):
        out = call()
        self.assertEqual(out['values']['contract']['verification_plan'], ['G0', 'G1', 'G2', 'G3'])
        c = good_contract(verification_plan=[{'gate': 'G2', 'check': 'lint'}, {'gate': 'G0', 'check': 'scope'}])
        self.assertEqual(call(contract=c)['values']['contract']['verification_plan'], ['G2', 'G0'])

    def test_the_review_entry_with_args_is_accepted(self):
        self.assertIn({'gate': 'G3', 'check': 'review', 'args': ['AC1', 'AC2']}, good_contract()['verification_plan'])
        self.assertIsNone(call()['refusal'])

    def test_plan_entries_out_of_form(self):
        cases = (('a verification_plan entry is not a dict', ['G0']),
                 ('a verification_plan entry has no text gate', [{'check': 'scope'}]),
                 ('a verification_plan entry has no text gate', [{'gate': 3, 'check': 'scope'}]),
                 ('a verification_plan entry has no text gate', [{'gate': '', 'check': 'scope'}]),
                 ('a verification_plan entry has a gate that is not G and digits', [{'gate': 'g1', 'check': 'build'}]),
                 ('a verification_plan entry has a gate that is not G and digits', [{'gate': 'G', 'check': 'build'}]))
        for want, plan in cases:
            self.assertEqual(refusal(call(contract=good_contract(verification_plan=plan))), ('plan', want), plan)

    def test_risk_rules_in_the_governors_form_are_passed_on_unchanged_as_copies(self):
        rules = [{'match': ['src/**'], 'class': 'medium'}]
        s = good_sources(risk_rules=rules)
        out = call(sources=s)
        self.assertEqual(out['values']['risk_rules'], rules)
        self.assertIsNot(out['values']['risk_rules'], rules)
        self.assertIsNot(out['values']['risk_rules'][0], rules[0])
        self.assertIsNot(out['values']['risk_rules'][0]['match'], rules[0]['match'])

    def test_risk_rules_out_of_form(self):
        m = 'a risk rule has a match that is not a non-empty list of non-empty texts'
        k = 'a risk rule has a class that is not one of low, medium, high or critical'
        e = 'a risk rule is not a dict with exactly the keys match and class'
        cases = ((m, [{'match': [], 'class': None}]), (m, [{'match': [], 'class': 'low'}]), (m, [{'match': 'src/**', 'class': 'low'}]),
                 (m, [{'match': ['src/**', 3], 'class': 'low'}]), (k, [{'match': ['src/**'], 'class': None}]),
                 (k, [{'match': ['src/**'], 'class': 'severe'}]), (e, [{'match': ['src/**'], 'class': 'low', 'id': 'R1'}]),
                 (e, [{'match': ['src/**']}]), (e, [['src/**', 'low']]), ('risk_rules is not a list', {'match': ['a'], 'class': 'low'}))
        for want, rules in cases:
            self.assertEqual(refusal(call(sources=good_sources(risk_rules=rules))), ('risk_rules', want), rules)

    def test_policy_version_is_a_non_empty_text(self):
        self.assertEqual(call(sources=good_sources(policy_version='v5'))['values']['policy_version'], 'v5')
        for bad in ('', 5, ['v5'], True):
            self.assertEqual(refusal(call(sources=good_sources(policy_version=bad))),
                             ('argument', 'policy_version is not a non-empty text'), bad)

    def test_a_missing_budgets_key_is_a_retries_refusal_and_other_forms_stay_argument(self):
        # AC3 names a missing budgets key under reason retries; the objective's general rule keeps the wrong forms as argument (D-6847).
        c = good_contract()
        del c['autonomy']['budgets']
        self.assertEqual(refusal(call(contract=c)), ('retries', 'autonomy has no budgets'))
        detail = 'contract has no autonomy with a budgets dict'
        self.assertEqual(refusal(call(contract=good_contract(autonomy='x'))), ('argument', detail))
        self.assertEqual(refusal(call(contract=good_contract(autonomy={'budgets': ['retries']}))), ('argument', detail))
        self.assertEqual(refusal(call(contract=good_contract(autonomy={'budgets': None}))), ('argument', detail))

    def test_requirement_profiles_must_be_a_list_whose_dict_entries_have_a_text_id(self):
        # governor.py :614-:618 adds an entry only when its id is in the traced requirements, so a non-text id would silently drop its evidence.
        add = [{'dimension': 'security', 'evidence_types': ['review']}]
        for bad in (5, 'x', {}, {'id': 'SPEC-001', 'add': add}):
            self.assertEqual(refusal(call(sources=good_sources(requirement_profiles=bad))),
                             ('argument', 'requirement_profiles is not a list'), bad)
        for bad_id in (5, 1.5, True, ['SPEC-001'], '', '\ud800'):
            reqs = [{'id': bad_id, 'add': add}]
            self.assertEqual(refusal(call(sources=good_sources(requirement_profiles=reqs))),
                             ('argument', 'a requirement profile has no text id'), bad_id)
        self.assertEqual(refusal(call(sources=good_sources(requirement_profiles=[{'add': add}]))),
                         ('argument', 'a requirement profile has no text id'))
        self.assertIsNone(call(sources=good_sources(requirement_profiles=[]))['refusal'])
        # a non-dict entry or a dict with other keys stays with governor.derive_inputs, which raises: reason incomplete
        out = call(sources=good_sources(requirement_profiles=[5]))
        self.assertEqual(refusal(out), ('incomplete', 'governor.derive_inputs refused the values: a requirement profile is not {id, add}'))

    def test_text_that_utf8_cannot_encode_is_refused_like_governor_does(self):
        surrogate = 'v\ud800'
        for name in ('policy_version', 'level_version', 'ruleset_version'):
            self.assertEqual(refusal(call(sources=good_sources(**{name: surrogate}))),
                             ('argument', name + ' is not a non-empty text'), name)
        rules = [{'match': ['docs/**', 'a\ud800'], 'class': 'low'}]
        self.assertEqual(refusal(call(sources=good_sources(risk_rules=rules))),
                         ('risk_rules', 'a risk rule has a match that is not a non-empty list of non-empty texts'))
        self.assertEqual(refusal(call(contract=good_contract(traces_to=['SPEC-001', '\ud800']))),
                         ('argument', 'contract has no traces_to that is a non-empty list of non-empty texts'))
        self.assertEqual(refusal(call(recorder='r\ud800')), ('argument', 'recorder is not a non-empty text'))

    def test_level_and_ruleset_versions_are_non_empty_texts(self):
        # governor.py :191-:193 needs a non-empty text for each of the three versions.
        for name in ('level_version', 'ruleset_version'):
            self.assertEqual(call(sources=good_sources(**{name: 'v7'}))['values'][name], 'v7')
            for bad in ('', 5, ['v1'], True):
                self.assertEqual(refusal(call(sources=good_sources(**{name: bad}))),
                                 ('argument', name + ' is not a non-empty text'), (name, bad))

    def test_owner_kept_rules_form(self):
        detail = 'owner_kept_rules is not a list of dicts whose match is a non-empty list of non-empty texts'
        self.assertIsNone(call(sources=good_sources(owner_kept_rules=[]))['refusal'])
        for bad in ('x', {}, 5, [5], ['x'], [{'id': 'A'}], [{'match': []}], [{'match': 'a'}],
                    [{'match': ['a', '']}], [{'match': ['a']}, 3]):
            self.assertEqual(refusal(call(sources=good_sources(owner_kept_rules=bad))), ('argument', detail), bad)

    def test_evidence_comparison_form(self):
        detail = 'evidence_comparison is not a dict with exactly the key weakens and a bool value'
        for ok in ({'weakens': False}, {'weakens': True}):
            self.assertIsNone(call(sources=good_sources(evidence_comparison=ok))['refusal'], ok)
        for bad in ({}, {'weakens': 'no'}, {'weakens': 0}, {'weakens': None}, {'weakens': False, 'x': 1}, [], 'x', 3):
            self.assertEqual(refusal(call(sources=good_sources(evidence_comparison=bad))), ('argument', detail), bad)

    def test_auto_accept_form(self):
        detail = 'auto_accept is not a dict'
        self.assertIsNone(call(sources=good_sources(auto_accept={'low': True}))['refusal'])
        for bad in ([], 'x', 3, True):
            self.assertEqual(refusal(call(sources=good_sources(auto_accept=bad))), ('argument', detail), bad)

    def test_a_source_that_is_not_plain_data_is_refused(self):
        out = call(sources=good_sources(articles={'x'}))
        self.assertEqual(refusal(out), ('argument', 'a source or a plan entry is not plain data: not plain data'))
        out = call(sources=good_sources(articles=[{1: 'x'}]))
        self.assertEqual(refusal(out), ('argument', 'a source or a plan entry is not plain data: a key is not a text'))


class AC4ThePolicyPaths(unittest.TestCase):
    def test_each_of_the_four_policy_source_files_is_refused(self):
        for path in POLICY_PATHS:
            out = call(changed_paths=['src/x.py', path])
            self.assertEqual(refusal(out), ('policy_path', 'a changed path is a policy source: ' + path), path)

    def test_paths_that_only_contain_a_policy_path_or_differ_in_case_are_not_refused(self):
        for path in ('docs/pre-genesis/constitution.md.bak', 'other/docs/pre-genesis/constitution.md',
                     'DOCS/PRE-GENESIS/constitution.md', 'docs/specs/risk-rules-gov-aieos.md/x'):
            self.assertIsNone(call(changed_paths=['src/x.py', path])['refusal'], path)

    def test_the_policy_ref_is_carried_in_the_evidence(self):
        self.assertEqual(call()['evidence']['policy_ref'], POLICY_REF)
        self.assertEqual(call(policy_ref='c' * 40)['evidence']['policy_ref'], 'c' * 40)

    def test_the_policy_path_is_checked_before_the_gaps(self):
        out = call(changed_paths=[POLICY_PATHS[0]], sources=good_sources(delegation=None))
        self.assertEqual(refusal(out)[0], 'policy_path')


class AC5TheCiRecords(unittest.TestCase):
    def test_the_records_equal_what_ci_evidence_gives_and_g3_has_none(self):
        out = call()
        self.assertEqual(out['ci_records'], ci_records())
        self.assertEqual(sorted(r['gate'] for r in out['ci_records']), ['G0', 'G1', 'G2'])
        self.assertEqual(out['evidence']['ci']['head_sha'], COMMIT)
        self.assertEqual([r['run_id'] for r in out['evidence']['ci']['runs']], [100])

    def test_ci_evidence_is_called_once_with_a_fresh_copy_of_the_intent_versions(self):
        seen = []

        def capture(task_id, commit, contract_sha256, intent_versions, plan, changed_paths, runs, recorder):
            seen.append((intent_versions, plan, changed_paths))
            return {'records': [], 'uncovered': [], 'evidence': {'head_sha': commit}, 'refusal': None}

        s = good_sources()
        with mock.patch.object(eval_inputs.ci_evidence, 'ci_evidence', capture):
            out = call(sources=s)
        self.assertIsNone(out['refusal'])
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][0], {'SPEC-001': 'v2'})
        self.assertIsNot(seen[0][0], s['intent_versions'])
        self.assertEqual(seen[0][1], PLAN4)

    def test_a_refusal_of_ci_evidence_is_passed_on(self):
        cases = ((dict(changed_paths=['src/x.py', '.github/x']), 'path', 'a changed path is under .github: .github/x'),
                 (dict(runs=[]), 'run', 'no eligible run'),
                 (dict(runs=[run(log=MAIN_LOG)]), 'detect', 'the detect step says no task'))
        for changes, reason, detail in cases:
            out = call(**changes)
            self.assertEqual(refusal(out), ('ci', 'ci_evidence refused: %s: %s' % (reason, detail)), changes)
            self.assertEqual((out['declared'], out['values'], out['ci_records'], out['evidence']), (None, None, [], None))

    def test_the_uncovered_entries_are_carried_in_the_evidence_as_a_fresh_copy(self):
        out = call()
        self.assertEqual([(e['gate'], e['check']) for e in out['evidence']['uncovered']], [('G3', 'review')])
        given = [{'gate': 'G3', 'check': 'review', 'detail': 'not run by CI'}]

        def capture(task_id, commit, contract_sha256, intent_versions, plan, changed_paths, runs, recorder):
            return {'records': [], 'uncovered': given, 'evidence': {'head_sha': commit}, 'refusal': None}

        with mock.patch.object(eval_inputs.ci_evidence, 'ci_evidence', capture):
            out = call()
        self.assertEqual(out['evidence']['uncovered'], given)
        self.assertIsNot(out['evidence']['uncovered'], given)
        self.assertIsNot(out['evidence']['uncovered'][0], given[0])

    def test_an_intent_versions_that_ci_evidence_refuses_is_a_ci_refusal(self):
        out = call(sources=good_sources(intent_versions={'SPEC-001': 'two'}))
        self.assertEqual(refusal(out)[0], 'ci')


class AC6TheGuardAgainstTheLog(unittest.TestCase):
    def test_with_an_empty_log_every_record_is_to_append(self):
        out = call()
        self.assertEqual(out['ci_records'], ci_records())
        self.assertEqual(out['evidence']['already_in_log'], [])

    def test_a_payload_equal_to_a_record_is_not_returned_again(self):
        records = ci_records()
        out = call(log_payloads=[copy.deepcopy(records[0])])
        self.assertIsNone(out['refusal'])
        self.assertEqual(out['ci_records'], records[1:])
        self.assertEqual(out['evidence']['already_in_log'], [records[0]['record_id']])

    def test_every_record_in_the_log_gives_no_record_to_append(self):
        records = ci_records()
        out = call(log_payloads=copy.deepcopy(records))
        self.assertEqual(out['ci_records'], [])
        self.assertEqual(out['evidence']['already_in_log'], [r['record_id'] for r in records])

    def test_the_same_record_id_with_other_content_is_a_conflict(self):
        records = ci_records()
        other = copy.deepcopy(records[0])
        other['outcome'] = 'fail' if other['outcome'] == 'pass' else 'pass'
        out = call(log_payloads=[other])
        self.assertEqual(refusal(out), ('conflict', 'the log holds another record under the record_id ' + records[0]['record_id']))
        self.assertEqual((out['declared'], out['values'], out['ci_records'], out['evidence']), (None, None, [], None))

    def test_check_all_then_append_one_equal_and_one_differing_payload(self):
        records = ci_records()
        other = copy.deepcopy(records[1])
        other['recorder'] = 'another recorder'
        out = call(log_payloads=[copy.deepcopy(records[0]), other])
        self.assertEqual(refusal(out)[0], 'conflict')
        self.assertEqual(out['ci_records'], [])

    def test_the_module_appends_nothing_and_calls_no_writer(self):
        names = {n.id for n in ast.walk(ast.parse((ROOT / 'src/aieos_bootstrap/eval_inputs.py').read_text(encoding='utf-8')))
                 if isinstance(n, ast.Name)}
        self.assertFalse(names & {'writer', 'append_event', 'append'})

    def test_payloads_without_a_record_id_are_ignored(self):
        self.assertIsNone(call(log_payloads=[{'x': 1}])['refusal'])


class AC7TheResultAndTheCompleteness(unittest.TestCase):
    def test_the_declared_and_the_values_have_the_forms_of_evaluate_task(self):
        out = call()
        self.assertEqual(out['declared'], {'intent_versions': {'SPEC-001': 'v2'}, 'retries': 1})
        self.assertEqual(set(out['values']), governor.VALUE_KEYS)
        self.assertEqual(set(out['values']['contract']), governor.CONTRACT_KEYS)
        self.assertIs(out['values']['contract']['owner_kept_act'], False)
        self.assertEqual(out['values']['changed_paths'], ['src/x.py'])
        inp = governor.derive_inputs(copy.deepcopy(out['values']))
        self.assertEqual(inp['risk'], 'medium')
        self.assertEqual(set(out['evidence']), {'policy_ref', 'evaluated_commit', 'contract_sha256', 'ci', 'uncovered',
                                                 'already_in_log', 'gaps'})
        self.assertEqual(out['evidence']['gaps'], [])

    def test_the_owner_kept_act_text_true_gives_true(self):
        out = call(contract=good_contract(owner_kept_act='true'))
        self.assertIs(out['values']['contract']['owner_kept_act'], True)

    def test_a_risk_that_cannot_be_derived_is_incomplete(self):
        out = call(sources=good_sources(risk_rules=[{'match': ['docs/**'], 'class': 'low'}]))
        self.assertEqual(refusal(out), ('incomplete', 'governor.derive_inputs gives no decision: the risk cannot be derived; '
                                                      'the evidence profile cannot be derived'))

    def test_an_evidence_profile_that_cannot_be_derived_is_incomplete(self):
        out = call(sources=good_sources(default_profiles={}))
        self.assertEqual(refusal(out), ('incomplete', 'governor.derive_inputs gives no decision: the evidence profile cannot be derived'))

    def test_a_delegation_that_is_not_a_bool_is_incomplete(self):
        out = call(sources=good_sources(delegation='yes'))
        self.assertEqual(refusal(out), ('incomplete', 'governor.derive_inputs gives no decision: the delegation is not a bool'))

    def test_values_that_derive_inputs_refuses_are_incomplete(self):
        out = call(sources=good_sources(articles=[{'id': 'X'}]))
        self.assertEqual(refusal(out), ('incomplete', 'governor.derive_inputs refused the values: an article is not {id, scope, evidence_required}'))

    def test_no_argument_is_changed_and_nothing_returned_aliases_one(self):
        args = kw(log_payloads=[copy.deepcopy(ci_records()[0])])
        before = copy.deepcopy(args)
        out = eval_inputs.eval_inputs(**args)
        self.assertEqual(args, before)
        self.assertIsNone(out['refusal'])
        s = args['sources']
        self.assertIsNot(out['declared']['intent_versions'], s['intent_versions'])
        for name in ('owner_kept_rules', 'articles', 'default_profiles', 'requirement_profiles', 'evidence_comparison', 'auto_accept'):
            self.assertEqual(out['values'][name], s[name])
            self.assertIsNot(out['values'][name], s[name], name)
        self.assertIsNot(out['values']['articles'][0], s['articles'][0])
        self.assertIsNot(out['values']['articles'][0]['scope'], s['articles'][0]['scope'])
        self.assertIsNot(out['values']['changed_paths'], args['changed_paths'])
        self.assertIsNot(out['values']['contract']['traces_to'], args['contract']['traces_to'])
        for r in out['ci_records']:
            self.assertIsNot(r['intent_versions'], s['intent_versions'])

    def test_equal_arguments_give_equal_results(self):
        self.assertEqual(call(), call())
        self.assertEqual(call(sources=good_sources(delegation=None)), call(sources=good_sources(delegation=None)))


if __name__ == '__main__':
    unittest.main()

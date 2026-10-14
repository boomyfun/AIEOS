"""Unit tests of aieos_bootstrap.scope_drift (task TASK-033, its rules R1 to R9); every rule has at least one passing
case and one failing case. The tests write and remove no file, and open none except the module's own source, read for
R8's script checks (TASK-033 AC12). Each test names the criteria it stands for in its own docstring."""

import ast
import copy
import hashlib
import pathlib
import re
import unittest
from unittest import mock

from aieos_bootstrap import governor, records, scope_drift

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap' / 'scope_drift.py'
C = 'c' * 40
CONST = 'docs/pre-genesis/constitution.md'
POLICY = 'docs/specs/risk-rules-gov-aieos.md'
LIST = ['docs/History/**', 'docs/Progress/**', 'docs/Deferred/**', 'docs/Lessons/**']
# The policy v3 rules R1 to R11 in the governor's {match, class} form, R3 by point 3's fail-closed reading.
RULES = [
    {'match': ['docs/**', '*.md'], 'class': 'low'},
    {'match': ['src/**', 'tests/**'], 'class': 'medium'},
    {'match': ['src/**', 'tests/**'], 'class': 'high'},
    {'match': ['docs/plan/**', 'docs/WORKING-RECORDS.md', '.gitattributes', '.gitignore'], 'class': 'high'},
    {'match': ['migrations/**', 'contracts/**', '**/migrations/**', '**/contracts/**'], 'class': 'critical'},
    {'match': ['AIEOS-concept.md', CONST, 'docs/pre-genesis/CR-*.md', 'docs/specs/**'], 'class': 'critical'},
    {'match': ['docs/pre-genesis/**', 'docs/genesis/**'], 'class': 'critical'},
    {'match': ['docs/pre-genesis/measurement-protocol.md', 'docs/pre-genesis/measurements/**'], 'class': 'critical'},
    {'match': ['.github/**', '.claude/**', 'CLAUDE.md'], 'class': 'critical'},
    {'match': ['.aieos/**'], 'class': 'critical'},
    {'match': ['tests/conformance/**'], 'class': 'critical'},
]
EVALUATOR = ['.github/**', 'src/aieos_bootstrap/**', 'tests/conformance/**',
             'docs/pre-genesis/conformance-scenarios-initial.md', 'docs/records/**', 'tests/unit/**',
             'tests/integration/**', 'tests/property/**', 'tests/run_tests.py', '**/pyproject.toml', '**/setup.cfg',
             '**/setup.py', '**/requirements*.txt']
POLICY_TEXT = '\n'.join([
    '# The self-build\'s risk rules', '', '## 3. The rules', '', '```yaml', 'policy_version: v3',
    'non_task_paths: ["docs/History/**", "docs/Progress/**", "docs/Deferred/**", "docs/Lessons/**"]', 'risk_rules:',
    '  # R1, low: concept line 597.', '  - match: { paths: ["docs/**", "*.md"] }', '    risk: low', '```', '',
    '## 4. Why', ''])


def inputs(**over):
    """A well-formed input: a commit with no trailer whose only path is a session record (detected and exempt)."""
    base = {'commit': C, 'parents': 1, 'trailer_tasks': [], 'changed_paths': ['docs/History/2026-10/x.md'],
            'contracts': {}, 'non_task': list(LIST), 'risk_rules': copy.deepcopy(RULES),
            'evaluator': list(EVALUATOR), 'constitution_path': CONST, 'policy_path': POLICY}
    base.update(over)
    return base


def unc(res):
    return {(u['ref'], u['detail']) for u in res['uncovered']}


def digest(*parts):
    return hashlib.sha256('\n'.join(parts).encode('utf-8')).hexdigest()


def gov_class(path, rules=RULES):
    """The governor's own per-path class: derive_inputs with one changed path and a declared risk of low."""
    values = {'contract': {'traces_to': ['SPEC-004'], 'risk': 'low', 'owner_kept_act': False,
                           'verification_plan': ['G0']},
              'changed_paths': [path], 'risk_rules': copy.deepcopy(rules), 'owner_kept_rules': [], 'articles': [],
              'default_profiles': {}, 'requirement_profiles': [], 'delegation': True,
              'evidence_comparison': {'weakens': False}, 'auto_accept': {}, 'policy_version': 'v3',
              'level_version': 'v1', 'ruleset_version': 'v1'}
    return governor.derive_inputs(values)['risk']


class InputForm(unittest.TestCase):
    """R1."""

    def test_well_formed_has_no_error(self):
        """TASK-033 AC1 and TASK-033 AC13: a well-formed input gives error None, with a 40- and a 64-character commit
        and with non_task None."""
        for c in (C, 'd' * 64):
            self.assertIsNone(scope_drift.claims(inputs(commit=c))['error'])
        self.assertIsNone(scope_drift.claims(inputs(non_task=None))['error'])

    def test_each_malformed_form_names_its_key(self):
        """TASK-033 AC1 and TASK-033 AC13: each malformed value gives an error naming its key, no event, detected and
        exempt false and no uncovered entry."""
        bad = [('commit', 'C' * 40), ('commit', 'a' * 39), ('parents', True), ('parents', -1), ('parents', 1.0),
               ('trailer_tasks', ['task-1']), ('trailer_tasks', 'TASK-1'), ('changed_paths', []),
               ('changed_paths', ['']), ('contracts', []), ('non_task', 'docs/**'), ('non_task', [1]),
               ('risk_rules', {}), ('evaluator', None), ('evaluator', [2]), ('constitution_path', ''),
               ('policy_path', None)]
        for key, value in bad:
            res = scope_drift.claims(inputs(**{key: value}))
            self.assertTrue(res['error'] and res['error'].startswith(key), (key, value, res))
            self.assertEqual((res['events'], res['detected'], res['exempt'], res['uncovered']), ([], False, False, []))

    def test_missing_unknown_and_not_a_mapping(self):
        """TASK-033 AC1 and TASK-033 AC13: a missing key, an unknown key and a non-mapping are errors."""
        i = inputs()
        del i['evaluator']
        self.assertEqual(scope_drift.claims(i)['error'], 'inputs lacks evaluator')
        self.assertEqual(scope_drift.claims(inputs(extra=1))['error'], 'inputs has an unknown key: extra')
        self.assertEqual(scope_drift.claims([])['error'], 'inputs is not a mapping')

    def test_first_failing_key_in_order(self):
        """TASK-033 AC1 and TASK-033 AC13: with several malformed keys, the first in AC1's order is named."""
        self.assertTrue(scope_drift.claims(inputs(parents=-1, policy_path=''))['error'].startswith('parents'))


class TheList(unittest.TestCase):
    """R2."""

    def test_the_list_is_read(self):
        """TASK-033 AC2 and TASK-033 AC13: the policy text's line gives its four patterns in order."""
        self.assertEqual(scope_drift.non_task_list(POLICY_TEXT), LIST)

    def test_each_case_gives_none(self):
        """TASK-033 AC2 and TASK-033 AC13: no block, no line, two lines, the line before policy_version, an item with
        a quote, comma or bracket, an item out of point 6's form, an empty list, a line with another spacing, and a
        text that is not a string each give None."""
        line = 'non_task_paths: ["docs/History/**", "docs/Progress/**", "docs/Deferred/**", "docs/Lessons/**"]'
        cases = [
            POLICY_TEXT.replace('## 3. The rules', '## 3. Rules'),
            POLICY_TEXT.replace('```yaml', '```'),
            POLICY_TEXT.replace(line + '\n', ''),
            POLICY_TEXT.replace(line, line + '\n' + line),
            POLICY_TEXT.replace('policy_version: v3\n' + line, line + '\npolicy_version: v3'),
            POLICY_TEXT.replace('"docs/Lessons/**"', '"docs/Les\\"sons/**"'),
            POLICY_TEXT.replace('"docs/Lessons/**"', '"docs/Lessons,x/**"'),
            POLICY_TEXT.replace('"docs/Lessons/**"', '"docs/Les]sons/**"'),
            POLICY_TEXT.replace('"docs/Lessons/**"', '"docs/Lessons/a**"'),
            POLICY_TEXT.replace('"docs/Lessons/**"', '"docs/../x"'),
            POLICY_TEXT.replace('"docs/Lessons/**"', '"docs//x"'),
            POLICY_TEXT.replace(line, 'non_task_paths: []'),
            POLICY_TEXT.replace(line, line.replace(', ', ',')),
            POLICY_TEXT.replace(line, line + ' '),
            POLICY_TEXT.replace(line + '\n', '').replace('## 4. Why', '```yaml\n' + line + '\n```\n## 4. Why'),
            POLICY_TEXT.replace(line + '\nrisk_rules:', 'risk_rules:').replace('```\n', '```\n' + line + '\n', 1),
            POLICY_TEXT.split('```\n')[0],
        ]
        for text in cases:
            self.assertIsNone(scope_drift.non_task_list(text), text)
        for text in (None, b'x', 3):
            self.assertIsNone(scope_drift.non_task_list(text))

    def test_no_exception_escapes(self):
        """TASK-033 AC2 and TASK-033 AC8 and TASK-033 AC13: an exception inside the reading gives None."""
        with mock.patch.object(scope_drift, '_list_from', side_effect=RuntimeError('x')):
            self.assertIsNone(scope_drift.non_task_list(POLICY_TEXT))


class Detection(unittest.TestCase):
    """R3."""

    def test_no_trailer_is_detected(self):
        """TASK-033 AC3 and TASK-033 AC13: a commit with no trailer task on a source path is detected and a claim."""
        res = scope_drift.claims(inputs(changed_paths=['src/x.py']))
        self.assertTrue(res['detected'])
        self.assertEqual(len(res['events']), 1)

    def test_a_trailer_whose_contract_holds_every_path_is_not_detected(self):
        """TASK-033 AC3 and TASK-033 AC5 and TASK-033 AC13: a task commit on evaluator paths that its contract holds is
        not detected, so no event, though its paths are evaluator paths."""
        res = scope_drift.claims(inputs(trailer_tasks=['TASK-033'], changed_paths=['src/aieos_bootstrap/x.py',
                                                                                    'tests/unit/test_x.py'],
                                        contracts={'TASK-033': ['src/aieos_bootstrap/x.py', 'tests/unit/**']}))
        self.assertEqual((res['detected'], res['exempt'], res['events'], res['uncovered']), (False, False, [], []))

    def test_a_path_outside_the_write_set_is_detected(self):
        """TASK-033 AC3 and TASK-033 AC13: one path outside the contract's write-set makes the commit detected."""
        res = scope_drift.claims(inputs(trailer_tasks=['TASK-033'], changed_paths=['src/aieos_bootstrap/x.py',
                                                                                    'src/aieos_bootstrap/y.py'],
                                        contracts={'TASK-033': ['src/aieos_bootstrap/x.py']}))
        self.assertTrue(res['detected'])
        self.assertEqual(res['events'][0]['payload']['paths'], ['src/aieos_bootstrap/x.py', 'src/aieos_bootstrap/y.py'])

    def test_uncovered_detection_cases(self):
        """TASK-033 AC3 and TASK-033 AC13: several trailers, no contract and a write set that cannot be evaluated each
        make the commit detected and are named."""
        cases = [
            (inputs(trailer_tasks=['TASK-1', 'TASK-2'], contracts={'TASK-1': ['**'], 'TASK-2': ['**']}),
             (C, 'several trailers')),
            (inputs(trailer_tasks=['TASK-1']), ('TASK-1', 'no contract')),
            (inputs(trailer_tasks=['TASK-1'], contracts={'TASK-1': []}), ('TASK-1', 'write set cannot be evaluated')),
            (inputs(trailer_tasks=['TASK-1'], contracts={'TASK-1': ['a/**b']}),
             ('TASK-1', 'write set cannot be evaluated')),
            (inputs(trailer_tasks=['TASK-1'], contracts={'TASK-1': 'src/**'}),
             ('TASK-1', 'write set cannot be evaluated')),
        ]
        for i, want in cases:
            res = scope_drift.claims(i)
            self.assertTrue(res['detected'], i)
            self.assertEqual(unc(res), {want})

    def test_equal_trailers_count_as_one(self):
        """TASK-033 AC3 and TASK-033 AC13: the same trailer task twice is one trailer task."""
        res = scope_drift.claims(inputs(trailer_tasks=['TASK-1', 'TASK-1'], changed_paths=['src/x.py'],
                                        contracts={'TASK-1': ['src/**']}))
        self.assertEqual((res['detected'], res['uncovered']), (False, []))

    def test_not_one_parent_is_uncovered_with_no_event(self):
        """TASK-033 AC3 and TASK-033 AC13: parents 0 and 2 give no event and an uncovered entry; parents 1 does not."""
        for p in (0, 2, 3):
            res = scope_drift.claims(inputs(parents=p, changed_paths=['src/x.py']))
            self.assertEqual((res['events'], res['detected'], res['exempt']), ([], False, False))
            self.assertEqual(res['uncovered'], [{'ref': C, 'detail': 'not one parent'}])
        self.assertEqual(scope_drift.claims(inputs(changed_paths=['src/x.py']))['uncovered'], [])

    def test_matching_is_the_governors(self):
        """TASK-033 AC3 and TASK-033 AC4 and TASK-033 AC13: governor.matches is the function called."""
        with mock.patch.object(governor, 'matches', wraps=governor.matches) as m:
            scope_drift.claims(inputs(trailer_tasks=['TASK-1'], contracts={'TASK-1': ['src/**']},
                                      changed_paths=['src/x.py', 'docs/History/a.md']))
            self.assertTrue(m.called)
        with mock.patch.object(governor, 'matches', return_value=True):
            res = scope_drift.claims(inputs(trailer_tasks=['TASK-1'], contracts={'TASK-1': ['nothing/**']},
                                            changed_paths=['src/x.py']))
        self.assertEqual((res['detected'], res['events']), (False, []))


class NonTask(unittest.TestCase):
    """R4."""

    def test_a_record_path_is_exempt(self):
        """TASK-033 AC4 and TASK-033 AC5 and TASK-033 AC13: all four conditions hold for the four record folders."""
        res = scope_drift.claims(inputs(changed_paths=['docs/History/2026-10/x.md', 'docs/Progress/2026-10.md',
                                                       'docs/Deferred/DEF-0001-x.md', 'docs/Lessons/L-0001-x.md']))
        self.assertEqual((res['detected'], res['exempt'], res['events']), (True, True, []))

    def test_each_condition_failing_alone(self):
        """TASK-033 AC4 and TASK-033 AC13: (1) a path not on the list; (2) a path on the list above low (R5's
        **/contracts/**); (3) a path on the list that an evaluator pattern matches (a build-file name); (4) the
        constitution, the policy and .github/ named as such: each is not non-task."""
        cases = [('docs/plan/x.md', None),
                 ('docs/Deferred/contracts/x.md', None),
                 ('docs/Lessons/pyproject.toml', None),
                 ('docs/History/c.md', {'constitution_path': 'docs/History/c.md'}),
                 ('docs/History/p.md', {'policy_path': 'docs/History/p.md'})]
        for path, over in cases:
            res = scope_drift.claims(inputs(changed_paths=[path], **(over or {})))
            self.assertEqual((res['exempt'], len(res['events'])), (False, 1), path)
            self.assertEqual(res['events'][0]['payload']['paths'], [path])
        gh = scope_drift.claims(inputs(changed_paths=['.github/x.md'], non_task=['.github/**'],
                                       risk_rules=[{'match': ['**'], 'class': 'low'}], evaluator=['src/**']))
        self.assertEqual((gh['exempt'], gh['events'][0]['payload']['paths']), (False, ['.github/x.md']))
        ok = scope_drift.claims(inputs(changed_paths=['other/x.md'], non_task=['other/**'],
                                       risk_rules=[{'match': ['**'], 'class': 'low'}], evaluator=['src/**']))
        self.assertTrue(ok['exempt'])

    def test_only_exactly_low_is_non_task(self):
        """TASK-033 AC4 and TASK-033 AC13: a listed path of class medium, of class high, or of no class (no rule
        matches it) is not non-task; the same path of class low is."""
        for rules in ([{'match': ['other/**'], 'class': 'medium'}], [{'match': ['other/**'], 'class': 'high'}],
                      [{'match': ['src/**'], 'class': 'low'}]):
            res = scope_drift.claims(inputs(changed_paths=['other/x.md'], non_task=['other/**'], risk_rules=rules,
                                            evaluator=['src/**']))
            self.assertEqual((res['exempt'], res['events'][0]['payload']['paths']), (False, ['other/x.md']), rules)
        low = scope_drift.claims(inputs(changed_paths=['other/x.md'], non_task=['other/**'],
                                        risk_rules=[{'match': ['other/**'], 'class': 'low'}], evaluator=['src/**']))
        self.assertTrue(low['exempt'])

    def test_out_of_form_inputs_make_no_path_non_task(self):
        """TASK-033 AC4 and TASK-033 AC13: no list, a list item out of form, a rule out of form (an extra key, a bad
        class, an empty match), an empty or malformed evaluator list: no path is non-task."""
        bad_rules = [RULES + [{'match': ['x/**'], 'class': 'low', 'id': 'R12'}], RULES + [{'match': ['x/**'],
                                                                                          'class': 'none'}],
                     RULES + [{'match': [], 'class': 'low'}], RULES + ['R12']]
        cases = [{'non_task': None}, {'non_task': ['docs/History/**', 'docs/**x']}, {'evaluator': []},
                 {'evaluator': ['**/a**']}] + [{'risk_rules': r} for r in bad_rules]
        for over in cases:
            res = scope_drift.claims(inputs(**over))
            self.assertEqual((res['detected'], res['exempt'], len(res['events'])), (True, False, 1), over)
            self.assertEqual(res['events'][0]['payload']['paths'], ['docs/History/2026-10/x.md'])

    def test_the_class_equals_the_governors(self):
        """TASK-033 AC4 and TASK-033 AC13: the class function equals governor.derive_inputs's per-path class on the
        policy's rules, for paths that hit each rule and a path no rule matches; and on rules with an unevaluable match
        or an unreadable class."""
        paths = ['docs/History/x.md', 'README.md', 'src/x.py', 'tests/y.py', 'docs/plan/master-plan.md',
                 'docs/WORKING-RECORDS.md', '.gitignore', 'a/migrations/x', 'docs/Deferred/contracts/x.md',
                 'AIEOS-concept.md', CONST, 'docs/pre-genesis/CR-002.md', 'docs/specs/x.md', 'docs/genesis/x.md',
                 'docs/pre-genesis/measurements/x', '.github/workflows/x.yml', '.claude/x', 'CLAUDE.md', '.aieos/x',
                 'tests/conformance/set.py', 'other/file.txt']
        for path in paths:
            self.assertEqual(scope_drift._path_class(RULES, path), gov_class(path), path)
        self.assertIsNone(scope_drift._path_class(RULES, 'other/file.txt'))
        odd = [{'match': ['docs/**'], 'class': 'low'}, {'match': 'x', 'class': 'medium'},
               {'match': ['src/**'], 'class': 'unknown'}]
        for path in ('docs/a.md', 'src/b.py', 'z'):
            self.assertEqual(scope_drift._path_class(odd, path), gov_class(path, odd), path)
        surrogate = [{'match': ['docs/**'], 'class': 'low'}, {'match': ['\ud800/**'], 'class': 'high'}]
        for path in ('docs/a.md', 'z'):
            self.assertEqual(scope_drift._path_class(surrogate, path), gov_class(path, surrogate), path)
        self.assertEqual(scope_drift._path_class(surrogate, 'docs/a.md'), 'high')
        self.assertTrue(scope_drift.claims(inputs(changed_paths=['docs/History/\ud800.md']))['error'])


class ClaimOrExempt(unittest.TestCase):
    """R5."""

    def test_exempt_and_claim(self):
        """TASK-033 AC5 and TASK-033 AC13: every path non-task gives exempt; one other path gives a claim."""
        self.assertTrue(scope_drift.claims(inputs())['exempt'])
        res = scope_drift.claims(inputs(changed_paths=['docs/History/a.md', 'docs/specs/x.md']))
        self.assertEqual((res['exempt'], res['events'][0]['payload']['paths']), (False, ['docs/specs/x.md']))

    def test_always_claim_kinds_on_a_detected_commit(self):
        """TASK-033 AC5 and TASK-033 AC13: a detected commit touching the constitution, the policy, .github/ or an
        evaluator path is a claim, with a record path beside it."""
        for path in (CONST, POLICY, '.github/workflows/aieos-checks.yml', 'docs/records/TASK-001.jsonl'):
            res = scope_drift.claims(inputs(changed_paths=['docs/History/a.md', path]))
            self.assertEqual((res['detected'], res['exempt']), (True, False), path)
            self.assertEqual(res['events'][0]['payload']['paths'], [path])


class TheEvent(unittest.TestCase):
    """R6."""

    def test_payload_and_id(self):
        """TASK-033 AC6 and TASK-033 AC13: the payload's keys and values, sorted and without duplicates; the id's
        value; check_payload finds nothing; no task_id."""
        res = scope_drift.claims(inputs(trailer_tasks=['TASK-9', 'TASK-9'], contracts={'TASK-9': ['src/a.py']},
                                        changed_paths=['src/b.py', 'src/a.py', 'src/b.py', 'docs/History/x.md']))
        e = res['events'][0]
        self.assertEqual(set(e), {'event_id', 'event_type', 'payload'})
        self.assertEqual(e['event_type'], 'drift.detected')
        self.assertEqual(e['payload'], {'paths': ['src/a.py', 'src/b.py'], 'entities': ['TASK-9']})
        self.assertEqual(e['event_id'], digest('drift.detected', 'scope', C))
        self.assertEqual(records.check_payload('drift.detected', e['payload']), [])

    def test_the_id_depends_on_the_commit_only(self):
        """TASK-033 AC6 and TASK-033 AC13: a second call gives the same id; other paths and trailers give the same id;
        another commit gives another id."""
        a = scope_drift.claims(inputs(changed_paths=['src/x.py']))['events'][0]['event_id']
        b = scope_drift.claims(inputs(changed_paths=['src/x.py']))['events'][0]['event_id']
        c = scope_drift.claims(inputs(changed_paths=['src/y.py'], trailer_tasks=['TASK-2'],
                                      contracts={'TASK-2': ['a/**']}))['events'][0]['event_id']
        d = scope_drift.claims(inputs(commit='e' * 40, changed_paths=['src/x.py']))['events'][0]['event_id']
        self.assertEqual(a, b)
        self.assertEqual(a, c)
        self.assertNotEqual(a, d)

    def test_a_payload_the_checker_refuses_gives_an_error(self):
        """TASK-033 AC6 and TASK-033 AC8 and TASK-033 AC13: when check_payload finds something, no event is given."""
        with mock.patch.object(records, 'check_payload', return_value=['x']):
            res = scope_drift.claims(inputs(changed_paths=['src/x.py']))
        self.assertEqual((res['events'], res['detected'], res['exempt'], res['uncovered']), ([], False, False, []))
        self.assertTrue(res['error'])


class Result(unittest.TestCase):
    """R7."""

    def test_keys_and_sorting(self):
        """TASK-033 AC8 and TASK-033 AC13: exactly the five keys; uncovered sorted without duplicates; exempt only when
        detected."""
        for i in (inputs(), inputs(changed_paths=['src/x.py']), inputs(parents=2), inputs(commit='x')):
            res = scope_drift.claims(i)
            self.assertEqual(set(res), set(scope_drift.RESULT_KEYS))
            self.assertFalse(res['exempt'] and not res['detected'])
            self.assertEqual(res['uncovered'], sorted(res['uncovered'], key=lambda u: (u['ref'], u['detail'])))

    def test_pure(self):
        """TASK-033 AC8 and TASK-033 AC13: the input is not changed and a second call is equal."""
        i = inputs(changed_paths=['src/x.py', 'docs/History/a.md'], trailer_tasks=['TASK-1'],
                   contracts={'TASK-1': ['x/**']})
        before = copy.deepcopy(i)
        first = scope_drift.claims(i)
        self.assertEqual(i, before)
        self.assertEqual(scope_drift.claims(i), first)
        self.assertEqual(scope_drift.non_task_list(POLICY_TEXT), scope_drift.non_task_list(POLICY_TEXT))

    def test_no_exception_escapes(self):
        """TASK-033 AC8 and TASK-033 AC13: an exception inside the computation becomes an error result."""
        with mock.patch.object(governor, 'matches', side_effect=RecursionError('deep')):
            res = scope_drift.claims(inputs(trailer_tasks=['TASK-1'], contracts={'TASK-1': ['src/**']},
                                            changed_paths=['src/x.py']))
        self.assertEqual((res['events'], res['detected'], res['exempt'], res['uncovered']), ([], False, False, []))
        self.assertEqual(res['error'], 'an exception: RecursionError')


class Purity(unittest.TestCase):
    """R8."""

    def test_imports(self):
        """TASK-033 AC9 and TASK-033 AC13: the module imports only hashlib, re, aieos_bootstrap.governor and
        aieos_bootstrap.records."""
        tree = ast.parse(SRC.read_bytes().decode('utf-8'))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.update('%s.%s' % (node.module, a.name) for a in node.names)
        self.assertEqual(names, {'hashlib', 're', 'aieos_bootstrap.governor', 'aieos_bootstrap.records'})

    def test_no_file_clock_or_dynamic_calls(self):
        """TASK-033 AC7 and TASK-033 AC9 and TASK-033 AC13: no open, write, clock, environment, exec, eval, compile,
        __import__ or assert; a seeded call is found by the same check."""
        text = SRC.read_bytes().decode('utf-8')

        def found(source):
            tree = ast.parse(source)
            called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
            attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
            return (called & {'open', 'exec', 'eval', 'compile', '__import__'}
                    or attrs & {'write', 'write_text', 'write_bytes', 'time', 'now', 'environ', 'getenv', 'system'}
                    or [n for n in ast.walk(tree) if isinstance(n, ast.Assert)])

        self.assertFalse(found(text))
        self.assertTrue(found(text + '\nopen("x")\n'))
        self.assertNotIn('importlib', text)
        self.assertNotIn('.aieos', text)

    def test_docstring_states_r1_and_the_caller(self):
        """TASK-033 AC5 and TASK-033 AC7 and TASK-033 AC11 and TASK-033 AC13: the docstring states R1 as a reading,
        names the caller TASK-034, and says that nothing is appended or classified."""
        doc = ' '.join(ast.get_docstring(ast.parse(SRC.read_bytes().decode('utf-8'))).split())
        for s in ('reading R1, proposed, decision D-702', 'not as the specification\'s own words', 'TASK-034',
                  'appends nothing', 'classifies and proposes nothing', 'not checked against Git'):
            self.assertIn(s, doc)


class Naming(unittest.TestCase):
    """R9."""

    def test_every_test_names_its_criteria(self):
        """TASK-033 AC12 and TASK-033 AC13: every test method of this module's test classes names "TASK-033 AC" in its
        docstring and no other task's criterion in qualified form (read from the loaded objects, no file opened)."""
        seen = 0
        for cls in list(globals().values()):
            if not (isinstance(cls, type) and issubclass(cls, unittest.TestCase)):
                continue
            for name, fn in vars(cls).items():
                if name.startswith('test_'):
                    seen += 1
                    doc = fn.__doc__ or ''
                    self.assertIn('TASK-033 AC', doc, name)
                    self.assertEqual([t for t in re.findall(r'TASK-(\d+) AC', doc) if t != '033'], [], name)
        self.assertGreater(seen, 20)


if __name__ == '__main__':
    unittest.main()

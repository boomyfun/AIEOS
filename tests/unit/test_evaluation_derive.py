"""Unit tests of the pure derivations of the evaluation sources (TASK-157, BT3b-2b; AC2 to AC5). Every case is built in memory;
the files read are the module's own source and the governor's source (to compute a real hash). The tests are exempt from the
rule that no string constant of src/ names the project-state directory, and name it on purpose."""
import ast
import hashlib
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import evaluation_derive
from aieos_bootstrap import evaluation_policy

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE = ROOT / 'src/aieos_bootstrap/evaluation_derive.py'
TRUE = {'weakens': True}
FALSE = {'weakens': False}
UNRELATED = ['docs/runs/x.md', 'README.md']
ENTRIES = list(evaluation_policy.EVIDENCE_DEFINING_PATHS)
CASE_ROWS = ['SRC/AIEOS_BOOTSTRAP/GOVERNOR.PY', 'docs/Pre-Genesis/constitution.md']
DOT_ROWS = ['.aieos/intent/requirements/x.md', '.aieos/intent', '.aieos', '.AIEOS/Intent/x', '.aieos/project.yaml',
            '.aieos/tasks/TASK-1.yaml', '.github/workflows/x.yml', '.gitignore']
MALFORMED_ROWS = ['docs\\x.md', './docs/x.md', '/docs/x.md', 'docs/../x.md', 'docs/./x.md', 'docs//x.md', 'docs/x/', 'docs/x\x00.md',
                  'docs/x\x7f.md', ' docs/x.md', 'docs/x.md ', 'docs/ x.md', 'docs/x /y.md', 'C:/x.md', 'docs/x.', 'docs/x ',
                  'docs/\u00e9.md', 'docs/PROGRA~1/x.md', 'docs/x:y.md', 'docs/x\t.md', 'docs/x\n.md', 'docs/x\t']
ORDINARY_ROWS = ['docs/runs/x.md', 'src/aieos_bootstrap/cli.py', 'tests/unit/test_x.py', 'README.md']


def _ref_malformed(path):
    """A hand-written reference of the malformed check, for the table-adequacy test (no refused name is used)."""
    segs = path.split('/')
    if '\\' in path or ':' in path or path.startswith('/') or path.endswith('/') or any(s in ('', '.', '..') for s in segs):
        return True
    if any(ord(c) < 32 or ord(c) >= 127 for c in path):
        return True
    return any(s != s.strip() or s.endswith('.') or '~' in s for s in segs)


def _ref(paths, dot_first=True, fold=True, malformed=True):
    if type(paths) is not list:
        return dict(TRUE)
    listed = [e.casefold() if fold else e for e in evaluation_policy.EVIDENCE_DEFINING_PATHS]
    for p in paths:
        if type(p) is not str or p == '' or (malformed and _ref_malformed(p)):
            return dict(TRUE)
        if (p.casefold() if fold else p) in listed or (dot_first and p.split('/')[0].startswith('.')):
            return dict(TRUE)
    return dict(FALSE)


def ref_without_rule_f(paths):
    return _ref(paths, dot_first=False)


def ref_without_casefold(paths):
    return _ref(paths, fold=False)


def ref_without_malformed_check(paths):
    return _ref(paths, malformed=False)


class AC2RulesetAndLevel(unittest.TestCase):
    def test_the_exact_texts(self):
        data = b'governor bytes'
        digest = hashlib.sha256(data).hexdigest()
        out = evaluation_derive.ruleset_version(data, digest)
        self.assertEqual(out, {'value': 'governor-sha256:' + digest, 'findings': []})
        self.assertEqual(len(out['value']), len('governor-sha256:') + 64)
        self.assertEqual(evaluation_derive.level_version('v5'), {'value': 'L1:v5', 'findings': []})

    def test_a_different_hash_is_refused(self):
        out = evaluation_derive.ruleset_version(b'a', hashlib.sha256(b'b').hexdigest())
        self.assertIsNone(out['value'])
        self.assertEqual(len(out['findings']), 1)
        self.assertLessEqual(len(out['findings'][0]['detail']), 40)

    def test_wrong_forms_are_refused_and_nothing_raises(self):
        good = hashlib.sha256(b'a').hexdigest()
        for gb, pin in ((None, good), ('a', good), (bytearray(b'a'), good), (b'a', None), (b'a', good.upper()), (b'a', good[:63]),
                        (b'a', good + '0'), (b'a', 7), (b'a', 'g' * 64), ([], {}), (object(), object()), (b'a', 'a' * 100000), ('x' * 100000, good)):
            out = evaluation_derive.ruleset_version(gb, pin)
            self.assertIsNone(out['value'])
            self.assertEqual(len(out['findings']), 1)
        for pv in (None, '', 5, b'v5', ['v5'], object()):
            out = evaluation_derive.level_version(pv)
            self.assertIsNone(out['value'])
            self.assertEqual(len(out['findings']), 1)
        self.assertEqual(evaluation_derive.level_version('x' * 100000)['value'], 'L1:' + 'x' * 100000)

    def test_the_real_governor_hash_is_accepted_as_the_pin(self):
        raw = (ROOT / 'src/aieos_bootstrap/governor.py').read_bytes()
        out = evaluation_derive.ruleset_version(raw, hashlib.sha256(raw).hexdigest())
        self.assertEqual(out['findings'], [])
        self.assertTrue(out['value'].startswith('governor-sha256:'))


class AC3EvidenceComparison(unittest.TestCase):
    def check(self, paths, want):
        self.assertEqual(evaluation_derive.evidence_comparison(paths), want, paths)

    def test_every_entry_alone_and_mixed(self):
        for entry in ENTRIES:
            self.check([entry], TRUE)
            self.check(UNRELATED + [entry], TRUE)
            self.check([entry] + UNRELATED, TRUE)

    def test_the_case_rows(self):
        for row in CASE_ROWS:
            self.check([row], TRUE)
            self.check(UNRELATED + [row], TRUE)

    def test_the_dot_first_rows(self):
        for row in DOT_ROWS:
            self.check([row], TRUE)
            self.check(UNRELATED + [row], TRUE)

    def test_each_malformed_row(self):
        for row in MALFORMED_ROWS:
            self.check([row], TRUE)
            self.check(UNRELATED + [row], TRUE)

    def test_not_a_list_of_texts(self):
        class Sub(list):
            pass
        for bad in (None, 'docs/runs/x.md', ('docs/runs/x.md',), {'docs/runs/x.md'}, 5, Sub(['docs/runs/x.md'])):
            self.check(bad, TRUE)
        for bad in ([''], [None], [1], [b'docs/x.md'], ['docs/runs/x.md', ''], ['docs/runs/x.md', None]):
            self.check(bad, TRUE)

    def test_ordinary_paths_and_the_empty_list(self):
        for row in ORDINARY_ROWS:
            self.check([row], FALSE)
        self.check(ORDINARY_ROWS, FALSE)
        self.check([], FALSE)

    def test_a_nested_dot_directory_is_not_dot_first(self):
        self.check(['docs/.hidden/x.md'], FALSE)
        self.check(['docs/.aieos/x'], FALSE)

    def test_the_function_reads_the_tuple_by_name(self):
        extra = 'zz/extra-evidence.md'
        self.check([extra], FALSE)
        with mock.patch.object(evaluation_policy, 'EVIDENCE_DEFINING_PATHS', evaluation_policy.EVIDENCE_DEFINING_PATHS + (extra,)):
            self.check([extra], TRUE)
        self.check([extra], FALSE)

    def test_the_result_is_always_the_bare_mapping(self):
        for paths in (None, [], ['docs/runs/x.md'], ENTRIES, MALFORMED_ROWS):
            out = evaluation_derive.evidence_comparison(paths)
            self.assertEqual(set(out), {'weakens'})
            self.assertIs(type(out['weakens']), bool)

    def test_the_table_rejects_each_weaker_reference_implementation(self):
        rows = [[p] for p in ENTRIES + CASE_ROWS + DOT_ROWS + MALFORMED_ROWS + ORDINARY_ROWS] + [[], UNRELATED]
        for ref, label in ((ref_without_rule_f, 'rule (f)'), (ref_without_casefold, 'casefold'), (ref_without_malformed_check, 'malformed check')):
            caught = [r for r in rows if ref(r) == FALSE and evaluation_derive.evidence_comparison(r) == TRUE]
            self.assertTrue(caught, 'no row of the table rejects the reference without ' + label)
        self.assertIn(['.aieos/intent'], [r for r in rows if ref_without_rule_f(r) == FALSE and evaluation_derive.evidence_comparison(r) == TRUE])
        self.assertIn(['SRC/AIEOS_BOOTSTRAP/GOVERNOR.PY'], [r for r in rows if ref_without_casefold(r) == FALSE and evaluation_derive.evidence_comparison(r) == TRUE])
        self.assertIn(['docs\\x.md'], [r for r in rows if ref_without_malformed_check(r) == FALSE and evaluation_derive.evidence_comparison(r) == TRUE])
        for r in rows:
            self.assertEqual(_ref(r), evaluation_derive.evidence_comparison(r), r)


class AC4PlainDataAndPurity(unittest.TestCase):
    def problem(self, value):
        return evaluation_derive.plain_data_problem(value)

    def test_plain_data_is_accepted(self):
        for v in (None, True, False, 0, -3, 2 ** 80, 1.5, 'text', '', [], {}, {'a': [1, 2.5, {'b': None}]}, [[[]]], {'k': 'v'}):
            self.assertIsNone(self.problem(v), v)

    def test_non_finite_numbers_anywhere_are_refused(self):
        for bad in (float('nan'), float('inf'), -float('inf')):
            for v in (bad, [bad], {'a': {'b': [bad]}}):
                self.assertIsNotNone(self.problem(v), v)

    def test_wrong_types_are_refused(self):
        class DictSub(dict):
            pass

        class StrSub(str):
            pass

        class IntSub(int):
            pass
        for v in ((1,), b'x', bytearray(b'x'), {1}, frozenset([1]), object(), DictSub(), StrSub('x'), IntSub(1), 1 + 2j, range(3)):
            self.assertIsNotNone(self.problem(v), v)
            self.assertIsNotNone(self.problem([v]), v)
        self.assertIsNotNone(self.problem({'a': StrSub('x')}))
        self.assertIsNotNone(self.problem({StrSub('k'): 1}))
        self.assertIsNotNone(self.problem({1: 'a'}))
        self.assertIsNotNone(self.problem({None: 'a'}))

    def test_bool_is_accepted_and_an_int_subclass_is_refused(self):
        class IntSub(int):
            pass
        self.assertIsNone(self.problem(True))
        self.assertIsNone(self.problem(False))
        self.assertIsNone(self.problem([True, False]))
        self.assertIsNotNone(self.problem(IntSub(1)))

    def test_depth_boundary(self):
        def nest(levels):
            v = []
            for _ in range(levels - 1):
                v = [v]
            return v
        self.assertIsNone(self.problem(nest(50)))
        self.assertIsNotNone(self.problem(nest(51)))
        leaf = 7
        for _ in range(50):
            leaf = [leaf]
        self.assertIsNone(self.problem(leaf))
        self.assertIsNotNone(self.problem([leaf]))
        d = {}
        for _ in range(49):
            d = {'k': d}
        self.assertIsNone(self.problem(d))
        self.assertIsNotNone(self.problem({'k': d}))
        cyc = []
        cyc.append(cyc)
        self.assertIsNotNone(self.problem(cyc))

    def test_every_detail_has_at_most_40_characters(self):
        for v in (float('nan'), (1,), {1: 2}, self._deep()):
            out = self.problem(v)
            self.assertIsNotNone(out)
            self.assertEqual(set(out), {'reason', 'detail'})
            self.assertLessEqual(len(out['detail']), 40)

    def test_a_longer_detail_is_cut_to_40_characters(self):
        self.assertEqual(evaluation_derive._finding('r', 'x' * 100), {'reason': 'r', 'detail': 'x' * 40})
        self.assertEqual(evaluation_derive._refused('r', 'y' * 100)['findings'][0]['detail'], 'y' * 40)

    def _deep(self):
        v = []
        for _ in range(60):
            v = [v]
        return v

    def test_the_module_is_pure_and_imports_three_modules_only(self):
        source = MODULE.read_bytes().decode('utf-8')
        tree = ast.parse(source)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module + '.' + ','.join(sorted(a.name for a in node.names)))
        self.assertEqual(imports, {'hashlib', 'math', 'aieos_bootstrap.evaluation_policy'})
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        for refused in ('open', 'exec', 'eval', 'compile', '__import__', 'input', 'breakpoint', 'os', 'sys', 'subprocess', 'socket', 'importlib', 'builtins'):
            self.assertNotIn(refused, names)
        public = {n.name for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')}
        self.assertEqual(public, {'ruleset_version', 'level_version', 'evidence_comparison', 'plain_data_problem'})

    def test_no_string_constant_of_the_module_names_the_state_directory(self):
        tree = ast.parse(MODULE.read_bytes().decode('utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.assertNotIn('.' + 'aieos', node.value)
        source = MODULE.read_bytes().decode('utf-8')
        self.assertNotIn('native' + '/', source)
        self.assertNotIn('bench' + '/', source)


class AC5TheEvidencePathEntry(unittest.TestCase):
    def test_the_module_is_an_entry_of_the_list(self):
        paths = evaluation_policy.EVIDENCE_DEFINING_PATHS
        self.assertEqual(len(paths), 16)
        self.assertEqual(len(set(paths)), 16)
        self.assertEqual(paths[8], 'src/aieos_bootstrap/eval_inputs.py')
        self.assertEqual(paths[9], 'src/aieos_bootstrap/evaluation_derive.py')
        self.assertEqual(list(paths[10:16]), ['src/aieos_bootstrap/evaluation_sources.py', 'src/aieos_bootstrap/scope_reconcile.py', 'src/aieos_bootstrap/base_inputs.py', 'src/aieos_bootstrap/base_files.py', 'src/aieos_bootstrap/evaluation.py', 'src/aieos_bootstrap/ci_evidence.py'])
        for p in paths:
            self.assertFalse(p.startswith('/') or '..' in p.split('/') or '\\' in p, p)
        self.assertTrue((ROOT / paths[-1]).is_file())

    def test_the_test_file_names_neither_forbidden_string(self):
        source = pathlib.Path(__file__).read_bytes().decode('utf-8')
        self.assertNotIn('native' + '/', source)
        self.assertNotIn('bench' + '/', source)


if __name__ == '__main__':
    unittest.main()

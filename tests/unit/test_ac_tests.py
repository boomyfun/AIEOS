"""Unit tests of aieos_bootstrap.ac_tests (task TASK-022, its rules R1 to R6); every rule has at least one passing
case and one failing case. Each test names the criteria it stands for in its own docstring."""

import ast
import copy
import hashlib
import pathlib
import unittest

from aieos_bootstrap import ac_tests, records

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap'
T = 'TASK-099'
P = 'tests/unit/test_x.py'


def contract(acs=('AC1', 'AC2'), g2=None, const=('INV-001',)):
    """A well-formed contract whose G2 tests gate names every AC by default."""
    g2 = list(acs) if g2 is None else list(g2)
    return {'acceptance_criteria': [{a: 'text of ' + a} for a in acs],
            'verification_plan': [{'gate': 'G0', 'check': 'scope'}, {'gate': 'G2', 'check': 'tests', 'args': g2},
                                  {'gate': 'G3', 'check': 'constitution', 'args': list(const)}],
            'constitution': list(const)}


def src(*bodies):
    return '\n\n'.join(bodies) + '\n'


def fn(name, doc=None):
    return 'def %s():\n%s    pass\n' % (name, '    """%s"""\n' % doc if doc is not None else '')


def run(c=None, tests=None, ws=None, task=T):
    c = contract() if c is None else c
    tests = {P: src(fn('test_a', 'AC1'), fn('test_b', 'AC2'))} if tests is None else tests
    ws = {task: [P]} if ws is None else ws
    return ac_tests.listing(task, c, tests, ws)


def kinds(out):
    return [(f['kind'], f['ref']) for f in out['findings']]


class R1Malformed(unittest.TestCase):

    def test_well_formed_gives_no_malformed(self):
        """TASK-022 AC1: a well-formed input gives no malformed finding."""
        self.assertEqual(run()['findings'], [])

    def test_each_malformed_form(self):
        """TASK-022 AC1: each malformed form gives exactly one malformed finding, named in the order of the inputs."""
        bad_contract = contract()
        del bad_contract['constitution']
        cases = [
            ('TASK-99', contract(), {P: ''}, {}, 'task_id'),
            (T, ['not', 'a', 'mapping'], {P: ''}, {}, 'contract'),
            (T, bad_contract, {P: ''}, {}, 'contract'),
            (T, contract(), [], {}, 'tests'),
            (T, contract(), {'': ''}, {}, 'tests'),
            (T, contract(), {'tests\\unit\\x.py': ''}, {}, 'tests'),
            (T, contract(), {'/tests/x.py': ''}, {}, 'tests'),
            (T, contract(), {P: b'def x(): pass'}, {}, P),
            (T, contract(), {P: ''}, [], 'write_sets'),
            (T, contract(), {P: ''}, {'TASK-1': [P]}, 'write_sets'),
            (T, contract(), {P: ''}, {T: P}, T),
            (T, contract(), {P: ''}, {T: ['']}, T),
        ]
        for task, c, tests, ws, ref in cases:
            with self.subTest(ref=ref, task=task):
                out = ac_tests.listing(task, c, tests, ws)
                self.assertEqual(out['named'], {})
                self.assertEqual(out['ambiguous'], [])
                self.assertEqual([f['kind'] for f in out['findings']], ['malformed'])
                self.assertEqual(out['findings'][0]['ref'], ref)

    def test_a_source_that_does_not_parse(self):
        """TASK-022 AC1: a source that does not parse, a null byte or nesting too deep for the parser, gives one
        malformed finding naming the first such path in sorted order, and no exception escapes."""
        deep = 'x = ' + '(' * 100000 + ')' * 100000 + '\n'
        for bad in ('def (:\n', 'x = 1\x00\n', deep):
            with self.subTest(bad=bad[:12]):
                out = ac_tests.listing(T, contract(), {'tests/b.py': bad, 'tests/a.py': 'x = 1\n'}, {})
                self.assertEqual(kinds(out), [('malformed', 'tests/b.py')])
        out = ac_tests.listing(T, contract(), {'tests/b.py': 'def (:\n', 'tests/a.py': 'def (:\n'}, {})
        self.assertEqual(kinds(out), [('malformed', 'tests/a.py')])

    def test_a_path_form_before_any_source(self):
        """TASK-022 AC1: every test path's form is checked before any source, so a bad path form at a late path is
        reported before an earlier source that does not parse."""
        out = ac_tests.listing(T, contract(), {'tests/a.py': 'def (:\n', 'tests/z\\x.py': ''}, {})
        self.assertEqual(kinds(out), [('malformed', 'tests')])


class R2Naming(unittest.TestCase):

    def test_qualified_in_another_tasks_file(self):
        """TASK-022 AC2: a qualified mention counts for its task in any file, also one the task's write set does not
        list."""
        tests = {P: src(fn('test_a', 'TASK-099 AC1 and TASK-099 AC2'))}
        out = run(tests=tests, ws={'TASK-098': [P]})
        self.assertEqual(out['named'], {'AC1': [P + '::test_a'], 'AC2': [P + '::test_a']})
        self.assertEqual(out['findings'], [])

    def test_several_qualified_and_the_in_place_of_form(self):
        """TASK-022 AC2: a docstring naming several qualified criteria, in the "(in place of ...)" form too, counts
        for each task and criterion it names, and for no other."""
        doc = 'TASK-099 AC2 (in place of TASK-098 AC1): x'
        tests = {P: src(fn('test_a', doc))}
        out99 = run(tests=tests)
        self.assertEqual(out99['named'], {'AC1': [], 'AC2': [P + '::test_a']})
        self.assertEqual(kinds(out99), [('untested', 'AC1')])
        out98 = run(tests=tests, task='TASK-098', ws={})
        self.assertEqual(out98['named'], {'AC1': [P + '::test_a'], 'AC2': []})

    def test_bare_in_own_file_counts(self):
        """TASK-022 AC2: a bare mention in a file that only the task's write set lists counts, from the docstring or a
        name part ac<digits>."""
        tests = {P: src(fn('test_a', 'AC1: the input'), fn('test_ac2_the_output'))}
        out = run(tests=tests)
        self.assertEqual(out['named'], {'AC1': [P + '::test_a'], 'AC2': [P + '::test_ac2_the_output']})
        self.assertEqual(out['findings'], [])

    def test_bare_does_not_count_beside_a_task_id_or_elsewhere(self):
        """TASK-022 AC2: a bare mention does not count beside a task id, nor in a file the task's write set does not
        list; a name part such as "acx" or "ac1x2" names nothing."""
        tests = {P: src(fn('test_a', 'TASK-098 decision; AC1'), fn('test_acx'), fn('test_ac1x2'))}
        self.assertEqual(run(tests=tests)['named'], {'AC1': [], 'AC2': []})
        tests = {P: src(fn('test_a', 'AC1'), fn('test_b', 'AC2'))}
        self.assertEqual(run(tests=tests, ws={'TASK-098': [P]})['named'], {'AC1': [], 'AC2': []})

    def test_module_class_docstrings_and_comments_do_not_count(self):
        """TASK-022 AC2: module docstrings, class docstrings and comments do not name criteria; a method directly in
        a top-level class is a test, a nested function and a non-test function are not."""
        text = ('"""TASK-099 AC1 AC2"""\n\n\nclass Case:\n    """TASK-099 AC1 AC2"""\n\n'
                '    def test_m(self):\n        # TASK-099 AC1\n        pass\n\n'
                '    def test_n(self):\n        """TASK-099 AC2"""\n\n        def test_inner():\n'
                '            """TASK-099 AC1"""\n\n\ndef helper():\n    """TASK-099 AC1"""\n')
        out = run(tests={P: text})
        self.assertEqual(out['named'], {'AC1': [], 'AC2': [P + '::Case.test_n']})

    def test_a_bare_criterion_beside_a_qualified_one_does_not_count(self):
        """TASK-022 AC2: a bare criterion beside a qualified mention of the same task in one docstring does not count,
        even in the task's own file; only the qualified one does."""
        out = run(tests={P: src(fn('test_a', 'TASK-099 AC1 and AC2'))})
        self.assertEqual(out['named'], {'AC1': [P + '::test_a'], 'AC2': []})
        self.assertEqual(kinds(out), [('untested', 'AC2')])

    def test_an_over_long_or_lower_case_task_id_is_not_one(self):
        """TASK-022 AC2: "TASK-" with four digits or in lower case is not a task id, so a bare criterion beside it still
        counts in the task's own file."""
        out = run(tests={P: src(fn('test_a', 'TASK-0221 and AC1'), fn('test_b', 'task-099 and AC2'))})
        self.assertEqual(out['named'], {'AC1': [P + '::test_a'], 'AC2': [P + '::test_b']})
        self.assertEqual(out['findings'], [])

    def test_a_write_set_path_in_another_form_matches_no_test(self):
        """TASK-022 AC1 and TASK-022 AC2: a write-set path with backslash separators is not a malformed input, and it
        matches no test, so a bare criterion in the test file counts for nobody."""
        out = run(ws={T: ['tests\\unit\\test_x.py']})
        self.assertEqual(out['named'], {'AC1': [], 'AC2': []})
        self.assertEqual([f['kind'] for f in out['findings']], ['untested', 'untested'])

    def test_a_path_in_two_write_sets_is_ambiguous(self):
        """TASK-022 AC2: a bare mention in a file that two tasks' write sets list counts for neither, and the test is
        listed as ambiguous for each; a qualified mention there still counts."""
        tests = {P: src(fn('test_a', 'AC1'), fn('test_b', 'TASK-099 AC2'))}
        ws = {T: [P], 'TASK-098': [P]}
        out = run(tests=tests, ws=ws)
        self.assertEqual(out['named'], {'AC1': [], 'AC2': [P + '::test_b']})
        self.assertEqual(out['ambiguous'], [P + '::test_a'])
        self.assertEqual(run(tests=tests, ws=ws, task='TASK-098', c=contract())['ambiguous'], [P + '::test_a'])


class R3Untested(unittest.TestCase):

    def test_untested_in_plan_order_once_each(self):
        """TASK-022 AC3: each untested criterion of the G2 tests gate gives one finding, in plan and args order, once,
        even when named in two gates."""
        c = contract(acs=('AC1', 'AC2', 'AC3'), g2=('AC3', 'AC1', 'AC3'))
        c['verification_plan'].append({'gate': 'G2', 'check': 'tests', 'args': ['AC1', 'AC2']})
        out = run(c=c, tests={P: src(fn('test_x', 'unrelated'))})
        self.assertEqual(kinds(out), [('untested', 'AC3'), ('untested', 'AC1'), ('untested', 'AC2')])

    def test_criteria_outside_the_g2_tests_gate_give_none(self):
        """TASK-022 AC3: a criterion that only a G3 gate or a G2 gate with another check names gives no untested
        finding; an article in the G2 args gives none either."""
        c = contract(acs=('AC1', 'AC2'), g2=('AC1', 'INV-001'))
        c['verification_plan'].append({'gate': 'G2', 'check': 'lint', 'args': ['AC2']})
        out = run(c=c, tests={P: src(fn('test_a', 'AC1'))})
        self.assertEqual(out['findings'], [])


class R4Result(unittest.TestCase):

    def test_keys_and_sorting(self):
        """TASK-022 AC4: the result has exactly the keys named, ambiguous and findings; named follows the order of the
        criteria and lists sorted test keys; each finding has exactly kind, ref and detail."""
        tests = {'tests/b.py': src(fn('test_z', 'TASK-099 AC1')), 'tests/a.py': src(fn('test_y', 'TASK-099 AC1'))}
        out = run(c=contract(acs=('AC2', 'AC1')), tests=tests, ws={})
        self.assertEqual(set(out), {'named', 'ambiguous', 'findings'})
        self.assertEqual(list(out['named']), ['AC2', 'AC1'])
        self.assertEqual(out['named']['AC1'], ['tests/a.py::test_y', 'tests/b.py::test_z'])
        self.assertEqual([set(f) for f in out['findings']], [{'kind', 'ref', 'detail'}])

    def test_purity(self):
        """TASK-022 AC4: the input is not changed, and a second call gives an equal result."""
        c, tests, ws = contract(), {P: src(fn('test_a', 'AC1'))}, {T: [P], 'TASK-098': [P, 'x.py']}
        before = copy.deepcopy((c, tests, ws))
        first = ac_tests.listing(T, c, tests, ws)
        self.assertEqual((c, tests, ws), before)
        self.assertEqual(ac_tests.listing(T, c, tests, ws), first)
        self.assertNotEqual(first, run())


class R5Record(unittest.TestCase):

    def test_none_for_no_findings(self):
        """TASK-022 AC5: no findings give no record."""
        self.assertIsNone(ac_tests.listing_record(T, 'v1', [], 'r', 'deterministic_tool_local'))

    def test_the_record(self):
        """TASK-022 AC5: the record's keys, values and id, and records.check_record finds nothing in it."""
        findings = run(tests={P: ''})['findings']
        self.assertTrue(findings)
        for sc in ('deterministic_tool_local', 'deterministic_tool_external_ci'):
            rec = ac_tests.listing_record(T, 'v2', findings, 'the core', sc)
            self.assertEqual(rec, {
                'record_id': hashlib.sha256(b'ac-tests\nTASK-099\nv2').hexdigest(), 'fact_kind': 'observation',
                'source_class': sc, 'recorder': 'the core', 'subject': T, 'evidence_type': 'ac_tests',
                'outcome': 'blocking', 'blocking_kind': 'other'})
            self.assertEqual(records.check_record(rec), [])

    def test_each_value_error(self):
        """TASK-022 AC5: each argument out of its form raises ValueError."""
        f = [{'kind': 'untested', 'ref': 'AC1', 'detail': 'x'}]
        good = (T, 'v1', f, 'r', 'deterministic_tool_local')
        for i, bad in ((0, 'TASK-1'), (1, '1'), (2, 'x'), (3, ''), (4, 'agent_declared')):
            args = list(good)
            args[i] = bad
            with self.subTest(i=i):
                with self.assertRaises(ValueError):
                    ac_tests.listing_record(*args)


class R6ModuleText(unittest.TestCase):

    def test_imports_and_calls(self):
        """TASK-022 AC6: the module imports only ast, hashlib, re and aieos_bootstrap's records and ac_coverage, and
        calls no open, write, clock, process, exec, eval, compile or __import__."""
        tree = ast.parse((SRC / 'ac_tests.py').read_bytes().decode('utf-8'))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                imports |= {node.module + '.' + a.name for a in node.names}
        self.assertEqual(imports, {'ast', 'hashlib', 're', 'aieos_bootstrap.records', 'aieos_bootstrap.ac_coverage'})
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for bad in ('open', 'exec', 'eval', 'compile', '__import__', 'input', 'print'):
            self.assertNotIn(bad, names)
        for bad in ('write', 'read', 'time', 'environ', 'system', 'popen', 'remove', 'unlink', 'getenv'):
            self.assertNotIn(bad, attrs)
        self.assertIn('compile', attrs)  # only as re.compile, the module-level patterns
        self.assertEqual({n.value.id for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == 'compile'},
                         {'re'})
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Assert)])

    def test_docstring_states_the_limits(self):
        """TASK-022 AC6: the docstring states line 73's limit and leaves DEF-0042 points 7 and 8 open; the package
        lists the module."""
        doc = ast.get_docstring(ast.parse((SRC / 'ac_tests.py').read_bytes().decode('utf-8')))
        self.assertIn('a name-based mapping shows that a test claims an AC, not that it tests it', doc)
        self.assertIn('DEF-0042 points 7 and 8', doc)
        self.assertIn('decides no acceptance', doc)
        init = (SRC / '__init__.py').read_bytes().decode('utf-8')
        self.assertIn("'ac_tests'", init)


if __name__ == '__main__':
    unittest.main()

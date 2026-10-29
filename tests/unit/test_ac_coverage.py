"""Unit tests of aieos_bootstrap.ac_coverage (TASK-021 AC12, rules R1 to R7); every rule has at least one passing case
and one failing case."""

import ast
import copy
import hashlib
import pathlib
import unittest

from aieos_bootstrap import ac_coverage, records

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap'


def contract(acs=('AC1', 'AC2'), plan=None, const=('INV-001',)):
    """A well-formed contract whose plan names every AC by default."""
    if plan is None:
        plan = [{'gate': 'G0', 'check': 'scope'}, {'gate': 'G2', 'check': 'tests', 'args': list(acs)},
                {'gate': 'G3', 'check': 'constitution', 'args': list(const)}]
    return {'task': 'TASK-099', 'acceptance_criteria': [{a: 'text of ' + a} for a in acs],
            'verification_plan': plan, 'constitution': list(const)}


def kinds(findings):
    return [(f['kind'], f['ref']) for f in findings]


class R1Malformed(unittest.TestCase):
    """AC1: each malformed form gives exactly one malformed finding."""

    def test_well_formed_gives_no_malformed(self):
        self.assertEqual(ac_coverage.check(contract()), [])

    def test_each_malformed_form(self):
        cases = []
        cases.append(['not', 'a', 'mapping'])
        for key in ('acceptance_criteria', 'verification_plan', 'constitution'):
            c = contract()
            del c[key]
            cases.append(c)
        c = contract(); c['acceptance_criteria'] = 'AC1'; cases.append(c)
        c = contract(); c['acceptance_criteria'] = [{'AC1': 'a', 'AC2': 'b'}]; cases.append(c)
        c = contract(); c['acceptance_criteria'] = [{'ac1': 'a'}]; cases.append(c)
        c = contract(); c['acceptance_criteria'] = [{'AC1': ''}]; cases.append(c)
        c = contract(); c['acceptance_criteria'] = [{'AC1': 'a'}, {'AC1': 'b'}]; cases.append(c)
        c = contract(); c['verification_plan'] = {'gate': 'G0'}; cases.append(c)
        c = contract(); c['verification_plan'] = [{'gate': 'G0'}]; cases.append(c)
        c = contract(); c['verification_plan'] = [{'gate': 'X0', 'check': 'scope'}]; cases.append(c)
        c = contract(); c['verification_plan'] = [{'gate': 'G2', 'check': 'tests', 'args': 'AC1'}]; cases.append(c)
        c = contract(); c['verification_plan'] = [{'gate': 'G2', 'check': 'tests', 'args': ['AC1', '']}]; cases.append(c)
        c = contract(); c['verification_plan'] = [{'gate': 'G2', 'check': 'tests', 'other': 1}]; cases.append(c)
        c = contract(); c['constitution'] = 'INV-001'; cases.append(c)
        c = contract(); c['constitution'] = ['INV-001', 3]; cases.append(c)
        for c in cases:
            with self.subTest(c=c):
                out = ac_coverage.check(c)
                self.assertEqual(len(out), 1)
                self.assertEqual(out[0]['kind'], 'malformed')

    def test_more_malformed_forms(self):
        cases = (('verification_plan', ['G0']), ('verification_plan', [{'gate': 'G0', 'check': ''}]),
                 ('acceptance_criteria', [{'AC1': 3}]),
                 ('verification_plan', [{'gate': 'G2', 'check': 'tests', 'args': ['AC1', 3]}]))
        for key, value in cases:
            c = contract()
            c[key] = value
            with self.subTest(key=key, value=value):
                self.assertEqual(kinds(ac_coverage.check(c)), [('malformed', key)])


class R2Uncovered(unittest.TestCase):
    """AC2: an AC no gate names is uncovered, in the order of acceptance_criteria."""

    def test_all_named(self):
        self.assertEqual(kinds(ac_coverage.check(contract(acs=('AC1', 'AC2', 'AC3')))), [])

    def test_uncovered_in_order(self):
        plan = [{'gate': 'G0', 'check': 'scope'}, {'gate': 'G2', 'check': 'tests', 'args': ['AC2']}]
        out = ac_coverage.check(contract(acs=('AC3', 'AC1', 'AC2'), plan=plan, const=()))
        self.assertEqual(kinds(out), [('uncovered', 'AC3'), ('uncovered', 'AC1')])

    def test_named_in_any_gate(self):
        plan = [{'gate': 'G2', 'check': 'tests', 'args': ['AC1']}, {'gate': 'G3', 'check': 'constitution', 'args': ['AC2']}]
        self.assertEqual(ac_coverage.check(contract(plan=plan, const=())), [])


class R3Empty(unittest.TestCase):
    """AC3: an empty acceptance_criteria list."""

    def test_empty(self):
        out = ac_coverage.check(contract(acs=(), plan=[{'gate': 'G0', 'check': 'scope'}], const=()))
        self.assertEqual(kinds(out), [('no_acceptance_criteria', 'acceptance_criteria')])

    def test_not_empty(self):
        self.assertNotIn('no_acceptance_criteria', [f['kind'] for f in ac_coverage.check(contract())])


class R4Stray(unittest.TestCase):
    """AC4: an args entry that is neither an AC of the contract nor an article of its constitution list."""

    def test_each_stray_entry(self):
        for entry in ('AC9', 'Ac1', 'SEC-001', 'INV-01'):
            plan = [{'gate': 'G2', 'check': 'tests', 'args': ['AC1', 'AC2', entry]}]
            with self.subTest(entry=entry):
                self.assertEqual(kinds(ac_coverage.check(contract(plan=plan))), [('stray_arg', entry)])

    def test_article_in_the_list_is_not_stray(self):
        plan = [{'gate': 'G2', 'check': 'tests', 'args': ['AC1', 'AC2']},
                {'gate': 'G3', 'check': 'constitution', 'args': ['INV-001', 'SEC-001']}]
        self.assertEqual(ac_coverage.check(contract(plan=plan, const=('INV-001', 'SEC-001'))), [])

    def test_reported_once_in_plan_order(self):
        plan = [{'gate': 'G2', 'check': 'tests', 'args': ['AC1', 'X2', 'X1']},
                {'gate': 'G3', 'check': 'constitution', 'args': ['X1', 'AC2', 'X3']}]
        self.assertEqual(kinds(ac_coverage.check(contract(plan=plan, const=()))),
                         [('stray_arg', 'X2'), ('stray_arg', 'X1'), ('stray_arg', 'X3')])

    def test_the_stray_detail_names_its_gate(self):
        want = 'X1 in the args of %s is neither an AC of the contract nor an article of its constitution list'
        for gate in ('G2', 'G3'):
            plan = [{'gate': 'G2', 'check': 'tests', 'args': ['AC1', 'AC2'] + (['X1'] if gate == 'G2' else [])},
                    {'gate': 'G3', 'check': 'constitution', 'args': ['INV-001'] + (['X1'] if gate == 'G3' else [])}]
            with self.subTest(gate=gate):
                out = ac_coverage.check(contract(plan=plan))
                self.assertEqual([f['detail'] for f in out], [want % gate])


class R5Result(unittest.TestCase):
    """AC5: the order of kinds, the keys of a finding, purity."""

    def test_order_and_keys(self):
        plan = [{'gate': 'G2', 'check': 'tests', 'args': ['AC1', 'X1']}]
        out = ac_coverage.check(contract(acs=('AC1', 'AC2'), plan=plan, const=()))
        self.assertEqual(kinds(out), [('uncovered', 'AC2'), ('stray_arg', 'X1')])
        for f in out:
            self.assertEqual(set(f), {'kind', 'ref', 'detail'})
            self.assertTrue(isinstance(f['detail'], str) and f['detail'])
        empty = ac_coverage.check({'acceptance_criteria': [], 'constitution': [],
                                   'verification_plan': [{'gate': 'G2', 'check': 'tests', 'args': ['X1']}]})
        self.assertEqual(kinds(empty), [('no_acceptance_criteria', 'acceptance_criteria'), ('stray_arg', 'X1')])

    def test_pure(self):
        c = contract(acs=('AC1', 'AC2'), plan=[{'gate': 'G2', 'check': 'tests', 'args': ['AC1', 'X1']}])
        before = copy.deepcopy(c)
        first = ac_coverage.check(c)
        self.assertEqual(c, before)
        self.assertEqual(ac_coverage.check(c), first)
        self.assertNotEqual(first, [])


class R6Record(unittest.TestCase):
    """AC6: the record, its id, its form, the refusals."""

    def test_none_for_no_findings(self):
        self.assertIsNone(ac_coverage.coverage_record('TASK-021', 'v1', [], 'aieos-core', 'deterministic_tool_local'))

    def test_record(self):
        found = ac_coverage.check(contract(plan=[{'gate': 'G2', 'check': 'tests', 'args': ['AC1']}], const=()))
        for cls in ('deterministic_tool_local', 'deterministic_tool_external_ci'):
            r = ac_coverage.coverage_record('TASK-021', 'v2', found, 'aieos-ci', cls)
            want = hashlib.sha256('ac-coverage\nTASK-021\nv2'.encode('utf-8')).hexdigest()
            self.assertEqual(r, {'record_id': want, 'fact_kind': 'observation', 'source_class': cls,
                                 'recorder': 'aieos-ci', 'subject': 'TASK-021', 'evidence_type': 'ac_coverage',
                                 'outcome': 'blocking', 'blocking_kind': 'other'})
            self.assertEqual(records.check_record(r), [])
        self.assertNotEqual(ac_coverage.coverage_record('TASK-021', 'v1', found, 'x', 'deterministic_tool_local')['record_id'],
                            ac_coverage.coverage_record('TASK-021', 'v2', found, 'x', 'deterministic_tool_local')['record_id'])

    def test_refusals(self):
        found = [{'kind': 'uncovered', 'ref': 'AC1', 'detail': 'x'}]
        bad = [('TASK-x', 'v1', found, 'r', 'deterministic_tool_local'),
               ('TASK-021', '1', found, 'r', 'deterministic_tool_local'),
               ('TASK-021', 'v1', found, '', 'deterministic_tool_local'),
               ('TASK-021', 'v1', found, 'r', 'agent_declared'),
               ('TASK-021', 'v1', 'uncovered', 'r', 'deterministic_tool_local')]
        for args in bad:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    ac_coverage.coverage_record(*args)


class R7Purity(unittest.TestCase):
    """AC7 and AC8: a script check of the module's imports and calls, and its docstring's limits."""

    def tree(self):
        return ast.parse((SRC / 'ac_coverage.py').read_bytes().decode('utf-8'))

    def test_imports(self):
        tree = self.tree()
        imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        froms = {(n.module, a.name) for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
        self.assertEqual(imports, {'hashlib', 're'})
        self.assertEqual(froms, {('aieos_bootstrap', 'records')})

    def test_no_file_clock_or_write(self):
        tree = self.tree()
        names = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        attrs = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        for refused in ('open', 'exec', 'eval', 'compile', '__import__', 'input'):
            self.assertNotIn(refused, names)
        for refused in ('open', 'write', 'write_text', 'write_bytes', 'now', 'utcnow', 'time', 'getenv', 'system'):
            self.assertNotIn(refused, attrs)
        self.assertFalse(any(isinstance(n, ast.Assert) for n in ast.walk(tree)))
        self.assertFalse(any(isinstance(n, ast.Constant) and isinstance(n.value, str) and '.aieos' in n.value
                             for n in ast.walk(tree)))

    def test_the_check_finds_a_refused_call(self):
        tree = ast.parse('open("x", "rb")\n')
        names = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertIn('open', names)

    def test_no_refused_name_anywhere(self):
        names = {n.id for n in ast.walk(self.tree()) if isinstance(n, ast.Name)}
        for refused in ('open', 'exec', 'eval', 'compile', '__import__', 'input'):
            self.assertNotIn(refused, names)
        self.assertIn('open', {n.id for n in ast.walk(ast.parse('f = open\n')) if isinstance(n, ast.Name)})

    def test_docstring_states_the_limits(self):
        doc = ast.get_docstring(self.tree())
        for s in ('DEF-0042 point 7', 'decides no acceptance', 'writes and appends nothing', 'at gate level only',
                  'no reader of contract files'):
            self.assertIn(s, doc)


if __name__ == '__main__':
    unittest.main()

"""Unit tests of aieos_bootstrap.autonomy (task TASK-036). The tests write and remove no file, and open none except the
package's own source files, read for the purity and caller scans (TASK-036 AC6, AC9 and AC11). Every value below is
made up for these tests; none is a level, allowance or status of any project. Each test names the criteria it stands
for in its own docstring."""

import pathlib
import re
import unittest

from aieos_bootstrap import autonomy

PKG = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap'
SRC = PKG / 'autonomy.py'
L2 = {'level': 'L2', 'change_request': 'CR-MADE-UP', 'metrics': 'made-up metrics'}
L1 = {'level': 'L1'}
PASS = {'C13': 'PASS', 'P-CRED': 'PASS'}
KEYS = {'allowed', 'level', 'reasons'}


DEFAULT = object()


def call(levels=DEFAULT, allowance=DEFAULT, risk='low', status=DEFAULT, touches=False):
    return autonomy.auto_accept_allowed({'low': L2, 'medium': L2} if levels is DEFAULT else levels,
                                        {'low': True, 'medium': True} if allowance is DEFAULT else allowance,
                                        risk, PASS if status is DEFAULT else status, touches)


class Hostile(str):
    """A str subclass whose comparison and hash raise (decision D-739 C1)."""

    def __eq__(self, other):
        raise RuntimeError('eq')

    def __ne__(self, other):
        raise RuntimeError('ne')

    def __hash__(self):
        raise RuntimeError('hash')


class HostileKey(str):
    """A str subclass that can be a dict key (its hash is str's) but whose comparison raises (decision D-739 C1)."""

    __hash__ = str.__hash__

    def __eq__(self, other):
        raise RuntimeError('eq')

    def __ne__(self, other):
        raise RuntimeError('ne')


class Result(unittest.TestCase):
    def test_result_has_exactly_three_keys(self):
        """TASK-036 AC1: the result is a new dict with exactly allowed, level and reasons; allowed is True if and only
        if reasons is empty."""
        for r in (call(), call(risk='high'), call(touches=None)):
            self.assertIs(type(r), dict)
            self.assertEqual(set(r), KEYS)
            self.assertIs(type(r['allowed']), bool)
            self.assertIn(r['level'], ('L1', 'L2'))
            self.assertIs(type(r['reasons']), list)
            self.assertEqual(r['allowed'], r['reasons'] == [])
            self.assertTrue(all(type(x) is str for x in r['reasons']))

    def test_new_result_and_list_each_call(self):
        """TASK-036 AC1: each call returns a new result and a new reasons list."""
        a, b = call(risk='high'), call(risk='high')
        self.assertEqual(a, b)
        self.assertIsNot(a, b)
        self.assertIsNot(a['reasons'], b['reasons'])


class Positive(unittest.TestCase):
    def test_low_and_medium_allowed_on_made_up_values(self):
        """TASK-036 AC7 and TASK-036 AC2: with made-up values (an L2 entry, an allowance of True, both statuses
        "PASS" and touches False), risk low and risk medium give allowed True and level "L2"."""
        for risk in ('low', 'medium'):
            self.assertEqual(call(risk=risk), {'allowed': True, 'level': 'L2', 'reasons': []})

    def test_each_condition_alone_fails(self):
        """TASK-036 AC7 and TASK-036 AC2: changing any one condition of the made-up positive case alone makes
        allowed False with that condition's reason."""
        cases = [
            (dict(risk='lowish'), ['risk', 'L1', 'policy']),
            (dict(levels={'low': L1}), ['L1']),
            (dict(levels={}), ['level', 'L1']),
            (dict(allowance={'low': False}), ['policy']),
            (dict(status={'C13': 'FAIL', 'P-CRED': 'PASS'}), ['C13']),
            (dict(status={'C13': 'PASS', 'P-CRED': 'FAIL'}), ['P-CRED']),
            (dict(touches=True), ['touches policy']),
        ]
        for kw, want in cases:
            r = call(**kw)
            self.assertFalse(r['allowed'], kw)
            self.assertEqual(r['reasons'], want, kw)


class Rule(unittest.TestCase):
    def test_risk_reason(self):
        """TASK-036 AC2: a risk that is not one of the four classes adds "risk", the level is "L1" and "level" is
        not added; a valid class does not add "risk"."""
        r = call(risk=None)
        self.assertEqual(r['level'], 'L1')
        self.assertEqual(r['reasons'][:2], ['risk', 'L1'])
        self.assertNotIn('level', r['reasons'])
        self.assertNotIn('risk', call(risk='medium')['reasons'])

    def test_level_reason_for_entries_out_of_form(self):
        """TASK-036 AC2: levels not a dict, no entry, or an entry out of form adds "level" and the level is "L1"."""
        bad = [None, [], 'L2', {'low': None}, {'low': 'L2'}, {'low': {'level': 'L2'}},
               {'low': {'level': 'L2', 'change_request': '', 'metrics': 'm'}},
               {'low': {'level': 'L2', 'change_request': 'c', 'metrics': ''}},
               {'low': {'level': 'L2', 'change_request': 'c', 'metrics': 'm', 'extra': 1}},
               {'low': {'level': 'L1', 'note': 'x'}}, {'low': {'level': 'L3'}}, {'low': {'level': 'L4'}},
               {'low': {'level': 'l2', 'change_request': 'c', 'metrics': 'm'}}]
        for levels in bad:
            r = call(levels=levels)
            self.assertEqual(r['level'], 'L1', levels)
            self.assertEqual(r['reasons'], ['level', 'L1'], levels)

    def test_l1_entry(self):
        """TASK-036 AC2: an entry exactly {"level": "L1"} gives level "L1" and the reason "L1" only."""
        self.assertEqual(call(levels={'low': L1}), {'allowed': False, 'level': 'L1', 'reasons': ['L1']})

    def test_risk_above_medium_at_l2(self):
        """TASK-036 AC2: level "L2" with risk high or critical adds "risk above medium" (concept line 622)."""
        for risk in ('high', 'critical'):
            r = call(levels={risk: L2}, allowance={risk: True}, risk=risk)
            self.assertEqual(r, {'allowed': False, 'level': 'L2', 'reasons': ['risk above medium']})

    def test_policy_reason(self):
        """TASK-036 AC2: "policy" unless allowance is a dict whose value for the class is True; a missing value and
        another class's True fail."""
        for allowance in (None, [], {}, {'medium': True}, {'low': None}):
            self.assertEqual(call(allowance=allowance)['reasons'], ['policy'], allowance)

    def test_status_reasons(self):
        """TASK-036 AC2: "C13" and "P-CRED" unless status holds the str "PASS" for each; a missing value counts as not
        PASS (reading R1 for P-CRED)."""
        self.assertEqual(call(status={})['reasons'], ['C13', 'P-CRED'])
        self.assertEqual(call(status={'C13': 'PASS'})['reasons'], ['P-CRED'])
        self.assertEqual(call(status={'P-CRED': 'PASS'})['reasons'], ['C13'])
        self.assertEqual(call(status=None)['reasons'], ['C13', 'P-CRED'])
        self.assertEqual(call()['reasons'], [])
        self.assertEqual(autonomy.auto_accept_allowed({'low': L2}, {'low': True}, 'low', None, False)['reasons'],
                         ['C13', 'P-CRED'])

    def test_reasons_in_order(self):
        """TASK-036 AC2: every reason at once, in the fixed order."""
        r = autonomy.auto_accept_allowed([], [], 'high', [], None)
        self.assertEqual(r['reasons'], ['level', 'L1', 'policy', 'C13', 'P-CRED', 'touches policy'])
        r = autonomy.auto_accept_allowed({'high': L2}, {}, 'high', {}, 0)
        self.assertEqual(r['reasons'], ['risk above medium', 'policy', 'C13', 'P-CRED', 'touches policy'])
        r = autonomy.auto_accept_allowed(None, None, 7, None, None)
        self.assertEqual(r['reasons'], ['risk', 'L1', 'policy', 'C13', 'P-CRED', 'touches policy'])


class Strict(unittest.TestCase):
    def test_allowance_must_be_true_itself(self):
        """TASK-036 AC3: an allowance of 1, "true", "True" or another truthy value fails."""
        for v in (1, 'true', 'True', [1], 1.0):
            self.assertEqual(call(allowance={'low': v})['reasons'], ['policy'], v)

    def test_status_must_be_the_str_pass(self):
        """TASK-036 AC3: "pass", " PASS", "PASS " and non-str values fail."""
        for v in ('pass', ' PASS', 'PASS ', True, 1, None, ['PASS'], b'PASS'):
            self.assertEqual(call(status={'C13': v, 'P-CRED': 'PASS'})['reasons'], ['C13'], v)

    def test_touches_must_be_false_itself(self):
        """TASK-036 AC3: touches 0, None, "False", "" and [] fail."""
        for v in (0, None, 'False', '', [], 0.0):
            self.assertEqual(call(touches=v)['reasons'], ['touches policy'], v)

    def test_risk_must_be_a_str_among_the_four(self):
        """TASK-036 AC3: True, a list, a dict, b"low", "Low" and " low" fail."""
        for v in (True, ['low'], {'low': 1}, b'low', 'Low', ' low', 0):
            self.assertIn('risk', call(risk=v)['reasons'], v)

    def test_subclasses_are_not_dict_or_str(self):
        """TASK-036 AC3 and TASK-036 AC4: a dict subclass is treated as not a dict, and a str subclass (one whose
        comparison and hash raise, decision D-739 C1) as not a str; nothing raises."""

        class D(dict):
            pass

        self.assertEqual(call(levels=D({'low': L2}))['reasons'], ['level', 'L1'])
        self.assertEqual(call(allowance=D({'low': True}))['reasons'], ['policy'])
        self.assertEqual(call(status=D(PASS))['reasons'], ['C13', 'P-CRED'])
        self.assertEqual(call(levels={'low': D(L2)})['reasons'], ['level', 'L1'])
        h = Hostile('low')
        self.assertIn('risk', call(risk=h)['reasons'])
        self.assertEqual(call(levels={'low': {'level': Hostile('L2'), 'change_request': 'c', 'metrics': 'm'}})['reasons'],
                         ['level', 'L1'])
        self.assertEqual(call(levels={'low': {'level': 'L2', 'change_request': Hostile('c'), 'metrics': 'm'}})['reasons'],
                         ['level', 'L1'])
        self.assertEqual(call(status={'C13': Hostile('PASS'), 'P-CRED': 'PASS'})['reasons'], ['C13'])


class NeverRaises(unittest.TestCase):
    def test_odd_values_for_every_parameter(self):
        """TASK-036 AC4: odd and unhashable values for every parameter return a result in AC1's form and raise
        nothing."""
        odd = [None, 0, 1, -1, 2.5, '', 'x', b'x', [], [1], {}, {1: 2}, {(1,): 'L2'}, set(), {1}, (), (1,),
               frozenset(), True, False, object(), Hostile('low'), [{'level': 'L2'}], {'low': [1]},
               {'low': {'level': ['L2']}}, {'low': {1: 'L2'}}, {'low': {'level': {}}}]
        for v in odd:
            for args in ((v, {'low': True}, 'low', PASS, False), ({'low': L2}, v, 'low', PASS, False),
                         ({'low': L2}, {'low': True}, v, PASS, False), ({'low': L2}, {'low': True}, 'low', v, False),
                         ({'low': L2}, {'low': True}, 'low', PASS, v)):
                r = autonomy.auto_accept_allowed(*args)
                self.assertEqual(set(r), KEYS)
                self.assertEqual(r['allowed'], r['reasons'] == [])

    def test_dict_with_non_str_keys(self):
        """TASK-036 AC4: dicts whose keys are not str, or are str subclasses that raise, are read without hashing."""
        self.assertEqual(call(levels={1: L2, (2,): L2, HostileKey('low'): L2})['reasons'], ['level', 'L1'])
        self.assertEqual(call(allowance={HostileKey('low'): True, 3: True})['reasons'], ['policy'])
        self.assertEqual(call(status={HostileKey('C13'): 'PASS', 'P-CRED': 'PASS'})['reasons'], ['C13'])


class SelfBuildFacts(unittest.TestCase):
    def test_present_facts_give_false_for_every_class(self):
        """TASK-036 AC7 and TASK-036 AC6: the self-build's present facts (no level table, an empty allowance, C13 and
        P-CRED not PASS, touches False) give allowed False for every class, with reasons "level", "L1", "policy",
        "C13" and "P-CRED"."""
        for risk in autonomy.CLASSES:
            r = autonomy.auto_accept_allowed({}, {}, risk, {}, False)
            self.assertEqual(r, {'allowed': False, 'level': 'L1', 'reasons': ['level', 'L1', 'policy', 'C13', 'P-CRED']})


class Scans(unittest.TestCase):
    def test_no_caller_in_the_package(self):
        """TASK-036 AC6: no module of src/aieos_bootstrap imports or calls autonomy (the package docstring may name it
        in prose)."""
        for p in sorted(PKG.glob('*.py')):
            if p.name == 'autonomy.py':
                continue
            text = p.read_text(encoding='utf-8')
            self.assertIsNone(re.search(r'import\s+autonomy|from\s+\.?\s*autonomy|autonomy\.auto_accept|'
                                        r'aieos_bootstrap\.autonomy|from\s+\.\s+import[^\n]*autonomy', text), p.name)

    def test_no_project_value_in_the_module(self):
        """TASK-036 AC6: the module names no project and holds no level table, allowance or status value."""
        text = SRC.read_text(encoding='utf-8')
        code = text.split('"""', 2)[2]
        self.assertNotIn('gov-AIEOS', code)
        self.assertNotIn('PASS', code.replace("== 'PASS'", ''))
        self.assertIsNone(re.search(r"^[A-Z_]+ = \{", code, re.M))

    def test_purity(self):
        """TASK-036 AC9: the module imports nothing and does no I/O (no open, eval, exec, compile, __import__)."""
        code = SRC.read_text(encoding='utf-8').split('"""', 2)[2]
        self.assertIsNone(re.search(r'^\s*(import|from)\s', code, re.M))
        for bad in ('open', 'eval', 'exec', 'compile', '__import__'):
            self.assertIsNone(re.search(r'\b' + bad + r'\s*\(', code), bad)
        for bad in ('os.', 'sys.', 'subprocess', 'socket', 'time.', 'datetime', 'random', 'io.', 'pathlib'):
            self.assertNotIn(bad, code, bad)

    def test_docstring_states(self):
        """TASK-036 AC5: the module docstring states what allowed is not, where the values come from, no project
        values, the form-only L2 check, no bound above L2, reading R1 and the governor's wiring as a separate change."""
        doc = ' '.join(autonomy.__doc__.split())
        for s in ("the policy's half of row 4", 'not an acceptance', 'not a gate result', 'sufficient assurance',
                  'only from an approved, versioned policy', 'only from pinned values',
                  'defines no level, allowance or status for any project', 'a check of form only',
                  'Any bound above L2 is not expressible', 'Reading R1', 'only the owner may loosen it',
                  'separate governor change'):
            self.assertIn(s, doc, s)


class Naming(unittest.TestCase):
    def test_every_test_names_its_criteria(self):
        """TASK-036 AC10: every test method of this module's test classes names "TASK-036 AC" in its docstring and no
        other task's criterion in qualified form (read from the loaded objects, no file opened)."""
        seen = 0
        for cls in list(globals().values()):
            if not (isinstance(cls, type) and issubclass(cls, unittest.TestCase)):
                continue
            for name, fn in vars(cls).items():
                if name.startswith('test_'):
                    seen += 1
                    doc = fn.__doc__ or ''
                    self.assertIn('TASK-036 AC', doc, name)
                    self.assertEqual([t for t in re.findall(r'TASK-(\d+) AC', doc) if t != '036'], [], name)
        self.assertGreater(seen, 15)


if __name__ == '__main__':
    unittest.main()

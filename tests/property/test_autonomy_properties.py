"""Property tests of aieos_bootstrap.autonomy (task TASK-036), over inputs generated with the standard library's random
and a fixed seed (in this test module only). Every value is made up for these tests; none is a level, allowance or
status of any project. The tests write and open no file. Each test names the criteria it stands for in its own
docstring."""

import copy
import random
import re
import unittest

from aieos_bootstrap import autonomy

SEED = 36
N = 3000
L2 = {'level': 'L2', 'change_request': 'CR-MADE-UP', 'metrics': 'made-up metrics'}
ENTRIES = [L2, {'level': 'L1'}, {'level': 'L2'}, {'level': 'L3'}, None, 'L2',
           {'level': 'L2', 'change_request': '', 'metrics': 'm'}]
RISKS = list(autonomy.CLASSES) + [None, 'Low', 1, ['low']]
ALLOW = [True, False, 1, 'true', None]
STATUS = ['PASS', 'FAIL', 'pass', None, True]
TOUCH = [False, True, 0, None, 'False']


def pick(rng, values):
    """The first value (the one that meets its condition) with probability 0.7, else any value."""
    return values[0] if rng.random() < 0.7 else rng.choice(values)


def gen(rng):
    levels = {c: pick(rng, ENTRIES) for c in autonomy.CLASSES if rng.random() < 0.9}
    allowance = {c: pick(rng, ALLOW) for c in autonomy.CLASSES if rng.random() < 0.9}
    status = {k: pick(rng, STATUS) for k in ('C13', 'P-CRED') if rng.random() < 0.95}
    return levels, allowance, rng.choice(RISKS), status, pick(rng, TOUCH)


def oracle(levels, allowance, risk, status, touches):
    """Every condition of TASK-036 AC2 for allowed True, written apart from the module."""
    return (type(risk) is str and risk in ('low', 'medium') and levels.get(risk) == L2
            and allowance.get(risk) is True and type(status.get('C13')) is str and status.get('C13') == 'PASS'
            and type(status.get('P-CRED')) is str and status.get('P-CRED') == 'PASS' and touches is False)


class Properties(unittest.TestCase):
    def test_allowed_only_when_every_condition_holds(self):
        """TASK-036 AC8 and TASK-036 AC2: over generated inputs, allowed is True exactly when every condition holds,
        and both outcomes occur."""
        rng = random.Random(SEED)
        seen = set()
        for _ in range(N):
            args = gen(rng)
            r = autonomy.auto_accept_allowed(*args)
            self.assertEqual(r['allowed'], oracle(*args), args)
            seen.add(r['allowed'])
        self.assertEqual(seen, {True, False})

    def test_a_failing_condition_never_allows(self):
        """TASK-036 AC8: from an allowed input, making any one condition fail never gives allowed True."""
        rng = random.Random(SEED + 1)
        base = ({'low': L2, 'medium': L2}, {'low': True, 'medium': True}, 'low', {'C13': 'PASS', 'P-CRED': 'PASS'},
                False)
        self.assertTrue(autonomy.auto_accept_allowed(*base)['allowed'])
        for _ in range(N):
            args = list(copy.deepcopy(base))
            args[2] = rng.choice(['low', 'medium'])
            k = rng.randrange(5)
            if k == 0:
                args[0][args[2]] = rng.choice(ENTRIES[1:])
            elif k == 1:
                args[1][args[2]] = rng.choice(ALLOW[1:])
            elif k == 2:
                args[2] = rng.choice(['high', 'critical', None, 'Low'])
                args[0][args[2]] = L2 if type(args[2]) is str else None
            elif k == 3:
                args[3][rng.choice(['C13', 'P-CRED'])] = rng.choice(STATUS[1:])
            else:
                args[4] = rng.choice(TOUCH[1:])
            self.assertFalse(autonomy.auto_accept_allowed(*args)['allowed'], args)

    def test_deterministic_and_inputs_unchanged(self):
        """TASK-036 AC8 and TASK-036 AC1: equal inputs give equal results, the inputs are left unchanged, and each
        call returns a new result and a new reasons list."""
        rng = random.Random(SEED + 2)
        for _ in range(N // 3):
            args = gen(rng)
            before = copy.deepcopy(args)
            a = autonomy.auto_accept_allowed(*args)
            b = autonomy.auto_accept_allowed(*args)
            self.assertEqual(a, b)
            self.assertIsNot(a, b)
            self.assertIsNot(a['reasons'], b['reasons'])
            self.assertEqual(args, before)


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
        self.assertEqual(seen, 4)


if __name__ == '__main__':
    unittest.main()

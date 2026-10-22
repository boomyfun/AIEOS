"""Unit tests of the hardening of aieos_bootstrap.session_violation (task TASK-071, AC5, AC6, AC7 and AC8): exact types
and fixed values on adapter.violation's answer, the one try around the lookup answer's reading, and the exact-type
event_id; stand-ins for the lookup and adapter.violation only, copied here as new definitions. No file is written and no
process starts. Each test names its criteria in its own docstring."""

import ast
import datetime
import pathlib
import re
import unittest
from unittest import mock

from aieos_bootstrap import adapter
from aieos_bootstrap import session_violation as sv
from aieos_bootstrap import violation as violations
from aieos_bootstrap import writer

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap'
ROOT = '/made-up-root'
NOW = datetime.datetime(2026, 10, 16, 12, 0, 0, tzinfo=datetime.timezone.utc)
TASK = 'TASK-100'
LEASE = {'task_id': TASK, 'fencing_token': {'epoch': 'E' * 20, 'counter': 3}, 'expires_at': NOW}
OBS = {'record_id': 'obs-1', 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
       'recorder': 'r', 'subject': TASK, 'evidence_type': 'write_outside_write_set', 'outcome': 'blocking',
       'blocking_kind': 'violation', 'refers_to': 'src/outside.py'}
NO_TIED = 'lease: the lookup gave no tied lease'
NO_MAPPING = 'entry: adapter.violation gave no result mapping'


def other_task_ids(text):
    """The qualified AC ids of tasks other than TASK-071 in text, with every run of whitespace collapsed (rule (e))."""
    return re.findall(r'TASK-(?!071 )[0-9]+ AC[0-9]+', ' '.join(text.split()))


class StrSub(str):
    pass


class Raising(str):
    def __eq__(self, other):
        raise ValueError('eq')

    __hash__ = str.__hash__


def core(**over):
    c = {'result': 'done', 'reason': None, 'findings': [], 'appended': ['ev'], 'duplicate': [], 'released': None}
    c.update(over)
    return c


def answer(**over):
    a = adapter._result('done', None, [], core(), 'STOP: violation')
    a.update(over)
    return a


def call(given=None, lookup_answer=None, event_id='ev'):
    """session_violation with stand-ins: the lookup gives lookup_answer (a tied lease by default), adapter.violation
    gives given; returns the result and the calls of each stand-in."""
    looked, recorded = [], []
    tied = writer.StoreResult('done', 'tied', value=dict(LEASE)) if lookup_answer is None else lookup_answer

    def lookup(r, s, n):
        looked.append(1)
        return tied

    def stand_in(*a, **k):
        recorded.append(1)
        return answer() if given is None else given
    with mock.patch.object(adapter, 'violation', stand_in):
        out = sv.session_violation(ROOT, 's-1', OBS, event_id, 'r', NOW, lookup=lookup)
    return out, looked, recorded


def refused(findings, reason='leases'):
    r = writer.StoreResult('refused', reason, [])
    r.findings = findings
    return r


class AC6Hardening(unittest.TestCase):

    def test_a_good_answer_passes(self):
        """TASK-071 AC6: an answer of the checked shape and core None both pass as today."""
        self.assertEqual(call()[0]['result'], 'done')
        self.assertEqual(call(answer(core=None))[0]['result'], 'done')

    def test_exact_types_and_fixed_values(self):
        """TASK-071 AC6: each field of (a) and (b) out of type or value gives "entry", NO_MAPPING."""
        cases = {'findings item': answer(findings=[StrSub('x')]), 'findings int': answer(findings=[1]),
                 'core findings': answer(core=core(findings=[StrSub('x')])),
                 'result None': answer(result=None), 'result other': answer(result='other'),
                 'result subclass': answer(result=StrSub('done')), 'reason int': answer(reason=1),
                 'reason subclass': answer(reason=StrSub('r')), 'decision other': answer(decision='other'),
                 'decision subclass': answer(decision=StrSub('STOP: violation')),
                 'core result': answer(core=core(result='other')), 'core result None': answer(core=core(result=None)),
                 'core reason': answer(core=core(reason=1)), 'core appended': answer(core=core(appended=[1])),
                 'core duplicate': answer(core=core(duplicate=[StrSub('d')])),
                 'core extra key': answer(core=dict(core(), more=1)),
                 'core missing key': answer(core={k: v for k, v in core().items() if k != 'released'})}
        for name, given in cases.items():
            with self.subTest(case=name):
                out = call(given)[0]
                self.assertEqual((out['result'], out['reason'], out['findings']), ('refused', 'entry', [NO_MAPPING]))

    def test_a_raising_dict_subclass(self):
        """TASK-071 AC6: a dict subclass answer whose reads raise still gives "entry: after the record: <type name>"."""
        class Bad(dict):
            def __getitem__(self, key):
                raise KeyError(key)
        out = call(Bad(answer()))[0]
        self.assertEqual(out['findings'], ['entry: after the record: KeyError'])

    def test_the_lookup_answer_reading(self):
        """TASK-071 AC6: a StoreResult subclass whose attributes raise, findings not iterable, a plain str or a str
        subclass reason give NO_TIED; str-subclass items are dropped, then the fixed finding; a mixed list keeps its
        exact str items."""
        class Bad(writer.StoreResult):
            __slots__ = ()

            @property
            def result(self):
                raise RuntimeError('r')
        bad = Bad.__new__(Bad)
        cases = [(bad, [NO_TIED]), (refused(5), [NO_TIED]), (refused('abc'), [NO_TIED]),
                 (refused(['leases: x'], StrSub('leases')), [NO_TIED]),
                 (refused([StrSub('a'), Raising('b')]), ['lease: the lookup refused (leases)']),
                 (refused([StrSub('a'), 'leases: kept', 1]), ['leases: kept']),
                 (refused((1, None)), ['lease: the lookup refused (leases)'])]
        for given, findings in cases:
            with self.subTest(given=type(given).__name__, findings=findings):
                out, looked, recorded = call(lookup_answer=given)
                self.assertEqual((out['result'], out['reason'], out['findings'], recorded),
                                 ('refused', 'lease', findings, []))

    def test_a_raising_lookup_keeps_its_finding(self):
        """TASK-071 AC6: a lookup that raises keeps "lease: session_lease raised <type name>"."""
        def lookup(r, s, n):
            raise OSError('x')
        out = sv.session_violation(ROOT, 's-1', OBS, 'ev', 'r', NOW, lookup=lookup)
        self.assertEqual(out['findings'], ['lease: session_lease raised OSError'])

    def test_the_event_id(self):
        """TASK-071 AC6: an event_id of a str subclass, None, an int or bytes gives "argument", with the lookup not
        called and nothing appended; an empty str passes (0); with a bad root only _session_findings' finding."""
        for ev in [StrSub('ev'), None, 7, b'ev']:
            with self.subTest(event_id=repr(ev)):
                out, looked, recorded = call(event_id=ev)
                self.assertEqual((out['reason'], out['findings'], looked, recorded),
                                 ('argument', ['argument: event_id is not a string'], [], []))
        out, looked, recorded = call(event_id='')
        self.assertEqual((len(looked), len(recorded)), (1, 1))
        out = sv.session_violation('', 's-1', OBS, None, 'r', NOW, lookup=lambda r, s, n: None)
        self.assertEqual(out['findings'], ['argument: root is not a non-empty string'])


class AC5Constants(unittest.TestCase):

    def test_the_core_keys(self):
        """TASK-071 AC5: _CORE_KEYS equals violation's result keys, written out, not imported."""
        self.assertEqual(sv._CORE_KEYS, frozenset(violations.RESULT_KEYS))
        tree = ast.parse((SRC / 'session_violation.py').read_bytes().decode('utf-8'))
        mods = {n.module + '.' + a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
        self.assertEqual(mods, {'aieos_bootstrap.adapter', 'aieos_bootstrap.writer'})


class AC5Names(unittest.TestCase):

    def test_no_secret_named_str_constant(self):
        """TASK-071 AC5: no module-level name holding "token", "pass", "secret" or "pwd" is bound to a str constant in
        session_violation.py."""
        tree = ast.parse((SRC / 'session_violation.py').read_bytes().decode('utf-8'))
        names = [t.id for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
                 and isinstance(n.value.value, str) for t in n.targets if isinstance(t, ast.Name)]
        self.assertEqual([x for x in names if any(w in x.lower() for w in ('token', 'pass', 'secret', 'pwd'))], [])


class AC7Stated(unittest.TestCase):

    def test_the_docstring_states_the_hardening(self):
        """TASK-071 AC7: session_violation.py's module docstring states the points of (d), (b)'s departure, the direct
        reading, the caller's stand-ins, the limit and (0), (a) and (c) (whitespace collapsed)."""
        doc = ' '.join(ast.get_docstring(ast.parse((SRC / 'session_violation.py').read_bytes().decode('utf-8'))).split())
        for words in ('An exception raised by adapter.violation itself ends as the plain "entry: <type name>"',
                      'A "done" may carry released None', 'the token filter\'s breadth',
                      'The lookup\'s lock cost', 'a deliberate fail-closed departure',
                      'read directly after an isinstance test, not through adapter._store_done',
                      'A production caller passes no lookup, append or release',
                      'type-checked but not passed through the token filter', 'stay isinstance-checked',
                      'event_id must be of exact type str', 'checked by exact types and fixed values',
                      'collapse to "lease: the lookup gave no tied lease"',
                      'an ending that can follow a record already written'):
            with self.subTest(words=words):
                self.assertIn(words, doc)
        self.assertNotIn('.' + 'aieos', doc)


class AC8OwnTests(unittest.TestCase):

    def test_hardening_tests_name_their_criteria(self):
        """TASK-071 AC8: every test function of this module names "TASK-071 ACn" in its own docstring and no other
        task's AC in qualified form."""
        tree = ast.parse(pathlib.Path(__file__).read_bytes().decode('utf-8'))
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test')]:
            doc = ast.get_docstring(fn) or ''
            with self.subTest(test=fn.name):
                self.assertTrue(re.findall(r'TASK-071 AC[0-9]+', ' '.join(doc.split())))
                self.assertEqual(other_task_ids(doc), [])


if __name__ == '__main__':
    unittest.main()

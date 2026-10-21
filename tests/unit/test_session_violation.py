"""Unit tests of aieos_bootstrap.session_violation (task TASK-070, rules R1, R2, R3, R5 and R6): the violation
path tied by the live lease, with stand-ins for the lookup, adapter.violation, append and release; every stand-in's
call is bound to the real function's signature. No file is written or created and no process starts; the one call of
the real writer.session_lease (a relative root) is refused at its root check. Each test names its criteria in its own
docstring."""

import ast
import copy
import datetime
import inspect
import pathlib
import re
import unittest

from aieos_bootstrap import adapter
from aieos_bootstrap import eventlog
from aieos_bootstrap import session_violation as sv
from aieos_bootstrap import violation as violations
from aieos_bootstrap import writer

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap'
ROOT = str(pathlib.Path(__file__).resolve().parents[2] / 'no-such-adapter-root')
TASK = 'TASK-100'
SID = 'session-1'
NOW = datetime.datetime(2026, 10, 16, 12, 0, 0, tzinfo=datetime.timezone.utc)
LATER = NOW + datetime.timedelta(hours=1)
REC = 'aieos-adapter (unit)'
EV = 'ev-1'
EPOCH = 'epoch-value-0123456789abcdef'
TOKEN = {'epoch': EPOCH, 'counter': 3}
LEASE = {'task_id': TASK, 'fencing_token': TOKEN, 'expires_at': LATER}
HIDDEN = 'release: the lease is held with another token (not shown)'
NO_TIED = 'lease: the lookup gave no tied lease'
NO_MAPPING = 'entry: adapter.violation gave no result mapping'
REFUSAL = 'the lease on %s is held with epoch %s counter 4, not epoch %s counter 3' % (TASK, 'other-epoch-xyz', EPOCH)
WRITER_REASONS = ('argument', 'root', 'no_store', 'link', 'unreadable', 'tables', 'lease_row_without_session',
                  'no_lease_row', 'session', 'ended', 'leases')


def observation(**over):
    o = {'record_id': 'obs-1', 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
         'recorder': REC, 'subject': TASK, 'evidence_type': 'write_outside_write_set', 'outcome': 'blocking',
         'blocking_kind': 'violation', 'refers_to': 'src/outside.py'}
    o.update(over)
    return o


def holds_token(value, epochs=(EPOCH,)):
    """The token predicate of TASK-070's header: walked through dicts, lists and tuples, a dict with the keys epoch and
    counter, a str holding both "epoch" and "counter", or a str holding one of the given epoch values."""
    if isinstance(value, dict):
        if 'epoch' in value and 'counter' in value:
            return True
        return any(holds_token(k, epochs) or holds_token(v, epochs) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(holds_token(v, epochs) for v in value)
    if isinstance(value, str):
        return ('epoch' in value and 'counter' in value) or any(e in value for e in epochs)
    return False


class Calls:
    """Stand-ins that record each call, bound to the real function's signature, and give a set answer."""

    def __init__(self, answers=None):
        self.calls = []
        self.answers = dict(answers or {})

    def make(self, name, real):
        def stand_in(*args, **kwargs):
            inspect.signature(real).bind(*args, **kwargs)
            self.calls.append((name, args, kwargs))
            a = self.answers.get(name)
            if isinstance(a, Exception):
                raise a
            return a(*args, **kwargs) if callable(a) else a
        return stand_in

    def names(self):
        return [c[0] for c in self.calls]


def tied(lease=LEASE):
    return writer.StoreResult('done', 'tied', value=lease)


def core_done(released=None, findings=()):
    return {'result': 'done', 'reason': None, 'findings': list(findings), 'appended': [EV, EV + '/decision'],
            'duplicate': [], 'released': released}


def answer(core=None, released=None, findings=(), result='done', reason=None, decision=violations.DECISION):
    return {'result': result, 'reason': reason, 'findings': list(findings), 'core': core, 'decision': decision,
            'fencing_token': None, 'released': released}


def run(c, lookup_answer=tied(), violation_answer=None, patch=True, **over):
    """session_violation with a lookup stand-in and, when patch, adapter.violation replaced by a stand-in."""
    c.answers.setdefault('lookup', lookup_answer)
    c.answers.setdefault('violation', violation_answer)
    args = dict(root=ROOT, session_id=SID, observation=observation(), event_id=EV, recorder=REC, now=NOW)
    args.update(over)
    real = adapter.violation
    if patch:
        adapter.violation = c.make('violation', real)
    try:
        return sv.session_violation(lookup=c.make('lookup', writer.session_lease), **args)
    finally:
        adapter.violation = real


class Raising(dict):
    """A dict whose every way of being read or copied raises."""

    def _no(self, *args, **kwargs):
        raise RuntimeError('no')
    keys = items = values = __iter__ = __getitem__ = get = copy = _no


class BadStr(str):
    def __ne__(self, other):
        raise RuntimeError('no')

    def __eq__(self, other):
        raise RuntimeError('no')

    __hash__ = str.__hash__


class R1Arguments(unittest.TestCase):

    def test_step_one_refuses_each_argument(self):
        """TASK-070 AC1: root, session_id and now out of form each give "refused", reason "argument", a fixed finding
        naming the argument, and no later step's function is called."""
        cases = [({'root': None}, 'root'), ({'root': ''}, 'root'), ({'root': b'x'}, 'root'),
                 ({'session_id': None}, 'session_id'), ({'session_id': ''}, 'session_id'),
                 ({'session_id': 1}, 'session_id'),
                 ({'now': NOW.replace(tzinfo=None)}, 'now'), ({'now': NOW.replace(microsecond=5)}, 'now'),
                 ({'now': NOW.astimezone(datetime.timezone(datetime.timedelta(hours=7)))}, 'now'),
                 ({'now': NOW.date()}, 'now'), ({'now': '2026-10-16T12:00:00Z'}, 'now')]
        for over, name in cases:
            with self.subTest(over=over):
                c = Calls()
                r = run(c, **over)
                self.assertEqual(tuple(r), adapter.RESULT_KEYS)
                self.assertEqual((r['result'], r['reason']), ('refused', 'argument'))
                self.assertEqual(len(r['findings']), 1)
                self.assertTrue(r['findings'][0].startswith('argument: %s is not' % name), r['findings'])
                self.assertIsNone(r['fencing_token'])
                self.assertEqual(c.calls, [])

    def test_an_argument_whose_methods_raise(self):
        """TASK-070 AC1: an argument whose own methods raise gives "argument: checking the arguments raised <type>"."""
        c = Calls()
        r = run(c, session_id=BadStr('s'))
        self.assertEqual((r['result'], r['reason'], r['findings']),
                         ('refused', 'argument', ['argument: checking the arguments raised RuntimeError']))
        self.assertEqual(c.calls, [])

    def test_no_exception_escapes(self):
        """TASK-070 AC1: a stand-in of adapter.violation that raises gives "entry: <type name>"; an answer whose every
        read raises gives "entry: after the record: <type name>"."""
        r = run(Calls({'violation': ValueError('x')}))
        self.assertEqual((r['result'], r['reason'], r['findings']), ('refused', 'entry', ['entry: ValueError']))
        r = run(Calls({'violation': lambda *a, **k: Raising()}))
        self.assertEqual((r['result'], r['reason'], r['findings']),
                         ('refused', 'entry', ['entry: after the record: RuntimeError']))
        self.assertEqual(tuple(r), adapter.RESULT_KEYS)

    def test_answers_that_are_no_result_mapping(self):
        """TASK-070 AC1: an answer of adapter.violation that is not a mapping with exactly RESULT_KEYS, whose core is
        neither None nor a dict, whose lists are not lists, or whose released values are neither a dict nor None gives
        "entry: adapter.violation gave no result mapping"."""
        good = answer(core_done())
        bad = [None, [], 'done', {k: good[k] for k in list(good)[:-1]}, dict(good, extra=1),
               dict(good, core='x'), dict(good, findings=()), dict(good, released='x'),
               dict(good, core=dict(core_done(), appended=())), dict(good, core=dict(core_done(), duplicate=None)),
               dict(good, core=dict(core_done(), findings='x')), dict(good, core=dict(core_done(), released=[]))]
        for a in bad:
            with self.subTest(answer=a):
                r = run(Calls({'violation': a}))
                self.assertEqual((r['result'], r['reason'], r['findings']), ('refused', 'entry', [NO_MAPPING]))
        r = run(Calls({'violation': good}))
        self.assertEqual(r['result'], 'done')

    def test_equal_inputs_equal_results(self):
        """TASK-070 AC1: equal arguments give equal results; nothing is kept between calls."""
        first = run(Calls({'violation': answer(core_done(released=LEASE), released=LEASE)}))
        second = run(Calls({'violation': answer(core_done(released=LEASE), released=LEASE)}))
        self.assertEqual(first, second)
        self.assertIsNone(first['fencing_token'])
        self.assertFalse(holds_token(first))


class R2Lookup(unittest.TestCase):

    def test_the_lookup_is_called_once_with_the_three_arguments(self):
        """TASK-070 AC2: lookup is called once with exactly (root, session_id, now), the test's stand-in."""
        c = Calls({'violation': answer(core_done())})
        run(c)
        self.assertEqual([x for x in c.calls if x[0] == 'lookup'], [('lookup', (ROOT, SID, NOW), {})])

    def test_the_default_lookup_is_reached_at_call_time(self):
        """TASK-070 AC2: with no lookup given, writer.session_lease is reached at call time (a stand-in patched on the
        writer module is the one called)."""
        c = Calls({'session_lease': writer.StoreResult('refused', 'session', ['session: no such session'])})
        real = writer.session_lease
        writer.session_lease = c.make('session_lease', real)
        try:
            r = sv.session_violation(ROOT, SID, observation(), EV, REC, NOW)
        finally:
            writer.session_lease = real
        self.assertEqual(c.calls, [('session_lease', (ROOT, SID, NOW), {})])
        self.assertEqual((r['result'], r['reason'], r['findings']), ('refused', 'lease', ['session: no such session']))

    def test_each_writer_reason_gives_lease(self):
        """TASK-070 AC2: each writer reason of a refused answer gives "refused", reason "lease", the writer's findings
        with findings[0] starting "<reason>:", and adapter.violation is not called."""
        for reason in WRITER_REASONS:
            with self.subTest(reason=reason):
                c = Calls()
                r = run(c, lookup_answer=writer.StoreResult('refused', reason, ['%s: the writer says so' % reason]))
                self.assertEqual((r['result'], r['reason']), ('refused', 'lease'))
                self.assertEqual(r['findings'], ['%s: the writer says so' % reason])
                self.assertNotIn('violation', c.names())

    def test_a_refusal_with_no_finding(self):
        """TASK-070 AC2: a refused answer with a str reason and no str finding gives the fixed finding naming the
        reason."""
        for found in ((), (1, None)):
            r = run(Calls(), lookup_answer=writer.StoreResult('refused', 'ended', found))
            self.assertEqual(r['findings'], ['lease: the lookup refused (ended)'])

    def test_a_relative_root_through_the_real_lookup(self):
        """TASK-070 AC2: through the real writer.session_lease a relative root gives "lease" with findings[0] starting
        "root:", never "argument"."""
        r = sv.session_violation('relative-root', SID, observation(), EV, REC, NOW)
        self.assertEqual((r['result'], r['reason']), ('refused', 'lease'))
        self.assertTrue(r['findings'][0].startswith('root:'), r['findings'])

    def test_answers_that_are_no_tied_lease(self):
        """TASK-070 AC2: a done no_lease_row, a tied value of the wrong shape, a refused answer with a non-str reason,
        a non-StoreResult answer and an exception of lookup each give "lease" with the fixed finding, and
        adapter.violation is not called; no text of the answer reaches a finding."""
        mark = 'TEXT-OF-THE-ANSWER-QQ'
        shapes = [writer.StoreResult('done', 'no_lease_row'), tied(None), tied([mark]), tied(dict(LEASE, more=mark)),
                  tied({k: LEASE[k] for k in ('task_id', 'fencing_token')}), tied(dict(LEASE, task_id=mark)),
                  tied(dict(LEASE, fencing_token={'epoch': mark})), tied(dict(LEASE, fencing_token=mark)),
                  writer.StoreResult('refused', 7, [mark]), writer.StoreResult('done', mark, value=LEASE),
                  mark, None, {'result': 'done', 'reason': 'tied', 'value': LEASE}]
        for a in shapes:
            with self.subTest(answer=a):
                c = Calls()
                r = run(c, lookup_answer=a)
                self.assertEqual((r['result'], r['reason'], r['findings']), ('refused', 'lease', [NO_TIED]))
                self.assertNotIn('violation', c.names())
                self.assertNotIn(mark, repr(r))
        c = Calls({'lookup': OSError('x')})
        r = run(c)
        self.assertEqual(r['findings'], ['lease: session_lease raised OSError'])
        self.assertNotIn('violation', c.names())

    def test_a_refusal_finding_holding_a_token_is_replaced(self):
        """TASK-070 AC2 (R3-5): the lookup's refused findings holding both "epoch" and "counter" come out replaced by the
        fixed finding."""
        r = run(Calls(), lookup_answer=writer.StoreResult('refused', 'leases',
                                                          ['leases: epoch e counter 2', REFUSAL, 'leases: plain']))
        self.assertEqual(r['findings'], [HIDDEN, HIDDEN, 'leases: plain'])

    def test_the_lease_keys(self):
        """TASK-070 AC2 and TASK-070 AC5: the private key set equals eventlog.LEASE_KEYS."""
        self.assertEqual(sv._LEASE_KEYS, eventlog.LEASE_KEYS)


class R3Record(unittest.TestCase):

    def test_the_record_call(self):
        """TASK-070 AC3: on a tied lease adapter.violation is called once with the lease's task and token and the
        caller's other arguments, append and release passed through."""
        append, release = object(), object()
        c = Calls({'violation': answer(core_done())})
        obs = observation()
        run(c, observation=obs, append=append, release=release)
        calls = [x for x in c.calls if x[0] == 'violation']
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], (ROOT, TASK, TOKEN, obs, EV, REC, NOW))
        self.assertIs(calls[0][2]['append'], append)
        self.assertIs(calls[0][2]['release'], release)

    def test_the_result_is_a_token_free_copy(self):
        """TASK-070 AC3 and TASK-070 AC1: the result equals the stand-in's answer but for released's and
        core['released']'s fencing_token and the replaced token findings; the answer is not mutated and no list is
        shared."""
        core = core_done(released=LEASE, findings=['release: nothing released (token)', REFUSAL, 'x epoch y counter',
                                                   'kept'])
        given = answer(core, released=LEASE, findings=[REFUSAL, 'kept'])
        before = copy.deepcopy(given)
        r = run(Calls({'violation': given}))
        self.assertEqual(given, before)
        no_token = {'task_id': TASK, 'expires_at': LATER}
        expected = copy.deepcopy(before)
        expected['released'] = no_token
        expected['findings'] = [HIDDEN, 'kept']
        expected['core']['released'] = no_token
        expected['core']['findings'] = ['release: nothing released (token)', HIDDEN, HIDDEN, 'kept']
        self.assertEqual(r, expected)
        self.assertIsNot(r, given)
        self.assertIsNot(r['core'], given['core'])
        for k in ('appended', 'duplicate', 'findings'):
            self.assertIsNot(r['core'][k], given['core'][k])
        self.assertIsNot(r['findings'], given['findings'])
        self.assertFalse(holds_token(r, (EPOCH, 'other-epoch-xyz')))
        self.assertTrue(holds_token(given, (EPOCH,)))

    def test_through_the_real_violation_call(self):
        """TASK-070 AC3: through the real adapter.violation with stand-ins for append and release: another task's
        observation gives "argument" with nothing appended; a fence on the first append gives "core" with decision None
        and nothing appended; the partial outcome keeps the violation's event_id in core's appended; a done gives
        'STOP: violation' and released copied out without its token."""
        def appended(*a, **k):
            return eventlog.AppendResult('appended', seq=1)

        def fence(*a, **k):
            return eventlog.AppendResult('refused', 'fence', findings=('fence: lease lost',))

        def released(*a, **k):
            return writer.StoreResult('done', value=LEASE)

        c = Calls({'append': appended, 'release': released})
        r = run(c, patch=False, observation=observation(subject='TASK-200'),
                append=c.make('append', writer.append_event), release=c.make('release', writer.release_lease_token))
        self.assertEqual((r['result'], r['reason']), ('refused', 'argument'))
        self.assertIn('argument: observation subject is not the task id', r['findings'])
        self.assertEqual(c.names(), ['lookup'])

        c = Calls({'append': fence, 'release': released})
        r = run(c, patch=False, append=c.make('append', writer.append_event),
                release=c.make('release', writer.release_lease_token))
        self.assertEqual((r['result'], r['reason'], r['decision']), ('refused', 'core', None))
        self.assertEqual((r['core']['reason'], r['core']['appended']), ('fence', []))

        answers = iter([appended, fence])
        c = Calls({'append': lambda *a, **k: next(answers)(*a, **k), 'release': released})
        r = run(c, patch=False, append=c.make('append', writer.append_event),
                release=c.make('release', writer.release_lease_token))
        self.assertEqual((r['result'], r['reason'], r['decision']), ('refused', 'core', None))
        self.assertEqual(r['core']['appended'], [EV])
        self.assertNotIn('release', c.names())

        c = Calls({'append': appended, 'release': released})
        r = run(c, patch=False, append=c.make('append', writer.append_event),
                release=c.make('release', writer.release_lease_token))
        self.assertEqual((r['result'], r['decision']), ('done', violations.DECISION))
        self.assertEqual(r['released'], {'task_id': TASK, 'expires_at': LATER})
        self.assertEqual(r['core']['released'], {'task_id': TASK, 'expires_at': LATER})
        self.assertFalse(holds_token(r))


def new_part():
    """The source of session_violation.py, its code after the module docstring, and the AST of the whole."""
    text = (SRC / 'session_violation.py').read_bytes().decode('utf-8')
    return text, text.split('"""', 2)[2], ast.parse(text)


class R5WhatItDoes(unittest.TestCase):

    def test_the_new_code_opens_nothing_and_reads_no_clock(self):
        """TASK-070 AC5: the new definitions use no exec, eval, compile, __import__, importlib or assert, no open, no
        clock, no environment, no process and no project-state directory's name; they call of writer only
        session_lease (as the default lookup) and name its StoreResult."""
        text, part, tree = new_part()
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        self.assertFalse(names & {'open', 'exec', 'eval', 'compile', '__import__', 'importlib'})
        self.assertFalse(attrs & {'now', 'utcnow', 'today', 'time', 'environ', 'getenv', 'system', 'popen', 'open',
                                  'run', 'Popen', 'stdin'})
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Assert)])
        imports = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imports |= {a.name for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                imports |= {'%s.%s' % (n.module, a.name) for a in n.names}
        self.assertEqual(imports, {'aieos_bootstrap.adapter', 'aieos_bootstrap.writer'})
        consts = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        self.assertFalse(consts & {'valid', 'accepted', 'approved'})
        used = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                and n.value.id == 'writer'}
        self.assertEqual(used, {'session_lease', 'StoreResult'})
        self.assertNotIn('.' + 'aieos', text)
        self.assertNotIn('eventlog', part)

    def test_no_hook_side_module_names_it(self):
        """TASK-070 AC5: none of the six hook-side modules names session_violation."""
        for name in ('claude_code.py', 'claude_code_hook.py', 'claude_code_channel.py', 'claude_code_reads.py',
                     'claude_code_store.py', 'claude_code_read_hook.py'):
            with self.subTest(module=name):
                self.assertNotIn('session_violation', (SRC / name).read_bytes().decode('utf-8'))


class R6Stated(unittest.TestCase):

    def test_the_docstring_states_the_fifth_call(self):
        """TASK-070 AC6: session_violation.py's module docstring states the call's tie, the token's removal, the flow, the
        "lease" refusal, the limits and that nothing hook-side calls it yet (whitespace collapsed)."""
        doc = ' '.join(ast.get_docstring(ast.parse((SRC / 'session_violation.py').read_bytes().decode('utf-8'))).split())
        for words in ('The core violation path tied by the live lease (task TASK-070', 'specification 5 :109, with :108',
                      'The token is read core-side from that lease and never returned',
                      'kept as findings[0]\'s prefix', '"lease_row_without_session" and a "no_lease_row" done cannot '
                      'arise with a session id required', 'one now for the lookup and the record',
                      'the observation\'s subject must be the tied lease\'s task',
                      'the released lease (released and core[\'released\'])', 'holding both "epoch" and "counter"',
                      '"release: the lease is held with another token (not shown)"', '"entry: after the record"',
                      'A "lease" refusal is no section 8 violation and no STOP',
                      'the race between the lookup and the appends', 'the partial outcome',
                      'a retry with the same event_id while the lease is still held completes it',
                      'a repeat after "done" gives "lease"', 'the fail-open direction',
                      'the observed read-set record is left for section 11 point 10',
                      'It never writes an observed read-set record', 'Nothing hook-side calls it yet'):
            with self.subTest(words=words):
                self.assertIn(words, doc)
        self.assertNotIn('.' + 'aieos', doc)
        self.assertNotIn('called only by this function', doc)


class R7OwnTests(unittest.TestCase):

    def test_every_test_names_its_criteria(self):
        """TASK-070 AC7: every test function of this module names "TASK-070 ACn" in its own docstring and no other
        task's AC in qualified form."""
        tree = ast.parse(pathlib.Path(__file__).read_bytes().decode('utf-8'))
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test')]:
            doc = ast.get_docstring(fn) or ''
            with self.subTest(test=fn.name):
                self.assertTrue(re.findall(r'TASK-070 AC[0-9]+', doc))
                self.assertEqual(re.findall(r'TASK-(?!070 )[0-9]+ AC[0-9]+', doc), [])


if __name__ == '__main__':
    unittest.main()

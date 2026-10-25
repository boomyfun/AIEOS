"""Unit tests of launcher.end_outside and the command end of aieos_bootstrap.cli (task TASK-092): the arguments and the
result's form, the order of the steps and the records lines, failing closed, the command's parse, runtime refusal and
output forms, the modules and the docstrings. Every callee is a stand-in recording its calls; launcher.end_outside is
replaced in the CLI tests through mock.patch.object, restored after each test; the clock is a counting stand-in; no
test writes a file, opens a store or runs Git; the root is a literal Windows path that names no folder."""

import ast
import datetime
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import cli, launcher, mcp_server, read_set_record, writer

HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / 'src' / 'aieos_bootstrap'
ROOT = 'C:/outside-root-92'
SID = 'launch-0123'
REC = 'tester'
UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 10, 25, 12, 0, 0, tzinfo=UTC)
EARLIER = datetime.datetime(2026, 10, 25, 11, 0, 0, tzinfo=UTC)
LATER = datetime.datetime(2026, 10, 25, 13, 0, 0, tzinfo=UTC)
RECORDER_TEXT = REC + ' outside the runtime, for session ' + SID + ', its lease row possibly unexpired'


class R:
    """A store answer: result, value, reason and findings."""

    def __init__(self, result='done', value=None, reason=None, findings=()):
        self.result = result
        self.value = value
        self.reason = reason
        self.findings = list(findings)


def record(result='written'):
    return {'result': result, 'reason': None, 'findings': [], 'record': None, 'core': None}


def conflict():
    return {'result': 'refused', 'reason': 'core', 'findings': [], 'record': None,
            'core': {'result': 'refused', 'reason': 'conflict'}}


def row(task, expires=LATER):
    return {'task_id': task, 'fencing_token': {'token': task}, 'expires_at': expires}


class World:
    """The five callees as recording stand-ins, each answer settable, each raise settable by name."""

    def __init__(self, rows=None, ended=False):
        rows = [row('TASK-1')] if rows is None else rows
        self.log = []
        self.leases = R('done', {'ended': ended, 'leases': rows})
        self.stored = {}
        self.records = {}
        self.removed = {}
        tasks = sorted(set(r['task_id'] for r in rows if isinstance(r, dict) and isinstance(r.get('task_id'), str)))
        self.ended = R('done', [{'task_id': t} for t in tasks])
        self.raises = {}

    def _call(self, name, *args):
        self.log.append((name,) + args)
        if name in self.raises:
            raise self.raises[name]

    def session_leases(self, root, session_id, now):
        self._call('session_leases', root, session_id, now)
        return self.leases

    def stored_reads(self, root, session_id, task_id):
        self._call('stored_reads', task_id)
        return self.stored.get(task_id, R('done', ['src/a.py']))

    def observe_gone(self, root, task_id, session_id, reads, reason, now, recorder):
        self._call('observe_gone', task_id, session_id, reads, reason, now, recorder)
        return self.records.get(task_id, record())

    def remove_reads(self, root, session_id, task_id):
        self._call('remove_reads', task_id)
        return self.removed.get(task_id, R('done', 1))

    def end_session(self, root, session_id, now):
        self._call('end_session', root, session_id, now)
        return self.ended

    def names(self):
        return [entry[0] if entry[0] in ('session_leases', 'end_session') else '%s %s' % entry[:2]
                for entry in self.log]


def outside(world, root=ROOT, session_id=SID, now=NOW, recorder=REC):
    return launcher.end_outside(root, session_id, now, recorder, session_leases=world.session_leases,
                                stored_reads=world.stored_reads, remove_reads=world.remove_reads,
                                observe_gone=world.observe_gone, end_session=world.end_session)


class RaisingNow(datetime.datetime):
    def utcoffset(self):
        raise RuntimeError('utcoffset')


class TASK092AC1Arguments(unittest.TestCase):
    def assert_argument(self, result, world):
        self.assertEqual((result['result'], result['reason'], result['released']), ('refused', 'argument', []))
        self.assertEqual(world.log, [])

    def test_root_not_absolute(self):
        """TASK-092 AC1: a root that is not an absolute path gives "argument" and no callee called."""
        for root in ('relative/root', '', None, 7):
            world = World()
            self.assert_argument(outside(world, root=root), world)

    def test_session_id(self):
        """TASK-092 AC1: an empty or non-str session_id gives "argument" and no callee called."""
        for session_id in ('', None, 3):
            world = World()
            self.assert_argument(outside(world, session_id=session_id), world)

    def test_now(self):
        """TASK-092 AC1: a naive now, a now not in UTC and a now with microseconds give "argument"."""
        for now in (datetime.datetime(2026, 10, 25, 12, 0, 0),
                    datetime.datetime(2026, 10, 25, 12, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=7))),
                    datetime.datetime(2026, 10, 25, 12, 0, 0, 5, tzinfo=UTC), '2026-10-25'):
            world = World()
            self.assert_argument(outside(world, now=now), world)

    def test_now_whose_checks_raise(self):
        """TASK-092 AC1: a now whose own checks raise gives "argument", the raise named, no callee called."""
        world = World()
        result = outside(world, now=RaisingNow(2026, 10, 25, 12, 0, 0, tzinfo=UTC))
        self.assert_argument(result, world)
        self.assertEqual(result['findings'], ['argument: checking the arguments raised RuntimeError'])

    def test_recorder(self):
        """TASK-092 AC1: an empty or non-str recorder gives "argument" and no callee called."""
        for recorder in ('', None):
            world = World()
            self.assert_argument(outside(world, recorder=recorder), world)

    def test_callee_not_callable(self):
        """TASK-092 AC1: a callee neither None nor callable gives "argument" and no callee called."""
        for name in launcher._OUTSIDE_CALLEES:
            world = World()
            kwargs = {'session_leases': world.session_leases, 'stored_reads': world.stored_reads,
                      'remove_reads': world.remove_reads, 'observe_gone': world.observe_gone,
                      'end_session': world.end_session}
            kwargs[name] = 'not callable'
            result = launcher.end_outside(ROOT, SID, NOW, REC, **kwargs)
            self.assert_argument(result, world)
            self.assertIn('argument: %s is neither None nor callable' % name, result['findings'])

    def test_keys_in_every_case(self):
        """TASK-092 AC1: the result has exactly OUTSIDE_KEYS, refused or done."""
        self.assertEqual(launcher.OUTSIDE_KEYS, ('result', 'reason', 'findings', 'records', 'released'))
        bad = World()
        bad.leases = R('refused', reason='session')
        for result in (outside(World()), outside(World(), root='x'), outside(bad)):
            self.assertEqual(tuple(result), launcher.OUTSIDE_KEYS)

    def test_callees_default_at_call_time(self):
        """TASK-092 AC1: each callee left None is looked up at call time: stand-ins patched after import are called."""
        world = World()
        with mock.patch.object(writer, 'session_leases', world.session_leases), \
                mock.patch.object(writer, 'stored_reads', world.stored_reads), \
                mock.patch.object(writer, 'remove_reads', world.remove_reads), \
                mock.patch.object(read_set_record, 'observe_gone', world.observe_gone), \
                mock.patch.object(writer, 'end_session', world.end_session):
            result = launcher.end_outside(ROOT, SID, NOW, REC)
        self.assertEqual(result['result'], 'done')
        self.assertEqual(world.names(), ['session_leases', 'stored_reads TASK-1', 'observe_gone TASK-1',
                                         'remove_reads TASK-1', 'end_session'])

    def test_no_call_raises(self):
        """TASK-092 AC1: with every callee raising in turn, end_outside returns a mapping and never raises."""
        for name in launcher._OUTSIDE_CALLEES:
            world = World()
            world.raises[name] = RuntimeError(name)
            result = outside(world)
            self.assertEqual(tuple(result), launcher.OUTSIDE_KEYS)


class TASK092AC2Order(unittest.TestCase):
    def two(self):
        return World([row('TASK-2', EARLIER), row('TASK-1'), row('TASK-1')])

    def test_order(self):
        """TASK-092 AC2: rows in reverse str order, one task in two rows: each distinct task once, in str sorted
        order, stored_reads, observe_gone and remove_reads, then end_session once, after every record."""
        world = self.two()
        result = outside(world)
        self.assertEqual(world.names(), ['session_leases', 'stored_reads TASK-1', 'observe_gone TASK-1',
                                         'remove_reads TASK-1', 'stored_reads TASK-2', 'observe_gone TASK-2',
                                         'remove_reads TASK-2', 'end_session'])
        self.assertEqual((result['result'], result['reason']), ('done', None))

    def test_observe_gone_arguments(self):
        """TASK-092 AC2: observe_gone gets the task, the session, the reads as a list, GONE_WHY[2], now and exactly
        the recorder followed by the outside text, the session id and ", its lease row possibly unexpired"."""
        world = World()
        world.stored['TASK-1'] = R('done', ['src/a.py', 'src/b.py'])
        outside(world)
        call = [entry for entry in world.log if entry[0] == 'observe_gone'][0]
        self.assertEqual(call, ('observe_gone', 'TASK-1', SID, ['src/a.py', 'src/b.py'], read_set_record.GONE_WHY[2],
                                NOW, RECORDER_TEXT))
        self.assertEqual(read_set_record.GONE_WHY[2], 'no fencing token given')
        self.assertIs(type(call[3]), list)

    def test_records_lines(self):
        """TASK-092 AC2: the records lines for a written, a duplicate and a conflict (present) record, the conflict
        adding its finding."""
        world = World([row('TASK-1'), row('TASK-2'), row('TASK-3')])
        world.records['TASK-2'] = record('duplicate')
        world.records['TASK-3'] = conflict()
        world.removed['TASK-3'] = R('done', 0)
        result = outside(world)
        self.assertEqual(result['records'], ['TASK-1: record written, 1 reads removed',
                                             'TASK-2: record duplicate, 1 reads removed',
                                             'TASK-3: record conflict (present), 0 reads removed'])
        self.assertEqual(result['findings'],
                         ['TASK-3: record: a record is already present under its event id (conflict)'])
        self.assertEqual(result['result'], 'done')

    def test_failed_removal_line(self):
        """TASK-092 AC2: a failed removal gives "reads not removed" in the records line."""
        world = World()
        world.removed['TASK-1'] = R('refused', reason='no_store', findings=['no store'])
        result = outside(world)
        self.assertEqual(result['records'], ['TASK-1: record written, reads not removed'])
        self.assertEqual(result['findings'], ["TASK-1: remove_reads: remove_reads gave 'refused' ('no_store')",
                                              'no store'])

    def test_done_released(self):
        """TASK-092 AC2: "done" from end_session gives "done", reason None and released its task ids in order."""
        world = self.two()
        world.ended = R('done', [{'task_id': 'TASK-2', 'x': 1}, {'task_id': 'TASK-1'}])
        result = outside(world)
        self.assertEqual((result['result'], result['reason'], result['released']), ('done', None, ['TASK-2', 'TASK-1']))

    def test_released_not_among_rows(self):
        """TASK-092 AC2: a released task not among the rows read adds its finding."""
        world = World()
        world.ended = R('done', [{'task_id': 'TASK-1'}, {'task_id': 'TASK-9'}])
        result = outside(world)
        self.assertEqual(result['released'], ['TASK-1', 'TASK-9'])
        self.assertEqual(result['findings'],
                         ['end: TASK-9 released with no record (it was not among the rows read)'])

    def test_done_value_out_of_form(self):
        """TASK-092 AC2: a "done" value out of form gives "done", released [] and its finding."""
        for value in (None, {'task_id': 'TASK-1'}, [{'task': 'TASK-1'}], [{'task_id': 1}], ['TASK-1']):
            world = World()
            world.ended = R('done', value)
            result = outside(world)
            self.assertEqual((result['result'], result['released']), ('done', []), value)
            self.assertEqual(result['findings'], ["end: end_session's value is out of form"])

    def test_no_lease(self):
        """TASK-092 AC2: a session with no lease gives records [] with end_session still called."""
        world = World([])
        result = outside(world)
        self.assertEqual(world.names(), ['session_leases', 'end_session'])
        self.assertEqual((result['result'], result['records'], result['released']), ('done', [], []))


class TASK092AC3FailingClosed(unittest.TestCase):
    def assert_closed(self, result, reason, world):
        self.assertEqual((result['result'], result['reason'], result['released']), ('refused', reason, []))
        self.assertNotIn('end_session', world.names())

    def test_lease_rows_refused(self):
        """TASK-092 AC3: a refused session_leases answer, its "session" refusal included, gives "lease_rows" with its
        findings kept, nothing ended."""
        world = World()
        world.leases = R('refused', reason='session', findings=["the session 'x' was never started"])
        result = outside(world)
        self.assert_closed(result, 'lease_rows', world)
        self.assertEqual(result['findings'], ["lease_rows: session_leases gave 'refused' ('session')",
                                              "the session 'x' was never started"])

    def test_lease_rows_out_of_form(self):
        """TASK-092 AC3: a value out of form gives "lease_rows", nothing ended."""
        naive = datetime.datetime(2026, 10, 25, 13, 0, 0)
        values = [None, {'ended': False}, {'ended': 0, 'leases': []}, {'ended': False, 'leases': ()},
                  {'ended': False, 'leases': [{'task_id': 'TASK-1', 'expires_at': LATER}]},
                  {'ended': False, 'leases': [row('TASK-1', naive)]},
                  {'ended': False, 'leases': [row(5)]}, {'ended': False, 'leases': [row(['TASK-1'])]},
                  {'ended': False, 'leases': [row('task-1')]}, {'ended': False, 'leases': [row('TASK-1'), row(2)]}]
        for value in values:
            world = World()
            world.leases = R('done', value)
            result = outside(world)
            self.assert_closed(result, 'lease_rows', world)
            self.assertEqual(world.names(), ['session_leases'], value)

    def test_ended(self):
        """TASK-092 AC3: ended true gives "ended" and its one finding, nothing written or ended."""
        world = World(ended=True)
        result = outside(world)
        self.assert_closed(result, 'ended', world)
        self.assertEqual(result['findings'], ['ended: the session is already ended'])
        self.assertEqual(world.names(), ['session_leases'])

    def test_stored_reads_refused(self):
        """TASK-092 AC3: a refused stored_reads at the second task gives "stored_reads", its findings kept, the
        first task's records line kept, no call for a later task, nothing ended."""
        world = World([row('TASK-1'), row('TASK-2'), row('TASK-3')])
        world.stored['TASK-2'] = R('refused', reason='no_store', findings=['no store'])
        result = outside(world)
        self.assert_closed(result, 'stored_reads', world)
        self.assertEqual(result['records'], ['TASK-1: record written, 1 reads removed'])
        self.assertEqual(result['findings'], ["TASK-2: stored_reads: stored_reads gave 'refused' ('no_store')",
                                              'no store'])
        self.assertNotIn('stored_reads TASK-3', world.names())
        world = World()
        world.stored['TASK-1'] = R('done', ('a',))
        self.assert_closed(outside(world), 'stored_reads', world)

    def test_record_not_present(self):
        """TASK-092 AC3: a record not found present gives "record", its findings kept, no removal, nothing ended."""
        world = World([row('TASK-1'), row('TASK-2')])
        world.records['TASK-1'] = {'result': 'refused', 'reason': 'core', 'findings': ['bad'], 'record': None,
                                   'core': {'result': 'refused', 'reason': 'other'}}
        result = outside(world)
        self.assert_closed(result, 'record', world)
        self.assertEqual(result['findings'], ['TASK-1: record: the record was not found present', 'bad'])
        self.assertNotIn('remove_reads TASK-1', world.names())
        self.assertNotIn('stored_reads TASK-2', world.names())
        world = World()
        world.records['TASK-1'] = None
        self.assert_closed(outside(world), 'record', world)

    def test_raise_at_each_step(self):
        """TASK-092 AC3: a raise at lease_rows, stored_reads or record gives that step's reason, the step named,
        the earlier records lines kept, nothing ended."""
        for name, reason, text in (('session_leases', 'lease_rows', 'lease_rows: a step raised KeyError'),
                                   ('stored_reads', 'stored_reads', 'TASK-1: stored_reads: a step raised KeyError'),
                                   ('observe_gone', 'record', 'TASK-1: record: a step raised KeyError')):
            world = World()
            world.raises[name] = KeyError('k')
            result = outside(world)
            self.assert_closed(result, reason, world)
            self.assertEqual(result['findings'], [text])

    def test_raise_keeps_earlier_records(self):
        """TASK-092 AC3: a raise at the second task keeps the first task's records line."""
        world = World([row('TASK-1'), row('TASK-2')])
        calls = []

        def observe_gone(root, task_id, session_id, reads, reason, now, recorder):
            calls.append(task_id)
            if task_id == 'TASK-2':
                raise ValueError('v')
            return record()
        result = launcher.end_outside(ROOT, SID, NOW, REC, session_leases=world.session_leases,
                                      stored_reads=world.stored_reads, remove_reads=world.remove_reads,
                                      observe_gone=observe_gone, end_session=world.end_session)
        self.assert_closed(result, 'record', world)
        self.assertEqual(result['records'], ['TASK-1: record written, 1 reads removed'])
        self.assertEqual(result['findings'], ['TASK-2: record: a step raised ValueError'])

    def test_remove_reads_goes_on(self):
        """TASK-092 AC3: a refused or raising remove_reads is named and end_session is still called."""
        world = World()
        world.raises['remove_reads'] = OSError('o')
        result = outside(world)
        self.assertEqual(result['result'], 'done')
        self.assertEqual(result['findings'], ['TASK-1: remove_reads: a step raised OSError'])
        self.assertEqual(result['records'], ['TASK-1: record written, reads not removed'])
        self.assertEqual(world.names()[-1], 'end_session')

    def test_end_refused(self):
        """TASK-092 AC3: a refused end_session gives "end" with its findings."""
        world = World()
        world.ended = R('refused', reason='ended', findings=["the session 'x' was already ended"])
        result = outside(world)
        self.assertEqual((result['result'], result['reason'], result['released']), ('refused', 'end', []))
        self.assertEqual(result['findings'], ["end: end_session gave 'refused' ('ended')",
                                              "the session 'x' was already ended"])
        self.assertEqual(result['records'], ['TASK-1: record written, 1 reads removed'])

    def test_end_raises(self):
        """TASK-092 AC3: a raise in end_session gives "end" and the "may be ended" finding."""
        world = World()
        world.raises['end_session'] = ValueError('no store')
        result = outside(world)
        self.assertEqual((result['result'], result['reason']), ('refused', 'end'))
        self.assertEqual(result['findings'], ['end: a step raised ValueError; the session may be ended'])

    def test_no_own_finding_holds_the_root(self):
        """TASK-092 AC3: no finding end_outside makes itself holds the root."""
        results = [outside(World(), root='relative')]
        for name in launcher._OUTSIDE_CALLEES:
            world = World()
            world.raises[name] = RuntimeError(ROOT)
            results.append(outside(world))
        world = World()
        world.leases = R('refused', reason='root')
        results.append(outside(world))
        for result in results:
            self.assertFalse([f for f in result['findings'] if ROOT in f], result)


class EndStand:
    def __init__(self, answer=None, raises=None):
        self.calls = []
        self.answer = answer
        self.raises = raises

    def __call__(self, root, session_id, now, recorder):
        self.calls.append((root, session_id, now, recorder))
        if self.raises is not None:
            raise self.raises
        return self.answer


class Sink:
    def __init__(self):
        self.writes = []

    def write(self, text):
        self.writes.append(text)

    def flush(self):
        return None


class Clock:
    def __init__(self, raises=None):
        self.calls = 0
        self.raises = raises

    def __call__(self):
        self.calls += 1
        if self.raises is not None:
            raise self.raises
        return NOW


def answer(result='done', reason=None, findings=(), records=(), released=()):
    return {'result': result, 'reason': reason, 'findings': list(findings), 'records': list(records),
            'released': list(released)}


DONE = answer(findings=['f1'], records=['TASK-1: record written, 1 reads removed'], released=['TASK-1'])


def run_end(argv, given=DONE, raises=None, environ=None, clock=None):
    sink = Sink()
    clock = Clock() if clock is None else clock
    stand = EndStand(given, raises)
    with mock.patch.object(launcher, 'end_outside', stand):
        rc = cli.main(argv, sink, {} if environ is None else environ, clock)
    return rc, ''.join(sink.writes), stand, clock


def end(*flags):
    return ['end', SID, '--root', ROOT] + list(flags)


class TASK092AC4Command(unittest.TestCase):
    def test_refused_inside_a_runtime(self):
        """TASK-092 AC4: an environ holding any of RUNTIME_VARS gives exit 1 and the refusal, text or JSON, with
        neither the clock nor end_outside called."""
        for name in cli.RUNTIME_VARS:
            rc, out, stand, clock = run_end(end(), environ={name: ''})
            self.assertEqual((rc, out), (1, 'finding: end: refused inside a runtime (spec 7 :34)\n'))
            self.assertEqual((stand.calls, clock.calls), ([], 0))
            rc, out, stand, clock = run_end(end('--json'), environ={name: 'x'})
            self.assertEqual((rc, out), (1, '{"findings": ["end: refused inside a runtime (spec 7 :34)"]}\n'))
            self.assertEqual((stand.calls, clock.calls), ([], 0))

    def test_bad_argv_inside_a_runtime(self):
        """TASK-092 AC4: the parse comes first: a bad argv inside a runtime gives exit 2 and USAGE."""
        inside = {name: 'x' for name in cli.RUNTIME_VARS}
        for argv in (['end'], ['end', '.', '--root', ROOT], ['end', SID]):
            rc, out, stand, clock = run_end(argv, environ=inside)
            self.assertEqual((rc, out, stand.calls, clock.calls), (2, cli.USAGE, [], 0), argv)

    def test_accepted_forms(self):
        """TASK-092 AC4: "end S --root R" and with --json call end_outside once with R, S, the clock's value and
        'aieos cli end'."""
        for argv in (end(), end('--json'), ['end', SID, '--json', '--root', ROOT]):
            rc, out, stand, clock = run_end(argv)
            self.assertEqual(stand.calls, [(ROOT, SID, NOW, 'aieos cli end')], argv)
            self.assertEqual((rc, clock.calls), (0, 1))
        self.assertEqual(cli.RECORDER, 'aieos cli end')

    def test_usage_cases(self):
        """TASK-092 AC4: the out-of-form argvs of end give exit 2 and USAGE with nothing called."""
        cases = [['end'], ['end', '--root', ROOT], ['end', '.', '--root', ROOT], ['end', '..', '--root', ROOT],
                 ['end', '-x', '--root', ROOT], ['end', '', '--root', ROOT], ['end', 'a' * 129, '--root', ROOT],
                 ['end', 'a/b', '--root', ROOT], ['end', 's\n', '--root', ROOT], ['end', SID],
                 ['end', SID, '--root'], ['end', SID, 'extra', '--root', ROOT], ['End', SID, '--root', ROOT]]
        for argv in cases:
            rc, out, stand, clock = run_end(argv)
            self.assertEqual((rc, out, stand.calls, clock.calls), (2, cli.USAGE, [], 0), argv)

    def test_session_form(self):
        """TASK-092 AC4: a session of 128 characters is accepted; SESSION is the text of mcp_server._SESSION's
        pattern (D-3068)."""
        rc, out, stand, clock = run_end(['end', 'a' * 128, '--root', ROOT])
        self.assertEqual((rc, len(stand.calls)), (0, 1))
        self.assertEqual(cli.SESSION, mcp_server._SESSION.pattern)

    def test_done_text(self):
        """TASK-092 AC4: "done" gives exit 0 and the record, released and finding lines in that order."""
        rc, out, _, _ = run_end(end())
        self.assertEqual((rc, out), (0, 'record: TASK-1: record written, 1 reads removed\nreleased: TASK-1\n'
                                        'finding: f1\n'))

    def test_done_no_lease(self):
        """TASK-092 AC4: "done" with nothing released gives "ended, no lease released", not after the out-of-form
        value finding."""
        rc, out, _, _ = run_end(end(), given=answer())
        self.assertEqual((rc, out), (0, 'ended, no lease released\n'))
        rc, out, _, _ = run_end(end(), given=answer(findings=["end: end_session's value is out of form"]))
        self.assertEqual((rc, out), (0, "finding: end: end_session's value is out of form\n"))

    def test_done_json(self):
        """TASK-092 AC4: "done" under --json gives the one sorted JSON line of findings, records and released."""
        rc, out, _, _ = run_end(end('--json'))
        self.assertEqual((rc, out), (0, '{"findings": ["f1"], "records": ["TASK-1: record written, 1 reads removed"], '
                                        '"released": ["TASK-1"]}\n'))

    def test_refused(self):
        """TASK-092 AC4: a refused answer gives exit 1 and "end: <reason>", the record lines and its findings, in
        both forms."""
        given = answer('refused', 'record', ['TASK-2: record: the record was not found present'],
                       ['TASK-1: record written, 1 reads removed'])
        rc, out, _, _ = run_end(end(), given=given)
        self.assertEqual((rc, out), (1, 'finding: end: record\nfinding: record: TASK-1: record written, 1 reads '
                                        'removed\nfinding: TASK-2: record: the record was not found present\n'))
        rc, out, _, _ = run_end(end('--json'), given=given)
        self.assertEqual((rc, out), (1, '{"findings": ["end: record", "record: TASK-1: record written, 1 reads '
                                        'removed", "TASK-2: record: the record was not found present"]}\n'))

    def test_out_of_form_answers(self):
        """TASK-092 AC4: each out-of-form answer gives exit 1 and the out-of-form finding."""
        extra = dict(DONE)
        extra['more'] = 1
        missing = dict(DONE)
        del missing['records']
        cases = [None, [], extra, missing, answer('maybe'), answer('refused', None), dict(DONE, records='x'),
                 dict(DONE, released=[1]), dict(DONE, findings=(None,))]
        for given in cases:
            rc, out, _, _ = run_end(end(), given=given)
            self.assertEqual((rc, out), (1, 'finding: end: end_outside gave an answer out of form\n'), given)

    def test_raising_clock_or_end_outside(self):
        """TASK-092 AC4: a raising clock or end_outside gives exit 1 and "end: a step raised <type>"."""
        rc, out, stand, _ = run_end(end(), clock=Clock(raises=OSError('c')))
        self.assertEqual((rc, out, stand.calls), (1, 'finding: end: a step raised OSError\n', []))
        rc, out, _, _ = run_end(end(), raises=KeyError('k'))
        self.assertEqual((rc, out), (1, 'finding: end: a step raised KeyError\n'))


class TASK092AC5Modules(unittest.TestCase):
    def test_this_test_file(self):
        """TASK-092 AC5: this file imports no tempfile, sqlite3 or shutil, names no open, roots only the literal
        'C:/outside-root-92', and has no one-argument .replace() and no .replace(target=...)."""
        tree = ast.parse(HERE.read_bytes().decode('utf-8'))
        imported = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imported.update(a.name.split('.')[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                imported.add((n.module or '').split('.')[0])
        self.assertEqual(imported & {'tempfile', 'sqlite3', 'shutil'}, set())
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == 'open'])
        roots = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                 and len(n.value) > 3 and n.value.startswith('C:/')]
        self.assertEqual(set(roots), {ROOT})
        replaces = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == 'replace' and (len(n.args) == 1 or [k.arg for k in n.keywords] == ['target'])]
        self.assertEqual(replaces, [])

    def test_end_outside_names(self):
        """TASK-092 AC5: end_outside and its helpers name no open, os, sys, time or subprocess and read no attribute
        now, environ or getenv."""
        tree = ast.parse((SRC / 'launcher.py').read_bytes().decode('utf-8'))
        mine = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                and (n.name == 'end_outside' or n.name.startswith('_outside'))]
        self.assertEqual(len(mine), 6)
        names, attrs = set(), set()
        for node in mine:
            for n in ast.walk(node):
                if isinstance(n, ast.Name):
                    names.add(n.id)
                elif isinstance(n, ast.Attribute):
                    attrs.add(n.attr)
        self.assertEqual(names & {'open', 'os', 'sys', 'time', 'subprocess'}, set())
        self.assertEqual(attrs & {'open', 'now', 'environ', 'getenv'}, set())


class TASK092AC6Docs(unittest.TestCase):
    def test_launcher_docstring(self):
        """TASK-092 AC6: launcher.py's docstring holds the paragraph's phrases and the two reworded sentences."""
        text = ' '.join(ast.get_docstring(ast.parse((SRC / 'launcher.py').read_bytes().decode('utf-8'))).split())
        for phrase in ('end_outside', 'aieos end', 'the record before the release', 'no fencing token given',
                       'no lease is released before its record', 'possibly unexpired', 'TASK-092',
                       'four call places', 'at the next start', 'before the expiry', 'or `aieos end` ends it'):
            self.assertIn(phrase, text)
        for phrase in ('writes no observed read-set record', 'three call places'):
            self.assertNotIn(phrase, text)

    def test_cli_docstring(self):
        """TASK-092 AC6: cli.py's docstring names end and no longer holds the two replaced phrases."""
        text = ' '.join(ast.get_docstring(ast.parse((SRC / 'cli.py').read_bytes().decode('utf-8'))).split())
        for phrase in ('end <session>', 'refused inside a runtime', 'TASK-092'):
            self.assertIn(phrase, text)
        for phrase in ('whose only entry is tasks', 'come with later tasks'):
            self.assertNotIn(phrase, text)

    def test_usage_names_end(self):
        """TASK-092 AC6: USAGE names end and its session, and ends with LF."""
        self.assertIn('end <session>', cli.USAGE)
        self.assertTrue(cli.USAGE.endswith('\n'))

    def test_every_test_names_its_criteria(self):
        """TASK-092 AC6: every test function of this module names "TASK-092 AC" in its own docstring, more than 30
        in all."""
        tree = ast.parse(HERE.read_bytes().decode('utf-8'))
        tests = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
        self.assertGreater(len(tests), 30)
        for node in tests:
            self.assertIn('TASK-092 AC', ast.get_docstring(node) or '', node.name)


if __name__ == '__main__':
    unittest.main()

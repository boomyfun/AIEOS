"""Unit tests of launcher.launch_outside and the command launch of cli.py (task TASK-094; specification 7 section 3
:34-35, sections 5 and 7). launch_outside's callees (begin, contract_at, finish, finish_outside, write_handoff), its
clock and its starter are stand-ins passed as keyword arguments, or patched through mock.patch.object for the
defaults, each restored after its test; the command's launch_outside is patched the same way. No process starts, no
runtime starts and no file is written; the only files read are the package's own launcher.py, cli.py and
handoff_file.py and this file, with pathlib's read_bytes, for the ast checks; the root is a literal Windows path that
names no folder. Stand-in defaults are sentinels, never a value a case passes (L-0033). Each test names its criteria in
its own docstring."""

import ast
import datetime
import pathlib
import unittest
from collections import OrderedDict
from unittest import mock

from aieos_bootstrap import base_inputs, claude_code_channel, cli, handoff_file, launcher

HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / 'src' / 'aieos_bootstrap'
ROOT = 'C:/launch-root-94'
TASK = 'TASK-1'
NOW = datetime.datetime(2026, 10, 25, 12, 0, 0, tzinfo=datetime.timezone.utc)
SESSION = 'launch-abc'
HEAD = 'a' * 40
TOKEN = {'epoch': 'e1', 'counter': 1}
ENV = {'AIEOS_SESSION_ID': SESSION, 'AIEOS_ROOT': ROOT, 'AIEOS_BASE': HEAD}
PATHS = ['src/aieos_bootstrap/mod.py', 'tests/unit/**']
RECORDER = 'aieos cli launch for session ' + SESSION
GOOD = object()


def granted(**over):
    out = {'result': 'granted', 'reason': None, 'findings': ['gone_records: one line'], 'session_id': SESSION,
           'head_commit': HEAD, 'decision': 'CONTINUE', 'fencing_token': dict(TOKEN), 'environment': dict(ENV),
           'start': None, 'end': None}
    out.update(over)
    return out


def contract(paths=GOOD):
    return ({'task': TASK, 'write_set': {'paths': list(PATHS) if paths is GOOD else paths}}, 'f' * 64), None


def ended(result='done', reason=None, findings=('end: a line',)):
    return {'result': result, 'reason': reason, 'findings': list(findings), 'path': 'fenced', 'record': None,
            'removed': None, 'end': None}


def handoff(result='written', reason=None, findings=()):
    return {'result': result, 'reason': reason, 'findings': list(findings), 'path': None}


class World:
    """The stand-ins of launch_outside: each records its call in order and gives its answer, or raises."""

    def __init__(self, begin=GOOD, contract_at=GOOD, finish=GOOD, finish_outside=GOOD, write_handoff=GOOD,
                 starter=None, clocks=GOOD):
        self.answers = {'begin': granted() if begin is GOOD else begin,
                        'contract_at': contract() if contract_at is GOOD else contract_at,
                        'finish': ended() if finish is GOOD else finish,
                        'finish_outside': ended() if finish_outside is GOOD else finish_outside,
                        'write_handoff': handoff() if write_handoff is GOOD else write_handoff,
                        'starter': None if starter is None else starter}
        self.clocks = [NOW, NOW + datetime.timedelta(minutes=5)] if clocks is GOOD else list(clocks)
        self.calls = []

    def _give(self, name, args):
        self.calls.append((name, args))
        answer = self.answers[name]
        if isinstance(answer, BaseException):
            raise answer
        return answer

    def clock(self):
        self.calls.append(('clock', ()))
        value = self.clocks.pop(0) if len(self.clocks) > 1 else self.clocks[0]
        if isinstance(value, BaseException):
            raise value
        return value

    def begin(self, *args):
        return self._give('begin', args)

    def contract_at(self, *args):
        return self._give('contract_at', args)

    def finish(self, *args):
        return self._give('finish', args)

    def finish_outside(self, *args):
        return self._give('finish_outside', args)

    def write_handoff(self, *args):
        return self._give('write_handoff', args)

    def starter(self, *args):
        return self._give('starter', args)

    def names(self):
        return [name for name, _ in self.calls]

    def args(self, name):
        return [args for n, args in self.calls if n == name]


def launch(world, **over):
    kw = {'begin': world.begin, 'contract_at': world.contract_at, 'finish': world.finish,
          'finish_outside': world.finish_outside, 'write_handoff': world.write_handoff}
    kw.update(over)
    return launcher.launch_outside(ROOT, TASK, world.clock, world.starter, **kw)


ORDER = ['clock', 'begin', 'contract_at', 'starter', 'clock', 'finish', 'write_handoff']


class TASK094AC1Composition(unittest.TestCase):
    def test_the_order_and_the_result(self):
        """TASK-094 AC1: a grant gives clock, begin, contract_at, starter, clock, finish and write_handoff once each in
        that order, no finish_outside, and "done" with exactly LAUNCH_KEYS, the callees' dicts and run "returned"."""
        world = World()
        out = launch(world)
        self.assertEqual(world.names(), ORDER)
        self.assertEqual(tuple(out), launcher.LAUNCH_KEYS)
        self.assertEqual((out['result'], out['reason'], out['session_id'], out['run']), ('done', None, SESSION,
                                                                                         'returned'))
        self.assertEqual((out['start'], out['end'], out['handoff']), (granted(), ended(), handoff()))
        self.assertEqual(out['findings'], ['gone_records: one line', 'end: a line'])

    def test_the_arguments(self):
        """TASK-094 AC1: begin, contract_at, finish and write_handoff get the contract's arguments: max_risk None,
        the lease of LAUNCH_LEASE, the grant's head, the contract's paths, the allowlist [] and commit None."""
        world = World()
        launch(world)
        later = NOW + datetime.timedelta(minutes=5)
        self.assertEqual(world.args('begin'), [(ROOT, ROOT, TASK, 'claude_code', None, 'aieos cli launch',
                                                'aieos cli launch', NOW, NOW + launcher.LAUNCH_LEASE)])
        self.assertEqual(world.args('contract_at'), [(ROOT, HEAD, TASK)])
        self.assertEqual(world.args('finish'), [(ROOT, TASK, SESSION, TOKEN, later, PATHS, [], RECORDER)])
        self.assertEqual(world.args('write_handoff'), [(ROOT, TASK, SESSION, None)])
        self.assertEqual(launcher.LAUNCH_LEASE, datetime.timedelta(hours=2))

    def test_the_starter_gets_a_copy(self):
        """TASK-094 AC1: the starter is called once with a copy of the grant's environment, equal and not the same
        object."""
        answer = granted()
        world = World(begin=answer)
        launch(world)
        (args,) = world.args('starter')
        self.assertEqual(args, (ENV,))
        self.assertIsNot(args[0], answer['environment'])

    def test_the_callees_default_at_call_time(self):
        """TASK-094 AC1: with no callee given, the mock.patch.object stand-ins of launcher.start, launcher.end,
        launcher.end_outside, base_inputs.contract_at and handoff_file.write made after import are the ones
        called."""
        world = World()
        with mock.patch.object(launcher, 'start', world.begin), mock.patch.object(launcher, 'end', world.finish), \
                mock.patch.object(launcher, 'end_outside', world.finish_outside), \
                mock.patch.object(base_inputs, 'contract_at', world.contract_at), \
                mock.patch.object(handoff_file, 'write', world.write_handoff):
            out = launcher.launch_outside(ROOT, TASK, world.clock, world.starter)
        self.assertEqual((out['result'], world.names()), ('done', ORDER))

    def test_none_for_steps_not_reached(self):
        """TASK-094 AC1: a step not reached leaves its key None: a start not granted gives run, end and handoff
        None."""
        out = launch(World(begin=granted(result='not granted', reason='decision')))
        self.assertEqual((out['run'], out['end'], out['handoff'], out['session_id']), (None, None, None, None))


class TASK094AC2Failures(unittest.TestCase):
    def test_wrong_arguments(self):
        """TASK-094 AC2: a root not an absolute Windows path, a task_id out of form, a clock or a starter not
        callable, or a callee neither None nor callable gives "argument" with nothing called."""
        world = World()
        cases = [dict(root='relative/root'), dict(root=3), dict(task_id='task-1'), dict(clock=None),
                 dict(starter='x'), dict(begin=3), dict(write_handoff='w')]
        for case in cases:
            args = {'root': ROOT, 'task_id': TASK, 'clock': world.clock, 'starter': world.starter}
            callees = {}
            for k, v in case.items():
                (args if k in args else callees)[k] = v
            out = launcher.launch_outside(args['root'], args['task_id'], args['clock'], args['starter'], **callees)
            self.assertEqual((out['result'], out['reason']), ('refused', 'argument'), case)
        self.assertEqual(world.calls, [])

    def test_a_bad_clock(self):
        """TASK-094 AC2: a raising clock, a naive time or one with microseconds gives "clock" with nothing else
        called."""
        for value in (RuntimeError('c'), NOW.replace(tzinfo=None), NOW.replace(microsecond=5)):
            world = World(clocks=[value])
            out = launch(world)
            self.assertEqual((out['reason'], world.names()), ('clock', ['clock']), value)

    def test_start_not_granted(self):
        """TASK-094 AC2: begin giving "not granted", "refused", a non-dict or a raise gives that outcome with reason
        "start", "start" None for the non-dict and the raise, and no other callee called."""
        cases = [(granted(result='not granted', reason='decision'), 'not granted', True),
                 (granted(result='refused', reason='head'), 'refused', True),
                 (['granted'], 'refused', False), (RuntimeError('b'), 'refused', False)]
        for answer, result, kept in cases:
            world = World(begin=answer)
            out = launch(world)
            self.assertEqual((out['result'], out['reason'], world.names()), (result, 'start', ['clock', 'begin']))
            self.assertEqual(out['start'] is not None, kept)

    def test_a_granted_answer_out_of_form(self):
        """TASK-094 AC2: a granted answer whose session_id, fencing_token, head_commit or environment is out of form
        gives reason "start", no starter, and one finish_outside call when session_id is a str."""
        cases = [granted(fencing_token=None), granted(head_commit='x'), granted(environment={'AIEOS_ROOT': ROOT}),
                 granted(environment=dict(ENV, AIEOS_BASE=3))]
        for answer in cases:
            world = World(begin=answer)
            out = launch(world)
            self.assertEqual((out['reason'], world.names()), ('start', ['clock', 'begin', 'clock', 'finish_outside',
                                                                        'write_handoff']))
            self.assertEqual(world.args('finish_outside')[0][1:2], (SESSION,))
        world = World(begin=granted(session_id=3))
        out = launch(world)
        self.assertEqual((out['reason'], world.names()), ('start', ['clock', 'begin']))

    def test_contract_failures(self):
        """TASK-094 AC2: contract_at findings, a raise, an answer out of form, an empty paths list, or a path outside
        _LAUNCH_PATH or with an empty segment give reason "contract", no starter, no finish and one finish_outside."""
        cases = [(None, ['no file']), RuntimeError('r'), 'x', contract(paths=[]), contract(paths=['a b']),
                 contract(paths=['x//y']), contract(paths=['/x']), contract(paths='src/a.py'), contract(paths=[3]),
                 (contract()[0], ['x'])]
        for answer in cases:
            world = World(contract_at=answer)
            out = launch(world)
            self.assertEqual((out['reason'], world.names()), ('contract', ['clock', 'begin', 'contract_at', 'clock',
                                                                           'finish_outside', 'write_handoff']),
                             answer)
            self.assertEqual(world.args('finish_outside'), [(ROOT, SESSION, NOW + datetime.timedelta(minutes=5),
                                                             RECORDER)])

    def test_a_raising_starter(self):
        """TASK-094 AC2: a starter raising an Exception gives "run" with finish and write_handoff still called."""
        world = World(starter=ValueError('s'))
        out = launch(world)
        self.assertEqual((out['reason'], out['run'], world.names()), ('run', 'raised ValueError', ORDER))
        self.assertIn('run: the starter raised ValueError', out['findings'])

    def test_a_keyboard_interrupt(self):
        """TASK-094 AC2: a starter raising KeyboardInterrupt has finish and write_handoff called, then the
        KeyboardInterrupt re-raised."""
        world = World(starter=KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):
            launch(world)
        self.assertEqual(world.names(), ORDER)

    def test_finish_refused_before_any_release(self):
        """TASK-094 AC2: finish refused with reason "argument" or "record" is followed by one finish_outside call,
        whose answer is in "end"."""
        for reason in ('argument', 'record'):
            outside = ended(findings=('outside: a line',))
            world = World(finish=ended('refused', reason, ('record: not present',)), finish_outside=outside)
            out = launch(world)
            self.assertEqual(world.names(), ORDER[:-1] + ['finish_outside', 'write_handoff'])
            self.assertEqual((out['end'], out['reason']), (outside, 'end'))
            self.assertIn('record: not present', out['findings'])

    def test_finish_held_or_lease_rows(self):
        """TASK-094 AC2: finish refused "held" or "lease_rows" is followed by no finish_outside and no write_handoff,
        with reason "end" and the "handoff: not written" finding."""
        for reason in ('held', 'lease_rows'):
            world = World(finish=ended('refused', reason))
            out = launch(world)
            self.assertEqual(world.names(), ORDER[:-1])
            self.assertEqual((out['reason'], out['handoff']), ('end', None))
            self.assertIn("handoff: not written, the session's end was not done", out['findings'])

    def test_an_end_not_done(self):
        """TASK-094 AC2: a raising finish or a non-dict answer gives "end" None, reason "end" and no write_handoff."""
        for answer in (RuntimeError('f'), ['done']):
            world = World(finish=answer)
            out = launch(world)
            self.assertEqual((out['reason'], out['end'], world.names()), ('end', None, ORDER[:-1]))

    def test_handoff_failures(self):
        """TASK-094 AC2: write_handoff "refused", a raise or a non-dict gives reason "handoff"."""
        for answer, kept in ((handoff('refused', 'claims'), True), (RuntimeError('h'), False), ('written', False)):
            out = launch(World(write_handoff=answer))
            self.assertEqual((out['result'], out['reason'], out['handoff'] is not None), ('refused', 'handoff', kept))

    def test_a_bad_second_clock(self):
        """TASK-094 AC2: a raising second clock read gives a "clock:" finding and the first time for the end; no
        Exception escapes."""
        world = World(clocks=[NOW, RuntimeError('c2'), NOW])
        out = launch(world)
        self.assertEqual(world.args('finish')[0][4], NOW)
        self.assertIn('clock: the clock raised RuntimeError', out['findings'])

    def test_what_launch_outside_names(self):
        """TASK-094 AC2: by ast, launch_outside and the names beginning _launch name no open, exec, eval, compile,
        __import__, subprocess, os, sys or time."""
        tree = ast.parse((SRC / 'launcher.py').read_bytes().decode('utf-8'))
        mine = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                and (n.name == 'launch_outside' or n.name.startswith('_launch'))]
        self.assertGreater(len(mine), 5)
        names = {x.id for n in mine for x in ast.walk(n) if isinstance(x, ast.Name)}
        self.assertEqual(names & {'open', 'exec', 'eval', 'compile', '__import__', 'subprocess', 'os', 'sys',
                                  'time'}, set())


class TASK094AC3Handoff(unittest.TestCase):
    def test_the_handoff_docstring(self):
        """TASK-094 AC3: handoff_file's docstring holds "calls write after the launcher", not "nothing calls write
        but its tests", and no project-state directory name."""
        doc = ' '.join(handoff_file.__doc__.split())
        self.assertIn('calls write after the launcher', doc)
        self.assertNotIn('nothing calls write but its tests', doc)
        self.assertNotIn('.' + 'aieos', doc)


class Sink:
    def __init__(self):
        self.writes = []

    def write(self, text):
        self.writes.append(text)

    def flush(self):
        pass


class Clock:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return NOW


def answer(result='done', reason=None, findings=GOOD, session_id=SESSION, start=GOOD, run='returned', end=GOOD,
           handoff_answer=GOOD):
    return {'result': result, 'reason': reason, 'findings': ['f'] if findings is GOOD else findings,
            'session_id': session_id, 'start': granted() if start is GOOD else start, 'run': run,
            'end': ended() if end is GOOD else end, 'handoff': handoff() if handoff_answer is GOOD else handoff_answer}


class Stand:
    """launcher.launch_outside as a stand-in: gives its answer, or raises, and records each call."""

    def __init__(self, given=GOOD, raises=None):
        self.answer = answer() if given is GOOD else given
        self.raises = raises
        self.calls = []

    def __call__(self, root, task_id, clock, starter):
        self.calls.append((root, task_id, clock, starter))
        if self.raises is not None:
            raise self.raises
        return self.answer


def starter(environment):
    return None


def run(argv, given=GOOD, raises=None, environ=None, with_starter=True):
    sink, clock = Sink(), Clock()
    stand = Stand(given, raises)
    kw = {'starter': starter} if with_starter else {}
    with mock.patch.object(launcher, 'launch_outside', stand):
        rc = cli.main(argv, sink, {} if environ is None else environ, clock, **kw)
    return rc, ''.join(sink.writes), stand, clock


def cmd(*flags):
    return ['launch', TASK, '--root', ROOT] + list(flags)


TEXT = 'session: launch-abc\nrun: returned\nend: done\nhandoff: written\nfinding: f\n'
JSON = '{"findings": ["f"], "session_id": "launch-abc"}\n'


class SubDict(dict):
    pass


class TASK094AC4Command(unittest.TestCase):
    def test_no_starter(self):
        """TASK-094 AC4: with no starter (main's default) "launch TASK-1 --root R" gives exit 1 and the one finding
        NO_STARTER, with neither the clock nor launch_outside called."""
        rc, out, stand, clock = run(cmd(), with_starter=False)
        self.assertEqual((rc, out, stand.calls, clock.calls), (1, 'finding: %s\n' % cli.NO_STARTER, [], 0))

    def test_one_call_with_a_starter(self):
        """TASK-094 AC4: with a starter, one launch_outside call with the root, the task, the clock and the
        starter."""
        for argv in (cmd(), cmd('--json'), ['launch', TASK, '--json', '--root', ROOT]):
            rc, _, stand, clock = run(argv)
            self.assertEqual((rc, stand.calls), (0, [(ROOT, TASK, clock, starter)]), argv)

    def test_usage_errors(self):
        """TASK-094 AC4: "launch", "launch --root R", "launch TASK-1", "launch task-1 --root R", "launch TASK-1 --root
        R extra" and "launch TASK-1 --root R --json --json" give exit 2 and USAGE with nothing called, inside a
        runtime too."""
        bad = (['launch'], ['launch', '--root', ROOT], ['launch', TASK], ['launch', 'task-1', '--root', ROOT],
               cmd('extra'), cmd('--json', '--json'))
        for environ in ({}, {'AIEOS_ROOT': 'x'}):
            for argv in bad:
                rc, out, stand, clock = run(argv, environ=environ)
                self.assertEqual((rc, out, stand.calls, clock.calls), (2, cli.USAGE, [], 0), (argv, environ))

    def test_refused_inside_a_runtime(self):
        """TASK-094 AC4: an environ holding any one of the three RUNTIME_VARS, '' included, gives exit 1 and
        LAUNCH_RUNTIME_REFUSAL with nothing called, starter given or not."""
        line = 'finding: %s\n' % cli.LAUNCH_RUNTIME_REFUSAL
        for name in cli.RUNTIME_VARS:
            for value in ('x', ''):
                for with_starter in (True, False):
                    rc, out, stand, clock = run(cmd(), environ={name: value}, with_starter=with_starter)
                    self.assertEqual((rc, out, stand.calls, clock.calls), (1, line, [], 0), (name, value))

    def test_done_lines(self):
        """TASK-094 AC4: "done" gives exit 0 and the four lines, then one "finding:" line per finding."""
        self.assertEqual(run(cmd())[:2], (0, TEXT))

    def test_the_json_line(self):
        """TASK-094 AC4: under --json "done" gives exactly '{"findings": [...], "session_id": "..."}'."""
        self.assertEqual(run(cmd('--json'))[:2], (0, JSON))

    def test_refused_and_not_granted(self):
        """TASK-094 AC4: "not granted" and "refused" give exit 1 and "finding: launch: <result> <reason>" then the
        findings, among them a refused end and a refused handoff."""
        cases = [(answer('not granted', 'start', ['start: not granted decision'], None, start=None, run=None,
                         end=None, handoff_answer=None), 'not granted start'),
                 (answer('refused', 'end', ['end: refused held'], end=ended('refused', 'held'), handoff_answer=None),
                  'refused end'),
                 (answer('refused', 'handoff', ['h'], handoff_answer=handoff('refused', 'claims')), 'refused handoff')]
        for given, head in cases:
            rc, out, _, _ = run(cmd(), given=given)
            lines = ['finding: launch: %s' % head] + ['finding: %s' % f for f in given['findings']]
            self.assertEqual((rc, out), (1, ''.join(line + '\n' for line in lines)))

    def test_answers_out_of_form(self):
        """TASK-094 AC4: each answer out of form gives exit 1 and the out-of-form finding."""
        good = answer()
        bad = [None, 'done', [good], SubDict(good), OrderedDict(good), dict(good, extra=1),
               {k: v for k, v in good.items() if k != 'run'}, dict(good, result='other'), dict(good, reason='r'),
               dict(good, session_id=None), dict(good, start=granted(result='refused')), dict(good, run='raised X'),
               dict(good, end=ended('refused', 'end')), dict(good, handoff=handoff('refused')),
               dict(good, start=['x']), dict(good, end='done'), dict(good, run='other'),
               answer('refused', 'other'), answer('refused', 3), dict(good, findings=[3]), dict(good, findings=('f',)),
               answer('refused', 'end', ['e'], end=ended('refused', 'held'), handoff_answer='written'),
               answer('refused', 'start', ['s'], None, start='granted', run=None, end=None, handoff_answer=None)]
        for given in bad:
            with self.subTest(given=given):
                rc, out, _, _ = run(cmd(), given=given)
                self.assertEqual((rc, out), (1, 'finding: %s\n' % cli.LAUNCH_OUT_OF_FORM))

    def test_a_raising_launch_outside(self):
        """TASK-094 AC4: a raising launch_outside gives "launch: a step raised <type>"."""
        rc, out, _, _ = run(cmd(), raises=MemoryError())
        self.assertEqual((rc, out), (1, 'finding: launch: a step raised MemoryError\n'))

    def test_a_raising_render(self):
        """TASK-094 AC4: a raising _render_launch (patched) gives exit 1 and "cli: a step raised <type>"."""
        with mock.patch.object(cli, '_render_launch', mock.Mock(side_effect=ValueError('render'))):
            rc, out, _, _ = run(cmd())
        self.assertEqual((rc, out), (1, 'finding: cli: a step raised ValueError\n'))


def used_names(node):
    return ({n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            | {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)})


def function(name, file_name):
    tree = ast.parse((SRC / file_name).read_bytes().decode('utf-8'))
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name][0]


class TASK094AC5Modules(unittest.TestCase):
    def test_the_path_pattern(self):
        """TASK-094 AC5: launcher._LAUNCH_PATH's pattern equals claude_code_channel._PATTERN's."""
        self.assertEqual(launcher._LAUNCH_PATH.pattern, claude_code_channel._PATTERN.pattern)

    def test_the_command_functions(self):
        """TASK-094 AC5: by ast, cli.py's _launch, _render_launch and _launch_in_form name no writer, held_leases or
        handoff_file."""
        for name in ('_launch', '_render_launch', '_launch_in_form'):
            self.assertFalse(used_names(function(name, 'cli.py')) & {'writer', 'held_leases', 'handoff_file'}, name)

    def test_this_test_file(self):
        """TASK-094 AC5: this file imports no tempfile, sqlite3, shutil or subprocess, names no open, roots only the
        literal 'C:/launch-root-94', and has no one-argument .replace() and no .replace(target=...)."""
        tree = ast.parse(HERE.read_bytes().decode('utf-8'))
        imported = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imported.update(a.name.split('.')[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                imported.add((n.module or '').split('.')[0])
        self.assertEqual(imported & {'tempfile', 'sqlite3', 'shutil', 'subprocess'}, set())
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == 'open'])
        roots = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                 and len(n.value) > 3 and n.value.startswith('C:/')]
        self.assertEqual(set(roots), {ROOT})
        replaces = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == 'replace' and (len(n.args) == 1 or [k.arg for k in n.keywords] == ['target'])]
        self.assertEqual(replaces, [])


def doc(file_name):
    return ' '.join(ast.get_docstring(ast.parse((SRC / file_name).read_bytes().decode('utf-8'))).split())


class TASK094AC6Docs(unittest.TestCase):
    def test_the_launcher_docstring(self):
        """TASK-094 AC6: launcher.py's docstring holds the paragraph's six phrases."""
        text = doc('launcher.py')
        for phrase in ('launch_outside', 'TASK-094', 'no starter', 'max_risk None', "reads the caller's clock",
                       'end_outside'):
            self.assertIn(phrase, text)

    def test_the_cli_docstring_and_usage(self):
        """TASK-094 AC6, as TASK-096 AC6 and TASK-097 AC6 widen it: cli.py's docstring holds "aieos launch",
        "TASK-094", "no runtime starter", "COMMANDS, tasks, end, status, init, launch, approve, edit, reject or import"
        and "end and init call it after the parse", and not "COMMANDS, tasks, end, status or init", "COMMANDS, tasks,
        end, status, init or launch", "COMMANDS, tasks, end, status, init, launch, approve, edit or reject" nor "comes
        with a later task"; USAGE names launch."""
        text = doc('cli.py')
        for phrase in ('aieos launch', 'TASK-094', 'no runtime starter',
                       'COMMANDS, tasks, end, status, init, launch, approve, edit, reject or import',
                       'end and init call it after the parse'):
            self.assertIn(phrase, text)
        for phrase in ('COMMANDS, tasks, end, status or init', 'COMMANDS, tasks, end, status, init or launch',
                       'COMMANDS, tasks, end, status, init, launch, approve, edit or reject',
                       'comes with a later task'):
            self.assertNotIn(phrase, text)
        self.assertIn('launch <task> --root <path> [--json]', cli.USAGE)

    def test_every_test_names_its_criteria(self):
        """TASK-094 AC6: every test function of this module names "TASK-094 AC" in its own docstring, more than 20
        in all."""
        tree = ast.parse(HERE.read_bytes().decode('utf-8'))
        tests = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
        self.assertGreater(len(tests), 20)
        for node in tests:
            self.assertIn('TASK-094 AC', ast.get_docstring(node) or '', node.name)


if __name__ == '__main__':
    unittest.main()

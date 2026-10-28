"""Unit tests of launcher.import_task and of the command import of cli.py (task TASK-097; specification 7 section 3
:29, specification 2 sections 3 and 5.1). import_task's callees (read, read_log, write_contract, append) are
stand-ins given as keyword arguments, over event logs built in memory with eventlog.append, the append stand-in bound
to writer.append_event's signature; the command is run by mock.patch.object of launcher.import_task, restored after
each test. No test writes a file, runs Git or starts a process; the only files read are the package's own
launcher.py and cli.py and this file, with pathlib's read_bytes, for the ast checks; the root is a literal Windows
path that names no folder (L-0032). Stand-in defaults are sentinels, never a value a case passes (L-0033). Each test
names its criteria in its own docstring."""

import ast
import datetime
import hashlib
import inspect
import json
import pathlib
import unittest
from collections import OrderedDict
from unittest import mock

from aieos_bootstrap import base_inputs, cli, eventlog, gitread, launcher, records, task_contract, writer

REAL_APPEND_EVENT = writer.append_event
APPEND_SIGNATURE = inspect.signature(REAL_APPEND_EVENT)
HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / 'src' / 'aieos_bootstrap'
ROOT = 'C:/import-root-97'
NOW = datetime.datetime(2026, 10, 28, 9, 0, 0, tzinfo=datetime.timezone.utc)
TASK = 'TASK-7'
OTHER = 'TASK-1'
HEAD = 'c' * 40
GOOD = object()
KEYS = ('task', 'contract_version', 'task_type', 'objective', 'traces_to', 'input_state', 'write_set', 'read_set',
        'forbidden', 'constitution', 'acceptance_criteria', 'capabilities', 'risk', 'autonomy', 'verification_plan',
        'exit_conditions', 'owner_kept_act')


def expected(task=TASK, head=HEAD):
    """The template filled with the task and the head, written out line by line."""
    lines = [
        'task: ' + task,
        'contract_version: v1',
        'task_type: drafting',
        'objective: >-',
        '  Read the repository and draft an architecture proposal and a constitution change request, proposing only '
        'and',
        '  changing nothing else.',
        'traces_to: []',
        'input_state:',
        '  base_commit: ' + head,
        '  depends_on: []',
        '  intent_versions: {}',
        'write_set:',
        '  paths:',
        '    - docs/proposals/ARCH-001.md',
        '    - docs/proposals/CHG-001.md',
        'read_set:',
        '  paths:',
        '    - "**"',
        '  interfaces: []',
        '  schemas: []',
        'forbidden:',
        '  - .aieos/**',
        'constitution: []',
        'acceptance_criteria:',
        '  - AC1: >-',
        "      docs/proposals/ARCH-001.md is an architecture proposal in specification 2 section 4.2's form.",
        '  - AC2: >-',
        "      docs/proposals/CHG-001.md is a change request in specification 2 section 4.3's form naming the "
        'constitution as a',
        '      target with no current version, a new entity.',
        '  - AC3: >-',
        '      No other path is changed.',
        'capabilities:',
        '  filesystem: {read: [the repository at base_commit], write: [the write_set paths]}',
        '  shell: {allow: []}',
        '  network: {allow: []}',
        '  git: {allow: [commit], forbid: [push, "push --force", rebase, "reset --hard", tag]}',
        '  secrets: deny',
        '  external_side_effects: deny',
        'risk: critical',
        'autonomy:',
        '  max_level: L1',
        '  budgets: {tokens: 400k, wall_time: 2h, retries: 1, human_attention: 0m}',
        'verification_plan:',
        '  - {gate: G0, check: scope}',
        '  - {gate: G3, check: review, args: [AC1, AC2, AC3]}',
        'exit_conditions:',
        '  success: both proposals present in their forms and nothing else changed',
        '  escalate: [needs_out_of_scope_change, needs_owner_act]',
        'owner_kept_act: true',
    ]
    return ''.join(line + '\n' for line in lines)


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def event_id_of(task, h):
    return hashlib.sha256('\n'.join(('import-event', 'task.drafted', task, h)).encode('utf-8')).hexdigest()


HASH = digest(expected())
EID = event_id_of(TASK, HASH)
PATH = '.aieos/tasks/%s.yaml' % TASK
STUCK = 'append: the contract %s (%s) is written, the task.drafted is not' % (PATH, HASH)


class Log:
    """An event log kept as bytes; every line is decided by eventlog.append."""

    def __init__(self):
        self.data = b''
        self.n = 0

    def add(self, event_type, payload, task_id=OTHER):
        self.n += 1
        r = eventlog.append(self.data, event_type, payload, 'ev-%d' % self.n, NOW, task_id=task_id)
        if r.result != 'appended':
            raise ValueError(r.findings)
        self.data += r.line
        return self

    def drafted(self, task_id=OTHER):
        return self.add('task.drafted', {'contract_version': 'v1', 'contract_hash': 'a' * 64}, task_id)


def with_duplicate(data):
    """The log with its last line repeated as an ignored duplicate (the same event, the next seq)."""
    obj = json.loads(data.splitlines()[-1].decode('ascii'))
    obj['seq'] += 1
    return data + (json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode('ascii')


class World:
    """The callees of import_task as stand-ins: read gives HEAD, read_log the log bytes, write_contract "done" with
    the task's path, append decides with eventlog.append over the log and keeps the line."""

    def __init__(self, log=None, read=GOOD, write=GOOD, refuse=False, raise_on=()):
        self.data = (Log().drafted() if log is None else log).data
        self.read_answer = {'exit': 0, 'out': (HEAD + '\n').encode('ascii'), 'err': b'', 'error': None} \
            if read is GOOD else read
        self.write_answer = write
        self.refuse = refuse
        self.raise_on = raise_on
        self.calls = []

    def names(self):
        return [c[0] for c in self.calls]

    def read(self, repo, args, timeout):
        self.calls.append(('read', repo, tuple(args)))
        if 'read' in self.raise_on:
            raise OSError('read')
        return self.read_answer

    def read_log(self, root):
        self.calls.append(('read_log', root))
        if 'read_log' in self.raise_on:
            raise OSError('read_log')
        return self.data

    def write_contract(self, root, task_id, text):
        self.calls.append(('write_contract', root, task_id, text))
        if 'write_contract' in self.raise_on:
            raise OSError('write_contract')
        if self.write_answer is GOOD:
            return writer.StoreResult('done', value='.aieos/tasks/%s.yaml' % task_id)
        return self.write_answer

    def append(self, *args, **kwargs):
        a = APPEND_SIGNATURE.bind(*args, **kwargs).arguments
        first = next(iter(a.values()))
        self.calls.append(('append', first, a['event_type'], a['payload'], a['event_id'], a['appended_at'],
                           a['recorder'], a.get('task_id'), a.get('fencing_token')))
        if 'append' in self.raise_on:
            raise OSError('append')
        if self.refuse:
            return writer.WriteResult(eventlog.AppendResult('refused', 'event', findings=('stand-in refusal',)))
        r = eventlog.append(self.data, a['event_type'], a['payload'], a['event_id'], a['appended_at'],
                            task_id=a.get('task_id'), recorder=a['recorder'])
        if r.result == 'appended':
            self.data += r.line
        return writer.WriteResult(r)

    def kw(self):
        return {'read': self.read, 'read_log': self.read_log, 'write_contract': self.write_contract,
                'append': self.append}


class Clock:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return NOW


def imp(world, task=TASK, clock=None, **over):
    kw = world.kw()
    kw.update(over)
    return launcher.import_task(ROOT, task, clock or (lambda: NOW), **kw)


def written(world):
    return [c for c in world.calls if c[0] == 'write_contract']


class TASK097AC1Writes(unittest.TestCase):
    def test_the_done_path(self):
        """TASK-097 AC1: one clock read, one _head read, one read_log, one write_contract with (root, task, text),
        then one append of task.drafted with the text's hash, the event id, now, IMPORT_RECORDER, task_id the task and
        no fencing token, in that order; "done" with the path, the hash, the event id and 'appended'."""
        w = World()
        clock = Clock()
        out = imp(w, clock=clock)
        self.assertEqual(clock.calls, 1)
        self.assertEqual(w.names(), ['read', 'read_log', 'write_contract', 'append'])
        self.assertEqual(w.calls[0], ('read', ROOT, tuple(launcher.HEAD_ARGS)))
        self.assertEqual(w.calls[1], ('read_log', ROOT))
        self.assertEqual(w.calls[2], ('write_contract', ROOT, TASK, expected()))
        payload = {'contract_version': 'v1', 'contract_hash': HASH}
        self.assertEqual(w.calls[3], ('append', ROOT, 'task.drafted', payload, EID, NOW, 'aieos cli import', TASK,
                                      None))
        self.assertEqual(out, {'result': 'done', 'reason': None, 'findings': [], 'path': PATH, 'contract_hash': HASH,
                               'event_id': EID, 'append': 'appended'})

    def test_the_text_is_the_template(self):
        """TASK-097 AC1: the text written is the template filled with the task and the head only, every line equal
        to the literal expected text, for two tasks and two heads."""
        for task, head in ((TASK, HEAD), ('TASK-123', 'd' * 40)):
            read = {'exit': 0, 'out': (head + '\n').encode('ascii'), 'err': b'', 'error': None}
            w = World(read=read)
            out = imp(w, task=task)
            self.assertEqual(out['result'], 'done', out)
            text = written(w)[0][3]
            self.assertEqual(text.splitlines(), expected(task, head).splitlines())
            self.assertEqual(text, expected(task, head))
            self.assertEqual(out['contract_hash'], digest(text))
            self.assertEqual(out['event_id'], event_id_of(task, digest(text)))

    def test_the_text_parses(self):
        """TASK-097 AC1: the filled text parses by task_contract.parse_contract with no finding and by base_inputs'
        contract parser with every CONTRACT_NEEDS key; its keys are TASK-096's in order; owner_kept_act true, risk
        critical, push forbidden, and its write set outside the project-state directory."""
        text = expected()
        parsed = task_contract.parse_contract(text, TASK)
        self.assertEqual((parsed['result'], parsed['reason'], parsed['findings']), ('read', None, []), parsed)
        self.assertEqual((parsed['task'], parsed['base_commit']), (TASK, HEAD))
        self.assertEqual(parsed['write_set'], ['docs/proposals/ARCH-001.md', 'docs/proposals/CHG-001.md'])
        self.assertEqual(parsed['forbidden'], [writer.STATE_DIR + '/**'])
        for path in parsed['write_set']:
            self.assertFalse(path.startswith(writer.STATE_DIR), path)
        mapping = base_inputs._parse_contract_text(text)
        for key in base_inputs.CONTRACT_NEEDS:
            self.assertIn(key, mapping)
        self.assertEqual(tuple(line.split(':', 1)[0] for line in text.splitlines() if line[:1].isalpha()), KEYS)
        lines = text.splitlines()
        self.assertIn('owner_kept_act: true', lines)
        self.assertIn('risk: critical', lines)
        self.assertIn('  git: {allow: [commit], forbid: [push, "push --force", rebase, "reset --hard", tag]}', lines)

    def test_the_log_passes_check_log(self):
        """TASK-097 AC1: the task.drafted payload passes its check and the log after the run passes
        records.check_log, its last event the task's task.drafted."""
        w = World()
        self.assertEqual(imp(w)['result'], 'done')
        self.assertEqual(records.check_payload('task.drafted', w.calls[3][3]), [])
        report = records.check_log(w.data)
        self.assertEqual(report.findings(), [])
        last = report.lines[-1].event
        self.assertEqual((last['type'], last['task_id'], last['event_id']), ('task.drafted', TASK, EID))

    def test_a_rerun_is_refused(self):
        """TASK-097 AC1: a rerun over the log the first run made gives "refused" "exists" with no write and no
        append."""
        w = World()
        self.assertEqual(imp(w)['result'], 'done')
        out = imp(w)
        self.assertEqual((out['result'], out['reason'], out['findings']),
                         ('refused', 'exists', ['exists: %s has events in the log' % TASK]))
        self.assertEqual(len(written(w)), 1)
        self.assertEqual(w.names().count('append'), 1)

    def test_callees_default_at_call_time(self):
        """TASK-097 AC1: with no callee given, gitread.run, writer.read_log, writer.write_contract and
        writer.append_event, patched after import, are the ones called."""
        w = World()
        with mock.patch.object(gitread, 'run', w.read), mock.patch.object(writer, 'read_log', w.read_log), \
                mock.patch.object(writer, 'write_contract', w.write_contract), \
                mock.patch.object(writer, 'append_event', w.append):
            out = launcher.import_task(ROOT, TASK, lambda: NOW)
        self.assertEqual(out['result'], 'done', out)
        self.assertEqual(w.names(), ['read', 'read_log', 'write_contract', 'append'])

    def test_the_keys(self):
        """TASK-097 AC1: every answer has exactly IMPORT_KEYS, a done one and a refused one; the reasons are
        IMPORT_REASONS."""
        self.assertEqual(launcher.IMPORT_KEYS, ('result', 'reason', 'findings', 'path', 'contract_hash', 'event_id',
                                                'append'))
        self.assertEqual(launcher.IMPORT_REASONS, ('argument', 'clock', 'head', 'log', 'exists', 'layout', 'write',
                                                   'append'))
        for out in (imp(World()), imp(World(), task='x')):
            self.assertEqual(tuple(out), launcher.IMPORT_KEYS)


class TASK097AC2Refusals(unittest.TestCase):
    def refused(self, out, reason):
        self.assertEqual((out['result'], out['reason']), ('refused', reason), out)
        return out['findings']

    def test_wrong_arguments(self):
        """TASK-097 AC2: each wrong argument gives "argument" with nothing called."""
        for case in (dict(task='task-7'), dict(task=7), dict(task='TASK-'), dict(task='TASK-7 '), dict(clock=5),
                     dict(read='run'), dict(read_log=5), dict(write_contract='x'), dict(append=5)):
            w = World()
            self.refused(imp(w, **case), 'argument')
            self.assertEqual(w.calls, [], case)
        for root in ('relative/root', None, 3, ''):
            w = World()
            self.refused(launcher.import_task(root, TASK, lambda: NOW, **w.kw()), 'argument')
            self.assertEqual(w.calls, [], root)

    def test_the_clock(self):
        """TASK-097 AC2: a raising clock, a naive time and a time with a fraction of a second give "clock" with
        nothing else called."""
        def raising():
            raise RuntimeError('clock')
        for clock in (raising, lambda: NOW.replace(tzinfo=None), lambda: NOW.replace(microsecond=5), lambda: 'now'):
            w = World()
            self.refused(imp(w, clock=clock), 'clock')
            self.assertEqual(w.calls, [])

    def test_the_head(self):
        """TASK-097 AC2: _head's findings, a raising read and a head that is not 40 lowercase hex give "head", with
        no read_log call and nothing written."""
        for answer in ({'exit': 1, 'out': b'', 'err': b'', 'error': None}, {'exit': 0, 'out': b'xyz\n', 'error': None},
                       None, {'exit': 0, 'out': ('C' * 40 + '\n').encode('ascii'), 'err': b'', 'error': None},
                       {'exit': 0, 'out': ('c' * 39 + '\n').encode('ascii'), 'err': b'', 'error': None}):
            w = World(read=answer)
            self.refused(imp(w), 'head')
            self.assertEqual(w.names(), ['read'])
        w = World(raise_on=('read',))
        self.assertIn('head: a step raised OSError', self.refused(imp(w), 'head'))

    def test_the_log(self):
        """TASK-097 AC2: a raising read_log, an answer that is not bytes and a log records.check_log refuses give
        "log", with nothing written."""
        w = World(raise_on=('read_log',))
        self.assertIn('log: a step raised OSError', self.refused(imp(w), 'log'))
        for data in ('text', None, bytearray(b''), b'not json\n'):
            w = World()
            w.data = data
            self.refused(imp(w), 'log')
            self.assertEqual(written(w), [])
            self.assertNotIn('append', w.names())

    def test_the_task_already_in_the_log(self):
        """TASK-097 AC2: a log holding any event of the task, a duplicate line included, gives "exists" with no
        write; a log of other tasks only, or an empty one, is done."""
        dup = Log().drafted(task_id=TASK)
        dup.data = with_duplicate(dup.data)
        report = records.check_log(dup.data)
        self.assertEqual(report.findings(), [])
        self.assertEqual(report.lines[-1].duplicate_of, report.lines[0].number)
        for log in (Log().drafted(task_id=TASK), Log().drafted().drafted(task_id=TASK).drafted(), dup):
            w = World(log=log)
            self.assertEqual(self.refused(imp(w), 'exists'), ['exists: %s has events in the log' % TASK])
            self.assertEqual(written(w), [])
        for log in (Log(), Log().drafted().drafted(task_id='TASK-70')):
            self.assertEqual(imp(World(log=log))['result'], 'done')

    def test_the_write_refusals(self):
        """TASK-097 AC2: write_contract "refused" "exists" or "layout" pass through with their findings; any other
        refusal, a done with another path, an answer out of form and a raise give "write"; none appends."""
        for answer, reason, found in (
                (writer.StoreResult('refused', 'exists', ['exists: the contract file is not empty']), 'exists',
                 ['exists: the contract file is not empty']),
                (writer.StoreResult('refused', 'layout', ['layout: x']), 'layout', ['layout: x']),
                (writer.StoreResult('refused', 'link', ['link: y']), 'write',
                 ['write: write_contract gave refused link']),
                (writer.StoreResult('refused', 'unwritable', ['unwritable: OSError']), 'write', None),
                (writer.StoreResult('refused', 'argument', ['argument: x']), 'write', None),
                (writer.StoreResult('done', value='.aieos/tasks/TASK-8.yaml'), 'write', None),
                (writer.StoreResult('done'), 'write', None),
                ('done', 'write', ['write: write_contract gave an answer that is not a StoreResult']),
                (None, 'write', None)):
            w = World(write=answer)
            out = imp(w)
            got = self.refused(out, reason)
            if found is not None:
                self.assertEqual(got, found)
            self.assertNotIn('append', w.names())
            self.assertEqual((out['path'], out['contract_hash'], out['event_id']), (None, None, None))
        w = World(raise_on=('write_contract',))
        self.assertEqual(self.refused(imp(w), 'write'), ['write: a step raised OSError'])
        self.assertNotIn('append', w.names())

    def test_the_append_refusals(self):
        """TASK-097 AC2: an append "refused", raising or answering out of form gives "append" with the exact finding
        naming the written contract and its hash, the path, hash and event id kept."""
        for world, first in ((World(refuse=True), 'append: task.drafted: refused event'),
                             (World(raise_on=('append',)), 'append: task.drafted: a step raised OSError')):
            out = imp(world)
            self.assertEqual(self.refused(out, 'append'), [first, STUCK])
            self.assertEqual((out['path'], out['contract_hash'], out['event_id'], out['append']),
                             (PATH, HASH, EID, None))
        out = imp(World(), append=lambda *a, **k: 'appended')
        self.assertEqual(self.refused(out, 'append'),
                         ['append: task.drafted: append gave an answer that is not a WriteResult', STUCK])

    def test_no_exception_escapes(self):
        """TASK-097 AC2: callees that raise or answer with values whose methods raise give a refusal, never a
        raise."""
        class Odd(dict):
            def get(self, *a):
                raise RuntimeError('get')
        self.assertEqual(imp(World(read=Odd(exit=0)))['reason'], 'head')
        self.assertEqual(imp(World(write=writer.StoreResult('done', value=Odd())))['reason'], 'write')
        for name in ('read', 'read_log', 'write_contract', 'append'):
            self.assertEqual(imp(World(raise_on=(name,)))['result'], 'refused', name)

    def test_what_import_task_names(self):
        """TASK-097 AC2: by ast, import_task and the names beginning _import or IMPORT name no open, exec, eval,
        compile, __import__, subprocess, os, sys or time, and hold no string constant naming the project-state
        directory, every such path built from writer.STATE_DIR."""
        tree = ast.parse((SRC / 'launcher.py').read_bytes().decode('utf-8'))
        mine = []
        for n in tree.body:
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and (n.name == 'import_task'
                                                                   or n.name.startswith('_import')):
                mine.append(n)
            elif isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id.lstrip('_').startswith('IMPORT')
                                                   for t in n.targets):
                mine.append(n)
        self.assertGreater(len(mine), 10)
        names = {x.id for n in mine for x in ast.walk(n) if isinstance(x, ast.Name)}
        self.assertEqual(names & {'open', 'exec', 'eval', 'compile', '__import__', 'subprocess', 'os', 'sys', 'time'},
                         set())
        texts = [x.value for n in mine for x in ast.walk(n)
                 if isinstance(x, ast.Constant) and isinstance(x.value, str)]
        self.assertEqual([t for t in texts if writer.STATE_DIR in t], [])
        self.assertIn('STATE_DIR', {x.attr for n in mine for x in ast.walk(n) if isinstance(x, ast.Attribute)})


class Stand:
    def __init__(self, answer=GOOD, raises=None):
        self.calls = []
        self.answer = answer
        self.raises = raises

    def __call__(self, *args):
        self.calls.append(args)
        if self.raises is not None:
            raise self.raises
        return self.answer


class Sink:
    def __init__(self):
        self.writes = []

    def write(self, text):
        self.writes.append(text)


def done(**over):
    answer = {'result': 'done', 'reason': None, 'findings': [], 'path': '.aieos/tasks/TASK-1.yaml',
              'contract_hash': 'h', 'event_id': 'e', 'append': 'appended'}
    answer.update(over)
    return answer


def refused(**over):
    answer = {'result': 'refused', 'reason': 'exists', 'findings': ['exists: x'], 'path': None,
              'contract_hash': None, 'event_id': None, 'append': None}
    answer.update(over)
    return answer


def run(argv, answer=GOOD, raises=None, environ=None):
    sink, clock = Sink(), Clock()
    stand = Stand(done() if answer is GOOD else answer, raises)
    with mock.patch.object(launcher, 'import_task', stand):
        rc = cli.main(argv, sink, {} if environ is None else environ, clock)
    return rc, ''.join(sink.writes), stand, clock


ARGV = ['import', 'TASK-1', '--root', ROOT]


class TASK097AC4Command(unittest.TestCase):
    def test_the_call(self):
        """TASK-097 AC4: "import TASK-1 --root R" calls import_task once with (R, 'TASK-1', the clock); --json may
        come before --root."""
        rc, _, stand, clock = run(ARGV)
        self.assertEqual((rc, stand.calls), (0, [(ROOT, 'TASK-1', clock)]))
        self.assertEqual(clock.calls, 0)
        rc, _, stand, clock = run(['import', 'TASK-1', '--json', '--root', ROOT])
        self.assertEqual((rc, stand.calls), (0, [(ROOT, 'TASK-1', clock)]))

    def test_usage_errors(self):
        """TASK-097 AC4: each argv out of form gives exit 2 and USAGE with nothing called, inside a runtime too."""
        bad = [['import'], ['import', '--root', ROOT], ['import', 'task-1', '--root', ROOT], ['import', 'TASK-1'],
               ARGV + ['--root', ROOT], ARGV + ['--json', '--json'], ['import', 'TASK-1', '--root', ''],
               ['import', 'TASK-1', '--root', '--x'], ARGV + ['extra'], ARGV + ['--class', 'decision_agent'],
               ['import', 'TASK-1', 'TASK-2', '--root', ROOT], ['import', 'TASK-1', '--root']]
        for argv in bad:
            for environ in ({}, {'AIEOS_ROOT': 'x'}):
                rc, out, stand, clock = run(argv, environ=environ)
                self.assertEqual((rc, out, stand.calls, clock.calls), (2, cli.USAGE, [], 0), argv)

    def test_inside_a_runtime(self):
        """TASK-097 AC4: an environ holding any one of the three RUNTIME_VARS ('' included) gives exit 1 and the
        runtime refusal with nothing called."""
        for name in cli.RUNTIME_VARS:
            for value in ('', 'x'):
                rc, out, stand, clock = run(ARGV, environ={name: value})
                self.assertEqual((rc, out, stand.calls, clock.calls),
                                 (1, 'finding: %s\n' % cli.IMPORT_RUNTIME_REFUSAL, [], 0), name)
        rc, out, _, _ = run(ARGV + ['--json'], environ={'AIEOS_BASE': 'b'})
        self.assertEqual((rc, json.loads(out)), (1, {'findings': [cli.IMPORT_RUNTIME_REFUSAL]}))
        self.assertEqual(cli.IMPORT_RUNTIME_REFUSAL,
                         'import: refused inside a runtime (it writes; specification 7 :34 names end and launch, and '
                         'import is refused for the same reason)')

    def test_done_output(self):
        """TASK-097 AC4: "done" gives exit 0 and the contract and event lines, then the findings, or under --json
        the exact sorted line."""
        answer = done(findings=['f1'], append='duplicate')
        rc, out, _, _ = run(ARGV, answer=answer)
        self.assertEqual((rc, out), (0, 'contract: .aieos/tasks/TASK-1.yaml h\nevent: e duplicate\nfinding: f1\n'))
        rc, out, _, _ = run(ARGV + ['--json'], answer=answer)
        self.assertEqual((rc, out), (0, '{"append": "duplicate", "contract_hash": "h", "event_id": "e", '
                                        '"findings": ["f1"], "path": ".aieos/tasks/TASK-1.yaml"}\n'))
        rc, out, _, _ = run(ARGV)
        self.assertEqual((rc, out), (0, 'contract: .aieos/tasks/TASK-1.yaml h\nevent: e appended\n'))

    def test_refused_output(self):
        """TASK-097 AC4: "refused" gives exit 1 and "finding: import: refused <reason>" then the findings, or under
        --json one findings line."""
        rc, out, _, _ = run(ARGV, answer=refused())
        self.assertEqual((rc, out), (1, 'finding: import: refused exists\nfinding: exists: x\n'))
        answer = refused(reason='append', findings=['append: y', 'z'], path='p', contract_hash='h', event_id='e')
        rc, out, _, _ = run(ARGV + ['--json'], answer=answer)
        self.assertEqual((rc, json.loads(out)), (1, {'findings': ['import: refused append', 'append: y', 'z']}))

    def test_answers_out_of_form(self):
        """TASK-097 AC4: each answer out of form gives the out-of-form finding."""
        bad = [None, 'done', OrderedDict(done()), dict(done(), extra=1), {k: v for k, v in done().items()
                                                                          if k != 'append'},
               done(result='maybe'), done(reason='x'), done(path=None), done(path=3), done(contract_hash=None),
               done(event_id=b'e'), done(append='other'), done(append=None), done(findings='f'),
               done(findings=[3]), refused(reason='nope'), refused(reason=None), refused(findings=[3]),
               refused(path=3), refused(append=1)]
        for answer in bad:
            rc, out, _, _ = run(ARGV, answer=answer)
            self.assertEqual((rc, out), (1, 'finding: %s\n' % cli.IMPORT_OUT_OF_FORM), answer)
        self.assertEqual(cli.IMPORT_OUT_OF_FORM, 'import: import_task gave an answer out of form')

    def test_raises(self):
        """TASK-097 AC4: a raising import_task gives "import: a step raised <type>"; a raising _render_import
        (patched) gives "cli: a step raised <type>"."""
        rc, out, _, _ = run(ARGV, raises=RuntimeError('x'))
        self.assertEqual((rc, out), (1, 'finding: import: a step raised RuntimeError\n'))
        with mock.patch.object(cli, '_render_import', mock.Mock(side_effect=ValueError('render'))):
            rc, out, _, _ = run(ARGV)
        self.assertEqual((rc, out), (1, 'finding: cli: a step raised ValueError\n'))


def used_names(node):
    return ({n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            | {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)})


def function(name, file_name):
    tree = ast.parse((SRC / file_name).read_bytes().decode('utf-8'))
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name][0]


class TASK097AC5Modules(unittest.TestCase):
    def test_the_command_functions(self):
        """TASK-097 AC5: by ast, cli.py's _import, _render_import and _import_in_form name no writer or
        held_leases."""
        for name in ('_import', '_render_import', '_import_in_form'):
            self.assertFalse(used_names(function(name, 'cli.py')) & {'writer', 'held_leases'}, name)

    def test_no_recorder_holds_owner(self):
        """TASK-097 AC5: IMPORT_RECORDER and the recorder of the task.drafted appended hold no "owner" in any
        case."""
        self.assertEqual(launcher.IMPORT_RECORDER, 'aieos cli import')
        w = World()
        self.assertEqual(imp(w)['result'], 'done')
        for call in w.calls:
            if call[0] == 'append':
                self.assertNotIn('owner', call[6].lower())

    def test_this_test_file(self):
        """TASK-097 AC5: this file imports no tempfile, sqlite3, shutil or subprocess, names no open, roots only the
        literal 'C:/import-root-97', and has no one-argument .replace() and no .replace(target=...)."""
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


class TASK097AC6Docs(unittest.TestCase):
    def test_the_launcher_docstring(self):
        """TASK-097 AC6: launcher.py's docstring holds the import paragraph's phrases."""
        text = doc('launcher.py')
        for phrase in ('import_task', 'TASK-097', 'drafts nothing', 'task.drafted', 'not changed',
                       "reads the caller's clock once", 'writer.write_contract'):
            self.assertIn(phrase, text)

    def test_the_cli_docstring_and_usage(self):
        """TASK-097 AC6: cli.py's docstring holds the import phrases and the COMMANDS phrase, and not the replaced
        one; USAGE names import."""
        text = doc('cli.py')
        for phrase in ('aieos import', 'TASK-097', 'drafts nothing', 'not run on any real project',
                       'COMMANDS, tasks, end, status, init, launch, approve, edit, reject or import',
                       'end and init call it after the parse', 'import also calls it after the parse'):
            self.assertIn(phrase, text)
        self.assertNotIn('COMMANDS, tasks, end, status, init, launch, approve, edit or reject', text)
        self.assertIn('import <task> --root <path> [--json]', cli.USAGE)
        self.assertEqual(cli.COMMANDS[-1], 'import')

    def test_every_test_names_its_criteria(self):
        """TASK-097 AC6: every test function of this module names "TASK-097 AC" in its own docstring, more than 20
        in all."""
        tree = ast.parse(HERE.read_bytes().decode('utf-8'))
        tests = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
        self.assertGreater(len(tests), 20)
        for node in tests:
            self.assertIn('TASK-097 AC', ast.get_docstring(node) or '', node.name)


if __name__ == '__main__':
    unittest.main()

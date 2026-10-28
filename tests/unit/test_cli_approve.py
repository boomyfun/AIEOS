"""Unit tests of launcher.approval_act, of records.py's Edit claim and of the commands approve, edit and reject of
cli.py (task TASK-096; specification 1 section 12, specification 2 revision 11, specification 7 section 4).
approval_act's callees (read, read_log, append, contract_at, task_states) are stand-ins given as keyword arguments,
over event logs built in memory with eventlog.append, the append stand-in bound to writer.append_event's signature;
the commands are run by mock.patch.object of launcher.approval_act, each restored after its test. No test writes a
file, runs Git or starts a process; the only files read are the package's own launcher.py, records.py and cli.py and
this file, with pathlib's read_bytes, for the ast checks; the root is a literal Windows path that names no folder.
Stand-in defaults are sentinels, never a value a case passes (L-0033). Each test names its criteria in its own
docstring."""

import ast
import datetime
import hashlib
import inspect
import json
import pathlib
import unittest
from collections import OrderedDict
from unittest import mock

from aieos_bootstrap import base_inputs, cli, eventlog, execution, gitread, launcher, records, writer

REAL_TASK_STATES = execution.task_states
REAL_APPEND_EVENT = writer.append_event
HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / 'src' / 'aieos_bootstrap'
ROOT = 'C:/approve-root-96'
NOW = datetime.datetime(2026, 10, 26, 9, 0, 0, tzinfo=datetime.timezone.utc)
TASK = 'TASK-7'
DEP = 'TASK-1'
H = 'a' * 64
HEAD = 'c' * 40
GOOD = object()
CONTRACT = {'task': TASK, 'contract_version': 'v1', 'input_state': {'depends_on': [DEP]}, 'owner_kept_act': 'false'}
REC = 'a unit test'


def acceptance(next_state, rid):
    return {'record_id': rid, 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_local',
            'recorder': REC, 'subject': TASK, 'decision': 'NEEDS_REWORK', 'next_task_state': next_state}


class Log:
    """An event log kept as bytes; every line is decided by eventlog.append."""

    def __init__(self):
        self.data = b''
        self.n = 0

    def add(self, event_type, payload, task_id=TASK):
        self.n += 1
        r = eventlog.append(self.data, event_type, payload, 'ev-%d' % self.n, NOW, task_id=task_id)
        if r.result != 'appended':
            raise ValueError(r.findings)
        self.data += r.line
        return self

    def drafted(self, h=H, version='v1', task_id=TASK, kind='task.drafted'):
        return self.add(kind, {'contract_version': version, 'contract_hash': h}, task_id)

    def done_dep(self):
        self.drafted(task_id=DEP)
        self.add('task.approved', {'contract_version': 'v1', 'contract_hash': H, 'approval_record': 'r'}, DEP)
        return self.add('task.done', {'decision_record': 'd'}, DEP)


def good_log():
    return Log().done_dep().drafted()


class World:
    """The callees of approval_act as stand-ins: read gives HEAD, contract_at the contract, read_log the log bytes,
    task_states the real one (counted), append decides with eventlog.append over the log and keeps the line."""

    def __init__(self, log=None, contract=GOOD, read=GOOD, refuse=(), raise_on=()):
        self.data = (good_log() if log is None else log).data
        self.contract = ((dict(CONTRACT), H), None) if contract is GOOD else contract
        self.read_answer = {'exit': 0, 'out': (HEAD + '\n').encode('ascii'), 'err': b'', 'error': None} \
            if read is GOOD else read
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

    def contract_at(self, *args):
        self.calls.append(('contract_at',) + args)
        if 'contract_at' in self.raise_on:
            raise RuntimeError('contract_at')
        return self.contract

    def read_log(self, root):
        self.calls.append(('read_log', root))
        if 'read_log' in self.raise_on:
            raise OSError('read_log')
        return self.data

    def task_states(self, log, task_ids):
        self.calls.append(('task_states', log, list(task_ids)))
        if 'task_states' in self.raise_on:
            raise RuntimeError('task_states')
        return REAL_TASK_STATES(log, task_ids)

    def append(self, *args, **kwargs):
        bound = inspect.signature(REAL_APPEND_EVENT).bind(*args, **kwargs)
        a = bound.arguments
        self.calls.append(('append', a['event_type'], a['payload'], a['event_id'], a['appended_at'], a['recorder'],
                           a.get('task_id'), a.get('fencing_token')))
        if a['event_type'] in self.raise_on:
            raise OSError('append')
        if a['event_type'] in self.refuse:
            return writer.WriteResult(eventlog.AppendResult('refused', 'event', findings=('stand-in refusal',)))
        r = eventlog.append(self.data, a['event_type'], a['payload'], a['event_id'], a['appended_at'],
                            task_id=a.get('task_id'), recorder=a['recorder'])
        if r.result == 'appended':
            self.data += r.line
        return writer.WriteResult(r)

    def kw(self):
        return {'read': self.read, 'read_log': self.read_log, 'append': self.append, 'contract_at': self.contract_at,
                'task_states': self.task_states}


def act(world, what='approve', source='decision_agent', who='D-1', note=None, clock=None, **over):
    kw = world.kw()
    kw.update(over)
    return launcher.approval_act(ROOT, TASK, what, source, who, note, clock or (lambda: NOW), **kw)


def appended(world):
    return [c for c in world.calls if c[0] == 'append']


def rid_of(what, *rest):
    return 'approval/' + hashlib.sha256('\n'.join(('approval', what, TASK, H) + rest).encode('utf-8')).hexdigest()


class TASK096AC1Writes(unittest.TestCase):
    def test_approve_by_the_decision_agent(self):
        """TASK-096 AC1: approve with decision_agent and 'D-1': one read, one contract_at (root, head, task), one
        read_log, one task_states (log, depends_on), then record.added and task.approved, each with now, the record's
        recorder, task_id the task and no fencing token; "done" with the record id, two event ids, both appended."""
        w = World()
        log = w.data
        clock = Clock()
        out = act(w, clock=clock)
        self.assertEqual(out['result'], 'done', out)
        self.assertEqual(clock.calls, 1)
        self.assertEqual(w.names(), ['read', 'contract_at', 'read_log', 'task_states', 'append', 'append'])
        self.assertEqual(w.calls[0], ('read', ROOT, tuple(launcher.HEAD_ARGS)))
        self.assertEqual(w.calls[1], ('contract_at', ROOT, HEAD, TASK))
        self.assertEqual(w.calls[3], ('task_states', log, [DEP]))
        first, second = appended(w)
        recorder = 'decided by: decision agent (A41, A51), decision D-1, through aieos cli approve'
        self.assertEqual(first[1], 'record.added')
        self.assertEqual(first[2], {'record_id': rid_of('approve'), 'fact_kind': 'authority',
                                    'source_class': 'decision_agent', 'recorder': recorder, 'subject': TASK,
                                    'approval_binding': {'kind': 'contract', 'hash': H}, 'decision_ref': 'D-1'})
        self.assertEqual(second[1:3], ('task.approved', {'contract_version': 'v1', 'contract_hash': H,
                                                         'approval_record': rid_of('approve')}))
        for call in (first, second):
            self.assertEqual(call[4:], (NOW, recorder, TASK, None))
        self.assertEqual((out['record_id'], out['event_ids'], out['appends']),
                         (rid_of('approve'), [first[3], second[3]], ['appended', 'appended']))
        self.assertEqual(out['reason'], None)

    def test_approve_by_a_named_person(self):
        """TASK-096 AC1: with human_authority the record has no decision_ref and its recorder says "not checked"."""
        w = World()
        out = act(w, source='human_authority', who='Ann Lee')
        self.assertEqual(out['result'], 'done', out)
        record = appended(w)[0][2]
        self.assertNotIn('decision_ref', record)
        self.assertEqual(record['recorder'], 'Ann Lee, as stated to aieos cli approve (not checked)')
        self.assertEqual(record['source_class'], 'human_authority')

    def test_reject(self):
        """TASK-096 AC1: reject appends one record.added with outcome fail and no task.approved, and calls no
        task_states."""
        w = World()
        clock = Clock()
        out = act(w, what='reject', clock=clock)
        self.assertEqual(out['result'], 'done', out)
        self.assertEqual(clock.calls, 1)
        calls = appended(w)
        self.assertEqual([c[1] for c in calls], ['record.added'])
        self.assertEqual((calls[0][2]['outcome'], calls[0][2]['approval_binding']), ('fail', {'kind': 'contract',
                                                                                            'hash': H}))
        self.assertNotIn('task_states', w.names())
        self.assertEqual(len(out['event_ids']), 1)

    def test_edit(self):
        """TASK-096 AC1: edit appends one record.added holding a claim with evidence_type contract_edit and the note
        as text, and calls no task_states."""
        w = World()
        clock = Clock()
        out = act(w, what='edit', note='rename the second criterion', clock=clock)
        self.assertEqual(out['result'], 'done', out)
        self.assertEqual(clock.calls, 1)
        calls = appended(w)
        self.assertEqual([c[1] for c in calls], ['record.added'])
        record = calls[0][2]
        self.assertEqual((record['fact_kind'], record['evidence_type'], record['text']),
                         ('claim', 'contract_edit', 'rename the second criterion'))
        self.assertNotIn('session', record)
        self.assertEqual(record['record_id'], rid_of('edit', 'decision_agent', 'D-1', 'rename the second criterion'))
        self.assertNotIn('task_states', w.names())

    def test_the_records_and_the_log_are_of_form(self):
        """TASK-096 AC1: every record passes records.check_payload('record.added', ...), every payload its type's
        check, and the log after each act passes records.check_log."""
        for what, note in (('approve', None), ('reject', None), ('edit', 'a note')):
            for source, who in (('decision_agent', 'D-9'), ('human_authority', 'Bo')):
                w = World()
                out = act(w, what=what, source=source, who=who, note=note)
                self.assertEqual(out['result'], 'done', (what, source, out))
                for call in appended(w):
                    self.assertEqual(records.check_payload(call[1], call[2]), [], (what, source))
                self.assertEqual(records.check_log(w.data).findings(), [], (what, source))

    def test_reruns(self):
        """TASK-096 AC1: over the log a first run made, a rerun of reject or edit gives "done" with the same ids and
        appends ['duplicate']; an approve whose task.approved was refused after its record gives ['duplicate',
        'appended'] when run again; a full rerun of approve is refused "state"."""
        for what, note in (('reject', None), ('edit', 'n')):
            w = World()
            first = act(w, what=what, note=note)
            again = act(w, what=what, note=note)
            self.assertEqual((again['result'], again['event_ids'], again['appends']),
                             ('done', first['event_ids'], ['duplicate']), what)
        w = World(refuse=('task.approved',))
        half = act(w)
        self.assertEqual(half['reason'], 'append')
        w.refuse = ()
        done = act(w)
        self.assertEqual((done['result'], done['appends']), ('done', ['duplicate', 'appended']))
        self.assertEqual(act(w)['reason'], 'state')

    def test_callees_default_at_call_time(self):
        """TASK-096 AC1: with no callee given, gitread.run, writer.read_log, writer.append_event,
        base_inputs.contract_at and execution.task_states, patched after import, are the ones called."""
        w = World()
        with mock.patch.object(gitread, 'run', w.read), mock.patch.object(writer, 'read_log', w.read_log), \
                mock.patch.object(writer, 'append_event', w.append), \
                mock.patch.object(base_inputs, 'contract_at', w.contract_at), \
                mock.patch.object(execution, 'task_states', w.task_states):
            out = launcher.approval_act(ROOT, TASK, 'approve', 'decision_agent', 'D-1', None, lambda: NOW)
        self.assertEqual(out['result'], 'done', out)
        self.assertEqual(w.names(), ['read', 'contract_at', 'read_log', 'task_states', 'append', 'append'])

    def test_the_keys(self):
        """TASK-096 AC1: every answer has exactly APPROVAL_KEYS, a done one and a refused one."""
        self.assertEqual(launcher.APPROVAL_KEYS, ('result', 'reason', 'findings', 'record_id', 'event_ids',
                                                  'appends'))
        for out in (act(World()), act(World(), what='x')):
            self.assertEqual(tuple(out), launcher.APPROVAL_KEYS)


class TASK096AC2Refusals(unittest.TestCase):
    def refused(self, out, reason):
        self.assertEqual((out['result'], out['reason']), ('refused', reason), out)
        return out['findings']

    def test_wrong_arguments(self):
        """TASK-096 AC2: each wrong argument gives "argument" with nothing called, a human_authority who or an Edit
        note holding "owner" in any case among them."""
        cases = [dict(what='approved'), dict(what=None), dict(source='owner'), dict(source=['decision_agent']),
                 dict(who='D1'), dict(who='d-1'), dict(who='D-1 '), dict(source='human_authority', who=''),
                 dict(source='human_authority', who='a\nb'), dict(source='human_authority', who='x' * 201),
                 dict(source='human_authority', who='The Owner'), dict(source='human_authority', who='OWNERS'),
                 dict(note='n'), dict(what='reject', note=''), dict(what='edit'), dict(what='edit', note=''),
                 dict(what='edit', note='a\rb'), dict(what='edit', note='x' * 2001),
                 dict(what='edit', note='the owner approved'), dict(what='edit', note='Owner: yes'),
                 dict(clock=5), dict(append=5), dict(read='run')]
        for case in cases:
            w = World()
            out = act(w, **case)
            self.refused(out, 'argument')
            self.assertEqual(w.calls, [], case)
        for root, task in (('relative/root', TASK), (ROOT, 'task-7'), (ROOT, 7)):
            w = World()
            out = launcher.approval_act(root, task, 'approve', 'decision_agent', 'D-1', None, lambda: NOW, **w.kw())
            self.refused(out, 'argument')
            self.assertEqual(w.calls, [])
        self.assertEqual(act(World(), what='edit', note='x' * 2000)['result'], 'done')

    def test_the_clock(self):
        """TASK-096 AC2: a raising clock, a naive time and a time with a fraction of a second give "clock" with
        nothing else called."""
        def raising():
            raise RuntimeError('clock')
        for clock in (raising, lambda: NOW.replace(tzinfo=None), lambda: NOW.replace(microsecond=5)):
            w = World()
            self.refused(act(w, clock=clock), 'clock')
            self.assertEqual(w.calls, [])

    def test_the_head(self):
        """TASK-096 AC2: _head's findings (a failing or out-of-form answer) and a raising read give "head", with no
        contract_at call."""
        for answer in ({'exit': 1, 'out': b'', 'err': b'', 'error': None}, {'exit': 0, 'out': b'xyz\n', 'error': None},
                       None):
            w = World(read=answer)
            self.refused(act(w), 'head')
            self.assertEqual(w.names(), ['read'])
        w = World(raise_on=('read',))
        self.assertIn('head: a step raised OSError', self.refused(act(w), 'head'))

    def test_the_contract(self):
        """TASK-096 AC2: contract_at's findings, a raise and an answer out of form give "contract", with no read_log
        call."""
        bad = dict(CONTRACT)
        del bad['contract_version']
        for answer, want in (((None, ['gone']), 'contract: gone'),
                             ((None, None), 'contract: contract_at gave no value'),
                             (((CONTRACT, H), ['x']), 'contract: x'), ('x', None), (((CONTRACT, 'h'), None), None),
                             (((bad, H), None), None), ((CONTRACT, None), None)):
            w = World(contract=answer)
            found = self.refused(act(w), 'contract')
            if want is not None:
                self.assertIn(want, found)
            self.assertNotIn('read_log', w.names())
        w = World(raise_on=('contract_at',))
        self.assertIn('contract: a step raised RuntimeError', self.refused(act(w), 'contract'))

    def test_the_log(self):
        """TASK-096 AC2: a raising read_log, an answer that is not bytes and a log records.check_log refuses give
        "log"."""
        w = World(raise_on=('read_log',))
        self.refused(act(w), 'log')
        for data in ('text', None, b'not json\n'):
            w = World()
            w.data = data
            self.refused(act(w), 'log')
            self.assertEqual(appended(w), [])

    def test_the_state(self):
        """TASK-096 AC2: a task with no task.drafted, or whose task.drafted is followed by task.approved,
        task.blocked or decision.acceptance, gives "state" with nothing appended."""
        logs = [Log().done_dep(), good_log().add('task.approved', {'contract_version': 'v1', 'contract_hash': H,
                                                                   'approval_record': 'r'}),
                good_log().add('task.blocked', {'reason': 'r', 'blocked_by': [DEP]}),
                good_log().add('decision.acceptance', acceptance('REWORK', 'dec-1'))]
        for log in logs:
            w = World(log=log)
            found = self.refused(act(w), 'state')
            self.assertEqual(found, ['state: %s is not in DRAFT' % TASK])
            self.assertEqual(appended(w), [])

    def test_the_version(self):
        """TASK-096 AC2: a contract hash or contract_version other than the last task.drafted's or task.replanned's
        gives "version"; a later replanned version of the same hash and version is approved."""
        for log in (Log().done_dep().drafted(h='b' * 64), Log().done_dep().drafted(version='v2'),
                    good_log().drafted(h='b' * 64, kind='task.replanned')):
            w = World(log=log)
            self.refused(act(w), 'version')
            self.assertEqual(appended(w), [])
        log = Log().done_dep().drafted(h='b' * 64).drafted(kind='task.replanned')
        self.assertEqual(act(World(log=log))['result'], 'done')

    def test_the_dependencies(self):
        """TASK-096 AC2: for approve a dependency not DONE, task_states' findings or a raise, and a depends_on out
        of form give "dependencies"."""
        w = World(log=Log().drafted(task_id=DEP).drafted())
        self.assertEqual(self.refused(act(w), 'dependencies'), ['dependencies: %s is not DONE' % DEP])
        w = World(raise_on=('task_states',))
        self.assertIn('dependencies: a step raised RuntimeError', self.refused(act(w), 'dependencies'))
        w = World()
        self.assertEqual(self.refused(act(w, task_states=lambda log, ids: (None, ['made up'])), 'dependencies'),
                         ['dependencies: made up'])
        for depends in ('TASK-1', ['task-1'], None, [1]):
            c = dict(CONTRACT, input_state={'depends_on': depends})
            self.refused(act(World(contract=((c, H), None))), 'dependencies')
        self.refused(act(World(contract=((dict(CONTRACT, input_state='x'), H), None))), 'dependencies')

    def test_the_owner_kept_act(self):
        """TASK-096 AC2: a decision_agent approval of a contract whose owner_kept_act is 'true' or out of form gives
        "owner_kept_act", while a human_authority approval of it is done."""
        for value in ('true', 'yes', None):
            c = dict(CONTRACT, owner_kept_act=value)
            w = World(contract=((c, H), None))
            self.refused(act(w), 'owner_kept_act')
            self.assertEqual(appended(w), [])
            w = World(contract=((c, H), None))
            self.assertEqual(act(w, source='human_authority', who='Ann')['result'], 'done')

    def test_an_earlier_reject(self):
        """TASK-096 AC2: an approve after a Reject of the same version after the last task.drafted gives "rejected";
        after a new task.drafted it is approved."""
        w = World()
        self.assertEqual(act(w, what='reject')['result'], 'done')
        self.refused(act(w), 'rejected')
        log = Log()
        log.data = w.data
        log.n = 50
        w2 = World(log=log.drafted())
        self.assertEqual(act(w2)['result'], 'done')

    def test_the_appends(self):
        """TASK-096 AC2: an append refused or raising gives "append"; a refused task.approved after an appended
        record.added names the record with its id and gives the first event id; a rerun of approve with another
        --by over a log holding the first record and no task.approved is refused as a conflict."""
        w = World(refuse=('record.added',))
        found = self.refused(act(w), 'append')
        self.assertEqual(found, ['append: record.added: refused event', 'stand-in refusal'])
        w = World(raise_on=('record.added',))
        self.assertEqual(self.refused(act(w), 'append'), ['append: record.added: a step raised OSError'])
        w = World(refuse=('task.approved',))
        out = act(w)
        self.refused(out, 'append')
        self.assertIn('append: the record %s is in the log, the task.approved is not; running approve again appends '
                      'it' % rid_of('approve'), out['findings'])
        self.assertEqual((out['record_id'], len(out['event_ids']), out['appends']), (rid_of('approve'), 1,
                                                                                     ['appended']))
        w.refuse = ()
        found = self.refused(act(w, who='D-2'), 'append')
        self.assertTrue(found[0].startswith('append: record.added: refused conflict'), found)
        out = act(World(), append=lambda *a, **k: 'appended')
        self.assertEqual(self.refused(out, 'append'),
                         ['append: record.added: append gave an answer that is not a WriteResult'])

    def test_no_exception_escapes(self):
        """TASK-096 AC2: callees that raise or answer with values whose methods raise give a refusal, never a
        raise."""
        class Odd(dict):
            def get(self, *a):
                raise RuntimeError('get')
        out = act(World(contract=((Odd(CONTRACT), H), None)))
        self.assertEqual(out['result'], 'refused')
        out = act(World(), task_states=lambda log, ids: ({DEP: Odd()}, None))
        self.assertEqual(out['reason'], 'dependencies')
        for name in ('read', 'contract_at', 'read_log', 'task_states', 'record.added', 'task.approved'):
            self.assertEqual(act(World(raise_on=(name,)))['result'], 'refused', name)

    def test_what_approval_act_names(self):
        """TASK-096 AC2: by ast, approval_act and the names beginning _approval name no open, exec, eval, compile,
        __import__, subprocess, os, sys or time."""
        tree = ast.parse((SRC / 'launcher.py').read_bytes().decode('utf-8'))
        mine = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
                and (n.name == 'approval_act' or n.name.startswith('_approval'))]
        self.assertGreater(len(mine), 5)
        names = {x.id for n in mine for x in ast.walk(n) if isinstance(x, ast.Name)}
        self.assertEqual(names & {'open', 'exec', 'eval', 'compile', '__import__', 'subprocess', 'os', 'sys', 'time'},
                         set())


def claim(**over):
    r = {'record_id': 'r-1', 'fact_kind': 'claim', 'source_class': 'human_authority', 'recorder': REC,
         'subject': TASK, 'evidence_type': 'contract_edit', 'text': 'a note'}
    r.update(over)
    return r


def rules(record):
    return {f.rule for f in records.check_record(record)}


class TASK096AC3Records(unittest.TestCase):
    def test_an_edit_claim(self):
        """TASK-096 AC3: a claim with evidence_type contract_edit, a TASK- subject, text and no session gives no
        finding; with another subject or evidence_type, or as an observation, "6.2:text"."""
        self.assertEqual(records.check_record(claim()), [])
        self.assertIn('6.2:text', rules(claim(subject='SPEC-1')))
        self.assertIn('6.2:text', rules(claim(evidence_type='edit_note')))
        self.assertIn('6.2:text', rules(claim(fact_kind='observation', source_class='deterministic_tool_local')))

    def test_the_session_and_acs_rules_stay(self):
        """TASK-096 AC3: an Edit claim with a session that is not a non-empty str gives "6.2:session", with acs and
        no gate "6.2:acs"."""
        self.assertIn('6.2:session', rules(claim(session='')))
        self.assertIn('6.2:session', rules(claim(session=3)))
        self.assertIn('6.2:acs', rules(claim(acs=['AC1'])))

    def test_the_text_rule_for_other_claims(self):
        """TASK-096 AC3: a claim without session and without the marker keeps the "6.2:text" finding; a session
        claim keeps its text."""
        plain = claim()
        del plain['evidence_type']
        self.assertIn('6.2:text', rules(plain))
        self.assertEqual(records.check_record(claim(evidence_type='agent_claim', session='s-1')), [])


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


class Clock:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return NOW


class Sink:
    def __init__(self):
        self.writes = []

    def write(self, text):
        self.writes.append(text)


def done(what='approve'):
    n = 2 if what == 'approve' else 1
    return {'result': 'done', 'reason': None, 'findings': [], 'record_id': 'approval/x',
            'event_ids': ['e%d' % i for i in range(1, n + 1)], 'appends': ['appended'] * n}


def run(argv, answer=GOOD, raises=None, environ=None, real=False):
    sink, clock = Sink(), Clock()
    stand = Stand(done(argv[0] if argv else 'approve') if answer is GOOD else answer, raises)
    if real:
        rc = cli.main(argv, sink, {} if environ is None else environ, clock)
    else:
        with mock.patch.object(launcher, 'approval_act', stand):
            rc = cli.main(argv, sink, {} if environ is None else environ, clock)
    return rc, ''.join(sink.writes), stand, clock


def argv_of(what='approve', *extra):
    base = [what, 'TASK-1', '--root', ROOT, '--class', 'decision_agent', '--by', 'D-1']
    return base + (['--note', 'n'] if what == 'edit' else []) + list(extra)


class TASK096AC4Commands(unittest.TestCase):
    def test_the_call(self):
        """TASK-096 AC4: approve, edit and reject call approval_act once with (root, task, act, class, by, note,
        clock), the note only for edit; --json may come anywhere after the task."""
        for what in ('approve', 'edit', 'reject'):
            rc, _, stand, clock = run(argv_of(what))
            self.assertEqual(rc, 0, what)
            self.assertEqual(stand.calls, [(ROOT, 'TASK-1', what, 'decision_agent', 'D-1',
                                            'n' if what == 'edit' else None, clock)], what)
        rc, _, stand, _ = run(['reject', 'TASK-1', '--json', '--by', 'Ann', '--class', 'human_authority', '--root',
                               ROOT])
        self.assertEqual((rc, stand.calls[0][3:6]), (0, ('human_authority', 'Ann', None)))

    def test_usage_errors(self):
        """TASK-096 AC4: each argv out of form gives exit 2 and USAGE with nothing called, inside a runtime too."""
        base = ['approve', 'TASK-1', '--root', ROOT]
        bad = [base, base + ['--class', 'decision_agent'], base + ['--by', 'D-1'],
               base + ['--class', 'owner', '--by', 'D-1'], argv_of('approve', '--note', 'n'),
               argv_of('reject', '--note', 'n'), ['edit', 'TASK-1', '--root', ROOT, '--class', 'decision_agent', '--by',
                                                  'D-1'],
               argv_of('approve', '--by', 'D-2'), argv_of('edit', '--note', 'm'),
               argv_of('approve', '--json', '--json'),
               base + ['--class', 'decision_agent', '--by', ''], base + ['--class', 'decision_agent', '--by', '--x'],
               ['approve', 'task-1', '--root', ROOT, '--class', 'decision_agent', '--by', 'D-1'],
               argv_of('approve', 'extra'), ['approve'], ['approve', '--root', ROOT],
               ['approve', 'TASK-1', '--class', 'decision_agent', '--by', 'D-1']]
        for argv in bad:
            for environ in ({}, {'AIEOS_ROOT': 'x'}):
                rc, out, stand, clock = run(argv, environ=environ)
                self.assertEqual((rc, out, stand.calls, clock.calls), (2, cli.USAGE, [], 0), argv)

    def test_a_by_out_of_form_reaches_approval_act(self):
        """TASK-096 AC4: a --by out of approval_act's form passes the parse and, with the real approval_act (step 1
        refuses before any callee), gives exit 1 with "finding: approve: refused argument"."""
        rc, out, _, clock = run(argv_of('approve')[:-1] + ['Ann'], real=True)
        self.assertEqual(rc, 1)
        self.assertTrue(out.startswith('finding: approve: refused argument\nfinding: argument: who is not a '
                                       'decision id'), out)
        self.assertEqual(clock.calls, 0)

    def test_inside_a_runtime(self):
        """TASK-096 AC4: an environ holding any one of the three RUNTIME_VARS ('' included) gives exit 1 and the
        runtime refusal filled with the command, with nothing called."""
        for what in ('approve', 'edit', 'reject'):
            line = cli.APPROVAL_RUNTIME_REFUSAL % (what, what)
            for name in cli.RUNTIME_VARS:
                rc, out, stand, clock = run(argv_of(what), environ={name: ''})
                self.assertEqual((rc, out, stand.calls, clock.calls), (1, 'finding: %s\n' % line, [], 0), name)
            rc, out, _, _ = run(argv_of(what, '--json'), environ={'AIEOS_BASE': 'b'})
            self.assertEqual((rc, json.loads(out)), (1, {'findings': [line]}))
        self.assertEqual(cli.APPROVAL_RUNTIME_REFUSAL % ('approve', 'approve'),
                         'approve: refused inside a runtime (it writes; specification 7 :34 names end and launch, and '
                         'approve is refused for the same reason)')

    def test_done_output(self):
        """TASK-096 AC4: "done" gives exit 0 and the record and event lines, then the findings, or under --json the
        exact sorted line."""
        answer = dict(done(), findings=['f1'], appends=['duplicate', 'appended'])
        rc, out, _, _ = run(argv_of('approve'), answer=answer)
        self.assertEqual((rc, out), (0, 'record: approval/x\nevent: e1 duplicate\nevent: e2 appended\nfinding: f1\n'))
        rc, out, _, _ = run(argv_of('approve', '--json'), answer=answer)
        self.assertEqual((rc, out), (0, '{"appends": ["duplicate", "appended"], "event_ids": ["e1", "e2"], '
                                        '"findings": ["f1"], "record_id": "approval/x"}\n'))

    def test_refused_output(self):
        """TASK-096 AC4: "refused" gives exit 1 and "finding: <act>: refused <reason>" then the findings, its record
        id and event ids not printed, or under --json one findings line."""
        answer = {'result': 'refused', 'reason': 'append', 'findings': ['append: x'], 'record_id': 'approval/x',
                  'event_ids': ['e1'], 'appends': ['appended']}
        rc, out, _, _ = run(argv_of('approve'), answer=answer)
        self.assertEqual((rc, out), (1, 'finding: approve: refused append\nfinding: append: x\n'))
        rc, out, _, _ = run(argv_of('edit', '--json'), answer=dict(answer, reason='state'))
        self.assertEqual((rc, json.loads(out)), (1, {'findings': ['edit: refused state', 'append: x']}))

    def test_answers_out_of_form(self):
        """TASK-096 AC4: each answer out of form gives "<act>: approval_act gave an answer out of form"."""
        refused = {'result': 'refused', 'reason': 'state', 'findings': [], 'record_id': None, 'event_ids': [],
                   'appends': []}
        bad = [None, 'done', OrderedDict(done()), dict(done(), extra=1), dict(done(), result='maybe'),
               dict(done(), reason='x'), dict(done(), event_ids=['e1'], appends=['appended']),
               dict(done(), appends=['appended']), dict(done(), appends=['appended', 'other']),
               dict(done(), record_id=None), dict(refused, reason='nope'), dict(refused, findings=[3]),
               dict(refused, record_id=3), dict(done(), findings='f')]
        for answer in bad:
            rc, out, _, _ = run(argv_of('approve'), answer=answer)
            self.assertEqual((rc, out), (1, 'finding: approve: approval_act gave an answer out of form\n'), answer)
        rc, _, _, _ = run(argv_of('edit'), answer=done('approve'))
        self.assertEqual(rc, 1)

    def test_raises(self):
        """TASK-096 AC4: a raising approval_act gives "<act>: a step raised <type>"; a raising _render_approval
        (patched) gives "cli: a step raised <type>"."""
        rc, out, _, _ = run(argv_of('reject'), raises=RuntimeError('x'))
        self.assertEqual((rc, out), (1, 'finding: reject: a step raised RuntimeError\n'))
        with mock.patch.object(cli, '_render_approval', mock.Mock(side_effect=ValueError('render'))):
            rc, out, _, _ = run(argv_of('approve'))
        self.assertEqual((rc, out), (1, 'finding: cli: a step raised ValueError\n'))


def used_names(node):
    return ({n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            | {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)})


def function(name, file_name):
    tree = ast.parse((SRC / file_name).read_bytes().decode('utf-8'))
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name][0]


class TASK096AC5Modules(unittest.TestCase):
    def test_the_command_functions(self):
        """TASK-096 AC5: by ast, cli.py's _approval, _render_approval and _approval_in_form name no writer or
        held_leases."""
        for name in ('_approval', '_render_approval', '_approval_in_form'):
            self.assertFalse(used_names(function(name, 'cli.py')) & {'writer', 'held_leases'}, name)

    def test_no_record_claims_the_owner(self):
        """TASK-096 AC5: no recorder or text field of any record approval_act builds, over every act and class,
        holds "owner" in any case."""
        for what, note in (('approve', None), ('reject', None), ('edit', 'a note')):
            for source, who in (('decision_agent', 'D-3'), ('human_authority', 'Ann')):
                w = World()
                self.assertEqual(act(w, what=what, source=source, who=who, note=note)['result'], 'done')
                for call in appended(w):
                    payload = call[2]
                    for key in ('recorder', 'text'):
                        self.assertNotIn('owner', str(payload.get(key, '')).lower(), (what, source, key))

    def test_this_test_file(self):
        """TASK-096 AC5: this file imports no tempfile, sqlite3, shutil or subprocess, names no open, roots only the
        literal 'C:/approve-root-96', and has no one-argument .replace() and no .replace(target=...)."""
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


class TASK096AC6Docs(unittest.TestCase):
    def test_the_launcher_docstring(self):
        """TASK-096 AC6: launcher.py's docstring holds the paragraph's phrases."""
        text = doc('launcher.py')
        for phrase in ('approval_act', 'TASK-096', 'contract-kind', 'HEAD', 'not checked', 'DEF-0101',
                       "reads the caller's clock once", 'writer.append_event'):
            self.assertIn(phrase, text)

    def test_the_records_docstring(self):
        """TASK-096 AC6: records.py's module docstring holds "contract_edit" and "TASK-096" and keeps the text rule's
        phrase."""
        text = doc('records.py')
        for phrase in ('contract_edit', 'TASK-096',
                       'allowed only on a record whose fact_kind is claim and whose session is set'):
            self.assertIn(phrase, text)

    def test_the_cli_docstring_and_usage(self):
        """TASK-096 AC6, as TASK-097 AC6 and TASK-098 AC6 widen it: cli.py's docstring holds the new commands' phrases
        and the COMMANDS phrase, and not the three replaced ones; USAGE names approve, edit and reject."""
        text = doc('cli.py')
        for phrase in ('aieos approve', 'aieos edit', 'aieos reject', 'TASK-096',
                       'writes nothing the governor counts at acceptance', 'not checked',
                       'COMMANDS, tasks, end, status, init, launch, approve, edit, reject, import or run',
                       'end and init call it after the parse'):
            self.assertIn(phrase, text)
        for phrase in ('COMMANDS, tasks, end, status, init or launch',
                       'COMMANDS, tasks, end, status, init, launch, approve, edit or reject',
                       'COMMANDS, tasks, end, status, init, launch, approve, edit, reject or import'):
            self.assertNotIn(phrase, text)
        for what in ('approve <task>', 'edit <task>', 'reject <task>', '--note <text>'):
            self.assertIn(what, cli.USAGE)
        self.assertTrue(cli.USAGE.endswith('\n'))

    def test_every_test_names_its_criteria(self):
        """TASK-096 AC6: every test function of this module names "TASK-096 AC" in its own docstring, more than 20
        in all."""
        tree = ast.parse(HERE.read_bytes().decode('utf-8'))
        tests = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
        self.assertGreater(len(tests), 20)
        for node in tests:
            self.assertIn('TASK-096 AC', ast.get_docstring(node) or '', node.name)


if __name__ == '__main__':
    unittest.main()

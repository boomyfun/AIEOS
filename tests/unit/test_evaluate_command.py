"""Unit tests of aieos_bootstrap.evaluate_command (task TASK-162; specification 7 revision 14, section 3). The log is
bytes held in memory and decided with eventlog.append; the contract reader, the file reader, the CI intake, the source
loader, the input assembler and evaluate_task are stand-ins set with mock.patch.object and restored after each call;
evaluation_intake.manifest, evaluation_sources.parse_json and evaluation._task_events are real. No test writes a file,
runs Git or starts a process; the only files read are the module's source and this file. Each test names its criteria in
its own docstring."""

import ast
import copy
import datetime
import hashlib
import json
import pathlib
import types
import unittest
from unittest import mock

from aieos_bootstrap import base_files
from aieos_bootstrap import base_inputs
from aieos_bootstrap import eval_inputs
from aieos_bootstrap import evaluate_command
from aieos_bootstrap import evaluation
from aieos_bootstrap import evaluation_intake
from aieos_bootstrap import evaluation_sources
from aieos_bootstrap import eventlog
from aieos_bootstrap import governor
from aieos_bootstrap import writer

HERE = pathlib.Path(__file__).resolve()
MODULE = HERE.parents[2] / 'src' / 'aieos_bootstrap' / 'evaluate_command.py'
ROOT = str(HERE.parents[2] / 'no-such-evaluate-root')
REPO = str(HERE.parents[2])
TASK = 'TASK-162'
REC = 'aieos cli evaluate'
NOW = datetime.datetime(2026, 11, 26, 12, 0, 0, tzinfo=datetime.timezone.utc)
TEXT = 'task: TASK-162\nowner_kept_act: false\n'
DATA = TEXT.encode('utf-8')
SHA = hashlib.sha256(DATA).hexdigest()
COMMIT = '3' * 40
BASE = 'a' * 40
FENCE = {'epoch': 'e0', 'counter': 1}
CI_TEXT = '{"run-1-1.log": "x"}'
DOCS = 'docs/tasks/TASK-162.yaml'


class Log:
    """A stand-in writer: read_log gives the bytes; append checks expected_log_sha256 as the writer does, decides with
    eventlog.append and keeps the line."""

    def __init__(self):
        self.log = b''
        self.reads = 0
        self.calls = []
        self.fences = []
        self.answers = {}

    def read_log(self, root):
        self.reads += 1
        return self.log

    def append(self, root, event_type, payload, event_id, appended_at, recorder, task_id=None, fencing_token=None,
               corrects=None, expected_log_sha256=None):
        self.calls.append((root, event_type, payload, event_id, appended_at, recorder, task_id, expected_log_sha256))
        self.fences.append((fencing_token, corrects))
        given = self.answers.get(len(self.calls))
        if isinstance(given, BaseException):
            raise given
        if given is not None:
            return types.SimpleNamespace(result='refused', reason=given, line=None, findings=(given + ': stand-in',))
        if expected_log_sha256 != hashlib.sha256(self.log).hexdigest():
            return types.SimpleNamespace(result='refused', reason='changed', line=None, findings=('changed',))
        r = eventlog.append(self.log, event_type, payload, event_id, appended_at, task_id=task_id, recorder=recorder)
        if r.result == 'appended':
            self.log += r.line
        return r

    def add(self, event_type, payload, event_id, fencing_token=None, lease=None):
        r = eventlog.append(self.log, event_type, payload, event_id, NOW, task_id=TASK, fencing_token=fencing_token,
                            lease=lease)
        assert r.result == 'appended', (r.result, r.findings)
        self.log += r.line
        return self


def submitted_log():
    log = Log().add('task.approved', {'contract_version': 'v1', 'contract_hash': SHA, 'approval_record': 'rec-a'}, 'a1')
    lease = {'task_id': TASK, 'fencing_token': FENCE, 'expires_at': NOW + datetime.timedelta(hours=1)}
    return log.add('task.submitted', {'commit': COMMIT, 'compensating': False}, 's1', fencing_token=FENCE, lease=lease)


def record(n):
    return {'record_id': 'ci-%d' % n, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
            'recorder': REC, 'subject': TASK, 'evidence_type': 'unit_test', 'commit': COMMIT}


class World:
    """The stand-ins of one call and what they saw."""

    def __init__(self, **changes):
        self.log = submitted_log()
        self.contract = {'task': TASK, 'input_state': {'base_commit': BASE}}
        self.contract_answer = ((self.contract, SHA), None)
        self.files = {DOCS: TEXT}
        self.intake = {'result': 'present', 'runs': [{'log': 'log one'}, {'log': 'log two'}],
                       'files': [{'name': 'run-1-1.log', 'sha256': 'f' * 64}], 'findings': []}
        shared = ['same']
        self.provenance = [{'path': 'p', 'list': shared}, {'path': 'q', 'list': shared},
                           {'contract': SHA, 'commit': COMMIT}]
        self.loaded = {'result': 'present', 'sources': {'s': 1}, 'changed_paths': ['src/x.py'],
                       'provenance': self.provenance, 'findings': []}
        self.ci_records = [record(1), record(2)]
        self.inputs_refusal = None
        self.manifest_refusal = None
        self.answer = {'result': 'evaluated', 'reason': None, 'findings': ['left out'], 'event_id': 'e9',
                       'changed_paths': ['src/x.py'], 'decision': 'REJECT', 'next_task_state': 'REJECTED'}
        self.raises = {}
        self.calls = {}
        self.order = []
        for key, value in changes.items():
            setattr(self, key, value)

    def seen(self, name, args):
        self.calls.setdefault(name, []).append(args)
        self.order.append(name)
        if name in self.raises:
            raise self.raises[name]

    def contract_at(self, repo, commit, task_id, read=None):
        self.seen('contract_at', (repo, commit, task_id, read))
        return self.contract_answer

    def read_file(self, repo, commit, path, read=None):
        self.seen('read_file', (repo, commit, path, read))
        if path in self.files:
            return {'blob': 'b' * 40, 'text': self.files[path]}, None
        return None, ['%s is missing' % path]

    def read_ci_data(self, files, task_id, commit):
        self.seen('read_ci_data', (files, task_id, commit))
        return self.intake

    def load_sources(self, repo, policy_ref, commit, task_id, ci_logs, read=None):
        self.seen('load_sources', (repo, policy_ref, commit, task_id, ci_logs, read))
        return self.loaded

    def eval_inputs(self, task_id, commit, policy_ref, contract, sha, changed, runs, sources, payloads, recorder):
        self.seen('eval_inputs', (task_id, commit, policy_ref, contract, sha, changed, runs, sources, payloads,
                                  recorder))
        if self.inputs_refusal is not None:
            return {'declared': None, 'values': None, 'ci_records': [], 'evidence': None,
                    'refusal': self.inputs_refusal}
        held = [p.get('record_id') for p in payloads]
        fresh = [r for r in self.ci_records if r['record_id'] not in held]
        return {'declared': {'d': 1}, 'values': {'v': 1}, 'ci_records': fresh,
                'evidence': {'ci': {'head_sha': COMMIT}, 'uncovered': [{'gate': 'G3'}]}, 'refusal': None}

    def evaluate_task(self, *args, **kwargs):
        self.seen('evaluate_task', (args, kwargs))
        return self.answer

    def run(self, root=ROOT, repo=REPO, task=TASK, ci_text=CI_TEXT, recorder=REC, now=NOW, read=None, read_log=None):
        def manifest(*args):
            self.seen('manifest', args)
            if self.manifest_refusal is not None:
                return {'result': 'refused', 'text': None, 'sha256': None, 'record': None,
                        'findings': [self.manifest_refusal]}
            return REAL_MANIFEST(*args)

        def logged_read(given_root):
            self.order.append('read_log')
            return (self.log.read_log if read_log is None else read_log)(given_root)

        def logged_append(*args, **kwargs):
            self.order.append('append')
            return self.log.append(*args, **kwargs)

        with mock.patch.object(base_inputs, 'contract_at', self.contract_at), \
                mock.patch.object(base_files, 'read_file', self.read_file), \
                mock.patch.object(evaluation_intake, 'read_ci_data', self.read_ci_data), \
                mock.patch.object(evaluation_sources, 'load_sources', self.load_sources), \
                mock.patch.object(eval_inputs, 'eval_inputs', self.eval_inputs), \
                mock.patch.object(evaluation_intake, 'manifest', manifest), \
                mock.patch.object(evaluation, 'evaluate_task', self.evaluate_task):
            return evaluate_command.evaluate(root, repo, task, ci_text, recorder, now, read=read,
                                             read_log=logged_read, append=logged_append)


REAL_MANIFEST = evaluation_intake.manifest


def event_id(record_id):
    return hashlib.sha256(('evaluation-record\nTASK-162\n' + record_id).encode('utf-8')).hexdigest()


def manifest_record_id(sha):
    text = 'evaluation-manifest\nTASK-162\n' + COMMIT + '\n' + sha
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def text_sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


class RaisingTime(datetime.datetime):
    def utcoffset(self):
        raise ValueError('x')


class TASK162AC1Module(unittest.TestCase):
    def tree(self):
        return ast.parse(MODULE.read_bytes().decode('utf-8'))

    def test_imports(self):
        """TASK-162 AC1: the module imports only the standard-library modules datetime, hashlib, os and re and modules
        of aieos_bootstrap (governor among them since TASK-166 AC4), and uses os only as os.path.isabs."""
        names = set()
        for n in ast.walk(self.tree()):
            if isinstance(n, ast.Import):
                names.update(a.name for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                names.update('%s.%s' % (n.module, a.name) for a in n.names)
        self.assertEqual(names, {'datetime', 'hashlib', 'os', 're'} | {
            'aieos_bootstrap.' + m for m in ('base_files', 'base_inputs', 'contract_path', 'eval_inputs', 'evaluation',
                                             'evaluation_intake', 'evaluation_sources', 'eventlog', 'governor',
                                             'writer')})
        uses = [ast.unparse(n) for n in ast.walk(self.tree()) if isinstance(n, ast.Attribute)
                and ast.unparse(n).startswith('os.')]
        self.assertEqual(sorted(set(uses)), ['os.path', 'os.path.isabs'])

    def test_no_file_process_or_clock_and_only_two_writer_names(self):
        """TASK-162 AC1, AC13: no open, exec, eval, input or compile name, no now or today call, and of the writer only
        read_log and append_event."""
        tree = self.tree()
        used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertEqual(used & {'open', 'exec', 'eval', 'input', 'compile', '__import__'}, set())
        attrs = [n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)]
        self.assertFalse({'now', 'today', 'utcnow', 'environ', 'getenv'} & set(attrs))
        of_writer = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                     and n.value.id == 'writer'}
        self.assertEqual(of_writer, {'read_log', 'append_event'})


class TASK162AC2Function(unittest.TestCase):
    def test_a_done_call(self):
        """TASK-162 AC2, AC8, AC9: the ten keys, the appended ids in order, evaluate_task's answer passed through, one
        read of the log, and evaluate_task given the contract bytes, no extra record and the Git reader."""
        w = World()
        seam = object()
        out = w.run(read=seam)
        self.assertEqual(tuple(sorted(out)), tuple(sorted((
            'result', 'reason', 'findings', 'event_id', 'decision', 'next_task_state', 'manifest_sha256', 'manifest',
            'appended', 'uncovered'))))
        manifest_id = manifest_record_id(out['manifest_sha256'])
        self.assertEqual(w.log.calls[2][2]['record_id'], manifest_id)
        self.assertEqual(w.log.fences, [(None, None)] * 3)
        self.assertEqual(w.order, ['read_log', 'contract_at', 'read_file', 'read_file', 'read_ci_data', 'load_sources',
                                   'eval_inputs', 'manifest', 'append', 'append', 'append', 'evaluate_task'])
        self.assertEqual((out['result'], out['reason'], out['findings'], out['event_id'], out['decision'],
                          out['next_task_state']), ('evaluated', None, ['left out'], 'e9', 'REJECT', 'REJECTED'))
        self.assertEqual(out['appended'], ['ci-1', 'ci-2', manifest_id])
        self.assertEqual(out['uncovered'], [{'gate': 'G3'}])
        self.assertEqual(hashlib.sha256(out['manifest'].encode('utf-8')).hexdigest(), out['manifest_sha256'])
        self.assertEqual(w.log.reads, 1)
        self.assertEqual(w.calls['evaluate_task'],
                         [((ROOT, REPO, TASK, DATA, {'d': 1}, {'v': 1}, [], REC, NOW), {'read': seam})])
        self.assertEqual(w.calls['contract_at'], [(REPO, COMMIT, TASK, seam)])
        self.assertEqual([c[3] for c in w.calls['read_file']], [seam] * len(w.calls['read_file']))
        self.assertEqual(w.calls['load_sources'], [(REPO, BASE, COMMIT, TASK, ['log one', 'log two'], seam)])
        self.assertEqual(w.calls['read_ci_data'], [({'run-1-1.log': 'x'}, TASK, COMMIT)])
        self.assertEqual(w.calls['eval_inputs'], [(TASK, COMMIT, BASE, w.contract, SHA, ['src/x.py'],
                                                   w.intake['runs'], {'s': 1}, [], REC)])

    def test_a_refusal_stops_the_calls_at_its_step(self):
        """TASK-162 AC2, AC14: the steps run in their order and a raise in one makes no later call."""
        steps = ['read_log', 'contract_at', 'read_file', 'read_file', 'read_ci_data', 'load_sources', 'eval_inputs',
                 'manifest']
        for name in ('contract_at', 'read_ci_data', 'load_sources', 'eval_inputs', 'manifest'):
            w = World(raises={name: KeyError('k')})
            w.run()
            self.assertEqual(w.order, steps[:steps.index(name) + 1], name)

    def test_the_default_reader_and_writer_are_looked_up_at_each_call(self):
        """TASK-162 AC2: with read_log and append None, writer.read_log and writer.append_event are looked up at the
        call."""
        w = World()
        with mock.patch.object(writer, 'read_log', w.log.read_log), \
                mock.patch.object(writer, 'append_event', w.log.append), \
                mock.patch.object(base_inputs, 'contract_at', w.contract_at), \
                mock.patch.object(base_files, 'read_file', w.read_file), \
                mock.patch.object(evaluation_intake, 'read_ci_data', w.read_ci_data), \
                mock.patch.object(evaluation_sources, 'load_sources', w.load_sources), \
                mock.patch.object(eval_inputs, 'eval_inputs', w.eval_inputs), \
                mock.patch.object(evaluation, 'evaluate_task', w.evaluate_task):
            out = evaluate_command.evaluate(ROOT, REPO, TASK, CI_TEXT, REC, NOW)
        self.assertEqual((out['result'], w.log.reads, len(w.log.calls)), ('evaluated', 1, 3), out['findings'])

    def test_argument_refusals_come_before_any_read(self):
        """TASK-162 AC2: each argument out of form gives "argument", with nothing read or written."""
        cases = ({'root': 'relative'}, {'root': ''}, {'repo': 'relative'}, {'repo': None}, {'task': 'T-1'},
                 {'task': 'TASK-1\n'}, {'ci_text': b'{}'}, {'recorder': ''},
                 {'now': NOW.replace(tzinfo=None)}, {'now': NOW + datetime.timedelta(microseconds=1)},
                 {'now': NOW.astimezone(datetime.timezone(datetime.timedelta(hours=1)))})
        for changes in cases:
            w = World()
            out = w.run(**changes)
            self.assertEqual((out['result'], out['reason'], w.log.reads, w.log.calls, w.calls),
                             ('refused', 'argument', 0, [], {}), changes)
            self.assertEqual((out['manifest'], out['manifest_sha256'], out['uncovered'], out['appended']),
                             (None, None, None, []), changes)

    def test_a_raise_in_the_argument_checks(self):
        """TASK-162 AC2: a raise in the argument checks gives "argument", with nothing read or written."""
        w = World()
        out = w.run(now=RaisingTime(2026, 11, 26, 12, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual((out['result'], out['reason'], out['findings'], w.order),
                         ('refused', 'argument', ['argument: a step raised ValueError'], []))

    def test_an_unexpected_exception_is_a_refusal_of_its_step(self):
        """TASK-162 AC2: a raise in a step gives that step's reason and names the type; a BaseException that is not an
        Exception passes through."""
        for name, reason, appended in (('contract_at', 'contract', 0), ('read_ci_data', 'ci', 0),
                                       ('load_sources', 'sources', 0), ('eval_inputs', 'inputs', 0),
                                       ('manifest', 'manifest', 0), ('evaluate_task', 'evaluate', 3)):
            w = World(raises={name: KeyError('k')})
            out = w.run()
            self.assertEqual((out['result'], out['reason'], len(out['appended'])), ('refused', reason, appended), name)
            self.assertEqual(out['findings'], ['%s: a step raised KeyError' % reason], name)
        w = World(raises={'load_sources': KeyboardInterrupt()})
        with self.assertRaises(KeyboardInterrupt):
            w.run()


class TASK162AC3Log(unittest.TestCase):
    def test_the_log_refusals(self):
        """TASK-162 AC3: a log that is not bytes, damaged or raising gives "log"; no approval or no submission gives
        "state"; nothing else is called."""
        def boom(root):
            raise OSError('x')
        no_approval = ['state: the log holds no task.approved of TASK-162']
        no_submission = ['state: the task is in None with no submission; only VERIFYING or IN_REVIEW after a '
                         'submission is evaluated']
        for read_log, reason, findings in (
                (lambda root: 'text', 'log', ['log: read_log gave str, not bytes']),
                (lambda root: b'garbage\n', 'log', None),
                (boom, 'log', ['log: a step raised OSError']),
                (lambda root: b'', 'state', no_approval),
                (lambda root: Log().add('task.approved', {
                    'contract_version': 'v1', 'contract_hash': SHA, 'approval_record': 'r'}, 'a1').log, 'state',
                 no_submission)):
            w = World()
            out = w.run(read_log=read_log)
            self.assertEqual((out['result'], out['reason'], w.log.calls, w.calls),
                             ('refused', reason, [], {}), (reason, out['findings']))
            if findings is None:
                self.assertTrue(out['findings'] and all(f.startswith('log: line 1: ') for f in out['findings']),
                                out['findings'])
            else:
                self.assertEqual(out['findings'], findings)


class TASK162AC4Contract(unittest.TestCase):
    def test_the_contract_refusals(self):
        """TASK-162 AC4: a refused contract read, no file with contract_at's SHA-256, or a SHA-256 that is not the
        approved contract_hash gives "contract" before any append; the state place is read first and the docs file
        is taken."""
        other = hashlib.sha256(b'other\n').hexdigest()
        no_file = 'contract: no file read at the evaluated commit has the SHA-256 contract_at gave'
        cases = (
            (World(contract_answer=(None, ['contract: TASK-162 is in both folders'])),
             'contract: TASK-162 is in both folders'),
            (World(files={DOCS: TEXT + ' '}), no_file),
            (World(files={}), no_file),
            (World(contract_answer=(({'task': TASK}, other), None), files={DOCS: 'other\n'}),
             'contract: its SHA-256 is not the approved contract_hash'),
        )
        for w, finding in cases:
            out = w.run()
            self.assertEqual((out['result'], out['reason'], out['findings'], w.log.calls),
                             ('refused', 'contract', [finding], []))
            self.assertEqual((out['manifest'], out['manifest_sha256'], out['uncovered']), (None, None, None))
            self.assertNotIn('load_sources', w.calls)
        w = World()
        w.run()
        paths = [c[2] for c in w.calls['read_file']]
        self.assertEqual(paths, [writer.STATE_DIR + '/tasks/TASK-162.yaml', DOCS])


class TASK162AC5Ci(unittest.TestCase):
    def test_the_ci_refusals(self):
        """TASK-162 AC5: a text that does not parse, a value that is not an object, or a refused intake gives "ci"."""
        for ci_text, finding in (('not json', 'json: json.loads gave JSONDecodeError'),
                                 ('[1]', 'ci: the CI data is not a JSON object'),
                                 ('{"a": 1, "a": 2}', 'duplicate: the text holds a duplicate')):
            w = World()
            out = w.run(ci_text=ci_text)
            self.assertEqual((out['reason'], out['findings'], w.log.calls), ('ci', [finding], []), ci_text)
            self.assertEqual((out['manifest'], out['manifest_sha256'], out['uncovered']), (None, None, None))
            self.assertNotIn('read_ci_data', w.calls)
        w = World(intake={'result': 'refused', 'runs': None, 'files': None,
                          'findings': [{'reason': 'run', 'detail': 'no eligible run'}]})
        out = w.run()
        self.assertEqual((out['reason'], out['findings']), ('ci', ['run: no eligible run']))
        self.assertNotIn('load_sources', w.calls)


class TASK162AC6Sources(unittest.TestCase):
    def test_the_policy_ref(self):
        """TASK-162 AC6: no input_state mapping, no base_commit, one that is not 40 lowercase hexadecimal characters or
        one equal to the evaluated commit gives "policy_ref" before the sources are read."""
        for state in (None, 'x', {}, {'base_commit': 'a' * 39}, {'base_commit': 'A' * 40}, {'base_commit': COMMIT}):
            contract = {'task': TASK} if state is None else {'task': TASK, 'input_state': state}
            w = World(contract_answer=((contract, SHA), None))
            out = w.run()
            self.assertEqual((out['reason'], w.log.calls), ('policy_ref', []), state)
            self.assertEqual((out['manifest'], out['manifest_sha256'], out['uncovered']), (None, None, None))
            self.assertNotIn('load_sources', w.calls)

    def test_a_loader_refusal(self):
        """TASK-162 AC6: a refusal of load_sources, the pin line's among them, gives "sources" with its reason and
        detail."""
        w = World(loaded={'result': 'refused', 'sources': None, 'changed_paths': None, 'provenance': [],
                          'findings': [{'reason': 'pin', 'detail': 'log 1 has no pin line'}]})
        out = w.run()
        self.assertEqual((out['reason'], out['findings'], w.log.calls),
                         ('sources', ['pin: log 1 has no pin line'], []))
        self.assertEqual((out['manifest'], out['manifest_sha256'], out['uncovered']), (None, None, None))


class TASK162AC7Inputs(unittest.TestCase):
    def test_an_inputs_refusal(self):
        """TASK-162 AC7: every refusal of eval_inputs gives "inputs" with its reason and detail."""
        for reason in ('gap', 'ci', 'conflict'):
            w = World(inputs_refusal={'reason': reason, 'detail': 'd'})
            out = w.run()
            self.assertEqual((out['reason'], out['findings'], w.log.calls, out['manifest']),
                             ('inputs', ['%s: d' % reason], [], None))

    def test_the_manifest_arguments_are_fresh_trees(self):
        """TASK-162 AC7: the manifest gets the contract's SHA-256, copies in which no list or mapping stands twice, and
        none of the caller's own containers."""
        w = World()
        w.run()
        args = w.calls['manifest'][0]
        self.assertEqual(args[:4], (TASK, COMMIT, BASE, SHA))
        self.assertEqual(args[4], w.provenance)
        seen = []

        def walk(value):
            if isinstance(value, (dict, list)):
                seen.append(id(value))
                for v in (value.values() if isinstance(value, dict) else value):
                    walk(v)
        for value in args[4:7]:
            walk(value)
        self.assertEqual(len(seen), len(set(seen)))
        self.assertNotIn(id(w.provenance), seen)
        self.assertNotIn(id(w.intake['files']), seen)

    def test_a_manifest_refusal(self):
        """TASK-162 AC7: a refused manifest gives "manifest" and nothing is appended."""
        w = World(manifest_refusal={'reason': 'plain', 'detail': 'd'})
        out = w.run()
        self.assertEqual((out['reason'], out['findings'], w.log.calls, out['manifest_sha256']),
                         ('manifest', ['plain: d'], [], None))
        self.assertEqual(out['uncovered'], [{'gate': 'G3'}])


class TASK162AC8Appends(unittest.TestCase):
    def test_ids_times_and_expected_hashes(self):
        """TASK-162 AC8: each record is appended as record.added with the task id, the derived event id, now, the
        recorder and the SHA-256 of the log read followed by the earlier lines."""
        w = World()
        start = w.log.log
        w.run()
        lines = w.log.log[len(start):].splitlines(True)
        self.assertEqual(len(lines), 3)
        current = start
        for call, line in zip(w.log.calls, lines):
            root, event_type, payload, ident, at, recorder, task_id, expected = call
            self.assertEqual((root, event_type, at, recorder, task_id), (ROOT, 'record.added', NOW, REC, TASK))
            self.assertEqual(ident, event_id(payload['record_id']))
            self.assertEqual(expected, hashlib.sha256(current).hexdigest())
            current += line
        self.assertEqual([c[2]['record_id'] for c in w.log.calls[:2]], ['ci-1', 'ci-2'])
        self.assertEqual(w.log.calls[2][2]['evidence_type'], 'evaluation_manifest')

    def test_a_second_run_appends_no_record_the_log_holds(self):
        """TASK-162 AC8 (D-7278 C4): after a run whose decision step refused, a second run appends no CI record and no
        manifest record again and goes on to the decision."""
        w = World(answer={'result': 'refused', 'reason': 'git', 'findings': ['git: x'], 'event_id': None,
                          'changed_paths': None, 'decision': None, 'next_task_state': None})
        first = w.run()
        self.assertEqual((first['reason'], len(first['appended'])), ('evaluate', 3))
        w.answer = dict(w.answer, result='evaluated', reason=None, findings=[], decision='ACCEPT')
        before = w.log.log
        second = w.run()
        self.assertEqual((second['result'], second['appended'], len(w.log.calls)), ('evaluated', [], 3))
        self.assertEqual(w.log.log, before)

    def test_a_different_record_under_the_manifest_id_refuses(self):
        """TASK-162 AC8: a payload of the task under the manifest's record_id that differs gives "append" with nothing
        written."""
        held_id = manifest_record_id(World().run()['manifest_sha256'])
        held = dict(record(1), record_id=held_id, recorder='another')
        w = World()
        w.log.add('record.added', held, 'held-1')
        out = w.run()
        self.assertEqual((out['reason'], out['findings'], w.log.calls, out['appended']),
                         ('append', ['append: the log holds another record under the manifest record_id ' + held_id],
                          [], []))
        self.assertEqual(text_sha(out['manifest']), out['manifest_sha256'])

    def test_check_all_before_the_first_append(self):
        """TASK-162 AC8: a record that would not be appended anywhere in the list gives "append" with nothing
        written."""
        bad = dict(record(2))
        del bad['fact_kind']
        w = World(ci_records=[record(1), bad])
        out = w.run()
        self.assertEqual((out['reason'], w.log.calls), ('append', []), out['findings'])

    def test_a_refused_or_raising_append_stops(self):
        """TASK-162 AC8: a refused or raising append gives "append", stops, and appended names what was written; the
        writer's "nostore" refuses so."""
        refused = ['append: record ci-2 was not appended (refused, changed)', 'changed: stand-in']
        raised = ['append: record ci-2 raised OSError; whether it was written is not known']
        nostore = ['append: record ci-1 was not appended (refused, nostore)', 'nostore: stand-in']
        for answers, written, call_count, findings in (({2: 'changed'}, ['ci-1'], 2, refused),
                                                       ({2: OSError('x')}, ['ci-1'], 2, raised),
                                                       ({1: 'nostore'}, [], 1, nostore)):
            w = World()
            w.log.answers = answers
            out = w.run()
            self.assertEqual((out['result'], out['reason'], out['appended'], len(w.log.calls)),
                             ('refused', 'append', written, call_count), out['findings'])
            self.assertEqual(out['findings'], findings)
            self.assertEqual(text_sha(out['manifest']), out['manifest_sha256'])
            self.assertEqual(out['uncovered'], [{'gate': 'G3'}])
            self.assertNotIn('evaluate_task', w.calls)


    def test_a_raise_after_the_line_is_written(self):
        """TASK-162 AC8 (D-7331): an append that raises after it wrote the line gives "append", names that record as not
        known whether it was written, keeps appended to the confirmed writes and calls nothing after."""
        for failing, written in ((1, []), (2, ['ci-1'])):
            w = World()
            start = w.log.log

            def writes_then_raises(*args, real=w.log.append, w=w, failing=failing, **kwargs):
                result = real(*args, **kwargs)
                if len(w.log.calls) == failing:
                    raise OSError('x')
                return result

            w.log.append = writes_then_raises
            out = w.run()
            finding = 'append: record ci-%d raised OSError; whether it was written is not known' % failing
            self.assertEqual((out['result'], out['reason'], out['appended'], out['findings'], len(w.log.calls)),
                             ('refused', 'append', written, [finding], failing))
            self.assertEqual(len(w.log.log[len(start):].splitlines()), failing)
            self.assertEqual(text_sha(out['manifest']), out['manifest_sha256'])
            self.assertNotIn('evaluate_task', w.calls)


class TASK162AC9Decision(unittest.TestCase):
    def test_the_answers_of_evaluate_task(self):
        """TASK-162 AC9: "duplicate" and an error record's decision None are passed through; "refused" and an answer
        out of form give "evaluate"."""
        base = World().answer
        for changes in ({'result': 'duplicate'}, {'decision': None}):
            w = World(answer=dict(base, **changes))
            out = w.run()
            self.assertEqual((out['result'], out['reason'], out['decision']),
                             (w.answer['result'], None, w.answer['decision']), changes)
        w = World(answer=dict(base, result='refused', reason='store', findings=['store: x']))
        out = w.run()
        self.assertEqual((out['result'], out['reason'], out['findings']),
                         ('refused', 'evaluate', ['evaluate: refused store', 'store: x']))
        self.assertEqual(text_sha(out['manifest']), out['manifest_sha256'])
        for answer in (None, {}, dict(base, extra=1), dict(base, result='done'), dict(base, findings='x')):
            w = World(answer=answer)
            out = w.run()
            self.assertEqual((out['reason'], out['findings']),
                             ('evaluate', ['evaluate: evaluate_task gave an answer out of form']), answer)
            self.assertEqual(text_sha(out['manifest']), out['manifest_sha256'])


class TASK163AC6Contract(unittest.TestCase):
    def test_another_contract_of_the_loader_refuses(self):
        """TASK-163 AC6: a provenance that is not a list of mappings, none or two mappings with the key contract, a
        further key, or another digest or commit gives "sources" with one finding, before the inputs and with nothing
        appended."""
        good = {'contract': SHA, 'commit': COMMIT}
        other = {'path': 'p'}
        finding = "sources: the loader's contract digest or commit differs from the command's"
        for provenance in ([other], [other, good, dict(good)], [dict(good, path='p')], [{'contract': SHA}],
                           [dict(good, contract='f' * 64)], [dict(good, commit=BASE)], [good, 'x'], (good,), None):
            w = World(loaded={'result': 'present', 'sources': {'s': 1}, 'changed_paths': ['src/x.py'],
                              'provenance': provenance, 'findings': []})
            out = w.run()
            self.assertEqual((out['result'], out['reason'], out['findings'], w.log.calls, out['appended']),
                             ('refused', 'sources', [finding], [], []), provenance)
            self.assertEqual((out['manifest'], out['manifest_sha256'], out['uncovered']), (None, None, None))
            self.assertNotIn('eval_inputs', w.calls)

    def test_an_answer_without_provenance_refuses(self):
        """TASK-163 AC6: a present answer of the loader without a provenance is refused the same way."""
        w = World(loaded={'result': 'present', 'sources': {'s': 1}, 'changed_paths': ['src/x.py'], 'findings': []})
        out = w.run()
        self.assertEqual((out['reason'], w.log.calls), ('sources', []), out['findings'])

    def test_the_same_contract_goes_on(self):
        """TASK-163 AC6: the one entry with the command's digest and commit goes on to the decision."""
        w = World(loaded={'result': 'present', 'sources': {'s': 1}, 'changed_paths': ['src/x.py'],
                          'provenance': [{'contract': SHA, 'commit': COMMIT}], 'findings': []})
        out = w.run()
        self.assertEqual((out['result'], len(out['appended'])), ('evaluated', 3), out['findings'])


# TASK-166: the review records.
PROFILE = [{'dimension': 'SEC-002', 'evidence_types': ['ai_review']},
           {'dimension': 'GOV-004', 'evidence_types': ['human_review']}]
IV = {'SPEC-001': 'v2'}


def other_model(**changes):
    e = {'dimension': 'SEC-002', 'evidence_type': 'other_model_review', 'commit': COMMIT, 'outcome': 'pass',
         'decision_ref': 'D-1', 'models': {'reviewer': 'm-a', 'implementer': 'm-b'}}
    e.update(changes)
    return e


def agent_review(**changes):
    e = {'dimension': 'GOV-004', 'evidence_type': 'decision_agent_review', 'commit': COMMIT, 'outcome': 'pass',
         'decision_ref': 'D-2', 'basis': 'b-1', 'stands_for': 'human_review'}
    e.update(changes)
    return e


def reviews_text(*entries):
    return json.dumps(list(entries or (other_model(), agent_review())))


# The ids are the SHA-256 of "review-record", TASK-162, the commit and each entry's canonical JSON text, joined by line
# feeds, computed outside the code under test.
OTHER_ID = 'bb01344211503d6a08ea6fda3a0f56061c82c343bff5a13bb7df5ee2fdc9f0fa'
AGENT_ID = 'a3b4362ac77c10ca6e9189ee043042212059a3461d7e36ecbf294bfdea77ebcd'
OTHER_RECORD = {'record_id': OTHER_ID, 'fact_kind': 'observation', 'source_class': 'same_lineage_review',
                'recorder': 'aieos cli evaluate', 'subject': 'TASK-162', 'commit': '3' * 40,
                'intent_versions': {'SPEC-001': 'v2'}, 'evidence_type': 'other_model_review', 'dimension': 'SEC-002',
                'outcome': 'pass', 'decision_ref': 'D-1', 'models': {'reviewer': 'm-a', 'implementer': 'm-b'}}
AGENT_RECORD = {'record_id': AGENT_ID, 'fact_kind': 'observation', 'source_class': 'decision_agent',
                'recorder': 'aieos cli evaluate', 'subject': 'TASK-162', 'commit': '3' * 40,
                'intent_versions': {'SPEC-001': 'v2'}, 'evidence_type': 'decision_agent_review',
                'dimension': 'GOV-004', 'outcome': 'pass', 'decision_ref': 'D-2', 'basis': 'b-1',
                'stands_for': 'human_review'}


class ReviewWorld(World):
    """World with intent versions in the inputs' declared values and a stand-in for governor.derive_inputs."""

    derived = None

    def eval_inputs(self, *args):
        out = World.eval_inputs(self, *args)
        out['declared'] = {'intent_versions': dict(IV)}
        return out

    def derive_inputs(self, values):
        self.seen('derive_inputs', (values,))
        return {'evidence_profile': copy.deepcopy(PROFILE)} if self.derived is None else self.derived

    def run_reviews(self, text):
        def manifest(*args, **keywords):
            self.seen('manifest', args)
            self.manifest_keywords = keywords
            return REAL_MANIFEST(*args, **keywords)

        with mock.patch.object(base_inputs, 'contract_at', self.contract_at), \
                mock.patch.object(base_files, 'read_file', self.read_file), \
                mock.patch.object(evaluation_intake, 'read_ci_data', self.read_ci_data), \
                mock.patch.object(evaluation_sources, 'load_sources', self.load_sources), \
                mock.patch.object(eval_inputs, 'eval_inputs', self.eval_inputs), \
                mock.patch.object(governor, 'derive_inputs', self.derive_inputs), \
                mock.patch.object(evaluation_intake, 'manifest', manifest), \
                mock.patch.object(evaluation, 'evaluate_task', self.evaluate_task):
            return evaluate_command.evaluate(ROOT, REPO, TASK, CI_TEXT, REC, NOW, read_log=self.log.read_log,
                                             append=self.log.append, reviews_text=text)


class TASK166Command(unittest.TestCase):
    def test_the_reviews_are_appended_between_the_ci_records_and_the_manifest(self):
        """TASK-166 AC4: the profile comes from derive_inputs on the inputs' values, the records join the batch, and the
        manifest names the text's SHA-256."""
        text = reviews_text()
        w = ReviewWorld()
        out = w.run_reviews(text)
        self.assertEqual((out['result'], out['reason']), ('evaluated', None), out['findings'])
        self.assertEqual(out['appended'],
                         ['ci-1', 'ci-2', OTHER_ID, AGENT_ID, manifest_record_id(out['manifest_sha256'])])
        self.assertEqual([c[2] for c in w.log.calls[2:4]], [OTHER_RECORD, AGENT_RECORD])
        self.assertEqual(w.calls['derive_inputs'], [({'v': 1},)])
        self.assertEqual(w.manifest_keywords, {'reviews_sha256': text_sha(text)})
        self.assertEqual(json.loads(out['manifest'])['reviews_sha256'], text_sha(text))
        self.assertEqual(w.order[w.order.index('eval_inputs') + 1:][:2], ['derive_inputs', 'manifest'])

    def test_without_a_text_no_profile_is_derived_and_the_manifest_has_no_keyword(self):
        """TASK-166 AC4: with None every step is the one of before."""
        w = ReviewWorld()
        out = w.run_reviews(None)
        self.assertEqual((out['result'], len(out['appended']), w.manifest_keywords), ('evaluated', 3, {}))
        self.assertNotIn('derive_inputs', w.calls)
        self.assertNotIn('reviews_sha256', out['manifest'])

    def test_a_second_run_appends_nothing(self):
        """TASK-166 AC4: a review record the log holds is left out."""
        w = ReviewWorld()
        first = w.run_reviews(reviews_text())
        before = w.log.log
        second = w.run_reviews(reviews_text())
        self.assertEqual((len(first['appended']), second['result'], second['appended'], w.log.log),
                         (5, 'evaluated', [], before))

    def test_an_equal_held_record_is_left_out_alone(self):
        """TASK-166 AC4: only the held review record is left out."""
        w = ReviewWorld()
        w.log.add('record.added', copy.deepcopy(OTHER_RECORD), 'held-r')
        out = w.run_reviews(reviews_text())
        self.assertEqual(out['appended'], ['ci-1', 'ci-2', AGENT_ID, manifest_record_id(out['manifest_sha256'])])

    def test_a_different_held_record_refuses_and_writes_nothing(self):
        """TASK-166 AC4: another payload under a review's record_id gives "append" with nothing written."""
        held = dict(AGENT_RECORD, recorder='another')
        w = ReviewWorld()
        w.log.add('record.added', held, 'held-r')
        out = w.run_reviews(reviews_text())
        self.assertEqual((out['reason'], out['findings'], w.log.calls, out['appended']),
                         ('append', ['append: the log holds another record under the record_id ' + AGENT_ID], [], []))

    def test_a_refused_file_appends_nothing(self):
        """TASK-166 AC4: a refusal of the maker gives the reason reviews, before the manifest."""
        for text, start in (('[]', 'entry: '), ('{', 'json: '), (reviews_text(agent_review(commit=BASE)), 'entry: '),
                            (reviews_text(other_model(dimension='other')), 'entry: ')):
            w = ReviewWorld()
            out = w.run_reviews(text)
            self.assertEqual((out['result'], out['reason'], w.log.calls, out['manifest'], out['appended']),
                             ('refused', 'reviews', [], None, []), text)
            self.assertEqual(len(out['findings']), 1)
            self.assertTrue(out['findings'][0].startswith(start), out['findings'])
            self.assertEqual(out['uncovered'], [{'gate': 'G3'}])
            self.assertNotIn('evaluate_task', w.calls)

    def test_a_profile_that_cannot_be_derived_refuses(self):
        """TASK-166 AC4: a ValueError of derive_inputs or no profile gives "reviews"."""
        for changes in ({'derived': {'evidence_profile': None}}, {'raises': {'derive_inputs': ValueError('v')}}):
            w = ReviewWorld(**changes)
            out = w.run_reviews(reviews_text())
            self.assertEqual((out['reason'], w.log.calls, out['manifest']), ('reviews', [], None), changes)

    def test_another_raise_in_the_step_names_it(self):
        """TASK-166 AC4: an unexpected raise in the step is a refusal with the reason reviews."""
        w = ReviewWorld(raises={'derive_inputs': KeyError('k')})
        out = w.run_reviews(reviews_text())
        self.assertEqual((out['reason'], out['findings']), ('reviews', ['reviews: a step raised KeyError']))

    def test_a_text_that_is_not_a_str_is_an_argument_refusal(self):
        """TASK-166 AC4: any other value than None or a str refuses before anything is read."""
        for value in (b'[]', 5, []):
            w = ReviewWorld()
            out = w.run_reviews(value)
            self.assertEqual((out['reason'], out['findings'], w.log.reads, w.calls),
                             ('argument', ['argument: reviews_text is not a str'], 0, {}), value)


if __name__ == '__main__':
    unittest.main()

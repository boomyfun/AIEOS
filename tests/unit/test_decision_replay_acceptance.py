"""Unit tests of the replay of decision.acceptance lines in aieos_bootstrap.decision_replay (task TASK-167; DEF-0137 task
B). Every Git answer comes from a stand-in read over objects held in memory; no test runs Git, starts a process or writes a
file. The literal ids and the literal record below are typed here; they are never copied from a run of the replay or of
the governor."""

import copy
import datetime
import hashlib
import json
import pathlib
import sys
import unittest
from unittest import mock

import aieos_bootstrap
from aieos_bootstrap import decision_replay, eventlog

ROOT = str(pathlib.Path(__file__).resolve().parents[2])
TASK = 'TASK-900'
NOW = datetime.datetime(2026, 11, 27, 12, 0, 0, tzinfo=datetime.timezone.utc)
FENCE = {'epoch': 'e0', 'counter': 1}

A_SHA = 'b6a98d9ce9a2d9149288fa3df42d377c3e42737afdcdaf714e33c0a100b51060'
PIN = '94e9304305697f915bc3f98960ee965e0336553782241fb94446db5bc42c1a48'
P = '1122ff902969e417bce3569c1568f0b02a02ab31'
CONTRACT_SHA = 'f0d969d4fee48a4ff15eb407d4c18a099a338a0453f0ff188dd109bd803c6906'
E = '7fd8ed7d0544f6387f2f8aa3a08724133879983f'
CONTENT = '4c92dbd91d3b07f95676dcbf7f6ff1bd5dcda1cb31f042a00c2065e8452c3deb'
RECORD_ID = 'decision-9c6f2b96a051418db9beb944443bde0918d83274a747918084e657175e102e18'
EVENT_ID = '9412c94ca85ddcd95947a19d8e2f7d627b591f4691143210217c085860a5aa4a'
RECORD_ID_NOTED = 'decision-553b8196a98b285ba39f3a49350e7d705cdfc1b6d14a3e9c3936b3bc51f2bc64'
EVENT_ID_NOTED = '5ee2b77d5f4ad945996255db5ebf5db2622912c60d4ec148d7384c60aed7ab27'

POLICY_PATH = 'docs/specs/evaluation-policy-gov-aieos.md'
GOVERNOR_PATH = 'src/aieos_bootstrap/governor.py'
RESUME_PATH = 'src/aieos_bootstrap/resume_check.py'
CONTRACT_PATH = 'docs/tasks/TASK-900.yaml'
LOG_PATH = 'state/events.jsonl'
POLICY_TEXT = ('## 3. The sources\n\n```yaml\nowner_kept_rules: []\narticles: []\ndefault_profiles:\n  low:\n'
               '    - {dimension: functional, evidence_types: [build]}\nrequirement_profiles: []\ndelegation: true\n'
               'auto_accept:\n  low: false\n```\n')
RISK_TEXT = ('## 3. The rules\n\n```yaml\npolicy_version: v7\nrisk_rules:\n'
             '  - match: { paths: ["docs/**", "src/**"] }\n    risk: low\n```\n')
GOVERNOR_TEXT = '# a stand-in governor file: the replay hashes it and imports the real module\n'
OTHER_GOVERNOR = '# another stand-in governor file\n'
RESUME_TEXT = '# a stand-in resume check file\n'
RESUME_PIN = hashlib.sha256(RESUME_TEXT.encode('utf-8')).hexdigest()
A_TEXT = 'alpha\n'
DM_TEXT = '# DM\n\n| A1 | `docs/a.md` revision 3 (%s), a row |\n' % A_SHA
CONTRACT_FORM = ('task: TASK-900\ncontract_version: v1\ntraces_to:\n  - docs/a.md\ninput_state:\n  base_commit: %s\n'
                 '  intent_versions:\n    docs/a.md: %s\nwrite_set:\n  paths:\n    - docs/b.md\nread_set:\n  paths:\n'
                 '    - docs/a.md\nacceptance_criteria:\n  - AC1: x\nrisk: low\nautonomy:\n  budgets: {retries: 1}\n'
                 'verification_plan:\n  - {gate: G0, check: scope}\nowner_kept_act: false\n')

PAYLOAD = {
    'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_local',
    'recorder': 'src/aieos_bootstrap/governor.py', 'subject': 'TASK-900', 'governor_identity': None,
    'scenario_set_hash': None, 'policy_version': 'v7', 'level_version': 'L1:v7',
    'ruleset_version': 'governor-sha256:' + PIN, 'decision': 'INSUFFICIENT_EVIDENCE', 'next_task_state': 'REWORK',
    'table_row': 3, 'task_content_hash': CONTENT, 'evaluated_commit': E, 'intent_versions': {'docs/a.md': 'v3'},
    'profile_used': [{'dimension': 'functional', 'required': ['build'], 'satisfied_by': [],
                      'missing_types': ['build']}],
    'missing_gates': ['G0'], 'blocking': [], 'failed_gates': [], 'reverify': [], 'approval_record': None,
    'uncovered': [
        'advisory: decisions of this governor are advisory (governor-spec.md section 10)',
        'inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository',
        "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this "
        "module's defaults, not the channel or the identity that specification 2 section 6.4 names",
    ],
    'rests_on_ai': {'entries': [], 'approval': False},
    'record_id': RECORD_ID,
}
OTHER_RECORD = {'record_id': 'rec-x', 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
                'recorder': 'x', 'subject': 'TASK-900'}
GATED = ('aieos_bootstrap.governor', 'aieos_bootstrap.evaluation_sources', 'aieos_bootstrap.evaluation')


def ok(out):
    return {'exit': 0, 'out': out, 'err': b'', 'error': None}


def failed():
    return {'exit': 128, 'out': b'', 'err': b'fatal', 'error': None}


def gid(kind, data):
    return hashlib.sha1(b'%s %d\x00' % (kind.encode('ascii'), len(data)) + data, usedforsecurity=False).hexdigest()


class Git:
    """A stand-in for gitread.run over objects held in memory: ids are Git's own hashes of the objects."""

    def __init__(self):
        self.objects = {}
        self.diffs = {}
        self.calls = []
        self.override = {}

    def put(self, kind, data):
        oid = gid(kind, data)
        self.objects[oid] = (kind, data)
        return oid

    def tree_of(self, files):
        top = {}
        for path, text in files.items():
            parts = path.split('/')
            d = top
            for part in parts[:-1]:
                d = d.setdefault(part, {})
            d[parts[-1]] = text

        def make(d):
            entries = []
            for name, value in d.items():
                if isinstance(value, dict):
                    entries.append(('040000', 'tree', make(value), name))
                else:
                    entries.append(('100644', 'blob', self.put('blob', value.encode('utf-8')), name))
            return self.put('tree', ''.join('%s %s %s\t%s\n' % e for e in entries).encode('utf-8'))
        return make(top)

    def commit(self, tree, parents=(), message='m\n'):
        head = 'tree %s\n' % tree + ''.join('parent %s\n' % p for p in parents)
        text = head + 'author A B 1 +0000\ncommitter A B 1 +0000\n\n' + message
        return self.put('commit', text.encode('utf-8'))

    def __call__(self, repo, args, timeout=None):
        self.calls.append(list(args))
        key = tuple(args)
        if key in self.override:
            return self.override[key]
        oid = args[-1]
        if args[0] == 'rev-parse':
            return ok((oid + '\n').encode('ascii')) if oid in self.objects else failed()
        if args[:2] == ['cat-file', '-t'] and oid in self.objects:
            return ok((self.objects[oid][0] + '\n').encode('ascii'))
        if args[:2] == ['cat-file', '-p'] and oid in self.objects:
            return ok(self.objects[oid][1])
        if args[0] == 'diff-tree' and oid in self.diffs:
            return ok(self.diffs[oid])
        return failed()


def compact(event):
    return json.dumps(event, sort_keys=True, separators=(',', ':')).encode('utf-8')


class World:
    """The policy commit, the task commit, the event log with one acceptance line and the checked commit that holds it."""

    def __init__(self, policy_text=POLICY_TEXT, governor_at_policy=GOVERNOR_TEXT, governor_checked=GOVERNOR_TEXT,
                 changed=('docs/b.md', 'docs/c.md'), records=(), payload=PAYLOAD, event_id=EVENT_ID,
                 resume_text=RESUME_TEXT, contract_form=CONTRACT_FORM):
        g = self.git = Git()
        base = {POLICY_PATH: policy_text, 'docs/specs/risk-rules-gov-aieos.md': RISK_TEXT,
                GOVERNOR_PATH: governor_at_policy, 'docs/pre-genesis/decision-matrix.md': DM_TEXT, 'docs/a.md': A_TEXT,
                RESUME_PATH: resume_text}
        self.policy = g.commit(g.tree_of(base), message='policy\n')
        self.contract = contract_form % (self.policy, A_SHA)
        self.evaluated = g.commit(g.tree_of(dict(base, **{CONTRACT_PATH: self.contract})), parents=(self.policy,),
                                  message='work\n\nAIEOS-Task: TASK-900\n')
        g.diffs[self.evaluated] = b''.join(name.encode('utf-8') + b'\x00' for name in changed)
        log = self.append(b'', 'task.approved', {
            'contract_version': 'v1', 'contract_hash': hashlib.sha256(self.contract.encode('utf-8')).hexdigest(),
            'approval_record': 'rec-a'}, 'a1')
        lease = {'task_id': TASK, 'fencing_token': FENCE, 'expires_at': NOW + datetime.timedelta(hours=1)}
        log = self.append(log, 'task.submitted', {'commit': self.evaluated, 'compensating': False}, 's1',
                          fencing_token=FENCE, lease=lease)
        for n, record in enumerate(records, 1):
            log = self.append(log, 'record.added', record, 'r%d' % n)
        self.index = log.count(b'\n')
        self.log = self.append(log, 'decision.acceptance', copy.deepcopy(payload), event_id)
        checked = dict(base, **{GOVERNOR_PATH: governor_checked, LOG_PATH: self.log.decode('utf-8')})
        self.checked = g.commit(g.tree_of(checked), parents=(self.evaluated,), message='state\n')

    @staticmethod
    def append(log, event_type, payload, event_id, fencing_token=None, lease=None):
        r = eventlog.append(log, event_type, payload, event_id, NOW, task_id=TASK, fencing_token=fencing_token,
                            lease=lease)
        assert r.result == 'appended', (r.result, r.findings)
        return log + r.line

    def changed_line(self, change):
        """The log with the acceptance line changed by change(event)."""
        lines = self.log.split(b'\n')[:-1]
        event = json.loads(lines[self.index].decode('utf-8'))
        change(event)
        lines[self.index] = compact(event)
        return b'\n'.join(lines) + b'\n'

    def replay(self, log=None, repo=ROOT, pin=PIN):
        return decision_replay._replay_acceptance(repo, self.log if log is None else log, self.index, pin, self.checked,
                                                  self.git)


class TheFixture(unittest.TestCase):
    def test_the_fixture_gives_the_literal_ids(self):
        w = World()
        self.assertEqual(w.policy, P)
        self.assertEqual(w.evaluated, E)
        self.assertEqual(hashlib.sha256(w.contract.encode('utf-8')).hexdigest(), CONTRACT_SHA)
        self.assertEqual(hashlib.sha256(GOVERNOR_TEXT.encode('utf-8')).hexdigest(), PIN)
        self.assertEqual(hashlib.sha256(A_TEXT.encode('utf-8')).hexdigest(), A_SHA)


class TheReplay(unittest.TestCase):
    def test_the_literal_record_replays(self):
        """TASK-167 AC6, AC7 and AC10."""
        w = World()
        self.assertEqual(w.replay(), [])
        diffs = [c for c in w.git.calls if c[0] == 'diff-tree']
        self.assertTrue(diffs)
        self.assertTrue(all('--no-renames' in c for c in diffs))

    def test_a_changed_payload_value_fails_and_is_named(self):
        w = World()
        log = w.changed_line(lambda e: e['payload'].update(policy_version='v8'))
        self.assertEqual(w.replay(log), ['record: the recomputed record differs from the logged one at: policy_version'])

    def test_an_added_key_fails_and_is_named(self):
        w = World()
        found = w.replay(w.changed_line(lambda e: e['payload'].update(extra=1)))
        self.assertEqual(found, ["log: line 3: 6.4:unknown_key: payload has the key 'extra', which sections 6.2 and 6.4 "
                                 "do not name"])

    def test_a_removed_key_fails_and_is_named(self):
        w = World()
        found = w.replay(w.changed_line(lambda e: e['payload'].pop('scenario_set_hash')))
        self.assertEqual(found, ['record: the recomputed record differs from the logged one at: scenario_set_hash'])

    def test_a_changed_event_id_fails_and_is_named(self):
        w = World()
        log = w.changed_line(lambda e: e.update(event_id='another'))
        self.assertEqual(w.replay(log), ['record: the recomputed record differs from the logged one at: event_id'])

    def test_a_changed_task_id_fails_and_is_named(self):
        w = World()
        found = w.replay(w.changed_line(lambda e: e.update(task_id='TASK-901')))
        self.assertEqual(found, ["log: line 3: 6.1:task_id: task_id differs from the record subject 'TASK-900'"])

    def test_another_ruleset_version_fails_before_the_governor(self):
        w = World()
        log = w.changed_line(lambda e: e['payload'].update(ruleset_version='governor-sha256:' + '0' * 64))
        self.assertEqual(w.replay(log), ['record: ruleset_version is not "governor-sha256:" and the governor pin'])

    def test_a_governor_at_the_checked_commit_that_is_not_the_pin_fails(self):
        w = World(governor_checked=OTHER_GOVERNOR)
        self.assertEqual(w.replay(),
                         ['governor: the governor at the checked commit is not the pinned one; it is not imported'])

    def test_a_governor_at_policy_ref_that_is_not_the_pin_fails(self):
        w = World(governor_at_policy=OTHER_GOVERNOR)
        found = w.replay()
        self.assertEqual(len(found), 1, found)
        self.assertTrue(found[0].startswith('sources: governor: '), found)

    def test_a_governor_file_that_is_not_the_repositorys_fails(self):
        w = World()
        self.assertEqual(w.replay(repo=ROOT + '/elsewhere'),
                         ['governor: the governor file is not the repository\'s src/aieos_bootstrap/governor.py'])

    def test_an_evaluated_commit_that_cannot_be_read_fails_with_its_own_finding(self):
        w = World()
        w.git.override[('cat-file', '-p', w.evaluated)] = failed()
        self.assertEqual(w.replay(), ['record: the evaluated commit %s cannot be read in this checkout' % E])

    def test_a_refused_source_fails(self):
        w = World(policy_text='no policy here\n')
        found = w.replay()
        self.assertEqual(len(found), 1, found)
        self.assertTrue(found[0].startswith('sources: policy: '), found)

    def test_a_repeated_record_id_is_left_out_as_the_evaluation_leaves_it(self):
        """TASK-167 AC10 and the repeated record id of DEF-0152: the second record is left out, the replay passes."""
        payload = copy.deepcopy(PAYLOAD)
        payload['uncovered'] = payload['uncovered'] + ['rec-x: not used: no evidence type or gate']
        payload['record_id'] = RECORD_ID_NOTED
        w = World(records=(OTHER_RECORD, OTHER_RECORD), payload=payload, event_id=EVENT_ID_NOTED)
        self.assertEqual(w.replay(), [])

    def test_a_nan_in_a_line_is_refused_by_the_log_check(self):
        w = World()
        log = w.log.replace(b'"table_row":3', b'"table_row":NaN')
        self.assertNotEqual(log, w.log)
        self.assertEqual(w.replay(log),
                         ['log: line 3: 6.1:json: the line is not one JSON object (NaN is not a JSON value)'])

    def test_the_old_side_of_a_rename_is_in_the_changed_paths(self):
        """TASK-167 AC10 and the rename duty of DEF-0152: the diff lists the old and the new path, both reach the values
        of the evaluation, and the replay passes."""
        from aieos_bootstrap import evaluation
        w = World(changed=('docs/old.md', 'docs/c.md'))
        seen = []
        real = evaluation.evaluate_task

        def watched(*args, **kwargs):
            seen.append(list(args[5]['changed_paths']))
            return real(*args, **kwargs)

        with mock.patch.object(evaluation, 'evaluate_task', watched):
            self.assertEqual(w.replay(), [])
        self.assertEqual(seen, [['docs/c.md', 'docs/old.md']])
        diffs = [c for c in w.git.calls if c[0] == 'diff-tree']
        self.assertTrue(diffs)
        self.assertTrue(all('--no-renames' in c for c in diffs))

    def test_values_that_give_no_risk_fail_as_the_command_refuses_them(self):
        """TASK-167 erratum E1.2: a changed path that no risk rule matches; the governor would give an error record,
        which aieos evaluate never writes, so the replay fails before it calls the evaluation."""
        from aieos_bootstrap import evaluation
        w = World(changed=('.old', 'docs/c.md'))
        with mock.patch.object(evaluation, 'evaluate_task', side_effect=AssertionError('the evaluation was called')):
            self.assertEqual(w.replay(), ['inputs: incomplete: governor.derive_inputs gives no decision: the risk cannot '
                                          'be derived; the evidence profile cannot be derived'])

    def test_a_line_with_a_fencing_token_or_a_corrects_field_fails(self):
        """TASK-167 erratum E1.2: the evaluation writes neither."""
        for key, value in (('fencing_token', {'epoch': 'e0', 'counter': 2}), ('corrects', 'a1')):
            with self.subTest(key):
                w = World()
                log = w.changed_line(lambda e: e.update({key: value}))
                self.assertEqual(w.replay(log),
                                 ['record: line 3 holds %s, which the evaluation does not write' % key])

    def test_a_record_on_the_first_line_and_a_line_of_another_type_fail(self):
        w = World()
        event = json.loads(w.log.split(b'\n')[w.index].decode('utf-8'))
        event['seq'] = 1
        self.assertEqual(
            decision_replay._replay_acceptance(ROOT, compact(event) + b'\n', 0, PIN, w.checked, w.git),
            ['log: a record on the first line has no earlier line to recompute from'])
        self.assertEqual(decision_replay._replay_acceptance(ROOT, w.log, 0, PIN, w.checked, w.git),
                         ['record: line 1 is not a decision.acceptance event'])


class TheLineItself(unittest.TestCase):
    """TASK-167 erratum E2.6: a line that the writer never writes, and arguments that the command refuses."""

    def test_an_ignored_duplicate_line_fails(self):
        w = World()
        event = json.loads(w.log.split(b'\n')[w.index].decode('utf-8'))
        event['seq'] += 1
        log = w.log + compact(event) + b'\n'
        self.assertEqual(
            decision_replay._replay_acceptance(ROOT, log, w.index + 1, PIN, w.checked, w.git),
            ['record: line 4 is an ignored duplicate of line 3, which the writer never writes'])

    def test_a_line_that_is_not_in_the_writers_form_fails(self):
        w = World()
        lines = w.log.split(b'\n')[:-1]
        event = json.loads(lines[w.index].decode('utf-8'))
        reordered = json.dumps(dict(reversed(list(event.items()))), separators=(',', ':')).encode('utf-8')
        spaced = lines[w.index].replace(b'"task_id":', b'"task_id": ', 1)
        for what, line in (('keys reordered', reordered), ('a space after a colon', spaced)):
            with self.subTest(what):
                self.assertNotEqual(line, lines[w.index])
                self.assertEqual(json.loads(line.decode('utf-8')), event)
                log = b'\n'.join(lines[:w.index] + [line]) + b'\n'
                self.assertEqual(w.replay(log), ['record: line 3 is not in the form the writer writes'])

    def test_a_log_that_does_not_end_with_lf_fails(self):
        w = World()
        self.assertEqual(w.replay(w.log[:-1]), ['log: the log does not end with LF'])

    def test_a_contract_that_the_commands_argument_checks_refuse_fails(self):
        cases = (
            ('risk: low\n', 'risk: Low\n', 'contract has no risk of low, medium, high or critical'),
            ('owner_kept_act: false\n', 'owner_kept_act: yes\n',
             'contract has no owner_kept_act that is the text true or false'),
        )
        for old, new, text in cases:
            with self.subTest(new.strip()):
                self.assertIn(old, CONTRACT_FORM)
                w = World(contract_form=CONTRACT_FORM.replace(old, new))
                self.assertEqual(w.replay(), ['inputs: argument: ' + text])


class TheGates(unittest.TestCase):
    def without_the_governor(self, call):
        """Run call with the gated modules taken out of the interpreter; give its answer and the names loaded after.
        Every name taken out is recorded, and afterwards each is restored, or deleted when it was not there before."""
        taken = GATED + ('aieos_bootstrap.eval_inputs', 'aieos_bootstrap.evaluate_command')
        shorts = [full.rsplit('.', 1)[1] for full in taken]
        held = {}
        with mock.patch.dict(sys.modules):
            for full in taken:
                sys.modules.pop(full, None)
            for short in shorts:
                if short in vars(aieos_bootstrap):
                    held[short] = vars(aieos_bootstrap)[short]
                    delattr(aieos_bootstrap, short)
            try:
                answer = call()
                loaded = [n for n in GATED if n in sys.modules]
            finally:
                for short in shorts:
                    if short in held:
                        setattr(aieos_bootstrap, short, held[short])
                    elif short in vars(aieos_bootstrap):
                        delattr(aieos_bootstrap, short)
        return answer, loaded

    def test_no_module_that_imports_the_governor_is_loaded_when_a_gate_fails(self):
        """TASK-167 AC5."""
        cases = (
            ('another ruleset_version', World(), lambda w: w.replay(pin='0' * 64)),
            ('another governor at the checked commit', World(governor_checked=OTHER_GOVERNOR), lambda w: w.replay()),
            ('a governor file elsewhere', World(), lambda w: w.replay(repo=ROOT + '/elsewhere')),
            ('a first line', World(), lambda w: decision_replay._replay_acceptance(
                ROOT, w.log, 0, PIN, w.checked, w.git)),
        )
        for what, world, call in cases:
            with self.subTest(what):
                found, loaded = self.without_the_governor(lambda: call(world))
                self.assertTrue(found, what)
                self.assertEqual(loaded, [], what)

    def test_none_of_them_is_loaded_after_the_entrys_own_refusals(self):
        """TASK-167 erratum E1.5: the engine gate, a malformed governor pin and two governor pins."""
        for argv in ([ROOT, '--governor-pin', PIN, '0' * 64], [ROOT, '--governor-pin', 'zz', RESUME_PIN],
                     [ROOT, '--governor-pin', PIN, '--governor-pin', PIN, RESUME_PIN]):
            with self.subTest(argv[1:]):
                w = World()
                (code, lines), loaded = self.without_the_governor(lambda: entry(w, argv))
                self.assertEqual(code, 1, lines)
                self.assertEqual(loaded, [])

    def test_the_entry_loads_none_of_them_without_a_governor_pin(self):
        w = World()
        (code, lines), loaded = self.without_the_governor(lambda: entry(w, [ROOT, RESUME_PIN]))
        self.assertEqual(code, 1, lines)
        self.assertEqual(loaded, [])

    def test_an_engine_with_the_governor_pins_hash_and_no_flag_replays_nothing(self):
        """TASK-167 erratum E2.6: the engine file at HEAD holds the governor's text and that hash is given as an
        accepted engine, with no --governor-pin: the engine gate passes and the hash is not read as a governor pin."""
        w = World(resume_text=GOVERNOR_TEXT)
        (code, lines), loaded = self.without_the_governor(lambda: entry(w, [ROOT, PIN]))
        self.assertEqual(code, 1, lines)
        self.assertTrue(any(l.startswith('NOT REPLAYED: decision.acceptance ')
                            and l.endswith(': no governor pin was given') for l in lines), lines)
        self.assertEqual(loaded, [])

    def test_none_of_them_is_loaded_when_the_engine_gate_passes_and_the_governor_gate_fails(self):
        """TASK-167 erratum E2.6, at the entry."""
        w = World(governor_checked=OTHER_GOVERNOR)
        (code, lines), loaded = self.without_the_governor(
            lambda: entry(w, [ROOT, '--governor-pin', PIN, RESUME_PIN]))
        self.assertEqual(code, 1, lines)
        self.assertTrue(any(l.startswith('FAIL ') and 'is not the pinned one' in l for l in lines), lines)
        self.assertEqual(loaded, [])


def entry(w, argv):
    """The command-line entry over the world: the configuration and status reads are answered clean, HEAD is the checked
    commit and the listing of the tree gives the one event log."""
    def read(repo, args, timeout=None):
        if args[0] == 'config':
            return ok(b'core.bare\nfalse\0')
        if args[0] == 'status':
            return ok(b'')
        if args[0] == 'rev-parse' and args[-1] == 'HEAD':
            return ok((w.checked + '\n').encode('ascii'))
        return w.git(repo, args, timeout)

    real = decision_replay.base_files.list_paths

    def list_paths(repo, commit, prefix, *rest):
        if prefix == '':
            return [LOG_PATH], None
        return real(repo, commit, prefix, *rest)

    lines = []
    with mock.patch.object(decision_replay.base_files, 'list_paths', side_effect=list_paths):
        code = decision_replay.main(argv, read=read, out=lines.append)
    return code, lines


class TheEntry(unittest.TestCase):
    def test_the_literal_record_passes_through_the_entry(self):
        code, lines = entry(World(), [ROOT, '--governor-pin', PIN, RESUME_PIN])
        self.assertEqual(code, 0, lines)
        self.assertTrue(any(l.startswith('REPLAYED ' + RECORD_ID + ' ') and l.endswith(' ok') for l in lines), lines)
        self.assertIn('decision records: 1, replayed and passed: 1, failed: 0', lines[-1])

    def test_without_the_flag_the_line_is_not_replayed_and_fails(self):
        for argv in ([ROOT, RESUME_PIN], [ROOT, RESUME_PIN, PIN]):
            with self.subTest(len(argv)):
                code, lines = entry(World(), argv)
                self.assertEqual(code, 1, lines)
                self.assertTrue(any(l.startswith('NOT REPLAYED: decision.acceptance ')
                                    and l.endswith(': no governor pin was given') for l in lines), lines)
                self.assertIn('replayed and passed: 0, failed: 1', lines[-1])

    def test_a_flag_out_of_form_is_one_line_and_exit_one(self):
        wrong = ([ROOT, '--governor-pin'], [ROOT, '--governor-pin', 'zz'], [ROOT, '--governor-pin', PIN.upper()],
                 [ROOT, '--governor-pin', PIN, '--governor-pin', PIN])
        for argv in wrong:
            with self.subTest(argv[1:]):
                code, lines = entry(World(), argv)
                self.assertEqual((code, lines),
                                 (1, ['FAIL: --governor-pin is given once, followed by 64 lowercase hex characters']))

    def test_the_governor_pin_is_not_an_accepted_engine(self):
        code, lines = entry(World(), [ROOT, '--governor-pin', PIN])
        self.assertEqual(code, 1, lines)
        self.assertTrue(any(l.startswith('FAIL ') and 'not an accepted engine (0 accepted)' in l for l in lines), lines)
        self.assertIn('replayed and passed: 0, failed: 1', lines[-1])

    def test_the_governor_pin_given_alone_does_not_pass_the_engine_gate_even_when_it_is_the_engines_hash(self):
        """TASK-167 erratum E1.5: here the engine file holds the governor's text, so its hash is the governor pin."""
        code, lines = entry(World(resume_text=GOVERNOR_TEXT), [ROOT, '--governor-pin', PIN])
        self.assertEqual(code, 1, lines)
        self.assertTrue(any(l.startswith('FAIL ') and 'not an accepted engine (0 accepted)' in l for l in lines), lines)

    def test_a_failed_acceptance_replay_is_a_fail_line(self):
        code, lines = entry(World(governor_checked=OTHER_GOVERNOR), [ROOT, '--governor-pin', PIN, RESUME_PIN])
        self.assertEqual(code, 1, lines)
        self.assertTrue(any(l.startswith('FAIL ') and 'is not the pinned one' in l for l in lines), lines)


if __name__ == '__main__':
    unittest.main()

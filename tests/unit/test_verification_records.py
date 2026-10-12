"""Unit tests of aieos_bootstrap.verification_records (task TASK-029). The writer is replaced by a stand-in that keeps
a log as bytes and decides each append with eventlog.append, as the real writer does, so no file is touched here; the
only file read is the module's own source, with pathlib's read_bytes. Each test names the criteria it stands for in
its own docstring."""

import ast
import copy
import datetime
import hashlib
import pathlib
import unittest

from aieos_bootstrap import ac_coverage
from aieos_bootstrap import eventlog
from aieos_bootstrap import governor
from aieos_bootstrap import records
from aieos_bootstrap import verification_records as vr
from aieos_bootstrap import writer

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE = ROOT / 'src' / 'aieos_bootstrap' / 'verification_records.py'
FS_ROOT = str(ROOT / 'no-such-state-root')
TASK = 'TASK-500'
COMMIT = 'a' * 40
OLD = 'b' * 40
HASH = 'c' * 64
IV = {'SPEC-001': 'v2'}
REC = 'aieos-core'
NOW = datetime.datetime(2026, 10, 12, 10, 0, 0, tzinfo=datetime.timezone.utc)
CI = 'deterministic_tool_external_ci'


def values(**changes):
    v = {
        'contract': {'traces_to': ['SPEC-001'], 'risk': 'high', 'owner_kept_act': False, 'verification_plan': ['G0', 'G1']},
        'changed_paths': ['src/x.py', 'tests/unit/test_x.py'],
        'risk_rules': [{'id': 'R2', 'match': ['src/**', 'tests/**'], 'class': 'medium'}],
        'owner_kept_rules': [{'id': 'OPS-002', 'match': ['docs/pre-genesis/measurement-protocol.md']}],
        'articles': [{'id': 'INV-002', 'scope': ['src/**'], 'evidence_required': ['ai_review']}],
        'default_profiles': {'medium': [{'dimension': 'functional', 'evidence_types': ['build']}],
                             'high': [{'dimension': 'functional', 'evidence_types': ['unit_test']}]},
        'requirement_profiles': [],
        'delegation': True,
        'evidence_comparison': {'weakens': False},
        'auto_accept': {},
        'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1',
    }
    v.update(changes)
    return v


def coverage(uncovered=False):
    acs = [{'AC1': 'one'}] + ([{'AC2': 'two'}] if uncovered else [])
    return {'acceptance_criteria': acs, 'verification_plan': [{'gate': 'G2', 'check': 'tests', 'args': ['AC1']}],
            'constitution': ['INV-001']}


def build(**changes):
    args = {'task_id': TASK, 'contract_version': 'v1', 'evaluated_commit': COMMIT, 'intent_versions': dict(IV),
            'values': values(), 'coverage_contract': coverage(), 'recorder': REC}
    args.update(changes)
    return vr.build_records(**args)


def sha(*parts):
    return hashlib.sha256('\n'.join(parts).encode('utf-8')).hexdigest()


class Log:
    """A stand-in writer: append decides with eventlog.append (no lease) and keeps the line."""

    def __init__(self):
        self.log = b''
        self.appends = []

    def append(self, root, event_type, payload, event_id, appended_at, recorder, task_id=None, fencing_token=None):
        self.appends.append((root, event_type, payload, event_id, appended_at, recorder, task_id, fencing_token))
        r = eventlog.append(self.log, event_type, payload, event_id, appended_at, task_id=task_id,
                            fencing_token=fencing_token, recorder=recorder)
        if r.result == 'appended':
            self.log += r.line
        return r


def run(log=None, **changes):
    args = {'root': FS_ROOT, 'task_id': TASK, 'contract_version': 'v1', 'evaluated_commit': COMMIT,
            'intent_versions': dict(IV), 'values': values(), 'coverage_contract': coverage(), 'recorder': REC,
            'now': NOW, 'append': (log or Log()).append}
    args.update(changes)
    return vr.record_evaluation(**args)


class Interface(unittest.TestCase):

    def test_each_argument_out_of_its_form_raises(self):
        """TASK-029 AC1: each argument wrong in turn raises ValueError; the right ones build."""
        self.assertEqual(len(build()), 2)
        bad = {'task_id': ['TASK-', 'task-500', 500, None], 'contract_version': ['1', 'v', 'v1a'],
               'evaluated_commit': ['A' * 40, 'a' * 39, 'g' * 40, None], 'intent_versions': [{}, {'X': '1'}, {'': 'v1'}, []],
               'values': [{}, values(policy_version=''), values(policy_version=None), 'v'],
               'recorder': ['', None], 'source_class': ['agent_declared', None]}
        for key, items in bad.items():
            for item in items:
                with self.assertRaises(ValueError, msg=(key, item)):
                    build(**{key: item})

    def test_derive_inputs_raising_raises_a_value_error(self):
        """TASK-029 AC1: governor.derive_inputs raising gives ValueError naming the step."""
        broken = values()
        del broken['articles']
        with self.assertRaisesRegex(ValueError, 'derive_inputs'):
            build(values=broken)
        with self.assertRaisesRegex(ValueError, 'derive_inputs'):
            build(values=values(changed_paths=[]))

    def test_the_arguments_are_not_changed(self):
        """TASK-029 AC1: the arguments are not changed."""
        v, iv, c = values(), dict(IV), coverage(True)
        v0, iv0, c0 = copy.deepcopy(v), dict(iv), copy.deepcopy(c)
        out = build(values=v, intent_versions=iv, coverage_contract=c)
        out[0]['intent_versions']['SPEC-001'] = 'v9'
        out[1]['evidence_profile'].append('x')
        self.assertEqual((v, iv, c), (v0, iv0, c0))
        self.assertNotEqual(build(values=v)[1]['evidence_profile'][-1:], ['x'])


class TheCopies(unittest.TestCase):

    def test_the_exact_records(self):
        """TASK-029 AC2, AC3: the exact records and ids for a classified change."""
        risk, profile = build()
        self.assertEqual(risk, {
            'record_id': sha('risk-class', TASK, COMMIT, 'v2'), 'fact_kind': 'observation',
            'source_class': 'deterministic_tool_local', 'recorder': REC, 'subject': TASK, 'evidence_type': 'risk_class',
            'risk_class': 'medium', 'commit': COMMIT, 'intent_versions': IV})
        expected = governor.derive_inputs(values())['evidence_profile']
        self.assertEqual(profile, {
            'record_id': sha('evidence-profile', TASK, COMMIT, 'v2'), 'fact_kind': 'observation',
            'source_class': 'deterministic_tool_local', 'recorder': REC, 'subject': TASK,
            'evidence_type': 'evidence_profile', 'evidence_profile': expected, 'commit': COMMIT, 'intent_versions': IV})
        self.assertIn({'dimension': 'functional', 'evidence_types': ['unit_test']}, expected)

    def test_the_risk_class_is_the_rules_class_not_the_declared_one(self):
        """TASK-029 AC2: a higher declared risk does not raise the risk_class value; the profile rests on it."""
        for declared in ('high', 'critical', 'low', 'medium'):
            v = values()
            v['contract']['risk'] = declared
            self.assertEqual(build(values=v)[0]['risk_class'], 'medium', declared)
        self.assertEqual(governor.derive_inputs(values())['risk'], 'high')

    def test_an_unmatched_path_gives_null(self):
        """TASK-029 AC2, AC3: a path no rule matches gives a null class, and an underivable profile null."""
        risk, profile = build(values=values(changed_paths=['src/x.py', 'docs/y.md']))
        self.assertIsNone(risk['risk_class'])
        self.assertIsNone(profile['evidence_profile'])
        self.assertEqual(records.check_record(risk), [])
        self.assertEqual(records.check_record(profile), [])

    def test_an_underivable_profile_alone_gives_null(self):
        """TASK-029 AC3: a risk with no default profile gives a null profile and a class."""
        v = values(default_profiles={})
        risk, profile = build(values=v)
        self.assertEqual(risk['risk_class'], 'medium')
        self.assertIsNone(profile['evidence_profile'])

    def test_the_ids_change_with_task_commit_and_policy(self):
        """TASK-029 AC2, AC3, AC5: the ids depend on the task, the commit and the policy version, and are distinct."""
        a = [r['record_id'] for r in build()]
        self.assertEqual(len(set(a)), 2)
        for change in ({'task_id': 'TASK-501'}, {'evaluated_commit': OLD}, {'values': values(policy_version='v3')}):
            self.assertTrue(set(a).isdisjoint(r['record_id'] for r in build(**change)), change)
        self.assertEqual(a, [r['record_id'] for r in build(recorder='other', source_class=CI)])


class Coverage(unittest.TestCase):

    def test_no_findings_no_coverage_record(self):
        """TASK-029 AC4: a contract whose criteria are all named gives no coverage record."""
        self.assertEqual([r['evidence_type'] for r in build()], ['risk_class', 'evidence_profile'])

    def test_findings_give_the_coverage_record_unchanged(self):
        """TASK-029 AC4, AC5: an uncovered AC gives coverage_record's own record, last."""
        out = build(coverage_contract=coverage(True))
        self.assertEqual(len(out), 3)
        expected = ac_coverage.coverage_record(TASK, 'v1', ac_coverage.check(coverage(True)), REC,
                                               'deterministic_tool_local')
        self.assertEqual(out[2], expected)
        self.assertEqual(len({r['record_id'] for r in out}), 3)
        for r in out:
            self.assertEqual(records.check_record(r), [])

    def test_a_malformed_coverage_contract_gives_its_malformed_record(self):
        """TASK-029 AC4: a malformed contract gives coverage_record's record for the malformed finding."""
        out = build(coverage_contract={'acceptance_criteria': 'x'})
        self.assertEqual(out[2]['evidence_type'], 'ac_coverage')


class Caller(unittest.TestCase):

    def test_appends_each_record_once_in_order(self):
        """TASK-029 AC6: the exact append calls and event ids; result written."""
        log = Log()
        out = run(log, coverage_contract=coverage(True))
        built = build(coverage_contract=coverage(True))
        self.assertEqual(out['result'], 'written')
        self.assertIsNone(out['reason'])
        self.assertEqual(out['findings'], [])
        self.assertEqual([a[1:7] for a in log.appends],
                         [('record.added', r, sha('record.added', r['record_id']), NOW, REC, TASK) for r in built])
        self.assertTrue(all(a[7] is None for a in log.appends))
        self.assertEqual(out['records'], [{'record_id': r['record_id'], 'event_id': sha('record.added', r['record_id']),
                                           'status': 'appended'} for r in built])
        self.assertEqual(set(out), {'result', 'reason', 'records', 'findings'})

    def test_a_rerun_is_a_duplicate(self):
        """TASK-029 AC6, AC9: a second run gives duplicate for each record and appends nothing."""
        log = Log()
        run(log)
        before = log.log
        out = run(log)
        self.assertEqual(out['result'], 'written')
        self.assertEqual([e['status'] for e in out['records']], ['duplicate', 'duplicate'])
        self.assertEqual(log.log, before)

    def test_a_build_failure_appends_nothing(self):
        """TASK-029 AC6: a ValueError from build_records gives refused, argument; append is not called."""
        log = Log()
        out = run(log, task_id='nope')
        self.assertEqual((out['result'], out['reason'], out['records']), ('refused', 'argument', []))
        self.assertTrue(out['findings'] and out['findings'][0].startswith('argument:'))
        self.assertEqual(log.appends, [])

    def test_a_refused_result_stops_the_loop(self):
        """TASK-029 AC6: a writer result other than appended or duplicate stops the loop with the writer's findings."""
        calls = []

        class R:
            def __init__(self, result, findings=()):
                self.result, self.findings = result, findings

        def append(*a, **k):
            calls.append(a[3])
            return R('appended') if len(calls) == 1 else R('refused', ['fence: no lease', 3])

        out = run(append=append, coverage_contract=coverage(True))
        self.assertEqual((out['result'], out['reason']), ('refused', 'store'))
        self.assertEqual([e['status'] for e in out['records']], ['appended', 'not appended', 'not appended'])
        self.assertEqual(out['findings'], ["store: the writer gave 'refused'", 'fence: no lease'])
        self.assertEqual(len(calls), 2)

    def test_a_raising_or_odd_append_stops_the_loop(self):
        """TASK-029 AC6: append raising, or a result whose result is not a str, gives refused, store; nothing escapes."""
        class Odd:
            result = 1

        def boom(*a, **k):
            raise OSError('disk')

        for append in (boom, lambda *a, **k: Odd(), lambda *a, **k: None):
            out = run(append=append)
            self.assertEqual((out['result'], out['reason']), ('refused', 'store'))
            self.assertEqual([e['status'] for e in out['records']], ['not appended', 'not appended'])
            self.assertIn('whether the record was appended is not known', out['findings'][0])

    def test_append_defaults_to_the_writer_at_call_time(self):
        """TASK-029 AC6: append defaults, at call time, to writer.append_event."""
        log = Log()
        saved = writer.append_event
        writer.append_event = log.append
        try:
            out = vr.record_evaluation(FS_ROOT, TASK, 'v1', COMMIT, dict(IV), values(), coverage(), REC, NOW)
        finally:
            writer.append_event = saved
        self.assertEqual(out['result'], 'written')
        self.assertEqual(len(log.appends), 2)


class NoRepeatedRecord(unittest.TestCase):

    def test_the_log_holds_one_record_added_per_record_id(self):
        """TASK-029 AC9: two runs through eventlog.append leave one record.added per record_id; the log checks clean."""
        log = Log()
        run(log, coverage_contract=coverage(True))
        run(log, coverage_contract=coverage(True))
        report = records.check_log(log.log)
        events = [line.event for line in report.lines]
        self.assertTrue(all(e is not None for e in events))
        ids = [e['payload']['record_id'] for e in events if e['type'] == 'record.added']
        self.assertEqual(len(ids), 3)
        self.assertEqual(len(set(ids)), 3)


def gov_request(**changes):
    r = {'task_id': TASK, 'task_content_hash': HASH, 'evaluated_commit': COMMIT, 'intent_versions': dict(IV),
         'task_state': 'VERIFYING', 'changed_paths': ['src/x.py'], 'retry_count': {'used': 0, 'limit': 2}}
    r.update(changes)
    return r


def gov_inputs(**changes):
    i = {'traces_to': ['SPEC-001'], 'risk': 'low', 'owner_kept_act': False, 'weakens_evidence': False,
         'delegation_in_force': True, 'auto_accept': False, 'verification_plan': ['G0', 'G1'],
         'evidence_profile': [{'dimension': 'functional', 'evidence_types': ['build']}],
         'applicable_articles': [], 'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1'}
    i.update(changes)
    return i


def rec(rid, **fields):
    r = {'record_id': rid, 'fact_kind': 'observation', 'source_class': CI, 'recorder': 'external CI',
         'subject': TASK, 'commit': COMMIT, 'intent_versions': dict(IV), 'outcome': 'pass'}
    r.update(fields)
    return {k: v for k, v in r.items() if v is not None}


def gates():
    return [rec('g0', gate='G0', evidence_type='scope_check', dimension='scope'),
            rec('g1', gate='G1', evidence_type='build', dimension='functional')]


def approval():
    return rec('ap', fact_kind='authority', source_class='human_authority', recorder='an approver', commit=None,
               intent_versions=None, outcome=None, approval_binding={'kind': 'acceptance', 'hash': HASH})


SETS = {
    'all gates and an approval': gates() + [approval()],
    'all gates, no approval': gates(),
    'a missing gate': gates()[:1],
    'a failed gate': [gates()[0], rec('g1', gate='G1', evidence_type='build', dimension='functional', outcome='fail')],
    'a blocking record': gates() + [rec('b', outcome='blocking', blocking_kind='other', evidence_type='x')],
    'an out-of-scope record': gates() + [rec('b', outcome='blocking', blocking_kind='out_of_scope', evidence_type='x')],
    'a repeated record id (error)': gates() + [gates()[1]],
    'no records': [],
}


def audit(commit=COMMIT, **change):
    out = build(evaluated_commit=commit)
    for r in out:
        r.update(change)
    return out


class Governor(unittest.TestCase):

    def without(self, record, keys=('reverify', 'uncovered', 'record_id')):
        return {k: v for k, v in record.items() if k not in keys}

    def test_well_formed_and_stale_copies_change_no_decision(self):
        """TASK-029 AC8: over each set, in VERIFYING and in IN_REVIEW, current and earlier-commit copies change
        nothing but reverify, uncovered and the derived record_id; the sets reach rows 1, 2, 3 and 5 and the error
        record (row 4 is never reached by the governor at L1)."""
        rows = set()
        decisions = set()
        for state in ('VERIFYING', 'IN_REVIEW'):
            for name, rs in SETS.items():
                req = gov_request(task_state=state)
                base = governor.evaluate(req, gov_inputs(), copy.deepcopy(rs))
                rows.add(base.get('table_row'))
                decisions.add((base.get('decision'), base.get('next_task_state')))
                for extra in (audit(), audit(OLD), audit() + audit(OLD)):
                    got = governor.evaluate(req, gov_inputs(), copy.deepcopy(rs) + extra)
                    self.assertEqual(self.without(got), self.without(base), (state, name))
                current = governor.evaluate(req, gov_inputs(), copy.deepcopy(rs) + audit())
                if base.get('decision') is not None:
                    self.assertEqual(current, base, (state, name))
        self.assertEqual(rows, {1, 2, 3, 5, None})
        self.assertIn(('NEEDS_REVIEW', 'ACCEPTED'), decisions)

    def test_malformed_copies_change_no_decision_unless_blocking(self):
        """TASK-029 AC8: a malformed copy is not used and is noted; one that carries outcome blocking still blocks
        (rule 4), with the effect its blocking_kind gives."""
        base = governor.evaluate(gov_request(), gov_inputs(), gates())

        def without_key(key):
            out = audit()
            for r in out:
                r.pop(key if key != 'own' else r['evidence_type'], None)
            return out

        variants = [audit(**change) for change in (
            {'outcome': 'pass'}, {'outcome': 'fail'}, {'gate': 'G1'}, {'dimension': 'functional'},
            {'fact_kind': 'claim'}, {'source_class': 'agent_declared'}, {'blocking_kind': 'other'})]
        variants += [without_key('own'), without_key('commit'), without_key('intent_versions')]
        other = audit()
        other[0]['evidence_profile'] = None
        other[1]['risk_class'] = 'low'
        variants.append(other)
        for bad in variants:
            self.assertTrue(all(records.check_audit_copy(r) for r in bad), bad)
            got = governor.evaluate(gov_request(), gov_inputs(), gates() + bad)
            self.assertEqual(self.without(got), self.without(base), bad)
            for r in bad:
                self.assertTrue(any(n.startswith(r['record_id'] + ': not used: ') for n in got['uncovered']),
                                (r['record_id'], got['uncovered']))
        blocked = governor.evaluate(gov_request(), gov_inputs(), gates() + audit(outcome='blocking', blocking_kind='other'))
        self.assertNotEqual(blocked['decision'], base['decision'])
        self.assertTrue(blocked['blocking'])
        rejected = governor.evaluate(gov_request(), gov_inputs(),
                                     gates() + audit(outcome='blocking', blocking_kind='forbidden_path'))
        self.assertEqual(rejected['decision'], 'REJECT')


ALLOWED_IMPORTS = {'copy', 'hashlib', 'aieos_bootstrap.ac_coverage', 'aieos_bootstrap.governor',
                   'aieos_bootstrap.records', 'aieos_bootstrap.writer'}
BAD_NAMES = {'open', 'subprocess', 'os', 'time', 'socket', 'datetime', 'exec', 'eval', 'compile', '__import__',
             'importlib'}
BAD_ATTRS = {'environ', 'now', 'system', 'popen', 'run', 'import_module'}


def purity_breaches(source):
    """The breaches of AC10's rule in a source text: imports outside ALLOWED_IMPORTS, and refused names or attributes."""
    tree = ast.parse(source)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += ['import ' + a.name for a in node.names if a.name not in ALLOWED_IMPORTS]
        elif isinstance(node, ast.ImportFrom):
            found += ['import %s.%s' % (node.module, a.name) for a in node.names
                      if '%s.%s' % (node.module, a.name) not in ALLOWED_IMPORTS]
        elif isinstance(node, ast.Name) and node.id in BAD_NAMES:
            found.append('name ' + node.id)
        elif isinstance(node, ast.Attribute) and node.attr in BAD_ATTRS:
            found.append('attribute ' + node.attr)
    return found


class Purity(unittest.TestCase):

    def test_imports_and_no_forbidden_calls(self):
        """TASK-029 AC10: the module imports only hashlib and copy and four package modules, and names no file,
        process, clock, environment, dynamic import or network call."""
        source = MODULE.read_bytes().decode('utf-8')
        self.assertEqual(purity_breaches(source), [])
        self.assertIn('import hashlib', source)

    def test_the_check_finds_a_breach(self):
        """TASK-029 AC10: the same check, purity_breaches, refuses the module's source with one breach added."""
        source = MODULE.read_bytes().decode('utf-8')
        for added in ('import os\n', 'from importlib import import_module\n', 'x = open\n', 'y = copy.environ\n',
                      'z = __import__\n', 'w = datetime.now\n'):
            self.assertTrue(purity_breaches(source + added), added)


class FormGuards(unittest.TestCase):

    def test_a_built_record_out_of_form_raises(self):
        """TASK-029 AC5: build_records refuses when records.check_record finds a built record out of form."""
        saved = records.check_record
        records.check_record = lambda r: ['6.2:x: forced']
        try:
            with self.assertRaisesRegex(ValueError, 'out of form'):
                build()
        finally:
            records.check_record = saved

    def test_repeated_record_ids_raise(self):
        """TASK-029 AC5: build_records refuses two built records with the same record_id."""
        saved = ac_coverage.coverage_record
        first = build()[0]
        ac_coverage.coverage_record = lambda *a: dict(first)
        try:
            with self.assertRaisesRegex(ValueError, 'same record_id'):
                build(coverage_contract=coverage(True))
        finally:
            ac_coverage.coverage_record = saved

    def test_a_rerun_with_other_content_is_a_refused_conflict(self):
        """TASK-029 AC6: a rerun under the same ids with another recorder is refused by the writer, reported as
        refused, store."""
        log = Log()
        run(log)
        before = log.log
        out = run(log, recorder='other-core')
        self.assertEqual((out['result'], out['reason']), ('refused', 'store'))
        self.assertEqual(out['records'][0]['status'], 'not appended')
        self.assertTrue(out['findings'][0].startswith('store: the writer gave '), out['findings'])
        self.assertNotIn(out['findings'][0], ("store: the writer gave 'appended'", "store: the writer gave 'duplicate'"))
        self.assertEqual(log.log, before)


if __name__ == '__main__':
    unittest.main()

"""Tests of src/aieos_bootstrap/metrics_report.py (task TASK-112): the read-only report over the event log for the
metrics of concept section 12. Every log is built in the test from fixed text on synthetic data; no test writes a file
and no test reads the project's own log. Every test names the ACs it stands for in its docstring."""

import ast
import json
import unittest
from pathlib import Path

from aieos_bootstrap import eventlog, metrics_report, records

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src' / 'aieos_bootstrap' / 'metrics_report.py'
LITERAL_STATUSES = ('mechanical', 'needs_judgement', 'no_source')
COMMIT = '1' * 40
HASH = 'a' * 64
A, B, C, D, E, F, G, H, Z = ('TASK-001', 'TASK-002', 'TASK-003', 'TASK-004', 'TASK-005', 'TASK-006', 'TASK-008',
                             'TASK-007', 'TASK-009')


class Log:
    """A log built line by line; every line is a valid event of the checker (records.check_log)."""

    def __init__(self):
        self.lines = []
        self.n = 0

    def add(self, etype, payload, task=None, at=None, **extra):
        self.n += 1
        obj = {'event_id': 'e%d' % self.n, 'type': etype, 'seq': self.n, 'payload': payload,
               'appended_at': at or '2026-11-01T10:%02d:%02dZ' % (self.n // 60, self.n % 60)}
        if task is not None:
            obj['task_id'] = task
        obj.update(extra)
        self.lines.append(json.dumps(obj, sort_keys=True))
        return obj['event_id']

    def data(self):
        return ('\n'.join(self.lines) + '\n').encode('utf-8') if self.lines else b''


def rec(rid, task, **kw):
    r = {'record_id': rid, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
         'recorder': 'test', 'subject': task}
    r.update(kw)
    return r


def item(missing=(), dimension='functional'):
    return {'dimension': dimension, 'required': ['unit_test'], 'satisfied_by': [] if missing else ['r1'],
            'missing_types': list(missing)}


def acceptance(log, task, decision, state, profile=None, uncovered=(), gates=(), omit=(), **kw):
    body = rec('d%d' % (log.n + 1), task, fact_kind='interpretation', decision=decision, next_task_state=state,
               profile_used=[item()] if profile is None else profile, missing_gates=list(gates), failed_gates=[],
               blocking=[], uncovered=list(uncovered) if isinstance(uncovered, (list, tuple)) else uncovered)
    body.update(kw)
    for key in omit:
        body.pop(key, None)
    return log.add('decision.acceptance', body, task)


def ready(log):
    """The bytes of a hand-built log, after asserting that the checker finds no finding in it."""
    data = log.data()
    findings = records.check_log(data).findings()
    assert findings == [], findings
    return data


def error_decision(log, task, profile=None):
    body = rec('d%d' % (log.n + 1), task, fact_kind='interpretation', decision=None, error='the inputs are refused',
               profile_used=[] if profile is None else profile)
    return log.add('decision.acceptance', body, task)


def submit(log, task, compensating=False):
    return log.add('task.submitted', {'commit': COMMIT, 'compensating': compensating}, task,
                   fencing_token={'epoch': 'epoch1', 'counter': log.n + 1})


def approve(log, task, at=None):
    return log.add('task.approved', {'contract_version': 'v1', 'contract_hash': HASH, 'approval_record': 'a1'}, task,
                   at=at)


def done(log, task, at=None):
    return log.add('task.done', {'decision_record': 'd1'}, task, at=at)


def scenario():
    """A log of nine tasks: an L1 acceptance, a rework, a submission with no decision, an error decision, a
    compensating submission only, a human-only insufficient evidence, an escalation, a done task with no approval and a
    task with one human record and no risk class."""
    log = Log()
    approve(log, A, at='2026-11-01T09:00:00Z')
    submit(log, A)
    acceptance(log, A, 'NEEDS_REVIEW', 'IN_REVIEW')
    acceptance(log, A, 'NEEDS_REVIEW', 'ACCEPTED', uncovered=['note a', 'note b'])
    done(log, A, at='2026-11-01T09:00:30.500Z')
    approve(log, B, at='2026-11-01T09:10:00Z')
    submit(log, B)
    acceptance(log, B, 'NEEDS_REWORK', 'REWORK', profile=[item(['unit_test'])], gates=['G2'])
    submit(log, B)
    acceptance(log, B, 'NEEDS_REVIEW', 'IN_REVIEW')
    done(log, B, at='2026-11-01T09:12:00Z')
    log.add('violation.detected', rec('v1', B, outcome='blocking', blocking_kind='violation'), B)
    submit(log, C)
    log.add('record.added', eventlog.refusal_record('e1', C, 'test', 'refusal1'), C)
    submit(log, D)
    error_decision(log, D)
    submit(log, E, compensating=True)
    submit(log, F)
    acceptance(log, F, 'INSUFFICIENT_EVIDENCE', 'IN_REVIEW', profile=[item(['human_review'])])
    submit(log, H)
    acceptance(log, H, 'NEEDS_REWORK', 'ESCALATED', profile=[])
    done(log, G)
    log.add('drift.detected', {'paths': ['a.py'], 'entities': ['E1']})
    log.add('record.added', rec('rc1', A, evidence_type='risk_class', risk_class='medium', commit=COMMIT,
                                intent_versions={}), A)
    log.add('record.added', rec('rc2', A, evidence_type='risk_class', risk_class='high', commit=COMMIT,
                                intent_versions={}), A)
    for rid, task in (('h1', A), ('h2', A), ('h3', Z)):
        log.add('record.added', rec(rid, task, fact_kind='authority', source_class='human_authority',
                                    approval_binding={'kind': 'contract', 'hash': HASH}), task)
    log.add('record.added', rec('h4', 'INT-001', fact_kind='authority', source_class='human_authority',
                                approval_binding={'kind': 'contract', 'hash': HASH}))
    return log


class Frame(unittest.TestCase):
    def test_a_clean_log_gives_the_four_keys_and_the_eight_metrics_in_order(self):
        """TASK-112 AC1: report gives exactly ok, findings, corrections_present and metrics, and the eight metric names
        in the fixed order, on a log the checker finds clean."""
        data = scenario().data()
        self.assertEqual(records.check_log(data).findings(), [])
        out = metrics_report.report(data)
        self.assertEqual(sorted(out), ['corrections_present', 'findings', 'metrics', 'ok'])
        self.assertTrue(out['ok'])
        self.assertEqual(out['findings'], [])
        self.assertEqual(out['corrections_present'], {'lines': 0, 'corrected_event_ids': []})
        self.assertEqual(list(out['metrics']), list(metrics_report.METRIC_NAMES))
        for metric in out['metrics'].values():
            self.assertIn(metric['status'], LITERAL_STATUSES)
            self.assertIsInstance(metric['sources'], list)
            self.assertIsInstance(metric['limits'], list)

    def test_a_log_with_a_finding_gives_no_figure(self):
        """TASK-112 AC1: any text or line finding gives ok false, the findings as strings and no metrics."""
        data = scenario().data() + b'not json\n'
        out = metrics_report.report(data)
        self.assertFalse(out['ok'])
        self.assertIsNone(out['corrections_present'])
        self.assertEqual(out['metrics'], {})
        self.assertTrue(out['findings'])
        self.assertTrue(all(isinstance(f, str) for f in out['findings']))
        self.assertTrue(out['findings'][0].startswith('line 30: '))
        text = metrics_report.report(b'\xef\xbb\xbf' + scenario().data())
        self.assertFalse(text['ok'])
        self.assertTrue(text['findings'][0].startswith('text: '))

    def test_the_argument_forms(self):
        """TASK-112 AC1: bytes, bytearray and str give the same report; any other argument raises check_log's TypeError;
        an empty log is clean and gives empty figures."""
        data = scenario().data()
        base = metrics_report.report(data)
        self.assertEqual(metrics_report.report(bytearray(data)), base)
        self.assertEqual(metrics_report.report(data.decode('utf-8')), base)
        for bad in (None, 5, ['x'], {'a': 1}):
            with self.assertRaises(TypeError):
                metrics_report.report(bad)
        empty = metrics_report.report(b'')
        self.assertTrue(empty['ok'])
        self.assertEqual(empty['metrics']['caught_rate']['submissions'], 0)
        self.assertIsNone(empty['metrics']['caught_rate']['ratio'])
        self.assertIsNone(empty['metrics']['first_pass_acceptance']['ratio'])
        self.assertIsNone(empty['metrics']['cost_per_accepted_task']['median'])

    def test_a_duplicate_line_is_skipped_and_corrections_are_counted(self):
        """TASK-112 AC1: an identical repeat is skipped; lines that carry corrects are counted as they stand and their
        number and the corrected event ids are reported."""
        log = Log()
        submit(log, A)
        first = acceptance(log, A, 'NEEDS_REWORK', 'REWORK')
        log.add('decision.acceptance', json.loads(log.lines[-1])['payload'], A, event_id=first)
        self.assertEqual(records.check_log(log.data()).findings(), [])
        out = metrics_report.report(log.data())
        self.assertEqual(out['metrics']['caught_rate']['blocked'], 1)
        self.assertEqual(out['metrics']['rework_rate']['rework_before_acceptance']['total'], 1)
        fix = rec('fix1', A, evidence_type='note')
        log.add('record.added', fix, A, corrects=first)
        out = metrics_report.report(log.data())
        self.assertEqual(out['corrections_present'], {'lines': 1, 'corrected_event_ids': [first]})
        for half in ('corrections are not applied', 'a corrected and a correcting decision are both counted'):
            self.assertTrue(all(any(half in s for s in m['limits']) for m in out['metrics'].values()), half)


class CaughtRateAndFirstPass(unittest.TestCase):
    def setUp(self):
        self.metrics = metrics_report.report(scenario().data())['metrics']

    def test_the_outcome_of_a_submission_is_read_from_the_next_state(self):
        """TASK-112 AC2: blocked is REWORK, REJECTED or ESCALATED; not blocked is IN_REVIEW or ACCEPTED (an L1 task
        accepted has the decision NEEDS_REVIEW); undecided and undecided_error are counted apart; the compensating
        submission is not a submission."""
        m = self.metrics['caught_rate']
        self.assertEqual(m['status'], 'mechanical')
        self.assertEqual((m['blocked'], m['submissions']), (2, 7))
        self.assertEqual(m['ratio'], 2 / 7)
        self.assertEqual((m['not_blocked'], m['not_blocked_needs_review'], m['not_blocked_insufficient_human'],
                          m['not_blocked_other']), (3, 2, 1, 0))
        self.assertEqual((m['undecided'], m['undecided_error'], m['unclassified']), (1, 1, 0))
        self.assertEqual(m['compensating_submissions'], 1)

    def test_violations_and_fence_refusals_are_separate_counts(self):
        """TASK-112 AC2: violation_detected and fence_refusals (record.added with evidence_type refused_submission) are
        two counts of their own, never added into the headline; the reason share is a label with no number."""
        m = self.metrics['caught_rate']
        self.assertEqual((m['violation_detected'], m['fence_refusals']), (1, 1))
        self.assertEqual(m['blocked'], 2)
        self.assertEqual(m['reason_share']['status'], 'needs_judgement')
        self.assertIsNone(m['reason_share']['value'])
        self.assertIn('AI-judged, CR-002 K6', m['reason_share']['note'])
        self.assertNotIn('without_task_id', m)

    def test_a_submission_is_decided_only_inside_its_own_window(self):
        """TASK-112 AC2: the decision of a submission is the first one before the task's next task.submitted; a later
        decision is not borrowed by an earlier submission."""
        log = Log()
        submit(log, A)
        submit(log, A)
        acceptance(log, A, 'NEEDS_REVIEW', 'IN_REVIEW')
        m = metrics_report.report(log.data())['metrics']['caught_rate']
        self.assertEqual((m['submissions'], m['undecided'], m['not_blocked']), (2, 1, 1))

    def test_first_pass_acceptance(self):
        """TASK-112 AC2: the denominator is the tasks whose first submission has a decision with a decision value;
        the numerator needs NEEDS_REVIEW or ACCEPT with empty gate lists and every missing_types empty; tasks with no
        submission, no decision or an error decision are counted apart and are not in the denominator."""
        m = self.metrics['first_pass_acceptance']
        self.assertEqual(m['status'], 'mechanical')
        self.assertEqual((m['passed'], m['denominator']), (1, 4))
        self.assertEqual(m['ratio'], 0.25)
        self.assertEqual(m['tasks_without_submission'], [E, G, Z])
        self.assertEqual(m['without_decision'], [C])
        self.assertEqual(m['first_decision_error'], [D])

    def test_a_first_decision_with_a_missing_type_is_not_a_pass(self):
        """TASK-112 AC2: a NEEDS_REVIEW decision whose profile still has a missing type, or whose gate list is not
        empty, is in the denominator and not in the numerator (a hand-built log; the governor does not give it)."""
        log = Log()
        submit(log, A)
        acceptance(log, A, 'NEEDS_REVIEW', 'IN_REVIEW', profile=[item(['unit_test'])])
        submit(log, B)
        acceptance(log, B, 'NEEDS_REVIEW', 'IN_REVIEW', gates=['G2'])
        submit(log, C)
        acceptance(log, C, 'ACCEPT', 'ACCEPTED')
        m = metrics_report.report(log.data())['metrics']['first_pass_acceptance']
        self.assertEqual((m['passed'], m['denominator']), (1, 3))


class DriftEscapedHuman(unittest.TestCase):
    def setUp(self):
        self.metrics = metrics_report.report(scenario().data())['metrics']

    def test_drift_has_counts_by_event_type_and_no_rate(self):
        """TASK-112 AC3: the drift false positive rate has status no_source and no value; the counts are by event type,
        drift.detected and violation.detected apart and never summed."""
        m = self.metrics['drift_false_positive_rate']
        self.assertEqual(m['status'], 'no_source')
        self.assertIsNone(m['value'])
        self.assertEqual(m['drift_warning_counts'], {'drift.detected': 1, 'violation.detected': 1})

    def test_escaped_defects_have_no_source(self):
        """TASK-112 AC3: escaped defects have status no_source, no value and no source."""
        m = self.metrics['escaped_defects']
        self.assertEqual((m['status'], m['value'], m['sources']), ('no_source', None, []))

    def test_human_authority_records_are_counted_by_the_latest_risk_class(self):
        """TASK-112 AC3: human time has status no_source and no value; the human_authority records are counted by the
        task's latest risk_class audit copy, a task with none as unknown."""
        m = self.metrics['human_time_per_task']
        self.assertEqual(m['status'], 'no_source')
        self.assertIsNone(m['value'])
        self.assertEqual(m['human_authority_records_by_risk_class'], {'high': 2, 'unknown': 1})
        self.assertEqual(m['without_task_id'], 1)
        self.assertTrue(any('not a time' in s for s in m['limits']))


class CoverageCostRework(unittest.TestCase):
    def setUp(self):
        self.metrics = metrics_report.report(scenario().data())['metrics']

    def test_evidence_coverage_uses_the_last_decision_of_each_task(self):
        """TASK-112 AC4: for the last acceptance decision of each task with a decision value and a profile, a dimension
        is satisfied when its missing_types is empty; the uncovered notes are listed; a last decision with a null
        decision or an empty profile is counted apart."""
        m = self.metrics['evidence_coverage']
        self.assertEqual(m['status'], 'mechanical')
        self.assertEqual((m['decisions_counted'], m['dimensions_satisfied'], m['dimensions_required']), (3, 2, 3))
        self.assertEqual(m['ratio'], 2 / 3)
        self.assertEqual(m['uncovered'], ['note a', 'note b'])
        self.assertEqual(m['decisions_without_profile'], 2)

    def test_cost_is_wall_time_from_the_first_approval_to_done(self):
        """TASK-112 AC4: wall_seconds runs from a task's first task.approved to its task.done; the median and the
        maximum follow; a task done with no approval is counted apart; tokens have no source."""
        m = self.metrics['cost_per_accepted_task']
        self.assertEqual(m['status'], 'mechanical')
        self.assertEqual(m['wall_seconds'], {A: 30.5, B: 120.0})
        self.assertEqual((m['median'], m['maximum']), (75.25, 120.0))
        self.assertEqual(m['tasks_done_without_approved'], [G])
        self.assertEqual((m['tasks_done'], m['tasks_without_done']), (3, 6))
        self.assertEqual(m['tokens'], {'status': 'no_source', 'value': None})
        self.assertTrue(any('idle time' in s for s in m['limits']))

    def test_rework_before_acceptance_is_not_the_rework_rate(self):
        """TASK-112 AC4: the rework rate has status no_source and no value; rework_before_acceptance has status
        mechanical and counts the REWORK decisions since the task's last task.approved."""
        m = self.metrics['rework_rate']
        self.assertEqual((m['status'], m['value']), ('no_source', None))
        r = m['rework_before_acceptance']
        self.assertEqual(r['status'], 'mechanical')
        self.assertEqual(r['per_task'], {A: 0, B: 1, D: 0, F: 0, H: 0})
        self.assertEqual(r['total'], 1)
        self.assertEqual(r['without_approved'], [D, F, H])


class Honesty(unittest.TestCase):
    def test_no_source_and_judged_metrics_carry_no_number(self):
        """TASK-112 AC5: every no_source metric has a null value, every needs_judgement figure is a label, every
        status is one of the three words, and the same bytes give the same report."""
        data = scenario().data()
        out = metrics_report.report(data)
        for name, m in out['metrics'].items():
            self.assertIn(m['status'], LITERAL_STATUSES, name)
            if m['status'] == 'no_source':
                self.assertIsNone(m['value'], name)
        self.assertIsNone(out['metrics']['caught_rate']['reason_share']['value'])
        self.assertEqual(out['metrics']['caught_rate']['reason_share']['status'], 'needs_judgement')
        self.assertIsNone(out['metrics']['cost_per_accepted_task']['tokens']['value'])
        self.assertEqual(metrics_report.report(data), out)

    def test_the_limits_state_what_the_contract_requires(self):
        """TASK-112 AC2, TASK-112 AC3 and TASK-112 AC4: the limits of the metrics without a source and of the figures
        with a stated reading say so in plain words."""
        metrics = metrics_report.report(scenario().data())['metrics']

        def limits(name):
            return ' | '.join(metrics[name]['limits'])

        self.assertIn('right or wrong', limits('drift_false_positive_rate'))
        self.assertIn('defect was found after DONE', limits('escaped_defects'))
        self.assertIn("decision agent's", limits('human_time_per_task'))
        self.assertIn('not a time', limits('human_time_per_task'))
        self.assertIn('fail closed', limits('first_pass_acceptance'))
        self.assertIn('empty profile_used list is clean', limits('first_pass_acceptance'))
        self.assertIn('empty list', limits('evidence_coverage'))
        self.assertIn('tasks_with_negative_wall', limits('cost_per_accepted_task'))
        self.assertIn('not_blocked_other', limits('caught_rate'))
        self.assertIn('never the rework rate', limits('rework_rate'))

    def test_the_module_is_pure_and_names_its_limits(self):
        """TASK-112 AC5: the module imports only the standard library and the own records module, uses none of the
        refused names, has no state-directory string, has none of the three effect words and its docstring states the
        limits in plain words."""
        text = SRC.read_text(encoding='utf-8')
        tree = ast.parse(text)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split('.')[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or '').split('.')[0])
        self.assertEqual(imported, {'datetime', 're', 'aieos_bootstrap'})
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertFalse(names & {'open', 'exec', 'eval', 'compile', 'input', '__import__'})
        attributes = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        self.assertFalse(attributes & {'now', 'utcnow', 'today', 'time', 'environ', 'getenv'})
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'replace':
                self.assertNotEqual(len(node.args) + len(node.keywords), 1)
        strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertFalse([s for s in strings if '.aieos' in s])
        for word in ('MEASURED', 'ENFORCED', 'GUARANTEED'):  # OPS-003; A30: MEASURED only through the owner-approved lifecycle
            self.assertNotIn(word, text)
        doc = ast.get_docstring(tree)
        for phrase in ('CR-002 K6', 'L1', 'master plan line 113', 'descriptive', 'reads no clock', 'corrections'):
            self.assertIn(phrase, doc)


class NoWritePath(unittest.TestCase):
    def test_the_module_does_not_use_a_writer(self):
        """TASK-112 AC6: the module reads no store and appends no event: it imports neither writer nor eventlog and
        the report does not change its argument."""
        tree = ast.parse(SRC.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or '').split('.')[0] == 'aieos_bootstrap':
                self.assertEqual(node.module, 'aieos_bootstrap')
                self.assertEqual([a.name for a in node.names], ['records'])
            if isinstance(node, ast.Import):
                self.assertFalse([a.name for a in node.names if a.name.startswith('aieos_bootstrap')])
        data = bytearray(scenario().data())
        before = bytes(data)
        metrics_report.report(data)
        self.assertEqual(bytes(data), before)


class Branches(unittest.TestCase):
    """The branches that the scenario of nine tasks does not reach, each on a small hand-built log."""

    def test_every_outcome_branch_of_a_submission(self):
        """TASK-112 AC2: REJECTED is blocked; a not-blocked decision other than NEEDS_REVIEW, or INSUFFICIENT_EVIDENCE
        with the next state ACCEPTED, is counted under not_blocked_other; a next state outside both sets, or no next
        state, is unclassified; NEEDS_REVIEW with ACCEPTED is not blocked."""
        log = Log()
        for task, decision, state, extra in (
                (A, 'REJECT', 'REJECTED', {}),
                (B, 'NEEDS_REWORK', 'IN_REVIEW', {}),
                (C, 'NEEDS_REVIEW', 'BLOCKED', {}),
                (D, 'NEEDS_REVIEW', None, {'omit': ('next_task_state',)}),
                (E, 'NEEDS_REVIEW', 'ACCEPTED', {}),
                (F, 'INSUFFICIENT_EVIDENCE', 'ACCEPTED', {})):
            submit(log, task)
            acceptance(log, task, decision, state, **extra)
        m = metrics_report.report(ready(log))['metrics']['caught_rate']
        self.assertEqual((m['submissions'], m['blocked'], m['not_blocked']), (6, 1, 3))
        self.assertEqual((m['not_blocked_needs_review'], m['not_blocked_insufficient_human'],
                          m['not_blocked_other']), (1, 0, 2))
        self.assertEqual((m['unclassified'], m['undecided'], m['undecided_error']), (2, 0, 0))

    def test_first_pass_fails_closed(self):
        """TASK-112 AC2: a first decision is clean only when its gate lists are empty lists and its profile_used is a
        list whose items all have an empty list of missing types; an empty profile_used list is clean, an absent one
        is not; a non-empty failed_gates or blocking, a null missing_types and an absent missing_gates are not."""
        log = Log()
        for task, extra in (
                (A, {'profile': []}),
                (B, {'failed_gates': ['G1']}),
                (C, {'blocking': ['out_of_scope']}),
                (D, {'omit': ('profile_used',)}),
                (E, {'profile': [dict(item(), missing_types=None)]}),
                (F, {}),
                (G, {'omit': ('missing_gates',)})):
            submit(log, task)
            acceptance(log, task, 'NEEDS_REVIEW', 'IN_REVIEW', **extra)
        m = metrics_report.report(ready(log))['metrics']['first_pass_acceptance']
        self.assertEqual((m['passed'], m['denominator']), (2, 7))
        self.assertEqual(m['ratio'], 2 / 7)

    def test_coverage_is_fail_closed_and_lists_every_uncovered_note(self):
        """TASK-112 AC4: a missing_types that is not an empty list is not satisfied; a last decision with an empty or
        absent profile_used is counted apart, and its uncovered notes are still listed; a non-list uncovered is
        ignored."""
        log = Log()
        acceptance(log, A, 'NEEDS_REVIEW', 'IN_REVIEW', uncovered=['a'])
        acceptance(log, B, 'NEEDS_REVIEW', 'IN_REVIEW', profile=[dict(item(), missing_types=None)])
        acceptance(log, C, 'NEEDS_REVIEW', 'IN_REVIEW', profile=[], uncovered=['zone x'])
        acceptance(log, D, 'NEEDS_REVIEW', 'IN_REVIEW', omit=('profile_used',))
        acceptance(log, E, 'NEEDS_REVIEW', 'IN_REVIEW', uncovered='text')
        m = metrics_report.report(ready(log))['metrics']['evidence_coverage']
        self.assertEqual((m['decisions_counted'], m['dimensions_required'], m['dimensions_satisfied']), (3, 3, 2))
        self.assertEqual(m['ratio'], 2 / 3)
        self.assertEqual(m['decisions_without_profile'], 2)
        self.assertEqual(m['uncovered'], ['a', 'zone x'])

    def test_the_latest_risk_class_copy_decides_also_when_null(self):
        """TASK-112 AC3: a later risk_class audit copy whose value is null makes the class unknown; a risk_class copy
        from a source that is not an audit source is a finding of the check, so the report gives no figure."""
        log = Log()
        for rid, value in (('rc1', 'high'), ('rc2', None)):
            log.add('record.added', rec(rid, A, evidence_type='risk_class', risk_class=value, commit=COMMIT,
                                        intent_versions={}), A)
        log.add('record.added', rec('h1', A, fact_kind='authority', source_class='human_authority',
                                    approval_binding={'kind': 'contract', 'hash': HASH}), A)
        m = metrics_report.report(ready(log))['metrics']['human_time_per_task']
        self.assertEqual(m['human_authority_records_by_risk_class'], {'unknown': 1})
        log.add('record.added', rec('rcx', A, evidence_type='risk_class', risk_class='low',
                                    source_class='human_authority', commit=COMMIT, intent_versions={}), A)
        self.assertTrue(records.check_log(log.data()).findings())
        out = metrics_report.report(log.data())
        self.assertFalse(out['ok'])
        self.assertEqual(out['metrics'], {})

    def test_cost_takes_the_first_approval_and_excludes_a_negative_wall_time(self):
        """TASK-112 AC4: wall time starts at the FIRST task.approved; with three values the median is the middle one;
        a task done before its approval is listed under tasks_with_negative_wall and is out of the figures; a zero
        wall time stays in."""
        log = Log()
        approve(log, A, at='2026-11-01T09:00:00Z')
        approve(log, A, at='2026-11-01T09:05:00Z')
        done(log, A, at='2026-11-01T09:06:00Z')
        approve(log, B, at='2026-11-01T10:00:00Z')
        done(log, B, at='2026-11-01T10:00:10Z')
        approve(log, C, at='2026-11-01T11:00:00Z')
        done(log, C, at='2026-11-01T11:01:30Z')
        approve(log, 'TASK-010', at='2026-11-01T12:00:00Z')
        done(log, 'TASK-010', at='2026-11-01T11:00:00Z')
        m = metrics_report.report(ready(log))['metrics']['cost_per_accepted_task']
        self.assertEqual(m['wall_seconds'], {A: 360.0, B: 10.0, C: 90.0})
        self.assertEqual((m['median'], m['maximum']), (90.0, 360.0))
        self.assertEqual(m['tasks_with_negative_wall'], ['TASK-010'])
        zero = Log()
        approve(zero, Z, at='2026-11-01T13:00:00Z')
        done(zero, Z, at='2026-11-01T13:00:00Z')
        m = metrics_report.report(ready(zero))['metrics']['cost_per_accepted_task']
        self.assertEqual((m['wall_seconds'], m['median'], m['maximum']), ({Z: 0.0}, 0.0, 0.0))
        self.assertEqual(m['tasks_with_negative_wall'], [])

    def test_an_error_decision_with_a_profile_is_not_counted_in_coverage(self):
        """TASK-112 AC4: a last decision whose decision is null is counted apart even when its profile_used is a
        non-empty list; no dimension is required or satisfied."""
        log = Log()
        error_decision(log, A, profile=[item()])
        m = metrics_report.report(ready(log))['metrics']['evidence_coverage']
        self.assertEqual((m['decisions_counted'], m['decisions_without_profile']), (0, 1))
        self.assertEqual((m['dimensions_required'], m['dimensions_satisfied'], m['ratio']), (0, 0, None))

    def test_a_rework_decision_with_no_approval_counts_from_the_start(self):
        """TASK-112 AC4: for a task with a decision and no task.approved the window starts at the first line, so a
        REWORK decision counts and the task is listed under without_approved."""
        log = Log()
        acceptance(log, A, 'NEEDS_REWORK', 'REWORK')
        r = metrics_report.report(ready(log))['metrics']['rework_rate']['rework_before_acceptance']
        self.assertEqual((r['per_task'], r['total'], r['without_approved']), ({A: 1}, 1, [A]))

    def test_rework_counts_only_since_the_last_approval(self):
        """TASK-112 AC4: a REWORK decision before the task's last task.approved is not counted."""
        log = Log()
        approve(log, A)
        acceptance(log, A, 'NEEDS_REWORK', 'REWORK')
        approve(log, A)
        acceptance(log, A, 'NEEDS_REWORK', 'REWORK')
        r = metrics_report.report(ready(log))['metrics']['rework_rate']['rework_before_acceptance']
        self.assertEqual((r['per_task'], r['total'], r['without_approved']), ({A: 1}, 1, []))

    def test_corrections_are_counted_and_their_targets_listed_once_each(self):
        """TASK-112 AC1: three lines that carry corrects, two of them for one event, give lines 3 and the two corrected
        event ids once each, sorted."""
        log = Log()
        first = submit(log, A)
        second = acceptance(log, A, 'NEEDS_REWORK', 'REWORK')
        log.add('record.added', rec('fix1', A, evidence_type='note'), A, corrects=second)
        log.add('record.added', rec('fix2', A, evidence_type='note'), A, corrects=second)
        log.add('record.added', rec('fix3', A, evidence_type='note'), A, corrects=first)
        out = metrics_report.report(ready(log))
        self.assertEqual(out['corrections_present'], {'lines': 3, 'corrected_event_ids': [first, second]})


if __name__ == '__main__':
    unittest.main()

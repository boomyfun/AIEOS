"""A read-only report over the event log for the metrics of concept section 12 (task TASK-112; M8 plan section 8;
concept lines 810-821; master plan lines 109-114).

``report`` takes an event log (bytes, bytearray or str), reads it with ``records.check_log`` and no second parser, and
returns a mapping with exactly the keys ``ok``, ``findings``, ``corrections_present`` and ``metrics``. If the check
gives any finding, text or line, ``ok`` is false, ``findings`` lists them as strings (the line number, then the
finding), ``corrections_present`` is None and ``metrics`` is empty: no figure comes from a log that is not clean.
Otherwise ``ok`` is true and ``metrics`` holds the eight metrics in this order: caught_rate, first_pass_acceptance,
drift_false_positive_rate, escaped_defects, human_time_per_task, evidence_coverage, cost_per_accepted_task,
rework_rate. Each is a mapping with ``status``, ``sources`` (the event types and payload keys read, with file and line)
and ``limits`` (plain words), and its own figures. The status is one of three words:

- ``mechanical``: the figures are counted from the log's events;
- ``needs_judgement``: the figure needs a judge; it is AI-judged under CR-002 K6 and is a label here, never a number;
- ``no_source``: the log holds nothing to count; the metric's ``value`` is None and the metric is listed as uncovered
  (concept line 819); no estimate is made. A context count beside such a metric sits under its own named key and is
  a count, not the metric.

A line that repeats an earlier line exactly (``duplicate_of`` set) is skipped; a repeat with other content is already
a finding of the check. Lines that carry ``corrects`` are counted as they stand: this report does not apply
corrections, as the base inputs do not read ``corrects`` either, so a corrected and a correcting decision are both
counted. ``corrections_present`` gives their number and the sorted event ids they correct, so that a double count is
visible. A task is joined to an event only through the envelope's ``task_id``. In a clean log every event of the
types task.* and decision.* and every record whose subject is a task carries a task_id, and a record about a subject
that is not a task must not carry one (records.py :698-706); events of the other types, for example intent.changed,
drift.detected, evidence.stale or conflict.detected, may lack one. No metric joins such an event to a task: the drift
counts take events by type, and the human_authority records without a task_id are counted apart as ``without_task_id``
under human_time_per_task and are attributed to no task. The metrics are separate cuts of the same events: no figure
is added to another metric's figure, and one event may appear under two metrics' names.

At L1 the governor never gives the decision ACCEPT (governor.py rows 4 and 5): an accepted task has the decision
NEEDS_REVIEW and the next state ACCEPTED, and a task waiting for approval has the next state IN_REVIEW. So the outcome
of a submission is read from the next state of the acceptance decision that follows it, and "not blocked" means
waiting for approval or approved, not accepted.

Limits: the figures are descriptive over a small self-build log; the judged parts are AI-judged under CR-002 K6 and
are no basis for the product's L1 default or for any level; no measurement of the trust boundary is involved
(master plan line 113). The function reads no clock, no file and no environment, writes nothing and raises nothing but the
TypeError of an argument that ``records.check_log`` refuses (anything but bytes, bytearray or str).
"""

import datetime
import re

from aieos_bootstrap import records

METRIC_NAMES = ('caught_rate', 'first_pass_acceptance', 'drift_false_positive_rate', 'escaped_defects',
                'human_time_per_task', 'evidence_coverage', 'cost_per_accepted_task', 'rework_rate')
STATUSES = ('mechanical', 'needs_judgement', 'no_source')
_BLOCKED_STATES = ('REWORK', 'REJECTED', 'ESCALATED')
_NOT_BLOCKED_STATES = ('IN_REVIEW', 'ACCEPTED')
_FIRST_PASS_DECISIONS = ('NEEDS_REVIEW', 'ACCEPT')
_AUDIT_SOURCES = ('deterministic_tool_local', 'deterministic_tool_external_ci')
_TIME = re.compile(r'([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]+))?Z')
_CORRECTIONS_LIMIT = 'corrections are not applied: a corrected and a correcting decision are both counted'


def _payload(event):
    value = event.get('payload')
    return value if isinstance(value, dict) else {}


def _by_task(events):
    """The events that carry a task_id, grouped by it in log order."""
    groups = {}
    for event in events:
        task = event.get('task_id')
        if isinstance(task, str) and task:
            groups.setdefault(task, []).append(event)
    return groups


def _is_submission(event):
    return event.get('type') == 'task.submitted' and _payload(event).get('compensating') is not True


def _window_decision(task_events, start):
    """The first decision.acceptance after index ``start`` and before the next task.submitted of the task, or None."""
    for event in task_events[start + 1:]:
        if event.get('type') == 'task.submitted':
            return None
        if event.get('type') == 'decision.acceptance':
            return event
    return None


def _caught_rate(groups, events):
    submissions = blocked = not_blocked = undecided = undecided_error = unclassified = 0
    needs_review = insufficient_human = other_decision = 0
    for task_events in groups.values():
        for index, event in enumerate(task_events):
            if not _is_submission(event):
                continue
            submissions += 1
            decision = _window_decision(task_events, index)
            if decision is None:
                undecided += 1
                continue
            body = _payload(decision)
            if body.get('decision') is None:
                undecided_error += 1
            elif body.get('next_task_state') in _BLOCKED_STATES:
                blocked += 1
            elif body.get('next_task_state') in _NOT_BLOCKED_STATES:
                not_blocked += 1
                if body.get('decision') == 'NEEDS_REVIEW':
                    needs_review += 1
                elif body.get('decision') == 'INSUFFICIENT_EVIDENCE' and body.get('next_task_state') == 'IN_REVIEW':
                    insufficient_human += 1
                else:
                    other_decision += 1
            else:
                unclassified += 1
    compensating = sum(1 for e in events if e.get('type') == 'task.submitted' and _payload(e).get('compensating') is True)
    return {
        'status': 'mechanical',
        'blocked': blocked,
        'submissions': submissions,
        'ratio': (blocked / submissions) if submissions else None,
        'not_blocked': not_blocked,
        'not_blocked_needs_review': needs_review,
        'not_blocked_insufficient_human': insufficient_human,
        'not_blocked_other': other_decision,
        'undecided': undecided,
        'undecided_error': undecided_error,
        'unclassified': unclassified,
        'violation_detected': sum(1 for e in events if e.get('type') == 'violation.detected'),
        'fence_refusals': sum(1 for e in events if e.get('type') == 'record.added'
                              and _payload(e).get('evidence_type') == 'refused_submission'),
        'compensating_submissions': compensating,
        'reason_share': {'status': 'needs_judgement', 'value': None,
                         'note': 'needs judgement (AI-judged, CR-002 K6), not estimated'},
        'sources': ['task.submitted payload compensating (records.py :275)',
                    'decision.acceptance payload decision and next_task_state (records.py :122-125; governor.py :464-482)',
                    'violation.detected (drift.py :51)',
                    'record.added payload evidence_type refused_submission (eventlog.py :117-122)'],
        'limits': ['at L1 the governor never gives ACCEPT (governor.py :474-475): the outcome is read from next_task_state',
                   'not_blocked means waiting for approval (IN_REVIEW) or approved (ACCEPTED), not accepted',
                   'violation_detected and fence_refusals are never added into the headline',
                   'unclassified and not_blocked_other are names added beside the contract\'s figures: they hold a '
                   'decision the definitions do not place (a next state outside both sets, or a not-blocked decision '
                   'other than NEEDS_REVIEW and other than INSUFFICIENT_EVIDENCE with the next state IN_REVIEW), so '
                   'that none is dropped',
                   'not_blocked_insufficient_human is INSUFFICIENT_EVIDENCE with the next state IN_REVIEW, which the '
                   'governor gives only when every missing type is a human one (governor.py :470-473); '
                   'INSUFFICIENT_EVIDENCE with the next state ACCEPTED, which the governor never gives, is counted '
                   'under not_blocked_other',
                   _CORRECTIONS_LIMIT],
    }


def _empty_list(value):
    return isinstance(value, list) and not value


def _clean_decision(body):
    """Fail closed: a list that is absent, null or not a list is not empty, so the decision is not clean."""
    if body.get('decision') not in _FIRST_PASS_DECISIONS:
        return False
    if not (_empty_list(body.get('missing_gates')) and _empty_list(body.get('failed_gates'))
            and _empty_list(body.get('blocking'))):
        return False
    profile = body.get('profile_used')
    if not isinstance(profile, list):
        return False
    return all(isinstance(item, dict) and _empty_list(item.get('missing_types')) for item in profile)


def _first_pass(groups):
    denominator = passed = 0
    without_submission = []
    without_decision = []
    first_decision_error = []
    for task, task_events in groups.items():
        first = next((i for i, e in enumerate(task_events) if _is_submission(e)), None)
        if first is None:
            without_submission.append(task)
            continue
        decision = _window_decision(task_events, first)
        if decision is None:
            without_decision.append(task)
            continue
        body = _payload(decision)
        if body.get('decision') is None:
            first_decision_error.append(task)
            continue
        denominator += 1
        if _clean_decision(body):
            passed += 1
    return {
        'status': 'mechanical',
        'passed': passed,
        'denominator': denominator,
        'ratio': (passed / denominator) if denominator else None,
        'tasks_without_submission': sorted(without_submission),
        'without_decision': sorted(without_decision),
        'first_decision_error': sorted(first_decision_error),
        'sources': ['task.submitted (records.py :275)',
                    'task.submitted payload compensating (records.py :275)',
                    'decision.acceptance payload decision, missing_gates, failed_gates, blocking, profile_used '
                    '(governor.py :430-431, :450-455, :493-495)'],
        'limits': ['the raw figure is reported as it is; a first decision that is not clean is not interpreted',
                   'a task whose only submissions are compensating is listed under tasks_without_submission',
                   'the decision NEEDS_REVIEW or ACCEPT is reached only when no earlier row of the governor applied',
                   'fail closed: a decision whose profile_used key is absent or not a list, or whose missing_gates, '
                   'failed_gates or blocking is absent, null or not an empty list, or one of whose items has a '
                   'missing_types that is not an empty list, is not clean',
                   'an empty profile_used list is clean: the governor writes it when the profile has no dimension '
                   '(governor.py :433, :450)',
                   _CORRECTIONS_LIMIT],
    }


def _drift(events):
    return {
        'status': 'no_source',
        'value': None,
        'drift_warning_counts': {
            'drift.detected': sum(1 for e in events if e.get('type') == 'drift.detected'),
            'violation.detected': sum(1 for e in events if e.get('type') == 'violation.detected'),
        },
        'sources': ['drift.detected (emitted by scope_drift.py :68 and scope_reconcile.py :105)',
                    'violation.detected (emitted by drift.py :51 and violation.py)'],
        'limits': ['no record in the log judges a warning right or wrong, so the rate has no source',
                   'the counts are by event type only; the envelope has no emitter field',
                   'the counts take every event, with or without a task_id; no event is joined to a task here',
                   'the two counts are never summed; violation.detected is also the violation_detected count of caught_rate',
                   _CORRECTIONS_LIMIT],
    }


def _escaped():
    return {
        'status': 'no_source',
        'value': None,
        'sources': [],
        'limits': ['no event or record says that a defect was found after DONE', _CORRECTIONS_LIMIT],
    }


def _risk_classes(events):
    """The latest risk_class audit copy of each task in log order (records.py :106-114)."""
    classes = {}
    for event in events:
        if event.get('type') != 'record.added':
            continue
        body = _payload(event)
        if body.get('evidence_type') == 'risk_class' and body.get('source_class') in _AUDIT_SOURCES:
            subject = body.get('subject')
            value = body.get('risk_class')
            if isinstance(subject, str):
                # the latest copy decides, also when its value is null (not computed): the class is then unknown
                classes[subject] = value if isinstance(value, str) else 'unknown'
    return classes


def _human(events):
    classes = _risk_classes(events)
    counts = {}
    without_task_id = 0
    for event in events:
        if event.get('type') != 'record.added':
            continue
        body = _payload(event)
        if body.get('source_class') != 'human_authority':
            continue
        task = event.get('task_id')
        if not (isinstance(task, str) and task):
            without_task_id += 1
            continue
        risk = classes.get(task, 'unknown')
        counts[risk] = counts.get(risk, 0) + 1
    return {
        'status': 'no_source',
        'value': None,
        'human_authority_records_by_risk_class': {k: counts[k] for k in sorted(counts)},
        'without_task_id': without_task_id,
        'sources': ['record.added payload source_class human_authority (records.py :99-101)',
                    'record.added payload evidence_type risk_class (records.py :106-114)'],
        'limits': ['the log holds no human attention time; the counts are not a time',
                   'a human_authority record without a task_id is counted apart as without_task_id and is attributed '
                   'to no task',
                   'in the self-build most approvals are the decision agent\'s; a risk class with no human_authority '
                   'record is absent from the mapping, not listed as zero',
                   _CORRECTIONS_LIMIT],
    }


def _coverage(groups):
    counted = without_profile = satisfied = required = 0
    uncovered = set()
    for task_events in groups.values():
        decisions = [e for e in task_events if e.get('type') == 'decision.acceptance']
        if not decisions:
            continue
        body = _payload(decisions[-1])
        notes = body.get('uncovered')
        if isinstance(notes, list):
            uncovered.update(n for n in notes if isinstance(n, str))
        profile = body.get('profile_used')
        if body.get('decision') is None or not isinstance(profile, list) or not profile:
            without_profile += 1
            continue
        counted += 1
        for item in profile:
            if isinstance(item, dict):
                required += 1
                if _empty_list(item.get('missing_types')):
                    satisfied += 1
    return {
        'status': 'mechanical',
        'decisions_counted': counted,
        'dimensions_satisfied': satisfied,
        'dimensions_required': required,
        'ratio': (satisfied / required) if required else None,
        'uncovered': sorted(uncovered),
        'decisions_without_profile': without_profile,
        'sources': ['decision.acceptance payload profile_used and uncovered (records.py :122-126; governor.py :450-455)'],
        'limits': ['only the last acceptance decision of each task is counted',
                   'a dimension is satisfied when its missing_types is an empty list; any other value is not satisfied',
                   'the uncovered notes are taken from the last acceptance decision of every task, counted or not',
                   'decisions_without_profile also counts a last decision whose decision is null (an error record)',
                   _CORRECTIONS_LIMIT],
    }


def _seconds(text):
    # appended_at is required and its form is checked by records.check_log (records.py :96, :243-254, :776)
    match = _TIME.fullmatch(text)
    parts = [int(match.group(i)) for i in range(1, 7)]
    micro = int((match.group(7) or '0')[:6].ljust(6, '0'))
    return datetime.datetime(*parts, microsecond=micro)


def _median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _cost(groups):
    walls = {}
    approved_missing = []
    negative = []
    for task, task_events in groups.items():
        done = next((e for e in task_events if e.get('type') == 'task.done'), None)
        if done is None:
            continue
        approved = next((e for e in task_events if e.get('type') == 'task.approved'), None)
        if approved is None:
            approved_missing.append(task)
            continue
        start, end = _seconds(approved.get('appended_at')), _seconds(done.get('appended_at'))
        if end < start:
            negative.append(task)
            continue
        walls[task] = round((end - start).total_seconds(), 6)
    values = list(walls.values())
    all_done = sum(1 for t in groups.values() if any(e.get('type') == 'task.done' for e in t))
    return {
        'status': 'mechanical',
        'wall_seconds': {k: walls[k] for k in sorted(walls)},
        'median': round(_median(values), 6) if values else None,
        'maximum': max(values) if values else None,
        'tasks_done_without_approved': sorted(approved_missing),
        'tasks_with_negative_wall': sorted(negative),
        'tasks_without_done': sum(1 for t in groups.values() if not any(e.get('type') == 'task.done' for e in t)),
        'tasks_done': all_done,
        'tokens': {'status': 'no_source', 'value': None},
        'sources': ['task.approved and task.done appended_at (spec-01 :49, :62-69)'],
        'limits': ['wall time between the first task.approved and the first task.done; it includes idle time',
                   'a task whose done time is before its approval time is listed under tasks_with_negative_wall and is '
                   'kept out of wall_seconds, median and maximum; a zero wall time stays in',
                   'wall_seconds is a mapping keyed by task id (sorted), not a list',
                   'a fraction of a second beyond six digits is cut to six (microseconds), so two times that differ '
                   'only beyond the sixth digit count as equal',
                   'an accepted task here means a task that has a task.done',
                   'no token count is in the log',
                   _CORRECTIONS_LIMIT],
    }


def _rework(groups):
    per_task = {}
    without_approved = []
    for task, task_events in groups.items():
        decisions = [i for i, e in enumerate(task_events) if e.get('type') == 'decision.acceptance']
        if not decisions:
            continue
        approvals = [i for i, e in enumerate(task_events) if e.get('type') == 'task.approved']
        start = approvals[-1] if approvals else -1
        if not approvals:
            without_approved.append(task)
        per_task[task] = sum(1 for i in decisions if i > start
                             and _payload(task_events[i]).get('next_task_state') == 'REWORK')
    return {
        'status': 'no_source',
        'value': None,
        'rework_before_acceptance': {
            'status': 'mechanical',
            'per_task': {k: per_task[k] for k in sorted(per_task)},
            'total': sum(per_task.values()),
            'without_approved': sorted(without_approved),
        },
        'sources': ['decision.acceptance payload next_task_state REWORK since the last task.approved (spec-01 :73)'],
        'limits': ['the concept\'s rework rate (DONE tasks reopened or reverted) has no source: no DONE task is reopened '
                   'by an event and a revert is not an event',
                   'rework_before_acceptance is a different measure and is never the rework rate',
                   _CORRECTIONS_LIMIT],
    }


def report(log):
    """The report of the module docstring for ``log``; see there."""
    checked = records.check_log(log)
    findings = ['line %d: %s' % (number, finding) if number else 'text: %s' % (finding,)
                for number, finding in checked.findings()]
    if findings:
        return {'ok': False, 'findings': findings, 'corrections_present': None, 'metrics': {}}
    events = [line.event for line in checked.lines if line.duplicate_of is None and line.event is not None]
    groups = _by_task(events)
    corrected = sorted({e['corrects'] for e in events if isinstance(e.get('corrects'), str)})
    metrics = {
        'caught_rate': _caught_rate(groups, events),
        'first_pass_acceptance': _first_pass(groups),
        'drift_false_positive_rate': _drift(events),
        'escaped_defects': _escaped(),
        'human_time_per_task': _human(events),
        'evidence_coverage': _coverage(groups),
        'cost_per_accepted_task': _cost(groups),
        'rework_rate': _rework(groups),
    }
    return {
        'ok': True,
        'findings': [],
        'corrections_present': {'lines': sum(1 for e in events if 'corrects' in e), 'corrected_event_ids': corrected},
        'metrics': metrics,
    }

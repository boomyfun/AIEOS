"""The audit copies of specification 4 section 10 (task TASK-029; specification 4 revision 3, sections 4 item 1, 6
item 1, 8 and 10; specification 2 revision 4, section 6.2).

``build_records`` is pure. For one task at an evaluated commit it returns, in this order:
- the risk_class record: the class that the policy's risk rules give for the task's changed paths, computed with
  governor.derive_inputs on the caller's values with the contract's declared risk set to "low", so that a higher
  declared risk, which the governor also uses, does not raise it (the reading of TASK-029 AC2); null when a changed
  path matches no rule; a rule that cannot be evaluated matches every path and a class that cannot be read counts as
  critical, as derive_inputs fails closed;
- the evidence_profile record: governor.derive_inputs on the values as given, so the profile rests on the governor's
  own risk, which a higher declared risk may raise; the two records may therefore rest on different classes; null
  when the profile cannot be derived;
- the AC coverage record of the contract version, ac_coverage.check and ac_coverage.coverage_record called unchanged,
  only when there are findings.
The two audit copies are observations bound to the evaluated commit and its intent versions, with no outcome, gate,
blocking_kind or dimension (specification 2 revision 4); their record ids are the SHA-256 hex digest of "risk-class"
or "evidence-profile", the task id, the evaluated commit and the policy version joined by LF.

``record_evaluation`` appends each built record once as a record.added event through the core's single writer
(constitution INV-004), with no fencing token, under an event id that is the SHA-256 hex digest of "record.added" and
the record id joined by LF, so that a rerun with the same content gives the writer's "duplicate"; a rerun with other
content under the same ids (other values under the same policy version, or another recorder or source class) is
refused by the writer as a conflict, and record_evaluation reports it as refused. It is called beside
evaluation.evaluate_task with the same values; neither calls the other. The caller calls record_evaluation before
evaluate_task: evaluate_task derives its event id from the task's kept records, and the audit copies are records of
the task, so copies written after an evaluation would give a rerun of that evaluation a new event id instead of a
duplicate.

Limits (TASK-029 AC12):
- The values are the writer's statements, not the governor's; the governor's rules and inputs are unchanged and it
  takes no value from these records (specification 4 section 12 point 10 stays open).
- The policy version is not on the record (specification 2 revision 4); it is part of the record id only.
- At most one record of each name per task and evaluated commit is the caller's duty; the derived ids make a rerun a
  duplicate, not a second record.
- No evidence.stale event, reconciliation or drift (specification 4 sections 3 and 7); no lease, state effect or Git
  read; no file is opened except through the writer, and no process, clock, environment, network or model call.
- records.py does not gain the keys session, ci_run and acs of specification 2 revision 3 (DEF-0051, line 24).
"""
import copy
import hashlib

from aieos_bootstrap import ac_coverage
from aieos_bootstrap import governor
from aieos_bootstrap import records
from aieos_bootstrap import writer

EVENT_TYPE = 'record.added'
SOURCE_CLASSES = ('deterministic_tool_local', 'deterministic_tool_external_ci')
RISK_TYPE = 'risk_class'
PROFILE_TYPE = 'evidence_profile'
_DIGITS = frozenset('0123456789')
_HEX = frozenset('0123456789abcdef')


def _text(value):
    return isinstance(value, str) and value != ''


def _digits(value):
    return value != '' and all(c in _DIGITS for c in value)


def _is_task(value):
    return _text(value) and value.startswith('TASK-') and _digits(value[5:])


def _is_version(value):
    return _text(value) and value[0] == 'v' and _digits(value[1:])


def _is_commit(value):
    return isinstance(value, str) and len(value) in (40, 64) and all(c in _HEX for c in value)


def _digest(*parts):
    return hashlib.sha256('\n'.join(parts).encode('utf-8')).hexdigest()


def _copy(task_id, kind, label, value, evaluated_commit, policy_version, intent_versions, recorder, source_class):
    return {'record_id': _digest(label, task_id, evaluated_commit, policy_version), 'fact_kind': 'observation',
            'source_class': source_class, 'recorder': recorder, 'subject': task_id, 'evidence_type': kind,
            kind: value, 'commit': evaluated_commit, 'intent_versions': dict(intent_versions)}


def build_records(task_id, contract_version, evaluated_commit, intent_versions, values, coverage_contract, recorder,
                  source_class='deterministic_tool_local'):
    """The records of AC2 to AC4 in order (AC1). Raises ValueError naming the argument or the step for any value out
    of its form, for governor.derive_inputs raising, and for a built record that records.check_record finds out of
    form (AC5). Its arguments are not changed."""
    if not _is_task(task_id):
        raise ValueError('task_id is not TASK- followed by digits')
    if not _is_version(contract_version):
        raise ValueError('contract_version is not v followed by digits')
    if not _is_commit(evaluated_commit):
        raise ValueError('evaluated_commit is not a full lowercase hex commit id')
    if not (isinstance(intent_versions, dict) and intent_versions
            and all(_text(k) and _is_version(v) for k, v in intent_versions.items())):
        raise ValueError('intent_versions is not a non-empty map of ids to v followed by digits')
    if not (isinstance(values, dict) and _text(values.get('policy_version'))):
        raise ValueError('values is not a mapping with a non-empty policy_version')
    if not _text(recorder):
        raise ValueError('recorder is not a non-empty string')
    if source_class not in SOURCE_CLASSES:
        raise ValueError('source_class is not deterministic_tool_local or deterministic_tool_external_ci')
    try:
        given = governor.derive_inputs(copy.deepcopy(values))
        low = copy.deepcopy(values)
        low['contract'] = dict(low['contract'], risk='low')
        rules_only = governor.derive_inputs(low)
    except Exception as exc:
        raise ValueError('derive_inputs raised %s' % type(exc).__name__) from None
    policy = values['policy_version']
    profile = given['evidence_profile']
    built = [
        _copy(task_id, RISK_TYPE, 'risk-class', rules_only['risk'], evaluated_commit, policy, intent_versions, recorder,
              source_class),
        _copy(task_id, PROFILE_TYPE, 'evidence-profile', None if profile is None else copy.deepcopy(profile),
              evaluated_commit, policy, intent_versions, recorder, source_class),
    ]
    findings = ac_coverage.check(coverage_contract)
    coverage = ac_coverage.coverage_record(task_id, contract_version, findings, recorder, source_class)
    if coverage is not None:
        built.append(coverage)
    for r in built:
        problems = records.check_record(r)
        if problems:
            raise ValueError('a built record is out of form: %s' % problems[0])
    if len({r['record_id'] for r in built}) != len(built):
        raise ValueError('two built records have the same record_id')
    return built


def event_id_of(record_id):
    """The event id under which a record is appended (AC6)."""
    return _digest(EVENT_TYPE, record_id)


def _result(result, reason, entries, findings):
    return {'result': result, 'reason': reason, 'records': entries, 'findings': list(findings)}


def record_evaluation(root, task_id, contract_version, evaluated_commit, intent_versions, values, coverage_contract,
                      recorder, now, source_class='deterministic_tool_local', append=None):
    """Build the records and append each once through the writer (AC6). No exception escapes."""
    try:
        append = writer.append_event if append is None else append
        try:
            built = build_records(task_id, contract_version, evaluated_commit, intent_versions, values,
                                  coverage_contract, recorder, source_class)
        except Exception as exc:
            return _result('refused', 'argument', [], ['argument: %s' % (exc if isinstance(exc, ValueError)
                                                                         else type(exc).__name__)])
        entries = [{'record_id': r['record_id'], 'event_id': event_id_of(r['record_id']), 'status': 'not appended'}
                   for r in built]
        for entry, r in zip(entries, built):
            try:
                w = append(root, EVENT_TYPE, r, entry['event_id'], now, recorder, task_id=task_id)
                outcome = getattr(w, 'result', None)
                if type(outcome) is not str:
                    raise TypeError('the result is not a string')
            except Exception as exc:
                return _result('refused', 'store', entries, ['store: the append raised or gave no result (%s); '
                                                             'whether the record was appended is not known'
                                                             % type(exc).__name__])
            if outcome in ('appended', 'duplicate'):
                entry['status'] = outcome
                continue
            try:
                extra = [f for f in (getattr(w, 'findings', ()) or ()) if type(f) is str]
            except Exception:
                extra = []
            return _result('refused', 'store', entries, ['store: the writer gave %r' % outcome] + extra)
        return _result('written', None, entries, [])
    except Exception as exc:  # AC6: no exception escapes
        return _result('refused', 'store', [], ['a step raised %s' % type(exc).__name__])

"""Form checks for the event log of specification 2, sections 6.1 to 6.4 (task TASK-001).

Given the bytes or the text of an event log, ``check_log`` reports, for each line, the parsed event or the list of its
findings, each naming the rule it breaks (a section of specification 2 and a short name, for example ``6.1:seq``).
``check_record``, ``check_payload`` and ``check_decision`` check one record, one payload or one decision contract.

Limits (TASK-001 AC7):
- It checks form only. Its results say "no error found" or list the findings; they never say that a line, a record or
  an event is right, counts as evidence, counts as an approval, or is current.
- It does not check that the ids named in approval_record, decision_record, refers_to or blocked_by exist, and it
  checks reason only as a non-empty string.
- It checks no state transition (specification 1 sections 5 and 6), recomputes no hash, and treats the fencing rule
  of specification 1 section 8 as out of scope beyond the form of the token (AC3).
- Of the acceptance keys of section 6.4 only decision is required (a reading). When present, task_content_hash must
  be 64 lowercase hex digits, evaluated_commit a commit id, next_task_state a state name of section 2, and
  profile_used a list of objects with exactly its four keys (the values inside each item are not checked);
  intent_versions and fact_kind are checked by the record rules (fact_kind must be interpretation). The other
  acceptance keys are not checked.
- A decision.execution payload may hold, besides the record keys, decision and error, the keys of specification 3
  section 9's execution decision record (TASK-011): contract_hash, contract_version, base_commit, head_commit,
  log_seq, delta, checks, outcomes_fired, read_set, signatures, intent_versions, dependencies, constitution, runtime,
  budgets, policy_version, engine_identity, uncovered and state_effect; any other key is an unknown key. None of them
  is required (a reading). When present:
  - base_commit and head_commit must be full lowercase hex commit ids; log_seq an integer at least 0 and not a
    boolean; contract_hash 64 lowercase hex digits; contract_version v followed by digits;
  - engine_identity an object with exactly code_sha256 (null or 64 lowercase hex digits) and python ("X.Y.Z", digits);
  - checks a list of exactly eight objects with exactly the keys check, status, outcome and detail: check the integers
    1 to 8 (not booleans), each once; status one of passed, fired, skipped and not_run; outcome an execution decision
    value when status is fired and null otherwise; detail a string;
  - outcomes_fired a list of the fired values of specification 3 section 7 (STOP: violation, STOP: scope invalid,
    STOP: runtime insufficient, ESCALATE, BLOCKED, REPLAN, CONTINUE_WITH; CONTINUE is not one of them), without
    repeats and in that order; when decision is not null, decision must equal its first value, or CONTINUE when it is
    empty;
  - policy_version a non-empty string or null;
  - intent_versions, for this payload type only, either in the record form or an object mapping each entry to exactly
    {contract, current}, each a non-empty string or null; any other value is refused (a reading, decision D-337's
    erratum of AC3, carried to the next revision of specifications 2 and 3);
  - of delta, signatures, uncovered and state_effect only that each is a list, and of read_set, dependencies,
    constitution, runtime and budgets only that each is an object, is checked, not the forms inside.
  No Resume Check exists until TASK-008, so no real execution record is checked by this module yet.
- record_id is checked as a non-empty string; whether it is unique across a log is not checked. evidence_type and
  dimension are open vocabularies, checked as non-empty strings only.
- An ignored duplicate is reported as such whether or not the line it repeats has findings of its own.
- It reads only what it is given: it opens no file, writes nothing, starts no process and makes no network call.

Readings of the specifications that the contract marks "(reading)" are noted where they are applied.
"""

import collections
import datetime
import json
import re

EVENT_TYPES = frozenset({
    'task.drafted', 'task.approved', 'task.blocked', 'task.unblocked', 'task.submitted', 'decision.acceptance',
    'decision.execution', 'task.done', 'task.stale', 'task.replanned', 'intent.changed', 'drift.detected',
    'violation.detected', 'evidence.stale', 'conflict.detected', 'record.added'})
STATE_NAMES = frozenset({
    'DRAFT', 'READY', 'IN_PROGRESS', 'VERIFYING', 'ACCEPTED', 'DONE', 'IN_REVIEW', 'REWORK', 'ESCALATED', 'REJECTED',
    'BLOCKED', 'STALE'})
ENVELOPE_REQUIRED = ('event_id', 'type', 'appended_at', 'seq', 'payload')
ENVELOPE_KEYS = frozenset(ENVELOPE_REQUIRED + ('task_id', 'fencing_token', 'corrects'))
FACT_KINDS = frozenset({'claim', 'observation', 'interpretation', 'authority'})
SOURCE_CLASSES = frozenset({
    'agent_declared', 'same_lineage_review', 'deterministic_tool_local', 'deterministic_tool_external_ci',
    'cross_vendor_review', 'decision_agent', 'human_authority', 'delegate_ai'})
OUTCOMES = frozenset({'pass', 'fail', 'blocking'})
BLOCKING_KINDS = frozenset({'out_of_scope', 'forbidden_path', 'violation', 'constitution', 'other'})
BINDING_KINDS = frozenset({'contract', 'acceptance', 'change_request', 'baseline'})
RECORD_REQUIRED = ('record_id', 'fact_kind', 'source_class', 'recorder', 'subject')
RECORD_KEYS = frozenset(RECORD_REQUIRED + (
    'evidence_type', 'dimension', 'gate', 'outcome', 'blocking_kind', 'commit', 'intent_versions', 'approval_binding',
    'decision_ref', 'models', 'basis', 'stands_for', 'refers_to'))
ACCEPTANCE_DECISIONS = frozenset({'ACCEPT', 'NEEDS_REVIEW', 'INSUFFICIENT_EVIDENCE', 'NEEDS_REWORK', 'REJECT'})
EXECUTION_DECISIONS = frozenset({
    'CONTINUE', 'CONTINUE_WITH', 'REPLAN', 'STOP: scope invalid', 'STOP: runtime insufficient', 'STOP: violation',
    'BLOCKED', 'ESCALATE'})
ACCEPTANCE_KEYS = frozenset({
    'task_content_hash', 'evaluated_commit', 'intent_versions', 'next_task_state', 'table_row', 'profile_used',
    'missing_gates', 'blocking', 'failed_gates', 'reverify', 'approval_record', 'policy_version', 'level_version',
    'governor_identity', 'ruleset_version', 'scenario_set_hash', 'uncovered', 'rests_on_ai'})
PROFILE_KEYS = frozenset({'dimension', 'required', 'satisfied_by', 'missing_types'})
# The keys of specification 3 section 9's execution decision record besides the record keys, decision and error
# (TASK-011 AC1), and the order of section 7 in which fired outcomes are listed (TASK-011 AC2).
EXECUTION_KEYS = frozenset({
    'contract_hash', 'contract_version', 'base_commit', 'head_commit', 'log_seq', 'delta', 'checks',
    'outcomes_fired', 'read_set', 'signatures', 'intent_versions', 'dependencies', 'constitution', 'runtime',
    'budgets', 'policy_version', 'engine_identity', 'uncovered', 'state_effect'})
EXECUTION_ORDER = ('STOP: violation', 'STOP: scope invalid', 'STOP: runtime insufficient', 'ESCALATE', 'BLOCKED',
                   'REPLAN', 'CONTINUE_WITH')
CHECK_KEYS = frozenset({'check', 'status', 'outcome', 'detail'})
CHECK_STATUSES = frozenset({'passed', 'fired', 'skipped', 'not_run'})
RECORD_PAYLOAD_TYPES = frozenset({'record.added', 'violation.detected', 'decision.acceptance', 'decision.execution'})
DECISION_TYPES = frozenset({'decision.acceptance', 'decision.execution'})

_TIME = re.compile(r'([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?Z')
_HASH = re.compile(r'[0-9a-f]{64}')
_COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
_VERSION = re.compile(r'v[0-9]+')
_TASK = re.compile(r'TASK-[0-9]+')
_CHANGE = re.compile(r'CHG-[0-9]+')
_GATE = re.compile(r'G[0-9]+')
_BOM = b'\xef\xbb\xbf'


class Finding(collections.namedtuple('Finding', ('rule', 'detail'))):
    """One broken rule: ``rule`` names it (section and short name), ``detail`` says where and how."""

    __slots__ = ()

    def __str__(self):
        return '%s: %s' % (self.rule, self.detail)


class LineReport:
    """The result for one line: its number, the parsed event (only when no finding was made), its findings, and the
    number of the earlier line it repeats when it is an ignored duplicate (specification 1 section 7 point 4)."""

    __slots__ = ('number', 'event', 'findings', 'duplicate_of')

    def __init__(self, number, event, findings, duplicate_of=None):
        self.number = number
        self.findings = tuple(findings)
        self.event = None if self.findings else event
        self.duplicate_of = duplicate_of

    def describe(self):
        head = 'line %d' % self.number
        if self.duplicate_of is not None:
            head += ' (an ignored duplicate of line %d)' % self.duplicate_of
        if not self.findings:
            return head + ': no error found'
        return head + ': ' + '; '.join(str(f) for f in self.findings)


class LogReport:
    """The result for a whole log: the findings about the text as a whole, and one LineReport per line."""

    __slots__ = ('text_findings', 'lines')

    def __init__(self, text_findings, lines):
        self.text_findings = tuple(text_findings)
        self.lines = tuple(lines)

    def findings(self):
        """Every finding, as (line number, finding); line number 0 for a finding about the text as a whole."""
        out = [(0, f) for f in self.text_findings]
        for line in self.lines:
            out.extend((line.number, f) for f in line.findings)
        return out

    def describe(self):
        parts = ['text: ' + '; '.join(str(f) for f in self.text_findings)] if self.text_findings else []
        parts.extend(line.describe() for line in self.lines)
        if not self.findings():
            parts.append('no error found')
        return '\n'.join(parts)


class _Malformed(ValueError):
    pass


def _pairs(pairs):
    """object_pairs_hook: a repeated key in one JSON object makes the object ambiguous (reading: not one object)."""
    out = {}
    for key, value in pairs:
        if key in out:
            raise _Malformed('repeated key %r' % key)
        out[key] = value
    return out


def _constant(name):
    """parse_constant: NaN and the infinities are not JSON."""
    raise _Malformed('%s is not a JSON value' % name)


def _is_str(value):
    return isinstance(value, str) and value != ''


def _is_int(value, minimum=None):
    return isinstance(value, int) and not isinstance(value, bool) and (minimum is None or value >= minimum)


def _matches(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _in(values, value):
    return isinstance(value, str) and value in values


def _is_str_list(value):
    return isinstance(value, list) and all(_is_str(item) for item in value)


def _is_time(value):
    """A UTC time of section 6.1 that exists on the calendar (reading: a leap second, :60, is refused)."""
    if not isinstance(value, str):
        return False
    m = _TIME.fullmatch(value)
    if m is None:
        return False
    try:
        datetime.datetime(*(int(g) for g in m.groups()[:6]))
    except ValueError:
        return False
    return True


# The form of each payload key of section 6.3 (AC5), as (test, description).
_VERSION_FORM = (lambda v: _matches(_VERSION, v), 'v followed by digits')
_HASH_FORM = (lambda v: _matches(_HASH, v), '64 lowercase hex digits')
_STR_FORM = (_is_str, 'a non-empty string')
_LIST_FORM = (_is_str_list, 'a list of non-empty strings (reading: section 6.3 says lists of strings)')
_COMMIT_FORM = (lambda v: _matches(_COMMIT, v), 'a full lowercase hex commit id')
_BOOL_FORM = (lambda v: isinstance(v, bool), 'true or false')


def _one_of(*values):
    return (lambda v: _in(frozenset(values), v), 'one of ' + ', '.join(values))


PAYLOAD_FORMS = {
    'task.drafted': {'contract_version': _VERSION_FORM, 'contract_hash': _HASH_FORM},
    'task.approved': {'contract_version': _VERSION_FORM, 'contract_hash': _HASH_FORM, 'approval_record': _STR_FORM},
    'task.blocked': {'reason': _STR_FORM, 'blocked_by': _LIST_FORM},
    'task.unblocked': {'reason': _STR_FORM},
    'task.submitted': {'commit': _COMMIT_FORM, 'compensating': _BOOL_FORM},
    'task.done': {'decision_record': _STR_FORM},
    'task.stale': {'cause': _one_of('intent_change', 'conflict'), 'refers_to': _STR_FORM},
    'task.replanned': {'contract_version': _VERSION_FORM, 'contract_hash': _HASH_FORM},
    'intent.changed': {'entity': _STR_FORM, 'from_version': _VERSION_FORM, 'to_version': _VERSION_FORM,
                       'change_request': (lambda v: _matches(_CHANGE, v), 'CHG- followed by digits')},
    'drift.detected': {'paths': _LIST_FORM, 'entities': _LIST_FORM},
    'evidence.stale': {'records': _LIST_FORM, 'reason': _one_of('commit', 'intent_version')},
}


def _keys_and_forms(obj, forms, rule, where):
    """Exactly the keys of ``forms``, each of its form."""
    findings = []
    for key in sorted(k for k in obj if k not in forms):
        findings.append(Finding(rule + ':unknown_key', '%s has the key %r, which section 6.3 does not name' % (where, key)))
    for key in sorted(forms):
        if key not in obj:
            findings.append(Finding(rule + ':missing_key', '%s lacks %r' % (where, key)))
            continue
        test, text = forms[key]
        if not test(obj[key]):
            findings.append(Finding(rule + ':' + key, '%s %r is not %s' % (where, key, text)))
    return findings


def check_record(record, extra_keys=frozenset(), where='record', section='6.2'):
    """The form of one record of section 6.2 (AC4). ``extra_keys`` are further keys the caller allows, and ``section``
    names the section(s) whose keys are allowed, for the unknown-key finding (``6.4`` for a decision contract)."""
    if not isinstance(record, dict):
        return [Finding('6.2:record', '%s is not a JSON object' % where)]
    findings = []
    names = 'section 6.2 does not name' if section == '6.2' else 'sections 6.2 and %s do not name' % section
    for key in sorted(k for k in record if k not in RECORD_KEYS and k not in extra_keys):
        findings.append(Finding(section + ':unknown_key', '%s has the key %r, which %s' % (where, key, names)))
    for key in RECORD_REQUIRED:
        if key not in record:
            findings.append(Finding('6.2:missing_key', '%s lacks %r (reading: required)' % (where, key)))
    for key in ('record_id', 'recorder', 'subject'):
        if key in record and not _is_str(record[key]):
            findings.append(Finding('6.2:' + key, '%s %r is not a non-empty string' % (where, key)))
    if 'fact_kind' in record and not _in(FACT_KINDS, record['fact_kind']):
        findings.append(Finding('6.2:fact_kind', '%s fact_kind is not claim, observation, interpretation or authority' % where))
    if 'source_class' in record and not _in(SOURCE_CLASSES, record['source_class']):
        findings.append(Finding('6.2:source_class', '%s source_class is not one of the classes of DM B3' % where))
    findings.extend(_check_outcome(record, where))
    if 'commit' in record and not _matches(_COMMIT, record['commit']):
        findings.append(Finding('6.2:commit', '%s commit is not a full lowercase hex commit id' % where))
    if 'intent_versions' in record and not _is_intent_versions(record['intent_versions']):
        findings.append(Finding('6.2:intent_versions', '%s intent_versions does not map ids to versions v<digits>' % where))
    findings.extend(_check_binding(record, where))
    findings.extend(_check_review_fields(record, where))
    if 'gate' in record and not _matches(_GATE, record['gate']):
        findings.append(Finding('6.2:gate', '%s gate is not G followed by digits' % where))
    for key in ('evidence_type', 'dimension', 'refers_to'):
        if key in record and not _is_str(record[key]):
            findings.append(Finding('6.2:' + key, '%s %r is not a non-empty string' % (where, key)))
    return findings


def _check_outcome(record, where):
    findings = []
    outcome = record.get('outcome')
    if 'outcome' in record and not _in(OUTCOMES, outcome):
        findings.append(Finding('6.2:outcome', '%s outcome is not pass, fail or blocking' % where))
    if outcome == 'blocking' and 'blocking_kind' not in record:
        findings.append(Finding('6.2:blocking_kind', '%s has outcome blocking but no blocking_kind' % where))
    if outcome != 'blocking' and 'blocking_kind' in record:
        findings.append(Finding('6.2:blocking_kind', '%s has blocking_kind without outcome blocking' % where))
    if 'blocking_kind' in record and not _in(BLOCKING_KINDS, record['blocking_kind']):
        findings.append(Finding('6.2:blocking_kind', '%s blocking_kind is not one of %s' % (where, ', '.join(sorted(BLOCKING_KINDS)))))
    return findings


def _is_intent_versions(value):
    return isinstance(value, dict) and all(_is_str(k) and _matches(_VERSION, v) for k, v in value.items())


def _check_binding(record, where):
    if 'approval_binding' not in record:
        if record.get('fact_kind') == 'authority':
            return [Finding('6.2:approval_binding', '%s is an authority record without approval_binding' % where)]
        return []
    b = record['approval_binding']
    if not (isinstance(b, dict) and set(b) == {'kind', 'hash'} and _in(BINDING_KINDS, b['kind'])
            and _matches(_HASH, b['hash'])):
        return [Finding('6.2:approval_binding', '%s approval_binding is not {kind, hash} with kind contract, acceptance, '
                        'change_request or baseline and a 64-hex hash' % where)]
    return []


def _check_review_fields(record, where):
    findings = []
    kind = record.get('evidence_type')
    needs_ref = record.get('source_class') == 'decision_agent' or kind == 'other_model_review'
    if needs_ref and 'decision_ref' not in record:
        findings.append(Finding('6.2:decision_ref', '%s needs decision_ref (a decision_agent record or an other_model_review)' % where))
    if 'decision_ref' in record and not _is_str(record['decision_ref']):
        findings.append(Finding('6.2:decision_ref', '%s decision_ref is not a non-empty string' % where))
    if kind == 'other_model_review' and 'models' not in record:
        findings.append(Finding('6.2:models', '%s is an other_model_review without models' % where))
    if 'models' in record:
        m = record['models']
        if not (isinstance(m, dict) and set(m) == {'reviewer', 'implementer'} and _is_str(m['reviewer'])
                and _is_str(m['implementer'])):
            findings.append(Finding('6.2:models', '%s models is not {reviewer, implementer} with non-empty strings' % where))
    if kind == 'decision_agent_review':
        for key in ('basis', 'stands_for'):
            if key not in record:
                findings.append(Finding('6.2:' + key, '%s is a decision_agent_review without %s' % (where, key)))
    if 'basis' in record and not (_is_str(record['basis']) or (_is_str_list(record['basis']) and record['basis'])):
        findings.append(Finding('6.2:basis', '%s basis is not a non-empty string or list of strings (reading)' % where))
    if 'stands_for' in record and not _is_str(record['stands_for']):
        findings.append(Finding('6.2:stands_for', '%s stands_for is not a non-empty string' % where))
    return findings


def check_decision(event_type, payload, where='payload'):
    """The decision contract of section 6.4 (AC6), the payload of decision.acceptance and decision.execution."""
    if event_type not in DECISION_TYPES:
        return [Finding('6.4:type', '%r is not decision.acceptance or decision.execution' % (event_type,))]
    acceptance = event_type == 'decision.acceptance'
    extra = frozenset({'decision', 'error'}) | (ACCEPTANCE_KEYS if acceptance else EXECUTION_KEYS)
    viewed = payload
    if not acceptance and isinstance(payload, dict) and 'intent_versions' in payload:
        # TASK-011 AC3 (reading; decision D-337's erratum): for this payload type intent_versions may have section 9's
        # form or the record form, both checked below, so the record rules see the payload without it.
        viewed = {k: v for k, v in payload.items() if k != 'intent_versions'}
    findings = check_record(viewed, extra, where, '6.4')
    if not isinstance(payload, dict):
        return findings
    if not acceptance:
        findings.extend(_check_execution_keys(payload, where))
    if 'decision' not in payload:
        findings.append(Finding('6.4:decision', '%s lacks decision' % where))
        return findings
    decision = payload['decision']
    has_error = 'error' in payload
    if (decision is None) != has_error:
        findings.append(Finding('6.4:error', '%s decision must be null exactly when error is present' % where))
    if has_error and not _is_str(payload['error']):
        findings.append(Finding('6.4:error', '%s error is not a non-empty string (reading)' % where))
    allowed = ACCEPTANCE_DECISIONS if acceptance else EXECUTION_DECISIONS
    if decision is not None and not _in(allowed, decision):
        findings.append(Finding('6.4:decision', '%s decision %r is not one of the %d %s values' % (
            where, decision, len(allowed), 'acceptance' if acceptance else 'execution')))
    if 'subject' in payload and _is_str(payload['subject']) and not _matches(_TASK, payload['subject']):
        findings.append(Finding('6.4:subject', '%s subject is not a task id (reading: TASK- followed by digits)' % where))
    if acceptance:
        # Of the acceptance keys only decision is required (reading: section 6.4 does not say which keys a result
        # with an error carries); these four are checked for form when they are present.
        if 'task_content_hash' in payload and not _matches(_HASH, payload['task_content_hash']):
            findings.append(Finding('6.4:task_content_hash', '%s task_content_hash is not 64 lowercase hex digits' % where))
        if 'evaluated_commit' in payload and not _matches(_COMMIT, payload['evaluated_commit']):
            findings.append(Finding('6.4:evaluated_commit', '%s evaluated_commit is not a full lowercase hex commit id' % where))
        if 'fact_kind' in payload and payload['fact_kind'] != 'interpretation':
            findings.append(Finding('6.4:fact_kind', '%s fact_kind is not interpretation' % where))
        if 'next_task_state' in payload and not _in(STATE_NAMES, payload['next_task_state']):
            findings.append(Finding('6.4:next_task_state', '%s next_task_state is not a state name of section 2' % where))
        if 'profile_used' in payload and not _is_profile(payload['profile_used']):
            findings.append(Finding('6.4:profile_used', '%s profile_used is not a list of objects with exactly '
                                    'dimension, required, satisfied_by and missing_types' % where))
    return findings


def _is_profile(value):
    return isinstance(value, list) and all(isinstance(item, dict) and set(item) == PROFILE_KEYS for item in value)


_PYTHON = re.compile(r'[0-9]+\.[0-9]+\.[0-9]+')
# TASK-011 AC2: the keys checked by JSON type only.
_EXECUTION_LISTS = ('delta', 'signatures', 'uncovered', 'state_effect')
_EXECUTION_OBJECTS = ('read_set', 'dependencies', 'constitution', 'runtime', 'budgets')


def _is_checks(value):
    """Eight objects with exactly check, status, outcome and detail; check 1 to 8 each once; outcome an execution
    value exactly when status is fired, else null; detail a string (TASK-011 AC2)."""
    if not (isinstance(value, list) and len(value) == 8):
        return False
    seen = []
    for item in value:
        if not (isinstance(item, dict) and set(item) == CHECK_KEYS):
            return False
        if not _is_int(item['check'], 1) or item['check'] > 8 or not _in(CHECK_STATUSES, item['status']):
            return False
        if item['status'] == 'fired':
            if not _in(EXECUTION_DECISIONS, item['outcome']):
                return False
        elif item['outcome'] is not None:
            return False
        if not isinstance(item['detail'], str):
            return False
        seen.append(item['check'])
    return sorted(seen) == list(range(1, 9))


def _check_execution_keys(payload, where):
    """The forms of specification 3 section 9's keys in a decision.execution payload, each checked only when present
    (TASK-011 AC2, AC3)."""
    findings = []

    def bad(key, text):
        findings.append(Finding('6.4:' + key, '%s %s is not %s' % (where, key, text)))

    for key in ('base_commit', 'head_commit'):
        if key in payload and not _matches(_COMMIT, payload[key]):
            bad(key, 'a full lowercase hex commit id')
    if 'log_seq' in payload and not _is_int(payload['log_seq'], 0):
        bad('log_seq', 'an integer at least 0')
    if 'contract_hash' in payload and not _matches(_HASH, payload['contract_hash']):
        bad('contract_hash', '64 lowercase hex digits')
    if 'contract_version' in payload and not _matches(_VERSION, payload['contract_version']):
        bad('contract_version', 'v followed by digits')
    if 'engine_identity' in payload:
        ident = payload['engine_identity']
        if not (isinstance(ident, dict) and set(ident) == {'code_sha256', 'python'}
                and (ident['code_sha256'] is None or _matches(_HASH, ident['code_sha256']))
                and _matches(_PYTHON, ident['python'])):
            bad('engine_identity', 'an object with exactly code_sha256 (null or 64 lowercase hex digits) and python '
                '(X.Y.Z)')
    if 'checks' in payload and not _is_checks(payload['checks']):
        bad('checks', 'eight objects with exactly check (1 to 8, each once), status, outcome and detail')
    if 'outcomes_fired' in payload:
        fired = payload['outcomes_fired']
        if not (isinstance(fired, list) and all(_in(frozenset(EXECUTION_ORDER), v) for v in fired)
                and len(set(fired)) == len(fired)
                and fired == sorted(fired, key=EXECUTION_ORDER.index)):
            bad('outcomes_fired', 'a list of fired execution values without repeats in the order of section 7')
        elif payload.get('decision') is not None and payload.get('decision') != (fired[0] if fired else 'CONTINUE'):
            bad('outcomes_fired', 'a list whose first value is the decision (CONTINUE when it is empty)')
    if 'policy_version' in payload and not (payload['policy_version'] is None or _is_str(payload['policy_version'])):
        bad('policy_version', 'a non-empty string or null')
    if 'intent_versions' in payload:
        iv = payload['intent_versions']
        if not (_is_intent_versions(iv) or (isinstance(iv, dict) and all(
                _is_str(k) and isinstance(v, dict) and set(v) == {'contract', 'current'}
                and all(x is None or _is_str(x) for x in v.values()) for k, v in iv.items()))):
            bad('intent_versions', 'in the record form or an object mapping each entry to exactly {contract, current} '
                '(reading)')
    for key in _EXECUTION_LISTS:
        if key in payload and not isinstance(payload[key], list):
            bad(key, 'a list')
    for key in _EXECUTION_OBJECTS:
        if key in payload and not isinstance(payload[key], dict):
            bad(key, 'an object')
    return findings


def check_payload(event_type, payload, where='payload'):
    """The payload of one event type of section 6.3 (AC5); records and decisions by AC4 and AC6."""
    if event_type not in EVENT_TYPES:
        return [Finding('6.3:type', '%r is not an event type of section 6.3' % (event_type,))]
    if not isinstance(payload, dict):
        return [Finding('6.1:payload', '%s is not a JSON object' % where)]
    if event_type in DECISION_TYPES:
        return check_decision(event_type, payload, where)
    if event_type == 'record.added':
        return check_record(payload, where=where)
    if event_type == 'violation.detected':
        findings = check_record(payload, where=where)
        for key, want in (('fact_kind', 'observation'), ('outcome', 'blocking'), ('blocking_kind', 'violation')):
            if payload.get(key) != want:
                findings.append(Finding('6.3:violation', '%s %s is not %s' % (where, key, want)))
        return findings
    if event_type == 'conflict.detected':
        forms = {'tasks': _LIST_FORM}
        for key in ('paths', 'interfaces'):
            if key in payload:
                forms[key] = _LIST_FORM
        findings = _keys_and_forms(payload, forms, '6.3', where)
        if 'paths' not in payload and 'interfaces' not in payload:
            findings.append(Finding('6.3:missing_key', '%s has neither paths nor interfaces' % where))
        return findings
    return _keys_and_forms(payload, PAYLOAD_FORMS[event_type], '6.3', where)


def _check_fence(obj, event_type):
    if 'fencing_token' not in obj:
        if event_type == 'task.submitted':
            return [Finding('6.1:fencing_token', 'task.submitted lacks fencing_token')]
        return []
    t = obj['fencing_token']
    ok = (isinstance(t, dict) and set(t) == {'epoch', 'counter'} and _is_int(t['counter'], 0)
          and (_is_str(t['epoch']) or _is_int(t['epoch'], 0)))
    if not ok:
        return [Finding('6.1:fencing_token', 'fencing_token is not {epoch, counter} with counter an integer of 0 or '
                        'more and epoch a non-empty string or an integer of 0 or more (reading)')]
    return []


def _check_task_id(obj, event_type, payload):
    findings = []
    has = 'task_id' in obj
    task_id = obj.get('task_id')
    if has and not _matches(_TASK, task_id):
        findings.append(Finding('6.1:task_id', 'task_id is not TASK- followed by digits (reading)'))
    subject = payload.get('subject') if event_type in RECORD_PAYLOAD_TYPES and isinstance(payload, dict) else None
    subject_is_task = _matches(_TASK, subject)
    needed = event_type.startswith(('task.', 'decision.')) or subject_is_task
    if needed and not has:
        findings.append(Finding('6.1:task_id', '%s lacks task_id' % event_type))
    if has and subject_is_task and task_id != subject:
        findings.append(Finding('6.1:task_id', 'task_id differs from the record subject %r' % subject))
    if (has and event_type in ('record.added', 'violation.detected') and _is_str(subject) and not subject_is_task):
        findings.append(Finding('6.1:task_id', 'a record about an intent entity carries task_id (reading)'))
    return findings


class _LogState:
    """What the lines before the current one fixed: the last seq read, and the first line of each event_id."""

    def __init__(self):
        self.previous_seq = None
        self.first_line = {}


def _without_order(obj):
    """The line's object without seq and appended_at, as canonical JSON text, so that true, 1 and 1.0 stay apart when
    two lines are compared; None when the object cannot be written back as text (too deep or too large a number)."""
    try:
        return json.dumps({k: v for k, v in obj.items() if k not in ('seq', 'appended_at')}, sort_keys=True)
    except (ValueError, RecursionError):
        return None


def _int_text(n):
    """An integer as text for a finding, without converting a very large one, whose decimal text may be refused."""
    return '%d' % n if n.bit_length() <= 64 else 'an integer of %d bits' % n.bit_length()


def _check_seq(obj, number, state):
    seq = obj.get('seq')
    expected = number if state.previous_seq is None else state.previous_seq + 1
    state.previous_seq = seq if _is_int(seq) else None
    if 'seq' not in obj:
        return []
    if not _is_int(seq):
        return [Finding('6.1:seq', 'seq is not an integer')]
    if seq != expected:
        return [Finding('6.1:seq', 'seq is %s; expected %s' % (_int_text(seq), _int_text(expected)))]
    return []


def _check_line(number, raw, state):
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        state.previous_seq = None
        return LineReport(number, None, [Finding('6.1:utf8', 'the line is not UTF-8 (%s)' % exc.reason)])
    try:
        obj = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, RecursionError) as exc:
        state.previous_seq = None
        return LineReport(number, None, [Finding('6.1:json', 'the line is not one JSON object (%s)' % exc)])
    if not isinstance(obj, dict):
        state.previous_seq = None
        return LineReport(number, None, [Finding('6.1:json', 'the line is a JSON %s, not an object' % type(obj).__name__)])
    findings = []
    for key in ENVELOPE_REQUIRED:
        if key not in obj:
            findings.append(Finding('6.1:missing_key', 'the line lacks %r' % key))
    for key in sorted(k for k in obj if k not in ENVELOPE_KEYS):
        findings.append(Finding('2:unknown_key', 'the line has the key %r, which section 6.1 does not name' % key))
    event_id = obj.get('event_id')
    if 'event_id' in obj and not _is_str(event_id):
        findings.append(Finding('6.1:event_id', 'event_id is not a non-empty string'))
    event_type = obj.get('type')
    known_type = _in(EVENT_TYPES, event_type)
    if 'type' in obj and not known_type:
        findings.append(Finding('6.1:type', 'type is not an event type of section 6.3'))
    payload = obj.get('payload')
    if 'payload' in obj and not isinstance(payload, dict):
        findings.append(Finding('6.1:payload', 'payload is not a JSON object'))
    findings.extend(_check_seq(obj, number, state))
    if 'appended_at' in obj and not _is_time(obj['appended_at']):
        findings.append(Finding('6.1:appended_at', 'appended_at is not a UTC time YYYY-MM-DDTHH:MM:SS[.fraction]Z '
                                'that exists on the calendar'))
    duplicate_of = None
    key = _without_order(obj)
    if key is None:
        findings.append(Finding('6.1:json', 'the line cannot be written back as JSON text to compare it with other lines'))
    if _is_str(event_id) and event_id in state.first_line:
        first, earlier = state.first_line[event_id]
        if key is not None and key == earlier:
            duplicate_of = first
        else:
            findings.append(Finding('6.1:duplicate_event_id', 'event_id %r is on line %d with other content '
                                    '(reading: only an identical repeat is an ignored duplicate)' % (event_id, first)))
    if known_type:
        findings.extend(_check_task_id(obj, event_type, payload))
        findings.extend(_check_fence(obj, event_type))
    elif 'fencing_token' in obj:
        findings.extend(_check_fence(obj, None))
    if 'corrects' in obj:
        corrects = obj['corrects']
        if not (_is_str(corrects) and corrects in state.first_line):
            findings.append(Finding('6.1:corrects', 'corrects is not the event_id of an earlier line (reading)'))
    if known_type and isinstance(payload, dict):
        findings.extend(check_payload(event_type, payload))
    if _is_str(event_id) and event_id not in state.first_line:
        state.first_line[event_id] = (number, key)
    return LineReport(number, obj, findings, duplicate_of)


def check_log(data):
    """Check an event log given as bytes (or as text, which is encoded as UTF-8 first). Returns a LogReport.

    The text as a whole must not start with a byte-order mark and must hold no CR byte (section 2). Lines are split at
    LF; a last empty line after the final LF is not a line. Every line counts for seq, an ignored duplicate included
    (reading)."""
    if isinstance(data, str):
        raw = data.encode('utf-8', 'surrogatepass')
    elif isinstance(data, (bytes, bytearray)):
        raw = bytes(data)
    else:
        raise TypeError('check_log takes bytes or str, not %s' % type(data).__name__)
    text_findings = []
    if raw.startswith(_BOM):
        text_findings.append(Finding('2:bom', 'the text starts with a byte-order mark'))
    if b'\r' in raw:
        text_findings.append(Finding('2:cr', 'the text holds a CR byte; line ends are LF only'))
    parts = raw.split(b'\n')
    if parts[-1] == b'':
        parts.pop()
    state = _LogState()
    return LogReport(text_findings, [_check_line(n, part, state) for n, part in enumerate(parts, 1)])

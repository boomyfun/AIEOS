// Round 2: the forms of records.py that eventlog.append and recovery.reconcile use, with their findings' full texts:
// check_log (and _check_line), check_payload, check_record (with check_audit_copy), check_decision and _check_fence.
// Every finding is kept as Python's Finding(rule, detail), whose text is "rule: detail".

import type { V, VObj } from './r2_pyjson.ts';
import {
  R2Fail, PyMalformed, isDict, isList, isInt, isStr, get, keysAre, sortedStrs, pyRepr, reprStr, dumps, pyLoads,
} from './r2_pyjson.ts';

export class Finding {
  readonly rule: string;
  readonly detail: string;
  constructor(rule: string, detail: string) {
    this.rule = rule;
    this.detail = detail;
  }
  toString(): string {
    return this.rule + ': ' + this.detail;
  }
}

const F = (rule: string, detail: string): Finding => new Finding(rule, detail);

export const EVENT_TYPES: ReadonlySet<string> = new Set([
  'task.drafted', 'task.approved', 'task.blocked', 'task.unblocked', 'task.submitted', 'decision.acceptance',
  'decision.execution', 'task.done', 'task.stale', 'task.replanned', 'intent.changed', 'drift.detected',
  'violation.detected', 'evidence.stale', 'conflict.detected', 'record.added']);
const STATE_NAMES: ReadonlySet<string> = new Set([
  'DRAFT', 'READY', 'IN_PROGRESS', 'VERIFYING', 'ACCEPTED', 'DONE', 'IN_REVIEW', 'REWORK', 'ESCALATED', 'REJECTED',
  'BLOCKED', 'STALE']);
const ENVELOPE_REQUIRED = ['event_id', 'type', 'appended_at', 'seq', 'payload'] as const;
const ENVELOPE_KEYS: ReadonlySet<string> = new Set([...ENVELOPE_REQUIRED, 'task_id', 'fencing_token', 'corrects']);
const FACT_KINDS: ReadonlySet<string> = new Set(['claim', 'observation', 'interpretation', 'authority']);
const SOURCE_CLASSES: ReadonlySet<string> = new Set([
  'agent_declared', 'same_lineage_review', 'deterministic_tool_local', 'deterministic_tool_external_ci',
  'cross_vendor_review', 'decision_agent', 'human_authority', 'delegate_ai']);
const OUTCOMES: ReadonlySet<string> = new Set(['pass', 'fail', 'blocking']);
const BLOCKING_KINDS: ReadonlySet<string> = new Set(['out_of_scope', 'forbidden_path', 'violation', 'constitution', 'other']);
const BINDING_KINDS: ReadonlySet<string> = new Set(['contract', 'acceptance', 'change_request', 'baseline']);
const RECORD_REQUIRED = ['record_id', 'fact_kind', 'source_class', 'recorder', 'subject'] as const;
const RECORD_KEYS: ReadonlySet<string> = new Set([
  ...RECORD_REQUIRED, 'evidence_type', 'dimension', 'gate', 'outcome', 'blocking_kind', 'commit', 'intent_versions',
  'approval_binding', 'decision_ref', 'models', 'basis', 'stands_for', 'refers_to', 'risk_class', 'evidence_profile']);
const AUDIT_COPY_TYPES = ['risk_class', 'evidence_profile'] as const;
const AUDIT_COPY_SOURCES: ReadonlySet<string> = new Set(['deterministic_tool_local', 'deterministic_tool_external_ci']);
const AUDIT_COPY_FORBIDDEN = ['outcome', 'gate', 'blocking_kind', 'dimension'] as const;
const RISK_CLASSES: ReadonlySet<string> = new Set(['low', 'medium', 'high', 'critical']);
const ACCEPTANCE_DECISIONS: ReadonlySet<string> = new Set([
  'ACCEPT', 'NEEDS_REVIEW', 'INSUFFICIENT_EVIDENCE', 'NEEDS_REWORK', 'REJECT']);
const EXECUTION_DECISIONS: ReadonlySet<string> = new Set([
  'CONTINUE', 'CONTINUE_WITH', 'REPLAN', 'STOP: scope invalid', 'STOP: runtime insufficient', 'STOP: violation',
  'BLOCKED', 'ESCALATE']);
const ACCEPTANCE_KEYS: ReadonlySet<string> = new Set([
  'task_content_hash', 'evaluated_commit', 'intent_versions', 'next_task_state', 'table_row', 'profile_used',
  'missing_gates', 'blocking', 'failed_gates', 'reverify', 'approval_record', 'policy_version', 'level_version',
  'governor_identity', 'ruleset_version', 'scenario_set_hash', 'uncovered', 'rests_on_ai']);
const PROFILE_KEYS = ['dimension', 'required', 'satisfied_by', 'missing_types'] as const;
const EXECUTION_KEYS: ReadonlySet<string> = new Set([
  'contract_hash', 'contract_version', 'base_commit', 'head_commit', 'log_seq', 'delta', 'checks',
  'outcomes_fired', 'read_set', 'signatures', 'intent_versions', 'dependencies', 'constitution', 'runtime',
  'budgets', 'policy_version', 'engine_identity', 'uncovered', 'state_effect']);
const EXECUTION_ORDER = ['STOP: violation', 'STOP: scope invalid', 'STOP: runtime insufficient', 'ESCALATE', 'BLOCKED',
  'REPLAN', 'CONTINUE_WITH'] as const;
const CHECK_KEYS = ['check', 'status', 'outcome', 'detail'] as const;
const CHECK_STATUSES: ReadonlySet<string> = new Set(['passed', 'fired', 'skipped', 'not_run']);
const RECORD_PAYLOAD_TYPES: ReadonlySet<string> = new Set([
  'record.added', 'violation.detected', 'decision.acceptance', 'decision.execution']);
const DECISION_TYPES: ReadonlySet<string> = new Set(['decision.acceptance', 'decision.execution']);

const TIME = /^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?Z$/;
const HASH = /^[0-9a-f]{64}$/;
const COMMIT = /^(?:[0-9a-f]{40}|[0-9a-f]{64})$/;
const VERSION = /^v[0-9]+$/;
export const TASK = /^TASK-[0-9]+$/;
const CHANGE = /^CHG-[0-9]+$/;
const GATE = /^G[0-9]+$/;
const PYTHON = /^[0-9]+\.[0-9]+\.[0-9]+$/;

export function matches(re: RegExp, v: V | undefined): boolean {
  return typeof v === 'string' && re.test(v);
}

function inSet(values: ReadonlySet<string>, v: V | undefined): boolean {
  return typeof v === 'string' && values.has(v);
}

function isStrList(v: V | undefined): boolean {
  return isList(v) && v.every((x) => isStr(x));
}

/** Python's "value != text" for a text: true unless the value is that same string. */
function differs(v: V | undefined, text: string): boolean {
  return !(typeof v === 'string' && v === text);
}

function daysInMonth(y: number, m: number): number {
  if (m === 2) return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0 ? 29 : 28;
  return [4, 6, 9, 11].includes(m) ? 30 : 31;
}

/** _is_time: a UTC time of section 6.1 that exists on the calendar (datetime(...) accepts it). */
function isTime(v: V | undefined): boolean {
  if (typeof v !== 'string') return false;
  const m = TIME.exec(v);
  if (m === null) return false;
  const [y, mo, d, h, mi, s] = m.slice(1, 7).map((x) => Number(x)) as [number, number, number, number, number, number];
  return y >= 1 && mo >= 1 && mo <= 12 && d >= 1 && d <= daysInMonth(y, mo) && h <= 23 && mi <= 59 && s <= 59;
}

// ---------------------------------------------------------------------------------------------------------------
// The payload forms of section 6.3

type Form = [(v: V) => boolean, string];
const VERSION_FORM: Form = [(v) => matches(VERSION, v), 'v followed by digits'];
const HASH_FORM: Form = [(v) => matches(HASH, v), '64 lowercase hex digits'];
const STR_FORM: Form = [(v) => isStr(v), 'a non-empty string'];
const LIST_FORM: Form = [(v) => isStrList(v), 'a list of non-empty strings (reading: section 6.3 says lists of strings)'];
const COMMIT_FORM: Form = [(v) => matches(COMMIT, v), 'a full lowercase hex commit id'];
const BOOL_FORM: Form = [(v) => typeof v === 'boolean', 'true or false'];

function oneOf(...values: string[]): Form {
  const set = new Set(values);
  return [(v) => inSet(set, v), 'one of ' + values.join(', ')];
}

const PAYLOAD_FORMS: ReadonlyMap<string, ReadonlyMap<string, Form>> = new Map<string, ReadonlyMap<string, Form>>([
  ['task.drafted', new Map([['contract_version', VERSION_FORM], ['contract_hash', HASH_FORM]])],
  ['task.approved', new Map([['contract_version', VERSION_FORM], ['contract_hash', HASH_FORM],
    ['approval_record', STR_FORM]])],
  ['task.blocked', new Map([['reason', STR_FORM], ['blocked_by', LIST_FORM]])],
  ['task.unblocked', new Map([['reason', STR_FORM]])],
  ['task.submitted', new Map([['commit', COMMIT_FORM], ['compensating', BOOL_FORM]])],
  ['task.done', new Map([['decision_record', STR_FORM]])],
  ['task.stale', new Map([['cause', oneOf('intent_change', 'conflict')], ['refers_to', STR_FORM]])],
  ['task.replanned', new Map([['contract_version', VERSION_FORM], ['contract_hash', HASH_FORM]])],
  ['intent.changed', new Map([['entity', STR_FORM], ['from_version', VERSION_FORM], ['to_version', VERSION_FORM],
    ['change_request', [(v: V) => matches(CHANGE, v), 'CHG- followed by digits'] as Form]])],
  ['drift.detected', new Map([['paths', LIST_FORM], ['entities', LIST_FORM]])],
  ['evidence.stale', new Map([['records', LIST_FORM], ['reason', oneOf('commit', 'intent_version')]])],
]);

function keysAndForms(obj: VObj, forms: ReadonlyMap<string, Form>, rule: string, where: string): Finding[] {
  const f: Finding[] = [];
  for (const key of sortedStrs([...obj.keys()].filter((k) => !forms.has(k)))) {
    f.push(F(rule + ':unknown_key', where + ' has the key ' + reprStr(key) + ', which section 6.3 does not name'));
  }
  for (const key of sortedStrs(forms.keys())) {
    if (!obj.has(key)) {
      f.push(F(rule + ':missing_key', where + ' lacks ' + reprStr(key)));
      continue;
    }
    const [test, text] = forms.get(key) as Form;
    if (!test(get(obj, key))) f.push(F(rule + ':' + key, where + ' ' + reprStr(key) + ' is not ' + text));
  }
  return f;
}

// ---------------------------------------------------------------------------------------------------------------
// check_record

function isIntentVersions(v: V): boolean {
  if (!isDict(v)) return false;
  for (const [k, x] of v) if (!(k !== '' && matches(VERSION, x))) return false;
  return true;
}

export function checkRecord(record: V, extraKeys: ReadonlySet<string> = new Set(), where: string = 'record',
  section: string = '6.2'): Finding[] {
  if (!isDict(record)) return [F('6.2:record', where + ' is not a JSON object')];
  const r = record;
  const f: Finding[] = [];
  const names = section === '6.2' ? 'section 6.2 does not name' : 'sections 6.2 and ' + section + ' do not name';
  for (const key of sortedStrs([...r.keys()].filter((k) => !RECORD_KEYS.has(k) && !extraKeys.has(k)))) {
    f.push(F(section + ':unknown_key', where + ' has the key ' + reprStr(key) + ', which ' + names));
  }
  for (const key of RECORD_REQUIRED) {
    if (!r.has(key)) f.push(F('6.2:missing_key', where + ' lacks ' + reprStr(key) + ' (reading: required)'));
  }
  for (const key of ['record_id', 'recorder', 'subject']) {
    if (r.has(key) && !isStr(get(r, key))) {
      f.push(F('6.2:' + key, where + ' ' + reprStr(key) + ' is not a non-empty string'));
    }
  }
  if (r.has('fact_kind') && !inSet(FACT_KINDS, get(r, 'fact_kind'))) {
    f.push(F('6.2:fact_kind', where + ' fact_kind is not claim, observation, interpretation or authority'));
  }
  if (r.has('source_class') && !inSet(SOURCE_CLASSES, get(r, 'source_class'))) {
    f.push(F('6.2:source_class', where + ' source_class is not one of the classes of DM B3'));
  }
  // _check_outcome
  const outcome = get(r, 'outcome');
  if (r.has('outcome') && !inSet(OUTCOMES, outcome)) {
    f.push(F('6.2:outcome', where + ' outcome is not pass, fail or blocking'));
  }
  if (outcome === 'blocking' && !r.has('blocking_kind')) {
    f.push(F('6.2:blocking_kind', where + ' has outcome blocking but no blocking_kind'));
  }
  if (outcome !== 'blocking' && r.has('blocking_kind')) {
    f.push(F('6.2:blocking_kind', where + ' has blocking_kind without outcome blocking'));
  }
  if (r.has('blocking_kind') && !inSet(BLOCKING_KINDS, get(r, 'blocking_kind'))) {
    f.push(F('6.2:blocking_kind', where + ' blocking_kind is not one of ' + sortedStrs(BLOCKING_KINDS).join(', ')));
  }
  if (r.has('commit') && !matches(COMMIT, get(r, 'commit'))) {
    f.push(F('6.2:commit', where + ' commit is not a full lowercase hex commit id'));
  }
  if (r.has('intent_versions') && !isIntentVersions(get(r, 'intent_versions'))) {
    f.push(F('6.2:intent_versions', where + ' intent_versions does not map ids to versions v<digits>'));
  }
  // _check_binding
  if (!r.has('approval_binding')) {
    if (get(r, 'fact_kind') === 'authority') {
      f.push(F('6.2:approval_binding', where + ' is an authority record without approval_binding'));
    }
  } else {
    const b = get(r, 'approval_binding');
    if (!(isDict(b) && keysAre(b, ['kind', 'hash']) && inSet(BINDING_KINDS, get(b, 'kind'))
          && matches(HASH, get(b, 'hash')))) {
      f.push(F('6.2:approval_binding', where + ' approval_binding is not {kind, hash} with kind contract, acceptance, '
        + 'change_request or baseline and a 64-hex hash'));
    }
  }
  // _check_review_fields
  const kind = get(r, 'evidence_type');
  const needsRef = get(r, 'source_class') === 'decision_agent' || kind === 'other_model_review';
  if (needsRef && !r.has('decision_ref')) {
    f.push(F('6.2:decision_ref', where + ' needs decision_ref (a decision_agent record or an other_model_review)'));
  }
  if (r.has('decision_ref') && !isStr(get(r, 'decision_ref'))) {
    f.push(F('6.2:decision_ref', where + ' decision_ref is not a non-empty string'));
  }
  if (kind === 'other_model_review' && !r.has('models')) {
    f.push(F('6.2:models', where + ' is an other_model_review without models'));
  }
  if (r.has('models')) {
    const m = get(r, 'models');
    if (!(isDict(m) && keysAre(m, ['reviewer', 'implementer']) && isStr(get(m, 'reviewer'))
          && isStr(get(m, 'implementer')))) {
      f.push(F('6.2:models', where + ' models is not {reviewer, implementer} with non-empty strings'));
    }
  }
  if (kind === 'decision_agent_review') {
    for (const key of ['basis', 'stands_for']) {
      if (!r.has(key)) f.push(F('6.2:' + key, where + ' is a decision_agent_review without ' + key));
    }
  }
  if (r.has('basis')) {
    const basis = get(r, 'basis');
    if (!(isStr(basis) || (isStrList(basis) && isList(basis) && basis.length > 0))) {
      f.push(F('6.2:basis', where + ' basis is not a non-empty string or list of strings (reading)'));
    }
  }
  if (r.has('stands_for') && !isStr(get(r, 'stands_for'))) {
    f.push(F('6.2:stands_for', where + ' stands_for is not a non-empty string'));
  }
  if (r.has('gate') && !matches(GATE, get(r, 'gate'))) {
    f.push(F('6.2:gate', where + ' gate is not G followed by digits'));
  }
  for (const key of ['evidence_type', 'dimension', 'refers_to']) {
    if (r.has(key) && !isStr(get(r, key))) {
      f.push(F('6.2:' + key, where + ' ' + reprStr(key) + ' is not a non-empty string'));
    }
  }
  f.push(...checkAuditCopy(r, where));
  return f;
}

function isAuditValue(kind: string, v: V): boolean {
  if (v === null) return true;
  if (kind === 'risk_class') return inSet(RISK_CLASSES, v);
  return isList(v) && v.every((e) => isDict(e) && keysAre(e, ['dimension', 'evidence_types'])
    && isStr(get(e, 'dimension')) && isStrList(get(e, 'evidence_types')));
}

function checkAuditCopy(r: VObj, where: string): Finding[] {
  const f: Finding[] = [];
  const kind = get(r, 'evidence_type');
  if (!(kind === 'risk_class' || kind === 'evidence_profile')) {
    for (const key of AUDIT_COPY_TYPES) {
      if (r.has(key)) {
        f.push(F('6.2:audit_copy_key', where + ' carries ' + reprStr(key) + ', but its evidence_type is not '
          + reprStr(key)));
      }
    }
    return f;
  }
  const other = kind === AUDIT_COPY_TYPES[0] ? AUDIT_COPY_TYPES[1] : AUDIT_COPY_TYPES[0];
  if (get(r, 'fact_kind') !== 'observation') {
    f.push(F('6.2:audit_copy_fact_kind', where + ' is an audit copy whose fact_kind is not observation'));
  }
  if (!inSet(AUDIT_COPY_SOURCES, get(r, 'source_class'))) {
    f.push(F('6.2:audit_copy_source_class', where + ' is an audit copy whose source_class is neither '
      + 'deterministic_tool_local nor deterministic_tool_external_ci'));
  }
  if (!r.has(kind)) {
    f.push(F('6.2:audit_copy_key', where + ' is a ' + kind + ' audit copy that lacks its key ' + reprStr(kind)));
  } else if (!isAuditValue(kind, get(r, kind))) {
    f.push(F('6.2:audit_copy_value', where + ' ' + reprStr(kind) + ' is not null or a value of its form'));
  }
  if (r.has(other)) {
    f.push(F('6.2:audit_copy_key', where + ' is a ' + kind + ' audit copy that carries ' + reprStr(other)));
  }
  for (const key of ['commit', 'intent_versions']) {
    if (!r.has(key)) f.push(F('6.2:audit_copy_binding', where + ' is an audit copy that lacks ' + reprStr(key)));
  }
  for (const key of AUDIT_COPY_FORBIDDEN) {
    if (r.has(key)) f.push(F('6.2:audit_copy_forbidden', where + ' is an audit copy that carries ' + reprStr(key)));
  }
  return f;
}

// ---------------------------------------------------------------------------------------------------------------
// check_decision

function isProfile(v: V): boolean {
  return isList(v) && v.every((item) => isDict(item) && keysAre(item, PROFILE_KEYS));
}

function isChecks(v: V): boolean {
  if (!(isList(v) && v.length === 8)) return false;
  const seen: number[] = [];
  for (const item of v) {
    if (!(isDict(item) && keysAre(item, CHECK_KEYS))) return false;
    const check = get(item, 'check');
    if (!isInt(check, 1) || Number(check) > 8 || !inSet(CHECK_STATUSES, get(item, 'status'))) return false;
    if (get(item, 'status') === 'fired') {
      if (!inSet(EXECUTION_DECISIONS, get(item, 'outcome'))) return false;
    } else if (get(item, 'outcome') !== null) {
      return false;
    }
    if (typeof get(item, 'detail') !== 'string') return false;
    seen.push(Number(check));
  }
  seen.sort((a, b) => a - b);
  return seen.every((x, k) => x === k + 1);
}

function checkExecutionKeys(payload: VObj, where: string): Finding[] {
  const f: Finding[] = [];
  const bad = (key: string, text: string): void => {
    f.push(F('6.4:' + key, where + ' ' + key + ' is not ' + text));
  };
  for (const key of ['base_commit', 'head_commit']) {
    if (payload.has(key) && !matches(COMMIT, get(payload, key))) bad(key, 'a full lowercase hex commit id');
  }
  if (payload.has('log_seq') && !isInt(get(payload, 'log_seq'), 0)) bad('log_seq', 'an integer at least 0');
  if (payload.has('contract_hash') && !matches(HASH, get(payload, 'contract_hash'))) {
    bad('contract_hash', '64 lowercase hex digits');
  }
  if (payload.has('contract_version') && !matches(VERSION, get(payload, 'contract_version'))) {
    bad('contract_version', 'v followed by digits');
  }
  if (payload.has('engine_identity')) {
    const ident = get(payload, 'engine_identity');
    if (!(isDict(ident) && keysAre(ident, ['code_sha256', 'python'])
          && (get(ident, 'code_sha256') === null || matches(HASH, get(ident, 'code_sha256')))
          && matches(PYTHON, get(ident, 'python')))) {
      bad('engine_identity', 'an object with exactly code_sha256 (null or 64 lowercase hex digits) and python '
        + '(X.Y.Z)');
    }
  }
  if (payload.has('checks') && !isChecks(get(payload, 'checks'))) {
    bad('checks', 'eight objects with exactly check (1 to 8, each once), status, outcome and detail');
  }
  if (payload.has('outcomes_fired')) {
    const fired = get(payload, 'outcomes_fired');
    const order: readonly string[] = EXECUTION_ORDER;
    let good = isList(fired) && fired.every((x) => typeof x === 'string' && order.includes(x));
    if (good) {
      const items = fired as string[];
      good = new Set(items).size === items.length;
      if (good) {
        for (let k = 1; k < items.length; k++) {
          if (order.indexOf(items[k] as string) < order.indexOf(items[k - 1] as string)) good = false;
        }
      }
    }
    if (!good) {
      bad('outcomes_fired', 'a list of fired execution values without repeats in the order of section 7');
    } else {
      const items = fired as string[];
      const decision = get(payload, 'decision');
      if (decision !== null && differs(decision, items.length > 0 ? items[0] as string : 'CONTINUE')) {
        bad('outcomes_fired', 'a list whose first value is the decision (CONTINUE when it is empty)');
      }
    }
  }
  if (payload.has('policy_version')) {
    const pv = get(payload, 'policy_version');
    if (!(pv === null || isStr(pv))) bad('policy_version', 'a non-empty string or null');
  }
  if (payload.has('intent_versions')) {
    const iv = get(payload, 'intent_versions');
    let other = false;
    if (isDict(iv)) {
      other = true;
      for (const [k, v] of iv) {
        if (!(k !== '' && isDict(v) && keysAre(v, ['contract', 'current'])
              && [...v.values()].every((x) => x === null || isStr(x)))) {
          other = false;
          break;
        }
      }
    }
    if (!(isIntentVersions(iv) || other)) {
      bad('intent_versions', 'in the record form or an object mapping each entry to exactly {contract, current} '
        + '(reading)');
    }
  }
  for (const key of ['delta', 'signatures', 'uncovered', 'state_effect']) {
    if (payload.has(key) && !isList(get(payload, key))) bad(key, 'a list');
  }
  for (const key of ['read_set', 'dependencies', 'constitution', 'runtime', 'budgets']) {
    if (payload.has(key) && !isDict(get(payload, key))) bad(key, 'an object');
  }
  return f;
}

function checkDecision(eventType: string, payload: VObj, where: string): Finding[] {
  const acceptance = eventType === 'decision.acceptance';
  const extra = new Set<string>(['decision', 'error', ...(acceptance ? ACCEPTANCE_KEYS : EXECUTION_KEYS)]);
  let viewed: VObj = payload;
  if (!acceptance && payload.has('intent_versions')) {
    viewed = new Map([...payload].filter(([k]) => k !== 'intent_versions'));
  }
  const f = checkRecord(viewed, extra, where, '6.4');
  if (!acceptance) f.push(...checkExecutionKeys(payload, where));
  if (!payload.has('decision')) {
    f.push(F('6.4:decision', where + ' lacks decision'));
    return f;
  }
  const decision = get(payload, 'decision');
  const hasError = payload.has('error');
  if ((decision === null) !== hasError) {
    f.push(F('6.4:error', where + ' decision must be null exactly when error is present'));
  }
  if (hasError && !isStr(get(payload, 'error'))) {
    f.push(F('6.4:error', where + ' error is not a non-empty string (reading)'));
  }
  const allowed = acceptance ? ACCEPTANCE_DECISIONS : EXECUTION_DECISIONS;
  if (decision !== null && !inSet(allowed, decision)) {
    f.push(F('6.4:decision', where + ' decision ' + pyRepr(decision) + ' is not one of the ' + allowed.size + ' '
      + (acceptance ? 'acceptance' : 'execution') + ' values'));
  }
  const subject = get(payload, 'subject');
  if (payload.has('subject') && isStr(subject) && !matches(TASK, subject)) {
    f.push(F('6.4:subject', where + ' subject is not a task id (reading: TASK- followed by digits)'));
  }
  if (acceptance) {
    if (payload.has('task_content_hash') && !matches(HASH, get(payload, 'task_content_hash'))) {
      f.push(F('6.4:task_content_hash', where + ' task_content_hash is not 64 lowercase hex digits'));
    }
    if (payload.has('evaluated_commit') && !matches(COMMIT, get(payload, 'evaluated_commit'))) {
      f.push(F('6.4:evaluated_commit', where + ' evaluated_commit is not a full lowercase hex commit id'));
    }
    if (payload.has('fact_kind') && differs(get(payload, 'fact_kind'), 'interpretation')) {
      f.push(F('6.4:fact_kind', where + ' fact_kind is not interpretation'));
    }
    if (payload.has('next_task_state') && !inSet(STATE_NAMES, get(payload, 'next_task_state'))) {
      f.push(F('6.4:next_task_state', where + ' next_task_state is not a state name of section 2'));
    }
    if (payload.has('profile_used') && !isProfile(get(payload, 'profile_used'))) {
      f.push(F('6.4:profile_used', where + ' profile_used is not a list of objects with exactly '
        + 'dimension, required, satisfied_by and missing_types'));
    }
  }
  return f;
}

// ---------------------------------------------------------------------------------------------------------------
// check_payload and _check_fence

/** check_payload(event_type, payload): an event_type that Python cannot hash (a list or an object) raises its
 * TypeError there, which fails closed. */
export function checkPayload(eventType: V, payload: V, where: string = 'payload'): Finding[] {
  if (isList(eventType) || isDict(eventType)) throw new R2Fail('an event_type that Python cannot hash');
  if (!(typeof eventType === 'string' && EVENT_TYPES.has(eventType))) {
    return [F('6.3:type', pyRepr(eventType) + ' is not an event type of section 6.3')];
  }
  if (!isDict(payload)) return [F('6.1:payload', where + ' is not a JSON object')];
  if (DECISION_TYPES.has(eventType)) return checkDecision(eventType, payload, where);
  if (eventType === 'record.added') return checkRecord(payload, new Set(), where);
  if (eventType === 'violation.detected') {
    const f = checkRecord(payload, new Set(), where);
    for (const [key, want] of [['fact_kind', 'observation'], ['outcome', 'blocking'], ['blocking_kind', 'violation']]) {
      if (differs(get(payload, key as string), want as string)) {
        f.push(F('6.3:violation', where + ' ' + key + ' is not ' + want));
      }
    }
    return f;
  }
  if (eventType === 'conflict.detected') {
    const forms = new Map<string, Form>([['tasks', LIST_FORM]]);
    for (const key of ['paths', 'interfaces']) if (payload.has(key)) forms.set(key, LIST_FORM);
    const f = keysAndForms(payload, forms, '6.3', where);
    if (!payload.has('paths') && !payload.has('interfaces')) {
      f.push(F('6.3:missing_key', where + ' has neither paths nor interfaces'));
    }
    return f;
  }
  return keysAndForms(payload, PAYLOAD_FORMS.get(eventType) as ReadonlyMap<string, Form>, '6.3', where);
}

/** _check_fence(obj, event_type). */
export function checkFence(obj: VObj, eventType: string | null): Finding[] {
  if (!obj.has('fencing_token')) {
    if (eventType === 'task.submitted') return [F('6.1:fencing_token', 'task.submitted lacks fencing_token')];
    return [];
  }
  const t = get(obj, 'fencing_token');
  const ok = isDict(t) && keysAre(t, ['epoch', 'counter']) && isInt(get(t, 'counter'), 0)
    && (isStr(get(t, 'epoch')) || isInt(get(t, 'epoch'), 0));
  if (!ok) {
    return [F('6.1:fencing_token', 'fencing_token is not {epoch, counter} with counter an integer of 0 or '
      + 'more and epoch a non-empty string or an integer of 0 or more (reading)')];
  }
  return [];
}

function checkTaskId(obj: VObj, eventType: string, payload: V): Finding[] {
  const f: Finding[] = [];
  const has = obj.has('task_id');
  const taskId = get(obj, 'task_id');
  if (has && !matches(TASK, taskId)) f.push(F('6.1:task_id', 'task_id is not TASK- followed by digits (reading)'));
  const subject = RECORD_PAYLOAD_TYPES.has(eventType) && isDict(payload) ? get(payload, 'subject') : null;
  const subjectIsTask = matches(TASK, subject);
  const needed = eventType.startsWith('task.') || eventType.startsWith('decision.') || subjectIsTask;
  if (needed && !has) f.push(F('6.1:task_id', eventType + ' lacks task_id'));
  if (has && subjectIsTask && differs(taskId, subject as string)) {
    f.push(F('6.1:task_id', 'task_id differs from the record subject ' + pyRepr(subject)));
  }
  if (has && (eventType === 'record.added' || eventType === 'violation.detected') && isStr(subject) && !subjectIsTask) {
    f.push(F('6.1:task_id', 'a record about an intent entity carries task_id (reading)'));
  }
  return f;
}

// ---------------------------------------------------------------------------------------------------------------
// check_log

export class LineReport {
  readonly number: number;
  readonly event: VObj | null;
  readonly findings: readonly Finding[];
  readonly duplicateOf: number | null;
  constructor(number: number, event: VObj | null, findings: Finding[], duplicateOf: number | null = null) {
    this.number = number;
    this.findings = findings;
    this.event = findings.length > 0 ? null : event;
    this.duplicateOf = duplicateOf;
  }
}

export class LogReport {
  readonly textFindings: readonly Finding[];
  readonly lines: readonly LineReport[];
  constructor(textFindings: Finding[], lines: LineReport[]) {
    this.textFindings = textFindings;
    this.lines = lines;
  }
  /** Every finding, the text's first, then each line's. */
  findings(): Finding[] {
    const out: Finding[] = [...this.textFindings];
    for (const line of this.lines) out.push(...line.findings);
    return out;
  }
}

class LogState {
  previousSeq: bigint | null = null;
  firstLine: Map<string, [number, string | null]> = new Map();
}

function intOf(v: V): bigint {
  return typeof v === 'bigint' ? v : BigInt(v as number);
}

/** _int_text: '%d' for an integer of at most 64 bits. */
function intText(n: bigint): string {
  const a = n < 0n ? -n : n;
  const bits = a === 0n ? 0 : a.toString(2).length;
  return bits <= 64 ? n.toString() : 'an integer of ' + bits + ' bits';
}

function checkSeq(obj: VObj, number: number, state: LogState): Finding[] {
  const seq = get(obj, 'seq');
  const expected = state.previousSeq === null ? BigInt(number) : state.previousSeq + 1n;
  state.previousSeq = isInt(seq) ? intOf(seq) : null;
  if (!obj.has('seq')) return [];
  if (!isInt(seq)) return [F('6.1:seq', 'seq is not an integer')];
  if (intOf(seq) !== expected) {
    return [F('6.1:seq', 'seq is ' + intText(intOf(seq)) + '; expected ' + intText(expected))];
  }
  return [];
}

/** _without_order: the line without seq and appended_at as JSON text (here compact; only equality is used). */
function withoutOrder(obj: VObj): string | null {
  const m: VObj = new Map([...obj].filter(([k]) => k !== 'seq' && k !== 'appended_at'));
  return dumps(m, true);
}

function checkLine(number: number, raw: string, state: LogState): LineReport {
  let obj: V;
  try {
    obj = pyLoads(raw);
  } catch (e) {
    if (e instanceof PyMalformed) {
      state.previousSeq = null;
      return new LineReport(number, null, [F('6.1:json', 'the line is not one JSON object (' + e.message + ')')]);
    }
    throw e;
  }
  if (!isDict(obj)) {
    // "the line is a JSON <type>, not an object" names a Python type: fail closed (brief section 6.3).
    throw new R2Fail('a log line that is a JSON value other than an object');
  }
  const f: Finding[] = [];
  for (const key of ENVELOPE_REQUIRED) {
    if (!obj.has(key)) f.push(F('6.1:missing_key', 'the line lacks ' + reprStr(key)));
  }
  for (const key of sortedStrs([...obj.keys()].filter((k) => !ENVELOPE_KEYS.has(k)))) {
    f.push(F('2:unknown_key', 'the line has the key ' + reprStr(key) + ', which section 6.1 does not name'));
  }
  const eventId = get(obj, 'event_id');
  if (obj.has('event_id') && !isStr(eventId)) f.push(F('6.1:event_id', 'event_id is not a non-empty string'));
  const eventType = get(obj, 'type');
  const knownType = typeof eventType === 'string' && EVENT_TYPES.has(eventType);
  if (obj.has('type') && !knownType) f.push(F('6.1:type', 'type is not an event type of section 6.3'));
  const payload = get(obj, 'payload');
  if (obj.has('payload') && !isDict(payload)) f.push(F('6.1:payload', 'payload is not a JSON object'));
  f.push(...checkSeq(obj, number, state));
  if (obj.has('appended_at') && !isTime(get(obj, 'appended_at'))) {
    f.push(F('6.1:appended_at', 'appended_at is not a UTC time YYYY-MM-DDTHH:MM:SS[.fraction]Z '
      + 'that exists on the calendar'));
  }
  let duplicateOf: number | null = null;
  const key = withoutOrder(obj);
  if (key === null) {
    f.push(F('6.1:json', 'the line cannot be written back as JSON text to compare it with other lines'));
  }
  if (isStr(eventId) && state.firstLine.has(eventId)) {
    const [first, earlier] = state.firstLine.get(eventId) as [number, string | null];
    if (key !== null && key === earlier) {
      duplicateOf = first;
    } else {
      f.push(F('6.1:duplicate_event_id', 'event_id ' + reprStr(eventId) + ' is on line ' + first + ' with other '
        + 'content (reading: only an identical repeat is an ignored duplicate)'));
    }
  }
  if (knownType) {
    f.push(...checkTaskId(obj, eventType as string, payload));
    f.push(...checkFence(obj, eventType as string));
  } else if (obj.has('fencing_token')) {
    f.push(...checkFence(obj, null));
  }
  if (obj.has('corrects')) {
    const corrects = get(obj, 'corrects');
    if (!(isStr(corrects) && state.firstLine.has(corrects))) {
      f.push(F('6.1:corrects', 'corrects is not the event_id of an earlier line (reading)'));
    }
  }
  if (knownType && isDict(payload)) f.push(...checkPayload(eventType as string, payload));
  if (isStr(eventId) && !state.firstLine.has(eventId)) state.firstLine.set(eventId, [number, key]);
  return new LineReport(number, obj, f, duplicateOf);
}

/** check_log over a log given as text whose characters are its bytes (every log of round 2 is ASCII). */
export function checkLog(raw: string): LogReport {
  const textFindings: Finding[] = [];
  if (raw.startsWith('\xef\xbb\xbf')) textFindings.push(F('2:bom', 'the text starts with a byte-order mark'));
  if (raw.includes('\r')) textFindings.push(F('2:cr', 'the text holds a CR byte; line ends are LF only'));
  const parts = raw.split('\n');
  if (parts[parts.length - 1] === '') parts.pop();
  const state = new LogState();
  return new LogReport(textFindings, parts.map((part, k) => checkLine(k + 1, part, state)));
}

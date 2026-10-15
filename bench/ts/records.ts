// The record forms of records.py that the governor uses: check_record (with check_audit_copy) and the state names and
// blocking kinds. Only each finding's rule is kept, since the governor reads only the first finding's rule and whether
// there is any.

import type { J, JObj } from './json.ts';
import { isObj, isList, pget, keySetIs, sortStrs } from './json.ts';

export const STATE_NAMES: ReadonlySet<string> = new Set([
  'DRAFT', 'READY', 'IN_PROGRESS', 'VERIFYING', 'ACCEPTED', 'DONE', 'IN_REVIEW', 'REWORK', 'ESCALATED', 'REJECTED',
  'BLOCKED', 'STALE']);
const FACT_KINDS: ReadonlySet<string> = new Set(['claim', 'observation', 'interpretation', 'authority']);
const SOURCE_CLASSES: ReadonlySet<string> = new Set([
  'agent_declared', 'same_lineage_review', 'deterministic_tool_local', 'deterministic_tool_external_ci',
  'cross_vendor_review', 'decision_agent', 'human_authority', 'delegate_ai']);
const OUTCOMES: ReadonlySet<string> = new Set(['pass', 'fail', 'blocking']);
export const BLOCKING_KINDS: ReadonlySet<string> = new Set([
  'out_of_scope', 'forbidden_path', 'violation', 'constitution', 'other']);
const BINDING_KINDS: ReadonlySet<string> = new Set(['contract', 'acceptance', 'change_request', 'baseline']);
const RECORD_REQUIRED = ['record_id', 'fact_kind', 'source_class', 'recorder', 'subject'] as const;
const RECORD_KEYS: ReadonlySet<string> = new Set([
  ...RECORD_REQUIRED, 'evidence_type', 'dimension', 'gate', 'outcome', 'blocking_kind', 'commit', 'intent_versions',
  'approval_binding', 'decision_ref', 'models', 'basis', 'stands_for', 'refers_to', 'risk_class', 'evidence_profile']);
const AUDIT_COPY_TYPES = ['risk_class', 'evidence_profile'] as const;
const AUDIT_COPY_SOURCES: ReadonlySet<string> = new Set(['deterministic_tool_local', 'deterministic_tool_external_ci']);
const AUDIT_COPY_FORBIDDEN = ['outcome', 'gate', 'blocking_kind', 'dimension'] as const;
const RISK_CLASSES: ReadonlySet<string> = new Set(['low', 'medium', 'high', 'critical']);

const HASH = /^[0-9a-f]{64}$/;
const COMMIT = /^(?:[0-9a-f]{40}|[0-9a-f]{64})$/;
const VERSION = /^v[0-9]+$/;
const GATE = /^G[0-9]+$/;

function isStr(v: J): boolean {
  return typeof v === 'string' && v !== '';
}

function matches(re: RegExp, v: J): boolean {
  return typeof v === 'string' && re.test(v);
}

function inSet(values: ReadonlySet<string>, v: J): boolean {
  return typeof v === 'string' && values.has(v);
}

function isStrList(v: J): boolean {
  return isList(v) && v.every((x) => isStr(x));
}

function isIntentVersions(v: J): boolean {
  if (!isObj(v)) return false;
  for (const [k, x] of v) {
    if (!(k !== '' && matches(VERSION, x))) return false;
  }
  return true;
}

/** The rules of check_record's findings for one record, in its order (records.py check_record, section 6.2). */
export function checkRecord(record: J): string[] {
  if (!isObj(record)) return ['6.2:record'];
  const r: JObj = record;
  const f: string[] = [];
  for (const _k of sortStrs([...r.keys()].filter((k) => !RECORD_KEYS.has(k)))) f.push('6.2:unknown_key');
  for (const k of RECORD_REQUIRED) if (!r.has(k)) f.push('6.2:missing_key');
  for (const k of ['record_id', 'recorder', 'subject']) {
    if (r.has(k) && !isStr(pget(r, k))) f.push('6.2:' + k);
  }
  if (r.has('fact_kind') && !inSet(FACT_KINDS, pget(r, 'fact_kind'))) f.push('6.2:fact_kind');
  if (r.has('source_class') && !inSet(SOURCE_CLASSES, pget(r, 'source_class'))) f.push('6.2:source_class');
  // _check_outcome
  const outcome = pget(r, 'outcome');
  if (r.has('outcome') && !inSet(OUTCOMES, outcome)) f.push('6.2:outcome');
  if (outcome === 'blocking' && !r.has('blocking_kind')) f.push('6.2:blocking_kind');
  if (outcome !== 'blocking' && r.has('blocking_kind')) f.push('6.2:blocking_kind');
  if (r.has('blocking_kind') && !inSet(BLOCKING_KINDS, pget(r, 'blocking_kind'))) f.push('6.2:blocking_kind');
  if (r.has('commit') && !matches(COMMIT, pget(r, 'commit'))) f.push('6.2:commit');
  if (r.has('intent_versions') && !isIntentVersions(pget(r, 'intent_versions'))) f.push('6.2:intent_versions');
  // _check_binding
  if (!r.has('approval_binding')) {
    if (pget(r, 'fact_kind') === 'authority') f.push('6.2:approval_binding');
  } else {
    const b = pget(r, 'approval_binding');
    if (!(isObj(b) && keySetIs(b, ['kind', 'hash']) && inSet(BINDING_KINDS, pget(b, 'kind'))
          && matches(HASH, pget(b, 'hash')))) {
      f.push('6.2:approval_binding');
    }
  }
  // _check_review_fields
  const kind = pget(r, 'evidence_type');
  const needsRef = pget(r, 'source_class') === 'decision_agent' || kind === 'other_model_review';
  if (needsRef && !r.has('decision_ref')) f.push('6.2:decision_ref');
  if (r.has('decision_ref') && !isStr(pget(r, 'decision_ref'))) f.push('6.2:decision_ref');
  if (kind === 'other_model_review' && !r.has('models')) f.push('6.2:models');
  if (r.has('models')) {
    const m = pget(r, 'models');
    if (!(isObj(m) && keySetIs(m, ['reviewer', 'implementer']) && isStr(pget(m, 'reviewer'))
          && isStr(pget(m, 'implementer')))) {
      f.push('6.2:models');
    }
  }
  if (kind === 'decision_agent_review') {
    for (const k of ['basis', 'stands_for']) if (!r.has(k)) f.push('6.2:' + k);
  }
  if (r.has('basis')) {
    const basis = pget(r, 'basis');
    if (!(isStr(basis) || (isStrList(basis) && isList(basis) && basis.length > 0))) f.push('6.2:basis');
  }
  if (r.has('stands_for') && !isStr(pget(r, 'stands_for'))) f.push('6.2:stands_for');
  if (r.has('gate') && !matches(GATE, pget(r, 'gate'))) f.push('6.2:gate');
  for (const k of ['evidence_type', 'dimension', 'refers_to']) {
    if (r.has(k) && !isStr(pget(r, k))) f.push('6.2:' + k);
  }
  f.push(...checkAuditCopy(r));
  return f;
}

function isAuditValue(kind: string, v: J): boolean {
  if (v === null) return true;
  if (kind === 'risk_class') return inSet(RISK_CLASSES, v);
  return isList(v) && v.every((e) => isObj(e) && keySetIs(e, ['dimension', 'evidence_types'])
    && isStr(pget(e, 'dimension')) && isStrList(pget(e, 'evidence_types')));
}

/** records.py check_audit_copy, rules only. */
function checkAuditCopy(r: JObj): string[] {
  const f: string[] = [];
  const kind = pget(r, 'evidence_type');
  if (!(kind === 'risk_class' || kind === 'evidence_profile')) {
    for (const k of AUDIT_COPY_TYPES) if (r.has(k)) f.push('6.2:audit_copy_key');
    return f;
  }
  const other = kind === AUDIT_COPY_TYPES[0] ? AUDIT_COPY_TYPES[1] : AUDIT_COPY_TYPES[0];
  if (pget(r, 'fact_kind') !== 'observation') f.push('6.2:audit_copy_fact_kind');
  if (!inSet(AUDIT_COPY_SOURCES, pget(r, 'source_class'))) f.push('6.2:audit_copy_source_class');
  if (!r.has(kind)) f.push('6.2:audit_copy_key');
  else if (!isAuditValue(kind, pget(r, kind))) f.push('6.2:audit_copy_value');
  if (r.has(other)) f.push('6.2:audit_copy_key');
  for (const k of ['commit', 'intent_versions']) if (!r.has(k)) f.push('6.2:audit_copy_binding');
  for (const k of AUDIT_COPY_FORBIDDEN) if (r.has(k)) f.push('6.2:audit_copy_forbidden');
  return f;
}

// The port of governor.evaluate and every function it calls (governor.py, TASK-004): one acceptance decision record
// for a request, the inputs of governor-spec.md section 3.2 and the records it reads. Pure: it reads only its
// arguments and never changes them.

import type { J, JObj } from './json.ts';
import { isObj, isList, isInt, pget, keySetIs, pyEq, cmpStr, sortStrs, sortedSet, canon } from './json.ts';
import { sha256Text, hasLoneSurrogate } from './bytes.ts';
import { checkRecord, STATE_NAMES, BLOCKING_KINDS } from './records.ts';

export type Rec = { [key: string]: unknown };

/** The ValueError of evaluate: a request that is not an object or has no task id TASK-<digits>. */
export class GovernorError extends Error {}

const MODULE_PATH = 'src/aieos_bootstrap/governor.py';
const SOURCE_CLASS = 'deterministic_tool_local';
const CI = 'deterministic_tool_external_ci';
const RISKS = ['low', 'medium', 'high', 'critical'];
const EVALUATED_STATES = ['VERIFYING', 'IN_REVIEW'];
const HUMAN_TYPES = ['human_review', 'human_security_review'];
const AI_REVIEW = 'ai_review';
const CROSS_MODEL = 'ai_review (cross-model)';
const REVIEW_RECORD_TYPES = ['other_model_review', 'decision_agent_review'];
const ROW_1_KINDS = ['out_of_scope', 'forbidden_path', 'violation'];
const REQUEST_KEYS = ['task_id', 'task_content_hash', 'evaluated_commit', 'intent_versions', 'task_state',
  'changed_paths', 'retry_count'];
const INPUT_KEYS = ['traces_to', 'risk', 'owner_kept_act', 'weakens_evidence', 'delegation_in_force', 'auto_accept',
  'verification_plan', 'evidence_profile', 'applicable_articles', 'policy_version', 'level_version',
  'ruleset_version'];
// The self-build runs at L1 (A35); row 4 needs L2 or above, so it never applies.
const LEVEL_AT_LEAST_L2 = false;
const NOTES = [
  'advisory: decisions of this governor are advisory (governor-spec.md section 10)',
  'inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository',
  'identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this '
    + 'module\'s defaults, not the channel or the identity that specification 2 section 6.4 names',
];

const HEX64 = /^[0-9a-f]{64}$/;
const COMMIT = /^(?:[0-9a-f]{40}|[0-9a-f]{64})$/;
const TASK = /^TASK-[0-9]+$/;
const VERSION = /^v[0-9]+$/;
const GATE = /^G[0-9]+$/;

function oneOf(values: readonly string[], v: J): boolean {
  return typeof v === 'string' && values.includes(v);
}

/** _text: a non-empty string that UTF-8 can encode. */
function text(v: J): v is string {
  return typeof v === 'string' && v !== '' && !hasLoneSurrogate(v);
}

function texts(v: J): v is string[] {
  return isList(v) && v.every((x) => text(x));
}

function full(re: RegExp, v: J): v is string {
  return typeof v === 'string' && re.test(v);
}

function count(v: J): boolean {
  return isInt(v) && v >= 0;
}

function recordId(rec: Rec): string {
  return 'decision-' + sha256Text(canon(rec) + '\n');
}

// ---------------------------------------------------------------------------------------------------------------
// Input checks

function intentVersions(v: J): v is JObj {
  if (!isObj(v)) return false;
  for (const [k, x] of v) if (!(text(k) && full(VERSION, x))) return false;
  return true;
}

function requestErrors(req: J): string[] {
  if (!isObj(req) || !keySetIs(req, REQUEST_KEYS)) {
    return ['the request is not exactly the keys of specification 2 section 6.5'];
  }
  const errors: string[] = [];
  if (!full(HEX64, pget(req, 'task_content_hash'))) errors.push('task_content_hash');
  if (!full(COMMIT, pget(req, 'evaluated_commit'))) errors.push('evaluated_commit');
  if (!intentVersions(pget(req, 'intent_versions'))) errors.push('intent_versions');
  if (!oneOf(EVALUATED_STATES, pget(req, 'task_state'))) errors.push('task_state');
  if (!texts(pget(req, 'changed_paths'))) errors.push('changed_paths');
  const rc = pget(req, 'retry_count');
  if (!(isObj(rc) && keySetIs(rc, ['used', 'limit']) && count(pget(rc, 'used')) && count(pget(rc, 'limit')))) {
    errors.push('retry_count');
  }
  return errors.map((e) => 'the request\'s ' + e + ' is malformed');
}

function profileForm(v: J): v is JObj[] {
  return isList(v) && v.every((e) => isObj(e) && keySetIs(e, ['dimension', 'evidence_types'])
    && text(pget(e, 'dimension')) && texts(pget(e, 'evidence_types')));
}

function articlesForm(v: J): v is JObj[] {
  return isList(v) && v.every((a) => isObj(a) && keySetIs(a, ['id', 'evidence_required'])
    && text(pget(a, 'id')) && texts(pget(a, 'evidence_required')));
}

function inputsErrors(inp: J): string[] {
  if (!isObj(inp) || !keySetIs(inp, INPUT_KEYS)) {
    return ['the inputs are not exactly the keys of conformance-files.md section 4'];
  }
  const errors: string[] = [];
  if (!texts(pget(inp, 'traces_to'))) errors.push('traces_to');
  if (!oneOf(RISKS, pget(inp, 'risk'))) errors.push('risk');
  for (const key of ['owner_kept_act', 'weakens_evidence', 'delegation_in_force', 'auto_accept']) {
    if (typeof pget(inp, key) !== 'boolean') errors.push(key);
  }
  const plan = pget(inp, 'verification_plan');
  if (!(texts(plan) && plan.every((g) => full(GATE, g)))) errors.push('verification_plan');
  if (!profileForm(pget(inp, 'evidence_profile'))) errors.push('evidence_profile');
  if (!articlesForm(pget(inp, 'applicable_articles'))) errors.push('applicable_articles');
  for (const key of ['policy_version', 'level_version', 'ruleset_version']) {
    if (!text(pget(inp, key))) errors.push(key);
  }
  return errors.map((e) => 'the inputs\' ' + e + ' is malformed');
}

function recordsErrors(recs: J): string[] {
  if (!isList(recs)) return ['the records are not a list'];
  const seen = new Set<string>();
  const errors: string[] = [];
  for (const r of recs) {
    const rid = isObj(r) ? pget(r, 'record_id') : null;
    if (text(rid)) {
      if (seen.has(rid)) errors.push('the record id ' + rid + ' is used twice');
      seen.add(rid);
    }
  }
  return errors;
}

// ---------------------------------------------------------------------------------------------------------------
// The decision record

function base(task: string, inputs: J): Rec {
  const rec: Rec = {
    fact_kind: 'interpretation',
    source_class: SOURCE_CLASS,
    recorder: MODULE_PATH,
    subject: task,
    governor_identity: null,
    scenario_set_hash: null,
  };
  for (const key of ['policy_version', 'level_version', 'ruleset_version']) {
    const v = isObj(inputs) ? pget(inputs, key) : null;
    rec[key] = isObj(inputs) && text(v) ? v : null;
  }
  return rec;
}

function errorRecord(task: string, request: JObj, inputs: J, error: string): Rec {
  const rec = base(task, inputs);
  Object.assign(rec, {
    decision: null, error, table_row: null, profile_used: [], missing_gates: [], blocking: [], failed_gates: [],
    reverify: [], approval_record: null, uncovered: [...NOTES], rests_on_ai: { entries: [], approval: false },
  });
  const tch = pget(request, 'task_content_hash');
  if (full(HEX64, tch)) rec['task_content_hash'] = tch;
  const ec = pget(request, 'evaluated_commit');
  if (full(COMMIT, ec)) rec['evaluated_commit'] = ec;
  const iv = pget(request, 'intent_versions');
  if (intentVersions(iv)) rec['intent_versions'] = new Map(iv);
  const st = pget(request, 'task_state');
  if (typeof st === 'string' && STATE_NAMES.has(st)) rec['next_task_state'] = st;
  rec['record_id'] = recordId(rec);
  return rec;
}

// ---------------------------------------------------------------------------------------------------------------
// The profile

function join(profile: JObj[], articles: JObj[]): Array<[string, string[]]> {
  const out = new Map<string, string[]>();
  const add = (key: string, types: string[]): void => {
    let list = out.get(key);
    if (list === undefined) {
      list = [];
      out.set(key, list);
    }
    for (const t of types) if (!list.includes(t)) list.push(t);
  };
  for (const entry of profile) add(pget(entry, 'dimension') as string, pget(entry, 'evidence_types') as string[]);
  for (const article of articles) add(pget(article, 'id') as string, pget(article, 'evidence_required') as string[]);
  return [...out.entries()];
}

function reviewLike(kind: string): boolean {
  return kind.endsWith('review') || kind.startsWith(AI_REVIEW);
}

function isWay2(r: JObj): boolean {
  const m = pget(r, 'models');
  return pget(r, 'source_class') === 'same_lineage_review' && pget(r, 'evidence_type') === 'other_model_review'
    && isObj(m) && !pyEq(pget(m, 'reviewer'), pget(m, 'implementer')) && text(pget(r, 'decision_ref'));
}

function isDaReview(r: JObj, standsFor: string): boolean {
  return pget(r, 'source_class') === 'decision_agent' && pget(r, 'evidence_type') === 'decision_agent_review'
    && pget(r, 'stands_for') === standsFor && r.has('basis') && text(pget(r, 'decision_ref'));
}

function candidate(r: JObj, kind: string, inputs: JObj): boolean {
  const cls = pget(r, 'source_class');
  const et = pget(r, 'evidence_type');
  const delegated = pget(inputs, 'delegation_in_force') === true;
  if (HUMAN_TYPES.includes(kind)) {
    if (cls === 'human_authority' && et === kind) return true;
    return delegated && pget(inputs, 'owner_kept_act') !== true && isDaReview(r, kind);
  }
  if (kind === AI_REVIEW) return delegated && isWay2(r);
  if (reviewLike(kind)) return false;
  return cls === CI && et === kind;
}

function rid(r: JObj): string {
  return pget(r, 'record_id') as string;
}

function entry(dimension: string, kind: string, current: JObj[], inputs: JObj, reserved: Set<string>):
    [string[], string[]] {
  const rs = current.filter((r) => pyEq(pget(r, 'dimension'), dimension));
  if (kind === CROSS_MODEL) {
    if (!(pget(inputs, 'delegation_in_force') === true && oneOf(['high', 'critical'], pget(inputs, 'risk')))) {
      return [[], []];
    }
    const way2 = rs.filter((r) => isWay2(r));
    const da = rs.filter((r) => isDaReview(r, CROSS_MODEL));
    const failed = [...way2, ...da].filter((r) => pget(r, 'outcome') === 'fail').map(rid);
    const w = sortStrs(way2.filter((r) => pget(r, 'outcome') === 'pass').map(rid));
    const d = sortStrs(da.filter((r) => pget(r, 'outcome') === 'pass').map(rid));
    if (w.length > 0 && d.length > 0) {
      reserved.add(w[0] as string);
      return [[w[0] as string, d[0] as string], failed];
    }
    return [[], failed];
  }
  const cands = rs.filter((r) => candidate(r, kind, inputs) && !reserved.has(rid(r)));
  const sat = sortStrs(cands.filter((r) => pget(r, 'outcome') === 'pass').map(rid));
  const failed = sortStrs(cands.filter((r) => pget(r, 'outcome') === 'fail').map(rid));
  return [sat, failed];
}

// ---------------------------------------------------------------------------------------------------------------
// Records: subject, use, binding, blocking

type Sorted = {
  blocking: Array<[string, string]>;
  approvals: JObj[];
  current: JObj[];
  stale: string[];
  notes: string[];
};

function sortRecords(task: string, request: JObj, recs: J[]): Sorted {
  const blocking: Array<[string, string]> = [];
  const approvals: JObj[] = [];
  const current: JObj[] = [];
  const stale: string[] = [];
  const notes: string[] = [];
  const commit = pget(request, 'evaluated_commit');
  const versions = pget(request, 'intent_versions') as JObj;
  let n = 0;
  for (const r of recs) {
    n++;
    const id = isObj(r) ? pget(r, 'record_id') : null;
    const label = text(id) ? id : 'record ' + n;
    if (isObj(r)) {
      const subject = pget(r, 'subject');
      if (typeof subject === 'string' && subject !== '' && subject !== task) {
        notes.push(label + ': about another subject, not read');
        continue;
      }
    }
    const findings = checkRecord(r);
    if (isObj(r) && pget(r, 'outcome') === 'blocking') {
      const kind = pget(r, 'blocking_kind');
      blocking.push([label, typeof kind === 'string' && BLOCKING_KINDS.has(kind) ? kind : 'other']);
      if (findings.length > 0) notes.push(label + ': blocking, and not otherwise used: ' + findings[0]);
      continue;
    }
    if (findings.length > 0) {
      notes.push(label + ': not used: ' + findings[0]);
      continue;
    }
    const rec = r as JObj;
    if (!text(id)) {
      notes.push(label + ': not used: its record_id cannot be written');
      continue;
    }
    if (pget(rec, 'fact_kind') === 'authority') {
      approvals.push(rec);
      continue;
    }
    if (!rec.has('evidence_type') && !rec.has('gate')) {
      notes.push(label + ': not used: no evidence type or gate');
      continue;
    }
    if (!rec.has('commit') || !rec.has('intent_versions')) {
      notes.push(label + ': not used: no commit binding');
      continue;
    }
    let isStale = !pyEq(pget(rec, 'commit'), commit);
    if (!isStale) {
      for (const [k, v] of pget(rec, 'intent_versions') as JObj) {
        if (!pyEq(pget(versions, k), v)) {
          isStale = true;
          break;
        }
      }
    }
    if (isStale) {
      stale.push(id);
      continue;
    }
    if (pget(rec, 'fact_kind') !== 'observation') {
      notes.push(label + ': not used: a ' + String(pget(rec, 'fact_kind')) + ', not an observation');
      continue;
    }
    current.push(rec);
  }
  return { blocking, approvals, current, stale: sortedSet(stale), notes };
}

function approval(request: JObj, inputs: JObj, approvals: JObj[], notes: string[]): [string | null, boolean] {
  const counted: Array<[number, string]> = [];
  for (const r of approvals) {
    const b = pget(r, 'approval_binding');
    if (!(isObj(b) && pget(b, 'kind') === 'acceptance' && pyEq(pget(b, 'hash'), pget(request, 'task_content_hash')))) {
      notes.push(rid(r) + ': an approval not bound to this task\'s content hash');
      continue;
    }
    if (r.has('outcome') && pget(r, 'outcome') !== 'pass') {
      notes.push(rid(r) + ': an authority record whose outcome is not pass is not an approval');
      continue;
    }
    const cls = pget(r, 'source_class');
    if (cls === 'human_authority') {
      counted.push([0, rid(r)]);
    } else if (cls === 'decision_agent') {
      if (pget(inputs, 'delegation_in_force') !== true) {
        notes.push(rid(r) + ': a delegated approval while the delegation is not in force');
      } else if (pget(inputs, 'owner_kept_act') === true || pget(inputs, 'weakens_evidence') === true) {
        notes.push(rid(r) + ': a delegated approval where only the owner\'s counts');
      } else if (text(pget(r, 'decision_ref'))) {
        counted.push([1, rid(r)]);
      }
    } else {
      notes.push(rid(r) + ': an approval from a class that cannot approve');
    }
  }
  if (counted.length === 0) return [null, false];
  counted.sort((x, y) => (x[0] !== y[0] ? x[0] - y[0] : cmpStr(x[1], y[1])));
  const first = counted[0] as [number, string];
  return [first[1], first[0] === 1];
}

// ---------------------------------------------------------------------------------------------------------------
// Evaluation

function nextAfterRework(request: JObj): string {
  const rc = pget(request, 'retry_count') as JObj;
  return (pget(rc, 'used') as number | bigint) >= (pget(rc, 'limit') as number | bigint) ? 'ESCALATED' : 'REWORK';
}

/** governor.evaluate(request, inputs, records). Throws GovernorError where the Python raises ValueError. */
export function evaluate(request: J, inputs: J, records: J): Rec {
  if (!isObj(request) || !full(TASK, pget(request, 'task_id'))) {
    throw new GovernorError('the request has no task id of the form TASK-<digits>');
  }
  const task = pget(request, 'task_id') as string;
  const errors = [...requestErrors(request), ...inputsErrors(inputs), ...recordsErrors(records)];
  if (errors.length > 0) return errorRecord(task, request, inputs, errors.join('; '));
  const inp = inputs as JObj;

  const { blocking, approvals, current, stale, notes } = sortRecords(task, request, records as J[]);

  let plan = ['G0', ...(pget(inp, 'verification_plan') as string[]).filter((g) => g !== 'G0')];
  plan = plan.filter((g, i) => !plan.slice(0, i).includes(g));
  const gateResults = current.filter((r) => r.has('gate') && pget(r, 'source_class') === CI);
  const passed = new Set(gateResults.filter((r) => pget(r, 'outcome') === 'pass').map((r) => pget(r, 'gate') as string));
  const failedGates = sortedSet(gateResults.filter((r) => pget(r, 'outcome') === 'fail')
    .map((r) => pget(r, 'gate') as string));
  const missingGates = plan.filter((g) => !passed.has(g));

  const profileUsed: Array<{ dimension: string; required: string[]; satisfied_by: string[]; missing_types: string[] }>
    = [];
  const failedRecords: string[] = [];
  const rests: Array<{ dimension: string; evidence_type: string }> = [];
  const byId = new Map<string, JObj>();
  for (const r of current) byId.set(rid(r), r);
  const joined = join(pget(inp, 'evidence_profile') as JObj[], pget(inp, 'applicable_articles') as JObj[]);
  for (const [dimension, kinds] of joined) {
    const reserved = new Set<string>();
    const order = [...kinds.filter((k) => k === CROSS_MODEL), ...kinds.filter((k) => k !== CROSS_MODEL)];
    const sat = new Map<string, string[]>();
    const missing: string[] = [];
    for (const kind of order) {
      const [ids, failed] = entry(dimension, kind, current, inp, reserved);
      failedRecords.push(...failed);
      if (ids.length > 0) sat.set(kind, ids);
      else missing.push(kind);
    }
    for (const kind of kinds) {
      const ids = sat.get(kind);
      if (ids !== undefined) {
        if (ids.every((i) => oneOf(REVIEW_RECORD_TYPES, pget(byId.get(i) as JObj, 'evidence_type')))) {
          rests.push({ dimension, evidence_type: kind });
        }
      }
    }
    const all: string[] = [];
    for (const ids of sat.values()) all.push(...ids);
    profileUsed.push({
      dimension,
      required: [...kinds],
      satisfied_by: sortedSet(all),
      missing_types: kinds.filter((k) => missing.includes(k)),
    });
  }

  const row1 = blocking.filter(([, kind]) => ROW_1_KINDS.includes(kind)).map(([label]) => label);
  const otherBlocking = blocking.filter(([, kind]) => !ROW_1_KINDS.includes(kind)).map(([label]) => label);
  const missingAny = profileUsed.some((item) => item.missing_types.length > 0);
  const reEvaluating = pget(request, 'task_state') === 'IN_REVIEW';

  let approvalRecord: string | null = null;
  let aiApproval = false;
  let decision: string;
  let state: string;
  let row: number;
  if (row1.length > 0) {
    decision = 'REJECT';
    state = 'REJECTED';
    row = 1;
  } else if (otherBlocking.length > 0 || failedGates.length > 0 || failedRecords.length > 0) {
    decision = 'NEEDS_REWORK';
    state = nextAfterRework(request);
    row = 2;
  } else if (missingGates.length > 0 || missingAny) {
    decision = 'INSUFFICIENT_EVIDENCE';
    row = 3;
    const missingKinds: string[] = [];
    for (const item of profileUsed) missingKinds.push(...item.missing_types);
    const humanOnly = missingGates.length === 0 && missingKinds.every((k) => HUMAN_TYPES.includes(k));
    state = humanOnly ? 'IN_REVIEW' : nextAfterRework(request);
  } else if (pget(inp, 'auto_accept') === true && LEVEL_AT_LEAST_L2 && !reEvaluating) {
    decision = 'ACCEPT';
    state = 'ACCEPTED';
    row = 4;
  } else {
    decision = 'NEEDS_REVIEW';
    state = 'IN_REVIEW';
    row = 5;
    if (reEvaluating) {
      [approvalRecord, aiApproval] = approval(request, inp, approvals, notes);
      if (approvalRecord !== null) state = 'ACCEPTED';
    }
  }

  const rec = base(task, inp);
  Object.assign(rec, {
    decision,
    next_task_state: state,
    table_row: row,
    task_content_hash: pget(request, 'task_content_hash'),
    evaluated_commit: pget(request, 'evaluated_commit'),
    intent_versions: new Map(pget(request, 'intent_versions') as JObj),
    profile_used: profileUsed,
    missing_gates: missingGates,
    blocking: sortStrs(blocking.map(([label]) => label)),
    failed_gates: failedGates,
    reverify: stale,
    approval_record: approvalRecord,
    uncovered: [...NOTES, ...notes],
    rests_on_ai: { entries: rests, approval: aiApproval },
  });
  rec['record_id'] = recordId(rec);
  return rec;
}

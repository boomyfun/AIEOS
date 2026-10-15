// The port of resume_check.check and every function it calls (resume_check.py, TASK-008): the check 0 precondition,
// the eight checks of specification 3 section 2, the decision of section 7 and one execution decision record. Pure:
// it reads only its arguments and never changes them. The caller gives no code_sha256 (the reference calls
// check(inputs)), so code_sha256 is always null here.

import type { J, JObj } from './json.ts';
import { isObj, isList, isInt, pget, keySetIs, pyEq, sortStrs, sortedSet } from './json.ts';
import { sha256Text } from './bytes.ts';

export type Rec = { [key: string]: unknown };

/** The value of engine_identity.python: the brief's one placeholder (a port has no Python interpreter version). */
export const PLACEHOLDER = '<engine>';

const INPUT_KEYS = ['task_id', 'log_seq', 'task_state', 'contract', 'contract_hash', 'approved_contract_hash',
  'head_commit', 'base_is_ancestor', 'commits', 'components', 'interfaces', 'symbols', 'schemas', 'derived_read_set',
  'observed_read_set', 'intent_current', 'dependencies', 'articles', 'runtime', 'risk_rules', 'policy_version',
  'budget_use'];
const INPUT_KEY_SET: ReadonlySet<string> = new Set(INPUT_KEYS);
const TASK_STATES = ['READY', 'REWORK', 'IN_PROGRESS'];
const CHANGES = ['added', 'modified', 'deleted'];
const RISKS = ['low', 'medium', 'high', 'critical'];
const ORDER = ['STOP: violation', 'STOP: scope invalid', 'STOP: runtime insufficient', 'ESCALATE', 'BLOCKED', 'REPLAN',
  'CONTINUE_WITH'];
const RECORDER = 'the Resume Check (aieos_bootstrap.resume_check)';
const SOURCE_CLASS = 'deterministic_tool_local';
const AMBIGUOUS = 'ambiguous';
const NO_TASK = 'TASK-0';
const MAX_LOG_SEQ = 2n ** 63n;

const HEX64 = /^[0-9a-f]{64}$/;
const COMMIT = /^(?:[0-9a-f]{40}|[0-9a-f]{64})$/;
const TASK = /^TASK-[0-9]+$/;
const VERSION = /^v[0-9]+$/;
const AMOUNT = /^([0-9]+)([a-z]*)$/;
const TOKEN_UNITS = new Map<string, bigint>([['', 1n], ['k', 1000n], ['m', 1000000n]]);
const TIME_UNITS = new Map<string, bigint>([['s', 1n], ['m', 60n], ['h', 3600n], ['d', 86400n]]);

/** An input that is missing or not in its section 9 form. */
class Bad extends Error {}

// ---------------------------------------------------------------------------------------------------------------
// Value forms

function str(v: J): v is string {
  return typeof v === 'string' && v !== '';
}

function int(v: J): v is number | bigint {
  return isInt(v) && v >= 0;
}

function strs(v: J): v is string[] {
  return isList(v) && v.every((x) => str(x));
}

function full(re: RegExp, v: J): v is string {
  return typeof v === 'string' && re.test(v);
}

function oneOf(values: readonly string[], v: J): v is string {
  return typeof v === 'string' && values.includes(v);
}

function need(ok: boolean, what: string): void {
  if (!ok) throw new Bad(what);
}

function logSeqOk(v: J): boolean {
  return int(v) && BigInt(v) < MAX_LOG_SEQ;
}

function idsOf(taskId: J, logSeq: J, headCommit: J): (eventType: string) => string {
  return (eventType: string): string => {
    const text = [
      typeof taskId === 'string' ? taskId : '',
      logSeqOk(logSeq) ? String(logSeq) : '',
      typeof headCommit === 'string' ? headCommit : '',
      '', // code_sha256 or '': the caller gives none
      eventType,
    ].join('\n');
    return sha256Text(text);
  };
}

// ---------------------------------------------------------------------------------------------------------------
// Patterns

function starMatch(patternText: string, nameText: string): boolean {
  const pattern = Array.from(patternText);
  const name = Array.from(nameText);
  let p = 0;
  let n = 0;
  let star = -1;
  let mark = 0;
  while (n < name.length) {
    if (p < pattern.length && pattern[p] === '*') {
      star = p;
      mark = n;
      p += 1;
    } else if (p < pattern.length && pattern[p] === name[n]) {
      p += 1;
      n += 1;
    } else if (star >= 0) {
      mark += 1;
      p = star + 1;
      n = mark;
    } else {
      return false;
    }
  }
  while (p < pattern.length && pattern[p] === '*') p += 1;
  return p === pattern.length;
}

function namesMeet(a: string, b: string): boolean {
  const sa = a.includes('*');
  const sb = b.includes('*');
  if (!sa && !sb) return a === b;
  if (sa && sb) return true;
  return sa ? starMatch(a, b) : starMatch(b, a);
}

function parts(pattern: string): string[] {
  return (pattern.includes('/') ? pattern : '**/' + pattern).split('/');
}

/** resume_check.meet: whether two patterns meet. */
export function meet(a: string, b: string): boolean {
  const pa = parts(a);
  const pb = parts(b);
  const memo = new Map<number, boolean>();
  const width = pb.length + 1;
  const go = (i: number, j: number): boolean => {
    const key = i * width + j;
    const known = memo.get(key);
    if (known !== undefined) return known;
    let ok: boolean;
    if (i === pa.length && j === pb.length) {
      ok = true;
    } else if (i < pa.length && pa[i] === '**') {
      ok = go(i + 1, j) || (j < pb.length && go(i, j + 1));
    } else if (j < pb.length && pb[j] === '**') {
      ok = go(i, j + 1) || (i < pa.length && go(i + 1, j));
    } else if (i < pa.length && j < pb.length) {
      ok = namesMeet(pa[i] as string, pb[j] as string) && go(i + 1, j + 1);
    } else {
      ok = false;
    }
    memo.set(key, ok);
    return ok;
  };
  return go(0, 0);
}

function matches(pattern: string, path: string): boolean {
  return meet(pattern, path);
}

function folder(path: string): string[] {
  if (path.includes('*')) return [path];
  return [path, path.replace(/\/+$/, '') + '/**'];
}

// ---------------------------------------------------------------------------------------------------------------
// The inputs

function schemaSide(v: J): boolean {
  if (v === null || v === AMBIGUOUS) return true;
  return isObj(v) && keySetIs(v, ['path', 'sha256']) && str(pget(v, 'path')) && full(HEX64, pget(v, 'sha256'));
}

function checkContract(c: J): void {
  need(isObj(c), 'contract is not an object');
  const m = c as JObj;
  for (const key of ['input_state', 'write_set', 'read_set', 'constitution', 'task_type', 'risk', 'autonomy',
    'contract_version']) {
    need(m.has(key), 'contract lacks ' + key);
  }
  const s = pget(m, 'input_state');
  need(isObj(s), 'contract input_state is not an object');
  const si = s as JObj;
  need(full(COMMIT, pget(si, 'base_commit')), 'contract base_commit is not a commit id');
  need(strs(pget(si, 'depends_on')), 'contract depends_on is not a list of task ids');
  const iv = pget(si, 'intent_versions');
  need(isObj(iv) && [...iv].every(([k, v]) => str(k) && str(v)), 'contract intent_versions is not an object of versions');
  const ws = pget(m, 'write_set');
  need(isObj(ws) && strs(pget(ws, 'paths')), 'contract write_set.paths is not a list');
  const rs = pget(m, 'read_set');
  need(isObj(rs) && ['paths', 'interfaces', 'schemas'].every((k) => strs(rs.has(k) ? pget(rs, k) : [])),
    'contract read_set is not {paths, interfaces, schemas}');
  need(strs(pget(m, 'constitution')), 'contract constitution is not a list of article ids');
  need(str(pget(m, 'task_type')), 'contract task_type is not a string');
  need(oneOf(RISKS, pget(m, 'risk')), 'contract risk is not low, medium, high or critical');
  need(full(VERSION, pget(m, 'contract_version')), 'contract contract_version is not v<digits>');
  const au = pget(m, 'autonomy');
  const b = isObj(au) ? pget(au, 'budgets') : null;
  need(isObj(b) && [...b].every(([k, v]) => str(k) && (int(v) || str(v))),
    'contract autonomy.budgets is not an object of limits');
}

function checkInputs(inp: J): void {
  need(isObj(inp), 'inputs is not an object');
  const m = inp as JObj;
  const missing = sortStrs(INPUT_KEYS.filter((k) => !m.has(k)));
  need(missing.length === 0, 'inputs lacks ' + missing.join(', '));
  const extra = sortStrs([...m.keys()].filter((k) => !INPUT_KEY_SET.has(k)));
  need(extra.length === 0, 'inputs has keys section 9 does not name: ' + extra.join(', '));
  need(full(TASK, pget(m, 'task_id')), 'task_id is not TASK-<digits>');
  need(logSeqOk(pget(m, 'log_seq')), 'log_seq is not an integer from 0 to 2**63 - 1');
  need(oneOf(TASK_STATES, pget(m, 'task_state')), 'task_state is not READY, REWORK or IN_PROGRESS');
  for (const key of ['contract_hash', 'approved_contract_hash']) {
    need(full(HEX64, pget(m, key)), key + ' is not 64 lowercase hex digits');
  }
  need(full(COMMIT, pget(m, 'head_commit')), 'head_commit is not a commit id');
  need(typeof pget(m, 'base_is_ancestor') === 'boolean', 'base_is_ancestor is not true or false');
  checkContract(pget(m, 'contract'));
  const commits = pget(m, 'commits');
  need(isList(commits), 'commits is not a list');
  for (const c of commits as J[]) {
    need(isObj(c) && keySetIs(c, ['id', 'paths', 'submitted']), 'a commit is not {id, paths, submitted}');
    const cm = c as JObj;
    need(full(COMMIT, pget(cm, 'id')), 'a commit id is not a commit id');
    need(typeof pget(cm, 'submitted') === 'boolean', 'a commit submitted is not true or false');
    const ps = pget(cm, 'paths');
    need(isList(ps), 'a commit paths is not a list');
    for (const p of ps as J[]) {
      need(isObj(p) && keySetIs(p, ['path', 'change']) && str(pget(p, 'path')) && oneOf(CHANGES, pget(p, 'change')),
        'a commit path is not {path, change}');
    }
  }
  const components = pget(m, 'components');
  need(isList(components), 'components is not a list');
  for (const c of components as J[]) {
    need(isObj(c) && str(pget(c, 'id')) && strs(pget(c, 'paths')), 'a component is not {id, paths, tags}');
  }
  const interfaces = pget(m, 'interfaces');
  need(isList(interfaces), 'interfaces is not a list');
  for (const i of interfaces as J[]) {
    need(isObj(i) && str(pget(i, 'id')) && str(pget(i, 'component')), 'an interface is not {id, component}');
  }
  const symbols = pget(m, 'symbols');
  need(isList(symbols), 'symbols is not a list');
  for (const s of symbols as J[]) {
    need(isObj(s) && keySetIs(s, ['interface', 'base', 'head']) && str(pget(s, 'interface'))
      && ['base', 'head'].every((k) => { const v = pget(s, k); return v === null || typeof v === 'string'; }),
    'a symbol is not {interface, base, head}');
  }
  const schemas = pget(m, 'schemas');
  need(isList(schemas), 'schemas is not a list');
  for (const s of schemas as J[]) {
    need(isObj(s) && keySetIs(s, ['name', 'base', 'head']) && str(pget(s, 'name'))
      && ['base', 'head'].every((k) => schemaSide(pget(s, k))), 'a schema is not {name, base, head}');
  }
  need(strs(pget(m, 'derived_read_set')), 'derived_read_set is not a list of paths');
  const ors = pget(m, 'observed_read_set');
  need(ors === null || strs(ors), 'observed_read_set is not a list of paths or null');
  const ic = pget(m, 'intent_current');
  need(isObj(ic) && [...ic].every(([k, v]) => str(k) && (v === null || str(v))),
    'intent_current is not an object of versions or null');
  const deps = pget(m, 'dependencies');
  need(isObj(deps), 'dependencies is not an object');
  for (const [k, d] of deps as JObj) {
    need(str(k) && isObj(d) && keySetIs(d, ['state', 'stale_evidence'])
      && (pget(d, 'state') === null || str(pget(d, 'state'))) && typeof pget(d, 'stale_evidence') === 'boolean',
    'a dependency is not {state, stale_evidence}');
  }
  const articles = pget(m, 'articles');
  need(isList(articles), 'articles is not a list');
  for (const a of articles as J[]) {
    need(isObj(a) && str(pget(a, 'id')) && a.has('violated')
      && (pget(a, 'violated') === null || typeof pget(a, 'violated') === 'boolean'),
    'an article is not {id, scope, applicability, violated}');
  }
  const rt = pget(m, 'runtime');
  need(isObj(rt) && keySetIs(rt, ['adapter', 'max_risk']) && str(pget(rt, 'adapter'))
    && (pget(rt, 'max_risk') === null || oneOf(RISKS, pget(rt, 'max_risk'))), 'runtime is not {adapter, max_risk}');
  const rr = pget(m, 'risk_rules');
  need(isList(rr) && rr.every((r) => isObj(r)), 'risk_rules is not a list of rules');
  const pv = pget(m, 'policy_version');
  need(pv === null || str(pv), 'policy_version is not a string or null');
  const bu = pget(m, 'budget_use');
  need(isObj(bu), 'budget_use is not an object');
  for (const [k, u] of bu as JObj) {
    need(str(k) && isObj(u) && keySetIs(u, ['used', 'reported']) && typeof pget(u, 'reported') === 'boolean'
      && (int(pget(u, 'used')) || typeof pget(u, 'used') === 'string'), 'a budget use is not {used, reported}');
  }
}

// ---------------------------------------------------------------------------------------------------------------
// The effective read-set and the signatures

type Entry = { entry: string; kind: string; sources: string[] };
type Met = { entry: string; kind: string; verdict: string; reason: string };

function readSet(inp: JObj): Entry[] {
  const rs = pget(pget(inp, 'contract') as JObj, 'read_set') as JObj;
  const get = (k: string): string[] => (rs.has(k) ? pget(rs, k) : []) as string[];
  const paths = new Map<string, string[]>();
  const observed = pget(inp, 'observed_read_set');
  const sources: Array<[string, string[]]> = [
    ['declared', get('paths')],
    ['derived', pget(inp, 'derived_read_set') as string[]],
    ['observed', isList(observed) ? (observed as string[]) : []],
  ];
  for (const [source, items] of sources) {
    for (const p of items) {
      let list = paths.get(p);
      if (list === undefined) {
        list = [];
        paths.set(p, list);
      }
      if (!list.includes(source)) list.push(source);
    }
  }
  const entries: Entry[] = sortStrs(paths.keys()).map((p) => ({ entry: p, kind: 'path', sources: paths.get(p) as string[] }));
  for (const i of sortedSet(get('interfaces'))) entries.push({ entry: i, kind: 'interface', sources: ['declared'] });
  for (const s of sortedSet(get('schemas'))) entries.push({ entry: s, kind: 'schema', sources: ['declared'] });
  return entries;
}

function componentPaths(inp: JObj, componentId: string): string[] | null {
  const found = (pget(inp, 'components') as JObj[]).filter((c) => pyEq(pget(c, 'id'), componentId));
  if (found.length !== 1) return null;
  const out: string[] = [];
  for (const p of pget(found[0] as JObj, 'paths') as string[]) out.push(...folder(p));
  return out;
}

function interfaceComponent(inp: JObj, name: string): string[] | null {
  const found = (pget(inp, 'interfaces') as JObj[]).filter((i) => pyEq(pget(i, 'id'), name));
  if (found.length !== 1) return null;
  return componentPaths(inp, pget(found[0] as JObj, 'component') as string);
}

function schemaPaths(inp: JObj, name: string): string[] | null {
  const found = (pget(inp, 'schemas') as JObj[]).filter((s) => pyEq(pget(s, 'name'), name));
  if (found.length !== 1) return null;
  const f = found[0] as JObj;
  const sides = [pget(f, 'base'), pget(f, 'head')];
  if (sides.some((v) => !isObj(v))) return null;
  return sortedSet(sides.map((v) => pget(v as JObj, 'path') as string));
}

function verdicts(inp: JObj, entries: Entry[], delta: string[]): [Met[], string[]] {
  const met: Met[] = [];
  const unresolved: string[] = [];
  for (const e of entries) {
    const name = e.entry;
    const kind = e.kind;
    if (kind === 'path') {
      if (delta.some((p) => matches(name, p))) {
        met.push({ entry: name, kind, verdict: 'non_breaking',
          reason: 'a path entry has no signature; its change is non-breaking' });
      }
      continue;
    }
    if (kind === 'interface') {
      const comp = interfaceComponent(inp, name);
      if (comp === null) {
        unresolved.push(name);
        if (delta.length > 0) {
          met.push({ entry: name, kind, verdict: 'breaking',
            reason: 'the interface or its component cannot be resolved (fail closed)' });
        }
        continue;
      }
      if (!comp.some((c) => delta.some((p) => matches(c, p)))) continue;
      const sym = (pget(inp, 'symbols') as JObj[]).filter((s) => pyEq(pget(s, 'interface'), name));
      let verdict: string;
      let reason: string;
      if (sym.length !== 1) {
        verdict = 'breaking';
        reason = 'no single symbol entry for the interface (fail closed)';
      } else {
        const b = pget(sym[0] as JObj, 'base');
        const h = pget(sym[0] as JObj, 'head');
        if (b === null || h === null) {
          verdict = 'breaking';
          reason = 'the symbol is in no file at one commit';
        } else if (b === AMBIGUOUS || h === AMBIGUOUS) {
          verdict = 'breaking';
          reason = 'the symbol is defined more than once at one commit';
        } else if (!pyEq(b, h)) {
          verdict = 'breaking';
          reason = 'the signature differs between base_commit and HEAD';
        } else {
          verdict = 'non_breaking';
          reason = 'the signature is equal at base_commit and HEAD';
        }
      }
      met.push({ entry: name, kind, verdict, reason });
      continue;
    }
    const resolved = schemaPaths(inp, name);
    if (resolved === null) {
      unresolved.push(name);
      if (delta.length > 0) {
        met.push({ entry: name, kind, verdict: 'breaking',
          reason: 'the schema resolves to no file or to more than one at one commit (fail closed)' });
      }
      continue;
    }
    if (!resolved.some((r) => delta.some((p) => matches(r, p)))) continue;
    const s = (pget(inp, 'schemas') as JObj[]).filter((x) => pyEq(pget(x, 'name'), name))[0] as JObj;
    let verdict: string;
    let reason: string;
    if (pyEq(pget(s, 'base'), pget(s, 'head'))) {
      verdict = 'non_breaking';
      reason = 'the schema file is the same path with the same content hash';
    } else {
      verdict = 'breaking';
      reason = 'the schema file or its content hash differs';
    }
    met.push({ entry: name, kind, verdict, reason });
  }
  return [met, unresolved];
}

function taskPatterns(inp: JObj, entries: Entry[]): string[] {
  const contract = pget(inp, 'contract') as JObj;
  const out = [...(pget(pget(contract, 'write_set') as JObj, 'paths') as string[])];
  for (const e of entries) {
    if (e.kind === 'path') {
      out.push(e.entry);
    } else if (e.kind === 'interface') {
      const comp = interfaceComponent(inp, e.entry);
      out.push(...(comp !== null ? comp : ['**']));
    } else {
      const sp = schemaPaths(inp, e.entry);
      out.push(...(sp !== null ? sp : ['**']));
    }
  }
  return out;
}

// ---------------------------------------------------------------------------------------------------------------
// Check 6, check 7 and check 8

function scopePatterns(inp: JObj, scope: J): string[] | null {
  if (scope === null) return [];
  if (!isObj(scope)) return null;
  const paths = scope.has('paths') ? pget(scope, 'paths') : [];
  const comps = scope.has('components') ? pget(scope, 'components') : [];
  if (!(strs(paths) && strs(comps))) return null;
  const out: string[] = [...paths];
  for (const cid of comps) {
    const cp = componentPaths(inp, cid);
    if (cp === null) return null;
    out.push(...cp);
  }
  return out;
}

function applicableArticle(inp: JObj, article: JObj, patterns: string[]): boolean {
  const contract = pget(inp, 'contract') as JObj;
  const listed = (pget(contract, 'constitution') as string[]).some((x) => pyEq(x, pget(article, 'id')));
  const app = pget(article, 'applicability');
  if (app !== null) {
    const types = isObj(app) ? pget(app, 'task_types') : null;
    if (strs(types) && !types.some((t) => pyEq(t, pget(contract, 'task_type'))) && !listed) return false;
  }
  if (listed) return true;
  const sp = scopePatterns(inp, pget(article, 'scope'));
  if (sp === null) return true;
  return sp.some((a) => patterns.some((b) => meet(a, b)));
}

function rulePatterns(rule: JObj): string[] | null {
  const m = pget(rule, 'match');
  if (isObj(m) && strs(pget(m, 'paths'))) return pget(m, 'paths') as string[];
  return null;
}

function taskRisk(inp: JObj): [string, string[]] {
  const contract = pget(inp, 'contract') as JObj;
  let risk = pget(contract, 'risk') as string;
  const unmatched: string[] = [];
  for (const wp of pget(pget(contract, 'write_set') as JObj, 'paths') as string[]) {
    let hit = false;
    for (const rule of pget(inp, 'risk_rules') as JObj[]) {
      const pats = rulePatterns(rule);
      const r = pget(rule, 'risk');
      const cls = oneOf(RISKS, r) ? r : 'critical';
      if (pats === null || pats.some((p) => meet(p, wp))) {
        hit = true;
        if (RISKS.indexOf(cls) > RISKS.indexOf(risk)) risk = cls;
      }
    }
    if (!hit) unmatched.push(wp);
  }
  return [risk, unmatched];
}

function amount(name: string, value: J): number | bigint | null {
  if (int(value)) return value;
  if (typeof value !== 'string') return null;
  const m = AMOUNT.exec(value);
  if (m === null) return null;
  const units = name === 'tokens' ? TOKEN_UNITS : (name === 'wall_time' || name === 'human_attention') ? TIME_UNITS
    : null;
  if (units === null) return null;
  const unit = units.get(m[2] as string);
  if (unit === undefined) return null;
  return BigInt(m[1] as string) * unit;
}

// ---------------------------------------------------------------------------------------------------------------
// The record

function baseRecord(taskId: J, eventId: (t: string) => string): Rec {
  return {
    record_id: eventId('decision.execution'),
    fact_kind: 'interpretation',
    source_class: SOURCE_CLASS,
    recorder: RECORDER,
    subject: full(TASK, taskId) ? taskId : NO_TASK,
    engine_identity: { code_sha256: null, python: PLACEHOLDER },
  };
}

function errorRecord(inputs: J, reason: string): Rec {
  const g = (k: string): J => (isObj(inputs) ? pget(inputs, k) : null);
  const eventId = idsOf(g('task_id'), g('log_seq'), g('head_commit'));
  const rec = baseRecord(g('task_id'), eventId);
  const uncovered: string[] = ['engine_identity.code_sha256: not given by the caller'];
  if (rec['subject'] === NO_TASK) {
    uncovered.push('subject: task_id is malformed, so ' + NO_TASK + ' stands for it (decision D-359)');
  }
  Object.assign(rec, { decision: null, error: reason, uncovered, state_effect: [] });
  return rec;
}

/** resume_check.check(inputs) with code_sha256 None. A JS exception inside the decision (which the Python would
 * report as "the check could not complete: <type>") is not caught here: the caller fails closed on it. */
export function check(inputs: J): Rec {
  try {
    checkInputs(inputs);
  } catch (e) {
    if (e instanceof Bad) return errorRecord(inputs, 'an input is missing or malformed: ' + e.message);
    throw e;
  }
  const m = inputs as JObj;
  if (pget(m, 'contract_hash') !== pget(m, 'approved_contract_hash')) {
    return errorRecord(inputs, 'check 0: the contract at HEAD is not the approved contract');
  }
  return decide(m);
}

type Check = { check: number; status: string; outcome: string | null; detail: string };

function decide(inp: JObj): Rec {
  const c = pget(inp, 'contract') as JObj;
  const s = pget(c, 'input_state') as JObj;
  const headCommit = pget(inp, 'head_commit') as string;
  const baseCommit = pget(s, 'base_commit') as string;
  const writePaths = pget(pget(c, 'write_set') as JObj, 'paths') as string[];
  const eventId = idsOf(pget(inp, 'task_id'), pget(inp, 'log_seq'), headCommit);
  const uncovered: string[] = [];
  const checks = new Map<number, Check>();
  const put = (n: number, status: string, outcome: string | null, detail: string): void => {
    checks.set(n, { check: n, status, outcome, detail });
  };

  // Check 1: base freshness.
  const delta = new Map<string, string>();
  let computed = false;
  if (baseCommit === headCommit) {
    put(1, 'passed', null, 'base_commit equals HEAD');
  } else if (pget(inp, 'base_is_ancestor') !== true) {
    put(1, 'fired', 'ESCALATE', 'base_commit is not an ancestor of HEAD');
  } else {
    for (const commit of pget(inp, 'commits') as JObj[]) {
      if (pget(commit, 'submitted') === true) continue;
      for (const p of pget(commit, 'paths') as JObj[]) delta.set(pget(p, 'path') as string, pget(p, 'change') as string);
    }
    computed = true;
    put(1, 'passed', null, delta.size + ' paths changed since base_commit');
  }
  const entries = readSet(inp);
  let met: Met[] = [];
  let unresolved: string[] = [];
  const deltaSorted = sortStrs(delta.keys());
  // Check 2: write-set conflict; check 3: read-set freshness.
  if (baseCommit === headCommit) {
    put(2, 'skipped', null, 'HEAD equals base_commit');
    put(3, 'skipped', null, 'HEAD equals base_commit');
  } else if (!computed) {
    put(2, 'not_run', null, 'the delta cannot be computed');
    put(3, 'not_run', null, 'the delta cannot be computed');
  } else {
    const hit = deltaSorted.filter((p) => writePaths.some((w) => matches(w, p)));
    if (hit.length > 0) put(2, 'fired', 'STOP: scope invalid', 'delta meets the write-set: ' + hit.join(', '));
    else put(2, 'passed', null, 'delta does not meet the write-set');
    [met, unresolved] = verdicts(inp, entries, deltaSorted);
    if (met.length === 0) {
      put(3, 'passed', null, 'delta meets no entry of the effective read-set');
    } else if (met.some((x) => x.verdict === 'breaking')) {
      put(3, 'fired', 'REPLAN', 'a met entry is breaking: '
        + met.filter((x) => x.verdict === 'breaking').map((x) => x.entry).join(', '));
    } else {
      put(3, 'fired', 'CONTINUE_WITH', 'every met entry is non-breaking');
    }
  }
  // Check 4: intent freshness.
  const iv = new Map<string, { contract: string; current: J }>();
  const moved: string[] = [];
  const civ = pget(s, 'intent_versions') as JObj;
  const current = pget(inp, 'intent_current') as JObj;
  for (const entity of sortStrs(civ.keys())) {
    const version = pget(civ, entity) as string;
    const cur = pget(current, entity);
    iv.set(entity, { contract: version, current: cur });
    if (cur !== version) moved.push(entity);
  }
  if (moved.length > 0) put(4, 'fired', 'REPLAN', 'intent moved or missing at HEAD: ' + moved.join(', '));
  else put(4, 'passed', null, 'every intent version is current');
  // Check 5: dependency freshness.
  const deps = new Map<string, J>();
  const blocking: string[] = [];
  const dependencies = pget(inp, 'dependencies') as JObj;
  const dependsOn = pget(s, 'depends_on') as string[];
  for (const task of dependsOn) {
    const d = dependencies.get(task);
    const state = d !== undefined ? pget(d as JObj, 'state') : null;
    deps.set(task, state);
    if (state !== 'DONE') blocking.push(task);
  }
  if (blocking.length > 0) {
    put(5, 'fired', 'BLOCKED', 'a dependency is not DONE, is STALE or is unknown: ' + blocking.join(', '));
  } else {
    put(5, 'passed', null, 'every dependency is DONE');
  }
  // Check 6: constitution.
  const patterns = taskPatterns(inp, entries);
  const applicable: string[] = [];
  const violated: string[] = [];
  const noResult: string[] = [];
  const articles = pget(inp, 'articles') as JObj[];
  for (const a of articles) {
    if (applicableArticle(inp, a, patterns)) {
      const id = pget(a, 'id') as string;
      applicable.push(id);
      const v = pget(a, 'violated');
      if (v === true) violated.push(id);
      else if (v === null) noResult.push(id);
    }
  }
  const known = new Set(articles.map((a) => pget(a, 'id') as string));
  for (const aid of pget(c, 'constitution') as string[]) {
    if (!known.has(aid) && !applicable.includes(aid)) {
      applicable.push(aid);
      noResult.push(aid);
    }
  }
  for (const aid of noResult) uncovered.push('article ' + aid + ': no check result at HEAD');
  if (violated.length > 0) {
    put(6, 'fired', 'ESCALATE', 'an applicable article is violated at HEAD: ' + violated.join(', '));
  } else {
    put(6, 'passed', null, 'no applicable article is violated at HEAD');
  }
  // Check 7: runtime.
  const [risk, unmatched] = taskRisk(inp);
  const runtime = pget(inp, 'runtime') as JObj;
  const maxRisk = pget(runtime, 'max_risk') as string | null;
  if (maxRisk === null || RISKS.indexOf(maxRisk) < RISKS.indexOf(risk)) {
    put(7, 'fired', 'STOP: runtime insufficient',
      maxRisk !== null ? 'max_risk ' + maxRisk + ' is below the task risk ' + risk : 'the runtime has no declaration');
  } else if (unmatched.length > 0) {
    put(7, 'fired', 'ESCALATE', 'a write-set pattern meets no risk rule: ' + unmatched.join(', '));
  } else {
    put(7, 'passed', null, 'max_risk ' + maxRisk + ' covers the task risk ' + risk);
  }
  // Check 8: budget.
  const budgets = new Map<string, { limit: J; used: J; reported: boolean }>();
  const over: string[] = [];
  const limits = pget(pget(c, 'autonomy') as JObj, 'budgets') as JObj;
  const budgetUse = pget(inp, 'budget_use') as JObj;
  for (const name of sortStrs(limits.keys())) {
    const limit = pget(limits, name);
    const use = budgetUse.get(name);
    const used = use !== undefined ? pget(use as JObj, 'used') : null;
    const reported = use !== undefined && pget(use as JObj, 'reported') === true;
    budgets.set(name, { limit, used, reported });
    if (!reported) {
      uncovered.push('budget ' + name + ': use not reported');
      continue;
    }
    let lim = amount(name, limit);
    let amt = amount(name, used);
    if (name === 'retries') {
      lim = int(limit) ? limit : null;
      amt = int(used) ? used : null;
    }
    if (lim === null || amt === null) {
      uncovered.push('budget ' + name + ': a form that cannot be parsed');
      continue;
    }
    if (amt > lim) over.push(name);
  }
  if (over.length > 0) put(8, 'fired', 'ESCALATE', 'a budget is used up: ' + over.join(', '));
  else put(8, 'passed', null, 'every reported budget use is within its limit');

  const ordered: Check[] = [];
  for (let n = 1; n <= 8; n++) ordered.push(checks.get(n) as Check);
  const fired = ordered.filter((x) => x.status === 'fired').map((x) => x.outcome as string);
  const outcomes = ORDER.filter((o) => fired.includes(o));
  const decision = outcomes.length > 0 ? (outcomes[0] as string) : 'CONTINUE';
  const observed = pget(inp, 'observed_read_set');
  if (observed === null) uncovered.push('read-set: no observed source, the effective read-set is an estimate');
  uncovered.push('engine_identity.code_sha256: not given by the caller');

  const record = baseRecord(pget(inp, 'task_id'), eventId);
  const effect = stateEffect(decision, checks, inp, eventId, record['record_id'] as string, met, delta, uncovered);
  Object.assign(record, {
    decision,
    contract_hash: pget(inp, 'contract_hash'),
    contract_version: pget(c, 'contract_version'),
    base_commit: baseCommit,
    head_commit: headCommit,
    log_seq: pget(inp, 'log_seq'),
    delta: deltaSorted.map((p) => ({ path: p, change: delta.get(p) as string })),
    checks: ordered,
    outcomes_fired: outcomes,
    read_set: { entries, estimate: observed === null, unresolved: sortedSet(unresolved), unanalysed: [] },
    signatures: met,
    intent_versions: iv,
    dependencies: deps,
    constitution: { applicable, violated, no_result: noResult },
    runtime: { adapter: pget(runtime, 'adapter'), max_risk: maxRisk, task_risk: risk },
    budgets,
    policy_version: pget(inp, 'policy_version'),
    uncovered,
    state_effect: effect,
  });
  return record;
}

type Event = { event_id: string; type: string; payload: unknown; task_id: string };

function event(eventId: (t: string) => string, taskId: string, type: string, payload: unknown): Event {
  return { event_id: eventId(type), type, payload, task_id: taskId };
}

function meetsEntry(inp: JObj, m: Met, path: string): boolean {
  if (m.kind === 'path') return matches(m.entry, path);
  const resolved = schemaPaths(inp, m.entry);
  return resolved === null ? true : resolved.some((r) => matches(r, path));
}

function stateEffect(decision: string, checks: Map<number, Check>, inp: JObj, eventId: (t: string) => string,
  recordId: string, met: Met[], delta: Map<string, string>, uncovered: string[]): Event[] {
  const task = pget(inp, 'task_id') as string;
  const contract = pget(inp, 'contract') as JObj;
  if (decision === 'REPLAN') {
    const replan = [3, 4].filter((n) => {
      const ch = checks.get(n) as Check;
      return ch.status === 'fired' && ch.outcome === 'REPLAN';
    });
    const first = Math.min(...replan);
    if (first === 4) {
      uncovered.push('check 4 REPLAN: no task.stale, since the intent.changed event it must refer to is not '
        + 'an input (specification 3 section 12 point 4)');
      return [];
    }
    const hits: string[] = [];
    for (const m of met) {
      for (const p of delta.keys()) if (m.kind !== 'interface' && meetsEntry(inp, m, p)) hits.push(p);
    }
    const conflict = event(eventId, task, 'conflict.detected', {
      tasks: [], paths: sortedSet(hits),
      interfaces: sortStrs(met.filter((m) => m.kind === 'interface').map((m) => m.entry)),
    });
    uncovered.push('conflict.detected tasks: the commits\' trailers are not an input');
    if (pget(inp, 'task_state') === 'READY') return [conflict];
    return [conflict, event(eventId, task, 'task.stale', { cause: 'conflict', refers_to: conflict.event_id })];
  }
  if (decision === 'BLOCKED') {
    const dependencies = pget(inp, 'dependencies') as JObj;
    const tasks = (pget(pget(contract, 'input_state') as JObj, 'depends_on') as string[]).filter((t) => {
      const d = dependencies.get(t);
      return (d !== undefined && d !== null ? pget(d as JObj, 'state') : null) !== 'DONE';
    });
    return [event(eventId, task, 'task.blocked', { reason: 'dependency', blocked_by: tasks })];
  }
  if (decision === 'ESCALATE') {
    return [event(eventId, task, 'task.blocked', { reason: 'escalate', blocked_by: [recordId] })];
  }
  if (decision === 'STOP: scope invalid') {
    const writePaths = pget(pget(contract, 'write_set') as JObj, 'paths') as string[];
    const hit = sortStrs([...delta.keys()].filter((p) => writePaths.some((w) => matches(w, p))));
    const conflict = event(eventId, task, 'conflict.detected', { tasks: [], paths: hit });
    uncovered.push('conflict.detected tasks: the commits\' trailers are not an input');
    return [conflict, event(eventId, task, 'task.blocked',
      { reason: 'scope_invalid', blocked_by: [conflict.event_id] })];
  }
  return [];
}

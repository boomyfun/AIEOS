// Round 2's document: the input document read and checked as test_export_round2.parse_input reads it, every append
// call and reconcile case computed as reference_document computes it (the log carried from call to call), and the
// whole output built in the canonical text before the program's single write.

import type { J, JObj } from './json.ts';
import { parseJson, canonicalText, isObj, isList, pget, keySetIs } from './json.ts';
import type { V, VObj } from './r2_pyjson.ts';
import { checkDepth } from './r2_pyjson.ts';
import type { AppendResult, Lease, Time } from './r2_eventlog.ts';
import { append } from './r2_eventlog.ts';
import type { RecoveryResult } from './r2_recovery.ts';
import { reconcile } from './r2_recovery.ts';

export const CALL_KEYS = ['event_type', 'payload', 'event_id', 'appended_at', 'task_id', 'fencing_token', 'corrects',
  'lease', 'recorder', 'record_id'] as const;
export const CASE_KEYS = ['log', 'commits', 'leases', 'now', 'recorder'] as const;
export const USAGE = 'usage: node main2.ts <round-2 input document>\n';

/** Not a round-2 input document, or a call or case that cannot be computed. */
export class Round2Error extends Error {}

const TIME = /^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})Z$/;

function daysFromCivil(y: number, m: number, d: number): number {
  const yy = m <= 2 ? y - 1 : y;
  const era = Math.floor(yy / 400);
  const yoe = yy - era * 400;
  const doy = Math.floor((153 * (m + (m > 2 ? -3 : 9)) + 2) / 5) + d - 1;
  const doe = yoe * 365 + Math.floor(yoe / 4) - Math.floor(yoe / 100) + doy;
  return era * 146097 + doe - 719468;
}

function daysInMonth(y: number, m: number): number {
  if (m === 2) return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0 ? 29 : 28;
  return [4, 6, 9, 11].includes(m) ? 30 : 31;
}

/** time_value: a text YYYY-MM-DDTHH:MM:SSZ that strptime reads and strftime writes back unchanged, read as UTC. A
 * year below 1000 is refused: strftime's %Y writes it without its leading zeros on Linux (a stated limit). */
export function timeValue(v: J): Time {
  if (typeof v !== 'string') throw new Round2Error('a time is not text');
  const m = TIME.exec(v);
  if (m === null) throw new Round2Error('a time is not YYYY-MM-DDTHH:MM:SSZ');
  const [y, mo, d, h, mi, s] = m.slice(1, 7).map((x) => Number(x)) as [number, number, number, number, number, number];
  if (!(y >= 1000 && mo >= 1 && mo <= 12 && d >= 1 && d <= daysInMonth(y, mo) && h <= 23 && mi <= 59 && s <= 59)) {
    throw new Round2Error('a time is not YYYY-MM-DDTHH:MM:SSZ');
  }
  return { text: v, secs: daysFromCivil(y, mo, d) * 86400 + h * 3600 + mi * 60 + s };
}

/** _lease_value: None stays None; otherwise an object with expires_at, read as a time. */
function leaseValue(v: J): Lease | null {
  if (v === null) return null;
  if (!isObj(v) || !v.has('expires_at')) throw new Round2Error('a lease is not an object with expires_at');
  return { entries: v as VObj, expires: timeValue(pget(v, 'expires_at')) };
}

/** [_lease_value(x) for x in case['leases']]: Python iterates a list, and also a text or an object, whose items (a
 * character, a key) are refused; so an empty text or object is an empty list, and anything else is refused. */
function leaseList(v: J): Lease[] {
  let items: J[];
  if (isList(v)) items = v;
  else if (typeof v === 'string' && v === '') items = [];
  else if (isObj(v) && v.size === 0) items = [];
  else throw new Round2Error('the leases cannot be read');
  return items.map((x) => {
    const lease = leaseValue(x);
    if (lease === null) throw new Round2Error('a lease is not a mapping');
    return lease;
  });
}

/** parse_input: ASCII, one JSON object with exactly append and reconcile, in its canonical text, each call and case
 * with exactly its keys. */
export function parseInput(bytes: Uint8Array): JObj {
  const codes: string[] = [];
  for (let k = 0; k < bytes.length; k++) {
    const b = bytes[k] as number;
    if (b > 0x7f) throw new Round2Error('not a round-2 input document: not ASCII');
    codes.push(String.fromCharCode(b));
  }
  const text = codes.join('');
  let doc: J;
  try {
    doc = parseJson(text);
  } catch (e) {
    throw new Round2Error('not a round-2 input document: not one JSON value');
  }
  if (!isObj(doc) || !keySetIs(doc, ['append', 'reconcile'])) {
    throw new Round2Error('not a round-2 input document: not one object with append and reconcile');
  }
  checkDepth(doc);
  if (canonicalText(doc) !== text) throw new Round2Error('not a round-2 input document: not its canonical text');
  const calls = pget(doc, 'append');
  for (const call of isList(calls) ? calls : [null]) {
    if (!isObj(call) || !keySetIs(call, CALL_KEYS)) {
      throw new Round2Error('not a round-2 input document: an append call without exactly its keys');
    }
  }
  const cases = pget(doc, 'reconcile');
  for (const c of isList(cases) ? cases : [null]) {
    if (!isObj(c) || !keySetIs(c, CASE_KEYS)) {
      throw new Round2Error('not a round-2 input document: a reconcile case without exactly its keys');
    }
  }
  return doc;
}

export type AppendEntry = {
  result: string; reason: string | null; findings: string[]; seq: number | bigint | null; line: string | null;
  record: { [key: string]: string } | null;
};
export type ReconcileEntry = { log: string; events: RecoveryResult['events']; expired: VObj[]; findings: string[] };

/** One append call over the carried log: [its entry, the log after it]. */
export function appendEntry(log: string, call: JObj): [AppendEntry, string] {
  const r: AppendResult = append(log, pget(call, 'event_type') as V, pget(call, 'payload') as V,
    pget(call, 'event_id') as V, timeValue(pget(call, 'appended_at')), pget(call, 'task_id') as V,
    pget(call, 'fencing_token') as V, pget(call, 'corrects') as V, leaseValue(pget(call, 'lease')),
    pget(call, 'recorder') as V, pget(call, 'record_id') as V);
  const entry: AppendEntry = {
    result: r.result, reason: r.reason, findings: r.findings, seq: r.seq, line: r.line, record: r.record,
  };
  return [entry, r.result === 'appended' ? r.log as string : log];
}

/** One reconcile case. */
export function reconcileEntry(c: JObj): ReconcileEntry {
  const log = pget(c, 'log');
  if (typeof log !== 'string') throw new Round2Error('a reconcile case whose log is not text');
  const leases = leaseList(pget(c, 'leases'));
  const r = reconcile(log, pget(c, 'commits') as V, leases, timeValue(pget(c, 'now')), pget(c, 'recorder') as V);
  return { log: r.log, events: r.events, expired: r.expired.map((x) => x.entries), findings: r.findings };
}

/** Every entry of the document, as values. */
export function computeEntries(doc: JObj): { append: AppendEntry[]; reconcile: ReconcileEntry[] } {
  let log = '';
  const outAppend: AppendEntry[] = [];
  for (const call of pget(doc, 'append') as J[]) {
    const [entry, next] = appendEntry(log, call as JObj);
    outAppend.push(entry);
    log = next;
  }
  const outReconcile: ReconcileEntry[] = [];
  for (const c of pget(doc, 'reconcile') as J[]) outReconcile.push(reconcileEntry(c as JObj));
  return { append: outAppend, reconcile: outReconcile };
}

/** The whole output document as text (ASCII, LF, one final LF); throws when it cannot be built. */
export function buildDocument(bytes: Uint8Array): string {
  const doc = parseInput(bytes);
  const entries = computeEntries(doc);
  const out = canonicalText(entries);
  for (let k = 0; k < out.length; k++) {
    if (out.charCodeAt(k) > 0x7f) throw new Round2Error('the document is not ASCII');
  }
  return out;
}

export type Result = { code: number; stdout: string; stderr: string };

/** The command line: exactly one argument, the input document's path; read is the one file reader (node:fs in
 * main2.ts, an in-memory reader in the tests). Never throws; on any failure stdout is empty and code is non-zero. */
export function runMain2(args: readonly string[], read: (path: string) => Uint8Array): Result {
  if (args.length !== 1) return { code: 2, stdout: '', stderr: USAGE };
  let bytes: Uint8Array;
  try {
    bytes = read(args[0] as string);
  } catch (e) {
    return { code: 1, stdout: '', stderr: 'round 2 failed: the input document cannot be read\n' };
  }
  try {
    return { code: 0, stdout: buildDocument(bytes), stderr: '' };
  } catch (e) {
    const what = e instanceof Error ? e.constructor.name + ': ' + e.message : 'an unknown failure';
    return { code: 1, stdout: '', stderr: 'round 2 failed: ' + what + '\n' };
  }
}

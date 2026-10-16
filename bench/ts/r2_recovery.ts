// Round 2: recovery.reconcile (TASK-009) with recovery.trailers, over a log given as ASCII text. Every event is built
// by r2_eventlog.append, one at a time, as the Python builds it by eventlog.append.

import type { V, VObj } from './r2_pyjson.ts';
import { R2Fail, isDict, isList, keysAre, get, reprStr } from './r2_pyjson.ts';
import { sha256Hex, utf8Encode } from './bytes.ts';
import { checkLog } from './r2_records.ts';
import type { Lease, Time } from './r2_eventlog.ts';
import { append, tokenText } from './r2_eventlog.ts';

const TASK = /^TASK-[0-9]+$/;
const COMMIT = /^[0-9a-f]{40}$/;
const COUNTER = /^[0-9]+$/;
const TASK_KEY = 'AIEOS-Task';
const FENCE_KEY = 'AIEOS-Fence';
const COMMIT_KEYS = ['commit', 'message'] as const;
const LEASE_KEYS = ['task_id', 'fencing_token', 'expires_at'] as const;
const ID_PREFIX = 'recovery';
const MAX_INT_DIGITS = 4300;
const SAFE = 9007199254740991n;

export type RecoveryEvent = { event_id: string; type: string; task_id: string; result: string };
export type RecoveryResult = { log: string; events: RecoveryEvent[]; expired: Lease[]; findings: string[] };

/** _id: the SHA-256 hex digest of "recovery", the commit id and the kind, joined by LF, as UTF-8. */
export function recoveryId(commit: string, kind: string): string {
  return sha256Hex(utf8Encode([ID_PREFIX, commit, kind].join('\n')));
}

/** str.strip() with no argument, for ASCII text: Python's whitespace (with \x1c to \x1f, which JavaScript's trim
 * leaves). */
function isPySpace(c: number): boolean {
  return c === 0x20 || (c >= 0x09 && c <= 0x0d) || (c >= 0x1c && c <= 0x1f);
}

function pyStrip(s: string): string {
  for (let k = 0; k < s.length; k++) {
    if (s.charCodeAt(k) > 0x7f) throw new R2Fail('a text outside ASCII');
  }
  let a = 0;
  let b = s.length;
  while (a < b && isPySpace(s.charCodeAt(a))) a++;
  while (b > a && isPySpace(s.charCodeAt(b - 1))) b--;
  return s.slice(a, b);
}

function stripLf(s: string): string {
  let a = 0;
  let b = s.length;
  while (a < b && s[a] === '\n') a++;
  while (b > a && s[b - 1] === '\n') b--;
  return s.slice(a, b);
}

/** str.partition(':') */
function partition(s: string): [string, string, string] {
  const k = s.indexOf(':');
  return k < 0 ? [s, '', ''] : [s.slice(0, k), ':', s.slice(k + 1)];
}

/** str.rpartition(':') */
function rpartition(s: string): [string, string, string] {
  const k = s.lastIndexOf(':');
  return k < 0 ? ['', '', s] : [s.slice(0, k), ':', s.slice(k + 1)];
}

export type Trailer = { task: string | null; fence: VObj | null };

/** trailers(message): the AIEOS-Task and AIEOS-Fence values of the last paragraph, and the findings. */
export function trailers(message: string): [Trailer, string[]] {
  const paragraphs = stripLf(message).split(/\n[ \t]*\n/).filter((p) => pyStrip(p) !== '');
  const last = paragraphs.length > 0 ? (paragraphs[paragraphs.length - 1] as string).split('\n') : [];
  const keys = new Map<string, string>([[TASK_KEY.toLowerCase(), TASK_KEY], [FENCE_KEY.toLowerCase(), FENCE_KEY]]);
  const found = new Map<string, string[]>([[TASK_KEY, []], [FENCE_KEY, []]]);
  const findings: string[] = [];
  for (const paragraph of paragraphs.slice(0, -1)) {
    for (const line of paragraph.split('\n')) {
      const [key, sep] = partition(line);
      if (sep !== '' && keys.has(pyStrip(key).toLowerCase())) {
        findings.push('trailer: ' + reprStr(pyStrip(key)) + ' is named outside the last paragraph');
      }
    }
  }
  for (const line of last) {
    const [key, sep, value] = partition(line);
    const name = pyStrip(key);
    if (!(sep !== '' && keys.has(name.toLowerCase()))) continue;
    const proper = keys.get(name.toLowerCase()) as string;
    if (name !== proper) {
      findings.push('trailer: ' + reprStr(name) + ' is not spelled ' + reprStr(proper));
      continue;
    }
    if (key !== name) findings.push('trailer: ' + reprStr(name) + ' is not at the start of its line');
    (found.get(name) as string[]).push(pyStrip(value));
  }
  const trailer: Trailer = { task: null, fence: null };
  for (const key of [TASK_KEY, FENCE_KEY]) {
    const n = (found.get(key) as string[]).length;
    if (n > 1) findings.push('trailer: ' + key + ' is given ' + n + ' times');
  }
  const tasks = found.get(TASK_KEY) as string[];
  if (tasks.length === 1) {
    const task = tasks[0] as string;
    if (TASK.test(task)) trailer.task = task;
    else findings.push('trailer: ' + TASK_KEY + ' ' + reprStr(task) + ' is not TASK- followed by digits');
  }
  const fences = found.get(FENCE_KEY) as string[];
  if (fences.length === 1) {
    const [epoch, sep, counter] = rpartition(fences[0] as string);
    if (sep !== '' && epoch !== '' && COUNTER.test(counter)) {
      // int(counter): Python refuses a text of more than 4300 digits with a ValueError of its own wording.
      if (counter.length > MAX_INT_DIGITS) throw new R2Fail('a counter Python would not convert');
      const b = BigInt(counter);
      trailer.fence = new Map<string, V>([['epoch', epoch], ['counter', b <= SAFE ? Number(b) : b]]);
    } else {
      findings.push('trailer: ' + FENCE_KEY + ' ' + reprStr(fences[0] as string) + ' is not <epoch>:<counter>');
    }
  }
  return [trailer, findings];
}

/** _check_arguments: any refusal is Python's TypeError or ValueError, which fails closed. */
function checkArguments(commits: V, leases: readonly Lease[], recorder: V): Array<{ commit: string; message: string }> {
  if (!isList(commits)) throw new R2Fail('the commits are not a list');
  const out: Array<{ commit: string; message: string }> = [];
  for (const c of commits) {
    if (!(isDict(c) && keysAre(c, COMMIT_KEYS))) throw new R2Fail('a commit is not exactly commit and message');
    const commit = get(c, 'commit');
    const message = get(c, 'message');
    if (!(typeof commit === 'string' && COMMIT.test(commit))) throw new R2Fail('a commit id is not 40 hex digits');
    if (typeof message !== 'string') throw new R2Fail('a commit message is not a string');
    out.push({ commit, message });
  }
  for (const lease of leases) {
    if (!keysAre(lease.entries, LEASE_KEYS)) throw new R2Fail('a lease without exactly its keys');
  }
  if (!(typeof recorder === 'string' && recorder !== '')) throw new R2Fail('the recorder is not a non-empty string');
  return out;
}

/** _submissions: (commit, task_id, token text) of each first task.submitted line of a log free of findings. */
function submissions(log: string): Array<[string, string, string | null]> {
  const out: Array<[string, string, string | null]> = [];
  for (const line of checkLog(log).lines) {
    const e = line.event;
    if (line.duplicateOf === null && e !== null && get(e, 'type') === 'task.submitted') {
      const payload = get(e, 'payload') as VObj;
      out.push([get(payload, 'commit') as string, get(e, 'task_id') as string, tokenText(get(e, 'fencing_token'))]);
    }
  }
  return out;
}

/** observation: the payload of the record.added event of an unfenced write. */
function observation(commit: string, taskId: string, recorder: string): VObj {
  return new Map<string, V>([
    ['record_id', recoveryId(commit, 'unfenced_write')], ['fact_kind', 'observation'],
    ['source_class', 'deterministic_tool_local'], ['recorder', recorder], ['subject', taskId],
    ['evidence_type', 'unfenced_write'], ['outcome', 'fail'], ['refers_to', commit]]);
}

function pairKey(taskId: string, token: string | null): string {
  return JSON.stringify([taskId, token]);
}

/** reconcile(log, commits, leases, now, recorder). */
export function reconcile(givenLog: string, commitsValue: V, leases: readonly Lease[], now: Time,
  recorderValue: V): RecoveryResult {
  const commits = checkArguments(commitsValue, leases, recorderValue);
  const recorder = recorderValue as string;
  let log = givenLog;
  const expired = leases.filter((lease) => !(lease.expires.secs > now.secs));
  const report = checkLog(log);
  const damaged = report.findings().map((f) => f.toString());
  if (log !== '' && !log.endsWith('\n')) damaged.push('2:lf: the log does not end with LF');
  if (damaged.length > 0) return { log, events: [], expired, findings: damaged.map((f) => 'log: ' + f) };

  const findings: string[] = [];
  const events: RecoveryEvent[] = [];
  const given = new Set(commits.map((c) => c.commit));
  const submitted = submissions(log);
  // Step 2: Git wins.
  for (const [commit, taskId] of submitted) {
    if (!given.has(commit)) {
      findings.push('step 2: the log\'s task.submitted of ' + taskId + ' names the commit ' + commit + ', which is '
        + 'not among the given commits; nothing is appended');
    }
  }
  const named = new Set(submitted.map(([commit]) => commit));
  const used = new Set(submitted.map(([, taskId, token]) => pairKey(taskId, token)));

  const add = (eventType: string, payload: VObj, eventId: string, taskId: string, fencingToken: V = null,
    lease: Lease | null = null): boolean => {
    const r = append(log, eventType, payload, eventId, now, taskId, fencingToken, null, lease, recorder,
      recoveryId(eventId, 'refused_submission'));
    if (r.result === 'refused') {
      findings.push('step 1: eventlog.append refused the ' + eventType + ' of ' + taskId + ' (reason '
        + (r.reason as string) + '): ' + r.findings.join('; '));
      return false;
    }
    if (r.result === 'appended') log = r.log as string;
    events.push({ event_id: eventId, type: eventType, task_id: taskId, result: r.result });
    return true;
  };

  // Step 1, oldest first.
  for (const c of commits) {
    const [trailer, bad] = trailers(c.message);
    if (bad.length > 0) {
      for (const f of bad) findings.push('commit ' + c.commit + ': ' + f);
      continue;
    }
    const taskId = trailer.task;
    if (taskId === null || named.has(c.commit)) continue;
    const token = trailer.fence !== null ? tokenText(trailer.fence) : null;
    let lease: Lease | null = null;
    if (token !== null && !used.has(pairKey(taskId, token))) {
      for (const held of leases) {
        const heldTask = get(held.entries, 'task_id');
        if (typeof heldTask === 'string' && heldTask === taskId
            && tokenText(get(held.entries, 'fencing_token')) === token && held.expires.secs > now.secs) {
          lease = held;
          break;
        }
      }
    }
    if (lease !== null) {
      const payload = new Map<string, V>([['commit', c.commit], ['compensating', true]]);
      if (add('task.submitted', payload, recoveryId(c.commit, 'task.submitted'), taskId, trailer.fence, lease)) {
        used.add(pairKey(taskId, token));
        named.add(c.commit);
      }
    } else {
      add('record.added', observation(c.commit, taskId, recorder), recoveryId(c.commit, 'record.added'), taskId);
    }
  }
  return { log, events, expired, findings };
}

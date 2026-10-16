// Round 2: eventlog.append (TASK-007, TASK-015), over a log given as ASCII text, returning the AppendResult's fields.

import type { V, VObj } from './r2_pyjson.ts';
import { R2Fail, DumpsError, isStr, get, keysAre, dumps, pyRepr, reprStr } from './r2_pyjson.ts';
import { checkLog, checkFence, checkPayload, matches, TASK } from './r2_records.ts';

/** A UTC time read from its text YYYY-MM-DDTHH:MM:SSZ: the text (which is also its strftime form) and its seconds. */
export type Time = { readonly text: string; readonly secs: number };

/** A lease as the bootstrap is given it: the input's object, its expires_at read as a Time. */
export type Lease = { readonly entries: VObj; readonly expires: Time };

export type AppendResult = {
  result: 'appended' | 'duplicate' | 'refused';
  reason: string | null;
  seq: number | bigint | null;
  line: string | null;
  log: string | null;
  findings: string[];
  record: { [key: string]: string } | null;
};

const LEASE_KEYS = ['task_id', 'fencing_token', 'expires_at'] as const;
const SAME_EVENT_KEYS = ['type', 'payload', 'task_id', 'fencing_token', 'corrects'] as const;

function refused(reason: string, findings: string[], seq: number | bigint | null = null,
  record: { [key: string]: string } | null = null): AppendResult {
  return { result: 'refused', reason, seq, line: null, log: null, findings, record };
}

/** _canonical: json.dumps(sort_keys, compact, ensure_ascii, allow_nan=False). */
function canonical(v: V): string {
  return dumps(v, false);
}

/** _same_text and _token_text: the canonical text, or None when json.dumps raises its ValueError. */
function textOrNone(v: V): string | null {
  try {
    return canonical(v);
  } catch (e) {
    if (e instanceof DumpsError) return null;
    throw e;
  }
}

function sameText(obj: VObj): string | null {
  const m: VObj = new Map();
  for (const k of SAME_EVENT_KEYS) if (obj.has(k)) m.set(k, get(obj, k));
  return textOrNone(m);
}

export const tokenText = textOrNone;

/** _needs_lease. */
function needsLease(eventType: V, fencingToken: V): boolean {
  return fencingToken !== null || eventType === 'task.submitted';
}

/** refusal_record: the payload of the record.added event of a fence refusal. */
export function refusalRecord(eventId: string, taskId: string, recorder: string, recordId: string):
  { [key: string]: string } {
  return {
    record_id: recordId, fact_kind: 'observation', source_class: 'deterministic_tool_local', recorder,
    subject: taskId, evidence_type: 'refused_submission', outcome: 'fail', refers_to: eventId,
  };
}

/** _lease_findings: why the lease given does not hold the event; empty when it does. */
function leaseFindings(lease: Lease | null, taskId: string, fencingToken: V, appendedAt: Time): string[] {
  if (lease === null) return ['fence: no lease is given'];
  if (!keysAre(lease.entries, LEASE_KEYS)) {
    return ['fence: the lease is not a mapping with exactly task_id, fencing_token and expires_at'];
  }
  const found: string[] = [];
  if (fencingToken === null) found.push('fence: the event carries no fencing_token');
  const leaseTask = get(lease.entries, 'task_id');
  if (!(typeof leaseTask === 'string' && leaseTask === taskId)) {
    found.push('fence: the lease is on ' + pyRepr(leaseTask) + ', not on the event\'s task ' + reprStr(taskId));
  }
  const leaseToken = tokenText(get(lease.entries, 'fencing_token'));
  if (fencingToken !== null && (leaseToken === null || leaseToken !== tokenText(fencingToken))) {
    found.push('fence: the event\'s fencing_token is not the lease\'s');
  }
  // expires_at is always a timezone-aware UTC datetime here: the reader made it one.
  if (!(lease.expires.secs > appendedAt.secs)) found.push('fence: the lease expired at or before the append time');
  return found;
}

/** eventlog.append(log, event_type, payload, event_id, appended_at, task_id, fencing_token, corrects, lease, recorder,
 * record_id); None is null. */
export function append(log: string, eventType: V, payload: V, eventId: V, appendedAt: Time, taskId: V,
  fencingToken: V, corrects: V, lease: Lease | null, recorder: V, recordId: V): AppendResult {
  // AC1: the given log.
  const report = checkLog(log);
  const logFindings = report.findings().map((f) => f.toString());
  if (log !== '' && !log.endsWith('\n')) logFindings.push('2:lf: the log does not end with LF');
  if (logFindings.length > 0) return refused('log', logFindings);

  // AC2: idempotency by event_id, against the first line that holds it.
  const newEvent: VObj = new Map<string, V>([['type', eventType], ['payload', payload]]);
  if (taskId !== null) newEvent.set('task_id', taskId);
  if (fencingToken !== null) newEvent.set('fencing_token', fencingToken);
  if (corrects !== null) newEvent.set('corrects', corrects);
  const knownIds = new Set<string>();
  for (const line of report.lines) {
    const old = line.event as VObj;
    const oldId = get(old, 'event_id') as string;
    knownIds.add(oldId);
    if (line.duplicateOf === null && typeof eventId === 'string' && oldId === eventId) {
      const oldSeq = get(old, 'seq') as number | bigint;
      const a = sameText(old);
      if (a !== null && a === sameText(newEvent)) {
        return { result: 'duplicate', reason: null, seq: oldSeq, line: null, log: null, findings: [], record: null };
      }
      return refused('conflict', ['event_id ' + reprStr(eventId) + ' is on the line with seq ' + oldSeq.toString()
        + ' with another event'], oldSeq);
    }
  }

  // AC3: the new event's own form (appended_at is always a UTC time here: the reader made it one).
  const findings: string[] = [];
  if (!isStr(eventId)) findings.push('6.1:event_id: event_id is not a non-empty string');
  if (taskId !== null && !matches(TASK, taskId)) {
    findings.push('6.1:task_id: task_id is not TASK- followed by digits (reading)');
  }
  if (fencingToken !== null) {
    findings.push(...checkFence(new Map<string, V>([['fencing_token', fencingToken]]), null).map((f) => f.toString()));
  }
  if (corrects !== null && !(isStr(corrects) && knownIds.has(corrects))) {
    findings.push('6.1:corrects: corrects is not the event_id of a line of the log (reading)');
  }
  findings.push(...checkPayload(eventType, payload).map((f) => f.toString()));
  let line = '';
  if (findings.length === 0) {
    const obj: VObj = new Map(newEvent);
    obj.set('event_id', eventId);
    obj.set('appended_at', appendedAt.text);
    obj.set('seq', report.lines.length + 1);
    try {
      line = canonical(obj) + '\n';
    } catch (e) {
      // "the event cannot be written as one JSON text (<Python's message>)": not reached by a JSON input.
      throw new R2Fail('an event that json.dumps refuses');
    }
  }
  if (findings.length > 0) return refused('event', findings);

  // AC6, AC7: the fence.
  if (needsLease(eventType, fencingToken)) {
    const fence = taskId === null
      ? ['fence: the event names no task_id, so no lease can be on its task']
      : leaseFindings(lease, taskId as string, fencingToken, appendedAt);
    if (fence.length > 0) {
      if (taskId === null) return refused('fence', [...fence, 'fence: no refusal record, the event names no task_id']);
      if (!(isStr(recorder) && isStr(recordId))) {
        return refused('fence', [...fence, 'fence: no refusal record, recorder and record_id are not both '
          + 'non-empty strings']);
      }
      return refused('fence', fence, null, refusalRecord(eventId as string, taskId as string, recorder, recordId));
    }
  }

  // AC4: the whole log after the append.
  const newLog = log + line;
  const after = checkLog(newLog).findings().map((f) => f.toString());
  if (after.length > 0) return refused('log_after', after);

  // AC5: the given text is an exact prefix, followed by exactly one line.
  if (!(newLog.startsWith(log) && newLog.slice(log.length) === line && line.split('\n').length === 2)) {
    throw new R2Fail('the append-only property failed');
  }
  return { result: 'appended', reason: null, seq: report.lines.length + 1, line, log: newLog, findings: [], record: null };
}

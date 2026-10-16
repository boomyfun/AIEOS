// Round 2's own tests: `node test2.ts <round-2 input document> <round-2 reference document>`. They read only those two
// paths (every other input is built in memory and given to runMain2 through an in-memory reader), print each result
// and exit non-zero on any failure. Only these tests read the reference document, as the expected output.

import { readFileSync } from 'node:fs';
import process from 'node:process';
import type { J, JObj } from './json.ts';
import { parseJson, canon, canonicalText, isObj, pget } from './json.ts';
import type { V } from './r2_pyjson.ts';
import { pyLoads, pyRepr, floatRepr, dumps, PyFloat, PyMalformed, R2Fail } from './r2_pyjson.ts';
import { checkLog } from './r2_records.ts';
import { trailers } from './r2_recovery.ts';
import { runMain2, parseInput, computeEntries, appendEntry, reconcileEntry, timeValue } from './r2_document.ts';

let failures = 0;
let passes = 0;

function ok(name: string, cond: boolean, detail: string = ''): void {
  if (cond) {
    passes++;
    process.stdout.write('PASS ' + name + '\n');
  } else {
    failures++;
    process.stdout.write('FAIL ' + name + (detail !== '' ? ': ' + detail : '') + '\n');
  }
}

function ascii(s: string): Uint8Array {
  const out = new Uint8Array(s.length);
  for (let k = 0; k < s.length; k++) out[k] = s.charCodeAt(k) & 0xff;
  return out;
}

function text(b: Uint8Array): string {
  let s = '';
  for (let k = 0; k < b.length; k++) s += String.fromCharCode(b[k] as number);
  return s;
}

function bytesEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  for (let k = 0; k < a.length; k++) if (a[k] !== b[k]) return false;
  return true;
}

function firstDiff(a: string, b: string): number {
  const n = Math.min(a.length, b.length);
  for (let k = 0; k < n; k++) if (a[k] !== b[k]) return k;
  return a.length === b.length ? -1 : n;
}

function throwsKind(f: () => unknown, kind: Function): boolean {
  try {
    f();
  } catch (e) {
    return e instanceof kind;
  }
  return false;
}

/** A field of a computed entry, in the canonical text, against the same field of the reference entry. */
function sameField(computed: unknown, reference: J): boolean {
  return canon(computed) === canon(reference);
}

const args = process.argv.slice(2);
if (args.length !== 2) {
  process.stderr.write('usage: node test2.ts <round-2 input document> <round-2 reference document>\n');
  process.exitCode = 2;
} else {
  const inputPath = args[0] as string;
  const inputBytes = readFileSync(inputPath);
  const referenceBytes = readFileSync(args[1] as string);
  const referenceText = text(referenceBytes);
  const reference = parseJson(referenceText) as JObj;
  const refAppend = pget(reference, 'append') as J[];
  const refReconcile = pget(reference, 'reconcile') as J[];
  const input = parseInput(inputBytes);
  const calls = pget(input, 'append') as JObj[];
  const cases = pget(input, 'reconcile') as JObj[];

  const files = new Map<string, Uint8Array>();
  files.set(inputPath, inputBytes);
  const read = (p: string): Uint8Array => {
    const b = files.get(p);
    if (b === undefined) throw new Error('no such file: ' + p);
    return b;
  };

  // 1. The byte equality over the whole input.
  const whole = runMain2([inputPath], read);
  ok('whole input: exit 0 and nothing on stderr', whole.code === 0 && whole.stderr === '', whole.stderr);
  ok('whole input: byte-equal to the reference', bytesEqual(ascii(whole.stdout), referenceBytes)
    && whole.stdout.length === referenceBytes.length,
    'first difference at ' + firstDiff(whole.stdout, referenceText));
  ok('whole input: ASCII, LF only, one final LF', /^[\x00-\x7f]*$/.test(whole.stdout) && !whole.stdout.includes('\r')
    && whole.stdout.endsWith('}\n') && !whole.stdout.endsWith('\n\n'));
  ok('whole input: a second run gives the same bytes', runMain2([inputPath], read).stdout === whole.stdout);

  // 2. One append call field by field: call 5, a submission with no lease, refused by the fence with its record.
  {
    let log = '';
    for (let k = 0; k < 5; k++) log = appendEntry(log, calls[k] as JObj)[1];
    const [entry, after] = appendEntry(log, calls[5] as JObj);
    const ref = refAppend[5] as JObj;
    for (const key of ['result', 'reason', 'findings', 'seq', 'line', 'record'] as const) {
      ok('append call 5: field ' + key, sameField(entry[key], pget(ref, key)), canon(entry[key]));
    }
    ok('append call 5: the result is refused by the fence', entry.result === 'refused' && entry.reason === 'fence');
    ok('append call 5: its record names the call\'s record_id and event_id', entry.record !== null
      && entry.record['record_id'] === pget(calls[5] as JObj, 'record_id')
      && entry.record['refers_to'] === pget(calls[5] as JObj, 'event_id'));
    ok('append call 5: the refused call leaves the log as it was', after === log);
  }
  // and call 0, appended, field by field
  {
    const [entry] = appendEntry('', calls[0] as JObj);
    const ref = refAppend[0] as JObj;
    for (const key of ['result', 'reason', 'findings', 'seq', 'line', 'record'] as const) {
      ok('append call 0: field ' + key, sameField(entry[key], pget(ref, key)), canon(entry[key]));
    }
  }

  // 3. One reconcile case field by field: case 0, a compensating submission under a lease that holds.
  {
    const entry = reconcileEntry(cases[0] as JObj);
    const ref = refReconcile[0] as JObj;
    for (const key of ['log', 'events', 'expired', 'findings'] as const) {
      ok('reconcile case 0: field ' + key, sameField(entry[key], pget(ref, key)), canon(entry[key]));
    }
    ok('reconcile case 0: one task.submitted appended', entry.events.length === 1
      && entry.events[0]?.type === 'task.submitted' && entry.events[0]?.result === 'appended');
    ok('reconcile case 0: the log grows by exactly one line', entry.log.startsWith(pget(cases[0] as JObj, 'log') as string)
      && entry.log.slice((pget(cases[0] as JObj, 'log') as string).length).split('\n').length === 2);
  }
  // every reconcile case, field by field
  {
    for (let k = 0; k < cases.length; k++) {
      const entry = reconcileEntry(cases[k] as JObj);
      ok('reconcile case ' + k + ': all fields', sameField(entry, refReconcile[k] as J));
    }
  }

  // 4. The carried log: an entry after an appended one and after a refused one.
  {
    const entries = computeEntries(input).append;
    ok('carried log: call 0 appended at seq 1', entries[0]?.result === 'appended' && entries[0]?.seq === 1);
    ok('carried log: call 1, after an appended call, is appended at seq 2', entries[1]?.result === 'appended'
      && entries[1]?.seq === 2 && sameField(entries[1], refAppend[1] as J));
    ok('carried log: call 2 is a duplicate of seq 1 (the log holds call 0)', entries[2]?.result === 'duplicate'
      && entries[2]?.seq === 1 && sameField(entries[2], refAppend[2] as J));
    ok('carried log: call 5 is refused', entries[5]?.result === 'refused');
    ok('carried log: call 6, after a refused call, is appended at seq 3', entries[6]?.result === 'appended'
      && entries[6]?.seq === 3 && sameField(entries[6], refAppend[6] as J));
    ok('carried log: call 12, after the refused call 11, is appended at seq 6', entries[11]?.result === 'refused'
      && entries[12]?.result === 'appended' && entries[12]?.seq === 6 && sameField(entries[12], refAppend[12] as J));
    let log = '';
    let lastSeq = 0;
    let monotone = true;
    for (let k = 0; k < calls.length; k++) {
      const [entry, next] = appendEntry(log, calls[k] as JObj);
      if (entry.result === 'appended') {
        if (!(next === log + entry.line && entry.seq === lastSeq + 1)) monotone = false;
        lastSeq = entry.seq as number;
      } else if (next !== log) {
        monotone = false;
      }
      log = next;
    }
    ok('carried log: an appended call extends the log by its line, any other leaves it', monotone);
    let matching = true;
    for (let k = 0; k < entries.length; k++) if (!sameField(entries[k], refAppend[k] as J)) matching = false;
    ok('carried log: every append entry equals the reference entry', matching && entries.length === refAppend.length);
  }

  // 5. Each fail-closed input: nothing on standard output, a non-zero exit, and standard error naming the cause.
  const failClosed = (name: string, argv: string[], cause: string): void => {
    const r = runMain2(argv, read);
    ok('fail closed: ' + name, r.code !== 0 && r.stdout === '' && r.stderr.includes(cause),
      'code ' + r.code + ', stdout ' + r.stdout.length + ', stderr ' + r.stderr.trim());
  };
  const withFile = (name: string, content: string | Uint8Array, cause: string): void => {
    const path = 'in-memory/' + name;
    files.set(path, typeof content === 'string' ? ascii(content) : content);
    failClosed(name, [path], cause);
  };
  const docWith = (change: (doc: JObj) => void): string => {
    const doc = parseJson(text(inputBytes)) as JObj;
    change(doc);
    return canonicalText(doc);
  };
  const callWith = (index: number, key: string, value: J): string => docWith((doc) => {
    ((pget(doc, 'append') as J[])[index] as JObj).set(key, value);
  });
  const caseWith = (index: number, key: string, value: J): string => docWith((doc) => {
    ((pget(doc, 'reconcile') as J[])[index] as JObj).set(key, value);
  });

  failClosed('a missing argument', [], 'usage: node main2.ts');
  failClosed('an extra argument', [inputPath, inputPath], 'usage: node main2.ts');
  failClosed('a path that cannot be read', ['in-memory/no-such-file.json'], 'cannot be read');
  withFile('empty', '', 'not one JSON value');
  withFile('not-json', 'not json', 'not one JSON value');
  withFile('a-list', '[]\n', 'not one object with append and reconcile');
  withFile('an-empty-object', '{}\n', 'not one object with append and reconcile');
  withFile('an-extra-key', '{\n  "append": [],\n  "reconcile": [],\n  "x": 1\n}\n',
    'not one object with append and reconcile');
  withFile('a-repeated-key', '{"append":[],"append":[],"reconcile":[]}\n', 'not one JSON value');
  withFile('not-canonical', JSON.stringify({ append: [], reconcile: [] }) + '\n', 'not its canonical text');
  withFile('no-final-lf', docWith(() => undefined).slice(0, -1), 'not its canonical text');
  withFile('crlf', docWith(() => undefined).replace(/\n/g, '\r\n'), 'not its canonical text');
  {
    const b = new Uint8Array(inputBytes.length + 1);
    b.set(inputBytes.subarray(0, 10));
    b[10] = 0xc3;
    b.set(inputBytes.subarray(10), 11);
    withFile('not-ascii', b, 'not ASCII');
  }
  withFile('a-call-without-its-keys', docWith((doc) => {
    doc.set('append', [new Map<string, J>([['event_type', 'task.done']])]);
  }), 'an append call without exactly its keys');
  withFile('a-case-without-its-keys', docWith((doc) => {
    doc.set('reconcile', [new Map<string, J>([['log', '']])]);
  }), 'a reconcile case without exactly its keys');
  withFile('append-not-a-list', docWith((doc) => {
    doc.set('append', new Map<string, J>());
  }), 'an append call without exactly its keys');
  withFile('a-float', docWith(() => undefined).replace('"counter": 0', '"counter": 0.5'), 'not one JSON value');
  // Calls and cases that cannot be computed.
  withFile('a-time-not-of-the-form', callWith(0, 'appended_at', '2026-01-01 00:00:00'), 'a time is not');
  withFile('a-time-not-on-the-calendar', callWith(0, 'appended_at', '2026-02-30T00:00:00Z'), 'a time is not');
  withFile('a-leap-second', callWith(0, 'appended_at', '2026-01-01T00:00:60Z'), 'a time is not');
  withFile('a-lease-without-expires_at', callWith(6, 'lease', new Map<string, J>([['task_id', 'TASK-1000']])),
    'a lease is not an object with expires_at');
  withFile('an-event_type-python-cannot-hash', callWith(4, 'event_type', ['task.done']), 'cannot hash');
  withFile('reconcile-commits-not-a-list', caseWith(0, 'commits', 'none'), 'the commits are not a list');
  withFile('reconcile-log-not-text', caseWith(0, 'log', 5), 'whose log is not text');
  withFile('reconcile-recorder-empty', caseWith(0, 'recorder', ''), 'the recorder is not a non-empty string');
  withFile('reconcile-leases-not-a-list', caseWith(0, 'leases', 'abc'), 'the leases cannot be read');
  withFile('reconcile-a-lease-null', caseWith(0, 'leases', [null]), 'a lease is not a mapping');
  withFile('reconcile-a-commit-id-not-hex', caseWith(1, 'commits', [new Map<string, J>([
    ['commit', 'x'.repeat(40)], ['message', 'm']])]), 'a commit id is not 40 hex digits');
  // The texts that name a Python type, and the scanner's own messages: failed closed (brief 6.3).
  withFile('reconcile-a-log-line-that-is-a-list', caseWith(0, 'log', '[1]\n'), 'other than an object');
  withFile('reconcile-a-log-line-that-is-not-json', caseWith(0, 'log', '{"a":\n'), 'JSONDecodeError');
  withFile('reconcile-an-empty-log-line', caseWith(0, 'log', '\n'), 'JSONDecodeError');
  // and the empty leases Python reads from an empty text: computed, not refused
  {
    const path = 'in-memory/reconcile-leases-an-empty-text';
    files.set(path, ascii(caseWith(1, 'leases', '')));
    const r = runMain2([path], read);
    ok('an empty text as the leases is read as no lease, as Python iterates it', r.code === 0
      && r.stdout === whole.stdout, r.stderr);
  }

  // 6. The ports of Python's own forms that the reference does not reach.
  ok('json: a repeated key is records._Malformed with Python\'s text', (() => {
    try {
      pyLoads('{"a":1,"b":2,"a":3}');
    } catch (e) {
      return e instanceof PyMalformed && e.message === 'repeated key \'a\'';
    }
    return false;
  })());
  ok('json: NaN is records._Malformed', throwsKind(() => pyLoads('{"a":NaN}'), PyMalformed));
  ok('json: a decode error fails closed', throwsKind(() => pyLoads('{"a":1,}'), R2Fail));
  ok('json: 1.0 is a float, 1 an integer', pyLoads('[1.0,1]') instanceof Array
    && (pyLoads('[1.0,1]') as V[])[0] instanceof PyFloat && (pyLoads('[1.0,1]') as V[])[1] === 1);
  ok('repr: floats as Python writes them', floatRepr(1e16) === '1e+16' && floatRepr(1e15) === '1000000000000000.0'
    && floatRepr(0.0001) === '0.0001' && floatRepr(0.00001) === '1e-05' && floatRepr(-0) === '-0.0'
    && floatRepr(1.5) === '1.5' && floatRepr(123.0) === '123.0');
  ok('repr: values as Python writes them', pyRepr(new Map<string, V>([['a', [1, true, null]], ['b', 'it\'s']]))
    === '{\'a\': [1, True, None], \'b\': "it\'s"}' && pyRepr('a\tb\x7f') === '\'a\\tb\\x7f\'');
  ok('repr: a character outside ASCII fails closed', throwsKind(() => pyRepr('é'), R2Fail));
  ok('dumps: compact, sorted, ASCII escapes', dumps(new Map<string, V>([['b', 'x\n\u007f'], ['a', 1]]), false)
    === '{"a":1,"b":"x\\n\\u007f"}');
  ok('check_log: a damaged seq', checkLog('{"appended_at":"2026-01-01T00:00:00Z","event_id":"a","payload":'
    + '{"decision_record":"d"},"seq":2,"task_id":"TASK-1","type":"task.done"}\n').findings().map(String).join('|')
    === '6.1:seq: seq is 2; expected 1');
  ok('check_log: a repeated key is a finding', checkLog('{"a":1,"a":2}\n').findings().map(String).join('|')
    === '6.1:json: the line is not one JSON object (repeated key \'a\')');
  ok('trailers: a key outside the last paragraph and a bad fence', (() => {
    const [t, f] = trailers('AIEOS-Task: TASK-1\n\nAIEOS-Task: TASK-2\nAIEOS-Fence: x');
    return t.task === 'TASK-2' && t.fence === null && f.join('|') === 'trailer: \'AIEOS-Task\' is named outside the '
      + 'last paragraph|trailer: AIEOS-Fence \'x\' is not <epoch>:<counter>';
  })());
  ok('time: a year below 1000 is refused', (() => {
    try {
      timeValue('0999-01-01T00:00:00Z');
    } catch (e) {
      return true;
    }
    return false;
  })());
  ok('input: the reference document itself is not an input document', (() => {
    try {
      parseInput(referenceBytes);
    } catch (e) {
      return true;
    }
    return false;
  })());
  ok('input: the input document is read back in its canonical text', canonicalText(input) === text(inputBytes)
    && isObj(input));

  process.stdout.write(passes + ' passed, ' + failures + ' failed\n');
  process.exitCode = failures === 0 ? 0 : 1;
}

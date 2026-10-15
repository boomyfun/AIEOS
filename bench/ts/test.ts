// The port's own tests: `node test.ts <fixture document> <reference document>`. They read only those two paths (the
// other inputs are built in memory and given to runMain through an in-memory reader), print each result and exit
// non-zero on any failure.

import { readFileSync } from 'node:fs';
import process from 'node:process';
import type { J, JObj } from './json.ts';
import { parseJson, canon, canonicalText, isObj, isList, pget } from './json.ts';
import { utf8Decode, utf8Encode, sha256Text } from './bytes.ts';
import { runMain } from './export.ts';
import { evaluate } from './governor.ts';
import { check } from './resume_check.ts';

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

function bytesEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false;
  return true;
}

function firstDiff(a: string, b: string): number {
  const n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i++) if (a[i] !== b[i]) return i;
  return a.length === b.length ? -1 : n;
}

const args = process.argv.slice(2);
if (args.length !== 2) {
  process.stderr.write('usage: node test.ts <fixture document> <reference document>\n');
  process.exitCode = 2;
} else {
  const fixturePath = args[0] as string;
  const fixtureBytes = readFileSync(fixturePath);
  const referenceBytes = readFileSync(args[1] as string);
  const referenceText = utf8Decode(referenceBytes);
  const reference = parseJson(referenceText) as JObj;
  const fixtures = parseJson(utf8Decode(fixtureBytes)) as JObj;

  // An in-memory reader: the real fixture document under its own path, the made-up inputs under made-up names.
  const files = new Map<string, Uint8Array>();
  files.set(fixturePath, fixtureBytes);
  const read = (p: string): Uint8Array => {
    const b = files.get(p);
    if (b === undefined) throw new Error('no such file: ' + p);
    return b;
  };

  // 0. The primitives.
  ok('sha256 of "abc"',
    sha256Text('abc') === 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
  ok('sha256 of the empty text',
    sha256Text('') === 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');

  // 1. Byte equality over the whole fixture document.
  const run = runMain([fixturePath], read);
  ok('exit code 0 on the fixture document', run.code === 0, 'code ' + run.code + ' ' + run.stderr);
  const outBytes = utf8Encode(run.stdout);
  const equal = bytesEqual(outBytes, referenceBytes);
  const at = firstDiff(run.stdout, referenceText);
  ok('the output is byte-equal to the reference document', equal,
    'first difference at offset ' + at + ': ' + JSON.stringify(run.stdout.slice(Math.max(0, at - 80), at + 80)));
  ok('the output is ASCII with LF line ends and one final LF',
    outBytes.every((x) => x < 128) && !run.stdout.includes('\r') && run.stdout.endsWith('}\n'));

  const out = parseJson(run.stdout) as JObj;
  const keys = [...out.keys()];
  ok('30 keys: 19 governor and 11 Resume Check', keys.length === 30
    && keys.filter((k) => k.startsWith('fixtures/')).length === 19
    && keys.filter((k) => k.startsWith('fixtures_rc/')).length === 11, String(keys.length));

  // 2. One governor case field by field.
  function fieldByField(name: string, computed: unknown, expected: J): void {
    const want = expected as JObj;
    const got = parseJson(canonicalText(computed)) as JObj;
    const all = new Set<string>([...want.keys(), ...got.keys()]);
    const bad: string[] = [];
    for (const k of all) {
      if (!want.has(k) || !got.has(k) || canon(want.get(k)) !== canon(got.get(k))) bad.push(k);
    }
    ok(name + ': every field equals the reference (' + all.size + ' fields)', bad.length === 0, bad.join(', '));
  }
  const accCase = (pget(pget(fixtures, 'fixtures/acc_13') as JObj, 'cases') as J[])[2] as JObj;
  fieldByField('governor case fixtures/acc_13 case 3',
    evaluate(pget(accCase, 'request'), pget(accCase, 'inputs'), pget(accCase, 'records')),
    (pget(reference, 'fixtures/acc_13') as J[])[2] as J);
  const acc1 = (pget(pget(fixtures, 'fixtures/acc_01') as JObj, 'cases') as J[])[0] as JObj;
  const acc1Rec = evaluate(pget(acc1, 'request'), pget(acc1, 'inputs'), pget(acc1, 'records'));
  const acc1Ref = (pget(reference, 'fixtures/acc_01') as J[])[0] as JObj;
  ok('governor case fixtures/acc_01: decision', acc1Rec['decision'] === pget(acc1Ref, 'decision'));
  ok('governor case fixtures/acc_01: next_task_state', acc1Rec['next_task_state'] === pget(acc1Ref, 'next_task_state'));
  ok('governor case fixtures/acc_01: record_id', acc1Rec['record_id'] === pget(acc1Ref, 'record_id'));

  // 3. One Resume Check case field by field.
  const rcCase = (pget(pget(fixtures, 'fixtures_rc/rc_01') as JObj, 'cases') as J[])[0] as JObj;
  const rcRec = check(pget(rcCase, 'inputs'));
  fieldByField('Resume Check case fixtures_rc/rc_01 case 1', rcRec, (pget(reference, 'fixtures_rc/rc_01') as J[])[0] as J);
  const rcRef = (pget(reference, 'fixtures_rc/rc_01') as J[])[0] as JObj;
  ok('Resume Check case fixtures_rc/rc_01: decision', rcRec['decision'] === pget(rcRef, 'decision'));
  ok('Resume Check case fixtures_rc/rc_01: record_id', rcRec['record_id'] === pget(rcRef, 'record_id'));

  // 4. The placeholder: in every record that has engine_identity.python, and nowhere else.
  let rcRecords = 0;
  let placed = 0;
  let governorWithEngine = 0;
  for (const [key, recs] of out) {
    for (const r of recs as J[]) {
      const ident = pget(r as JObj, 'engine_identity');
      if (key.startsWith('fixtures_rc/')) {
        rcRecords++;
        if (isObj(ident) && pget(ident, 'python') === '<engine>' && pget(ident, 'code_sha256') === null) placed++;
      } else if (ident !== null) {
        governorWithEngine++;
      }
    }
  }
  ok('the placeholder is in every Resume Check record', rcRecords === 11 && placed === rcRecords,
    placed + ' of ' + rcRecords);
  ok('no governor record has engine_identity', governorWithEngine === 0);
  ok('"<engine>" appears only as engine_identity.python',
    run.stdout.split('<engine>').length - 1 === rcRecords
    && run.stdout.split('"python": "<engine>"').length - 1 === rcRecords);

  // 5. Each fail-closed input.
  function failsClosed(name: string, argv: string[]): void {
    const r = runMain(argv, read);
    ok('fails closed: ' + name, r.code !== 0 && r.stdout === '', 'code ' + r.code + ', ' + r.stdout.length
      + ' bytes on stdout');
  }
  function withFile(name: string, path: string, bytes: Uint8Array): void {
    files.set(path, bytes);
    failsClosed(name, [path]);
  }
  function mutated(change: (doc: JObj) => void): Uint8Array {
    const doc = parseJson(utf8Decode(fixtureBytes)) as JObj;
    change(doc);
    return utf8Encode(canonicalText(doc));
  }
  failsClosed('no argument', []);
  failsClosed('two arguments', [fixturePath, fixturePath]);
  failsClosed('a file that cannot be read', ['missing.json']);
  withFile('a file that is not JSON', 'not-json.json', utf8Encode('{"fixtures/acc_01": \n'));
  withFile('a file that is not UTF-8', 'not-utf8.json', Uint8Array.from([0x7b, 0xff, 0x7d, 0x0a]));
  withFile('a JSON list, not a fixture document', 'list.json', utf8Encode('[]\n'));
  withFile('a document without its final LF', 'no-lf.json', fixtureBytes.subarray(0, fixtureBytes.length - 1));
  withFile('a document with CR LF line ends', 'crlf.json',
    utf8Encode(utf8Decode(fixtureBytes).split('\n').join('\r\n')));
  const fixtureText = utf8Decode(fixtureBytes);
  ok('the fraction test has a number to change', fixtureText.includes('"used": 0\n'));
  withFile('a number with a fraction', 'float.json', utf8Encode(fixtureText.replace('"used": 0\n', '"used": 0.0\n')));
  withFile('a key that is not "<folder>/<stem>"', 'bad-key.json', mutated((d) => {
    d.set('other/acc_99', pget(d, 'fixtures/acc_01'));
  }));
  withFile('no Resume Check fixture', 'no-rc.json', mutated((d) => {
    for (const k of [...d.keys()]) if (k.startsWith('fixtures_rc/')) d.delete(k);
  }));
  withFile('a fixture with no cases', 'no-cases.json', mutated((d) => {
    (pget(d, 'fixtures/acc_01') as JObj).set('cases', []);
  }));
  withFile('a governor case without its records (cannot compute)', 'no-records.json', mutated((d) => {
    const c = (pget(pget(d, 'fixtures/acc_01') as JObj, 'cases') as J[])[0] as JObj;
    c.delete('records');
  }));
  withFile('a governor request without a task id (evaluate raises)', 'no-task.json', mutated((d) => {
    const c = (pget(pget(d, 'fixtures/acc_02') as JObj, 'cases') as J[])[0] as JObj;
    (pget(c, 'request') as JObj).set('task_id', 'not a task');
  }));
  withFile('a Resume Check case without its inputs (cannot compute)', 'no-inputs.json', mutated((d) => {
    const c = (pget(pget(d, 'fixtures_rc/rc_01') as JObj, 'cases') as J[])[0] as JObj;
    c.delete('inputs');
  }));
  withFile('a document whose output would not be ASCII', 'non-ascii.json', mutated((d) => {
    const c = (pget(pget(d, 'fixtures/acc_01') as JObj, 'cases') as J[])[0] as JObj;
    (pget(c, 'inputs') as JObj).set('policy_version', 'vé');
  }));

  // A changed but well-formed document still runs, and its records are computed, not copied.
  const changed = mutated((d) => {
    const c = (pget(pget(d, 'fixtures/acc_01') as JObj, 'cases') as J[])[0] as JObj;
    (pget(c, 'inputs') as JObj).set('policy_version', 'v9');
  });
  files.set('changed.json', changed);
  const r2 = runMain(['changed.json'], read);
  const changedOut = r2.code === 0 ? parseJson(r2.stdout) as JObj : null;
  const changedRec = changedOut !== null ? (pget(changedOut, 'fixtures/acc_01') as J[])[0] as JObj : null;
  ok('a changed input changes the computed record', changedRec !== null && pget(changedRec, 'policy_version') === 'v9'
    && pget(changedRec, 'record_id') !== pget(acc1Ref, 'record_id') && isList(pget(changedRec, 'uncovered')));

  process.stdout.write((failures === 0 ? 'OK' : 'FAILED') + ': ' + passes + ' passed, ' + failures + ' failed\n');
  process.exitCode = failures === 0 ? 0 : 1;
}

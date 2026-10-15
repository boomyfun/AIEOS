// The port's document: for every governor fixture (fixtures/<name>) and every Resume Check fixture
// (fixtures_rc/<name>) of the fixture document, the records of its cases in case order, computed as
// test_export_reference.py computes them, in the canonical text, with the one placeholder (engine_identity.python of
// the Resume Check records is "<engine>"). RISK-01 (fixtures_risk/) is in the fixture document but not in round 1, so
// it is passed over.

import type { J, JObj } from './json.ts';
import { parseJson, canonicalText, isObj, isList, pget } from './json.ts';
import { utf8Decode } from './bytes.ts';
import { evaluate } from './governor.ts';
import { check, PLACEHOLDER } from './resume_check.ts';

export const GOVERNOR_FOLDER = 'fixtures';
export const RC_FOLDER = 'fixtures_rc';
const RISK_FOLDER = 'fixtures_risk';
const KEY = /^(fixtures|fixtures_rc|fixtures_risk)\/([^/]+)$/;
export const USAGE = 'usage: node main.ts <fixture document>\n';

/** Not a fixture document, or a case that cannot be computed. */
export class PortError extends Error {}

/** test_export_reference.placeholder: engine_identity.python of a Resume Check record becomes "<engine>". */
function placeholder(folder: string, record: { [key: string]: unknown }): { [key: string]: unknown } {
  if (folder !== RC_FOLDER) return record;
  const ident = record['engine_identity'];
  if (typeof ident === 'object' && ident !== null && !Array.isArray(ident) && !(ident instanceof Map)
      && Object.prototype.hasOwnProperty.call(ident, 'python')) {
    return { ...record, engine_identity: { ...(ident as object), python: PLACEHOLDER } };
  }
  return record;
}

/** The records of one fixture's cases (test_export_reference.case_records). */
export function caseRecords(folder: string, fixture: JObj): Array<{ [key: string]: unknown }> {
  const cases = pget(fixture, 'cases') as J[];
  const out: Array<{ [key: string]: unknown }> = [];
  let n = 0;
  for (const c of cases) {
    n++;
    if (!isObj(c)) throw new PortError('case ' + n + ': not an object');
    let rec: { [key: string]: unknown };
    try {
      if (folder === GOVERNOR_FOLDER) {
        if (!(c.has('request') && c.has('inputs') && c.has('records'))) {
          throw new PortError('no request, inputs or records');
        }
        rec = evaluate(pget(c, 'request'), pget(c, 'inputs'), pget(c, 'records'));
      } else {
        if (!c.has('inputs')) throw new PortError('no inputs');
        rec = check(pget(c, 'inputs'));
      }
    } catch (e) {
      const what = e instanceof Error ? e.constructor.name + ': ' + e.message : 'a non-error value';
      throw new PortError('case ' + n + ': the call raised ' + what);
    }
    out.push(placeholder(folder, rec));
  }
  return out;
}

/** The fixture document (bytes) parsed and checked for its form: UTF-8 without a byte-order mark or a CR, one JSON
 * object in the canonical text, every key "<folder>/<stem>" of the three exported folders, every value an object,
 * and those of the two round-1 folders with a non-empty list of cases, at least one of each folder. */
export function readFixtureDocument(bytes: Uint8Array): JObj {
  let text: string;
  try {
    text = utf8Decode(bytes);
  } catch (e) {
    throw new PortError('the fixture document is not UTF-8');
  }
  if (text.startsWith('﻿') || text.includes('\r')) {
    throw new PortError('the fixture document has a byte-order mark or a CR byte');
  }
  let value: J;
  try {
    value = parseJson(text);
  } catch (e) {
    throw new PortError('the fixture document is not one JSON value: ' + (e instanceof Error ? e.message : ''));
  }
  if (canonicalText(value) !== text) throw new PortError('the fixture document is not in the canonical text');
  if (!isObj(value)) throw new PortError('the fixture document is not an object');
  const seen = new Set<string>();
  for (const [key, fixture] of value) {
    const m = KEY.exec(key);
    if (m === null) throw new PortError('not a fixture key: ' + key);
    if (!isObj(fixture)) throw new PortError(key + ': not an object');
    const folder = m[1] as string;
    if (folder !== RISK_FOLDER) {
      const cases = pget(fixture, 'cases');
      if (!isList(cases) || cases.length === 0) throw new PortError(key + ': no cases');
    }
    seen.add(folder);
  }
  for (const folder of [GOVERNOR_FOLDER, RC_FOLDER]) {
    if (!seen.has(folder)) throw new PortError('missing fixture folder ' + folder);
  }
  return value;
}

/** The port's whole document, as text (ASCII, LF, one final LF). Throws PortError when it cannot be built. */
export function buildDocument(bytes: Uint8Array): string {
  const fixtures = readFixtureDocument(bytes);
  const doc = new Map<string, unknown>();
  for (const [key, fixture] of fixtures) {
    const folder = key.slice(0, key.indexOf('/'));
    if (folder !== GOVERNOR_FOLDER && folder !== RC_FOLDER) continue;
    try {
      doc.set(key, caseRecords(folder, fixture as JObj));
    } catch (e) {
      throw new PortError(key + ': ' + (e instanceof Error ? e.message : ''));
    }
  }
  let out: string;
  try {
    out = canonicalText(doc);
  } catch (e) {
    throw new PortError('the document has no canonical text');
  }
  for (let i = 0; i < out.length; i++) {
    if (out.charCodeAt(i) > 127) throw new PortError('the document is not ASCII');
  }
  return out;
}

export type Result = { code: number; stdout: string; stderr: string };

/** The command line: exactly one argument, the fixture document's path; read is the one file reader (node:fs in
 * main.ts, an in-memory reader in the tests). Never throws; on any failure stdout is empty and code is non-zero. */
export function runMain(args: readonly string[], read: (path: string) => Uint8Array): Result {
  if (args.length !== 1) return { code: 2, stdout: '', stderr: USAGE };
  try {
    let bytes: Uint8Array;
    try {
      bytes = read(args[0] as string);
    } catch (e) {
      return { code: 2, stdout: '', stderr: 'port failed: the fixture document cannot be read\n' };
    }
    return { code: 0, stdout: buildDocument(bytes), stderr: '' };
  } catch (e) {
    const what = e instanceof Error ? e.message : 'an unknown failure';
    return { code: 1, stdout: '', stderr: 'port failed: ' + what + '\n' };
  }
}

// Round 2: Python's json module and repr as the round-2 sources use them.
//
// - pyLoads: json.loads as records.check_log calls it on one log line (object_pairs_hook=_pairs, parse_constant=
//   _constant), following CPython's C scanner, so that a text is accepted exactly when Python accepts it. A repeated key
//   and NaN/Infinity raise PyMalformed with Python's own message (records._Malformed); every other refusal of the
//   scanner (JSONDecodeError, whose wording depends on the Python version, a too-large integer, too deep a nesting) is
//   a case this port cannot compute (R2Fail), so the program fails closed.
// - dumps: json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True), with allow_nan as given.
// - pyRepr: repr() of a JSON value; a string with a character outside ASCII is a case this port cannot compute.
//
// Values: null, booleans, integers (number when safe, else bigint), strings, arrays, Maps (insertion order is the
// text's order, as a Python dict built by the hook) and PyFloat for a number with a fraction or an exponent.

export class PyFloat {
  readonly value: number;
  constructor(value: number) {
    this.value = value;
  }
}

export type V = null | boolean | number | bigint | string | PyFloat | V[] | VObj;
export interface VObj extends Map<string, V> {}

/** A call or case this port cannot compute: the program fails closed. */
export class R2Fail extends Error {}

/** records._Malformed: its message is str(exc) in the finding "the line is not one JSON object (...)". */
export class PyMalformed extends Error {}

/** json.dumps refused a value (allow_nan=False and a float out of range): Python's ValueError. */
export class DumpsError extends Error {}

export const MAX_DEPTH = 200;
const MAX_INT_DIGITS = 4300;
const SAFE = 9007199254740991n;

// ---------------------------------------------------------------------------------------------------------------
// Predicates as records.py writes them

export function isDict(v: unknown): v is VObj {
  return v instanceof Map;
}

export function isList(v: unknown): v is V[] {
  return Array.isArray(v);
}

/** isinstance(v, int) and not isinstance(v, bool), and v >= minimum when given. */
export function isInt(v: V | undefined, minimum: number | null = null): boolean {
  let b: bigint;
  if (typeof v === 'number' && Number.isInteger(v)) b = BigInt(v);
  else if (typeof v === 'bigint') b = v;
  else return false;
  return minimum === null || b >= BigInt(minimum);
}

/** _is_str: a non-empty string. */
export function isStr(v: V | undefined): v is string {
  return typeof v === 'string' && v !== '';
}

/** dict.get(k): None when absent. */
export function get(m: VObj, k: string): V {
  const v = m.get(k);
  return v === undefined ? null : v;
}

/** set(m) == set(keys). */
export function keysAre(m: VObj, keys: readonly string[]): boolean {
  if (m.size !== keys.length) return false;
  for (const k of keys) if (!m.has(k)) return false;
  return true;
}

/** Python's ordering of str: by code point. */
export function cmpPy(a: string, b: string): number {
  let i = 0;
  let j = 0;
  while (i < a.length && j < b.length) {
    const ca = a.codePointAt(i) as number;
    const cb = b.codePointAt(j) as number;
    if (ca !== cb) return ca < cb ? -1 : 1;
    i += ca > 0xffff ? 2 : 1;
    j += cb > 0xffff ? 2 : 1;
  }
  if (i < a.length) return 1;
  if (j < b.length) return -1;
  return 0;
}

export function sortedStrs(values: Iterable<string>): string[] {
  return Array.from(values).sort(cmpPy);
}

// ---------------------------------------------------------------------------------------------------------------
// repr

/** repr(float), CPython's short form. */
export function floatRepr(x: number): string {
  if (Number.isNaN(x)) return 'nan';
  if (x === Infinity) return 'inf';
  if (x === -Infinity) return '-inf';
  if (x === 0) return Object.is(x, -0) ? '-0.0' : '0.0';
  const m = /^(-?)(\d)(?:\.(\d+))?e([+-]\d+)$/.exec(x.toExponential());
  if (m === null) throw new R2Fail('a float without a repr');
  const sign = m[1] as string;
  const digits = (m[2] as string) + (m[3] ?? '');
  const exp = Number(m[4]);
  const decpt = exp + 1;
  if (decpt > -4 && decpt <= 16) {
    if (decpt <= 0) return sign + '0.' + '0'.repeat(-decpt) + digits;
    if (decpt >= digits.length) return sign + digits + '0'.repeat(decpt - digits.length) + '.0';
    return sign + digits.slice(0, decpt) + '.' + digits.slice(decpt);
  }
  const mant = digits.length > 1 ? digits[0] + '.' + digits.slice(1) : digits;
  const e = Math.abs(exp);
  return sign + mant + 'e' + (exp < 0 ? '-' : '+') + (e < 10 ? '0' + e : String(e));
}

/** repr(str) for a string of ASCII characters; any other character fails closed (its repr depends on Unicode's
 * printable table, and the output would not be ASCII). */
export function reprStr(s: string): string {
  const quote = s.includes("'") && !s.includes('"') ? '"' : "'";
  let out = quote;
  for (let k = 0; k < s.length; k++) {
    const c = s.charCodeAt(k);
    const ch = s[k] as string;
    if (c > 0x7f) throw new R2Fail('the repr of a string with a character outside ASCII');
    if (ch === quote || ch === '\\') out += '\\' + ch;
    else if (ch === '\t') out += '\\t';
    else if (ch === '\n') out += '\\n';
    else if (ch === '\r') out += '\\r';
    else if (c < 0x20 || c === 0x7f) out += '\\x' + c.toString(16).padStart(2, '0');
    else out += ch;
  }
  return out + quote;
}

/** repr() of a JSON value. */
export function pyRepr(v: V): string {
  if (v === null) return 'None';
  if (v === true) return 'True';
  if (v === false) return 'False';
  if (typeof v === 'number') return String(v);
  if (typeof v === 'bigint') return v.toString();
  if (typeof v === 'string') return reprStr(v);
  if (v instanceof PyFloat) return floatRepr(v.value);
  if (Array.isArray(v)) return '[' + v.map((x) => pyRepr(x)).join(', ') + ']';
  const parts: string[] = [];
  for (const [k, x] of v) parts.push(reprStr(k) + ': ' + pyRepr(x));
  return '{' + parts.join(', ') + '}';
}

// ---------------------------------------------------------------------------------------------------------------
// json.dumps(sort_keys=True, separators=(',', ':'), ensure_ascii=True)

function dumpStr(s: string): string {
  let out = '"';
  for (let k = 0; k < s.length; k++) {
    const c = s.charCodeAt(k);
    if (c === 0x22) out += '\\"';
    else if (c === 0x5c) out += '\\\\';
    else if (c === 0x08) out += '\\b';
    else if (c === 0x0c) out += '\\f';
    else if (c === 0x0a) out += '\\n';
    else if (c === 0x0d) out += '\\r';
    else if (c === 0x09) out += '\\t';
    else if (c < 0x20 || c > 0x7e) out += '\\u' + c.toString(16).padStart(4, '0');
    else out += s[k];
  }
  return out + '"';
}

export function dumps(v: V, allowNan: boolean, depth: number = 0): string {
  if (depth > MAX_DEPTH) throw new R2Fail('a value nested too deep');
  if (v === null) return 'null';
  if (v === true) return 'true';
  if (v === false) return 'false';
  if (typeof v === 'number') {
    if (!Number.isInteger(v)) throw new R2Fail('a number that is not an integer outside PyFloat');
    return Object.is(v, -0) ? '0' : String(v);
  }
  if (typeof v === 'bigint') return v.toString();
  if (typeof v === 'string') return dumpStr(v);
  if (v instanceof PyFloat) {
    const x = v.value;
    if (!Number.isFinite(x)) {
      if (!allowNan) throw new DumpsError('Out of range float values are not JSON compliant');
      return Number.isNaN(x) ? 'NaN' : x > 0 ? 'Infinity' : '-Infinity';
    }
    return floatRepr(x);
  }
  if (Array.isArray(v)) return '[' + v.map((x) => dumps(x, allowNan, depth + 1)).join(',') + ']';
  const keys = sortedStrs(v.keys());
  return '{' + keys.map((k) => dumpStr(k) + ':' + dumps(v.get(k) as V, allowNan, depth + 1)).join(',') + '}';
}

/** The depth of a value (a scalar is 0), failing closed beyond MAX_DEPTH. */
export function checkDepth(v: unknown, depth: number = 0): void {
  if (depth > MAX_DEPTH) throw new R2Fail('a value nested too deep');
  if (Array.isArray(v)) {
    for (const x of v) checkDepth(x, depth + 1);
  } else if (v instanceof Map) {
    for (const x of v.values()) checkDepth(x, depth + 1);
  } else if (typeof v === 'bigint') {
    const digits = (v < 0n ? -v : v).toString().length;
    if (digits > MAX_INT_DIGITS) throw new R2Fail('an integer Python would not convert');
  }
}

// ---------------------------------------------------------------------------------------------------------------
// json.loads of one log line

function isDigit(c: string | undefined): boolean {
  return c !== undefined && c >= '0' && c <= '9';
}

export function pyLoads(s: string): V {
  let i = 0;
  const n = s.length;
  const end = n - 1;

  function refuse(): never {
    throw new R2Fail('a log line that Python refuses with a JSONDecodeError (its wording is Python\'s own)');
  }

  function ws(): void {
    while (i < n) {
      const c = s[i];
      if (c === ' ' || c === '\t' || c === '\n' || c === '\r') i++;
      else break;
    }
  }

  function str(): string {
    // s[i] is the opening quote
    i++;
    let out = '';
    while (true) {
      if (i >= n) refuse();
      const c = s.charCodeAt(i);
      if (c === 0x22) {
        i++;
        return out;
      }
      if (c === 0x5c) {
        i++;
        if (i >= n) refuse();
        const e = s[i];
        if (e === 'u') {
          const hex = s.slice(i + 1, i + 5);
          if (!/^[0-9a-fA-F]{4}$/.test(hex)) refuse();
          out += String.fromCharCode(parseInt(hex, 16));
          i += 5;
          continue;
        }
        if (e === '"' || e === '\\' || e === '/') out += e;
        else if (e === 'b') out += '\b';
        else if (e === 'f') out += '\f';
        else if (e === 'n') out += '\n';
        else if (e === 'r') out += '\r';
        else if (e === 't') out += '\t';
        else refuse();
        i++;
        continue;
      }
      if (c < 0x20) refuse();
      out += s[i];
      i++;
    }
  }

  function num(): V {
    const start = i;
    if (s[i] === '-') {
      i++;
      if (i > end) refuse();
    }
    if (s[i] !== undefined && (s[i] as string) >= '1' && (s[i] as string) <= '9') {
      i++;
      while (i <= end && isDigit(s[i])) i++;
    } else if (s[i] === '0') {
      i++;
    } else {
      refuse();
    }
    let isFloat = false;
    if (i < end && s[i] === '.' && isDigit(s[i + 1])) {
      isFloat = true;
      i += 2;
      while (i <= end && isDigit(s[i])) i++;
    }
    if (i < end && (s[i] === 'e' || s[i] === 'E')) {
      const eStart = i;
      i++;
      if (i < end && (s[i] === '-' || s[i] === '+')) i++;
      while (i <= end && isDigit(s[i])) i++;
      if (isDigit(s[i - 1])) isFloat = true;
      else i = eStart;
    }
    const text = s.slice(start, i);
    if (isFloat) return new PyFloat(Number(text));
    const digits = text.startsWith('-') ? text.length - 1 : text.length;
    if (digits > MAX_INT_DIGITS) throw new R2Fail('an integer Python would not convert');
    const b = BigInt(text);
    return b >= -SAFE && b <= SAFE ? Number(b) : b;
  }

  function constant(name: string): never {
    throw new PyMalformed(name + ' is not a JSON value');
  }

  function value(depth: number): V {
    if (i >= n) refuse();
    const c = s[i];
    if (c === '"') return str();
    if (c === '{') {
      if (depth >= MAX_DEPTH) throw new R2Fail('a log line nested too deep');
      i++;
      const pairs: Array<[string, V]> = [];
      ws();
      if (i > end || s[i] !== '}') {
        while (true) {
          if (i > end || s[i] !== '"') refuse();
          const k = str();
          ws();
          if (i > end || s[i] !== ':') refuse();
          i++;
          ws();
          const v = value(depth + 1);
          pairs.push([k, v]);
          ws();
          if (i <= end && s[i] === '}') break;
          if (i > end || s[i] !== ',') refuse();
          i++;
          ws();
        }
      }
      i++;
      // records._pairs, the object_pairs_hook
      const m: VObj = new Map<string, V>();
      for (const [k, v] of pairs) {
        if (m.has(k)) throw new PyMalformed('repeated key ' + reprStr(k));
        m.set(k, v);
      }
      return m;
    }
    if (c === '[') {
      if (depth >= MAX_DEPTH) throw new R2Fail('a log line nested too deep');
      i++;
      const a: V[] = [];
      ws();
      if (i > end || s[i] !== ']') {
        while (true) {
          a.push(value(depth + 1));
          ws();
          if (i <= end && s[i] === ']') break;
          if (i > end || s[i] !== ',') refuse();
          i++;
          ws();
        }
      }
      i++;
      return a;
    }
    if (c === 'n' && s.startsWith('null', i)) {
      i += 4;
      return null;
    }
    if (c === 't' && s.startsWith('true', i)) {
      i += 4;
      return true;
    }
    if (c === 'f' && s.startsWith('false', i)) {
      i += 5;
      return false;
    }
    if (c === 'N' && s.startsWith('NaN', i)) constant('NaN');
    if (c === 'I' && s.startsWith('Infinity', i)) constant('Infinity');
    if (c === '-' && s.startsWith('-Infinity', i)) constant('-Infinity');
    return num();
  }

  ws();
  const v = value(0);
  ws();
  if (i !== n) refuse();
  return v;
}

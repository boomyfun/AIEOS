// JSON values as Python's json module reads them for the bootstrap, and the canonical text of
// conformance.canonical_text (conformance-files.md section 2).
//
// Objects are Maps, so that key order is insertion order for every key (a plain JS object would put integer-like keys
// first) and no key can touch a prototype. Integers outside the safe range are bigints, so that no digit is lost.
// A number with a fraction or an exponent and the constants NaN and Infinity are refused, as conformance.unwrap refuses
// them.

export type J = null | boolean | number | bigint | string | J[] | JObj;
export interface JObj extends Map<string, J> {}

export class JsonError extends Error {}

const MAX_DEPTH = 900;
const SAFE = 9007199254740991n;

export function parseJson(text: string): J {
  let i = 0;
  const n = text.length;

  function fail(what: string): never {
    throw new JsonError(what + ' at offset ' + i);
  }

  function ws(): void {
    while (i < n) {
      const c = text.charCodeAt(i);
      if (c === 0x20 || c === 0x09 || c === 0x0a || c === 0x0d) {
        i++;
      } else {
        break;
      }
    }
  }

  function str(): string {
    // text[i] is the opening quote
    i++;
    let out = '';
    let start = i;
    while (true) {
      if (i >= n) fail('an unterminated string');
      const c = text.charCodeAt(i);
      if (c === 0x22) {
        out += text.slice(start, i);
        i++;
        return out;
      }
      if (c < 0x20) fail('a control character in a string');
      if (c === 0x5c) {
        out += text.slice(start, i);
        i++;
        if (i >= n) fail('an unterminated escape');
        const e = text[i];
        if (e === '"' || e === '\\' || e === '/') out += e;
        else if (e === 'b') out += '\b';
        else if (e === 'f') out += '\f';
        else if (e === 'n') out += '\n';
        else if (e === 'r') out += '\r';
        else if (e === 't') out += '\t';
        else if (e === 'u') {
          const hex = text.slice(i + 1, i + 5);
          if (!/^[0-9a-fA-F]{4}$/.test(hex)) fail('a bad \\u escape');
          out += String.fromCharCode(parseInt(hex, 16));
          i += 4;
        } else {
          fail('a bad escape');
        }
        i++;
        start = i;
        continue;
      }
      i++;
    }
  }

  const NUM = /-?(?:0|[1-9][0-9]*)/y;

  function num(): number | bigint {
    NUM.lastIndex = i;
    const m = NUM.exec(text);
    if (m === null) fail('not a JSON value');
    i += m[0].length;
    if (i < n && (text[i] === '.' || text[i] === 'e' || text[i] === 'E')) {
      fail('a number with a fraction or an exponent');
    }
    const b = BigInt(m[0]);
    if (b >= -SAFE && b <= SAFE) return Number(b);
    return b;
  }

  function value(depth: number): J {
    if (depth > MAX_DEPTH) fail('nesting too deep');
    ws();
    if (i >= n) fail('no value');
    const c = text[i];
    if (c === '{') {
      i++;
      const m: JObj = new Map<string, J>();
      ws();
      if (text[i] === '}') {
        i++;
        return m;
      }
      while (true) {
        ws();
        if (text[i] !== '"') fail('an object key that is not a string');
        const k = str();
        ws();
        if (text[i] !== ':') fail('no colon');
        i++;
        const v = value(depth + 1);
        if (m.has(k)) fail('a repeated key');
        m.set(k, v);
        ws();
        if (text[i] === ',') {
          i++;
          continue;
        }
        if (text[i] === '}') {
          i++;
          return m;
        }
        fail('no comma or closing brace');
      }
    }
    if (c === '[') {
      i++;
      const a: J[] = [];
      ws();
      if (text[i] === ']') {
        i++;
        return a;
      }
      while (true) {
        a.push(value(depth + 1));
        ws();
        if (text[i] === ',') {
          i++;
          continue;
        }
        if (text[i] === ']') {
          i++;
          return a;
        }
        fail('no comma or closing bracket');
      }
    }
    if (c === '"') return str();
    if (text.startsWith('true', i)) {
      i += 4;
      return true;
    }
    if (text.startsWith('false', i)) {
      i += 5;
      return false;
    }
    if (text.startsWith('null', i)) {
      i += 4;
      return null;
    }
    return num();
  }

  const v = value(0);
  ws();
  if (i !== n) fail('extra data');
  return v;
}

// ---------------------------------------------------------------------------------------------------------------
// Python-like helpers over J

export function isObj(v: unknown): v is JObj {
  return v instanceof Map;
}

export function isList(v: unknown): v is J[] {
  return Array.isArray(v);
}

export function isInt(v: unknown): v is number | bigint {
  return (typeof v === 'number' && Number.isInteger(v)) || typeof v === 'bigint';
}

/** dict.get(k): None (null) when the key is missing. */
export function pget(m: JObj, k: string): J {
  const v = m.get(k);
  return v === undefined ? null : v;
}

/** set(m) == set(keys). */
export function keySetIs(m: JObj, keys: readonly string[]): boolean {
  if (m.size !== keys.length) return false;
  for (const k of keys) if (!m.has(k)) return false;
  return true;
}

/** Python's == over JSON values (bool and int compare as numbers, as in Python). */
export function pyEq(a: J, b: J): boolean {
  const numA = typeof a === 'number' || typeof a === 'bigint' || typeof a === 'boolean';
  const numB = typeof b === 'number' || typeof b === 'bigint' || typeof b === 'boolean';
  if (numA || numB) {
    if (!(numA && numB)) return false;
    const x = typeof a === 'boolean' ? (a ? 1n : 0n) : BigInt(a as number | bigint);
    const y = typeof b === 'boolean' ? (b ? 1n : 0n) : BigInt(b as number | bigint);
    return x === y;
  }
  if (a === null || b === null) return a === b;
  if (typeof a === 'string' || typeof b === 'string') return a === b;
  if (Array.isArray(a) || Array.isArray(b)) {
    if (!(Array.isArray(a) && Array.isArray(b)) || a.length !== b.length) return false;
    for (let k = 0; k < a.length; k++) if (!pyEq(a[k] as J, b[k] as J)) return false;
    return true;
  }
  const ma = a as JObj;
  const mb = b as JObj;
  if (ma.size !== mb.size) return false;
  for (const [k, v] of ma) {
    if (!mb.has(k) || !pyEq(v, mb.get(k) as J)) return false;
  }
  return true;
}

/** Python's ordering of str: by code point. */
export function cmpStr(a: string, b: string): number {
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

/** sorted() over strings. */
export function sortStrs(values: Iterable<string>): string[] {
  return Array.from(values).sort(cmpStr);
}

/** sorted(set(...)) over strings. */
export function sortedSet(values: Iterable<string>): string[] {
  return sortStrs(new Set(values));
}

// ---------------------------------------------------------------------------------------------------------------
// The canonical text (conformance.canon and conformance.canonical_text)

export class CanonError extends Error {}

function canonStr(s: string): string {
  let out = '"';
  for (let k = 0; k < s.length; k++) {
    const ch = s[k] as string;
    const c = s.charCodeAt(k);
    if (ch === '"' || ch === '\\') {
      out += '\\' + ch;
    } else if (c < 0x20) {
      out += '\\u' + c.toString(16).padStart(4, '0');
    } else {
      out += ch;
    }
  }
  return out + '"';
}

/** The canonical JSON text of one value, without the final LF. Accepts Maps, plain objects, arrays and scalars. */
export function canon(value: unknown, indent: number = 0): string {
  const pad = ' '.repeat(indent + 2);
  if (value instanceof Map) {
    if (value.size === 0) return '{}';
    const keys = sortStrs(value.keys() as Iterable<string>);
    const items = keys.map((k) => pad + canonStr(k) + ': ' + canon(value.get(k), indent + 2));
    return '{\n' + items.join(',\n') + '\n' + ' '.repeat(indent) + '}';
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return '[]';
    return '[\n' + value.map((x: unknown) => pad + canon(x, indent + 2)).join(',\n') + '\n' + ' '.repeat(indent) + ']';
  }
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (value === null) return 'null';
  if (typeof value === 'number') {
    if (!Number.isInteger(value)) throw new CanonError('a number that is not an integer has no canonical form');
    return Object.is(value, -0) ? '0' : String(value);
  }
  if (typeof value === 'bigint') return value.toString();
  if (typeof value === 'string') return canonStr(value);
  if (typeof value === 'object') {
    const obj = value as { [k: string]: unknown };
    const keys = sortStrs(Object.keys(obj));
    if (keys.length === 0) return '{}';
    const items = keys.map((k) => pad + canonStr(k) + ': ' + canon(obj[k], indent + 2));
    return '{\n' + items.join(',\n') + '\n' + ' '.repeat(indent) + '}';
  }
  throw new CanonError('a value of type ' + typeof value + ' has no canonical form');
}

/** conformance.canonical_text, as a string (the caller encodes it). */
export function canonicalText(value: unknown): string {
  return canon(value) + '\n';
}

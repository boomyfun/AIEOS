// UTF-8 as Python's strict codec reads and writes it, and SHA-256 (FIPS 180-4), written out because the port may use
// no module but node:fs and node:process.

export class EncodingError extends Error {}

/** str.encode('utf-8'): a lone surrogate cannot be encoded. */
export function utf8Encode(s: string): Uint8Array {
  const out: number[] = [];
  for (let i = 0; i < s.length; i++) {
    let c = s.charCodeAt(i);
    if (c >= 0xd800 && c <= 0xdbff) {
      const d = i + 1 < s.length ? s.charCodeAt(i + 1) : 0;
      if (d >= 0xdc00 && d <= 0xdfff) {
        c = 0x10000 + ((c - 0xd800) << 10) + (d - 0xdc00);
        i++;
      } else {
        throw new EncodingError('a lone surrogate cannot be encoded');
      }
    } else if (c >= 0xdc00 && c <= 0xdfff) {
      throw new EncodingError('a lone surrogate cannot be encoded');
    }
    if (c < 0x80) {
      out.push(c);
    } else if (c < 0x800) {
      out.push(0xc0 | (c >> 6), 0x80 | (c & 63));
    } else if (c < 0x10000) {
      out.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63));
    } else {
      out.push(0xf0 | (c >> 18), 0x80 | ((c >> 12) & 63), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63));
    }
  }
  return Uint8Array.from(out);
}

/** bytes.decode('utf-8') (strict): overlong forms, surrogates and code points above U+10FFFF are refused. */
export function utf8Decode(b: Uint8Array): string {
  const parts: string[] = [];
  let chunk: number[] = [];
  const flush = (): void => {
    if (chunk.length > 0) {
      parts.push(String.fromCharCode(...chunk));
      chunk = [];
    }
  };
  let i = 0;
  const n = b.length;
  const cont = (k: number): number => {
    if (k >= n) throw new EncodingError('a truncated UTF-8 sequence');
    const x = b[k] as number;
    if ((x & 0xc0) !== 0x80) throw new EncodingError('a bad UTF-8 continuation byte');
    return x & 63;
  };
  while (i < n) {
    const x = b[i] as number;
    let cp: number;
    if (x < 0x80) {
      cp = x;
      i += 1;
    } else if (x >= 0xc2 && x <= 0xdf) {
      cp = ((x & 31) << 6) | cont(i + 1);
      i += 2;
    } else if (x >= 0xe0 && x <= 0xef) {
      const y = b[i + 1];
      if (x === 0xe0 && y !== undefined && y < 0xa0) throw new EncodingError('an overlong UTF-8 sequence');
      if (x === 0xed && y !== undefined && y > 0x9f) throw new EncodingError('a UTF-8 encoded surrogate');
      cp = ((x & 15) << 12) | (cont(i + 1) << 6) | cont(i + 2);
      i += 3;
    } else if (x >= 0xf0 && x <= 0xf4) {
      const y = b[i + 1];
      if (x === 0xf0 && y !== undefined && y < 0x90) throw new EncodingError('an overlong UTF-8 sequence');
      if (x === 0xf4 && y !== undefined && y > 0x8f) throw new EncodingError('a code point above U+10FFFF');
      cp = ((x & 7) << 18) | (cont(i + 1) << 12) | (cont(i + 2) << 6) | cont(i + 3);
      i += 4;
    } else {
      throw new EncodingError('a byte that starts no UTF-8 sequence');
    }
    if (cp > 0xffff) {
      const v = cp - 0x10000;
      chunk.push(0xd800 + (v >> 10), 0xdc00 + (v & 0x3ff));
    } else {
      chunk.push(cp);
    }
    if (chunk.length >= 8192) flush();
  }
  flush();
  return parts.join('');
}

const K = new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]);

function rotr(x: number, r: number): number {
  return (x >>> r) | (x << (32 - r));
}

/** The SHA-256 of the bytes, as 64 lowercase hex digits. */
export function sha256Hex(data: Uint8Array): string {
  const h = new Uint32Array([
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
  ]);
  const len = data.length;
  const total = Math.ceil((len + 9) / 64) * 64;
  const buf = new Uint8Array(total);
  buf.set(data);
  buf[len] = 0x80;
  const bits = len * 8;
  const hi = Math.floor(bits / 0x100000000);
  const lo = bits >>> 0;
  buf[total - 8] = (hi >>> 24) & 255;
  buf[total - 7] = (hi >>> 16) & 255;
  buf[total - 6] = (hi >>> 8) & 255;
  buf[total - 5] = hi & 255;
  buf[total - 4] = (lo >>> 24) & 255;
  buf[total - 3] = (lo >>> 16) & 255;
  buf[total - 2] = (lo >>> 8) & 255;
  buf[total - 1] = lo & 255;
  const w = new Uint32Array(64);
  for (let off = 0; off < total; off += 64) {
    for (let t = 0; t < 16; t++) {
      const p = off + 4 * t;
      w[t] = (((buf[p] as number) << 24) | ((buf[p + 1] as number) << 16) | ((buf[p + 2] as number) << 8)
        | (buf[p + 3] as number)) >>> 0;
    }
    for (let t = 16; t < 64; t++) {
      const a15 = w[t - 15] as number;
      const a2 = w[t - 2] as number;
      const s0 = rotr(a15, 7) ^ rotr(a15, 18) ^ (a15 >>> 3);
      const s1 = rotr(a2, 17) ^ rotr(a2, 19) ^ (a2 >>> 10);
      w[t] = ((w[t - 16] as number) + s0 + (w[t - 7] as number) + s1) >>> 0;
    }
    let a = h[0] as number;
    let b = h[1] as number;
    let c = h[2] as number;
    let d = h[3] as number;
    let e = h[4] as number;
    let f = h[5] as number;
    let g = h[6] as number;
    let hh = h[7] as number;
    for (let t = 0; t < 64; t++) {
      const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
      const ch = (e & f) ^ (~e & g);
      const t1 = (hh + S1 + ch + (K[t] as number) + (w[t] as number)) >>> 0;
      const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const t2 = (S0 + maj) >>> 0;
      hh = g;
      g = f;
      f = e;
      e = (d + t1) >>> 0;
      d = c;
      c = b;
      b = a;
      a = (t1 + t2) >>> 0;
    }
    h[0] = ((h[0] as number) + a) >>> 0;
    h[1] = ((h[1] as number) + b) >>> 0;
    h[2] = ((h[2] as number) + c) >>> 0;
    h[3] = ((h[3] as number) + d) >>> 0;
    h[4] = ((h[4] as number) + e) >>> 0;
    h[5] = ((h[5] as number) + f) >>> 0;
    h[6] = ((h[6] as number) + g) >>> 0;
    h[7] = ((h[7] as number) + hh) >>> 0;
  }
  let out = '';
  for (let k = 0; k < 8; k++) out += (h[k] as number).toString(16).padStart(8, '0');
  return out;
}

/** The SHA-256 hex of a text's UTF-8 bytes (raises for a lone surrogate, as Python's encode does). */
export function sha256Text(s: string): string {
  return sha256Hex(utf8Encode(s));
}

/** Whether a string holds a surrogate that UTF-8 cannot encode. */
export function hasLoneSurrogate(s: string): boolean {
  return /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/.test(s);
}

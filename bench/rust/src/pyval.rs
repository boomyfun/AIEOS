//! Round 2's values as the Python source sees them (dict, list, str, int, bool, None), with dicts in insertion order
//! (Python's `repr` of a dict shows that order); Python's `repr` of these values, `json.dumps(value, sort_keys=True,
//! separators=(',', ':'), ensure_ascii=True)`, and a reader of one log line as records.py's `json.loads` with its
//! object_pairs_hook and parse_constant reads it.
//!
//! Every error of type `String` returned here is a value or a text the port cannot compute (fail closed).

use crate::json::{Int, Json};

/// One value. Objects keep their keys in insertion order; a key is never repeated.
#[derive(Clone, Debug)]
pub enum V {
    Null,
    Bool(bool),
    Int(Int),
    Str(String),
    Arr(Vec<V>),
    Obj(Vec<(String, V)>),
}

pub static NONE: V = V::Null;

impl V {
    /// The value of a round-1 JSON value. Its objects are sorted by key, which is the order of the canonical text the
    /// value was read from, so it is the insertion order Python's reader gives.
    pub fn from_json(j: &Json) -> V {
        match j {
            Json::Null => V::Null,
            Json::Bool(b) => V::Bool(*b),
            Json::Int(n) => V::Int(n.clone()),
            Json::Str(s) => V::Str(s.clone()),
            Json::Arr(a) => V::Arr(a.iter().map(V::from_json).collect()),
            Json::Obj(m) => V::Obj(
                m.iter()
                    .map(|(k, v)| (k.clone(), V::from_json(v)))
                    .collect(),
            ),
        }
    }

    /// The round-1 JSON value (keys sorted), for the canonical text.
    pub fn to_json(&self) -> Json {
        match self {
            V::Null => Json::Null,
            V::Bool(b) => Json::Bool(*b),
            V::Int(n) => Json::Int(n.clone()),
            V::Str(s) => Json::Str(s.clone()),
            V::Arr(a) => Json::Arr(a.iter().map(V::to_json).collect()),
            V::Obj(p) => Json::Obj(p.iter().map(|(k, v)| (k.clone(), v.to_json())).collect()),
        }
    }

    pub fn s(text: &str) -> V {
        V::Str(text.to_string())
    }

    pub fn int(n: u64) -> V {
        V::Int(Int::from_u64(n))
    }

    pub fn strs(items: &[String]) -> V {
        V::Arr(items.iter().map(|x| V::s(x)).collect())
    }

    pub fn obj(pairs: Vec<(&str, V)>) -> V {
        V::Obj(pairs.into_iter().map(|(k, v)| (k.to_string(), v)).collect())
    }

    /// `value[key]` of a dict, None when the value is not a dict or lacks the key.
    pub fn field(&self, key: &str) -> Option<&V> {
        match self {
            V::Obj(p) => p.iter().find(|(k, _)| k == key).map(|(_, v)| v),
            _ => None,
        }
    }

    /// Python's `value.get(key)` on a dict (None for a missing key or a value that is not a dict).
    pub fn get(&self, key: &str) -> &V {
        self.field(key).unwrap_or(&NONE)
    }

    /// Python's `key in value` for a dict.
    pub fn has(&self, key: &str) -> bool {
        self.field(key).is_some()
    }

    pub fn is_null(&self) -> bool {
        matches!(self, V::Null)
    }

    pub fn is_obj(&self) -> bool {
        matches!(self, V::Obj(_))
    }

    pub fn is_arr(&self) -> bool {
        matches!(self, V::Arr(_))
    }

    pub fn is_str(&self) -> bool {
        matches!(self, V::Str(_))
    }

    pub fn as_str(&self) -> Option<&str> {
        match self {
            V::Str(s) => Some(s),
            _ => None,
        }
    }

    pub fn as_arr(&self) -> Option<&[V]> {
        match self {
            V::Arr(a) => Some(a),
            _ => None,
        }
    }

    pub fn as_obj(&self) -> Option<&[(String, V)]> {
        match self {
            V::Obj(p) => Some(p),
            _ => None,
        }
    }

    pub fn as_int(&self) -> Option<&Int> {
        match self {
            V::Int(n) => Some(n),
            _ => None,
        }
    }

    /// records.py `_is_str`: a non-empty string.
    pub fn is_text(&self) -> bool {
        matches!(self, V::Str(s) if !s.is_empty())
    }

    /// Python's `value == text` for a str constant.
    pub fn eq_str(&self, text: &str) -> bool {
        matches!(self, V::Str(s) if s == text)
    }

    /// records.py `_in(values, value)`: a str among the values.
    pub fn str_in(&self, values: &[&str]) -> bool {
        matches!(self, V::Str(s) if values.contains(&s.as_str()))
    }

    /// records.py `_is_int(value, minimum)`: an int, not a bool, at least the minimum.
    pub fn is_int_min(&self, minimum: u64) -> bool {
        matches!(self, V::Int(n) if *n >= Int::from_u64(minimum))
    }

    /// records.py `_is_int(value)` with no minimum.
    pub fn is_int(&self) -> bool {
        matches!(self, V::Int(_))
    }

    /// Python's `set(value) == {keys}` for a dict (false for anything else).
    pub fn keys_are(&self, keys: &[&str]) -> bool {
        match self {
            V::Obj(p) => {
                p.len() == keys.len() && keys.iter().all(|k| p.iter().any(|(x, _)| x == k))
            }
            _ => false,
        }
    }

    /// Whether Python can hash the value (a list or a dict cannot be a set member or a dict key).
    pub fn is_hashable(&self) -> bool {
        !matches!(self, V::Arr(_) | V::Obj(_))
    }
}

/// Python's `==` between two values (True == 1 and False == 0, dicts compared without order).
pub fn py_eq(a: &V, b: &V) -> bool {
    match (a, b) {
        (V::Null, V::Null) => true,
        (V::Bool(x), V::Bool(y)) => x == y,
        (V::Int(x), V::Int(y)) => x == y,
        (V::Bool(x), V::Int(y)) | (V::Int(y), V::Bool(x)) => *y == Int::from_u64(u64::from(*x)),
        (V::Str(x), V::Str(y)) => x == y,
        (V::Arr(x), V::Arr(y)) => x.len() == y.len() && x.iter().zip(y).all(|(p, q)| py_eq(p, q)),
        (V::Obj(x), V::Obj(y)) => {
            x.len() == y.len()
                && x.iter().all(|(k, v)| {
                    y.iter()
                        .find(|(kk, _)| kk == k)
                        .is_some_and(|(_, w)| py_eq(v, w))
                })
        }
        _ => false,
    }
}

// ---------------------------------------------------------------------------------------------------------------
// Python's repr

/// Python's `repr(text)`. A character outside ASCII is refused: whether Python shows it or escapes it depends on
/// Unicode's printable classes, which the port does not carry (fail closed).
pub fn repr_str(s: &str) -> Result<String, String> {
    let quote = if s.contains('\'') && !s.contains('"') {
        '"'
    } else {
        '\''
    };
    let mut out = String::with_capacity(s.len() + 2);
    out.push(quote);
    for ch in s.chars() {
        let c = ch as u32;
        if ch == quote || ch == '\\' {
            out.push('\\');
            out.push(ch);
        } else if ch == '\t' {
            out.push_str("\\t");
        } else if ch == '\n' {
            out.push_str("\\n");
        } else if ch == '\r' {
            out.push_str("\\r");
        } else if c < 0x20 || c == 0x7f {
            out.push_str(&format!("\\x{:02x}", c));
        } else if c < 0x7f {
            out.push(ch);
        } else {
            return Err(
                "a text to be shown by Python's repr holds a character outside ASCII".to_string(),
            );
        }
    }
    out.push(quote);
    Ok(out)
}

/// Python's `repr(value)` (`%r`).
pub fn repr(v: &V) -> Result<String, String> {
    Ok(match v {
        V::Null => "None".to_string(),
        V::Bool(true) => "True".to_string(),
        V::Bool(false) => "False".to_string(),
        V::Int(n) => n.text(),
        V::Str(s) => repr_str(s)?,
        V::Arr(a) => {
            let parts: Result<Vec<String>, String> = a.iter().map(repr).collect();
            format!("[{}]", parts?.join(", "))
        }
        V::Obj(p) => {
            let mut parts = Vec::with_capacity(p.len());
            for (k, x) in p {
                parts.push(format!("{}: {}", repr_str(k)?, repr(x)?));
            }
            format!("{{{}}}", parts.join(", "))
        }
    })
}

// ---------------------------------------------------------------------------------------------------------------
// json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)

fn dumps_str(s: &str, out: &mut String) {
    out.push('"');
    for ch in s.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            c if (' '..='~').contains(&c) => out.push(c),
            c => {
                let mut buf = [0u16; 2];
                for unit in c.encode_utf16(&mut buf) {
                    out.push_str(&format!("\\u{:04x}", unit));
                }
            }
        }
    }
    out.push('"');
}

fn dumps_into(v: &V, out: &mut String) {
    match v {
        V::Null => out.push_str("null"),
        V::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        V::Int(n) => out.push_str(&n.text()),
        V::Str(s) => dumps_str(s, out),
        V::Arr(a) => {
            out.push('[');
            for (n, x) in a.iter().enumerate() {
                if n > 0 {
                    out.push(',');
                }
                dumps_into(x, out);
            }
            out.push(']');
        }
        V::Obj(p) => {
            let mut items: Vec<&(String, V)> = p.iter().collect();
            items.sort_by(|a, b| a.0.cmp(&b.0));
            out.push('{');
            for (n, (k, x)) in items.into_iter().enumerate() {
                if n > 0 {
                    out.push(',');
                }
                dumps_str(k, out);
                out.push(':');
                dumps_into(x, out);
            }
            out.push('}');
        }
    }
}

/// The one compact canonical JSON text of eventlog's `_canonical` and recovery's `_token_text` (ASCII only).
pub fn dumps(v: &V) -> String {
    let mut out = String::new();
    dumps_into(v, &mut out);
    out
}

// ---------------------------------------------------------------------------------------------------------------
// One log line read as records.py reads it

/// Why a line could not be read: `Malformed` is the text of the ValueError that records.py's own hooks raise (a
/// repeated key, NaN or an infinity), which it shows in a finding; `Cannot` is any other failure, whose text is
/// Python's own (its JSON decoder's messages, a fraction or exponent the port does not carry, a lone surrogate),
/// so the port fails closed.
#[derive(Debug)]
pub enum LineError {
    Malformed(String),
    Cannot(String),
}

/// Nesting deeper than this is not computed (Python's own limit lies above it).
const MAX_DEPTH: usize = 512;

fn cannot(what: &str) -> LineError {
    LineError::Cannot(format!(
        "a log line Python's reader handles in a way not computed: {}",
        what
    ))
}

struct LineParser<'a> {
    b: &'a [u8],
    i: usize,
}

impl LineParser<'_> {
    fn peek(&self) -> Option<u8> {
        self.b.get(self.i).copied()
    }

    fn rest_starts(&self, w: &[u8]) -> bool {
        self.b[self.i..].starts_with(w)
    }

    fn ws(&mut self) {
        while matches!(self.peek(), Some(b' ' | b'\t' | b'\n' | b'\r')) {
            self.i += 1;
        }
    }

    fn value(&mut self, depth: usize) -> Result<V, LineError> {
        match self.peek() {
            Some(b'"') => Ok(V::Str(self.string()?)),
            Some(b'{') => self.object(depth + 1),
            Some(b'[') => self.array(depth + 1),
            Some(b'n') if self.rest_starts(b"null") => {
                self.i += 4;
                Ok(V::Null)
            }
            Some(b't') if self.rest_starts(b"true") => {
                self.i += 4;
                Ok(V::Bool(true))
            }
            Some(b'f') if self.rest_starts(b"false") => {
                self.i += 5;
                Ok(V::Bool(false))
            }
            Some(b'N') if self.rest_starts(b"NaN") => {
                Err(LineError::Malformed("NaN is not a JSON value".to_string()))
            }
            Some(b'I') if self.rest_starts(b"Infinity") => Err(LineError::Malformed(
                "Infinity is not a JSON value".to_string(),
            )),
            Some(b'-') if self.rest_starts(b"-Infinity") => Err(LineError::Malformed(
                "-Infinity is not a JSON value".to_string(),
            )),
            _ => self.number(),
        }
    }

    fn number(&mut self) -> Result<V, LineError> {
        let neg = self.peek() == Some(b'-');
        if neg {
            self.i += 1;
        }
        let start = self.i;
        match self.peek() {
            Some(b'0') => self.i += 1,
            Some(c) if c.is_ascii_digit() => {
                while self.peek().is_some_and(|c| c.is_ascii_digit()) {
                    self.i += 1;
                }
            }
            _ => return Err(cannot("no value")),
        }
        if matches!(self.peek(), Some(b'.' | b'e' | b'E')) {
            return Err(cannot("a number with a fraction or an exponent"));
        }
        let n = Int::from_digits(neg, &self.b[start..self.i])
            .ok_or_else(|| cannot("an integer too long"))?;
        Ok(V::Int(n))
    }

    fn object(&mut self, depth: usize) -> Result<V, LineError> {
        if depth > MAX_DEPTH {
            return Err(cannot("too deep"));
        }
        self.i += 1;
        let mut pairs: Vec<(String, V)> = Vec::new();
        self.ws();
        if self.peek() == Some(b'}') {
            self.i += 1;
            return Ok(V::Obj(pairs));
        }
        loop {
            if self.peek() != Some(b'"') {
                return Err(cannot("a key that is not a string"));
            }
            let key = self.string()?;
            self.ws();
            if self.peek() != Some(b':') {
                return Err(cannot("no colon"));
            }
            self.i += 1;
            self.ws();
            let v = self.value(depth)?;
            pairs.push((key, v));
            self.ws();
            match self.peek() {
                Some(b',') => {
                    self.i += 1;
                    self.ws();
                }
                Some(b'}') => {
                    self.i += 1;
                    break;
                }
                _ => return Err(cannot("no comma or closing brace")),
            }
        }
        // records.py's object_pairs_hook, called when the object closes: the first key seen twice.
        let mut seen: Vec<&str> = Vec::with_capacity(pairs.len());
        for (k, _) in &pairs {
            if seen.contains(&k.as_str()) {
                let shown = repr_str(k).map_err(LineError::Cannot)?;
                return Err(LineError::Malformed(format!("repeated key {}", shown)));
            }
            seen.push(k);
        }
        Ok(V::Obj(pairs))
    }

    fn array(&mut self, depth: usize) -> Result<V, LineError> {
        if depth > MAX_DEPTH {
            return Err(cannot("too deep"));
        }
        self.i += 1;
        let mut items = Vec::new();
        self.ws();
        if self.peek() == Some(b']') {
            self.i += 1;
            return Ok(V::Arr(items));
        }
        loop {
            items.push(self.value(depth)?);
            self.ws();
            match self.peek() {
                Some(b',') => {
                    self.i += 1;
                    self.ws();
                }
                Some(b']') => {
                    self.i += 1;
                    return Ok(V::Arr(items));
                }
                _ => return Err(cannot("no comma or closing bracket")),
            }
        }
    }

    fn hex4(&mut self) -> Result<u32, LineError> {
        if self.i + 4 > self.b.len() {
            return Err(cannot("a short escape"));
        }
        let mut v = 0u32;
        for k in 0..4 {
            let d = char::from(self.b[self.i + k])
                .to_digit(16)
                .ok_or_else(|| cannot("a bad escape"))?;
            v = v * 16 + d;
        }
        self.i += 4;
        Ok(v)
    }

    fn string(&mut self) -> Result<String, LineError> {
        self.i += 1;
        let mut out: Vec<u8> = Vec::new();
        loop {
            let c = self
                .peek()
                .ok_or_else(|| cannot("an unterminated string"))?;
            if c == b'"' {
                self.i += 1;
                break;
            }
            if c < 0x20 {
                return Err(cannot("a control character in a string"));
            }
            if c != b'\\' {
                out.push(c);
                self.i += 1;
                continue;
            }
            self.i += 1;
            let e = self
                .peek()
                .ok_or_else(|| cannot("an unterminated string"))?;
            self.i += 1;
            let ch = match e {
                b'"' => '"',
                b'\\' => '\\',
                b'/' => '/',
                b'b' => '\u{8}',
                b'f' => '\u{c}',
                b'n' => '\n',
                b'r' => '\r',
                b't' => '\t',
                b'u' => {
                    let u = self.hex4()?;
                    let code = if (0xd800..0xdc00).contains(&u) {
                        if !self.rest_starts(b"\\u") {
                            return Err(cannot("a lone surrogate"));
                        }
                        self.i += 2;
                        let low = self.hex4()?;
                        if !(0xdc00..0xe000).contains(&low) {
                            return Err(cannot("a lone surrogate"));
                        }
                        0x10000 + ((u - 0xd800) << 10) + (low - 0xdc00)
                    } else if (0xdc00..0xe000).contains(&u) {
                        return Err(cannot("a lone surrogate"));
                    } else {
                        u
                    };
                    char::from_u32(code).ok_or_else(|| cannot("a bad escape"))?
                }
                _ => return Err(cannot("a bad escape")),
            };
            let mut buf = [0u8; 4];
            out.extend_from_slice(ch.encode_utf8(&mut buf).as_bytes());
        }
        String::from_utf8(out).map_err(|_| cannot("a string that is not UTF-8"))
    }
}

/// `json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)` of records.py, for one decoded line.
pub fn loads_line(text: &str) -> Result<V, LineError> {
    let mut p = LineParser {
        b: text.as_bytes(),
        i: 0,
    };
    p.ws();
    let v = p.value(0)?;
    p.ws();
    if p.i != p.b.len() {
        return Err(cannot("extra data"));
    }
    Ok(v)
}

// ---------------------------------------------------------------------------------------------------------------
// Integers of any size as records.py's seq check uses them

/// A signed decimal integer of any length (Python's int), for `previous_seq + 1`.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Num {
    neg: bool,
    mag: Vec<u8>,
}

impl Num {
    pub fn of(n: &Int) -> Num {
        let t = n.text();
        let (neg, mag) = match t.strip_prefix('-') {
            Some(m) => (true, m.as_bytes().to_vec()),
            None => (false, t.as_bytes().to_vec()),
        };
        Num { neg, mag }
    }

    pub fn small(n: u64) -> Num {
        Num {
            neg: false,
            mag: n.to_string().into_bytes(),
        }
    }

    /// The number plus one.
    pub fn plus_one(&self) -> Num {
        let mut mag = self.mag.clone();
        if !self.neg {
            let mut k = mag.len();
            loop {
                if k == 0 {
                    mag.insert(0, b'1');
                    break;
                }
                k -= 1;
                if mag[k] == b'9' {
                    mag[k] = b'0';
                } else {
                    mag[k] += 1;
                    break;
                }
            }
            Num { neg: false, mag }
        } else {
            // A negative number's magnitude is at least 1: subtract one from it.
            let mut k = mag.len();
            while k > 0 {
                k -= 1;
                if mag[k] == b'0' {
                    mag[k] = b'9';
                } else {
                    mag[k] -= 1;
                    break;
                }
            }
            let start = mag.iter().position(|&d| d != b'0').unwrap_or(mag.len() - 1);
            let mag = mag[start..].to_vec();
            let neg = mag != b"0";
            Num { neg, mag }
        }
    }

    fn text(&self) -> String {
        let mut s = String::new();
        if self.neg {
            s.push('-');
        }
        s.push_str(&String::from_utf8_lossy(&self.mag));
        s
    }

    fn bit_length(&self) -> u64 {
        // The magnitude in base 2^32, least significant limb first.
        let mut limbs: Vec<u32> = Vec::new();
        for &d in &self.mag {
            let mut carry = u64::from(d - b'0');
            for limb in limbs.iter_mut() {
                let v = u64::from(*limb) * 10 + carry;
                *limb = v as u32;
                carry = v >> 32;
            }
            if carry > 0 {
                limbs.push(carry as u32);
            }
        }
        while limbs.last() == Some(&0) {
            limbs.pop();
        }
        match limbs.last() {
            None => 0,
            Some(top) => 32 * (limbs.len() as u64 - 1) + u64::from(32 - top.leading_zeros()),
        }
    }

    /// records.py `_int_text`: the decimal text, or "an integer of N bits" beyond 64 bits.
    pub fn int_text(&self) -> String {
        let bits = self.bit_length();
        if bits <= 64 {
            self.text()
        } else {
            format!("an integer of {} bits", bits)
        }
    }
}

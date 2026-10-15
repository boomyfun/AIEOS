//! JSON values as the Python source sees them (dict, list, str, int, bool, None), a strict reader (the rules of
//! conformance.py's `_loads`: no repeated key, no fraction or exponent, no NaN or infinity) and the canonical text of
//! `conformance.canon` / `conformance.canonical_text`.

use std::cmp::Ordering;
use std::collections::BTreeMap;

/// CPython's default limit on the digits of an integer read from text (`sys.int_info.default_max_str_digits`).
pub const MAX_INT_DIGITS: usize = 4300;
/// Nesting deeper than this is refused (the Python reader has a recursion limit of its own).
const MAX_DEPTH: usize = 512;

/// An integer of any size, kept as its decimal magnitude and a sign (Python's `int`).
#[derive(Clone, Debug)]
pub struct Int {
    neg: bool,
    mag: Vec<u8>,
}

impl Int {
    pub fn from_u64(n: u64) -> Int {
        Int {
            neg: false,
            mag: n.to_string().into_bytes(),
        }
    }

    /// The integer of a run of ASCII digits (leading zeros allowed), or None when it is empty, holds a non-digit or
    /// is longer than CPython converts (`int()` raises ValueError then).
    pub fn from_digits(neg: bool, digits: &[u8]) -> Option<Int> {
        if digits.is_empty()
            || digits.len() > MAX_INT_DIGITS
            || !digits.iter().all(u8::is_ascii_digit)
        {
            return None;
        }
        let start = digits
            .iter()
            .position(|&d| d != b'0')
            .unwrap_or(digits.len() - 1);
        let mag = digits[start..].to_vec();
        let neg = neg && mag != b"0";
        Some(Int { neg, mag })
    }

    pub fn is_nonneg(&self) -> bool {
        !self.neg
    }

    /// The product with a small non-negative factor.
    pub fn mul_small(&self, m: u64) -> Int {
        if m == 0 {
            return Int::from_u64(0);
        }
        let mut out: Vec<u8> = Vec::with_capacity(self.mag.len() + 20);
        let mut carry: u64 = 0;
        for &d in self.mag.iter().rev() {
            let v = u64::from(d - b'0') * m + carry;
            out.push(b'0' + (v % 10) as u8);
            carry = v / 10;
        }
        while carry > 0 {
            out.push(b'0' + (carry % 10) as u8);
            carry /= 10;
        }
        out.reverse();
        let start = out.iter().position(|&d| d != b'0').unwrap_or(out.len() - 1);
        let mag = out[start..].to_vec();
        let neg = self.neg && mag != b"0";
        Int { neg, mag }
    }

    /// Python's `str(n)`.
    pub fn text(&self) -> String {
        let mut s = String::with_capacity(self.mag.len() + 1);
        if self.neg {
            s.push('-');
        }
        for &d in &self.mag {
            s.push(char::from(d));
        }
        s
    }
}

impl PartialEq for Int {
    fn eq(&self, other: &Int) -> bool {
        self.cmp(other) == Ordering::Equal
    }
}

impl Eq for Int {}

impl PartialOrd for Int {
    fn partial_cmp(&self, other: &Int) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for Int {
    fn cmp(&self, other: &Int) -> Ordering {
        match (self.neg, other.neg) {
            (false, true) => Ordering::Greater,
            (true, false) => Ordering::Less,
            (false, false) => cmp_mag(&self.mag, &other.mag),
            (true, true) => cmp_mag(&other.mag, &self.mag),
        }
    }
}

fn cmp_mag(a: &[u8], b: &[u8]) -> Ordering {
    a.len().cmp(&b.len()).then_with(|| a.cmp(b))
}

/// One JSON value. Objects keep their keys sorted by code point, which is the order `sorted()` gives in Python.
#[derive(Clone, Debug)]
pub enum Json {
    Null,
    Bool(bool),
    Int(Int),
    Str(String),
    Arr(Vec<Json>),
    Obj(BTreeMap<String, Json>),
}

pub static NULL: Json = Json::Null;

impl Json {
    pub fn s(text: &str) -> Json {
        Json::Str(text.to_string())
    }

    pub fn strs<S: AsRef<str>>(items: &[S]) -> Json {
        Json::Arr(items.iter().map(|x| Json::s(x.as_ref())).collect())
    }

    pub fn obj(pairs: Vec<(&str, Json)>) -> Json {
        Json::Obj(pairs.into_iter().map(|(k, v)| (k.to_string(), v)).collect())
    }

    /// Python's `value.get(key)` on a dict, None (JSON null) for a missing key or a value that is not a dict.
    pub fn get(&self, key: &str) -> &Json {
        match self {
            Json::Obj(m) => m.get(key).unwrap_or(&NULL),
            _ => &NULL,
        }
    }

    /// Python's `key in value` for a dict (false for anything else).
    pub fn has(&self, key: &str) -> bool {
        match self {
            Json::Obj(m) => m.contains_key(key),
            _ => false,
        }
    }

    pub fn as_str(&self) -> Option<&str> {
        match self {
            Json::Str(s) => Some(s),
            _ => None,
        }
    }

    pub fn as_obj(&self) -> Option<&BTreeMap<String, Json>> {
        match self {
            Json::Obj(m) => Some(m),
            _ => None,
        }
    }

    pub fn as_arr(&self) -> Option<&Vec<Json>> {
        match self {
            Json::Arr(a) => Some(a),
            _ => None,
        }
    }

    pub fn as_bool(&self) -> Option<bool> {
        match self {
            Json::Bool(b) => Some(*b),
            _ => None,
        }
    }

    /// The integer when the value is an int that is not a bool.
    pub fn as_int(&self) -> Option<&Int> {
        match self {
            Json::Int(n) => Some(n),
            _ => None,
        }
    }

    pub fn is_null(&self) -> bool {
        matches!(self, Json::Null)
    }

    pub fn is_obj(&self) -> bool {
        matches!(self, Json::Obj(_))
    }

    pub fn is_arr(&self) -> bool {
        matches!(self, Json::Arr(_))
    }

    pub fn is_str(&self) -> bool {
        matches!(self, Json::Str(_))
    }

    pub fn is_bool(&self) -> bool {
        matches!(self, Json::Bool(_))
    }

    /// A non-empty string. Every string read here is valid Unicode, so it is also one UTF-8 can encode.
    pub fn is_text(&self) -> bool {
        matches!(self, Json::Str(s) if !s.is_empty())
    }

    /// Python's `value == text` for a str constant.
    pub fn eq_str(&self, text: &str) -> bool {
        matches!(self, Json::Str(s) if s == text)
    }

    /// Python's `isinstance(value, str) and value in values`.
    pub fn str_in(&self, values: &[&str]) -> bool {
        match self {
            Json::Str(s) => values.contains(&s.as_str()),
            _ => false,
        }
    }

    /// Python's `_int(v)`: an int, not a bool, at least 0.
    pub fn is_count(&self) -> bool {
        matches!(self, Json::Int(n) if n.is_nonneg())
    }

    /// The keys of a dict are exactly the given ones.
    pub fn keys_are(&self, keys: &[&str]) -> bool {
        match self {
            Json::Obj(m) => m.len() == keys.len() && keys.iter().all(|k| m.contains_key(*k)),
            _ => false,
        }
    }
}

/// Python's `==` between two JSON-like values (True == 1 and False == 0, as in Python).
pub fn py_eq(a: &Json, b: &Json) -> bool {
    match (a, b) {
        (Json::Null, Json::Null) => true,
        (Json::Bool(x), Json::Bool(y)) => x == y,
        (Json::Int(x), Json::Int(y)) => x == y,
        (Json::Bool(x), Json::Int(y)) | (Json::Int(y), Json::Bool(x)) => {
            *y == Int::from_u64(u64::from(*x))
        }
        (Json::Str(x), Json::Str(y)) => x == y,
        (Json::Arr(x), Json::Arr(y)) => {
            x.len() == y.len() && x.iter().zip(y).all(|(p, q)| py_eq(p, q))
        }
        (Json::Obj(x), Json::Obj(y)) => {
            x.len() == y.len() && x.iter().all(|(k, v)| y.get(k).is_some_and(|w| py_eq(v, w)))
        }
        _ => false,
    }
}

// ---------------------------------------------------------------------------------------------------------------
// The reader

/// The JSON value of a UTF-8 text, read as conformance.py's `_loads` reads it, or why not.
pub fn parse(data: &[u8]) -> Result<Json, String> {
    let text = std::str::from_utf8(data).map_err(|_| "the text is not UTF-8".to_string())?;
    let mut p = Parser {
        b: text.as_bytes(),
        i: 0,
    };
    p.ws();
    let value = p.value(0)?;
    p.ws();
    if p.i != p.b.len() {
        return Err(p.err("extra data"));
    }
    Ok(value)
}

struct Parser<'a> {
    b: &'a [u8],
    i: usize,
}

impl Parser<'_> {
    fn err(&self, what: &str) -> String {
        format!("not JSON: {} at byte {}", what, self.i)
    }

    fn peek(&self) -> Option<u8> {
        self.b.get(self.i).copied()
    }

    fn ws(&mut self) {
        while let Some(c) = self.peek() {
            if c == b' ' || c == b'\t' || c == b'\n' || c == b'\r' {
                self.i += 1;
            } else {
                break;
            }
        }
    }

    fn word(&mut self, w: &[u8], v: Json) -> Result<Json, String> {
        if self.b[self.i..].starts_with(w) {
            self.i += w.len();
            Ok(v)
        } else {
            Err(self.err("an unknown word"))
        }
    }

    fn value(&mut self, depth: usize) -> Result<Json, String> {
        match self.peek() {
            Some(b'{') => self.object(depth + 1),
            Some(b'[') => self.array(depth + 1),
            Some(b'"') => Ok(Json::Str(self.string()?)),
            Some(b't') => self.word(b"true", Json::Bool(true)),
            Some(b'f') => self.word(b"false", Json::Bool(false)),
            Some(b'n') => self.word(b"null", Json::Null),
            Some(c) if c == b'-' || c.is_ascii_digit() => self.number(),
            _ => Err(self.err("no value")),
        }
    }

    fn object(&mut self, depth: usize) -> Result<Json, String> {
        if depth > MAX_DEPTH {
            return Err(self.err("too deep"));
        }
        self.i += 1;
        let mut m = BTreeMap::new();
        self.ws();
        if self.peek() == Some(b'}') {
            self.i += 1;
            return Ok(Json::Obj(m));
        }
        loop {
            self.ws();
            if self.peek() != Some(b'"') {
                return Err(self.err("a key that is not a string"));
            }
            let key = self.string()?;
            self.ws();
            if self.peek() != Some(b':') {
                return Err(self.err("no colon"));
            }
            self.i += 1;
            self.ws();
            let v = self.value(depth)?;
            if m.contains_key(&key) {
                return Err(self.err("a repeated key"));
            }
            m.insert(key, v);
            self.ws();
            match self.peek() {
                Some(b',') => self.i += 1,
                Some(b'}') => {
                    self.i += 1;
                    return Ok(Json::Obj(m));
                }
                _ => return Err(self.err("no comma or closing brace")),
            }
        }
    }

    fn array(&mut self, depth: usize) -> Result<Json, String> {
        if depth > MAX_DEPTH {
            return Err(self.err("too deep"));
        }
        self.i += 1;
        let mut a = Vec::new();
        self.ws();
        if self.peek() == Some(b']') {
            self.i += 1;
            return Ok(Json::Arr(a));
        }
        loop {
            self.ws();
            a.push(self.value(depth)?);
            self.ws();
            match self.peek() {
                Some(b',') => self.i += 1,
                Some(b']') => {
                    self.i += 1;
                    return Ok(Json::Arr(a));
                }
                _ => return Err(self.err("no comma or closing bracket")),
            }
        }
    }

    fn hex4(&mut self) -> Result<u32, String> {
        if self.i + 4 > self.b.len() {
            return Err(self.err("a short escape"));
        }
        let mut v = 0u32;
        for k in 0..4 {
            let d = char::from(self.b[self.i + k])
                .to_digit(16)
                .ok_or_else(|| self.err("a bad escape"))?;
            v = v * 16 + d;
        }
        self.i += 4;
        Ok(v)
    }

    fn string(&mut self) -> Result<String, String> {
        self.i += 1;
        let mut out: Vec<u8> = Vec::new();
        loop {
            let c = self
                .peek()
                .ok_or_else(|| self.err("an unterminated string"))?;
            if c == b'"' {
                self.i += 1;
                break;
            }
            if c < 0x20 {
                return Err(self.err("a control character in a string"));
            }
            if c != b'\\' {
                out.push(c);
                self.i += 1;
                continue;
            }
            self.i += 1;
            let e = self
                .peek()
                .ok_or_else(|| self.err("an unterminated escape"))?;
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
                        if self.b[self.i..].starts_with(b"\\u") {
                            self.i += 2;
                            let low = self.hex4()?;
                            if !(0xdc00..0xe000).contains(&low) {
                                return Err(self.err("a lone surrogate"));
                            }
                            0x10000 + ((u - 0xd800) << 10) + (low - 0xdc00)
                        } else {
                            return Err(self.err("a lone surrogate"));
                        }
                    } else if (0xdc00..0xe000).contains(&u) {
                        return Err(self.err("a lone surrogate"));
                    } else {
                        u
                    };
                    char::from_u32(code).ok_or_else(|| self.err("a bad escape"))?
                }
                _ => return Err(self.err("a bad escape")),
            };
            let mut buf = [0u8; 4];
            out.extend_from_slice(ch.encode_utf8(&mut buf).as_bytes());
        }
        String::from_utf8(out).map_err(|_| self.err("a string that is not UTF-8"))
    }

    fn number(&mut self) -> Result<Json, String> {
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
            _ => return Err(self.err("a bad number")),
        }
        if matches!(self.peek(), Some(b'.') | Some(b'e') | Some(b'E')) {
            return Err(self.err("a number with a fraction or an exponent"));
        }
        let n = Int::from_digits(neg, &self.b[start..self.i])
            .ok_or_else(|| self.err("an integer too long"))?;
        Ok(Json::Int(n))
    }
}

// ---------------------------------------------------------------------------------------------------------------
// The canonical text (conformance-files.md section 2)

fn canon_into(value: &Json, indent: usize, out: &mut String) {
    match value {
        Json::Obj(m) => {
            if m.is_empty() {
                out.push_str("{}");
                return;
            }
            out.push_str("{\n");
            for (n, (k, v)) in m.iter().enumerate() {
                if n > 0 {
                    out.push_str(",\n");
                }
                push_pad(out, indent + 2);
                canon_str(k, out);
                out.push_str(": ");
                canon_into(v, indent + 2, out);
            }
            out.push('\n');
            push_pad(out, indent);
            out.push('}');
        }
        Json::Arr(a) => {
            if a.is_empty() {
                out.push_str("[]");
                return;
            }
            out.push_str("[\n");
            for (n, x) in a.iter().enumerate() {
                if n > 0 {
                    out.push_str(",\n");
                }
                push_pad(out, indent + 2);
                canon_into(x, indent + 2, out);
            }
            out.push('\n');
            push_pad(out, indent);
            out.push(']');
        }
        Json::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        Json::Null => out.push_str("null"),
        Json::Int(n) => out.push_str(&n.text()),
        Json::Str(s) => canon_str(s, out),
    }
}

fn push_pad(out: &mut String, n: usize) {
    for _ in 0..n {
        out.push(' ');
    }
}

fn canon_str(s: &str, out: &mut String) {
    out.push('"');
    for ch in s.chars() {
        if ch == '"' || ch == '\\' {
            out.push('\\');
            out.push(ch);
        } else if (ch as u32) < 0x20 {
            out.push_str(&format!("\\u{:04x}", ch as u32));
        } else {
            out.push(ch);
        }
    }
    out.push('"');
}

/// `canon(value)`: the canonical text without the final LF.
pub fn canon(value: &Json) -> String {
    let mut out = String::new();
    canon_into(value, 0, &mut out);
    out
}

/// `conformance.canonical_text(value)`: the canonical text with its final LF, as UTF-8 bytes.
pub fn canonical_text(value: &Json) -> Vec<u8> {
    let mut s = canon(value);
    s.push('\n');
    s.into_bytes()
}

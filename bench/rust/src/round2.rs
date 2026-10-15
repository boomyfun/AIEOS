//! Round 2 (the port brief's section 6): the round-2 input document read and the output document built, as
//! test_export_round2.py's `reference_document` builds it: for each append call in order `eventlog.append` with the
//! log carried from call to call, giving {result, reason, findings, seq, line, record}; for each reconcile case
//! `recovery.reconcile`, giving {log, events, expired, findings}; bytes as text and times in the input's text form;
//! one object {append, reconcile} in the canonical text, ASCII with LF line ends.
//!
//! It reads only the bytes it is given, writes nothing, and reads no clock (every time comes from the input).

use crate::eventlog::{append, AppendResult, Event, Lease, Time};
use crate::json::{canon, canonical_text, parse, Json};
use crate::pyval::V;
use crate::records2::valid_date_time;
use crate::recovery::{reconcile, RecoveryResult};

pub const USAGE: &str = "usage: port2 <round-2 input document>";
pub const CALL_KEYS: [&str; 10] = [
    "event_type",
    "payload",
    "event_id",
    "appended_at",
    "task_id",
    "fencing_token",
    "corrects",
    "lease",
    "recorder",
    "record_id",
];
pub const CASE_KEYS: [&str; 5] = ["log", "commits", "leases", "now", "recorder"];

/// `time_value(text)`: a "YYYY-MM-DDTHH:MM:SSZ" text read as a UTC time, refused unless written back it is the same
/// text. A year before 1000 is refused too: how Python writes it back (`%Y`) differs between platforms.
pub fn time_value(v: &V) -> Result<Time, String> {
    let bad = || {
        format!(
            "a time is not YYYY-MM-DDTHH:MM:SSZ: {:?}",
            v.as_str().unwrap_or("(not text)")
        )
    };
    let s = v
        .as_str()
        .ok_or_else(|| "a time is not text".to_string())?
        .as_bytes();
    let shape = b"dddd-dd-ddTdd:dd:ddZ";
    if s.len() != shape.len() {
        return Err(bad());
    }
    for (c, want) in s.iter().zip(shape.iter()) {
        let ok = if *want == b'd' {
            c.is_ascii_digit()
        } else {
            c == want
        };
        if !ok {
            return Err(bad());
        }
    }
    let num = |a: usize, b: usize| -> u32 {
        s[a..b]
            .iter()
            .fold(0u32, |n, d| n * 10 + u32::from(d - b'0'))
    };
    let t = Time {
        year: num(0, 4),
        month: num(5, 7),
        day: num(8, 10),
        hour: num(11, 13),
        minute: num(14, 16),
        second: num(17, 19),
    };
    if t.year < 1000 || !valid_date_time(t.year, t.month, t.day, t.hour, t.minute, t.second) {
        return Err(bad());
    }
    Ok(t)
}

/// `_lease_value(lease)`: None, or the lease with its expires_at read as a time.
pub fn lease_value(v: &V) -> Result<Option<Lease>, String> {
    if v.is_null() {
        return Ok(None);
    }
    let at = v
        .field("expires_at")
        .filter(|_| v.is_obj())
        .ok_or_else(|| "a lease is not an object with expires_at".to_string())?;
    Ok(Some(Lease {
        value: v.clone(),
        expires_at: time_value(at)?,
    }))
}

/// `parse_input(data)`: the input document's value, refused unless it is the canonical text of one object with
/// append and reconcile, each a list of objects with exactly their keys.
pub fn read_input(data: &[u8]) -> Result<V, String> {
    if !data.is_ascii() {
        return Err("not a round-2 input document: not ASCII".to_string());
    }
    let value = parse(data).map_err(|e| format!("not a round-2 input document: {}", e))?;
    if !matches!(&value, Json::Obj(m) if m.len() == 2 && m.contains_key("append") && m.contains_key("reconcile"))
    {
        return Err(
            "not a round-2 input document: not one object with append and reconcile".to_string(),
        );
    }
    let mut text = canon(&value);
    text.push('\n');
    if text.as_bytes() != data {
        return Err("not a round-2 input document: not its canonical text".to_string());
    }
    let doc = V::from_json(&value);
    let calls_ok = doc
        .get("append")
        .as_arr()
        .is_some_and(|a| a.iter().all(|c| c.keys_are(&CALL_KEYS)));
    if !calls_ok {
        return Err(
            "not a round-2 input document: an append call without exactly its keys".to_string(),
        );
    }
    let cases_ok = doc
        .get("reconcile")
        .as_arr()
        .is_some_and(|a| a.iter().all(|c| c.keys_are(&CASE_KEYS)));
    if !cases_ok {
        return Err(
            "not a round-2 input document: a reconcile case without exactly its keys".to_string(),
        );
    }
    Ok(doc)
}

/// The text of bytes the port built (ASCII in every case it computes).
fn text_of(bytes: &[u8]) -> Result<String, String> {
    if !bytes.is_ascii() {
        return Err("a log that is not ASCII".to_string());
    }
    Ok(String::from_utf8_lossy(bytes).into_owned())
}

/// One append call over the log given: `eventlog.append` with the call's arguments.
pub fn append_call(log: &[u8], call: &V) -> Result<AppendResult, String> {
    let lease = lease_value(call.get("lease"))?;
    let event = Event {
        event_type: call.get("event_type"),
        payload: call.get("payload"),
        event_id: call.get("event_id"),
        appended_at: time_value(call.get("appended_at"))?,
        task_id: call.get("task_id"),
        fencing_token: call.get("fencing_token"),
        corrects: call.get("corrects"),
        lease: lease.as_ref(),
        recorder: call.get("recorder"),
        record_id: call.get("record_id"),
    };
    append(log, &event).map_err(|e| format!("an append call cannot be computed: {}", e))
}

/// The entry of one append result: {result, reason, findings, seq, line, record}.
pub fn append_entry(r: &AppendResult) -> Result<V, String> {
    let line = match &r.line {
        Some(b) => V::Str(text_of(b)?),
        None => V::Null,
    };
    Ok(V::obj(vec![
        ("result", V::s(r.result)),
        ("reason", r.reason.map(V::s).unwrap_or(V::Null)),
        ("findings", V::strs(&r.findings)),
        ("seq", r.seq.clone().unwrap_or(V::Null)),
        ("line", line),
        ("record", r.record.clone().unwrap_or(V::Null)),
    ]))
}

/// Every append entry in order, the log carried from call to call (an appended result's new log becomes the next
/// call's log; any other result leaves it).
pub fn append_entries(doc: &V) -> Result<Vec<V>, String> {
    let mut log: Vec<u8> = Vec::new();
    let mut out = Vec::new();
    for call in doc.get("append").as_arr().unwrap_or(&[]) {
        let r = append_call(&log, call)?;
        out.push(append_entry(&r)?);
        if r.result == "appended" {
            if let Some(new_log) = r.log {
                log = new_log;
            }
        }
    }
    Ok(out)
}

/// The leases of a case as Python iterates `case['leases']`: a list element by element; an empty text or an empty
/// object gives none; any other value is refused (a non-empty text or object yields items that are not leases).
fn case_leases(v: &V) -> Result<Vec<Lease>, String> {
    let items: &[V] = match v {
        V::Arr(a) => a,
        V::Str(s) if s.is_empty() => &[],
        V::Obj(p) if p.is_empty() => &[],
        _ => return Err("the leases are not a list of lease objects".to_string()),
    };
    let mut out = Vec::new();
    for item in items {
        match lease_value(item)? {
            Some(l) => out.push(l),
            None => return Err("a lease is not a mapping".to_string()),
        }
    }
    Ok(out)
}

/// One reconcile case: `recovery.reconcile` with the case's arguments.
pub fn reconcile_case(case: &V) -> Result<RecoveryResult, String> {
    let log = case
        .get("log")
        .as_str()
        .ok_or_else(|| "a reconcile case cannot be computed: its log is not text".to_string())?;
    let leases = case_leases(case.get("leases"))?;
    let now = time_value(case.get("now"))?;
    reconcile(
        log.as_bytes(),
        case.get("commits"),
        &leases,
        now,
        case.get("recorder"),
    )
    .map_err(|e| format!("a reconcile case cannot be computed: {}", e))
}

/// The entry of one recovery result: {log, events, expired, findings}.
pub fn reconcile_entry(r: &RecoveryResult) -> Result<V, String> {
    Ok(V::obj(vec![
        ("log", V::Str(text_of(&r.log)?)),
        ("events", V::Arr(r.events.clone())),
        (
            "expired",
            V::Arr(r.expired.iter().map(|l| l.value.clone()).collect()),
        ),
        ("findings", V::strs(&r.findings)),
    ]))
}

/// Every reconcile entry in case order.
pub fn reconcile_entries(doc: &V) -> Result<Vec<V>, String> {
    let mut out = Vec::new();
    for case in doc.get("reconcile").as_arr().unwrap_or(&[]) {
        out.push(reconcile_entry(&reconcile_case(case)?)?);
    }
    Ok(out)
}

/// The output document's bytes for the input document's bytes, or why it cannot be built (nothing is printed then).
pub fn document(data: &[u8]) -> Result<Vec<u8>, String> {
    let doc = read_input(data)?;
    let out = V::obj(vec![
        ("append", V::Arr(append_entries(&doc)?)),
        ("reconcile", V::Arr(reconcile_entries(&doc)?)),
    ]);
    let bytes = canonical_text(&out.to_json());
    if bytes.iter().any(|&b| b == b'\r' || b > 127) {
        return Err("the document is not ASCII with LF line ends".to_string());
    }
    Ok(bytes)
}

/// The one argument, or the usage text when there is not exactly one.
pub fn the_argument(args: &[String]) -> Result<&str, String> {
    match args {
        [one] => Ok(one.as_str()),
        _ => Err(USAGE.to_string()),
    }
}

/// The whole run but the read of the file and the write: the arguments (without the program name), the reader of
/// the one path, and the document's bytes, or why there is none.
pub fn run(
    args: &[String],
    read: &dyn Fn(&str) -> Result<Vec<u8>, String>,
) -> Result<Vec<u8>, String> {
    let path = the_argument(args)?;
    let data = read(path)?;
    document(&data)
}

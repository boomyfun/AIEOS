//! eventlog.py's `append` (TASK-007, TASK-015): whether and how one event is appended to a log given as bytes, as an
//! `AppendResult` (appended, duplicate, or refused with one reason). It returns bytes and writes none.

use std::collections::HashSet;

use crate::pyval::{dumps, py_eq, repr, V};
use crate::records2::{check_fence, check_log, check_payload, m_task, R};

pub const LEASE_KEYS: [&str; 3] = ["task_id", "fencing_token", "expires_at"];
const SAME_EVENT_KEYS: [&str; 5] = ["type", "payload", "task_id", "fencing_token", "corrects"];

/// A timezone-aware UTC time to the second (every time of round 2 has that form). The field order makes the derived
/// order the order of time.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub struct Time {
    pub year: u32,
    pub month: u32,
    pub day: u32,
    pub hour: u32,
    pub minute: u32,
    pub second: u32,
}

impl Time {
    /// eventlog's `_time_text`: ISO 8601 UTC with "Z", to the second, four-digit year.
    pub fn text(&self) -> String {
        format!(
            "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}Z",
            self.year, self.month, self.day, self.hour, self.minute, self.second
        )
    }
}

/// A lease as the caller holds it: the mapping as given, and its expires_at read as a UTC time.
#[derive(Clone, Debug)]
pub struct Lease {
    pub value: V,
    pub expires_at: Time,
}

/// The arguments of one `append` call after the log (None is JSON null).
pub struct Event<'a> {
    pub event_type: &'a V,
    pub payload: &'a V,
    pub event_id: &'a V,
    pub appended_at: Time,
    pub task_id: &'a V,
    pub fencing_token: &'a V,
    pub corrects: &'a V,
    pub lease: Option<&'a Lease>,
    pub recorder: &'a V,
    pub record_id: &'a V,
}

/// The result of one append (eventlog.py's AppendResult).
#[derive(Clone, Debug)]
pub struct AppendResult {
    pub result: &'static str,
    pub reason: Option<&'static str>,
    pub seq: Option<V>,
    pub line: Option<Vec<u8>>,
    pub log: Option<Vec<u8>>,
    pub findings: Vec<String>,
    pub record: Option<V>,
}

fn refused(
    reason: &'static str,
    findings: Vec<String>,
    seq: Option<V>,
    record: Option<V>,
) -> AppendResult {
    AppendResult {
        result: "refused",
        reason: Some(reason),
        seq,
        line: None,
        log: None,
        findings,
        record,
    }
}

/// `_same_text`: the canonical text of the keys that make an event the same event, absent keys left out.
fn same_text(obj: &V) -> String {
    let pairs: Vec<(&str, V)> = SAME_EVENT_KEYS
        .iter()
        .filter_map(|k| obj.field(k).map(|v| (*k, v.clone())))
        .collect();
    dumps(&V::obj(pairs))
}

/// `refusal_record`: the payload of the record.added event that records a fence refusal.
pub fn refusal_record(event_id: &V, task_id: &V, recorder: &V, record_id: &V) -> V {
    V::obj(vec![
        ("record_id", record_id.clone()),
        ("fact_kind", V::s("observation")),
        ("source_class", V::s("deterministic_tool_local")),
        ("recorder", recorder.clone()),
        ("subject", task_id.clone()),
        ("evidence_type", V::s("refused_submission")),
        ("outcome", V::s("fail")),
        ("refers_to", event_id.clone()),
    ])
}

/// `_lease_findings`: why the lease given does not hold the event; empty when it does.
fn lease_findings(
    lease: Option<&Lease>,
    task_id: &V,
    fencing_token: &V,
    appended_at: Time,
) -> R<Vec<String>> {
    let lease = match lease {
        None => return Ok(vec!["fence: no lease is given".to_string()]),
        Some(l) => l,
    };
    if !lease.value.keys_are(&LEASE_KEYS) {
        return Ok(vec![
            "fence: the lease is not a mapping with exactly task_id, fencing_token and expires_at"
                .to_string(),
        ]);
    }
    let mut found = Vec::new();
    if fencing_token.is_null() {
        found.push("fence: the event carries no fencing_token".to_string());
    }
    let lease_task = lease.value.get("task_id");
    if !py_eq(lease_task, task_id) {
        found.push(format!(
            "fence: the lease is on {}, not on the event's task {}",
            repr(lease_task)?,
            repr(task_id)?
        ));
    }
    let lease_token = dumps(lease.value.get("fencing_token"));
    if !fencing_token.is_null() && lease_token != dumps(fencing_token) {
        found.push("fence: the event's fencing_token is not the lease's".to_string());
    }
    if lease.expires_at <= appended_at {
        found.push("fence: the lease expired at or before the append time".to_string());
    }
    Ok(found)
}

/// `eventlog.append(log, ...)`. An `Err` is a call the port cannot compute (fail closed).
pub fn append(log: &[u8], e: &Event) -> R<AppendResult> {
    // AC1: the given log, checked before anything else.
    let report = check_log(log)?;
    let mut log_findings = report.findings();
    if !log.is_empty() && !log.ends_with(b"\n") {
        log_findings.push("2:lf: the log does not end with LF".to_string());
    }
    if !log_findings.is_empty() {
        return Ok(refused("log", log_findings, None, None));
    }

    // AC2: idempotency by event_id, against the first line that holds it.
    let mut new_pairs: Vec<(&str, V)> = vec![
        ("type", e.event_type.clone()),
        ("payload", e.payload.clone()),
    ];
    for (key, value) in [
        ("task_id", e.task_id),
        ("fencing_token", e.fencing_token),
        ("corrects", e.corrects),
    ] {
        if !value.is_null() {
            new_pairs.push((key, value.clone()));
        }
    }
    let new_event = V::obj(new_pairs);
    let mut known_ids: HashSet<String> = HashSet::new();
    for line in &report.lines {
        let old = line
            .event
            .as_ref()
            .ok_or_else(|| "a line of a log without findings has no event".to_string())?;
        let old_id = old.get("event_id");
        if let Some(id) = old_id.as_str() {
            known_ids.insert(id.to_string());
        }
        if line.duplicate_of.is_none() && py_eq(old_id, e.event_id) {
            let seq = old.get("seq").clone();
            if same_text(old) == same_text(&new_event) {
                return Ok(AppendResult {
                    result: "duplicate",
                    reason: None,
                    seq: Some(seq),
                    line: None,
                    log: None,
                    findings: Vec::new(),
                    record: None,
                });
            }
            let seq_text = seq
                .as_int()
                .map(|n| n.text())
                .ok_or_else(|| "a seq that is not an integer".to_string())?;
            let finding = format!(
                "event_id {} is on the line with seq {} with another event",
                repr(e.event_id)?,
                seq_text
            );
            return Ok(refused("conflict", vec![finding], Some(seq), None));
        }
    }

    // AC3: the new event's own form.
    let mut findings = Vec::new();
    if !e.event_id.is_text() {
        findings.push("6.1:event_id: event_id is not a non-empty string".to_string());
    }
    if !e.task_id.is_null() && !m_task(e.task_id) {
        findings.push("6.1:task_id: task_id is not TASK- followed by digits (reading)".to_string());
    }
    if !e.fencing_token.is_null() {
        findings.extend(check_fence(
            &V::obj(vec![("fencing_token", e.fencing_token.clone())]),
            None,
        ));
    }
    if !e.corrects.is_null() {
        let ok = matches!(e.corrects.as_str(), Some(c) if !c.is_empty() && known_ids.contains(c));
        if !ok {
            findings.push(
                "6.1:corrects: corrects is not the event_id of a line of the log (reading)"
                    .to_string(),
            );
        }
    }
    findings.extend(check_payload(e.event_type, e.payload, "payload")?);
    if !findings.is_empty() {
        return Ok(refused("event", findings, None, None));
    }
    let seq = report.lines.len() + 1;
    let mut obj = match new_event {
        V::Obj(p) => p,
        _ => Vec::new(),
    };
    obj.push(("event_id".to_string(), e.event_id.clone()));
    obj.push(("appended_at".to_string(), V::s(&e.appended_at.text())));
    obj.push(("seq".to_string(), V::int(seq as u64)));
    let mut line_text = dumps(&V::Obj(obj));
    line_text.push('\n');
    let line_bytes = line_text.into_bytes();

    // AC6, AC7: the fence.
    if !e.fencing_token.is_null() || e.event_type.eq_str("task.submitted") {
        let fence = if e.task_id.is_null() {
            vec!["fence: the event names no task_id, so no lease can be on its task".to_string()]
        } else {
            lease_findings(e.lease, e.task_id, e.fencing_token, e.appended_at)?
        };
        if !fence.is_empty() {
            let mut fence = fence;
            if e.task_id.is_null() {
                fence.push("fence: no refusal record, the event names no task_id".to_string());
                return Ok(refused("fence", fence, None, None));
            }
            if !(e.recorder.is_text() && e.record_id.is_text()) {
                fence.push(
                    "fence: no refusal record, recorder and record_id are not both non-empty strings".to_string(),
                );
                return Ok(refused("fence", fence, None, None));
            }
            let record = refusal_record(e.event_id, e.task_id, e.recorder, e.record_id);
            return Ok(refused("fence", fence, None, Some(record)));
        }
    }

    // AC4: the whole log after the append.
    let mut new_log = log.to_vec();
    new_log.extend_from_slice(&line_bytes);
    let after = check_log(&new_log)?.findings();
    if !after.is_empty() {
        return Ok(refused("log_after", after, None, None));
    }

    // AC5: the given bytes are an exact prefix, followed by exactly one line.
    let one_line = line_bytes.iter().filter(|&&b| b == b'\n').count() == 1;
    if !(new_log.starts_with(log) && new_log[log.len()..] == line_bytes[..] && one_line) {
        return Err("the append-only property failed (AC5)".to_string());
    }
    Ok(AppendResult {
        result: "appended",
        reason: None,
        seq: Some(V::int(seq as u64)),
        line: Some(line_bytes),
        log: Some(new_log),
        findings: Vec::new(),
        record: None,
    })
}

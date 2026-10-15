//! The forms of records.py that round 2 uses, with the full text of each finding ("rule: detail", as `str(f)`):
//! `check_log` (and every line check it makes), `check_payload`, `check_record`, `check_decision` and `_check_fence`.
//!
//! An `Err` is a case the port cannot compute: a text Python would build from its own messages or type names (a JSON
//! decoder error, "the line is a JSON <type>", a TypeError), or a value the port does not carry (fail closed).

use std::collections::HashMap;

use crate::pyval::{dumps, loads_line, py_eq, repr, repr_str, LineError, Num, V};
use crate::records::{BLOCKING_KINDS, CI_CLASS, STATE_NAMES};

pub type R<T> = Result<T, String>;

pub const EVENT_TYPES: [&str; 16] = [
    "task.drafted",
    "task.approved",
    "task.blocked",
    "task.unblocked",
    "task.submitted",
    "decision.acceptance",
    "decision.execution",
    "task.done",
    "task.stale",
    "task.replanned",
    "intent.changed",
    "drift.detected",
    "violation.detected",
    "evidence.stale",
    "conflict.detected",
    "record.added",
];
const ENVELOPE_REQUIRED: [&str; 5] = ["event_id", "type", "appended_at", "seq", "payload"];
const ENVELOPE_KEYS: [&str; 8] = [
    "event_id",
    "type",
    "appended_at",
    "seq",
    "payload",
    "task_id",
    "fencing_token",
    "corrects",
];
const FACT_KINDS: [&str; 4] = ["claim", "observation", "interpretation", "authority"];
const SOURCE_CLASSES: [&str; 8] = [
    "agent_declared",
    "same_lineage_review",
    "deterministic_tool_local",
    CI_CLASS,
    "cross_vendor_review",
    "decision_agent",
    "human_authority",
    "delegate_ai",
];
const OUTCOMES: [&str; 3] = ["pass", "fail", "blocking"];
const BINDING_KINDS: [&str; 4] = ["contract", "acceptance", "change_request", "baseline"];
const RECORD_REQUIRED: [&str; 5] = [
    "record_id",
    "fact_kind",
    "source_class",
    "recorder",
    "subject",
];
const RECORD_KEYS: [&str; 20] = [
    "record_id",
    "fact_kind",
    "source_class",
    "recorder",
    "subject",
    "evidence_type",
    "dimension",
    "gate",
    "outcome",
    "blocking_kind",
    "commit",
    "intent_versions",
    "approval_binding",
    "decision_ref",
    "models",
    "basis",
    "stands_for",
    "refers_to",
    "risk_class",
    "evidence_profile",
];
const AUDIT_COPY_TYPES: [&str; 2] = ["risk_class", "evidence_profile"];
const AUDIT_COPY_SOURCES: [&str; 2] = ["deterministic_tool_local", CI_CLASS];
const AUDIT_COPY_FORBIDDEN: [&str; 4] = ["outcome", "gate", "blocking_kind", "dimension"];
const RISK_CLASSES: [&str; 4] = ["low", "medium", "high", "critical"];
const ACCEPTANCE_DECISIONS: [&str; 5] = [
    "ACCEPT",
    "NEEDS_REVIEW",
    "INSUFFICIENT_EVIDENCE",
    "NEEDS_REWORK",
    "REJECT",
];
const EXECUTION_DECISIONS: [&str; 8] = [
    "CONTINUE",
    "CONTINUE_WITH",
    "REPLAN",
    "STOP: scope invalid",
    "STOP: runtime insufficient",
    "STOP: violation",
    "BLOCKED",
    "ESCALATE",
];
const ACCEPTANCE_KEYS: [&str; 18] = [
    "task_content_hash",
    "evaluated_commit",
    "intent_versions",
    "next_task_state",
    "table_row",
    "profile_used",
    "missing_gates",
    "blocking",
    "failed_gates",
    "reverify",
    "approval_record",
    "policy_version",
    "level_version",
    "governor_identity",
    "ruleset_version",
    "scenario_set_hash",
    "uncovered",
    "rests_on_ai",
];
const PROFILE_KEYS: [&str; 4] = ["dimension", "required", "satisfied_by", "missing_types"];
const EXECUTION_KEYS: [&str; 19] = [
    "contract_hash",
    "contract_version",
    "base_commit",
    "head_commit",
    "log_seq",
    "delta",
    "checks",
    "outcomes_fired",
    "read_set",
    "signatures",
    "intent_versions",
    "dependencies",
    "constitution",
    "runtime",
    "budgets",
    "policy_version",
    "engine_identity",
    "uncovered",
    "state_effect",
];
const EXECUTION_ORDER: [&str; 7] = [
    "STOP: violation",
    "STOP: scope invalid",
    "STOP: runtime insufficient",
    "ESCALATE",
    "BLOCKED",
    "REPLAN",
    "CONTINUE_WITH",
];
const CHECK_KEYS: [&str; 4] = ["check", "status", "outcome", "detail"];
const CHECK_STATUSES: [&str; 4] = ["passed", "fired", "skipped", "not_run"];
const RECORD_PAYLOAD_TYPES: [&str; 4] = [
    "record.added",
    "violation.detected",
    "decision.acceptance",
    "decision.execution",
];
const DECISION_TYPES: [&str; 2] = ["decision.acceptance", "decision.execution"];
const EXECUTION_LISTS: [&str; 4] = ["delta", "signatures", "uncovered", "state_effect"];
const EXECUTION_OBJECTS: [&str; 5] = [
    "read_set",
    "dependencies",
    "constitution",
    "runtime",
    "budgets",
];
const BOM: &[u8] = b"\xef\xbb\xbf";

/// One finding's text, `str(Finding(rule, detail))`.
fn fnd(rule: &str, detail: String) -> String {
    format!("{}: {}", rule, detail)
}

// ---------------------------------------------------------------------------------------------------------------
// The fixed patterns (re.fullmatch; "[0-9]" and "[0-9a-f]" are ASCII ranges)

fn lower_hex(s: &str) -> bool {
    s.bytes()
        .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

pub fn digits(s: &str) -> bool {
    !s.is_empty() && s.bytes().all(|b| b.is_ascii_digit())
}

pub fn m_hex64(v: &V) -> bool {
    matches!(v.as_str(), Some(s) if s.len() == 64 && lower_hex(s))
}

pub fn m_commit(v: &V) -> bool {
    matches!(v.as_str(), Some(s) if (s.len() == 40 || s.len() == 64) && lower_hex(s))
}

pub fn m_task(v: &V) -> bool {
    matches!(v.as_str(), Some(s) if s.strip_prefix("TASK-").is_some_and(digits))
}

pub fn m_version(v: &V) -> bool {
    matches!(v.as_str(), Some(s) if s.strip_prefix('v').is_some_and(digits))
}

fn m_gate(v: &V) -> bool {
    matches!(v.as_str(), Some(s) if s.strip_prefix('G').is_some_and(digits))
}

fn m_change(v: &V) -> bool {
    matches!(v.as_str(), Some(s) if s.strip_prefix("CHG-").is_some_and(digits))
}

fn m_python(v: &V) -> bool {
    match v.as_str() {
        Some(s) => {
            let parts: Vec<&str> = s.split('.').collect();
            parts.len() == 3 && parts.iter().all(|p| digits(p))
        }
        None => false,
    }
}

/// `_is_str_list`: a list of non-empty strings.
fn is_text_list(v: &V) -> bool {
    matches!(v.as_arr(), Some(a) if a.iter().all(V::is_text))
}

/// `_is_intent_versions`: a dict mapping non-empty strings to versions v<digits>.
fn is_intent_versions(v: &V) -> bool {
    match v.as_obj() {
        Some(p) => p.iter().all(|(k, x)| !k.is_empty() && m_version(x)),
        None => false,
    }
}

/// `_is_time`: a UTC time of section 6.1 that exists on the calendar.
fn is_time(v: &V) -> bool {
    let s = match v.as_str() {
        Some(s) => s.as_bytes(),
        None => return false,
    };
    if s.len() < 20 || s[s.len() - 1] != b'Z' {
        return false;
    }
    let head = &s[..19];
    let shape = b"dddd-dd-ddTdd:dd:dd";
    for (c, want) in head.iter().zip(shape.iter()) {
        let ok = if *want == b'd' {
            c.is_ascii_digit()
        } else {
            c == want
        };
        if !ok {
            return false;
        }
    }
    let frac = &s[19..s.len() - 1];
    if !frac.is_empty()
        && !(frac[0] == b'.' && frac.len() > 1 && frac[1..].iter().all(u8::is_ascii_digit))
    {
        return false;
    }
    let num = |a: usize, b: usize| -> u32 {
        head[a..b]
            .iter()
            .fold(0u32, |n, d| n * 10 + u32::from(d - b'0'))
    };
    valid_date_time(
        num(0, 4),
        num(5, 7),
        num(8, 10),
        num(11, 13),
        num(14, 16),
        num(17, 19),
    )
}

/// Whether `datetime.datetime(y, mo, d, h, mi, s)` exists (year 1 to 9999).
pub fn valid_date_time(y: u32, mo: u32, d: u32, h: u32, mi: u32, s: u32) -> bool {
    (1..=9999).contains(&y)
        && (1..=12).contains(&mo)
        && d >= 1
        && d <= days_in_month(y, mo)
        && h < 24
        && mi < 60
        && s < 60
}

fn days_in_month(y: u32, mo: u32) -> u32 {
    match mo {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        _ => {
            if (y.is_multiple_of(4) && !y.is_multiple_of(100)) || y.is_multiple_of(400) {
                29
            } else {
                28
            }
        }
    }
}

fn sorted_keys<'a>(obj: &'a V, keep: &dyn Fn(&str) -> bool) -> Vec<&'a String> {
    let mut keys: Vec<&String> = obj
        .as_obj()
        .unwrap_or(&[])
        .iter()
        .map(|(k, _)| k)
        .filter(|k| keep(k))
        .collect();
    keys.sort();
    keys
}

// ---------------------------------------------------------------------------------------------------------------
// The payload forms of section 6.3

#[derive(Clone, Copy)]
enum Form {
    Version,
    Hash,
    Str,
    List,
    Commit,
    Bool,
    OneOf(&'static [&'static str]),
    Change,
}

impl Form {
    fn test(self, v: &V) -> bool {
        match self {
            Form::Version => m_version(v),
            Form::Hash => m_hex64(v),
            Form::Str => v.is_text(),
            Form::List => is_text_list(v),
            Form::Commit => m_commit(v),
            Form::Bool => matches!(v, V::Bool(_)),
            Form::OneOf(values) => v.str_in(values),
            Form::Change => m_change(v),
        }
    }

    fn text(self) -> String {
        match self {
            Form::Version => "v followed by digits".to_string(),
            Form::Hash => "64 lowercase hex digits".to_string(),
            Form::Str => "a non-empty string".to_string(),
            Form::List => {
                "a list of non-empty strings (reading: section 6.3 says lists of strings)"
                    .to_string()
            }
            Form::Commit => "a full lowercase hex commit id".to_string(),
            Form::Bool => "true or false".to_string(),
            Form::OneOf(values) => format!("one of {}", values.join(", ")),
            Form::Change => "CHG- followed by digits".to_string(),
        }
    }
}

const STALE_CAUSES: [&str; 2] = ["intent_change", "conflict"];
const STALE_REASONS: [&str; 2] = ["commit", "intent_version"];

fn payload_forms(event_type: &str) -> Vec<(&'static str, Form)> {
    match event_type {
        "task.drafted" | "task.replanned" => {
            vec![
                ("contract_version", Form::Version),
                ("contract_hash", Form::Hash),
            ]
        }
        "task.approved" => vec![
            ("contract_version", Form::Version),
            ("contract_hash", Form::Hash),
            ("approval_record", Form::Str),
        ],
        "task.blocked" => vec![("reason", Form::Str), ("blocked_by", Form::List)],
        "task.unblocked" => vec![("reason", Form::Str)],
        "task.submitted" => vec![("commit", Form::Commit), ("compensating", Form::Bool)],
        "task.done" => vec![("decision_record", Form::Str)],
        "task.stale" => vec![
            ("cause", Form::OneOf(&STALE_CAUSES)),
            ("refers_to", Form::Str),
        ],
        "intent.changed" => vec![
            ("entity", Form::Str),
            ("from_version", Form::Version),
            ("to_version", Form::Version),
            ("change_request", Form::Change),
        ],
        "drift.detected" => vec![("paths", Form::List), ("entities", Form::List)],
        "evidence.stale" => vec![
            ("records", Form::List),
            ("reason", Form::OneOf(&STALE_REASONS)),
        ],
        _ => Vec::new(),
    }
}

/// `_keys_and_forms`: exactly the keys of the forms, each of its form.
fn keys_and_forms(
    obj: &V,
    forms: &[(&'static str, Form)],
    rule: &str,
    where_: &str,
) -> R<Vec<String>> {
    let mut f = Vec::new();
    for key in sorted_keys(obj, &|k| !forms.iter().any(|(n, _)| *n == k)) {
        f.push(fnd(
            &format!("{}:unknown_key", rule),
            format!(
                "{} has the key {}, which section 6.3 does not name",
                where_,
                repr_str(key)?
            ),
        ));
    }
    let mut names: Vec<(&'static str, Form)> = forms.to_vec();
    names.sort_by(|a, b| a.0.cmp(b.0));
    for (key, form) in names {
        match obj.field(key) {
            None => f.push(fnd(
                &format!("{}:missing_key", rule),
                format!("{} lacks {}", where_, repr_str(key)?),
            )),
            Some(v) => {
                if !form.test(v) {
                    f.push(fnd(
                        &format!("{}:{}", rule, key),
                        format!("{} {} is not {}", where_, repr_str(key)?, form.text()),
                    ));
                }
            }
        }
    }
    Ok(f)
}

// ---------------------------------------------------------------------------------------------------------------
// check_record (section 6.2)

/// `check_record(record, extra_keys, where, section)`.
pub fn check_record(record: &V, extra: &[&str], where_: &str, section: &str) -> R<Vec<String>> {
    if !record.is_obj() {
        return Ok(vec![fnd(
            "6.2:record",
            format!("{} is not a JSON object", where_),
        )]);
    }
    let mut f = Vec::new();
    let names = if section == "6.2" {
        "section 6.2 does not name".to_string()
    } else {
        format!("sections 6.2 and {} do not name", section)
    };
    for key in sorted_keys(record, &|k| {
        !RECORD_KEYS.contains(&k) && !extra.contains(&k)
    }) {
        f.push(fnd(
            &format!("{}:unknown_key", section),
            format!("{} has the key {}, which {}", where_, repr_str(key)?, names),
        ));
    }
    for key in RECORD_REQUIRED {
        if !record.has(key) {
            f.push(fnd(
                "6.2:missing_key",
                format!("{} lacks {} (reading: required)", where_, repr_str(key)?),
            ));
        }
    }
    for key in ["record_id", "recorder", "subject"] {
        if record.has(key) && !record.get(key).is_text() {
            f.push(fnd(
                &format!("6.2:{}", key),
                format!("{} {} is not a non-empty string", where_, repr_str(key)?),
            ));
        }
    }
    if record.has("fact_kind") && !record.get("fact_kind").str_in(&FACT_KINDS) {
        f.push(fnd(
            "6.2:fact_kind",
            format!(
                "{} fact_kind is not claim, observation, interpretation or authority",
                where_
            ),
        ));
    }
    if record.has("source_class") && !record.get("source_class").str_in(&SOURCE_CLASSES) {
        f.push(fnd(
            "6.2:source_class",
            format!("{} source_class is not one of the classes of DM B3", where_),
        ));
    }
    check_outcome(record, where_, &mut f);
    if record.has("commit") && !m_commit(record.get("commit")) {
        f.push(fnd(
            "6.2:commit",
            format!("{} commit is not a full lowercase hex commit id", where_),
        ));
    }
    if record.has("intent_versions") && !is_intent_versions(record.get("intent_versions")) {
        f.push(fnd(
            "6.2:intent_versions",
            format!(
                "{} intent_versions does not map ids to versions v<digits>",
                where_
            ),
        ));
    }
    check_binding(record, where_, &mut f);
    check_review_fields(record, where_, &mut f);
    if record.has("gate") && !m_gate(record.get("gate")) {
        f.push(fnd(
            "6.2:gate",
            format!("{} gate is not G followed by digits", where_),
        ));
    }
    for key in ["evidence_type", "dimension", "refers_to"] {
        if record.has(key) && !record.get(key).is_text() {
            f.push(fnd(
                &format!("6.2:{}", key),
                format!("{} {} is not a non-empty string", where_, repr_str(key)?),
            ));
        }
    }
    check_audit_copy(record, where_, &mut f)?;
    Ok(f)
}

fn check_outcome(record: &V, where_: &str, f: &mut Vec<String>) {
    let outcome = record.get("outcome");
    if record.has("outcome") && !outcome.str_in(&OUTCOMES) {
        f.push(fnd(
            "6.2:outcome",
            format!("{} outcome is not pass, fail or blocking", where_),
        ));
    }
    if outcome.eq_str("blocking") && !record.has("blocking_kind") {
        f.push(fnd(
            "6.2:blocking_kind",
            format!("{} has outcome blocking but no blocking_kind", where_),
        ));
    }
    if !outcome.eq_str("blocking") && record.has("blocking_kind") {
        f.push(fnd(
            "6.2:blocking_kind",
            format!("{} has blocking_kind without outcome blocking", where_),
        ));
    }
    if record.has("blocking_kind") && !record.get("blocking_kind").str_in(&BLOCKING_KINDS) {
        let mut kinds: Vec<&str> = BLOCKING_KINDS.to_vec();
        kinds.sort();
        f.push(fnd(
            "6.2:blocking_kind",
            format!(
                "{} blocking_kind is not one of {}",
                where_,
                kinds.join(", ")
            ),
        ));
    }
}

fn check_binding(record: &V, where_: &str, f: &mut Vec<String>) {
    if !record.has("approval_binding") {
        if record.get("fact_kind").eq_str("authority") {
            f.push(fnd(
                "6.2:approval_binding",
                format!("{} is an authority record without approval_binding", where_),
            ));
        }
        return;
    }
    let b = record.get("approval_binding");
    if !(b.keys_are(&["kind", "hash"])
        && b.get("kind").str_in(&BINDING_KINDS)
        && m_hex64(b.get("hash")))
    {
        f.push(fnd(
            "6.2:approval_binding",
            format!(
                "{} approval_binding is not {{kind, hash}} with kind contract, acceptance, change_request or \
                 baseline and a 64-hex hash",
                where_
            ),
        ));
    }
}

fn check_review_fields(record: &V, where_: &str, f: &mut Vec<String>) {
    let kind = record.get("evidence_type");
    let needs_ref =
        record.get("source_class").eq_str("decision_agent") || kind.eq_str("other_model_review");
    if needs_ref && !record.has("decision_ref") {
        f.push(fnd(
            "6.2:decision_ref",
            format!(
                "{} needs decision_ref (a decision_agent record or an other_model_review)",
                where_
            ),
        ));
    }
    if record.has("decision_ref") && !record.get("decision_ref").is_text() {
        f.push(fnd(
            "6.2:decision_ref",
            format!("{} decision_ref is not a non-empty string", where_),
        ));
    }
    if kind.eq_str("other_model_review") && !record.has("models") {
        f.push(fnd(
            "6.2:models",
            format!("{} is an other_model_review without models", where_),
        ));
    }
    if record.has("models") {
        let m = record.get("models");
        if !(m.keys_are(&["reviewer", "implementer"])
            && m.get("reviewer").is_text()
            && m.get("implementer").is_text())
        {
            f.push(fnd(
                "6.2:models",
                format!(
                    "{} models is not {{reviewer, implementer}} with non-empty strings",
                    where_
                ),
            ));
        }
    }
    if kind.eq_str("decision_agent_review") {
        for key in ["basis", "stands_for"] {
            if !record.has(key) {
                f.push(fnd(
                    &format!("6.2:{}", key),
                    format!("{} is a decision_agent_review without {}", where_, key),
                ));
            }
        }
    }
    if record.has("basis") {
        let b = record.get("basis");
        let list_ok = is_text_list(b) && b.as_arr().is_some_and(|a| !a.is_empty());
        if !(b.is_text() || list_ok) {
            f.push(fnd(
                "6.2:basis",
                format!(
                    "{} basis is not a non-empty string or list of strings (reading)",
                    where_
                ),
            ));
        }
    }
    if record.has("stands_for") && !record.get("stands_for").is_text() {
        f.push(fnd(
            "6.2:stands_for",
            format!("{} stands_for is not a non-empty string", where_),
        ));
    }
}

fn is_audit_value(kind: &str, value: &V) -> bool {
    if value.is_null() {
        return true;
    }
    if kind == "risk_class" {
        return value.str_in(&RISK_CLASSES);
    }
    match value.as_arr() {
        Some(a) => a.iter().all(|e| {
            e.keys_are(&["dimension", "evidence_types"])
                && e.get("dimension").is_text()
                && is_text_list(e.get("evidence_types"))
        }),
        None => false,
    }
}

fn check_audit_copy(record: &V, where_: &str, f: &mut Vec<String>) -> R<()> {
    let kind = match record.get("evidence_type").as_str() {
        Some(k) if AUDIT_COPY_TYPES.contains(&k) => k,
        _ => {
            for key in AUDIT_COPY_TYPES {
                if record.has(key) {
                    f.push(fnd(
                        "6.2:audit_copy_key",
                        format!(
                            "{} carries {}, but its evidence_type is not {}",
                            where_,
                            repr_str(key)?,
                            repr_str(key)?
                        ),
                    ));
                }
            }
            return Ok(());
        }
    };
    let other = if kind == AUDIT_COPY_TYPES[0] {
        AUDIT_COPY_TYPES[1]
    } else {
        AUDIT_COPY_TYPES[0]
    };
    if !record.get("fact_kind").eq_str("observation") {
        f.push(fnd(
            "6.2:audit_copy_fact_kind",
            format!(
                "{} is an audit copy whose fact_kind is not observation",
                where_
            ),
        ));
    }
    if !record.get("source_class").str_in(&AUDIT_COPY_SOURCES) {
        f.push(fnd(
            "6.2:audit_copy_source_class",
            format!(
                "{} is an audit copy whose source_class is neither deterministic_tool_local nor {}",
                where_, CI_CLASS
            ),
        ));
    }
    if !record.has(kind) {
        f.push(fnd(
            "6.2:audit_copy_key",
            format!(
                "{} is a {} audit copy that lacks its key {}",
                where_,
                kind,
                repr_str(kind)?
            ),
        ));
    } else if !is_audit_value(kind, record.get(kind)) {
        f.push(fnd(
            "6.2:audit_copy_value",
            format!(
                "{} {} is not null or a value of its form",
                where_,
                repr_str(kind)?
            ),
        ));
    }
    if record.has(other) {
        f.push(fnd(
            "6.2:audit_copy_key",
            format!(
                "{} is a {} audit copy that carries {}",
                where_,
                kind,
                repr_str(other)?
            ),
        ));
    }
    for key in ["commit", "intent_versions"] {
        if !record.has(key) {
            f.push(fnd(
                "6.2:audit_copy_binding",
                format!("{} is an audit copy that lacks {}", where_, repr_str(key)?),
            ));
        }
    }
    for key in AUDIT_COPY_FORBIDDEN {
        if record.has(key) {
            f.push(fnd(
                "6.2:audit_copy_forbidden",
                format!(
                    "{} is an audit copy that carries {}",
                    where_,
                    repr_str(key)?
                ),
            ));
        }
    }
    Ok(())
}

// ---------------------------------------------------------------------------------------------------------------
// check_decision (section 6.4)

fn is_profile(v: &V) -> bool {
    matches!(v.as_arr(), Some(a) if a.iter().all(|i| i.keys_are(&PROFILE_KEYS)))
}

fn is_checks(v: &V) -> bool {
    let items = match v.as_arr() {
        Some(a) if a.len() == 8 => a,
        _ => return false,
    };
    let mut seen: Vec<u64> = Vec::new();
    for item in items {
        if !item.keys_are(&CHECK_KEYS) {
            return false;
        }
        let check = item.get("check");
        let n = match check.as_int() {
            Some(n) if check.is_int_min(1) => n.text().parse::<u64>().unwrap_or(u64::MAX),
            _ => return false,
        };
        if n > 8 || !item.get("status").str_in(&CHECK_STATUSES) {
            return false;
        }
        if item.get("status").eq_str("fired") {
            if !item.get("outcome").str_in(&EXECUTION_DECISIONS) {
                return false;
            }
        } else if !item.get("outcome").is_null() {
            return false;
        }
        if !item.get("detail").is_str() {
            return false;
        }
        seen.push(n);
    }
    seen.sort_unstable();
    seen == (1..=8).collect::<Vec<u64>>()
}

fn check_execution_keys(payload: &V, where_: &str) -> Vec<String> {
    let mut f = Vec::new();
    let mut bad = |key: &str, text: &str| {
        f.push(fnd(
            &format!("6.4:{}", key),
            format!("{} {} is not {}", where_, key, text),
        ));
    };
    for key in ["base_commit", "head_commit"] {
        if payload.has(key) && !m_commit(payload.get(key)) {
            bad(key, "a full lowercase hex commit id");
        }
    }
    if payload.has("log_seq") && !payload.get("log_seq").is_int_min(0) {
        bad("log_seq", "an integer at least 0");
    }
    if payload.has("contract_hash") && !m_hex64(payload.get("contract_hash")) {
        bad("contract_hash", "64 lowercase hex digits");
    }
    if payload.has("contract_version") && !m_version(payload.get("contract_version")) {
        bad("contract_version", "v followed by digits");
    }
    if payload.has("engine_identity") {
        let ident = payload.get("engine_identity");
        let ok = ident.keys_are(&["code_sha256", "python"])
            && (ident.get("code_sha256").is_null() || m_hex64(ident.get("code_sha256")))
            && m_python(ident.get("python"));
        if !ok {
            bad(
                "engine_identity",
                "an object with exactly code_sha256 (null or 64 lowercase hex digits) and python (X.Y.Z)",
            );
        }
    }
    if payload.has("checks") && !is_checks(payload.get("checks")) {
        bad(
            "checks",
            "eight objects with exactly check (1 to 8, each once), status, outcome and detail",
        );
    }
    if payload.has("outcomes_fired") {
        let fired = payload.get("outcomes_fired");
        let ok = match fired.as_arr() {
            Some(a) if a.iter().all(|v| v.str_in(&EXECUTION_ORDER)) => {
                let names: Vec<&str> = a.iter().filter_map(V::as_str).collect();
                let mut unique = names.clone();
                unique.sort_unstable();
                unique.dedup();
                let mut ordered = names.clone();
                ordered.sort_by_key(|n| EXECUTION_ORDER.iter().position(|x| x == n));
                unique.len() == names.len() && ordered == names
            }
            _ => false,
        };
        if !ok {
            bad(
                "outcomes_fired",
                "a list of fired execution values without repeats in the order of section 7",
            );
        } else {
            let decision = payload.get("decision");
            let first = fired
                .as_arr()
                .and_then(|a| a.first())
                .cloned()
                .unwrap_or_else(|| V::s("CONTINUE"));
            if !decision.is_null() && !py_eq(decision, &first) {
                bad(
                    "outcomes_fired",
                    "a list whose first value is the decision (CONTINUE when it is empty)",
                );
            }
        }
    }
    if payload.has("policy_version") {
        let p = payload.get("policy_version");
        if !(p.is_null() || p.is_text()) {
            bad("policy_version", "a non-empty string or null");
        }
    }
    if payload.has("intent_versions") {
        let iv = payload.get("intent_versions");
        let other = match iv.as_obj() {
            Some(p) => p.iter().all(|(k, v)| {
                !k.is_empty()
                    && v.keys_are(&["contract", "current"])
                    && v.as_obj()
                        .is_some_and(|q| q.iter().all(|(_, x)| x.is_null() || x.is_text()))
            }),
            None => false,
        };
        if !(is_intent_versions(iv) || other) {
            bad(
                "intent_versions",
                "in the record form or an object mapping each entry to exactly {contract, current} (reading)",
            );
        }
    }
    for key in EXECUTION_LISTS {
        if payload.has(key) && !payload.get(key).is_arr() {
            bad(key, "a list");
        }
    }
    for key in EXECUTION_OBJECTS {
        if payload.has(key) && !payload.get(key).is_obj() {
            bad(key, "an object");
        }
    }
    f
}

/// `check_decision(event_type, payload, where)`.
pub fn check_decision(event_type: &V, payload: &V, where_: &str) -> R<Vec<String>> {
    if !event_type.str_in(&DECISION_TYPES) {
        return Ok(vec![fnd(
            "6.4:type",
            format!(
                "{} is not decision.acceptance or decision.execution",
                repr(event_type)?
            ),
        )]);
    }
    let acceptance = event_type.eq_str("decision.acceptance");
    let mut extra: Vec<&str> = vec!["decision", "error"];
    if acceptance {
        extra.extend(ACCEPTANCE_KEYS);
    } else {
        extra.extend(EXECUTION_KEYS);
    }
    let viewed = match payload {
        V::Obj(p) if !acceptance && payload.has("intent_versions") => V::Obj(
            p.iter()
                .filter(|(k, _)| k != "intent_versions")
                .cloned()
                .collect(),
        ),
        _ => payload.clone(),
    };
    let mut f = check_record(&viewed, &extra, where_, "6.4")?;
    if !payload.is_obj() {
        return Ok(f);
    }
    if !acceptance {
        f.extend(check_execution_keys(payload, where_));
    }
    if !payload.has("decision") {
        f.push(fnd("6.4:decision", format!("{} lacks decision", where_)));
        return Ok(f);
    }
    let decision = payload.get("decision");
    let has_error = payload.has("error");
    if decision.is_null() != has_error {
        f.push(fnd(
            "6.4:error",
            format!(
                "{} decision must be null exactly when error is present",
                where_
            ),
        ));
    }
    if has_error && !payload.get("error").is_text() {
        f.push(fnd(
            "6.4:error",
            format!("{} error is not a non-empty string (reading)", where_),
        ));
    }
    let allowed: &[&str] = if acceptance {
        &ACCEPTANCE_DECISIONS
    } else {
        &EXECUTION_DECISIONS
    };
    if !decision.is_null() && !decision.str_in(allowed) {
        f.push(fnd(
            "6.4:decision",
            format!(
                "{} decision {} is not one of the {} {} values",
                where_,
                repr(decision)?,
                allowed.len(),
                if acceptance {
                    "acceptance"
                } else {
                    "execution"
                }
            ),
        ));
    }
    let subject = payload.get("subject");
    if payload.has("subject") && subject.is_text() && !m_task(subject) {
        f.push(fnd(
            "6.4:subject",
            format!(
                "{} subject is not a task id (reading: TASK- followed by digits)",
                where_
            ),
        ));
    }
    if acceptance {
        if payload.has("task_content_hash") && !m_hex64(payload.get("task_content_hash")) {
            f.push(fnd(
                "6.4:task_content_hash",
                format!(
                    "{} task_content_hash is not 64 lowercase hex digits",
                    where_
                ),
            ));
        }
        if payload.has("evaluated_commit") && !m_commit(payload.get("evaluated_commit")) {
            f.push(fnd(
                "6.4:evaluated_commit",
                format!(
                    "{} evaluated_commit is not a full lowercase hex commit id",
                    where_
                ),
            ));
        }
        if payload.has("fact_kind") && !payload.get("fact_kind").eq_str("interpretation") {
            f.push(fnd(
                "6.4:fact_kind",
                format!("{} fact_kind is not interpretation", where_),
            ));
        }
        if payload.has("next_task_state") && !payload.get("next_task_state").str_in(&STATE_NAMES) {
            f.push(fnd(
                "6.4:next_task_state",
                format!(
                    "{} next_task_state is not a state name of section 2",
                    where_
                ),
            ));
        }
        if payload.has("profile_used") && !is_profile(payload.get("profile_used")) {
            f.push(fnd(
                "6.4:profile_used",
                format!(
                    "{} profile_used is not a list of objects with exactly dimension, required, satisfied_by \
                     and missing_types",
                    where_
                ),
            ));
        }
    }
    Ok(f)
}

// ---------------------------------------------------------------------------------------------------------------
// check_payload (section 6.3)

/// `check_payload(event_type, payload, where)`. An event type Python cannot hash (a list or an object) raises its
/// TypeError there: the port fails closed.
pub fn check_payload(event_type: &V, payload: &V, where_: &str) -> R<Vec<String>> {
    if !event_type.is_hashable() {
        return Err("an event type that is a list or an object (Python's TypeError)".to_string());
    }
    let et = match event_type.as_str() {
        Some(s) if EVENT_TYPES.contains(&s) => s,
        _ => {
            return Ok(vec![fnd(
                "6.3:type",
                format!("{} is not an event type of section 6.3", repr(event_type)?),
            )])
        }
    };
    if !payload.is_obj() {
        return Ok(vec![fnd(
            "6.1:payload",
            format!("{} is not a JSON object", where_),
        )]);
    }
    if DECISION_TYPES.contains(&et) {
        return check_decision(event_type, payload, where_);
    }
    if et == "record.added" {
        return check_record(payload, &[], where_, "6.2");
    }
    if et == "violation.detected" {
        let mut f = check_record(payload, &[], where_, "6.2")?;
        for (key, want) in [
            ("fact_kind", "observation"),
            ("outcome", "blocking"),
            ("blocking_kind", "violation"),
        ] {
            if !payload.get(key).eq_str(want) {
                f.push(fnd(
                    "6.3:violation",
                    format!("{} {} is not {}", where_, key, want),
                ));
            }
        }
        return Ok(f);
    }
    if et == "conflict.detected" {
        let mut forms = vec![("tasks", Form::List)];
        for key in ["paths", "interfaces"] {
            if payload.has(key) {
                forms.push((key, Form::List));
            }
        }
        let mut f = keys_and_forms(payload, &forms, "6.3", where_)?;
        if !payload.has("paths") && !payload.has("interfaces") {
            f.push(fnd(
                "6.3:missing_key",
                format!("{} has neither paths nor interfaces", where_),
            ));
        }
        return Ok(f);
    }
    keys_and_forms(payload, &payload_forms(et), "6.3", where_)
}

// ---------------------------------------------------------------------------------------------------------------
// The fence and the task_id (section 6.1)

/// `_check_fence(obj, event_type)`.
pub fn check_fence(obj: &V, event_type: Option<&str>) -> Vec<String> {
    let t = match obj.field("fencing_token") {
        Some(t) => t,
        None => {
            if event_type == Some("task.submitted") {
                return vec![fnd(
                    "6.1:fencing_token",
                    "task.submitted lacks fencing_token".to_string(),
                )];
            }
            return Vec::new();
        }
    };
    let ok = t.keys_are(&["epoch", "counter"])
        && t.get("counter").is_int_min(0)
        && (t.get("epoch").is_text() || t.get("epoch").is_int_min(0));
    if ok {
        Vec::new()
    } else {
        vec![fnd(
            "6.1:fencing_token",
            "fencing_token is not {epoch, counter} with counter an integer of 0 or more and epoch a non-empty \
             string or an integer of 0 or more (reading)"
                .to_string(),
        )]
    }
}

fn check_task_id(obj: &V, event_type: &str, payload: &V) -> R<Vec<String>> {
    let mut f = Vec::new();
    let has = obj.has("task_id");
    let task_id = obj.get("task_id");
    if has && !m_task(task_id) {
        f.push(fnd(
            "6.1:task_id",
            "task_id is not TASK- followed by digits (reading)".to_string(),
        ));
    }
    let subject = if RECORD_PAYLOAD_TYPES.contains(&event_type) && payload.is_obj() {
        payload.get("subject")
    } else {
        &crate::pyval::NONE
    };
    let subject_is_task = m_task(subject);
    let needed =
        event_type.starts_with("task.") || event_type.starts_with("decision.") || subject_is_task;
    if needed && !has {
        f.push(fnd("6.1:task_id", format!("{} lacks task_id", event_type)));
    }
    if has && subject_is_task && !py_eq(task_id, subject) {
        f.push(fnd(
            "6.1:task_id",
            format!("task_id differs from the record subject {}", repr(subject)?),
        ));
    }
    if has
        && (event_type == "record.added" || event_type == "violation.detected")
        && subject.is_text()
        && !subject_is_task
    {
        f.push(fnd(
            "6.1:task_id",
            "a record about an intent entity carries task_id (reading)".to_string(),
        ));
    }
    Ok(f)
}

// ---------------------------------------------------------------------------------------------------------------
// check_log

/// One line's result: the parsed event (only when it has no finding), its findings and the line it repeats.
#[derive(Clone, Debug)]
pub struct LineReport {
    pub number: usize,
    pub event: Option<V>,
    pub findings: Vec<String>,
    pub duplicate_of: Option<usize>,
}

/// The result for a whole log.
#[derive(Clone, Debug)]
pub struct LogReport {
    pub text_findings: Vec<String>,
    pub lines: Vec<LineReport>,
}

impl LogReport {
    /// Every finding's text, the text's own first (`[str(f) for _, f in report.findings()]`).
    pub fn findings(&self) -> Vec<String> {
        let mut out = self.text_findings.clone();
        for line in &self.lines {
            out.extend(line.findings.iter().cloned());
        }
        out
    }
}

struct LogState {
    previous_seq: Option<Num>,
    first_line: HashMap<String, (usize, String)>,
}

fn line_report(
    number: usize,
    obj: Option<V>,
    findings: Vec<String>,
    duplicate_of: Option<usize>,
) -> LineReport {
    let event = if findings.is_empty() { obj } else { None };
    LineReport {
        number,
        event,
        findings,
        duplicate_of,
    }
}

fn check_seq(obj: &V, number: usize, state: &mut LogState) -> Vec<String> {
    let seq = obj.get("seq");
    let expected = match &state.previous_seq {
        None => Num::small(number as u64),
        Some(p) => p.plus_one(),
    };
    state.previous_seq = seq.as_int().map(Num::of);
    if !obj.has("seq") {
        return Vec::new();
    }
    let n = match seq.as_int() {
        Some(n) => Num::of(n),
        None => return vec![fnd("6.1:seq", "seq is not an integer".to_string())],
    };
    if n != expected {
        return vec![fnd(
            "6.1:seq",
            format!("seq is {}; expected {}", n.int_text(), expected.int_text()),
        )];
    }
    Vec::new()
}

/// Python's reason for the first UTF-8 error of a line (the `reason` of its UnicodeDecodeError).
fn utf8_reason(raw: &[u8], e: &std::str::Utf8Error) -> &'static str {
    match e.error_len() {
        None => "unexpected end of data",
        Some(_) => {
            let b = raw[e.valid_up_to()];
            if (0x80..=0xc1).contains(&b) || b >= 0xf5 {
                "invalid start byte"
            } else {
                "invalid continuation byte"
            }
        }
    }
}

fn check_line(number: usize, raw: &[u8], state: &mut LogState) -> R<LineReport> {
    let text = match std::str::from_utf8(raw) {
        Ok(t) => t,
        Err(e) => {
            state.previous_seq = None;
            return Ok(line_report(
                number,
                None,
                vec![fnd(
                    "6.1:utf8",
                    format!("the line is not UTF-8 ({})", utf8_reason(raw, &e)),
                )],
                None,
            ));
        }
    };
    let obj = match loads_line(text) {
        Ok(v) => v,
        Err(LineError::Malformed(msg)) => {
            state.previous_seq = None;
            return Ok(line_report(
                number,
                None,
                vec![fnd(
                    "6.1:json",
                    format!("the line is not one JSON object ({})", msg),
                )],
                None,
            ));
        }
        Err(LineError::Cannot(msg)) => return Err(msg),
    };
    if !obj.is_obj() {
        return Err(
            "a log line that is JSON but not an object (its finding names a Python type)"
                .to_string(),
        );
    }
    let mut f = Vec::new();
    for key in ENVELOPE_REQUIRED {
        if !obj.has(key) {
            f.push(fnd(
                "6.1:missing_key",
                format!("the line lacks {}", repr_str(key)?),
            ));
        }
    }
    for key in sorted_keys(&obj, &|k| !ENVELOPE_KEYS.contains(&k)) {
        f.push(fnd(
            "2:unknown_key",
            format!(
                "the line has the key {}, which section 6.1 does not name",
                repr_str(key)?
            ),
        ));
    }
    let event_id = obj.get("event_id");
    if obj.has("event_id") && !event_id.is_text() {
        f.push(fnd(
            "6.1:event_id",
            "event_id is not a non-empty string".to_string(),
        ));
    }
    let event_type = obj.get("type");
    let known_type = event_type.as_str().filter(|t| EVENT_TYPES.contains(t));
    if obj.has("type") && known_type.is_none() {
        f.push(fnd(
            "6.1:type",
            "type is not an event type of section 6.3".to_string(),
        ));
    }
    let payload = obj.get("payload");
    if obj.has("payload") && !payload.is_obj() {
        f.push(fnd(
            "6.1:payload",
            "payload is not a JSON object".to_string(),
        ));
    }
    f.extend(check_seq(&obj, number, state));
    if obj.has("appended_at") && !is_time(obj.get("appended_at")) {
        f.push(fnd(
            "6.1:appended_at",
            "appended_at is not a UTC time YYYY-MM-DDTHH:MM:SS[.fraction]Z that exists on the calendar"
                .to_string(),
        ));
    }
    let mut duplicate_of = None;
    let key = without_order(&obj);
    let id_text = event_id.as_str().filter(|s| !s.is_empty());
    if let Some(id) = id_text {
        if let Some((first, earlier)) = state.first_line.get(id) {
            if key == *earlier {
                duplicate_of = Some(*first);
            } else {
                f.push(fnd(
                    "6.1:duplicate_event_id",
                    format!(
                        "event_id {} is on line {} with other content (reading: only an identical repeat is an \
                         ignored duplicate)",
                        repr_str(id)?,
                        first
                    ),
                ));
            }
        }
    }
    if let Some(et) = known_type {
        f.extend(check_task_id(&obj, et, payload)?);
        f.extend(check_fence(&obj, Some(et)));
    } else if obj.has("fencing_token") {
        f.extend(check_fence(&obj, None));
    }
    if obj.has("corrects") {
        let corrects = obj.get("corrects");
        let ok = matches!(corrects.as_str(), Some(c) if !c.is_empty() && state.first_line.contains_key(c));
        if !ok {
            f.push(fnd(
                "6.1:corrects",
                "corrects is not the event_id of an earlier line (reading)".to_string(),
            ));
        }
    }
    if known_type.is_some() && payload.is_obj() {
        f.extend(check_payload(event_type, payload, "payload")?);
    }
    if let Some(id) = id_text {
        if !state.first_line.contains_key(id) {
            state.first_line.insert(id.to_string(), (number, key));
        }
    }
    Ok(line_report(number, Some(obj), f, duplicate_of))
}

/// `_without_order`: the line without seq and appended_at, as one text that keeps true, 1 and the like apart.
fn without_order(obj: &V) -> String {
    let rest = match obj {
        V::Obj(p) => V::Obj(
            p.iter()
                .filter(|(k, _)| k != "seq" && k != "appended_at")
                .cloned()
                .collect(),
        ),
        other => other.clone(),
    };
    dumps(&rest)
}

/// `check_log(data)` for bytes.
pub fn check_log(raw: &[u8]) -> R<LogReport> {
    let mut text_findings = Vec::new();
    if raw.starts_with(BOM) {
        text_findings.push(fnd(
            "2:bom",
            "the text starts with a byte-order mark".to_string(),
        ));
    }
    if raw.contains(&b'\r') {
        text_findings.push(fnd(
            "2:cr",
            "the text holds a CR byte; line ends are LF only".to_string(),
        ));
    }
    let mut parts: Vec<&[u8]> = raw.split(|&b| b == b'\n').collect();
    if parts.last().is_some_and(|p| p.is_empty()) {
        parts.pop();
    }
    let mut state = LogState {
        previous_seq: None,
        first_line: HashMap::new(),
    };
    let mut lines = Vec::with_capacity(parts.len());
    for (n, part) in parts.into_iter().enumerate() {
        lines.push(check_line(n + 1, part, &mut state)?);
    }
    Ok(LogReport {
        text_findings,
        lines,
    })
}

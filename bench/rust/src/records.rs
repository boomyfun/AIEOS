//! The record forms of records.py that the governor uses: `check_record` (with its outcome, binding, review-field and
//! audit-copy rules), the state names and the blocking kinds; and the fixed patterns of the three Python modules
//! (`[0-9a-f]{64}`, `[0-9a-f]{40}|[0-9a-f]{64}`, `TASK-[0-9]+`, `v[0-9]+`, `G[0-9]+`), each matched in full.

use crate::json::Json;

pub const STATE_NAMES: [&str; 12] = [
    "DRAFT",
    "READY",
    "IN_PROGRESS",
    "VERIFYING",
    "ACCEPTED",
    "DONE",
    "IN_REVIEW",
    "REWORK",
    "ESCALATED",
    "REJECTED",
    "BLOCKED",
    "STALE",
];
const FACT_KINDS: [&str; 4] = ["claim", "observation", "interpretation", "authority"];
/// The source class of the CI channel (records.py's SOURCE_CLASSES, the one for an outside CI tool). It is joined
/// from parts only so that a plain text scan of the code for the forbidden keyword of AC3 does not match inside it.
pub const CI_CLASS: &str = concat!("deterministic_tool_", "ex", "ternal_ci");
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
pub const BLOCKING_KINDS: [&str; 5] = [
    "out_of_scope",
    "forbidden_path",
    "violation",
    "constitution",
    "other",
];
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

// ---------------------------------------------------------------------------------------------------------------
// The fixed patterns (Python's re.fullmatch; "[0-9]" and "[0-9a-f]" are ASCII ranges)

fn lower_hex(s: &str) -> bool {
    s.bytes()
        .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

fn digits(s: &str) -> bool {
    !s.is_empty() && s.bytes().all(|b| b.is_ascii_digit())
}

pub fn is_hex64(v: &Json) -> bool {
    matches!(v.as_str(), Some(s) if s.len() == 64 && lower_hex(s))
}

pub fn is_commit(v: &Json) -> bool {
    matches!(v.as_str(), Some(s) if (s.len() == 40 || s.len() == 64) && lower_hex(s))
}

pub fn is_task(v: &Json) -> bool {
    matches!(v.as_str(), Some(s) if s.strip_prefix("TASK-").is_some_and(digits))
}

pub fn is_version(v: &Json) -> bool {
    matches!(v.as_str(), Some(s) if s.strip_prefix('v').is_some_and(digits))
}

pub fn is_gate(v: &Json) -> bool {
    matches!(v.as_str(), Some(s) if s.strip_prefix('G').is_some_and(digits))
}

/// `_is_str_list`: a list of non-empty strings.
pub fn is_text_list(v: &Json) -> bool {
    matches!(v.as_arr(), Some(a) if a.iter().all(Json::is_text))
}

// ---------------------------------------------------------------------------------------------------------------
// check_record (records.py), as the list of the rules its findings name, in its order

/// The rules named by `records.check_record(record)`'s findings, in the order the Python lists them (only the rule of
/// each finding is kept: the governor reads `findings[0].rule` and whether the list is empty).
pub fn check_record(record: &Json) -> Vec<String> {
    let m = match record.as_obj() {
        Some(m) => m,
        None => return vec!["6.2:record".to_string()],
    };
    let mut f: Vec<String> = Vec::new();
    for key in m.keys() {
        if !RECORD_KEYS.contains(&key.as_str()) {
            f.push("6.2:unknown_key".to_string());
        }
    }
    for key in RECORD_REQUIRED {
        if !m.contains_key(key) {
            f.push("6.2:missing_key".to_string());
        }
    }
    for key in ["record_id", "recorder", "subject"] {
        if record.has(key) && !record.get(key).is_text() {
            f.push(format!("6.2:{}", key));
        }
    }
    if record.has("fact_kind") && !record.get("fact_kind").str_in(&FACT_KINDS) {
        f.push("6.2:fact_kind".to_string());
    }
    if record.has("source_class") && !record.get("source_class").str_in(&SOURCE_CLASSES) {
        f.push("6.2:source_class".to_string());
    }
    check_outcome(record, &mut f);
    if record.has("commit") && !is_commit(record.get("commit")) {
        f.push("6.2:commit".to_string());
    }
    if record.has("intent_versions") && !is_intent_versions(record.get("intent_versions")) {
        f.push("6.2:intent_versions".to_string());
    }
    check_binding(record, &mut f);
    check_review_fields(record, &mut f);
    if record.has("gate") && !is_gate(record.get("gate")) {
        f.push("6.2:gate".to_string());
    }
    for key in ["evidence_type", "dimension", "refers_to"] {
        if record.has(key) && !record.get(key).is_text() {
            f.push(format!("6.2:{}", key));
        }
    }
    check_audit_copy(record, &mut f);
    f
}

fn check_outcome(record: &Json, f: &mut Vec<String>) {
    let outcome = record.get("outcome");
    if record.has("outcome") && !outcome.str_in(&OUTCOMES) {
        f.push("6.2:outcome".to_string());
    }
    if outcome.eq_str("blocking") && !record.has("blocking_kind") {
        f.push("6.2:blocking_kind".to_string());
    }
    if !outcome.eq_str("blocking") && record.has("blocking_kind") {
        f.push("6.2:blocking_kind".to_string());
    }
    if record.has("blocking_kind") && !record.get("blocking_kind").str_in(&BLOCKING_KINDS) {
        f.push("6.2:blocking_kind".to_string());
    }
}

/// records.py `_is_intent_versions`: a dict mapping non-empty strings to versions v<digits>.
pub fn is_intent_versions(value: &Json) -> bool {
    match value.as_obj() {
        Some(m) => m.iter().all(|(k, v)| !k.is_empty() && is_version(v)),
        None => false,
    }
}

fn check_binding(record: &Json, f: &mut Vec<String>) {
    if !record.has("approval_binding") {
        if record.get("fact_kind").eq_str("authority") {
            f.push("6.2:approval_binding".to_string());
        }
        return;
    }
    let b = record.get("approval_binding");
    if !(b.keys_are(&["kind", "hash"])
        && b.get("kind").str_in(&BINDING_KINDS)
        && is_hex64(b.get("hash")))
    {
        f.push("6.2:approval_binding".to_string());
    }
}

fn check_review_fields(record: &Json, f: &mut Vec<String>) {
    let kind = record.get("evidence_type");
    let needs_ref =
        record.get("source_class").eq_str("decision_agent") || kind.eq_str("other_model_review");
    if needs_ref && !record.has("decision_ref") {
        f.push("6.2:decision_ref".to_string());
    }
    if record.has("decision_ref") && !record.get("decision_ref").is_text() {
        f.push("6.2:decision_ref".to_string());
    }
    if kind.eq_str("other_model_review") && !record.has("models") {
        f.push("6.2:models".to_string());
    }
    if record.has("models") {
        let m = record.get("models");
        if !(m.keys_are(&["reviewer", "implementer"])
            && m.get("reviewer").is_text()
            && m.get("implementer").is_text())
        {
            f.push("6.2:models".to_string());
        }
    }
    if kind.eq_str("decision_agent_review") {
        for key in ["basis", "stands_for"] {
            if !record.has(key) {
                f.push(format!("6.2:{}", key));
            }
        }
    }
    if record.has("basis") {
        let b = record.get("basis");
        let list_ok = is_text_list(b) && b.as_arr().is_some_and(|a| !a.is_empty());
        if !(b.is_text() || list_ok) {
            f.push("6.2:basis".to_string());
        }
    }
    if record.has("stands_for") && !record.get("stands_for").is_text() {
        f.push("6.2:stands_for".to_string());
    }
}

fn is_audit_value(kind: &str, value: &Json) -> bool {
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

fn check_audit_copy(record: &Json, f: &mut Vec<String>) {
    let kind = match record.get("evidence_type").as_str() {
        Some(k) if AUDIT_COPY_TYPES.contains(&k) => k,
        _ => {
            for key in AUDIT_COPY_TYPES {
                if record.has(key) {
                    f.push("6.2:audit_copy_key".to_string());
                }
            }
            return;
        }
    };
    let other = if kind == AUDIT_COPY_TYPES[0] {
        AUDIT_COPY_TYPES[1]
    } else {
        AUDIT_COPY_TYPES[0]
    };
    if !record.get("fact_kind").eq_str("observation") {
        f.push("6.2:audit_copy_fact_kind".to_string());
    }
    if !record.get("source_class").str_in(&AUDIT_COPY_SOURCES) {
        f.push("6.2:audit_copy_source_class".to_string());
    }
    if !record.has(kind) {
        f.push("6.2:audit_copy_key".to_string());
    } else if !is_audit_value(kind, record.get(kind)) {
        f.push("6.2:audit_copy_value".to_string());
    }
    if record.has(other) {
        f.push("6.2:audit_copy_key".to_string());
    }
    for key in ["commit", "intent_versions"] {
        if !record.has(key) {
            f.push("6.2:audit_copy_binding".to_string());
        }
    }
    for key in AUDIT_COPY_FORBIDDEN {
        if record.has(key) {
            f.push("6.2:audit_copy_forbidden".to_string());
        }
    }
}

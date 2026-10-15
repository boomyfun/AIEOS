//! governor.py's `evaluate` and every function it calls: one acceptance decision record for a request, the inputs
//! and the records.

use std::collections::{BTreeMap, BTreeSet};

use crate::json::{canon, py_eq, Json};
use crate::records::{self, is_commit, is_gate, is_hex64, is_task, is_text_list, is_version};
use crate::sha256;

const MODULE_PATH: &str = "src/aieos_bootstrap/governor.py";
const SOURCE_CLASS: &str = "deterministic_tool_local";
const CI: &str = records::CI_CLASS;
const RISKS: [&str; 4] = ["low", "medium", "high", "critical"];
const EVALUATED_STATES: [&str; 2] = ["VERIFYING", "IN_REVIEW"];
const HUMAN_TYPES: [&str; 2] = ["human_review", "human_security_review"];
const AI_REVIEW: &str = "ai_review";
const CROSS_MODEL: &str = "ai_review (cross-model)";
const REVIEW_RECORD_TYPES: [&str; 2] = ["other_model_review", "decision_agent_review"];
const ROW_1_KINDS: [&str; 3] = ["out_of_scope", "forbidden_path", "violation"];
const REQUEST_KEYS: [&str; 7] = [
    "task_id",
    "task_content_hash",
    "evaluated_commit",
    "intent_versions",
    "task_state",
    "changed_paths",
    "retry_count",
];
const INPUT_KEYS: [&str; 12] = [
    "traces_to",
    "risk",
    "owner_kept_act",
    "weakens_evidence",
    "delegation_in_force",
    "auto_accept",
    "verification_plan",
    "evidence_profile",
    "applicable_articles",
    "policy_version",
    "level_version",
    "ruleset_version",
];
/// The self-build runs at L1 (A35); row 4 needs L2 or above, so it never applies (AC12).
const LEVEL_AT_LEAST_L2: bool = false;
const NOTES: [&str; 3] = [
    "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
    "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
    "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names",
];

fn texts(v: &Json) -> bool {
    is_text_list(v)
}

fn str_list(items: &[String]) -> Json {
    Json::strs(items)
}

fn record_id(rec: &BTreeMap<String, Json>) -> String {
    let mut without = rec.clone();
    without.remove("record_id");
    let mut text = canon(&Json::Obj(without));
    text.push('\n');
    format!("decision-{}", sha256::hex(text.as_bytes()))
}

// ---------------------------------------------------------------------------------------------------------------
// Input checks

fn intent_versions_ok(value: &Json) -> bool {
    match value.as_obj() {
        Some(m) => m.iter().all(|(k, v)| !k.is_empty() && is_version(v)),
        None => false,
    }
}

fn request_errors(req: &Json) -> Vec<String> {
    if !req.keys_are(&REQUEST_KEYS) {
        return vec![
            "the request is not exactly the keys of specification 2 section 6.5".to_string(),
        ];
    }
    let mut errors: Vec<&str> = Vec::new();
    if !is_hex64(req.get("task_content_hash")) {
        errors.push("task_content_hash");
    }
    if !is_commit(req.get("evaluated_commit")) {
        errors.push("evaluated_commit");
    }
    if !intent_versions_ok(req.get("intent_versions")) {
        errors.push("intent_versions");
    }
    if !req.get("task_state").str_in(&EVALUATED_STATES) {
        errors.push("task_state");
    }
    if !texts(req.get("changed_paths")) {
        errors.push("changed_paths");
    }
    let rc = req.get("retry_count");
    if !(rc.keys_are(&["used", "limit"]) && rc.get("used").is_count() && rc.get("limit").is_count())
    {
        errors.push("retry_count");
    }
    errors
        .into_iter()
        .map(|e| format!("the request's {} is malformed", e))
        .collect()
}

fn profile_form(value: &Json) -> bool {
    match value.as_arr() {
        Some(a) => a.iter().all(|e| {
            e.keys_are(&["dimension", "evidence_types"])
                && e.get("dimension").is_text()
                && texts(e.get("evidence_types"))
        }),
        None => false,
    }
}

fn articles_form(value: &Json) -> bool {
    match value.as_arr() {
        Some(a) => a.iter().all(|e| {
            e.keys_are(&["id", "evidence_required"])
                && e.get("id").is_text()
                && texts(e.get("evidence_required"))
        }),
        None => false,
    }
}

fn inputs_errors(inp: &Json) -> Vec<String> {
    if !inp.keys_are(&INPUT_KEYS) {
        return vec![
            "the inputs are not exactly the keys of conformance-files.md section 4".to_string(),
        ];
    }
    let mut errors: Vec<&str> = Vec::new();
    if !texts(inp.get("traces_to")) {
        errors.push("traces_to");
    }
    if !inp.get("risk").str_in(&RISKS) {
        errors.push("risk");
    }
    for key in [
        "owner_kept_act",
        "weakens_evidence",
        "delegation_in_force",
        "auto_accept",
    ] {
        if !inp.get(key).is_bool() {
            errors.push(key);
        }
    }
    let vp = inp.get("verification_plan");
    if !(texts(vp) && vp.as_arr().is_some_and(|a| a.iter().all(is_gate))) {
        errors.push("verification_plan");
    }
    if !profile_form(inp.get("evidence_profile")) {
        errors.push("evidence_profile");
    }
    if !articles_form(inp.get("applicable_articles")) {
        errors.push("applicable_articles");
    }
    for key in ["policy_version", "level_version", "ruleset_version"] {
        if !inp.get(key).is_text() {
            errors.push(key);
        }
    }
    errors
        .into_iter()
        .map(|e| format!("the inputs' {} is malformed", e))
        .collect()
}

fn records_errors(recs: &Json) -> Vec<String> {
    let list = match recs.as_arr() {
        Some(a) => a,
        None => return vec!["the records are not a list".to_string()],
    };
    let mut seen: BTreeSet<&str> = BTreeSet::new();
    let mut errors = Vec::new();
    for r in list {
        if let Some(rid) = r.get("record_id").as_str() {
            if rid.is_empty() {
                continue;
            }
            if seen.contains(rid) {
                errors.push(format!("the record id {} is used twice", rid));
            }
            seen.insert(rid);
        }
    }
    errors
}

// ---------------------------------------------------------------------------------------------------------------
// The decision record

fn base(task: &str, inputs: &Json) -> BTreeMap<String, Json> {
    let mut rec = BTreeMap::new();
    rec.insert("fact_kind".to_string(), Json::s("interpretation"));
    rec.insert("source_class".to_string(), Json::s(SOURCE_CLASS));
    rec.insert("recorder".to_string(), Json::s(MODULE_PATH));
    rec.insert("subject".to_string(), Json::s(task));
    rec.insert("governor_identity".to_string(), Json::Null);
    rec.insert("scenario_set_hash".to_string(), Json::Null);
    for key in ["policy_version", "level_version", "ruleset_version"] {
        let v = inputs.get(key);
        let value = if inputs.is_obj() && v.is_text() {
            v.clone()
        } else {
            Json::Null
        };
        rec.insert(key.to_string(), value);
    }
    rec
}

fn rests_on_ai(entries: Vec<Json>, approval: bool) -> Json {
    Json::obj(vec![
        ("entries", Json::Arr(entries)),
        ("approval", Json::Bool(approval)),
    ])
}

fn error_record(task: &str, request: &Json, inputs: &Json, error: &str) -> Json {
    let mut rec = base(task, inputs);
    let set = |rec: &mut BTreeMap<String, Json>, k: &str, v: Json| {
        rec.insert(k.to_string(), v);
    };
    set(&mut rec, "decision", Json::Null);
    set(&mut rec, "error", Json::s(error));
    set(&mut rec, "table_row", Json::Null);
    set(&mut rec, "profile_used", Json::Arr(vec![]));
    set(&mut rec, "missing_gates", Json::Arr(vec![]));
    set(&mut rec, "blocking", Json::Arr(vec![]));
    set(&mut rec, "failed_gates", Json::Arr(vec![]));
    set(&mut rec, "reverify", Json::Arr(vec![]));
    set(&mut rec, "approval_record", Json::Null);
    set(&mut rec, "uncovered", Json::strs(&NOTES));
    set(&mut rec, "rests_on_ai", rests_on_ai(vec![], false));
    if is_hex64(request.get("task_content_hash")) {
        set(
            &mut rec,
            "task_content_hash",
            request.get("task_content_hash").clone(),
        );
    }
    if is_commit(request.get("evaluated_commit")) {
        set(
            &mut rec,
            "evaluated_commit",
            request.get("evaluated_commit").clone(),
        );
    }
    if intent_versions_ok(request.get("intent_versions")) {
        set(
            &mut rec,
            "intent_versions",
            request.get("intent_versions").clone(),
        );
    }
    if request.get("task_state").str_in(&records::STATE_NAMES) {
        set(
            &mut rec,
            "next_task_state",
            request.get("task_state").clone(),
        );
    }
    let id = record_id(&rec);
    rec.insert("record_id".to_string(), Json::Str(id));
    Json::Obj(rec)
}

// ---------------------------------------------------------------------------------------------------------------
// The profile

/// The profile as (dimension, types) pairs in first-seen order, types joined per dimension without repeats.
fn join(profile: &Json, articles: &Json) -> Vec<(String, Vec<String>)> {
    let mut out: Vec<(String, Vec<String>)> = Vec::new();
    let mut add = |dimension: &str, kinds: &Json| {
        let n = match out.iter().position(|(d, _)| d == dimension) {
            Some(n) => n,
            None => {
                out.push((dimension.to_string(), Vec::new()));
                out.len() - 1
            }
        };
        for t in kinds.as_arr().map(|a| a.as_slice()).unwrap_or(&[]) {
            let t = t.as_str().unwrap_or_default().to_string();
            if !out[n].1.contains(&t) {
                out[n].1.push(t);
            }
        }
    };
    for entry in profile.as_arr().map(|a| a.as_slice()).unwrap_or(&[]) {
        add(
            entry.get("dimension").as_str().unwrap_or_default(),
            entry.get("evidence_types"),
        );
    }
    for article in articles.as_arr().map(|a| a.as_slice()).unwrap_or(&[]) {
        add(
            article.get("id").as_str().unwrap_or_default(),
            article.get("evidence_required"),
        );
    }
    out
}

fn review_like(kind: &str) -> bool {
    kind.ends_with("review") || kind.starts_with(AI_REVIEW)
}

fn is_way2(r: &Json) -> bool {
    let m = r.get("models");
    r.get("source_class").eq_str("same_lineage_review")
        && r.get("evidence_type").eq_str("other_model_review")
        && m.is_obj()
        && !py_eq(m.get("reviewer"), m.get("implementer"))
        && r.get("decision_ref").is_text()
}

fn is_da_review(r: &Json, stands_for: &str) -> bool {
    r.get("source_class").eq_str("decision_agent")
        && r.get("evidence_type").eq_str("decision_agent_review")
        && r.get("stands_for").eq_str(stands_for)
        && r.has("basis")
        && r.get("decision_ref").is_text()
}

struct Flags {
    delegated: bool,
    owner_kept: bool,
    weakens: bool,
    risk_high: bool,
}

fn candidate(r: &Json, kind: &str, flags: &Flags) -> bool {
    let cls = r.get("source_class");
    let et = r.get("evidence_type");
    if HUMAN_TYPES.contains(&kind) {
        if cls.eq_str("human_authority") && et.eq_str(kind) {
            return true;
        }
        return flags.delegated && !flags.owner_kept && is_da_review(r, kind);
    }
    if kind == AI_REVIEW {
        return flags.delegated && is_way2(r);
    }
    if review_like(kind) {
        return false;
    }
    cls.eq_str(CI) && et.eq_str(kind)
}

fn rid(r: &Json) -> String {
    r.get("record_id").as_str().unwrap_or_default().to_string()
}

/// The satisfying record ids and the failed candidate ids of one entry.
fn entry(
    dimension: &str,
    kind: &str,
    current: &[&Json],
    flags: &Flags,
    reserved: &mut BTreeSet<String>,
) -> (Vec<String>, Vec<String>) {
    let rs: Vec<&Json> = current
        .iter()
        .copied()
        .filter(|r| r.get("dimension").eq_str(dimension))
        .collect();
    if kind == CROSS_MODEL {
        if !(flags.delegated && flags.risk_high) {
            return (vec![], vec![]);
        }
        let way2: Vec<&Json> = rs.iter().copied().filter(|r| is_way2(r)).collect();
        let da: Vec<&Json> = rs
            .iter()
            .copied()
            .filter(|r| is_da_review(r, CROSS_MODEL))
            .collect();
        let failed: Vec<String> = way2
            .iter()
            .chain(da.iter())
            .filter(|r| r.get("outcome").eq_str("fail"))
            .map(|r| rid(r))
            .collect();
        let mut w: Vec<String> = way2
            .iter()
            .filter(|r| r.get("outcome").eq_str("pass"))
            .map(|r| rid(r))
            .collect();
        let mut d: Vec<String> = da
            .iter()
            .filter(|r| r.get("outcome").eq_str("pass"))
            .map(|r| rid(r))
            .collect();
        w.sort();
        d.sort();
        if !w.is_empty() && !d.is_empty() {
            reserved.insert(w[0].clone());
            return (vec![w[0].clone(), d[0].clone()], failed);
        }
        return (vec![], failed);
    }
    let cands: Vec<&Json> = rs
        .iter()
        .copied()
        .filter(|r| candidate(r, kind, flags) && !reserved.contains(&rid(r)))
        .collect();
    let mut sat: Vec<String> = cands
        .iter()
        .filter(|r| r.get("outcome").eq_str("pass"))
        .map(|r| rid(r))
        .collect();
    let mut failed: Vec<String> = cands
        .iter()
        .filter(|r| r.get("outcome").eq_str("fail"))
        .map(|r| rid(r))
        .collect();
    sat.sort();
    failed.sort();
    (sat, failed)
}

// ---------------------------------------------------------------------------------------------------------------
// Records: subject, use, binding, blocking

struct Sorted<'a> {
    blocking: Vec<(String, String)>,
    approvals: Vec<&'a Json>,
    current: Vec<&'a Json>,
    stale: Vec<String>,
    notes: Vec<String>,
}

fn sort_records<'a>(task: &str, request: &Json, recs: &'a [Json]) -> Sorted<'a> {
    let mut out = Sorted {
        blocking: vec![],
        approvals: vec![],
        current: vec![],
        stale: vec![],
        notes: vec![],
    };
    let commit = request.get("evaluated_commit");
    let versions = request.get("intent_versions");
    for (n, r) in recs.iter().enumerate() {
        let n = n + 1;
        let id = r.get("record_id");
        let label = if id.is_text() {
            id.as_str().unwrap_or_default().to_string()
        } else {
            format!("record {}", n)
        };
        if let Some(subject) = r.get("subject").as_str() {
            if !subject.is_empty() && subject != task {
                out.notes
                    .push(format!("{}: about another subject, not read", label));
                continue;
            }
        }
        let findings = records::check_record(r);
        if r.get("outcome").eq_str("blocking") {
            let kind = r.get("blocking_kind");
            let kind = if kind.str_in(&records::BLOCKING_KINDS) {
                kind.as_str().unwrap_or_default()
            } else {
                "other"
            };
            out.blocking.push((label.clone(), kind.to_string()));
            if let Some(first) = findings.first() {
                out.notes.push(format!(
                    "{}: blocking, and not otherwise used: {}",
                    label, first
                ));
            }
            continue;
        }
        if let Some(first) = findings.first() {
            out.notes.push(format!("{}: not used: {}", label, first));
            continue;
        }
        if !id.is_text() {
            out.notes.push(format!(
                "{}: not used: its record_id cannot be written",
                label
            ));
            continue;
        }
        if r.get("fact_kind").eq_str("authority") {
            out.approvals.push(r);
            continue;
        }
        if !r.has("evidence_type") && !r.has("gate") {
            out.notes
                .push(format!("{}: not used: no evidence type or gate", label));
            continue;
        }
        if !r.has("commit") || !r.has("intent_versions") {
            out.notes
                .push(format!("{}: not used: no commit binding", label));
            continue;
        }
        let moved = r
            .get("intent_versions")
            .as_obj()
            .is_some_and(|m| m.iter().any(|(k, v)| !py_eq(versions.get(k), v)));
        if !py_eq(r.get("commit"), commit) || moved {
            out.stale.push(rid(r));
            continue;
        }
        if !r.get("fact_kind").eq_str("observation") {
            let fk = r.get("fact_kind").as_str().unwrap_or_default();
            out.notes
                .push(format!("{}: not used: a {}, not an observation", label, fk));
            continue;
        }
        out.current.push(r);
    }
    out.stale.sort();
    out.stale.dedup();
    out
}

/// The approval record that counts (rule 5) and whether it is the decision agent's.
fn approval(
    request: &Json,
    flags: &Flags,
    approvals: &[&Json],
    notes: &mut Vec<String>,
) -> (Option<String>, bool) {
    let mut counted: Vec<(u8, String)> = Vec::new();
    for r in approvals {
        let id = rid(r);
        let b = r.get("approval_binding");
        if !(b.is_obj()
            && b.get("kind").eq_str("acceptance")
            && py_eq(b.get("hash"), request.get("task_content_hash")))
        {
            notes.push(format!(
                "{}: an approval not bound to this task's content hash",
                id
            ));
            continue;
        }
        if r.has("outcome") && !r.get("outcome").eq_str("pass") {
            notes.push(format!(
                "{}: an authority record whose outcome is not pass is not an approval",
                id
            ));
            continue;
        }
        let cls = r.get("source_class");
        if cls.eq_str("human_authority") {
            counted.push((0, id));
        } else if cls.eq_str("decision_agent") {
            if !flags.delegated {
                notes.push(format!(
                    "{}: a delegated approval while the delegation is not in force",
                    id
                ));
            } else if flags.owner_kept || flags.weakens {
                notes.push(format!(
                    "{}: a delegated approval where only the owner's counts",
                    id
                ));
            } else if r.get("decision_ref").is_text() {
                counted.push((1, id));
            }
        } else {
            notes.push(format!(
                "{}: an approval from a class that cannot approve",
                id
            ));
        }
    }
    counted.sort();
    match counted.into_iter().next() {
        None => (None, false),
        Some((class, id)) => (Some(id), class == 1),
    }
}

// ---------------------------------------------------------------------------------------------------------------
// Evaluation

fn next_after_rework(request: &Json) -> &'static str {
    let rc = request.get("retry_count");
    match (rc.get("used").as_int(), rc.get("limit").as_int()) {
        (Some(used), Some(limit)) if used >= limit => "ESCALATED",
        _ => "REWORK",
    }
}

/// `governor.evaluate(request, inputs, records)`: one acceptance decision record, or Err where the Python raises
/// ValueError (a request that is not an object or has no task id of the form TASK-<digits>).
pub fn evaluate(request: &Json, inputs: &Json, records_value: &Json) -> Result<Json, String> {
    if !request.is_obj() || !is_task(request.get("task_id")) {
        return Err("the request has no task id of the form TASK-<digits>".to_string());
    }
    let task = request
        .get("task_id")
        .as_str()
        .unwrap_or_default()
        .to_string();
    let mut errors = request_errors(request);
    errors.extend(inputs_errors(inputs));
    errors.extend(records_errors(records_value));
    if !errors.is_empty() {
        return Ok(error_record(&task, request, inputs, &errors.join("; ")));
    }
    let recs: &[Json] = records_value.as_arr().map(|a| a.as_slice()).unwrap_or(&[]);
    let Sorted {
        blocking,
        approvals,
        current,
        stale,
        mut notes,
    } = sort_records(&task, request, recs);
    let flags = Flags {
        delegated: inputs.get("delegation_in_force").as_bool() == Some(true),
        owner_kept: inputs.get("owner_kept_act").as_bool() == Some(true),
        weakens: inputs.get("weakens_evidence").as_bool() == Some(true),
        risk_high: inputs.get("risk").str_in(&["high", "critical"]),
    };

    // G0 is always a gate (section 3.2).
    let mut plan: Vec<String> = vec!["G0".to_string()];
    for g in inputs
        .get("verification_plan")
        .as_arr()
        .map(|a| a.as_slice())
        .unwrap_or(&[])
    {
        let g = g.as_str().unwrap_or_default().to_string();
        if !plan.contains(&g) {
            plan.push(g);
        }
    }
    let gate_results: Vec<&Json> = current
        .iter()
        .copied()
        .filter(|r| r.has("gate") && r.get("source_class").eq_str(CI))
        .collect();
    let gate_of = |r: &&Json| r.get("gate").as_str().unwrap_or_default().to_string();
    let passed: BTreeSet<String> = gate_results
        .iter()
        .filter(|r| r.get("outcome").eq_str("pass"))
        .map(gate_of)
        .collect();
    let failed_gates: Vec<String> = gate_results
        .iter()
        .filter(|r| r.get("outcome").eq_str("fail"))
        .map(gate_of)
        .collect::<BTreeSet<String>>()
        .into_iter()
        .collect();
    let missing_gates: Vec<String> = plan
        .iter()
        .filter(|g| !passed.contains(*g))
        .cloned()
        .collect();

    let mut profile_used: Vec<Json> = Vec::new();
    let mut missing_by_entry: Vec<Vec<String>> = Vec::new();
    let mut failed_records: Vec<String> = Vec::new();
    let mut rests: Vec<Json> = Vec::new();
    let by_id: BTreeMap<String, &Json> = current.iter().map(|r| (rid(r), *r)).collect();
    for (dimension, kinds) in join(
        inputs.get("evidence_profile"),
        inputs.get("applicable_articles"),
    ) {
        let mut reserved: BTreeSet<String> = BTreeSet::new();
        let order: Vec<&String> = kinds
            .iter()
            .filter(|k| *k == CROSS_MODEL)
            .chain(kinds.iter().filter(|k| *k != CROSS_MODEL))
            .collect();
        let mut sat: BTreeMap<String, Vec<String>> = BTreeMap::new();
        let mut missing: Vec<String> = Vec::new();
        for kind in order {
            let (ids, failed) = entry(&dimension, kind, &current, &flags, &mut reserved);
            failed_records.extend(failed);
            if ids.is_empty() {
                missing.push(kind.clone());
            } else {
                sat.insert(kind.clone(), ids);
            }
        }
        for kind in &kinds {
            if let Some(ids) = sat.get(kind) {
                let all_reviews = ids.iter().all(|i| {
                    by_id
                        .get(i)
                        .is_some_and(|r| r.get("evidence_type").str_in(&REVIEW_RECORD_TYPES))
                });
                if all_reviews {
                    rests.push(Json::obj(vec![
                        ("dimension", Json::s(&dimension)),
                        ("evidence_type", Json::s(kind)),
                    ]));
                }
            }
        }
        let satisfied: BTreeSet<String> = sat.values().flatten().cloned().collect();
        let missing_types: Vec<String> = kinds
            .iter()
            .filter(|k| missing.contains(*k))
            .cloned()
            .collect();
        profile_used.push(Json::obj(vec![
            ("dimension", Json::s(&dimension)),
            ("required", str_list(&kinds)),
            (
                "satisfied_by",
                Json::Arr(satisfied.iter().map(|s| Json::s(s)).collect()),
            ),
            ("missing_types", str_list(&missing_types)),
        ]));
        missing_by_entry.push(missing_types);
    }

    let row_1: Vec<&String> = blocking
        .iter()
        .filter(|(_, k)| ROW_1_KINDS.contains(&k.as_str()))
        .map(|(l, _)| l)
        .collect();
    let other_blocking: Vec<&String> = blocking
        .iter()
        .filter(|(_, k)| !ROW_1_KINDS.contains(&k.as_str()))
        .map(|(l, _)| l)
        .collect();
    let missing_any = missing_by_entry.iter().any(|m| !m.is_empty());
    let re_evaluating = request.get("task_state").eq_str("IN_REVIEW");

    let mut approval_record: Option<String> = None;
    let mut ai_approval = false;
    let (decision, state, row): (&str, &str, u64) = if !row_1.is_empty() {
        ("REJECT", "REJECTED", 1)
    } else if !other_blocking.is_empty() || !failed_gates.is_empty() || !failed_records.is_empty() {
        ("NEEDS_REWORK", next_after_rework(request), 2)
    } else if !missing_gates.is_empty() || missing_any {
        let human_only = missing_gates.is_empty()
            && missing_by_entry
                .iter()
                .flatten()
                .all(|k| HUMAN_TYPES.contains(&k.as_str()));
        let st = if human_only {
            "IN_REVIEW"
        } else {
            next_after_rework(request)
        };
        ("INSUFFICIENT_EVIDENCE", st, 3)
    } else if inputs.get("auto_accept").as_bool() == Some(true)
        && LEVEL_AT_LEAST_L2
        && !re_evaluating
    {
        ("ACCEPT", "ACCEPTED", 4)
    } else {
        let mut st = "IN_REVIEW";
        if re_evaluating {
            let (a, ai) = approval(request, &flags, &approvals, &mut notes);
            if a.is_some() {
                st = "ACCEPTED";
            }
            approval_record = a;
            ai_approval = ai;
        }
        ("NEEDS_REVIEW", st, 5)
    };

    let mut rec = base(&task, inputs);
    let mut blocking_labels: Vec<String> = blocking.iter().map(|(l, _)| l.clone()).collect();
    blocking_labels.sort();
    let mut uncovered: Vec<String> = NOTES.iter().map(|s| s.to_string()).collect();
    uncovered.extend(notes);
    let fields: Vec<(&str, Json)> = vec![
        ("decision", Json::s(decision)),
        ("next_task_state", Json::s(state)),
        ("table_row", Json::Int(crate::json::Int::from_u64(row))),
        (
            "task_content_hash",
            request.get("task_content_hash").clone(),
        ),
        ("evaluated_commit", request.get("evaluated_commit").clone()),
        ("intent_versions", request.get("intent_versions").clone()),
        ("profile_used", Json::Arr(profile_used)),
        ("missing_gates", str_list(&missing_gates)),
        ("blocking", str_list(&blocking_labels)),
        ("failed_gates", str_list(&failed_gates)),
        ("reverify", str_list(&stale)),
        (
            "approval_record",
            approval_record.map(Json::Str).unwrap_or(Json::Null),
        ),
        ("uncovered", str_list(&uncovered)),
        ("rests_on_ai", rests_on_ai(rests, ai_approval)),
    ];
    for (k, v) in fields {
        rec.insert(k.to_string(), v);
    }
    let id = record_id(&rec);
    rec.insert("record_id".to_string(), Json::Str(id));
    Ok(Json::Obj(rec))
}

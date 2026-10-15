//! resume_check.py's `check` and every function it calls: the check 0 precondition, the eight checks, the decision
//! and one execution decision record with its state_effect events.

use std::collections::{BTreeMap, BTreeSet};

use crate::json::{py_eq, Int, Json};
use crate::records::{is_commit, is_hex64, is_task, is_version};
use crate::sha256;

const INPUT_KEYS: [&str; 22] = [
    "task_id",
    "log_seq",
    "task_state",
    "contract",
    "contract_hash",
    "approved_contract_hash",
    "head_commit",
    "base_is_ancestor",
    "commits",
    "components",
    "interfaces",
    "symbols",
    "schemas",
    "derived_read_set",
    "observed_read_set",
    "intent_current",
    "dependencies",
    "articles",
    "runtime",
    "risk_rules",
    "policy_version",
    "budget_use",
];
const TASK_STATES: [&str; 3] = ["READY", "REWORK", "IN_PROGRESS"];
const CHANGES: [&str; 3] = ["added", "modified", "deleted"];
const RISKS: [&str; 4] = ["low", "medium", "high", "critical"];
const ORDER: [&str; 7] = [
    "STOP: violation",
    "STOP: scope invalid",
    "STOP: runtime insufficient",
    "ESCALATE",
    "BLOCKED",
    "REPLAN",
    "CONTINUE_WITH",
];
const RECORDER: &str = "the Resume Check (aieos_bootstrap.resume_check)";
const SOURCE_CLASS: &str = "deterministic_tool_local";
const AMBIGUOUS: &str = "ambiguous";
const NO_TASK: &str = "TASK-0";
/// The value of engine_identity.python: the reference writes this placeholder, since the interpreter's version is
/// not a value a port can reproduce (the brief's section 2; decision D-794 C2).
pub const PLACEHOLDER: &str = "<engine>";

/// 2 ** 63, the bound below which log_seq is in its section 9 form.
fn max_log_seq() -> Int {
    Int::from_digits(false, b"9223372036854775808").unwrap_or_else(|| Int::from_u64(u64::MAX))
}

fn risk_index(r: &str) -> usize {
    RISKS.iter().position(|x| *x == r).unwrap_or(0)
}

/// `_str`: a non-empty string.
fn is_s(v: &Json) -> bool {
    v.is_text()
}

/// `_strs`: a list of non-empty strings.
fn is_ss(v: &Json) -> bool {
    matches!(v.as_arr(), Some(a) if a.iter().all(Json::is_text))
}

fn arr(v: &Json) -> &[Json] {
    v.as_arr().map(|a| a.as_slice()).unwrap_or(&[])
}

fn text(v: &Json) -> &str {
    v.as_str().unwrap_or_default()
}

fn texts(v: &Json) -> Vec<String> {
    arr(v).iter().map(|x| text(x).to_string()).collect()
}

fn log_seq_ok(v: &Json) -> bool {
    matches!(v.as_int(), Some(n) if n.is_nonneg() && *n < max_log_seq())
}

/// `_ids(...)`: the event id of a type, the SHA-256 of the task id, log_seq, head_commit, code_sha256 and the type.
struct Ids {
    prefix: String,
}

impl Ids {
    fn new(task_id: &Json, log_seq: &Json, head_commit: &Json, code_sha256: Option<&str>) -> Ids {
        let seq = if log_seq_ok(log_seq) {
            log_seq.as_int().map(Int::text).unwrap_or_default()
        } else {
            String::new()
        };
        let parts = [
            task_id.as_str().unwrap_or_default().to_string(),
            seq,
            head_commit.as_str().unwrap_or_default().to_string(),
            code_sha256.unwrap_or_default().to_string(),
        ];
        Ids {
            prefix: parts.join("\n") + "\n",
        }
    }

    fn id(&self, event_type: &str) -> String {
        sha256::hex(format!("{}{}", self.prefix, event_type).as_bytes())
    }
}

// ---------------------------------------------------------------------------------------------------------------
// Patterns

/// The greedy two-index match of one name against one name pattern in which "*" stands for any part of the name.
fn star_match(pattern: &[char], name: &[char]) -> bool {
    let (mut p, mut n) = (0usize, 0usize);
    let (mut star, mut mark): (Option<usize>, usize) = (None, 0);
    while n < name.len() {
        if p < pattern.len() && pattern[p] == '*' {
            star = Some(p);
            mark = n;
            p += 1;
        } else if p < pattern.len() && pattern[p] == name[n] {
            p += 1;
            n += 1;
        } else if let Some(s) = star {
            mark += 1;
            p = s + 1;
            n = mark;
        } else {
            return false;
        }
    }
    while p < pattern.len() && pattern[p] == '*' {
        p += 1;
    }
    p == pattern.len()
}

fn names_meet(a: &str, b: &str) -> bool {
    let (sa, sb) = (a.contains('*'), b.contains('*'));
    if !sa && !sb {
        return a == b;
    }
    if sa && sb {
        return true;
    }
    let (pattern, name) = if sa { (a, b) } else { (b, a) };
    let p: Vec<char> = pattern.chars().collect();
    let n: Vec<char> = name.chars().collect();
    star_match(&p, &n)
}

fn parts(pattern: &str) -> Vec<String> {
    let full = if pattern.contains('/') {
        pattern.to_string()
    } else {
        format!("**/{}", pattern)
    };
    full.split('/').map(|s| s.to_string()).collect()
}

/// `meet(a, b)`: whether some path could match both patterns. The Python's memoised recursion, computed bottom-up.
pub fn meet(a: &str, b: &str) -> bool {
    let pa = parts(a);
    let pb = parts(b);
    let (la, lb) = (pa.len(), pb.len());
    let w = lb + 1;
    let mut ok = vec![false; (la + 1) * w];
    for i in (0..=la).rev() {
        for j in (0..=lb).rev() {
            let v = if i == la && j == lb {
                true
            } else if i < la && pa[i] == "**" {
                ok[(i + 1) * w + j] || (j < lb && ok[i * w + j + 1])
            } else if j < lb && pb[j] == "**" {
                ok[i * w + j + 1] || (i < la && ok[(i + 1) * w + j])
            } else if i < la && j < lb {
                names_meet(&pa[i], &pb[j]) && ok[(i + 1) * w + j + 1]
            } else {
                false
            };
            ok[i * w + j] = v;
        }
    }
    ok[0]
}

fn matches(pattern: &str, path: &str) -> bool {
    meet(pattern, path)
}

fn folder(path: &str) -> Vec<String> {
    if path.contains('*') {
        return vec![path.to_string()];
    }
    vec![
        path.to_string(),
        format!("{}/**", path.trim_end_matches('/')),
    ]
}

// ---------------------------------------------------------------------------------------------------------------
// The inputs

fn need(ok: bool, what: &str) -> Result<(), String> {
    if ok {
        Ok(())
    } else {
        Err(what.to_string())
    }
}

fn check_inputs(inp: &Json) -> Result<(), String> {
    let m = inp
        .as_obj()
        .ok_or_else(|| "inputs is not an object".to_string())?;
    let missing: Vec<&str> = INPUT_KEYS
        .iter()
        .copied()
        .filter(|k| !m.contains_key(*k))
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    need(
        missing.is_empty(),
        &format!("inputs lacks {}", missing.join(", ")),
    )?;
    let extra: Vec<&str> = m
        .keys()
        .map(|k| k.as_str())
        .filter(|k| !INPUT_KEYS.contains(k))
        .collect();
    need(
        extra.is_empty(),
        &format!(
            "inputs has keys section 9 does not name: {}",
            extra.join(", ")
        ),
    )?;
    need(is_task(inp.get("task_id")), "task_id is not TASK-<digits>")?;
    need(
        log_seq_ok(inp.get("log_seq")),
        "log_seq is not an integer from 0 to 2**63 - 1",
    )?;
    need(
        inp.get("task_state").str_in(&TASK_STATES),
        "task_state is not READY, REWORK or IN_PROGRESS",
    )?;
    for key in ["contract_hash", "approved_contract_hash"] {
        need(
            is_hex64(inp.get(key)),
            &format!("{} is not 64 lowercase hex digits", key),
        )?;
    }
    need(
        is_commit(inp.get("head_commit")),
        "head_commit is not a commit id",
    )?;
    need(
        inp.get("base_is_ancestor").is_bool(),
        "base_is_ancestor is not true or false",
    )?;
    check_contract(inp.get("contract"))?;
    let commits = inp.get("commits");
    need(commits.is_arr(), "commits is not a list")?;
    for c in arr(commits) {
        need(
            c.keys_are(&["id", "paths", "submitted"]),
            "a commit is not {id, paths, submitted}",
        )?;
        need(is_commit(c.get("id")), "a commit id is not a commit id")?;
        need(
            c.get("submitted").is_bool(),
            "a commit submitted is not true or false",
        )?;
        need(c.get("paths").is_arr(), "a commit paths is not a list")?;
        for p in arr(c.get("paths")) {
            need(
                p.keys_are(&["path", "change"])
                    && is_s(p.get("path"))
                    && p.get("change").str_in(&CHANGES),
                "a commit path is not {path, change}",
            )?;
        }
    }
    need(inp.get("components").is_arr(), "components is not a list")?;
    for c in arr(inp.get("components")) {
        need(
            c.is_obj() && is_s(c.get("id")) && is_ss(c.get("paths")),
            "a component is not {id, paths, tags}",
        )?;
    }
    need(inp.get("interfaces").is_arr(), "interfaces is not a list")?;
    for i in arr(inp.get("interfaces")) {
        need(
            i.is_obj() && is_s(i.get("id")) && is_s(i.get("component")),
            "an interface is not {id, component}",
        )?;
    }
    need(inp.get("symbols").is_arr(), "symbols is not a list")?;
    for s in arr(inp.get("symbols")) {
        let sides = ["base", "head"]
            .iter()
            .all(|k| s.get(k).is_null() || s.get(k).is_str());
        need(
            s.keys_are(&["interface", "base", "head"]) && is_s(s.get("interface")) && sides,
            "a symbol is not {interface, base, head}",
        )?;
    }
    need(inp.get("schemas").is_arr(), "schemas is not a list")?;
    for s in arr(inp.get("schemas")) {
        let sides = ["base", "head"].iter().all(|k| schema_side(s.get(k)));
        need(
            s.keys_are(&["name", "base", "head"]) && is_s(s.get("name")) && sides,
            "a schema is not {name, base, head}",
        )?;
    }
    need(
        is_ss(inp.get("derived_read_set")),
        "derived_read_set is not a list of paths",
    )?;
    let observed = inp.get("observed_read_set");
    need(
        observed.is_null() || is_ss(observed),
        "observed_read_set is not a list of paths or null",
    )?;
    let ic = inp.get("intent_current");
    let ic_ok = ic.as_obj().is_some_and(|m| {
        m.iter()
            .all(|(k, v)| !k.is_empty() && (v.is_null() || is_s(v)))
    });
    need(ic_ok, "intent_current is not an object of versions or null")?;
    let deps = inp.get("dependencies");
    need(deps.is_obj(), "dependencies is not an object")?;
    for (k, d) in deps.as_obj().into_iter().flatten() {
        need(
            !k.is_empty()
                && d.keys_are(&["state", "stale_evidence"])
                && (d.get("state").is_null() || is_s(d.get("state")))
                && d.get("stale_evidence").is_bool(),
            "a dependency is not {state, stale_evidence}",
        )?;
    }
    need(inp.get("articles").is_arr(), "articles is not a list")?;
    for a in arr(inp.get("articles")) {
        let v = a.get("violated");
        need(
            a.is_obj() && is_s(a.get("id")) && a.has("violated") && (v.is_null() || v.is_bool()),
            "an article is not {id, scope, applicability, violated}",
        )?;
    }
    let rt = inp.get("runtime");
    let max_risk = rt.get("max_risk");
    need(
        rt.keys_are(&["adapter", "max_risk"])
            && is_s(rt.get("adapter"))
            && (max_risk.is_null() || max_risk.str_in(&RISKS)),
        "runtime is not {adapter, max_risk}",
    )?;
    let rules = inp.get("risk_rules");
    need(
        rules.is_arr() && arr(rules).iter().all(Json::is_obj),
        "risk_rules is not a list of rules",
    )?;
    let pv = inp.get("policy_version");
    need(
        pv.is_null() || is_s(pv),
        "policy_version is not a string or null",
    )?;
    let bu = inp.get("budget_use");
    need(bu.is_obj(), "budget_use is not an object")?;
    for (k, u) in bu.as_obj().into_iter().flatten() {
        let used = u.get("used");
        need(
            !k.is_empty()
                && u.keys_are(&["used", "reported"])
                && u.get("reported").is_bool()
                && (used.is_count() || used.is_str()),
            "a budget use is not {used, reported}",
        )?;
    }
    Ok(())
}

fn schema_side(v: &Json) -> bool {
    if v.is_null() || v.eq_str(AMBIGUOUS) {
        return true;
    }
    v.keys_are(&["path", "sha256"]) && is_s(v.get("path")) && is_hex64(v.get("sha256"))
}

fn check_contract(c: &Json) -> Result<(), String> {
    need(c.is_obj(), "contract is not an object")?;
    for key in [
        "input_state",
        "write_set",
        "read_set",
        "constitution",
        "task_type",
        "risk",
        "autonomy",
        "contract_version",
    ] {
        need(c.has(key), &format!("contract lacks {}", key))?;
    }
    let s = c.get("input_state");
    need(s.is_obj(), "contract input_state is not an object")?;
    need(
        is_commit(s.get("base_commit")),
        "contract base_commit is not a commit id",
    )?;
    need(
        is_ss(s.get("depends_on")),
        "contract depends_on is not a list of task ids",
    )?;
    let iv = s.get("intent_versions");
    let iv_ok = iv
        .as_obj()
        .is_some_and(|m| m.iter().all(|(k, v)| !k.is_empty() && is_s(v)));
    need(
        iv_ok,
        "contract intent_versions is not an object of versions",
    )?;
    let ws = c.get("write_set");
    need(
        ws.is_obj() && is_ss(ws.get("paths")),
        "contract write_set.paths is not a list",
    )?;
    let rs = c.get("read_set");
    let rs_ok = rs.is_obj()
        && ["paths", "interfaces", "schemas"]
            .iter()
            .all(|k| !rs.has(k) || is_ss(rs.get(k)));
    need(
        rs_ok,
        "contract read_set is not {paths, interfaces, schemas}",
    )?;
    need(
        is_ss(c.get("constitution")),
        "contract constitution is not a list of article ids",
    )?;
    need(
        is_s(c.get("task_type")),
        "contract task_type is not a string",
    )?;
    need(
        c.get("risk").str_in(&RISKS),
        "contract risk is not low, medium, high or critical",
    )?;
    need(
        is_version(c.get("contract_version")),
        "contract contract_version is not v<digits>",
    )?;
    let b = c.get("autonomy").get("budgets");
    let b_ok = b.as_obj().is_some_and(|m| {
        m.iter()
            .all(|(k, v)| !k.is_empty() && (v.is_count() || is_s(v)))
    });
    need(b_ok, "contract autonomy.budgets is not an object of limits")?;
    Ok(())
}

// ---------------------------------------------------------------------------------------------------------------
// The effective read-set and the signatures

struct Entry {
    entry: String,
    kind: &'static str,
    sources: Vec<&'static str>,
}

struct Met {
    entry: String,
    kind: &'static str,
    verdict: &'static str,
    reason: &'static str,
}

/// `rs.get(key, [])` for a read_set already checked.
fn read_set_list(rs: &Json, key: &str) -> Vec<String> {
    if rs.has(key) {
        texts(rs.get(key))
    } else {
        vec![]
    }
}

fn read_set(inp: &Json) -> Vec<Entry> {
    let rs = inp.get("contract").get("read_set");
    let mut paths: BTreeMap<String, Vec<&'static str>> = BTreeMap::new();
    let sources: [(&'static str, Vec<String>); 3] = [
        ("declared", read_set_list(rs, "paths")),
        ("derived", texts(inp.get("derived_read_set"))),
        ("observed", texts(inp.get("observed_read_set"))),
    ];
    for (source, items) in sources.iter() {
        for p in items {
            let list = paths.entry(p.clone()).or_default();
            if !list.contains(source) {
                list.push(source);
            }
        }
    }
    let mut entries: Vec<Entry> = paths
        .into_iter()
        .map(|(p, s)| Entry {
            entry: p,
            kind: "path",
            sources: s,
        })
        .collect();
    let interfaces: BTreeSet<String> = read_set_list(rs, "interfaces").into_iter().collect();
    entries.extend(interfaces.into_iter().map(|i| Entry {
        entry: i,
        kind: "interface",
        sources: vec!["declared"],
    }));
    let schemas: BTreeSet<String> = read_set_list(rs, "schemas").into_iter().collect();
    entries.extend(schemas.into_iter().map(|s| Entry {
        entry: s,
        kind: "schema",
        sources: vec!["declared"],
    }));
    entries
}

/// The patterns of a component's paths, or None when the component is unknown or defined more than once.
fn component_paths(inp: &Json, component_id: &str) -> Option<Vec<String>> {
    let found: Vec<&Json> = arr(inp.get("components"))
        .iter()
        .filter(|c| c.get("id").eq_str(component_id))
        .collect();
    if found.len() != 1 {
        return None;
    }
    Some(
        texts(found[0].get("paths"))
            .iter()
            .flat_map(|p| folder(p))
            .collect(),
    )
}

fn interface_component(inp: &Json, name: &str) -> Option<Vec<String>> {
    let found: Vec<&Json> = arr(inp.get("interfaces"))
        .iter()
        .filter(|i| i.get("id").eq_str(name))
        .collect();
    if found.len() != 1 {
        return None;
    }
    component_paths(inp, text(found[0].get("component")))
}

fn schema_paths(inp: &Json, name: &str) -> Option<Vec<String>> {
    let found: Vec<&Json> = arr(inp.get("schemas"))
        .iter()
        .filter(|s| s.get("name").eq_str(name))
        .collect();
    if found.len() != 1 {
        return None;
    }
    let sides = [found[0].get("base"), found[0].get("head")];
    if sides.iter().any(|v| !v.is_obj()) {
        return None;
    }
    let set: BTreeSet<String> = sides
        .iter()
        .map(|v| text(v.get("path")).to_string())
        .collect();
    Some(set.into_iter().collect())
}

fn verdicts(inp: &Json, entries: &[Entry], delta: &[String]) -> (Vec<Met>, Vec<String>) {
    let mut met = Vec::new();
    let mut unresolved = Vec::new();
    for e in entries {
        let name = e.entry.as_str();
        let push = |met: &mut Vec<Met>, verdict, reason| {
            met.push(Met {
                entry: name.to_string(),
                kind: e.kind,
                verdict,
                reason,
            });
        };
        if e.kind == "path" {
            if delta.iter().any(|p| matches(name, p)) {
                push(
                    &mut met,
                    "non_breaking",
                    "a path entry has no signature; its change is non-breaking",
                );
            }
            continue;
        }
        if e.kind == "interface" {
            let comp = match interface_component(inp, name) {
                Some(c) => c,
                None => {
                    unresolved.push(name.to_string());
                    if !delta.is_empty() {
                        push(
                            &mut met,
                            "breaking",
                            "the interface or its component cannot be resolved (fail closed)",
                        );
                    }
                    continue;
                }
            };
            if !comp.iter().any(|c| delta.iter().any(|p| matches(c, p))) {
                continue;
            }
            let sym: Vec<&Json> = arr(inp.get("symbols"))
                .iter()
                .filter(|s| s.get("interface").eq_str(name))
                .collect();
            let (verdict, reason) = if sym.len() != 1 {
                (
                    "breaking",
                    "no single symbol entry for the interface (fail closed)",
                )
            } else {
                let (b, h) = (sym[0].get("base"), sym[0].get("head"));
                if b.is_null() || h.is_null() {
                    ("breaking", "the symbol is in no file at one commit")
                } else if b.eq_str(AMBIGUOUS) || h.eq_str(AMBIGUOUS) {
                    (
                        "breaking",
                        "the symbol is defined more than once at one commit",
                    )
                } else if !py_eq(b, h) {
                    (
                        "breaking",
                        "the signature differs between base_commit and HEAD",
                    )
                } else {
                    (
                        "non_breaking",
                        "the signature is equal at base_commit and HEAD",
                    )
                }
            };
            push(&mut met, verdict, reason);
            continue;
        }
        let resolved = match schema_paths(inp, name) {
            Some(r) => r,
            None => {
                unresolved.push(name.to_string());
                if !delta.is_empty() {
                    push(
                        &mut met,
                        "breaking",
                        "the schema resolves to no file or to more than one at one commit (fail closed)",
                    );
                }
                continue;
            }
        };
        if !resolved.iter().any(|r| delta.iter().any(|p| matches(r, p))) {
            continue;
        }
        let s = arr(inp.get("schemas"))
            .iter()
            .find(|x| x.get("name").eq_str(name))
            .unwrap_or(&crate::json::NULL);
        let (verdict, reason) = if py_eq(s.get("base"), s.get("head")) {
            (
                "non_breaking",
                "the schema file is the same path with the same content hash",
            )
        } else {
            ("breaking", "the schema file or its content hash differs")
        };
        push(&mut met, verdict, reason);
    }
    (met, unresolved)
}

/// The write-set and the effective read-set as patterns, for check 6.
fn task_patterns(inp: &Json, entries: &[Entry]) -> Vec<String> {
    let mut out = texts(inp.get("contract").get("write_set").get("paths"));
    for e in entries {
        if e.kind == "path" {
            out.push(e.entry.clone());
        } else if e.kind == "interface" {
            out.extend(
                interface_component(inp, &e.entry).unwrap_or_else(|| vec!["**".to_string()]),
            );
        } else {
            out.extend(schema_paths(inp, &e.entry).unwrap_or_else(|| vec!["**".to_string()]));
        }
    }
    out
}

// ---------------------------------------------------------------------------------------------------------------
// Check 6, check 7 and check 8

/// `scope.get(key, [])`.
fn get_or_empty<'a>(v: &'a Json, key: &str) -> &'a Json {
    static EMPTY: Json = Json::Arr(Vec::new());
    if v.has(key) {
        v.get(key)
    } else {
        &EMPTY
    }
}

/// An article's scope as patterns: [] for no scope, None when the scope cannot be evaluated.
fn scope_patterns(inp: &Json, scope: &Json) -> Option<Vec<String>> {
    if scope.is_null() {
        return Some(vec![]);
    }
    if !scope.is_obj() {
        return None;
    }
    let paths = get_or_empty(scope, "paths");
    let comps = get_or_empty(scope, "components");
    if !(is_ss(paths) && is_ss(comps)) {
        return None;
    }
    let mut out = texts(paths);
    for cid in texts(comps) {
        out.extend(component_paths(inp, &cid)?);
    }
    Some(out)
}

fn applicable(inp: &Json, article: &Json, patterns: &[String]) -> bool {
    let contract = inp.get("contract");
    let id = article.get("id");
    let listed = arr(contract.get("constitution"))
        .iter()
        .any(|x| py_eq(x, id));
    let app = article.get("applicability");
    if !app.is_null() {
        let types = if app.is_obj() {
            app.get("task_types")
        } else {
            &crate::json::NULL
        };
        let task_type = contract.get("task_type");
        if is_ss(types) && !arr(types).iter().any(|t| py_eq(t, task_type)) && !listed {
            return false;
        }
    }
    if listed {
        return true;
    }
    match scope_patterns(inp, article.get("scope")) {
        None => true,
        Some(sp) => sp.iter().any(|a| patterns.iter().any(|b| meet(a, b))),
    }
}

fn rule_patterns(rule: &Json) -> Option<Vec<String>> {
    let m = rule.get("match");
    if m.is_obj() && is_ss(m.get("paths")) {
        Some(texts(m.get("paths")))
    } else {
        None
    }
}

/// The task's risk (check 7) and the write-set patterns no rule meets.
fn task_risk(inp: &Json) -> (String, Vec<String>) {
    let contract = inp.get("contract");
    let mut risk = text(contract.get("risk")).to_string();
    let mut unmatched = Vec::new();
    for wp in texts(contract.get("write_set").get("paths")) {
        let mut hit = false;
        for rule in arr(inp.get("risk_rules")) {
            let pats = rule_patterns(rule);
            let r = rule.get("risk");
            let cls = if r.str_in(&RISKS) {
                text(r)
            } else {
                "critical"
            };
            if pats
                .as_ref()
                .is_none_or(|ps| ps.iter().any(|p| meet(p, &wp)))
            {
                hit = true;
                if risk_index(cls) > risk_index(&risk) {
                    risk = cls.to_string();
                }
            }
        }
        if !hit {
            unmatched.push(wp);
        }
    }
    (risk, unmatched)
}

/// `_amount(name, value)`: Ok(None) when the form cannot be parsed; Err where the Python's `int()` raises
/// (more digits than CPython converts), which makes the check one that cannot complete.
fn amount(name: &str, value: &Json) -> Result<Option<Int>, String> {
    if value.is_count() {
        return Ok(value.as_int().cloned());
    }
    let s = match value.as_str() {
        Some(s) => s,
        None => return Ok(None),
    };
    let split = s
        .bytes()
        .position(|b| !b.is_ascii_digit())
        .unwrap_or(s.len());
    let (digits, unit) = s.split_at(split);
    if digits.is_empty() || !unit.bytes().all(|b| b.is_ascii_lowercase()) {
        return Ok(None);
    }
    let factor: Option<u64> = match name {
        "tokens" => match unit {
            "" => Some(1),
            "k" => Some(1000),
            "m" => Some(1_000_000),
            _ => None,
        },
        "wall_time" | "human_attention" => match unit {
            "s" => Some(1),
            "m" => Some(60),
            "h" => Some(3600),
            "d" => Some(86400),
            _ => None,
        },
        _ => None,
    };
    let factor = match factor {
        Some(f) => f,
        None => return Ok(None),
    };
    let n = Int::from_digits(false, digits.as_bytes())
        .ok_or_else(|| "the check could not complete: ValueError".to_string())?;
    Ok(Some(n.mul_small(factor)))
}

// ---------------------------------------------------------------------------------------------------------------
// The record

fn base(task_id: &Json, ids: &Ids, code_sha256: Option<&str>) -> BTreeMap<String, Json> {
    let subject = if is_task(task_id) {
        text(task_id)
    } else {
        NO_TASK
    };
    let code = code_sha256.map(Json::s).unwrap_or(Json::Null);
    let mut rec = BTreeMap::new();
    rec.insert(
        "record_id".to_string(),
        Json::Str(ids.id("decision.execution")),
    );
    rec.insert("fact_kind".to_string(), Json::s("interpretation"));
    rec.insert("source_class".to_string(), Json::s(SOURCE_CLASS));
    rec.insert("recorder".to_string(), Json::s(RECORDER));
    rec.insert("subject".to_string(), Json::s(subject));
    rec.insert(
        "engine_identity".to_string(),
        Json::obj(vec![
            ("code_sha256", code),
            ("python", Json::s(PLACEHOLDER)),
        ]),
    );
    rec
}

fn error(inputs: &Json, code_sha256: Option<&str>, reason: &str) -> Json {
    let ids = Ids::new(
        inputs.get("task_id"),
        inputs.get("log_seq"),
        inputs.get("head_commit"),
        code_sha256,
    );
    let mut rec = base(inputs.get("task_id"), &ids, code_sha256);
    let mut uncovered: Vec<String> = Vec::new();
    if code_sha256.is_none() {
        uncovered.push("engine_identity.code_sha256: not given by the caller".to_string());
    }
    if rec.get("subject").is_some_and(|s| s.eq_str(NO_TASK)) {
        uncovered.push(format!(
            "subject: task_id is malformed, so {} stands for it (decision D-359)",
            NO_TASK
        ));
    }
    rec.insert("decision".to_string(), Json::Null);
    rec.insert("error".to_string(), Json::s(reason));
    rec.insert("uncovered".to_string(), Json::strs(&uncovered));
    rec.insert("state_effect".to_string(), Json::Arr(vec![]));
    Json::Obj(rec)
}

/// `resume_check.check(inputs)`: one execution decision record, or Err for a case it cannot compute (the brief's
/// section 2: the two paths whose error record names a Python exception type fail closed).
pub fn check(inputs: &Json) -> Result<Json, String> {
    check_with(inputs, None)
}

/// `resume_check.check(inputs, code_sha256)`.
pub fn check_with(inputs: &Json, code_sha256: Option<&Json>) -> Result<Json, String> {
    let code = match code_sha256 {
        None | Some(Json::Null) => None,
        Some(c) if is_hex64(c) => c.as_str(),
        Some(_) => {
            return Ok(error(
                inputs,
                None,
                "code_sha256 is not 64 lowercase hex digits",
            ))
        }
    };
    if let Err(what) = check_inputs(inputs) {
        return Ok(error(
            inputs,
            code,
            &format!("an input is missing or malformed: {}", what),
        ));
    }
    if !py_eq(
        inputs.get("contract_hash"),
        inputs.get("approved_contract_hash"),
    ) {
        return Ok(error(
            inputs,
            code,
            "check 0: the contract at HEAD is not the approved contract",
        ));
    }
    decide(inputs, code)
}

struct Checks {
    items: BTreeMap<u32, (&'static str, Option<&'static str>, String)>,
}

impl Checks {
    fn put(&mut self, n: u32, status: &'static str, outcome: Option<&'static str>, detail: String) {
        self.items.insert(n, (status, outcome, detail));
    }

    fn status(&self, n: u32) -> &str {
        self.items.get(&n).map(|x| x.0).unwrap_or_default()
    }

    fn outcome(&self, n: u32) -> Option<&'static str> {
        self.items.get(&n).and_then(|x| x.1)
    }

    fn to_json(&self) -> Json {
        Json::Arr(
            (1..=8)
                .map(|n| {
                    let (status, outcome, detail) =
                        self.items
                            .get(&n)
                            .cloned()
                            .unwrap_or(("", None, String::new()));
                    Json::obj(vec![
                        ("check", Json::Int(Int::from_u64(u64::from(n)))),
                        ("status", Json::s(status)),
                        ("outcome", outcome.map(Json::s).unwrap_or(Json::Null)),
                        ("detail", Json::Str(detail)),
                    ])
                })
                .collect(),
        )
    }
}

fn decide(inp: &Json, code_sha256: Option<&str>) -> Result<Json, String> {
    let c = inp.get("contract");
    let s = c.get("input_state");
    let ids = Ids::new(
        inp.get("task_id"),
        inp.get("log_seq"),
        inp.get("head_commit"),
        code_sha256,
    );
    let mut uncovered: Vec<String> = Vec::new();
    let mut checks = Checks {
        items: BTreeMap::new(),
    };
    let write_set = texts(c.get("write_set").get("paths"));
    let same_head = py_eq(s.get("base_commit"), inp.get("head_commit"));

    // Check 1: base freshness.
    let mut delta: BTreeMap<String, String> = BTreeMap::new();
    let mut computed = false;
    if same_head {
        checks.put(1, "passed", None, "base_commit equals HEAD".to_string());
    } else if inp.get("base_is_ancestor").as_bool() != Some(true) {
        checks.put(
            1,
            "fired",
            Some("ESCALATE"),
            "base_commit is not an ancestor of HEAD".to_string(),
        );
    } else {
        for commit in arr(inp.get("commits")) {
            if commit.get("submitted").as_bool() == Some(true) {
                continue;
            }
            for p in arr(commit.get("paths")) {
                delta.insert(
                    text(p.get("path")).to_string(),
                    text(p.get("change")).to_string(),
                );
            }
        }
        computed = true;
        checks.put(
            1,
            "passed",
            None,
            format!("{} paths changed since base_commit", delta.len()),
        );
    }
    let entries = read_set(inp);
    let mut met: Vec<Met> = Vec::new();
    let mut unresolved: Vec<String> = Vec::new();
    // Check 2: write-set conflict; check 3: read-set freshness.
    if same_head {
        checks.put(2, "skipped", None, "HEAD equals base_commit".to_string());
        checks.put(3, "skipped", None, "HEAD equals base_commit".to_string());
    } else if !computed {
        checks.put(
            2,
            "not_run",
            None,
            "the delta cannot be computed".to_string(),
        );
        checks.put(
            3,
            "not_run",
            None,
            "the delta cannot be computed".to_string(),
        );
    } else {
        let hit: Vec<String> = delta
            .keys()
            .filter(|p| write_set.iter().any(|w| matches(w, p)))
            .cloned()
            .collect();
        if !hit.is_empty() {
            checks.put(
                2,
                "fired",
                Some("STOP: scope invalid"),
                format!("delta meets the write-set: {}", hit.join(", ")),
            );
        } else {
            checks.put(
                2,
                "passed",
                None,
                "delta does not meet the write-set".to_string(),
            );
        }
        let delta_paths: Vec<String> = delta.keys().cloned().collect();
        (met, unresolved) = verdicts(inp, &entries, &delta_paths);
        if met.is_empty() {
            checks.put(
                3,
                "passed",
                None,
                "delta meets no entry of the effective read-set".to_string(),
            );
        } else if met.iter().any(|m| m.verdict == "breaking") {
            let names: Vec<&str> = met
                .iter()
                .filter(|m| m.verdict == "breaking")
                .map(|m| m.entry.as_str())
                .collect();
            checks.put(
                3,
                "fired",
                Some("REPLAN"),
                format!("a met entry is breaking: {}", names.join(", ")),
            );
        } else {
            checks.put(
                3,
                "fired",
                Some("CONTINUE_WITH"),
                "every met entry is non-breaking".to_string(),
            );
        }
    }
    // Check 4: intent freshness.
    let mut iv: BTreeMap<String, Json> = BTreeMap::new();
    let mut moved: Vec<String> = Vec::new();
    for (entity, version) in s.get("intent_versions").as_obj().into_iter().flatten() {
        let current = inp.get("intent_current").get(entity);
        iv.insert(
            entity.clone(),
            Json::obj(vec![
                ("contract", version.clone()),
                ("current", current.clone()),
            ]),
        );
        if !py_eq(current, version) {
            moved.push(entity.clone());
        }
    }
    if !moved.is_empty() {
        checks.put(
            4,
            "fired",
            Some("REPLAN"),
            format!("intent moved or missing at HEAD: {}", moved.join(", ")),
        );
    } else {
        checks.put(
            4,
            "passed",
            None,
            "every intent version is current".to_string(),
        );
    }
    // Check 5: dependency freshness.
    let mut deps: BTreeMap<String, Json> = BTreeMap::new();
    let mut blocking: Vec<String> = Vec::new();
    for task in texts(s.get("depends_on")) {
        let d = inp.get("dependencies").get(&task);
        let state = if d.is_null() {
            Json::Null
        } else {
            d.get("state").clone()
        };
        let done = state.eq_str("DONE");
        deps.insert(task.clone(), state);
        if !done {
            blocking.push(task);
        }
    }
    if !blocking.is_empty() {
        let detail = format!(
            "a dependency is not DONE, is STALE or is unknown: {}",
            blocking.join(", ")
        );
        checks.put(5, "fired", Some("BLOCKED"), detail);
    } else {
        checks.put(5, "passed", None, "every dependency is DONE".to_string());
    }
    // Check 6: constitution.
    let patterns = task_patterns(inp, &entries);
    let mut applicable_ids: Vec<String> = Vec::new();
    let mut violated: Vec<String> = Vec::new();
    let mut no_result: Vec<String> = Vec::new();
    for a in arr(inp.get("articles")) {
        if applicable(inp, a, &patterns) {
            let id = text(a.get("id")).to_string();
            applicable_ids.push(id.clone());
            let v = a.get("violated");
            if v.as_bool() == Some(true) {
                violated.push(id);
            } else if v.is_null() {
                no_result.push(id);
            }
        }
    }
    let known: BTreeSet<String> = arr(inp.get("articles"))
        .iter()
        .map(|a| text(a.get("id")).to_string())
        .collect();
    for aid in texts(c.get("constitution")) {
        if !known.contains(&aid) && !applicable_ids.contains(&aid) {
            applicable_ids.push(aid.clone());
            no_result.push(aid);
        }
    }
    for aid in &no_result {
        uncovered.push(format!("article {}: no check result at HEAD", aid));
    }
    if !violated.is_empty() {
        let detail = format!(
            "an applicable article is violated at HEAD: {}",
            violated.join(", ")
        );
        checks.put(6, "fired", Some("ESCALATE"), detail);
    } else {
        checks.put(
            6,
            "passed",
            None,
            "no applicable article is violated at HEAD".to_string(),
        );
    }
    // Check 7: runtime.
    let (task_risk_value, unmatched) = task_risk(inp);
    let max_risk = inp.get("runtime").get("max_risk");
    match max_risk.as_str() {
        Some(mr) if risk_index(mr) >= risk_index(&task_risk_value) => {
            if !unmatched.is_empty() {
                let detail = format!(
                    "a write-set pattern meets no risk rule: {}",
                    unmatched.join(", ")
                );
                checks.put(7, "fired", Some("ESCALATE"), detail);
            } else {
                let detail = format!("max_risk {} covers the task risk {}", mr, task_risk_value);
                checks.put(7, "passed", None, detail);
            }
        }
        Some(mr) => {
            let detail = format!("max_risk {} is below the task risk {}", mr, task_risk_value);
            checks.put(7, "fired", Some("STOP: runtime insufficient"), detail);
        }
        None => {
            checks.put(
                7,
                "fired",
                Some("STOP: runtime insufficient"),
                "the runtime has no declaration".to_string(),
            );
        }
    }
    // Check 8: budget.
    let mut budgets: BTreeMap<String, Json> = BTreeMap::new();
    let mut over: Vec<String> = Vec::new();
    for (name, limit) in c
        .get("autonomy")
        .get("budgets")
        .as_obj()
        .into_iter()
        .flatten()
    {
        let use_ = inp.get("budget_use").get(name);
        let used = if use_.is_null() {
            Json::Null
        } else {
            use_.get("used").clone()
        };
        let reported = !use_.is_null() && use_.get("reported").as_bool() == Some(true);
        budgets.insert(
            name.clone(),
            Json::obj(vec![
                ("limit", limit.clone()),
                ("used", used.clone()),
                ("reported", Json::Bool(reported)),
            ]),
        );
        if !reported {
            uncovered.push(format!("budget {}: use not reported", name));
            continue;
        }
        let (mut lim, mut amt) = (amount(name, limit)?, amount(name, &used)?);
        if name == "retries" {
            lim = if limit.is_count() {
                limit.as_int().cloned()
            } else {
                None
            };
            amt = if used.is_count() {
                used.as_int().cloned()
            } else {
                None
            };
        }
        match (lim, amt) {
            (Some(l), Some(a)) => {
                if a > l {
                    over.push(name.clone());
                }
            }
            _ => uncovered.push(format!("budget {}: a form that cannot be parsed", name)),
        }
    }
    if !over.is_empty() {
        checks.put(
            8,
            "fired",
            Some("ESCALATE"),
            format!("a budget is used up: {}", over.join(", ")),
        );
    } else {
        checks.put(
            8,
            "passed",
            None,
            "every reported budget use is within its limit".to_string(),
        );
    }

    let fired: Vec<&str> = (1..=8)
        .filter(|n| checks.status(*n) == "fired")
        .filter_map(|n| checks.outcome(n))
        .collect();
    let outcomes: Vec<&str> = ORDER
        .iter()
        .copied()
        .filter(|o| fired.contains(o))
        .collect();
    let decision = outcomes.first().copied().unwrap_or("CONTINUE");
    let observed_none = inp.get("observed_read_set").is_null();
    if observed_none {
        uncovered.push(
            "read-set: no observed source, the effective read-set is an estimate".to_string(),
        );
    }
    if code_sha256.is_none() {
        uncovered.push("engine_identity.code_sha256: not given by the caller".to_string());
    }

    let mut record = base(inp.get("task_id"), &ids, code_sha256);
    let record_id = record
        .get("record_id")
        .map(|r| text(r).to_string())
        .unwrap_or_default();
    let effect = effect(
        decision,
        &checks,
        inp,
        &ids,
        &record_id,
        &met,
        &delta,
        &write_set,
        &mut uncovered,
    );
    let unresolved: BTreeSet<String> = unresolved.into_iter().collect();
    let entries_json: Vec<Json> = entries
        .iter()
        .map(|e| {
            Json::obj(vec![
                ("entry", Json::s(&e.entry)),
                ("kind", Json::s(e.kind)),
                ("sources", Json::strs(&e.sources)),
            ])
        })
        .collect();
    let met_json: Vec<Json> = met
        .iter()
        .map(|m| {
            Json::obj(vec![
                ("entry", Json::s(&m.entry)),
                ("kind", Json::s(m.kind)),
                ("verdict", Json::s(m.verdict)),
                ("reason", Json::s(m.reason)),
            ])
        })
        .collect();
    let delta_json: Vec<Json> = delta
        .iter()
        .map(|(p, ch)| Json::obj(vec![("path", Json::s(p)), ("change", Json::s(ch))]))
        .collect();
    let fields: Vec<(&str, Json)> = vec![
        ("decision", Json::s(decision)),
        ("contract_hash", inp.get("contract_hash").clone()),
        ("contract_version", c.get("contract_version").clone()),
        ("base_commit", s.get("base_commit").clone()),
        ("head_commit", inp.get("head_commit").clone()),
        ("log_seq", inp.get("log_seq").clone()),
        ("delta", Json::Arr(delta_json)),
        ("checks", checks.to_json()),
        ("outcomes_fired", Json::strs(&outcomes)),
        (
            "read_set",
            Json::obj(vec![
                ("entries", Json::Arr(entries_json)),
                ("estimate", Json::Bool(observed_none)),
                (
                    "unresolved",
                    Json::Arr(unresolved.iter().map(|u| Json::s(u)).collect()),
                ),
                ("unanalysed", Json::Arr(vec![])),
            ]),
        ),
        ("signatures", Json::Arr(met_json)),
        ("intent_versions", Json::Obj(iv)),
        ("dependencies", Json::Obj(deps)),
        (
            "constitution",
            Json::obj(vec![
                ("applicable", Json::strs(&applicable_ids)),
                ("violated", Json::strs(&violated)),
                ("no_result", Json::strs(&no_result)),
            ]),
        ),
        (
            "runtime",
            Json::obj(vec![
                ("adapter", inp.get("runtime").get("adapter").clone()),
                ("max_risk", max_risk.clone()),
                ("task_risk", Json::s(&task_risk_value)),
            ]),
        ),
        ("budgets", Json::Obj(budgets)),
        ("policy_version", inp.get("policy_version").clone()),
        ("uncovered", Json::strs(&uncovered)),
        ("state_effect", Json::Arr(effect)),
    ];
    for (k, v) in fields {
        record.insert(k.to_string(), v);
    }
    Ok(Json::Obj(record))
}

fn event(ids: &Ids, task: &Json, event_type: &str, payload: Json) -> Json {
    Json::obj(vec![
        ("event_id", Json::Str(ids.id(event_type))),
        ("type", Json::s(event_type)),
        ("payload", payload),
        ("task_id", task.clone()),
    ])
}

/// The events of specification 3 section 10 for the decision, in the order the caller would append them.
#[allow(clippy::too_many_arguments)]
fn effect(
    decision: &str,
    checks: &Checks,
    inp: &Json,
    ids: &Ids,
    record_id: &str,
    met: &[Met],
    delta: &BTreeMap<String, String>,
    write_set: &[String],
    uncovered: &mut Vec<String>,
) -> Vec<Json> {
    let task = inp.get("task_id");
    let trailers = "conflict.detected tasks: the commits' trailers are not an input";
    match decision {
        "REPLAN" => {
            let fired = |n: u32| checks.status(n) == "fired" && checks.outcome(n) == Some("REPLAN");
            if !fired(3) && fired(4) {
                uncovered.push(
                    "check 4 REPLAN: no task.stale, since the intent.changed event it must refer to is not an input \
                     (specification 3 section 12 point 4)"
                        .to_string(),
                );
                return vec![];
            }
            let hit: BTreeSet<String> = met
                .iter()
                .filter(|m| m.kind != "interface")
                .flat_map(|m| delta.keys().filter(move |p| meets_entry(inp, m, p)))
                .cloned()
                .collect();
            let mut interfaces: Vec<String> = met
                .iter()
                .filter(|m| m.kind == "interface")
                .map(|m| m.entry.clone())
                .collect();
            interfaces.sort();
            let paths: Vec<String> = hit.into_iter().collect();
            let conflict = event(
                ids,
                task,
                "conflict.detected",
                Json::obj(vec![
                    ("tasks", Json::Arr(vec![])),
                    ("paths", Json::strs(&paths)),
                    ("interfaces", Json::strs(&interfaces)),
                ]),
            );
            uncovered.push(trailers.to_string());
            if inp.get("task_state").eq_str("READY") {
                return vec![conflict];
            }
            let refers_to = conflict.get("event_id").clone();
            let stale = event(
                ids,
                task,
                "task.stale",
                Json::obj(vec![
                    ("cause", Json::s("conflict")),
                    ("refers_to", refers_to),
                ]),
            );
            vec![conflict, stale]
        }
        "BLOCKED" => {
            let deps = inp.get("dependencies");
            let tasks: Vec<String> =
                texts(inp.get("contract").get("input_state").get("depends_on"))
                    .into_iter()
                    .filter(|t| !deps.get(t).get("state").eq_str("DONE"))
                    .collect();
            vec![event(
                ids,
                task,
                "task.blocked",
                Json::obj(vec![
                    ("reason", Json::s("dependency")),
                    ("blocked_by", Json::strs(&tasks)),
                ]),
            )]
        }
        "ESCALATE" => vec![event(
            ids,
            task,
            "task.blocked",
            Json::obj(vec![
                ("reason", Json::s("escalate")),
                ("blocked_by", Json::strs(&[record_id])),
            ]),
        )],
        "STOP: scope invalid" => {
            let hit: Vec<String> = delta
                .keys()
                .filter(|p| write_set.iter().any(|w| matches(w, p)))
                .cloned()
                .collect();
            let conflict = event(
                ids,
                task,
                "conflict.detected",
                Json::obj(vec![
                    ("tasks", Json::Arr(vec![])),
                    ("paths", Json::strs(&hit)),
                ]),
            );
            uncovered.push(trailers.to_string());
            let refers = conflict.get("event_id").clone();
            let blocked = event(
                ids,
                task,
                "task.blocked",
                Json::obj(vec![
                    ("reason", Json::s("scope_invalid")),
                    ("blocked_by", Json::Arr(vec![refers])),
                ]),
            );
            vec![conflict, blocked]
        }
        _ => vec![],
    }
}

fn meets_entry(inp: &Json, m: &Met, path: &str) -> bool {
    if m.kind == "path" {
        return matches(&m.entry, path);
    }
    match schema_paths(inp, &m.entry) {
        None => true,
        Some(resolved) => resolved.iter().any(|r| matches(r, path)),
    }
}

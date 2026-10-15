//! Round 2's own tests (TASK-048 AC5; the port brief's section 6.4), run as `cargo test --release --test port2_test
//! -- <round-2 input document> <round-2 reference document>`. They reach the code only through the library, read the
//! two documents given as arguments, print each check and exit non-zero on any failure.

use aieos_bench_port::pyval::V;
use aieos_bench_port::round2;
use aieos_bench_port::{canon, canonical_text, parse, Json};

struct Checks {
    passed: usize,
    failed: usize,
}

impl Checks {
    fn check(&mut self, ok: bool, what: &str) {
        if ok {
            self.passed += 1;
            println!("ok: {}", what);
        } else {
            self.failed += 1;
            println!("FAIL: {}", what);
        }
    }
}

fn read_file(path: &str) -> Result<Vec<u8>, String> {
    std::fs::read(path).map_err(|e| format!("cannot read {}: {}", path, e))
}

/// The canonical text of a value, for comparing one field.
fn text(v: &Json) -> String {
    canon(v)
}

fn list(v: &Json, key: &str) -> Vec<Json> {
    v.get(key).as_arr().cloned().unwrap_or_default()
}

/// A copy of the document with one key of one entry of one list set to a value.
fn with_entry(doc: &Json, list_key: &str, index: usize, key: &str, value: Json) -> Json {
    let mut out = doc.clone();
    if let Json::Obj(m) = &mut out {
        if let Some(Json::Arr(a)) = m.get_mut(list_key) {
            if let Some(Json::Obj(entry)) = a.get_mut(index) {
                entry.insert(key.to_string(), value);
            }
        }
    }
    out
}

/// A document holding only the given append calls and reconcile cases.
fn small(calls: Vec<Json>, cases: Vec<Json>) -> Json {
    Json::obj(vec![
        ("append", Json::Arr(calls)),
        ("reconcile", Json::Arr(cases)),
    ])
}

fn field_by_field(c: &mut Checks, what: &str, ours: &Json, theirs: &Json, fields: &[&str]) {
    for field in fields {
        c.check(
            text(ours.get(field)) == text(theirs.get(field)),
            &format!("{}: field {} equals the reference", what, field),
        );
    }
    c.check(
        ours.as_obj().map(|m| m.len()) == Some(fields.len()),
        &format!("{}: exactly the fields {}", what, fields.join(", ")),
    );
}

fn main() -> Result<(), String> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.len() != 2 {
        return Err(
            "usage: port2_test <round-2 input document> <round-2 reference document>".to_string(),
        );
    }
    let input = read_file(&args[0])?;
    let reference = read_file(&args[1])?;
    let mut c = Checks {
        passed: 0,
        failed: 0,
    };

    // 1. The byte equality over the whole input, through the run the entry makes.
    let reader = |p: &str| -> Result<Vec<u8>, String> {
        if p == "round2-input" {
            Ok(input.clone())
        } else {
            Err(format!("no such file: {}", p))
        }
    };
    let out = round2::run(&["round2-input".to_string()], &reader);
    c.check(
        out.as_ref().is_ok_and(|o| *o == reference),
        "the whole document is byte-equal to the reference",
    );
    if let Err(e) = &out {
        println!("  reason: {}", e);
    }
    c.check(
        out.as_ref().is_ok_and(|o| {
            o.is_ascii() && !o.contains(&b'\r') && o.ends_with(b"\n") && !o.ends_with(b"\n\n")
        }),
        "the document is ASCII with LF line ends and one final LF",
    );

    let ref_doc = parse(&reference)?;
    let in_doc = parse(&input)?;
    let ref_append = list(&ref_doc, "append");
    let ref_reconcile = list(&ref_doc, "reconcile");
    let doc = round2::read_input(&input)?;
    let calls: Vec<V> = doc
        .get("append")
        .as_arr()
        .map(|a| a.to_vec())
        .unwrap_or_default();
    let append_fields = ["findings", "line", "reason", "record", "result", "seq"];
    let reconcile_fields = ["events", "expired", "findings", "log"];
    c.check(
        calls.len() == ref_append.len() && calls.len() > 12,
        "one append entry per call in the reference",
    );

    // 2. One append call field by field (call 5: a submission with no lease, refused by the fence with its record),
    // and one reconcile case field by field (case 1: a compensating submission).
    let entries = round2::append_entries(&doc)?;
    field_by_field(
        &mut c,
        "append call 5",
        &entries[5].to_json(),
        &ref_append[5],
        &append_fields,
    );
    let recs = round2::reconcile_entries(&doc)?;
    c.check(
        recs.len() == ref_reconcile.len() && !recs.is_empty(),
        "one reconcile entry per case in the reference",
    );
    field_by_field(
        &mut c,
        "reconcile case 1",
        &recs[0].to_json(),
        &ref_reconcile[0],
        &reconcile_fields,
    );

    // 3. The carried log: each call is given the log after the calls before it, extended only by an appended one.
    let mut log: Vec<u8> = Vec::new();
    let mut after_appended = None;
    let mut after_refused = None;
    let mut all_equal = true;
    let mut grows_only_when_appended = true;
    for (i, call) in calls.iter().enumerate() {
        let r = round2::append_call(&log, call)?;
        let ours = round2::append_entry(&r)?.to_json();
        let equal = text(&ours) == text(&ref_append[i]);
        all_equal &= equal;
        if i > 0 {
            let previous = ref_append[i - 1].get("result");
            if previous.eq_str("appended") && after_appended.is_none() && r.result == "appended" {
                after_appended = Some((i, equal));
            }
            if previous.eq_str("refused") && after_refused.is_none() && r.result == "appended" {
                after_refused = Some((i, equal));
            }
        }
        if r.result == "appended" {
            let new_log = r.log.clone().unwrap_or_default();
            let line = r.line.clone().unwrap_or_default();
            grows_only_when_appended &=
                new_log.starts_with(&log) && new_log[log.len()..] == line[..];
            log = new_log;
        }
    }
    c.check(
        all_equal,
        "every append entry, computed call by call over the carried log, equals the reference",
    );
    c.check(
        grows_only_when_appended,
        "an appended call's log is the carried log followed by its line",
    );
    match after_appended {
        Some((i, equal)) => {
            c.check(
                equal,
                &format!("call {} (after an appended one) equals the reference", i),
            );
            let alone = round2::append_call(b"", &calls[i])?;
            let alone_entry = round2::append_entry(&alone)?.to_json();
            c.check(
                text(&alone_entry) != text(&ref_append[i]),
                &format!(
                    "call {} over the empty log differs, so the carried log is what makes it equal",
                    i
                ),
            );
        }
        None => c.check(false, "an appended entry right after an appended one"),
    }
    match after_refused {
        Some((i, equal)) => c.check(
            equal,
            &format!("call {} (after a refused one) equals the reference", i),
        ),
        None => c.check(false, "an appended entry right after a refused one"),
    }

    // 4. Each fail-closed input of AC1: no document (main then writes nothing and exits non-zero).
    c.check(round2::run(&[], &reader).is_err(), "no argument: refused");
    c.check(
        round2::run(&["round2-input".to_string(), "x".to_string()], &reader).is_err(),
        "an extra argument: refused",
    );
    c.check(
        round2::run(&["no-such-file".to_string()], &reader).is_err(),
        "a file that cannot be read: refused",
    );
    let mut without_lf = input.clone();
    without_lf.pop();
    let mut spaced = b" ".to_vec();
    spaced.extend_from_slice(&input);
    let not_documents: Vec<(&str, Vec<u8>)> = vec![
        ("an empty file", b"".to_vec()),
        ("not JSON", b"not json".to_vec()),
        ("a list", b"[]\n".to_vec()),
        ("an empty object", b"{}\n".to_vec()),
        (
            "an extra key",
            b"{\n  \"append\": [],\n  \"reconcile\": [],\n  \"x\": 1\n}\n".to_vec(),
        ),
        (
            "a repeated key",
            b"{\"append\":[],\"append\":[],\"reconcile\":[]}\n".to_vec(),
        ),
        (
            "append not a list",
            canonical_text(&small_value("append", Json::Bool(true))),
        ),
        ("the input without its final LF", without_lf),
        ("the input after a space", spaced),
        (
            "an append call without its keys",
            canonical_text(&small(
                vec![Json::obj(vec![("event_type", Json::s("task.done"))])],
                vec![],
            )),
        ),
        (
            "a reconcile case without its keys",
            canonical_text(&small(vec![], vec![Json::obj(vec![("log", Json::s(""))])])),
        ),
    ];
    for (what, data) in &not_documents {
        c.check(
            round2::document(data).is_err(),
            &format!("not an input document ({}): refused", what),
        );
    }

    let call0 = list(&in_doc, "append")[0].clone();
    let case0 = list(&in_doc, "reconcile")[0].clone();
    let one_call = small(vec![call0.clone()], vec![]);
    let one_case = small(vec![], vec![case0.clone()]);
    c.check(
        round2::document(&canonical_text(&one_call)).is_ok()
            && round2::document(&canonical_text(&one_case)).is_ok(),
        "the small documents the cases below change are computed",
    );
    let cannot: Vec<(&str, Json)> = vec![
        (
            "a time not of the form",
            with_entry(
                &one_call,
                "append",
                0,
                "appended_at",
                Json::s("2026-01-01 00:00:00"),
            ),
        ),
        (
            "a year before 1000",
            with_entry(
                &one_call,
                "append",
                0,
                "appended_at",
                Json::s("0999-01-01T00:00:00Z"),
            ),
        ),
        (
            "an event type that is a list (Python's TypeError)",
            with_entry(
                &one_call,
                "append",
                0,
                "event_type",
                Json::Arr(vec![Json::s("task.done")]),
            ),
        ),
        (
            "a lease that is not an object",
            with_entry(&one_call, "append", 0, "lease", Json::s("x")),
        ),
        (
            "commits that are not a list",
            with_entry(&one_case, "reconcile", 0, "commits", Json::s("none")),
        ),
        (
            "a log that is not text",
            with_entry(&one_case, "reconcile", 0, "log", Json::Bool(true)),
        ),
        (
            "a log line that is a JSON list (a text naming a Python type)",
            with_entry(&one_case, "reconcile", 0, "log", Json::s("[]\n")),
        ),
        (
            "a log line with a fraction (Python's own reader messages)",
            with_entry(&one_case, "reconcile", 0, "log", Json::s("{\"a\":1.5}\n")),
        ),
        (
            "a recorder that is empty",
            with_entry(&one_case, "reconcile", 0, "recorder", Json::s("")),
        ),
    ];
    for (what, value) in &cannot {
        c.check(
            round2::document(&canonical_text(value)).is_err(),
            &format!("a case that cannot be computed ({}): refused", what),
        );
    }

    println!("{} checks passed, {} failed", c.passed, c.failed);
    if c.failed > 0 {
        return Err(format!("{} checks failed", c.failed));
    }
    Ok(())
}

/// A document {append: value, reconcile: []}.
fn small_value(key: &str, value: Json) -> Json {
    let mut out = small(vec![], vec![]);
    if let Json::Obj(m) = &mut out {
        m.insert(key.to_string(), value);
    }
    out
}

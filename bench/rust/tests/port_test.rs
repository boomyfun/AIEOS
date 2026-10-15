//! The port's own tests (TASK-045 AC5), run as `cargo test --locked --offline --release -- <fixture document>
//! <reference document>`. They reach the port only through its library, read only the two documents named by their
//! arguments, print each check and exit non-zero on any failure.

use aieos_bench_port as port;
use port::Json;

struct Tally {
    passed: usize,
    failed: usize,
}

impl Tally {
    fn check(&mut self, name: &str, ok: bool, detail: &str) {
        if ok {
            self.passed += 1;
            println!("ok    {}", name);
        } else {
            self.failed += 1;
            println!("FAIL  {}: {}", name, detail);
        }
    }
}

fn obj_mut<'a>(v: &'a mut Json, key: &str) -> &'a mut Json {
    match v {
        Json::Obj(m) => m.get_mut(key).unwrap_or_else(|| panic!("no key {}", key)),
        _ => panic!("not an object at {}", key),
    }
}

fn idx_mut(v: &mut Json, n: usize) -> &mut Json {
    match v {
        Json::Arr(a) => &mut a[n],
        _ => panic!("not a list"),
    }
}

fn remove_key(v: &mut Json, key: &str) {
    if let Json::Obj(m) = v {
        m.remove(key);
    }
}

fn keys(v: &Json) -> Vec<String> {
    v.as_obj()
        .map(|m| m.keys().cloned().collect())
        .unwrap_or_default()
}

fn text_of(v: &Json) -> String {
    port::canon(v)
}

/// The run over the given bytes as the one argument's content.
fn run_bytes(data: &[u8]) -> Result<Vec<u8>, String> {
    let owned = data.to_vec();
    port::run(&["doc".to_string()], &move |_: &str| Ok(owned.clone()))
}

/// The first key and case where two documents differ, for a readable failure.
fn first_difference(a: &[u8], b: &[u8]) -> String {
    let pos = a
        .iter()
        .zip(b)
        .position(|(x, y)| x != y)
        .unwrap_or(a.len().min(b.len()));
    let line = a[..pos].iter().filter(|&&c| c == b'\n').count() + 1;
    let mut where_ = String::new();
    if let (Ok(da), Ok(db)) = (port::parse(a), port::parse(b)) {
        for key in keys(&da) {
            let (x, y) = (da.get(&key), db.get(&key));
            if text_of(x) != text_of(y) {
                let n = x.as_arr().map(|l| l.len()).unwrap_or(0);
                for i in 0..n {
                    let (p, q) = (&x.as_arr().unwrap()[i], y.as_arr().and_then(|l| l.get(i)));
                    if q.is_none_or(|q| text_of(p) != text_of(q)) {
                        where_ = format!(", key {} case {}", key, i + 1);
                        break;
                    }
                }
                if where_.is_empty() {
                    where_ = format!(", key {}", key);
                }
                break;
            }
        }
    }
    format!(
        "lengths {} and {}, first difference at byte {} (line {}){}",
        a.len(),
        b.len(),
        pos,
        line,
        where_
    )
}

/// Every field of the port's record against the reference's: the key sets, then each value's canonical text. One
/// line per case; each differing field is named.
fn fields(t: &mut Tally, name: &str, got: &Json, want: &Json) -> usize {
    let mut bad: Vec<String> = Vec::new();
    if keys(got) != keys(want) {
        bad.push(format!("keys {:?} / {:?}", keys(got), keys(want)));
    }
    let mut n = 0;
    for key in keys(want) {
        let (g, w) = (text_of(got.get(&key)), text_of(want.get(&key)));
        if g != w {
            bad.push(format!("field {}: port {} / reference {}", key, g, w));
        }
        n += 1;
    }
    t.check(
        &format!("{}: {} fields equal, field by field", name, n),
        bad.is_empty() && n > 0,
        &bad.join("; "),
    );
    n
}

fn main() -> Result<(), String> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.len() != 2 {
        return Err("usage: port_test <fixture document> <reference document>".to_string());
    }
    let fixtures =
        std::fs::read(&args[0]).map_err(|e| format!("cannot read {}: {}", args[0], e))?;
    let reference =
        std::fs::read(&args[1]).map_err(|e| format!("cannot read {}: {}", args[1], e))?;
    let mut t = Tally {
        passed: 0,
        failed: 0,
    };

    // 1. The byte equality over the whole fixture document (through the same run function main calls).
    let fixture_path = args[0].clone();
    let fx_bytes = fixtures.clone();
    let reader = move |p: &str| {
        if p == fixture_path {
            Ok(fx_bytes.clone())
        } else {
            Err(format!("no such document {}", p))
        }
    };
    let out = port::run(std::slice::from_ref(&args[0]), &reader);
    let out = match out {
        Ok(o) => o,
        Err(e) => {
            t.check("the port builds the document", false, &e);
            Vec::new()
        }
    };
    let detail = if out == reference {
        String::new()
    } else {
        first_difference(&out, &reference)
    };
    t.check(
        "byte equality with the reference document",
        out == reference,
        &detail,
    );
    t.check(
        "the output is ASCII, LF only, one final LF",
        out.iter().all(|&b| b < 128 && b != b'\r')
            && out.ends_with(b"\n")
            && !out.ends_with(b"\n\n"),
        "",
    );
    t.check(
        "the same output on a second run",
        run_bytes(&fixtures).ok() == Some(out.clone()),
        "",
    );

    let fx = port::parse(&fixtures).map_err(|e| format!("the fixture document: {}", e))?;
    let refdoc = port::parse(&reference).map_err(|e| format!("the reference document: {}", e))?;
    let outdoc = port::parse(&out).unwrap_or(Json::Null);

    // 2. One governor case and one Resume Check case field by field (every case is compared, each field reported).
    let (mut gov_fields, mut rc_fields, mut gov_cases, mut rc_cases) = (0, 0, 0, 0);
    for key in keys(&fx) {
        let (folder, _) = key.split_once('/').unwrap_or_default();
        if folder != port::GOVERNOR_FOLDER && folder != port::RC_FOLDER {
            continue;
        }
        let cases = fx
            .get(&key)
            .get("cases")
            .as_arr()
            .cloned()
            .unwrap_or_default();
        for (n, case) in cases.iter().enumerate() {
            let name = format!("{} case {}", key, n + 1);
            let want = refdoc
                .get(&key)
                .as_arr()
                .and_then(|l| l.get(n))
                .cloned()
                .unwrap_or(Json::Null);
            let got = if folder == port::GOVERNOR_FOLDER {
                port::evaluate(case.get("request"), case.get("inputs"), case.get("records"))
            } else {
                port::check(case.get("inputs"))
            };
            let mut got = match got {
                Ok(g) => g,
                Err(e) => {
                    t.check(&name, false, &e);
                    continue;
                }
            };
            port::placeholder(folder, &mut got);
            let f = fields(&mut t, &name, &got, &want);
            if folder == port::GOVERNOR_FOLDER {
                gov_fields += f;
                gov_cases += 1;
            } else {
                rc_fields += f;
                rc_cases += 1;
            }
        }
    }
    t.check(
        "governor and Resume Check cases compared field by field",
        gov_cases > 0 && rc_cases > 0 && gov_fields > 0 && rc_fields > 0,
        &format!(
            "{} governor cases, {} Resume Check cases",
            gov_cases, rc_cases
        ),
    );
    println!(
        "      ({} governor cases, {} fields; {} Resume Check cases, {} fields)",
        gov_cases, gov_fields, rc_cases, rc_fields
    );

    // 3. The placeholder: exactly engine_identity.python of every Resume Check record, and nothing else.
    let (mut rc_records, mut placeholders, mut misplaced) = (0, 0, 0);
    for key in keys(&outdoc) {
        let is_rc = key.starts_with("fixtures_rc/");
        for rec in outdoc.get(&key).as_arr().cloned().unwrap_or_default() {
            let ident = rec.get("engine_identity");
            if is_rc {
                rc_records += 1;
                if ident.get("python").eq_str(port::PLACEHOLDER) {
                    placeholders += 1;
                }
            } else if !ident.is_null() {
                misplaced += 1;
            }
        }
    }
    let count = out
        .windows(port::PLACEHOLDER.len())
        .filter(|w| *w == port::PLACEHOLDER.as_bytes())
        .count();
    t.check(
        "every Resume Check record has engine_identity.python as the placeholder",
        rc_records > 0 && placeholders == rc_records,
        &format!("{} of {}", placeholders, rc_records),
    );
    t.check("no governor record has engine_identity", misplaced == 0, "");
    t.check(
        "the placeholder text appears once per Resume Check record",
        count == rc_records,
        &format!("{}", count),
    );
    let mut sample = Json::obj(vec![(
        "engine_identity",
        Json::obj(vec![
            ("code_sha256", Json::Null),
            ("python", Json::s("3.12.1")),
        ]),
    )]);
    let mut gov_sample = sample.clone();
    port::placeholder(port::RC_FOLDER, &mut sample);
    port::placeholder(port::GOVERNOR_FOLDER, &mut gov_sample);
    t.check(
        "placeholder() replaces only engine_identity.python, only in the Resume Check folder",
        sample
            .get("engine_identity")
            .get("python")
            .eq_str(port::PLACEHOLDER)
            && sample.get("engine_identity").get("code_sha256").is_null()
            && gov_sample
                .get("engine_identity")
                .get("python")
                .eq_str("3.12.1"),
        "",
    );

    // 4. Each fail-closed input of AC1: the run gives no document (main then writes nothing and exits non-zero).
    let fails = |data: &[u8]| run_bytes(data).is_err();
    t.check("missing argument", port::run(&[], &reader).is_err(), "");
    t.check(
        "extra argument",
        port::run(&[args[0].clone(), args[0].clone()], &reader).is_err(),
        "",
    );
    t.check(
        "an argument that cannot be read",
        port::run(&["no-such-document".to_string()], &reader).is_err(),
        "",
    );
    t.check(
        "control: the canonical re-serialisation is accepted",
        run_bytes(&port::canonical_text(&fx)).ok() == Some(out.clone()),
        "",
    );
    t.check("not a fixture document: empty", fails(b""), "");
    t.check("not a fixture document: not JSON", fails(b"fixtures\n"), "");
    t.check("not a fixture document: a list", fails(b"[]\n"), "");
    t.check(
        "not a fixture document: an empty object",
        fails(b"{}\n"),
        "",
    );
    t.check(
        "not a fixture document: the reference document",
        fails(&reference),
        "",
    );
    let crlf: Vec<u8> = fixtures
        .iter()
        .flat_map(|&b| {
            if b == b'\n' {
                vec![b'\r', b'\n']
            } else {
                vec![b]
            }
        })
        .collect();
    t.check("not a fixture document: CR LF line ends", fails(&crlf), "");
    t.check(
        "not a fixture document: no final LF",
        fails(&fixtures[..fixtures.len() - 1]),
        "",
    );
    let mut bom = b"\xef\xbb\xbf".to_vec();
    bom.extend_from_slice(&fixtures);
    t.check("not a fixture document: a byte-order mark", fails(&bom), "");
    t.check(
        "not a fixture document: a fraction",
        fails(b"{\n  \"fixtures/a\": 1.5\n}\n"),
        "",
    );
    t.check(
        "not a fixture document: a repeated key",
        fails(b"{\n  \"a\": 1,\n  \"a\": 1\n}\n"),
        "",
    );
    let first_rc = keys(&fx)
        .into_iter()
        .find(|k| k.starts_with("fixtures_rc/"))
        .unwrap_or_default();
    let first_gov = keys(&fx)
        .into_iter()
        .find(|k| k.starts_with("fixtures/"))
        .unwrap_or_default();
    let mutated = |f: &dyn Fn(&mut Json)| {
        let mut v = fx.clone();
        f(&mut v);
        port::canonical_text(&v)
    };
    t.check(
        "not a fixture document: a Resume Check fixture missing",
        fails(&mutated(&|v| remove_key(v, &first_rc))),
        "",
    );
    t.check(
        "not a fixture document: a key of another folder",
        fails(&mutated(&|v| {
            if let Json::Obj(m) = v {
                let x = m.get(&first_gov).cloned().unwrap_or(Json::Null);
                m.insert("other/x".to_string(), x);
            }
        })),
        "",
    );
    t.check(
        "not a fixture document: a fixture with no cases",
        fails(&mutated(&|v| {
            *obj_mut(obj_mut(v, &first_gov), "cases") = Json::Arr(vec![])
        })),
        "",
    );
    t.check(
        "a case it cannot compute: a governor request with no task id",
        fails(&mutated(&|v| {
            remove_key(
                obj_mut(
                    idx_mut(obj_mut(obj_mut(v, &first_gov), "cases"), 0),
                    "request",
                ),
                "task_id",
            )
        })),
        "",
    );
    t.check(
        "a case it cannot compute: a governor case with no records",
        fails(&mutated(&|v| {
            remove_key(
                idx_mut(obj_mut(obj_mut(v, &first_gov), "cases"), 0),
                "records",
            )
        })),
        "",
    );
    t.check(
        "a case it cannot compute: a Resume Check case with no inputs",
        fails(&mutated(&|v| {
            remove_key(
                idx_mut(obj_mut(obj_mut(v, &first_rc), "cases"), 0),
                "inputs",
            )
        })),
        "",
    );
    // resume_check.check's "the check could not complete: <type>" (the brief's section 2): int() of a budget with more
    // digits than CPython converts raises ValueError inside the check, so the port fails closed.
    let long = format!("{}k", "1".repeat(port_digits() + 1));
    let budget = |v: &mut Json| {
        let inputs = obj_mut(
            idx_mut(obj_mut(obj_mut(v, &first_rc), "cases"), 0),
            "inputs",
        );
        let budgets = obj_mut(obj_mut(obj_mut(inputs, "contract"), "autonomy"), "budgets");
        if let Json::Obj(m) = budgets {
            m.insert("tokens".to_string(), Json::s(&long));
        }
        let uses = obj_mut(inputs, "budget_use");
        if let Json::Obj(m) = uses {
            m.insert(
                "tokens".to_string(),
                Json::obj(vec![
                    ("reported", Json::Bool(true)),
                    ("used", Json::s("1k")),
                ]),
            );
        }
    };
    t.check(
        "a case it cannot compute: the Resume Check cannot complete",
        fails(&mutated(&budget)),
        "",
    );
    let mut long_doc = fx.clone();
    budget(&mut long_doc);
    let inputs = long_doc
        .get(&first_rc)
        .get("cases")
        .as_arr()
        .map(|a| a[0].get("inputs").clone())
        .unwrap_or(Json::Null);
    t.check(
        "check() itself gives no record for that case",
        port::check(&inputs).is_err(),
        "",
    );
    let fine = format!("{}k", "1".repeat(port_digits()));
    let mut ok_inputs = inputs.clone();
    if let Json::Obj(m) = obj_mut(
        obj_mut(obj_mut(&mut ok_inputs, "contract"), "autonomy"),
        "budgets",
    ) {
        m.insert("tokens".to_string(), Json::s(&fine));
    }
    t.check(
        "control: the longest convertible budget still gives a record",
        port::check(&ok_inputs).is_ok(),
        "",
    );

    // 5. The record forms the governor reads: a few rules of check_record in their order.
    let rec = |pairs: Vec<(&str, Json)>| Json::obj(pairs);
    t.check(
        "check_record: not an object",
        port::check_record(&Json::Null) == vec!["6.2:record".to_string()],
        "",
    );
    let bad = rec(vec![("zzz", Json::Null), ("record_id", Json::s(""))]);
    let rules = port::check_record(&bad);
    t.check(
        "check_record: unknown key first, then the missing keys",
        rules.first().map(String::as_str) == Some("6.2:unknown_key")
            && rules.get(1).map(String::as_str) == Some("6.2:missing_key"),
        &format!("{:?}", rules),
    );

    println!("{} passed, {} failed", t.passed, t.failed);
    if t.failed > 0 {
        return Err(format!("{} checks failed", t.failed));
    }
    Ok(())
}

/// CPython's default limit on the digits of an integer converted from text.
fn port_digits() -> usize {
    4300
}

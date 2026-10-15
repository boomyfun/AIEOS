//! The fixture document read and the output document built, as test_export_reference.py builds the reference: for
//! each governor fixture `governor.evaluate(case['request'], case['inputs'], case['records'])`, for each Resume Check
//! fixture `resume_check.check(case['inputs'])` with the one placeholder applied, keyed "<folder>/<file stem>", in
//! the canonical text, ASCII with LF line ends.

use std::collections::BTreeMap;

use crate::json::{canon, canonical_text, parse, Json};
use crate::{governor, resume_check};

pub const GOVERNOR_FOLDER: &str = "fixtures";
pub const RC_FOLDER: &str = "fixtures_rc";
/// The Risk Engine's folder is in the fixture document but not in round 1 (the brief's section 2): it is passed over.
pub const RISK_FOLDER: &str = "fixtures_risk";
/// The brief's section 2: 19 governor fixtures and 11 Resume Check fixtures.
pub const GOVERNOR_COUNT: usize = 19;
pub const RC_COUNT: usize = 11;

/// The fixture document's value, or why the bytes are not a fixture document: canonical JSON text (as
/// conformance.unwrap requires of each fixture), one object whose keys are "<folder>/<file stem>" of the three
/// folders, each value an object with a non-empty list of cases, 19 governor keys and 11 Resume Check keys.
pub fn read_fixture_document(data: &[u8]) -> Result<Json, String> {
    let value = parse(data).map_err(|e| format!("not a fixture document: {}", e))?;
    let mut text = canon(&value);
    text.push('\n');
    if text.as_bytes() != data {
        return Err("not a fixture document: the text is not in the canonical form".to_string());
    }
    let m = value
        .as_obj()
        .ok_or_else(|| "not a fixture document: not one object".to_string())?;
    let (mut governor_keys, mut rc_keys) = (0usize, 0usize);
    for (key, fixture) in m {
        let (folder, stem) = key
            .split_once('/')
            .ok_or_else(|| format!("not a fixture document: the key {} names no folder", key))?;
        if stem.is_empty() || stem.contains('/') {
            return Err(format!(
                "not a fixture document: the key {} names no file stem",
                key
            ));
        }
        match folder {
            GOVERNOR_FOLDER => governor_keys += 1,
            RC_FOLDER => rc_keys += 1,
            RISK_FOLDER => {}
            _ => {
                return Err(format!(
                    "not a fixture document: the key {} names another folder",
                    key
                ))
            }
        }
        if !fixture.get("cases").as_arr().is_some_and(|c| !c.is_empty()) {
            return Err(format!("not a fixture document: {}: no cases", key));
        }
    }
    if governor_keys != GOVERNOR_COUNT || rc_keys != RC_COUNT {
        return Err(format!(
            "not a fixture document: {} governor and {} Resume Check fixtures, not {} and {}",
            governor_keys, rc_keys, GOVERNOR_COUNT, RC_COUNT
        ));
    }
    Ok(value)
}

/// `case[key]` as the Python reads it: the case must be an object holding the key (KeyError or TypeError otherwise).
fn case_arg<'a>(case: &'a Json, key: &str, where_: &str) -> Result<&'a Json, String> {
    if case.has(key) {
        Ok(case.get(key))
    } else {
        Err(format!("{}: the case has no {}", where_, key))
    }
}

/// test_export_reference.placeholder: engine_identity.python of a Resume Check record becomes the placeholder text.
pub fn placeholder(folder: &str, record: &mut Json) {
    if folder != RC_FOLDER {
        return;
    }
    if let Json::Obj(m) = record {
        if let Some(Json::Obj(ident)) = m.get_mut("engine_identity") {
            if ident.contains_key("python") {
                ident.insert("python".to_string(), Json::s(resume_check::PLACEHOLDER));
            }
        }
    }
}

/// The records of one fixture's cases in case order.
pub fn case_records(key: &str, folder: &str, fixture: &Json) -> Result<Vec<Json>, String> {
    let mut out = Vec::new();
    for (n, case) in fixture
        .get("cases")
        .as_arr()
        .map(|a| a.as_slice())
        .unwrap_or(&[])
        .iter()
        .enumerate()
    {
        let where_ = format!("{}: case {}", key, n + 1);
        let mut rec = if folder == GOVERNOR_FOLDER {
            let request = case_arg(case, "request", &where_)?;
            let inputs = case_arg(case, "inputs", &where_)?;
            let records = case_arg(case, "records", &where_)?;
            governor::evaluate(request, inputs, records)
                .map_err(|e| format!("{}: {}", where_, e))?
        } else {
            let inputs = case_arg(case, "inputs", &where_)?;
            resume_check::check(inputs).map_err(|e| format!("{}: {}", where_, e))?
        };
        placeholder(folder, &mut rec);
        out.push(rec);
    }
    Ok(out)
}

/// The output document's bytes for the fixture document's bytes, or why it cannot be built (nothing is printed then).
pub fn document(data: &[u8]) -> Result<Vec<u8>, String> {
    let value = read_fixture_document(data)?;
    let mut obj: BTreeMap<String, Json> = BTreeMap::new();
    for (key, fixture) in value.as_obj().into_iter().flatten() {
        let folder = key.split_once('/').map(|(f, _)| f).unwrap_or_default();
        if folder != GOVERNOR_FOLDER && folder != RC_FOLDER {
            continue;
        }
        obj.insert(key.clone(), Json::Arr(case_records(key, folder, fixture)?));
    }
    let out = canonical_text(&Json::Obj(obj));
    if out.iter().any(|&b| b == b'\r' || b > 127) {
        return Err("the document is not ASCII with LF line ends".to_string());
    }
    Ok(out)
}

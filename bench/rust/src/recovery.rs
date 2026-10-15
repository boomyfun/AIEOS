//! recovery.py's `reconcile` (TASK-009): the log against the commits read from Git, the leases held and the recovery
//! time, as a `RecoveryResult`; every event is built by `eventlog::append`, one at a time. It reads and writes
//! nothing.

use std::collections::HashSet;

use crate::eventlog::{append, Event, Lease, Time, LEASE_KEYS};
use crate::json::Int;
use crate::pyval::{dumps, py_eq, repr_str, V};
use crate::records2::{check_log, digits, R};
use crate::sha256;

pub const TASK_KEY: &str = "AIEOS-Task";
pub const FENCE_KEY: &str = "AIEOS-Fence";
const ID_PREFIX: &str = "recovery";

/// The result of one recovery: the log after every appended event, the events built ({event_id, type, task_id,
/// result}), the given leases whose expiry has passed (in the given order) and the findings.
#[derive(Clone, Debug)]
pub struct RecoveryResult {
    pub log: Vec<u8>,
    pub events: Vec<V>,
    pub expired: Vec<Lease>,
    pub findings: Vec<String>,
}

/// `_id`: the SHA-256 hex digest of "recovery", the commit id and the kind, joined by LF.
pub fn id(commit: &str, kind: &str) -> String {
    sha256::hex(format!("{}\n{}\n{}", ID_PREFIX, commit, kind).as_bytes())
}

/// The trailer read from a commit message: the task id and the fence {epoch, counter}, each None when absent.
#[derive(Clone, Debug)]
pub struct Trailer {
    pub task: Option<String>,
    pub fence: Option<V>,
}

/// Python's whitespace among ASCII characters (`str.isspace`).
fn py_space(c: char) -> bool {
    matches!(
        c,
        ' ' | '\t' | '\n' | '\u{b}' | '\u{c}' | '\r' | '\u{1c}' | '\u{1d}' | '\u{1e}' | '\u{1f}'
    )
}

/// Python's `text.strip()` (the message is ASCII, checked by the caller).
fn py_strip(s: &str) -> &str {
    s.trim_matches(py_space)
}

/// `re.split(r'\n[ \t]*\n', text)`.
fn split_paragraphs(s: &str) -> Vec<&str> {
    let b = s.as_bytes();
    let mut out = Vec::new();
    let mut start = 0;
    let mut i = 0;
    while i < b.len() {
        if b[i] == b'\n' {
            let mut j = i + 1;
            while j < b.len() && (b[j] == b' ' || b[j] == b'\t') {
                j += 1;
            }
            if j < b.len() && b[j] == b'\n' {
                out.push(&s[start..i]);
                start = j + 1;
                i = j + 1;
                continue;
            }
        }
        i += 1;
    }
    out.push(&s[start..]);
    out
}

/// The canonical spelling of a trailer key named in any letter case, if it is one of the two.
fn known_key(name: &str) -> Option<&'static str> {
    match name.to_ascii_lowercase().as_str() {
        "aieos-task" => Some(TASK_KEY),
        "aieos-fence" => Some(FENCE_KEY),
        _ => None,
    }
}

/// `trailers(message)`: the AIEOS-Task and AIEOS-Fence values of the message's last paragraph, and the findings.
pub fn trailers(message: &str) -> R<(Trailer, Vec<String>)> {
    if !message.is_ascii() {
        return Err(
            "a commit message outside ASCII (Python's whitespace and letter case not computed)"
                .to_string(),
        );
    }
    let paragraphs: Vec<&str> = split_paragraphs(message.trim_matches('\n'))
        .into_iter()
        .filter(|p| !py_strip(p).is_empty())
        .collect();
    let last: Vec<&str> = match paragraphs.last() {
        Some(p) => p.split('\n').collect(),
        None => Vec::new(),
    };
    let mut found_task: Vec<String> = Vec::new();
    let mut found_fence: Vec<String> = Vec::new();
    let mut findings = Vec::new();
    if paragraphs.len() > 1 {
        for paragraph in &paragraphs[..paragraphs.len() - 1] {
            for line in paragraph.split('\n') {
                if let Some((key, _)) = line.split_once(':') {
                    let name = py_strip(key);
                    if known_key(name).is_some() {
                        findings.push(format!(
                            "trailer: {} is named outside the last paragraph",
                            repr_str(name)?
                        ));
                    }
                }
            }
        }
    }
    for line in last {
        let (key, value) = match line.split_once(':') {
            Some(kv) => kv,
            None => continue,
        };
        let name = py_strip(key);
        let canonical = match known_key(name) {
            Some(c) => c,
            None => continue,
        };
        if name != canonical {
            findings.push(format!(
                "trailer: {} is not spelled {}",
                repr_str(name)?,
                repr_str(canonical)?
            ));
            continue;
        }
        if key != name {
            findings.push(format!(
                "trailer: {} is not at the start of its line",
                repr_str(name)?
            ));
        }
        let v = py_strip(value).to_string();
        if canonical == TASK_KEY {
            found_task.push(v);
        } else {
            found_fence.push(v);
        }
    }
    let mut trailer = Trailer {
        task: None,
        fence: None,
    };
    for (key, found) in [(TASK_KEY, &found_task), (FENCE_KEY, &found_fence)] {
        if found.len() > 1 {
            findings.push(format!("trailer: {} is given {} times", key, found.len()));
        }
    }
    if let [task] = found_task.as_slice() {
        if task.strip_prefix("TASK-").is_some_and(digits) {
            trailer.task = Some(task.clone());
        } else {
            findings.push(format!(
                "trailer: {} {} is not TASK- followed by digits",
                TASK_KEY,
                repr_str(task)?
            ));
        }
    }
    if let [fence] = found_fence.as_slice() {
        match fence.rsplit_once(':') {
            Some((epoch, counter)) if !epoch.is_empty() && digits(counter) => {
                let n = Int::from_digits(false, counter.as_bytes())
                    .ok_or_else(|| "a fence counter too long for Python's int()".to_string())?;
                trailer.fence = Some(V::obj(vec![("epoch", V::s(epoch)), ("counter", V::Int(n))]));
            }
            _ => findings.push(format!(
                "trailer: {} {} is not <epoch>:<counter>",
                FENCE_KEY,
                repr_str(fence)?
            )),
        }
    }
    Ok((trailer, findings))
}

/// `_check_arguments` (the log is bytes by construction): a failure is Python's ValueError or TypeError, so the
/// port fails closed.
fn check_arguments(commits: &V, leases: &[Lease], recorder: &V) -> R<()> {
    let list = commits
        .as_arr()
        .ok_or_else(|| "the commits are not given as a list".to_string())?;
    for c in list {
        if !c.keys_are(&["commit", "message"]) {
            return Err("a commit is not a mapping with exactly commit and message".to_string());
        }
        let ok = matches!(c.get("commit").as_str(), Some(s) if s.len() == 40
            && s.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b)));
        if !ok {
            return Err("a commit id is not 40 lowercase hex digits".to_string());
        }
        if !c.get("message").is_str() {
            return Err("a commit message is not a string".to_string());
        }
    }
    for lease in leases {
        if !lease.value.keys_are(&LEASE_KEYS) {
            return Err(
                "a lease is not a mapping with exactly task_id, fencing_token and expires_at"
                    .to_string(),
            );
        }
    }
    if !recorder.is_text() {
        return Err("the recorder is not a non-empty string".to_string());
    }
    Ok(())
}

/// `observation`: the payload of the record.added event of an unfenced write.
pub fn observation(commit: &str, task_id: &str, recorder: &V) -> V {
    V::obj(vec![
        ("record_id", V::s(&id(commit, "unfenced_write"))),
        ("fact_kind", V::s("observation")),
        ("source_class", V::s("deterministic_tool_local")),
        ("recorder", recorder.clone()),
        ("subject", V::s(task_id)),
        ("evidence_type", V::s("unfenced_write")),
        ("outcome", V::s("fail")),
        ("refers_to", V::s(commit)),
    ])
}

/// One submission of the log: (commit, task_id, token text).
type Submission = (String, String, String);

/// `_submissions`: the task.submitted events of a log free of findings, each first line.
fn submissions(log: &[u8]) -> R<Vec<Submission>> {
    let mut out = Vec::new();
    for line in check_log(log)?.lines {
        let e = match (&line.event, line.duplicate_of) {
            (Some(e), None) => e,
            _ => continue,
        };
        if !e.get("type").eq_str("task.submitted") {
            continue;
        }
        let commit = e.get("payload").get("commit").as_str();
        let task_id = e.get("task_id").as_str();
        match (commit, task_id) {
            (Some(c), Some(t)) => {
                out.push((c.to_string(), t.to_string(), dumps(e.get("fencing_token"))))
            }
            _ => {
                return Err(
                    "a submission of a log without findings lacks its commit or task".to_string(),
                )
            }
        }
    }
    Ok(out)
}

struct Steps<'a> {
    log: Vec<u8>,
    events: Vec<V>,
    findings: Vec<String>,
    now: Time,
    recorder: &'a V,
}

impl Steps<'_> {
    /// The inner `add`: one event by eventlog.append; false when it is refused.
    fn add(
        &mut self,
        event_type: &str,
        payload: V,
        event_id: &str,
        task_id: &str,
        fencing_token: &V,
        lease: Option<&Lease>,
    ) -> R<bool> {
        let et = V::s(event_type);
        let eid = V::s(event_id);
        let tid = V::s(task_id);
        let rid = V::s(&id(event_id, "refused_submission"));
        let r = append(
            &self.log,
            &Event {
                event_type: &et,
                payload: &payload,
                event_id: &eid,
                appended_at: self.now,
                task_id: &tid,
                fencing_token,
                corrects: &V::Null,
                lease,
                recorder: self.recorder,
                record_id: &rid,
            },
        )?;
        if r.result == "refused" {
            self.findings.push(format!(
                "step 1: eventlog.append refused the {} of {} (reason {}): {}",
                event_type,
                task_id,
                r.reason.unwrap_or("None"),
                r.findings.join("; ")
            ));
            return Ok(false);
        }
        if let Some(new_log) = r.log {
            self.log = new_log;
        }
        self.events.push(V::obj(vec![
            ("event_id", eid),
            ("type", et),
            ("task_id", tid),
            ("result", V::s(r.result)),
        ]));
        Ok(true)
    }
}

/// `recovery.reconcile(log, commits, leases, now, recorder)`. An `Err` is a case the port cannot compute.
pub fn reconcile(
    log: &[u8],
    commits: &V,
    leases: &[Lease],
    now: Time,
    recorder: &V,
) -> R<RecoveryResult> {
    check_arguments(commits, leases, recorder)?;
    let expired: Vec<Lease> = leases
        .iter()
        .filter(|l| l.expires_at <= now)
        .cloned()
        .collect();
    let report = check_log(log)?;
    let mut damaged = report.findings();
    if !log.is_empty() && !log.ends_with(b"\n") {
        damaged.push("2:lf: the log does not end with LF".to_string());
    }
    if !damaged.is_empty() {
        return Ok(RecoveryResult {
            log: log.to_vec(),
            events: Vec::new(),
            expired,
            findings: damaged.iter().map(|f| format!("log: {}", f)).collect(),
        });
    }
    let commits = commits.as_arr().unwrap_or(&[]);
    let mut steps = Steps {
        log: log.to_vec(),
        events: Vec::new(),
        findings: Vec::new(),
        now,
        recorder,
    };
    let given: HashSet<&str> = commits
        .iter()
        .filter_map(|c| c.get("commit").as_str())
        .collect();
    let submitted = submissions(log)?;
    // Step 2: Git wins; a submission naming a commit that is not given is reported, nothing is appended.
    for (commit, task_id, _) in &submitted {
        if !given.contains(commit.as_str()) {
            steps.findings.push(format!(
                "step 2: the log's task.submitted of {} names the commit {}, which is not among the given commits; \
                 nothing is appended",
                task_id, commit
            ));
        }
    }
    let mut named: HashSet<String> = submitted.iter().map(|(c, _, _)| c.clone()).collect();
    let mut used: HashSet<(String, String)> = submitted
        .iter()
        .map(|(_, t, k)| (t.clone(), k.clone()))
        .collect();

    // Step 1, oldest first.
    for c in commits {
        let commit = c.get("commit").as_str().unwrap_or_default();
        let message = c.get("message").as_str().unwrap_or_default();
        let (trailer, bad) = trailers(message)?;
        if !bad.is_empty() {
            for f in bad {
                steps.findings.push(format!("commit {}: {}", commit, f));
            }
            continue;
        }
        let task_id = match &trailer.task {
            Some(t) if !named.contains(commit) => t.clone(),
            _ => continue,
        };
        let token = trailer.fence.as_ref().map(dumps);
        let mut lease: Option<&Lease> = None;
        if let Some(tok) = &token {
            if !used.contains(&(task_id.clone(), tok.clone())) {
                let want = V::s(&task_id);
                lease = leases.iter().find(|held| {
                    py_eq(held.value.get("task_id"), &want)
                        && dumps(held.value.get("fencing_token")) == *tok
                        && held.expires_at > now
                });
            }
        }
        match (lease, &trailer.fence, &token) {
            (Some(held), Some(fence), Some(tok)) => {
                let payload = V::obj(vec![
                    ("commit", V::s(commit)),
                    ("compensating", V::Bool(true)),
                ]);
                let event_id = id(commit, "task.submitted");
                if steps.add(
                    "task.submitted",
                    payload,
                    &event_id,
                    &task_id,
                    fence,
                    Some(held),
                )? {
                    used.insert((task_id.clone(), tok.clone()));
                    named.insert(commit.to_string());
                }
            }
            _ => {
                let payload = observation(commit, &task_id, recorder);
                let event_id = id(commit, "record.added");
                steps.add("record.added", payload, &event_id, &task_id, &V::Null, None)?;
            }
        }
    }
    Ok(RecoveryResult {
        log: steps.log,
        events: steps.events,
        expired,
        findings: steps.findings,
    })
}

# DEF-0101: the launcher's open requirements before a runtime is launched

- Status: open
- Opened: 2026-10-24 (session 3797498a; TASK-086's contract, decisions D-2673, D-2681)
- Deferred by: decision agent (A41, A51), D-2681 Q1 and Q3 (TASK-086's launcher writes no observed read-set record
  and leaves max_risk to its caller; these requirements are carried here).
- Decision group: A (later M7 tasks within the self-build; launching with a runtime stays the owner's, DM A51 item (4)).

## What
TASK-086's launcher (src/aieos_bootstrap/launcher.py) runs the core's expiry, the Resume Check and the grant over
adapter.start and adapter.end, and starts no runtime. Before a runtime is launched with it, these stay open:
- closed: the observed read-set record before every lease release (specification 7 :45, specification 5 :112;
  read_set_record.py :19-24) at its three call places: the normal end and the gone session's record at the end after
  a violation or an expiry are written by TASK-089's launcher.end, with the stored reads' removal; the third, the gone
  session's record at the next start (specification 5 :125), with its listing of gone sessions through
  writer.read_sessions, is written by TASK-090's launcher.start before the expiry (decision D-2956);
- closed: the check that HEAD is the base branch's tip: launcher.start's step "base" (TASK-106, decision D-3970) reads
  refs/heads/<base> (the base is "main" unless a caller passes another; `aieos launch` passes none) once, after the head
  and before the log, and does not grant unless HEAD is that tip; AIEOS_BASE is the head_commit read once, found equal to
  the tip at that read (the race, the local ref only and the strict name rule are stated in launcher.py's docstrings);
- closed: check 0 of the contract (specification 5 :121; specification 7 :49) is made by the Resume Check at every
  start (resume_check.py :529-:530), not by the launcher's hook; TASK-106's composed-path test in
  tests/integration/test_launcher_repo.py shows it on the real adapter.start and the real Resume Check;
- open: the check that the project's root is untouched before a launch (specification 5 :121); no task has been decided
  for it;
- launching with a runtime, the owner's act, is not before this item's open points are closed: the untouched-root check
  and max_risk; this is a statement, not a lock;
- max_risk is the caller's: a caller passing a non-null max_risk declares the runtime's tier, which only the owner's
  measurement can back (C6, P-LOC); the self-build passes null until then, so the launcher never grants (decision
  D-2673 ruling 2);
- closed: a stand-in start giving a non-list truthy findings value would raise past the launcher's step guard; end's
  own findings handling was fixed in TASK-089, and start's two places by TASK-090, which keep only a list's or a
  tuple's str items (DEF-0102, decision D-2956).

## Why deferred
D-2681 Q1: the three record call places and the stored reads' removal were planned as one task after TASK-086, split
by decision D-2771 into TASK-089 (end's two call places and the removal) and TASK-090 (the next start's record); Q3:
max_risk stays the caller's until a tier is measured.

## Resume when
The record's three call places are closed by TASK-089 and TASK-090 (decisions D-2876, D-2956); this item closes when
the untouched-root check is met or moved by its own decision (the base-tip check and check 0 were closed by TASK-106);
max_risk stays the caller's, as its bullet states.

## Depends on
TASK-086 (the launcher), TASK-089 (end's record and the stored reads' removal), TASK-064 (read_set_record, the
record's core side; read_set_record.py :1), TASK-066 to TASK-068 (the read hook that writes the reads; DEF-0097 :14),
TASK-051 (adapter); specification 5 section 11 points 7 and 10, specification 7 section 5.

## Log
- 2026-10-24: opened with TASK-086's records (session 3797498a; decisions D-2681, D-2758).
- 2026-10-25: TASK-089 accepted (decision D-2876): end writes the record at two of the three call places and removes
  the stored reads; the next start's record and the launch line now name TASK-090 (session 3797498a; decisions D-2771,
  D-2876).
- 2026-10-25: TASK-090 accepted (decision D-2956): start writes the gone sessions' records at the next start and
  removes their stored reads; start's findings handling closed; the launch line now names the base-tip check, check 0
  and max_risk (session ea6ea0a3; decisions D-2910, D-2953, D-2956).
- 2026-10-25: TASK-094 accepted (decision D-3178): launcher.launch_outside composes one launch from outside the runtime
  (start with max_risk None and a lease of two hours, the contract's write set at the grant's head, the caller's
  starter, the end in every case after a grant, the handoff after a done end), and the shipped command `aieos launch`
  passes no starter and refuses "no runtime starter"; open for the task that adds a real starter, which stays the
  owner's and is asked separately: gitread's pinned list or another wrapper, the workflow's pattern rule, INV-001's
  question whether an allowed executable runs a model, the lease length and its renewal, and a finish refused
  "stored_reads", which launch_outside leaves to `aieos end` or the lease's expiry with no end_outside call (session
  ea6ea0a3; decisions D-3154, D-3164, D-3172, D-3178).
- 2026-10-29: M7 exited (`docs/plan/m7-exit-review.md`): the base-tip check, check 0 and max_risk stay open before any runtime launch (session ea6ea0a3).
- 2026-10-31: TASK-106 accepted (decision D-3970): launcher.start gains the step "base" (the base-tip check) and the
  keyword base; gitread's rev-parse takes refs/heads/<base> as a third name form; check 0 is closed for the launcher by
  the Resume Check at every start, shown by a composed-path test; the untouched-root check stays open, and so does
  max_risk; `aieos launch` now refuses unless HEAD is the tip of the local refs/heads/main (session 85a45f06; decisions
  D-3918, D-3919, D-3927, D-3938, D-3970).

# DEF-0072: ADV-02's route to a conformance run

- Status: open
- Opened: 2026-10-16 (decision D-1056)
- Deferred by: decision agent (A41), D-1056 (ADV-02's route approved as the scope; its drafting carried to the next session).
- Decision group: A (a specification section and tasks within M5's approved plan).

## What
- **ADV-02** (Capability Boundaries; `docs/pre-genesis/conformance-scenarios-initial.md` line 64) is NOT_RUN: its set entry has no fixture, and the runner's expected path is None for Capability Boundaries (src/aieos_bootstrap/conformance.py, expected_path), so it is "the entry point … is absent until its milestone". Specification 5 section 8 (line 81) plans a replay route: the fixture is written in the replay adapter's form, so ADV-02 can run in conformance without a live runtime; a passing ADV-02 then shows only the core's handling of a recorded observation, not that any hook observes anything.
- **The route, in RISK-01's three steps (D-429; DEF-0042):**
  1. Done: `docs/specs/conformance-files.md` revision 10, section 11 "The Capability Boundaries fixture and entry", approved as DM F48 and on main as 2049aeec (D-1063 to D-1066). It settles the open point of D-1056 Q2: after STOP: violation, a second session on the same in-memory log submits the change through the adapter's own calls (adapter.start, adapter.submit, adapter.end), then evaluation.evaluate_task runs; expected from the Expected cell only: STOP: violation, REJECT and REJECTED, the metrics not fixed.
  2. In progress: TASK-056, the runner's Capability Boundaries entry (an evaluator change, critical_cr), with tests in both states; its contract on main as commit C 274d971e (D-1067 to D-1069); the owner was told before any code; the code is next.
  3. A task: ADV-02's fixture and the set file's entry, the set file frozen before the task (conformance-files.md section 7, revision 5), possibly split as D-459 split RISK-01's step 3; test_conformance_files.py's guard that the set file names no ADV-02 fixture is that task's to change.
- Rejected: a fixture in section 4's form (the When given, not run; it duplicates the governor's row 1) and deferring until a measured T3 runtime exists.
- Owner-kept acts: none; the T3 tier and C6 stay the owner's to measure.

## Resume when
- At the next session's start, after the decision files D-1061 onward: TASK-056's code per its contract.

## Log
- 2026-10-16: opened (D-1056).
- 2026-10-17: step 1 done (revision 10 approved as DM F48, on main as 2049aeec; D-1063 to D-1066); step 2's contract, TASK-056, on main as commit C 274d971e (D-1067 to D-1069).

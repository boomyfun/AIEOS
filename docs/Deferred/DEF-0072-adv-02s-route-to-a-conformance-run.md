# DEF-0072: ADV-02's route to a conformance run

- Status: open
- Opened: 2026-10-16 (decision D-1056)
- Deferred by: decision agent (A41), D-1056 (ADV-02's route approved as the scope; its drafting carried to the next session).
- Decision group: A (a specification section and tasks within M5's approved plan).

## What
- **ADV-02** (Capability Boundaries; `docs/pre-genesis/conformance-scenarios-initial.md` line 64) is NOT_RUN: its set entry has no fixture, and the runner's expected path is None for Capability Boundaries (src/aieos_bootstrap/conformance.py, expected_path), so it is "the entry point … is absent until its milestone". Specification 5 section 8 (line 81) plans a replay route: the fixture is written in the replay adapter's form, so ADV-02 can run in conformance without a live runtime; a passing ADV-02 then shows only the core's handling of a recorded observation, not that any hook observes anything.
- **The route, in RISK-01's three steps (D-429; DEF-0042):**
  1. `docs/specs/conformance-files.md` revision 10, a section "The Capability Boundaries fixture and entry", a specification text approved under A51 as a DM section F row: the folder tests/conformance/fixtures_cb/ (adv_02.py); a case of a replay document in replay.py's form with the violation key, the setup events, a commit table and the evaluation's values; the entry: replay.replay with in-memory stand-ins for the writer, then evaluation.evaluate_task over that log, both from the base; expected from the Expected cell only: STOP: violation (violation.detected and its decision appended, the lease released) and REJECT with next state REJECTED; "recorded in the runtime's and the agent's metrics" in not_fixed (metrics come from the event log from M8; Master Plan section 7), the violation.detected record being the only observable trace; not covered, stated: replayed records are deterministic_tool_local, the T3 tier and C6 unmeasured (the owner's).
  2. A task: the runner's Capability Boundaries entry (an evaluator change, critical_cr), with tests in both states.
  3. A task: ADV-02's fixture and the set file's entry, the set file frozen before the task (conformance-files.md section 7, revision 5), possibly split as D-459 split RISK-01's step 3.
- **The open point the draft must settle (D-1056 Q2):** after STOP: violation no task.* event follows, so the task stays READY with no lease (TASK-053 AC7's limit) and evaluation refuses outside VERIFYING or IN_REVIEW with reason "state". The draft must say how the fixture reaches an evaluable state (a submission in setup before the replayed session, or a second replay document), matching "the change is rejected" through the real path and adding no step the core does not have.
- Rejected: a fixture in section 4's form (the When given, not run; it duplicates the governor's row 1) and deferring until a measured T3 runtime exists.
- Owner-kept acts: none; the T3 tier and C6 stay the owner's to measure.

## Resume when
- At the next session's start, after the decision files D-1043 onward: conformance files revision 10's draft.

## Log
- 2026-10-16: opened (D-1056).

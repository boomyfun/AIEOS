# DEF-0030: The event log's file writer, the local store, and the workflow's revision 6

- Status: open
- Opened: 2026-10-10 (decision files D-313 and D-315)
- Deferred by: decision agent (A41), D-313 Q4 and C5: TASK-007 takes shape (P), a pure module that returns the bytes to append and opens no file, because the CI workflow's deterministic_rule step refuses any file write in src/ and tests/ and any string in src/ that names the project-state directory ("no core writer exists yet").
- Decision group: A for the later task's contents; B for the workflow's revision 6 (the owner's act: A61; constitution SEC-003).

## What
- The single file writer of the event log (constitution INV-004: "inside the core only the single writer's module opens files in the directory for writing"; spec 1 §4; spec 2 §3 and §6), its tests, and the local store of leases and sessions (spec 1 §5.2 and §8; spec 2 §3, SQLite), which TASK-007's AC6 takes as a lease the caller gives.
- The workflow's revision 6, put to the owner as one question: an exemption of the deterministic_rule step for exactly that writer module (and what its tests need), together with setting the Resume Check pin AIEOS_PINNED_RESUME_CHECK once the Resume Check is accepted and the set file names its fixtures (TASK-005b), as revision 5's header and the owner question of D-313 say.
- TASK-008 (the Resume Check reads Git) and TASK-009 (recovery between Git and the event log) meet the same rules (no process, no file write); they take the same pure shape unless a later decision says otherwise (D-313 C5).

## Why deferred
An exemption designed before the contract of the code that needs it would be designed blind, and revision 6 is needed anyway for the pin, so the owner is asked once for both (D-313).

## Resume when
After TASK-008 is accepted and TASK-005b has added the set file's Resume Check entries, or earlier if an M3 task needs the writer; before M3 exits (Master Plan §4 M3: "the core's single writer").

## Depends on
TASK-007 (the append rules), TASK-008, TASK-005b; DEF-0024 (the workflow's other carried points).

## Log
- 2026-10-10: opened (decision files D-313 and D-315). ../History/2026-10/2026-10-10-0735-decision-files-d303-d310-ci-revision-5-and-task-007-contract.md
- 2026-10-10 (session 72b399d0): TASK-007 (the append rules, shape (P)) accepted and on `main` (9803593c; D-328, D-329). The writer task must also resolve DEF-0032's F-a and F-b (two departures of TASK-007 from its contract's literal text) by or before its acceptance.
- 2026-10-11 (session 2fb2ae0f): scope ruled (decision file D-401): the writer and the local store are one task, TASK-016, in one module, src/aieos_bootstrap/writer.py; next session, its contract first (approved, not yet committed), then the CI workflow's revision 7, the deterministic_rule exemption for exactly that module and its tests, sized to the contract, each allowance justified (the attribute `.open` argued for or against), the decision agent's own `.github/` decision under DM A66 and named as a loosening of a check (anything granting write permission, secrets, tokens or settings goes to the owner), then the contract's commit, then the code. The contract states: the time and, for tests, the epoch given as arguments; no repair of a damaged last line; no lock beyond SQLite's transaction; the caller runs the Resume Check before a grant; no `.gitignore` change (spec 2's "listed as ignored by Git" carried to the task that first creates a real `.aieos/`); every departure from proposed text openly (D-401 C2, C3). F-a and F-b resolved by TASK-015 (D-405). Its writer gives recorder and record_id on every lease-needing append and records every refusal, since append now returns a fence refusal with no record when they are missing (D-405, disposition (h)). ../History/2026-10/2026-10-11-0121-decision-files-d388-d398-and-task-015.md
- 2026-10-11 (session 22aadea0): the writer and the local store done: TASK-016 accepted and on `main` (decision file D-414; 32d9a7d4), with the CI workflow's revision 7, the deterministic_rule exemption for exactly writer.py and its three test modules (D-411). Still carried: spec 2's "listed as ignored by Git" for `.aieos/local/`, to the task that first creates a real project-state directory; a requirement on the contract of the first task that calls the store: never give an earlier store's epoch to a recreated store (D-414; DEF-0041 (c)); and, from M3's exit, no core caller yet applies the execution decision's state effect through the writer or grants a lease on CONTINUE (specification 3 section 10), to resume when a milestone first runs a task through the core and before AIEOS governs its own build (D-415 C3). ../History/2026-10/2026-10-11-0220-decision-files-d399-d408-the-writer-and-m3-exit.md

# DEF-0029: TASK-006's review findings and the Resume Check entry's limit, carried to later tasks

- Status: open
- Opened: 2026-10-10 (decision files D-307 and D-308)
- Deferred by: decision agent (A41), D-307 C3: none of the findings is blocking, and a fix is a new commit that makes the five reviews and the CI run stale (assurance-model.md line 39; D-278 C1).
- Decision group: A (test and wording changes in a later task touching the runner or its tests; notes to TASK-008 and TASK-005b).

## What
Non-blocking findings of TASK-006's five way-2 reviews on claude-sonnet-5-5 (commit 471f4e60be31275f7a15f5255b7aa1b56175c420), and one limit of the entry:
- **The limit (for TASK-008, first):** `records.check_decision` for `decision.execution` allows only the record keys, `decision` and `error`, so a real Resume Check that returns the full record of specification 3 section 9 is NOT_RUN under TASK-006's AC6 as written. TASK-008's contract (or a change to `records.py`) settles what the entry returns.
- **For a later task touching the runner's tests (test strength):** R5-1, no test pins the AC3 order of decision D-287 when two conditions fail at once (row hash and capability; path and capability), so a reordering of the checks would survive (two in-memory cases close it); R4-5 and R5-3, the INV-007 property test collects the paths read but does not assert on them; R4-4, the INV-005 membership assertion adds little beyond the returned-string case; R4-6, the one-byte property rests largely on the stand-in answering by exact inputs; R4-7, the integration test "the eleven frozen fixtures pass with a stand-in" shows the form check and the wiring, not that the fixtures are right; R5, a failed load with the file present is not pinned by a test.
- **For a later task touching the runner (wording and behaviour):** R4-1, the module docstring's "makes its scenarios NOT_RUN, never PASS" is too wide (a layout change that keeps the capability and the row hash still passes); R4-2, the reason "the capability differs from the bound scenario file" also covers "no capability readable"; R4-3, `run()`'s docstring on a null `resume_check` hash holds only when a Resume Check entry has a fixture; R3-1 and R5-4, the Resume Check module is imported even when a blocking problem already means the run cannot count.
- **For TASK-008 and TASK-005b:** R3-2 and R5-2, the AC8 integration test asserts that `src/aieos_bootstrap/resume_check.py` is absent and that exactly 13 scenarios are NOT_RUN; the task that adds the module, and the one that fills the set file's Resume Check entries, change it under their own contracts.
- Recorded only: R1-1 and R2-1 (the import runs the module's top level before the origin check, as for the governor: a guard on use, not on execution) are limits in the acceptance record; R3-3 and R3-4 are lines in DEF-0024.

## Why deferred
D-307 C3: none blocks the acceptance; the acceptance record (docs/records/TASK-006.jsonl, decision D-308) states the limits.

## Resume when
At TASK-008's contract, at TASK-005b's contract, and at the next task that changes the runner or its tests.

## Depends on
TASK-006 accepted (D-308) and on `main`.

## Log
- 2026-10-10: opened (decision files D-307 and D-308).
- 2026-10-10 (session 675f09ef): the limit for TASK-008 is settled by TASK-011's contract (records.check_decision allows specification 3 §9's keys for decision.execution; D-333, D-334), and TASK-008's contract changes the AC8 integration test's absence assertion under its own AC9 (R3-2, R5-2). Added (TASK-012's way-2 R5, D-342): R5CallAndComparison.test_each_not_run_rule compares only the reason string, which any check_decision finding gives, so it cannot tell an unknown-key finding from another; for a later task touching the runner's tests.

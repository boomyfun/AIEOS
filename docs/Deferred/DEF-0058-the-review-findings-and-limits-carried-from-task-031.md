# DEF-0058: the review findings and limits carried from TASK-031, the reconciliation caller

- Status: open
- Opened: 2026-10-14 (decision D-680)
- Deferred by: decision agent (A41), D-680 (the dispositions P1 to P15 of the five way-2 reviews; C4, the items carried) and D-681 (C3).
- Decision group: A (limits of the reconciliation caller within the self-build).

## What
- **P3, a rerun conflict** (reviewer R5, confirmed by a test): an evidence.stale event's id is derived from the task, the trigger and the reason only (TASK-023, stale.py). When a record is added to a DONE task after a reconciliation at a trigger, a rerun at the same trigger builds a new payload under the same id; the writer refuses it as a conflict, so that rerun, and every later rerun at that trigger, stops at that append, before drift's violation events. It fails closed and is named, and the next trigger derives new ids. Possible remedies, none promised: an id that covers the record list (a change to stale.py), or appending the violations before the stale events (a change to AC8's order).
- **P2, one task's stale error refuses the whole run** (R2, R4, R5): a DONE task whose id has four or more digits (stale.stale takes exactly three), or whose record.added payloads repeat a record_id, makes stale.stale give an error, and AC4 refuses the run with "stale", so drift and every other task go unchecked in that run. R2's alternative, a per-task uncovered entry, would change AC4.
- **P10, a repeated decision record id** (R2): among a task's decision.acceptance events with the same record_id the last one counts; R2's alternative, "ambiguous" as a fourth uncovered gap when the matches disagree on evaluated_commit, would change AC2.
- **P11, a mapped step absent from the steps given** (R2): rule_results_from_steps names a step the mapping does not name, but not a mapped step missing from the steps, so an article mapped from two steps with one absent reads from the other alone; the caller compares the mapping's step names with the steps it gives. Naming absent steps would change AC7.
- **P15, two test gaps** (R3): no test makes the uncovered list's de-duplication meet an actual duplicate, and none walks a history whose accepted commit is itself a merge (outside the base range by AC3's text; covered by the property test's ground truth that no merge follows a computed task's accepted commit).
- **P13, a reviewer input's wording** (R4, R5): the readings file given to the reviewers said a left-out task record is named "task_records[i]"; the code, the docstring and AC5 name it by its record_id when that is a non-empty string, and by the index otherwise. The file is outside the repository; recorded here and in the History.

## Why deferred
D-680 accepted the dispositions: each alternative changes the text of an approved criterion (AC2, AC4, AC7, AC8) or touches stale.py, which TASK-031 may not change; each case fails closed or is a stated limit in reconcile.py's docstring.

## Resume when
When a task changes stale.stale's event id or reconcile's order of appends, when the reconciliation caller is first run at a real base commit, or at the review point at M4's exit.

## Depends on
TASK-031 (accepted, decision D-681); TASK-023 (stale.py); DEF-0030; DEF-0057.

## Log
- 2026-10-14: opened (decisions D-680 and D-681; session 45777526).
- 2026-10-15 (session 218e5c55): M4 exited with named limits (decision D-756; docs/plan/m4-exit-review.md §3, after the owner chose Option C on 2026-10-15). Limit L-d: the reconciliation callers have not run at a real base commit; this item stays open until their first such run or a task that changes them.

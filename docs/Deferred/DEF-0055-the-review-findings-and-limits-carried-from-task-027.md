# DEF-0055: the review findings and limits carried from TASK-027, the evaluation path

- Status: open
- Opened: 2026-10-12 (decision D-639)
- Deferred by: decision agent (A41), D-639 (the dispositions P1 to P15 of the five way-2 reviews; P4, P6, P8 and P9 carried) and D-640 (C5).
- Decision group: A (limits of the evaluation path within the self-build).
- Blocks v0.1: no (a non-blocking review finding or limit of an accepted task)
- Scheduled in: M8, the verification-path fix task (ac_coverage, ac_tests, stale, drift, reconcile, execution, evaluation, verification_records, scope_reconcile), before the M8 exit review

## What
- **P4, the retries used** (reviewers R1 and R5): by erratum E1 to AC2 (decision D-636), a decision.acceptance that keeps the state sets nothing, so two REWORK decisions with no other state between them count once, where AC2 and specification 1 line 73 count every REWORK decision after the last approval. Reachable only through a log written outside this path (the module refuses evaluation in REWORK). To decide: whether E1 should say so, or the count follow the decisions.
- **P6, state transitions not checked** (R2, R5): the state is the last state-setting event's, so a log out of the state machine's order (for example a decision with next_task_state IN_REVIEW after one with REWORK and no new submission) is evaluated on the last submission's commit. Transition checks belong to a general state projection, a later task.
- **P8, the event id and the caller's data** (R2, R5): the event id covers the task, the state-setting event and the kept record ids, not declared or values; a rerun with other values gives "duplicate" with a decision computed, not stored.
- **P9, the first commit below the task** (R5): it is read by the same trailer rule, so a trailer finding there refuses every evaluation of the task (fail closed, as decision D-634 ruled).
- **Carried limits** (decisions D-633 C1, D-634 E1): declared (intent_versions and retries) and values are caller data, not bound to the hashed contract bytes; one evaluation of a task runs at a time; this repository's contracts write input_state.intent_versions as path to SHA-256, not specification 2's version form, so a caller maps them.

## Why deferred
Each is stated in evaluation.py's docstring; none is reachable through the core's own writer in v0.1's one-task-at-a-time use, and a fix needs a state projection, a caller that reads the contract, or a change of erratum E1, which are later work (D-639).

## Resume when
At the task that adds a state projection or the caller that reads contracts and the policy, or at the next task that changes src/aieos_bootstrap/evaluation.py.

## Depends on
DEF-0030 (the core's caller); TASK-027.

## Log
- 2026-10-12 (session 3e0b27e1): opened. TASK-027 accepted at ade6fda1 and on `main` (decision D-640; records 3a1acd31, D-641). ../History/2026-10/2026-10-12-0944-the-evaluation-path-accepted-and-on-main.md
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass A batch 2, decision D-5265): read in full; evaluation.py is unchanged since TASK-102 and a Grep of src finds no call site of evaluate_task( outside its definition (evaluation.py:341), so the event is not met; all of P4, P6, P8, P9 and the carried limits remain (the Log has only the opening). State: open; Blocks v0.1: no (a non-blocking review finding or limit of an accepted task); Scheduled in: M8, the verification-path fix task (ac_coverage, ac_tests, stale, drift, reconcile, execution, evaluation, verification_records, scope_reconcile), before the M8 exit review.
- 2026-11-12 (session 7d0b3852-d124-4653-b026-25d167d6f9c4; TASK-128 records, acceptance decisions D-5647 and D-5673): carried limit: the other values fields of evaluate_task stay caller data (D-633 C1); only owner_kept_act is bound to the contract bytes since TASK-128 (TASK-128.yaml:3, :5, :76).

# DEF-0068: TASK-053's carried reviews and acceptance (a violation makes acceptance reject)

- Status: open
- Opened: 2026-10-16 (decision D-1016)
- Deferred by: decision agent (A41), D-1016 Q4 (the bands: the reviews would cross the session's 80% line).
- Decision group: A (the order of work within an approved contract).

## What
- **TASK-053** (contract revision 1, commit C 12349ef7 on main, decisions D-1012 to D-1014; erratum E1 to AC2, D-1016): its first task commit c7295250 on task/TASK-053 (D-1016), aieos-checks run 329 passing every step (G0 "commits 1, paths 8, failures 0"; 1048 + 90 + 128 tests; bandit no issues). The decision agent read the code in full (D-1016).
- **Left:** five way-2 reviews at c7295250 on a model other than the main session's; their briefs name for R3 the four changed earlier tests (test_violation R8Purity, test_replay R9Purity, test_adapter R9Purity and R9OwnTests, the last a departure from AC6's list of three, D-1015 amendment 1) and E1 to AC2, and for all reading (a), the whole-log span, and its consequence M1; the decision agent's own review, the other half of the cross-model entry; the acceptance (change class critical_cr, the approval form ruled there, D-492's precedent) and the landing on main.
- **Carried wording point** (D-1016): evaluation.py's docstring item 8, "so a rerun gives "duplicate" (AC9)", from TASK-027, cannot hold after a REJECT (the task is then REJECTED and not evaluated); for a later task that touches evaluation.py.
- **Limits** (the contract's AC7): the whole-log span (a violation of the task makes every later evaluation of it reject, also after a new approval); the task stays READY with no lease until an evaluation runs; no bound on repeated stops; the refused_submission label; F-a; no hook observed; no conformance set or fixture changed (ADV-02's fixture is a later task); no observed read-set call; the real writer's files not tested.

## Resume when
- At the next session's start, after the decision files D-1006 onward.

## Log
- 2026-10-16: opened (D-1016).

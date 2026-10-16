# DEF-0069: the findings and limits carried from TASK-053, and TASK-054's code

- Status: open
- Opened: 2026-10-16 (decisions D-1025, D-1028 amendment 1)
- Deferred by: decision agent (A41), D-1025 (TASK-053's acceptance) and D-1027 amendment 1 (TASK-054's code carried to the next session).
- Decision group: A (limits of an accepted task; the order of work within an approved contract).

## What
- **TASK-054** (a blocking record that the evaluation would leave out refuses the evaluation; contract revision 1, commit C 46554bde on main, decisions D-1027 and D-1028 with E1 and E2; run 334 passing): its code is not started. Left: the owner notice before any code (owner item 5), the code in the six write-set paths, the local compiled suite and the scans, the first task commit to task/TASK-054, five way-2 reviews on a model other than the main session's, the decision agent's own review, the acceptance (change class critical_cr; the approval form ruled there, D-492's precedent) and the landing on main.
- **D1, the fail-closed change TASK-054 makes:** at TASK-053's head, `_kept` leaves out a record whose record_id an earlier kept record has (records.py does not check record_id uniqueness across a log), so a violation.detected that reuses the id of an earlier passing record of the task never reaches the governor and the evaluation need not reject. evaluation.py's, violation.py's, adapter.py's and replay.py's docstrings state it as a limit, which TASK-054 replaces.
- **Carried findings of TASK-053's reviews** (D-1021): D4 (the property test compares the selection only, over logs with no blocking record.added and no repeated id); D6 (R9OwnTests' widened lookahead admits any "TASK-053 ACn", with no positive control beyond the changed docstrings); D9 (the end-to-end test sets the leases directly on the stand-in store); D10 (the "duplicate" half of AC2 cannot be tested with a violation). D3 is covered by the base's R7Records.
- **Limits** (TASK-053's AC7): the whole-log span (a violation of the task makes every later evaluation of it reject where the task is evaluable, also after a new approval); the task stays READY with no lease until an evaluation runs; no bound on repeated stops; the refused_submission label; F-a; no hook observed (C6 unmeasured); no conformance set or fixture changed (ADV-02's fixture is a later task); no observed read-set call; the real writer's files not tested.

## Resume when
- At the next session's start, after the decision files D-1018 onward: TASK-054 first; the findings and limits with a hardening task after M5's violation path, or any task that touches evaluation.py.

## Log
- 2026-10-16: opened (D-1025, D-1028 amendment 1).

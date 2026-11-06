# DEF-0112: whether the base-tests step should fail

- Status: open
- Opened: 2026-10-30 (session 9dbe9c67; TASK-103's acceptance, D-3830; D-3755 question Q1)
- Deferred by: decision agent (A41, A51), the acceptance decision of TASK-103 (D-3830)
- Decision group: A
- Blocks v0.1: no (the step is report-only and every acceptance names its base-test failures)
- Scheduled in: M8, the general policy decision for the evaluator paths, after the first real run and before the M8 exit review

## What
The step "GOV-003 base tests (report only)" exits 0 whatever the base's tests report; every later acceptance of a task that changes tests/ brings its raw output and names each base-test failure in its departure (DEF-0107 point 7; D-3755 C3). Whether the step should fail the job, and under what condition, is not decided.

## Why deferred
D-3755 Q1 ruled the step report-only: a failing step would make a task whose tests change on purpose red by construction, and would need a contract field for the expected changes.

## Resume when
After the next three accepted tasks that change tests/, or when a base-test failure is found that an acceptance did not name.

## Depends on
DEF-0107.

## Log
- 2026-10-30: opened at TASK-103's acceptance (D-3830).
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass E decision D-5258 (K4)): read in full; the Resume-when event (after the next three accepted tasks that change tests/) occurred: TASK-114, 115, 117, 118, 121, 122 and 123 changed tests (DEF-0110 Log) and each acceptance named its failures; the step stays report-only meanwhile. State: open; Blocks v0.1: no (the step is report-only and every acceptance names its base-test failures); Scheduled in: M8, the general policy decision for the evaluator paths, after the first real run and before the M8 exit review.

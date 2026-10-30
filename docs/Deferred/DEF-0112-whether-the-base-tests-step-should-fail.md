# DEF-0112: whether the base-tests step should fail

- Status: open
- Opened: 2026-10-30 (session 9dbe9c67; TASK-103's acceptance, D-3830; D-3755 question Q1)
- Deferred by: decision agent (A41, A51), the acceptance decision of TASK-103 (D-3830)
- Decision group: A

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

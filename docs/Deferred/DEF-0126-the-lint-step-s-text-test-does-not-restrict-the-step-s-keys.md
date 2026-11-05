# DEF-0126: the lint step's text test does not restrict the step's keys (a `shell:` or another `timeout-minutes:` key would pass); restrict them to name, if and run

- Status: open
- Opened: 2026-11-05 (session 6550f093-c843-41f2-99ca-c427579f48bf; TASK-119, decision D-4900)
- Deferred by: decision agent (A41, A51), D-4900 (C5)
- Decision group: A (self-build)

## What
The text test of TASK-119 (`tests/integration/test_ci_lint_step.py`, on the stopped branch task/TASK-119) pins the lint step's `run` text line by line, but it does not restrict the keys the step may carry. A `shell:` key or a second `timeout-minutes:` key added to the step would still pass the test. D-4900 C5 ruled: restrict the keys to name, if and run. The acceptance request of TASK-119 was to list this as a named departure together with pip's index page and version-check reads under AC3's wording.

## Resume when
The lint step is next changed or TASK-119 resumes as an r6: the r6 test restricts the step's keys to name, if and run.

## Follow-ups owed
- TASK-119 r6 (after the fix task of DEF-0124 and DEF-0125 has landed on main) carries the key restriction in its test; the step text itself stays as it is.

## Depends on
TASK-119 (stopped under AC4); DEF-0118; DEF-0124; DEF-0125.

## Log
- 2026-11-05: opened (session 6550f093), from D-4900 C5 (recorded in the records batch of D-4906).

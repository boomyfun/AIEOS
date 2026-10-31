# L-0042: A records commit is never pushed to the task branch; it reaches main only by a fast-forward together with the task commit

Rule: The records commit of a task (docs/records/<task>.jsonl) is not pushed to the task branch; the task commit and the records commit are pushed to main by one fast-forward, and the CI of the records commit is read on main.

- Status: active
- Category: process
- Binding: record only. Related: D-3400 (TASK-099), D-3712 (TASK-102), D-3981 (TASK-106), D-3898 (TASK-104's form).

## Pattern
The G0 scope step of the CI judges the commits of a task branch that main does not hold and fails any path that matches the contract's forbidden patterns; docs/records/** is forbidden (docs/** in the contract), so the CI run of a task branch that holds the records commit fails by design. On main, "no task" is printed and the run passes.

## Occurrences
- 2026-10-31 (../History/2026-10/2026-10-30-2323-m8-stage-8-task-106-the-base-tip-check.md, D-3979, D-3981): the records commit Y of TASK-106 was pushed to task/TASK-106 and the aieos-checks run 41157914363 failed at G0 scope (forbidden path docs/records/TASK-106.jsonl); the plan (D-3964 C6, D-3970 C5) had listed "the push of Y to the task branch; CI on Y" and the decision agent had overlooked the precedents; main was then fast-forwarded with X and Y (D-3987) and its CI passed.

## Why it happens
The TASK-104 route (D-3898) pushed X and R straight to main; a plan written from the order of steps listed the task branch push for the records commit as well, and nobody read the earlier red runs (TASK-099, TASK-102) as a rule.

## Prevention and detection
- A plan for a task's landing lists: X pushed to the task branch and its CI read; the records made and committed in the scratch clone; X and the records commit pushed to main together by a fast-forward (the D-3898 form); the CI read on main.
- Before any push of a commit that changes docs/records, ask which branch's CI will judge it and whether G0 forbids the path there.

# DEF-0125: pyflakes reports an unused local variable r at tests/unit/test_runner_rc.py:341

- Status: open
- Opened: 2026-11-05 (session 6550f093-c843-41f2-99ca-c427579f48bf; TASK-119, decision D-4902)
- Deferred by: decision agent (A41, A51), D-4902
- Decision group: A (self-build)

## What
The first run of the new lint step (pyflakes 4.0.3, pinned by version and hash) of TASK-119 on the branch task/TASK-119 (run aieos-checks 41965451678, head 5b9330c13eb40cee0006f25297449948be686e5c) reported, in the finding text of log line 7327 (the line's job, step name and time stamp left out):

`/home/runner/work/AIEOS/AIEOS/work/tests/unit/test_runner_rc.py:341:9: local variable 'r' is assigned to but never used`

The line of the file is `r = go(files, check=stand_in(), asked=asked)`; `r` is not used in the lines that follow (the decision agent read lines 333-346 at D-4902). The path is a GOV-003 evaluator path (a unit test file); the fix is its own task and its own decision.

## Resume when
A task removes the unused assignment (keeping the call if its effect is the point of the test) at tests/unit/test_runner_rc.py:341 and has landed on main. The lint step's text is never changed to ignore this finding (TASK-119 AC4 and AC6).

## Follow-ups owed
- The fix task (with DEF-0124's, or its own), before TASK-119 resumes as an r6 with a new base commit and a NEW branch name.

## Depends on
TASK-119 (stopped under AC4); DEF-0118; DEF-0124.

## Log
- 2026-11-05: opened (session 6550f093), at the first red run of the lint step (decision D-4902).

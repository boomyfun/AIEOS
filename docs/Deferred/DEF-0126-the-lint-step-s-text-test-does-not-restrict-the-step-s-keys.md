# DEF-0126: the lint step's text test does not restrict the step's keys (a `shell:` or another `timeout-minutes:` key would pass); restrict them to name, if and run

- Status: done
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
- 2026-11-06 (session f348bb86): TASK-124 adds to the text test of the lint step the test test_the_step_keys_are_exactly_name_if_and_run (keys exactly name, if and run; task commit bc33ff6a), which restricts the step's keys as this entry asked; limits recorded by the way-2 review (decision D-5149): the key pattern excludes digits and the run-block reader stops at a line indented under ten spaces; the status stays as the acceptance decides.
- 2026-11-06 (session f348bb86): closed. TASK-124 adds the text test test_the_step_keys_are_exactly_name_if_and_run (task commit bc33ff6a, on main since the push of D-5177; the main CI of that push, aieos-checks 42163853015 and aieos-native 42163853056, was read at D-5181), which restricts the lint step's keys to name, if and run as this entry asked. The acceptance of TASK-124 (D-5175; decided by: decision agent (A41, A51)) says, in its exit-review states: "DEF-0126: done (the key test; its limits are findings 3 and 4, recorded in its Log); the status is set in the closing records." The limits of the test stay as D-5149 recorded them and as the line of 2026-11-06 above states: the key pattern excludes digits and the run-block reader stops at a line indented under ten spaces. The records commit 0af82927 (D-5202) ran on main as aieos-checks 42172726686 (read at D-5204).

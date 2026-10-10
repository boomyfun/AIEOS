# DEF-0036: The state helpers copied in three tree-run test modules

- Status: open
- Opened: 2026-10-10 (decision files D-373 and D-375)
- Deferred by: decision agent (A41), D-373 (the dispositions of TASK-013's way-2 findings) and D-375 (TASK-013 accepted with this carried).
- Decision group: A (test code within the self-build).

## What
TASK-013 added the same helpers, rc_state, resume_check_record and present_results (and the constants RC_STATE_IDS and GOVERNOR_IDS), to each of tests/integration/test_runner_run.py, tests/integration/test_governor_conformance.py and tests/integration/test_runner_rc_run.py, as its contract's write set allowed no shared module. Way-2 reviews R1 and R3 of the first round noted the copies as a maintenance risk with no functional effect. Other non-blocking points recorded with the acceptance: the ACC-01 reason literal 'not met: case 1: decision' and WATCH_ASKED = 1 are exact pins that fail closed if the fixture or the runner's loading changes.

## Why deferred
D-373: no functional effect; a shared helper module would be a new path outside TASK-013's write set.

## Resume when
TASK-014 changes the tree-run tests (when the present state becomes the tree's), or any later task that touches those three modules.

## Depends on
TASK-013 accepted (done, D-375).

## Log
- 2026-10-10: opened (decision files D-373 and D-375).

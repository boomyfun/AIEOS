# DEF-0047: the review findings carried from TASK-020

- Status: open
- Opened: 2026-10-11 (decision D-506)
- Deferred by: decision agent (A41), D-506 (Q1 and C5: the dispositions F4, F6, F7 and F8 of the five way-2 reviews).
- Decision group: A (tests and checkers within the self-build).

## What
- F4: the worker's line checker ac_checks20.py (AC9) compares lines by content and the net count of assertion calls, so a removed assertion hidden by an equal line elsewhere, or offset by an added one, would pass it; for TASK-020 the reviewers read the whole diff. A later checker should compare per test and per line position.
- F6: tests/integration/test_conformance_risk_set.py's module docstring and the comment above its allow list still speak of TASK-020 as future ("null until TASK-020", "once TASK-020 sets it"); both states are still allowed by its test, so the text is not false.
- F7: TASK-020's AC4 says TASK-014's freeze record "still exists unchanged"; tests/integration/test_conformance_rc_set.py checks that a record with that binding and that id is still recorded (its docstring says so); recorded at acceptance as a reading (decision D-507).
- F8: the kept altered-set case 'a fixture outside Verification' of tests/unit/test_conformance_files.py edits scenarios[17], which is RISK-01; since Risk Engine is now an allowed capability, it errs by path, hash and named files only, and its name no longer describes it (at the base it erred by path and capability); 'a fixture for ADV-02' now exercises the capability rule, together with a path error.

## Resume when
A later task that changes these modules or the worker's line checker.

## Depends on
Nothing.

## Log
- 2026-10-11: opened (decision D-506; session e6209999).

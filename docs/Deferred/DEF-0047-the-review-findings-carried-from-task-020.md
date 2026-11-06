# DEF-0047: the review findings carried from TASK-020

- Status: open
- Opened: 2026-10-11 (decision D-506)
- Deferred by: decision agent (A41), D-506 (Q1 and C5: the dispositions F4, F6, F7 and F8 of the five way-2 reviews).
- Decision group: A (tests and checkers within the self-build).
- Blocks v0.1: no (a non-blocking review finding or limit of an accepted task)
- Scheduled in: M8, the conformance and runner test-fix task, before the M8 exit review

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
- 2026-10-30: TASK-102 (accepted by decision D-3707 at f25b4576; range fb90baaf..f25b4576; records d3a328bd; the map is docs/records/TASK-102.jsonl :44): settled F6 (tests/integration/test_conformance_risk_set.py:6, :29) and F8 (tests/unit/test_conformance_files.py:626); open F4 and F7. Status stays open.
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass A batch 1, decision D-5264 (F4 kept open by its condition C3)): read in full; git log f25b4576..HEAD (TASK-102's task commit) over the paths named in the Resume-when text printed no commit, so the event is not met (tests/integration/test_conformance_risk_set.py and tests/unit/test_conformance_files.py unchanged); open per the Log of 2026-10-30: F4 (a method point about line checkers; kept open, the absence of the 2026-10-11 script from the repository is not evidence that it is fixed) and F7. State: open; Blocks v0.1: no (a non-blocking review finding or limit of an accepted task); Scheduled in: M8, the conformance and runner test-fix task, before the M8 exit review.

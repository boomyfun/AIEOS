# DEF-0027: TASK-005's review findings carried to a later task

- Status: open
- Opened: 2026-10-10 (decision files D-278 C1 and D-279)
- Deferred by: decision agent (A41), D-278 C1: TASK-005 is accepted without a fix, since a fix is a new commit that makes every review and the CI run stale (assurance-model.md line 39; D-204, D-212).
- Decision group: A (test and wording changes in a later fixture task).

## What
Non-blocking findings of TASK-005's way-2 reviews, round 2 (commit 61ff86fd15a7ec457f72f9e261d710d89f9b11ee), to settle in TASK-005b's contract or a later task:
- R1-1: the property module's `canon` raises TypeError, not ValueError, on a float; a mutation that made a float would fail the test for the wrong reason.
- R3-2: the tests read the bound scenario file, the set file and TASK-002's records from the tree under evaluation; a check against the base's pinned hashes (the contract's intent_versions) would anchor them.
- R4-1 to R4-3: the module docstrings should say that no Resume Check exists and every RC scenario is NOT_RUN; the names of the INV-005 to INV-008 property tests should say they check the fixture data only; `rule_risk`'s docstring should say "as specification 3 section 3 decides" instead of "as check 7 computes it".
- R5-1: in RC-02 to RC-06, `head_commit` differs from the id of the single commit of base..HEAD (a placeholder no expected element depends on).
- R5-2 to R5-4: `check_given`'s exceptions for RC-03, RC-09 and RC-11 are wider than AC4's text.
- R5-5: no failing case for Δ meeting an interface's component or a schema's file.
- R5-6: no unit failing case for unsorted keys, an extra final LF, uppercase \u escapes or unneeded escapes.
- R5-7: the path-rule test checks a helper the test re-implements.
- R5-8: the INV-007 property does not assert that RC-06 is the only fixture whose intent is not current.
- R5-9: the folder check ignores sub-folders, and the check of tests/conformance/fixtures/ looks only for the rc_ prefix.
- From the decision agent's review (D-278): TASK-005b, which names the fixtures in the set file, must change the two integration tests of `tests/integration/test_conformance_rc_set.py` that assert the set file unchanged and its RC entries null, and its write set must include them.

## Why deferred
D-278 C1: none of the gaps lets an unfaithful fixture through (the decision agent checked the 11 fixtures itself); fixing them in TASK-005 would redo all eight reviews.

## Resume when
At TASK-005b's contract (after TASK-008), which must cite this item.

## Depends on
TASK-005 accepted (D-279) and its 11 files frozen (DM F29).

## Log
- 2026-10-10: opened (decision files D-278 and D-279).

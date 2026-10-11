# DEF-0044: TASK-018's carried review findings and erratum E1 to its AC7

- Status: open
- Opened: 2026-10-11 (decision files D-472 and D-473)
- Deferred by: decision agent (A41, A51), D-472 (the dispositions of the five way-2 reviews; erratum E1 adopted by D-359's route).
- Decision group: A (test and wording within the self-build).

## What
- Erratum E1 (D-472 C3), to be recorded in docs/records/TASK-018.jsonl at acceptance: AC7's list of the other modules that may name tests/conformance/fixtures_risk/ also includes tests/conformance/set.py, whose RISK-01 entry names the fixture's path as data once TASK-020 sets it; AC6 and the header's both-states rule govern (D-461 E2, D-472).
- AC8's "compile" means the builtin; the tests use `re.compile` (R1).
- The tests' matcher and its second reading in the property module share three readings of point 6 (an empty "*", a zero-name middle "**", a one-name trailing "**"); case is tested by one unit case only (R1, R3, R5).
- The integration module's policy check reads only `paths:` rules and adds R3 by hand; the unit module reads both kinds (R1, R5).
- `naming()` reads every .py file under src and tests on each run (R1).
- The tests' record and request form checks are their own restatement, since AC8 allows no import of the records module; the runner's own check accepted the file (R2).
- AC2's failing cases do not cover every sub-condition: retry_count, intent_versions, task_content_hash, a record's gate, outcome and intent_versions, unknown keys (R3, R5).
- `rules_problems`' article branch has no failing case of its own (R3).
- The "no expected element depends on a placeholder" check and the INV-005 and INV-006 properties are minimal; the one-byte hash property is trivially true of SHA-256 (R3, R5).
- `test_the_expected_cell_is_the_bound_one` checks cells 0, 2 and 4 of RISK-01's row, not the Source cell (R4).
- The contract header's sentence on what TASK-017's test modules glob was checked by script at drafting (D-460 (iv)) but not from the reviewers' inputs (R4).

## Why deferred
D-472: every finding is non-blocking; the one blocking finding (the set file in the second state) was fixed in the third commit and read by the decision agent; the rest are thin coverage or wording that does not change what the tests accept.

## Resume when
The next task that changes the Risk Engine fixture's test modules (TASK-019 or TASK-020), or the next revision of TASK-018's kind of contract; E1 at TASK-018's acceptance.

## Depends on
TASK-018's acceptance.

## Log
- 2026-10-11: opened (decision D-472; session 38c27ccc).

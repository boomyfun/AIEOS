# DEF-0035: The Resume Check's carried review findings

- Status: open
- Opened: 2026-10-10 (decision files D-361 and D-363)
- Deferred by: decision agent (A41), D-361 (the dispositions of TASK-008's way-2 findings) and D-363 (TASK-008 accepted with them carried).
- Decision group: A (task contracts within the self-build; a specification revision under A51, B9, where a finding needs one).

## What
Non-blocking findings of TASK-008's five way-2 reviews (R1 to R5), carried to TASK-008's next revision or to the task that reads the Resume Check's inputs from Git, the log and the files (DEF-0030):
- **R2 a:** the two ordering properties take the order from the module itself, and the "milder decision" property mutates only checks 4, 7 and 8.
- **R2 b:** a path with no "/" is read as "**/path", so a top-level file such as README.md meets docs/README.md (over-matching, the safe side).
- **R2 c:** a pattern with a trailing "/" (a read_set entry form the contracts use) never matches the files below it (the milder side).
- **R2 d, R5 F5:** when max_risk is too low and a write-set pattern also meets no rule, check 7 records only the STOP, so its ESCALATE never reaches outcomes_fired (the decision is unaffected).
- **R2 e, R5 F6:** test gaps: equal limits beyond retries; the payloads of the state_effect events; the check-3-over-check-4 choice; the conflict.detected uncovered line; the event_id formula; verdict reasons; schema null or ambiguous; a malformed approved_contract_hash.
- **R5 F2:** `used` null with `reported` false gives an error, while conformance-files.md §9 gives `{used, reported}` with no null form (a new reading, not a defect against the text).
- **R5 F3:** a risk_rules entry `{}` gives critical and STOP, not an error.
- **R5 F4:** read_set.unanalysed is always [], and uncovered does not say that the derived read-set and every input are the caller's.
- **R1 2:** `records` is imported and unused (AC9 requires the import).
- **R1 3:** the integration test reads the fixtures with pathlib, not through the runner's own readers as AC10 words it (as the base runner test does).
- **R4:** check's broad except turns programming errors into error records.
- **R3:** very long paths reach RecursionError in meet, caught and turned into an error record.

## Why deferred
D-361: none is blocking; each meets TASK-008's contract text or needs a reading or a specification revision.

## Resume when
TASK-008's next revision, or the task that reads the Resume Check's inputs (DEF-0030); R5 F2 and R2 c at the next revision of specification 3 or conformance-files.md.

## Depends on
TASK-008 accepted (done, D-363).

## Log
- 2026-10-10: opened (decision files D-361 and D-363).

# DEF-0043: TASK-017's non-blocking findings, one base-code point and section 10's articles wording

- Status: open
- Opened: 2026-10-11 (decision files D-458 and D-462)
- Deferred by: decision agent (A41, A51), D-458 (TASK-017 accepted with these recorded, no third commit), D-456 C4 (the base-code point) and D-462 C2 (the wording).
- Decision group: A (code, test and wording within the self-build).

## What
- (a) tests/property/test_runner_risk_properties.py: the random half of `test_a_rehashed_one_byte_change` asserts only that the result is one of the three, so it is a smoke check (round-2 review S2); name it so.
- (b) tests/unit/test_runner_risk.py: `load_derive`'s branch where the module's `__file__` is not a string is untested (S2).
- (c) src/aieos_bootstrap/conformance.py: the reason for a raising derivation in the runner's output carries the error's message as well as its type, which TASK-017's AC6 names (D-458).
- (d) src/aieos_bootstrap/conformance.py at feac0c8d, line 545 (base code, outside TASK-017's AC1): the Verification fixture checker's `rid in seen` raises on an unhashable record id instead of making the fixture malformed (D-456 C4).
- (e) docs/specs/conformance-files.md section 10: the table names `articles` "the constitution's articles", which cannot be literal while the constitution's scopes are named by role and three are "all paths"; TASK-018 uses `[]` by the placeholder rule ("no article's scope meets a changed path"); a later revision of section 10 may align the wording (D-462).

## Why deferred
D-458: every finding is non-blocking and none changes what PASS means; the one fail-open path of round 1 was fixed in TASK-017's second commit and reviewed; a third commit would have cost a push, a CI run and a reading for test naming and an output string. (d) is outside TASK-017's reach by its AC1. (e) is settled for TASK-018 within the text.

## Resume when
The next task that changes src/aieos_bootstrap/conformance.py or the runner's Risk Engine tests ((a) to (d)); the next revision of conformance-files.md ((e)).

## Depends on
TASK-017 accepted (done, D-458).

## Log
- 2026-10-11: opened (decision files D-458, D-456 C4 and D-462; session 51321169).
- 2026-10-29: point (e) is addressed by conformance-files.md revision 11 (section 10's `articles` row; DM F76; decisions D-3611 and the decision that approves the row), in the commit that adds DM F76; section 9's row `inputs` uses the same words for the Resume Check input `articles` and is not changed by revision 11, so it is noted here for the file's next revision; points (a) to (d) remain, so the item stays open.
- 2026-10-30: TASK-102 (accepted by decision D-3707 at f25b4576; range fb90baaf..f25b4576; records d3a328bd; the map is docs/records/TASK-102.jsonl :44): settled (b) (tests/unit/test_runner_risk.py:206); also done though not in the map: (a) the smoke check (tests/property/test_runner_risk_properties.py:153); open (c), (d); (e) is addressed by conformance-files revision 11. Status stays open.

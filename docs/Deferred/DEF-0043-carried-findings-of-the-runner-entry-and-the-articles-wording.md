# DEF-0043: TASK-017's non-blocking findings, one base-code point and section 10's articles wording

- Status: done
- Opened: 2026-10-11 (decision files D-458 and D-462)
- Deferred by: decision agent (A41, A51), D-458 (TASK-017 accepted with these recorded, no third commit), D-456 C4 (the base-code point) and D-462 C2 (the wording).
- Decision group: A (code, test and wording within the self-build).
- Blocks v0.1: no (a non-blocking review finding or limit of an accepted task)
- Scheduled in: v0.2 or later (concept section 16)

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
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass A batch 1, decision D-5264): read in full; git log f25b4576..HEAD (TASK-102's task commit) over the paths named in the Resume-when text printed no commit, so the event is not met (conformance.py and the runner's Risk Engine tests unchanged); open per the Log of 2026-10-30: (c) and (d); (e) is addressed by conformance-files revision 11 (Log of 2026-10-29). State: open; Blocks v0.1: no (a non-blocking review finding or limit of an accepted task); Scheduled in: M8, the conformance and runner test-fix task, before the M8 exit review.
- 2026-11-27 (session 228f426b; closure pass 2 of the deferred items, D-7443, D-7485; decided by: decision agent (A41, A51), D-7485): moved to "v0.2 or later (concept section 16)" under master plan section 6 point (6) (f): the item names no concrete wrong result of the kind of point (6) (a). Status and Resume when unchanged.
- 2026-11-28 (session 228f426b; TASK-171, accepted at D-7727, commit a2c808305d3f28df413e2771bfc247b4d3559a5a, docs/runs/TASK-171-acceptance.md; main CI runs 46058827716 and 46058827710 success): not done. Closed points: (c) src/aieos_bootstrap/conformance.py:1068, tests/unit/test_runner_risk.py:336; (d) conformance.py:587-592 and :533, tests/unit/test_runner_rc.py:673; (a) and (b) TASK-102; (e) conformance-files.md revision 11. Open: the section 9 row "inputs" of conformance-files.md noted on 2026-10-29 (D-7703), not revised because the change would reach beyond that row (D-7730). A dated entry under master plan section 6 point (6) (a): what: expected.approval.record_id given as a list or a dict raises TypeError in check_fixture (conformance.py:549), as before this task; what goes wrong if it is not done: a malformed fixture raises instead of giving an error finding; it fails safe (no wrong result), accepted as limit L2 of the acceptance text; the task that resolves it: this item's, with the section 9 row; Resume when: the next change of the fixture checkers of conformance.py or the next revision of conformance-files.md. Status, Blocks v0.1: no and schedule unchanged.
- 2026-11-28 (session 228f426b; TASK-172, accepted at D-7796, commit 3e3c5dca014a36ebe73398ca88c98a1217fc7979, docs/runs/TASK-172-acceptance.md; main CI runs 46104078602 and 46104078510 success): closed, done, point by point. (a) The smoke-check comment: tests/property/test_runner_risk_properties.py:153 (TASK-102). (b) The non-str __file__ test: tests/unit/test_runner_risk.py:206 (TASK-102). (c) A raising derivation names only the type: src/aieos_bootstrap/conformance.py:1068, tests/unit/test_runner_risk.py:336 (TASK-171). (d) A non-text record id in the fixture check: conformance.py:533 and :587-:592, tests/unit/test_runner_rc.py:673 (TASK-171). (e) The articles wording of section 10: docs/specs/conformance-files.md:176 (revision 11). The section 9 row "inputs": revision 12, docs/specs/conformance-files.md:177, committed at d70085d1. The expected approval record_id given as a list or a dict: conformance.py:549, tests tests/unit/test_runner_rc.py:691 and :695 (TASK-172). The entry of 2026-11-28 above read that point as failing safe, accepted as limit L2; that was wrong on one point: at base cfbcfd1e the TypeError was caught neither by run_scenario (conformance.py:981-:1000) nor by main (:1666-:1670), so no run record would be printed. It is closed here.

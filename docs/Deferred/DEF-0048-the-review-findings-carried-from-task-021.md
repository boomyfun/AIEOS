# DEF-0048: the review findings carried from TASK-021, a reading for specification 4 and an uncovered criterion of TASK-004

- Status: open
- Opened: 2026-10-11 (decisions D-516 and D-520)
- Deferred by: decision agent (A41), D-516 (C2: the reading R1 and TASK-004's AC12) and D-520 (Q1 and C3: the dispositions F1 to F11 of the five way-2 reviews).
- Decision group: A (tests, a checker and a specification text within the self-build).

## What
- Reading R1 (decision D-516): specification 4 section 6 item 1 says a gate's `args` entry "that names no AC of the contract" is a finding; TASK-021's check allows an entry that is an article of the contract's own `constitution` list, since every G3 plan names articles. For specification 4's next revision. With it, F4: any string in a contract's own constitution list excuses a stray entry, so a contract can silence a stray finding by listing it; a stricter rule would read the article ids from the constitution at the base.
- TASK-004's AC12 (its limits criterion, `docs/tasks/TASK-004.yaml` line 222) is named by neither its G2 args (line 271) nor its G3 args (line 272): an uncovered criterion of an accepted contract, found by TASK-021's integration test and recorded as data; nothing in TASK-004 is changed and no acceptance is reopened.
- F1: the purity test of tests/unit/test_ac_coverage.py looks at Call nodes only; a bare reference such as `f = open` would pass it (the CI's deterministic_rule step refuses the name itself).
- F2: two weak properties in tests/property/test_ac_coverage_properties.py (the key-order property cannot change this implementation's result; the "named or uncovered, never both" property restates the implementation's set logic); neither is vacuous.
- F3: the constant KINDS in src/aieos_bootstrap/ac_coverage.py is defined and unused.
- F5: coverage_record does not examine the elements of `findings`; any non-empty list gives the blocking record (fail closed); its docstring could say so.
- F6: AC4's stray finding names its gate in the detail (src/aieos_bootstrap/ac_coverage.py lines 108-109), but no test asserts it.
- F7: the integration test's contract reader skips an AC line it cannot match, while it raises on a plan line it cannot parse; every "  - AC" line of the 21 contracts matches its form today, so no criterion is dropped now; a later revision should make it raise.
- F8: the property generator rarely makes a fully covered contract with no stray entry, so the `None` branch of the record property may not run there (the unit tests cover it).
- F9: some malformed forms are untested (a gate that is not a mapping, an empty check, a non-string criterion text, a non-string args entry); the code refuses each.
- F10: the module docstring calls the reading "TASK-021 R1", while in the contract R1 is AC12's first test rule; "AC4's reading, decision D-516 R1" is clearer.
- F11: the docstring test pins three limit phrases, not the gate-level and "no caller" limits of AC9 (the docstring states them).
- DEF-0042 point 7 (how a corrected contract clears the coverage record, and whether the governor should name an uncovered criterion as a missing gate result) stays with DEF-0042.

## Resume when
- R1 and F4: at specification 4's next revision.
- TASK-004's AC12: if TASK-004's contract is ever revised or given an erratum.
- F1 to F3 and F5 to F11: at a later task that changes ac_coverage.py or its tests, or the task that gives the core a caller of the check.

## Depends on
Nothing.

## Log
- 2026-10-11: opened (decisions D-516 and D-520; session a447d091).
- 2026-10-30: TASK-102 (accepted by decision D-3707 at f25b4576; range fb90baaf..f25b4576; records d3a328bd; the map is docs/records/TASK-102.jsonl :44): settled F1 (tests/unit/test_ac_coverage.py:212-216), F2 in part (a literal-oracle property added, tests/property/test_ac_coverage_properties.py:80; no change to the key-order property is shown), F3 (src/aieos_bootstrap/ac_coverage.py:29), F5 (ac_coverage.py:116-117), F6 (test_ac_coverage.py:118), F9 (:60), F10 (ac_coverage.py:8), F11 in part (test_ac_coverage.py:220); open F11's no-caller limit (ac_coverage.py:20 says there is no caller in the core, while src/aieos_bootstrap/verification_records.py:120-121 calls it), reading R1 with F4 (for specification 4's next revision), TASK-004's AC12 (an uncovered criterion of an accepted contract), F7, F8, DEF-0042 point 7. Status stays open.

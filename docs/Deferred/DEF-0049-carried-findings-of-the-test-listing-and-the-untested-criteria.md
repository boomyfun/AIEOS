# DEF-0049: the review findings carried from TASK-022, the criteria named by no test before it, and a naming convention

- Status: open
- Opened: 2026-10-11 (decisions D-530 and D-536)
- Deferred by: decision agent (A41), D-530 (C3: the counts, the full list and the convention) and D-536 (Q1 and C2: the dispositions F1 to F12 of the five way-2 reviews).
- Decision group: A (tests, a checker and a working convention within the self-build).

## What
- The criteria named by no test before TASK-022 (data; decision D-530): TASK-022's listing (src/aieos_bootstrap/ac_tests.py), under the naming rules of decision D-529 C2 (a test's own name and docstring only; a qualified "TASK-nnn ACn" counts in any file; a bare "ACn" only for the one task whose write set lists the file), finds 180 of the 183 criteria of the G2 tests gates of TASK-001 to TASK-021 named by no test. The tests of those tasks name criteria mainly in module and class docstrings and comments, which the rules do not count (8 of 620 test functions had a docstring). These are findings under specification 4 section 6 item 2; nothing in those tasks is changed and no acceptance is reopened. The list, from the module's own output (SP/t022/compare-2.txt of session a067ac68), per task (count): criteria:
  - TASK-001 (8): AC1, AC2, AC3, AC4, AC5, AC6, AC7, AC9
  - TASK-002 (6): AC1, AC2, AC3, AC4, AC5, AC7
  - TASK-003 (11): AC1, AC2, AC3, AC4, AC5, AC6, AC7, AC8, AC9, AC11, AC12
  - TASK-004 (12): AC1, AC2, AC3, AC4, AC5, AC6, AC7, AC8, AC9, AC11, AC13, AC14
  - TASK-005 (7): AC1, AC2, AC3, AC4, AC5, AC6, AC8
  - TASK-006 (11): AC1, AC2, AC3, AC4, AC5, AC6, AC7, AC8, AC10, AC12, AC13
  - TASK-007 (10): AC1, AC2, AC3, AC4, AC5, AC6, AC7, AC9, AC11, AC12
  - TASK-008 (12): AC1, AC2, AC3, AC4, AC5, AC6, AC7, AC8, AC9, AC11, AC13, AC14
  - TASK-009 (10): AC1, AC2, AC3, AC4, AC5, AC6, AC7, AC8, AC10, AC12
  - TASK-010 (5): AC1, AC2, AC3, AC4, AC6
  - TASK-011 (7): AC1, AC2, AC3, AC4, AC5, AC6, AC8
  - TASK-012 (4): AC1, AC2, AC3, AC5
  - TASK-013 (8): AC1, AC2, AC3, AC4, AC5, AC6, AC7, AC10
  - TASK-014 (6): AC1, AC2, AC5, AC6, AC7, AC10
  - TASK-015 (7): AC1, AC2, AC3, AC4, AC5, AC7, AC9
  - TASK-016 (10): AC1, AC2, AC3, AC4, AC5, AC6, AC7, AC8, AC10, AC12
  - TASK-017 (14): AC1, AC2, AC3, AC4, AC5, AC6, AC7, AC8, AC9, AC10, AC11, AC13, AC15, AC16
  - TASK-018 (8): AC1, AC2, AC3, AC4, AC5, AC6, AC7, AC9
  - TASK-019 (8): AC1, AC2, AC3, AC4, AC5, AC6, AC7, AC10
  - TASK-020 (7): AC1, AC2, AC3, AC5, AC6, AC7, AC10
  - TASK-021 (9): AC1, AC2, AC3, AC4, AC5, AC6, AC7, AC10, AC12
- A convention, proposed for the next contracts' form, not a rule (decision D-530 Q2): each test names the criteria it stands for in its own docstring, as "TASK-nnn ACn" when the file is shared by tasks; every criterion is written with its task id (a bare "ACn" beside a task id is not counted).
- F1: every path's form is checked before any source, so a bad path form at a late path is reported before a bad source at an earlier path (ref "tests"); AC1's "tests by sorted path" can be read per path; not tested. To state the reading in AC1 or the module docstring and pin it by a test.
- F2: a test method defined twice in one class counts both docstrings under one key, although Python keeps only the last definition; counting a discarded earlier definition lets it claim an AC (spec 4 line 73); rule to adopt at the next touch: last definition only (decision D-536 C2).
- F3: no unit test of a bare criterion beside a qualified mention of the same task ("TASK-099 AC1 and AC2"); a mutant that strips qualified mentions before deciding whether a task id is named would pass the unit and property tests.
- F4: the property "named or untested, never both" is close to a restatement of the implementation; no property checks bare or ambiguous outcomes against an oracle.
- F5: the integration test's line reader drops a write-set path line that carries a trailing comment (no contract has one today).
- F7: an over-long task id ("TASK-0221") or a lower-case one is not read as a task id, so a bare criterion beside it may count.
- F8: listing_record does not examine the elements of `findings`; any non-empty list gives the blocking record (fail closed; as TASK-021's coverage_record).
- F9: write-set paths are checked only as non-empty strings, not in the tests' path form; a path in another form never matches.
- F10: the integration test pins the past's counts; a later test naming an earlier task's criterion in qualified form would change them (such a change is deliberate and comes with its own decision).
- F11: the integration test's docstring says each criterion is "named by one of its own tests", while a qualified mention in any file also counts.
- F6 (only the number of ambiguous keys is pinned) and F12 (a parser limit beyond the module's control) need no action (decision D-536).
- DEF-0042 points 7 (clearing such a record) and 8 (a record key for the criteria a gate covers) stay with DEF-0042.

## Resume when
- The convention: when the next task contract is drafted (its tests name their criteria so), and at the next revision of the contract form or of specification 4.
- The 180: if the tests of an earlier task are ever changed for another reason, its criteria may be named then; no task is reworked for this alone.
- F1 to F5 and F7 to F11: at a later task that changes ac_tests.py or its tests, or the task that gives the core a caller of the listing.

## Depends on
Nothing.

## Log
- 2026-10-11: opened (decisions D-530 and D-536; session a067ac68).
- 2026-10-30: TASK-102 (accepted by decision D-3707 at f25b4576; range fb90baaf..f25b4576; records d3a328bd; the map is docs/records/TASK-102.jsonl :44): settled F1 (src/aieos_bootstrap/ac_tests.py:8-9; tests/unit/test_ac_tests.py:88), F3 (:142), F5 (tests/integration/test_ac_tests_tree.py:25, :82), F7 and F9 by stating the behaviour and pinning it, with no change to it (ac_tests.py:20-23; test_ac_tests.py:149, :156), F11 (test_ac_tests_tree.py:110); open F4; F2, F8 (ac_tests.py:184-186 is unchanged) and F10 were not shown changed, although the map says all but F4 are settled; the 180 criteria (data), the naming convention and DEF-0042 points 7 and 8 are unchanged; F6 and F12 need no action. Status stays open.

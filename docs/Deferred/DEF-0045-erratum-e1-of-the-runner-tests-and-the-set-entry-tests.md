# DEF-0045: TASK-019's erratum E1 and the four tests that TASK-020 changes

- Status: open
- Opened: 2026-10-11 (decision files D-484 to D-486)
- Deferred by: decision agent (A41, A51), D-484 (erratum E1 by D-359's route); decision agent (A41), D-481 (the split with TASK-020).
- Decision group: A (test and wording within the self-build).

## What
- Erratum E1 to TASK-019 (D-484), to be recorded in docs/records/TASK-019.jsonl at acceptance: "AC3's test R6RunRecord.test_the_outcome_with_a_resume_check_scenario may instead set the fixture of every Risk Engine entry to null in its own set value, as it already does for every Verification entry, with every assertion line byte-equal and holding in both states; then no mirror helper is added and real_files() does not change. That one changed line is allowed in AC2's line check of tests/unit/test_runner_rc.py besides the helpers' changed lines, and AC10's R3 reads as that test passing over the tree and under AC7's simulation (D-483, D-484)."
- The four tests that fail in the simulated state of TASK-020 and belong to it (D-481; TASK-019 AC7): test_conformance_files SetFileTest.test_the_set_file; test_conformance_rc_set RcSetTest.test_the_set_file_is_unchanged_and_frozen; test_conformance_set ConformanceSetEndToEndTest.test_the_set_binds_the_bound_file and test_the_whole_set.
- TASK-019's stated limits (its AC9): the present state is run only by the simulation until TASK-020 lands; the simulated RISK-01 PASS with the root's governor is worker evidence about the tests, not conformance evidence; the fixed set value's pin fails closed if TASK-020 changes the set file beyond RISK-01's fixture and fixture_set_version.

## Resume when
TASK-019's acceptance (E1 into its records file); TASK-020's contract (the four tests and the set file's new freeze before its first commit).

## Depends on
TASK-019's reviews and acceptance.

## Log
- 2026-10-11: opened (decisions D-481, D-484; session b94736f9).
- 2026-10-11: erratum E1 recorded in docs/records/TASK-019.jsonl (its contract record) at TASK-019's acceptance (decisions D-493, D-494); the set file's freeze for TASK-020 given first (decision D-496, DM F35); the four tests stay for TASK-020's contract (session d662611e).

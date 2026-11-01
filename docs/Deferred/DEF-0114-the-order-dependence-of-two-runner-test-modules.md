# DEF-0114: the order dependence of tests/integration/test_runner_run.py and tests/unit/test_runner.py on other test modules loaded in the same process

- Status: open
- Opened: 2026-11-01 (session a048abb9; TASK-112 step X, decisions D-4376 to D-4379)
- Deferred by: decision agent (A41, A51), D-4379 for the text and D-4380 for where it is written (the docs commit after the records commit of TASK-112, not the code commit)
- Decision group: A

## What
When the suite is run in eight explicit parts (the scratch runner of TASK-111 and TASK-112, 110 s per command), three tests of `tests/integration/test_runner_run.py` (`RunnerEndToEndTest.test_a_stand_in_that_answers_from_the_expected_values`, `test_a_stand_in_with_one_decision_outside_a_list`, `test_no_governor`) and three of `tests/unit/test_runner.py` (`R1ReaderAndRoot.test_inputs_come_only_through_the_reader`, `R3DoesNotCount.test_the_real_set_counts`, `R4FreezeApproval.test_the_real_approval_and_two_approvals_of_one_hash`) fail unless certain other test modules are loaded in the same process (`test_runner_run.py` fails alone, G3); the three `test_runner.py` tests fail in the lists of G1, G5 and G7. The first failure text is an extra problem, "the Capability Boundaries entry could not be loaded from the root (reading)" (`tests/integration/test_runner_run.py` :250; `src/aieos_bootstrap/conformance.py` :1208-1241 and :1597), and the counts of the real set are empty.
Evidence (scratch runs of TASK-112; the raw outputs `out_G1.txt` to `out_G7.txt`, with their runners and SHA-256 lists, are kept outside the repository in `%USERPROFILE%\AIEOS-REG0-lite\sessions\a048abb9-a7d0-4fe9-8438-32ad5ef5b875\scratchpad-evidence\t112\`): the 20 modules of part 6 after the new module of TASK-112 shifted the stride layout fail 6 tests (G1) and fail the same 6 in a clean clone at 2547d549 with no TASK-112 file (G7), so the defect predates TASK-112; `test_runner_run.py` alone fails 3 of 3 (G3); with `test_records_execution` or `test_stale` it still fails 3 (G4, G6); with `test_runner` it fails 6 (G5); the 20 modules of the old part 6 pass (G2, and the baseline of 2848 tests in eight parts). G1 and G2 differ by three modules each way, so the module that makes the tests pass is one of, or a combination of, `test_records_read_set`, `test_runner_cb` and `test_startup`. Not proven: why the CI discovery is green, and what primes the state; all three candidates are unit modules whose tests run after those of `test_runner_run.py`, and the runner imports every module before any test runs, so the priming would come from import-time effects.

## Why deferred
The defect predates TASK-112 and lies in older tests and in how the conformance runner loads its entries from the root; fixing pre-existing tests is outside TASK-112 (D-4376 C6). CI, which runs the suite in one process, was green at commit C, so the gate is not known to be affected; the risk is a hidden coupling that makes a split run of the suite give false failures, or a future reordering of discovery give them in CI.

## Resume when
The next task that touches `tests/unit/test_runner.py`, `tests/integration/test_runner_run.py` or `src/aieos_bootstrap/conformance.py` (its `load_cb`), or when a CI discovery order change or a split run shows the same six failures, or when the three candidate modules are found to prime the state (three more diagnostic runs would find which one).

## Depends on
TASK-112 (the runs G1 to G7, D-4376 to D-4378); the conformance runner tasks that built `test_runner_run.py` and `test_runner.py`.

## Log
- 2026-11-01: opened (session a048abb9; D-4379). Written in the docs commit whose parent is the records commit 960db78f0e3dc35c9b46711b397664b8e25793e1 of TASK-112 (the commit that adds this file only; its own id is not written here, it is the child of that records commit); the code commit of TASK-112 is c68c953ca34cb3c8cae3893e5430b538d4850bbd.

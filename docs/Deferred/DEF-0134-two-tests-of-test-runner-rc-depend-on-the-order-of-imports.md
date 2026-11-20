# DEF-0134: two tests of tests/unit/test_runner_rc.py depend on the order in which modules are imported and fail when the file runs alone

- Status: open
- Opened: 2026-11-14 (../History/2026-11/2026-11-14-2148-m8-stage-8-task-135-the-judge-fix-accepted-and-landed-26136a0a.md)
- Deferred by: decision agent (A41, A51), D-6252
- Decision group: A (scheduling)
- Blocks v0.1: no (the file run alone fails 2 of 35, but the CI's full discovery passes: the unit_test step of the runs of 5bd65778 is green)
- Scheduled in: M8, as its own test-only task

## What
In tests/unit/test_runner_rc.py the class R3EntryPoint (a subclass of Isolated) has two tests, test_absent and test_a_loaded_module, that assert `r.problems == []`. The fixture Isolated.setUp removes the governor from sys.modules and puts the Absent finder first on sys.meta_path (test_runner_rc.py :143-149, :176-192, the insertion of Absent() at :189; the class R3EntryPoint at :353, test_absent at :354, test_a_loaded_module at :396), so importing aieos_bootstrap.governor raises ModuleNotFoundError. conformance.load_cb imports aieos_bootstrap.evaluation (conformance.py :1215-1219), and evaluation.py :148 has a module-level `from aieos_bootstrap import governor`. When evaluation is not yet in sys.modules, that import fails with the name aieos_bootstrap.governor, which is not one of CB_MODULES (conformance.py :134), so load_cb returns FAILED and the run adds the problem "the Capability Boundaries entry could not be loaded from the root (reading)". Run alone, the file fails 2 of 35 tests (the tests 16 and 20); with `import aieos_bootstrap.evaluation` first (a runner with one added line, task TASK-135, D-6251) it passes 35 of 35. In the CI's full discovery the files before it load evaluation first, so the order hides it.

## Why deferred
Found while testing TASK-135 (slice 3b of the unit tests timed out and showed two failures; each of the 14 files of the slice was then run alone, D-6250). The file and evaluation.py are outside TASK-135's write set (D-6252 C4: not fixed inside TASK-135). It blocks nothing: the CI is green.

## Resume when
When a task touches tests/unit/test_runner_rc.py or the order of the unit discovery, or at the M8 exit review.

## Depends on
None. Related: DEF-0114 (the same problem text, "the Capability Boundaries entry could not be loaded from the root (reading)", in tests/integration/test_runner_run.py and tests/unit/test_runner.py when they run without certain other test modules). The cause found here (aieos_bootstrap.evaluation not yet loaded when the governor is hidden) may be the cause there too; this is not checked.

## Log
- 2026-11-14: opened (session 26136a0a; decisions D-6250, D-6251, D-6252).
- 2026-11-20 (session dc7cf6ca; the acceptance of TASK-147, decisions D-6642 C5, D-6644 S2, D-6660 and D-6665): met again in a local slice run of the whole suite for TASK-147 (24 slices in a scratch clone). In slice 24 the two tests of this entry failed, test_runner_rc.R3EntryPoint.test_a_loaded_module and test_runner_rc.R3EntryPoint.test_absent, with the problem text of this entry ("the Capability Boundaries entry could not be loaded from the root (reading)", one problem against an expected empty list). In slice 22 the three tests of DEF-0114 failed, test_runner.R1ReaderAndRoot.test_inputs_come_only_through_the_reader, test_runner.R3DoesNotCount.test_the_real_set_counts and test_runner.R4FreezeApproval.test_the_real_approval_and_two_approvals_of_one_hash; the first failure text of that slice is "AssertionError: False is not true" at tests/unit/test_runner.py :243 (`self.assertTrue(r.value['counts'])`, the empty counts that DEF-0114 names). The five failures are exactly the two tests of this entry and the three of DEF-0114; no other test failed. The same tests pass when aieos_bootstrap.replay, adapter and evaluation were already imported in the process, under the CI's per-group discovery (the CI runs of the TASK-147 branch and of main were green) and under a local partition that imports every test module of the group first (the diagnoses D1, D2, S, C and diag_pre of that session). Reading, not a decision about the cause: the import-order coupling described above, seen now also in the file of DEF-0114 and consistent with the failure of its three tests; the same tests pass with TASK-147's files when those modules are imported first, so TASK-147's files are not shown to cause it. Nothing was changed. State: open; Blocks v0.1: no. The acceptance record: docs/runs/TASK-147-acceptance.md, item "DEFECT ITEM 2".

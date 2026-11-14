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

# DEF-0046: the review findings carried from TASK-019

- Status: open
- Opened: 2026-10-11 (decisions D-491 and D-492)
- Deferred by: decision agent (A41), D-491 (C5: the dispositions F2, F4, F5 and R5's carried case); decision agent (A41), D-492 (the findings recorded in DA-3, none blocking).
- Decision group: A (tests within the self-build).

## What
- F2: the state helper risk_state and its constant RISK_01_SHA256 are copied in four test modules (test_governor_conformance.py, test_runner_rc_run.py, test_runner_risk_run.py, test_runner_run.py), as TASK-013's rc_state is; a copy may drift; a shared helper needs a path outside TASK-019's write set.
- F4: test_runner_risk_run.py's test_the_tree_as_it_is keeps its base docstring line "AC10: RISK-01's entry is null, so it is NOT_RUN" (AC4 keeps base lines byte-equal); the added comment below it states the present state.
- F5: that test's present-state branch asserts each scenario in a loop over the run's results and then the outcome, with no count assertion of the scenarios.
- R5's carried case: no test of a fixture file in the tree whose SHA-256 differs from the set entry's (the state helper reads the file from the tree; a test would need a write to the tree or another helper signature, outside the contract).

## Resume when
A later task that changes these modules (TASK-020 changes the set file's state and may update F4's docstring), or a task that factors the test helpers.

## Depends on
Nothing.

## Log
- 2026-10-11: opened (decisions D-491, D-492; session d662611e).

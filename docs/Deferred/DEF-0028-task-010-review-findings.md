# DEF-0028: TASK-010's review findings carried to later tasks

- Status: open
- Opened: 2026-10-10 (decision files D-298 and D-299)
- Deferred by: decision agent (A41), D-298 C2: none of the findings is blocking, and a fix is a new commit that makes the five reviews and the CI run stale (assurance-model.md line 39; D-278 C1).
- Decision group: A (test and wording changes in a later fixture task; notes to TASK-006 and TASK-008).

## What
Non-blocking findings of TASK-010's five way-2 reviews (commit ead46b03260aaf032da91c9a7d2d54df4ebe78d1):
- For a later fixture task touching `tests/integration/test_conformance_rc_set.py`: R1-1 (the path normalisation `str(...).replace('\\', '/')` is old code; with membership instead of equality, a file named with a backslash on a POSIX runner could alias an allowed name; `as_posix()` closes it); R5-1 (no test of the sorting, none of an allowed file name in a wrong folder: two more in-memory cases); R5-3 (the failure message of `set(OWN) <= set(found)` does not name the missing module); R4-2 and R4-3 (the module and the commit message state no limit; the commit message's "every other module that names the folder still fails the assertion" holds only for .py files under src/ and tests/ with the literal name); R3-4 (the allowances are tied to paths, not to TASK-006).
- For TASK-006: `src/aieos_bootstrap/__init__.py` is in its write set but not on the allowed list; if its new text names the Resume Check fixture folder, the assertion fails and TASK-006 must escalate (it forbids that module). Re-confirm the allowed list at TASK-006's acceptance.
- For TASK-008: once the runner names the folder, a module under src/ that imports it can reach the fixtures without naming the folder, which the literal-name assertion cannot see; TASK-008's contract or review must check that `resume_check` imports nothing from the runner.
- The contract's wording only (not changed): the runner is called a module that "does not exist yet", but it exists at the base; only its naming of the folder is missing.

## Why deferred
D-298 C2: none blocks the acceptance; the protection of the assertion is advisory and the acceptance records say so.

## Resume when
At TASK-006's contract request and acceptance, at TASK-008's contract, and at the next task that changes the module.

## Depends on
TASK-010 accepted (D-299) and on `main` (D-300).

## Log
- 2026-10-10: opened (decision files D-298 and D-299).
- 2026-10-10 (session b6752b9f): the TASK-006 points are met: `src/aieos_bootstrap/__init__.py` does not name the Resume Check fixture folder, and the allowed list was re-confirmed at TASK-006's acceptance (D-308: the modules naming the folder at 471f4e60 are exactly the runner and the six allowed test modules). The other points stay open.

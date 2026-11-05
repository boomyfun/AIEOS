# DEF-0124: pyflakes reports an unused import at src/aieos_bootstrap/resume_check.py:42 (aieos_bootstrap.records), a pinned governance file

- Status: open
- Opened: 2026-11-05 (session 6550f093-c843-41f2-99ca-c427579f48bf; TASK-119, decision D-4902)
- Deferred by: decision agent (A41, A51), D-4902
- Decision group: A (self-build)

## What
The first run of the new lint step (pyflakes 4.0.3, pinned by version and hash) of TASK-119 on the branch task/TASK-119 (run aieos-checks 41965451678, head 5b9330c13eb40cee0006f25297449948be686e5c) reported, in the finding text of log line 7326 (the line's job, step name and time stamp left out):

`/home/runner/work/AIEOS/AIEOS/work/src/aieos_bootstrap/resume_check.py:42:1: 'aieos_bootstrap.records' imported but unused`

The line of the file is `from aieos_bootstrap import records`. The finding is the CI's; the worker did not run the tool locally (the app's classifier denied the one local trial, D-4873).

The file is a pinned governance file: the workflow pins its SHA-256 (AIEOS_PINNED_RESUME_CHECK = e1578939...5a135 in the run's conformance line) and the conformance run binds it. A change to the file therefore brings the pin handling (a change under `.github/` is its own A66 decision bound by SHA-256) and a new base run; the fix task is critical. The fix task must also show that the import has no side-effect use (nothing else relies on the name or on the import's effect).

## Resume when
A task removes (or justifies by a stated reason that the lint step can accept without changing its text) the unused import at src/aieos_bootstrap/resume_check.py:42, with the pin handling, and that task has landed on main. The lint step's text is never changed to ignore this finding (TASK-119 AC4 and AC6).

## Follow-ups owed
- The fix task (expected TASK-120, with its own contract and decisions): found by reading the pin route of TASK-008/D-396 and its successors, not by guessing.
- DEF-0125 (the second finding of the same run) may be fixed in the same task or in its own; both before TASK-119 resumes.
- TASK-119 then resumes as an r6 with a new base commit and a NEW branch name (no force-update of the old branch).

## Depends on
TASK-119 (stopped under AC4); DEF-0118; DEF-0125.

## Log
- 2026-11-05: opened (session 6550f093), at the first red run of the lint step (decision D-4902).
- 2026-11-05 (session 43f86835): TASK-121, the enabler of the pin handling, landed on main (X c9cb986f, accepted at D-4975): the workflow now holds a job value AIEOS_PINNED_RESUME_CHECK_PREVIOUS (empty) and one bounded acceptance in the base run, so that a pinned upgrade of src/aieos_bootstrap/resume_check.py can pass the base run. The import itself is not yet removed: that comes with TASK-120 (revision r3), whose landing sets the pin and the previous-version value in the workflow under A66. The status stays open.

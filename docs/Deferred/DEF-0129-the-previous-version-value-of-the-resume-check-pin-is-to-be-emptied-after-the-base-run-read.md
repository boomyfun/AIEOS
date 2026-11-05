# DEF-0129: the previous-version value of the Resume Check pin is to be emptied after the base-run read (TASK-122)

- Status: open
- Opened: 2026-11-05 (session 43f86835-8e74-41ad-8a42-ea9e67c52d9b; TASK-122, decision D-5024 C6)
- Deferred by: decision agent (A41, A51), D-5024 (the two entries of this records commit), D-5019 C4(d)
- Decision group: A (self-build), a later change under A66

## What
TASK-122 set the job value AIEOS_PINNED_RESUME_CHECK_PREVIOUS in .github/workflows/aieos-checks.yml to the old Resume Check version (e1578939404da0b61d56d9187521b92c923e7cb841acdf15d0afb7155605a135) and AIEOS_PINNED_RESUME_CHECK to the new one (b03c0b8a1caaa77c2974da0b512bd38e1f330b5d08dda1bbd85427944eee2e76). While the previous-version value stays set, the conformance base run also accepts the old file as the base's Resume Check file when the pushed head's file is the new one (the path that TASK-121 added). That acceptance served the upgrade; after the upgrade has been read green on main it is a standing loosening of the check.

## Why deferred
The contract of TASK-122 allowed exactly two value lines in the workflow (AC4, AC6); emptying the previous-version value is a different act with its own security meaning and is a change under `.github/`, its own A66 decision bound by SHA-256 (D-5019 C4(d)).

## Resume when
The base run on L has been read green at the push of the records commit of TASK-122 (its notice shows the base resume check file equal to the pinned version, RC-01 to RC-11 pass, outcome pass). Then a task changes that one value line back to empty (the value that means off) under A66, and its CI run is read.

## Depends on
TASK-122; the read of the base run on L; DEF-0128 for the same file.

## Log
- 2026-11-05: opened (session 43f86835), in the records commit of TASK-122 (decision D-5024 C6).

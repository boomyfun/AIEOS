# DEF-0108: earlier tasks' GOV-003 "holds" records may overstate

- Status: open
- Opened: 2026-10-30 (session 1c1bf794; TASK-102's acceptance, decisions D-3705, D-3706, D-3707)
- Deferred by: decision agent (A41, A51), at TASK-102's acceptance
- Decision group: A

## What
The gap of DEF-0107 applies to every earlier self-build task that changed or added tests. Some earlier records say GOV-003 "holds" (for example TASK-101, which added `tests/unit/test_export_resume.py`: its GOV-003 record TASK-101-way2-R3-GOV-003 in docs/records/TASK-101.jsonl). Those records may overstate. They are not reopened by TASK-102; they are public and permanent, and a later decision can supersede them.

## Why deferred
Reopening them now would be scope growth for TASK-102, and the right wording depends on how DEF-0107 is closed.

## Resume when
DEF-0107 is taken up.

## Depends on
DEF-0107.

## Log
- 2026-10-30: opened at TASK-102's acceptance (session 1c1bf794).
- 2026-10-30: the wording is set by point 6 of DEF-0107's stated policy (D-3740): earlier GOV-003 "holds" records of tasks that changed or added tests do not cover the tests part; no record is edited. Status stays open until DEF-0107 is done; no list of the earlier tasks that changed tests is made unless a later decision asks for it.

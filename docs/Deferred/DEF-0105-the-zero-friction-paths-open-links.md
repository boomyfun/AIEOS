# DEF-0105: the zero-friction path's open links

- Status: open
- Opened: 2026-10-29 (session ea6ea0a3; M7's exit review, decisions D-3323, D-3324)
- Deferred by: decision agent (A41, A51), at M7's exit (`docs/plan/m7-exit-review.md` §3)
- Decision group: A (self-build tasks after M7; launching and real use stay the owner's, DM A51 item (4))

## What
`aieos init`, `import` and `run` are built (TASK-095, TASK-097, TASK-098). The path from an intent to a running task is still open at these links:
- No reader reads the contracts that `import` and `run` write under `.aieos/tasks/`. Who commits them, and how they stay out of an agent's commit, is not settled. This is (r3) of TASK-098's scope, decision D-3277 Q3.
- `aieos import` accepts the root only in its Windows form (decision D-3281). Its end-to-end test leg is skipped off Windows.
- `aieos run`: the same intent and class recorded under another `--by`, on a log that already holds the intent's claim, is refused "conflict" after the template's write. This is G2 of decision D-3315.

## Why deferred
Each link needs its own contract. None of them blocks M7's goal parts, which are built and tested.

## Resume when
The first M8 task that reads `.aieos/tasks/`, or the next task that changes `launcher.import_task` or `launcher.run_task`.

## Depends on
TASK-095, TASK-097, TASK-098; specification 7 §2, §3.

## Log
- 2026-10-29: opened at M7's exit (session ea6ea0a3).

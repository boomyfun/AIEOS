# DEF-0106: text items carried from M7

- Status: open
- Opened: 2026-10-29 (session ea6ea0a3; M7's exit review, decisions D-3323, D-3324)
- Deferred by: decision agent (A41, A51), at M7's exit (`docs/plan/m7-exit-review.md` §3)
- Decision group: A

## What
These are text only, with no change to behaviour:
- `src/aieos_bootstrap/launcher.py` :120-121. The departure from specification 5 :125 is named for `end_outside` alone. TASK-094's `launch_outside` is a second caller (TASK-094's contract, :180).
- `docs/specs/spec-04-verification-and-evidence.md` :61. It asks which source names the implementer's model, an open point for specification 2's next revision.
- The markers `contract_edit` (TASK-096) and `intent` (TASK-098). They are named for specification 2's next revision.
- TASK-098's docstring sentence on the lowercased form, which is classed against lowercased patterns (departure D-3290; G3 of decision D-3315).
- `src/aieos_bootstrap/cli.py` :3 (the docstring), which names "specification 7 revision 2" where revision 3 is in force (G4 of decision D-3315).

## Why deferred
They are text only. Fixing them now would take a code task of its own, so each is fixed with the next revision or task that touches its file.

## Resume when
Specification 2's or specification 4's next revision, or the next task that changes `launcher.py` or `cli.py`.

## Depends on
TASK-094, TASK-096, TASK-098.

## Log
- 2026-10-29: opened at M7's exit (session ea6ea0a3).

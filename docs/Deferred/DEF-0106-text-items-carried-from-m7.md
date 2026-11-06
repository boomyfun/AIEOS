# DEF-0106: text items carried from M7

- Status: open
- Opened: 2026-10-29 (session ea6ea0a3; M7's exit review, decisions D-3323, D-3324)
- Deferred by: decision agent (A41, A51), at M7's exit (`docs/plan/m7-exit-review.md` §3)
- Decision group: A
- Blocks v0.1: no (text only, no behaviour)
- Scheduled in: M8, the launcher text-fix task (launcher, cli), before the M8 exit review

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
- 2026-10-30: TASK-102 (accepted by decision D-3707 at f25b4576; range fb90baaf..f25b4576; records d3a328bd; the map is docs/records/TASK-102.jsonl :44): settled launch_outside named (src/aieos_bootstrap/launcher.py:120-121) and cli.py:3 revision; open the lowercased-form sentence (launcher.py:169), the specification 4 :61 point, the markers. Status stays open.
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass B decision D-5259 and the citation line of D-5269 C1): read in full; the Resume-when event occurred: cli.py was changed by TASK-115 (b8b003f, ba83811, 2026-11-02), launcher.py by TASK-115, TASK-117 and TASK-118, and specification 2 by TASK-117 (7253aa9, 2026-11-04), none of which took the items; open per the Log of 2026-10-30: the lowercased-form sentence (the line the item cites, launcher.py :169, now holds other text and the sentence was not found), the specification 4 :61 point, the markers contract_edit and intent named for specification 2's next revision; added by D-5269 C1: specification 4 :61 cites specification 2 :156 for models while DEF-0103 recorded that the lines are at :163 (spec-02 was not re-read in this pass), and the launcher.py :120-121 point was settled by TASK-102 (the Log of 2026-10-30). State: open; Blocks v0.1: no (text only, no behaviour); Scheduled in: M8, the launcher text-fix task (launcher, cli), before the M8 exit review.

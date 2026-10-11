# DEF-0050: the review findings carried from TASK-023, the stale-evidence computation

- Status: open
- Opened: 2026-10-11 (decisions D-551 and D-552)
- Deferred by: decision agent (A41), D-551 (Q2 and C4: the dispositions of the five way-2 reviews of TASK-023) and D-552 (Q1 and C3: two narrowness points of the fix).
- Decision group: A (tests and readings within the self-build).

## What
- TASK-023 (src/aieos_bootstrap/stale.py, specification 4 section 3 rules 2 and 3 and section 7 item 3) was reviewed at its first task commit 8cc5af05 by five way-2 reviews (all pass, no blocking finding); six findings were fixed in the task's second commit 2b7bf152 (decision D-551) and read by the decision agent instead of a second round (decision D-552). These are carried:
- F3: an unknown key of the inputs is reported only after the nine named keys have passed; this follows AC1's order and needs no change; state it if AC1 is revised.
- F4: extra keys inside a record pass silently, as AC1 says ("other keys ignored").
- F6 and F7: the first task commit's message calls the four readings of decision D-544 "of what cannot be checked" and says all 25 of TASK-022's records are stale "after a later change"; one of the 25 is stale by the rule that treats a commit of unknown order as earlier. The second commit's message corrects both; both messages stay as pushed.
- F8: the unit test of the module's effects checks a fixed list of names; its docstring reads broader than that list (the import test covers the rest).
- F9: a changed path with about a thousand or more "/" separated names could make resume_check's recursive matching raise RecursionError, which stale calls; the same limit applies to resume_check itself (its own area, DEF-0035), and TASK-023 could not change resume_check.
- F10: trigger_commit is not required to be one of the base commits; the facts are the caller's.
- Two points of the fix (decision D-552 Q1): the empty patterns list is uncovered for every kind of entry, but the new test covers it for interface and schema entries only; the second commit's message names only interface and schema entries.
- The readings that TASK-023 states as proposed (decisions D-544 Q2 points 1 to 4, D-548 Q2 and Q3, D-551 Q2) wait for specification 4's next revision to be adopted or replaced.

## Why deferred
D-551 Q2: these findings are non-blocking, and fixing them was not worth a further round; the ones that touch resume_check or the specification belong to their own change.

## Resume when
- F9: at the next task that changes resume_check, or the task that gives the core a caller of stale (DEF-0030).
- F3, F4, F6 to F8, F10 and the two fix points: at a later task that changes stale.py or its tests.
- The readings: at the next revision of specification 4.

## Depends on
Nothing.

## Log
- 2026-10-11: opened (decisions D-551 and D-552; session 953a7328).

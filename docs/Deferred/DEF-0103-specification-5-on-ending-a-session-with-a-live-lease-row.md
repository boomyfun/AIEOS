# DEF-0103: specification 5's sentence on an unexpired lease row, against `aieos end`

- Status: done
- Opened: 2026-10-25 (session ea6ea0a3; TASK-092's records, decisions D-3047 (c1), D-3051 Q1 and R5b, D-3076)
- Deferred by: decision agent (A41, A51), D-3051 R5b (found by the contract's reviews rv92a F5 and rv92b B2; a
  specification text, not a code change).
- Decision group: A (a revision of specification 5, within the self-build; the specifications' owner rules apply).
- Blocks v0.1: no (done)
- Scheduled in: none (done)

## What
Specification 5 revision 5 :125 says, in point 10's general rule for every core-written gone record, that "a session
whose lease row is still unexpired is not processed", and that the record's recorder says it was written without a
held lease. TASK-092's launcher.end_outside (`aieos end <session>`, specification 7 :48, specification 5 :119) writes
that record for a crashed session whose lease row may be unexpired, before the release, as specification 5 :112 and
specification 7 :45 require. Its recorder names the row as possibly unexpired (", its lease row possibly unexpired",
decision D-3051 R5a), and read_set_record's GONE_JOIN text ("written by the core without a held lease",
read_set_record.py :208) is true of the writer but not of the session while the row is live. TASK-092's contract
states the departure (decisions D-3047 (c1), D-3051 Q1).

## Why deferred
The code follows the later and more specific text (specification 7 :48, specification 5 :112, :119); the sentence of
:125 needs a revision that names `aieos end` as the path that writes the record before the release on a possibly live
row, and GONE_JOIN's wording read with it. A specification revision is its own change.

## Resume when
At the revision of specification 5 planned before TASK-096 (MYSP/m7/m7-rest-plan.md); this item closes when :125
names `aieos end` and its live-row case, and GONE_JOIN's reading is stated.

## Depends on
TASK-092 (end_outside), TASK-089 and TASK-090 (the gone records), specification 5 revision 5, specification 7
revision 2.

## Log
- 2026-10-25: opened with TASK-092's records (session ea6ea0a3; decisions D-3047, D-3051, D-3076).
- 2026-10-25: closed by specification 5 revision 6 (DM F66; decisions D-3184 to D-3189): section 11 point 10 (:125) names the two paths through the core's outside end, `aieos end <session>` and the launcher's own fallback, as writing a gone session's record before the release while its lease row may be unexpired, the recorder naming the row as possibly unexpired, and reads "without a held lease" as said of the writer; carried to the next task that touches them: launcher.py :120-121's "departs from specification 5 :125", now out of date, and specification 4 :61's citation of specification 2 :156 for `models`, which is at :163 (session ea6ea0a3).
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass F batch 3, decision D-5269 (C1)): the Status word 'closed (2026-10-25; DM F66)' is not a value of the README and is changed to 'done' under D-5269 C1 and C4; the facts stay in the Log of 2026-10-25 (closed by specification 5 revision 6, DM F66); the two points carried there: launcher.py :120-121 was settled by TASK-102 (DEF-0106's Log of 2026-10-30), and the specification 4 :61 citation of specification 2 :156 is carried in DEF-0106. State: done; Blocks v0.1: no (done); Scheduled in: none (done).

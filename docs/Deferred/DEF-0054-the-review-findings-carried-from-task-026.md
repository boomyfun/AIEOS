# DEF-0054: the review findings carried from TASK-026, recovery at start

- Status: open
- Opened: 2026-10-12 (decision D-626)
- Deferred by: decision agent (A41), D-626 (the dispositions M1 to M7 of the five round-2 way-2 reviews; M1, M3 and M7 carried) and D-627 (C5).
- Decision group: A (robustness against hostile stand-ins and a documentation point within the self-build).

## What
- **M1, a lease list iterated twice** (round-2 reviewer R2): recover iterates the leases read in AC4 once in reconcile and once in the release step; a list subclass whose iteration raises only on its second pass would let an exception leave recover, against AC10. The fix named: take list(held) inside the try that reads the leases.
- **M3, the trusted PATH limit** (R4): startup.py's docstring states the PATH precondition but not gitread's own caveat that the refusal of an empty or relative entry closes that route on POSIX only. The fix named: add "on POSIX only" to that limit.
- **M7, a task_id whose text form raises** (R4; added by the decision agent in D-626): a hashable task_id whose __str__ raises would escape through a finding's text formatting. The fix named: a guarded finding text.

## Why deferred
M1 and M7 are reachable only through hostile stand-ins: the real writer returns plain lists of leases whose task ids come from the store as text; M3 is documentation completeness, and AC13 requires only the precondition. A third fix commit would have needed another review round for no change in real behaviour (D-626).

## Resume when
At the next task that changes src/aieos_bootstrap/startup.py.

## Depends on
DEF-0030 (the core's caller); TASK-026.

## Log
- 2026-10-12 (session 4b3931cd): opened. TASK-026 accepted at 1f6ff6d8 and on `main` (decision D-627; records 325d13c6, D-628). ../History/2026-10/2026-10-12-0833-recovery-at-start-accepted-and-on-main.md

# DEF-0059: the review findings and limits carried from TASK-032, the execution path

- Status: open
- Opened: 2026-10-15 (decision D-692)
- Deferred by: decision agent (A41), D-692 (the dispositions P1 to P14 of the five way-2 reviews; the items carried) and D-693 (C3).
- Decision group: A (limits of the execution path within the self-build).

## What
- **CONTINUE with a state effect** (R2, R3; P6): a record whose decision is CONTINUE or CONTINUE_WITH but whose state_effect is not empty is appended with its effect and then granted the lease; it is not refused. The real resume_check.check never gives such a record (its _effect returns no event for those decisions), so only a stand-in check can; tests show the grant comes after every event.
- **A valueless "done" release** (R2; P14): a StoreResult with result "done" and no value gives released None in the result. The real writer.release_lease_token always returns the removed lease.
- **Leases out of form in the property worlds** (R3; P7): the property worlds now refuse appends, but never hold an expired or malformed lease; unit tests R2 and R11 cover those cases.
- **The kept lease's unchecked holder** (R1; P13; decision D-687 M4): on CONTINUE or CONTINUE_WITH for a task IN_PROGRESS, the kept lease is the store's held lease; whether grant_request's holder and session hold it is not checked, since writer.held_lease gives no holder. Carried to the caller (specification 3 section 1, "a lease it still holds").
- **A partial state effect** (R4; P8): a crash, or a refused or raising append, can leave a record with only part of its state effect (for example decision.execution and its conflict.detected without its task.blocked). The next Resume Check decides again under a new log_seq and appends a new record and its whole effect; the earlier partial effect stays in the append-only log.

## Why deferred
D-692 accepted the dispositions: each case fails closed or is a stated limit in execution.py's docstring, and the real Resume Check and writer never produce the first two. (The worker's reason, not part of D-692: refusing more in these cases would change the text of an approved criterion, AC4 or AC7, beyond erratum E2.)

## Resume when
When a module first calls execute (the session start of specification 3 section 1, in a later milestone), when writer.held_lease is changed to give the holder, or at the review point at M4's exit.

## Depends on
TASK-032 (accepted, decision D-693); TASK-008 (resume_check.py); TASK-016 and TASK-028 (writer.py); DEF-0030 (point (i), the Resume Check's READY -> STALE alignment).

## Log
- 2026-10-15: opened (decisions D-692 and D-693; session 8dcd35e9).
- 2026-10-15 (session 218e5c55): M4 exited with named limits (decision D-756; docs/plan/m4-exit-review.md §3, after the owner chose Option C on 2026-10-15). Limit L-c: no module calls execute yet; the session-start caller of specification 3 section 1 comes with the runtime of M5 to M7.

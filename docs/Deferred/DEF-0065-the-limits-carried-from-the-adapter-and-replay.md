# DEF-0065: the limits carried from TASK-051 (the adapter–core interface and the replay adapter)

- Status: open
- Opened: 2026-10-16 (decision D-997)
- Deferred by: decision agent (A41), D-997 (TASK-051's acceptance), with D-996's findings F1 to F3.
- Decision group: A (limits of an accepted task, carried for later tasks).

## What
- **F-a** (D-988): the repository has no project-state directory yet, so the replay's empty-log rule cannot tell a fresh scratch root from the self-build's own root before its first event; replay has no caller, and a caller must give a fresh root.
- **D2 with F1** (D-991, D-996): a start refused by the core leaves its session row open; when the grant itself raised, whether a lease was granted is unknown, so a lease may stay held until it expires (the lease's expiry is the fallback, specification 5 §11 point 10).
- **F2** (D-996): the adapter's fencing_token check is stricter than AC1's "a mapping or None" (exactly {epoch: a non-empty text, counter: an int at least 0}), a reading.
- **F3** (D-996): the AST-only "no token compared" test (D11) has a limited reach.
- No observed read-set call (specification 5 §7; the record keys are for specification 2's next revision, §11 points 3 and 4); the violation call is TASK-052's.
- Abnormal ends beyond the lease's expiry not handled (§11 point 10); the lease's write-set neither passed nor enforced; the token taken from the grant, not the document (M2 of D-983); a run against the real writer's files not tested; `__all__` does not name adapter or replay.

## Resume when
- A task that gives replay a caller (F-a); specification 2's next revision (the observation call); or a task on abnormal session ends.

## Log
- 2026-10-16: opened (D-997).

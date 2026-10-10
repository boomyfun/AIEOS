# DEF-0039: specification 1, recovery step 1 and a lease past its expiry

- Status: open
- Opened: 2026-10-11 (decision file D-390)
- Deferred by: decision agent (A41), D-390 (reading (t1) for TASK-009; the tension carried to the specification's next revision, as DEF-0026 carried an earlier one).
- Decision group: A (a specification revision under A51).

## What
- Specification 1 section 7 step 1 counts "a lease on that task which the local store still holds (this step runs before step 5)"; its parenthetical reads as counting a lease past its expiry that the store has not yet expired.
- Section 8 refuses a submission "whose lease has passed its expiry time even if the store has not yet expired it", and concept line 849 says an expired lease is expired, whatever its holder believes; TASK-007's eventlog.append refuses such a submission with reason fence.
- Both sentences are proposed (section 10 point 10). TASK-009 follows section 8 (reading (t1), D-390): a commit made under a lease past its expiry gives the unfenced-write observation, never a compensating submission.
- The next revision of specification 1 should say so in section 7 step 1, or decide otherwise with its own route.

## Why deferred
D-390: a recorded reading carried to the next revision costs less than a revision round for a point on which the stricter side was taken.

## Resume when
Specification 1's next revision, or any task that changes recovery or the fence.

## Depends on
TASK-009 (done, D-395); DEF-0026 (the same specification's other carried point).

## Log
- 2026-10-11: opened (decision files D-390 and D-395).

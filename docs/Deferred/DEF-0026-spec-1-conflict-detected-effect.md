# DEF-0026: Specification 1's effect of `conflict.detected` and specification 3's STOP: scope invalid

- Status: open
- Opened: 2026-10-10 (decision file D-255 Q4; review finding D1-5)
- Deferred by: decision agent (A41), D-255 Q4: outside DEF-0025's list, so no change in specification 1 revision 2.
- Decision group: A (a specification revision under A51, B9).

## What
- Specification 1 §5.3 gives `conflict.detected` the effect "CONTINUE_WITH or REPLAN (specification 3)", while specification 3 §10 also appends `conflict.detected` for STOP: scope invalid, a write-set collision that is not an interface-breaking CONFLICT. The next revision of specification 1 says which effects a `conflict.detected` can have, with specification 3 §10's three uses.

## Why deferred
Doc-1 (D-254 C2) was limited to DEF-0025's list.

## Resume when
At the next revision of specification 1, and before the contract of TASK-008 (the Resume Check) if that contract relies on the effect.

## Depends on
Specification 1 revision 2 (DM F25); specification 3 (DM F23).

## Log
- 2026-10-10: opened (decision file D-255). ../History/2026-10/2026-10-10-0043-bootstrap-scope-and-m3-documents.md

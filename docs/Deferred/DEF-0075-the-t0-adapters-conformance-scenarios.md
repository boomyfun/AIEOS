# DEF-0075: the T0 manual adapter's conformance scenarios

- Status: done
- Opened: 2026-10-17 (session ee32c9d8; decisions D-1179 Q2 (4) and D-1182 Q3)
- Deferred by: decision agent (A41), D-1182 (a Deferred item of its own; DEF-0072 is done and carries no new open work).
- Decision group: A (a fixture task within M5's approved plan).

## What
- Specification 5 section 11 point 11 (`docs/specs/spec-05-adapter-contract.md` line 108): which conformance scenarios each adapter must pass, beyond ADV-02, for T0 among them, set with their fixtures in tasks of their own (section 9).
- TASK-060 (the T0 manual adapter; contract on main as commit C 59b8c76d, decisions D-1179 to D-1181) leaves them out by its scope (D-1179 Q2 (4); TASK-060.yaml AC7).
- The work: a fixture task of its own after TASK-060's acceptance, naming the scenarios, their fixtures and their freeze approvals (DM B1, B10); TASK-060's acceptance refers to this item.

## Resume when
- After TASK-060 is accepted.

## Log
- 2026-10-17: opened (session ee32c9d8; D-1179, D-1182).
- 2026-10-17: TASK-060 accepted at ec78a88c and on main (session 2375f48d; decision D-1195, records commit 9a342e19); the resume condition is met.
- 2026-10-17: done (session 1947b313; decision D-1206): set version 2 holds no scenario that names T0 (docs/pre-genesis/conformance-scenarios-initial.md:10 tags capabilities only; :64, ADV-02, the only row naming a tier); the behaviour T0 relies on is covered at the governor and Resume Check level by ACC-09, ADV-03 and RC-09, and by TASK-060's own tests on claim records. If a later set version adds a row that names T0, the route is a T0 runner route and fixtures in tasks of their own (option A of D-1206). Specification 5 point 11's other part, the lease and fencing flow, is not touched by this close.

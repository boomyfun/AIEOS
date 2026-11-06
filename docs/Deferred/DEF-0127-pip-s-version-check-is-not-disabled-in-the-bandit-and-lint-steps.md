# DEF-0127: pip's own version check is not disabled in the bandit and lint steps

- Status: open
- Opened: 2026-11-05 (session 6550f093-c843-41f2-99ca-c427579f48bf; TASK-119, decision D-4897)
- Deferred by: decision agent (A41, A51), D-4897 (C8)
- Decision group: A (self-build)
- Blocks v0.1: no (pip's own version check is a network read outside the pinned install, in two steps)
- Scheduled in: M8, the CI workflow revision task (each change its own A66 decision), before the M8 exit review

## What
The `static_security_analysis` (bandit) step of `.github/workflows/aieos-checks.yml` and the new lint step of TASK-119 both install their pinned package with pip. Pip may also read its own version-check page (a network read that is not part of the pinned install). Neither step disables that check. D-4897 (iii) ruled the point valid: the lint step's header names it (the step stays unchanged), and one DEF entry covers the same check in both steps.

## Resume when
A task that changes the bandit step or the lint step next (for example TASK-119 r6 or a later hardening task) decides whether to disable pip's version check in both steps; a change under `.github/` is its own A66 decision bound by SHA-256.

## Follow-ups owed
- A later task decides, for both steps together, whether to set the pip option that disables the check, and records the choice.

## Depends on
TASK-119 (stopped under AC4); DEF-0118.

## Log
- 2026-11-05: opened (session 6550f093), from D-4897 C8 (recorded in the records batch of D-4906).
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass E decision D-5258): read in full; the Resume-when event (a task changing the bandit or the lint step) occurred: TASK-124 added the lint step (2026-11-06) and the choice was not made there. State: open; Blocks v0.1: no (pip's own version check is a network read outside the pinned install, in two steps); Scheduled in: M8, the CI workflow revision task (each change its own A66 decision), before the M8 exit review.

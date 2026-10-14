# DEF-0060: the review findings and limits carried from TASK-033, scope drift

- Status: open
- Opened: 2026-10-15 (decision D-707)
- Deferred by: decision agent (A41), D-707 (the dispositions P1 to P17 of the five way-2 reviews; the points carried to TASK-034) and D-708 (C3).
- Decision group: A (limits of the scope-drift computation within the self-build).

## What
- **The caller strips rule keys** (R4; P3; reading (a) of decision D-705): scope_drift.claims takes the policy's rules only in the form {match, class}; a rule with any other key, such as the governor's "id", makes no path non-task. TASK-034, the caller, translates the policy's section 3 block ({paths} or {component_tags} with risk; R3 as every path under src/** and tests/**) into that form and strips any other key.
- **An error is a stop** (R2; P1): a result whose error is not None says nothing about drift (no event, detected and exempt false). The caller must treat it as a stop and name it, never as "no claim".
- **The commit-only id** (R2; P4; reading R2 of decision D-702): a rerun for the same commit with other facts (another write-set version, another list) gives the same event id with another payload, which the writer refuses as a conflict; the caller states which facts a run used.
- **A merge** (AC3): a commit with other than one parent gives no event and is named as uncovered; reading a merge's paths against its first parent is the caller's (DEF-0058's merge limit).
- **Narrow tests kept** (R3, R5; P13 to P15, P17): the property worlds hold at most one trailer and fixed rules; the class-equality test does not cover every path form of every rule; odd input forms reach the no-exception rule through the malformed-form test and a patched matcher only.

## Why deferred
D-707 accepted the dispositions: each case fails closed or is a stated limit in scope_drift.py's docstring, and the caller, which reads the facts and appends the event, is TASK-034's (decision D-702).

## Resume when
At TASK-034's scope note (the scope-drift caller), or at the review point at M4's exit.

## Depends on
TASK-033 (accepted, decision D-708); TASK-031 (reconcile.py); TASK-016 and TASK-028 (writer.py); DEF-0030 (the core's caller); DEF-0058 (the merge limit).

## Log
- 2026-10-15: opened (decisions D-707 and D-708; session c5a72bcd).

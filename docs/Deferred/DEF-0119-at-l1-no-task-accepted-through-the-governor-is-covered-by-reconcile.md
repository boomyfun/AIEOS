# DEF-0119: at autonomy level L1 no task accepted through the governor is covered by reconcile, because the governor never gives the ACCEPT decision that reconcile requires (found at the M8 events plan, D-4711 to D-4713)

- Status: open
- Opened: 2026-11-03 (session 08342c65; decisions D-4711 to D-4713)
- Deferred by: decision agent (A41, A51), D-4718
- Decision group: A (self-build)

## What
At the self-build's autonomy level L1 the governor's acceptance record never carries the decision ACCEPT: row 4 (ACCEPT, next state ACCEPTED) needs L2 or above and "never reached now" (governor.py:474-475, LEVEL_AT_LEAST_L2 False at governor.py:55); a re-evaluation that finds an approval record that counts keeps the decision NEEDS_REVIEW and sets only next_task_state to ACCEPTED (governor.py:476-482). The reconciliation caller reads the other way: a DONE task's accepted commit is taken from its decision.acceptance record only when that record's decision is ACCEPT; a record whose decision is not ACCEPT leaves the task uncovered, fail closed (reconcile.py:8-12, :214-215). Two further facts: no function in src writes task.done (it is read by reconcile.py:203, metrics_report.py:348, :361 and execution.py:150, :543; only its form is in records.py:276), and the cycle-time figure of the metrics report counts "an accepted task" only by task.done (metrics_report.py:362-381, its limit at :379), while the state names ACCEPTED and DONE are separate (records.py:93-95).
So, with the code as it stands, a task carried to ACCEPTED at L1 (decision NEEDS_REVIEW, next_task_state ACCEPTED) and then given a task.done by a hand-written writer would still be uncovered by reconcile (stale-evidence and drift cover nothing for it), and the report counts a done task only through that same event. This is an inconsistency between two modules, not a defect of either module's own tests. It was found while planning how a first task could be carried through the existing functions (D-4711 to D-4713).

## Resume when
A decision rules how an accepted task at L1 is recorded for reconcile: that reconcile accepts a decision NEEDS_REVIEW with next_task_state ACCEPTED when the acceptance is by an approval record that counts (governor.py:480-482), or that the governor gives a distinct decision value for that case, or that task.done is written with a decision_record that reconcile may read; each is a change to the governor, to the reconciliation caller or to the specification text that governs them, and is its own task (the governor is a security-critical part under risk-rules R3, and a change to it is critical_cr until its identity is bound, risk-rules-gov-aieos.md :74).

## Follow-ups owed
- A task or change request that fixes the inconsistency, after the choice above (not before the owner's answer on the runtime tier below is known, since the first launched task is the first to meet it).
- A writer for task.done, if the choice needs one (new capability; DEF-0099: READY needs a task's dependencies DONE at task.approved, execution.py:55-56, so without a task.done writer no task with dependencies can be granted).
- The M8 exit statement names the three limits (D-4711): no task.done writer in the existing functions; the report counts 0 done tasks and its cost per accepted task is hollow; reconcile covers no task at L1.

## Depends on
D-4711 to D-4713 (the plan and the readings); DEF-0101 (the launcher's open requirements; max_risk is the caller's, DEF-0101:48-50); option O2 of D-4713, the scripted first run of a task through the existing functions on a low docs-only carrier, is HELD on the owner's answer to the runtime-tier question of D-4713; if the answer is "không", O2 is closed and DEF-0101 gets a Log line; DEF-0118 (the lint entry is the second blocker of a low carrier).

## Log
- 2026-11-03: opened (session 08342c65), at the M8 events plan (decisions D-4711 to D-4713, D-4718).
- 2026-11-03 (session 08342c65): before this file was written, the owner answered "có" to the runtime-tier question of D-4713 (D-4719), for the lowest-risk tasks of the self-build only, unmeasured and advisory; O2 is therefore no longer held on that answer, and the Depends-on and Follow-ups text above states the state at D-4718. The answer is recorded in the decision matrix by its own decision.

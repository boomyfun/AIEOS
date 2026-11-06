# DEF-0057: the review findings and limits carried from TASK-030, constitution drift

- Status: open
- Opened: 2026-10-12 (decision D-668)
- Deferred by: decision agent (A41), D-668 (the dispositions P1 to P10 of the five way-2 reviews; P4 and P5 carried as limits; C3, two points for TASK-031's scope) and D-669 (C2).
- Decision group: A (limits of the constitution-drift computation within the self-build).
- Blocks v0.1: no (a non-blocking review finding or limit of an accepted task)
- Scheduled in: M8, the verification-path fix task (ac_coverage, ac_tests, stale, drift, reconcile, execution, evaluation, verification_records, scope_reconcile), before the M8 exit review

## What
- **P4, a pathological scope** (reviewer R2): drift.violations calls governor.matches, which is recursive over a pattern's "/" parts, so a scope of about a thousand parts may raise instead of giving a result. The scopes come from the constitution at the base, trusted input; a guard that treats an exception as "scope cannot be evaluated" would change TASK-030 AC2's approved reading. Stated in the module's docstring.
- **P5, provenance not judged** (R2, R5): a rule result or a task record counts when it is a well-formed G3 observation; its source_class is checked for form only (by records.check_record), so an observation of any class, agent_declared included, counts as a pass or as a suppressing failure. Which channel a record came through is the caller's to establish (DEF-0051). Stated in the docstring.
- **The CI step texts** (decision D-664, AC11): the CI's G3 records in docs/records name a CI step in refers_to, not an article id, so drift counts them as no result and the one-finding rule matches none of them; each applicable article is then named "no rule result".
- **Two findings after a landing that is not a fast-forward** (AC5, AC11): the one-finding rule holds only when the base commit is the task's evaluated commit.
- For TASK-031's scope note (decision D-668 C3): which source classes count as rule results and as suppressing task records (for example the deterministic CI or core channels only), given P5 and DEF-0051; and the mapping of the CI's G3 steps to article ids (decision D-664 C4).

## Why deferred
D-668 accepted the dispositions: P4 and P5 are limits of the inputs the caller gives, not defects of the module against its contract; the mapping and the source classes belong to the caller, TASK-031, which does not exist yet.

## Resume when
At TASK-031's scope note (the reconciliation caller), or when a task changes drift.violations' reading of its inputs.

## Depends on
TASK-030 (accepted, decision D-669); DEF-0051; DEF-0030.

## Log
- 2026-10-12: opened (decisions D-668 and D-669; session 9dbc771d).
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass A batch 2, decision D-5265 with the correction of D-5266): read in full; the event 'TASK-031's scope note' occurred (TASK-031 accepted, D-681) and TASK-031's contract (docs/tasks/TASK-031.yaml :268-:270, :280-:289, :36-:38) states the source-class filter, the mapping helper rule_results_from_steps and the CI-step-names limit, so both points of the scope note were taken in the contract text (the code of reconcile.py was not read); drift.py is unchanged since TASK-102; the CI step texts limit remains a stated limit. State: open; Blocks v0.1: no (a non-blocking review finding or limit of an accepted task); Scheduled in: M8, the verification-path fix task (ac_coverage, ac_tests, stale, drift, reconcile, execution, evaluation, verification_records, scope_reconcile), before the M8 exit review.

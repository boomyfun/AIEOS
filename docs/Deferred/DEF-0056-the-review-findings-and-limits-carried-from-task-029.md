# DEF-0056: the review findings and limits carried from TASK-029, the audit copies

- Status: open
- Opened: 2026-10-12 (decision D-657)
- Deferred by: decision agent (A41), D-657 (the dispositions P1 to P16 of the five way-2 reviews; P8 and P10 carried as limits) and D-658 (C3).
- Decision group: A (limits of the audit copies within the self-build).

## What
- **P8, the order of the two calls** (reviewer R5): evaluation.evaluate_task derives its event id from the task's kept records, and the audit copies are records of the task; so copies written after an evaluation give a rerun of that evaluation a new event id, not a duplicate. The caller calls verification_records.record_evaluation before evaluate_task (stated in the module's docstring). No caller of both exists yet; the core's caller that runs them (DEF-0030) must keep that order or derive the evaluation's event id without the audit copies.
- **P10, a raising append** (R1, R2): when the writer's append raises, the record's status is reported as "not appended" although it may have been appended; the finding says the state is not known, and a rerun is safe (the event id is derived from the record id, so a rerun gives "duplicate" or a conflict).
- Carried from the contract (AC12): records.py does not gain specification 2 revision 3's keys session, ci_run and acs (DEF-0051, line 24); the policy version is not on an audit copy (specification 2 revision 4); at most one record of each name per task and evaluated commit is the caller's duty, and a rerun with other content under the same ids is refused by the writer as a conflict.
- Erratum E1 to AC8 (decision D-655): the decision record is compared in every key except reverify, uncovered and record_id, which is derived from the record's content; the first task commit's message says the audit copies "change no decision value", which E1 states exactly (P9).

## Why deferred
D-657 accepted the dispositions: P8 and P10 are properties of the caller and of the writer's results, not defects of the module; no caller of the core's functions exists yet.

## Resume when
When the core's caller that runs record_evaluation and evaluate_task is written (DEF-0030), or when a task changes either function's event id.

## Depends on
TASK-029 (accepted, decision D-658); DEF-0030.

## Log
- 2026-10-12: opened (decisions D-657 and D-658; session 556c5dd4).

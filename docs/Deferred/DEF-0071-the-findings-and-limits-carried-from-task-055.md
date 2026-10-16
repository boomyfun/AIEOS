# DEF-0071: the findings and limits carried from TASK-055

- Status: open
- Opened: 2026-10-16 (decisions D-1053, D-1054, D-1055)
- Deferred by: decision agent (A41), D-1053 (dispositions J1 to J8), D-1054 (its own review's residuals) and D-1055 (TASK-055's acceptance).
- Decision group: A (limits of an accepted task).

## What
- **J4 (R2):** the rule keys on the outcome value 'fail'; records.py:350 admits only pass, fail and blocking today; a new outcome value would need this rule revisited.
- **J6 (R3):** TASK-055's property test drives out-of-form records only through extra_records, because the log rejects them at append; no out-of-form blocking record is generated. The path is TASK-054's and unchanged.
- **H5 (carried from DEF-0070):** records are selected by the event envelope's task_id, not by the record's subject; for the log, eventlog ties a record.added's task_id to its subject; extra_records are not selected by task_id and the governor skips another subject.
- **A note of decision D-1054:** a record whose id is in form but that governor.py:347-349 cannot write is "not used" by the governor; since it does not count as kept there either, a left-out twin cannot hide anything the governor would use. No action.
- **Limits (TASK-055's AC3 and AC8):** a task with such a record is refused at every evaluation, the rerun included and also after a later task.approved and a new submission, and stays in VERIFYING or IN_REVIEW until superseded by a new task; the rule over-refuses (a left-out 'fail' whose absence changes nothing, such as a stale one or one about another subject, refuses too); one given only through extra_records refuses only while given; event_id_of, the governor and records.py's uniqueness rule unchanged; the limits of TASK-053 (its AC7) and TASK-054 (its AC8) stand; no conformance set or fixture changed.
- J5, J7 and J8 needed no change (D-1053).

## Resume when
- With a hardening task after M5's violation path, or any task that touches evaluation.py or records.py's outcome set.

## Log
- 2026-10-16: opened (D-1053, D-1054, D-1055).

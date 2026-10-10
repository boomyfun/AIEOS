# DEF-0040: TASK-015's non-blocking review findings in the event log's unit tests

- Status: open
- Opened: 2026-10-11 (decision file D-405)
- Deferred by: decision agent (A41, A51), D-405 (TASK-015 accepted with these recorded, no fix in that task).
- Decision group: A (test code and wording within the self-build).

## What
- tests/unit/test_eventlog.py: the kept name test_recorder_and_record_id_are_required_for_a_lease_event now says the opposite of its body (they are not required); TASK-015's AC4 kept the name; rename it, for example test_a_fence_refusal_without_recorder_or_record_id_carries_no_record.
- tests/unit/test_eventlog.py: no test combines no task_id with a missing recorder (the code gives only the task_id finding, since that check comes first), and none covers a lease-needing event other than task.submitted that names no task_id.
- src/aieos_bootstrap/eventlog.py: the second finding text says "recorder and record_id are not both non-empty strings", not which of the two is missing (it is TASK-015's AC3 text exactly).
- tests/unit/test_eventlog.py: the with-and-without matrix checks only the record's subject (the full record is checked for the no-lease cause in R7); a conflict without recorder is untested (the order makes it hold).
- Cosmetic: a duplicated True case in a lease token; one mis-indented continuation line; the module docstring of the test file still names R1 to R7.

## Why deferred
D-405: none weakens a check, and every refusal still appends nothing; a fix would have meant a second task commit, a push and new reviews for wording and test depth.

## Resume when
The next task that changes tests/unit/test_eventlog.py or src/aieos_bootstrap/eventlog.py.

## Depends on
TASK-015 accepted (done, D-405).

## Log
- 2026-10-11: opened (decision file D-405).

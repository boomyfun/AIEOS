# DEF-0032: TASK-007's review findings, two departures from its contract's literal text among them

- Status: open
- Opened: 2026-10-10 (decision files D-327 and D-328)
- Deferred by: decision agent (A41), D-327: none of the findings is blocking; nothing is ever appended wrongly (every departure fails closed); no caller exists yet, and the writer task (DEF-0030) defines the first caller; a fix now is a new commit that makes the five reviews and the CI run stale.
- Decision group: A (code, test and wording changes in a later task touching the event log's append rules or their tests).

## What
Findings of TASK-007's five way-2 reviews on claude-sonnet-5-5 and of the decision agent's reading (commit 9803593c13dbd34a73710f772a60203450e225c4; D-327 dispositions):
- **F-a, a departure, not met (resolve by or before the writer task's acceptance, DEF-0030):** a lease-needing call (an event with a fencing_token, or task.submitted) without `recorder` and `record_id` raises ValueError before the log check, the duplicate check and the fence decision. So a retried, already logged submission without them raises instead of giving "duplicate" (AC2), a task.submitted without a token and without them raises instead of "refused" with reason "fence" (AC6), and AC1's parameter list and result set do not name these arguments or this exception. One fix (way-2 R5): decide the requirement after the log and duplicate checks, and either keep raising or return "fence" with no record.
- **F-b, a departure, not met (resolve with F-a):** a task.submitted that names no task_id gives "refused" with reason "event", not "fence" (AC6's last sentence), because the refusal record's subject must be a task id.
- **F-c:** eventlog calls records' private helpers (`_is_str`, `_matches`, `_check_fence`); any change to records.py re-runs eventlog's tests.
- **F-d (test strength):** the test named `test_true_and_one_are_not_the_same` adds an unknown key and does not test True against 1, so that distinction is shown by reading only; untested too: True against 1 and 1 against 1.0 in a lease token, a payload that is not an object, an expiry with a non-zero offset, a retry of a submission after its lease expired. Rename the test and add the cases in the next task that touches these tests.
- **F-e:** AC11's limits are stated in the module docstring but no test asserts them "as such".
- **F-f (wording):** "duplicate" for a retried submission says nothing about the lease now (it is returned before the lease is looked at); the expiry is judged against the caller's time; the refusal record's refers_to names an event that is never on the log, and refused_submission is used for any fenced event; the docstrings could say so.
- **F-h (noted):** the AC5 re-check cannot fail as built; integer dictionary keys serialise like string keys in the sameness text (only invalid or foreign input).
- **F-i (wording):** a test comment names the owner's language; "non-ASCII text" is neutral.
- Lines in DEF-0024: F-g (the deterministic_rule's "compile" ban matches bare names only, so `re.compile` passes by the rule's blind spot) and way-2 R2 F2 (the SEC-002 step checks e-mail and URL patterns only; unrelated project names and account names are not machine-checked).

## Why deferred
D-327: the acceptance record (docs/records/TASK-007.jsonl, decision D-328) states F-a and F-b as departures and the other limits.

## Resume when
At the writer task's contract (DEF-0030), which must resolve F-a and F-b by or before its acceptance; and at the next task that changes eventlog.py or its tests.

## Depends on
TASK-007 accepted (D-328) and on `main`.

## Log
- 2026-10-10: opened (decision files D-327 and D-328).

# DEF-0070: the 'fail' gap of the evaluation and TASK-055's carried contract

- Status: done
- Opened: 2026-10-16 (decisions D-1035, D-1041)
- Deferred by: decision agent (A41), D-1035 (H2, H5, H8 carried at TASK-054's reviews), D-1038 (TASK-054's acceptance) and D-1041 (TASK-055's contract carried to the next session).
- Decision group: A (a limit of an accepted task; the order of work within an approved scope).

## What
- **H2, the gap, with its consequence:** at 56675042, evaluation._kept leaves out with a finding only a record whose outcome is 'fail' when its record_id repeats a kept record's. The governor then does not see that failed gate or entry, so a log the writer can produce can turn a decision that would be NEEDS_REWORK (and REWORK) into another decision, ACCEPT included. Stated in evaluation.py's docstring. Found by the five way-2 reviews of TASK-054 (R2, R5).
- **TASK-055, scoped (D-1039, D-1040), its contract not started:** after _kept, the evaluation is refused with reason "records" when _kept has left out, for a repeated record_id, an in-form record whose outcome is 'fail', unless the left-out record equals the earlier kept record with that record_id as a whole mapping. Left-out 'pass' records and out-of-form records that are not blocking stay left out (their absence cannot raise the decision: governor.py 334-336, 344-346, 351-353 with 384-386, 354-369, 309, 317-318, 429-430, 463-482, read at D-1040). The over-refusal of a stale or authority 'fail' (whose absence changes nothing) is stated. The cost: such a task is refused at every evaluation and stays in its state until superseded. The reason "records" is reused (C-b of D-1027 holds). The write-set: src/aieos_bootstrap/evaluation.py, tests/unit/test_evaluation_repeated.py (R7Script's words only: lines 454 and 458 assert the sentences that change) and a new tests/unit/test_evaluation_failed.py; risk high and change class critical_cr by script (risk_class55.py, gov003_class55.py). The checks before the contract (D-1040 C2 to C4): only test_evaluation_repeated.py and test_evaluation_violation.py read evaluation.py's text, and only the former asserts the sentences that change; evaluation.py:109 and governor.py:33 and :337 use the same records.check_record; no 'fail' record in test_evaluation_repo.py or test_evaluation_properties.py. It changes TASK-027 AC7's and TASK-054 AC2's prescribed behaviour for that case only.
- **The contract's AC requirements (D-1040 C5):** in TASK-054's form: the rule; what does not change; the cost; the texts; the tests, with failing cases for both orders (pass then fail refuses; fail then pass goes on as the base) and for the whole-mapping twin; the limits. The header cites evaluation.py:109 and governor.py:33 and :337 (D-1040 C3).
- **H5 (reading):** records are selected by the event envelope's task_id, not by the record's subject; for the log, eventlog ties a record.added's task_id to its subject; extra_records are not selected by task_id and the governor skips another subject; out of scope (D-1040).
- **H8:** TASK-054's property test has no case of the exception; covered by its R3GoesOn tests.

## Resume when
- At the next session's start, after the decision files D-1030 onward: TASK-055's contract first; then ADV-02's fixture (D-1039).

## Log
- 2026-10-16: opened (D-1035, D-1038, D-1041).
- 2026-10-16: done (D-1055): TASK-055 accepted and landed on main by a fast-forward to 11831af1, after its contract (D-1045), the owner notice (D-1046, D-1047), five way-2 reviews (D-1052, D-1053), fix J and the decision agent's review (D-1053, D-1054); H5 and the limits carried in DEF-0071.

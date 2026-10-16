# DEF-0066: TASK-052's carried reviews and acceptance (the violation path)

- Status: done
- Opened: 2026-10-16 (decision D-1003, with its amendments 1 and 2 and D-1004)
- Deferred by: decision agent (A41), D-1003 Q3 (the bands).
- Decision group: A (the order of work within an approved contract).

## What
- **TASK-052** (the violation path; contract revision 1, commit C 1fa22a1f on main, decisions D-999 to D-1001): its first task commit 004a7921 on task/TASK-052 (D-1003), whose aieos-checks run 324 failed at bandit (B105, a constant beside a token-named key in a test list); the fix as the second task commit 31071c15 (D-1003 amendments 1 and 2, D-1004), run 325 passing every step including bandit. The decision agent read the code in full at the first task commit (D-1003).
- **Left:** five way-2 reviews at 31071c15 on a model other than the main session's, their briefs naming N1 to N3 below; the decision agent's own review, the other half of the cross-model entry; the acceptance and the landing on main (main has moved past commit C, so a rebuilt landing, as TASK-051's).
- **Findings for the reviews and the acceptance** (D-1003): N1, test_replay's first R10 case builds a document that still has a submission; N2, AC3's refusal at each step is tested for the appends only by exceptions, not by a refused result other than the fence; N3, the property test varies only the event_id.
- **Readings approved** (D-1003): c1, a violation with no granted lease gives "violation" and still calls end; c2, adapter.violation's decision from record's appended and duplicate lists; c3, the fence result names the writer's refusal record's result. The quotation of specification 3 line 106 in violation.py uses "section 5.3" for the section sign, not verbatim.
- **Limits to carry at acceptance** (the contract's AC8): a STOP: violation does not yet make acceptance reject (evaluation.py passes the governor only record.added payloads); violation.record is called only by adapter.violation, and that only by replay and the tests, until a later task widens the evaluation; the task stays READY with no lease after a STOP: violation; no bound on repeated stops (specification 5 §11 point 12); a fence refusal's record is labelled refused_submission; F-a kept.

## Resume when
- At the next session's start, after the decision files D-993 onward.

## Log
- 2026-10-16: opened (D-1003, D-1004).
- 2026-10-16: done (D-1010): five way-2 reviews at 31071c15, all pass (D-1008); the dispositions D1 to D16 and the decision agent's own review, pass (D-1009); accepted and landed on main as two rebuilt commits ending at fe95a1e9 (D-1010); its limits and findings carried in DEF-0067.

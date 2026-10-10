# DEF-0042: specification 4's open points for other documents, and RISK-01's three steps

- Status: open
- Opened: 2026-10-11 (decision files D-428 and D-429)
- Deferred by: decision agent (A41), D-428 (Q3: one Deferred item for specification 4's open points 7, 8 and 10 to 12) and D-429 (RISK-01's three steps).
- Decision group: A (documents and tasks within the self-build; the policy change of point 11 is critical_cr).

## What
- Specification 4 (`docs/specs/spec-04-verification-and-evidence.md` revision 3, DM F32), section 12:
  - point 7: whether the governor specification should name section 6's AC coverage finding (a blocking record that the governor's row 2 reads now) as a missing gate result, and how a corrected contract clears such a record (governor rule 4 keeps a blocking record blocking);
  - point 8: a record key for the acceptance criteria a gate covers, and the source that names the implementer's model for the review-model check (specification 2's next revision);
  - point 10: whether the governor reads the profile and risk records of sections 4 and 8 instead of computing its own, and whether section 3's rule 3 should also make a record stale for the governor (the governor specification's revision);
  - point 11: the list of non-task paths for scope drift (section 7 item 2), a change to the policy (critical_cr), not made by the specification;
  - point 12: the policy's machine-readable form at the base, and which path rules report as G0 and which as G3.
- RISK-01 (the set's only Risk Engine scenario) is NOT_RUN for want of a fixture, and a fixture of conformance-files.md section 4 cannot run its classification. Three steps (D-429): (1) conformance-files.md revision 6, a Risk Engine section (drafted in session 9dd21f8f's scratchpad, accepted for review by D-430); (2) TASK-017, the runner's Risk Engine entry (an evaluator change, critical_cr); (3) TASK-018, the RISK-01 fixture and the set file's entry, the set file's freeze before the task (conformance-files.md section 7, revision 5).

## Why deferred
D-426 approved specification 4 with these points open, as F23 did for specification 3; each needs another document's revision or a policy change, each its own decision. D-429: the three steps follow M3's route for the Resume Check scenarios.

## Resume when
- Points 7, 8, 10 and 12: at the next revision of the governor specification or of specification 2, or when a task's contract needs one of them settled first.
- Point 11: when the scope-drift claims of non-task commits are to be closed by a policy list instead of one decision each.
- RISK-01: step 1 at the start of the next session (the reviews of revision 6, with D-430 C1's four points), then steps 2 and 3.

## Depends on
Specification 4 approved (done, F32; 75cfc58d).

## Log
- 2026-10-11: opened (decision files D-428, D-429 and D-430; session 9dd21f8f).
- 2026-10-11: step 1 done: the conformance files' revision 7 approved (DM F33, decision D-441) and on `main` (284babab); step 2: TASK-017's contract approved (D-446) and on `main` (f1b218c9); its code written in a scratchpad clone and archived as a patch, not pushed, not reviewed (D-448); session a212bf73.

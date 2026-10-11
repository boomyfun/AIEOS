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
- 2026-10-11: step 2 done: TASK-017 accepted (decision D-458) and on `main` (1779085a); step 3 split by decision D-459 into TASK-018 (the fixture), TASK-019 (the runner tests in both states) and TASK-020 (the set file's entry, its freeze first); TASK-018's contract at revision 1, not committed (session 51321169); TASK-017's carried findings in DEF-0043.
- 2026-10-11: step 3, TASK-018: contract on `main` (04d2598d, D-468); the fixture on task/TASK-018 at c2057385, reviewed and fixed, CI run 131 success; the decision agent's reviews, the freeze and the acceptance owed (session 38c27ccc); carried findings and erratum E1 in DEF-0044.
- 2026-10-11: step 3, TASK-018 accepted (decision D-478) and on `main` (4238c4bf, records 971f9fcd, DM F34); TASK-019's contract on `main` (72598350, D-483), its code on task/TASK-019 at 2cc87a41, reviews owed (session b94736f9); TASK-019's erratum and TASK-020's four tests in DEF-0045.
- 2026-10-11: step 3, TASK-019 accepted (decision D-493) and on `main` (b4984b70, records e3198199); TASK-020's set file frozen first (decision D-496; DM F35, a87f84e9); its contract next (session d662611e); TASK-019's carried findings in DEF-0046.
- 2026-10-11: step 3 done: TASK-020 accepted (decision D-507) and on `main` (bc45ece8, records 456e7fd8); RISK-01's set entry names the frozen fixture of DM F34 under the set freeze of DM F35; RISK-01's first conformance run is the base run of the next task push (session e6209999); TASK-020's carried findings in DEF-0047.
- 2026-10-11: RISK-01's first conformance run: the base run of TASK-021's branch push (CI run 150) and of its landing (run 151), over the set file of DM F35: RISK-01 PASS, ADV-02 NOT_RUN, all others PASS (advisory, never MEASURED; decisions D-519, D-522); TASK-021 (the AC coverage check of section 6 item 1) accepted and on `main` (7dac03ec, records 8214134a) without settling point 7; its findings and reading R1 in DEF-0048 (session a447d091).
- 2026-10-11: TASK-022 (the test-to-AC listing of specification 4 section 6 item 2) accepted and on `main` (4ef7dfa9, records 92da3802; decision D-537); it settles neither point 7 nor point 8; its conformance base run (CI run 155) gave RISK-01 PASS again (advisory, never MEASURED); its findings and the 180 untested criteria of the earlier tasks in DEF-0049 (session a067ac68).

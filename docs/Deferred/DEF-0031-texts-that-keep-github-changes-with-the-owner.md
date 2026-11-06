# DEF-0031: Texts that still keep `.github/` changes with the owner after DM A66

- Status: open
- Opened: 2026-10-10 (decision files D-321 and D-322)
- Deferred by: decision agent (A41), D-321 C3: the change-set that records the owner's widening (DM A66, A67; constitution SEC-003 revision 4; Genesis version 4; the decision agent's definition revision 10) changes only those records; until the texts below are revised they stay stricter (fail closed), and a `.github/` change that any pinned check or governor rule still routes to the owner goes to the owner.
- Decision group: A for the plan and the pre-genesis wording within A51's limits; the governor's code is a governor change (critical_cr while its identity is bound; governor-spec §8); the workflow message is itself a `.github/` change, now the decision agent's under A66.
- Blocks v0.1: no (the texts stay stricter, which costs nothing, DEF-0031:18)
- Scheduled in: M8, governor-spec.md lines 165, 196 and 200 when governor-spec next changes, with the pinned governor's path rule and risk rule R9

## What
- Master Plan §9 item 1 ("Creating or changing anything under `.github/` (SEC-003; A51 item (4))"), a `master_plan_update`.
- governor-spec.md lines 165, 196 and 200 (bound item 7): the CI channel's creation, the owner-kept act input built from SEC-003's path rule, and "`.github/` is the owner's".
- The pinned governor's own path rule, if it routes `.github/` to the owner as an owner-kept act.
- The workflow's SEC-003 record step message ("each needs the owner's own yes").
- Risk rules R9 (a risk class, not an approver; probably unchanged).
- The CI workflow's comments on AIEOS_PINNED_GOVERNOR ("changing it is the owner's (DM A61, A63)") and on AIEOS_PINNED_RESUME_CHECK ("changing it is the owner's (DM A61)"); to be corrected in the workflow revision that sets the Resume Check pin, citing A66 and D-317, the governor comment keeping that accepting a new governor version is not decided by a workflow change (decisions D-380 and D-381).
- docs/specs/conformance-files.md section 1: "the CI workflow (the owner's: A61; constitution SEC-003)" (decision D-381).

## Why deferred
D-321: the widening's change-set is one isolated amendment and its records; these follow-on texts each have their own change class, and staying stricter costs nothing.

## Resume when
At the next change to the Master Plan, governor-spec or the governor; at the workflow's next revision (DEF-0030's revision 6 at the latest).

## Depends on
DM A66 and A67 (in force from commit fb841531).

## Log
- 2026-10-10: opened (decision files D-321 and D-322).
- 2026-10-10: the two workflow comments and the conformance files document's section 1 sentence added (decision files D-380 and D-381).
- 2026-10-11: the two workflow comments on the pins corrected by the CI workflow's revision 6 (decision file D-396; emptying the governor pin stays the owner's, DM A65); the SEC-003 record step's message "(each needs the owner's own yes)" stays on the list (D-396 C5).
- 2026-10-29: the SEC-003 record step's message is addressed by the CI workflow's revision 13 (decision D-3613, under DM A66), in the commit that changes .github/workflows/aieos-checks.yml; the Master Plan section 9 item 1, governor-spec.md :165, :196 and :200, the pinned governor's path rule and risk rule R9 remain; Status stays open; the workflow's header grew by six lines, so the CI pin line cited as "aieos-checks.yml :135" in tests/integration/test_launcher_repo.py :107 is cited stale (only that test's docstring cites the line; the test body at :109-111 does not read the workflow at that line; the docstring is not changed by this item).
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass D decision D-5256 and the move into F in D-5267): read in full; moved from the D family to F because its own header calls it group A wording within A51 (D-5256); the Resume-when event (the next change to the Master Plan) occurred at revision 7 (92f0cad2) without the section 9 item 1 edit; open: Master Plan section 9 item 1, governor-spec.md lines 165, 196 and 200, the pinned governor's own path rule, risk rule R9. State: open; Blocks v0.1: no (the texts stay stricter, which costs nothing, DEF-0031:18); Scheduled in: M8, the next Master Plan revision (section 9 item 1), with governor-spec.md lines 165, 196 and 200 when governor-spec next changes.
- 2026-11-06 (session ce14b08a; decision D-5294 C3 (ii); the worker's own claim until checked): Master Plan section 9 item 1 was carried by revision 8 (commit ddce5d66, master-plan.md:129 and the revision 8 line at :160), so the 'Scheduled in' of the line above is stale for that part; master-plan revision 9 (the deferral controls) is again the 'next change to the Master Plan' of the Resume-when and does not touch the other parts; open: governor-spec.md lines 165, 196 and 200, the pinned governor's own path rule, risk rule R9. State: open; Blocks v0.1: no (unchanged); Scheduled in: M8, governor-spec.md lines 165, 196 and 200 when governor-spec next changes, with the pinned governor's path rule and risk rule R9. A Grep of the 'Resume when' sections of docs/Deferred for 'Master Plan' found no other item whose event is a change to the Master Plan (DEF-0030 and DEF-0131 only cite a section).

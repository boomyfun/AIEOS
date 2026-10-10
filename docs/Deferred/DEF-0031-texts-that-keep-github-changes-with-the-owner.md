# DEF-0031: Texts that still keep `.github/` changes with the owner after DM A66

- Status: open
- Opened: 2026-10-10 (decision files D-321 and D-322)
- Deferred by: decision agent (A41), D-321 C3: the change-set that records the owner's widening (DM A66, A67; constitution SEC-003 revision 4; Genesis version 4; the decision agent's definition revision 10) changes only those records; until the texts below are revised they stay stricter (fail closed), and a `.github/` change that any pinned check or governor rule still routes to the owner goes to the owner.
- Decision group: A for the plan and the pre-genesis wording within A51's limits; the governor's code is a governor change (critical_cr while its identity is bound; governor-spec §8); the workflow message is itself a `.github/` change, now the decision agent's under A66.

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

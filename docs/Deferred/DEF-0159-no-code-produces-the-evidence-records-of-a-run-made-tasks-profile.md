# DEF-0159: no code produces the evidence records of a run-made task's profile (the CI-class build and lint records and the review records of the applicable articles), so a correct run-made low task gets INSUFFICIENT_EVIDENCE

- Status: open
- Opened: 2026-11-27 (session 228f426b; the acceptance of TASK-164, D-7474; found at D-7456)
- Deferred by: decision agent (A41, A51), D-7456
- Decision group: A (scheduling; D-7456 C4 sends back to the owner, under DM A82, any change of governor.py, the profiles or the policy)
- Blocks v0.1: yes (master-plan.md :117 expects ACCEPT or NEEDS_REVIEW for the correct change of the first real run; without a producer of the profile's records the governor gives INSUFFICIENT_EVIDENCE)
- Scheduled in: M8, the task after TASK-164, with a design decision before its contract

## What
The evidence profile of a run-made low task asks for records that no code in src produces. The governor reads them in `_candidate` and `_entry` (src/aieos_bootstrap/governor.py :285-:319): a functional entry is met by a record of the CI source class with that evidence type (build, lint), and a review entry by a record of the kind and class that the table allows. A task with a missing type gets table row 3, INSUFFICIENT_EVIDENCE, with the next state REWORK or ESCALATED unless only human types are missing (:467-:473). For a change under docs/Deferred the missing entries are functional build and lint, the human_review of GOV-004, GOV-005 and OPS-002 and the ai_review of SEC-002 and OPS-003 (docs/tasks/TASK-164.yaml, AC7); other low paths have other applicable articles. The gate maker (gate_records.py) makes gate records only.

If this is not done: no run-made task can reach NEEDS_REVIEW, whatever its change, and master-plan.md :117 is not met.

## Why deferred
TASK-164 carries the owner's answer of DM A82, which changes the plan's G3 step only; adding a producer to it would have widened that answer (D-7456).

## Resume when
TASK-164's acceptance.

## Depends on
TASK-164 (accepted, D-7474); DEF-0156 (the intent versions that the evaluation needs).

## Log
- 2026-11-27: opened (session 228f426b; D-7456 C2, D-7474). Two limits on the design, from D-7456 C4: no record that is not derived from a CI run's own step results gets the CI source class, and governor.py, the profiles and the policy are not changed; if either would be needed, the work stops and goes to the owner. The article reviews have to exist before the evaluation that can give NEEDS_REVIEW.
- 2026-11-27: part A done by TASK-165 (design A1, D-7493; accepted at D-7512, commit fdb4b0f8fd1f207c4f7dbde804666544cf4d6d58, docs/runs/TASK-165-acceptance.md): ci_evidence makes the build and lint records of the derived evidence profile from the verified CI step results (gate_records.type_records); a run-made low task still gets INSUFFICIENT_EVIDENCE, only its article review types missing. The item stays open for part B (the review records), whose design rules are (D-7493 C3 and C5): the maker of review records refuses an entry whose source class is the CI class and any type outside a closed list; it is refused inside a runtime; it binds the commit and the intent versions from the evaluation's own sources; the manifest names the reviews file's SHA-256; no human_authority record is ever written by the worker or an agent on the owner's behalf. unit_test, integration_test and property_test records are not made (D-7493 C6). Docstring gaps to close when part B or a later task changes these modules (D-7511): the guard against the log looks only at records under the same record_id; until TASK-165 no code produced a record of these types; gate_records.py is not on EVIDENCE_DEFINING_PATHS, so that list does not mark a later change of the maker as one that may weaken evidence, and TASK-165 does not change it; a disagreement of the attempts on one of the two steps refuses the whole evaluation; the clause "which ci_evidence refuses" stands apart from the limits sentence in gate_records.py, and ci_evidence.py has no blank line before "The caller's duties:".

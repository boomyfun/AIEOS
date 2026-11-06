# DEF-0130: the word "blocking" in the workflow header carries no advisory label (revisions 14 and 19)

- Status: open
- Opened: 2026-11-06 (session f348bb86-32a8-48b8-b4a0-6b5948013e94; TASK-124, decision D-5173)
- Deferred by: decision agent (A41, A51), D-5173 (the finding ruled) and D-5175 (the entry opened at the acceptance of TASK-124)
- Decision group: A (self-build)
- Blocks v0.1: no (the word 'blocking' in a header comment; no behaviour)
- Scheduled in: M8, the CI workflow revision task (each change its own A66 decision), before the M8 exit review

## What
The per-article way-2 review of TASK-124 (agent a7f9275f650e51b40, claude-haiku-5-5) returned "OPS-003: does not hold" for the revision 19 paragraph of the header of .github/workflows/aieos-checks.yml: the paragraph calls the new lint step "one blocking step" with no advisory label of its own, while the header's first lines say the job's results are advisory. Revision 14 of the same header uses "blocking" in the same sense ("adds one blocking check"). In both, "blocking" describes the step's mechanical effect on the job (a failing step fails the job), not an assurance claim; the decision agent's reading, given at D-5173, is recorded in the acceptance of TASK-124 (D-5175).

## Why deferred
The contract of TASK-124 allowed only added lines (AC2: no existing line changes), so the wording of revision 14 could not be touched there, and a change to revision 19 alone would leave the header inconsistent with itself. A fix needs a new A66 decision.

## Resume when
A later change to the header comment of the workflow, decided under A66 on its exact diff, rewords both paragraphs together (for example "blocking for the job, advisory as to assurance") and says so; it adds no check and loosens none.

## Depends on
TASK-124; DEF-0127 (a later A66 change to the bandit and lint steps may carry both).

## Log
- 2026-11-06: opened (session f348bb86), in the records commit of TASK-124 (decisions D-5173 and D-5175).
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass F batch 3, decision D-5269): read in full; the Resume-when event (a later change to the header comment of the workflow under A66) is not met: the last workflow change, TASK-124, opened this item; a change inside the CI workflow revision task rewords both paragraphs together on its exact diff, adds no check and loosens none. State: open; Blocks v0.1: no (the word 'blocking' in a header comment; no behaviour); Scheduled in: M8, the CI workflow revision task (each change its own A66 decision), before the M8 exit review.

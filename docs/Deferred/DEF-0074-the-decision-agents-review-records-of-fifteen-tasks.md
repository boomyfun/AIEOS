# DEF-0074: the decision agent's review records of TASK-039, TASK-041 and TASK-043 to TASK-056

- Status: open
- Opened: 2026-10-17 (decision D-1092; found at D-1089's reading, widened by the worker's check)
- Deferred by: decision agent (A41), D-1092 (the fix is its own change-set, after TASK-057 has landed).
- Decision group: A (appended correcting records; late reviews by the decision agent). Accepting a gap without the missing review would let a review count where it is not counted, which is the owner's (CR-002 part 4 limit 8); this fix does not take that path.

## What
- **The pattern.** TASK-001 to TASK-036 and TASK-040 each have three decision-agent review records: architecture `human_review`, operational `human_review` (OPS-002's) and architecture `ai_review (cross-model)`. TASK-039, TASK-041 and TASK-043 to TASK-055 each have one, `stands_for` `human_review`, dimension architecture, whose basis says it was also "the cross-model half"; TASK-056 has one, `stands_for` `ai_review (cross-model)`.
- **(i) High tasks TASK-051 to TASK-055:** the cross-model entry is met only by a decision-agent review standing for that entry (`docs/pre-genesis/assurance-model.md` lines 82-85; `src/aieos_bootstrap/governor.py` lines 278-282 match `stands_for` exactly); their one record stands for `human_review`, which a high profile does not have, so a governor reading them finds the cross-model half missing.
- **(ii) Critical tasks TASK-039, TASK-041 and TASK-043 to TASK-050:** the profile has architecture `human_review` and the cross-model entry, and a review standing for `human_review` is never also the cross-model half (assurance-model.md line 85; CR-002 part 4 limit 4); one record meets at most one entry, so one review is missing.
- **(iii) OPS-002's `human_review`** (an applicable article's `evidence_required`, constitution.md line 134) has no decision-agent review record in TASK-039, TASK-041 and TASK-043 to TASK-056.
- **The dimension question:** governor.py lines 251-256 join an article's `evidence_required` under a dimension named by the article's id, while the older records use "operational"; settled by the governor run the fix shows.
- **The acceptances were the decision agent's.** It approved those tasks on less evidence than the bound text asks for (D-1092).
- **The records' form (D-1098).** No records file of the self-build holds the `intent_versions` key, so the governor's evaluate uses none of their observations ("not used: no commit binding", governor.py lines 357-359); run over TASK-056's records it gives INSUFFICIENT_EVIDENCE with every gate and entry missing. The contracts' intent versions are file hashes, while the governor reads only `v<n>`: how the two map is a design question, not a field to fill (an empty map would bind vacuously, D-1098). An article's evidence is read only from records whose dimension is the article's id (governor.py lines 250-256), while the records use concept dimensions. Fixes after a review that only the decision agent read in earlier tasks (for example TASK-056's third commit) are to be checked against "both bound to the evaluated commit" (assurance-model.md line 85).
- **Order of the fix (D-1098).** First a decision, as a task of its own, on how records become readable by the governor; then the governor's before-and-after check of the fix below. Until then, an acceptance's coverage is checked by a per-entry script (one planned record per profile entry and per article entry, none counted twice), with the governor's output reported as data.

## The fix (D-1092 (b))
1. Records are appended, never edited.
2. (i): for each of TASK-051 to TASK-055, a correcting record only where the acceptance decision's own text shows the review was made as the cross-model half, citing the decision file and its lines and the original record id; otherwise as (ii).
3. (ii) and (iii): never one review counted twice; either a second, distinct review that the acceptance decision's text shows was made, cited by its lines, or a new review by the decision agent now, at the task's accepted head, for the missing entry, recorded with its date and "made after acceptance". If a late review does not pass, that task's acceptance comes back to the decision agent as its own decision.
4. No record and no text says a gap is acceptable without the missing review.
5. Each fix change-set shows the governor's evaluation over each task's records at its accepted head before the fix (which entries are missing) and after it on a scratch copy (none missing), the decision lines it cites and every new record's exact text; late reviews in batches of at most five tasks per request.

## Resume when
- After TASK-057 has landed on main: a plan request choosing between TASK-058's scope and this item's first step (the records' readable form), with the decision agent's ruling (D-1100 C3).

## Log
- 2026-10-17: opened (D-1092); widened by the records-form finding (D-1098).

# DEF-0017: Align B3 and B4 with A35 and A36

- Status: done
- Opened: 2026-10-06 (../History/2026-10/2026-10-06-1741-close-def-0006-and-def-0010.md)
- Deferred by: owner. To Claude's question 1 (session 02bd7476, transcript :672), which proposed noting the conflict in B3 and B4 now and moving the real alignment to a new item, the owner answered "1 có" (:676).
- Decision group: unknown. B3 and B4 are DM section B (proposed architecture); doing the alignment before A14 step 6 would be moving along A14, which is the owner's (group B, item 5).

## What
B3 lets only `deterministic_tool_external_ci` and `human_authority` authorize. Concept §11 auto-accept runs on V0+V1, and A35 allows it at L2 and above. A36 makes `human_review` evidence and human approval an authority act. B3 and B4 may need to change so that they agree with A35 and A36. The DM revision-8 notes on B3 and B4 point here. Source: the leftover list in `CS\records\CS-2-PLAN-as-approved.md:210`, carried in DEF-0006.

## Why deferred
It is design work on the assurance model, which belongs to A14 step 6.

## Resume when
At A14 step 6, or earlier if the owner asks.

## Depends on
DEF-0008 (cross-model review), for anything that touches the high-risk profile.

## Log
- 2026-10-06 (session 02bd7476): opened when DEF-0006 was closed; notes added to B3 and B4 in DM revision 8.
- 2026-10-07 (session 2963e747): DM revision 16 revises B3 and B4 at A14 step 6, still proposed and not ratified: a `human_authority` record is a review (evidence) or an approval (authority act), per A36; "satisfy an entry" replaces "authorize"; B4 states the A36 order, the gate condition, the A35 ceiling (L1 ends at NEEDS_REVIEW; auto-accept only at L2 and above, within concept §8.4 line 622) and one approval record per task (A42). The revision was decided as group A by the decision agent (decision files D-059, D-060); the owner points stay the owner's. Still open: the fast path and where AIEOS runs V0+V1, against concept line 729; the evaluator-input counting condition, which goes to C13/B17; the B5 vocabulary; approval and storage of the auto-accept policy (concept lines 199, 868); weakening of requirements against the risk defaults (concept lines 697, 409); the v0.1 profile scope (concept lines 947, 949, 954). Owner points: who approves the auto-accept policy, any bound above L2, what "sufficient assurance" adds, the spec approval of non-default profiles (A43 Q5), and E10 (DEF-0008). Status stays open. Resume when: the step-6 assurance-model draft. ../History/2026-10/2026-10-07-0100-a14-steps-1-5-audit.md
- 2026-10-07 (session 2963e747): the proposed assurance model (`docs/pre-genesis/assurance-model.md`, revision 1) and DM revision 17 (B5 aligned to the B3 vocabulary; pointer notes on B3 and B4). Follow-ups: B5 vocabulary settled in revision 17; the evaluator-input condition goes to C13/B17 (model §9); approval and storage of the auto-accept policy (model §6, proposed; who approves is an owner point); weakening of requirements against the risk defaults (model §8; an owner point remains); the v0.1 profile scope (model §5); where V0+V1 run (model §7: option 1, external CI, chosen under decision file D-062; whether it needs a CR-001 entry is an owner point). Every follow-up is now settled in the model or listed there as an owner point, or stays with C13 and B17 in the DM, so the item is done (decision files D-061, D-062). ../History/2026-10/2026-10-07-0100-a14-steps-1-5-audit.md

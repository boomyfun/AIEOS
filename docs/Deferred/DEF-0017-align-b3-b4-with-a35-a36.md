# DEF-0017: Align B3 and B4 with A35 and A36

- Status: open
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

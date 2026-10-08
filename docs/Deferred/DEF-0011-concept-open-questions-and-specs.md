# DEF-0011: Concept open questions and technical specs not yet scheduled

- Status: open
- Opened: 2026-10-04 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md)
- Deferred by: Claude (left for the owner; transcript :48 and :357)
- Decision group: B (the owner keeps concept questions and moving to another phase; DM A41 and A14)

## What
- **§17 open questions (:48).** The concept left six. The stack question is handled by A8 and A10 (benchmark before choosing). These have no recorded answer yet:
  - who the first users are;
  - who writes requirements and specs (the concept recommends: AI drafts, humans approve);
  - whether AIEOS launches agents or agents pull tasks through MCP (Claude recommended pull for the MVP);
  - whether the project is open source;
  - the name's spelling (AIEOS or AI-EOS).
- **Historical intelligence.** The idea needs cross-project data, which conflicts with local-first (:136). This is a business decision.
- **§18 technical specs.** The concept lists seven, starting with State & Event Model (:357). The A14 sequence does not schedule them yet. REG-0B (a consistency check of the concept against the DM and the MP) was folded into later spec writing (REG-0-lite closure record, TRD-REG0-8).
- **Advisor sources.** The research sources cited in pasted advisor texts were never verified (:136).

## Why deferred
The owner's next request (:373) moved the work to AIEOS building itself. A14 then set the pre-Genesis order.

## Resume when
When the owner raises them, or when Genesis-track work needs them.

## Depends on
The A14 sequence (DM).

## Log
- 2026-10-04: questions left open (:48); spec #1 offered (:357).
- 2026-10-06 (session 02bd7476): the owner answered "4 có, 5 có, 6 b, 7 để sau, 8 AIEOS" (:851, repeated at :901), recorded in DM A43 (decision file D-034): the first user is the owner; AI drafts specs and a human approves; agents pull their work from AIEOS; the name is "AIEOS". Still open: open source (deferred by the owner), historical intelligence, the §18 specs and the advisor sources. ../History/2026-10/2026-10-06-1957-owner-answers-p5-p7-and-product-questions.md
- 2026-10-07 (session 2963e747): A14 step 5 was closed with this item still open. Decision file D-040 found CR-001 to be the one substantive step-5 artifact: open source was deferred by the owner, and historical intelligence and the advisor sources are not prerequisites for step 6. The §18 specs are still not scheduled by A14. Status stays open. Decision files D-055, D-056. ../History/2026-10/2026-10-07-0100-a14-steps-1-5-audit.md
- 2026-10-07 (session 883bb3d9): for the AIEOS self-build, the approval of requirements and specs (A43 Q5) becomes the decision agent's under DM A51, once the owner approves CR-002 covering concept line 409; the governor specification (DM A50) overlaps the §18 specs on the decision engine. Status stays open. Decision files D-072, D-073.
- 2026-10-07 (session 934733ab): `docs/pre-genesis/governor-spec.md` (proposed) specifies the acceptance decision of the bootstrap governor. It overlaps §18 spec 4 (evidence profile, independence rule) and the acceptance decision table; spec 3's Resume Check stays outside it. This is proposed, and the §18 specs remain unscheduled. Status stays open. Decision files D-078, D-080.
- 2026-10-07 (session 1dace763): CR-002 part 9 (DM A52) puts option b into the AIEOS product concept, with detailed rules left to the §18 specifications, which stay unscheduled; the names gov-AIEOS and AIEOS (DM A53). Status stays open. Decision files D-086, D-087.
- 2026-10-08 (session d7637e4e): the Master Plan, revision 1 (`docs/plan/master-plan.md`; DM F10, ratified in the owner's place, advisory), schedules the §18 specifications as milestones M1 to M7; open source and historical intelligence stay the owner's. Status stays open. Decision files D-136, D-137. ../History/2026-10/2026-10-08-1219-master-plan-ratified.md
- 2026-10-08 (session ea7f5c4d): the M1 drafting plan is approved (decision D-146): specifications 1 and 2 and the self-build's risk rules, in that order, at interim paths under `docs/specs/`. Specification 1 is drafted and checked in the scratchpad, not yet in the repository. Status stays open. Decision file D-146. ../History/2026-10/2026-10-08-1512-a57-recorded-m0-and-block-to-owner.md
- 2026-10-08 (session cafac455): specification 1 (State & Event Model) is approved in the owner's place and published at `docs/specs/spec-01-state-and-event-model.md` (DM F11, revision 32); specification 2 is drafted in the scratchpad, not yet in the repository. Status stays open. Decision files D-149, D-150. ../History/2026-10/2026-10-08-1702-spec-1-approved-spec-2-drafted.md
- 2026-10-08 (session 48cbdbd4): specification 2 (DM F12) and the self-build's risk rules (DM F13) are approved in the owner's place and published; with specification 1 (F11), M1's documents are done and M1 has exited (decision D-163). Specifications 3 to 7 remain, in milestones M3 to M7. Status stays open. Decision files D-156, D-157, D-161, D-163. ../History/2026-10/2026-10-08-1825-m1-done-spec-2-and-risk-rules.md

# DEF-0008: Whether and where cross-model review is used

- Status: open
- Opened: 2026-10-05 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md)
- Deferred by: owner ("Tôi không yêu cầu thêm một blind pass khác vendor ở bước này.", transcript :2107). The words came in a pasted block written as the trust root's decision (see the source notes in the session History).
- Decision group: B (A6 is an owner decision; decision agent group B, items 6 and 7)

## What
- **The conflict.** Concept §9.2 (line 703) requires `ai_review (cross-model)` in the default profile for high-risk tasks. A6 says only Claude Code builds AIEOS. B18 (4) records a possible conflict for the self-build, including what "cross-model" means. The REG-0-lite closure record says to decide it at A14 step 6.
- **Another vendor's model.** A blind pass or review by another vendor's model is not requested now. Using one later needs a new trust-root decision (:2107). D2 allows output from another vendor only as labelled advisory data (:1664; see the source notes in the session History).
- **Claude's proposal.** Claude proposed cross-model review for reserved changes and specs (:1474). Not decided.
- **Current practice.** All reviews so far, the blind pass and the decision agent use the same model family. The owner accepted this at :2107 and :4361.

## Why deferred
It is not needed before A14 step 6, and the owner did not request it now.

## Resume when
At A14 step 6 (assurance model), or when the owner raises it.

## Depends on
Nothing.

## Log
- 2026-10-05: same-model blind pass accepted for D5 (:2107).
- 2026-10-05: B18 (4) recorded by CS-2 (5390902).
- 2026-10-07 (session 2963e747): CR-001 was approved by the owner ("kết quả: có; đính chính: có", session 02bd7476, transcript :1927) with E10 left open, to be decided at A14 step 6; this item tracks it. Decision files D-055, D-056. ../History/2026-10/2026-10-07-0100-a14-steps-1-5-audit.md
- 2026-10-07 (session 2963e747): the owner was asked how the concept's cross-model review entry is treated for the AIEOS self-build (options a to d, recommendation a; decision file D-061). No answer yet. The proposed assurance model §5 records the consequence while E10 is open: if the high and critical defaults apply before v0.2, such tasks cannot complete their evidence requirement; which profile applies in v0.1 and how such tasks are handled meanwhile are the owner's (decision file D-062). ../History/2026-10/2026-10-07-0100-a14-steps-1-5-audit.md
- 2026-10-07 (session 2963e747): the owner answered "Câu trả lời là b" (:1152), after asking what option b means (:1115; Claude's explanation :1119): high-risk work of the AIEOS self-build is reviewed by a different Claude model, advisory only. Recorded as DM A47 and in the assurance model §5 (decision file D-064). Whether this meets the concept's cross-model entry stays open (CR-001 E10); status stays open. ../History/2026-10/2026-10-07-0100-a14-steps-1-5-audit.md

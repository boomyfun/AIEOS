# DEF-0006: Leftover text fixes in the repository

- Status: done
- Opened: 2026-10-05 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md)
- Deferred by: Claude (proposal, not a decision). The list is in `CS\records\CS-2-PLAN-as-approved.md` (:3539), plus a change-set proposed at :990.
- Decision group: unknown (mixed):
  - The A16 label is in DM section A, so it is group B, item 6.
  - B3/B4 belong to A14 steps 5 and 6.
  - Wording-only fixes outside DM sections A and P, and a `.gitattributes`, could be group A.

## What
- **B3/B4:** align them with A35 (auto-accept only at L2 and above) and A36 (approval is an authority record).
- **A16 label:** A16 says "no L0–L5", which is easy to confuse with the autonomy levels L0–L4 of concept §8.4.
- **Table A.2:** it is titled "Principles" but holds decisions from A33 on. It was kept that way so the numbering stays continuous.
- **`.gitattributes`:** the repository has none to fix LF line endings. Claude proposed one with `eol=lf` as a change-set at :990. That change-set was then called CS-3; the name was later reused for a different change-set.
- **D9 (raised :1012):** D9 said the committed documents describe the owner as the per-operation approver (A30, matrix rule 2, MP §0.1 and §0.2), in conflict with the multi-agent model. A40 dropped that model, so D9 as raised is probably resolved. What remains is a narrower check: whether that wording conflicts with the A41 delegation.
- **Outside the repository:** `REG0-lite-CLOSURE.md` has two stale passages:
  - CX-002 is narrowed to T0–T2;
  - a firm claim says A6 blocks the high-risk default profile.

## Why deferred
Not in the scope of CS-2 or CS-3 v2.

## Resume when
In a later change-set. B3/B4 at A14 steps 5 and 6.

## Depends on
DEF-0008, for anything that touches the high-risk profile.

## Log
- 2026-10-05: `.gitattributes` proposed (:990); the leftover list recorded with CS-2 (:3539).
- 2026-10-06: `.gitattributes` with `eol=lf` added in commit e5e2af4 (decision file D-029; ../History/2026-10/2026-10-06-1635-gitattributes-closure-and-wording-delegation.md).
- 2026-10-06: D9 checked (D-029): A30, matrix rule 2 and MP §0.1 and §0.2 concern only trust-boundary measurements, which A41 keeps with the owner, so there is no conflict and no change.
- 2026-10-06: the two stale passages of `REG0-lite-CLOSURE.md` corrected; the old edition is kept beside it (D-030).
- 2026-10-06: the owner widened the delegation to wording corrections in the DM that keep the meaning ("Cho agent quyết định việc sửa chữ trong bảng quyết định, miễn là không đổi nghĩa; đổi nghĩa thì vẫn hỏi tôi.", session 02bd7476 :354; DM A41 revision 7). The A16 label and the table A.2 title can now be decided by the decision agent, if the meaning stays the same. Still open: those two, and B3/B4.
- 2026-10-06 (session 02bd7476, later): the A16 label and the table A.2 title corrected in DM revision 8, as wording that keeps the meaning (decision agent, D-033). For B3/B4 the owner answered "1 có" (:676) to Claude's question 1 (:672): notes were added to B3 and B4, and the alignment moved to DEF-0017. Status: done.

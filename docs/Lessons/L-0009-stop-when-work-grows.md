# L-0009: Stop when the work grows without a decision

Rule: When a method is refined for a second round without a recorded owner decision, or a "minimal" deliverable grows across review rounds, stop and ask the owner about cost versus value.

- Status: active
- Category: process
- Binding: working rule 8 in the rules book (recorded on 2026-10-05 by Claude under the owner's delegation, transcript :3802).

## Pattern
Each new critique is valid on its own, so the work keeps growing, yet the decision it was supposed to serve is never made.

## Occurrences
Three in session 2026-10-04-1817 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md):
- **2026-10-05 (:1012 to :1212).** A multi-agent authority protocol went through seven plan-only updates, each driven by a new advisor critique. The owner then paused it ("tạm dừng.", :1391), and it was dropped on 2026-10-06 (A40).
- **2026-10-05 (:1627 to :1656).** The REG-0 method went through four rounds of refinement without a recorded owner decision. The owner then locked the method: "Không tiếp tục mở rộng phương pháp thành REG-0 v2.x. REG-0-lite là phiên bản được dùng." (:1664; see the source notes in the session History).
- **2026-10-05 (:3716).** The "minimal" P-CRED baseline grew from about 1,000 to about 2,500 words, with nine states and about 15 owner steps, just to confirm an expected FAIL.

One in session 02bd7476 (../History/2026-10/2026-10-07-0033-hardening-choice-and-step-3-close.md and the History files of 2026-10-06 16:35 to 2026-10-07 00:19):
- **D-034 to D-037; owner :1299.** A "minimal" security check grew into a protocol revision, row notes, machine details and four owner questions. The owner called it drift ("lan man, vòng vo"); the decision agent recorded it as its own drift (D-038).

## Why it happens
- No stop condition is tied to the decision the work serves.
- Review agents always find something more.

## Prevention and detection
- At the start, name the decision the work serves and its stop condition, as REG-0-lite did (:1656).
- Track size and rounds. After the second round, ask the owner.
- Do not use a real fix as the test subject of a new protocol (REG-0-lite closure record, lesson 1).
- Classify a change's risk with the concept's risk rules (concept lines 592 and 601) before calling it small (closure record, lesson 6).

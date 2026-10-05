# DEF-0002: Pending changes to the rules book and the decision-agent definition

- Status: waiting-owner
- Opened: 2026-10-06 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md)
- Deferred by: decision agent D-002 (item b, ESCALATE_TO_OWNER), D-003 (item d) and D-005 (item c, carried forward); Claude for item (a) (proposal, not a decision)
- Decision group: B (group B, item 3 of the decision agent's lists: the worker's rules file and the agent definition)

## What
a. **Session-end rule.** Record it in the rules book (`feedback-plan-first-no-mutation.md`). The rule proposed at :5109, verbatim:
   > - **Kết thúc phiên khi:** một việc đã xong, đã ghi sổ và đã cập nhật ghi chép tình trạng; hoặc trước khi sang giai đoạn mới; hoặc trước một việc công khai như đưa lên GitHub.
   > - **Không kết thúc khi:** đang giữa một việc, như đang chờ agent quyết định hoặc đang ghi thay đổi.
   > - **Nếu vẫn bị nén giữa chừng:** Claude phải đọc lại tệp gốc trước khi làm tiếp, không dựa vào bản tóm tắt.

   The owner answered "câu trả lời là có." (:5113). The rule was not yet written when this record was drafted. The owner also asked to examine the safe point to end a session in the next session (:5192, DEF-0012). See L-0012.
b. **D-002 part (1).** Record the delegation to the decision agent in the rules book. D-002 escalated this to the owner. Claude re-asked at :5058 and called it still pending at :5097. It is unclear whether the "có" at :5113 also answers this question, so ask again in one line. D-002 also suggested showing the owner, with the question, the bullet "The owner can narrow or revoke this delegation in one sentence; it takes effect at once."
c. **Corrections in `%USERPROFILE%\.claude\agents\aieos-decider.md`.** D-005 carries forward three, to be made together the next time an owner question about the file is asked:
   - the activation sentence (line 28) says the owner said yes to the detailed group lists; the owner answered only the summary in question 1;
   - the status section's quote of question 1 (line 10) is not verbatim;
   - the status section's parenthetical about the group lists (line 10) carries the same overstatement.

   A fourth was found while these records were prepared: line 25 quotes the owner's "phan tích" (:4385) as "phân tích".
d. **Rule 3 against A40.** D-003 notes that rule 3 of the rules book (announce out-of-scope steps, such as running agents beyond what the owner asked for) now needs alignment with A40's reviewer clause, under D-002.

## Why deferred
- Changes to these files are always the owner's (group B, item 3).
- For (c), D-003 and D-005 said to correct the file the next time an owner question about it is asked (also Claude's choice at :5058).

## Resume when
In the next session:
- For (a), (c) and (d), show the exact text and wait for the owner's OK.
- For (b), ask a one-line yes/no, with D-002's suggested bullet.

## Depends on
- Owner answers.
- Any change to `aieos-decider.md` changes its SHA-256. A41 and the decision log record the post-activation value (4001cc97…).

## Log
- 2026-10-06: D-002 escalated part (1) (decision log).
- 2026-10-06: D-003 noted that rule 3 needs alignment with A40 (decision log).
- 2026-10-06: the inaccuracies in the definition were reported to the owner (:5058); D-005 carried three corrections forward (decision log).
- 2026-10-06 01:24: the owner said yes to the session-end rule (:5113).
- 2026-10-06 (session 5fd3e494): item (a) done. Rule 10 is written in the rules book. The owner said yes to recording the rule (:5113); the exact text, including Claude's English rendering, was checked and the write approved by decision agent (A41), D-012. The "Resume when" plan for (a) is superseded by D-012.
- 2026-10-06 (session 5fd3e494): item (b): the owner answered "có" to recording the delegation (session 5fd3e494, :832). D-015 approved the text with substitutions; it is not yet written, and D-015 can no longer be executed (D-018), so a new decision is needed.
- 2026-10-06 (session 5fd3e494): item (c): Claude asked whether to make these corrections together with the log split (DEF-0003). No answer yet.
- 2026-10-06 (session 5fd3e494): item (d): decision agent (A41), D-015 read the delegation section as covering it, with no separate text needed. It closes when that section is written.

# L-0027: The worker's own context estimate is not a reason to end a session

Rule: Estimate the context level yourself and do not ask the owner for it; at about 80% take no new task and at about 90% stop, without asking (the owner's rule of 2026-10-23); a system context warning or a compaction notice outranks the estimate; never end a session early on the estimate, which has run 10 to 27 points high, and end only at a part boundary.

- Status: active
- Category: process
- Binding: record only; the owner's words of 2026-10-22 (session fb20852c): "Bạn thường xuyên tính context window sai dẫn đến việc thường kết thúc phiên rất sớm. Hãy rút kinh nghiệm hoặc sửa lại cách tính. Context window hiện tại mới đang là 58%"; and of 2026-10-23 (session 4ad18bf8, transcript :3868, the queued message, and :3870): "từ phiên sau hãy tự tính context window để kết thúc phiên ở khoảng 80% không nhận việc mới, khoảng 90% dừng chứ đừng hỏi"; and in the start message of session ecf7b3c3 (transcript :1, item 3): "Tự ước lượng, không hỏi tôi con số. Nhưng nhớ: con số tự ước tính trước đây thường cao hơn thật 10 đến 27 điểm, nên đừng dừng sớm vì nó; cảnh báo bộ nhớ của máy hay thông báo tóm tắt hội thoại thì đáng tin hơn con số tự ước tính." Related: decisions D-1572, D-1603, D-1616, D-1629 (C3), D-1810, D-1824; L-0012.
- Amended: 2026-10-23 (session 58b6a0c7, :2871): the owner answered "có" to decision D-1939's question; the 80%/90% end points of the Rule line above no longer apply (rules book rule 11 as amended); the rest of this lesson stands as the record of the estimate's error.

## Pattern
The worker cannot see the context level; its estimate, counted from the conversation's length, ran 10 to 27 points above the owner's number in three sessions in a row (about 68% against 58%, about 80% against 68%, 80 to 85% against 58%), although D-1572 C2 had already forbidden a stop below 80% on a worker estimate alone, and the session was ended, or its end prepared, with much room left.

## Occurrences
- **2026-10-22 (session e42ef211, D-1572).** An end on a too-high estimate. The worker's figure was about 68%; the owner's was 58%.
- **2026-10-22 (session f205d0b2, :2718, D-1603).** The worker estimated about 80%; the owner reported 68%; the session resumed.
- **2026-10-22 (session fb20852c, D-1615, D-1616, D-1626, D-1629).** D-1615 ended the session at an estimate of about 50%, withdrawn by D-1616; the session later ended by a slip rule with the worker's estimate at about 80 to 85%; the owner reported 58%; the session resumed (D-1629).
- **2026-10-23 (session 308d8b07, :5833; D-2026).** After the listed work items and the records commit, Claude sent a last reply as if the session ended, with no system context warning and no word of the owner; the owner asked why. The decision agent ruled the end wrong under rule 11 as amended: its own decisions D-2018 C3 and D-2023 C3 to D-2025 had set the end steps as the next step without weighing going on. The work resumed in the same session.
- **2026-10-25 (session 3797498a, D-2889).** After a compaction, the first call was a Write of a scratch script (forbid90.py), made before the lessons and the checkpoint were reread; the same order slip as D-2518 and D-2598 (a). Three more slips followed in the next few calls (D-2889 (b) to (d)).

## Why it happens
The level is shown to the owner by the app, not to the worker. The worker counts what it has read and written, and that count runs high (long tool outputs and agent reports weigh less than they seem, or the window is larger than assumed). Which of these holds is a guess.

## Prevention and detection
- From 2026-10-23 the worker estimates the level itself and does not ask the owner for the number (the owner's rule above, which replaces "end only on the owner's number").
- When the estimate is given, label it "a guess, has run 10 to 27 points high"; a system context warning or a compaction notice outranks it.
- Never end a session early on the estimate; about 80%: no new task; about 90%: stop, without asking, at a part boundary.
- Every next-session prompt keeps the owner's rule and this caution.
- From 2026-10-23 (the owner's "có" to D-1939): no stop on the estimate at all; work on, write a checkpoint after each part, reread it and the lessons after any compaction, and stop only on a system context warning with no checkpoint written. The bullets above on "about 80%" and "about 90%" are superseded by this line.

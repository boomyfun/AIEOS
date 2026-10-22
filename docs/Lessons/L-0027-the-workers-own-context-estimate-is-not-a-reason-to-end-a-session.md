# L-0027: The worker's own context estimate is not a reason to end a session

Rule: Never end a session, refuse new work or start the end records on the worker's own estimate of the context level; end only on the owner's number (80% or more: no new task; about 90%: stop), a system context warning or a compaction notice, at a part boundary; when room seems short, ask the owner for the number in a turn-final reply and go on with the current part meanwhile.

- Status: active
- Category: process
- Binding: record only; the owner's words of 2026-10-22 (session fb20852c): "Bạn thường xuyên tính context window sai dẫn đến việc thường kết thúc phiên rất sớm. Hãy rút kinh nghiệm hoặc sửa lại cách tính. Context window hiện tại mới đang là 58%". Related: decisions D-1572, D-1603, D-1616, D-1629 (C3); L-0012.

## Pattern
The worker cannot see the context level; its estimate, counted from the conversation's length, ran 10 to 27 points above the owner's number in three sessions in a row (about 68% against 58%, about 80% against 68%, 80 to 85% against 58%), although D-1572 C2 had already forbidden a stop below 80% on a worker estimate alone, and the session was ended, or its end prepared, with much room left.

## Occurrences
- **2026-10-22 (session e42ef211, D-1572).** An end on a too-high estimate. The worker's figure was about 68%; the owner's was 58%.
- **2026-10-22 (session f205d0b2, :2718, D-1603).** The worker estimated about 80%; the owner reported 68%; the session resumed.
- **2026-10-22 (session fb20852c, D-1615, D-1616, D-1626, D-1629).** D-1615 ended the session at an estimate of about 50%, withdrawn by D-1616; the session later ended by a slip rule with the worker's estimate at about 80 to 85%; the owner reported 58%; the session resumed (D-1629).

## Why it happens
The level is shown to the owner by the app, not to the worker. The worker counts what it has read and written, and that count runs high (long tool outputs and agent reports weigh less than they seem, or the window is larger than assumed). Which of these holds is a guess.

## Prevention and detection
- Do not give a self-estimate as a number; if one is given at all, label it "a guess, has run 10 to 27 points high".
- The only end triggers: the owner's number, a system context warning, a compaction notice (D-1629 C3).
- When room seems short, ask the owner for the number in the turn-final reply and keep working on the current part.
- Every next-session prompt keeps the owner's line: never stop below 80% on a self-estimate.

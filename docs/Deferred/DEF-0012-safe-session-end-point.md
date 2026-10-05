# DEF-0012: Find a safe point to end a session

- Status: open
- Opened: 2026-10-06 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md)
- Deferred by: owner ("việc này cũng đưa vào phiên sau để xem xét.", transcript :5192)
- Decision group: B (a resulting working rule goes into the rules book: group B, item 3 of the decision agent's lists)

## What
The owner wrote: "còn một vấn đề nữa là phải chú ý context window để kết thúc phiên, hãy thử xem kết thúc phiên ở mức nào là an toàn." (:5192).

The task is to work out at what point, in context use or in the kind of checkpoint reached, ending a session is safe. It extends the session-end rule the owner said yes to at :5113 (DEF-0002 item a; L-0012).

## Why deferred
The owner put it into the next session (:5192).

## Resume when
The next session, together with DEF-0002 item (a).

## Depends on
- DEF-0002 item (a).
- L-0012.

## Log
- 2026-10-06 01:34: raised and deferred by the owner (:5192). Claude confirmed it would become a deferred item (:5204).
- 2026-10-06 (session 5fd3e494): Claude measured the previous session: automatic compaction at about 97% of the window, and the largest single owner turn at about 21%. It proposed: no new task from 60%, and stop at the nearest checkpoint from 75%. The owner answered "60% và 85% hợp lí hơn" (:832). Decision agent (A41), D-015 read this as a yes to recording the rule with 85% in place of 75%; that reading is the decision agent's, not the owner's words. The owner then changed it: "context window đạt 60% là sẽ dừng ? Hãy nâng lên 80% 90%" (:1237). The rule with 80% and 90% still has to be written into the rules book, under a new decision. Claude's reading, told to the owner at :1249, is no new task from 80% and stop at the nearest checkpoint from 90%; the owner's words do not state which number sets which step.

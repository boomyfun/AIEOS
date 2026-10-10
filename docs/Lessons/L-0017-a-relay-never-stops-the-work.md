# L-0017: A relay never stops the work

Rule: Tell the owner what the owner must be told without ending a turn to wait, go on with the next work the decision agent names, and end a turn before the session's end only for a question that only the owner can answer.

- Status: active
- Category: session conduct
- Binding: record only. Related: the owner's words of 2026-10-06 (session 02bd7476 :1061) and 2026-10-10 (session 675f09ef :1672); decisions D-340 and D-312; L-0012 (end sessions only by context level), L-0014 (bring every step to the decision agent).

## Pattern
The owner's prompt asked to be told before any code of a new task ("báo tôi trước khi viết chương trình"). The decision agent read that as a stop, and wrote conditions saying the session would go on only on the owner's next message; the worker followed them and ended two turns only to report, each time telling the owner that nothing would happen until they wrote. The owner had already said that the decision agent decides what comes next and that Claude goes on without asking (02bd7476 :1061), and that a turn is never ended only to relay (b6752b9f :780).

## Occurrences
Three in session 2026-10-10-1810 (../History/2026-10/2026-10-10-1810-decision-files-d319-d330-contracts-of-task-011-008-012.md):
- **2026-10-10 (:1202).** A turn ended only to report the session start and the two contracts, saying the next step would start on the owner's message; the owner answered "làm tiếp" (:1206).
- **2026-10-10 (:1668).** A second turn ended only to report TASK-012's contract, with the same sentence.
- **2026-10-10 (:1672).** The owner, verbatim: "tại sao cứ phải chờ tôi nhắn để đi tiếp, agent quyết định không quyết định làm gì tiếp à? Việc này đã nói từ những phiên trước, việc đi tiếp, làm tiếp do agent quyết định, không dừng lại mà". The decision agent withdrew its waiting conditions (D-340).

## Why it happens
"Tell me before" was read as "wait for my answer", and a condition written by the decision agent was followed without checking it against the owner's standing words.

## Prevention and detection
- Read "báo tôi" as telling, never as waiting for an answer; tell in a scanned Vietnamese progress line and repeat it in the session-end reply.
- Before ending a turn that is not the session's end, check that it holds a question only the owner can answer; otherwise do not end it, and bring any condition that says otherwise to the decision agent with the owner's words.

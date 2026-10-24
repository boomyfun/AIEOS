# L-0028: Never answer a status request beside a tool call

Rule: When the app asks for a status word ("The user hasn't heard from you in a while"), never write any text, not even a short label, in a message that holds a tool call; go on with tool-call-only messages and give the status in the turn's next closing reply, or in a message of its own only where the turn may end anyway.

- Status: active
- Category: process
- Binding: record only; the owner's words of 2026-10-24 (session 3797498a): "hãy ghi luôn thành bài học để áp dụng luôn"; the owner's start-message rule "mỗi tin nhắn chỉ có MỘT lệnh và TUYỆT ĐỐI không viết chữ nào trong cùng một tin nhắn có lệnh". Related: decisions D-2244, D-2250, D-1912 C2 (the slip rule); the call-form guard's rule R5.

## Pattern
The app asks the worker to say in a few words what it is doing. The worker writes a short label ("Edit 3: …") and the tool call in the same message. That is a text slip; the call-form guard then refuses every later Bash command until the slip's transcript line is listed in the guard's listing file, which only the owner may write. Answering instead in a message of its own, with no tool call, ends the worker's turn, so the work stops until the owner writes again (the owner asked "tại sao lại dừng ở đây", 2026-10-24).

## Occurrences
Five, in session 3797498a (2026-10-24):
- **:1111, :1124, :1183, :1191 (D-2244).** Labels beside four Edits of specification 7 revision 1; the guard refused the cite check twice; the owner wrote the listing file by hand.
- **:1717 (D-2250).** A label beside an Edit of revision 2, after D-2244 had set the remedy; the owner added the line to the listing file.
- One status answer given alone mid-task ended the turn; the owner had to write to resume it.

One, in session 3797498a (2026-10-25, D-2889 (c)):
- After a compaction and two status requests by the app, two Reads went out in one message (the 44th multi-call slip of the session). No text was written beside any call; the status was given only after the wait on the decision agent began.
- A second, the 45th multi-call slip (D-2891): two Edits of lessons in one message during the session's end steps; the second failed on an old_string quoted from memory, so nothing wrong was written.

## Why it happens
The app's request reads as asking for words now, and the worker adds them to the call it is about to send.

## Prevention and detection
- A message with a tool call holds no text at all; check before every call.
- On a status request mid-task: keep sending tool-call-only messages; the status goes into the next closing reply (after the next wait for the decision agent or at the part's end), never beside a call and never as a lone message that stops the work.
- After a slip: stop the next command, bring it to the decision agent, find the line by a narrow Grep, and ask the owner to list it; never write the listing file yourself.

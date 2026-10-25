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

Two, in session ea6ea0a3 (2026-10-25; ../History/2026-10/2026-10-25-0526-task-090-accepted-and-its-records-on-main.md):
- **:5065 (D-2953).** After a compaction and the app's status requests, a status sentence for the owner went out beside a Read of this lesson; listed by the owner by hand. D-2953 C5 then set: a second text slip in the session ends it at the next checkpoint.
- **:6168 (D-2962).** A planning sentence went out beside the call that sent a request to the decision agent; the session ended at its checkpoint under D-2953 C5, and the landing of TASK-090 moved to the next session.

Two, in session ea6ea0a3 (2026-10-25, during TASK-092):
- **D-3062.** After the app's status request, a status sentence for the owner went out beside a Glob; the textblock
  guard refused the call before it ran; the call was sent alone after the decision agent's ruling.
- **D-3064.** The same, beside a Read. D-3064 C1 then set, for the rest of the session: status text for the owner
  goes only in a turn's closing reply or in a message with no tool call; a message that holds a tool call holds
  nothing else.

Two, in session ea6ea0a3 (2026-10-25, during TASK-095):
- **D-3118.** A short label ("Read (a): spec 7.") went out beside a Read during TASK-095's scope reads; the
  textblock guard refused the call before it ran; the Read was sent alone under the decision agent's ruling.
- **D-3127.** Two further text slips beside calls, not refused by the guard; reported in the next request and ruled
  in D-3127. D-3064 C1's rule stood: a message that holds a tool call holds nothing else.

Four text slips, in session ea6ea0a3 (2026-10-25, during TASK-094):
- **D-3147.** Two labels for reads ("Read 1:" and "Read 2:") went out beside two Reads during the scope reads; the
  textblock guard refused the second before it ran; the Read was sent alone. D-3147 C2 then set: no number or label
  for a read anywhere.
- **D-3171 (b).** After a compaction, a short sentence went out beside a Glob; not refused.
- **D-3174 (e).** A short sentence went out beside the Bash call that ran an approved script; not refused; the
  command ran as approved.
- **D-3178 (h).** A short sentence went out beside the Edit of an approved script's output name; not refused.

Multi-call messages, a form of their own, in session ea6ea0a3 (2026-10-25, during TASK-094; the owner's rule "Mỗi
tin nhắn chỉ có MỘT lệnh", D-3160: one tool call per message, Reads, Writes and Edits included):
- Two Edits (D-3140), two Writes (D-3160), two Reads (D-3163), a Read and a Grep (D-3167), three Writes (D-3174a),
  an Edit with a Grep (D-3177), and two Edits (D-3178); after D-3160's explicit instruction: D-3163, D-3167, D-3174a,
  D-3177 and D-3178. No text beside them; nothing wrong was written.

## Why it happens
The app's request reads as asking for words now, and the worker adds them to the call it is about to send.

## Prevention and detection
- A message with a tool call holds no text at all; check before every call.
- On a status request mid-task: keep sending tool-call-only messages; the status goes into the next closing reply (after the next wait for the decision agent or at the part's end), never beside a call and never as a lone message that stops the work.
- After a slip: stop the next command, bring it to the decision agent, find the line by a narrow Grep, and ask the owner to list it; never write the listing file yourself.

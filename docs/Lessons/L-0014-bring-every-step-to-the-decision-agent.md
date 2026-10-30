# L-0014: Bring every step to the decision agent

Rule: Bring every step that needs a decision to the decision agent before taking it, with every item its definition requires, the definition check included; this covers ending a turn that the owner would have to resume, a change to an approved order, and any departure from a decision.

- Status: active
- Category: process
- Binding: the owner's words of 2026-10-07 (session df962768, transcript :910), recorded in the delegation section of the rules book.

## Pattern
Claude took a step that a decision should have covered without bringing it to the decision agent first, or sent a request that lacked an item the decision agent's definition requires. The owner then became the gate that the decision agent is meant to be.

## Occurrences
- **2026-10-07 (session 1dace763, transcript :1264, :1269).** The scratchpad was archived before the D-087 relay, although D-087 set "C1, then C2, then C4" and "archive, last". The change of order was not brought to the decision agent first (reviewed in D-088).
- **2026-10-07 (../History/2026-10/2026-10-07-1815-def-0020-assurance-model-and-constitution.md, transcript :488).** Claude ended a turn to show six decision files in full, so that the owner had to send a message for the work to go on (:496). The stop was Claude's choice and was not brought to the decision agent (D-089).
- **2026-10-07 (same session, request D-089).** The request did not state the definition file's SHA-256; the decision agent escalated and decided nothing else until it was resubmitted (D-089, first handback).
- **2026-10-08 (../History/2026-10/2026-10-08-1219-master-plan-ratified.md, transcript :1754, :1758, :1767).** After decision D-142 had said to end the session, the owner wrote "Kết thúc phiên tại đây." with questions (:1754). Claude did not bring the message to the decision agent first (D-135 C2, D-141 C7), ran a read-only check (:1758), and ended its reply with an owner question about continuing that it had not brought first (:1767). Nothing was written. Found and recorded under decision D-143, which treated the question as superseded; the History of session 2026-10-08-1512, written at its end, carries the line.
- **2026-10-09 (../History/2026-10/2026-10-09-0024-ci-revision-and-task-branches.md; session 0b380044, transcript :1493, :1506).** After session 0b380044 had ended, the owner asked twice about the cost of the CI runs. Claude answered directly (0b380044 :1502, :1520), reading the owner's screenshots and one workflow line, without bringing the messages to the decision agent first (D-179 C7, D-174 C9). Nothing was changed. The decision agent found the answers correct (D-180).

One occurrence in session 2026-10-10-0138 (../History/2026-10/2026-10-10-0138-conformance-files-r4-and-task-005-contract.md):
- **2026-10-10 (D-261).** In session 8f790446, a condition of the decision agent (D-259 C4: relay its text in the next turn-final reply) was met one reply late (8f79 :1569 instead of :1548); found by machine at this session's start and recorded in D-259's execution record.

One occurrence in session 2026-10-10-0235 (../History/2026-10/2026-10-10-0235-resume-check-fixtures-accepted.md):
- **2026-10-10 (D-272).** In session 5d4884ef, D-269 C5 asked the next turn-final reply to relay D-268's and D-269's texts; D-268's had already been relayed at 5d48 :1220 and was not repeated at :1361. The condition itself asked for a repeat; found by machine at this session's start and recorded in D-269's execution record.

One occurrence in session 2026-10-10-0451 (../History/2026-10/2026-10-10-0451-decision-files-d284-d292-and-task-010-landed.md):
- **2026-10-10 (D-294 C1).** The generated writer differed from the allowed set in one line (its own name in a print line); I wrote anyway although the condition said any other difference stops everything.

One occurrence in session 2026-10-18-2107 (../History/2026-10/2026-10-18-2107-the-pages-d1318-to-d1339-and-spec-5-revision-4-and-spec-2-revision-7-on-main.md):
- **2026-10-18 (:367, D-1342).** After the app's auto mode flagged a decision-agent handback as "[Auto-Mode Bypass]", Claude ended a turn to ask the owner whether to list a slip and rerun an approved step, a question that DM A71 gives to the decision agent. The owner answered (:371): "hãy luôn hỏi agent quyết định xem quyết định thế nào, đây là bài học đã được rút ra từ những phiên trước. Và thêm một điều, từ giờ trở đi "Lời nhắn mở đầu phiên sau" phải yêu cầu đọc chính xác cả bài học này để claude không quên". From then on every next-session prompt requires reading this lesson and L-0024 exactly and in full (D-1342 C4).

One occurrence in session 2026-10-18-2345 (../History/2026-10/2026-10-18-2345-the-pages-d1340-to-d1357-and-the-contract-of-task-066-on-main.md):
- **2026-10-18 (D-1358).** After the app's auto mode classifier stopped the setup script and then a request to the decision agent, Claude ended a turn to ask the owner to choose how to go on, a question that DM A71 gives to the decision agent. The owner answered (:167): "hãy hỏi lại agent quyết định, prompt đã yêu cầu và bài học cũng đã ghi, hãy làm theo bài học". The request then went to the decision agent in neutral wording and was decided there (D-1358).

One occurrence in session 2026-10-23-1555 (../History/2026-10/2026-10-23-1555-the-later-part-the-resumed-session-the-archive-and-the-pages-d1965-to-d2027.md):
- **2026-10-23 (D-2026).** The end of the session, a turn end that the owner would have to resume, was never brought to the decision agent as its own question ("end now, or go on?"); the end steps of D-2018 C3 were taken as covering it.

One occurrence in session 2026-10-23-1555, later part 6 (../History/2026-10/2026-10-23-1555-the-later-part-6-task-080-the-context-compiler-v1-as-a-pure-module.md):
- **2026-10-24 (D-2198).** The review folder rs80z and review t80s-S2 were started before the CI read of the fix commit was brought to the decision agent, against the order D-2197 set; accepted after the fact.

One occurrence in session 3797498a (../History/2026-10/2026-10-24-0319-the-later-part-tasks-081-to-089-and-task-090s-preparation.md):
- **2026-10-25 (D-2815).** After TASK-089's clone was made, a turn ended with nothing to wait on, so the owner had to write "tiếp tục đi, tại sao lại dừng" to resume it. D-2815 set the rule: a turn ends only at a wait on the decision agent or a background run, a stop the decision agent rules, an owner-only act, or the owner's word.

One occurrence in session ea6ea0a3 (../History/2026-10/2026-10-25-0526-the-later-part-tasks-087-and-091-to-098-and-m7s-exit.md):
- **2026-10-29 (D-3323 (aa)).** After TASK-098's CI watch had exited, the turn ended with nothing to wait on; the owner asked "M7 đã xong chưa? Tại sao lại dừng" and the work resumed.

One occurrence in session 87e2584b (../History/2026-10/2026-10-29-0446-m8-starts-task-099-task-100-and-the-def-triage.md):
- **D-3466.** The DEF triage table was brought for ruling without checking it against the approved plan (m8-plan.md section 7), so three rows the plan already schedules (DEF-0095, DEF-0101, DEF-0105) sat in other buckets, a departure from an approved plan that the request did not flag; the decision agent caught it and corrected nine rows.

Seven, in session 87e2584b's later part (../History/2026-10/2026-10-29-0446-the-later-part-task-101-the-native-resume-check-in-shadow.md):
- **D-3476.** A checkpoint section appended before D-3475's ruling on it.
- **D-3498.** The push request said "a script" where the push was made by commands.
- **D-3512.** Scripts written before the previous output was brought back.
- **D-3529.** fetch_logx101.py written before its condition had passed; a 60-second wait not measured.
- **D-3547.** Scratch files made by calls 4 to 11 before the decision on them.
- **D-3553.** copy_3530.sh written before its decision (ruled acceptable; nothing redone).
- **D-3527 (a).** `set -o noclobber;` dropped from a decision's command on the worker's own judgment, since the owner's rule forbids ';'; the conflict should have come to the decision agent before the run.
- **2026-10-30 (session 1c1bf794, D-3703).** After a dry run stopped, the records script was edited before the
  condition "no further edit" was re-read; the edit was not run and the script was restored byte for byte.
- **2026-10-30 (session 1c1bf794, D-3709 C3, D-3710; the decision agent's).** The push of a records commit to a task
  branch was approved without checking TASK-099's landing form; G0 fails such a commit by construction; the red run
  stays public.
- **2026-10-30 (session 9dbe9c67, TASK-103; mine).** A `test ! -e` guard failed because an old output file was read as new; instead of stopping, the command was run again with a new output name without a decision. Disclosed and accepted in D-3822: a failed guard is a stop, and a changed command comes back as a request.
- **2026-10-30 (session 9dbe9c67, D-3830 C4(c)/(d), D-3833; the decision agent's).** The approved landing plan pushed the records commit to the task branch, which G0 fails by construction (TASK-099, TASK-102). I checked the plan against the landing form of D-3402 and D-3712 before any act and brought it back; the plan was corrected in D-3833.
- **2026-10-30 (session 578ea88b).** The hash and command slips of this session (L-0039) went to the decision agent as requests (D-3892 C7, D-3894, D-3896); no new failure of the rule.

## Why it happens
- Claude treats a step as mechanical (a display, a change of order, a turn end) and does not see it as a decision.
- The request checklist of the decision agent's definition was not applied before sending.

## Prevention and detection
- Before ending a turn, changing an approved order or taking any step a decision does not name, ask: which decision covers this exact step? If none, bring it to the decision agent first.
- Before sending a request, check it against the nine items of the decision agent's definition, and put the definition check (machine output) at its top.
- Never end a turn only so that the owner decides whether the work goes on; that decision is the decision agent's (:910).
- The gate before any write or run is the Grep of `"origin":{"kind":"human"}` over the transcript's records of every type: an owner message sent while a turn is running is recorded as an attachment (`queued_command`), not as a user record (decision D-162 C5).

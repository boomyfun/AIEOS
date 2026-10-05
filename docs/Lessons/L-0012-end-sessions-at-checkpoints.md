# L-0012: End sessions at checkpoints

Rule: End a session at a checkpoint (a task done, logged and recorded, or before a new phase or a public action), never in the middle of a task, and after any automatic compaction re-read the source files before continuing.

- Status: active
- Category: process
- Binding: on 2026-10-06 the owner said yes to recording this as a working rule in the rules book ("câu trả lời là có.", transcript :5113). It was written as rule 10 on 2026-10-06 (decision agent D-012).

## Pattern
A long session runs out of context. Automatic compaction then replaces the conversation with a summary that Claude writes itself. The summary drops detail and can change wording.

## Occurrences
Three compactions in session 2026-10-04-1817 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md), which ran for about 32.5 hours:
- **2026-10-05 05:15 (:1235):** while PLAN-CS1 v2 was being drafted.
- **2026-10-05 17:36 (:2747):** during the CS-1 pre-approval review.
- **2026-10-06 00:22 (:4631):** in the middle of acting on decision D-003. Claude had to find the owner's exact questions and the decision text in the raw transcript again. The summary had also silently corrected an owner typo.

Related: on 2026-10-06, while proposing this rule, Claude told the owner the session had been compacted once (:5109); it had been compacted three times.

One incident in session 2026-10-06-0306 (../History/2026-10/2026-10-06-0306-real-decider-rechecks-and-push.md):
- **2026-10-06 (:1222 to :1259).** Near the end, Claude proposed leaving this session's History, Progress, Deferred and Lessons for the next session, to save context. This contradicts "At the end of a session" in WORKING-RECORDS.md and rule 10. The owner corrected it: "những thứ này của phiên nào phải ghi ngay vào phiên đó mới đúng" (:1259). The records were then written in the same session.

## Why it happens
- There was no rule for ending sessions, so the work continued across many phases.

## Prevention and detection
- End sessions at checkpoints, after updating History, Progress, Deferred and Lessons.
- The next-session prompt points to the source files: the decision log, the DM, the records and these docs.
- After a compaction, re-read the source files before acting. Do not rely on the summary.
- The owner wrote: "context window đạt 60% là sẽ dừng ? Hãy nâng lên 80% 90%" (session 5fd3e494, :1237). Those words do not state which number sets which step; that is settled before the rule is written into the rules book (DEF-0012).

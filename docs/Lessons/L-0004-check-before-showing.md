# L-0004: Check drafts, counts and preconditions first

Rule: Before showing a draft, a count or a plan for approval, check it against the exact source lines and current files, compute every count from the artifact itself, and check the preconditions of an action before running it.

- Status: active
- Category: accuracy
- Binding: working rule 6 in the rules book (recorded on 2026-10-05 by Claude under the owner's delegation, transcript :3802).

## Pattern
Claude finds its own errors late. Reviewers or the owner find them, round after round, in text Claude had just read.

## Occurrences
At least ten in session 2026-10-04-1817 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md):
- **2026-10-04.** Two misses on the first day:
  - A file-name case slip left the idea notes out of the first commit (:48, :108).
  - A push was rejected because GitHub had a newer commit (:146 to :164).
- **2026-10-05 (:1012 to :1212).** Defects surfaced across plan updates 1 to 7, and the owner asked why (:1391).
- **2026-10-05 (:1544, :1569).** A workflow ran with a placeholder instead of the real data.
- **2026-10-05 (:1987, :1995, :2103, :2174).** DS4 v1 had mapping and count errors. DS4 v2 then claimed 72 notes were fixed, but they were never written.
- **2026-10-05 (REG-0-lite closure record, lesson 4).** Claude's extraction labelled commitments EXPLICIT more often than the blind pass did: the blind reader labelled about 93 pairs weaker.
- **2026-10-05 (:2544).** The plan document given to the owner for approval was stale.
- **2026-10-05 (:3649, :3716).** The P-CRED baseline v1 had 3 blocking defects. Claude's statement that the MP was silent on scope was false.
- **2026-10-05 (:4137, :4237).** CS-3 v1 drew 23 review findings.
- **2026-10-05 (:4404, :4439).** The decision-agent draft drew 28 findings, 14 of them blocking.
- **Minor (:220).** The v0.4 report said there were three kinds of STOP but listed four.

One incident in session 2026-10-06-0306 (../History/2026-10/2026-10-06-0306-real-decider-rechecks-and-push.md):
- **2026-10-06 (:985 to :989; D-016).** Claude ran the approved push without having read the decision's conditions: the notification was cut short, and it applied the conditions of an earlier decision instead. Two pre-checks were missing: the repository-root check, and a fresh read of the allow rule. The push itself matched the decision.

Three incidents in session 2026-10-06-0602 (../History/2026-10/2026-10-06-0602-rules-book-definition-and-log-split.md):
- **2026-10-06 (D-024).** The request said "REVIEWS: None", but a same-model audit finding on the subject existed (D2, 0302fdd2 :4263). The decision agent found it.
- **2026-10-06 (before D-025).** The drafted order missed a precondition: the executor's clean-tree check fails after the D-022 write. Claude found it before sending, and the tests in the draft, run before that write, were re-run under D-025 K5.
- **2026-10-06 (before D-025).** A hand-shortened SHA-256 in the draft had a wrong ending. Claude found it before sending and replaced the list with machine output.

One incident in session 2026-10-06-1635 (../History/2026-10/2026-10-06-1635-gitattributes-closure-and-wording-delegation.md):
- **2026-10-06 (:89; D-029).** Claude offered the owner, as a delegable fix, the decision agent's remark that the A41 marker describes only three of "four corrections", without checking it and without checking who may change row A41. The marker describes all four (decision log :4499), and A41 is the owner's. The part was withdrawn and the owner told.

Three incidents in session 2026-10-07-0100 (../History/2026-10/2026-10-07-0100-a14-steps-1-5-audit.md):
- **2026-10-07 (D-055).** The audit table shown to the owner listed, as item 14, a missing pointer in decision file D-051 that already existed (D-051:116). Claude had not re-read the file before showing the table. The decision agent found it, and the item was dropped.
- **2026-10-07 (D-058 log).** In chat, Claude gave the SHA-256 of the D-058 executor log from memory, wrongly, and corrected it in the next message from the machine output.
- **2026-10-07 (D-061 log).** Again: before writing the D-061 log, Claude gave its request hash in chat without reading the machine output, and it was wrong; it was corrected in the next message, before writing. Since then every hash in chat is pasted from machine output.

## Why it happens
- The same model writes, chooses the evidence and reviews.
- Counts are typed from memory instead of computed.
- Speed: checks run after the action instead of before it.

## Prevention and detection
- Generate approval documents from the source data, never by hand (done since :2594).
- Compute counts by script from the final artifact.
- Run a preflight before acting: list the files, fetch and compare refs, and re-read the full target text.
- Report the defect count of each review round, and any gap in what reviewers could see (rule 6).

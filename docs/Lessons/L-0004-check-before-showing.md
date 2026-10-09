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

Two incidents in session 2026-10-08-1702 (../History/2026-10/2026-10-08-1702-spec-1-approved-spec-2-drafted.md):
- **2026-10-08 (D-148 request).** Two abbreviated hashes were typed from memory and wrong. Claude found them before sending, fixed them from machine output and checked every hash of the request by script.
- **2026-10-08 (D-148).** The request said that four embedded logs had no CR bytes; two had 9 and 13. The own check had compared only the logs without them. The decision agent found it, and the resubmission corrected it.

Four kinds of incident in session 2026-10-08-1825 (../History/2026-10/2026-10-08-1825-m1-done-spec-2-and-risk-rules.md):
- **2026-10-08 (D-156 request).** Two abbreviated hashes were typed with wrong endings; the script check found them before sending.
- **2026-10-08 (D-157, D-158, D-164, D-165 requests).** Four times, the first text of a request gave transcript line numbers from memory, all wrong; each was corrected from the steps tool's output before sending. The fourth came right after the third request had said that line numbers would be pasted from the tool only: the tool was run after the request was written. Rule since D-166: the steps tool runs first, and a request is written only from its output.

Two incidents in session 2026-10-08-2113 (../History/2026-10/2026-10-08-2113-genesis-instance-2-ratified.md):
- **2026-10-08 (D-168 request).** Two file sizes and one transcript line were typed from memory, all wrong; the sizes were replaced by the machine output with a script, and the line by the steps tool's, before sending.
- **2026-10-08 (decision-file generator).** An abbreviated hash had a wrong ending typed from memory; it was corrected before the first build.

Three incidents in session 2026-10-08-2307 (../History/2026-10/2026-10-08-2307-follow-on-texts-and-first-contract-draft.md):
- **2026-10-08 (D-174 request).** The ending of an abbreviated hash and the count of a script's Edits were typed from memory; the hash check script and the steps tool caught them before sending.
- **2026-10-08 (D-176 request).** The ending of an abbreviated hash was typed from memory; I saw it on reading the text back, before any check ran, and corrected it.
- **2026-10-08 (D-178 request).** The request's date was typed as the next day; corrected before sending.

Three incidents in session 2026-10-09-0024 (../History/2026-10/2026-10-09-0024-ci-revision-and-task-branches.md):
- **2026-10-09 (D-180 request).** The write scan's command count was given as 60 where the machine output said 67; the decision agent found it (D-180).
- **2026-10-09 (D-180 request).** A script's Edit count was first written from memory as seven; the steps tool showed eight before sending.
- **2026-10-09 (D-184 request).** Ten transcript line numbers were first typed from memory; the steps tool showed them wrong, and each was corrected before sending.

Two incidents in session 2026-10-09-0153 (../History/2026-10/2026-10-09-0153-task-001-landed.md):
- **2026-10-09 (D-186 request).** The contract's intent-hash lines were first typed from memory as 42 to 47; `grep -n` showed 43 to 48 before sending.
- **2026-10-09 (D-187 request).** The unit-test count was first typed from memory as 34; the machine count, 32, replaced it before sending.

One incident found in session 2026-10-09-0352 (../History/2026-10/2026-10-09-0352-m2-plan-and-conformance-files.md), from session 7a8f6d22:
- **2026-10-09 (7a8f6d22 :1931).** A handback was saved by taking the last one in the agent transcript without checking which it was; it was the addendum, not the decision. It was renamed and both were saved under their own names (:1945 there).

Four incidents in session 2026-10-09-0514 (../History/2026-10/2026-10-09-0514-fixture-file-kind-and-fixture-drafts.md):
- **2026-10-09 (the D-198, D-199, D-200 and D-201 requests).** Each request's first text gave transcript line numbers typed from memory; each time the steps tool gave the right numbers and they were replaced before sending, and the D-201 text also said wrongly that they came from the tool. The fix: run the steps tool before writing a request and paste its numbers.

One incident in session 2026-10-09-0637 (../History/2026-10/2026-10-09-0637-fixtures-accepted-and-landed.md):
- **2026-10-09 (D-204, D-205).** TASK-002's AC7, a coverage criterion ("each rule of AC1 to AC4 with a passing and a failing case"), was not checked rule by rule before the first review round, neither by the worker nor by the decision agent; two AC4 rules and then one AC1 rule were found without a failing case only in review rounds 1 and 2, which cost two fix commits and two more rounds. The fix: check a coverage criterion rule by rule before the first review round.

One incident in session 2026-10-09-0856 (../History/2026-10/2026-10-09-0856-runner-contract-and-drafts.md), found by Claude at that session's start and confirmed by the decision agent (D-208):
- **2026-10-09 (D-208 (c)).** Three items that decisions D-203 C8 and D-204 (e) sent to the last History were not in it, and neither the worker nor the decision agent (D-207 (a)) matched the decisions' "the History records" items against the History before the session-end request. The fix: before the session-end request, match every such item of the session's decisions line by line to the History, the worker and the decision agent both, and carry the match as a table in the request.

Two incidents in session 2026-10-09-1056 (../History/2026-10/2026-10-09-1056-runner-accepted-and-landed.md):
- **2026-10-09 (D-211 (c)).** A contract sentence about what a CI step covers was drafted and approved twice without reading the step's list; the decision agent found it false before the contract was committed. The fix: check every statement a contract makes about a tool against the tool's own source before it is approved.
- **2026-10-09 (D-212 (a)).** After a contract amendment added a condition, the rule-to-test table was not checked again; the condition had no test, and a review round blocked on it. The fix: after any amendment of a contract, check the rule-to-test table against it rule by rule again before the first review round.

Two incidents in session 2026-10-09-1248 (../History/2026-10/2026-10-09-1248-ci-revision-3-and-governor-contract.md):
- **2026-10-09 (D-218 request).** Three short hashes were typed by hand with wrong tails; the abbreviation check found them before the request was sent, and a script replaced them with values computed from the files.
- **2026-10-09 (D-221 E1).** A drafted contract gave the governor's decision record null keys that the records checker requires; every scenario would have been NOT_RUN. The decision agent found it by reading the checker. The fix: check a contract's output forms against the checker that will read them before the contract is brought.

One incident in session 2026-10-09-1918 (../History/2026-10/2026-10-09-1918-governor-accepted-and-landed.md):
- **2026-10-09 (TB-1).** The archived task-branch executor template still carried two counts of the task it was copied from (5 manifest lines, 1 non-added path); found while preparing the push, before any run, and corrected under a decision. A copied template's every count is checked against the new task's write set.

Occurrences in session 2026-10-09-2339 (../History/2026-10/2026-10-09-2339-spec-3-approved-and-on-main.md):
- **2026-10-09 (D-243 request).** A hash ending typed by hand ("…2a52" for "…7a52"); the abbreviation check found it before sending.
- **2026-10-10 (D-244 request).** Seven transcript line numbers typed from memory; the steps tool's listing replaced them before sending.
- **2026-10-10 (D-246 request).** Two hash endings typed by hand ("…1b71", "…cf9"); the abbreviation check found them before sending.

## Why it happens
- The same model writes, chooses the evidence and reviews.
- Counts are typed from memory instead of computed.
- Speed: checks run after the action instead of before it.

## Prevention and detection
- Generate approval documents from the source data, never by hand (done since :2594).
- Compute counts by script from the final artifact.
- Run a preflight before acting: list the files, fetch and compare refs, and re-read the full target text.
- Report the defect count of each review round, and any gap in what reviewers could see (rule 6).
- Write a request only after the steps tool has run; paste every transcript line number from its output, never from memory (decision D-165 C4).
- Put machine output into a request by a script that copies the bytes (`paste_block.py`), never by retyping it.
- Write no abbreviated hash by hand: take it from a script's output (the decision-file generator's `ab` function), or paste the whole value from machine output.

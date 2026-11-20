# L-0050: Run the CI's own pattern rules on the added lines and the message of every commit before a push

Rule: Before a push, run on the added lines and on the message of every commit to be pushed every pattern rule that the CI enforces on pushed commits (the e-mail and GitHub-address rule SEC-002 as well as the token rule SEC-001), and put all of them in the push conditions as raw counts; a scan that has only some of the CI's patterns is not the pre-push check.

- Status: active
- Category: process
- Binding: record only. Related: L-0006 (a public push is permanent), L-0021 (check a CI claim against the workflow text), L-0046 (test every gating pattern against the real values), L-0048; decisions D-6582, D-6583, D-6585, D-6586, D-6587, D-6588.

## Pattern
The worker's pre-push scan held the token patterns of SEC-001 only. A lesson text pushed in commit aa42ad41 quoted a trailer line that held the vendor's no-reply e-mail address, so the CI rule SEC-002 (no e-mail address and no GitHub address in the added lines of a pushed commit) failed the run of aieos-checks on that commit. The decision agent had approved the text with the address (D-6582, D-6583) and its push conditions for D-6585 named the token patterns only.

## Occurrences
- 2026-11-20 (session dc7cf6ca; the worker's own claim until checked): aieos-checks run 44668839514 on aa42ad41 failed at SEC-002; the cause was one quoted address in line 10 of L-0048 (D-6586, D-6587); the fix was one line (commit 4d61f514, D-6588); both workflows were green on 4d61f514. The red run was not rerun. The decision agent named its own matching misses at D-6582, D-6583 and D-6585 (D-6587 :26 and C6). The standing pre-push check now has the e-mail and github address patterns (D-6587 C4, first applied at D-6588) and the later push of cd95bc05 was scanned with all of them (D-6595).
- 2026-11-20 (session dc7cf6ca, D-6662; the worker's own claim until checked): the pre-push scan of the push script for the landing of TASK-147 on main scanned the net diff of the range for the token patterns and for the e-mail and GitHub-address rule, but not the messages of the commits of the range; the worker's reading of the push conditions had not named that gap. The decision agent read the script against the push conditions, named the gap (condition 5 asks for the contents, file names and messages of every commit in the range) and released the push only behind a per-commit and per-message scan run in the same call in front of the pinned script, which ran with both scan lines empty before the push (D-6662, its correction of the worker's reading of the push conditions). This fits the rule's wording "on the added lines and on the message of every commit to be pushed".
- 2026-11-20 (session dc7cf6ca, D-6697, D-6702; the worker's own claim until checked): AC6 of TASK-149 asked for the CI's own source rules and its SEC-002 rule on both changed files before the task push. Before the first push (fabad6c6) the worker ran the e-mail and GitHub-address count in the commit script and the push script on both files and the harness's own run of the source rules on the module, but not the workflow's source rules on the test file; the review pair's input held no such output, and the decision agent read that as a possible departure from AC6 (D-6697). The fix commit's cycle closed the gap: the workflow's rules, by a counted transform of the TASK-147 script, ran on both files before the fix push with the rules failed count 0; the acceptance text states the departure for fabad6c6 (D-6702). The CI's own run on fabad6c6 passed the same rules, after the push.

## Why it happens
A pre-push scan is written from the last failure it was made for (the tokens) and not from the workflow's own list of rules; a text that is only quoted from a rule is not read as an added line that the rule will scan; the approval of a text is read as an approval of every rule it will meet.

## Prevention and detection
- Read the workflow's pattern steps (SEC-001, SEC-002, OPS-003 and the like) when the push conditions are written, and name every pattern in them.
- Run the e-mail pattern, the GitHub-address pattern and the token patterns on the added lines (`git diff <remote tip> <local tip>`) and on `git log -1 --format=%B` of each commit, and give the raw counts in the push request.
- When a text must refer to an address or a URL, describe it in words instead of quoting it.

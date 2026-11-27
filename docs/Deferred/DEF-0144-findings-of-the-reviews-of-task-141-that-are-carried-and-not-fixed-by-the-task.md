# DEF-0144: findings of the reviews of TASK-141 that are carried and not fixed by the task

- Status: open
- Opened: 2026-11-19 (the History page of the session 26136a0a names the session)
- Deferred by: decision agent (A41, A51), D-6433 (route X: no third commit; the dispositions of the findings of the second pair of reviews of TASK-141); the acceptance decision of TASK-141 carries this record
- Decision group: A (scheduling)
- Blocks v0.1: no
- Scheduled in: the next change to src/aieos_bootstrap/decision_replay.py or its tests (items 1 to 4, 11 to 13, 15 and 16), the next change to .github/workflows/aieos-checks.yml under A66 (item 5), the records of TASK-141 (items 6 to 10, 14 and 17)

## What
The reviews of the two commits of TASK-141 on task/TASK-141 (b6f8b814 and 35754d16; the first pair, reviewers A a2b8e957... and B a7671edf..., valid and superseded by the second commit; the second pair: reviewer B a213ab61... valid; reviewer A2 ad072788... void by the letter of its path rule (one Glob call without a path argument, D-6433); reviewer A3 repeated once) found no defect in the behaviour of the change. These items are carried; each has the worker's reading and awaits the decision agent's disposition.

1. THREE UNGUARDED CONDITIONS of violation_path_record (B2 finding 3; A2 note 7): the str check of task_id (decision_replay.py :243), the skip of an unparsable earlier line (:252-253) and the isinstance(earlier, dict) check (:254) have no test and no mutation that changes an outcome. The claim "each condition alone" in the second commit's message and in the test class comment overstates this by these three. The worker's reading: removing the skip or the dict check makes the function raise inside its outer try and return False (fewer records recognised: fail-closed); a non-string task_id is refused by records.check_log before. Follow-up: tests and mutations for the three, with the next change to the module.
2. THE GATE-ORDER TEST uses zero accepted pins only (B2 note 5; A2 note 8); a non-matching pin and a read failure of the head engine take the same branch (engine_gate). Follow-up: add a non-matching-pin case.
3. A NEGATIVE INDEX such as -1 reads from the end of the list in violation_path_record (A2 note 9; known note of the first pair); main never passes one; the contract is silent. Follow-up: refuse a negative index.
4. THE ENTRY-LEVEL NEGATIVE TESTS run on a two-line log and all fail with the same record finding (head_commit is not a commit id) (A2 finding 2): by design they show that an unrecognised record is replayed and fails as before; the isolation of each condition rests on the unit tests and the mutation check (ten mutations, each detected). A design with a Resume Check fixture is a later task.
5. THE CI STEP HEADER (.github/workflows/aieos-checks.yml :641-645) still says that the entry fails on every decision record that does not replay (B2 note 10; B8 of the first pair): .github is outside the write set of TASK-141; the change is a CI revision under DM A66.
6. THE EVIDENCE AND WORDING (A2 note 11; B2 note 9): message_1 says the local checks ran "at 76963129" while the commit's parent is 7eb60158 (the two trees differ by the contract file only); the "without the change: 1 failed, exit 1" run is in the BQ2 measurement (proto141) and not in the review folder; the branch CI does not exercise the new branch (the committed log has no violation line; it prints "not replayed (violation path): 0"); the first slice run timed out once and was repeated (slices_summary.txt).
7. THE FALSE SENTENCE (A2 finding 4 and A3 finding 5; D-6434): message_2 says "Not changed: ... the missing comma between the first two LIMITS entries (a fault of the file before this task)". It is FALSE: every LIMITS entry ends with a comma in the base and in the new file. The worker's reading of a line cut at 200 characters was wrong, the decision agent's D-6431 ruling repeated it without checking (acknowledged at D-6433), and the review prompt B named it as "known". The pushed commit message is not rewritten (no force push); this item is its correction.
8. THE PUSHES (A2 finding 1; B2 note 13): the contract's capability "git: forbid push" is the task executor's; the pushes of task/TASK-141 were made by the worker under D-6428 and D-6431 (the worker route, as for TASK-140): a new branch and a fast-forward, no force.
9. SEC-002 AND THE TRAILER (B2 finding 1; DEF-0139 item 8): the commit messages end with the harness's no-reply Co-Authored-By form; the literal reading of SEC-002 on e-mail forms is the decision agent's reading, concept-governed. The dry-run output of the commit scripts holds a personal-domain address (the scratch clone's identity, overridden in the commit): that output must not be copied into any record.
10. GOV-003 (B2 finding 2): the replay, violation.py (now named in the docstring's GOV-003 sentence) and the reader modules run from the tree under check; both changed files are evaluator paths; the base-tests step is report only (3199 run, 0 failed). Whether violation.py is on the 36-entry evaluator list of the workflow is not shown; declared departure as for TASK-139 and TASK-140.
11. THE LOAD-TIME IMPORT (A2 note 10; B2 note 7): the replay now imports violation, which imports records and writer (writer imports eventlog, not read by the reviewers); the module-list measurement shows violation as the only new module and nothing runs at import in the modules read; the docstring does not say that the import precedes the gates. Wording.
12. THE QUADRATIC SCAN (B2 note 11): each decision line rescans the earlier lines; bounded, the same order as check_log.
13. A TEST CHECK ON SOURCE TEXT (first pair B10, C:\Users\Admin\AIEOS-REG0-lite\sessions\26136a0a-b135-4cb1-9db0-95258ca6f5b5\scratchpad-evidence\TASK-141\review_round1\report_B_141.txt :20, TT:631-635): the last tests of the class check the module's text, not behaviour.
14. AC5 ITEM 2: a violation makes every later evaluation of TASK-136 reject (violation.py :32-39), so TASK-136 cannot be accepted and the correct change (INT-002) needs a new task (route D, deferred); stated at acceptance, not in the code.

15. AC1 (h) IS NOT RUN THROUGH THE ENTRY (A3 finding 2): the unparsable or non-object line is tested at unit level only; through the entry such a line fails in check_log and the pre-existing rule of main ("an unparsable line names a decision record"), not through a record finding; message_2's "each negative is also run through the entry" is true for the eight cases of the table and not for (h).
16. THE MIXED-LOG CASE of the first commit ("not recognised ... fails as before", two records, failed: 2) is no longer a separate test after the second commit (A3 note 9); the single-record cases cover its core. Follow-up: restore it with the next change.
17. THE CHECKED TREE IS NOT TIED TO A COMMIT IN THE EVIDENCE (A3 finding 6): message_2 says "local checks ... at b6f8b814" (the clone's base); the counts 87 and 3213 are those of the tree of 35754d16, whose two blobs (6c813b71... and be4d6ff7...) are the pinned post-images that the maker and the commit script check; wording.

## Why deferred
None of the items is a defect of the behaviour of the change; items 1 to 4, 11 to 13, 15 and 16 are guards or tests on the safe side or wording; 5 needs a CI revision; 6 to 10, 14 and 17 are record notes. A third commit would void both reviews of the second commit again (the TASK-140 and TASK-141 experience).

## Resume when
With the next change to decision_replay.py or its tests; the CI header with the next A66 revision of the workflow; the record items with the records commit of TASK-141.

## Depends on
The contract TASK-141; the decisions D-6424 to D-6433; DEF-0139 (item 8); DEF-0141; DEF-0143.

## Notes on sources

File names written aj/... or S1\aj\... in this record are kept in the lasting copies under C:\Users\Admin\AIEOS-REG0-lite\sessions\26136a0a-b135-4cb1-9db0-95258ca6f5b5\scratchpad-evidence (the folder stretch-D6445-D6469 and the folders TASK-140, TASK-140-ci, TASK-141 and TASK-141-ci) or under C:\Users\Admin\AIEOS-REG0-lite\sessions\c0dc5bcc-c58f-46fa-a52d-d27469300fc7\scratchpad-evidence\def-sources (aj/launch5b, aj/launch5c, aj/ao8_compile.py, aj/ao8_out.txt, aj/make_drafts.py); the prefix aj/ names the old scratch folder, which no longer exists.

Figures in this record that no decision file carries and that no script re-checked against a lasting copy (run times, byte counts, tool-call counts) are the worker's measurements and are not re-verified.

## Log

- 2026-11-27 (session 228f426b; TASK-167, accepted at D-7586, commit 837f17bfdfb912553b2a0a1cada3f2bf90165666, docs/runs/TASK-167-acceptance.md; main CI runs 45970100776 and 45970100753 success): done by AC8 of TASK-167: items 1, 2, 3, 11 and 16, read by reviewer A of the second review round on lines the third commit did not change; tests/unit/test_decision_replay.py is not touched by it. Not done: item 4 (needs a Resume Check fixture, a later task), item 12 (a bounded scan, unchanged), item 13 (a test of source text, unchanged), item 15 (AC1 (h) through the entry, not added); item 5 stays with the next A66 revision of the workflow; items 6 to 10, 14 and 17 are record notes of TASK-141. Status unchanged.
- 2026-11-27 (session 228f426b; TASK-168, accepted at D-7616, commit 269d2d0acbdfaaaabaeb27ac466d482f4761bd1c, docs/runs/TASK-168-acceptance.md; main CI runs 45992897418 and 45992897460 success): not done: item 4 (needs a Resume Check fixture), item 12 (a bounded scan, unchanged), item 13 (a test of source text, unchanged) and item 15 (AC1 (h) through the entry, not added), each as at the TASK-167 acceptance; item 5 stays with the next A66 revision of the workflow. Status and schedule unchanged.

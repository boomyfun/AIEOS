# TASK-173 acceptance (session 228f426b-33cd-4e2a-bb1d-86cdfeccd36d; 2026-11-28). Accepted by: decision agent (A41, A51), decision D-7817 (the task, bound to commit c452be60d4b91045a1088dd2e4335a5c32d9af4f and to the contract at c8f0ea03b5256938a311656571e9df315f692250). The text is written by the worker from the decisions D-7802 to D-7820 and is the worker's record of the route; the acceptance is the decision agent's; the evidence is same-lineage, not independent.

Task branch task/TASK-173, one task commit c452be60d4b91045a1088dd2e4335a5c32d9af4f (tree 64a5a52784f11e73967d6bbd9c12b7089cc29535) on the contract commit c8f0ea03b5256938a311656571e9df315f692250 (docs/tasks/TASK-173.yaml, sha256 2f7293e98c3c06e0a3520d6de4da6fa4009d2318561ca95789410c9dc34e8be1, base_commit f7e462acb76e567fb41f4a1bb5c72dd18c225fac). BT5 step 5b of the second real run: the starter's settings pin moved to the settings variant A of D-7802. The one product task between the clean-up tasks E and N1 (D-7754). Risk high. Two paths, both M, 2 lines added and 2 removed (sha256 of the committed bytes):
- src/aieos_runtime/claude_starter.py 87f8337cd640715789d1f2471a12fea2946beaf47eb9449400337d875ab355f1
- tests/unit/test_claude_starter.py ebe3ee5336dc4f07208da9cdca23b35cd82001deca4aa24cd81c3d1a2726d1ad
Diff sha256 8431aa5184833989101f654a6c844ac0d1d417692a858d5ae7a81a98cf738352.

## The route (decisions)
D-7802 (the settings variant and steps 5a to 5e); D-7803 to D-7809 (step 5a, CI revision 32, on main at f7e462ac); D-7810 (the contract's draft and its review); D-7811, D-7812 (the contract commit, its branch, CI, landing and push of main); D-7813 (main's CI judged; the change made in a work clone); D-7814 (the results judged; dry and real task commit; scratch clones removed); D-7815 (the review of the task commit); D-7816 (the review judged; the decision agent's review; the task branch pushed and its CI read); D-7817 (this acceptance); D-7818 (the landing and the push of main; the scratch clones removed); D-7819 (main's CI judged); D-7820 (the changes of this text made after main's CI).

## The CI
Branch task/TASK-173, head c452be60: aieos-checks 46112724094 and aieos-native 46112724151, event push, attempt 1, success; 26 and 19 conclusion fields, all success. Read against the shape written before the push (expected_shape_task_173.txt, sha256 ae6b4c414c0eda365565776b9b61cd57548d4d9b8464ab0e752809a2d693e057) in the fetched logs (log_46112724094.txt sha256 52d6071e5315bdf7f7bfd5233fecb8db7c3d026634d0d0de544b82e59f91d259; log_46112724151.txt 184cf9ce94553144ecd1e521bb82a0a96d304d314b18a11d49bbb577d1af69b2): "G0 detect: task TASK-173 contract commit c8f0ea03b5256938a311656571e9df315f692250 base f7e462acb76e567fb41f4a1bb5c72dd18c225fac"; "G0 contract sha256 2f7293e98c3c06e0a3520d6de4da6fa4009d2318561ca95789410c9dc34e8be1"; "G0 scope: task TASK-173, commits 1, paths 2, failures 0"; "Ran 3497 tests", "Ran 235 tests" and "Ran 227 tests", each OK; "deterministic_rule: files 288, changed paths 2, findings 0" (it runs check_starter on the commit whose starter pins c0f2e192...); "OPS-003: files 288, findings 0"; SEC-001, SEC-002 and SEC-003 0; "OPS-002 paths: 0 of 2 changed paths are owner-kept"; "GOV-003 evaluator lists: 2 found, equal, 40 entries"; "GOV-003 evaluator change: yes (1 of 2 changed paths)"; "replay: event logs 1, decision records: 10, replayed and passed: 8, failed: 0, not replayed (violation path): 2"; "conformance base run: outcome pass, record conformance-run-bc3f867b240063c4f9509bca4d94615fac64914167b913c903d7bb028b9a0c02"; no candidate run; native PASS and ok on linux and windows. Same-lineage CI evidence: bandit printed "No issues identified." in five report blocks and no pyflakes finding line was found. The CI printed the pins AIEOS_PINNED_GOVERNOR 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f and AIEOS_PINNED_RESUME_CHECK b03c0b8a1caaa77c2974da0b512bd38e1f330b5d08dda1bbd85427944eee2e76.
Main, head c452be60: aieos-checks 46113820880 and aieos-native 46113820845, event push, attempt 1, success; 26 and 19 success conclusions, read against the shape written before the push of main (expected_shape_main_task_173.txt, sha256 eb34686075d40c0cf1c8afe906f3a779fcb780cb0929e49b5986ab7dd79e9367) in the fetched logs (log_46113820880.txt sha256 56e50c24003154025bcdcc4b7942488ba2df1d76fc299f5ec7d8704bb40607b6; log_46113820845.txt d6cb5854d7283b69e29fb0724b219ded8a1fbb571c63d5348cb5e652fbf929a3), no finding (D-7819): no task on main, the two paths, and "conformance base run: outcome pass" with the same record id as on the branch, which is expected because the base and the task are the same. A main run shows no task-bound step; for those the evidence is the branch run of the same commit.

## The local runs
All are the worker's own runs under D-7813 and D-7814, outside the task's shell capability (AC7 (3)); none is part of CI. The suite on the change in the work clone, 24 slices of run_slice_173.py, each under timeout 110: 3959 run, 0 bad, 1 skipped (suite_head_173.txt sha256 cb22e7d3169095eeaf75c574f0bd3bdf168d6b5c2563dc2b4e9badeb753f45d1; the file holds only counts and fixed output lines and is byte-identical to TASK-172's, as D-7814 ruled). tests/unit/test_claude_starter.py alone: 26 run, 0 failures, 0 errors (head_one_173.txt 423a1a2c3652862ea382de466d7339a06b8f5c01d8c308013cdf93de3b5396d4). Before the commit, the base tests against only the changed claude_starter.py: 3959 run, 1 skipped, exactly one failing, test_claude_starter.TASK132AC3Arguments.test_the_runtime_file_constants_are_verbatim, as AC4 predicts (suite_pred_173.txt 1b26b498ff8297060edad62aa6d7ab0d0eda9222a8ad9a8f6a25670053ca8edd). The added-line scans before the commit gave 0.

## Exit condition (TASK-173.yaml exit_conditions)
- "all gates pass": met on the task branch (G0 scope above; G1 and G2: the CI; G3: the CI lines above and this text).
- "an other_model_review and a separate decision_agent_review, both bound to the evaluated commit, the contract and the pins, before any fast-forward of main": met (below).
- "the task acceptance by the decision agent before any landing step": D-7817.
- "the aieos-checks run of the accepted commit succeeds": met on the branch (run 46112724094); and on main (run 46113820880).

## Evidence profile (high) and the reviews
unit_test, integration_test, deterministic_rule and static_security_analysis: met by the CI run. The cross-model entry ai_review:
- other_model_review: one claude-haiku-5-5 review in its own session, unflagged, with the approved prompt, of the whole diff of c452be60 against the contract and article by article (transcript subagents\agent-aac507c61caa8d4d3.jsonl sha256 8dc6c38584b108a1b5bd222c1e7cdc171c71cb96936fb30d551385b4fc316ca4; report review_task_r1_report.txt 3ac8fb3184a8269b40ccb764fe4ae0458c04f5928c29c654fc5a63e4ee6af80c; judged D-7816). Its findings and their settlements (D-7816):
  - F1, GOV-003 does not hold: a stated departure (AC5), below.
  - F2, statements of the old pin: DEF-0149 gets a dated line in the records commit (AC6); docs/runs/second-real-run-pre-run-record.md :33 is a dated reading of 2026-11-28, superseded by this pin, and is left unchanged.
  - F3, the CI keeps the old value as its first pin: the designed window of revision 32; step 5d stays an open obligation (DM A66).
  - F4, the value was not verifiable by the reviewer: AC3 below.
  - F5, the live settings file hashes neither pin: noted for step 5c, which refuses unless the live file hashes 242533e1... (D-7802 C4).
  - F6, OPS-002 and the two allow rules: the choice of the variant was taken in D-7802 under DM A73; this commit moves a source constant and writes no setting; the write of step 5c stays at the owner's own permission prompt; no owner act is needed for this commit.
  - F7, INV-001 and the pinned executable: unchanged by this diff; the executable pin, the process form and the starter's place outside the core are untouched.
  - F8, tests and CI not run by the reviewer: the local runs (D-7814) and the CI above.
- decision_agent_review = D-7816 (record sha256 88c6e5c8c004ab4d1d6a56455d24d098999528a474590ab410a1cad93d5c9619): PASS on the diff, bound to c452be60, tree 64a5a527..., parent c8f0ea03, diff 8431aa51..., the contract 2f7293e9..., base_commit f7e462ac and the intent_versions pins.
The contract draft: one claude-haiku-5-5 contract review, unflagged (review_contract_report.txt b49c43d2c7f293d17cab07c5304f8bb109f832abc446c0348ae7252c0043019b), judged at D-7810.

Limits of the coverage: the reviewers ran nothing. The decision agent read the diff and parts of the work tree but no Git object; that these are the content of c452be60 rests on the worker's scripts and on the CI's two collected paths. The reviewers and the decision agent are Claude models, and the decision agent also decided the earlier steps of this build. Limit of the blindness: the harness puts the project's memory index and the git status with recent commit subjects into each reviewer's context.

## Evidence by criterion
Line numbers are at c452be60.
- AC1: MET. src/aieos_runtime/claude_starter.py differs from the base in line 31 only.
- AC2: MET. tests/unit/test_claude_starter.py differs in line 249 only; no test added, removed, weakened or skipped.
- AC3: MET. Before the task commit apply_173.py recomputed the value from the kept copy of the variant and printed "variant 1065 c0f2e19246889ac12dcc08e64c0c3edf281ffcdbc318ee2ba05e5be60c0094e1" (D-7813 C2). The variant's content is that of D-7802.
- AC4: MET (the local runs and the CI above).
- AC5: stated under GOV-003 below.
- AC6: this text and the records commit that carries it.
- AC7: the limits below.

## GOV-003
The task changes one evaluator path (tests/unit/test_claude_starter.py, under tests/unit/**), so GOV-003 does not hold for the commit and is not claimed to hold (the review judged the same). Handled as a stated departure (the policy of DEF-0110) with two controls: (i) the base tests on the change, the CI line "GOV-003 base tests: 3959 run, 1 failed, tests from f7e462acb76e567fb41f4a1bb5c72dd18c225fac, src from c452be60d4b91045a1088dd2e4335a5c32d9af4f", the one failing name test_claude_starter.TASK132AC3Arguments.test_the_runtime_file_constants_are_verbatim (the test whose expected value the task changes); and (ii) the review of the whole diff by a model other than the implementer's (above). The task work was done by claude-sonnet-5-5 (the worker's statement of its model; not read by script). The pushes are the worker's route under their own decisions, outside the task's capabilities.

## Budgets
Tokens and wall time were not measured against the contract's budgets (300k, 3h); no figure is claimed. Retries: none. human_attention: 0m.

## Exit review of the deferred items (master plan section 6, points (3), (5) (c) and (6))
### Touch rule (point (6) (b))
The contract's touch list. None is closed by this task:
- DEF-0139: its Scheduled in (the next change to claude_starter.py) is met. None of its items is done: the task changes two literal lines and no other byte. Items 1, 3 and 7 are text of another task; items 2, 4, 5, 6, 10 and 11 are stated limits; item 8 is concept-governed; item 9 (the pin typed twice): the two literals are changed together and checked by the test of line 249 and by the CI check; DEF-0141's open point that no unit test checks the typed pin against the settings file stays open. A dated entry in the records commit.
- DEF-0149: the pin of its point (2) is moved on this commit; the live settings file is not written, so the item stays open. A dated entry in the records commit, which also carries the review findings of CI revision 32 not applied (D-7803, D-7804).
- DEF-0151: its Resume when (a launch ending "capture" for an expired lease) is not met; the starter's timeout is unchanged. No entry.
- DEF-0154: its Resume when (a change of the EVALUATOR lists or of EVIDENCE_DEFINING_PATHS, or the BT3b-2 contract) is not met by this task; src/aieos_runtime/** stays outside the lists (D-7107). No entry.
The list was made from the contract's touch list and a reading of those items' texts; it is not a proof that no other item is met.

### Accepted limits (point (6) (a))
- L1: the settings file is not written by this task; until step 5c the starter refuses to start. Carried under DEF-0149 (Blocks v0.1: yes); no new item.
- L2: the CI accepts either of two settings pins until step 5d. Why not a new blocker: the starter holds one pin, and step 5d is a named step of D-7802 with its own decision.
- L3: the base-test prediction run, the suite slices and the added-line scans are the worker's own runs outside the task's capability. Blocks v0.1: no: CI repeats the base tests and runs the tests.
- L4: docs/runs/second-real-run-pre-run-record.md :33 states the old pin as read on 2026-11-28 and is not changed. Blocks v0.1: no: a dated reading; DEF-0149 records the new pin.

### Counts (point (6) (d))
At the contract commit: 83 open, resumed or waiting-owner items, 14 of them 'Blocks v0.1: yes' (159 files). This task: opened 0, dropped 0, closed 0; open after it 83, of them 14 'Blocks v0.1: yes'. Entries under point (6) (a): none new. The records commit recomputes the counts by script and stops if they differ.

### The clean-up (point (6) (c), revision 13; D-7754 C6)
Closed as done toward the 36 of the first batch's rise: 0 by this task; running total 17 of 36, 19 remaining. Batch 2: TASK-173 is its fifth accepted task. TASK-173 is a product task, the one between two clean-up tasks that revision 13 allows; the next planned clean-up task is N1 (D-7754).

## The limits (AC7), as the contract states them
(1) The settings file (C:\Users\Admin\AIEOS-runtime\claude-settings.json) is outside the repository and is not written by this task; its write is step 5c, at the owner's own permission prompt; until it is written the starter refuses to start with the new pin, and no launch is made. (2) This task lands under CI revision 32 (the two-value window); step 5d returns check_starter to the single new value and is an open obligation, its own decision under DM A66; step 5e (the rules removed after the run) is the owner's typed word. (3) The slice runs, the base prediction and the scans are the worker's own runs. (4) The evidence profile is that of risk high. (5) The task enables no launch: nothing under C:\Users\Admin\AIEOS-runtime is read or written and neither aieos launch, the starter nor the runtime program is run. The step 5c write is checked against the new value and the content AC3 names before any launch, and the two Edit rules stay in the written file until step 5e.

## Route slips (recorded)
Worker: the generated push script was run once in its "checks" mode without a decision naming that run; it stopped at its first local check, before any remote read, and wrote nothing (D-7816, recorded as a departure without harm). The two generated scripts keep a stale script name in a comment line.

## Evidence kept
The files of this task in the session scratchpad (t173, bt5 and the checkpoint entries) stay until a later decision; the kept copy of the settings variant is C:\Users\Admin\AIEOS-REG0-lite\bt5-d7810. The scratch clone c173treal was removed under D-7818.

## Not done
The records commit (this text, the entries above and the history page), its branch, its landing and their CI follow by their own decisions. Steps 5c, 5d and 5e of D-7802 are not done.

## Correction (2026-11-28, D-7838, D-7839)
Added after this acceptance; no line above is changed. Decided by: decision agent (A41, A51), D-7838 and D-7839. The text above states that TASK-173 is batch 2's fifth accepted task and gives no end count of the batch (master plan section 6 point (6) (c)). That count was missed by D-7817, D-7820 and D-7837 and by the worker's texts.
- Batch 2 is TASK-169 to TASK-173. Count at its start: 100. Count at its end: 112, which is 83 open at this task's acceptance, plus 9 entries added under (a), plus 20 accepted limits, plus 0 dropped. The rise is 12 (110 and 10 without two doubtful entries, which are counted because a line in doubt is counted).
- The readings (D-7838): (R1) a finding carried by an entry on an open item counts once, as the entry; so TASK-171's limit L2, carried by that task's entry on DEF-0043, is counted there and TASK-171 counts 4 limits (its text says 5), and this task's L1, carried by its entry on DEF-0149, is counted there. (R2) a limit recorded in an acceptance counts even if a later step ended it (this task's L2). (R3) a dated entry that carries review findings not applied onto an open item is an entry under (a).
- The 9 entries: DEF-0041 and DEF-0063 (TASK-170); DEF-0043, DEF-0113 and DEF-0114 (TASK-171); DEF-0137 (the findings of CI revision 31); DEF-0149 (the findings of CI revision 32 and this task's L1); and, in doubt, DEF-0110 (the gap noted with revision 31's records) and DEF-0137 (the line of the pre-run record of the second real run). The 20 limits: TASK-169 5, TASK-170 4, TASK-171 4, TASK-172 4, TASK-173 3.
- The clean-up: a clean-up series can close at most 9 items, so the clean-up of batch 2 is deferred once to the end of batch 3 (D-7839, under the rule's own clause; the owner is told). The next task, N1, is a clean-up task of the first batch, and its closures count toward that batch's 36 (17 closed so far). Batch 3 starts with N1; its start count is 83.

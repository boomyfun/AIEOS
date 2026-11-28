# TASK-176 acceptance (session 228f426b-33cd-4e2a-bb1d-86cdfeccd36d; 2026-11-28). Accepted by: decision agent (A41, A51), decision D-7906 (the task, bound to commit afb2b7d7f65804133752117a788f4a9eb48ac51f and to the contract at e3618832318fd4d6466a8c1d5d41c164956633a5). The text is written by the worker from the decisions D-7887 to D-7906 and is the worker's record of the route; the acceptance is the decision agent's; the evidence is same-lineage, not independent.

Task branch task/TASK-176, one task commit afb2b7d7f65804133752117a788f4a9eb48ac51f (tree d786a0376a0f26e9e43e858833dfa0fd761402a4) on the contract commit e3618832318fd4d6466a8c1d5d41c164956633a5 (docs/tasks/TASK-176.yaml, sha256 c48dfbca07ff05a5ba18d44fb8644d6f73c92f42ff871894705023777f02be3c, base_commit be65669702c4865b0ccb4faa0a04c7aa30c41ea6). N2, the next clean-up task of the first batch (D-7754, D-7887, D-7888): DEF-0052 and the CONTINUE half of DEF-0034 F-a. Risk high. Six paths, all M, 85 lines added and 18 removed (sha256 of the committed bytes):
- src/aieos_bootstrap/records.py e28029dc2d8185cf2865a68c7611fea918b675411e7eb907faf6e11c2f3f27f3
- src/aieos_bootstrap/gitread.py d86197af5488769dac44bc9485fd6800e07cc245ea1334a99e3e983166f8b3b6
- tests/unit/test_records_execution.py b571b724b08bc601a8f8b3930c93e8f078d091e84d0bdd95156a3836624ed90c
- tests/unit/test_gitread.py 0d56bab448b581adb3d094a8a92f29b54289a09a00cbd5244c13dc0ae2e49ac4
- tests/unit/test_scope_reconcile.py ec25d9a868705d065ba0a0335f535aba8a1da19288d17a67e677a00182ace0bf
- tests/unit/test_cli_import.py 5ee23e59b7517cec075acc811f70ef9622801c94d9646346213fa2a5a0ed18f4
Diff sha256 dac80e26d4f56cad3fd4cdb881bbee057484e45beae99b67d77588b65d34b10a.

## The route (decisions)
D-7887 (N2 chosen next, its read-only planning); D-7888 (the plan judged); D-7889 (the contract draft's other-model review); D-7890 (the flagged review judged; DEF-0034 stays open); D-7891 (draft v2; the dry contract commit); D-7892 (the contract commit); D-7893, D-7894 (its branch; a condition on a silently enforced check); D-7895 (the branch CI; the landing and push of main); D-7896 (main's CI; the change and the local runs); D-7897, D-7898 (two conditions of D-7896 and D-7897 corrected); D-7899 (a guard refusal); D-7900 (the local runs; the task commit and its other-model review); D-7901 (the review judged; the task branch pushed); D-7902 (its CI judged); D-7903 (the decision agent's review); D-7904, D-7905 (the two errata); D-7906 (this acceptance).

## The CI
Branch task/TASK-176, head afb2b7d7: aieos-checks 46146502188 and aieos-native 46146502185, event push, attempt 1, success; 26 and 19 conclusion fields, all success. Read against the shape written before the push (expected_shape_task_176.txt, sha256 ff0adf570a687485a6758f3464da9b9e9ee6d69260ceebb234c88dc29487b9db) in the fetched logs (log_46146502188.txt sha256 9671032e0120e26571c3e2ccb7f1d9544835dcc20d5ba7acc3148a2e6e2c5c4a; log_46146502185.txt b313c2e5a9588e5050ec0dc056174fdbaa06cc98c3ac7450ea977def6585a74a), judged with no departure (D-7902). The two lines AC7 asks for, from the run on refs/heads/task/TASK-176:
- "G0 detect: task TASK-176 contract commit e3618832318fd4d6466a8c1d5d41c164956633a5 base be65669702c4865b0ccb4faa0a04c7aa30c41ea6"
- "G0 contract sha256 c48dfbca07ff05a5ba18d44fb8644d6f73c92f42ff871894705023777f02be3c"
Also: "G0 scope: task TASK-176, commits 1, paths 6, failures 0"; "Ran 3503 tests", "Ran 236 tests" and "Ran 227 tests", each OK; "deterministic_rule: files 288, changed paths 6, findings 0"; "OPS-003: files 288, findings 0"; SEC-001, SEC-002 and SEC-003 0; "OPS-002 paths: 0 of 6 changed paths are owner-kept"; "GOV-003 evaluator lists: 2 found, equal, 40 entries"; "GOV-003 evaluator change: yes (6 of 6 changed paths)"; "replay: event logs 1, decision records: 10, replayed and passed: 8, failed: 0, not replayed (violation path): 2"; "conformance base run: outcome pass, record conformance-run-cc29e9040b8f4135d1915b5d95c70c39ae3913f6a907825b966e3f022d453f2c"; no candidate run; native PASS and ok on linux and windows. Same-lineage CI evidence: bandit printed "No issues identified." and no pyflakes finding line was found. The CI printed the pins AIEOS_PINNED_GOVERNOR 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f and AIEOS_PINNED_RESUME_CHECK b03c0b8a1caaa77c2974da0b512bd38e1f330b5d08dda1bbd85427944eee2e76.
Main, head afb2b7d7: aieos-checks 46148527568 and aieos-native 46148527589, event push, attempt 1, success; 26 and 19 success conclusions, read against the shape written before the push of main (expected_shape_main_task_176.txt, sha256 f65336bf0e2e9d600dbfabf1b6627b2efc0af3911ad9d9a2ef4b2adac22c9970) in the fetched logs (log_46148527568.txt sha256 0ae17be8fc02ef957e023f501c489cb5c428b4c4c83b12f54206b72bcf8b247b; log_46148527589.txt 19c6cec0e04af8ede2b5d8c225d4c3204e48c6813d636aa40486408c9b6cbb39), judged at D-7909 as matching with one stated finding: no task on main, the six paths, and "conformance base run: outcome pass" with the same record id as on the branch, which is expected because the base and the task are the same. ITEM 6, linux native governor on main: UNPROVEN. No line of this step is in GitHub's log. Two downloads of the run log (sha256 19c6cec0e04af8ede2b5d8c225d4c3204e48c6813d636aa40486408c9b6cbb39) and the job log (sha256 cbd56fa65736a9b498db065a991b8b95d299ea28254c105cdc5dd63d5e7fb6bc) were checked. The step concluded success, 13:13:26Z-13:13:41Z, and the job log has no group of the step between the toolchain step and the resume check. The same commit's task-branch run 46146502185 printed PASS and ok on linux (log_46146502185.txt :331-:332; D-7902). Every other item of the shape matched. Nothing was re-run (D-7908, D-7909). A main run shows no task-bound step; for those the evidence is the branch run of the same commit. The exit condition on main's aieos-checks run is met. Before the push of main (D-7907) the check printed "task trailer lines: 1" and "AIEOS-Task trailer values of the range: TASK-176".

## The local runs
All are the worker's own runs under D-7896 to D-7899, outside the task's shell capability (AC10); none is part of CI. The suite on the change in the work clone, 24 slices of run_slice_176.py, each under timeout 110: 3966 run, 0 bad, 1 skipped (suite_head_176.txt sha256 265b7053988395069cbcba9f08c4f8f1fbbdc2e2b452a306c1db6d4f4241d6dd). The base tests of e3618832 against the changed records.py and gitread.py: 3961 run, 0 bad, 1 skipped (suite_pred_176.txt 59ef42714b9760a56eb13f2340ee4c02550cc8e1b981125a69d53fe5f4d93cea, a file of slice counts only, the same bytes as TASK-175's). The added-line scans (scan_176.py): "paths 6 added lines 85", SEC-001 0, SEC-002 e-mail 0, SEC-002 GitHub URL 0, OPS-003 label 0, OPS-003 word 0; over the task commit (D-7900): secret matches 0, e-mail or GitHub URL in added lines 0, label words 0, "OPS-003: files 288, findings 0". No added line is over 120 characters (D-7898).

### The broken copies (AC1 to AC7), the output of broken_176.py unedited
The script prints each line of a run cut at 260 characters. It was not saved to a file when it ran; this block is its standard output as the session's transcript holds it, taken by script (broken_out_176.txt sha256 09e979b7d9b630b073b7c6fa32c36fc9ee58a1923b6490f300eeb30797a003e9). The runs are on this machine (Windows).
```
intact 7 tests
   exit 0
    run 7 failures 0 errors 0
broken ac1_old_rule
   exit 1
    FAIL: test_a_fired_check_never_carries_continue (test_records_execution.R2Forms.test_a_fired_check_never_carries_continue)
    AssertionError: '6.4:checks' not found in []
    run 1 failures 1 errors 0
broken ac2_no_nul_check
   exit 1
    FAIL: test_a_path_holding_a_nul_is_refused (test_gitread.TheProcess.test_a_path_holding_a_nul_is_refused)
    AssertionError: None != 'PATH holds a NUL byte'
    run 1 failures 1 errors 0
broken ac3_colon_split
   exit 1
    FAIL: test_the_path_is_split_on_the_platform_separator (test_gitread.TheProcess.test_the_path_is_split_on_the_platform_separator)
    AssertionError: 'PATH has an empty or relative entry' is not None
    run 1 failures 1 errors 0
broken ac4_no_refusal
   exit 1
    FAIL: test_a_repo_beginning_with_two_separators_is_refused (test_gitread.TheProcess.test_a_repo_beginning_with_two_separators_is_refused)
    AssertionError: isdir called
    run 1 failures 1 errors 0
broken ac5_empty_accepted
   exit 1
    FAIL: test_an_empty_task_trailer_value_passes_no_trailer_task (test_scope_reconcile.TheCommit.test_an_empty_task_trailer_value_passes_no_trailer_task)
    AssertionError: {'ref': 'ca5e34db5511fbcfb9e934788f10ee299d0f8c90bd1a7d9715b11714fd402571', 'detail': 'trailer out of form'} not found in []
    run 1 failures 1 errors 0
broken ac6_old_gitread_rule
   exit 1
    FAIL: test_the_three_modules_name_their_criteria (test_gitread.SingleWrapper.test_the_three_modules_name_their_criteria)
    AssertionError: Lists differ: ['test_a_path_holding_a_nul_is_refused', '[381 chars]ria'] != []
    run 1 failures 1 errors 0
broken ac6_old_scope_rule
   exit 1
    FAIL: test_every_test_names_its_criteria (test_scope_reconcile.Naming.test_every_test_names_its_criteria)
    AssertionError: {'TASK-176'} not less than or equal to {'TASK-034', 'TASK-035'} : ('TheCommit', 'test_an_empty_task_trailer_value_passes_no_trailer_task')
    run 1 failures 1 errors 0
```

## Exit condition (TASK-176.yaml exit_conditions)
- "all gates pass": met on the task branch (G0 scope above; G1 and G2: the CI; G3: the CI lines above and this text, GOV-003 as stated below).
- "an other_model_review and a separate decision_agent_review, both bound to the evaluated commit, the contract and the pins, before any fast-forward of main": met (below).
- "the task acceptance by the decision agent before any landing step": D-7906.
- "the aieos-checks run of the accepted commit succeeds": met on the branch (run 46146502188) and on main (run 46148527568; judged at D-7909, stated under The CI).

## Evidence profile (high) and the reviews
unit_test, integration_test, deterministic_rule and static_security_analysis: met by the CI run. The cross-model entry ai_review:
- other_model_review: one claude-haiku-5-5 review in its own session, unflagged, with the approved prompt, of the whole diff of afb2b7d7 against the contract and article by article (transcript subagents\agent-a256e90cc97d4c6a7.jsonl sha256 5edce03d5ce41921af6cde2cd2c8a0185400278722c929918b3569f60008b276; report review_task_r1_report.txt 98863ee818bc911bf2ccabd5dccedf62ef59853bb68db19861f856a439090ddf; judged D-7901, record sha256 c282cd81909528d098423eea1efecfc1224d26b40415cc98eb4d9242e9ce2ab1). AC1 to AC6 met by reading; its findings and their settlements (D-7901):
  - F1, GOV-003 does not hold as the article reads: stated below (AC9).
  - F2, the contract's line numbers are those of the base: this text's evidence lines are at the task commit.
  - F3, only PATH is checked for a NUL byte: accepted limit L4.
  - F4, a local root beginning "\\?\" is now refused: accepted limit L5.
  - F5, an uneven docstring wrap in gitread.py: a style finding, not applied (a new commit would void the review).
- decision_agent_review = D-7903 (record sha256 2b993ff035dbe756cc2ae65cd6b2fa6be5023db5f48d1e4659e3492a681b7300): passed on the whole diff, bound to afb2b7d7, tree d786a037, parent e3618832, contract c48dfbca..., diff dac80e26... and the CI runs above. Its N1 (the AC4 test patches os.path.isabs to True for all four forms on every platform, broader than the criterion needs; on POSIX the backslash forms are refused earlier as not absolute): stated here, not applied. N2 (the Linux half of AC3's broken-copy claim rests on reading, not on a run): part of accepted limit L6. N3 (frozenset(EXECUTION_ORDER) rebuilt for each item, consistent with records.py :628) and N4 (the docstring wrap, review F5): style, not applied.
The contract draft: one claude-haiku-5-5 contract review (review_contract_report_FLAGGED.txt 15dbc451aa913e59023fcd017e7dcce89ee847cc47bcd1226a5035c0d869bf23), flagged for four searches whose path was the export folder itself; its use was allowed and its findings were settled by D-7890.

Limits of the coverage: the reviewers ran nothing. The decision agent read the diff, parts of the work tree and the local refs but no Git object; that these are the content of afb2b7d7 rests on the worker's scripts and on the CI's six collected paths. The reviewers and the decision agent are Claude models, and the decision agent also decided the earlier steps of this build. Limit of the blindness: the harness puts the project's memory index and the git status with recent commit subjects into each reviewer's context.

## Evidence by criterion
Line numbers are at afb2b7d7.
- AC1: MET. records.py :590 requires a fired check's outcome in EXECUTION_ORDER (:134-:135); the docstrings :28-:30 and :578-:580; tests/unit/test_records_execution.py :130-:136.
- AC2: MET. gitread.py :208-:209, its docstring :203-:207; tests/unit/test_gitread.py :274-:285.
- AC3: MET. tests/unit/test_gitread.py :287-:292.
- AC4: MET. gitread.py :158-:159, with the docstrings; tests/unit/test_gitread.py :294-:302; tests/unit/test_cli_import.py changes only the docstring of test_the_root_forms.
- AC5: MET. gitread.py trailers docstring; tests/unit/test_scope_reconcile.py :229-:236; scope_reconcile.py unchanged.
- AC6: MET. tests/unit/test_gitread.py :646-:666; tests/unit/test_scope_reconcile.py Naming; the old rules fail (the output above).
- AC7: MET for the branch (the local runs and the CI above). The task commit went to main after this acceptance (D-7907); main's CI is stated under The CI (D-7909).
- AC8: open until the records commit, which writes this text, the Log lines below and the history page; the forms and counts are stated below.
- AC9: stated under GOV-003 below.
- AC10: the limits below.

## DEF-0052, point by point (AC8; D-7753: 1 done by a change in the task, 2 record note, 3 accepted limit, 4 carried by an open item's cited line)
- G4: form 1 (AC2). G5: form 1 (AC3). F15: form 1 (AC4). F16: form 1 (AC5), with scope_reconcile.py :395-:400 and recovery.py :137-:148 cited: the only reader of the trailer pairs refuses an empty value, and the other readers' parser gives a finding for it.
- E1: erratum (b) below (D-7905).
- G1 and F6: form 4: carried by DEF-0030 :30, open.
- F8: form 2: the first commit message's strongest claim was corrected in the second commit's message (D-580); both messages are permanent history.
- F14 and G7: form 3: accepted limits L1 and L2.
- G2, G3 and F13: settled (TASK-102, DEF-0052's Log of 2026-10-30); at afb2b7d7 the Windows limit is in gitread.py's docstring (:52-:55), the environment test at test_gitread.py :249 and the naming test at :646.
- The stale sentence "no caller exists yet": amended by TASK-110 (the Log of 2026-11-06).
With these, DEF-0052 closes as done in the records commit.

## DEF-0034 stays open (AC8; D-7890 C3)
The records commit adds one dated Log line, Status unchanged: F-a's CONTINUE half is done by TASK-176 (records.py :590); F-d and the TASK-008 part are settled; the tie of the fired checks to outcomes_fired is not done. Resume when: the next revision of specification 3, which states the tie (its own decision); resolved by the task after that revision, with records.py, tests/unit/test_records_execution.py and tests/property/test_records_execution_properties.py in its write set; what goes wrong if it is not done: a decision.execution record with a fired ESCALATE check, outcomes_fired [] and decision CONTINUE passes records.py :624-:631 (base lines).

## The errata (AC8; dated 2026-11-28; no file or commit they quote is changed; decided by: decision agent (A41, A51), D-7904 for (a), D-7905 for (b))
- (a) docs/tasks/TASK-011.yaml :171-:172 (AC2): "outcome an execution decision value when status is fired and null otherwise" (the line break removed). Correct reading from TASK-176's task commit: outcome a value of EXECUTION_ORDER, that is an execution decision value other than CONTINUE, when status is fired, and null otherwise (src/aieos_bootstrap/records.py :590 and :28-:30 at afb2b7d7). The rest of the criterion is not changed by this reading.
- (b) docs/tasks/TASK-024.yaml AC2 (from :196), AC10 (from :256) and AC12 (from :270): erratum E1 of TASK-024 revision 0, decided by the decision agent (A41, A51) at D-580 and recorded in that decision's file; the contract on main is unchanged and the erratum stands beside it. Its text, byte for byte from the record: "Erratum E1 to TASK-024 revision 0 (decision D-580): AC2's PATH clause reads: PATH (copied from os.environ, or the empty string when absent); run refuses, before any process starts, with the refusal result of AC3, when that PATH is empty or, split by os.pathsep, has an entry that is empty or not an absolute path. AC2's environment also holds GIT_NO_LAZY_FETCH "1". AC10's limits add: on Windows the program search stated in AC2 does not use the PATH passed to git, so this refusal closes the route of a relative or empty PATH entry on POSIX only; on a git older than 2.44 GIT_NO_LAZY_FETCH is ignored, and on one older than 2.32 GIT_CONFIG_GLOBAL is; output is not capped in size. AC12 R2 tests the refusal (an empty PATH, an empty entry, a relative entry, and the passing case) and the added key." Reading since TASK-176: run also refuses a PATH that holds a NUL byte and a repository path that begins with two separators; those are TASK-176's criteria, not part of E1.

## GOV-003
The task changes six evaluator paths (src/aieos_bootstrap/** and tests/unit/**), so GOV-003 does not hold for the commit and is not claimed to hold (the other-model review judged the same). Handled as a stated departure (the policy of DEF-0110) with two controls: (i) the base tests on the change, the CI line "GOV-003 base tests: 3961 run, 0 failed, tests from be65669702c4865b0ccb4faa0a04c7aa30c41ea6, src from afb2b7d7f65804133752117a788f4a9eb48ac51f" (log_46146502188.txt :9160), with no failing name; and (ii) the review of the whole diff by a model other than the implementer's (above). The task work was done by claude-sonnet-5-5 (the worker's statement of its model; not read by script). The task commit carries exactly one AIEOS-Task trailer line (the push check printed "AIEOS-Task trailer values: TASK-176", D-7901); the pushes are the worker's route under their own decisions, outside the task's capabilities.

## Budgets
Tokens and wall time were not measured against the contract's budgets (400k, 4h); no figure is claimed. Retries: none. human_attention: 0m.

## Exit review of the deferred items (master plan section 6, points (2), (3), (5) (c) and (6))
### The items the contract traces to, one dated line each in the records commit
- DEF-0052: done: every open point in one of the four forms, at least G4, G5, F15 and F16 done by a change. Resume when (the next task that changes gitread.py) met by this task.
- DEF-0034: not done: see above. Resume when (as its Log of 2026-10-11 restates it, D-415 C3: the next revision of specification 3 or the next task that changes records.py or its tests) met by this task for F-a's CONTINUE half.

### Touch rule (point (6) (b))
The contract's touch list, besides the two above. None is done by this task:
- DEF-0024: its Resume when (the next task that touches the checker or the evaluator) is met by the change of records.py. Its points are other behaviour of the checker and the workflow; not scheduled ahead of new work, recorded why (point (2)). A dated state entry in the records commit, Status unchanged.
- DEF-0030: its Resume when (after TASK-008 and TASK-005b, before M3 exits) was met before this task; its open points (the writer and later notes) are not changed by this task. No entry; it carries DEF-0052's G1 and F6.
- DEF-0033: Resume when (a revision of specification 2 or 3) not met.
- DEF-0051: Resume when (the core's submission path) was met before this task; its points need a specification revision and a later task. No entry.
- DEF-0056: Resume when (the caller of record_evaluation and evaluate_task, or an event id change) not met.
- DEF-0061: Resume when (a hardening task before M4's exit) is not met by this task, which changes one test of test_scope_reconcile for its own criteria.
- DEF-0063: its points are carried to the next change of its files, the benchmark route's; none is changed.
- DEF-0069: Resume when (a task that touches evaluation.py, among others) not met.
- DEF-0071: Resume when (evaluation.py or records.py's outcome set) not met: the outcome set it names, OUTCOMES (pass, fail and blocking; records.py :103 at afb2b7d7), is unchanged; the task narrows only the outcome a fired check may carry, which is another set.
- DEF-0100: Resume when (specification 3's next revision or resume_check's budget parse) not met.
- DEF-0101: Resume when (the real runtime starter and the read after the session) not met.
- DEF-0133: Resume when (the M8 exit review) not met.
- DEF-0142: Resume when (the fix route chosen and landed) not met.
The list was made from the contract's touch list and a reading of those items' texts; it is not a proof that no other item's Resume when is met.

### Accepted limits (point (6) (a)), each Blocks v0.1: no
- L1 (DEF-0052 F14, D-7753): the integration test of gitread needs the full history. Why not blocking: stated in its docstring; no fix, because the test's purpose is to read the real history.
- L2 (DEF-0052 G7, D-7753): that test fails on a machine whose real PATH has an empty or relative entry. Why not blocking: it fails closed, by intent. Why no fix: the test reads the real environment on purpose, and such an entry is the case run's refusal exists for.
- L3 (D-7890 C4): a line "AIEOS-Task:" with no space is not a trailer line to gitread (at the base, gitread.py :103 and :233-:235), so the commit is read as naming no task (scope_reconcile.py :395-:399), which fails closed to drift.detected (scope_drift.py :201-:203, :255-:261), as the CI's G0 grammar does. Why not blocking: fail closed; a case that lets such a commit pass with task paths would be a fix.
- L4 (D-7901 F3): only PATH is checked for a NUL byte; the other values git gets come from os.environ, literals or os.devnull, so a NUL in them is reachable only through a replaced environment(). That os.environ cannot hold a NUL is a reading of the standard library, not a run. Why not blocking: no caller reaches it.
- L5 (D-7901 F4; AC10): form_error sees the path's form only: a local extended-length root beginning "\\?\" is refused, and a mapped drive letter or a link that leads to a network share passes. Why not blocking: the refusal fails closed, and a caller passes a drive-letter path; the passing cases are as before this task.
- L6 (AC10; D-7903 N2): the slice runs, the base-test run, the broken-copy runs and the added-text scans are the worker's own runs, on Windows; the Linux half of AC3's broken-copy claim rests on reading. Why not blocking: CI runs the same tests on Linux and the base tests on the change.

Main's CI finding (D-7909), stated and not counted among L1 to L6: the linux native governor lines of main's run are unproven, as stated under The CI.

### Counts (point (6) (d))
At the contract commit: 80 open, resumed or waiting-owner items, 14 of them 'Blocks v0.1: yes' (159 files; no change under docs/Deferred since be656697). This task: opened 0, dropped 0, closed as done 1 (DEF-0052); open after it 79, of them 14 'Blocks v0.1: yes'. Entries under point (6) (a): 1, the dated Log line on DEF-0034 carrying the tie finding (D-7890). Accepted limits 6 (L1 to L6). The state entry on DEF-0024 carries no finding and is not counted. The records commit recomputes the counts by script and stops if they differ.

### The clean-up (point (6) (c), revision 13; D-7754 C6, D-7839)
Closed as done toward the 36 of the first batch's rise: 1 by this task (DEF-0052, open at 269d2d0a, the first batch's last task's accepting commit); running total 21 of 36, 15 remaining. Batch 2's rise of 12 is deferred to the end of batch 3 (D-7839). Batch 3: TASK-176 is its third accepted task; its count so far, from the start of 83: 79 open plus 16 accepted limits (6 of TASK-174, 4 of TASK-175, 6 of this task) plus 2 entries under (a) (DEF-0115, DEF-0034), 97.

## The limits (AC10), as the contract states them
"The slice runs, the base-test run, the broken-copy runs and the added-text scans are the worker's own runs outside the task's shell capability. The F15 refusal sees the form of the path only, not where a drive letter or a link leads. The task runs neither a hook, the runtime program nor a launch."

## Route slips (recorded)
Decision agent's conditions corrected: a check enforced silently by the push script but not printed (D-7894); a diff hash condition that two diff formats could not meet (D-7897); a long-line condition that counted existing lines (D-7898), the last two after the worker's request quoted added-line counts. Worker: the first change tool wrote a literal backslash-n and two long docstring lines, fixed before use (D-7896); a shell line named a script that does not exist, nothing ran from it (D-7896); a command with "timeout 590 python" refused by the owner's command guard (D-7899; nothing ran; not run again); the broken-copy output not saved when it ran (above); the contract review flagged (D-7890).

## Evidence kept
The files of this task in the session scratchpad (t176 and the checkpoint entries) stay until a later decision. The scratch clone c176treal was removed under D-7907.

## Not done
The task commit is landed on main (D-7907) and main's CI judged (D-7909); the records commit (this text, the Log lines above and the history page), its branch, its landing and their CI follow by their own decisions. DEF-0034 is not closed. No second real run.

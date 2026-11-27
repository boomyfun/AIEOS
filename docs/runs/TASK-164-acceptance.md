# TASK-164 acceptance (session 228f426b-33cd-4e2a-bb1d-86cdfeccd36d; 2026-11-27). Accepted by: decision agent (A41, A51), D-7474 (the task, bound to commit 21bb1e257ad7854ca3c75765cc6670e401b00fdd). The text is written by the worker from the decisions D-7441 to D-7473 and is the worker's record of the route; the acceptance is the decision agent's; the evidence is same-lineage, not independent.

Task branch task/TASK-164, one commit on the contract commit 7c22ad098d6c118b7fd9a7cda4f92e15f8995e1d (docs/tasks/TASK-164.yaml, sha256 e836da3f112a562a78380938383c581b647089a16d888bc90818ba249ff32b30, base_commit 959471688d34798ffc93741f8380be1e0336e5d5): 21bb1e257ad7854ca3c75765cc6670e401b00fdd. Risk high; the task of DM A82 point (2), option (a) of DEF-0153: the G3 step of the low run-made plan is "constitution" in place of "review", and the default check map of the gate maker holds the seven CI steps of that gate that can fail. Seven paths, 168 insertions, 19 deletions (sha256 of the committed bytes at 21bb1e25):
- src/aieos_bootstrap/ci_evidence.py (changed) b5e6c035920a66887e6ffa75603be4bcde174a1b2ec21be650278b235fab8a5a
- src/aieos_bootstrap/eval_inputs.py (changed) 1025bc0bb074e171b184e0a9b850ffc8cb5f9b9484d77e86c10dc6310a1d9c69
- src/aieos_bootstrap/gate_records.py (changed) f7b1e6dbceb6ec003be532b2f7c8d771a0134432c7d3fa9b6b4838b7203bf81e
- src/aieos_bootstrap/launcher.py (changed) 3871fdd8568ca801a3b5e44041ec052cffd54115b853e7fb987da2675e6ce57d
- tests/unit/test_ci_evidence.py (changed) f8bc235ff3ca622bed3753fae3f5d9eebeab9a2eec1dce61091341250f3434aa
- tests/unit/test_cli_run.py (changed) 914bff5242b0c8b1028af0e9eccceeabc4a0237069607039f5e7d5d70e8734fa
- tests/unit/test_gate_records.py (changed) fa7cb1d0dbc7fd25ff23650f5144358ddc9fffccfc1037a0d029df2a88729028

## The route (decisions)
D-7441 (the design); D-7456 to D-7466 (the missing producer found and ruled, the contract drafts, the Haiku 5.5 draft reviews R-A and R-B and their rulings, the base-test prediction of nine failing tests of 3804, the contract commit 7c22ad09, its branch push and CI, the landing on main); D-7467 (the main CI of the contract); D-7468 (the build, tests first, in a scratch clone); D-7469 (the diff, the touch-rule list and the dry and real task commit); D-7470 (the bring into E:\AIEOS and the push of the task branch, with the CI shape written before the push); D-7471 (the blind review's prompt); D-7472 (the branch CI accepted; the report's saver); D-7473 (the decision agent's own review and its ruling on the blind review); D-7474 (this acceptance).

## The CI (branch task/TASK-164, head 21bb1e25)
aieos-native 45912630521 and aieos-checks 45912630576, event push, attempt 1, success; 19 and 26 conclusion fields, all success. Read against the shape typed before the push (expected_shape_task_164.txt, sha256 efb7e94e9a7922e1851f739ae39e963c7ac171b3b56891f880655f130f5511c1) by the decision agent in the fetched logs (log_45912630576.txt sha256 24dfd6db951dafa266939995ffe8763bad21e5d556909e7aaba1b97f821783c1; log_45912630521.txt sha256 15c57db475a3ba417ec50f000436f45484a0d7a7b2483daba3139d6e48e8312a): every item of the shape met (D-7472).

## The local runs
The new tests over the base sources: 3811 run, exactly the sixteen tests listed before the run failing, no error. With the production change: 3811 run, 0 failed, 1 skipped. Each ran as 24 slices (unit 12, integration 6, property 6), each under timeout 110, in place of the contract's single line `timeout 110 python tests/run_tests.py < /dev/null`, because the whole suite cannot finish inside that limit. This slicing is a departure from the shell line of capabilities.shell.allow (TASK-164.yaml :375), approved at D-7468 (and at D-7459 for the prediction run). The dry and the real commit ran the CI's deterministic_rule and OPS-003 blocks locally (0 findings).

## Exit condition (TASK-164.yaml exit_conditions)
- "all gates pass": met on the task branch (G0 scope: "task TASK-164, commits 1, paths 7, failures 0"; G1 and G2: the CI and the local slices; G3: the CI lines above and this text). The contract's own G3 entry is check constitution; the map now covers it, but no gate record of this task is made by a run of the evaluation.
- "the evidence profile of risk high is satisfied (...) before any fast-forward of main": met by the pair below, given before any fast-forward of main, with the BLOCK stated.
- "the task acceptance by the decision agent before any landing step": met by D-7474.
- "the aieos-checks run of the accepted commit succeeds": met on the branch (run 45912630576); the run of main is owed, after the landing.

## Evidence profile (high) and the reviews
unit_test, integration_test, deterministic_rule and static_security_analysis: met by the CI run and the local slices. The cross-model entry ai_review: this pair on 21bb1e257ad7854ca3c75765cc6670e401b00fdd, same-lineage and not independent:
- other_model_review = claude-haiku-5-5, transcript subagents\agent-ada9ac26fd931f177.jsonl (sha256 82457a93d1d817b770c2d99883ff67d260604fb389a4e7dea4c79de2275d9858; report other_model_review_164_21bb1e25_report.txt, sha256 23f803fb46d3ff58ddb053cf18e2d661a5401bc8522abe6622adaf761e159291, 9420 bytes; prompt sha256 08fdd3329257340c96f45ad35bc9b9a873517b2f3b2dfe7f1a2cdd83106d003e, 4739 bytes; tools Read, Grep and SubagentHandback), verdict BLOCK: one BLOCKING finding F1, notes F2 to F5;
- decision_agent_review = D-7473 (claude-opus-5-5; record sha256 0086295368586f07b46629775701a619149cffb3713f6c5e8b34d9b641a6559a), PASS against AC1 to AC10; F1 ruled a stated limit; F3 a limit plus a log line of DEF-0137; F2, F4 and F5 notes with no change.
Both are bound to 21bb1e25, the contract (sha256 e836da3f...) and the seven pins above. This is a pair whose other-model member said BLOCK and whose BLOCK the decision agent settled; it is not two approvals. The reviewers and the decision agent are Claude models, and the decision agent also decided the earlier steps of this build. Limit of the blindness: the harness put the project's memory index and the git status with recent commit subjects into the reviewer's context; they carry no CI result and no opinion on the findings.

## Evidence by criterion
AC1 to AC10: MET as read at D-7473; the first review read AC5 as NOT MET (F1, below), AC7 as not checkable in full and AC9 as not checkable from the files. AC11: met on the task branch ("GOV-003 evaluator lists: 2 found, equal, 40 entries"; "GOV-003 evaluator change: yes (7 of 7 changed paths)"; "GOV-003 base tests: 3804 run, 9 failed", the nine ids named before the push: test_gate_records AC5TheDefaultMap.test_exactly_the_three_checks_with_the_exact_step_names; test_cli_run TASK098AC1Runs.test_the_single_path and .test_the_texts_are_the_templates, TASK098AC2Refusals.test_the_claim_append_refusals and .test_the_drafted_append_refusals, TASK115AC1Statement.test_the_unchanged_text, .test_the_statement_none_is_the_unchanged_text and .test_the_statement_false_decision_agent, TASK163Trace.test_both_kinds_with_a_trace); main owed. AC12: this text and the records commit.

## GOV-003
The task changes seven evaluator paths (src/** and tests/**), so GOV-003 is not claimed to hold. Handled as a stated departure with two controls, as DEF-0107 point 4 names them: (i) the base tests on the change (measured locally before the contract at D-7459 and again by the CI step: the nine predicted failures, each a pin that the task changes in the same commit), and (ii) a review of the test diff by a different model (the review above, claude-haiku-5-5, which read the test diff and found no weakened assertion other than the one AC2 requires). The task work was done by claude-sonnet-5-5 (the models of the assistant entries of the session transcript, read by script); claude-haiku-5-5 differs from each of them. The general policy stays open (DEF-0110).

## The limit, stated (AC5, F1)
Quoted verbatim from docs/tasks/TASK-164.yaml, AC5 (line 358):

> The limit (D-7441 C4), stated in the comment of AC3, in the docstrings of AC2 and AC6 where they speak of this gate, and in the acceptance text: the CI steps of the G3 constitution gate do not check the run-made contract's AC1 (launcher.py _RUN_SINGLE: the change does what the intent states), nor the path part of its AC2 (no other path is changed; G0 scope checks that). Each of the seven steps checks only what its own workflow text says, with the limits that text states (SEC-002 does not check account names; INV-010 replay does not replay decision.acceptance records; deterministic_rule is an accident filter; OPS-003 checks only effect labels and three named words; bandit skips named rules for named files and for tests). spec-04 :68 says that args name the criteria a gate checks; for this plan that is not true of the run-made AC1, this contract states the limit instead, changes no specification text and records the conflict as an open item (AC12). The run-made AC1 is judged by the decision agent's review while the task is in review (DM A82; the order: governor.py :476-:482), which is what the owner was promised in the question of A82. No text of this task says or implies that a CI step checks the run-made AC1; this contract's own verification plan binding its AC1 to G2 is no such claim either.

F1 of the blind review, stated plainly: the generated run contract's G3 line, "{gate: G3, check: constitution, args: [AC1, AC2]}", read with spec-04 :68, names AC1 and AC2 as criteria the constitution gate checks. No CI step checks AC1 or the path part of AC2 (G0 scope checks the paths). The generated contract carries no limit text beside the line. This is the open wording conflict of AC5 and AC12; the run-made AC1 is judged by the decision agent's review while the task is in review (DM A82).

F3 of the blind review, stated as a limit: the INV-010 replay step fails on any decision.acceptance record in the tree. So once such a record is in a pushed commit, the G3 constitution gate of every plan, run-made plans included, fails until the acceptance replay of DEF-0137 lands.

F2 of the blind review, stated as AC4's effect: every plan whose entry has the check constitution, the 156 project contracts under docs/tasks among them, can now get a G3 gate record from the seven steps when ci_evidence reads an eligible run. No governor rule changes and no evidence requirement is lowered (AC8).

## The outcome, stated (AC7)
Quoted verbatim, AC7 (line 362):

> The outcome, derived and stated (D-7441 C6; D-7456 C1). With this task alone, a correct run-made low task passes the gates G0 to G3 and the governor gives table row 3, INSUFFICIENT_EVIDENCE, with the next state REWORK or ESCALATED: the profile of a low task (functional build and lint, and the evidence_required of each applicable article, for a change under docs/Deferred the human_review of GOV-004, GOV-005 and OPS-002 and the ai_review of SEC-002 and OPS-003; other low paths have other applicable articles, for example GOV-003 under docs/tasks and INV-007 under docs/records) is not met. The cause: no code in src produces a build or lint evidence record or a review record for a run-made task (gate_records makes gate records only); the item that carries it, the missing producer of a run-made task's profile evidence records, is opened in this task's records commit (AC12). No change of governor.py, ac_coverage.py, the evidence profiles, the policy, .github/, spec-04 or the conformance scenarios is needed to reach NEEDS_REVIEW, and A82 is not widened. Ordering: the article reviews have to exist before the evaluation that can give NEEDS_REVIEW, and the acceptance approval, after the decision agent's review of the run-made AC1, comes after that evaluation (governor.py :476-:482). No test and no acceptance text claims NEEDS_REVIEW for a run-made task.

## AC12: limits, open items and records
Quoted verbatim, AC12 (line 372):

> Limits, open items and records, stated at acceptance: AC5 and AC7; the records commit of this task, which is not a task commit, carries no AIEOS-Task trailer and is pushed only after the task commits are on main, holds: the new docs/Deferred item for the missing producer (Status open; Blocks v0.1: yes, master plan :117; Resume when: TASK-164's acceptance; Scheduled in: the M8 task after TASK-164; what goes wrong if it is not done; governor.py :285-:319 and :467-:473) (D-7456 C2); the point (3) state of DEF-0136 on its own cause, and DEF-0153's closing line for its own cause (the plan's gate), neither with text implying that a run-made task now reaches NEEDS_REVIEW, each log line pointing to the new item (D-7456 C3; D-7441 C5); a log line with the open wording conflict of spec-04 :68 and the seven of nine steps (spec-04 :27, DEF-0153 :19); the accuracy line of DEF-0118 :35 (D-7441 C5); the counts of master plan section 6 point (6) (d) and the accepted limits of point (6) (a); the history page of specification 7 revision 16 (D-7440 C4), the history page of the deferred-list work of D-7446 to D-7455 and the L-0039 occurrence of this session (D-7455 C3). Spec-04 :32's stale lint sentence and the note that seven of the nine steps are counted stay as later wording candidates.

## Exit review of the deferred items (master plan section 6, points (3), (5) (c) and (6))
- DEF-0153: done. Closing evidence: AC2 and AC3 at 21bb1e25 (the run-made plan's G3 is constitution and the default map covers it). This closes the cause of the plan's gate only; it does not say that a run-made task reaches NEEDS_REVIEW (see the new item). Seven of the nine steps that DEF-0153 :19 names are mapped; the conformance scenarios' default plan still has no G3 (DEF-0153 :12 point (3)); both are logged.
- DEF-0136: done. Closing evidence: gate records that the governor counts now exist for G0 to G3 of a run-made low plan (test_a_run_made_low_plan_has_no_missing_gate_and_its_profile_is_not_met: missing_gates is empty; the CI above). A run-made task still does not reach NEEDS_REVIEW: its profile's records have no producer, which the new item carries with master-plan.md :117.
- New item (opened in the records commit): the missing producer of a run-made task's profile evidence records; open; Blocks v0.1: yes (master-plan.md :117); Resume when: this acceptance; Scheduled in: the M8 task after TASK-164, which gets a design decision before its contract (D-7456 C4).

### Touch rule (point (6) (b))
Deviation, 2026-11-27: the contract of TASK-164 omitted the list required by master plan section 6 point (6) (b). The omission was found before the build and is repaired here under D-7468; no build step depended on it. From the next contract the contract-filling script fills the list from git at base_commit. The list was made on main 7c22ad09 by this read-only command:

```
cd /e/AIEOS && n=0; m=0; k=0; for f in docs/Deferred/DEF-*.md; do n=$((n+1)); l=$(grep -m1 -E '^([-*] )?(\*\*)?Status(\*\*)?:' "$f"); [ -n "$l" ] || { echo "NO STATUS LINE $f"; continue; }; s=$(printf '%s' "$l" | sed -E 's/^[^:]*:(\*\*)? *//'); case "$s" in open*|resumed*|waiting-owner*) m=$((m+1)); p=""; for w in gate_records launcher ci_evidence eval_inputs test_gate_records test_cli_run test_ci_evidence; do ln=$(grep -nE "(^|[^A-Za-z0-9_])$w\.py" "$f" | cut -d: -f1 | tr '\n' ',' ); [ -n "$ln" ] && p="$p $w.py:${ln%,}"; done; if [ -n "$p" ]; then k=$((k+1)); echo "$(basename "$f" | cut -c1-8) | $(printf '%s' "$s" | cut -c1-40) |$p"; fi ;; esac; done; echo "files $n; open, resumed or waiting-owner $m; of those naming a write-set file $k"
```

Its unedited output:

```
DEF-0101 | open | launcher.py:12,22,30,42,45
DEF-0102 | open | launcher.py:14,16,17,19,41,43
DEF-0106 | open | launcher.py:12,22,29,30
DEF-0110 | open | launcher.py:27,28 test_cli_run.py:26
DEF-0113 | open | launcher.py:12,14,16
DEF-0131 | open | launcher.py:17,24
DEF-0136 | open | launcher.py:11
DEF-0142 | open (route (1) is done: the contract re | launcher.py:36
DEF-0145 | open | launcher.py:15
DEF-0147 | open | launcher.py:13,20
DEF-0151 | open | launcher.py:11,17
DEF-0152 | open | gate_records.py:11 launcher.py:50 ci_evidence.py:29 eval_inputs.py:32,35
DEF-0153 | open | gate_records.py:11 launcher.py:11,13,19
DEF-0154 | open | ci_evidence.py:26 eval_inputs.py:24
DEF-0156 | open | launcher.py:11 ci_evidence.py:11 eval_inputs.py:11,25
files 158; open, resumed or waiting-owner 102; of those naming a write-set file 15
```

State of each (DEF-0153 and DEF-0136 above):
- DEF-0101: not done here: its open points are the launcher's root and read-grant requirements; AC1 allows only the gates line and its comment in launcher.py. Schedule unchanged.
- DEF-0102: not done here: read_set_record.py is not touched. Schedule unchanged (the Resume Check and records fix task).
- DEF-0106: not done here: its 'Resume when' (the next task that changes launcher.py or cli.py) is met by this task, but AC1 allows no other text change; scheduled in the M8 launcher text-fix task.
- DEF-0110: not done here: no evaluator path policy (see GOV-003 above); schedule unchanged.
- DEF-0113: not done here: neither run_task nor import_task changes. Schedule unchanged (the launcher text-fix task).
- DEF-0131: not done here: not about the low run template; schedule unchanged (M8).
- DEF-0142: not done here: the read-set size route (2) is untouched; "Scheduled in: not scheduled (route (2) and the core replan command; closure pass 2 gives it a schedule)" stays.
- DEF-0145: not done here (the intent text in the Work Order); schedule unchanged.
- DEF-0147: not done here (the root-after check); schedule unchanged.
- DEF-0151: not done here (the capture lease time); schedule unchanged (BT4).
- DEF-0152: not done here: the rerun agreement now covers the seven new step names (AC4), which the item's duties already ask of the caller; the open duties stay scheduled (BT4 and the second real run).
- DEF-0154: its 'Resume when' ("or the BT3b-2 contract") was already met by an earlier BT3b-2 contract and was not acted on then; state now: scheduled, with its current 'Scheduled in' (M8, with or before the BT3b-2 evidence comparison). Neither list changes in this task.
- DEF-0156: not done here (no intent-version producer); schedule unchanged.

### Entries added to open items (point (6) (a), in the records commit)
- DEF-0137: since TASK-164 the INV-010 step's failure on any decision.acceptance record also fails the G3 constitution gate of every plan, run-made included; status and schedule unchanged (F3).
- DEF-0106: the wording conflict of spec-04 :68 (F1): the generated run contract's G3 line names AC1 and AC2 in its args and carries no limit text beside it; with it the seven of nine steps (spec-04 :27) and spec-04 :32's stale lint sentence. Resume when: specification 4's next revision, or the M8 launcher text-fix task, whichever comes first. Resolved by: the M8 launcher text-fix task (DEF-0106's Scheduled in) together with specification 4's next revision. What goes wrong if it is not done: a reader of the generated contract, or ac_coverage, takes G3's args as saying that a CI step checks the run-made AC1. Blocks v0.1: no (text; the governor does not read args).

Also in the records commit, a correction on a done item that is not counted under (a): the accuracy line of DEF-0118 :35 (the default plan of conformance-scenarios-initial.md has no G3).

### Accepted limits (point (6) (a)), each Blocks v0.1: no
- L1: each of the seven steps checks only what its workflow text says (AC5). Why not blocking: the run-made AC1 and the whole change are reviewed by the decision agent before acceptance, and the governor gives no ACCEPT.
- L2: five of the seven steps check more than the task's change, so a finding elsewhere in the repository fails the gate (AC4). Why not blocking: the failure is closed (rework), and the remedy is to repair the finding.
- L3: a first attempt of one of the seven steps that fails for want of a download is refused by the rerun rule; the remedy is a new commit (AC4). Why not blocking: closed, and it loses no record.
- L4: the governor transitions that AC4 names are not tested by this task. Why not blocking: governor.py is unchanged.
- L5: no real run was made; the evidence is tests with stand-ins and the CI. Why not blocking: the second real run is its own step on the owner's word.

### Counts (point (6) (d)), after the records commit
Batch 1 start: 102 open, resumed or waiting-owner at main 95947168. At the contract commit: 102 open, 16 of them 'Blocks v0.1: yes'. This task: opened 1, closed as done 2 (DEF-0136, DEF-0153), dropped 0; open after it 101, of them 15 'Blocks v0.1: yes'; entries added to open items 2; accepted limits 5.

## Route slips (worker, recorded)
The contract omitted the touch-rule list (above). The first list brought to the decision agent held one false match (DEF-0123, test_launcher.py) and missed DEF-0142. A request proposed a state for DEF-0136 from a misread of "point (3)" (D-7469 C3). The refresh of the continuity copy asked by D-7455 was missed and made later (D-7467 C4, D-7468). Some rewritten docstring lines are longer than their neighbours.

## Evidence kept
The clones c164b, c164tdry, c164treal, c164bt and the other c164 scratch clones, and the head-run folders and files in the session scratchpad stay until a later decision.

## Not done
Landing on main, the main CI and the records commit (the new item; the lines of DEF-0153 and DEF-0136 closing them; the DEF-0137 line; the DEF-0106 line; the DEF-0118 :35 line; the history pages; the L-0039 line) follow by their own decisions. The producer task, closure pass 2 and BT4/BT5 follow. A second real run is made only on the owner's word.

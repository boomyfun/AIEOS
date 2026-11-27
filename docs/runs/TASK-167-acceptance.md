# TASK-167 acceptance (session 228f426b-33cd-4e2a-bb1d-86cdfeccd36d; 2026-11-27). Accepted by: decision agent (A41, A51), D-7586 (the task, bound to commit 837f17bfdfb912553b2a0a1cada3f2bf90165666). The text is written by the worker from the decisions D-7557 to D-7584 and is the worker's record of the route; the acceptance is the decision agent's; the evidence is same-lineage, not independent.

Task branch task/TASK-167, three commits on the contract commit 7341f932e799b86990857a7156edd311d1392621 (docs/tasks/TASK-167.yaml, sha256 9d55cd8b9ea9897897f030dd4f0da3ab24fac556393f57a07ef3cbfe924f3a4c, base_commit ea82ab3f7d339d205060bc3f0bfb559f343da0ff): 9ff5a35177405f98c7706d816b2fd6e28f84e781, then 5ea607c245bd6448ff78d86c038679fc38a2f7eb (the repair of the first review round, erratum E1), then 837f17bfdfb912553b2a0a1cada3f2bf90165666 (the repair of the second review round, erratum E2). The first two commits are not accepted and are not landed without the third. Risk high; the code part of DEF-0137 task B: the replay of logged decision.acceptance records in decision_replay.py. The contract was not reviewed before its commit (D-7562 C3). Seven paths over the three commits (sha256 of the committed bytes at 837f17bf):
- src/aieos_bootstrap/decision_replay.py (changed) 8a6bc0d91326ca301d9e282551fb1c649d378bacc03dbc4591798f29dab913ec
- src/aieos_bootstrap/eval_inputs.py (changed) 0ae58d28dd7c158311204c51927fc461a521fd57a6ade326b823d02e53249353
- src/aieos_bootstrap/evaluation_sources.py (changed) de0b8d28004390c70c5f3b9f5c62987838f7a9e15af03b753fd2008eca837d3b
- tests/unit/test_decision_replay.py (changed) 050d7cafedaba1ee06a9e02779f55236208851afb65898275daa1ac245b2008b
- tests/unit/test_decision_replay_acceptance.py (new) 20467a12e2101c33d45b2e473e30032b633aae4fc8c5fab13f9b8f2528ecf023
- tests/unit/test_eval_inputs.py (changed) 92fbc5e1a19a82e7e5948ac9d5e5957d4b3360e4b27dc13d81aa57682d2b694f
- tests/unit/test_evaluation_sources.py (changed) 4daafcacea7aae760f408fe50e40e78cca07f53bfc9f3d7d207bf3741a86002f

## The route (decisions)
D-7557, D-7558 (the scope and the contract draft); D-7559, D-7560, D-7561 (the draft amended, the base-test prediction on a clone, one unpredicted failure and the contract amended); D-7562 to D-7565 (the contract commit 7341f932, its branch CI, its landing and the CI of main); D-7565 to D-7570 (the tests, their literals computed apart from the code, the test runs); D-7571 to D-7573 (the first task commit and the first review prompts; D-7572 returned MODIFY); D-7574 (the first review round ruled, my own review of 9ff5a351 NOT PASSED, erratum E1); D-7575 to D-7577 (the repair, its commit, the second review pair); D-7578 (the second round ruled, NOT PASSED, erratum E2); D-7579, D-7580 (the second repair and its commit); D-7581 (the third review); D-7582 (my review of 837f17bf PASSED); D-7583 (the task branch push); D-7584 (the CI read against its shape); D-7586 (this acceptance).

## The CI (branch task/TASK-167, head 837f17bf)
aieos-checks 45967082751 and aieos-native 45967087023, event push, attempt 1, success; 26 and 19 conclusion fields, all success. Read against the shape typed before the push (expected_shape_task_167.txt, sha256 99136851d4b41f597f38b1d6292589e95761ee492a537756e41be637a8e821f2) by the decision agent in the fetched logs (log_45967082751.txt sha256 59bcff4e856e512929080c9302a36d6155f7e1365d6c0cefba4889e8812c467d; log_45967087023.txt sha256 43d29dabbf2d41696ff7b9fd2189605d01e80ad1c08f1ea53e49c11002e393a8): no difference (D-7584): "G0 scope: task TASK-167, commits 3, paths 7, failures 0", unit 3452, integration 234 and property 227 tests OK, deterministic_rule and OPS-003 files 288 with 0 findings, "GOV-003 evaluator lists: 2 found, equal, 40 entries". Same-lineage CI evidence (D-7584 C4): bandit printed "No issues identified." (five invocations) and the pyflakes step printed no finding; they are the only evidence of the two linters, which are not installed locally (D-7570 C5). "GOV-003 base tests: 3866 run, 1 failed", the one failure test_decision_replay.py MainTests.test_arguments, as predicted. The first two task commits have no CI run of their own.

## The local runs
The base suite with the three production files of that time: 3866 run, one failure, test_decision_replay.py MainTests.test_arguments (D-7560, D-7561; observed, not predicted before it). The five touched modules and the whole suite: on the first commit 340 and 3902 (D-7570, D-7571), on the repair 345 and 3907 (D-7576), on the second repair 351 and 3913 tests, 0 failures, 1 skipped (D-7579, D-7580). The first run of the new tests found two faults of the tests themselves (D-7568). The repairs were not preceded by a run of the new tests against the unrepaired sources. The suite ran as 24 slices (unit 12, integration 6, property 6), each under timeout 110, in place of the single run line of the contract, because the whole suite cannot finish inside that limit: a departure approved by those decisions. Each dry and real commit ran the CI's deterministic_rule and OPS-003 blocks locally (0 findings).

## Exit condition (TASK-167.yaml exit_conditions)
- "all gates pass": met on the task branch (G0 scope above; G1 and G2: the CI and the local slices; G3: the CI lines above and this text).
- "an other_model_review and a separate decision_agent_review, both bound to the evaluated commit, the contract and the pins, before any fast-forward of main": met by the third round below, on 837f17bf, with the limit of its coverage stated.
- "the task acceptance by the decision agent before any landing step": met by D-7586.
- "the aieos-checks run of the accepted commit succeeds": met on the branch (run 45967082751); the run of main is owed, after the landing.

## Evidence profile (high) and the reviews
unit_test, integration_test, deterministic_rule and static_security_analysis: met by the CI run and the local slices. The cross-model entry ai_review: three review rounds, same-lineage and not independent. Every reviewer was claude-haiku-5-5 in its own session.

First round, on 9ff5a351, both BLOCK:
- reviewer A: transcript subagents\agent-a5517280a15f2a247.jsonl (sha256 ecbbeb50e02e38b4ce80edb9e24084b294553249143f86fc1ca131174b5d8fab); report review_A_167_9ff5a351_report.txt, sha256 0827bd5a025de34bc677bfdb729564820c9bb1e8d1ac293f0459b9abe16e78b4; approved prompt review_A_167_prompt.txt, sha256 ea93418677320e82694c1c64f4a86445a71af2574ae6c61f8e9e1e6746407727; tools Grep, Read, SubagentHandback; 54 Read, Grep or Glob calls;
- reviewer B: transcript subagents\agent-ad588d9b1c6c1bf84.jsonl (sha256 69a17df4143340c0e79c11cc678c2448731c40b5dafda36b87ae0c0b18d8cb40); report review_B_167_9ff5a351_report.txt, sha256 933ed357856e1deeae4b9aa583219c435db1a5335ecd3b24d7b29624eb8f0f3c; approved prompt review_B_167_prompt.txt, sha256 9bce9db17ecb6ada8251ce479127d40445f7c4f420ff7f35d548921a0c986a39; tools Grep, Read, SubagentHandback; 54 Read, Grep or Glob calls;
- decision_agent_review = D-7574 (record sha256 bd024bbf50278ff2849684f705af35fb8a72828b93a044fb4bbaa4b1a1e4c368), NOT PASSED: B1 upheld (the replay passed a governor error record that aieos evaluate would never write), with text and test findings; A1 not upheld; erratum E1.

Second round, on 5ea607c2, both BLOCK:
- reviewer A: transcript subagents\agent-a25d6c8c9fe7b7b01.jsonl (sha256 095401027a68c5731a4c26e81cca9022d82180daec2b57d127d406c8a114cfb6); report review_A_167_5ea607c2_report.txt, sha256 a7c4256e523890b24ff8a56eaa734fbf45b3175fa1597b7d185fe987d76e2527; approved prompt review_A_167r2_prompt.txt, sha256 91d935663def809244b2b2d94c10b66104f0fe412fbb04d4adda1c7c4c3bb83d; tools Grep, Read, SubagentHandback; 56 Read, Grep or Glob calls;
- reviewer B: transcript subagents\agent-ad5065ea228e7d6f8.jsonl (sha256 14214a6cb3dbdf49787dbbaf0d5a6ec1f1b3a26b0cc0f99f931f786054f63398); report review_B_167_5ea607c2_report.txt, sha256 2b7d4797ce3858d73777546f51d5119656c7f14bffaf004bf9115f1a4a39ef7f; approved prompt review_B_167r2_prompt.txt, sha256 5d100ebbc40adaba4fead035d36dce0c11dc436b46922d6a8abdf561cf09af7e; tools Grep, Read, SubagentHandback; 36 Read, Grep or Glob calls;
- decision_agent_review = D-7578 (record sha256 4b2cd21344bdc6b233a4892ffe9a508a3ade83ea3a29325dc49c6638a121d6fb), NOT PASSED: an ignored duplicate line was counted as passed, and the command's refusals on the contract's form were not repeated, with a false stated reason; the byte form and the final LF were not checked; two false sentences; small repairs and missing tests; erratum E2.

Third round, on 837f17bf, the reviews this acceptance rests on:
- other_model_review: transcript subagents\agent-a0bf806f1def92fc9.jsonl (sha256 9a1ebbe6417974eb9adeae9e081b800e130459697966bfed6004719b02326db1); report review_B_167_837f17bf_report.txt, sha256 f9d1b747a564ec603b30655afe7b976f4802ebfb1cfc578f956dbb1dd479cbed; approved prompt review_B_167r3_prompt.txt, sha256 d3eaef4258b44187a4a5f8aaa8e863686762211fe1b3dcb98c4f1a2c1b559188; tools Grep, Read, SubagentHandback; 35 Read, Grep or Glob calls; verdict APPROVE, no blocking finding, minor findings and notes;
- decision_agent_review = D-7582 (record sha256 8a2bc6d83e8275dce259a42d4fc794f5b0cc1638856fb34ef52f95b6de4df285), PASSED.

The third-round other_model_review (Haiku 5.5) read the second repair and the two files it changes, and did not read the contract file, the whole-range diff or the workflow; it also read parts of the code that the changed files call. The five pinned files unchanged since 5ea607c2 rest on the round-two pair. Both reviews of the third round are bound to the evaluated commit, the contract and the pins by their prompt and request; this reviewer did not review the whole range. The reviewers and the decision agent are Claude models, and the decision agent also decided the earlier steps of this build. Limit of the blindness: the harness put the project's memory index and the git status with recent commit subjects into each reviewer's context.

## Evidence by criterion
AC1 to AC10: MET as amended by errata E1 and E2, as read at D-7574, D-7578 and D-7582 (for the five files unchanged since 5ea607c2, on the round-two pair and D-7578). AC11: met on the task branch (quoted below); main owed. AC13: unchanged paths as listed there (the task changes seven paths, none under .github). AC14: met by the CI run. AC12 and AC15: this text and the records commit.

## The errata (the contract file is unchanged)
Quoted from the record of D-7574:

> ERRATUM E1 TO TASK-167 (decided here; the contract file is unchanged, because its hash is in the log):
> - E1.1, to AC1: eval_inputs.py may also hold one more private function. It contains exactly the lines of eval_inputs :321-333: the held ValueError gives refusal 'incomplete' and any other held exception is raised again; then come the three missing-value checks. eval_inputs calls it at that place, and every answer of eval_inputs, order and texts included, stays the base's.
> - E1.2, to AC6: after _assemble, the replay derives as eval_inputs derives (governor.derive_inputs over eval_inputs' copy of values, with an Exception held). It then calls that function. A refusal becomes the finding "inputs: incomplete: <detail>", and evaluate_task is not called. An acceptance line that holds fencing_token or corrects fails with a finding naming the field.
> - E1.3, to AC5: the sentence applies to the replay of an acceptance line. The execution-line path is unchanged and is stated as such.
> - E1.4, to AC9: add these limits:
>   - the command's refusals that rest on records trusted as logged (ci_evidence, the record-id guard, the reviews file, the manifest, the argument checks) are not repeated (DEF-0137);
>   - appended_at is taken from the line and is not otherwise checked.
> - E1.5, to AC10: "after each failing gate" means the gates of AC5 and of AC4's argument checks. Add these cases:
>   - a line whose values give no risk fails with the incomplete finding;
>   - lines with fencing_token, and with corrects;
>   - sys.modules after the engine gate, after a malformed pin and after two pins;
>   - with the flag, the governor pin given as the only pin does not pass the engine gate;
>   - the NaN case asserts check_log's NaN finding itself;
>   - the rename case shows that the changed paths hold the old path under --no-renames and that the replay passes.

Quoted from the record of D-7578:

> ERRATUM E2 TO TASK-167 (decided here; the contract file is unchanged):
> - E2.1, to AC6 and AC7. Before the recomputation, an acceptance line fails, each case with its own finding:
>   - (a) report.lines[index].duplicate_of is set: "record: line N is an ignored duplicate of line M, which the writer never writes";
>   - (b) lines[index] differs from eventlog._canonical(event).encode('ascii'): "record: line N is not in the form the writer writes";
>   - (c) log_bytes does not end with LF: "log: the log does not end with LF".
> - E2.2, to AC6. After _same_contract and before _assemble, the replay calls:
>   `eval_inputs._argument_error(task_id, commit, policy_ref, contract, sha, loaded['changed_paths'], [], loaded['sources'], [], payload.get('recorder'))`
>   A non-None answer fails with "inputs: argument: <text>". eval_inputs.py is not changed by E2.
> - E2.3, to AC9, amending E1.4.
>   - In the docstring and in LIMITS :171, the parenthesis becomes "(ci_evidence, the record-id guard, the reviews file, the manifest, and the form checks of the CI runs and the log payloads, which the replay passes as empty lists)".
>   - "makes its replay differ" becomes "can make its replay differ (when it changes the recomputed record)".
>   - Add this limit: "the duplicate, byte-form and final-LF checks apply to decision.acceptance lines only; decision.execution lines are compared by value, as before this task (DEF-0137)".
> - E2.4, to E1.3. Replace ", so an entry over a log that holds execution lines has imported it before any acceptance line." with: "; so when an execution line is replayed before an acceptance line, the governor is already imported when that line's governor gate runs, and the gate still checks the governor file and its SHA-256 before the acceptance replay uses it."
> - E2.5, to AC7. check_log, _acceptance_record, the E2.1 checks and _governor_gate run inside the try, so each exception is a finding. The import stays after the gate.
> - E2.6, to AC10, these tests:
>   - a duplicate line fails with (a);
>   - keys reordered, and a space after a colon, each fail with (b);
>   - a log with no final LF fails with (c);
>   - contract risk "Low", and owner_kept_act "yes", each fail with "inputs: argument:";
>   - at entry level, an engine at HEAD whose SHA-256 equals the governor pin, given with no flag: the line is NOT REPLAYED and the governor is not in sys.modules;
>   - at entry level, the engine gate passes, the governor gate fails, and sys.modules is checked;
>   - without_the_governor records every name it removes and, in finally, restores or deletes each one;
>   - test_the_governor_pin_is_not_an_accepted_engine also asserts that the line fails.
>   Existing fixtures may change only to write lines in the writer's form (tightening).

## The limits (AC9, as amended by E1.4 and E2.3)
Quoted verbatim from docs/tasks/TASK-167.yaml (line 381):

> Limits, stated in the docstring and at acceptance: the readers, the evaluation modules and the governor run from the tree under check (GOV-003 is not met by them); after a change of governor.py, or of a reader in a way that changes a result, older records fail closed, with no loader of the old code; the CI and review records in the log are trusted as logged, and nothing reads GitHub or a reviews file again; the record holds no log position, so a line appended between the evaluation's read and its own append makes the replay differ (it fails closed); a record whose evaluated commit the checkout does not hold fails, and which of fetching it, keeping such a record out of main's log, or another course is taken is the decision of the later workflow step; no logged acceptance record of the self-build exists, so no real record has been replayed.

As amended: the command's refusals that are not repeated are ci_evidence, the record-id guard, the reviews file, the manifest and the form checks of the CI runs and the log payloads, which the replay passes as empty lists; a line appended between an evaluation's read and its own append can make its replay differ, when it changes the recomputed record; the duplicate, byte-form and final-LF checks apply to decision.acceptance lines only.

Also stated:
- The recorder the replay gives the evaluation is the payload's recorder key, and the time is the line's appended_at (D-7559 C4 (1)); the finding N1 of DEF-0138 was already true at the base (D-7559 C4 (2)).
- No logged acceptance record of the self-build exists, so no real record has been replayed. The workflow of the CI passes no governor pin, so there a decision.acceptance record fails until its own step.
- The rename test uses a stand-in Git that lists the changed paths as given to it; it does not show Git's own rename behaviour (D-7575 C6).
- The sentence of erratum E2.4 in the docstring is unconditional; the correct reading is "when an execution line reaches its inputs": an execution line that fails the per-record engine checks imports nothing. The gate still runs before the acceptance import (D-7582).
- The docstring of test_an_engine_with_the_governor_pins_hash_and_no_flag_replays_nothing says that the engine gate passes; the test does not show that, because the entry answers the missing flag before the engine gate. It still fails if the engine pin were read as a governor pin (D-7582).

## The CI criterion (AC11)
Quoted verbatim (line 385):

> CI evidence: on the task branch and on main, "GOV-003 evaluator lists: 2 found, equal, 40 entries"; the evaluator-change line as the paths give, written into the pre-registration before each push; on the task branch the base tests run on the change (report only), their predicted failures named before the push: of the whole suite at the base (3866 tests), run with the three production files of this contract (the prediction run of D-7560, observed there, not predicted before it), exactly this one fails: test_decision_replay.py MainTests.test_arguments. The replay line of the CI stays "replay: event logs 1, decision records: 10, replayed and passed: 8, failed: 0, not replayed (violation path): 2".

Measured on the branch: "GOV-003 evaluator lists: 2 found, equal, 40 entries"; "GOV-003 evaluator change: yes (7 of 7 changed paths)"; base tests 3866 run, 1 failed, test_decision_replay.py MainTests.test_arguments; "replay: event logs 1, decision records: 10, replayed and passed: 8, failed: 0, not replayed (violation path): 2".

## GOV-003
The task changes seven evaluator paths (src/** and tests/**), so GOV-003 is not claimed to hold. Handled as a stated departure with two controls (DEF-0107 point 4): (i) the base tests on the change (D-7560 and the CI step: the one predicted failure, a pinned usage line that the contract changes), and (ii) reviews of the change, the test diff included, by a different model (claude-haiku-5-5, three rounds). The task work was done by claude-sonnet-5-5 (the worker's statement of its model; not read by script); claude-haiku-5-5 differs from it. The general policy stays open (DEF-0110).

## Exit review of the deferred items (master plan section 6, points (3), (5) (c) and (6))
Touch list, quoted verbatim from AC12 (line 387):

> Touch list (master plan section 6 point (6) (b)): DEF-0137 (the code part done here; the workflow step and the unreachable-commit choice stay); DEF-0138 (items 1, 2, 5, 6 by AC8, item 9 by this task; items 3 and 8 closed before; item 4 concerns review briefs and item 7 is a stated limit: judged at acceptance whether it closes); DEF-0144 (items 1, 2, 3, 11, 16 by AC8; items 4, 12, 13, 15 stated why not); DEF-0152 (F5, the repeated record id and NaN shown by AC10's tests; the rest not touched); DEF-0154 and DEF-0156 (they name eval_inputs.py or evaluation_sources.py; neither is changed by this task, said at acceptance). By script at base_commit: DEF-0137 (names decision_replay.py); DEF-0138 (names decision_replay.py); DEF-0144 (names decision_replay.py); DEF-0152 (names eval_inputs.py, evaluation_sources.py); DEF-0154 (names eval_inputs.py, evaluation_sources.py); DEF-0156 (names eval_inputs.py, evaluation_sources.py).

State of each, as the records commit is to write it:
- DEF-0137: stays open, narrowed. Done here: the code part of task B. Open: the workflow step that gives the entry the governor pin (its own A66 decision) and the choice for a record whose evaluated commit the checkout does not hold. Added (dated entry): the command's refusals that are not repeated, so a line such a refusal would have stopped passes the replay (D-7574 C6); decision.execution lines are not checked for duplicate, byte form or final LF, so such a line can count as replayed and passed (D-7578 C5); earlier lines of every non-acceptance type are read by value, unchecked for duplicates or byte form; the acceptance replay runs the readers and the evaluation modules from the tree under check, so a change to them can change what passes (GOV-003, carried by DEF-0110); the E2.4 sentence and the docstring of the test named above are to be corrected at the workflow-step task (D-7582 C3). Resume when: the workflow-step task of DEF-0137.
- DEF-0138: stays open. Done by AC8: items 1, 5 and 6, and item 2, which was already true at the base (D-7559 C4 (2)) and is listed in AC8 (read by reviewer A of the second round on bytes whose docstring steps the third commit did not change in those places). Item 9: task B's replay of acceptance records is done in code (the violation record is recognised since TASK-141); items 3 and 8 were closed before. Not done: item 4 (a brief of a later review of this module naming TASK-139's errata E1.1 to E1.7: the briefs of this task named this task's own errata) and item 7 (a stated limit).
- DEF-0144: stays open. Done by AC8: items 1, 2, 3, 11 and 16 (read by reviewer A of the second round, on lines the third commit did not change; test_decision_replay.py is not touched by it). Not done: item 4 (needs a Resume Check fixture, a later task); item 12 (a bounded scan, unchanged); item 13 (a test of source text, unchanged); item 15 (AC1 (h) through the entry, not added); item 5 belongs to the next A66 revision of the workflow; items 6 to 10, 14 and 17 are record notes of TASK-141.
- DEF-0152: stays open. A dated line: AC10's tests show the old side of a rename among the changed paths given to the evaluation (the log's (F5); with the stand-in Git of D-7575 C6), the repeated record id left out as the evaluation leaves it, and a NaN line refused by the log check, each for the replay path only. D-7574 C7 said the file's labels do not include "F5"; the log holds "(F5)" at its TASK-151 line and in the line of 2026-11-27, so the records line uses that label and says so.
- DEF-0154: not done here: no change of the pinned lists or of EVIDENCE_DEFINING_PATHS. Schedule unchanged.
- DEF-0156: not done here: no real evaluation was run; the producer of intent_versions is unchanged. Schedule unchanged.

### Accepted limits (point (6) (a)), each Blocks v0.1: no
- L1: appended_at is taken from the line and not otherwise checked (D-7574 C6). Why not blocking: it decides no result.
- L2: a line whose appended_at has fractional seconds fails closed (D-7574 C6). Why not blocking: the writer writes whole seconds, and the failure is closed.
- L3: the gate checks the governor's source file and not a stale ignored bytecode file beside it (D-7578). Why not blocking: the A66 step runs in a fresh checkout, where no bytecode exists.
- L4: the limits of AC9 as quoted and amended above that no deferred item carries: older records fail closed after a change of the governor or of a reader; the CI and review records in the log are trusted as logged; a line appended during an evaluation can make its replay differ. Why not blocking: each fails closed or is the stated trust of the log; the workflow step that would rely on them is its own decision.
- Not an accepted limit: the acceptance replay runs the readers and the evaluation modules from the tree under check (the governor is checked against the pin), so a change to them can change what passes (the module's LIMITS; D-6332). It is the GOV-003 departure above, carried by DEF-0110, and the dated DEF-0137 entry names it (D-7585).

### Counts (point (6) (d))
At the contract commit: 100 open, resumed or waiting-owner items, 14 of them 'Blocks v0.1: yes'. This task: opened 0, closed as done 0, dropped 0; open after it 100, of them 14 'Blocks v0.1: yes'; entries added to open items 4 (a dated entry on each of DEF-0137, DEF-0138, DEF-0144 and DEF-0152); accepted limits 4 (L1 to L4). TASK-167 is the fourth task of batch 1, so no count comparison is due (it is due at the fifth acceptance). The records commit recomputes these by script and stops if they differ.

## Route slips (recorded)
Worker: doubled backslashes in a scratch production file, found by the decision agent (D-7559); one test failure not predicted before the prediction run (D-7561); two faults in the first version of the new tests (D-7568); a save script that would have refused a read of the contract (D-7572); after D-7579, one command that held a Python call in a form the owner's rule forbids, refused by the command guard, not repeated, and brought to the decision agent (D-7580). Decision agent: a condition that asked for a Python flag the owner's rule forbids (D-7565 C2, amended by D-7566); erratum E2.4's sentence was imprecise (D-7582); D-7574 C7's statement about the labels of DEF-0152 does not hold (its log :30 and :53, read by the decision agent at D-7585); it came from reviewer A's first-round report, taken unchecked.

## Evidence kept
The clones c167p, c167cdry, c167creal, c167cb, c167ff, c167t, c167t2, c167s, c167tdry, c167treal, c167t3, c167s2, c167r2dry, c167r2real, c167t4, c167s3, c167r3dry, c167r3real and c167bt and the head-run folders and files in the session scratchpad stay until a later decision.

## Not done
Landing the three task commits on main, the main CI and the records commit (the entries above and the history page) follow by their own decisions. The A66 step that gives the INV-010 step the governor pin follows; a second real run is made only on the owner's word.

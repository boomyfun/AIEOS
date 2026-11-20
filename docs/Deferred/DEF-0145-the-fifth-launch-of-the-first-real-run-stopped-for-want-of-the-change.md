# DEF-0145: the fifth launch of the first real run stopped for want of the change: the Work Order of a task carries no text of the intent that the task refers to

- Status: open
- Opened: 2026-11-19 (the History page of the session 26136a0a names the session)
- Deferred by: decision agent (A41, A51), D-6441 (the finding and the fix (a) for the next task version); the choice of the general remedy is a later decision
- Decision group: A (scheduling) for the record; any further session is the owner's (the "Có" at the main transcript :24777 covers one sixth session; it is recorded in the pre-launch statement of that launch)
- Blocks v0.1: no (it blocks the first real run's session)
- Scheduled in: fix (a) in the contract TASK-142 v3 (the objective and AC1 state the change); the src intent layer is not scheduled

## What
The fifth launch (the owner's "Có" at :24380; the release D-6440; the scripts launch6; main d3215a5d, TASK-142 contract v2 with a one-file read set) ran on 2026-11-19 from 11:00:14 to 11:00:26 (local time). Its transcript (path only): C:\Users\Admin\.claude\projects\E--AIEOS\c42c6649-68d1-4059-bea2-95430749c51b.jsonl (sha256 8837b6ebb87dfae2a594cacd5e1516c5bce993bf0b7bb528e4bb4c723194fbcb). In short form: the starter's prompt; a ToolSearch of "select:mcp__aieos__get_work_order" (the narrow rule of TASK-140 passed the hook); mcp__aieos__get_work_order, whose result came back INLINE with 32,239 characters (not saved to a file: the one-file read set of TASK-142 worked, route C of D-6424); then the session's final text: "I stopped without changing anything. The Work Order for TASK-142 says to make the change that intent INT-002 states, but it never says what that change is." It made no Read, no Bash, no Edit, no status call: two tool calls. The launcher's summary: run returned, end done, handoff none, "root after: clean", exit 0. No violation; no tracked file changed; two lines were appended to .aieos/events.jsonl (30: the start's decision.execution CONTINUE; 31: the observed read set with read_paths []).

## The cause (measured, then read in the code)
1. The Work Order of TASK-142 (inspect_wo.py over the tool result in the transcript; launch6/inspect_wo_out.txt) holds the keys base, contract, contract_hash, contract_version, decision, layers, session_id, task, work_order_hash; the layers: constitution 23 items, components 0, traced 2 items (AC1 and AC2), files 1 item (the DEF-0095 file), handoff 0. The string "INT-002" occurs three times, all in the contract (the objective and the criteria name the intent by its id); "FIRST ACTS", "RULES OF THIS SESSION" and "TodoWrite" occur 0 times.
2. The compiler has no channel for an intent record: base_inputs.py :28 and :571-578 read, for the traced layer, "each traces_to entry's file read whole" (the contract's traces_to was empty), and neither base_inputs.py nor context_compiler.py mentions an intent. The contract that `aieos run` fills says only "Make the change that intent INT-002 states, within the write set" (launcher.py :1823-1825). So the text of an intent is never given to a session.
3. The consequence reaches back: the FIRST ACTS and the RULES OF THIS SESSION of INT-002 (a TodoWrite hook test, "no shell call") never reached any of the launched sessions; DEF-0143's cause 4 (a session that tried the shell) was due to that, and its first version wrongly said that the Work Order held them.

## The fix (a) and the options
(a) THE CONTRACT: state the change itself in the contract's objective and AC1 (TASK-142 v3, contract_version v3: on line 7 of DEF-0095, the citation "master-plan.md :116" becomes "master-plan.md :117", no other byte, the same citation in the Log unchanged; the intent INT-002 named by id in a parenthesis). Measured in a scratch clone: the Work Order of v3 is 32,756 characters and holds the objective and AC1 text. No code change.
(b) a docs file that holds the change text, listed in traces_to (the traced layer reads it whole): a new file and a class of its own; the same effect.
(c) THE GENERAL REMEDY: an "intent" layer of the Work Order, fed from the log's intent records of the task's referenced intents (base_inputs.py and context_compiler.py: a src task of class high, GOV-003); not scheduled; it would also let the FIRST ACTS and RULES reach a session.
Also: the contract's base_commit (861b64b1) differs from the Work Order's "base" (d3215a5d), which the session noted as a possible mismatch; it is the contract's input state at its drafting; carried.

## Limits and not measured
Whether the model does the change when the objective states it; whether a session reads master-plan.md to verify (outside the read set); the effect of an intent id in a parenthesis; the margin of the Work Order against the documentation's 50,000-character rule (a citation; the 32,239 characters were shown inline at the fifth launch).

## Resume when
After the sixth session is read (it measures whether the stated change suffices); the src intent layer when the first real run is closed.

## Depends on
DEF-0140, DEF-0142, DEF-0143 (cause 4 corrected by this record), DEF-0144; the contracts TASK-142 v2 and v3; the decisions D-6438 to D-6441; TASK-141 and TASK-140.

## Notes on sources

File names written aj/... or S1\aj\... in this record are kept in the lasting copies under C:\Users\Admin\AIEOS-REG0-lite\sessions\26136a0a-b135-4cb1-9db0-95258ca6f5b5\scratchpad-evidence (the folder stretch-D6445-D6469 and the folders TASK-140, TASK-140-ci, TASK-141 and TASK-141-ci) or under C:\Users\Admin\AIEOS-REG0-lite\sessions\c0dc5bcc-c58f-46fa-a52d-d27469300fc7\scratchpad-evidence\def-sources (aj/launch5b, aj/launch5c, aj/ao8_compile.py, aj/ao8_out.txt, aj/make_drafts.py); the prefix aj/ names the old scratch folder, which no longer exists.

Figures in this record that no decision file carries and that no script re-checked against a lasting copy (run times, byte counts, tool-call counts) are the worker's measurements and are not re-verified.

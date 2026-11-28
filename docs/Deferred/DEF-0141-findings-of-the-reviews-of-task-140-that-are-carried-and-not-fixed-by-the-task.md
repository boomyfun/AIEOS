# DEF-0141: findings of the reviews of TASK-140 that are carried and not fixed by the task

- Status: done
- Opened: 2026-11-19 (the History page of the session 26136a0a names the session)
- Deferred by: decision agent (A41, A51), D-6406 (the dispositions of the findings of the reviews B2 and A3 of TASK-140; A2 is void and its findings are information only) and D-6407 (the acceptance of TASK-140 with these items carried)
- Decision group: A (scheduling)
- Blocks v0.1: no
- Scheduled in: the next change to src/aieos_bootstrap/claude_code.py (the test cases), and the records of TASK-140 (the wording items)

## What
The reviews of the two commits of TASK-140 (6811ffb9 and 8e2a5b5f on task/TASK-140; the valid pair is reviewer B2, agent ac6fdc9e86b037ce0, and reviewer A3, agent a938c6ad7e5446fb2; the first pair A1 and B1 and reviewer A2, agent a3905006815b1f096, are void for breaches of the path rule and their findings are information only) found no defect in the code. These items are carried; each has the decision agent's disposition (D-6406), which is the worker's reading of it until the DEF is approved.

1. TEST GAP (B2 finding 3; real, no code effect today): no test passes a name with an added suffix or prefix, or a CR, as an element of the "select:" list; the code uses exact membership of MCP_TOOLS (claude_code.py :354), so it is correct today; the cases guard only against a future regression. Disposition: add the suffix, prefix and CR cases with the next change to claude_code.py (no third commit now: it would void both reviews).
2. SEC-002 and the trailer (B2 finding 2; DEF-0139 item 8): the commit messages end with the harness's no-reply Co-Authored-By form; the literal reading of SEC-002 on e-mail forms is the decision agent's reading, concept-governed. Carried with the identity forms in the evidence outputs (B2 finding 14).
3. THE PIN AGAINST THE FILE (B2 finding 5): no unit test checks the typed SETTINGS_SHA256 against the settings file; the check is the starter's live hash check at launch and the gate of the settings-write step (and the CI pins). Carried.
4. THE STARTER FAILS CLOSED UNTIL THE FILE IS WRITTEN (B2 finding 6, A2 note): the live settings file (hash bb9c8724...) is refused by the new starter until the new file (242533e1...) is written; this is the contract's order; to be stated at acceptance.
5. COMMIT MESSAGES (B2 finding 7): the messages omit AC4 limits 1 and 6 and the GOV-003 departure; these are carried by the acceptance and the records, as for TASK-138.
6. WORDING ERRORS (A2 finding 1 and B2 finding 8, B2 finding 10): message_1.txt says the checks ran "at 0f0357b6" while the evidence is at 7d86a264 (the five files are identical at both); the contract's line 59 says "the nine judged ones" where the judge names fourteen. No code effect.
7. A DOCSTRING CLAIM (B2 finding 9): the docstring's statement about the tool's own definition is an assumption; the docstring calls the shape of tool_input "unmeasured". A wording note.
8. THE STALE DOCSTRING of claude_code_hook.py :28-29 (finding 5 of the void first review, outside the write set): it lists the judged tools without ToolSearch and without the MCP names. Carried to the next change of that module.
9. A3 NOTE 2: the "869 bytes" of the draft settings file in message_1 is not measurable from the review folder (the draft file is not in it; the size comes from the contract and from a command run by the worker); the sha256 is in evidence/settings_draft_sha256.txt. Carried as a record note.
10. A3 NOTE 6: evidence/modules_out.txt lists three test groups (unit, integration, property; 175 modules); whether another group exists is not shown in it (the CI counts equal the slice totals 2744, 229 and 226). Carried as a record note.
11. ARTICLES "cannot be judged from SP" (B2): INV-003, GOV-003, SEC-002 and OPS-002; stated at acceptance, as for TASK-138.

## Why deferred
None of the items is a defect of the behaviour of the change; the first two are guards against a future regression and the rest are wording and record items. A third commit would void both repeated reviews.

## Resume when
With the next change to claude_code.py or claude_code_hook.py; the wording items with the records commit of TASK-140.

## Depends on
The contract TASK-140; the decisions D-6401 to D-6406; DEF-0139 (item 8 of the trailer); DEF-0140.

## Notes on sources

File names written aj/... or S1\aj\... in this record are kept in the lasting copies under C:\Users\Admin\AIEOS-REG0-lite\sessions\26136a0a-b135-4cb1-9db0-95258ca6f5b5\scratchpad-evidence (the folder stretch-D6445-D6469 and the folders TASK-140, TASK-140-ci, TASK-141 and TASK-141-ci) or under C:\Users\Admin\AIEOS-REG0-lite\sessions\c0dc5bcc-c58f-46fa-a52d-d27469300fc7\scratchpad-evidence\def-sources (aj/launch5b, aj/launch5c, aj/ao8_compile.py, aj/ao8_out.txt, aj/make_drafts.py); the prefix aj/ names the old scratch folder, which no longer exists.

Figures in this record that no decision file carries and that no script re-checked against a lasting copy (run times, byte counts, tool-call counts) are the worker's measurements and are not re-verified.

## Log
- 2026-11-28 (session 228f426b; TASK-171, accepted at D-7727, commit a2c808305d3f28df413e2771bfc247b4d3559a5a, docs/runs/TASK-171-acceptance.md; main CI runs 46058827716 and 46058827710 success): the Resume-when event is met: TASK-171 was the scheduled next change to src/aieos_bootstrap/claude_code.py; it changed only the module docstring, and the "select:" test cases of item 1 were not in its contract. The item stays open and its test cases stay scheduled with the next change to claude_code.py or claude_code_hook.py. Status unchanged.
- 2026-11-28 (session 228f426b; TASK-174, accepted at D-7863, commit d80af249da95634cdf70a1e9218c8dfb51eb3488, docs/runs/TASK-174-acceptance.md; main CI runs 46130608472 and 46130608475 success): closed, done, item by item. Item 1: tests/unit/test_claude_code.py:486. Item 8: src/aieos_bootstrap/claude_code_hook.py:28-:31 (a limit of its wording is accepted limit L6 of that acceptance). Item 6: erratum (d) for docs/tasks/TASK-140.yaml:59 and a record note for message_1.txt. Item 3: accepted limit L1. Item 2: carried by DEF-0139 item 8, open. Items 4, 5, 7, 9, 10 and 11: record notes of that acceptance.

# DEF-0091: the findings and limits carried from TASK-071

- Status: open
- Opened: 2026-10-22 (session e309084b; decisions D-1646, D-1664, D-1665, D-1667, D-1670 and D-1675)
- Deferred by: decision agent (A41, A51), D-1675, at TASK-071's acceptance, with the points ruled by decisions D-1646 C6, D-1664 C1, D-1665 C3, D-1667 and D-1670 C4.
- Decision group: A (a text and test change of src/aieos_bootstrap/task_contract.py, src/aieos_bootstrap/session_violation.py and their tests, in a task of its own, or H2b's contract where named).

## What
TASK-071 (H2a: the task contract reader and the hardening of session_violation carried from TASK-070) was accepted at its head 42a56f51 (D-1675; change class critical_cr, ruled at that acceptance, which is its one approval, governor row 5, L1, not auto-accepted), with these points carried, each non-blocking:
- **GOV-003's review part, an obligation of H2b:** the review of whether the pinned evaluator list covers every input A29 names was not done for TASK-071 (t71r-R5 did not review it; D-1670 C4). H2b's contract must include that review, before or when H2b makes task_contract.py an input of evaluation.
- **R4-4 (D-1646 C6):** fields of adapter.violation's answer are read twice, so a dict subclass with unstable reads is admitted by the isinstance design (production passes no lookup).
- **R4-5 (D-1646 C6):** released's other keys are copied unchecked.
- **R1-3/R4-6 (D-1646 C6):** the "no exception escapes" guarantee covers read_contract; parse_contract has no path that raises on str.
- **R3-11 (D-1646 C6):** the property test's mutation lists are a subset of AC3's.
- **AC8's "é" (D-1646 C6):** the example "(so 'é' refuses)" is a wording error of the contract; the "€" test is the proof.
- **t71s-R1 (D-1664 C1):** a test line over 120 characters (test_task_contract.py:159); no broken copies for R3-1 (a file as root), R3-4 (the rule lines) or R3-10 (an extra result key).
- **t71s-R2-1 (D-1664 C1):** the order test's docstring says "each adjacent pair" while two pairs are not in it, and no copy swaps "repeated vs missing" (a docstring overclaim to correct in a later task).
- **t71s-R2-2 (D-1664 C1):** only the repeated-name leak has a broken copy.
- **t71s-R2-3 (D-1664 C1):** test_more_parse_cases names AC3 but sits in class AC2NamesAndOrder.
- **t71s-R2-4 (D-1664 C1):** the line-id test compares pattern text, not behaviour.
- **t71s-R2-5 (D-1664 C1):** no broken copy for the extra-key shape check.
- **t71s-R2-6 (D-1664 C1):** the property test's "unreadable implies four None" branch is dead after the added assert and its docstring still claims it (a docstring overclaim to correct in a later task; covered by the single builder _unreadable, task_contract.py:72-74, and the unit tests at :117 and :324).
- **t71s-R2-7 (D-1664 C1):** the AST name check covers module-level names only (as ruled).
- **t71s-R2-8 (D-1664 C1):** a loop variable "_" is now used.
- **t71s-R2-9 (D-1664 C1):** the RULE_LINES copies are not mutated.
- **The contract layout read in three places (D-1665 C3):** G0, resume_check._check_contract and task_contract, copied not shared; native takeover (A11) takes them over as one capability, with conformance comparing G0's and task_contract's acceptance.
- **The run seam (D-1667 point (i)):** read_contract's run is injectable; H2b's caller must pass none (beside TASK-070's DA-3 (i)).
- **Round t71u's note:** the fake author lines "A <a> 1 +0000" in two tests are placeholders, not addresses.
- **The five unit failures (D-1667 point (ii), D-1660, D-1670):** test_runner.py (3) and test_runner_rc.py (2) failed in the local scratch clone; local cause unknown; CI run 39736522243 shows them passing.

## Resume when
- With H2b's contract (GOV-003's review part and the run seam), the next text change of task_contract.py or session_violation.py or their tests, native takeover of the contract reading, or the owner's word.

## Log
- 2026-10-22: opened (session e309084b; D-1675).

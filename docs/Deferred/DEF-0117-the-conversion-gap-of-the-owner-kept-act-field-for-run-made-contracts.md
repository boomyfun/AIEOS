# DEF-0117: the conversion gap of the owner_kept_act field for run-made contracts, and the run-side refusal by path (AC6 of TASK-115, D-4596 C4)

- Status: open
- Opened: 2026-11-02 (session 08342c65; TASK-115, decisions D-4596 C4 and D-4643)
- Deferred by: decision agent (A41, A51), D-4596 and D-4647
- Decision group: A (self-build)
- Blocks v0.1: yes (the governor's evaluation of a run-made contract stays owner-routed only through this gap, which is not a control, DEF-0117:9; the first real run goes through launch and the governor, master-plan.md :116)
- Scheduled in: M8, the run-made contract conversion task (owner_kept_act and the paths the run refuses), before the first real run

## What
First gap, the conversion gap (TASK-115.yaml r7 :4 and AC3 :70; t115/survey.md section 7): base_inputs._parse_contract_text yields plain text, so a run-made contract's owner_kept_act reads as the text false or true; governor.py:586 (kept = contract['owner_kept_act'] is not False) needs the boolean False; and no code in src/ builds the governor's contract mapping from a contract file's text. The governor's evaluation of a run-made contract therefore stays owner-routed, but only through this gap, which is not a control and is not counted as one. Since TASK-115, approval_act's effective refusal is loosened for run-made contracts: with `--class decision_agent --owner-kept-act false` a decision_agent approval is accepted and makes the task READY (spec 7 :32, spec 1 :65), after which a lease may be granted (spec 1 :78). A task that closes the gap makes the caller's statement reach the governor as well, and must decide that on purpose.

Second gap (D-4596 C4): the run-side refusal covers only the two path-rule routes (`.github/` and the measurement protocol, since X3 also the measurements folder). Other acts that stay the owner's, such as concept errata and CR-002 part 4 limits 5 and 8 outside those paths, rest on the approver and not on code. See the Finding-A DEF for the paths the guard does not refuse.

## Resume when
The first docs-only low-class `aieos run` has been done (D-4509 C3) and its result read, or a task changes approval_act or `_run_statement_findings`.

## Follow-ups owed
- A task that decides, by act and not by path, which statements a run may make for the caller.

## Depends on
TASK-115; the Finding-A DEF.

## Log
- 2026-11-02: opened (session 08342c65), at the acceptance of TASK-115.
- 2026-11-03 (session 08342c65): TASK-116 is the first low-risk task, a docs-only change made from a contract `aieos run` wrote (decisions D-4674 and D-4677); its result was read; it was not accepted at its task commit T b202e609 (D-4685: functional lint has no producer, DEF-0118), so the governor's evaluation of a run-made contract at acceptance was not exercised; this item stays open.
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass E decision D-5258 (K3)): read in full; the Resume-when event (the first docs-only low-class aieos run done and its result read) occurred: TASK-116 was that run and its result was read (Log 2026-11-03); the governor's evaluation of a run-made contract at acceptance was not exercised; the task decides it on purpose. State: open; Blocks v0.1: yes (the governor's evaluation of a run-made contract stays owner-routed only through this gap, which is not a control, DEF-0117:9; the first real run goes through launch and the governor, master-plan.md :116); Scheduled in: M8, the run-made contract conversion task (owner_kept_act and the paths the run refuses), before the first real run.

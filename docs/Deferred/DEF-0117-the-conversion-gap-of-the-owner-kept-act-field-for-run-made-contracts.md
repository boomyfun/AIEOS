# DEF-0117: the conversion gap of the owner_kept_act field for run-made contracts, and the run-side refusal by path (AC6 of TASK-115, D-4596 C4)

- Status: open
- Opened: 2026-11-02 (session 08342c65; TASK-115, decisions D-4596 C4 and D-4643)
- Deferred by: decision agent (A41, A51), D-4596 and D-4647
- Decision group: A (self-build)
- Blocks v0.1: yes (the governor's evaluation of a run-made contract stays owner-routed only through this gap, which is not a control, DEF-0117:9; the first real run goes through launch and the governor, master-plan.md :116)
- Scheduled in: after the first real run: the second gap (statements by act and not by path); the conversion gap was met by TASK-128 (decision D-6227); before the M8 exit review

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
- 2026-11-12 (session 7d0b3852-d124-4653-b026-25d167d6f9c4; TASK-128 records, acceptance decisions D-5647 and D-5673): TASK-128 landed Part B, the first gap: the governor's owner_kept_act input is bound to the approved contract bytes in evaluate_task (evaluation.py:486-519, :555): the governor sees False only when the bytes hold exactly one line owner_kept_act: false at column 0, no other key line and the line after it absent, blank or not indented; otherwise True, on a copy, with no new refusal; two limits are named: the statement 'no approved contract carries the other forms' rests on the assumption that only bytes that passed the project reader get approved, which this module does not enforce (deviation A(e) of the acceptance), and evaluation.py carries a textual mirror of part of the contract reader (base_inputs._parse_contract_text) that must follow any later change of that reader; status: stays open for the second gap (statements by act and not by path), which stays with the approver.
- 2026-11-14 (session 86f64e95-6029-4e67-8582-7d92a441a275; decision D-6227, the gate check of the first real run): the first gap (the conversion) is met by TASK-128 (Log 2026-11-12, with its two named limits). The second gap (which statements a run may make for the caller, by act and not by path) moves to after the first real run; it stays with the approver. Condition of that move: the pre-run record states that the run's contract write set and acts include no owner-kept act and no path in .github/, the measurement protocol, the measurements folder, the concept, CR-002, the decision matrix's sections A and P, the decision agent's definition or any setting; the decision agent checks this when it rules on the pre-run record. Status stays open; Blocks v0.1 stays yes.

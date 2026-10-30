# L-0037: Read the contract's budget and the checker's rule for each record type before the work starts

Rule: At the start of a task, read the contract's own autonomy budgets and exit conditions, and read the governor's and the records checker's rule for each evidence type that the contract's profile and articles need; do this before the work and the records are planned, not at the acceptance draft.

- Status: active
- Category: process
- Binding: record only. Related: decisions D-3636, D-3696, D-3704, D-3706; L-0034 (check a contract's record forms against the checker's rules).

## Pattern
The contract of TASK-102 states its own budgets (tokens 1500k, wall time 8 h) and an escalation on budget_exhausted. The session worked to other limits and noticed the contract's figures only when the acceptance text was drafted, 8 h after the contract commit; D-3636 had extended the budget, and the extension had to be quoted. In the same way, the governor satisfies an ai_review entry only by a way-2 record whose reviewer's model differs from the implementer's; that rule was read from the governor's code after three dry runs of the records script, when a failed article review could no longer be turned into a pass and had to be recorded as it was.

## Occurrences
- **2026-10-30 (session 1c1bf794, D-3696 ruling 1).** The contract's wall budget of 8 h and the escalation on budget_exhausted were found at the acceptance draft; D-3636's extension covered them.
- **2026-10-30 (session 1c1bf794, D-3704, D-3706).** A decision_agent_review standing for ai_review does not satisfy an ai_review entry (governor.py :270-319); the GOV-003 entry stayed unsatisfied, and the failed way-2 record gave NEEDS_REWORK at row 2.

## Why it happens
The budget and the checkers' rules are in files that the work does not touch, and the session's own limits (its token and time counts) stand in for them.

## Prevention and detection
- At the first step of a task, print the contract's budgets and exit conditions and the profile's evidence types, and read the governor's rule for each type.
- Run the records script's dry run, with the shadow, at the contract's approval and again after the reviews, not only at the end (AC9).

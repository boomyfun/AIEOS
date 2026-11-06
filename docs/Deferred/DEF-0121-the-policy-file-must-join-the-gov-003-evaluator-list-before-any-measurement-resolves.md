# DEF-0121: .aieos/project.yaml must join the GOV-003 evaluator list before any measurement of the runtime resolves through the core (found at TASK-117, K3)

- Status: open
- Opened: 2026-11-05 (session a0a0bdef-5258-47a7-94c1-6ba559edca43; TASK-117)
- Deferred by: decision agent (A41, A51), D-4776
- Decision group: A (self-build); the change itself is under DM A66
- Blocks v0.1: no (no reading above low is allowed and no measurement resolves through the core)
- Scheduled in: none

## What
After TASK-117 the Resume Check's runtime.max_risk comes from the declaration in .aieos/project.yaml at the base. The file is not on the pinned EVALUATOR list of the workflow (aieos-checks.yml:481-491). The contract settled K3 for this task: the file does NOT join the list now, because INV-004's path rule refuses any task commit that touches .aieos/ (aieos-checks.yml:1744-1747) and, while spec-02 section 10 point 12 is open, no reading exceeds low (spec-02:247 and :248 at X3), so an unnoticed change of the file cannot raise a tier above low. Before any measurement resolves through the core, a change to the file must be reported like any other evaluator change.

## Resume when
Before any `measurement` value is made to resolve through the core, or before any reading above low is allowed.

## Follow-ups owed
- A change to the workflow's evaluator list (a change under .github/, critical, its own decision under DM A66 with an exact diff, pins and the pair of reviews). Not part of TASK-117's acceptance.

## Depends on
TASK-117 (AC7, K3); spec-02 section 10 point 12 (the owner's); DEF-0101.

## Log
- 2026-11-05: opened at the acceptance of TASK-117.
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass E decision D-5258): read in full; the Resume-when event (before any measurement value resolves through the core, or any reading above low is allowed) is not met; the change would be under .github/ and its own A66 decision. State: open; Blocks v0.1: no (no reading above low is allowed and no measurement resolves through the core); Scheduled in: none.

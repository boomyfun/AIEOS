# DEF-0111: the lists-equal step runs inside the workflow it checks

- Status: open
- Opened: 2026-10-30 (session 9dbe9c67; TASK-103's acceptance, decisions D-3826 and D-3830)
- Deferred by: decision agent (A41, A51), the acceptance decision of TASK-103 (D-3830; finding 3 of the way-2 review R3w)
- Decision group: A

## What
The step "GOV-003 evaluator lists equal" in .github/workflows/aieos-checks.yml reads the checkout's own copy of the workflow, in the same job and after steps that run the pushed code, and it passes when both copies are empty lists. It guards against accidental drift between the two EVALUATOR copies, not against a change that wants to defeat it, which could edit the step or the file. Header line 3 of the workflow ("writes nothing to the repository") does not mention the runner-side worktree of the report-only step.

## Why deferred
The gap is the one DEF-0107 point 5 states for the governor (a changed evaluator judges itself); a hardening (run the check before any step that executes pushed code, or read the committed blob of the base, refuse empty lists, fix the header sentence) is a workflow change, which is its own A66 decision and its own task, and it cannot close the larger gap.

## Resume when
The next change of the workflow's EVALUATOR lists or of the lists-equal step, or the decision to close the gap of DEF-0107 point 5.

## Depends on
DEF-0107, DEF-0109.

## Log
- 2026-10-30: opened at TASK-103's acceptance (D-3830).

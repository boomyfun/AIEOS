# DEF-0154: the evaluator inputs that are in neither the pinned lists nor EVIDENCE_DEFINING_PATHS

- Status: open
- Opened: 2026-11-21 (session 0be70981; D-6986 F4 and C3, D-6996)
- Deferred by: decision agent (A41, A51), D-6996
- Decision group: A for adding paths, each by its own task and its own A66 decision; a reading that leaves any of these inputs outside the evaluator of DM A29 goes to the owner (the rule in DEF-0109's log, 2026-10-30, D-3740)
- Blocks v0.1: no (proposed: the CI step reports and passes and the governor does not read the list, docs/runs/TASK-156-acceptance.md Limits (a); INV-011 bars auto-accept while C13 is not PASS)
- Scheduled in: M8, with or before the BT3b-2 evidence comparison (proposed: the comparison reads EVIDENCE_DEFINING_PATHS, so an input outside it is invisible to it)

## What
After TASK-156 (docs/runs/TASK-156-acceptance.md, Limits (c)), these inputs are in neither the EVALUATOR lists of .github/workflows/aieos-checks.yml nor EVIDENCE_DEFINING_PATHS (src/aieos_bootstrap/evaluation_policy.py): .aieos/project.yaml (its shell_allow is read by the guard claude_code_shell_allow); src/aieos_runtime/** (task_capture.py, claude_starter.py); AIEOS-concept.md (covered by GOV-001's hash rule instead); measurement-protocol.md and the measurements folder (covered by OPS-002's owner paths instead). Whether the first two are evaluator inputs is the open review part of GOV-003 ("whether the pinned list covers every input A29 names"); TASK-156 did not close it and it must not be claimed closed. Not decided here: whether the other two need an entry or are covered by their own rule.

## Why deferred
E7 (TASK-156) was narrowed to the four entries that EVIDENCE_DEFINING_PATHS names and the lists did not match (D-6888 C4, D-6967); widening it would be scope creep and each input needs its own reading of A29.

## Resume when
The next change of the EVALUATOR lists or of EVIDENCE_DEFINING_PATHS, or the BT3b-2 contract, whichever comes first.

## Related
DEF-0109 (done; the like gap for the native and bench files), DEF-0110, DEF-0152 (the log line of the limit F3: EVIDENCE_DEFINING_PATHS is incomplete against governor-spec line 44).

## Log
- 2026-11-21: opened (session 0be70981; D-6996), from the limit (c) of docs/runs/TASK-156-acceptance.md.

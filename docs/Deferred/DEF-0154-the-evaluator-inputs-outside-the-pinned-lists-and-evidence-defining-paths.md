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
- 2026-11-21 (TASK-157, the task review F1 and the plan; D-7030 C4, D-7016 M6): two more evaluator inputs are in neither the EVALUATOR lists nor EVIDENCE_DEFINING_PATHS: src/aieos_bootstrap/scope_reconcile.py (it reads policy_version via policy_block and the risk rules via rules_from_policy, which eval_inputs.py requires) and src/aieos_bootstrap/base_inputs.py (contract_at, which eval_inputs.py consumes); under evidence_comparison as built by TASK-157, a change to either gives {weakens: false}. Each needs its own task and its own A66 decision to join the lists; not added now (outside the write set of TASK-157).
- 2026-11-21 (TASK-157, the four inputs of this item read under both questions at D-7016 to D-7018): for each of .aieos/project.yaml, src/aieos_runtime/**, AIEOS-concept.md and the measurement protocol with the measurements: (i) is it an input of the A29 evaluator and (ii) can a change to it change an evidence requirement (governor-spec :44): project.yaml: not read by the CI evaluator; no evidence entry today but the spec-2 layout would put the risk rules and default profiles there ("not today, yes if they move"); src/aieos_runtime/**: not read by the CI evaluator, no evidence entry; the concept: read by no src file, covered by GOV-001's hash rule; the measurement files: read by no src file, routed to the owner by OPS-002 and the OWNER_PATHS. Rule (f) of evidence_comparison treats every path whose first segment begins with a dot as weakening, so project.yaml is covered for that derivation. The decision agent's reading leaves project.yaml and src/aieos_runtime/** outside the lists; DEF-0154 :6 sends that reading to the owner, so a question to the owner is PENDING (the D-7016 M6 text, to be asked at the end of a session; the decision agent recommends "no"); it is not answered; this item stays open.
- 2026-11-25 (TASK-158; D-7061 M3, D-7063 B4; the corrective line to the line of the TASK-157 records, which is not edited): that line is wrong about the EVALUATOR lists for scope_reconcile.py and base_inputs.py, which src/aieos_bootstrap/** covers. TASK-158 added six entries to EVIDENCE_DEFINING_PATHS (evaluation_sources.py, scope_reconcile.py, base_inputs.py, base_files.py, evaluation.py, ci_evidence.py), sixteen entries in all. The rest of the import closure is NOT added and stays an open part of this item: gitread, eventlog, records, gate_records, recovery, writer, contract_path, resume_check, scope_drift.
- 2026-11-25 (TASK-158; D-7063 D4, a reading of D-7061 and D-7063, not what this item means; line :6 is not edited): the phrase of line :6 about each added path needing its own task and its own A66 decision is read there as concerning the EVALUATOR lists of the workflow; the tuple entries of TASK-158 were decided at D-7061 (group A). project.yaml and src/aieos_runtime/** stay under the pending D-7016 M6 owner question.

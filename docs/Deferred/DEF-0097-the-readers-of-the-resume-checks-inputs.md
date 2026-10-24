# DEF-0097: the readers of the Resume Check's inputs

- Status: open
- Opened: 2026-10-24 (session 3797498a; the owner's question on the Resume Check's inputs, decision D-2340)
- Deferred by: decision agent (A41, A51), D-2340 (a new M7 task, TASK-085, takes these readers).
- Decision group: A (an M7 task of specification 7's launcher, which runs the Resume Check before every grant).

## What
The Resume Check (TASK-008) decides only on the values it is given and reads nothing (src/aieos_bootstrap/resume_check.py :29-31). Its inputs are the 22 keys of resume_check.py :44-48, in the forms of docs/specs/conformance-files.md section 9 (:94). Before every grant the check is the launcher's (docs/specs/spec-07-cli-and-zero-friction-path.md :46). At main 4c496d7e:
- Read today: log_seq, task_state and approved_contract_hash, checked against the log by execution.py (TASK-032; docs/tasks/TASK-032.yaml :11, :335).
- Partly read: risk_rules (scope_reconcile.rules_from_policy, src/aieos_bootstrap/scope_reconcile.py :263, the governor's form, not section 9's).
- Read by TASK-082 at the base only, while the check reads at HEAD: contract (task_contract.py keeps seven keys, :228-229), contract_hash, components, interfaces, derived_read_set (the pure helper resume_check.direct_imports exists, :7-8), and the articles' texts.
- With the launcher (TASK-086): task_id; runtime ({adapter, max_risk}), to be confirmed.
- With no reader and no task before D-2340: head_commit; base_is_ancestor (gitread has no merge-base form, gitread.py :5-12; a walk by rev-list --parents is possible); commits (base..HEAD with each path's change kind and whether a task.submitted names the commit; reconcile.py walks commits with diff-tree --name-only, which gives no change kind); symbols (the pure helper resume_check.signature_form exists, :7-8); schemas; observed_read_set (the read hook writes the records, TASK-066 to TASK-068; nothing assembles them); intent_current (only a records script's mapper, outside src); dependencies (execution.py projects only its own task); the articles' scope, applicability and violated; policy_version; budget_use (retries by specification 1 section 5.1).
- The findings DEF-0035 carries "to the task that reads the Resume Check's inputs" (docs/Deferred/DEF-0035-the-resume-checks-carried-review-findings.md :9, :27; DEF-0030 :11), among them R5 F4 (read_set.unanalysed always [], and uncovered not saying that the derived read-set and every input are the caller's).

## Why deferred
D-2340: the readers are a task of their own, TASK-085, after TASK-082 (whose readers take a commit argument so that TASK-085 reuses them at HEAD) and TASK-084, and before the launcher's core (TASK-086), which calls the check.

## Resume when
At TASK-085's scope note; this item closes when every input above has a reader in an accepted task, or is moved to specification 3's next revision by its own decision.

## Depends on
TASK-081 (base_files), TASK-082 (the readers at a commit), TASK-008 (resume_check), TASK-032 (execution); specification 3 section 1, conformance-files.md section 9, specification 7 section 5.

## Log
- 2026-10-24: opened (session 3797498a; decision D-2340).

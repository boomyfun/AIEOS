# DEF-0107: GOV-003 in the self-build: the CI's test gates run the change's own tests

- Status: done
- Opened: 2026-10-30 (session 1c1bf794; TASK-102's acceptance, decisions D-3705, D-3706, D-3707)
- Deferred by: decision agent (A41, A51), at TASK-102's acceptance
- Decision group: A

## What
GOV-003 says the evaluator and its inputs are taken from the base or a pinned ref, never from the change under evaluation. The CI's unit, integration and property gates run the tests of the pushed checkout (`.github/workflows/aieos-checks.yml` :1438-1460), and the workflow's own list of evaluator paths includes `src/aieos_bootstrap/**`, `tests/unit/**`, `tests/integration/**` and `tests/property/**` (:429-436). A task that changes tests is therefore judged by its own tests. The review RG2 of TASK-102 found this ("GOV-003: does not hold", its record TASK-102-way2-GOV-003 in docs/records/TASK-102.jsonl), and the governor's shadow for TASK-102 is NEEDS_REWORK at row 2 for that reason alone. The gap is systemic: it applies to every self-build task that changes tests. DM row A29 is recorded as "a target, unmet by design for the self-build" (A51 item (7)).

## Why deferred
No rework of TASK-102 closes it. A fix needs a CI step or an equivalent that runs the base's tests (or a pinned set) against the change, or a stated policy by its own decision. That is a workflow change under A66 or a decision, not a text change.

## Resume when
It is the named successor of TASK-102. No later self-build task that changes files under `tests/` is started before this item is decided, either built or decided as a stated policy (D-3706 C3).

## Depends on
TASK-102, DEF-0108 (to be taken up with it).

## The stated policy (decision D-3740; the text of the decision agent's rulings D-3735 to D-3737)
Quotations, byte for byte from the source files (the executor checks each block as a substring of its source):

GOV-003, docs/pre-genesis/constitution.md lines 92-95:
```
### GOV-003 · governance · The evaluator is not taken from the change it judges
- Rule: the evaluator and its inputs, as A29 lists them, are taken from the base or a pinned ref, never from the change under evaluation. Source: A29, a target for gov-AIEOS (A51 item (7)); B17 (1) (proposed; not claimed sufficient, B17).
- Check: partial. Tool (way 1): CI rule, the evaluator paths and their inputs are read from the base ref, from a pinned list of paths; the list is itself one of those paths; and a path rule, a change that touches a listed path is marked as an evaluator change, which is judged by the base version and never auto-accepted (governor-spec.md §8, assurance-model.md §6, proposed). Review: the whole rule except what the tool part decides, in particular whether the pinned list covers every input A29 names. evidence_required: [ai_review].
- Severity: blocking. Scope: the evaluator paths. Applicability: all task types. Enforcement: blocking, ci_rule, cheap.
```

DM A29, docs/pre-genesis/decision-matrix.md line 90 (the cell):
```
**Composition invariant (C13).** *No execution path may exist in which the same authority domain can both change the evaluator or any input of the evaluator, and produce the evidence that evaluator uses to justify acceptance of that change.* **Authority domain** = every identity and channel that shares control; the agent's domain includes the agent account, everything in the agent's execution environment, and **every CI job that executes agent-modified code**. **Evaluator** = validators, fixtures, scenarios, workflows, runner version, governor, the dependencies and lockfiles they use, configuration they read from the change under evaluation, and the acceptance verifier itself. **[2026-10-07 (revision 21): for the AIEOS self-build, see A51.]**
```

DM A51 item (7), docs/pre-genesis/decision-matrix.md line 112, with its markers:
```
(7) A29 stays a target, unmet by design for the self-build, like C13. Recorded under decision agent decision D-073 (A41). **[2026-10-07 (revision 23): see A52.]** **[2026-10-07 (revision 25): see A54, points 1 and 2.]** **[2026-10-30: launching, connecting, measuring and approving findings, settings, publishing and sending messages, history rewrite and deletion on GitHub move to the decision agent for the self-build: see A73.]**
```

1. Scope: the AIEOS self-build only. It sets how an acceptance is handled; it does not change GOV-003, A29 or A51 (7). It sets the handling for files under tests/ only. The other evaluator paths of A29 and of the workflow's list (among them .github/**, src/aieos_bootstrap/**, docs/pre-genesis/conformance-scenarios-initial.md, docs/records/**, docs/tasks/**, constitution.md, risk-rules-gov-aieos.md, the lockfile and configuration forms, fixtures outside tests/) keep the handling GOV-003 gives them; this policy claims no "holds" for them. Whether they need a like policy is open as DEF-0110.
2. For a task that adds, changes or deletes any file under tests/ (the listed evaluator paths tests/unit/**, tests/integration/**, tests/property/**, tests/run_tests.py and tests/conformance/** are among them; A29 also names fixtures), GOV-003's article review is recorded as it falls. No "holds" is claimed for the tests part. The reading "tests are not 'validators'" (RG2's caveat) is not used.
3. Acceptance of such a task is a stated departure from the advisory governor, per task, in the form of D-3706 and D-3707; never automatic.
4. Required compensating controls (same-lineage evidence, not independent): (i) a local run of the base's tests against the change's src, the command brought to the decision agent first, its raw output recorded; (ii) a review of the test diff by a reviewer whose model differs from every model that did task work (L-0038), looking for removed or loosened asserts, skips, xfail, lost coverage, and removed or emptied fixtures.
5. Deeper gap, stated: src/aieos_bootstrap/** is itself an evaluator path (aieos-checks.yml :429), so a change to the governor is judged by the changed governor; the CI step in point 7 does not close it.
6. DEF-0108's wording: earlier GOV-003 "holds" records of tasks that changed or added tests do not cover the tests part. TASK-101's record TASK-101-way2-R3-GOV-003 (TASK-101.jsonl line 31) is an example: the change added tests/unit/test_export_resume.py (TASK-101.yaml :46 and :155), a file under an evaluator path, so the record's "holds" rests on "No existing test, pin, allow-list or closed-name list changed"; it does not show the new test file was judged by the base. This statement supersedes by wording only; no record is edited.
7. Next build task (a task with a contract commit and budgets of its own): a CI step that runs the base's tests against the change, together with DEF-0109's list fix (both copies of EVALUATOR in aieos-checks.yml :429-436 and :496-503, the native/bench/Go governor and lockfile forms, and a check that the copies match). The workflow diff is its own A66 decision; permissions stay contents: read, no secrets, no tokens (else owner). Until that task settles the reading, the native, bench and Go governor files are handled as evaluator paths; this is a handling rule, not a reading of A29. A reading that leaves any of them outside A29's evaluator narrows A29 and goes to the owner.
8. With this policy in the repository (the change-set's commit), D-3706 C3 is met: a task that changes tests/ may start, under points 2 to 4.

## Log
- 2026-10-30: opened at TASK-102's acceptance (session 1c1bf794).
- 2026-10-30: policy decided (D-3740), D-3706 C3 met; the CI step stays in the named build task; done when that task is accepted. Reviewed once by a reviewer on claude-haiku-5-5 (the draft before four small fixes); the fixes (the record's words in point 6, the scope sentence in point 1, the handling-rule wording in point 7, the status) were not reviewed again, nor were the restored quotations and the wording of point 1's list and of point 8 (D-3740).
- 2026-10-30: point 7 done: TASK-103 accepted (D-3830; the CI step runs the base's tests against the change; run 41019962046 on the task head, runs 41033002434 and 41033002251 on main at 621129ae green); the lists-equal step's gap is DEF-0111, the question of a failing step is DEF-0112; point 5's gap stays stated (DEF-0110, DEF-0111).

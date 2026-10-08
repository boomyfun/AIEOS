# DEF-0024: The CI workflow's next revision, and TASK-001's follow-up points

- Status: open
- Opened: 2026-10-09 (decision files D-189 and D-191)
- Deferred by: decision agent (A41), D-191 C5 and D-189 C6: none of the points blocks TASK-001's acceptance; a workflow revision is the owner's (A61; constitution SEC-003).
- Decision group: B for the workflow (the owner's permission, A61); A for the contents of follow-up tasks.

## What
- For the workflow's next revision: the deterministic_rule lists' gaps (module aliases, `from os import`, further modules, computed routes such as getattr with a built name); the SEC-002 step reads the files' added lines but not commit messages; tests/** and the other inputs A29 names are not on the pinned evaluator list, and the GOV-003 step only reports; OPS-003's three-word list; the step logs and the job summary need sign-in, so the path each step took is inferred.
- For TASK-001's successor work: a deeply nested decision value formatted with %r; `1e400` parsed as infinity; a leading byte-order mark hides line 1's other findings; non-string keys or a list event type raise in direct calls; violation.detected's fact_kind and blocking_kind share one failing case; no test sends an acceptance value on decision.execution; the Limits breadth (other ids unresolved, no cross-field checks) and the unscoped "no error found"; namedtuple's internal eval.

## Why deferred
None blocks TASK-001's acceptance (D-191); the workflow is the owner's to revise.

## Resume when
The next task that touches the checker or the evaluator, or the next workflow revision put to the owner.

## Depends on
DEF-0023 (done).

## Log
- 2026-10-09: opened (decision files D-189 and D-191). ../History/2026-10/2026-10-09-0153-task-001-landed.md
- 2026-10-09 (session e3ec0fb8): two more points carried (D-196 C5): for TASK-003 and the workflow question, the conformance run-record file is not in the repository and the CI step output needs sign-in, so how a run's results are read must be settled; for TASK-004, its own tests must cover how the governor derives the inputs of governor-spec section 3.2, which the fixtures give as values. Status: open. ../History/2026-10/2026-10-09-0352-m2-plan-and-conformance-files.md

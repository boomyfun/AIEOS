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
- 2026-10-09 (session 14e57acb): points carried for the workflow's next revision, which is the owner's (D-198 C6): pinning `.json` under tests/conformance/ for the INV-002 file rule, and adding tests/conformance/** to GOV-003's pinned list; for TASK-004 and the conformance files document's next revision (D-201 C4): section 4 gives no input for a risk class's level, so ACC-02's "at L1" rests on the set's default. Status: open. ../History/2026-10/2026-10-09-0514-fixture-file-kind-and-fixture-drafts.md
- 2026-10-09 (session 6b3792d9): TASK-002 accepted and landed (D-206). For the workflow's next revision, which is the owner's (A61): GOV-003's pinned list names no conformance path (tests/conformance/**, the bound scenario file, .aieos/conformance/**, the test modules, tests/run_tests.py), so its "evaluator change: no" is not evidence for a fixture task; the SEC-002 step reads only added lines (messages and file names only by SEC-001's patterns); the deterministic_rule lists' gaps (module aliases, `from os import`, further modules, Path.replace and Path.chmod); OPS-003's row pattern accepts any row-like token. For a later task touching the conformance tests (not frozen): INV-006's property counts outcome "fail" only; unused helper code and no tie between the three copies, one shared oracle; a limits docstring (no runner, NOT_RUN, inputs as values, a future PASS advisory); C0 versus Cc in the canonical escape; `re.compile` against AC6's literal word; ACC-13 with one case and an extra inputs key lack altered cases; ACC-10's equal-models record isolates governor-spec section 4 rule 3 only weakly; `missing` strings checked only as non-empty; the D-901 to D-904 placeholders; `refers_to` prose in two fixtures. Status: open. ../History/2026-10/2026-10-09-0637-fixtures-accepted-and-landed.md

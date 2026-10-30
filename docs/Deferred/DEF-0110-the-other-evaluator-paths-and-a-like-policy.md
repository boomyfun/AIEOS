# DEF-0110: the other evaluator paths and a like policy

- Status: open
- Opened: 2026-10-30 (session 9dbe9c67; DEF-0107's stated policy, decisions D-3737, D-3740)
- Deferred by: decision agent (A41, A51), D-3737 (Q4 of the haiku review of the policy draft)
- Decision group: A

## What
DEF-0107's stated policy sets the handling for files under `tests/` only. The other evaluator paths of DM A29 and of the workflow's list (among them `.github/**`, `src/aieos_bootstrap/**`, `docs/pre-genesis/conformance-scenarios-initial.md`, `docs/records/**`, `docs/tasks/**`, `docs/pre-genesis/constitution.md`, `docs/specs/risk-rules-gov-aieos.md`, the lockfile and configuration forms, fixtures outside `tests/`) keep the handling GOV-003 gives them, and the policy claims no "holds" for them. Whether a task that changes one of them needs a like policy (a stated departure, compensating controls) is not decided.

## Why deferred
The review of the draft policy found the coverage gap; deciding it needs its own look at each path class and is not needed to unblock the tests/ tasks.

## Resume when
A self-build task changes one of those paths, or DEF-0107's build task is planned, whichever comes first.

## Depends on
DEF-0107.

## Log
- 2026-10-30: opened with DEF-0107's stated policy (session 9dbe9c67).
- 2026-10-30: its resume condition was met by TASK-103, which changes .github/workflows/aieos-checks.yml; handled per task as a stated departure (GOV-003 recorded as fail by the way-2 review R3w for the workflow's own text; acceptance in the form of D-3706 and D-3707); the general policy stays open, so the status stays open.

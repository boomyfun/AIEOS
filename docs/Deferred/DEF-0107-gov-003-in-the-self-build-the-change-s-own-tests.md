# DEF-0107: GOV-003 in the self-build: the CI's test gates run the change's own tests

- Status: open
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

## Log
- 2026-10-30: opened at TASK-102's acceptance (session 1c1bf794).

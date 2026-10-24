# DEF-0099: list_tasks does not re-check a task's dependencies

- Status: done
- Opened: 2026-10-24 (session 3797498a; TASK-084's contract, decision D-2475)
- Deferred by: decision agent (A41, A51), D-2475 ruling 4 (list_tasks reads the log and the store only; the dependency check belongs to the launcher's grant path).
- Decision group: A (a later task's scope; nothing here changes a specification).

## What
TASK-084's list_tasks (src/aieos_bootstrap/execution.py) lists the tasks the log has in READY or REWORK with no unexpired lease in the store. It reads no contract, so it does not check that every task in a listed task's input_state.depends_on (specification 2 :103) is DONE. Specification 1 :65 makes READY require every dependency DONE at task.approved; list_tasks relies on that and does not see a dependency that left DONE afterwards, if a DONE task can become STALE (specification 1 section 10 point 8, :132, open; specification 1 :70 names no DONE source for task.stale), nor a log whose task.approved was appended with a dependency not yet DONE.

## Why deferred
D-2475 ruling 4: the check needs each listed task's contract read at a commit, which list_tasks does not do (ruling 3: the ids come from the log alone). The launcher's grant path (TASK-086) reads the contract anyway, so the check belongs there, before writer.grant_lease.

## Resume when
At TASK-086 (the launcher's core path), or any task that grants a lease from list_tasks' answer; this item closes when the grant path refuses a task whose dependency is not DONE, by its own decision.

## Depends on
TASK-084 (list_tasks), TASK-032 (execution's projection); specification 1 section 5.1; specification 2 :103; specification 7 sections 3 and 5.

## Log
- 2026-10-24: opened (session 3797498a; decision D-2475).
- 2026-10-24: done with TASK-086's records (decision D-2758): on the launcher's grant path a dependency not DONE makes the Resume Check's check 5 fire BLOCKED, so no lease is granted (TASK-086 AC6).

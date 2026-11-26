# DEF-0157: recovery of a half-written multi-append (X1, X2, run_task and import_task)

- Status: open
- Opened: 2026-11-26 (session 228f426b; the records of TASK-161; D-7217, D-7218; docs/tasks/TASK-161.yaml AC9 (8))
- Deferred by: decision agent (A41, A51), D-7218
- Decision group: A (scheduling); the group of the recovery work itself is set at its contract
- Blocks v0.1: no (decision agent, D-7262: the same half states already follow any append failure; the lock of TASK-161 adds only a trigger, a holder stuck longer than the timeout; X2 fails closed; the v0.1 exit review rechecks it)
- Scheduled in: none; a follow-up candidate

## What
"recovery of a half-written multi-append (X1, X2, run_task and import_task): a follow-up candidate, not part of TASK-161; one lock across both appends would remove only the lock as a trigger" (docs/tasks/TASK-161.yaml, AC9 (8)).

The cases (TASK-161 AC9 (7)): X1 execution.execute (also reached by adapter.start): the decision record may stand without its full state effect and the lease may already be released; a rerun is refused (D-687 M2). X2 the hook paths (claude_code_pretool_hook through session_violation, and claude_code_channel.deliver): violation.detected may stand without its STOP decision and the lease stays held until it expires; the observation still blocks the task (fail closed); that a rerun needs the same tool call is an assumption, not checked. launcher run_task and import_task: the contract file stays, a rerun is refused at write, and the file must be removed by hand.

## Why deferred
Not part of the guarded append (TASK-161); the states are older than it.

## Resume when
A task changes one of those callers, a real run meets one of these states, or the v0.1 exit review asks.

## Depends on
Nothing.

## Log
- 2026-11-26: opened (D-7217, D-7218; TASK-161 acceptance D-7255; group and v0.1 status D-7262).

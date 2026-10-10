# DEF-0038: TASK-009's non-blocking review findings in the recovery module and its tests

- Status: open
- Opened: 2026-10-11 (decision file D-395)
- Deferred by: decision agent (A41, A51), D-395 (TASK-009 accepted with these recorded, no fix in that task).
- Decision group: A (code and test code within the self-build).

## What
- tests/unit/test_recovery.py: the argument checks lack failing cases for a non-UTC aware time, an extra key in a commit or a lease, a recorder that is not a string, and a tuple of commits.
- tests/property/test_recovery_properties.py: "compensating only under a counting lease" is checked one way (each submission had a counting lease, not that every counting lease gave one), and the generated logs hold no earlier submission.
- tests/unit/test_recovery.py: the refused-append test covers a conflict, not a fence refusal (the contract expects none).
- tests/unit/test_recovery.py: its docstring says "all in memory" while the import check reads the module's own source (read under D-395 as allowed by AC8 and AC12 R8, and nothing else); one comment cites D-393 C3 where the rule is C2.
- src/aieos_bootstrap/recovery.py: the module docstring's step 1 summary omits the finding a malformed, misplaced or miscased trailer gives (the task commit's message omits it too).
- Recorded only: a CRLF message is read as one paragraph, and a line with a prefix before a key is not read as a trailer, as the CI's line-anchored trailer rule does not read it either (D-395 checked that no shape the CI counts escapes recovery); findings echo message text with %r; the import check needs Python 3.10 or later, which the CI's runner has; AC10's purity limits rest on the code check, not a unit test.

## Why deferred
D-395: none weakens a check; a fix would have meant a second task commit, a push and new reviews for test depth and wording.

## Resume when
The next task that changes src/aieos_bootstrap/recovery.py or its test modules.

## Depends on
TASK-009 accepted (done, D-395).

## Log
- 2026-10-11: opened (decision file D-395).

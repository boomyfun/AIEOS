# DEF-0053: the review findings carried from TASK-025, the submission path

- Status: done
- Opened: 2026-10-12 (decisions D-598 and D-599)
- Deferred by: decision agent (A41), D-598 (the dispositions F1 to F10 of the five way-2 reviews; F3 and F5 carried) and D-599 (C4).
- Decision group: A (a design point of the writer and a test gap within the self-build).

## What
- **F3, the release after an appended event takes no token** (way-2 reviewers R2 and R5): submit calls writer.release_lease(root, task_id), which removes whatever lease the store holds on the task. If the lease expired and a new one was granted to another holder between the append and the release, that new lease would be released. The limit is stated in submit.py's docstring. A release by token needs a writer change (writer.py, outside TASK-025's write set).
- **F5, stand-in writer results** (R2): submit reads the writer's result with getattr; a stand-in whose attributes raise other than AttributeError, or whose findings are not iterable, makes submit raise. The real WriteResult is slotted and well formed, so this concerns stand-ins only.

## Why deferred
F3 needs a change to the single writer, which TASK-025 may not touch; v0.1 runs one task at a time (concept line 951), so the window cannot open today. F5 does not occur with the real writer (D-598).

## Resume when
F3: before more than one task runs at a time, and before TASK-026 (recovery at start) or TASK-027 (the evaluation path) relies on the release. F5: at the next task that changes submit.py.

## Depends on
DEF-0030 (the core's caller); TASK-016 (the writer).

## Log
- 2026-10-12 (session a3411bd9): opened. TASK-025 accepted at b647c160 and on `main` (decision D-600; records ee7d5ccd, D-601). ../History/2026-10/2026-10-12-0215-the-submission-path-accepted-and-on-main.md
- 2026-10-12 (session bab88211): done. F3 resolved by TASK-028 (release by token: writer.release_lease_token removes the held lease only when its token equals the given one, compared and removed in one store transaction; the submission path releases through it with the commit's token) and F5 resolved by TASK-028 (the submission path reads writer and release results of any shape without raising); TASK-028 accepted at 0f204666 and on `main` (decision D-613; records bcd3fe9a). ../History/2026-10/2026-10-12-0333-release-by-token-accepted-and-the-recovery-contract.md

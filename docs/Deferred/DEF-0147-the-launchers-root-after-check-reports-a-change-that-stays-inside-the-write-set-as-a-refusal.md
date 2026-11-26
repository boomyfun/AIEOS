# DEF-0147: the launcher's "root after" check reports a change that stays inside the write set as a refusal, so the first correct change of a launched session ends with exit code 1

- Status: open
- Opened: 2026-11-19 (the History page of the session 26136a0a names the session)
- Deferred by: decision agent (A41, A51), D-6465 (the finding, as read by the worker from the seventh launch)
- Decision group: A (scheduling)
- Blocks v0.1: no (it does not stop a run; it makes a correct run look refused)
- Scheduled in: M8: decided after the second real run (D-6756; docs/runs/TASK-148-acceptance.md :53)

## What
The seventh launch (TASK-143 v2; 2026-11-19 17:30:18 to 17:30:31; the decision D-6464) ended with the lines (inner_out.txt): "finding: launch: refused root after", "finding: root after: root: 1 entries (changes against HEAD in the index or the working tree, or untracked files)", "finding: root after: root: b'docs/Deferred/DEF-0095-the-handoff-file-of-the-claim-tools-for-the-launcher.md'" and "cli.main exit code: 1". The session had done what the contract asks: one Edit of line 7 of that very file (the one path of the write set), checked by a Read, no shell call, no violation. The sixth launch (no edit made) ended with "root after: clean".

## The cause (read in src/aieos_bootstrap/launcher.py :1205-1215 and its docstring :1253-1261, task TASK-127)
After the session's end the launcher reads the root once more: a clean root adds the finding "root after: clean"; ANY other answer (a change against HEAD in the index or the working tree, an untracked file) adds findings that begin "root after:" and, when no earlier reason is set, the reason "root after", so that the result is "refused"; the end and the handoff are made as before; the finding is advisory and no event is written. The check does not compare the changed paths with the contract's write set, so a change inside the write set, which is exactly what a successful task of the loop leaves in the working tree (the capture step takes it from there), is reported like a stray change.

## Consequences
The launched run's exit code is 1 and its result "refused" after a correct run; a reader (the worker, the decision agent, a script) must know that the finding is advisory and look at the paths: here the one path of the write set. Nothing was lost: the decision.execution (CONTINUE) and the observed-read-set lines were written (log lines 43 and 44) and the working tree held the intended change.

## Options (none chosen)
(a) Leave the check as it is and state in the instructions that the finding is advisory and is read with the changed paths. (b) The check compares the changed paths with the write set of the contract (the end call already receives the write set) and reports "root after: only the write set changed (paths ...)" as a non-refusing finding, and refuses only for a path outside the write set or an untracked file. (c) The check refuses only for a path outside the write set and for the index (a staged change). (b) and (c) change src/aieos_bootstrap/launcher.py (class high) and its tests (TASK-127's), as a task of the loop.

## Limits and not measured
One launch showed it; the other ends (a done end with no change, an end with a change outside the write set) are not re-measured here; the docstring states the limits (a change made and undone within the session is not seen; a change after the read is not seen).

## Resume when
Before the second real run of a loop task whose result is read by a script or by the governor's input, or when the end-of-run result is judged mechanically.

## Depends on
TASK-127 (the check), DEF-0143, DEF-0146; the seventh launch's evidence (inner_out.txt 065e7bf5...).

## Notes on sources

File names written aj/... or S1\aj\... in this record are kept in the lasting copies under C:\Users\Admin\AIEOS-REG0-lite\sessions\26136a0a-b135-4cb1-9db0-95258ca6f5b5\scratchpad-evidence (the folder stretch-D6445-D6469 and the folders TASK-140, TASK-140-ci, TASK-141 and TASK-141-ci) or under C:\Users\Admin\AIEOS-REG0-lite\sessions\c0dc5bcc-c58f-46fa-a52d-d27469300fc7\scratchpad-evidence\def-sources (aj/launch5b, aj/launch5c, aj/ao8_compile.py, aj/ao8_out.txt, aj/make_drafts.py); the prefix aj/ names the old scratch folder, which no longer exists.

Figures in this record that no decision file carries and that no script re-checked against a lasting copy (run times, byte counts, tool-call counts) are the worker's measurements and are not re-verified.

## Log

- 2026-11-27 (session 228f426b; closure pass 1 of the deferred items, D-7443, D-7444; decided by: decision agent (A41, A51), D-7444): scheduled.
- 2026-11-27 (session 228f426b; closure pass 1 of the deferred items, D-7443, D-7444; decided by: decision agent (A41, A51), D-7444): carried from DEF-0140 at its closing: a session that ends with no work returned exit 0 and "end: done" (the starter does not detect a denied prompt), not changed by TASK-140; to be looked at where the end-of-run result is judged mechanically.

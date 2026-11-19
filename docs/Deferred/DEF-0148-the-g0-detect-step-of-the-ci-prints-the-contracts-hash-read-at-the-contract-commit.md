# DEF-0148: the G0 detect step of the CI prints the contract's hash read at the contract commit, which for a task whose contract was revised after its creation commit is not the approved hash

- Status: open
- Opened: 2026-11-19 (session 26136a0a)
- Deferred by: decision agent (A41, A51), D-6467 (the finding, from the worker's reading of the CI text)
- Decision group: A
- Blocks v0.1: no (it blocks citing a state-contract task's run through "G0 detect")
- Scheduled in: not scheduled

## What
.github/workflows/aieos-checks.yml :335-370 (G0 detect): the task's contract commit C is "the one commit that adds docs/tasks/<id>.yaml or .aieos/tasks/<id>.yaml"; it prints "G0 contract sha256" of the bytes AT THAT COMMIT; its comment (:242) says "the approval check compares it with the approved contract_hash". For the tasks made by `aieos run` and then revised (TASK-142 v1 to v3; TASK-143 v1 to v2) the commit that adds the file holds the generated v1 (TASK-143: d0b3206a, sha256 44f7a146...), while the approved contract_hash in the log is the revised version's (TASK-143: e20e7864..., approved by task.approved at log line 42). The worker did not find, in the workflow text it read, where the comparison is made; if it is made against the approved hash of the log, a revised state-contract task would not match. The same applies to the other G0 checks that use the contract at C (the write set and the forbidden list come from v1: here equal to the revised ones).
## Limits and not measured
The comparison itself (where, with what); no push of a TASK-142 or TASK-143 commit with the AIEOS-Task trailer has ever run the step.
## Options (none chosen)
(a) the revision route also changes the CI's reading (the contract at the approved hash's commit); (b) the route makes the creation commit hold the final contract (the contract is written and approved before the first commit of the file); (c) accept and state that state-contract tasks that were revised are not cited through G0.
## Resume when
Before a state-contract task of the loop is pushed with its trailer commit.
## Depends on
DEF-0145, DEF-0146, TASK-143.

## Notes on sources

File names written aj/... or S1\aj\... in this record are kept in the lasting copies under C:\Users\Admin\AIEOS-REG0-lite\sessions\26136a0a-b135-4cb1-9db0-95258ca6f5b5\scratchpad-evidence (the folder stretch-D6445-D6469 and the folders TASK-140, TASK-140-ci, TASK-141 and TASK-141-ci) or under C:\Users\Admin\AIEOS-REG0-lite\sessions\c0dc5bcc-c58f-46fa-a52d-d27469300fc7\scratchpad-evidence\def-sources (aj/launch5b, aj/launch5c, aj/ao8_compile.py, aj/ao8_out.txt, aj/make_drafts.py); the prefix aj/ names the old scratch folder, which no longer exists.

Figures in this record that no decision file carries and that no script re-checked against a lasting copy (run times, byte counts, tool-call counts) are the worker's measurements and are not re-verified.

# DEF-0115: a task commit pushed straight to main makes the task-gated CI steps hollow

- Status: open
- Opened: 2026-11-02 (session bdca08a6; TASK-114, decisions D-4525, D-4526, D-4528, D-4529, D-4530, D-4531)
- Deferred by: decision agent (A41, A51), D-4526 C7 for the content, D-4531 for the text, and D-4554 for the correction section and the Log line
- Decision group: A (self-build)

## What
G0 detect takes the commits that are outside origin/main and reads the AIEOS-Task trailer from them. A task commit X that is pushed straight to `main` is not outside main, so detect finds no task and writes `"task": null`. Every task-gated step then exits at once with "no task" and checks nothing: G1 build, unit_test, integration_test, property_test, deterministic_rule, OPS-003, static_security_analysis and the GOV-003 base tests. The run is green and the steps are hollow.

Evidence, read from the run logs (the logs are to be kept for good at %USERPROFILE%\AIEOS-REG0-lite\sessions\bdca08a6-36fd-4768-9a7d-52e66d573c7b\scratchpad-evidence\t114\; the copy is its own later step and decision; the files are named below as they are in the session's scratchpad t114\x\):
- TASK-112 X (c68c953c; aieos-checks run 41305902459; `ci_log_X112_checks.txt`, sha256 0a646f2ce38e931d058e8319b73fa2ebc29d565a73cf403d6a9cfe137576ed1f; the log's line 45 reads "SHA: c68c953ca34cb3c8cae3893e5430b538d4850bbd"): "G0 detect: no task (... commits outside main: 0)" at line 216, "G0 scope: no task" at 666, and "no task" from G1 build, unit_test, integration_test, property_test, deterministic_rule, OPS-003, static_security_analysis and the GOV-003 base tests at lines 1516, 1526, 1536, 1546, 1782, 1838, 1871, 1907. No output line "G0 detect: task TASK-112". The records of that run are docs/records/TASK-112.jsonl lines 1-7, 14 and 16 (step03, 11, 14, 15, 16, 17, 19, 20, 21: G0 task detection, G0 scope, G1 build, unit_test, integration_test, property_test, deterministic_rule, OPS-003, bandit); line 31 (the acceptance) also cites the run.
- TASK-113 X (c1545b31; aieos-checks run 41328272424; `ci_log_X113_checks.txt`, sha256 509e94db4f128c74571715ab0f82079399747c947308e4e2b40db70e857209b8; the log's line 45 reads "SHA: c1545b31df23cceaa9f6e32a41b5a46ff84d9206"): "G0 detect: no task (... commits outside main: 0)" at line 216, "G0 scope: no task" at 663, and "no task" at 1513 (G1 build), 1523, 1533, 1543, 1779 (deterministic_rule), 1835 (OPS-003), 1868 (static_security_analysis), 1904 (GOV-003 base tests). The records of that run are docs/records/TASK-113.jsonl lines 1-7, 14 and 16 (the same layout, nine lines). Line 45 ties the file to X113's commit; that it is the log of run 41328272424 rests on the command recorded in the session's checkpoint (cp109), not on a new read.
- TASK-114 X (0fc09a53; aieos-checks run 41373188835 on main; `ci_log_X114_checks.txt`, sha256 e9c38ca24ed66a22a8330ee143d0e22b5161ad28ea4649819e181861b08fab88; the log's line 45 reads "SHA: 0fc09a53562c7b7bece72abd01227f796ad0088b"): the same mechanism, "no task" at lines 229, 692, 1542, 1552, 1562, 1572, 1808, 1864, 1897 and 1933.
- TASK-114 Z (1b0d4381; aieos-checks run 41376496465 on the branch task/TASK-114; `ci_log_Z114_checks.txt`, sha256 5b7f3bfde2acdb2ffaa01e87320a1da751aa07c36b466a52e68f4beea6f946cf; the log's line 45 reads "SHA: 1b0d4381eaab7846d6176f1a319f0cfe7b157f02"): the same tree and parent as X; "G0 detect: task TASK-114 contract commit 5031c56b... base 0723c786...", scope "commits 1, paths 2, failures 0", unit_test 2466, integration_test 196, property_test 219, deterministic_rule and OPS-003 "files 249 ... findings 0", bandit no issues. The steps ran.

Affected: TASK-112, TASK-113 and TASK-114 (the straight-to-main route began at TASK-112, decision D-4387). TASK-109 to TASK-111 pushed X to task branches (D-4159, D-4257, D-4334) and their cited runs are branch runs (the run views reported in request D-4530). From TASK-112 on, X was on main before its acceptance, which departs from DM A61, whose question said "Phần chính chỉ nhận phần việc đã được duyệt."; the rule below restores the branch-first route. The governor counts a CI-class record with outcome pass as meeting a tool entry without reading the step output (governor.py :285-319).

The decision agent approved the switch to the straight-to-main route at D-4387 without seeing that it makes these steps hollow (stated in D-4526).

## Correction to the records of TASK-112 and TASK-113 (D-4526 C6; written under D-4554)
- TASK-112 (accepted in D-4392 at X c68c953ca34cb3c8cae3893e5430b538d4850bbd): docs/records/TASK-112.jsonl lines 1-7, 14 and 16 are records that cite run 41305902459 for steps whose output in that run was "no task" (the log lines under What). They do not show that those steps checked anything at X.
- TASK-113 (accepted in D-4457 at X c1545b31df23cceaa9f6e32a41b5a46ff84d9206): the same holds for docs/records/TASK-113.jsonl lines 1-7, 14 and 16 and run 41328272424.
- No record is edited: the records are append-only and public. The two acceptances are not reopened by this note.
- A later option, not planned: a re-made copy of each X, with the same tree and parent and the task's trailer, pushed to `refs/heads/task/<id>` so that the steps run (the method used for TASK-114's Z); each push would be its own decision.

## Why deferred
The rule from TASK-115 on below needs no code change. The two follow-ups need their own contracts: a text-test change (tests only) and a records-maker or governor change.

## Rule from TASK-115 on (decided in D-4526 C7)
- A code task's X, or a re-made copy of X if X is already on main, is pushed to `refs/heads/task/<id>` before it goes to main. Each push is its own decision.
- No record cites a CI step as met unless that run's log shows "G0 detect: task <id>".

## Resume when
TASK-115's contract, and the next change to the records maker, the governor or the workflow's detect.

## Follow-ups owed
- A tests-only task: add the on-main and base-equals-parent lines to the DETECT_LINES of `tests/integration/test_g0_detect_copies.py` (D-4525).
- A task that makes the records maker or the governor refuse a CI-class record for a task-gated step whose cited log printed "no task" (its own task; an A66 decision if it touches .github/).

## Depends on
TASK-112, TASK-113, TASK-114; `.github/workflows/aieos-checks.yml` (G0 detect, two copies); governor.py :285-319.

## Log
- 2026-11-02: opened (session bdca08a6). Written in the docs commit whose parent is the records commit 428b6d0750fa862764e952353539fe2486779547 of TASK-114 (D-4554); the code commit of TASK-114 is 0fc09a53562c7b7bece72abd01227f796ad0088b.

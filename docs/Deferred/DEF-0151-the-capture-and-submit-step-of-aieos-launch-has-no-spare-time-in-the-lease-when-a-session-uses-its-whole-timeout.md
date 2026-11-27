# DEF-0151: the capture-and-submit step of `aieos launch` has no spare time in the lease when a session uses its whole timeout, so a slow step would submit after the lease expired and be refused (BT1b, TASK-148)

- Status: open
- Opened: 2026-11-20 (the acceptance text docs/runs/TASK-148-acceptance.md, decided at D-6756)
- Deferred by: decision agent (A41, A51), D-6737 (v) and D-6608 M2 (the item), D-6756 (the filing at the acceptance of TASK-148)
- Decision group: A (scheduling)
- Blocks v0.1: no (it does not stop a run; the refusal fails closed: the commit and the ref stay and the tree is left as the session left it); it must be looked at before the second real run uses the step (D-6756)
- Scheduled in: M8: BT4, looked at before the second real run uses the capture step (D-6756)

## What
`aieos launch` (src/aieos_bootstrap/launcher.py, launch_outside) begins the session with a lease of LAUNCH_LEASE, two hours (launcher.py :1074, begun at :1282; launcher.py line numbers at the contract's base c3036085, TASK-148 moves them). The runtime's starter bounds the session by 6600 seconds (src/aieos_runtime/claude_starter.py :100), so 600 seconds remain in the lease when the session uses its whole timeout. After the session returns, the new step capture_submit.capture_and_submit (TASK-148) makes at most about ten git calls, each with a timeout of 60 seconds (the TASK-147 module's limit (14), task_capture.py :32-34: every git call has a time limit of 60 seconds; the core's own reads use launcher.TIMEOUT, 30 seconds, launcher.py :309; the count of about ten calls is the contract's, AC9 (14)), so 600 seconds in the worst case, equal to the margin. A submission made after the lease expired is refused by the writer (the step's reason "submit"; the launch's reason is then "capture"); the step then leaves the commit and the task ref, does not restore the tree (D-6608 Q4, D-6609 C3 (b)) and the next launch of the task is not granted until the tree is resolved by hand.

## Consequences
A session that runs to its full timeout followed by a slow disk or a slow git can lose its submission by seconds. Nothing is lost: the commit stays on refs/heads/task/<id> and the work tree stays as the session left it. The cost is a by-hand resolution (a decided by-hand step: submit the kept commit, or reset the tree) and one wasted launch.

## Options (none chosen)
(a) Lengthen the lease to cover the step (for example LAUNCH_LEASE of two hours and ten minutes, or a lease renewal before the step); a change of src/aieos_bootstrap/launcher.py (class high) and its tests. (b) Shorten the starter's timeout by the step's worst case (a change in src/aieos_runtime/claude_starter.py, which the CI rule check_starter pins). (c) Leave it and state it in the instructions of a launch (the margin is a limit, read with the findings "submit: ..." of a refused step).

## Limits and not measured
The figures are the contract's (AC9 (14)) and the constants of the files; no launch with the step has run. How long the ten git calls take on the owner's disk is not measured.

## Resume when
When a launch ends with the reason "capture" and a finding that the submission was refused for an expired lease.

## Depends on
TASK-148 (the step; docs/runs/TASK-148-acceptance.md), TASK-147 (task_capture.py), D-6737 (v), D-6608 M2.

## Log
- 2026-11-20: opened (session dc7cf6ca; decisions D-6737, D-6608, D-6756).
- 2026-11-27 (session 228f426b; closure pass 1 of the deferred items, D-7443, D-7444; decided by: decision agent (A41, A51), D-7444): scheduled.
- 2026-11-28 (session 228f426b; BT4, the pre-run record of the second real run, D-7773 and D-7774; decided by: decision agent (A41, A51), D-7773): ruled option (c) for the second run (D-7773 R2): the lease margin is a stated limit (A12); the refusal fails closed and the run's tasks are one-line edits. Resume when is narrowed to its second trigger. The record is docs/runs/second-real-run-pre-run-record.md. Status unchanged.

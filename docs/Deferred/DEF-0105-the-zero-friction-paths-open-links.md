# DEF-0105: the zero-friction path's open links

- Status: open
- Opened: 2026-10-29 (session ea6ea0a3; M7's exit review, decisions D-3323, D-3324)
- Deferred by: decision agent (A41, A51), at M7's exit (`docs/plan/m7-exit-review.md` §3)
- Decision group: A (self-build tasks after M7; launching and real use stay the owner's, DM A51 item (4))

## What
`aieos init`, `import` and `run` are built (TASK-095, TASK-097, TASK-098). The path from an intent to a running task is still open at these links:
- No reader reads the contracts that `import` and `run` write under `.aieos/tasks/`. Who commits them, and how they stay out of an agent's commit, is not settled. This is (r3) of TASK-098's scope, decision D-3277 Q3.
- `aieos import` accepts the root only in its Windows form (decision D-3281). Its end-to-end test leg is skipped off Windows.
- `aieos run`: the same intent and class recorded under another `--by`, on a log that already holds the intent's claim, is refused "conflict" after the template's write. This is G2 of decision D-3315.

## Why deferred
Each link needs its own contract. None of them blocks M7's goal parts, which are built and tested.

## Resume when
The first M8 task that reads `.aieos/tasks/`, or the next task that changes `launcher.import_task` or `launcher.run_task`.

## Depends on
TASK-095, TASK-097, TASK-098; specification 7 §2, §3.

## Log
- 2026-10-29: opened at M7's exit (session ea6ea0a3).
- 2026-10-30: links 2 and 3 done by TASK-104 (accepted in D-3892; task commit f79656f1; the Linux leg of the end-to-end import test is the real test of the POSIX root); link 1 (the reader of the tasks folder) stays open.
- 2026-10-31: link 1's reading half done by TASK-107 (accepted in D-4060; it replaced TASK-105, whose contract was committed, never run and stays on main, and which specification 7 :106 and :116 still name; task commits fa04c256 and 86842ebc and records commit 41007fb7 on main, CI runs 41186045776 and 41186045779 green): base_inputs, task_contract.read_contract and the shell allowlist reader's contract walk resolve a contract's place by contract_path's one rule (specification 7 revision 6): the state folder's tasks first, then docs/tasks; a contract in both places is a finding and neither is read; a refusal on either side never falls back to the other. Still open under link 1: who commits the files under the state folder's tasks and how they stay out of an agent's commit (the proposed rule that a contract's write set does not list the state directory is read by no check), and the handoff reader (DEF-0095).

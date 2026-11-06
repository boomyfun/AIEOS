# DEF-0105: the zero-friction path's open links

- Status: open
- Opened: 2026-10-29 (session ea6ea0a3; M7's exit review, decisions D-3323, D-3324)
- Deferred by: decision agent (A41, A51), at M7's exit (`docs/plan/m7-exit-review.md` §3)
- Decision group: A (self-build tasks after M7; launching and real use stay the owner's, DM A51 item (4))
- Blocks v0.1: yes (concept lines 938 and 940: the .aieos/ format and the zero-friction path are in the v0.1 list; the loop has never run end to end, master-plan.md :160)
- Scheduled in: M8, the zero-friction path task (enforcement of the state-file rule, the texts that predate A73, the requirement and ADR readers), before the M8 exit review

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
- 2026-10-31: link 1's handoff reader done by TASK-108 (accepted in D-4111; task commit 5aada5be and records commit 9013f7ca on main; see DEF-0095's Log of the same day): base_inputs reads the last handoff from both the state folder's handoffs and docs/handoffs by the claim records' order. Still open under link 1: who commits the files under the state folder's tasks and handoffs and how they stay out of an agent's commit (read by no check), and the rest listed in DEF-0095 (session c7d6f32b; decisions D-4111, D-4116).
- 2026-11-02 (session bdca08a6): TASK-113 (accepted in D-4457; task commit c1545b31, records commit 4268cced) created the repository's root `.gitignore` with the one rule `.aieos/local/` (specification 2 section 3; decisions D-4428, D-4429). It settles nothing under link 1: whether, when and by whose decision the files under the state folder's tasks and handoffs, and the other files under `.aieos/`, are committed is still open (TASK-113's AC2); the state-file rule (specification 7 section 10 or specification 2 section 3, with its DM row) comes as a specification revision before the first commit of any file under `.aieos/` (decision D-4430 C3). Carried, not done: `aieos init` writes no ignore rule for product projects (AC3 (a)); the texts of cli.py (:67, :90-91, :102-103) and specification 7 (:35, :50) on whose act a launch, an import or a run is predate DM A73 and wait for a docs fix (AC3 (d)).
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass C decisions D-5257 and D-5258): read in full; the Resume-when event (the first M8 task that reads .aieos/tasks/) occurred: TASK-107 and TASK-108, accepted 2026-10-31, are M8 tasks; links 2 and 3 are done (TASK-104) and link 1's two readers are done (TASK-107, TASK-108); the state-file rule is stated in specification 7 revisions 6 and 10 (commit 0723c78, 2026-11-02, DM F82), before the state commit 711d7a95 (2026-11-05), so that commit was not a departure from D-4430 C3; open: the state-file rule is enforced by no check and the state commit is not automated, the texts of cli.py and specification 7 that predate A73, the requirement and ADR readers under .aieos/intent/ (master-plan.md :168), and the loop run end to end (the first real run); the point 'aieos init writes no ignore rule for product projects' is a point for AIEOS projects and is listed in the plan revision (D-5265 M1). State: open; Blocks v0.1: yes (concept lines 938 and 940: the .aieos/ format and the zero-friction path are in the v0.1 list; the loop has never run end to end, master-plan.md :160); Scheduled in: M8, the zero-friction path task (enforcement of the state-file rule, the texts that predate A73, the requirement and ADR readers), before the M8 exit review.

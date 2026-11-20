# DEF-0152: the caller of the gate maker (BT3) must give steps of a run whose detect step names the task, on the right commit, as plain data, without the args key, and must handle a rerun, because the maker cannot check any of this (BT2, TASK-150)

- Status: open
- Opened: 2026-11-21 (the acceptance text docs/runs/TASK-150-acceptance.md, decided at D-6789)
- Deferred by: decision agent (A41, A51), D-6785 C5 (the duties of the caller, one item) and D-6789 (the filing at the acceptance of TASK-150)
- Decision group: A (scheduling)
- Blocks v0.1: yes, through DEF-0136 (the maker of TASK-150 is only the pure part; the code that reads a CI run and appends the records is BT3, and it must meet these duties before a gate result is counted for a real task)
- Scheduled in: BT3 (the evaluation runner), before its first real use

## What
`gate_records` (src/aieos_bootstrap/gate_records.py, TASK-150) turns the step conclusions of one CI run, given as data, into gate-result records of the CI source class that the governor counts. It reads no CI run and appends nothing. Because it stamps the CI class on whatever steps it is given, five duties lie with the caller that wires it (BT3); the module docstring states them under "What the caller owes", and two blind reviews and the decision agent named them (D-6785):
1. **The detect step must name the task.** The four mapped steps of the default map (G0 task detection, G0 scope, G1 build, lint) also conclude as success in a run that has NO task: each prints a note ("G0 detect: no task ...", "G0 scope: no task", "G1 build: no task", "lint: no task") and exits 0 (the CI run of main at the contract commit 3572f958, aieos-checks 44777971143: log lines :231 "G0 detect: no task", :724 "G0 scope: no task", :1423 "G1 build: no task", :2127 "lint: no task"; the run on the task branch, 44780942904, shows the task forms, for example :231 "G0 detect: task TASK-150 ..."). The maker cannot tell the two apart from conclusions. The caller must give steps only of a run whose detect step output names this task (for example "G0 detect: task TASK-150 ..."), and the right commit.
2. **The steps belong to the run on the given commit.** The record carries the commit it is given. Whether the steps are of a run on that commit is the caller's (the contract's limit 4).
3. **Plain data.** The arguments are plain data as loaded from JSON. A str, dict or list subclass whose methods lie or change between two reads is outside the guarantee (review B finding 2, D-6785: option (2), the code is not changed because exact-type checks would end the contract's AC1 test that a BaseException raised from an argument's own method passes through).
4. **The plan entries without args.** The run-made plan's G3 entry carries an args key; the maker refuses the whole call for a plan entry with any key besides gate and check. The caller passes gate and check only.
5. **Reruns and the repeated record id.** The record_id binds the task, the commit and the gate, not the outcome or the intent versions: a rerun gives the same id, and the governor refuses a repeated id within one request (governor.py :197-208, an error record, fail closed). The caller must give one record per gate per evaluation and must decide what a rerun on the same commit does.

## Consequences
Without these, BT3 could count a "pass" for scope, build and lint that is no evidence for the task (a run with no task), or records of a run on another commit, or an error for the whole plan.

## Options (none chosen)
(a) BT3 reads the CI run's step log lines of the detect step and gives steps only when that line names the task; and checks the head commit of the run. (b) The maker takes an extra argument (the detect line) and refuses without it: a change of the contract of gate_records, a new task. (c) A test of BT3 for each duty.

## Resume when
At the contract of BT3 (the evaluation runner), before its first real use.

## Log
- 2026-11-21 (TASK-150, acceptance D-6789): opened with the items above. Sources: docs/runs/TASK-150-acceptance.md (limits A3, A4, B1, B2, B6, B7), the reports of the two blind reviews (SR rev150 report_A.txt, report_B.txt), D-6785 C5.

# DEF-0136: no maker records a gate result that the governor counts for a run-made task (gates G0 to G3), so the correct change of the first real run cannot reach NEEDS_REVIEW and master-plan.md :117 is not met by that run

- Status: open
- Opened: 2026-11-15 (docs/runs/first-real-run-pre-run-record.md, A3 (iii))
- Deferred by: decision agent (A41, A51), D-6281 (the change list of the one rewrite of the pre-run record: the missing G3 maker is opened as a deferred item, D-6239 (1)(i))
- Decision group: A (scheduling)
- Blocks v0.1: yes (the v0.1 exit criterion of master-plan.md :117 expects ACCEPT or NEEDS_REVIEW for the correct change of the first real run; with this gap the loop gives INSUFFICIENT_EVIDENCE for it, so the criterion stays open until a run meets it)
- Scheduled in: M8, after the first real run and before the run that meets the criterion

## What
The plan of a run-made low contract (the shape of .aieos/tasks/TASK-116.yaml, made by `aieos run`) is G0 (scope), G1 (build), G2 (lint) and G3 (review, args AC1 and AC2) (launcher.py :1794, :1828). The governor counts only gate results of source class deterministic_tool_external_ci (governor.py :37, :428) and drops any record whose subject is a string other than the task (governor.py :334). At b615820e a search of src/ for a "gate" key finds only reconcile.py :367 as a maker of gate records; rule_results_from_steps (reconcile.py :344-368) maps the steps of a CI run (the conclusions success and failure) to article-form G3 observations whose subject is the COMMIT (:366), which governor.py :334 does not read for a task; and no workflow under .github/ names a gate. So no maker produces any gate result that the governor counts for a run-made task: G0, G1, G2 and G3 are all missing, and the governor decides INSUFFICIENT_EVIDENCE (governor.py :467-468) for a correct change. The first real run is therefore expected to give INSUFFICIENT_EVIDENCE for its correct task (the pre-run record, A3), not the ACCEPT or NEEDS_REVIEW that master-plan.md :117 names. The missing piece is a maker that records the gate results with the TASK as subject, or a change in how records with the commit as subject are read for a task; the mapping of rule_results_from_steps as written cannot supply the task's gates. Which fix is open.

## Why deferred
D-6239 (1)(i) ruled that the gap is opened here, that master-plan.md :117 is not edited, and that neither the maker nor a step under .github/ comes before the first real run: the run is the measurement that shows the loop's real decisions. The cause was refined at D-6283 (the gap is all gates, not only G3).

## Resume when
After the first real run has ended and its result is read; before the run that is to meet master-plan.md :117.

## Depends on
The result of the first real run (the pre-run record, A3); DEF-0115 (a task's commit goes to main only after its acceptance).

## Log
- 2026-11-15: opened (session 26136a0a; decisions D-6239, D-6281, D-6283).

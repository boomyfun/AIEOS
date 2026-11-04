# DEF-0118: the low default evidence profile names a lint entry that the CI does not produce, and the plan of a run-made low contract names no lint gate (found at the evaluation of TASK-116)

- Status: open
- Opened: 2026-11-03 (session 08342c65; TASK-116, decisions D-4684 and D-4685)
- Deferred by: decision agent (A41, A51), D-4685
- Decision group: A (self-build)

## What
The default evidence profile of a low-risk task is functional [build, lint] (assurance-model.md section 5, line 78; AIEOS-concept.md:701; conformance-scenarios-initial.md:11, whose default plan is G0 scope, G1 build, G2 lint). The CI of this repository produces a build record (the G1 step, `python3 -m compileall -q src tests`) but no step that is a lint: a search of the branch log of TASK-116 (aieos-checks run 41494750362) for lint, ruff, flake, pyflakes and similar finds only test names and the bandit step, and D-4050 (line 43) had already recorded that no lint or line-length check exists in the workflows. No earlier task met the entry: TASK-116 is the first task whose class is low (every earlier contract under docs/tasks/ is high or critical, both cumulative on medium, and medium holds no lint, D-279).

Second, the verification plan that `aieos run` wrote for TASK-116 (.aieos/tasks/TASK-116.yaml, verification_plan) names G0 scope, G1 build and G3 review, but no G2 lint, although the class it wrote (risk: low) needs the lint entry. The plan of a run-made low contract does not follow the default plan of conformance-scenarios-initial.md:11.

The decision agent may not accept a task with an evidence entry dropped (CR-002-concept-errata.md part 4 limit 8; assurance-model.md:95). TASK-116 was therefore not accepted at its task commit T b202e609 (D-4685): the outcome is insufficient evidence, the only unmet entry is functional lint, and the governor's shadow over the 19 records (docs/records/TASK-116.jsonl) says the same and is advisory (A31).

## Resume when
A lint step exists in the CI channel and a record of it, bound to a commit of the task, can be shown; or the owner answers the question on the low profile's lint entry (limit 8); or a task changes the plan `aieos run` writes for a low contract.

## Follow-ups owed
- A later task that adds a lint step to the workflows (a change under `.github/`, its own decision under A66), or that decides what counts as lint for a docs-only change.
- A later task that makes the plan written by `aieos run` follow the default plan of the class it writes (G2 lint for low).
- TASK-116 can be re-evaluated only with evidence bound to T (b202e609292fcbcbd6503586f1d61b291c4cb70a).

## Depends on
TASK-116; DEF-0115 (the branch-first route and the rule that a task's commits go to main only after its acceptance); DEF-0117 (run-made contracts).

## Log
- 2026-11-03: opened (session 08342c65), at the evaluation of TASK-116 (decisions D-4684 and D-4685).
- 2026-11-05 (session a0a0bdef): TASK-117's evidence profile also has no lint record (the CI produces none, as at TASK-116); handled in the form of D-4685; acceptance decision D-4776; the status stays open.

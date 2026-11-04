# L-0021: Check a CI claim against the workflow text

Rule: Before a claim about which CI run does what goes into a commit message, a record or a request, read the step's condition in the workflow file and cite its lines (D-814).

- Status: active
- Category: verification
- Binding: record only. Related: decisions D-813, D-814; L-0007 (state what a check proves); L-0020 (a CI step a dry run cannot foresee).

## Pattern
A claim about the CI channel's behaviour (which run checks what, on which base) is written from memory or inference and reaches a public text before the workflow's own condition is read.

## Occurrences
One in session 2026-10-15-1601 (../History/2026-10/2026-10-15-1601-reference-export-contracted-after-the-policy-v4-landing.md):
- **2026-10-15 (D-813, D-814).** The records commit 1121c235's message said RISK-01's first run over policy v4 was the base run of its own push; the conformance base run on main runs only for a head commit with one AIEOS-Task trailer, so run 270 printed "no run". The decision agent accepted the sentence without checking. Corrected in the History and DEF-0063; no history rewrite.
- 2026-11-02 (../History/2026-11/2026-11-02-0522-m8-stage-8-task-114-the-ci-path-for-a-contract-the-core-writes.md, D-4523): I wrote "its detect found docs/tasks/TASK-114.yaml" as an inference from a step's success; the log said "no task" (cp105).

Occurrence in session a0a0bdef, part 2 (2026-11-05; ../History/2026-11/2026-11-05-0204-m8-stage-8-task-118-the-launchers-adapter-name-matches-the-declaration-a0a0bdef.md; D-4845, D-4846:23; the worker's own claim until checked):
- The expectation in the decision of D-4845 that the conformance base run on main would "pass" for the records commit F was wrong: for a push to main whose head commit has no trailer the workflow prints "conformance base run: a push to main whose head commit has 0 trailer lines; no run" (aieos-checks.yml:1067-1068); the decision agent wrote it without reading those lines (D-4846:23), and I reported the real line at D-4846 without marking that it differed. The claim reached a decision text, not a public text.

## Why it happens
The request and its review checked the change-set's own bytes, not the workflow's conditions that the sentence described.

## Prevention and detection
- Cite the workflow lines (and, after the run, the run's own log line) for every sentence that says what a CI run will do or did.

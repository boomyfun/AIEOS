# DEF-0155: the INV-004 rule of the CI sees single, case-sensitive string constants only, so a constructed or upper-cased spelling of the project-state directory name passes in src/

- Status: open
- Opened: 2026-11-21 (session 0be70981; D-7030 C4, the task review F3 of TASK-157)
- Deferred by: decision agent (A41, A51), D-7030
- Decision group: A for this record and for a change of the deterministic_rule step under .github/ (its own A66 decision; the check of INV-004 as written); a change of what INV-004 itself says (the constitution) is not covered by A66 and goes to the owner (fail closed)
- Blocks v0.1: no (proposed: the rule reports as a CI finding; the TASK-157 module was read by its two reviews and builds no such string; the rest of src/ was not searched for constructions, only for the literal, which the CI refuses)
- Scheduled in: not scheduled; with the next change of the deterministic_rule step of .github/workflows/aieos-checks.yml

## What
The deterministic_rule step of .github/workflows/aieos-checks.yml refuses, under src/, any ast string Constant that contains a dot directly before the lowercase name of the project-state directory, except in two files that are allowed (the core's single writer and the shell-allowlist reader). The check is on single constants and is case-sensitive: a string built by concatenation (for example a dot plus the name), by formatting, by character codes or in upper case passes it (aieos-checks.yml :2103-:2105; the reviewers of TASK-157 noted it: the contract review v2 finding 12 and the task review F3). The module of TASK-157 avoids the literal by a rule that tests only whether the first segment of a path begins with a dot, and a contract condition forbids any construction of the text (D-7017 C1); that condition is checked by reading the code, not by the CI.

## Why deferred
Closing it needs a change under .github/ (its own A66 decision and a test of the new pattern against the real tree, L-0046) and a reading of what INV-004 is meant to forbid; TASK-157 was not the place (its write set had no .github path).

## Resume when
The next change of the deterministic_rule step, or when a src/ file is found to build the name, or when a task needs to name the directory in src/.

## Related
DEF-0154 (the evaluator inputs outside the lists); INV-004; the contract of TASK-157 (AC3); docs/runs/TASK-157-acceptance.md Limits (F3).

## Log
- 2026-11-21: opened (session 0be70981; D-7030 C4; D-7044 acceptance of TASK-157, Limits F3).

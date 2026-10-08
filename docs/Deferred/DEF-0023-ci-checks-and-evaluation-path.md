# DEF-0023: The CI checks and the evaluation path of the first code task

- Status: done
- Opened: 2026-10-08 (decision file D-178)
- Deferred by: decision agent (A41), D-178: the first code task's contract is not approved until these are settled; both points are the owner's and are asked once, together, when their drafts exist.
- Decision group: B. Any change under `.github/` is the owner's (constitution SEC-003; A51 item (4)); a push of unaccepted task code to a GitHub ref other than a normal fast-forward of `main` is a new kind of ref change that the standing push authorization does not cover.

## What
- **The CI checks.** Every tool entry of a task's evidence profile is met only by records from the CI channel (constitution §4). The workflow `.github/workflows/aieos-checks.yml` runs the SEC-001 secret scan, the SEC-002 pattern rules and the SEC-003 record only. The first code task (high risk) needs CI records for build, unit and integration tests, the deterministic rules of its applicable articles (for example INV-001's and INV-002's import and pattern rules), static security analysis, and, if the applicable articles stay as D-178 M1 reads them, property tests and replay. The checkers are code, written in tasks of their own; the workflow revision is the owner's.
- **The evaluation path.** The CI channel runs on pushes, so the task's commit must be on GitHub before a tool entry can be met. Pushing unaccepted code to `main` makes it public and permanent even if it is rejected later; pushing it to another ref (a task branch or a pull request) is the owner's to allow.

## Why deferred
The first code task's contract (TASK-001, drafted in session 0b380044) was not approved (D-178, MODIFY): it is revised next session together with drafts of these two points.

## Resume when
The next session, after the decision files from D-174: TASK-001 revised under D-178 M1 to M4, the CI-checks plan and the evaluation path drafted, then one owner question covering both.

## Depends on
DEF-0011 (M2); the Master Plan revision 2 §8.

## Log
- 2026-10-08: opened (decision file D-178). ../History/2026-10/2026-10-08-2307-follow-on-texts-and-first-contract-draft.md
- 2026-10-09 (session c925987e): the owner answered "1 cách 1, 2 có" (:1208) to the one question of decision D-183, recorded as DM A61 (revision 41, commit 8632054): way 1 for the CI channel's revision 2, pushed as commit 8a21a57; and yes to pushing a code task's own commits to a branch of its own, `main` receiving only accepted work. Status: open, until the first code task is evaluated. Remaining: the contract approved with `base_commit` = 8a21a57 (written in full) and committed on `main`; the relay of the start of code; TASK-001's work and its first evaluation. Decision files D-181 to D-184. ../History/2026-10/2026-10-09-0024-ci-revision-and-task-branches.md
- 2026-10-09 (session 7a8f6d22): TASK-001 was evaluated through its own branch (A61): three commits, CI runs 19 to 21 with every step successful, two rounds of reviews; the decision agent accepted it at 33aa1c8 and it was fast-forwarded onto main (D-191). The CI observability limit (the step logs need sign-in) is carried in DEF-0024. Status: done. Decision files D-186 to D-191. ../History/2026-10/2026-10-09-0153-task-001-landed.md

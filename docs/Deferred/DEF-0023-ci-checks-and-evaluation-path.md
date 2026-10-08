# DEF-0023: The CI checks and the evaluation path of the first code task

- Status: waiting-owner
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

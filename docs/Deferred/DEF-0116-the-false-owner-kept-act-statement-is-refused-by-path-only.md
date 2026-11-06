# DEF-0116: the false owner_kept_act statement is refused by path only

- Status: open
- Opened: 2026-11-02 (session 08342c65; TASK-115, decision D-4643, Finding A)
- Deferred by: decision agent (A41, A51), D-4643 and D-4647
- Decision group: A (self-build)
- Blocks v0.1: no (the standing practice: no `aieos run --owner-kept-act false` on those paths)
- Scheduled in: M8, the run-made contract conversion task (owner_kept_act and the paths the run refuses), before the first real run

## What
`aieos run --class decision_agent --owner-kept-act false` (TASK-115, commits X ba83811c, X2 b8b003f4, X3 13647f14) writes `owner_kept_act: false` into a run-made contract only on that explicit statement, and refuses the statement (reason `argument`) for a write path under `.github/`, equal to `docs/pre-genesis/measurement-protocol.md`, or equal to or under `docs/pre-genesis/measurements`, case-insensitively. The last two are the paths the CI's OPS-002 step routes to the owner (OWNER_PATHS, aieos-checks.yml:475-476 and :492); `.github/` is routed by SEC-003 to the owner or, for the self-build, to the decision agent's own decision (DM A66). The guard works on paths only. It does not refuse the statement when the write set holds AIEOS-concept.md, docs/pre-genesis/decision-matrix.md, docs/pre-genesis/constitution.md, CLAUDE.md or a path under `.claude/`, paths whose content or effect the owner keeps in whole or in part (the concept and its errata, the A41 row of the matrix, the approval of the constitution while CR-002 is open, and Claude Code's permission settings) but that no path rule of the CI covers.

## Standing practice until this is closed
No `aieos run --owner-kept-act false` whose write set holds one of those paths.

## Resume when
A DEF task takes up the owner-kept acts outside the path rules (with the conversion-gap DEF), or the next change to `_run_statement_findings` in src/aieos_bootstrap/launcher.py.

## Follow-ups owed
- A task that adds those paths (or a rule by act, not by path) to the refusal, with a test for each.

## Depends on
TASK-115; DEF-0101 (the launchers' open requirements).

## Log
- 2026-11-02: opened (session 08342c65), found by the decision agent's own review of X3 in D-4643 and missed by the way-2 reviews R115x, R115x2, R115w and R115v.
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass E decision D-5258): read in full; _run_statement_findings was last changed by TASK-115 itself (13647f1, git log -L), so the Resume-when event (a DEF task taking up the owner-kept acts outside the path rules, or the next change of that function) is not met; it goes with the conversion-gap task of DEF-0117. State: open; Blocks v0.1: no (the standing practice: no `aieos run --owner-kept-act false` on those paths); Scheduled in: M8, the run-made contract conversion task (owner_kept_act and the paths the run refuses), before the first real run.

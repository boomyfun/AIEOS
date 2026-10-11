# DEF-0051: the derived channel, specification 2 revision 3's open point 11

- Status: open
- Opened: 2026-10-12 (decisions D-563 and D-564)
- Deferred by: decision agent (A41), D-563 (option (a): the counting rules removed from specification 2 revision 3 and carried as the requirements of its section 10 point 11) and D-564 (the dispositions of all 31 findings).
- Decision group: A (a specification revision under A51, B9, and later tasks within the self-build).

## What
- Specification 4 §5 item 3 asks that a record's class be checked against the channel it came through, and that a record written by the implementer's session count only as `agent_declared`. Specification 2 revision 3 (DM F36) adds the record keys `session`, `ci_run` and `acs` and the commit trailer `AIEOS-Implementer`, each the writer's statement, recorded and not checked; no check gives any record more or less standing because of them until its section 10 point 11 is settled.
- A first draft of revision 3 carried the counting rules themselves (a derived channel of five kinds, a table of classes against channels, an implementer rule, a trailer-based `models` check, a hold for earlier records). One way-2 round on claude-sonnet-5-5 (three reviewers, Y1 to Y3; all "fail") found eleven blocking findings in six clusters; they are the derivation's requirements:
  - (A) Y1-1, Y2-1, Y3-2: the class of a `decision_agent`, `human_authority` or review record must not rest on strings its writer supplies (`decision_ref`, a quoted owner line, a named `session`) unless a check resolves them; in this project the implementing session writes every records line.
  - (B) Y1-3, Y2-2, Y3-3: the task's commits and every lease that held the task must come from facts the core records (for example `task.submitted` with its `fencing_token`), not from agent-written trailers, failing closed where a commit or a lease's session cannot be resolved, also after the local store has dropped the lease.
  - (C) Y1-4, Y3-1: the core channel must attribute a record's origin, not only its transport (a record an agent session submits counts as `agent_declared` whatever class it names).
  - (D) Y1-2: a trailer-based `models` check applies only to commits made after the trailer exists.
  - (E) Y2-3: a CI re-fetch must be bound to the step that runs the record's gate, map the CI result onto `outcome`, and fail closed on a skipped, cancelled or unreadable step.
  - (F) Y2-4: only pinned checks may re-derive a record from Git, and the derivation must say from which commit or event it applies.
- Non-blocking findings carried with them: Y1-5 (the tension with specification 2 section 9 and CR-001 E3), Y1-6 and Y3-6 (with E), Y1-7 (section 6.4's decision records from the CI channel), Y1-8 (`delegate_ai` core-only, option-b projects), Y1-9 (with F), Y1-11 (`models.reviewer` self-declared; model-id aliases; several implementer sessions), Y2-5 and Y3-8 (with A), Y2-7 (specification 4's wording "recorder" to be revised), Y2-8 (with D), Y3-4 (with D), Y3-9 (with F: the switch-off "before AIEOS governs its own build").
- Applied in revision 3 or removed with the rules: Y1-10, Y2-6, Y2-9, Y3-5, Y3-7, Y3-10, Y3-11, and in part Y2-8 and Y3-9 (decision D-564's table).

## Why deferred
D-563: each fix is in substance the design of the core's caller (DEF-0030), whose facts do not exist yet; a fourth design round inside specification 2 would grow again, and rules-book rule 8 would need the owner's yes on cost versus value first.

## Resume when
After the core's submission path exists (the task after TASK-024, the row 13 note of decision D-567), so that the commit set, the lease's session and the appending party are facts in code; then a specification 2 revision settles point 11, and a later task implements the check.

## Depends on
DEF-0030 (the core's caller); TASK-024 (the Git reader).

## Log
- 2026-10-12: opened (decisions D-563, D-564; specification 2 revision 3, DM F36, on main as b586f9ea). ../History/2026-10/2026-10-11-2336-spec-2-revision-3-and-the-git-reader-contract.md

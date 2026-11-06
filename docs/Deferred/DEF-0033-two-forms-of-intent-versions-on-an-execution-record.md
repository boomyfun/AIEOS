# DEF-0033: The two forms of `intent_versions` on an execution decision record

- Status: open
- Opened: 2026-10-10 (decision files D-333, D-334 and D-337)
- Deferred by: decision agent (A41), D-333 C3 and D-337: TASK-011 reads the collision for `decision.execution` payloads only, without changing either specification; the specifications settle it at their next revisions.
- Decision group: A (a specification revision under A51, B9).
- Blocks v0.1: no (both forms are accepted for decision.execution payloads)
- Scheduled in: M8, the Resume Check and records fix task (with the component-path reading of context_compiler and specification 6 section 11), before the M8 exit review

## What
- Specification 3 §9 names a key `intent_versions` on the execution decision record, "for each entry: the contract's version and the current one" (an object of `{contract, current}`); specification 2 §6.2 names a record key `intent_versions` that maps ids to versions `v<digits>`, and records.check_record checks it so. The two forms meet on one payload.
- TASK-011's contract (AC3, read by D-337's erratum): for a `decision.execution` payload, `intent_versions` is accepted in either form and refused when it is neither; every other payload keeps the record form. TASK-008's records give §9's form.
- The next revisions of specifications 2 and 3 say which name or form each record uses (for example a different key name for §9's pairs), and records.py follows under its own task.

## Why deferred
D-333 C3: TASK-011 lets the Resume Check's record pass the checker the runner judges with; a specification revision is its own change (B9) and was outside the session's tasks. D-337: the strict reading refused the record form that TASK-001's property test generates, so the erratum accepts both forms until the revision.

## Resume when
At the next revision of specification 2 or specification 3, and before any reader of `decision.execution` records depends on one form.

## Depends on
TASK-011 accepted.

## Log
- 2026-10-10: opened (decision files D-333, D-334 and D-337).
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass F batch 1, decision D-5267 (K5)): read in full; the first half of the event (the next revision of specification 2 or 3) occurred without taking the item: specification 2 was revised several times since 2026-10-10 and specification 3 has had revisions 5 and 6 (citation only); docs/specs/spec-03-resume-check-and-decision-engine.md :127 still reads 'for each entry: the contract's version and the current one' and src/aieos_bootstrap/records.py :35, :525-:528 and :634-:639 still accept both forms; whether a reader of decision.execution records depends on one form was not checked. State: open; Blocks v0.1: no (both forms are accepted for decision.execution payloads); Scheduled in: M8, the Resume Check and records fix task (with the component-path reading of context_compiler and specification 6 section 11), before the M8 exit review.
